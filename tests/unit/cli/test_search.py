"""Unit tests for search command."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from gitctx.cli.main import app


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
                "commit_date": "2025-10-13",
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
    assert "Search the indexed repository" in result.stdout


def test_search_requires_query(cli_runner):
    """Verify search requires a query argument."""
    result = cli_runner.invoke(app, ["search"])
    assert result.exit_code == 2  # Exit code 2 for missing query
    # Accept either Typer's default message or our custom message
    output = result.stdout + result.stderr
    assert "Query required" in output or "Missing argument" in output


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_default_output(mock_search_repo):
    """Verify default mode is terse (file:line:score format)."""
    result = mock_search_repo.invoke(app, ["search", "authentication"])
    assert result.exit_code == 0
    # Check TUI_GUIDE.md format: file:line:score ● commit
    assert ".py:" in result.stdout or ".md:" in result.stdout
    assert "●" in result.stdout or "[HEAD]" in result.stdout  # Platform-aware
    assert "results in" in result.stdout  # Summary line


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_verbose_mode(mock_search_repo):
    """Verify --verbose shows code context."""
    result = mock_search_repo.invoke(app, ["search", "authentication", "--verbose"])
    assert result.exit_code == 0
    # Verbose should include code snippets
    assert "def " in result.stdout or "class " in result.stdout or "##" in result.stdout
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    assert len(lines) > 10  # Multi-line with context


def test_search_limit_option(mock_search_repo):
    """Verify --limit option works."""
    result = mock_search_repo.invoke(app, ["search", "test", "--limit", "2"])
    assert result.exit_code == 0
    # Should mention the limit in some way
    assert "2" in result.stdout or "results" in result.stdout


def test_search_short_flags(mock_search_repo):
    """Verify -n and -v short flags work."""
    result = mock_search_repo.invoke(app, ["search", "test", "-n", "3"])
    assert result.exit_code == 0

    result = mock_search_repo.invoke(app, ["search", "test", "-v"])
    assert result.exit_code == 0


def test_search_help_text(cli_runner):
    """Verify help text includes all options."""
    result = cli_runner.invoke(app, ["search", "--help"])
    assert "QUERY" in result.stdout or "query" in result.stdout
    assert "--limit" in result.stdout
    assert "-n" in result.stdout
    assert "Number of results" in result.stdout or "Maximum" in result.stdout


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_shows_history_and_head(mock_search_repo):
    """Verify search demonstrates both historical and HEAD results."""
    result = mock_search_repo.invoke(app, ["search", "test"])
    assert result.exit_code == 0
    # Should have HEAD indicator on some results
    has_head = "●" in result.stdout or "[HEAD]" in result.stdout or "HEAD" in result.stdout
    # Should have results with file paths
    lines_with_results = [
        line for line in result.stdout.split("\n") if ".py:" in line or ".md:" in line
    ]
    assert len(lines_with_results) >= 2  # At least 2 results to show mix
    assert has_head  # At least one HEAD result


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_mcp_flag(mock_search_repo):
    """Verify --mcp flag outputs structured markdown."""
    result = mock_search_repo.invoke(app, ["search", "test", "--mcp"])
    assert result.exit_code == 0
    # Check for YAML frontmatter
    assert "---" in result.stdout
    assert "status: success" in result.stdout
    assert "query: test" in result.stdout
    # Check for markdown structure
    assert "# Search Results:" in result.stdout
    assert "## Summary" in result.stdout
    assert "## Results" in result.stdout
    # Check for metadata
    assert "**Metadata**:" in result.stdout
    assert "```python" in result.stdout or "```markdown" in result.stdout


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_mcp_has_yaml_frontmatter(mock_search_repo):
    """Verify MCP mode includes valid YAML frontmatter."""
    result = mock_search_repo.invoke(app, ["search", "auth", "--mcp"])
    assert result.exit_code == 0
    # Check for YAML frontmatter (may have progress indicator before it)
    assert "---\n" in result.stdout
    assert "status: success" in result.stdout
    assert "results_count:" in result.stdout
    assert "duration_seconds:" in result.stdout
    # Verify frontmatter is near the start (within first 200 chars after any progress/success indicators)
    frontmatter_pos = result.stdout.find("---\n")
    assert frontmatter_pos < 200, "YAML frontmatter should be near the start of output"


@pytest.mark.skip(reason="Output formatting deferred to STORY-0001.3.3")
def test_search_mcp_with_limit(mock_search_repo):
    """Verify MCP mode respects limit option."""
    result = mock_search_repo.invoke(app, ["search", "test", "--mcp", "--limit", "2"])
    assert result.exit_code == 0
    assert "results_count: 2" in result.stdout
    # Should have exactly 2 result sections (numbered ### 1. and ### 2.)
    assert "### 1." in result.stdout
    assert "### 2." in result.stdout
    assert "### 3." not in result.stdout


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
        # LanceDB raises generic exceptions with table names in message
        mock_store_class.side_effect = Exception("Table 'code_chunks' not found in database")

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "Error: Index corrupted" in output
        assert "gitctx clear && gitctx index" in output
