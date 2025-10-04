"""Unit tests for index command."""

from typer.testing import CliRunner

from gitctx.cli.main import app

runner = CliRunner()


def test_index_command_exists():
    """Verify index command is registered."""
    result = runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "Index the repository" in result.stdout


def test_index_default_output():
    """Verify default mode is terse (single line)."""
    result = runner.invoke(app, ["index"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    # Default should be 1 line: "Indexed N commits (M unique blobs) in Xs"
    assert len(lines) == 1
    assert "Indexed" in result.stdout
    assert "commits" in result.stdout
    assert "unique blobs" in result.stdout


def test_index_verbose_flag():
    """Verify --verbose flag shows detailed output."""
    result = runner.invoke(app, ["index", "--verbose"])
    assert result.exit_code == 0
    # Verbose should have multiple sections
    assert "Walking commit graph" in result.stdout or "→" in result.stdout
    assert "Found" in result.stdout
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    assert len(lines) > 5  # Multiple lines in verbose mode


def test_index_quiet_flag():
    """Verify --quiet flag suppresses output."""
    result = runner.invoke(app, ["index", "--quiet"])
    assert result.exit_code == 0
    # Quiet mode should have NO output on success
    assert result.stdout.strip() == ""


def test_index_force_flag():
    """Verify --force flag is accepted."""
    result = runner.invoke(app, ["index", "--force"])
    assert result.exit_code == 0
    assert "Cleared existing index" in result.stdout or "force" in result.stdout.lower()


def test_index_short_flags():
    """Verify -v, -q, -f short flags work."""
    result = runner.invoke(app, ["index", "-v", "-f"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["index", "-q"])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_index_help_text():
    """Verify help text includes all options."""
    result = runner.invoke(app, ["index", "--help"])
    assert "--verbose" in result.stdout
    assert "-v" in result.stdout
    assert "--quiet" in result.stdout
    assert "-q" in result.stdout
    assert "--force" in result.stdout
    assert "-f" in result.stdout


def test_index_not_git_repository(tmp_path, monkeypatch):
    """Verify index fails with proper error in non-git directory."""
    # Change to non-git directory
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["index"])
    assert result.exit_code == 3  # Exit code 3 = not a git repository
    # Error message goes to stderr (via console_err)
    output = (result.stdout + result.stderr).lower()
    assert "not a git repository" in output
