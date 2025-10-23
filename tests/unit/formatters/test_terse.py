"""Unit tests for TerseFormatter with file grouping and score sorting."""

from __future__ import annotations

import re
from io import StringIO

from rich.console import Console

from gitctx.formatters.terse import TerseFormatter


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


def test_terse_shows_file_header_with_chunk_count(mock_search_result_factory) -> None:
    """Test that TerseFormatter shows file header with chunk count."""
    results = [
        mock_search_result_factory(file_path="src/auth.py", start_line=10, hybrid_score=0.95),
        mock_search_result_factory(file_path="src/auth.py", start_line=20, hybrid_score=0.85),
        mock_search_result_factory(file_path="src/auth.py", start_line=30, hybrid_score=0.75),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    assert "src/auth.py (3 chunks):" in result


def test_terse_singular_chunk_count(mock_search_result_factory) -> None:
    """Test that singular 'chunk' is used for single result."""
    results = [
        mock_search_result_factory(file_path="src/login.py", start_line=42, hybrid_score=0.87)
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    assert "src/login.py (1 chunk):" in result
    assert "(1 chunks)" not in result  # Should not use plural


def test_terse_shows_one_line_per_chunk(mock_search_result_factory) -> None:
    """Test that TerseFormatter shows one line per chunk (not just best)."""
    results = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            hybrid_score=0.95,
            chunk_content="class AuthMiddleware:",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=42,
            hybrid_score=0.87,
            chunk_content="def process_request(self):",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=103,
            hybrid_score=0.75,
            chunk_content="def validate_token(self):",
        ),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Should have 3 chunk lines (one per chunk)
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]
    assert len(chunk_lines) == 3


def test_terse_chunk_line_format(mock_search_result_factory) -> None:
    """Test that chunk line follows format: :LINE_NUM  SCORE  PREVIEW."""
    results = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            hybrid_score=0.95,
            chunk_content="class AuthMiddleware:",
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Should match format: :LINE_NUM  SCORE  PREVIEW
    assert re.search(r":\d+\s+\d+\.\d+\s+.+", result)
    # Specific check
    assert ":45  0.95  class AuthMiddleware:" in result


def test_terse_filters_by_score_threshold(mock_search_result_factory) -> None:
    """Test that chunks below min_similarity are filtered out."""
    results = [
        mock_search_result_factory(file_path="src/auth.py", start_line=10, hybrid_score=0.95),
        mock_search_result_factory(file_path="src/auth.py", start_line=20, hybrid_score=0.60),
        mock_search_result_factory(file_path="src/auth.py", start_line=30, hybrid_score=0.25),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Only 2 chunks should be shown (>= 0.5)
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]
    assert len(chunk_lines) == 2
    assert ":10  0.95" in result
    assert ":20  0.60" in result
    assert ":30  0.25" not in result  # Below threshold


def test_terse_chunks_sorted_by_score_descending(mock_search_result_factory) -> None:
    """Test that chunks are sorted by score descending (best first)."""
    results = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=30,
            hybrid_score=0.70,
            chunk_content="third",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            hybrid_score=0.95,
            chunk_content="first",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=20,
            hybrid_score=0.50,
            chunk_content="fourth",
        ),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]

    # Extract scores in order
    scores = [float(re.search(r"(\d+\.\d+)", line).group(1)) for line in chunk_lines]
    assert scores == [0.95, 0.70, 0.50]  # Descending order


def test_terse_tie_breaking_with_equal_scores(mock_search_result_factory) -> None:
    """Test that equal scores are broken by line number ascending."""
    results = [
        mock_search_result_factory(file_path="src/auth.py", start_line=30, hybrid_score=0.80),
        mock_search_result_factory(file_path="src/auth.py", start_line=10, hybrid_score=0.80),
        mock_search_result_factory(file_path="src/auth.py", start_line=20, hybrid_score=0.80),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]

    # Extract line numbers in order
    line_nums = [int(re.search(r":(\d+)", line).group(1)) for line in chunk_lines]
    assert line_nums == [10, 20, 30]  # Line ascending for same score


def test_terse_tie_breaking_with_equal_scores_and_lines(
    mock_search_result_factory,
) -> None:
    """Test that equal scores AND lines are broken by content lexicographically."""
    results = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            hybrid_score=0.80,
            chunk_content="ccc",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            hybrid_score=0.80,
            chunk_content="aaa",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            hybrid_score=0.80,
            chunk_content="bbb",
        ),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]

    # Extract content previews in order
    previews = [line.split("  ")[-1].strip() for line in chunk_lines]
    assert previews == ["aaa", "bbb", "ccc"]  # Lexicographic order


