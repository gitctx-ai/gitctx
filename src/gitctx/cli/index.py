"""Index command for gitctx CLI."""
# ruff: noqa: PLC0415 # Inline imports for fast --version startup (lazy load indexing pipeline)

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS
from gitctx.config.settings import IndexMode

console = Console()
console_err = Console(stderr=True)


def index_command(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output during indexing",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
    skip_confirmation: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts"),
    _force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reindexing even if cache exists",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show cost estimate without indexing",
    ),
) -> None:
    """
    Index the repository for searching.

    This command analyzes your git repository and creates searchable
    embeddings for all code and documentation files.

    Examples:

        # Basic indexing (terse output)
        $ gitctx index

        # Detailed output
        $ gitctx index --verbose

        # Silent operation
        $ gitctx index --quiet

        # Force reindex
        $ gitctx index --force
    """
    # Validate git repository exists
    if not Path(".git").exists():
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: not a git repository")
        raise typer.Exit(code=3)

    # Load settings
    from gitctx.config.settings import GitCtxSettings

    try:
        settings = GitCtxSettings()
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Configuration error: {e}")
        raise typer.Exit(code=1) from e

    # Check for history mode and show warning
    is_history_mode = settings.repo.index.index_mode == IndexMode.HISTORY
    if not dry_run and is_history_mode and not skip_confirmation:
        # Show warning with cost implications
        console_err.print("\n[yellow]⚠️  History Mode Enabled[/yellow]")
        console_err.print("  Indexing ALL versions across full git history.")
        console_err.print("  Cost/time may be 10-50x higher than snapshot mode.\n")

        # Prompt for confirmation (default: No)
        # Note: In non-interactive environments (CI, scripts), use --yes to skip this prompt
        # typer.confirm() will raise Abort if stdin is not available
        try:
            if not typer.confirm("Continue?", default=False):
                console_err.print("Cancelled")
                raise typer.Exit(0)
        except typer.Abort:
            # Non-interactive environment without --yes flag
            console_err.print(
                f"[red]{SYMBOLS['error']}[/red] Error: history mode requires confirmation"
            )
            console_err.print("Use --yes to skip confirmation in non-interactive environments")
            raise typer.Exit(code=1) from None

    # Run the indexing pipeline
    from gitctx.indexing.pipeline import index_repository

    repo_path = Path.cwd()

    try:
        # Quiet mode suppresses progress output
        use_verbose = verbose and not quiet

        asyncio.run(
            index_repository(
                repo_path=repo_path,
                settings=settings,
                dry_run=dry_run,
                verbose=use_verbose,
            )
        )
    except KeyboardInterrupt as e:
        # SIGINT (Ctrl+C) - exit with standard Unix code 130
        # Pipeline has already shown "Interrupted" message and partial stats
        raise typer.Exit(code=130) from e
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Indexing failed: {e}")
        raise typer.Exit(code=1) from e

    # Note: force flag is reserved for future cache clearing functionality
