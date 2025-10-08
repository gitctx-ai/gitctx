"""Unit tests for core data models.

Following TDD workflow:
1. Write these tests FIRST (they will fail - RED)
2. Then implement models (GREEN)
3. Refactor if needed
"""

from gitctx.core.models import CodeChunk


class TestCodeChunk:
    """Test suite for CodeChunk dataclass."""

    def test_code_chunk_creation_with_all_fields(self):
        """Test creating CodeChunk with all required fields."""
        # ARRANGE & ACT
        chunk = CodeChunk(
            content="def foo():\n    pass",
            start_line=10,
            end_line=11,
            token_count=8,
            metadata={
                "blob_sha": "abc123",
                "chunk_index": 0,
                "language": "python",
            },
        )

        # ASSERT
        assert chunk.content == "def foo():\n    pass"
        assert chunk.start_line == 10
        assert chunk.end_line == 11
        assert chunk.token_count == 8
        assert chunk.metadata["blob_sha"] == "abc123"
        assert chunk.metadata["language"] == "python"

    def test_code_chunk_uses_primitive_types(self):
        """Verify CodeChunk uses only primitive types (FFI-friendly)."""
        # ARRANGE & ACT
        chunk = CodeChunk(
            content="test",
            start_line=1,
            end_line=1,
            token_count=1,
            metadata={},
        )

        # ASSERT - All field types should be primitives
        assert isinstance(chunk.content, str)
        assert isinstance(chunk.start_line, int)
        assert isinstance(chunk.end_line, int)
        assert isinstance(chunk.token_count, int)
        assert isinstance(chunk.metadata, dict)

    def test_code_chunk_with_empty_metadata(self):
        """Test CodeChunk with minimal metadata."""
        # ARRANGE & ACT
        chunk = CodeChunk(
            content="x = 1",
            start_line=1,
            end_line=1,
            token_count=3,
            metadata={},
        )

        # ASSERT
        assert chunk.metadata == {}
        assert chunk.content == "x = 1"
