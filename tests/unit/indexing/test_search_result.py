"""Unit tests for SearchResult dataclass.

Tests validate SearchResult has all 18 required fields with correct types:
- 11 core fields (chunk_content, file_path, distance, etc.)
- 6 git metadata fields (author_name, commit_date, etc.)
- 3 score fields (bm25_score, vector_score, hybrid_score)

All fields use primitive types for FFI compatibility.
"""

from gitctx.indexing.types import SearchResult


def test_search_result_can_be_imported() -> None:
    """Test SearchResult can be imported."""
    assert SearchResult is not None


def test_search_result_creation_with_all_fields() -> None:
    """Test SearchResult can be created with all 18 fields."""
    result = SearchResult(
        # Core fields
        chunk_content="def authenticate(): pass",
        file_path="src/auth.py",
        distance=0.15,
        commit_sha="abc123" * 6 + "ab12",  # 40 chars
        token_count=50,
        blob_sha="def456" * 6 + "de45",  # 40 chars
        chunk_index=0,
        start_line=1,
        end_line=10,
        total_chunks=1,
        language="python",
        # Git metadata fields
        author_name="Alice Developer",
        author_email="alice@example.com",
        commit_date="2025-01-15T10:30:00Z",
        commit_message="feat: add authentication",
        is_head=True,
        is_merge=False,
        # Score fields
        bm25_score=0.85,
        vector_score=0.92,
        hybrid_score=0.88,
    )

    assert result is not None


# Core fields tests
def test_search_result_has_chunk_content_field() -> None:
    """Test SearchResult has chunk_content field (str)."""
    assert hasattr(SearchResult, "__annotations__")
    assert "chunk_content" in SearchResult.__annotations__
    assert SearchResult.__annotations__["chunk_content"] is str


def test_search_result_has_file_path_field() -> None:
    """Test SearchResult has file_path field (str)."""
    assert "file_path" in SearchResult.__annotations__
    assert SearchResult.__annotations__["file_path"] is str


def test_search_result_has_distance_field() -> None:
    """Test SearchResult has distance field (float - cosine distance)."""
    assert "distance" in SearchResult.__annotations__
    assert SearchResult.__annotations__["distance"] is float


def test_search_result_has_commit_sha_field() -> None:
    """Test SearchResult has commit_sha field (str - 40-char hex)."""
    assert "commit_sha" in SearchResult.__annotations__
    assert SearchResult.__annotations__["commit_sha"] is str


def test_search_result_has_token_count_field() -> None:
    """Test SearchResult has token_count field (int)."""
    assert "token_count" in SearchResult.__annotations__
    assert SearchResult.__annotations__["token_count"] is int


def test_search_result_has_blob_sha_field() -> None:
    """Test SearchResult has blob_sha field (str - 40-char hex)."""
    assert "blob_sha" in SearchResult.__annotations__
    assert SearchResult.__annotations__["blob_sha"] is str


def test_search_result_has_chunk_index_field() -> None:
    """Test SearchResult has chunk_index field (int)."""
    assert "chunk_index" in SearchResult.__annotations__
    assert SearchResult.__annotations__["chunk_index"] is int


def test_search_result_has_start_line_field() -> None:
    """Test SearchResult has start_line field (int)."""
    assert "start_line" in SearchResult.__annotations__
    assert SearchResult.__annotations__["start_line"] is int


def test_search_result_has_end_line_field() -> None:
    """Test SearchResult has end_line field (int)."""
    assert "end_line" in SearchResult.__annotations__
    assert SearchResult.__annotations__["end_line"] is int


def test_search_result_has_total_chunks_field() -> None:
    """Test SearchResult has total_chunks field (int)."""
    assert "total_chunks" in SearchResult.__annotations__
    assert SearchResult.__annotations__["total_chunks"] is int


def test_search_result_has_language_field() -> None:
    """Test SearchResult has language field (str)."""
    assert "language" in SearchResult.__annotations__
    assert SearchResult.__annotations__["language"] is str


# Git metadata fields tests
def test_search_result_has_author_name_field() -> None:
    """Test SearchResult has author_name field (str)."""
    assert "author_name" in SearchResult.__annotations__
    assert SearchResult.__annotations__["author_name"] is str


def test_search_result_has_author_email_field() -> None:
    """Test SearchResult has author_email field (str)."""
    assert "author_email" in SearchResult.__annotations__
    assert SearchResult.__annotations__["author_email"] is str


def test_search_result_has_commit_date_field() -> None:
    """Test SearchResult has commit_date field (str - ISO8601)."""
    assert "commit_date" in SearchResult.__annotations__
    assert SearchResult.__annotations__["commit_date"] is str


