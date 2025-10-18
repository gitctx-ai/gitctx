"""Unit tests for EmbeddingCache."""

import numpy as np
import pytest
import zstandard as zstd

from gitctx.indexing.types import Embedding
from gitctx.storage.embedding_cache import EmbeddingCache


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
        """Test cache creates compressed safetensor file."""
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
        cache_file = tmp_path / "embeddings" / "test-model" / "abc123.safetensors.zst"
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
        cache_file = tmp_path / "embeddings" / "test-model" / "unique_sha_456.safetensors.zst"
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
        """Test cache handles corrupted compressed files gracefully."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        cache_file = tmp_path / "embeddings" / "test-model" / "corrupted.safetensors.zst"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("CORRUPTED DATA")

        # ACT & ASSERT
        # Should return None on decompression failure
        result = cache.get("corrupted")
        assert result is None


class TestEmbeddingCacheCompression:
    """Test EmbeddingCache compression with zstd."""

    # Tests for set() with compression

    def test_set_writes_compressed_file_extension(self, tmp_path, test_embedding_vector):
        """Test set() writes .safetensors.zst file (not .safetensors)."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="test_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("test_sha", embeddings)

        # ASSERT
        compressed_file = tmp_path / "embeddings" / "test-model" / "test_sha.safetensors.zst"
        assert compressed_file.exists()
        uncompressed_file = tmp_path / "embeddings" / "test-model" / "test_sha.safetensors"
        assert not uncompressed_file.exists()

    def test_set_compresses_safetensors_bytes(self, tmp_path, test_embedding_vector):
        """Test set() compresses safetensors bytes before writing."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=100,
                model="test-model",
                cost_usd=0.000013,
                blob_sha="compress_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("compress_sha", embeddings)

        # ASSERT - File should start with zstd magic bytes
        compressed_file = tmp_path / "embeddings" / "test-model" / "compress_sha.safetensors.zst"
        compressed_bytes = compressed_file.read_bytes()
        # Zstd magic number: 0x28B52FFD (little-endian: 0xFD2FB528)
        assert compressed_bytes[:4] == b"\x28\xb5\x2f\xfd"

    def test_set_preserves_all_embedding_metadata(self, tmp_path, test_embedding_vector):
        """Test set() preserves all embedding metadata in compressed file."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=123,
                model="test-model",
                cost_usd=0.00001599,
                blob_sha="metadata_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("metadata_sha", embeddings)
        loaded = cache.get("metadata_sha")

        # ASSERT
        assert loaded is not None
        assert loaded[0].token_count == 123
        assert pytest.approx(loaded[0].cost_usd, rel=1e-5) == 0.00001599
        assert loaded[0].model == "test-model"
        assert loaded[0].blob_sha == "metadata_sha"

    def test_set_handles_multiple_embeddings(self, tmp_path, test_embedding_vector):
        """Test set() handles multiple embeddings correctly."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="multi_sha",
                chunk_index=0,
            ),
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=75,
                model="test-model",
                cost_usd=0.00000975,
                blob_sha="multi_sha",
                chunk_index=1,
            ),
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=100,
                model="test-model",
                cost_usd=0.000013,
                blob_sha="multi_sha",
                chunk_index=2,
            ),
        ]

        # ACT
        cache.set("multi_sha", embeddings)
        loaded = cache.get("multi_sha")

        # ASSERT
        assert loaded is not None
        assert len(loaded) == 3
        assert loaded[0].chunk_index == 0
        assert loaded[1].chunk_index == 1
        assert loaded[2].chunk_index == 2

    def test_set_handles_empty_embedding_list(self, tmp_path):
        """Test set() handles empty embedding list."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = []

        # ACT
        cache.set("empty_sha", embeddings)
        loaded = cache.get("empty_sha")

        # ASSERT
        assert loaded is not None
        assert len(loaded) == 0

    def test_set_creates_cache_directory_if_missing(self, tmp_path):
        """Test set() creates cache directory if missing."""
        # ARRANGE
        cache_dir = tmp_path / "nonexistent" / "cache"
        cache = EmbeddingCache(cache_dir, model="test-model")
        embeddings = [
            Embedding(
                vector=[0.1, 0.2],
                token_count=25,
                model="test-model",
                cost_usd=0.00000325,
                blob_sha="dir_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("dir_sha", embeddings)

        # ASSERT
        cache_file = cache_dir / "embeddings" / "test-model" / "dir_sha.safetensors.zst"
        assert cache_file.exists()

    def test_set_overwrites_existing_cache_file(self, tmp_path, test_embedding_vector):
        """Test set() overwrites existing cache file."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings_v1 = [
            Embedding(
                vector=[0.1, 0.2, 0.3],
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="overwrite_sha",
                chunk_index=0,
            )
        ]
        embeddings_v2 = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=100,
                model="test-model",
                cost_usd=0.000013,
                blob_sha="overwrite_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("overwrite_sha", embeddings_v1)
        cache.set("overwrite_sha", embeddings_v2)
        loaded = cache.get("overwrite_sha")

        # ASSERT
        assert loaded is not None
        assert loaded[0].token_count == 100  # v2, not v1

    def test_set_file_is_smaller_than_uncompressed(self, tmp_path, test_embedding_vector):
        """Test set() file is smaller than uncompressed safetensors."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        # Create embeddings with multiple chunks (more data to compress)
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=100,
                model="test-model",
                cost_usd=0.000013,
                blob_sha="size_sha",
                chunk_index=i,
            )
            for i in range(10)
        ]

        # ACT
        cache.set("size_sha", embeddings)

        # ASSERT
        compressed_file = tmp_path / "embeddings" / "test-model" / "size_sha.safetensors.zst"
        compressed_size = compressed_file.stat().st_size

        # Decompress and check uncompressed size
        compressed_bytes = compressed_file.read_bytes()
        decompressor = zstd.ZstdDecompressor()
        uncompressed_bytes = decompressor.decompress(compressed_bytes)
        uncompressed_size = len(uncompressed_bytes)

        # Compressed should be smaller
        assert compressed_size < uncompressed_size

    # Tests for get() with decompression

    def test_get_reads_compressed_file_correctly(self, tmp_path, test_embedding_vector):
        """Test get() reads .safetensors.zst file correctly."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="read_sha",
                chunk_index=0,
            )
        ]
        cache.set("read_sha", embeddings)

        # ACT
        loaded = cache.get("read_sha")

        # ASSERT
        assert loaded is not None
        assert len(loaded) == 1

    def test_get_decompresses_bytes_before_loading(self, tmp_path, test_embedding_vector):
        """Test get() decompresses bytes before loading safetensors."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=100,
                model="test-model",
                cost_usd=0.000013,
                blob_sha="decompress_sha",
                chunk_index=0,
            )
        ]
        cache.set("decompress_sha", embeddings)

        # ACT
        loaded = cache.get("decompress_sha")

        # ASSERT
        assert loaded is not None
        # Verify file is compressed (starts with zstd magic)
        compressed_file = tmp_path / "embeddings" / "test-model" / "decompress_sha.safetensors.zst"
        assert compressed_file.read_bytes()[:4] == b"\x28\xb5\x2f\xfd"

    def test_get_reconstructs_embeddings_identically(self, tmp_path, test_embedding_vector):
        """Test get() reconstructs embeddings identically."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        original = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=123,
                model="test-model",
                cost_usd=0.00001599,
                blob_sha="identical_sha",
                chunk_index=0,
            )
        ]
        cache.set("identical_sha", original)

        # ACT
        loaded = cache.get("identical_sha")

        # ASSERT
        assert loaded is not None
        assert len(loaded) == len(original)
        assert loaded[0].token_count == original[0].token_count
        assert loaded[0].model == original[0].model
        assert loaded[0].blob_sha == original[0].blob_sha
        assert loaded[0].chunk_index == original[0].chunk_index

    def test_get_preserves_vector_values(self, tmp_path, test_embedding_vector):
        """Test get() preserves vector values (no precision loss)."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        original_vector = test_embedding_vector().tolist()
        embeddings = [
            Embedding(
                vector=original_vector,
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="vector_sha",
                chunk_index=0,
            )
        ]
        cache.set("vector_sha", embeddings)

        # ACT
        loaded = cache.get("vector_sha")

        # ASSERT
        assert loaded is not None
        # Float32 precision comparison
        np.testing.assert_array_almost_equal(loaded[0].vector, original_vector, decimal=6)

    def test_get_preserves_token_count_metadata(self, tmp_path, test_embedding_vector):
        """Test get() preserves token_count metadata."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=789,
                model="test-model",
                cost_usd=0.00010257,
                blob_sha="tokens_sha",
                chunk_index=0,
            )
        ]
        cache.set("tokens_sha", embeddings)

        # ACT
        loaded = cache.get("tokens_sha")

        # ASSERT
        assert loaded is not None
        assert loaded[0].token_count == 789

    def test_get_preserves_cost_usd_metadata(self, tmp_path, test_embedding_vector):
        """Test get() preserves cost_usd metadata."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=500,
                model="test-model",
                cost_usd=0.0000650,
                blob_sha="cost_sha",
                chunk_index=0,
            )
        ]
        cache.set("cost_sha", embeddings)

        # ACT
        loaded = cache.get("cost_sha")

        # ASSERT
        assert loaded is not None
        assert pytest.approx(loaded[0].cost_usd, rel=1e-5) == 0.0000650

    def test_get_returns_none_for_missing_file(self, tmp_path):
        """Test get() returns None for missing file."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")

        # ACT
        result = cache.get("missing_sha")

        # ASSERT
        assert result is None

    def test_get_returns_none_for_corrupted_compressed_data(self, tmp_path):
        """Test get() returns None for corrupted compressed data."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        corrupted_file = tmp_path / "embeddings" / "test-model" / "corrupted.safetensors.zst"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        corrupted_file.write_bytes(b"CORRUPTED_ZSTD_DATA")

        # ACT
        result = cache.get("corrupted")

        # ASSERT
        assert result is None

    def test_get_logs_warning_on_decompression_failure(self, tmp_path, caplog):
        """Test get() logs warning on decompression failure."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        corrupted_file = tmp_path / "embeddings" / "test-model" / "log_test.safetensors.zst"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        corrupted_file.write_bytes(b"INVALID_DATA")

        # ACT
        result = cache.get("log_test")

        # ASSERT
        assert result is None
        assert "Failed to load cache for log_test" in caplog.text

    def test_get_returns_none_for_old_safetensors_files(self, tmp_path):
        """Test get() returns None for old .safetensors files (backward compat)."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        old_file = tmp_path / "embeddings" / "test-model" / "old_blob.safetensors"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text("OLD_SAFETENSORS_DATA")

        # ACT
        result = cache.get("old_blob")

        # ASSERT
        # Should look for .safetensors.zst, not find it, return None
        assert result is None

    def test_compressed_file_starts_with_zstd_magic_bytes(self, tmp_path, test_embedding_vector):
        """Test compressed file starts with zstd magic bytes (0x28B52FFD)."""
        # ARRANGE
        cache = EmbeddingCache(tmp_path, model="test-model")
        embeddings = [
            Embedding(
                vector=test_embedding_vector().tolist(),
                token_count=50,
                model="test-model",
                cost_usd=0.0000065,
                blob_sha="magic_sha",
                chunk_index=0,
            )
        ]

        # ACT
        cache.set("magic_sha", embeddings)

        # ASSERT
        compressed_file = tmp_path / "embeddings" / "test-model" / "magic_sha.safetensors.zst"
        magic_bytes = compressed_file.read_bytes()[:4]
        assert magic_bytes == b"\x28\xb5\x2f\xfd"