def test_terse_file_removed_when_no_chunks_pass_threshold(
    mock_search_result_factory,
) -> None:
    """Test that files with all chunks below threshold are omitted entirely."""
    results = [
        mock_search_result_factory(file_path="src/auth.py", start_line=10, hybrid_score=0.25),
        mock_search_result_factory(file_path="src/auth.py", start_line=20, hybrid_score=0.15),
        mock_search_result_factory(file_path="src/login.py", start_line=5, hybrid_score=0.95),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # src/auth.py should not appear (all chunks below 0.5)
    assert "src/auth.py" not in result
    # src/login.py should appear
    assert "src/login.py" in result


def test_terse_handles_empty_content(mock_search_result_factory) -> None:
    """Test that empty content shows [empty chunk]."""
    results = [
        mock_search_result_factory(
            file_path="src/test.py", start_line=1, hybrid_score=0.90, chunk_content=""
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    assert "[empty chunk]" in result


def test_terse_handles_whitespace_only_content(mock_search_result_factory) -> None:
    """Test that whitespace-only content shows [empty chunk]."""
    results = [
        mock_search_result_factory(
            file_path="src/test.py",
            start_line=1,
            hybrid_score=0.90,
            chunk_content="   \n\t  ",
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    assert "[empty chunk]" in result


def test_terse_strips_leading_whitespace_from_preview(
    mock_search_result_factory,
) -> None:
    """Test that leading whitespace is stripped from preview."""
    results = [
        mock_search_result_factory(
            file_path="src/test.py",
            start_line=42,
            hybrid_score=0.90,
            chunk_content="    def foo():",
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Should show "def foo():" not "    def foo():"
    assert "  def foo():" in result
    # Should not have 4 leading spaces in preview
    lines = [line for line in result.split("\n") if ":42" in line]
    assert len(lines) == 1
    # Extract preview part (after score)
    preview = lines[0].split("0.90")[-1].strip()
    assert preview == "def foo():"


def test_terse_truncates_preview_at_80_chars(mock_search_result_factory) -> None:
    """Test that preview is truncated to 80 characters with ellipsis."""
    long_content = "x" * 100  # 100 character line

    results = [
        mock_search_result_factory(
            file_path="src/test.py",
            start_line=1,
            hybrid_score=0.90,
            chunk_content=long_content,
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Should have 80 x's + "..."
    assert ("x" * 80 + "...") in result
    # Should not have all 100 x's
    assert ("x" * 100) not in result


def test_terse_preview_shows_first_line_only(mock_search_result_factory) -> None:
    """Test that preview shows only first line of multiline content."""
    multiline_content = "first line\nsecond line\nthird line"

    results = [
        mock_search_result_factory(
            file_path="src/test.py",
            start_line=10,
            hybrid_score=0.90,
            chunk_content=multiline_content,
        )
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    assert "first line" in result
    assert "second line" not in result
    assert "third line" not in result


def test_terse_respects_filter_head_mode(mock_search_result_factory) -> None:
    """Test that filter='head' shows only HEAD chunks."""
    results = [
        mock_search_result_factory(
            file_path="src/test.py", start_line=10, hybrid_score=0.95, is_head=True
        ),
        mock_search_result_factory(
            file_path="src/test.py", start_line=20, hybrid_score=0.85, is_head=False
        ),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="head")

    result = strip_ansi(output.getvalue())
    # Only 1 chunk (the HEAD one)
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]
    assert len(chunk_lines) == 1
    assert ":10  0.95" in result
    assert ":20" not in result


def test_terse_respects_filter_history_mode(mock_search_result_factory) -> None:
    """Test that filter='history' shows only historical chunks."""
    results = [
        mock_search_result_factory(
            file_path="src/test.py", start_line=10, hybrid_score=0.95, is_head=True
        ),
        mock_search_result_factory(
            file_path="src/test.py", start_line=20, hybrid_score=0.85, is_head=False
        ),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="history")

    result = strip_ansi(output.getvalue())
    # Only 1 chunk (the historical one)
    chunk_lines = [line for line in result.split("\n") if line.strip().startswith(":")]
    assert len(chunk_lines) == 1
    assert ":20  0.85" in result
    assert ":10" not in result


def test_terse_multiple_files_sorted_by_best_chunk_score(
    mock_search_result_factory,
) -> None:
    """Test that multiple files are sorted by their best chunk's score."""
    results = [
        # File A: best score 0.70
        mock_search_result_factory(file_path="src/a.py", start_line=10, hybrid_score=0.70),
        mock_search_result_factory(file_path="src/a.py", start_line=20, hybrid_score=0.60),
        # File B: best score 0.95
        mock_search_result_factory(file_path="src/b.py", start_line=10, hybrid_score=0.95),
        # File C: best score 0.80
        mock_search_result_factory(file_path="src/c.py", start_line=10, hybrid_score=0.80),
    ]

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = strip_ansi(output.getvalue())
    # Extract file headers in order
    file_headers = re.findall(r"(src/\w+\.py) \(\d+ chunks?\):", result)
    assert file_headers == ["src/b.py", "src/c.py", "src/a.py"]  # By best score


def test_terse_zero_results_produces_no_output(mock_search_result_factory) -> None:
    """Test that zero results produces no output."""
    results = []

    output = StringIO()
    console = Console(file=output, width=200, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console, min_similarity=0.5, filter="all")

    result = output.getvalue()
    assert result.strip() == ""


def test_format_preview_handles_only_newlines() -> None:
    """Test _format_preview with content that's only newlines after first line."""
    formatter = TerseFormatter()

    # Content with just a newline character on first line
    result = formatter._format_preview("\n")
    assert result == "[empty chunk]"


def test_format_preview_handles_long_line_boundary() -> None:
    """Test _format_preview truncation at exactly 80 chars."""
    formatter = TerseFormatter()

    # Exactly 80 chars - should NOT truncate
    content_80 = "x" * 80
    result = formatter._format_preview(content_80)
    assert result == content_80
    assert "..." not in result

    # 81 chars - should truncate
    content_81 = "x" * 81
    result = formatter._format_preview(content_81)
    assert result == "x" * 80 + "..."
    assert len(result) == 83  # 80 + "..."
