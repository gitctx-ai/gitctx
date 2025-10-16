"""Main CLI application."""
# ruff: noqa: PLC0415, PLR0913 # Inline imports for fast --version; CLI commands need many options

from typing import Annotated

import typer
from rich.console import Console

from gitctx import __version__

console = Console()

app = typer.Typer(
    name="gitctx",
    help="Context optimization engine for coding workflows",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"gitctx version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(  # noqa: ARG001
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version",
    ),
) -> None:
    """gitctx - Context optimization engine for coding workflows."""
    # If no command is provided, show quick start guide
    if ctx.invoked_subcommand is None:
        console.print("[bold]gitctx[/bold] - Context optimization engine")
        console.print()
        console.print("Use [cyan]gitctx --help[/cyan] to see available commands")
        console.print()
        console.print("[bold]Quick start:[/bold]")
        console.print("  1. [cyan]gitctx config set api_keys.openai <your-key>[/cyan]")
        console.print("  2. [cyan]gitctx index[/cyan]")
        console.print('  3. [cyan]gitctx search "your query"[/cyan]')


# Lazy command registration - imports happen only when commands are invoked
# This keeps --version and --help fast by avoiding heavy dependency imports


@app.command(name="index")
def index_command_wrapper(
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
    """Index the repository for searching."""
    from gitctx.cli.index import index_command

    index_command(
        verbose=verbose,
        quiet=quiet,
        skip_confirmation=skip_confirmation,
        _force=_force,
        dry_run=dry_run,
    )


@app.command(name="search", help="Search indexed code using semantic similarity")
def search_command_wrapper(
    query: Annotated[
        list[str] | None,
        typer.Argument(help="The search query to find relevant code and documentation"),
    ] = None,
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results to return (1-100)",
        min=1,
        max=100,
    ),
    min_similarity: float = typer.Option(
        0.5,
        "--min-similarity",
        "-s",
        help=(
            "Minimum similarity score (-1.0 to 1.0) for context engineering quality. "
            "Default: 0.5 (balanced). Use 0.7 for high precision, "
            "-1.0 to see all results (including opposite meaning)."
        ),
        min=-1.0,
        max=1.0,
        rich_help_panel="Result Filtering",
    ),
    output_format: str | None = typer.Option(
        None,
        "--format",
        help="Output format (terse, verbose, mcp)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show code context for each result",
    ),
    mcp: bool = typer.Option(
        False,
        "--mcp",
        help="Output structured markdown for AI consumption",
    ),
    theme: str | None = typer.Option(
        None,
        "--theme",
        help=(
            "Syntax highlighting theme (monokai, github-dark, solarized-light, etc.). "
            "Overrides user config."
        ),
        rich_help_panel="Output Formatting",
    ),
) -> None:
    """Search the indexed repository for relevant code."""
    from gitctx.cli.search import search_command

    search_command(
        query=query,
        limit=limit,
        min_similarity=min_similarity,
        output_format=output_format,
        verbose=verbose,
        mcp=mcp,
        theme=theme,
    )


def _register_config_commands() -> None:
    """Lazily register config subcommands."""
    from gitctx.cli.config import config_app

    app.add_typer(config_app, name="config")


# Register config command group (lightweight, no heavy imports)
_register_config_commands()


@app.command(name="clear")
def clear_command_wrapper(
    database: bool = typer.Option(
        False,
        "--database",
        "-d",
        help="Clear the vector database (preserves embeddings for fast rebuild)",
    ),
    embeddings: bool = typer.Option(
        False,
        "--embeddings",
        "-e",
        help="Clear cached embeddings (also clears database, requires API calls to rebuild)",
    ),
    all_data: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Clear all cached data (same as --embeddings)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Clear cached data and indexes."""
    from gitctx.cli.clear import clear_command

    clear_command(database=database, embeddings=embeddings, all_data=all_data, force=force)
