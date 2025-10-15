"""Base protocol for result formatters.

This module defines the ResultFormatter protocol that all formatters must implement.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rich.console import Console


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

    def format(self, results: list[dict[str, Any]], console: Console) -> None:
        """Format and output search results to console.

        Args:
            results: List of search result dictionaries from vector store
            console: Rich Console instance for formatted output

        Returns:
            None - Results are written directly to console
        """
        ...
