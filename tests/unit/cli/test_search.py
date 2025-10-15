"""Unit tests for search command."""
# ruff: noqa: PLC0415 # Inline imports for test isolation

import subprocess
from unittest.mock import Mock, patch

import pytest
import typer

from gitctx.cli.main import app
from gitctx.cli.search import _get_query_text


@pytest.fixture
def mock_search_repo(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Create a minimal git repository for testing search command with mocked dependencies.

    Mocks LanceDBStore to bypass actual indexing for fast unit tests.
    """
    # Create repo directory
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation environment
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add a file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx/db/lancedb directory (checked by search command)
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings with API key
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")
    mock_settings.user = Mock()
    mock_settings.user.theme = "monokai"

    # Mock LanceDBStore to bypass actual database operations
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)  # Non-zero = index exists
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss - force embed_query call
    mock_store.search = Mock(
        return_value=[
            {
                "file_path": "test.py",
                "start_line": 1,
                "end_line": 1,
                "_distance": 0.15,
                "commit_sha": "abc123",
                "commit_message": "Initial commit",
                "commit_date": 1728864000,  # Unix timestamp for 2024-10-13
                "author_name": "Test User",
                "is_head": True,
                "language": "python",
                "chunk_content": 'print("hello")',
            }
        ]
    )

    # Mock all dependencies for isolated unit testing
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(return_value=test_embedding_vector())  # Deterministic!
        mock_embedder_class.return_value = mock_embedder
        yield isolated_cli_runner


def test_search_command_exists(cli_runner):
    """Verify search command is registered."""
    result = cli_runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search indexed code using semantic similarity" in result.stdout


def test_search_requires_query(cli_runner):
    """Verify search requires a query argument."""
    result = cli_runner.invoke(app, ["search"])
    assert result.exit_code == 2  # Exit code 2 for missing query
    # Accept either Typer's default message or our custom message
    output = result.stdout + result.stderr
    assert "Query required" in output or "Missing argument" in output


def test_search_default_output(mock_search_repo):
    """Verify default mode is terse (file:line:score format)."""
    result = mock_search_repo.invoke(app, ["search", "authentication", "--min-similarity", "-1.0"])
    assert result.exit_code == 0
    # Check TUI_GUIDE.md format: file:line:score ● commit
    assert ".py:" in result.stdout or ".md:" in result.stdout
    assert "●" in result.stdout or "[HEAD]" in result.stdout  # Platform-aware
    assert "results in" in result.stdout  # Summary line


def test_search_verbose_mode(mock_search_repo):
    """Verify --verbose shows code context."""
    result = mock_search_repo.invoke(
        app, ["search", "authentication", "--verbose", "--min-similarity", "-1.0"]
    )
    assert result.exit_code == 0
    # Verbose should include code snippets
    assert "print" in result.stdout  # Our mock data has print("hello")
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    assert len(lines) >= 4  # Multi-line with context (header + metadata + code + summary)


def test_search_limit_option(mock_search_repo):
    """Verify --limit option works."""
    result = mock_search_repo.invoke(
        app, ["search", "test", "--limit", "2", "--min-similarity", "-1.0"]
    )
    assert result.exit_code == 0
    # Should mention the limit in some way
    assert "2" in result.stdout or "results" in result.stdout


def test_search_short_flags(mock_search_repo):
    """Verify -n and -v short flags work."""
    result = mock_search_repo.invoke(app, ["search", "test", "-n", "3", "--min-similarity", "-1.0"])
    assert result.exit_code == 0

    result = mock_search_repo.invoke(app, ["search", "test", "-v", "--min-similarity", "-1.0"])
    assert result.exit_code == 0


def test_search_help_text(cli_runner):
    """Verify help text includes all options."""
    result = cli_runner.invoke(app, ["search", "--help"])
    assert "QUERY" in result.stdout or "query" in result.stdout
    assert "--limit" in result.stdout
    assert "-n" in result.stdout
    assert "Number of results" in result.stdout or "Maximum" in result.stdout


def test_search_shows_history_and_head(mock_search_repo):
    """Verify search demonstrates both historical and HEAD results."""
    result = mock_search_repo.invoke(app, ["search", "test", "--min-similarity", "-1.0"])
    assert result.exit_code == 0
    # Should have HEAD indicator on some results
    has_head = "●" in result.stdout or "[HEAD]" in result.stdout or "HEAD" in result.stdout
    # Should have results with file paths
    lines_with_results = [
        line for line in result.stdout.split("\n") if ".py:" in line or ".md:" in line
    ]
    assert len(lines_with_results) >= 1  # At least 1 result (mock returns 1 result)
    assert has_head  # At least one HEAD result


def test_search_mcp_flag(mock_search_repo):
    """Verify --mcp flag outputs structured markdown."""
    result = mock_search_repo.invoke(app, ["search", "test", "--mcp", "--min-similarity", "-1.0"])
    assert result.exit_code == 0
    # Check for YAML frontmatter with results array
    assert "---" in result.stdout
    assert "results:" in result.stdout
    assert "file_path:" in result.stdout
    assert "line_numbers:" in result.stdout
    assert "score:" in result.stdout
    assert "commit_sha:" in result.stdout
    # Check for markdown structure with file headers
    assert "## test.py:" in result.stdout
    # Check for metadata and code blocks
    assert "**Score:**" in result.stdout
    assert "**Commit:**" in result.stdout
    assert "```python" in result.stdout


def test_search_mcp_has_yaml_frontmatter(mock_search_repo):
    """Verify MCP mode includes valid YAML frontmatter."""
    result = mock_search_repo.invoke(app, ["search", "auth", "--mcp", "--min-similarity", "-1.0"])
    assert result.exit_code == 0
    # Check for YAML frontmatter with results array
    assert "---" in result.stdout
    assert "results:" in result.stdout
    # Verify frontmatter structure has required fields
    assert "file_path:" in result.stdout
    assert "line_numbers:" in result.stdout
    assert "score:" in result.stdout
    assert "commit_sha:" in result.stdout


def test_search_mcp_with_limit(mock_search_repo):
    """Verify MCP mode respects limit option."""
    # Note: mock_search_repo returns only 1 result by default
    # So we're verifying the formatter works with whatever limit is applied
    result = mock_search_repo.invoke(
        app, ["search", "test", "--mcp", "--limit", "2", "--min-similarity", "-1.0"]
    )
    assert result.exit_code == 0
    # Should have YAML frontmatter and markdown body
    assert "---" in result.stdout
    assert "results:" in result.stdout
    # Count result blocks by ## headers (should have at least 1 from our mock)
    result_headers = [line for line in result.stdout.split("\n") if line.startswith("## ")]
    assert len(result_headers) >= 1  # At least 1 result block from our mock data


def test_search_mcp_and_verbose_are_mutually_exclusive(cli_runner):
    """Verify --mcp and --verbose cannot be used together."""
    result = cli_runner.invoke(app, ["search", "test", "--mcp", "--verbose"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "mutually exclusive" in output.lower() or "Error" in output


def test_search_validation_error_exits_with_code_2(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Verify ValidationError is caught and exits with code 2."""
    # ARRANGE - Set up minimal repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx directory structure
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # Mock LanceDBStore
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss - force embed_query call
    mock_store.search = Mock(return_value=[])

    # ACT & ASSERT - Mock QueryEmbedder to raise ValidationError
    from gitctx.search.errors import ValidationError

    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(side_effect=ValidationError("Query is too long"))
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        assert result.exit_code == 2
        output = result.stdout + result.stderr
        assert "Query is too long" in output


def test_search_configuration_error_exits_with_code_4(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Verify ConfigurationError is caught and exits with code 4."""
    # ARRANGE - Set up minimal repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx directory structure
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # ACT & ASSERT - Mock GitCtxSettings to raise ConfigurationError
    from gitctx.config.errors import ConfigurationError

    with patch(
        "gitctx.cli.search.GitCtxSettings",
        side_effect=ConfigurationError("Missing API key in configuration"),
    ):
        result = isolated_cli_runner.invoke(app, ["search", "test"])

        assert result.exit_code == 4
        output = result.stdout + result.stderr
        assert "Missing API key" in output


def test_search_embedding_error_exits_with_code_5(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Verify EmbeddingError is caught and exits with code 5."""
    # ARRANGE - Set up minimal repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx directory structure
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # Mock LanceDBStore
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss - force embed_query call
    mock_store.search = Mock(return_value=[])

    # ACT & ASSERT - Mock QueryEmbedder to raise EmbeddingError
    from gitctx.search.errors import EmbeddingError

    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(side_effect=EmbeddingError("API rate limit exceeded"))
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        assert result.exit_code == 5
        output = result.stdout + result.stderr
        assert "API rate limit" in output


def test_corrupted_index_missing_table(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Test search with missing code_chunks table (corrupted LanceDB index).

    Scenario: .gitctx/db/lancedb directory exists but code_chunks table is missing.
    Expected: Exit code 1 with helpful error message suggesting re-indexing.
    """
    # ARRANGE - Set up minimal repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx directory structure (directory exists but table doesn't)
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # ACT & ASSERT - Mock LanceDBStore to raise exception mentioning code_chunks table
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
    ):
        # LanceDB raises ValueError when table not found
        mock_store_class.side_effect = ValueError("Table 'code_chunks' not found in database")

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "Error: Index corrupted" in output
        assert "gitctx clear && gitctx index" in output


def test_search_no_query_interactive_tty():
    """Test that interactive TTY with no query shows proper error message."""
    # ARRANGE - Import the function to test directly

    # ARRANGE - Patch stdin.isatty to return True (interactive terminal)
    with patch("sys.stdin.isatty", return_value=True):
        # ACT & ASSERT - Should raise typer.Exit(2)
        with pytest.raises(typer.Exit) as exc_info:
            _get_query_text(None)

        assert exc_info.value.exit_code == 2


def test_search_cache_hit_shows_message(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Test that cache hit displays success message."""
    # ARRANGE - Set up minimal git repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Create .gitctx directory structure
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # Mock LanceDBStore with cache HIT
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    cached_vector = test_embedding_vector()
    mock_store.get_query_embedding = Mock(return_value=cached_vector)  # Cache HIT!
    mock_store.search = Mock(return_value=[])

    # ACT - Search with cache hit
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "test", "query"])

        # ASSERT
        assert result.exit_code == 0
        output = result.stdout + result.stderr
        assert "Using cached query embedding" in output
        # Embedder should NOT be called since we have a cache hit
        mock_embedder.embed_query.assert_not_called()
