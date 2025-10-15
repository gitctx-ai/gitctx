"""Formatter registry for search results.

This module provides the formatter registry and lookup functions for
different output formats (terse, verbose, MCP, etc.).
"""

from __future__ import annotations

from gitctx.formatters.base import ResultFormatter
from gitctx.formatters.mcp import MCPFormatter
from gitctx.formatters.terse import TerseFormatter
from gitctx.formatters.verbose import VerboseFormatter

__all__ = [
    "ResultFormatter",
    "get_formatter",
    "FORMATTERS",
    "TerseFormatter",
    "VerboseFormatter",
    "MCPFormatter",
]

# Formatter registry - will be populated by formatter implementations
# Key: formatter name (e.g., "terse", "verbose", "mcp")
# Value: formatter instance implementing ResultFormatter protocol
FORMATTERS: dict[str, ResultFormatter] = {
    "terse": TerseFormatter(),
    "verbose": VerboseFormatter(),
    "mcp": MCPFormatter(),
}


def get_formatter(name: str) -> ResultFormatter:
    """Get formatter by name.

    Args:
        name: Formatter name (e.g., "terse", "verbose", "mcp")

    Returns:
        Formatter instance implementing ResultFormatter protocol

    Raises:
        ValueError: If formatter not found in registry

    Examples:
        >>> formatter = get_formatter("terse")
        >>> formatter.format(results, console)

        >>> get_formatter("unknown")
        Traceback (most recent call last):
            ...
        ValueError: Unknown formatter: "unknown". Available: terse, verbose, mcp
    """
    if name not in FORMATTERS:
        available = ", ".join(sorted(FORMATTERS.keys())) if FORMATTERS else "(none)"
        raise ValueError(f'Unknown formatter: "{name}". Available: {available}')

    return FORMATTERS[name]
