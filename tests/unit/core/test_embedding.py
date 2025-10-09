"""Unit tests for embedding orchestration helpers."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from gitctx.core.chunker import LanguageAwareChunker
from gitctx.core.embedding import embed_with_cache
from gitctx.core.embedding_cache import EmbeddingCache
from gitctx.core.models import BlobLocation, BlobRecord, CodeChunk
from gitctx.core.protocols import Embedding


@pytest.mark.anyio
class TestEmbedWithCache:
    """Test embed_with_cache orchestration helper."""

    async def test_cache_hit_returns_cached_embeddings(self, tmp_path: Path, monkeypatch):
        """When blob exists in cache, return cached embeddings without API call.

        Given: A blob that has been embedded previously (in cache)
        When: I call embed_with_cache for the same blob
        Then: Cached embeddings are returned without calling the embedder
        """
        # ARRANGE - Create test blob
        blob_location = BlobLocation(
            commit_sha="abc123" * 7,
            file_path="test.py",
            is_head=True,
            author_name="Test",
            author_email="test@example.com",
            commit_date=1234567890,
            commit_message="Test commit",
            is_merge=False,
        )
        blob = BlobRecord(
            sha="test_blob_sha_001",
            content=b"def hello(): pass",
            size=17,
            locations=[blob_location],
        )

        # Create cache with pre-populated embeddings
        cache = EmbeddingCache(cache_dir=tmp_path, model="text-embedding-3-large")
        cached_embeddings = [
            Embedding(
                vector=[0.1] * 3072,
                token_count=10,
                model="text-embedding-3-large",
                cost_usd=0.0000013,
                blob_sha="test_blob_sha_001",
                chunk_index=0,
            )
        ]
        cache.set("test_blob_sha_001", cached_embeddings)

        # Mock chunker and embedder (should NOT be called)
        chunker = Mock(spec=LanguageAwareChunker)
        embedder = AsyncMock()

        # ACT - Call embed_with_cache
        result = await embed_with_cache(
            chunker=chunker, embedder=embedder, cache=cache, blob_record=blob
        )

        # ASSERT - Returns cached embeddings
        assert len(result) == 1
        # Check approximate equality (safetensors uses float32, not exact floats)
        assert all(abs(v - 0.1) < 0.001 for v in result[0].vector)
        assert result[0].blob_sha == "test_blob_sha_001"

        # ASSERT - Chunker and embedder NOT called (cache hit)
        chunker.chunk_file.assert_not_called()
        embedder.embed_chunks.assert_not_called()

    async def test_cache_miss_generates_and_caches_embeddings(self, tmp_path: Path, monkeypatch):
        """When blob not in cache, chunk → embed → cache → return.

        Given: A blob that is NOT in cache
        When: I call embed_with_cache
        Then: Blob is chunked, embedded, stored in cache, and returned
        """
        # ARRANGE - Create test blob
        blob_location = BlobLocation(
            commit_sha="def456" * 7,
            file_path="math.py",
            is_head=True,
            author_name="Test",
            author_email="test@example.com",
            commit_date=1234567890,
            commit_message="Add math",
            is_merge=False,
        )
        blob = BlobRecord(
            sha="test_blob_sha_002",
            content=b"def add(a, b): return a + b",
            size=28,
            locations=[blob_location],
        )

        # Create empty cache
        cache = EmbeddingCache(cache_dir=tmp_path, model="text-embedding-3-large")

        # Mock chunker to return test chunk
        chunker = Mock(spec=LanguageAwareChunker)
        test_chunk = CodeChunk(
            content="def add(a, b): return a + b",
            start_line=1,
            end_line=1,
            token_count=15,
            metadata={"chunk_index": 0, "total_chunks": 1},
        )
        chunker.chunk_file.return_value = [test_chunk]

        # Mock embedder to return test embedding
        embedder = AsyncMock()
        test_embedding = Embedding(
            vector=[0.2] * 3072,
            token_count=15,
            model="text-embedding-3-large",
            cost_usd=0.00000195,
            blob_sha="test_blob_sha_002",
            chunk_index=0,
        )
        embedder.embed_chunks.return_value = [test_embedding]

        # ACT - Call embed_with_cache
        result = await embed_with_cache(
            chunker=chunker, embedder=embedder, cache=cache, blob_record=blob
        )

        # ASSERT - Chunker called with correct language
        chunker.chunk_file.assert_called_once()
        call_args = chunker.chunk_file.call_args
        assert call_args[0][0] == "def add(a, b): return a + b"  # content
        assert call_args[0][1] == "python"  # language detected from .py

        # ASSERT - Embedder called
        embedder.embed_chunks.assert_called_once_with([test_chunk], "test_blob_sha_002")

        # ASSERT - Embeddings returned
        assert len(result) == 1
        assert all(abs(v - 0.2) < 0.001 for v in result[0].vector)
        assert result[0].blob_sha == "test_blob_sha_002"

        # ASSERT - Embeddings stored in cache
        cached = cache.get("test_blob_sha_002")
        assert cached is not None
        assert len(cached) == 1
        assert all(abs(v - 0.2) < 0.001 for v in cached[0].vector)

    async def test_language_detection_from_file_extension(self, tmp_path: Path):
        """Language is detected from file extension in blob location.

        Given: Blobs with different file extensions
        When: I call embed_with_cache
        Then: Correct language is passed to chunker
        """
        # Test data: file extension → expected language
        # (language codes match language_detection.py)
        test_cases = [
            ("main.py", "python"),
            ("app.js", "js"),
            ("app.jsx", "js"),
            ("types.ts", "ts"),
            ("component.tsx", "ts"),
            ("server.go", "go"),
            ("lib.rs", "rust"),
            ("README.md", "markdown"),  # Falls back to markdown
        ]

        cache = EmbeddingCache(cache_dir=tmp_path, model="text-embedding-3-large")

        for file_path, expected_lang in test_cases:
            # ARRANGE - Create blob with specific file extension
            blob_location = BlobLocation(
                commit_sha="abc" * 14,
                file_path=file_path,
                is_head=True,
                author_name="Test",
                author_email="test@example.com",
                commit_date=1234567890,
                commit_message="Test",
                is_merge=False,
            )
            blob = BlobRecord(
                sha=f"test_{file_path}",
                content=b"test content",
                size=12,
                locations=[blob_location],
            )

            # Mock chunker and embedder
            chunker = Mock(spec=LanguageAwareChunker)
            chunker.chunk_file.return_value = [
                CodeChunk(
                    content="test",
                    start_line=1,
                    end_line=1,
                    token_count=1,
                    metadata={"chunk_index": 0, "total_chunks": 1},
                )
            ]
            embedder = AsyncMock()
            embedder.embed_chunks.return_value = [
                Embedding(
                    vector=[0.1] * 3072,
                    token_count=1,
                    model="text-embedding-3-large",
                    cost_usd=0.0000001,
                    blob_sha=f"test_{file_path}",
                    chunk_index=0,
                )
            ]

            # ACT
            await embed_with_cache(
                chunker=chunker, embedder=embedder, cache=cache, blob_record=blob
            )

            # ASSERT - Chunker called with correct language
            call_args = chunker.chunk_file.call_args
            assert call_args[0][1] == expected_lang, (
                f"Expected {expected_lang} for {file_path}, got {call_args[0][1]}"
            )

    async def test_logging_for_cache_hit_and_miss(self, tmp_path: Path, caplog):
        """Cache hits and misses are logged for cost tracking.

        Given: Cache hits and misses
        When: I call embed_with_cache
        Then: Appropriate log messages are generated
        """
        import logging

        caplog.set_level(logging.INFO, logger="gitctx.embeddings")

        cache = EmbeddingCache(cache_dir=tmp_path, model="text-embedding-3-large")

        # ARRANGE - Blob for cache miss
        blob_location_miss = BlobLocation(
            commit_sha="abc" * 14,
            file_path="new.py",
            is_head=True,
            author_name="Test",
            author_email="test@example.com",
            commit_date=1234567890,
            commit_message="Test",
            is_merge=False,
        )
        blob_miss = BlobRecord(
            sha="miss_blob_sha",
            content=b"def new(): pass",
            size=15,
            locations=[blob_location_miss],
        )

        # Mock chunker and embedder for miss
        chunker = Mock(spec=LanguageAwareChunker)
        chunker.chunk_file.return_value = [
            CodeChunk(
                content="def new(): pass",
                start_line=1,
                end_line=1,
                token_count=10,
                metadata={"chunk_index": 0, "total_chunks": 1},
            )
        ]
        embedder = AsyncMock()
        embedder.embed_chunks.return_value = [
            Embedding(
                vector=[0.5] * 3072,
                token_count=10,
                model="text-embedding-3-large",
                cost_usd=0.0000013,
                blob_sha="miss_blob_sha",
                chunk_index=0,
            )
        ]

        # ACT - Cache miss
        caplog.clear()
        await embed_with_cache(
            chunker=chunker, embedder=embedder, cache=cache, blob_record=blob_miss
        )

        # ASSERT - Cache miss logged with cost/tokens
        assert any("Embedded blob" in record.message for record in caplog.records)
        assert any("chunks" in record.message for record in caplog.records)
        assert any("tokens" in record.message for record in caplog.records)
        assert any("$" in record.message for record in caplog.records)  # Cost logged

        # ARRANGE - Blob for cache hit (reuse same blob)
        blob_hit = blob_miss

        # ACT - Cache hit
        caplog.clear()
        await embed_with_cache(
            chunker=chunker, embedder=embedder, cache=cache, blob_record=blob_hit
        )

        # ASSERT - Cache hit logged (blob SHA truncated to 8 chars in log)
        assert any(
            "Cache hit" in record.message and "miss_blo" in record.message
            for record in caplog.records
        )
