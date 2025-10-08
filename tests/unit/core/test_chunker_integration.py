"""Integration tests for chunker pipeline (TASK-0001.2.2.4).

Tests the complete chunking pipeline including configuration integration.
"""

from gitctx.core.chunker import LanguageAwareChunker
from gitctx.core.models import CodeChunk


class TestChunkerPipeline:
    """Test complete chunker pipeline integration."""

    def test_pipeline_python_file(self, code_blob_factory):
        """Pipeline should process Python file end-to-end."""
        # Arrange - Create Python code blob
        content = code_blob_factory("python", target_tokens=250)

        # Act - Full pipeline
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.2)
        chunks = chunker.chunk_file(content, "python", max_tokens=100)

        # Assert - Multiple chunks created
        assert len(chunks) > 1
        assert all(isinstance(c, CodeChunk) for c in chunks)

        # Assert - All chunks within token limit
        assert all(c.token_count <= 100 for c in chunks)

    def test_pipeline_markdown_file(self):
        """Pipeline should process Markdown file end-to-end."""
        # Arrange
        content = "# Heading\n\nParagraph text.\n\n" * 100  # ~400 tokens

        # Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.15)
        chunks = chunker.chunk_file(content, "markdown", max_tokens=150)

        # Assert - Multiple chunks created
        assert len(chunks) > 1
        assert all(isinstance(c, CodeChunk) for c in chunks)

    def test_pipeline_respects_max_tokens(self, code_blob_factory):
        """Pipeline should respect max_tokens constraint."""
        # Arrange
        content = code_blob_factory("python", target_tokens=400)

        # Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.0)
        chunks = chunker.chunk_file(content, "python", max_tokens=100)

        # Assert - All chunks within token limit
        for chunk in chunks:
            assert chunk.token_count <= 100

    def test_pipeline_handles_overlap(self, code_blob_factory):
        """Pipeline should create overlapping chunks."""
        # Arrange
        content = code_blob_factory("python", target_tokens=200)

        # Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.3)
        chunks = chunker.chunk_file(content, "python", max_tokens=100)

        # Assert - At least 2 chunks with overlap
        assert len(chunks) >= 2

        # Assert - Overlap exists (rough check via line numbers)
        for i in range(len(chunks) - 1):
            current_end = chunks[i].end_line
            next_start = chunks[i + 1].start_line
            # With overlap, there should be overlapping line numbers
            # (next chunk starts before or at current chunk's end)
            assert next_start <= current_end + 1  # Allow 1 line gap

    def test_pipeline_metadata_completeness(self):
        """Pipeline should populate all chunk metadata fields."""
        # Arrange
        content = "def foo():\n    pass\n" * 50  # ~200 tokens

        # Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.1)
        chunks = chunker.chunk_file(content, "python", max_tokens=100)

        # Assert - All metadata present
        for chunk in chunks:
            assert isinstance(chunk, CodeChunk)
            assert chunk.content is not None
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
            assert chunk.token_count > 0
            assert chunk.token_count <= 100
            assert chunk.metadata is not None

    def test_pipeline_empty_content(self):
        """Pipeline should handle empty content gracefully."""
        # Arrange
        content = ""

        # Act
        chunker = LanguageAwareChunker()
        chunks = chunker.chunk_file(content, "python", max_tokens=800)

        # Assert - Empty list
        assert len(chunks) == 0

    def test_pipeline_single_chunk(self):
        """Pipeline should handle content that fits in single chunk."""
        # Arrange
        content = "print('hello')\n"  # ~3 tokens

        # Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.2)
        chunks = chunker.chunk_file(content, "python", max_tokens=1000)

        # Assert - Single chunk
        assert len(chunks) == 1
        assert chunks[0].content.strip() == content.strip()
        assert chunks[0].token_count <= 1000
