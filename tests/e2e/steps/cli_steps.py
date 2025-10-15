"""Step definitions for CLI tests."""

import os
import shlex
import sys
from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, then, when


@given("gitctx is installed")
def gitctx_installed() -> None:
    """Verify gitctx can be imported."""
    import gitctx

    assert gitctx.__version__


@given(parsers.parse('I run "{command}"'))
@when(parsers.parse('I run "{command}"'))
def run_command(
    command: str,
    e2e_cli_runner,
    e2e_env_factory,
    context: dict[str, Any],
    monkeypatch,
) -> None:
    """
    Execute a CLI command using CliRunner with full isolation.

    CRITICAL: Uses CliRunner.invoke() which runs in-process, enabling
    VCR to intercept HTTP calls for cassette recording/replay.

    Enhancement: Checks context["custom_env"] for custom environment variables
    set by previous @given steps (e.g., OPENAI_API_KEY, GITCTX_*).
    """
    from gitctx.cli.main import app

    # Parse the command to extract args using shlex to handle quotes properly
    if command.startswith("gitctx"):
        # Use shlex.split to properly handle quoted arguments
        all_args = shlex.split(command)
        # Remove 'gitctx' from the beginning
        args = all_args[1:] if len(all_args) > 1 else []
    else:
        # For non-gitctx commands, use shlex.split
        args = shlex.split(command)

    # Change to repo directory if provided
    cwd = context.get("repo_path")
    if cwd:
        assert cwd.exists(), f"Repo path {cwd} doesn't exist"
        monkeypatch.chdir(cwd)

    # Run CLI in-process with CliRunner
    # Environment automatically merged from context["custom_env"] by fixture
    result = e2e_cli_runner.invoke(app, args)

    # Clear custom_env after use to prevent leakage to next command
    context.pop("custom_env", None)

    context["result"] = result
    context["stdout"] = result.stdout  # ANSI codes stripped
    context["raw_stdout"] = result.raw_stdout  # Original with ANSI codes
    # Typer's CliRunner mixes stderr into stdout by default
    context["stderr"] = result.stderr if hasattr(result, "stderr") and result.stderr else ""
    context["exit_code"] = result.exit_code


@then(parsers.parse('the output should contain "{text}"'))
def check_output_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text appears in output."""
    output = context["stdout"]
    assert isinstance(output, str)
    assert text in output, f"Expected '{text}' in output, got: {output}"


@then(parsers.parse('the output should not contain "{text}"'))
def check_output_not_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text does NOT appear in output."""
    output = context["stdout"]
    assert isinstance(output, str)
    assert text not in output, f"Did not expect '{text}' in output, got: {output}"


@then("the exit code should be 0")
def check_exit_code_zero(context: dict[str, Any]) -> None:
    """Verify command succeeded."""
    exit_code = context["exit_code"]
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


@then(parsers.parse("the exit code should be {code:d}"))
def check_exit_code(code: int, context: dict[str, Any]) -> None:
    """Verify specific exit code."""
    assert context["exit_code"] == code


@then("the exit code should not be 0")
def check_exit_code_not_zero(context: dict[str, Any]) -> None:
    """Verify command failed (non-zero exit code)."""
    exit_code = context["exit_code"]
    assert exit_code != 0, f"Expected non-zero exit code, got {exit_code}"


# TASK-0001.1.2.1: Step definitions for config file management


@given(parsers.parse('user config contains "{content}"'))
def setup_user_config(e2e_git_isolation_env: dict[str, str], content: str) -> None:
    """Create user config file with specified YAML content in isolated HOME.

    CRITICAL: e2e_git_isolation_env["HOME"] already has .gitctx/ directory!
    DO NOT call mkdir() - it's redundant and already exists.
    """

    home = Path(e2e_git_isolation_env["HOME"])
    config_path = home / ".gitctx" / "config.yml"
    # .gitctx/ already exists - just write the file
    config_path.write_text(content.replace("\\n", "\n"))


@given(parsers.parse("user config exists with permissions {perms}"))
def setup_user_config_with_permissions(e2e_git_isolation_env: dict[str, str], perms: str) -> None:
    """Create user config file with specified permissions.

    CRITICAL: e2e_git_isolation_env["HOME"] already has .gitctx/ directory!
    """

    if sys.platform == "win32":
        import pytest

        pytest.skip("Permission tests not applicable on Windows")

    home = Path(e2e_git_isolation_env["HOME"])
    config_path = home / ".gitctx" / "config.yml"
    # Write a sample config
    config_path.write_text("api_keys:\n  openai: sk-test123\n")
    # Set specified permissions (convert octal string to int)
    config_path.chmod(int(perms, 8))


@given(parsers.parse('repo config contains "{content}"'))
def setup_repo_config(content: str) -> None:
    """Create repo config file with specified YAML content in temp directory.

    CRITICAL: isolate_working_directory autouse fixture ensures we're in tmp_path!
    """

    config_path = Path(".gitctx")
    config_path.mkdir(exist_ok=True)
    (config_path / "config.yml").write_text(content.replace("\\n", "\n"))


