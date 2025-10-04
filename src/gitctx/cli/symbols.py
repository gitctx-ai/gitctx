"""Platform-aware symbol rendering for CLI output.

Provides automatic fallback to ASCII symbols for legacy Windows cmd.exe
while using Unicode symbols for modern terminals (Windows Terminal, macOS, Linux).

See TUI_GUIDE.md for symbol specifications.
"""

from rich.console import Console

# Create console for platform detection
_console = Console()

# Symbol selection based on terminal capability
# Rich's legacy_windows auto-detects Windows cmd.exe vs modern terminals
if _console.legacy_windows:
    # Legacy Windows cmd.exe fallback
    SYMBOLS = {
        "success": "[OK]",
        "error": "[X]",
        "warning": "[!]",
        "tip": "[i]",
        "arrow": "->",
        "head": "[HEAD]",
    }
else:
    # Modern terminals (Windows Terminal, macOS, Linux)
    SYMBOLS = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "tip": "💡",
        "arrow": "→",
        "head": "●",
    }
