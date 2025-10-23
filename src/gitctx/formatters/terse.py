"""Terse formatter for file-grouped search results.

This formatter shows one line per chunk, sorted by score descending (best matches
first for quick scanning). Results are grouped by file with chunk counts.

Format:
    {file_path} ({N} chunks):
      :{line_num}  {score:.2f}  {head_marker}{sha[:7]}  {preview}

Example:
    src/auth/middleware.py (3 chunks):
      :15   0.95  🟢f9e8d7c  class AuthMiddleware:
      :42   0.87  🟢abc1234  def process_request(self, request):
      :103  0.75   def5678  def validate_token(self, token):

    src/auth/handlers.py (1 chunk):
      :42   0.87  🟢ghi9012  def authenticate_user(username, password):
"""

from __future__ import annotations

from typing import Any

from rich.console import Console

from gitctx.cli.symbols import SYMBOLS
from gitctx.formatters.base import MAX_PREVIEW_LENGTH, _ResultWrapper, filter_and_group_results


class TerseFormatter:
    """Terse single-line format with file grouping (default).

    Outputs one line per chunk with file grouping, showing line number, score,
    and preview. Chunks sorted by score descending within each file.

    Attributes:
        name: Formatter identifier
        description: Human-readable description
    """

    name = "terse"
    description = "Terse single-line format with file grouping (default)"

    def format(
        self,
        results: list[dict[str, Any]],
        console: Console,
        **kwargs: Any,
    ) -> None:
        """Format and output search results to console.

        Args:
            results: List of SearchResult objects
            console: Rich Console instance for formatted output
            **kwargs: Additional formatting options:
                - min_similarity: Minimum similarity threshold (default 0.5)
                - filter: Which chunks to include (head/history/all, default head)
                - theme: Unused in terse format (for compatibility)

        Returns:
            None - Results are written directly to console
        """
        # Wrap dicts in _ResultWrapper for .score property support
        # This allows dict-based results to work with filter_and_group_results()
        search_results = [_ResultWrapper(r) if isinstance(r, dict) else r for r in results]

        # Extract parameters
        min_similarity = kwargs.get("min_similarity", 0.5)
        filter_mode = kwargs.get("filter", "head")

        # Filter and group results (shared function handles filtering and file-level sorting)
        grouped = filter_and_group_results(search_results, min_similarity, filter_mode)

        # Format each file's chunks
        for file_path, chunks in grouped.items():
            # Sort chunks by score descending (best matches first)
            # Tie-breaking: score desc → line asc → content lex
            chunks.sort(key=lambda c: (-c.score, c.start_line, c.chunk_content))

            # File header with chunk count (singular/plural)
            chunk_word = "chunk" if len(chunks) == 1 else "chunks"
            console.print(f"\n{file_path} ({len(chunks)} {chunk_word}):")

            # One line per chunk: :LINE_NUM  SCORE  HEAD_MARKER+SHA  PREVIEW
            for chunk in chunks:
                # Extract preview (first line, max 80 chars)
                preview = self._format_preview(chunk.chunk_content)

                # Format HEAD marker (● or [HEAD] for current commit, space for history)
                head_marker = SYMBOLS["head"] if chunk.is_head else " "

                # Print chunk line (escape=False allows preview content with special chars)
                sha_short = chunk.commit_sha[:7]
                line_prefix = f"  :{chunk.start_line}  {chunk.score:.2f}"
                line_output = f"{line_prefix}  {head_marker}{sha_short}  {preview}"
                console.print(
                    line_output,
                    markup=False,  # Disable Rich markup to preserve [brackets]
                )

    def _format_preview(self, content: str) -> str:
        """Format chunk content as single-line preview.

        Args:
            content: Chunk content (may be multiline)

        Returns:
            First line, stripped of leading whitespace, truncated to 80 chars

        Edge cases:
            - Empty content: "[empty chunk]"
            - Whitespace-only: "[empty chunk]"
            - Multiline: Only first line
            - Long lines: Truncated with "..." suffix
        """
        # Handle empty or whitespace-only content
        if not content or not content.strip():
            return "[empty chunk]"

        # Extract first line (handle all line ending types: \n, \r\n, \r)
        lines = content.splitlines()
        first_line = lines[0] if lines else ""

        # Strip leading whitespace for readability
        first_line = first_line.lstrip()

        # Empty after stripping is caught above, so first_line has content here
        # Truncate to MAX_PREVIEW_LENGTH chars with ellipsis
        if len(first_line) > MAX_PREVIEW_LENGTH:
            return first_line[:MAX_PREVIEW_LENGTH] + "..."

        return first_line
