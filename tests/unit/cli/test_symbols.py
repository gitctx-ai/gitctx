"""Unit tests for platform-aware symbol rendering."""

import subprocess
import sys
from pathlib import Path


def _find_project_root(start_path: Path) -> Path:
    """Find project root by locating pyproject.toml.

    Args:
        start_path: Starting path to search from

    Returns:
        Path to project root directory

    Raises:
        RuntimeError: If pyproject.toml not found in any parent directory
    """
    current = start_path.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (pyproject.toml not found)")


def test_symbols_modern_terminals():
    """Verify symbols are correctly set based on terminal type."""
    from gitctx.cli.symbols import SYMBOLS, _console

    # Symbols should match the console's legacy_windows status
    if _console.legacy_windows:
        # Legacy Windows cmd.exe - ASCII fallback
        assert SYMBOLS["success"] == "[OK]"
        assert SYMBOLS["error"] == "[X]"
        assert SYMBOLS["warning"] == "[!]"
        assert SYMBOLS["tip"] == "[i]"
        assert SYMBOLS["arrow"] == "->"
        assert SYMBOLS["head"] == "[HEAD]"
    else:
        # Modern terminals - Unicode symbols
        assert SYMBOLS["success"] == "✓"
        assert SYMBOLS["error"] == "✗"
        assert SYMBOLS["warning"] == "⚠"
        assert SYMBOLS["tip"] == "💡"
        assert SYMBOLS["arrow"] == "→"
        assert SYMBOLS["head"] == "●"


def test_symbols_legacy_windows_simulation():
    """Verify ASCII fallback logic for legacy Windows cmd.exe.

    This test executes the symbols module in a subprocess with mocked legacy_windows=True
    to achieve coverage of the Windows-specific branch.
    """
    # Create a test script that mocks legacy_windows and imports symbols
    test_script = """
import sys
from unittest.mock import Mock, patch

# Mock Console BEFORE any imports
with patch("rich.console.Console") as MockConsole:
    mock_instance = Mock()
    mock_instance.legacy_windows = True
    MockConsole.return_value = mock_instance

    # Now import symbols with the mocked Console
    from gitctx.cli.symbols import SYMBOLS

    # Verify ASCII fallback symbols
    assert SYMBOLS["success"] == "[OK]", f"Got {SYMBOLS['success']}"
    assert SYMBOLS["error"] == "[X]", f"Got {SYMBOLS['error']}"
    assert SYMBOLS["warning"] == "[!]", f"Got {SYMBOLS['warning']}"
    assert SYMBOLS["tip"] == "[i]", f"Got {SYMBOLS['tip']}"
    assert SYMBOLS["arrow"] == "->", f"Got {SYMBOLS['arrow']}"
    assert SYMBOLS["head"] == "[HEAD]", f"Got {SYMBOLS['head']}"

    print("SUCCESS: All ASCII symbols verified")
"""

    # Run the test script in a subprocess to get fresh module imports
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=_find_project_root(Path(__file__)),  # Run from repo root
    )

    # Check that the test passed
    assert result.returncode == 0, (
        f"Script failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "SUCCESS" in result.stdout


def test_symbols_console_detection():
    """Verify symbols module uses Rich Console for platform detection."""
    # Import and check that _console is created
    from gitctx.cli import symbols

    # Verify the module has _console and it's a Console instance
    assert hasattr(symbols, "_console")
    from rich.console import Console

    assert isinstance(symbols._console, Console)

    # legacy_windows should be a boolean (platform-dependent)
    assert isinstance(symbols._console.legacy_windows, bool)


def test_symbols_used_in_cli_commands():
    """Verify symbols module is importable and usable by CLI commands."""
    from gitctx.cli.symbols import SYMBOLS

    # Symbols should be a dict with all required keys
    required_keys = {"success", "error", "warning", "tip", "arrow", "head", "spinner_frames"}
    assert set(SYMBOLS.keys()) == required_keys

    # All values should be non-empty strings
    for _key, value in SYMBOLS.items():
        assert isinstance(value, str)
        assert len(value) > 0
