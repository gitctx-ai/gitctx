"""Shared formatting utilities for indexing output.

Provides consistent formatting across progress reporting, cost estimation,
and pipeline output following TUI_GUIDE.md specifications.
"""


def format_cost(cost: float) -> str:
    """Format cost in USD with 4 decimal places.

    Always uses 4 decimal places to show sub-cent costs accurately.
    Examples: "$0.0001", "$1.2345", "$42.0000"

    Args:
        cost: Cost in USD

    Returns:
        Formatted cost string with dollar sign and 4 decimals
    """
    return f"${cost:.4f}"


def format_number(n: int) -> str:
    """Format integer with thousands separators.

    Examples: "1,234", "1,234,567", "42"

    Args:
        n: Integer to format

    Returns:
        Formatted string with comma separators
    """
    return f"{n:,}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Examples:
    - "8.3s" for 8.3 seconds
    - "1m 23s" for 83 seconds
    - "2m 5s" for 125 seconds

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    SECONDS_PER_MINUTE = 60
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.1f}s"

    minutes = int(seconds // SECONDS_PER_MINUTE)
    remaining_seconds = int(seconds % SECONDS_PER_MINUTE)
    return f"{minutes}m {remaining_seconds}s"
