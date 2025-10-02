"""Test package structure and basic functionality."""

import subprocess
import sys


def test_package_has_version() -> None:
    """Test that package exports version."""
    import gitctx

    assert hasattr(gitctx, "__version__")
    assert isinstance(gitctx.__version__, str)
    assert gitctx.__version__  # Not empty


def test_main_entry_point_exists() -> None:
    """Test that __main__ can be executed."""
    result = subprocess.run(
        [sys.executable, "-m", "gitctx", "--version"],
        capture_output=True,
        text=True,
        timeout=3,
    )
    assert result.returncode == 0
    assert "gitctx" in result.stdout.lower()


def test_cli_module_exists() -> None:
    """Test that CLI module can be imported."""
    from gitctx.cli import main

    assert main is not None


def test_cli_without_arguments() -> None:
    """Test that gitctx shows help when run with no arguments."""
    result = subprocess.run(
        [sys.executable, "-m", "gitctx"],
        capture_output=True,
        text=True,
        timeout=3,
    )
    # Typer returns exit code 2 when no command is provided
    assert result.returncode == 2
    assert "Missing command" in result.stderr
    assert "Usage:" in result.stderr


def test_version_callback_false_branch() -> None:
    """Test version_callback when not requesting version."""
    from gitctx.cli.main import version_callback

    # Should return None without any output or exception
    result = version_callback(False)
    assert result is None

    result = version_callback(None)
    assert result is None


def test_main_callback_directly() -> None:
    """Test the main callback function executes properly."""
    from gitctx.cli.main import main

    # Call with version=None (default case)
    # This should complete without error
    main(version=None)
