"""First-run tips system for gitctx CLI.

Provides helpful tips to users on their first run of each command,
then automatically hides them on subsequent runs.

See TUI_GUIDE.md for tip formatting specifications.
"""

import os
from pathlib import Path

from rich.box import ASCII, ROUNDED
from rich.console import Console
from rich.panel import Panel

from gitctx.cli.symbols import SYMBOLS


def _get_user_home() -> Path:
    """Get user home directory, respecting HOME env var.

    On Unix, Path.home() respects HOME environment variable.
    On Windows, Path.home() ignores HOME and uses USERPROFILE.
    This helper ensures HOME is used when set (critical for testing).

    Returns:
        Path: User home directory
    """
    return Path(os.environ.get("HOME", str(Path.home())))


# Create console for platform detection
_console = Console()

# Tips dictionary - add new tips here as needed
TIPS = {
    "config": (
        "API keys are stored securely in ~/.gitctx/config.yml with file permissions 0600. "
        "Team settings in .gitctx/config.yml are safe to commit."
    ),
    # Future tips for other commands:
    # "index": "Embeddings are stored in .gitctx/db/ and should be committed.",
    # "search": "Use --limit to control result count. Results are ranked by semantic similarity.",
}


def is_first_run(command: str) -> bool:
    """Detect if this is user's first time running a command.

    Creates a marker file at ~/.gitctx/.{command}_run to track first runs.
    Returns True only on the very first invocation of the command.

    Args:
        command: The command name (e.g., "config", "index", "search")

    Returns:
        True if this is the first run, False otherwise

    Example:
        >>> if is_first_run("config"):
        ...     show_tip("config")
    """
    marker_file = _get_user_home() / ".gitctx" / f".{command}_run"
    if not marker_file.exists():
        marker_file.parent.mkdir(parents=True, exist_ok=True)
        marker_file.touch()
        return True
    return False


def show_tip(command: str) -> None:
    """Display a tip box for the specified command.

    Uses platform-appropriate box style (ASCII for Windows cmd.exe,
    Unicode for modern terminals).

    Args:
        command: The command name to show a tip for

    Example:
        >>> show_tip("config")
        💡 Tip
        ╭────────────────────────────────────────╮
        │ API keys are stored securely in ...    │
        ╰────────────────────────────────────────╯
    """
    tip = TIPS.get(command)
    if not tip:
        return

    # Use ASCII box for legacy Windows cmd.exe, Unicode for modern terminals
    box_style = ASCII if _console.legacy_windows else ROUNDED
    tip_icon = SYMBOLS["tip"]

    panel = Panel(
        tip,
        title=f"{tip_icon} Tip",
        title_align="left",
        box=box_style,
        border_style="blue",
        expand=False,
    )

    _console.print()
    _console.print(panel)
    _console.print()
