"""Terse single-line formatter for search results.

This is the default formatter that outputs one line per result in a compact format
suitable for terminal viewing.

Format:
    {file_path}:{start_line}:{score:.2f} {marker} {sha[:7]} ({date}, {author}) "{msg[:50]}"

Example:
    src/auth.py:45:0.92 ● f9e8d7c (2025-10-02, Alice) "Add OAuth support"
    src/login.py:23:0.76   abc1234 (2025-09-15, Bob) "Initial login implementation with basic validat"
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console


class TerseFormatter:
    """Terse single-line format (default).

    Outputs one line per result with file path, line number, score, commit metadata,
    and truncated message. Uses platform-aware symbols for HEAD marker.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "terse"
    description = "Terse single-line format (default)"

    def format(self, results: list[dict[str, Any]], console: Console) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries with keys:
                - file_path: Path to file
                - start_line: Starting line number
                - _distance: Similarity score (0-1)
                - is_head: Whether commit is HEAD
                - commit_sha: Full commit SHA
                - commit_date: Commit date string
                - author_name: Author name
                - commit_message: Commit message
            console: Rich Console instance for formatted output

        Returns:
            None - Results are written directly to console
        """
        for result in results:
            # Extract values
            file_path = result["file_path"]
            start_line = result["start_line"]
            score = result["_distance"]
            is_head = result["is_head"]
            commit_sha = result["commit_sha"]
            commit_date = result["commit_date"]
            author_name = result["author_name"]
            commit_message = result["commit_message"]

            # Format HEAD marker based on terminal type
            if is_head:
                head_marker = " [HEAD]" if console.legacy_windows else " ●"
            else:
                # Space for alignment (no marker for historic commits)
                head_marker = "       " if console.legacy_windows else "  "

            # Take first line, then truncate to 50 characters
            first_line = commit_message.split("\n")[0]
            truncated_message = first_line[:50]

            # Format commit date from Unix timestamp to YYYY-MM-DD
            formatted_date = datetime.fromtimestamp(commit_date).strftime("%Y-%m-%d")

            # Format and print line (no_wrap + crop=False to prevent truncation)
            console.print(
                f"{file_path}:{start_line}:{score:.2f}{head_marker} "
                f"{commit_sha[:7]} ({formatted_date}, {author_name}) "
                f'"{truncated_message}"',
                no_wrap=True,
                crop=False,
            )
