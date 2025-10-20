"""Base protocol for result formatters.

This module defines the ResultFormatter protocol that all formatters must implement.
"""

from __future__ import annotations

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

    def format(
        self, results: list[dict[str, Any]], console: Console, theme: str = "monokai"
    ) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries from vector store
            console: Rich Console instance for formatted output
            theme: Syntax highlighting theme (default: "monokai")

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
