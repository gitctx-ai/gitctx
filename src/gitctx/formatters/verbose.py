"""Verbose formatter with syntax-highlighted code blocks and file grouping.

This formatter provides detailed, human-readable output with:
- File grouping (multiple chunks per file)
- Line order sorting (natural reading order)
- Best-match indicator (⭐ or *) for highest-scoring chunk per file
- Similarity score and HEAD commit markers
- Commit metadata
- Syntax-highlighted code with line numbers
- Filter mode support (head/history/all)
- Min similarity threshold support

Format (per file):
    {file_path} ({N} chunks):

      # Lines {start}-{end} (score: {score:.2f})
      {marker} {sha[:7]} - {commit_message} (dimmed)

      [Syntax-highlighted code with line numbers]

      # ⭐ Lines {start}-{end} (score: {score:.2f}, best match)
      {marker} {sha[:7]} - {commit_message} (dimmed)

      [Syntax-highlighted code with line numbers]

Example:
    src/auth.py (3 chunks):

      # Lines 10-15 (score: 0.80)
        f9e8d7c - Add login function

          10 def login(username, password):
          11     '''Login a user.'''
          12     ...

      # ⭐ Lines 45-52 (score: 0.95, best match)
      🟢 f9e8d7c - Add OAuth support

          45 def authenticate(user, password):
          46     '''Authenticate a user against the database.'''
          47     ...

      # Lines 103-110 (score: 0.75)
        abc1234 - Refactor auth module

         103 def logout(user):
         104     '''Logout a user.'''
         105     ...
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from rich.console import Console
from rich.syntax import Syntax

from gitctx.cli.symbols import SYMBOLS
from gitctx.formatters.base import _ResultWrapper, filter_and_group_results, format_distance_score


class VerboseFormatter:
    """Verbose output with code context and file grouping.

    Outputs multi-line format with file grouping, line order sorting,
    best-match indicators, syntax highlighting, and commit metadata.
    Optimized for human review of search results.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "verbose"
    description = "Verbose output with code context"

    def format(self, results: list[dict[str, Any]], console: Console, **kwargs: Any) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries with keys:
                - file_path: Path to file
                - start_line: Starting line number
                - end_line: Ending line number
                - distance: Similarity score (0-1)
                - is_head: Whether commit is HEAD
                - commit_sha: Full commit SHA
                - commit_message: Commit message
                - chunk_content: Code content
                - language: Language for syntax highlighting (optional)
            console: Rich Console instance for formatted output
            **kwargs: Additional options:
                - theme: Syntax highlighting theme (default: "monokai")
                - min_similarity: Minimum similarity threshold (default: 0.5)
                - filter: Which chunks to include (head/history/all, default: head)

        Returns:
            None - Results are written directly to console
        """
        # Extract parameters
        theme = kwargs.get("theme", "monokai")
        min_similarity = kwargs.get("min_similarity", 0.5)
        filter_mode = kwargs.get("filter", "head")

        # Convert dict results to wrapped objects
        # _ResultWrapper provides .score property and attribute access
        result_objs = [_ResultWrapper(r) for r in results]

        # Filter and group results (shared function handles filtering and file-level sorting)
        grouped = filter_and_group_results(result_objs, min_similarity, filter_mode)

        # Format each file's chunks
        for file_path, chunks in grouped.items():
            # Sort chunks by line order: (start_line, -score, content)
            # This ensures natural reading order (top to bottom)
            chunks.sort(key=lambda c: (c.start_line, -c.score, c.chunk_content))

            # Identify best match: max by (score, -start_line, content)
            # Highest score wins, ties broken by earliest line
            best_chunk = max(chunks, key=lambda c: (c.score, -c.start_line, c.chunk_content))

            # File header with chunk count (singular/plural)
            chunk_word = "chunk" if len(chunks) == 1 else "chunks"
            console.print(f"\n{file_path} ({len(chunks)} {chunk_word}):")

            # Format each chunk
            for chunk in chunks:
                # Check if this is the best match
                is_best_match = chunk == best_chunk

                # Format score (handle inf for BM25-only matches)
                score_str = format_distance_score(chunk.score, precision=2)

                # Build chunk header comment
                best_match_suffix = ", best match" if is_best_match else ""
                best_match_symbol = SYMBOLS["best_match"] if is_best_match else "#"
                header = (
                    f"{best_match_symbol} Lines {chunk.start_line}-{chunk.end_line} "
                    f"(score: {score_str}{best_match_suffix})"
                )
                console.print(f"\n  {header}")

                # Format HEAD marker based on terminal type
                head_marker = SYMBOLS["head"] if chunk.is_head else " "

                # Print metadata line (indented, dimmed)
                console.print(
                    f"  {head_marker} {chunk.commit_sha[:7]} - [dim]{chunk.commit_message}[/dim]"
                )

                # Print syntax-highlighted code (indented)
                console.print()  # Blank line before code
                syntax = Syntax(
                    chunk.chunk_content,
                    chunk.language,
                    line_numbers=True,
                    start_line=chunk.start_line,
                    theme=theme,
                    # Indent all lines by 4 spaces
                    code_width=196,  # Account for indentation (200 - 4)
                )

                # Capture syntax output and indent it
                syntax_output = StringIO()
                temp_console = Console(file=syntax_output, legacy_windows=console.legacy_windows)
                temp_console.print(syntax)
                syntax_lines = syntax_output.getvalue().rstrip().split("\n")

                # Print each line with indentation
                for line in syntax_lines:
                    console.print(f"    {line}")
