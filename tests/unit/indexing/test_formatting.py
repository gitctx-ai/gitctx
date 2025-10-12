"""Unit tests for indexing formatting utilities."""

from gitctx.indexing.formatting import format_cost, format_duration, format_number


class TestFormatCost:
    """Test cost formatting with 4 decimal places."""

    def test_format_small_cost(self):
        """Format sub-cent costs."""
        assert format_cost(0.0001) == "$0.0001"
        assert format_cost(0.0123) == "$0.0123"

    def test_format_typical_cost(self):
        """Format typical costs."""
        assert format_cost(1.2345) == "$1.2345"
        assert format_cost(42.5678) == "$42.5678"

    def test_format_large_cost(self):
        """Format large costs."""
        assert format_cost(1000.0) == "$1000.0000"
        assert format_cost(12345.6789) == "$12345.6789"

    def test_format_zero_cost(self):
        """Format zero cost."""
        assert format_cost(0.0) == "$0.0000"

    def test_format_rounds_correctly(self):
        """Verify rounding to 4 decimals."""
        assert format_cost(1.23456) == "$1.2346"  # Rounds up
        assert format_cost(1.23454) == "$1.2345"  # Rounds down


class TestFormatNumber:
    """Test number formatting with thousands separators."""

    def test_format_small_number(self):
        """Format numbers under 1000."""
        assert format_number(0) == "0"
        assert format_number(42) == "42"
        assert format_number(999) == "999"

    def test_format_thousands(self):
        """Format thousands."""
        assert format_number(1000) == "1,000"
        assert format_number(1234) == "1,234"
        assert format_number(9999) == "9,999"

    def test_format_millions(self):
        """Format millions."""
        assert format_number(1_000_000) == "1,000,000"
        assert format_number(1_234_567) == "1,234,567"

    def test_format_large_number(self):
        """Format very large numbers."""
        assert format_number(1_234_567_890) == "1,234,567,890"


class TestFormatDuration:
    """Test duration formatting."""

    def test_format_short_duration(self):
        """Format durations under 60 seconds."""
        assert format_duration(0.0) == "0.0s"
        assert format_duration(8.3) == "8.3s"
        assert format_duration(42.7) == "42.7s"
        assert format_duration(59.9) == "59.9s"

    def test_format_minutes(self):
        """Format durations in minutes."""
        assert format_duration(60) == "1m 0s"
        assert format_duration(83) == "1m 23s"
        assert format_duration(125) == "2m 5s"

    def test_format_long_duration(self):
        """Format long durations."""
        assert format_duration(600) == "10m 0s"
        assert format_duration(3661) == "61m 1s"

    def test_format_rounds_seconds(self):
        """Verify seconds are rounded to integers in minute format."""
        assert format_duration(62.9) == "1m 2s"  # 62.9s = 1m 2s
        assert format_duration(125.7) == "2m 5s"  # 125.7s = 2m 5s
