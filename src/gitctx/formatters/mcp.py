"""MCP formatter with structured markdown for AI consumption.

This formatter provides machine-readable output optimized for LLM tools:
- YAML frontmatter with file-grouped metadata
- Markdown body with file-grouped code blocks
- Never uses plain text (always markdown fallback)

Format (file-grouped):
    ---
    files:
      - file_path: {path}
        language: {lang}
        chunks: {count}
        best_score: {score:.3f}
    ---

    ## {file_path} ({N} chunks)

    **Lines {start}-{end}** | **Score:** {score:.3f} | **Commit:** {head_marker}{sha[:7]}
    ```{language}
    {content}
    ```

Example:
    ---
    files:
      - file_path: src/auth.py
        language: python
        chunks: 2
        best_score: 0.920
    ---

    ## src/auth.py (2 chunks)

    **Lines 45-52** | **Score:** 0.920 | **Commit:** 🟢f9e8d7c
    ```python
    def authenticate(user, password):
        '''Authenticate a user.'''
    ```

    **Lines 67-75** | **Score:** 0.850 | **Commit:**  abc1234
    ```python
    def validate_token(token):
        return token.is_valid()
    ```
"""

from __future__ import annotations

from typing import Any

import yaml
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS
from gitctx.formatters.base import _ResultWrapper, filter_and_group_results, format_distance_score


class MCPFormatter:
    """Structured markdown for AI tools with file grouping.

    Outputs YAML frontmatter with file-grouped metadata followed by Markdown
    body with file-grouped code blocks. Optimized for MCP (Model Context Protocol)
    and LLM consumption.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "mcp"
    description = "Structured markdown for AI tools"

    def format(
        self,
        results: list[dict[str, Any]],
        console: Console,
        **kwargs: Any,
    ) -> None:
        """Format and output search results to console with file grouping.

        Args:
            results: List of search result dictionaries with keys:
                - file_path: Path to file
                - start_line: Starting line number
                - end_line: Ending line number
                - distance: Similarity score (0-1)
                - commit_sha: Full commit SHA
                - chunk_content: Code content
                - language: Language for syntax highlighting (optional)
                - is_head: True if chunk is in HEAD (optional, default True)
            console: Rich Console instance for formatted output
            min_similarity: Minimum score threshold (default 0.5)
            filter: Which chunks to include (head/history/all, default head)

        Returns:
            None - Results are written directly to console
        """
        # Wrap dicts in _ResultWrapper for .score property support
        # This allows dict-based results to work with filter_and_group_results()
        search_results = [_ResultWrapper(r) if isinstance(r, dict) else r for r in results]

        # Extract filtering parameters
        min_similarity = kwargs.get("min_similarity", 0.5)
        filter_mode = kwargs.get("filter", "head")

        # Filter and group using shared function
        grouped = filter_and_group_results(search_results, min_similarity, filter_mode)

        # Build YAML frontmatter with file-grouped structure
        frontmatter = {
            "files": [
                {
                    "file_path": file_path,
                    "language": chunks[0].language,  # First chunk's language
                    "chunks": len(chunks),  # Count after filtering
                    "best_score": float(
                        format_distance_score(max(c.score for c in chunks), precision=3)
                    ),
                }
                for file_path, chunks in grouped.items()
            ]
        }

        # Print YAML frontmatter with proper escaping
        console.print("---")
        console.print(yaml.safe_dump(frontmatter, default_flow_style=False).rstrip())
        console.print("---\n")

        # Print Markdown body with file grouping
        for file_path, chunks in grouped.items():
            # Sort chunks by score descending (best first)
            # Tie-breaking: score desc → line asc → content lex
            chunks.sort(key=lambda c: (-c.score, c.start_line, c.chunk_content))

            # File header with chunk count
            chunk_word = "chunk" if len(chunks) == 1 else "chunks"
            console.print(f"\n## {file_path} ({len(chunks)} {chunk_word})")

            # Print each chunk with metadata + code block
            for chunk in chunks:
                score_str = format_distance_score(chunk.score, precision=3)

                # Format HEAD marker (● or [HEAD] for current commit, space for history)
                head_marker = SYMBOLS["head"] if chunk.is_head else " "

                console.print(
                    f"**Lines {chunk.start_line}-{chunk.end_line}** | **Score:** {score_str} | "
                    f"**Commit:** {head_marker}{chunk.commit_sha[:7]}"
                )
                console.print(f"```{chunk.language}")
                console.print(chunk.chunk_content)
                console.print("```\n")