def test_search_result_has_commit_message_field() -> None:
    """Test SearchResult has commit_message field (str)."""
    assert "commit_message" in SearchResult.__annotations__
    assert SearchResult.__annotations__["commit_message"] is str


def test_search_result_has_is_head_field() -> None:
    """Test SearchResult has is_head field (bool)."""
    assert "is_head" in SearchResult.__annotations__
    assert SearchResult.__annotations__["is_head"] is bool


def test_search_result_has_is_merge_field() -> None:
    """Test SearchResult has is_merge field (bool)."""
    assert "is_merge" in SearchResult.__annotations__
    assert SearchResult.__annotations__["is_merge"] is bool


# Score fields tests
def test_search_result_has_bm25_score_field() -> None:
    """Test SearchResult has bm25_score field (float | None)."""
    assert "bm25_score" in SearchResult.__annotations__
    # Check for Optional[float] or float | None
    assert "float" in str(SearchResult.__annotations__["bm25_score"])
    assert "None" in str(SearchResult.__annotations__["bm25_score"])


def test_search_result_has_vector_score_field() -> None:
    """Test SearchResult has vector_score field (float | None)."""
    assert "vector_score" in SearchResult.__annotations__
    assert "float" in str(SearchResult.__annotations__["vector_score"])
    assert "None" in str(SearchResult.__annotations__["vector_score"])


def test_search_result_has_hybrid_score_field() -> None:
    """Test SearchResult has hybrid_score field (float | None)."""
    assert "hybrid_score" in SearchResult.__annotations__
    assert "float" in str(SearchResult.__annotations__["hybrid_score"])
    assert "None" in str(SearchResult.__annotations__["hybrid_score"])


def test_search_result_score_fields_default_to_none() -> None:
    """Test score fields default to None (backward compatibility)."""
    # Create SearchResult with only required fields (no scores)
    result = SearchResult(
        chunk_content="test",
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
        author_email="test@example.com",
        commit_date="2025-01-01T00:00:00Z",
        commit_message="test",
        is_head=True,
        is_merge=False,
    )

    # Score fields should default to None
    assert result.bm25_score is None
    assert result.vector_score is None
    assert result.hybrid_score is None


def test_search_result_with_all_scores_populated() -> None:
    """Test SearchResult with all score fields populated."""
    result = SearchResult(
        chunk_content="test",
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
        author_email="test@example.com",
        commit_date="2025-01-01T00:00:00Z",
        commit_message="test",
        is_head=True,
        is_merge=False,
        bm25_score=0.85,
        vector_score=0.92,
        hybrid_score=0.88,
    )

    assert result.bm25_score == 0.85
    assert result.vector_score == 0.92
    assert result.hybrid_score == 0.88


def test_search_result_uses_primitive_types_only() -> None:
    """Test SearchResult uses only primitive types (FFI compatibility)."""
    primitive_types = {str, int, float, bool}

    for field_name, field_type in SearchResult.__annotations__.items():
        # Extract base type from Optional/Union
        type_str = str(field_type)

        # Check that base type is primitive
        # For Optional[float], check "float" is in type_str
        assert any(t.__name__ in type_str for t in primitive_types), (
            f"Field '{field_name}' has non-primitive type: {field_type}"
        )


# SearchResult.score property tests (TDD for TASK-0001.4.3.2)
def test_searchresult_score_property_prefers_hybrid() -> None:
    """Test SearchResult.score property returns hybrid_score when available."""
    result = SearchResult(
        chunk_content="test",
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
        author_email="test@example.com",
        commit_date="2025-01-01T00:00:00Z",
        commit_message="test",
        is_head=True,
        is_merge=False,
        hybrid_score=0.9,
        vector_score=0.7,
    )

    # Should prefer hybrid_score when available
    assert result.score == 0.9


def test_searchresult_score_property_fallback_to_vector() -> None:
    """Test SearchResult.score property falls back to vector_score."""
    result = SearchResult(
        chunk_content="test",
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
        author_email="test@example.com",
        commit_date="2025-01-01T00:00:00Z",
        commit_message="test",
        is_head=True,
        is_merge=False,
        hybrid_score=None,
        vector_score=0.8,
    )

    # Should use vector_score when hybrid_score is None
    assert result.score == 0.8


def test_searchresult_score_property_fallback_to_zero() -> None:
    """Test SearchResult.score property falls back to 0.0 when both scores None."""
    result = SearchResult(
        chunk_content="test",
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
        author_email="test@example.com",
        commit_date="2025-01-01T00:00:00Z",
        commit_message="test",
        is_head=True,
        is_merge=False,
        hybrid_score=None,
        vector_score=None,
    )

    # Should return 0.0 when both scores are None
    assert result.score == 0.0
