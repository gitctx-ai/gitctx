"""Unit tests for filter_and_group_results function.

Tests validate shared filtering and grouping logic:
- Chunks filtered by similarity threshold (min_similarity parameter, default 0.5)
- Chunks filtered by type (filter_mode: head/history/all, default head)
- Chunks grouped by file_path
- Files sorted by best chunk score
- Chunks within files NOT sorted (formatters decide)
"""

import pytest

from gitctx.formatters.base import filter_and_group_results
from gitctx.indexing.types import SearchResult


@pytest.fixture
def mock_results():
    """Create mock SearchResult objects with varying scores and file paths."""
    return [
        SearchResult(
            chunk_content="content1",
            file_path="file_a.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.95,
        ),
        SearchResult(
            chunk_content="content2",
            file_path="file_a.py",
            distance=0.3,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=10,
            end_line=15,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.60,
        ),
        SearchResult(
            chunk_content="content3",
            file_path="file_b.py",
            distance=0.2,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.85,
        ),
    ]


def test_filter_and_group_groups_chunks_by_path(mock_results):
    """Test that chunks are grouped by file_path."""
    grouped = filter_and_group_results(mock_results)

    assert "file_a.py" in grouped
    assert "file_b.py" in grouped
    assert len(grouped["file_a.py"]) == 2
    assert len(grouped["file_b.py"]) == 1


def test_filter_and_group_does_not_sort_chunks_within_file():
    """Test that chunks within a file remain in original order (NOT sorted)."""
    results = [
        SearchResult(
            chunk_content="low score",
            file_path="test.py",
            distance=0.5,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=10,
            end_line=15,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.5,
        ),
        SearchResult(
            chunk_content="high score",
            file_path="test.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=20,
            end_line=25,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.9,
        ),
        SearchResult(
            chunk_content="medium score",
            file_path="test.py",
            distance=0.3,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=2,
            start_line=30,
            end_line=35,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.7,
        ),
    ]

    grouped = filter_and_group_results(results)

    # Chunks should remain in original order: low (0.5), high (0.9), medium (0.7)
    chunks = grouped["test.py"]
    assert chunks[0].hybrid_score == 0.5
    assert chunks[1].hybrid_score == 0.9
    assert chunks[2].hybrid_score == 0.7


def test_filter_and_group_sorts_files_by_best_chunk_score():
    """Test that files are sorted by their best chunk score (descending)."""
    results = [
        SearchResult(
            chunk_content="file A best",
            file_path="file_a.py",
            distance=0.05,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.95,
        ),
        SearchResult(
            chunk_content="file B best",
            file_path="file_b.py",
            distance=0.15,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.85,
        ),
    ]

    grouped = filter_and_group_results(results)

    # Files should be sorted: file_a.py (0.95) before file_b.py (0.85)
    file_paths = list(grouped.keys())
    assert file_paths[0] == "file_a.py"
    assert file_paths[1] == "file_b.py"


def test_filter_and_group_filters_by_min_similarity():
    """Test that chunks below min_similarity threshold are filtered out."""
    results = [
        SearchResult(
            chunk_content="high score",
            file_path="test.py",
            distance=0.05,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.95,
        ),
        SearchResult(
            chunk_content="medium score",
            file_path="test.py",
            distance=0.4,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=10,
            end_line=15,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.60,
        ),
        SearchResult(
            chunk_content="low score",
            file_path="test.py",
            distance=0.75,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=2,
            start_line=20,
            end_line=25,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.25,
        ),
    ]

    grouped = filter_and_group_results(results, min_similarity=0.5)

    # Only 2 chunks should pass: 0.95 and 0.60 (>= 0.5)
    chunks = grouped["test.py"]
    assert len(chunks) == 2
    assert chunks[0].hybrid_score == 0.95
    assert chunks[1].hybrid_score == 0.60


def test_filter_and_group_removes_empty_files_after_filtering():
    """Test that files with no chunks after filtering are omitted entirely."""
    results = [
        SearchResult(
            chunk_content="low score 1",
            file_path="file_a.py",
            distance=0.6,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.40,
        ),
        SearchResult(
            chunk_content="low score 2",
            file_path="file_a.py",
            distance=0.7,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=10,
            end_line=15,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.30,
        ),
        SearchResult(
            chunk_content="high score",
            file_path="file_b.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.90,
        ),
    ]

    grouped = filter_and_group_results(results, min_similarity=0.5)

    # file_a.py should be completely removed (all chunks < 0.5)
    # file_b.py should remain (has 1 chunk >= 0.5)
    assert "file_a.py" not in grouped
    assert "file_b.py" in grouped
    assert len(grouped["file_b.py"]) == 1


