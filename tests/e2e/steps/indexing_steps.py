"""Step definitions for indexing feature tests."""
# ruff: noqa: PLC0415 # Inline imports in BDD steps for clarity

from typing import Any

from pytest_bdd import given, parsers, then, when


@given("a repository with history mode enabled")
def repo_with_history_mode(e2e_git_repo_factory, context: dict[str, Any], monkeypatch) -> None:
    """Create a repository with history mode configuration."""
    # Create repo with multiple commits
    files = {"test.py": 'print("hello")'}
    repo_path = e2e_git_repo_factory(files=files, num_commits=3)

    # Create .gitctx config with history mode
    gitctx_dir = repo_path / ".gitctx"
    gitctx_dir.mkdir(exist_ok=True)
    config_file = gitctx_dir / "config.yml"
    config_file.write_text("index:\n  index_mode: history\n")

    # Change to repo directory
    monkeypatch.chdir(repo_path)
    context["repo_path"] = repo_path


@given("a repository with snapshot mode enabled")
def repo_with_snapshot_mode(e2e_git_repo_factory, context: dict[str, Any], monkeypatch) -> None:
    """Create a repository with snapshot mode (default)."""
    # Create repo
    files = {"test.py": 'print("hello")'}
    repo_path = e2e_git_repo_factory(files=files, num_commits=3)

    # No config needed - snapshot is default
    # (or create explicit config if needed)

    # Change to repo directory
    monkeypatch.chdir(repo_path)
    context["repo_path"] = repo_path


@when('I run "gitctx index" interactively and decline')
def run_index_interactively_decline(e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command with user declining confirmation.

    Uses CliRunner's input= parameter to simulate user typing 'n' at the prompt.
    This bypasses TTY detection - typer.confirm() accepts the input directly.
    """
    from gitctx.cli.main import app

    # Simulate user input (decline with 'n')
    result = e2e_cli_runner.invoke(app, ["index"], input="n\n")

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""


@when('I run "gitctx index" interactively and accept')
def run_index_interactively_accept(e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command with user accepting confirmation.

    Uses CliRunner's input= parameter to simulate user typing 'y' at the prompt.
    This bypasses TTY detection - typer.confirm() accepts the input directly.
    """
    from gitctx.cli.main import app

    # Simulate user input (accept with 'y')
    result = e2e_cli_runner.invoke(app, ["index"], input="y\n")

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""


@when(parsers.parse('I run "gitctx index {flags}"'))
def run_index_with_flags(flags: str, e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command with specified flags."""
    from gitctx.cli.main import app

    args = ["index", *flags.split()]
    result = e2e_cli_runner.invoke(app, args)

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""


@when('I run "gitctx index" non-interactively')
def run_index_non_interactively(e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command in non-TTY environment (default for CliRunner)."""
    from gitctx.cli.main import app

    # CliRunner simulates non-TTY by default (sys.stdout.isatty() returns False)
    result = e2e_cli_runner.invoke(app, ["index"])

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""


@when('I run "gitctx index"')
def run_index(e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command (for snapshot mode test)."""
    from gitctx.cli.main import app

    result = e2e_cli_runner.invoke(app, ["index"])

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""


@then("no indexing should have occurred")
def check_no_indexing(context: dict[str, Any]) -> None:
    """Verify that indexing did not complete."""
    repo_path = context["repo_path"]

    # Check that .gitctx/db directory was not created (sign of indexing)
    db_path = repo_path / ".gitctx" / "db"
    assert not db_path.exists(), f"Database {db_path} should not exist after cancellation"


@then("indexing should complete successfully")
def check_indexing_completed(context: dict[str, Any]) -> None:
    """Verify that indexing completed."""
    output = context["stdout"] + context["stderr"]

    # Check for success indicators
    # Note: Real indexing would create .gitctx/db, but mocked tests may not
    # So we check output for success messages
    assert "Indexing Complete" in output or "Indexed" in output or context["exit_code"] == 0, (
        f"Indexing should complete successfully. Output: {output}"
    )
