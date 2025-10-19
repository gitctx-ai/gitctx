"""Tests for formatter utility functions."""

from gitctx.formatters.utils import format_commit_date


def test_format_commit_date_iso8601_string() -> None:
    """Test formatting ISO 8601 date string."""
    result = format_commit_date("2025-01-15T10:30:00Z")
    assert result == "2025-01-15"


def test_format_commit_date_iso8601_with_microseconds() -> None:
    """Test formatting ISO 8601 date string with microseconds."""
    result = format_commit_date("2025-10-19T12:47:15.123456Z")
    assert result == "2025-10-19"


def test_format_commit_date_unix_timestamp_int() -> None:
    """Test formatting Unix timestamp (int)."""
    # 2025-01-15 10:30:00 UTC
    result = format_commit_date(1736940600)
    assert result == "2025-01-15"


def test_format_commit_date_unix_timestamp_float() -> None:
    """Test formatting Unix timestamp (float)."""
    # 2025-01-15 10:30:00.5 UTC
    result = format_commit_date(1736940600.5)
    assert result == "2025-01-15"
