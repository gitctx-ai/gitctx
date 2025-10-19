"""Unit tests for LanceDB hybrid search functionality.

Tests validate hybrid search implementation using LanceDB's BM25 + vector search with RRF
(Reciprocal Rank Fusion) at K=60. Ensures score breakdown fields are correctly extracted
and populated in SearchResult objects.

Coverage:
- Hybrid query construction (query_type='hybrid')
- RRF reranking (K=60, return_score='all')
- Score extraction (_distance, _score, _relevance_score)
- Score field population (bm25_score, vector_score, hybrid_score)
- Post-filtering compatibility (max_distance still works)
- Parameter validation (limit, filter_head_only)
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from gitctx.indexing.types import SearchResult
from gitctx.storage.lancedb_store import LanceDBStore


@pytest.fixture
def mock_lancedb_table():
    """Create a mock LanceDB table for testing hybrid search queries."""
    table = Mock()

    # Mock schema for dimension validation
    vector_field = Mock()
    vector_field.type.list_size = 3072  # Match expected dimensions
    table.schema.field.return_value = vector_field

    # Create mock query builder that supports method chaining
    query_builder = Mock()
    query_builder.vector.return_value = query_builder
    query_builder.text.return_value = query_builder
    query_builder.limit.return_value = query_builder
    query_builder.rerank.return_value = query_builder
    query_builder.where.return_value = query_builder

    # Default to_list() returns hybrid search results with scores
    query_builder.to_list.return_value = [
        {
            "_distance": 0.15,
            "_score": 1.45,  # BM25 score
            "_relevance_score": 0.0328,  # RRF combined score
            "chunk_content": "class AuthMiddleware",
            "file_path": "src/auth/middleware.py",
            "commit_sha": "a" * 40,
            "token_count": 10,
            "blob_sha": "b" * 40,
            "chunk_index": 0,
            "start_line": 1,
            "end_line": 10,
            "total_chunks": 1,
            "language": "python",
            "author_name": "Alice",
            "author_email": "alice@example.com",
            "commit_date": "2025-01-15T10:30:00Z",
            "commit_message": "feat: add auth",
            "is_head": True,
            "is_merge": False,
        }
    ]

    table.search.return_value = query_builder
    table.count_rows.return_value = 1
    return table


@pytest.fixture
def store_with_hybrid(tmp_path, mock_lancedb_table):
    """Create LanceDBStore with mocked hybrid search table."""
    with patch("gitctx.storage.lancedb_store.lancedb.connect") as mock_connect:
        # Mock database
        mock_db = Mock()
        mock_db.table_names.return_value = ["code_chunks", "index_metadata"]
        mock_db.open_table.return_value = mock_lancedb_table
        mock_connect.return_value = mock_db

        store = LanceDBStore(tmp_path / "lancedb")
        yield store


def test_hybrid_query_construction(store_with_hybrid, mock_lancedb_table):
    """Test that hybrid search uses query_type='hybrid'."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "authentication middleware"

    # Execute hybrid search
    store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify hybrid query construction
    mock_lancedb_table.search.assert_called_once()
    call_args = mock_lancedb_table.search.call_args

    # LanceDB 0.3+ uses query_type parameter
    assert call_args.kwargs.get("query_type") == "hybrid"


