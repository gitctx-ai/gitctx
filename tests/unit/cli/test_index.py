"""Unit tests for index command."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from gitctx.cli.main import app


@pytest.fixture
def mock_git_repo(isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base):
    """Create a minimal git repository for testing index command.

    This creates an isolated git repo in tmp_path so tests don't pollute
    the actual gitctx repository or user's config.

    Uses git_isolation_base for proper security isolation (no GPG, SSH, etc.)
    """
    # Create repo directory
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git with isolation environment (prevents GPG, SSH, credentials)
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

    # Add a file and commit (git_isolation_base automatically disables GPG signing)
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, env=git_isolation_base, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, env=git_isolation_base, check=True
    )

    # Mock load_settings to return a valid settings object
    mock_settings = Mock()
    mock_settings.api_keys = Mock()
    mock_settings.api_keys.openai = "sk-test"
    mock_settings.indexing = Mock()
    mock_settings.indexing.max_tokens_per_chunk = 500
    mock_settings.indexing.overlap_tokens = 50

    with patch("gitctx.core.config.GitCtxSettings", return_value=mock_settings):
        # Mock index_repository to simulate successful indexing with output
        async def mock_index_impl(repo_path, settings, dry_run=False, verbose=False):
            """Mock implementation that produces expected output."""
            if dry_run:
                print("Files:        5")
                print("Lines:        100")
                print("Est. tokens:  500")
                print("Est. cost:    $0.0001")
                print("Range:        $0.0001 - $0.0001 (±20%)")
                return

            if verbose:
                print("→ Walking commit graph", file=__import__("sys").stderr)
                print("→ Generating embeddings", file=__import__("sys").stderr)
                print("\n✓ Indexing Complete\n", file=__import__("sys").stderr)
                print("Statistics:", file=__import__("sys").stderr)
                print("  Commits:      1", file=__import__("sys").stderr)
                print("  Unique blobs: 1", file=__import__("sys").stderr)
                print("  Chunks:       10", file=__import__("sys").stderr)
                print("  Tokens:       50", file=__import__("sys").stderr)
                print("  Cost:         $0.0001", file=__import__("sys").stderr)
                print("  Time:         0:00:01", file=__import__("sys").stderr)
            else:
                # Terse mode - single line
                print("Indexed 1 commits (1 unique blobs) in 0.1s")
                print("Tokens: 50 | Cost: $0.0001")

        # Mock asyncio.run to intercept the async call
        def mock_asyncio_run(coro):
            """Mock asyncio.run to execute our mock implementation."""
            import anyio

            # Create a simple async wrapper
            async def run_mock():
                # Extract arguments from the coroutine if possible
                try:
                    args = coro.cr_frame.f_locals
                    # Close the coroutine to avoid "never awaited" warning
                    coro.close()
                    return await mock_index_impl(
                        repo_path=args.get("repo_path"),
                        settings=args.get("settings"),
                        dry_run=args.get("dry_run", False),
                        verbose=args.get("verbose", False),
                    )
                except Exception:
                    # Close the coroutine if extraction failed
                    coro.close()
                    # Fallback: just run with defaults
                    return await mock_index_impl(
                        repo_path=None, settings=None, dry_run=False, verbose=False
                    )

            # Use anyio.run() to avoid event loop contamination in full test suite
            return anyio.run(run_mock)

        with patch("asyncio.run", side_effect=mock_asyncio_run):
            yield isolated_cli_runner


def test_index_command_exists(isolated_cli_runner):
    """Verify index command is registered."""
    result = isolated_cli_runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "Index the repository" in result.stdout


def test_index_default_output(mock_git_repo):
    """Verify default mode is terse (minimal output)."""
    result = mock_git_repo.invoke(app, ["index"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    # Default should be terse: summary line + cost line
    assert len(lines) == 2
    assert "Indexed" in result.stdout
    assert "commits" in result.stdout
    assert "unique blobs" in result.stdout
    assert "Tokens:" in result.stdout
    assert "Cost:" in result.stdout


def test_index_verbose_flag(mock_git_repo):
    """Verify --verbose flag shows detailed output."""
    result = mock_git_repo.invoke(app, ["index", "--verbose"])
    assert result.exit_code == 0
    # Verbose output goes to stderr
    output = result.stdout + result.stderr
    assert "Walking commit graph" in output or "→" in output
    assert "Statistics:" in output
    lines = [line for line in output.split("\n") if line.strip()]
    assert len(lines) > 5  # Multiple lines in verbose mode


def test_index_short_flags(mock_git_repo):
    """Verify -v short flag works."""
    result = mock_git_repo.invoke(app, ["index", "-v"])
    assert result.exit_code == 0
    # Verbose output goes to stderr
    output = result.stdout + result.stderr
    assert "→" in output or "Walking commit graph" in output


def test_index_help_text(isolated_cli_runner):
    """Verify help text includes all options."""
    result = isolated_cli_runner.invoke(app, ["index", "--help"])
    assert "--verbose" in result.stdout
    assert "-v" in result.stdout
    assert "--quiet" in result.stdout
    assert "-q" in result.stdout
    assert "--dry-run" in result.stdout


def test_index_not_git_repository(cli_runner):
    """Verify index fails with proper error when run outside a git repository.

    The cli_runner fixture (from tests/unit/conftest.py) automatically sets
    the current directory to an isolated temporary path that is NOT a git
    repository, ensuring this test verifies the "not a git repo" error path.
    """
    # cli_runner is already in a non-git temp directory (via isolated_cwd fixture)
    result = cli_runner.invoke(app, ["index"])
    assert result.exit_code == 3  # Exit code 3 = not a git repository
    # Error message goes to stderr (via console_err)
    output = (result.stdout + result.stderr).lower()
    assert "not a git repository" in output
