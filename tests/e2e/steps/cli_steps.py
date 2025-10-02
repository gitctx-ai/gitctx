"""Step definitions for CLI tests."""

import subprocess
import sys

import pytest
from pytest_bdd import given, parsers, then, when


# Store results in pytest context
@pytest.fixture
def context() -> dict[str, str | int]:
    """Store test context between steps."""
    return {}


@given("gitctx is installed")
def gitctx_installed() -> None:
    """Verify gitctx can be imported."""
    import gitctx

    assert gitctx.__version__


@when(parsers.parse('I run "{command}"'))
def run_command(
    command: str, e2e_git_isolation_env: dict[str, str], context: dict[str, str | int]
) -> None:
    """
    Execute a CLI command as subprocess with full isolation.

    CRITICAL: Uses subprocess.run() with isolated environment to ensure
    true isolation from developer SSH keys, GPG keys, and git config.

    This is NOT the same as CliRunner.invoke() which runs in-process.
    """
    # Remove "gitctx" from command and prepare args
    args = command.replace("gitctx", "").strip().split() if command.strip() != "gitctx" else []

    # Run gitctx as subprocess with full isolation
    # Use python -m gitctx to ensure we're using the installed package
    result = subprocess.run(
        [sys.executable, "-m", "gitctx"] + args,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )

    context["result"] = result
    context["output"] = result.stdout
    context["exit_code"] = result.returncode


@then(parsers.parse('the output should contain "{text}"'))
def check_output_contains(text: str, context: dict[str, str | int]) -> None:
    """Verify text appears in output."""
    output = context["output"]
    assert isinstance(output, str)
    assert text in output, f"Expected '{text}' in output, got: {output}"


@then("the exit code should be 0")
def check_exit_code_zero(context: dict[str, str | int]) -> None:
    """Verify command succeeded."""
    exit_code = context["exit_code"]
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


@then(parsers.parse("the exit code should be {code:d}"))
def check_exit_code(code: int, context: dict[str, str | int]) -> None:
    """Verify specific exit code."""
    assert context["exit_code"] == code
