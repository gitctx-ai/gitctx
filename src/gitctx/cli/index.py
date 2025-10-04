"""Index command for gitctx CLI."""

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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reindexing even if cache exists",
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

    # Mock implementation - demonstrates expected output format from TUI_GUIDE.md

    # QUIET MODE: No output on success
    if quiet:
        # Silent - real implementation would index here
        return

    # VERBOSE MODE: Multi-line detailed output (TUI_GUIDE.md lines 207-236)
    if verbose:
        if force:
            console.print("Cleared existing index (47.3 MB)")

        console.print(f"{SYMBOLS['arrow']} Walking commit graph")
        console.print("  Found 5678 commits")
        console.print()
        console.print(f"{SYMBOLS['arrow']} Extracting blobs")
        console.print("  Total blob references: 4567")
        console.print("  Unique blobs: 1234")
        console.print("  Deduplication: 73% savings")
        console.print()
        console.print(f"{SYMBOLS['arrow']} Generating embeddings")
        console.print("  Processing blobs: abc123, def456, ...")
        console.print()
        console.print(f"{SYMBOLS['arrow']} Saving index")
        console.print("  Embeddings: ~/.gitctx/embeddings/blobs/ (45.2 MB)")
        console.print("  Metadata: ~/.gitctx/embeddings/metadata/ (2.1 MB)")
        console.print("  Database: ~/.gitctx/db/ (1.8 MB, 1234 vectors)")
        console.print()
        console.print(
            f"[green]{SYMBOLS['success']}[/green] Indexed 5678 commits (1234 unique blobs) in 8.2s"
        )
        console.print()
        console.print("Statistics:")
        console.print("  Commits:      5678")
        console.print("  Unique blobs: 1234")
        console.print("  Total refs:   4567")
        console.print("  Dedup rate:   73%")
        console.print("  Chunks:       3456")
        console.print("  Vector dims:  1536")
        console.print("  DB records:   1234")
        console.print("  Total size:   47.3 MB")
        return

    # DEFAULT MODE: Terse single-line output (TUI_GUIDE.md line 189)
    if force:
        console.print("Cleared existing index (47.3 MB)")
    console.print("Indexed 5678 commits (1234 unique blobs) in 8.2s")
