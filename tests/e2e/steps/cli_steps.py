"""Step definitions for CLI tests."""

import subprocess
import sys
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when


# Store results in pytest context
@pytest.fixture
def context() -> dict[str, Any]:
    """Store test context between steps."""
    return {}


@given("gitctx is installed")
def gitctx_installed() -> None:
    """Verify gitctx can be imported."""
    import gitctx

    assert gitctx.__version__


@when(parsers.parse('I run "{command}"'))
def run_command(
    command: str, e2e_git_isolation_env: dict[str, str], context: dict[str, Any]
) -> None:
    """
    Execute a CLI command as subprocess with full isolation.

    CRITICAL: Uses subprocess.run() with isolated environment to ensure
    true isolation from developer SSH keys, GPG keys, and git config.

    This is NOT the same as CliRunner.invoke() which runs in-process.
    """
    # Parse the command and convert gitctx to python -m gitctx
    # This ensures the command works in all environments (local, CI, etc.)
    if command.startswith("gitctx"):
        # Replace 'gitctx' with 'python -m gitctx' for reliable execution
        args = command.replace("gitctx", "").strip().split() if command.strip() != "gitctx" else []
        cmd_parts = [sys.executable, "-m", "gitctx"] + args
    else:
        cmd_parts = command.strip().split()

    # Run gitctx as subprocess with full isolation
    # Uses python -m gitctx to ensure it works in all environments
    result = subprocess.run(
        cmd_parts,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )

    context["result"] = result
    context["output"] = result.stdout
    context["exit_code"] = result.returncode


@then(parsers.parse('the output should contain "{text}"'))
def check_output_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text appears in output."""
    output = context["output"]
    assert isinstance(output, str)
    assert text in output, f"Expected '{text}' in output, got: {output}"


@then(parsers.parse('the output should not contain "{text}"'))
def check_output_not_contains(text: str, context: dict[str, Any]) -> None:
    """Verify text does NOT appear in output."""
    output = context["output"]
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
