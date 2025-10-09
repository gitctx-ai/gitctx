"""Unit tests for EmbeddingCache."""

import pytest

from gitctx.core.embedding_cache import EmbeddingCache
from gitctx.core.protocols import Embedding


class TestEmbeddingCache:
    """Test EmbeddingCache storage and retrieval."""

    def test_cache_miss_returns_none(self, tmp_path):
        """Test cache returns None for missing blob SHA."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")

        # ACT
        result = cache.get("nonexistent_sha")

        # ASSERT
        assert result is None

    def test_cache_hit_returns_embeddings(self, tmp_path):
        """Test cache returns stored embeddings."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=[0.1, 0.2, 0.3],
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="test_sha",
                chunk_index=0,
            )
        ]
        cache.set("test_sha", embeddings)

        # ACT
        result = cache.get("test_sha")

        # ASSERT
        assert result is not None
        assert len(result) == 1
        # Float32 precision - use approximate comparison
        assert len(result[0].vector) == 3
        assert pytest.approx(result[0].vector, rel=1e-5) == [0.1, 0.2, 0.3]
        assert result[0].token_count == 50

    def test_cache_set_creates_file(self, tmp_path):
        """Test cache creates safetensor file."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=[0.1, 0.2],
                token_count=25,
                model="test-model",
                cost_usd=0.00000325,
                blob_sha="abc123",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("abc123", embeddings)

        # ASSERT
        cache_file = tmp_path / "embeddings" / "test-model" / "abc123.safetensors"
        assert cache_file.exists()

    def test_cache_directory_created(self, tmp_path):
        """Test cache creates directory structure."""
        # ARRANGE & ACT
        _ = EmbeddingCache(tmp_path, model="test-model")

        # ASSERT
        cache_dir = tmp_path / "embeddings" / "test-model"
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_cache_key_is_blob_sha(self, tmp_path):
        """Test cache uses blob SHA as filename."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=[0.5],
                token_count=10,
                model="test-model",
                cost_usd=0.0000013,
                blob_sha="unique_sha_456",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("unique_sha_456", embeddings)

        # ASSERT
        cache_file = tmp_path / "embeddings" / "test-model" / "unique_sha_456.safetensors"
        assert cache_file.exists()

    def test_cache_roundtrip(self, tmp_path):
        """Test cache roundtrip: set then get returns same data."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="roundtrip-model")
        original_embeddings = [
            Embedding(
                vector=[0.1, 0.2, 0.3],
                token_count=75,
                model="roundtrip-model",
                cost_usd=0.00000975,
                blob_sha="roundtrip_sha",
                chunk_index=0,
            ),
            Embedding(
                vector=[0.4, 0.5, 0.6],
                token_count=100,
                model="roundtrip-model",
                cost_usd=0.000013,
                blob_sha="roundtrip_sha",
                chunk_index=1,
            ),
        ]

        # ACT
        cache.set("roundtrip_sha", original_embeddings)
        loaded_embeddings = cache.get("roundtrip_sha")

        # ASSERT
        assert loaded_embeddings is not None
        assert len(loaded_embeddings) == 2
        # Float32 precision - use approximate comparison
        assert pytest.approx(loaded_embeddings[0].vector, rel=1e-5) == original_embeddings[0].vector
        assert loaded_embeddings[0].token_count == original_embeddings[0].token_count
        assert pytest.approx(loaded_embeddings[1].vector, rel=1e-5) == original_embeddings[1].vector

    def test_cache_handles_corrupted_files(self, tmp_path):
        """Test cache handles corrupted safetensor files gracefully."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        cache_file = tmp_path / "embeddings" / "test-model" / "corrupted.safetensors"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("CORRUPTED DATA")

        # ACT & ASSERT
        # Should return None or raise specific error
        result = cache.get("corrupted")
        assert result is None or isinstance(result, list)
