"""Unit tests for LanguageAwareChunker.

Following TDD workflow:
1. Write these tests FIRST (they will fail - RED)
2. Then implement chunker.py (GREEN)
3. Refactor if needed
"""

import random

import pytest
import tiktoken

from gitctx.indexing.chunker import LanguageAwareChunker, create_chunker


class TestLanguageAwareChunkerInitialization:
    """Test chunker initialization."""

    def test_init_default_overlap(self, isolated_env):
        """Chunker initializes with default 20% overlap."""
        # Arrange & Act
        chunker = LanguageAwareChunker()

        # Assert
        assert chunker.chunk_overlap_ratio == 0.2
        assert chunker.encoder is not None

    def test_init_custom_overlap(self, isolated_env):
        """Chunker initializes with custom overlap ratio."""
        # Arrange & Act
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.3)

        # Assert
        assert chunker.chunk_overlap_ratio == 0.3


class TestTokenCounting:
    """Test token counting with tiktoken."""

    def test_count_tokens_matches_tiktoken(self, isolated_env):
        """Verify token counting matches tiktoken directly."""
        # Arrange
        chunker = LanguageAwareChunker()
        text = "def foo():\n    pass"

        # Act
        token_count = chunker.count_tokens(text)

        # Assert
        encoder = tiktoken.get_encoding("cl100k_base")
        expected = len(encoder.encode(text))
        assert token_count == expected

    def test_count_tokens_empty_string(self, isolated_env):
        """Empty string has zero tokens."""
        # Arrange
        chunker = LanguageAwareChunker()

        # Act
        token_count = chunker.count_tokens("")

        # Assert
        assert token_count == 0


class TestChunkFile:
    """Test chunk_file method."""

    def test_chunk_empty_content_returns_empty_list(self, isolated_env):
        """Empty content returns empty list."""
        # Arrange
        chunker = LanguageAwareChunker()

        # Act
        chunks = chunker.chunk_file("", "python", max_tokens=800)

        # Assert
        assert chunks == []

    def test_chunk_small_content_single_chunk(self, isolated_env):
        """Content below max_tokens returns single chunk."""
        # Arrange
        chunker = LanguageAwareChunker()
        content = "def foo():\n    pass\n"

        # Act
        chunks = chunker.chunk_file(content, "python", max_tokens=800)

        # Assert
        assert len(chunks) == 1
        # LangChain may strip trailing whitespace - verify content is preserved
        assert chunks[0].content.strip() == content.strip()
        assert chunks[0].start_line == 1
        assert chunks[0].token_count <= 800

    def test_chunk_metadata_fields(self, isolated_env):
        """Chunk metadata includes required fields."""
        # Arrange
        chunker = LanguageAwareChunker()
        content = "def foo():\n    pass\n"

        # Act
        chunks = chunker.chunk_file(content, "python", max_tokens=800)

        # Assert
        assert len(chunks) == 1
        chunk = chunks[0]
        assert "chunk_index" in chunk.metadata
        assert "language" in chunk.metadata
        assert "max_tokens" in chunk.metadata
        assert "overlap_ratio" in chunk.metadata
        assert chunk.metadata["language"] == "python"


class TestChunkerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_character_content(self, isolated_env):
        """Handle single character gracefully."""
        # Arrange
        chunker = LanguageAwareChunker()

        # Act
        chunks = chunker.chunk_file("x", "python", max_tokens=800)

        # Assert
        assert len(chunks) == 1
        assert chunks[0].content == "x"

    def test_content_only_newlines(self, isolated_env):
        """Handle content with only newlines."""
        # Arrange
        chunker = LanguageAwareChunker()

        # Act
        chunks = chunker.chunk_file("\n\n\n", "python", max_tokens=800)

        # Assert
        # LangChain may return empty list or single chunk for whitespace-only
        assert isinstance(chunks, list)

    def test_zero_overlap_ratio(self, isolated_env):
        """Handle zero overlap (no overlap between chunks)."""
        # Arrange
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.0)

        # Act
        chunks = chunker.chunk_file("word " * 1000, "python", max_tokens=100)

        # Assert
        assert all(chunk.metadata["overlap_ratio"] == 0.0 for chunk in chunks)

    def test_maximum_overlap_ratio(self, isolated_env):
        """Handle maximum overlap (50%)."""
        # Arrange
        chunker = LanguageAwareChunker(chunk_overlap_ratio=0.5)

        # Act
        chunks = chunker.chunk_file("word " * 1000, "python", max_tokens=100)

        # Assert
        assert all(chunk.metadata["overlap_ratio"] == 0.5 for chunk in chunks)

    def test_unicode_content(self, isolated_env):
        """Handle Unicode characters correctly."""
        # Arrange
        chunker = LanguageAwareChunker()
        content = "Hello 世界 🌍\ndef foo():\n    pass"

        # Act
        chunks = chunker.chunk_file(content, "python", max_tokens=800)

        # Assert
        assert len(chunks) >= 1
        # Verify no corruption
        joined = "".join(chunk.content for chunk in chunks)
        assert "世界" in joined
        assert "🌍" in joined

    @pytest.mark.parametrize(
        "language",
        ["python", "js", "go", "rust", "java", "unknown_language", "markdown"],
    )
    def test_multiple_languages(self, isolated_env, language):
        """Chunker handles multiple languages without errors."""
        # Arrange
        chunker = LanguageAwareChunker()
        content = "function test() {\n  return 42;\n}\n" * 10

        # Act
        chunks = chunker.chunk_file(content, language, max_tokens=800)

        # Assert
        assert len(chunks) >= 1
        assert all(chunk.metadata["language"] == language for chunk in chunks)


class TestTokenRatioValidation:
    """Validate token ratio assumptions."""

    def test_chunk_token_limit_compliance(self, isolated_env):
        """Verify all chunks respect token limit with 10% tolerance."""
        # Arrange
        random.seed(42)  # Deterministic
        chunker = LanguageAwareChunker()
        max_tokens = 800
        tolerance = 1.1  # 10% over allowed

        # Generate 100 random code samples
        samples = []
        for i in range(100):
            # Random Python-like code
            lines = [
                f"def func{i}_{j}():\n    return {j}\n" for j in range(random.randint(10, 200))
            ]
            samples.append("".join(lines))

        # Act - chunk all samples
        all_chunks = []
        for sample in samples:
            chunks = chunker.chunk_file(sample, "python", max_tokens=max_tokens)
            all_chunks.extend(chunks)

        # Assert - all chunks within limit
        max_token_count = max(chunk.token_count for chunk in all_chunks)
        assert max_token_count <= max_tokens * tolerance, (
            f"Chunk exceeded tolerance: {max_token_count} tokens "
            f"(limit: {max_tokens}, tolerance: {max_tokens * tolerance})"
        )

        # Record actual chars-per-token ratio for documentation
        total_chars = sum(len(chunk.content) for chunk in all_chunks)
        total_tokens = sum(chunk.token_count for chunk in all_chunks)
        actual_ratio = total_chars / total_tokens if total_tokens > 0 else 0

        # Document findings
        print("\nToken ratio validation results:")
        print(f"  Total chunks: {len(all_chunks)}")
        print(f"  Max token count: {max_token_count} (limit: {max_tokens})")
        print(f"  Actual chars-per-token: {actual_ratio:.2f}")
        print("  Assumed chars-per-token: 2.5")
        assert actual_ratio >= 2.5, (
            f"2.5 assumption not conservative enough! Actual: {actual_ratio:.2f}"
        )


class TestFactoryFunction:
    """Test create_chunker factory."""

    def test_factory_creates_chunker(self, isolated_env):
        """Factory returns LanguageAwareChunker instance."""
        # Act
        chunker = create_chunker()

        # Assert
        assert isinstance(chunker, LanguageAwareChunker)
        assert chunker.chunk_overlap_ratio == 0.2

    def test_factory_custom_overlap(self, isolated_env):
        """Factory accepts custom overlap ratio."""
        # Act
        chunker = create_chunker(chunk_overlap_ratio=0.3)

        # Assert
        assert chunker.chunk_overlap_ratio == 0.3
