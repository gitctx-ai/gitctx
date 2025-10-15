"""Verbose formatter with syntax-highlighted code blocks.

This formatter provides detailed, human-readable output with:
- File path and line range
- Similarity score
- HEAD commit markers
- Commit metadata
- Syntax-highlighted code with line numbers

Format:
    {file_path}:{start}-{end} ({score:.2f}) {marker} {sha[:7]}
    {commit_message} (dimmed)

    [Syntax-highlighted code with line numbers]

Example:
    src/auth.py:45-52 (0.92) ● f9e8d7c
    Add OAuth support

      45 def authenticate(user, password):
      46     '''Authenticate a user against the database.'''
      47     if not user:
      48         raise ValueError("User required")
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.syntax import Syntax

from gitctx.cli.symbols import SYMBOLS


class VerboseFormatter:
    """Verbose output with code context.

    Outputs multi-line format with syntax highlighting, line numbers,
    and commit metadata. Optimized for human review of search results.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "verbose"
    description = "Verbose output with code context"

    def format(self, results: list[dict[str, Any]], console: Console) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries with keys:
                - file_path: Path to file
                - start_line: Starting line number
                - end_line: Ending line number
                - _distance: Similarity score (0-1)
                - is_head: Whether commit is HEAD
                - commit_sha: Full commit SHA
                - commit_message: Commit message
                - chunk_content: Code content
                - language: Language for syntax highlighting (optional)
            console: Rich Console instance for formatted output

        Returns:
            None - Results are written directly to console
        """
        for i, result in enumerate(results):
            # Extract values
            file_path = result["file_path"]
            start_line = result["start_line"]
            end_line = result["end_line"]
            score = result["_distance"]
            is_head = result["is_head"]
            commit_sha = result["commit_sha"]
            commit_message = result["commit_message"]
            chunk_content = result["chunk_content"]
            language = result.get("language", "markdown")

            # Format HEAD marker based on terminal type
            head_marker = SYMBOLS["head"] if is_head else " "

            # Print header line
            console.print(
                f"\n{file_path}:{start_line}-{end_line} ({score:.2f}) "
                f"{head_marker} {commit_sha[:7]}"
            )

            # Print metadata (dimmed)
            console.print(f"[dim]{commit_message}[/dim]")

            # Print syntax-highlighted code
            syntax = Syntax(
                chunk_content,
                language,
                line_numbers=True,
                start_line=start_line,
                theme="monokai",
            )
            console.print(syntax)

            # Add blank line separator (except after last result)
            if i < len(results) - 1:
                console.print()
