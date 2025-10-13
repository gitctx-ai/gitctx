"""Search command for gitctx CLI."""

from pathlib import Path
from typing import Annotated

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


def register(app: typer.Typer) -> None:
    """Register the search command with the CLI app."""
    app.command(name="search")(search_command)


def search_command(
    query: Annotated[
        list[str],
        typer.Argument(help="The search query to find relevant code and documentation"),
    ],
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
    # Join variadic query words into single string
    query_text = " ".join(query)

    # Validate mutually exclusive output modes
    if verbose and mcp:
        console_err = Console(stderr=True)
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --verbose and --mcp are mutually exclusive"
        )
        raise typer.Exit(code=2)

    # Generate query embedding
    try:
        settings = GitCtxSettings()
        repo_path = Path.cwd()
        store = LanceDBStore(repo_path / ".gitctx" / "db" / "lancedb")
        embedder = QueryEmbedder(settings, store)

        # Check cache first to avoid showing spinner for instant cache hits
        cache_key = embedder.get_cache_key(query_text)
        cached_vector = store.get_query_embedding(cache_key)

        if cached_vector is not None:
            # Cache hit - instant result
            console.print("[green]✓[/green] Using cached query embedding")
            query_vector = cached_vector
        else:
            # Cache miss - show progress for API call
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                embed_task = progress.add_task(
                    "[cyan]Generating query embedding...[/cyan]", total=None
                )
                query_vector = embedder.embed_query(query_text)  # noqa: F841 (will be used in STORY-0001.3.2)
                progress.update(
                    embed_task, description="[green]✓[/green] Query embedding generated"
                )

        # Success message
        console.print(
            f"[green]✓[/green] Query embedded successfully ({query_vector.shape[0]} dimensions)"
        )
        console.print("[dim]Note: Full search results coming in STORY-0001.3.2[/dim]")

    except ValidationError as err:
        console_err = Console(stderr=True)
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=2) from err

    except ConfigurationError as err:
        console_err = Console(stderr=True)
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=4) from err

    except EmbeddingError as err:
        console_err = Console(stderr=True)
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {err}")
        raise typer.Exit(code=5) from err

    # Mock implementation: query_vector will be used for actual semantic search in STORY-0001.3.2
    # TODO: Replace mock results with actual vector search: retriever.search(query_vector, limit=limit)

    # Mock search results: demonstrate both git history AND HEAD
    # TUI_GUIDE.md lines 404-411 (default), 417-465 (verbose)
    mock_results = [
        {
            "file": "src/auth/login.py",
            "line": 45,
            "score": 0.92,
            "commit": "f9e8d7c",
            "is_head": True,
            "date": "2025-10-02",
            "author": "Alice",
            "message": "Add OAuth support",
            "code": """def authenticate_user(username: str, password: str) -> User:
    \"\"\"Authenticate user with credentials.\"\"\"
    user = get_user_by_username(username)
    if not user:
        return None
    return user""",
        },
        {
            "file": "src/auth/middleware.py",
            "line": 12,
            "score": 0.87,
            "commit": "a1b2c3d",
            "is_head": False,  # Historical commit
            "date": "2024-09-15",
            "author": "Bob",
            "message": "Add middleware auth",
            "code": """class AuthenticationMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])""",
        },
        {
            "file": "docs/authentication.md",
            "line": 34,
            "score": 0.85,
            "commit": "e4f5g6h",
            "is_head": True,
            "date": "2025-10-02",
            "author": "Alice",
            "message": "Update auth docs",
            "code": """## Authentication Flow

1. User submits credentials to `/api/login`
2. Server validates against database
3. If valid, JWT token generated (24h expiry)""",
        },
        {
            "file": "tests/test_auth.py",
            "line": 78,
            "score": 0.76,
            "commit": "f9e8d7c",
            "is_head": True,
            "date": "2025-10-02",
            "author": "Alice",
            "message": "Add OAuth support",
            "code": """def test_login_with_valid_credentials():
    \"\"\"Test successful authentication.\"\"\"
    response = client.post("/api/login", json={
        "username": "testuser",
        "password": "<redacted>"
    })
    assert response.status_code == 200""",
        },
    ]

    # Limit results
    results_to_show = mock_results[: min(limit, len(mock_results))]

    # MCP MODE: Structured markdown for LLM consumption (TUI_GUIDE.md lines 467-599)
    if mcp:
        # YAML frontmatter
        console.print("---")
        console.print("status: success")
        console.print("command: search")
        console.print(f"query: {query_text}")
        console.print(f"results_count: {len(results_to_show)}")
        console.print("duration_seconds: 0.23")
        console.print("timestamp: 2025-10-04T13:00:00Z")
        console.print("version: 0.1.0")
        console.print("---")
        console.print()
        console.print(f'# Search Results: "{query_text}"')
        console.print()
        console.print("## Summary")
        console.print()
        console.print(f"- **Query**: `{query_text}`")
        console.print(f"- **Results**: {len(results_to_show)} matches")
        console.print("- **Duration**: 0.23s")
        console.print("- **Chunks searched**: 5678")
        console.print()
        console.print("## Results")

        for idx, result in enumerate(results_to_show, 1):
            console.print()
            console.print(
                f"### {idx}. {result['file']}:{result['line']} (Score: {result['score']:.2f})"
            )
            console.print()

            # Source metadata - ALWAYS show commit info for agentic context
            if result["is_head"]:
                console.print("**Source**: Current file (HEAD)")
            else:
                console.print("**Source**: Historical commit")

            # Always include full commit metadata for AI context
            console.print(f"**Commit**: {result['commit']}")
            console.print(f"**Author**: {result['author']}")
            console.print(f"**Date**: {result['date']}")
            console.print(f"**Message**: {result['message']}")

            console.print()
            console.print("**Context**: Code snippet")
            console.print()

            # Code block with language marker
            file_path = str(result["file"])
            lang = "python" if file_path.endswith(".py") else "markdown"
            console.print(f"```{lang}")
            console.print(result["code"])
            console.print("```")
            console.print()

            # Metadata section
            console.print("**Metadata**:")
            console.print(f"- File: `{result['file']}`")
            console.print(f"- Lines: {result['line']}")
            console.print(f"- Relevance: {result['score']:.2f}")
            console.print("- Type: function_definition")
            console.print(f"- Language: {lang}")
            console.print("- Tokens: 234")

            if idx < len(results_to_show):
                console.print()
                console.print("---")

        return

    # VERBOSE MODE: Show code context (TUI_GUIDE.md lines 417-465)
    if verbose:
        for result in results_to_show:
            # Symbol: ● for HEAD, space for historical
            head_symbol = SYMBOLS["head"] if result["is_head"] else " "

            # Header line
            console.print(
                f"\n{result['file']}:{result['line']} ({result['score']:.2f}) {head_symbol} "
                f"{result['commit']} ({result['date']}, {result['author']})"
            )
            console.print("─" * 70)
            console.print(f"Message: {result['message']}")
            console.print()
            # Code context (plain text, no syntax highlighting in mocks)
            console.print(result["code"])

        console.print(f"\n{len(results_to_show)} results in 0.23s")
        return

    # DEFAULT MODE: Terse output (TUI_GUIDE.md lines 404-411)
    for result in results_to_show:
        # Symbol: ● for HEAD, nothing for historical
        head_symbol = SYMBOLS["head"] if result["is_head"] else " "
        # Format: file:line:score ● commit (HEAD, date, author) "message"
        console.print(
            f"{result['file']}:{result['line']}:{result['score']:.2f} {head_symbol} "
            f"{result['commit']} ({'HEAD, ' if result['is_head'] else ''}{result['date']}, {result['author']}) "
            f'"{result["message"]}"'
        )

    console.print(f"\n{len(results_to_show)} results in 0.23s")
