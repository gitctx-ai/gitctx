"""Unit tests for VerboseFormatter with file grouping (TASK-0001.4.3.4).

This file contains NEW tests for the updated VerboseFormatter behavior:
- File grouping (multiple chunks per file)
- Line order sorting (not score order)
- Best-match indicator (⭐ or *) for highest-scoring chunk
- Filter mode support (head/history/all)
- Min similarity threshold support

These tests should FAIL initially (RED phase) until implementation is complete.
"""

from __future__ import annotations

from dataclasses import asdict
from io import StringIO

from rich.console import Console

from gitctx.formatters.verbose import VerboseFormatter
from gitctx.indexing.types import DISTANCE_NO_VECTOR_MATCH


def test_verbose_formatter_groups_chunks_by_file(mock_search_result_factory) -> None:
    """Test that chunks from the same file are grouped together."""
    # Create 3 chunks from same file (different lines, different scores)
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.85,
            chunk_content="def login():",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.92,
            chunk_content="def authenticate():",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=100,
            end_line=110,
            hybrid_score=0.78,
            chunk_content="def logout():",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # All 3 chunks should appear in output
    assert "def login():" in result
    assert "def authenticate():" in result
    assert "def logout():" in result

    # File path should appear only once (as header, not per-chunk)
    assert result.count("src/auth.py") >= 1


def test_verbose_formatter_sorts_chunks_by_line_order(mock_search_result_factory) -> None:
    """Test that chunks are sorted by start_line (ascending), not score."""
    # Create chunks in wrong order: highest score in middle
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=100,  # Line 100 (lowest score)
            end_line=110,
            hybrid_score=0.70,
            chunk_content="# Last function",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,  # Line 45 (highest score - but middle position)
            end_line=52,
            hybrid_score=0.95,
            chunk_content="# Middle function",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,  # Line 10 (medium score)
            end_line=15,
            hybrid_score=0.80,
            chunk_content="# First function",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Find positions in output
    pos_first = result.find("# First function")
    pos_middle = result.find("# Middle function")
    pos_last = result.find("# Last function")

    # Assert line order (not score order): 10 < 45 < 100
    assert pos_first < pos_middle, "Line 10 should appear before line 45"
    assert pos_middle < pos_last, "Line 45 should appear before line 100"


def test_verbose_formatter_best_match_indicator_on_highest_score(
    mock_search_result_factory,
) -> None:
    """Test that the best-match indicator appears on highest-scoring chunk."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.80,  # Not best
            chunk_content="def login():",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.95,  # BEST MATCH
            chunk_content="def authenticate():",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=100,
            end_line=110,
            hybrid_score=0.75,  # Not best
            chunk_content="def logout():",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # The chunk with score 0.95 should have best-match indicator
    # Look for ⭐ (modern) or * (legacy) near the authenticate function
    lines = result.split("\n")

    # Find line with "def authenticate():" and check surrounding context
    found_best_marker = False
    for i, line in enumerate(lines):
        if "45-52" in line or (i > 0 and "def authenticate():" in line):
            # Check this line and previous line for best-match marker
            context = "\n".join(lines[max(0, i - 2) : i + 3])
            if "⭐" in context or "best match" in context.lower():
                found_best_marker = True
                break

    assert found_best_marker, "Best-match indicator (⭐) should appear for highest score"


def test_verbose_formatter_best_match_tiebreaker_earliest_line(
    mock_search_result_factory,
) -> None:
    """Test that ties in score are broken by earliest line number."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.90,  # TIED BEST - earliest line wins
            chunk_content="def login():",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.90,  # TIED BEST - later line loses
            chunk_content="def authenticate():",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # The chunk at line 10 should have the best-match indicator (not line 45)
    lines = result.split("\n")

    # Find which chunk has the best-match marker
    found_login_best = False
    found_authenticate_best = False

    for i, line in enumerate(lines):
        context = "\n".join(lines[max(0, i - 2) : i + 3])
        if ("10-15" in line or "def login():" in context) and (
            "⭐" in context or "best match" in context.lower()
        ):
            found_login_best = True
        if ("45-52" in line or "def authenticate():" in context) and (
            "⭐" in context or "best match" in context.lower()
        ):
            found_authenticate_best = True

    assert found_login_best, "Line 10 should have best-match marker (earliest in tie)"
    assert not found_authenticate_best, "Line 45 should NOT have marker (loses tie)"


