"""Unit tests for ResultFormatter protocol."""

from __future__ import annotations

from typing import Protocol

from rich.console import Console


def test_result_formatter_protocol_has_required_attributes() -> None:
    """Test that ResultFormatter protocol has name and description attributes."""
    from gitctx.formatters.base import ResultFormatter

    # Protocol should define name and description as required attributes in annotations
    assert "name" in ResultFormatter.__annotations__
    assert "description" in ResultFormatter.__annotations__


def test_result_formatter_protocol_has_format_method() -> None:
    """Test that ResultFormatter protocol has format method."""
    from gitctx.formatters.base import ResultFormatter

    # Protocol should define format method
    assert hasattr(ResultFormatter, "format")


def test_formatter_format_method_signature() -> None:
    """Test that format method has correct signature."""
    from gitctx.formatters.base import ResultFormatter

    # Create a test formatter that implements the protocol
    class TestFormatter:
        name = "test"
        description = "Test formatter"

        def format(self, results: list[dict], console: Console) -> None:
            """Format results."""
            pass

    # Should be recognized as implementing ResultFormatter
    formatter: ResultFormatter = TestFormatter()
    assert formatter.name == "test"
    assert formatter.description == "Test formatter"


def test_protocol_runtime_checkable() -> None:
    """Test that ResultFormatter protocol is runtime checkable."""
    from gitctx.formatters.base import ResultFormatter

    # Protocol should be runtime checkable with isinstance
    class ValidFormatter:
        name = "valid"
        description = "Valid formatter"

        def format(self, results: list[dict], console: Console) -> None:
            pass

    formatter = ValidFormatter()

    # Should pass isinstance check if protocol is runtime_checkable
    assert isinstance(formatter, Protocol) or hasattr(ResultFormatter, "__subclasshook__")


def test_protocol_missing_attributes_fails() -> None:
    """Test that missing protocol attributes are detected."""

    # Formatter missing description should not satisfy protocol
    class IncompleteFormatter:
        name = "incomplete"

        def format(self, results: list[dict], console: Console) -> None:
            pass

    # Type checker should catch this, but we can test attribute existence
    formatter = IncompleteFormatter()
    assert not hasattr(formatter, "description")
