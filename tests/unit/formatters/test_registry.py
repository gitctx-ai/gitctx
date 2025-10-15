"""Unit tests for formatter registry."""

from __future__ import annotations

import pytest

from gitctx.formatters import FORMATTERS, get_formatter


def test_get_formatter_returns_terse_by_default() -> None:
    """Test that get_formatter returns terse formatter for 'terse'."""

    formatter = get_formatter("terse")

    assert formatter.name == "terse"
    assert formatter.description is not None


def test_get_formatter_returns_verbose() -> None:
    """Test that get_formatter returns verbose formatter."""

    formatter = get_formatter("verbose")

    assert formatter.name == "verbose"
    assert formatter.description is not None


def test_get_formatter_returns_mcp() -> None:
    """Test that get_formatter returns MCP formatter."""

    formatter = get_formatter("mcp")

    assert formatter.name == "mcp"
    assert formatter.description is not None


def test_get_formatter_unknown_raises_value_error() -> None:
    """Test that get_formatter raises ValueError for unknown formatter."""

    with pytest.raises(ValueError, match=r'Unknown formatter: "unknown"') as exc_info:
        get_formatter("unknown")

    # Should raise ValueError
    assert "Unknown formatter" in str(exc_info.value)


def test_get_formatter_error_message_lists_available() -> None:
    """Test that error message lists available formatters."""

    with pytest.raises(ValueError, match=r'Unknown formatter: "json".*Available:') as exc_info:
        get_formatter("json")

    error_msg = str(exc_info.value)

    # Should follow format: "Unknown formatter: \"{name}\". Available: {list}"
    assert 'Unknown formatter: "json"' in error_msg
    assert "Available:" in error_msg


def test_formatters_registry_exists() -> None:
    """Test that FORMATTERS registry exists."""

    # Should be a dict
    assert isinstance(FORMATTERS, dict)


def test_formatters_registry_contains_expected_keys() -> None:
    """Test that FORMATTERS registry has terse, verbose, mcp."""

    # Should contain the three expected formatters
    assert "terse" in FORMATTERS
    assert "verbose" in FORMATTERS
    assert "mcp" in FORMATTERS


def test_get_formatter_is_case_sensitive() -> None:
    """Test that formatter names are case-sensitive."""

    # Should not accept capitalized names
    with pytest.raises(ValueError, match=r'Unknown formatter: "Terse"'):
        get_formatter("Terse")

    with pytest.raises(ValueError, match=r'Unknown formatter: "VERBOSE"'):
        get_formatter("VERBOSE")


def test_formatters_have_format_method() -> None:
    """Test that all registered formatters have format method."""

    for name, formatter in FORMATTERS.items():
        assert hasattr(formatter, "format"), f"Formatter {name} missing format method"
        assert callable(formatter.format), f"Formatter {name}.format not callable"


def test_formatters_have_name_and_description() -> None:
    """Test that all registered formatters have name and description."""

    for name, formatter in FORMATTERS.items():
        assert hasattr(formatter, "name"), f"Formatter {name} missing name attribute"
        assert hasattr(formatter, "description"), f"Formatter {name} missing description attribute"
        assert formatter.name == name, f"Formatter name mismatch: {formatter.name} != {name}"
