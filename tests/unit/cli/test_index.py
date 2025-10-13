"""Unit tests for index command."""

import subprocess
import sys
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

    with patch("gitctx.config.settings.GitCtxSettings", return_value=mock_settings):
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
                print("→ Walking commit graph", file=sys.stderr)
                print("→ Generating embeddings", file=sys.stderr)
                print("\n✓ Indexing Complete\n", file=sys.stderr)
                print("Statistics:", file=sys.stderr)
                print("  Commits:      1", file=sys.stderr)
                print("  Unique blobs: 1", file=sys.stderr)
                print("  Chunks:       10", file=sys.stderr)
                print("  Tokens:       50", file=sys.stderr)
                print("  Cost:         $0.0001", file=sys.stderr)
                print("  Time:         0:00:01", file=sys.stderr)
            else:
                # Terse mode - single line
                print("Indexed 1 commits (1 unique blobs) in 0.1s")
                print("Tokens: 50 | Cost: $0.0001")

        # Patch index_repository where it's imported in the CLI
        # The CLI does: from gitctx.indexing.pipeline import index_repository
        # Then calls: asyncio.run(index_repository(...))
        # We patch the module so the import gets our mock
        with patch("gitctx.indexing.pipeline.index_repository", side_effect=mock_index_impl):
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


def test_index_handles_config_error(isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base):
    """Test index command handles configuration errors gracefully."""
    from gitctx.cli.symbols import SYMBOLS

    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Create a minimal git repo so config loading can proceed
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

    # Mock GitCtxSettings to raise an exception
    with patch("gitctx.config.settings.GitCtxSettings", side_effect=ValueError("Invalid config")):
        result = isolated_cli_runner.invoke(app, ["index"])

        # Exit code 1 for config error
        assert result.exit_code == 1
        output = result.stdout + (result.stderr or "")
        assert f"{SYMBOLS['error']}" in output or "error" in output.lower()
        assert "Configuration error" in output or "Invalid config" in output


def test_index_handles_keyboard_interrupt(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Test index command handles Ctrl+C gracefully."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Create git repo
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

    mock_settings = Mock()
    mock_settings.api_keys = Mock()
    mock_settings.api_keys.openai = "sk-test"

    async def mock_index_raises_interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    with (
        patch("gitctx.config.settings.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.indexing.pipeline.index_repository", side_effect=mock_index_raises_interrupt),
    ):
        result = isolated_cli_runner.invoke(app, ["index"])

        # KeyboardInterrupt should be caught and exit with code 130 (standard Unix SIGINT exit code)
        assert result.exit_code == 130


def test_index_handles_generic_exception(
    isolated_cli_runner, tmp_path, monkeypatch, git_isolation_base
):
    """Test index command handles unexpected errors gracefully."""
    from gitctx.cli.symbols import SYMBOLS

    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Create git repo
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

    mock_settings = Mock()
    mock_settings.api_keys = Mock()
    mock_settings.api_keys.openai = "sk-test"

    async def mock_index_raises_error(*args, **kwargs):
        raise RuntimeError("Unexpected error during indexing")

    with (
        patch("gitctx.config.settings.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.indexing.pipeline.index_repository", side_effect=mock_index_raises_error),
    ):
        result = isolated_cli_runner.invoke(app, ["index"])

        assert result.exit_code == 1
        output = result.stdout + (result.stderr or "")
        assert f"{SYMBOLS['error']}" in output or "error" in output.lower()
        assert "Indexing failed" in output or "Unexpected error" in output


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
