"""Unit tests for LanceDBStore implementation.

TDD Workflow: These tests are written FIRST (red phase) before implementation.
They define the expected behavior of LanceDBStore initialization and basic operations.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


def test_lancedb_store_init_creates_directory(tmp_path: Path, isolated_env):
    """LanceDBStore creates .gitctx/lancedb/ directory."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"

    # Directory should not exist before initialization
    assert not db_path.exists()

    # Create store
    _ = LanceDBStore(db_path)

    # Directory should exist after initialization
    assert db_path.exists()
    assert db_path.is_dir()


def test_lancedb_store_creates_two_tables(tmp_path: Path, isolated_env):
    """LanceDBStore initializes code_chunks and index_metadata tables."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Verify both tables exist
    table_names = store.db.table_names()
    assert "code_chunks" in table_names, "Missing code_chunks table"
    assert "index_metadata" in table_names, "Missing index_metadata table"


def test_empty_index_returns_zero_count(tmp_path: Path, isolated_env):
    """Empty index returns 0 for count()."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Empty index should have 0 chunks
    assert store.count() == 0


def test_empty_index_get_statistics(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros for empty index."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    stats = store.get_statistics()

    # Verify all stats are zero/empty for empty index
    assert stats["total_chunks"] == 0
    assert stats["total_files"] == 0
    assert stats["total_blobs"] == 0
    assert stats["index_size_mb"] >= 0  # Directory exists but minimal size


def test_lancedb_store_storage_location(tmp_path: Path, isolated_env):
    """Verify database is created at correct .gitctx/lancedb/ path."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Verify store's db_path attribute matches expected path
    assert store.db_path == db_path
    assert str(store.db_path).endswith(".gitctx/lancedb")


def test_dimension_validation_on_table_open(tmp_path: Path, isolated_env):
    """Dimension validation checks table metadata on initialization."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"

    # Create store with 3072-dim embeddings
    store = LanceDBStore(db_path, embedding_dimensions=3072)

    # Attempt to open store expecting different dimensions
    # This should raise DimensionMismatchError if metadata validation works
    # For now, opening with same dimensions should work
    store2 = LanceDBStore(db_path, embedding_dimensions=3072)
    assert store2.count() == 0  # Should open successfully
    # Use the first store to avoid F841
    assert store.count() == 0

    # Note: Testing actual dimension mismatch requires adding data first
    # That will be tested in integration tests after add_chunks_batch is implemented


def test_table_metadata_includes_embedding_model(tmp_path: Path, isolated_env):
    """Table metadata contains embedding_model field."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    embedding_model = "text-embedding-3-large"

    store = LanceDBStore(db_path, embedding_model=embedding_model)

    # Verify metadata is accessible (actual validation happens in integration tests)
    # For now, just verify store initializes with model parameter
    assert store.embedding_model == embedding_model


def test_get_db_size_mb_returns_positive_value(tmp_path: Path, isolated_env):
    """_get_db_size_mb() returns size in megabytes."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Database should have some size (even if minimal)
    size_mb = store._get_db_size_mb()
    assert size_mb >= 0
    assert isinstance(size_mb, float)


def test_dimension_validation_raises_error_on_mismatch(tmp_path: Path, isolated_env):
    """_validate_dimensions() raises DimensionMismatchError on dimension mismatch."""
    from gitctx.core.exceptions import DimensionMismatchError
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"

    # Create store with 3072 dimensions
    store1 = LanceDBStore(db_path, embedding_dimensions=3072)
    assert store1.count() == 0

    # Try to open with different dimensions - should raise error
    with pytest.raises(DimensionMismatchError) as exc_info:
        _ = LanceDBStore(db_path, embedding_dimensions=1536)

    # Verify error message format
    assert "Dimension mismatch" in str(exc_info.value)
    assert "3072" in str(exc_info.value)
    assert "1536" in str(exc_info.value)
    assert "gitctx index --force" in str(exc_info.value)


def test_count_returns_zero_on_exception(tmp_path: Path, isolated_env):
    """count() returns 0 if count_rows() raises exception."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Mock count_rows to raise exception
    with patch.object(store.chunks_table, "count_rows", side_effect=Exception("Mock error")):
        assert store.count() == 0


def test_get_statistics_handles_empty_dataframe(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros for empty dataframe."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Mock to_pandas to return empty dataframe
    # Pandas is a dependency of LanceDB, so we can import it here
    import pandas as pd

    empty_df = pd.DataFrame()
    with patch.object(store.chunks_table, "to_pandas", return_value=empty_df):
        stats = store.get_statistics()
        assert stats["total_chunks"] == 0
        assert stats["total_files"] == 0
        assert stats["total_blobs"] == 0
        assert stats["index_size_mb"] >= 0


def test_get_statistics_handles_exception(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros if to_pandas() raises exception."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Mock to_pandas to raise exception
    with patch.object(store.chunks_table, "to_pandas", side_effect=Exception("Mock error")):
        stats = store.get_statistics()
        assert stats["total_chunks"] == 0
        assert stats["total_files"] == 0
        assert stats["total_blobs"] == 0
        assert stats["index_size_mb"] >= 0