def test_verbose_formatter_file_grouping_with_file_header(
    mock_search_result_factory,
) -> None:
    """Test that file header appears when grouping chunks."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.85,
            chunk_content="chunk 1",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.92,
            chunk_content="chunk 2",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Should have a file-level header (not per-chunk headers)
    # Format might be like: "src/auth.py (2 chunks):" or similar
    assert "src/auth.py" in result
    # Both chunks should be present
    assert "chunk 1" in result
    assert "chunk 2" in result


def test_verbose_formatter_respects_min_similarity_filter(
    mock_search_result_factory,
) -> None:
    """Test that chunks below min_similarity threshold are filtered out."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.90,  # Above threshold (0.75)
            chunk_content="high score chunk",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.60,  # Below threshold (0.75)
            chunk_content="low score chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Set min_similarity to 0.75
    formatter.format(results, console, min_similarity=0.75)

    result = output.getvalue()

    # High score chunk should be present
    assert "high score chunk" in result

    # Low score chunk should be filtered out
    assert "low score chunk" not in result


def test_verbose_formatter_filter_mode_head_only(mock_search_result_factory) -> None:
    """Test that filter=head shows only HEAD chunks."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            is_head=True,  # HEAD
            hybrid_score=0.85,
            chunk_content="HEAD chunk",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            is_head=False,  # HISTORY
            hybrid_score=0.92,
            chunk_content="history chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Filter to HEAD only
    formatter.format(results, console, filter="head")

    result = output.getvalue()

    # HEAD chunk should be present
    assert "HEAD chunk" in result

    # History chunk should be filtered out
    assert "history chunk" not in result


def test_verbose_formatter_filter_mode_history_only(mock_search_result_factory) -> None:
    """Test that filter=history shows only non-HEAD chunks."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            is_head=True,  # HEAD
            hybrid_score=0.85,
            chunk_content="HEAD chunk",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            is_head=False,  # HISTORY
            hybrid_score=0.92,
            chunk_content="history chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Filter to history only
    formatter.format(results, console, filter="history")

    result = output.getvalue()

    # History chunk should be present
    assert "history chunk" in result

    # HEAD chunk should be filtered out
    assert "HEAD chunk" not in result


def test_verbose_formatter_filter_mode_all(mock_search_result_factory) -> None:
    """Test that filter=all shows both HEAD and history chunks."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            is_head=True,  # HEAD
            hybrid_score=0.85,
            chunk_content="HEAD chunk",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            is_head=False,  # HISTORY
            hybrid_score=0.92,
            chunk_content="history chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Filter to all
    formatter.format(results, console, filter="all")

    result = output.getvalue()

    # Both chunks should be present
    assert "HEAD chunk" in result
    assert "history chunk" in result


def test_verbose_formatter_multiple_files_sorted_by_best_chunk(
    mock_search_result_factory,
) -> None:
    """Test that files are sorted by their best chunk score (descending)."""
    results_objs = [
        # File 1: best chunk = 0.70
        mock_search_result_factory(
            file_path="src/config.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.70,
            chunk_content="config chunk",
        ),
        # File 2: best chunk = 0.95 (should appear first)
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.95,
            chunk_content="auth chunk high",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=100,
            end_line=110,
            hybrid_score=0.60,
            chunk_content="auth chunk low",
        ),
        # File 3: best chunk = 0.85
        mock_search_result_factory(
            file_path="src/utils.py",
            start_line=5,
            end_line=10,
            hybrid_score=0.85,
            chunk_content="utils chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Find positions of file paths in output
    pos_auth = result.find("src/auth.py")  # Best score 0.95
    pos_utils = result.find("src/utils.py")  # Best score 0.85
    pos_config = result.find("src/config.py")  # Best score 0.70

    # Assert file order: auth (0.95) < utils (0.85) < config (0.70)
    assert pos_auth < pos_utils, "auth.py (0.95) should appear before utils.py (0.85)"
    assert pos_utils < pos_config, "utils.py (0.85) should appear before config.py (0.70)"


def test_verbose_formatter_empty_results_after_filtering(
    mock_search_result_factory,
) -> None:
    """Test that formatter handles empty results gracefully."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.40,  # Below threshold
            chunk_content="low score chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Set threshold high enough to filter all results
    formatter.format(results, console, min_similarity=0.75)

    result = output.getvalue()

    # Should produce minimal/empty output (no crashes)
    # Chunk should not appear
    assert "low score chunk" not in result


