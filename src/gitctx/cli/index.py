"""Index command for gitctx CLI."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS

console = Console()
console_err = Console(stderr=True)


def register(app: typer.Typer) -> None:
    """Register the index command with the CLI app."""
    app.command(name="index")(index_command)


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
    _force: bool = typer.Option(  # noqa: ARG001 - Reserved for future use
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
    from gitctx.core.config import GitCtxSettings

    try:
        settings = GitCtxSettings()
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Configuration error: {e}")
        raise typer.Exit(code=1) from e

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
    except KeyboardInterrupt:
        # Handled by pipeline with exit 130
        pass
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Indexing failed: {e}")
        raise typer.Exit(code=1) from e

    # Note: force flag is reserved for future cache clearing functionality
