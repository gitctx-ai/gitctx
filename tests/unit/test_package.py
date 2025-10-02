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
    )
    assert result.returncode == 0
    assert "gitctx" in result.stdout.lower()


def test_cli_module_exists() -> None:
    """Test that CLI module can be imported."""
    from gitctx.cli import main

    assert main is not None
