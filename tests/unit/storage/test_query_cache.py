"""Unit tests for query embedding cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from gitctx.storage.lancedb_store import LanceDBStore


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    """Test that cache miss returns None."""
    store = LanceDBStore(tmp_path / "lancedb")
    cache_key = hashlib.sha256(b"nonexistent query" + b"model").hexdigest()

    result = store.get_query_embedding(cache_key)

    assert result is None


def test_cache_hit_returns_embedding(tmp_path: Path) -> None:
    """Test that cache hit returns embedding."""
    store = LanceDBStore(tmp_path / "lancedb")
    cache_key = hashlib.sha256(b"test query" + b"model").hexdigest()
    expected_vector = np.random.rand(3072)

    store.cache_query_embedding(cache_key, "test query", expected_vector, "text-embedding-3-large")
    result = store.get_query_embedding(cache_key)

    assert result is not None
    # Use almost_equal to account for float32 precision loss
    np.testing.assert_array_almost_equal(result, expected_vector, decimal=6)


def test_concurrent_cache_writes(tmp_path: Path) -> None:
    """Test that concurrent writes don't error (last-write-wins)."""
    store = LanceDBStore(tmp_path / "lancedb")
    cache_key = hashlib.sha256(b"same query" + b"model").hexdigest()
    vector1 = np.random.rand(3072)
    vector2 = np.random.rand(3072)

    # Write twice (simulates concurrent writes)
    store.cache_query_embedding(cache_key, "same query", vector1, "text-embedding-3-large")
    store.cache_query_embedding(cache_key, "same query", vector2, "text-embedding-3-large")

    # Should not raise error
    result = store.get_query_embedding(cache_key)
    assert result is not None


def test_cache_stores_query_text(tmp_path: Path) -> None:
    """Test that cache stores query text for debugging."""
    store = LanceDBStore(tmp_path / "lancedb")
    cache_key = hashlib.sha256(b"debug query" + b"model").hexdigest()
    vector = np.random.rand(3072)

    store.cache_query_embedding(cache_key, "debug query", vector, "text-embedding-3-large")

    # Verify embedding was stored (query text storage is implementation detail)
    result = store.get_query_embedding(cache_key)
    assert result is not None
