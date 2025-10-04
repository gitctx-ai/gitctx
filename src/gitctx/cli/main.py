"""Main CLI application."""

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


# Register commands
from gitctx.cli import clear, config, index, search  # noqa: E402

index.register(app)
search.register(app)
config.register(app)
clear.register(app)
