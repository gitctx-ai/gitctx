"""Clear command for gitctx CLI."""

import typer
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS

console = Console()


def clear_command(
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
    """
    Clear cached data and indexes.

    By default, asks for confirmation before clearing. Use --force to skip.

    IMPORTANT: Clearing embeddings requires regenerating them via API calls (costs money).
    Clearing only the database preserves embeddings for fast, free rebuilding.

    Database dependency: The database contains indexed vectors from embeddings,
    so clearing embeddings also clears the database.

    Examples:

        # Clear everything (requires API calls to rebuild)
        $ gitctx clear --all

        # Clear database only (fast rebuild from existing embeddings, no API calls)
        $ gitctx clear --database --force

        # Clear embeddings (also clears database, requires API calls to rebuild)
        $ gitctx clear --embeddings --force
    """
    # Determine what to clear
    # Note: embeddings implies database (database depends on embeddings)
    clear_db = database or embeddings or all_data
    clear_emb = embeddings or all_data

    if not clear_db and not clear_emb:
        console.print("[yellow]![/yellow] No data specified to clear")
        console.print("Use --database, --embeddings, or --all")
        return

    # Show what will be cleared
    items_to_clear = []
    if clear_db:
        items_to_clear.append("database (~/.gitctx/db/, 1.8 MB)")
    if clear_emb:
        items_to_clear.append("embeddings (~/.gitctx/embeddings/, 47.3 MB)")

    # Confirmation prompt (unless --force)
    if not force:
        console.print("\nThe following will be cleared:")
        for item in items_to_clear:
            console.print(f"  • {item}")
        console.print()

        # Warn about API costs if clearing embeddings
        if clear_emb:
            console.print(
                f"[yellow]{SYMBOLS['warning']}[/yellow]  "
                "Regenerating embeddings will incur API costs"
            )
            console.print()

        # Ask for confirmation
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[yellow]Operation cancelled[/yellow]")
            return

    # Mock deletion
    if clear_db:
        console.print("Cleared database (~/.gitctx/db/, 1.8 MB)")
    if clear_emb:
        console.print("Cleared embeddings (~/.gitctx/embeddings/, 47.3 MB)")

    # Summary
    total_size = 0.0
    if clear_db:
        total_size += 1.8
    if clear_emb:
        total_size += 47.3

    console.print(f"\n[green]{SYMBOLS['success']}[/green] Removed {total_size:.2f} MB")
