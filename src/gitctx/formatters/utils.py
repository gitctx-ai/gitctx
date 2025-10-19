"""Shared utility functions for formatters."""

from __future__ import annotations

from datetime import datetime


def format_commit_date(commit_date: str | int | float) -> str:
    """Convert commit date (ISO8601 or timestamp) to YYYY-MM-DD.

    Handles both ISO 8601 string format and Unix timestamp (int/float).
    This is a common operation across formatters to display commit dates
    in a consistent, human-readable format.

    Args:
        commit_date: Either an ISO 8601 string ("2025-01-15T10:30:00Z")
                    or Unix timestamp (int or float)

    Returns:
        Formatted date string in YYYY-MM-DD format

    Examples:
        >>> format_commit_date("2025-01-15T10:30:00Z")
        '2025-01-15'
        >>> format_commit_date(1736940600)
        '2025-01-15'
    """
    if isinstance(commit_date, str):
        # ISO 8601 string format - replace Z with timezone
        dt = datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    # Unix timestamp (int or float)
    return datetime.fromtimestamp(commit_date).strftime("%Y-%m-%d")
