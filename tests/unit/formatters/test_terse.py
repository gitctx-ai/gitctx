"""Unit tests for TerseFormatter."""

from __future__ import annotations

from io import StringIO

from rich.console import Console


def test_terse_formatter_has_name_and_description() -> None:
    """Test that TerseFormatter has required name and description attributes."""
    from gitctx.formatters.terse import TerseFormatter

    formatter = TerseFormatter()

    assert formatter.name == "terse"
    assert formatter.description is not None
    assert len(formatter.description) > 0


def test_terse_formatter_single_line_format() -> None:
    """Test that TerseFormatter outputs one line per result."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": True,
            "commit_sha": "f9e8d7c1234",  # pragma: allowlist secret
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth support",
        },
        {
            "file_path": "src/login.py",
            "start_line": 23,
            "_distance": 0.76,
            "is_head": False,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "commit_date": 1758268800,  # Unix timestamp for 2025-09-15
            "author_name": "Bob",
            "commit_message": "Initial login",
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    lines = output.getvalue().strip().split("\n")
    assert len(lines) == 2


def test_terse_formatter_includes_file_path() -> None:
    """Test that output includes file path."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "src/auth.py" in output.getvalue()


def test_terse_formatter_includes_line_number() -> None:
    """Test that output includes line number."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert ":45:" in output.getvalue()


def test_terse_formatter_includes_score_two_decimals() -> None:
    """Test that score is formatted with 2 decimal places."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92345,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "0.92" in output.getvalue()
    assert "0.923" not in output.getvalue()


def test_terse_formatter_includes_commit_sha_short() -> None:
    """Test that commit SHA is shortened to 7 characters."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c1234567890",  # pragma: allowlist secret
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "f9e8d7c" in result
    assert "f9e8d7c1234567890" not in result  # pragma: allowlist secret


def test_terse_formatter_includes_commit_date() -> None:
    """Test that commit date is included."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "2025-10-02" in output.getvalue()


def test_terse_formatter_includes_author_name() -> None:
    """Test that author name is included."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "Alice" in output.getvalue()


def test_terse_formatter_includes_commit_message_truncated() -> None:
    """Test that commit message is included."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth support for GitHub and GitLab",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "Add OAuth" in output.getvalue()


def test_terse_formatter_head_marker_modern_terminal() -> None:
    """Test that HEAD marker shows ● on modern terminals."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": True,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "●" in output.getvalue()


def test_terse_formatter_head_marker_legacy_windows() -> None:
    """Test that HEAD marker shows [HEAD] on legacy Windows."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": True,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=True)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert "[HEAD]" in output.getvalue()


def test_terse_formatter_historic_no_marker() -> None:
    """Test that historic commits show no marker (space character)."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "Add OAuth",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should not have ● marker
    assert "●" not in result
    # Should not have [HEAD] marker
    assert "[HEAD]" not in result


def test_terse_formatter_message_truncated_at_50_chars() -> None:
    """Test that commit message is truncated to 50 characters."""
    from gitctx.formatters.terse import TerseFormatter

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_date": 1759388400,  # Unix timestamp for 2025-10-02
            "author_name": "Alice",
            "commit_message": "This is a very long commit message that should be truncated at fifty characters exactly",
        }
    ]

    output = StringIO()
    # Use large width to prevent console from truncating the line
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = TerseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should contain first 50 chars
    assert "This is a very long commit message that should " in result
    # Should not contain full message
    assert "exactly" not in result


def test_terse_formatter_zero_results_empty_output() -> None:
    """Test that zero results produces no output lines."""
    from gitctx.formatters.terse import TerseFormatter

    results: list[dict] = []

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    assert output.getvalue() == ""