def test_filter_and_group_default_min_similarity_is_0_5():
    """Test that default min_similarity is 0.5."""
    results = [
        SearchResult(
            chunk_content="above threshold",
            file_path="test.py",
            distance=0.4,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.6,
        ),
        SearchResult(
            chunk_content="below threshold",
            file_path="test.py",
            distance=0.6,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=10,
            end_line=15,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.4,
        ),
    ]

    # Call without min_similarity parameter (should default to 0.5)
    grouped = filter_and_group_results(results)

    # Only chunk with score >= 0.5 should remain
    chunks = grouped["test.py"]
    assert len(chunks) == 1
    assert chunks[0].hybrid_score == 0.6


def test_filter_and_group_negative_similarity_allowed():
    """Test that negative similarity values are allowed (range -1.0 to 1.0)."""
    results = [
        SearchResult(
            chunk_content="positive",
            file_path="test.py",
            distance=0.5,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.5,
        ),
        SearchResult(
            chunk_content="zero",
            file_path="test.py",
            distance=1.0,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=1,
            start_line=10,
            end_line=15,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.0,
        ),
        SearchResult(
            chunk_content="negative",
            file_path="test.py",
            distance=1.3,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=2,
            start_line=20,
            end_line=25,
            total_chunks=3,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=-0.3,
        ),
    ]

    # Use min_similarity=-1.0 to allow all scores including negative
    grouped = filter_and_group_results(results, min_similarity=-1.0)

    # All 3 chunks should be included (including negative score)
    chunks = grouped["test.py"]
    assert len(chunks) == 3
    assert chunks[0].hybrid_score == 0.5
    assert chunks[1].hybrid_score == 0.0
    assert chunks[2].hybrid_score == -0.3


def test_filter_and_group_filter_mode_head():
    """Test filter_mode='head' only returns is_head=True chunks."""
    results = [
        SearchResult(
            chunk_content="head chunk",
            file_path="test.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=2,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.9,
        ),
        SearchResult(
            chunk_content="history chunk",
            file_path="test.py",
            distance=0.2,
            commit_sha="b" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="old commit",
            is_head=False,
            is_merge=False,
            hybrid_score=0.8,
        ),
    ]

    grouped = filter_and_group_results(results, filter_mode="head")

    # Only is_head=True chunk should be included
    chunks = grouped["test.py"]
    assert len(chunks) == 1
    assert chunks[0].is_head is True
    assert chunks[0].chunk_content == "head chunk"


def test_filter_and_group_filter_mode_history():
    """Test filter_mode='history' only returns is_head=False chunks."""
    results = [
        SearchResult(
            chunk_content="head chunk",
            file_path="test.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.9,
        ),
        SearchResult(
            chunk_content="history chunk",
            file_path="test.py",
            distance=0.2,
            commit_sha="b" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="old commit",
            is_head=False,
            is_merge=False,
            hybrid_score=0.8,
        ),
    ]

    grouped = filter_and_group_results(results, filter_mode="history")

    # Only is_head=False chunk should be included
    chunks = grouped["test.py"]
    assert len(chunks) == 1
    assert chunks[0].is_head is False
    assert chunks[0].chunk_content == "history chunk"


def test_filter_and_group_filter_mode_all():
    """Test filter_mode='all' returns both is_head=True and is_head=False chunks."""
    results = [
        SearchResult(
            chunk_content="head chunk",
            file_path="test.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.9,
        ),
        SearchResult(
            chunk_content="history chunk",
            file_path="test.py",
            distance=0.2,
            commit_sha="b" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="old commit",
            is_head=False,
            is_merge=False,
            hybrid_score=0.8,
        ),
    ]

    grouped = filter_and_group_results(results, filter_mode="all")

    # Both chunks should be included
    chunks = grouped["test.py"]
    assert len(chunks) == 2
    assert chunks[0].is_head is True
    assert chunks[1].is_head is False


def test_filter_and_group_empty_results():
    """Test that empty results list returns empty dict."""
    grouped = filter_and_group_results([])

    assert grouped == {}


def test_filter_and_group_single_chunk_per_file():
    """Test correct grouping when each file has exactly 1 chunk."""
    results = [
        SearchResult(
            chunk_content="file a",
            file_path="a.py",
            distance=0.1,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="b" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.95,
        ),
        SearchResult(
            chunk_content="file b",
            file_path="b.py",
            distance=0.2,
            commit_sha="a" * 40,
            token_count=10,
            blob_sha="c" * 40,
            chunk_index=0,
            start_line=1,
            end_line=5,
            total_chunks=1,
            language="python",
            author_name="Test",
            author_email="test@test.com",
            commit_date="2025-01-01T00:00:00Z",
            commit_message="test",
            is_head=True,
            is_merge=False,
            hybrid_score=0.85,
        ),
    ]

    grouped = filter_and_group_results(results)

    # 2 files, each with 1 chunk
    assert len(grouped) == 2
    assert len(grouped["a.py"]) == 1
    assert len(grouped["b.py"]) == 1
    # Files sorted by score: a.py (0.95) before b.py (0.85)
    file_paths = list(grouped.keys())
    assert file_paths[0] == "a.py"
    assert file_paths[1] == "b.py"
