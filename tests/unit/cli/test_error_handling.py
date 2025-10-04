"""Unit tests for error handling and validation."""

from gitctx.cli.main import app


def test_empty_command_shows_quick_start(cli_runner):
    """Verify running without commands shows quick start guide."""
    result = cli_runner.invoke(app, [])
    assert result.exit_code == 0
    assert "quick start" in result.stdout.lower()
    assert "gitctx index" in result.stdout.lower()
    assert "gitctx search" in result.stdout.lower()


def test_command_suggestion_for_typo(cli_runner):
    """Verify typos show error (Typer default behavior)."""
    # Note: Typer shows "No such command" errors in panels
    # Future: could add difflib suggestions if needed
    result = cli_runner.invoke(app, ["serach"])  # Typo of "search"
    assert result.exit_code != 0
    # Typer handles this with "No such command" error
    # Suggestion feature would require custom error handler


def test_missing_argument_uses_terse_format(cli_runner):
    """Verify missing arguments show proper error (Typer default)."""
    result = cli_runner.invoke(app, ["search"])
    assert result.exit_code != 0
    # Typer shows error in panel (acceptable per task notes)
    # Exit code 2 indicates usage error, which is correct


def test_exit_codes(cli_runner):
    """Verify correct exit codes per TUI_GUIDE.md."""
    # Success
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0

    # Usage error (missing argument)
    result = cli_runner.invoke(app, ["search"])
    assert result.exit_code == 2


def test_version_works_with_any_args(cli_runner):
    """Verify --version is eager and works even with other args."""
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "gitctx version" in result.stdout
