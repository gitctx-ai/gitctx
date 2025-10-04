"""Search command for gitctx CLI."""

import typer
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS

console = Console()


def register(app: typer.Typer) -> None:
    """Register the search command with the CLI app."""
    app.command(name="search")(search_command)


def search_command(
    query: str = typer.Argument(
        ...,
        help="The search query to find relevant code and documentation",
    ),
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
    # Validate mutually exclusive output modes
    if verbose and mcp:
        console_err = Console(stderr=True)
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --verbose and --mcp are mutually exclusive"
        )
        raise typer.Exit(code=2)

    # Mock implementation: query is validated by Typer but not used in mock results
    # Real implementation would use query for semantic search
    _ = query  # Acknowledge parameter (used by Typer for validation)

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
        "password": "testpass123"
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
        console.print(f"query: {query}")
        console.print(f"results_count: {len(results_to_show)}")
        console.print("duration_seconds: 0.23")
        console.print("timestamp: 2025-10-04T13:00:00Z")
        console.print("version: 0.1.0")
        console.print("---")
        console.print()
        console.print(f'# Search Results: "{query}"')
        console.print()
        console.print("## Summary")
        console.print()
        console.print(f"- **Query**: `{query}`")
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