def test_rrf_reranker_instantiation(store_with_hybrid):
    """Test RRFReranker created with K=60 and return_score='all'."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "authentication"

    # Patch lancedb.rerankers module since it's imported inside the method
    with patch("lancedb.rerankers.RRFReranker") as mock_rrf_class:
        mock_rrf_instance = Mock()
        mock_rrf_class.return_value = mock_rrf_instance

        # Execute hybrid search
        store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

        # Verify RRF reranker instantiation
        mock_rrf_class.assert_called_once_with(K=60, return_score="all")


def test_score_extraction_from_lancedb_results(store_with_hybrid, mock_lancedb_table):
    """Test score extraction from LanceDB response (_distance, _score, _relevance_score)."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "auth"

    # Set up mock result with all score fields
    mock_lancedb_table.search().to_list.return_value = [
        {
            "_distance": 0.25,
            "_score": 2.13,
            "_relevance_score": 0.0512,
            "chunk_content": "def authenticate()",
            "file_path": "auth.py",
            "commit_sha": "c" * 40,
            "token_count": 5,
            "blob_sha": "d" * 40,
            "chunk_index": 0,
            "start_line": 10,
            "end_line": 15,
            "total_chunks": 1,
            "language": "python",
            "author_name": "Bob",
            "author_email": "bob@example.com",
            "commit_date": "2025-01-16T10:00:00Z",
            "commit_message": "add auth",
            "is_head": True,
            "is_merge": False,
        }
    ]

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify scores extracted correctly
    assert len(results) == 1
    result = results[0]

    # Verify SearchResult type
    assert isinstance(result, SearchResult)

    # Verify score fields populated (exact values checked in later tests)
    assert result.vector_score is not None
    assert result.bm25_score is not None
    assert result.hybrid_score is not None


def test_bm25_score_populated_from_score_field(store_with_hybrid, mock_lancedb_table):
    """Test bm25_score populated from _score field."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "middleware"

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify BM25 score extracted from _score field
    assert results[0].bm25_score == 1.45  # From mock result


def test_vector_score_populated_from_distance(store_with_hybrid, mock_lancedb_table):
    """Test vector_score populated from (1.0 - _distance)."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "auth"

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify vector score = 1.0 - distance
    expected_vector_score = 1.0 - 0.15  # distance from mock result
    assert results[0].vector_score == pytest.approx(expected_vector_score, rel=1e-6)


def test_hybrid_score_populated_from_relevance_score(store_with_hybrid, mock_lancedb_table):
    """Test hybrid_score populated from _relevance_score field."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "middleware"

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify hybrid score from _relevance_score
    assert results[0].hybrid_score == pytest.approx(0.0328, rel=1e-6)


def test_post_filtering_compatibility_with_max_distance(store_with_hybrid, mock_lancedb_table):
    """Test post-filtering by max_distance still works with hybrid search."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "auth"

    # Set up mock results with varying distances
    mock_lancedb_table.search().to_list.return_value = [
        # This result should be filtered out (distance 0.6 > max_distance 0.5)
        {
            "_distance": 0.6,
            "_score": 0.5,
            "_relevance_score": 0.01,
            "chunk_content": "unrelated code",
            "file_path": "other.py",
            "commit_sha": "e" * 40,
            "token_count": 3,
            "blob_sha": "f" * 40,
            "chunk_index": 0,
            "start_line": 1,
            "end_line": 5,
            "total_chunks": 1,
            "language": "python",
            "author_name": "Charlie",
            "author_email": "charlie@example.com",
            "commit_date": "2025-01-17T10:00:00Z",
            "commit_message": "other",
            "is_head": True,
            "is_merge": False,
        },
        # This result should pass (distance 0.2 <= max_distance 0.5)
        {
            "_distance": 0.2,
            "_score": 1.8,
            "_relevance_score": 0.04,
            "chunk_content": "auth code",
            "file_path": "auth.py",
            "commit_sha": "g" * 40,
            "token_count": 5,
            "blob_sha": "h" * 40,
            "chunk_index": 0,
            "start_line": 10,
            "end_line": 15,
            "total_chunks": 1,
            "language": "python",
            "author_name": "Dave",
            "author_email": "dave@example.com",
            "commit_date": "2025-01-18T10:00:00Z",
            "commit_message": "auth",
            "is_head": True,
            "is_merge": False,
        },
    ]

    # Execute search with max_distance filter
    results = store_with_hybrid.search(
        query_vector=query_vector,
        query_text=query_text,
        limit=10,
        max_distance=0.5,
    )

    # Verify only results within max_distance returned
    assert len(results) == 1
    assert results[0].file_path == "auth.py"
    assert results[0].distance == 0.2


