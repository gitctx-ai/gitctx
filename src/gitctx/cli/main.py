"""Main CLI application."""

import typer

from gitctx import __version__

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


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version",
    ),
) -> None:
    """gitctx - Context optimization engine for coding workflows."""
    pass


# Register commands
from gitctx.cli import clear, config, index, search  # noqa: E402

index.register(app)
search.register(app)
config.register(app)
clear.register(app)