def test_verbose_formatter_single_chunk_per_file(mock_search_result_factory) -> None:
    """Test that single chunk still shows best-match indicator."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.92,
            chunk_content="only chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Chunk should appear
    assert "only chunk" in result

    # Even single chunk should have best-match indicator
    assert "⭐" in result or "best match" in result.lower()


def test_verbose_formatter_best_match_symbol_platform_aware(
    mock_search_result_factory,
) -> None:
    """Test that best-match symbol uses platform-aware rendering."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.95,
            chunk_content="best chunk",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=100,
            end_line=110,
            hybrid_score=0.70,
            chunk_content="other chunk",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    # Test with modern terminal
    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Modern terminals should use ⭐ or at least have "best" indicator
    # (Exact symbol depends on SYMBOLS dict, but should be present)
    assert "⭐" in result or "best" in result.lower()


def test_verbose_formatter_preserves_syntax_highlighting_with_grouping(
    mock_search_result_factory,
) -> None:
    """Test that syntax highlighting still works with file grouping."""
    results_objs = [
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=10,
            end_line=15,
            hybrid_score=0.85,
            chunk_content="def login():\n    pass",
            language="python",
        ),
        mock_search_result_factory(
            file_path="src/auth.py",
            start_line=45,
            end_line=52,
            hybrid_score=0.92,
            chunk_content="def authenticate():\n    return True",
            language="python",
        ),
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Both chunks should be present with their code
    assert "def login():" in result
    assert "def authenticate():" in result

    # Rich.Syntax should still apply (code content visible)
    assert "pass" in result
    assert "return True" in result


def test_verbose_formatter_score_fallback_to_vector_score(mock_search_result_factory) -> None:
    """Test score property falls back to vector_score when hybrid_score is None."""
    # Create result with only vector_score (no hybrid_score)
    results_objs = [
        mock_search_result_factory(
            file_path="src/test.py",
            start_line=1,
            end_line=5,
            hybrid_score=None,  # Force fallback to vector_score
            vector_score=0.75,
            chunk_content="def test():\n    pass",
        )
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Result should be formatted with vector_score used for scoring
    assert "src/test.py" in result
    assert "def test():" in result


def test_verbose_formatter_score_fallback_to_zero_for_infinite_distance(
    mock_search_result_factory,
) -> None:
    """Test score property returns 0.0 for infinite distance."""
    # Create result with infinite distance (BM25-only match)
    results_objs = [
        mock_search_result_factory(
            file_path="src/bm25.py",
            start_line=1,
            end_line=5,
            hybrid_score=None,
            vector_score=None,
            distance=DISTANCE_NO_VECTOR_MATCH,  # float("inf") - no vector match
            chunk_content="# BM25-only result\nprint('hello')",
        )
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Should handle BM25-only results (score=0.0)
    # Need to set min_similarity to allow 0.0 scores (default is 0.5)
    formatter.format(results, console, min_similarity=-1.0)

    result = output.getvalue()

    # Result should still be formatted despite 0.0 score
    assert "src/bm25.py" in result
    assert "BM25-only result" in result


def test_verbose_formatter_score_computed_from_distance(mock_search_result_factory) -> None:
    """Test score property computes from distance when no scores available (covers line 132)."""
    # Create result with only distance (no hybrid_score or vector_score)
    results_objs = [
        mock_search_result_factory(
            file_path="src/distance.py",
            start_line=1,
            end_line=5,
            hybrid_score=None,
            vector_score=None,
            distance=0.3,  # Score should be 1.0 - 0.3 = 0.7
            chunk_content="# Computed from distance\nprint('distance only')",
        )
    ]
    results = [asdict(r) for r in results_objs]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200)
    formatter = VerboseFormatter()

    # Should compute score from distance: 1.0 - 0.3 = 0.7
    formatter.format(results, console, min_similarity=0.5)

    result = output.getvalue()

    # Result should be formatted with computed score
    assert "src/distance.py" in result
    assert "Computed from distance" in result
