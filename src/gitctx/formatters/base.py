"""Base protocol for result formatters.

This module defines the ResultFormatter protocol that all formatters must implement.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Protocol, runtime_checkable

from rich.console import Console

from gitctx.indexing.types import DISTANCE_NO_VECTOR_MATCH


@runtime_checkable
class ResultFormatter(Protocol):
    """Protocol for search result formatters.

    All formatters must implement this protocol to be compatible with the
    formatter registry and CLI.

    Attributes:
        name: Short identifier for the formatter (e.g., "terse", "verbose")
        description: Human-readable description of the formatter's purpose
    """

    name: str
    description: str

    def format(self, results: list[dict[str, Any]], console: Console, **kwargs: Any) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries from vector store
            console: Rich Console instance for formatted output
            **kwargs: Additional formatting options (theme, filter, min_similarity, etc.)

        Returns:
            None - Results are written directly to console
        """
        ...


def format_distance_score(distance: float, precision: int = 2) -> str:
    """Format distance score, handling infinite values for BM25-only matches.

    In hybrid search, BM25-only matches (without vector component) have
    distance = DISTANCE_NO_VECTOR_MATCH to indicate "no vector similarity".
    This function formats such cases as "BM25" for clarity.

    Args:
        distance: Cosine distance value (0.0-2.0, or DISTANCE_NO_VECTOR_MATCH for BM25-only)
        precision: Number of decimal places for numeric scores (default: 2)

    Returns:
        Formatted score string ("BM25" for inf, otherwise numeric with precision)

    Examples:
        >>> format_distance_score(0.85, precision=2)
        '0.85'
        >>> format_distance_score(DISTANCE_NO_VECTOR_MATCH)
        'BM25'
        >>> format_distance_score(0.12345, precision=3)
        '0.123'
    """
    return "BM25" if distance == DISTANCE_NO_VECTOR_MATCH else f"{distance:.{precision}f}"


class FormatterBase:
    """Base formatter with shared filtering and grouping logic.

    Design: Pure data transformation (filter + group). Does NOT sort chunks
    within files - each formatter decides its own presentation order.
    """

    def _filter_and_group(
        self,
        results: list[Any],
        min_similarity: float = 0.5,
        filter_mode: str = "head",
    ) -> dict[str, list[Any]]:
        """Filter and group results by file_path.

        Args:
            results: Flat list of search results (SearchResult objects)
            min_similarity: Minimum similarity threshold (default 0.5, range -1.0 to 1.0)
            filter_mode: Which chunks to include (head/history/all, default head)

        Returns:
            Dict mapping file_path -> list of chunks (filtered, UNSORTED within each file)
            Files sorted by best chunk score (highest scoring file first)

        Note:
            Assumes valid inputs (validated at CLI layer). Invalid filter_mode will fail
            naturally on list comprehension.
        """
        # Filter by filter_mode (head/history/all)
        if filter_mode == "head":
            results = [r for r in results if r.is_head]
        elif filter_mode == "history":
            results = [r for r in results if not r.is_head]
        # "all" = no filtering

        grouped = defaultdict(list)

        # Group by file_path and filter by similarity
        # Use SearchResult.score property (returns hybrid_score or vector_score)
        for result in results:
            if result.score >= min_similarity:
                grouped[result.file_path].append(result)

        # Remove files with no chunks after filtering
        filtered_grouped: dict[str, list[Any]] = {k: v for k, v in grouped.items() if v}

        # Sort FILES by best chunk score (file-level ordering only)
        return dict(
            sorted(
                filtered_grouped.items(),
                key=lambda item: max(c.score for c in item[1]),
                reverse=True,
            )
        )