def test_limit_parameter_respected_after_reranking(store_with_hybrid, mock_lancedb_table):
    """Test limit parameter respected after RRF reranking."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "auth"

    # Execute search with limit=5
    store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=5)

    # Verify limit() called on query builder
    query_builder = mock_lancedb_table.search.return_value
    query_builder.limit.assert_called_once_with(5)


def test_filter_head_only_works_with_hybrid_search(store_with_hybrid, mock_lancedb_table):
    """Test filter_head_only parameter works with hybrid search."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "middleware"

    # Execute search with filter_head_only=True
    store_with_hybrid.search(
        query_vector=query_vector,
        query_text=query_text,
        limit=10,
        filter_head_only=True,
    )

    # Verify WHERE clause applied for HEAD filtering
    query_builder = mock_lancedb_table.search.return_value
    query_builder.where.assert_called_once_with("is_head = true")


def test_empty_results_handling(store_with_hybrid, mock_lancedb_table):
    """Test empty results handled gracefully."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "nonexistent"

    # Set up empty results
    mock_lancedb_table.search().to_list.return_value = []

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify empty list returned
    assert results == []


def test_score_breakdown_with_real_lancedb_response_structure(
    store_with_hybrid, mock_lancedb_table
):
    """Test score breakdown matches real LanceDB hybrid search response structure."""
    query_vector = np.random.rand(3072).astype(np.float32)
    query_text = "JWT authentication"

    # Realistic LanceDB hybrid search response (validated 2025-10-17)
    mock_lancedb_table.search().to_list.return_value = [
        {
            # Score fields
            "_distance": 0.18,  # Cosine distance (lower = more similar)
            "_score": 2.47,  # BM25 keyword score (higher = better match)
            "_relevance_score": 0.0615,  # RRF combined score (0-1, higher = more relevant)
            # Chunk fields
            "chunk_content": "class JWTAuthMiddleware",
            "file_path": "src/auth/jwt.py",
            "commit_sha": "abc123" * 6 + "ab12",
            "token_count": 15,
            "blob_sha": "def456" * 6 + "de45",
            "chunk_index": 0,
            "start_line": 5,
            "end_line": 20,
            "total_chunks": 2,
            "language": "python",
            # Git metadata
            "author_name": "Alice Developer",
            "author_email": "alice@example.com",
            "commit_date": "2025-01-15T10:30:00Z",
            "commit_message": "feat: add JWT auth middleware",
            "is_head": True,
            "is_merge": False,
        }
    ]

    # Execute search
    results = store_with_hybrid.search(query_vector=query_vector, query_text=query_text, limit=10)

    # Verify score breakdown matches LanceDB structure
    assert len(results) == 1
    result = results[0]

    # Verify SearchResult type
    assert isinstance(result, SearchResult)

    # Verify score fields
    assert result.vector_score == pytest.approx(1.0 - 0.18, rel=1e-6)  # 1.0 - distance
    assert result.bm25_score == pytest.approx(2.47, rel=1e-6)  # _score field
    assert result.hybrid_score == pytest.approx(0.0615, rel=1e-6)  # _relevance_score

    # Verify all other SearchResult fields populated correctly
    assert result.chunk_content == "class JWTAuthMiddleware"
    assert result.file_path == "src/auth/jwt.py"
    assert result.distance == pytest.approx(0.18, rel=1e-6)
    assert result.commit_sha == "abc123" * 6 + "ab12"
    assert result.token_count == 15
    assert result.blob_sha == "def456" * 6 + "de45"
    assert result.chunk_index == 0
    assert result.start_line == 5
    assert result.end_line == 20
    assert result.total_chunks == 2
    assert result.language == "python"
    assert result.author_name == "Alice Developer"
    assert result.author_email == "alice@example.com"
    assert result.commit_date == "2025-01-15T10:30:00Z"
    assert result.commit_message == "feat: add JWT auth middleware"
    assert result.is_head is True
    assert result.is_merge is False


def test_query_text_parameter_required_for_hybrid_search(store_with_hybrid, mock_lancedb_table):
    """Test query_text parameter required for hybrid search."""
    query_vector = np.random.rand(3072).astype(np.float32)

    # Attempt hybrid search without query_text should raise TypeError
    with pytest.raises(TypeError, match=r"missing.*required.*query_text"):
        store_with_hybrid.search(query_vector=query_vector, limit=10)
