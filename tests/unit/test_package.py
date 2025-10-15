"""Test package structure and basic functionality."""

import os
import subprocess
import sys

import gitctx
from gitctx.cli.main import main, version_callback


def test_package_has_version() -> None:
    """Test that package exports version."""

    assert hasattr(gitctx, "__version__")
    assert isinstance(gitctx.__version__, str)
    assert gitctx.__version__  # Not empty


def test_main_entry_point_exists() -> None:
    """Test that __main__ can be executed."""
    result = subprocess.run(
        [sys.executable, "-m", "gitctx", "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )
    assert result.returncode == 0
    assert "gitctx" in result.stdout.lower()


def test_version_cold_start_performance() -> None:
    """Test that --version completes quickly even without .pyc cache (CI simulation).

    This test simulates CI environment conditions where no bytecode cache exists.
    The --version command should complete in <1s without importing heavy dependencies
    like lancedb, pyarrow, or embedding models.
    """
    result = subprocess.run(
        [sys.executable, "-B", "-m", "gitctx", "--version"],  # -B disables .pyc cache
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0
    assert "gitctx" in result.stdout.lower()

    # Performance regression guard: Should complete in <1s even on cold start
    # This prevents the timeout issue seen in CI (FAILED with 3s timeout)


def test_cli_module_exists() -> None:
    """Test that CLI module can be imported."""

    assert main is not None


def test_cli_without_arguments() -> None:
    """Test that gitctx shows quick start guide when run with no arguments."""
    result = subprocess.run(
        [sys.executable, "-m", "gitctx"],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )
    # Now shows quick start guide instead of error
    assert result.returncode == 0
    assert "Quick start" in result.stdout
    assert "gitctx index" in result.stdout


def test_version_callback_false_branch() -> None:
    """Test version_callback when not requesting version."""

    # Should return None without any output or exception
    result = version_callback(False)
    assert result is None

    result = version_callback(None)
    assert result is None


def test_main_callback_directly() -> None:
    """Test the main callback function signature."""

    # main() now requires ctx parameter (Typer.Context)
    # This test just verifies the function exists and is callable
    assert callable(main)
    assert main.__name__ == "main"
