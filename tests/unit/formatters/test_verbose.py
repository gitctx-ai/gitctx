"""Unit tests for VerboseFormatter."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from gitctx.formatters.verbose import VerboseFormatter


def test_verbose_formatter_has_name_and_description() -> None:
    """Test that VerboseFormatter has required name and description attributes."""

    formatter = VerboseFormatter()

    assert formatter.name == "verbose"
    assert formatter.description is not None
    assert len(formatter.description) > 0


def test_verbose_formatter_multiline_format() -> None:
    """Test that VerboseFormatter outputs multiple lines per result."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "is_head": True,
            "commit_sha": "f9e8d7c1234",  # pragma: allowlist secret
            "commit_message": "Add OAuth support",
            "chunk_content": "def authenticate(user, password):\n    pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    lines = output.getvalue().strip().split("\n")
    # Should have header + metadata + code lines + separator
    assert len(lines) > 3


def test_verbose_formatter_header_with_line_range() -> None:
    """Test that header includes file path with line range."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "src/auth.py:45-52" in result


def test_verbose_formatter_score_in_header() -> None:
    """Test that score appears in header with 2 decimal places."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92345,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "(0.92)" in result
    assert "0.923" not in result


def test_verbose_formatter_head_marker_in_header() -> None:
    """Test that HEAD marker appears in header for HEAD commits."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "is_head": True,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Platform-aware: modern terminals use ●, legacy Windows uses [HEAD]
    assert "●" in result or "[HEAD]" in result


def test_verbose_formatter_commit_sha_in_header() -> None:
    """Test that commit SHA (7 chars) appears in header."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c1234567890",  # pragma: allowlist secret
            "commit_message": "Add OAuth",
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "f9e8d7c" in result
    assert "f9e8d7c1234567890" not in result  # pragma: allowlist secret


def test_verbose_formatter_metadata_line_dimmed() -> None:
    """Test that metadata line contains commit message."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth support for GitHub",
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "Add OAuth support for GitHub" in result


def test_verbose_formatter_syntax_highlighting() -> None:
    """Test that syntax highlighting is applied (ANSI codes present)."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 47,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "def authenticate():\n    pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Rich.Syntax adds ANSI escape codes for highlighting
    assert "def" in result
    assert "authenticate" in result


def test_verbose_formatter_line_numbers_enabled() -> None:
    """Test that line numbers are shown in code block."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 47,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "def authenticate():\n    pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Line numbers should be present (Rich.Syntax adds them)
    assert "45" in result or "46" in result


def test_verbose_formatter_start_line_offset() -> None:
    """Test that line numbers start at correct offset."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 100,
            "end_line": 102,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "def test():\n    pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should show line 100 or nearby (not line 1)
    assert "100" in result or "101" in result


def test_verbose_formatter_theme_monokai() -> None:
    """Test that monokai theme is used (implicit - just verify no crash)."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 47,
            "_distance": 0.92,
            "is_head": False,
            "commit_sha": "f9e8d7c",
            "commit_message": "Add OAuth",
            "chunk_content": "def authenticate():\n    pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Should not crash with monokai theme
    formatter.format(results, console)
    result = output.getvalue()
    assert len(result) > 0


def test_verbose_formatter_language_from_result() -> None:
    """Test that language is taken from result metadata."""

    results = [
        {
            "file_path": "test.js",
            "start_line": 1,
            "end_line": 3,
            "_distance": 0.85,
            "is_head": False,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "commit_message": "Add test",
            "chunk_content": "function test() { return 42; }",
            "language": "javascript",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should process JavaScript syntax (won't crash)
    assert "function" in result


def test_verbose_formatter_language_fallback_markdown() -> None:
    """Test that unknown/missing language falls back to markdown."""

    results = [
        {
            "file_path": "unknown.xyz",
            "start_line": 1,
            "end_line": 3,
            "_distance": 0.75,
            "is_head": False,
            "commit_sha": "def456",  # pragma: allowlist secret
            "commit_message": "Unknown file",
            "chunk_content": "some random content",
            # No language field
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Should not crash with missing language
    formatter.format(results, console)
    result = output.getvalue()
    assert "unknown.xyz" in result
    assert "some random content" in result


def test_verbose_formatter_blank_line_separator() -> None:
    """Test that results are separated by blank lines."""

    results = [
        {
            "file_path": "file1.py",
            "start_line": 1,
            "end_line": 2,
            "_distance": 0.9,
            "is_head": False,
            "commit_sha": "aaa1111",  # pragma: allowlist secret
            "commit_message": "First",
            "chunk_content": "code1",
            "language": "python",
        },
        {
            "file_path": "file2.py",
            "start_line": 10,
            "end_line": 11,
            "_distance": 0.8,
            "is_head": False,
            "commit_sha": "bbb2222",  # pragma: allowlist secret
            "commit_message": "Second",
            "chunk_content": "code2",
            "language": "python",
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should have both results
    assert "file1.py" in result
    assert "file2.py" in result
    # Should have blank line separators (multiple consecutive newlines)
    assert "\n\n" in result


def test_verbose_formatter_custom_theme() -> None:
    """Test that custom theme is used for syntax highlighting."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "is_head": True,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "commit_message": "Test commit",
            "chunk_content": "def test(): pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Test with custom theme
    formatter.format(results, console, theme="github-dark")

    result = output.getvalue()
    # Should contain the result
    assert "test.py" in result
    assert "def test(): pass" in result


def test_verbose_formatter_default_theme() -> None:
    """Test that default theme (monokai) is used when not specified."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "is_head": True,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "commit_message": "Test commit",
            "chunk_content": "def test(): pass",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Call without theme parameter (should use default)
    formatter.format(results, console)

    result = output.getvalue()
    # Should contain the result with default theme
    assert "test.py" in result
    assert "def test(): pass" in result
