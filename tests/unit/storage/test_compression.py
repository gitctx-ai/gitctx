"""Unit tests for safetensors compression with zstd.

This module tests the compression utilities used by EmbeddingCache to reduce
.gitctx/ directory size while maintaining data integrity.
"""

import numpy as np
import pytest
import zstandard as zstd
from safetensors.numpy import load, save

from gitctx.storage.embedding_cache import EmbeddingCache


class TestCompressionUtilities:
    """Test compression and decompression of safetensors data."""

    def test_compress_and_decompress_roundtrip(self, test_embedding_vector):
        """Test that compress → decompress produces identical bytes."""
        # ARRANGE
        tensors = {"chunk_0": test_embedding_vector()}
        metadata = {"model": "test-model", "chunks": "1"}
        original_bytes = save(tensors, metadata=metadata)

        # ACT - Compress
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)

        # ACT - Decompress
        decompressor = zstd.ZstdDecompressor()
        decompressed = decompressor.decompress(compressed)

        # ASSERT
        assert decompressed == original_bytes

    def test_compressed_size_is_smaller(self, test_embedding_vector):
        """Test that compressed size is smaller than original."""
        # ARRANGE
        tensors = {"chunk_0": test_embedding_vector()}
        metadata = {"model": "test-model", "chunks": "1"}
        original_bytes = save(tensors, metadata=metadata)

        # ACT
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)

        # ASSERT
        assert len(compressed) < len(original_bytes)

    def test_decompression_produces_identical_tensors(self, test_embedding_vector):
        """Test that decompression produces identical tensor data."""
        # ARRANGE
        original_vector = test_embedding_vector()
        tensors = {"chunk_0": original_vector}
        metadata = {"model": "test-model", "chunks": "1"}
        original_bytes = save(tensors, metadata=metadata)

        # ACT - Compress and decompress
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)
        decompressor = zstd.ZstdDecompressor()
        decompressed = decompressor.decompress(compressed)

        # Load tensors from decompressed bytes
        loaded_tensors = load(decompressed)

        # ASSERT
        np.testing.assert_array_almost_equal(loaded_tensors["chunk_0"], original_vector, decimal=6)

    def test_compression_level_affects_output_size(self, test_embedding_vector):
        """Test that different compression levels produce different sizes."""
        # ARRANGE
        tensors = {"chunk_0": test_embedding_vector()}
        metadata = {"model": "test-model", "chunks": "1"}
        original_bytes = save(tensors, metadata=metadata)

        # ACT - Compress with different levels
        compressed_level_1 = zstd.ZstdCompressor(level=1).compress(original_bytes)
        compressed_level_3 = zstd.ZstdCompressor(level=3).compress(original_bytes)
        compressed_level_5 = zstd.ZstdCompressor(level=5).compress(original_bytes)

        # ASSERT - Higher levels should compress more (smaller size)
        assert len(compressed_level_3) < len(compressed_level_1)
        assert len(compressed_level_5) <= len(compressed_level_3)

    def test_invalid_compressed_data_raises_error(self):
        """Test that invalid compressed data raises ZstdError."""
        # ARRANGE
        invalid_compressed = b"NOT_COMPRESSED_DATA"
        decompressor = zstd.ZstdDecompressor()

        # ACT & ASSERT
        with pytest.raises(zstd.ZstdError):
            decompressor.decompress(invalid_compressed)

    def test_compression_ratio_achieves_target(self, test_embedding_vector):
        """Test compression ratio achieves significant reduction.

        Note: This test uses deterministic test data (np.linspace) which compresses
        much better (~91% reduction) than real OpenAI embeddings (~8-10% reduction).
        Real embeddings have high entropy; test data has low entropy for reproducibility.
        """
        # ARRANGE - Create test embedding data (multiple chunks)
        tensors = {}
        metadata = {"model": "test-model", "chunks": "10"}

        for i in range(10):
            tensors[f"chunk_{i}"] = test_embedding_vector()

        original_bytes = save(tensors, metadata=metadata)

        # ACT
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)

        # ASSERT - Compression should achieve significant reduction
        # Test data (low entropy): ~91% reduction
        # Real embeddings (high entropy): ~8-10% reduction
        assert len(compressed) < len(original_bytes), (
            "Compressed size should be smaller than original"
        )
        ratio = len(compressed) / len(original_bytes)
        assert ratio < 0.95, f"Compression ratio {ratio:.2%} should be <95% (at least 5% reduction)"

    def test_compression_handles_empty_tensors_gracefully(self):
        """Test compression handles empty tensors gracefully."""
        # ARRANGE
        tensors = {}
        metadata = {"model": "test-model", "chunks": "0"}
        original_bytes = save(tensors, metadata=metadata)

        # ACT
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)
        decompressor = zstd.ZstdDecompressor()
        decompressed = decompressor.decompress(compressed)

        # ASSERT
        assert decompressed == original_bytes
        loaded = load(decompressed)
        assert len(loaded) == 0

    def test_compression_handles_large_tensors(self, test_embedding_vector):
        """Test compression handles large tensors (1000+ vectors)."""
        # ARRANGE - Create large dataset
        tensors = {}
        metadata = {"model": "test-model", "chunks": "1000"}

        for i in range(1000):
            tensors[f"chunk_{i}"] = test_embedding_vector()

        original_bytes = save(tensors, metadata=metadata)

        # ACT
        compressor = zstd.ZstdCompressor(level=EmbeddingCache.COMPRESSION_LEVEL)
        compressed = compressor.compress(original_bytes)
        decompressor = zstd.ZstdDecompressor()
        decompressed = decompressor.decompress(compressed)

        # ASSERT
        assert decompressed == original_bytes
        loaded = load(decompressed)
        assert len(loaded) == 1000


class TestEmbeddingCacheCompressionConstant:
    """Test EmbeddingCache has compression constant configured."""

    def test_compression_level_constant_exists(self):
        """Test that COMPRESSION_LEVEL constant is defined."""
        # ASSERT
        assert hasattr(EmbeddingCache, "COMPRESSION_LEVEL")

    def test_compression_level_is_three(self):
        """Test that COMPRESSION_LEVEL is set to 3 (recommended default)."""
        # ASSERT
        assert EmbeddingCache.COMPRESSION_LEVEL == 3