@given(parsers.re(r'environment variable "(?P<var>[^"]+)" is "(?P<value>.*)"'))
def setup_env_var(var: str, value: str, context: dict[str, Any], e2e_session_api_key: str) -> None:
    """Set environment variable for next command execution.

    CRITICAL: Stores in context["custom_env"] for run_command to use.
    The run_command step will apply these via monkeypatch before invoking CLI.

    Special handling: If value is "$ENV", pulls from e2e_session_api_key fixture
    (captured before e2e_cli_runner clears environment)

    Uses regex parser to handle empty strings correctly (parsers.parse doesn't work with "").
    """

    if "custom_env" not in context:
        context["custom_env"] = {}

    # Allow pulling from session-captured environment with $ENV token
    if value == "$ENV":
        # Use session-scoped API key captured before e2e_cli_runner cleared environment
        if var == "OPENAI_API_KEY":
            context["custom_env"][var] = e2e_session_api_key
        else:
            # For non-API-key env vars, try os.environ (though it may be cleared)
            actual_value = os.environ.get(var)
            if actual_value is None:
                # Fallback for VCR replay when env var not available
                context["custom_env"][var] = "vcr-test-key"
            else:
                context["custom_env"][var] = actual_value
    else:
        context["custom_env"][var] = value


@given(parsers.parse("repo config file exists with read-only permissions"))
def setup_readonly_repo_config() -> None:
    """Create read-only repo config file for testing permission errors.

    CRITICAL: isolate_working_directory autouse fixture ensures we're in tmp_path!
    """
    import platform
    import stat

    config_path = Path(".gitctx")
    config_path.mkdir(exist_ok=True)
    config_file = config_path / "config.yml"
    config_file.write_text("search:\n  limit: 10\n")

    if platform.system() == "Windows":
        # Windows: Use stat.S_IREAD for read-only (removes write permissions)
        config_file.chmod(stat.S_IREAD)
    else:
        # Unix: Use 0o444 for read-only
        config_file.chmod(0o444)


@given(parsers.parse('repo config contains invalid YAML "{content}"'))
def setup_invalid_yaml_repo_config(content: str) -> None:
    """Create repo config with invalid YAML for error testing.

    CRITICAL: isolate_working_directory autouse fixture ensures we're in tmp_path!
    """

    config_path = Path(".gitctx")
    config_path.mkdir(exist_ok=True)
    (config_path / "config.yml").write_text(content.replace("\\n", "\n"))


@then(parsers.parse('the file "{path}" should exist'))
def check_file_exists(e2e_git_isolation_env: dict[str, str], path: str) -> None:
    """Verify file exists at specified path.

    Handles both absolute paths and ~ expansion (to isolated HOME).
    """

    if path.startswith("~"):
        home = Path(e2e_git_isolation_env["HOME"])
        expanded = home / path[2:]  # Skip "~/"
    else:
        expanded = Path(path)

    assert expanded.exists(), f"File not found at {expanded}"


@then(parsers.parse('the file "{path}" should contain "{content}"'))
def check_file_contains(e2e_git_isolation_env: dict[str, str], path: str, content: str) -> None:
    """Verify file contains specified content."""

    if path.startswith("~"):
        home = Path(e2e_git_isolation_env["HOME"])
        expanded = home / path[2:]
    else:
        expanded = Path(path)

    assert expanded.exists(), f"File not found at {expanded}"
    file_content = expanded.read_text()
    assert content in file_content, f"Expected '{content}' in {path}, got: {file_content}"


@then(parsers.parse('the file "{path}" should not contain "{content}"'))
def check_file_not_contains(e2e_git_isolation_env: dict[str, str], path: str, content: str) -> None:
    """Verify file does NOT contain specified content."""

    if path.startswith("~"):
        home = Path(e2e_git_isolation_env["HOME"])
        expanded = home / path[2:]
    else:
        expanded = Path(path)

    if not expanded.exists():
        return  # File doesn't exist, so it doesn't contain the content

    file_content = expanded.read_text()
    assert content not in file_content, f"Did not expect '{content}' in {path}, got: {file_content}"


@then(parsers.parse('the user config file should exist at "{path}"'))
def check_user_config_exists(e2e_git_isolation_env: dict[str, str], path: str) -> None:
    """Verify user config file exists (alias for better readability in scenarios)."""
    check_file_exists(e2e_git_isolation_env, path)


@then(parsers.parse('"{filename}" should contain "{content}"'))
def check_gitignore_content(filename: str, content: str) -> None:
    """Verify .gitctx/.gitignore contains expected content."""

    file_path = Path(".gitctx") / filename.replace(".gitctx/", "")
    assert file_path.exists(), f"File not found: {file_path}"
    file_content = file_path.read_text()
    assert content in file_content, f"Expected '{content}' in {file_path}"


@then("the output should be empty")
def check_output_empty(context: dict[str, Any]) -> None:
    """Verify output is completely empty."""
    output = context["stdout"]
    assert isinstance(output, str)
    assert output.strip() == "", f"Expected empty output, got: {output}"


@then(parsers.parse('the error should contain "{text}"'))
def check_stderr_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text appears in stderr."""
    stderr = context["stderr"]
    assert isinstance(stderr, str)
    assert text in stderr, f"Expected '{text}' in stderr, got: {stderr}"


@then(parsers.parse('the error should not contain "{text}"'))
def check_stderr_not_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text does NOT appear in stderr."""
    stderr = context["stderr"]
    assert isinstance(stderr, str)
    assert text not in stderr, f"Expected '{text}' NOT in stderr, but it was found: {stderr}"
