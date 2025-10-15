"""MCP formatter with structured markdown for AI consumption.

This formatter provides machine-readable output optimized for LLM tools:
- YAML frontmatter with structured metadata
- Markdown body with headers
- Code blocks with language tags
- Never uses plain text (always markdown fallback)

Format:
    ---
    results:
      - file_path: {path}
        line_numbers: {start}-{end}
        score: {score:.3f}
        commit_sha: {sha}
    ---

    ## {file_path}:{start}-{end}
    **Score:** {score:.3f} | **Commit:** {sha[:7]}
    ```{language}
    {content}
    ```

Example:
    ---
    results:
      - file_path: src/auth.py
        line_numbers: 45-52
        score: 0.920
        commit_sha: f9e8d7c1234567890
    ---

    ## src/auth.py:45-52
    **Score:** 0.920 | **Commit:** f9e8d7c
    ```python
    def authenticate(user, password):
        '''Authenticate a user.'''
    ```
"""

from __future__ import annotations

from typing import Any

from rich.console import Console


class MCPFormatter:
    """Structured markdown for AI tools.

    Outputs YAML frontmatter with result metadata followed by Markdown
    body with code blocks. Optimized for MCP (Model Context Protocol)
    and LLM consumption.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "mcp"
    description = "Structured markdown for AI tools"

    def format(self, results: list[dict[str, Any]], console: Console) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries with keys:
                - file_path: Path to file
                - start_line: Starting line number
                - end_line: Ending line number
                - _distance: Similarity score (0-1)
                - commit_sha: Full commit SHA
                - chunk_content: Code content
                - language: Language for syntax highlighting (optional)
            console: Rich Console instance for formatted output

        Returns:
            None - Results are written directly to console
        """
        # Print YAML frontmatter
        console.print("---")
        console.print("results:")
        for result in results:
            file_path = result["file_path"]
            start_line = result["start_line"]
            end_line = result["end_line"]
            score = result["_distance"]
            commit_sha = result["commit_sha"]

            console.print(f"  - file_path: {file_path}")
            console.print(f"    line_numbers: {start_line}-{end_line}")
            console.print(f"    score: {score:.3f}")
            console.print(f"    commit_sha: {commit_sha}")

        console.print("---\n")

        # Print Markdown body
        for result in results:
            file_path = result["file_path"]
            start_line = result["start_line"]
            end_line = result["end_line"]
            score = result["_distance"]
            commit_sha = result["commit_sha"]
            chunk_content = result["chunk_content"]
            language = result.get("language", "markdown")

            # Print header
            console.print(f"## {file_path}:{start_line}-{end_line}")

            # Print metadata line
            console.print(f"**Score:** {score:.3f} | **Commit:** {commit_sha[:7]}")

            # Print code block with language tag
            console.print(f"```{language}")
            console.print(chunk_content)
            console.print("```\n")
