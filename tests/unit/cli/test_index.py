"""Unit tests for index command."""

import subprocess

import pytest

from gitctx.cli.main import app


@pytest.fixture
def mock_git_repo(isolated_cli_runner, tmp_path, monkeypatch):
    """Create a minimal git repository for testing index command.

    This creates an isolated git repo in tmp_path so tests don't pollute
    the actual gitctx repository or user's config.
    """
    # Create repo directory
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)

    # Add a file and commit
    (repo / "test.py").write_text('print("hello")')
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    return isolated_cli_runner


def test_index_command_exists(isolated_cli_runner):
    """Verify index command is registered."""
    result = isolated_cli_runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "Index the repository" in result.stdout


def test_index_default_output(mock_git_repo):
    """Verify default mode is terse (single line)."""
    result = mock_git_repo.invoke(app, ["index"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    # Default should be 1 line: "Indexed N commits (M unique blobs) in Xs"
    assert len(lines) == 1
    assert "Indexed" in result.stdout
    assert "commits" in result.stdout
    assert "unique blobs" in result.stdout


def test_index_verbose_flag(mock_git_repo):
    """Verify --verbose flag shows detailed output."""
    result = mock_git_repo.invoke(app, ["index", "--verbose"])
    assert result.exit_code == 0
    # Verbose should have multiple sections
    assert "Walking commit graph" in result.stdout or "→" in result.stdout
    assert "Found" in result.stdout
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    assert len(lines) > 5  # Multiple lines in verbose mode


def test_index_quiet_flag(mock_git_repo):
    """Verify --quiet flag suppresses output."""
    result = mock_git_repo.invoke(app, ["index", "--quiet"])
    assert result.exit_code == 0
    # Quiet mode should have NO output on success
    assert result.stdout.strip() == ""


def test_index_force_flag(mock_git_repo):
    """Verify --force flag is accepted."""
    result = mock_git_repo.invoke(app, ["index", "--force"])
    assert result.exit_code == 0
    assert "Cleared existing index" in result.stdout or "force" in result.stdout.lower()


def test_index_short_flags(mock_git_repo):
    """Verify -v, -q, -f short flags work."""
    result = mock_git_repo.invoke(app, ["index", "-v", "-f"])
    assert result.exit_code == 0

    result = mock_git_repo.invoke(app, ["index", "-q"])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_index_help_text(isolated_cli_runner):
    """Verify help text includes all options."""
    result = isolated_cli_runner.invoke(app, ["index", "--help"])
    assert "--verbose" in result.stdout
    assert "-v" in result.stdout
    assert "--quiet" in result.stdout
    assert "-q" in result.stdout
    assert "--force" in result.stdout
    assert "-f" in result.stdout


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
