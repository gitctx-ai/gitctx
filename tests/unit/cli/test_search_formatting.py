"""Unit tests for search command formatter integration."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock, patch

import pytest

from gitctx.cli.main import app


@pytest.fixture
def mock_formatter_search(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base, test_embedding_vector
):
    """Create mock search environment for formatter testing."""
    # Create repo directory
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation
    subprocess.run(
        ["git", "init"], cwd=repo, env=git_isolation_base, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, env=git_isolation_base, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        env=git_isolation_base,
        check=True,
    )

    # Add file and commit
    (repo / "test.py").write_text("def test(): pass")
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(["git", "commit", "-m", "Test"], cwd=repo, env=git_isolation_base, check=True)

    # Create index directory
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test")
    mock_settings.user = Mock()
    mock_settings.user.theme = "monokai"

    # Mock store with results
    mock_store = Mock()
    mock_store.count = Mock(return_value=10)
    mock_store.get_query_embedding = Mock(return_value=None)
    mock_store.search = Mock(
        return_value=[
            {
                "file_path": "test.py",
                "start_line": 1,
                "end_line": 5,
                "_distance": 0.92,
                "is_head": True,
                "commit_sha": "abc1234",  # pragma: allowlist secret
                "commit_message": "Test commit",
                "commit_date": 1760501897,  # Unix timestamp for 2025-10-14
                "author_name": "Alice",
                "chunk_content": "def test(): pass",
                "language": "python",
            }
        ]
    )

    # Mock embedder
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore", return_value=mock_store),
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_embedder = Mock()
        mock_embedder.get_cache_key = Mock(return_value="test_key")
        mock_embedder.embed_query = Mock(return_value=test_embedding_vector())
        mock_embedder_class.return_value = mock_embedder
        yield {"runner": isolated_cli_runner, "store": mock_store}


def test_search_default_format_terse(mock_formatter_search):
    """Test that default format is terse."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test"])

    assert result.exit_code == 0
    # Terse format: one line per result
    assert "test.py:1:" in result.stdout


def test_search_format_verbose_flag(mock_formatter_search):
    """Test --verbose flag sets verbose format."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--verbose"])

    assert result.exit_code == 0
    # Verbose format: multi-line with code blocks
    assert "test.py:1-5" in result.stdout
    assert "def test(): pass" in result.stdout


def test_search_format_mcp_flag(mock_formatter_search):
    """Test --mcp flag sets MCP format."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--mcp"])

    assert result.exit_code == 0
    # MCP format: YAML frontmatter + markdown
    assert "---" in result.stdout
    assert "results:" in result.stdout
    assert "file_path: test.py" in result.stdout


def test_search_verbose_short_flag_sets_format(mock_formatter_search):
    """Test -v short flag sets verbose format."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "-v"])

    assert result.exit_code == 0
    # Verbose format
    assert "test.py:1-5" in result.stdout


def test_search_mcp_and_verbose_mutually_exclusive(mock_formatter_search):
    """Test --mcp and --verbose flags are mutually exclusive."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--mcp", "--verbose"])

    assert result.exit_code == 2
    # Error messages from Typer may be in stdout or stderr
    combined_output = result.stdout + result.stderr
    assert "mutually exclusive" in combined_output


def test_search_results_summary_line(mock_formatter_search):
    """Test results summary line shows count and duration."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test"])

    assert result.exit_code == 0
    # Should show: "1 results in X.XXs"
    assert "1 results in" in result.stdout
    assert "s" in result.stdout  # Has seconds


def test_search_zero_results_summary(mock_formatter_search):
    """Test zero results summary line."""
    # Mock zero results
    mock_formatter_search["store"].search.return_value = []

    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test"])

    assert result.exit_code == 0
    # Should show: "0 results in X.XXs"
    assert "0 results in" in result.stdout


def test_search_format_flag_verbose(mock_formatter_search):
    """Test --format verbose works like --verbose."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--format", "verbose"])

    assert result.exit_code == 0
    # Verbose format
    assert "test.py:1-5" in result.stdout


def test_search_format_flag_mcp(mock_formatter_search):
    """Test --format mcp works like --mcp."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--format", "mcp"])

    assert result.exit_code == 0
    # MCP format
    assert "---" in result.stdout
    assert "results:" in result.stdout


def test_search_format_flag_terse(mock_formatter_search):
    """Test --format terse explicit setting."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--format", "terse"])

    assert result.exit_code == 0
    # Terse format
    assert "test.py:1:" in result.stdout


def test_search_unknown_formatter_error(mock_formatter_search):
    """Test unknown formatter name raises error."""
    runner = mock_formatter_search["runner"]
    result = runner.invoke(app, ["search", "test", "--format", "invalid"])

    assert result.exit_code != 0
    # Error messages from Typer may be in stdout or stderr
    combined_output = result.stdout + result.stderr
    assert "Unknown formatter" in combined_output or "invalid" in combined_output
