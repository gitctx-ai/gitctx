"""Search command for gitctx CLI."""

import sys
import time
from pathlib import Path
from typing import Annotated

import pyarrow as pa
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from gitctx.cli.symbols import SYMBOLS
from gitctx.config.errors import ConfigurationError
from gitctx.config.settings import GitCtxSettings
from gitctx.search.embeddings import QueryEmbedder
from gitctx.search.errors import EmbeddingError, ValidationError
from gitctx.storage.lancedb_store import LanceDBStore

console = Console()
console_err = Console(stderr=True)


def register(app: typer.Typer) -> None:
    """Register the search command with the CLI app."""
    app.command(name="search")(search_command)


def _get_query_text(query: list[str] | None) -> str:
    """Extract query text from CLI args or stdin.

    Args:
        query: CLI arguments after 'gitctx search' (e.g., ['auth', 'middleware'])

    Returns:
        str: Query text joined with spaces (e.g., 'auth middleware')

    Raises:
        typer.Exit(2): If no query provided (neither args nor stdin)
    """
    # If query provided as args, join and return early
    if query:
        return " ".join(query)

    # No args provided - check stdin
    if sys.stdin.isatty():
        # Interactive terminal with no piped input
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
        )
        raise typer.Exit(2)

    # Read from piped stdin
    query_text = sys.stdin.read().strip()
    if not query_text:
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
        )
        raise typer.Exit(2)

    return query_text


def search_command(
    query: Annotated[
        list[str] | None,
        typer.Argument(help="The search query to find relevant code and documentation"),
    ] = None,
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results to return",
        min=1,
        max=100,
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
) -> None:
    """
    Search the indexed repository for relevant code.

    This command searches through indexed git history to find
    the most relevant code across all commits.

    Examples:

        # Search (terse output)
        $ gitctx search "authentication logic"

        # With code context
        $ gitctx search "database connection" --verbose

        # Limit results
        $ gitctx search "API endpoints" -n 3

        # MCP mode (structured markdown for AI)
        $ gitctx search "authentication" --mcp
    """
    # Get query text from args or stdin
    query_text = _get_query_text(query)

    # Validate mutually exclusive output modes
    if verbose and mcp:
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --verbose and --mcp are mutually exclusive"
        )
        raise typer.Exit(code=2)

    # Check index directory exists
    db_path = Path.cwd() / ".gitctx" / "db" / "lancedb"

    if not db_path.exists():
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: No index found\nRun: gitctx index")
        raise typer.Exit(8)

    # Generate query embedding
    try:
        settings = GitCtxSettings()

        # Initialize store with error handling
        try:
            store = LanceDBStore(db_path)

            # Check for empty index
            if store.count() == 0:
                console_err.print(
                    f"[red]{SYMBOLS['error']}[/red] Error: No index found\nRun: gitctx index"
                )
                raise typer.Exit(8)
        except (ValueError, pa.lib.ArrowException) as err:
            # ValueError: Table not found (from LanceDB)
            # ArrowException: Schema/corruption issues (from PyArrow)
            if "code_chunks" in str(err).lower() or "table" in str(err).lower():
                console_err.print(
                    f"[red]{SYMBOLS['error']}[/red] Error: Index corrupted (missing code_chunks table)\n"
                    f"Fix with: gitctx clear && gitctx index"
                )
                raise typer.Exit(1) from err
            # Re-raise other exceptions
            raise

        embedder = QueryEmbedder(settings, store)

        # Check cache first to avoid showing spinner for instant cache hits
        cache_key = embedder.get_cache_key(query_text)
        cached_vector = store.get_query_embedding(cache_key)

        if cached_vector is not None:
            # Cache hit - instant result
            console_err.print("[green]✓[/green] Using cached query embedding")
            query_vector = cached_vector
        else:
            # Cache miss - show progress for API call
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console_err,
            ) as progress:
                embed_task = progress.add_task(
                    "[cyan]Generating query embedding...[/cyan]", total=None
                )
                query_vector = embedder.embed_query(query_text)
                progress.update(
                    embed_task, description="[green]✓[/green] Query embedding generated"
                )

        # Search LanceDB with timing
        start_time = time.time()
        results = store.search(query_vector=query_vector, limit=limit, filter_head_only=False)
        duration = time.time() - start_time

    except ValidationError as err:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=2) from err

    except ConfigurationError as err:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=4) from err

    except EmbeddingError as err:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=5) from err

    # Display results count (formatting deferred to STORY-0001.3.3)
    console.print(f"{len(results)} results in {duration:.2f}s")

    # TODO (STORY-0001.3.3): Add result formatting (terse, verbose, MCP modes)
    # For now, only display count. Result details will be implemented in STORY-0001.3.3
