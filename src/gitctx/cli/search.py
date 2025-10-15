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
from gitctx.formatters import get_formatter
from gitctx.search.embeddings import QueryEmbedder
from gitctx.search.errors import EmbeddingError, ValidationError
from gitctx.storage.lancedb_store import LanceDBStore

# Always force terminal colors for consistent CLI output (including tests)
# Use explicit color_system to ensure ANSI codes are generated
console = Console(force_terminal=True, color_system="truecolor")
console_err = Console(stderr=True, force_terminal=True, color_system="truecolor")

# Search limit constants
MIN_SEARCH_LIMIT = 1
MAX_SEARCH_LIMIT = 100
DEFAULT_SEARCH_LIMIT = 10

# OpenAI embedding token limits
MAX_QUERY_TOKENS = 8191  # text-embedding-3-* model limit


def _get_query_text(query: list[str] | None) -> str:
    """Extract query text from CLI args or stdin.

    Args:
        query: CLI arguments after 'gitctx search' (e.g., ['auth', 'middleware'])

    Returns:
        str: Query text joined with spaces (e.g., 'auth middleware')

    Raises:
        typer.Exit(2): If no query provided (neither args nor stdin)
        typer.Exit(2): If query exceeds MAX_QUERY_TOKENS token limit
    """
    # If query provided as args, join and return early
    if query:
        query_text = " ".join(query)
    elif sys.stdin.isatty():
        # No args provided and interactive terminal with no piped input
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
        )
        raise typer.Exit(2)
    else:
        # Read from piped stdin
        query_text = sys.stdin.read().strip()
        if not query_text:
            console_err.print(
                f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
            )
            raise typer.Exit(2)

    # Validate query token length
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoding.encode(query_text))

        if token_count > MAX_QUERY_TOKENS:
            console_err.print(
                f"[red]{SYMBOLS['error']}[/red] Error: Query exceeds {MAX_QUERY_TOKENS} tokens "
                f"(got {token_count})\nTry a shorter query or break it into multiple searches."
            )
            raise typer.Exit(2)
    except ImportError:
        # If tiktoken not available, skip validation (don't block functionality)
        pass

    return query_text


def search_command(
    query: Annotated[
        list[str] | None,
        typer.Argument(help="The search query to find relevant code and documentation"),
    ] = None,
    limit: int = typer.Option(
        DEFAULT_SEARCH_LIMIT,
        "--limit",
        "-n",
        help=f"Maximum number of results to return ({MIN_SEARCH_LIMIT}-{MAX_SEARCH_LIMIT})",
        min=MIN_SEARCH_LIMIT,
        max=MAX_SEARCH_LIMIT,
    ),
    min_similarity: float = 0.5,
    output_format: str = typer.Option(
        "terse",
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
    theme: str | None = None,
) -> None:
    """
    Search the indexed repository for relevant code using semantic similarity.

    **Context Engineering Focus:**

    gitctx is designed for context engineering - results are meant to be included
    in AI prompts (Claude, GPT, etc.). Quality matters more than quantity, since
    every result consumes precious context window tokens.

    **Default Behavior (--min-similarity 0.5):**

    Returns moderately to highly relevant results. Filters out noise and tangentially
    related code that would waste context tokens. This ensures AI assistants receive
    high-quality, relevant context.

    **Similarity Scoring:**

    - 0.7-1.0: Highly relevant (similar concepts/implementations) → EXCELLENT
    - 0.5-0.7: Moderately relevant (related functionality) → GOOD
    - 0.3-0.5: Vaguely related (marginal value) → QUESTIONABLE
    - 0.0-0.3: Barely related (noise) → FILTERED BY DEFAULT
    - -1.0-0.0: Opposite meaning (garbage) → FILTERED BY DEFAULT

    **Adjusting the Threshold:**

    - `--min-similarity 0.7`: High precision (only best matches for AI context)
    - `--min-similarity 0.5`: Balanced (DEFAULT - good context quality)
    - `--min-similarity 0.3`: High recall (include marginal results)
    - `--min-similarity 0.0`: Debug mode (show all non-negative results)
    - `--min-similarity -1.0`: Show ALL results (including opposite meaning)

    **Technical Details:**

    Uses cosine distance for vector search (LanceDB):
    - Cosine distance = 1 - cosine similarity (range: 0-2)
    - Lower distance = higher similarity = more relevant
    - Post-filtering applied after search (LanceDB limitation)
    - Reference: https://lancedb.com/docs/search/vector-search/
    - Filtering pattern: https://github.com/lancedb/lancedb/issues/745

    Examples:

        # Default: balanced quality (0.5 threshold)
        $ gitctx search "authentication logic"

        # High precision: only best matches for AI
        $ gitctx search "database connection" --min-similarity 0.7

        # Debug: see all non-negative similarity results
        $ gitctx search "API endpoints" --min-similarity 0.0

        # Testing: see absolutely ALL results (even opposite meaning)
        $ gitctx search "test query" --min-similarity -1.0

        # With code context
        $ gitctx search "database connection" --verbose

        # MCP mode (structured markdown for AI)
        $ gitctx search "authentication" --mcp
    """
    # Get query text from args or stdin
    query_text = _get_query_text(query)

    # Validate mutually exclusive output modes
    # Check for conflicts between boolean flags and --format flag
    if verbose and mcp:
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --verbose and --mcp are mutually exclusive"
        )
        raise typer.Exit(code=2)

    if verbose and output_format == "mcp":
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --verbose and --format mcp are mutually exclusive"
        )
        raise typer.Exit(code=2)

    if mcp and output_format == "verbose":
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --mcp and --format verbose are mutually exclusive"
        )
        raise typer.Exit(code=2)

    # Resolve format from flags (--verbose and --mcp override --format)
    if verbose:
        output_format = "verbose"
    elif mcp:
        output_format = "mcp"

    # Check index directory exists
    db_path = Path.cwd() / ".gitctx" / "db" / "lancedb"

    if not db_path.exists():
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: No index found\nRun: gitctx index")
        raise typer.Exit(8)

    # Generate query embedding
    try:
        settings = GitCtxSettings()

        # Resolve theme with precedence: CLI flag > UserConfig > default
        resolved_theme = theme if theme is not None else settings.user.theme

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
        # Convert similarity to distance: cosine_distance = 1 - cosine_similarity
        # LanceDB returns distances (0-2), users specify similarity (0-1)
        # Formula: max_distance = 1.0 - min_similarity
        # - min_similarity=0.0 (default) → max_distance=1.0 (filter out negative similarity)
        # - min_similarity=0.5 → max_distance=0.5 (show moderately similar results)
        # - min_similarity=0.7 → max_distance=0.3 (show highly similar results)
        # Reference: https://lancedb.com/docs/search/vector-search/
        max_distance = 1.0 - min_similarity
        results = store.search(
            query_vector=query_vector,
            limit=limit,
            filter_head_only=False,
            max_distance=max_distance,
        )
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

    # Format and display results
    try:
        formatter = get_formatter(output_format)
        formatter.format(results, console, theme=resolved_theme)
    except ValueError as err:
        # Unknown formatter name
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=2) from err

    # Display results summary with helpful message for zero results
    console.print(f"\n{len(results)} results in {duration:.2f}s")

    if len(results) == 0 and min_similarity > 0.0:
        console.print(
            f"\n[yellow]💡 Tip:[/yellow] No results above similarity threshold ({min_similarity:.1f}).\n"
            f"   Try a broader query or use [cyan]--min-similarity 0.0[/cyan] to see all results."
        )
