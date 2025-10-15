"""Unit tests for search command argument parsing and stdin handling."""

import subprocess
import sys
from unittest.mock import Mock, patch

from gitctx.cli.main import app


def test_search_variadic_args_joined(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Test that variadic args are joined with spaces: 'auth middleware' → 'auth middleware'."""
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

    # Mock LanceDBStore
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss
    mock_store.search = Mock(return_value=[])

    # ACT - Search with multiple unquoted args
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(return_value=test_embedding_vector())
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "auth", "middleware"])

        # ASSERT
        assert result.exit_code == 0
        # Verify QueryEmbedder was called with joined query
        mock_embedder.embed_query.assert_called_once()
        call_args = mock_embedder.embed_query.call_args[0]
        assert call_args[0] == "auth middleware"


def test_search_flags_before_args(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Test that flags can appear before query terms: '--limit 5 auth' parses correctly."""
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

    # Mock LanceDBStore
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss
    mock_store.search = Mock(return_value=[])

    # ACT - Search with flags before query terms
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(return_value=test_embedding_vector())
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "--limit", "5", "auth"])

        # ASSERT
        assert result.exit_code == 0
        # Verify QueryEmbedder was called with just "auth" (flags parsed separately)
        mock_embedder.embed_query.assert_called_once()
        call_args = mock_embedder.embed_query.call_args[0]
        assert call_args[0] == "auth"


def test_search_stdin_pipe(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Test that search reads from stdin when no args provided (piped input)."""
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

    # Mock LanceDBStore
    mock_store = Mock()
    mock_store.count = Mock(return_value=100)
    mock_store.get_query_embedding = Mock(return_value=None)  # Cache miss
    mock_store.search = Mock(return_value=[])

    # ACT - Search with stdin input (CliRunner simulates piped input automatically)
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_cache_key")
        mock_embedder.embed_query = Mock(return_value=test_embedding_vector())
        mock_embedder_class.return_value = mock_embedder

        # CliRunner with input= simulates piped stdin (non-TTY)
        result = isolated_cli_runner.invoke(app, ["search"], input="database setup\n")

        # ASSERT
        assert result.exit_code == 0
        # Verify QueryEmbedder was called with stdin content
        mock_embedder.embed_query.assert_called_once()
        call_args = mock_embedder.embed_query.call_args[0]
        assert call_args[0] == "database setup"


def test_search_empty_stdin_non_interactive(isolated_cli_runner, monkeypatch):
    """Test that empty stdin with no args exits with code 2 (non-interactive mode)."""
    # ARRANGE - Simulate non-interactive terminal (piped but empty)
    # CliRunner automatically simulates non-TTY when input= is used

    # ACT - Search with empty stdin
    result = isolated_cli_runner.invoke(app, ["search"], input="\n")

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "Error: Query required" in output


def test_search_no_args_interactive(isolated_cli_runner, monkeypatch):
    """Test that no args in interactive terminal exits with code 2."""
    # ARRANGE - Simulate interactive terminal (TTY)
    # When CliRunner is used without input=, it simulates interactive mode
    # But we need to explicitly test isatty() behavior

    # Mock stdin.isatty to return True (interactive terminal)
    original_isatty = sys.stdin.isatty
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    # ACT - Search with no args and no stdin
    result = isolated_cli_runner.invoke(app, ["search"])

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "Error: Query required" in output

    # Cleanup
    monkeypatch.setattr(sys.stdin, "isatty", original_isatty)


def test_search_empty_query_after_strip(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Test that stdin with only whitespace is treated as empty."""
    # ARRANGE - Set up minimal git repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git
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

    # ACT - Search with whitespace-only stdin
    result = isolated_cli_runner.invoke(app, ["search"], input="   \n\n  \n")

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "Error: Query required" in output


def test_search_query_exceeds_token_limit(isolated_cli_runner):
    """Test that queries exceeding MAX_QUERY_TOKENS (8191) exit with code 2."""
    # ARRANGE - Create a very long query that exceeds token limit
    # Average ~0.75 tokens per word, so ~11,000 words should exceed 8191 tokens
    long_query = " ".join(["authentication"] * 11000)

    # ACT - Search with oversized query
    result = isolated_cli_runner.invoke(app, ["search", long_query])

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "exceeds 8191 tokens" in output
    assert "Try a shorter query" in output


def test_format_and_verbose_mutually_exclusive(isolated_cli_runner):
    """Test that --format and --verbose are mutually exclusive."""
    # ACT - Try to use both --format and --verbose
    result = isolated_cli_runner.invoke(app, ["search", "query", "--format", "terse", "--verbose"])

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "--format cannot be used with --verbose" in output


def test_format_and_mcp_mutually_exclusive(isolated_cli_runner):
    """Test that --format and --mcp are mutually exclusive."""
    # ACT - Try to use both --format and --mcp
    result = isolated_cli_runner.invoke(app, ["search", "query", "--format", "terse", "--mcp"])

    # ASSERT
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "--format cannot be used with --mcp" in output


def test_format_and_verbose_any_value(isolated_cli_runner):
    """Test that --format (any value) and --verbose are mutually exclusive."""
    # ACT - Try to use --format mcp with --verbose
    result = isolated_cli_runner.invoke(app, ["search", "query", "--format", "mcp", "--verbose"])

    # ASSERT - Format value doesn't matter, still mutually exclusive
    assert result.exit_code == 2
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "--format cannot be used with --verbose" in output


def test_tiktoken_import_error_fallback():
    """Test that query validation gracefully handles missing tiktoken."""
    from unittest.mock import patch  # noqa: PLC0415 # Test-specific import for mocking

    from gitctx.cli.search import (  # noqa: PLC0415 # Import private function for testing
        _get_query_text,
    )

    # Create a very long query that would exceed token limit if tiktoken was available
    long_query = ["authentication"] * 11000

    # Mock tiktoken import to fail
    with (
        patch.dict("sys.modules", {"tiktoken": None}),
        patch("builtins.__import__", side_effect=ImportError("tiktoken not installed")),
    ):
        # ACT - Should not raise even with long query (validation skipped)
        result = _get_query_text(long_query)

        # ASSERT - Query accepted without validation
        assert result == " ".join(long_query)
