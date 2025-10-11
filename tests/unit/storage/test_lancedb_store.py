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
    assert stats["languages"] == {}
    assert stats["index_size_mb"] >= 0  # Directory exists but minimal size


def test_lancedb_store_storage_location(tmp_path: Path, isolated_env):
    """Verify database is created at correct .gitctx/lancedb/ path."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Verify store's db_path attribute matches expected path
    assert store.db_path == db_path
    # Use path parts to check path components (works on Windows and Unix)
    assert store.db_path.parts[-2:] == (".gitctx", "lancedb")


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


def test_get_statistics_handles_empty_table(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros for empty table."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Empty table from initialization
    stats = store.get_statistics()
    assert stats["total_chunks"] == 0
    assert stats["total_files"] == 0
    assert stats["total_blobs"] == 0
    assert stats["languages"] == {}
    assert stats["index_size_mb"] >= 0


def test_get_statistics_handles_exception(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros if to_arrow() raises exception."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Mock to_arrow to raise exception
    with patch.object(store.chunks_table, "to_arrow", side_effect=Exception("Mock error")):
        stats = store.get_statistics()
        assert stats["total_chunks"] == 0
        assert stats["total_files"] == 0
        assert stats["total_blobs"] == 0
        assert stats["languages"] == {}
        assert stats["index_size_mb"] >= 0


# ============================================================================
# TASK-0001.2.4.3: Core Storage Operations & Indexing (TDD Red Phase)
# ============================================================================


def test_add_chunks_batch_denormalizes_blob_location(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """add_chunks_batch denormalizes BlobLocation metadata into each chunk."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 embeddings from 2 blobs
    blob_sha_1 = "a" * 40
    blob_sha_2 = "b" * 40

    embeddings = [
        mock_embedding(blob_sha=blob_sha_1, content=f"chunk {i}", chunk_index=i) for i in range(5)
    ]
    embeddings.extend(
        [mock_embedding(blob_sha=blob_sha_2, content=f"chunk {i}", chunk_index=i) for i in range(5)]
    )

    blob_locations = {
        blob_sha_1: [mock_blob_location(file_path="src/main.py")],
        blob_sha_2: [mock_blob_location(file_path="src/utils.py")],
    }

    # This test will FAIL until we implement add_chunks_batch
    store.add_chunks_batch(embeddings=embeddings, blob_locations=blob_locations)

    # Query back and verify denormalized fields
    arrow_table = store.chunks_table.to_arrow()
    assert arrow_table.num_rows == 10

    # Verify all 19 denormalized fields are present
    expected_fields = [
        "vector",
        "chunk_content",
        "token_count",
        "blob_sha",
        "chunk_index",
        "start_line",
        "end_line",
        "total_chunks",
        "file_path",
        "language",
        "commit_sha",
        "author_name",
        "author_email",
        "commit_date",
        "commit_message",
        "is_head",
        "is_merge",
        "embedding_model",
        "indexed_at",
    ]
    for field in expected_fields:
        assert field in arrow_table.schema.names, f"Missing field: {field}"

    # Verify metadata from first blob
    records = arrow_table.to_pylist()
    first_blob_chunks = [r for r in records if r["blob_sha"] == blob_sha_1]
    assert len(first_blob_chunks) == 5
    assert first_blob_chunks[0]["author_name"] == "Test Author"
    assert first_blob_chunks[0]["file_path"] == "src/main.py"


def test_add_chunks_batch_empty_blob_locations_warning(
    tmp_path: Path, isolated_env, mock_embedding, caplog
):
    """add_chunks_batch logs warning and skips chunks with missing blob locations."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    blob_sha = "a" * 40
    embeddings = [mock_embedding(blob_sha=blob_sha, chunk_index=0)]

    # Empty blob_locations dict - should warn and skip
    store.add_chunks_batch(embeddings=embeddings, blob_locations={})

    # Verify warning was logged (first 8 chars of SHA)
    assert "No location found for blob" in caplog.text
    assert blob_sha[:8] in caplog.text

    # Verify no chunks were inserted
    assert store.count() == 0


def test_add_chunks_batch_uses_most_recent_location(tmp_path: Path, isolated_env, mock_embedding):
    """add_chunks_batch uses location with highest commit_date when blob has multiple locations."""
    from gitctx.core.models import BlobLocation
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    blob_sha = "a" * 40

    # Create 3 locations with different commit dates
    locations = [
        BlobLocation(
            commit_sha="old_commit",
            file_path="src/file.py",
            author_name="Author Old",
            author_email="old@example.com",
            commit_date=1000000000,  # Oldest
            commit_message="Old commit",
            is_head=False,
            is_merge=False,
        ),
        BlobLocation(
            commit_sha="newest_commit",
            file_path="src/file_renamed.py",
            author_name="Author New",
            author_email="new@example.com",
            commit_date=1000000200,  # Newest
            commit_message="Latest commit",
            is_head=True,
            is_merge=False,
        ),
        BlobLocation(
            commit_sha="middle_commit",
            file_path="src/file.py",
            author_name="Author Middle",
            author_email="middle@example.com",
            commit_date=1000000100,  # Middle
            commit_message="Middle commit",
            is_head=False,
            is_merge=False,
        ),
    ]

    embeddings = [mock_embedding(blob_sha=blob_sha, chunk_index=0)]
    blob_locations = {blob_sha: locations}

    store.add_chunks_batch(embeddings=embeddings, blob_locations=blob_locations)

    # Query back and verify the NEWEST location was used
    arrow_table = store.chunks_table.to_arrow()
    records = arrow_table.to_pylist()
    assert len(records) == 1

    chunk = records[0]
    assert chunk["commit_sha"] == "newest_commit"
    assert chunk["file_path"] == "src/file_renamed.py"
    assert chunk["author_name"] == "Author New"
    assert chunk["commit_date"] == 1000000200
    assert chunk["is_head"] is True


@pytest.mark.slow
def test_batch_insertion_performance_5000_chunks(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """Batch insertion handles 5000+ chunks at >100 chunks/sec."""
    import os
    import time

    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 5000 embeddings from 100 blobs (50 chunks per blob)
    embeddings = []
    blob_locations = {}

    for blob_idx in range(100):
        blob_sha = f"{blob_idx:040d}"  # Zero-padded 40-char hex
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{blob_idx}.py")]

        for chunk_idx in range(50):
            embeddings.append(
                mock_embedding(
                    blob_sha=blob_sha,
                    content=f"blob{blob_idx} chunk{chunk_idx}",
                    chunk_index=chunk_idx,
                )
            )

    # Measure performance
    start = time.time()
    store.add_chunks_batch(embeddings=embeddings, blob_locations=blob_locations)
    elapsed = time.time() - start

    # Verify all inserted
    assert store.count() == 5000

    # Performance target: >100 chunks/sec on baseline hardware (MacBook Pro M1, 16GB RAM, SSD)
    # Adjust threshold via GITCTX_PERF_THRESHOLD env var if your hardware differs
    min_chunks_per_sec = int(os.getenv("GITCTX_PERF_THRESHOLD", "100"))
    chunks_per_sec = 5000 / elapsed
    assert chunks_per_sec >= min_chunks_per_sec, (
        f"Too slow: {chunks_per_sec:.1f} chunks/sec (target: {min_chunks_per_sec}+)"
    )


def test_optimize_creates_ivf_pq_index_at_256_vectors(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """optimize() creates IVF-PQ index when count >= 256."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 256 embeddings (minimum for indexing)
    embeddings = []
    blob_locations = {}

    for i in range(256):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings.append(mock_embedding(blob_sha=blob_sha, chunk_index=0))

    store.add_chunks_batch(embeddings, blob_locations)
    assert store.count() == 256

    # This test will FAIL until we implement optimize
    store.optimize()

    # Verify index was created (LanceDB stores index metadata in table stats)
    # Note: LanceDB's index metadata is accessible via table.list_indices()
    indices = store.chunks_table.list_indices()
    assert len(indices) > 0, "No index created"


def test_optimize_skips_indexing_below_256_vectors(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location, caplog
):
    """optimize() skips indexing when count < 256."""
    import logging

    from gitctx.storage.lancedb_store import LanceDBStore

    # Set log level to capture INFO messages
    caplog.set_level(logging.INFO)

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 100 embeddings (below threshold)
    embeddings = []
    blob_locations = {}

    for i in range(100):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings.append(mock_embedding(blob_sha=blob_sha, chunk_index=0))

    store.add_chunks_batch(embeddings, blob_locations)
    assert store.count() == 100

    store.optimize()

    # Verify info message was logged
    assert "Not enough vectors (100) for indexing" in caplog.text
    assert "minimum: 256" in caplog.text


def test_search_returns_denormalized_metadata(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() returns results with all 19 denormalized fields."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 embeddings
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)

    # Search with a query vector
    query_vector = [0.1] * 3072
    results = store.search(query_vector, limit=5)

    assert len(results) > 0
    first = results[0]

    # Verify all 19 fields present
    expected_fields = [
        "vector",
        "chunk_content",
        "token_count",
        "blob_sha",
        "chunk_index",
        "start_line",
        "end_line",
        "total_chunks",
        "file_path",
        "language",
        "commit_sha",
        "author_name",
        "author_email",
        "commit_date",
        "commit_message",
        "is_head",
        "is_merge",
        "embedding_model",
        "indexed_at",
    ]
    for field in expected_fields:
        assert field in first, f"Missing field: {field}"


def test_search_filter_head_only(tmp_path: Path, isolated_env, mock_embedding, mock_blob_location):
    """search() with filter_head_only returns only HEAD chunks."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 embeddings: 5 from HEAD, 5 from history
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        is_head = i < 5  # First 5 are HEAD
        blob_locations[blob_sha] = [
            mock_blob_location(file_path=f"src/file_{i}.py", is_head=is_head)
        ]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)

    # Search with filter_head_only
    query_vector = [0.1] * 3072
    results = store.search(query_vector, limit=10, filter_head_only=True)

    # All results should have is_head=True
    assert len(results) > 0
    assert all(r["is_head"] for r in results), "Some results have is_head=False"


def test_get_statistics_accuracy(tmp_path: Path, isolated_env, mock_embedding, mock_blob_location):
    """get_statistics() returns accurate counts and languages."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 100 chunks from 10 blobs across 5 files
    embeddings = []
    blob_locations = {}

    for blob_idx in range(10):
        blob_sha = f"{blob_idx:040d}"
        file_idx = blob_idx % 5  # 5 unique files
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{file_idx}.py")]

        # 10 chunks per blob
        for chunk_idx in range(10):
            embeddings.append(
                mock_embedding(
                    blob_sha=blob_sha,
                    content=f"blob{blob_idx} chunk{chunk_idx}",
                    chunk_index=chunk_idx,
                )
            )

    store.add_chunks_batch(embeddings, blob_locations)

    stats = store.get_statistics()

    assert stats["total_chunks"] == 100
    assert stats["total_files"] == 5
    assert stats["total_blobs"] == 10
    assert "languages" in stats
    assert isinstance(stats["languages"], dict)
    assert stats["index_size_mb"] > 0


def test_incremental_updates_preserve_existing_chunks(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """Incremental updates preserve existing chunks (old data unchanged)."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Insert 10 initial chunks
    embeddings_1 = []
    blob_locations_1 = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        blob_locations_1[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings_1.append(
            mock_embedding(blob_sha=blob_sha, content=f"original {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings_1, blob_locations_1)
    assert store.count() == 10

    # Get original data
    arrow_table = store.chunks_table.to_arrow()
    original_blob_shas = set(arrow_table.column("blob_sha").to_pylist())

    # Insert 5 new chunks
    embeddings_2 = []
    blob_locations_2 = {}

    for i in range(10, 15):
        blob_sha = f"{i:040d}"
        blob_locations_2[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings_2.append(mock_embedding(blob_sha=blob_sha, content=f"new {i}", chunk_index=0))

    store.add_chunks_batch(embeddings_2, blob_locations_2)

    # Verify total count
    assert store.count() == 15

    # Verify old chunks still exist
    updated_arrow = store.chunks_table.to_arrow()
    updated_blob_shas = set(updated_arrow.column("blob_sha").to_pylist())

    # All original blob_shas should still be present
    assert original_blob_shas.issubset(updated_blob_shas), "Some original chunks were lost"


# ============================================================================
# TASK-0001.2.4.4: Index State Tracking & Final Integration (TDD Red Phase)
# ============================================================================


def test_save_index_state_stores_metadata(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """save_index_state() stores complete metadata."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Add some chunks first
    embeddings = [mock_embedding(blob_sha=f"{i:040d}", chunk_index=0) for i in range(100)]
    blob_locations = {
        f"{i:040d}": [mock_blob_location(file_path=f"file_{i}.py")] for i in range(100)
    }
    store.add_chunks_batch(embeddings, blob_locations)

    # This test will FAIL until we implement save_index_state
    store.save_index_state(
        last_commit="abc123def456",  # pragma: allowlist secret
        indexed_blobs=["blob1", "blob2", "blob3"],
        embedding_model="text-embedding-3-large",
    )

    # Query metadata table
    arrow_table = store.metadata_table.to_arrow()
    records = arrow_table.to_pylist()
    state = next(r for r in records if r["key"] == "index_state")

    assert state["last_commit"] == "abc123def456"  # pragma: allowlist secret
    assert "blob1" in state["indexed_blobs"]  # JSON list
    assert state["embedding_model"] == "text-embedding-3-large"
    assert state["total_chunks"] == 100
    assert state["total_blobs"] == 3


def test_save_index_state_upsert_pattern(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """save_index_state() replaces old state (upsert)."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Add some chunks first
    embeddings = [mock_embedding(blob_sha=f"{i:040d}", chunk_index=0) for i in range(100)]
    blob_locations = {
        f"{i:040d}": [mock_blob_location(file_path=f"file_{i}.py")] for i in range(100)
    }
    store.add_chunks_batch(embeddings, blob_locations)

    # Save state twice
    store.save_index_state("commit1", ["blob1"], "text-embedding-3-large")
    store.save_index_state("commit2", ["blob1", "blob2"], "text-embedding-3-large")

    # Only one row should exist (upsert, not append)
    arrow_table = store.metadata_table.to_arrow()
    records = arrow_table.to_pylist()
    states = [r for r in records if r["key"] == "index_state"]
    assert len(states) == 1
    assert states[0]["last_commit"] == "commit2"


def test_save_index_state_empty_table_no_exception(tmp_path: Path, isolated_env):
    """save_index_state() handles empty metadata table gracefully."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Should not raise exception even if table is empty
    store.save_index_state("commit1", [], "text-embedding-3-large")

    arrow_table = store.metadata_table.to_arrow()
    assert arrow_table.num_rows == 1


def test_query_returns_complete_blob_location_context(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """Query results include all 11 BlobLocation fields."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create embeddings with complete BlobLocation metadata
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [
            mock_blob_location(
                file_path=f"src/file_{i}.py",
                commit_sha=f"commit{i:040d}",
                is_head=i < 5,
            )
        ]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)

    query_vector = [0.1] * 3072
    results = store.search(query_vector, limit=5)

    # Verify complete BlobLocation context (11 fields from BlobLocation + chunk fields)
    first = results[0]
    assert "blob_sha" in first
    assert "file_path" in first
    assert "start_line" in first
    assert "end_line" in first
    assert "commit_sha" in first
    assert "author_name" in first
    assert "author_email" in first
    assert "commit_date" in first
    assert "commit_message" in first
    assert "is_head" in first
    assert "is_merge" in first


def test_statistics_language_breakdown(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """get_statistics() returns language counts."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create embeddings with different languages: 50 python, 30 javascript, 20 go
    embeddings = []
    blob_locations = {}

    languages = [("python", 50), ("javascript", 30), ("go", 20)]
    blob_idx = 0

    for language, count in languages:
        for i in range(count):
            blob_sha = f"{blob_idx:040d}"
            blob_locations[blob_sha] = [
                mock_blob_location(file_path=f"src/file_{blob_idx}.{language}")
            ]
            embeddings.append(
                mock_embedding(
                    blob_sha=blob_sha,
                    content=f"{language} content {i}",
                    chunk_index=0,
                    language=language,
                )
            )
            blob_idx += 1

    store.add_chunks_batch(embeddings, blob_locations)

    stats = store.get_statistics()

    assert "languages" in stats
    langs = stats["languages"]
    assert langs["python"] == 50
    assert langs["javascript"] == 30
    assert langs["go"] == 20


@pytest.mark.slow
def test_performance_insertion_speed(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """Verify >100 chunks/sec insertion speed."""
    import os
    import time

    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10000 embeddings
    embeddings = []
    blob_locations = {}

    for i in range(10000):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings.append(mock_embedding(blob_sha=blob_sha, content=f"content {i}", chunk_index=0))

    start = time.time()
    store.add_chunks_batch(embeddings=embeddings, blob_locations=blob_locations)
    elapsed = time.time() - start

    # Configurable threshold for different hardware
    min_chunks_per_sec = int(os.getenv("GITCTX_PERF_THRESHOLD_FAST", "100"))
    chunks_per_sec = 10000 / elapsed
    assert chunks_per_sec >= min_chunks_per_sec, (
        f"Insertion too slow: {chunks_per_sec:.1f} chunks/sec (target: {min_chunks_per_sec}+)"
    )


@pytest.mark.slow
def test_performance_search_latency(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """Verify <100ms search latency with IVF-PQ index."""
    import os
    import time

    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 1000 embeddings
    embeddings = []
    blob_locations = {}

    for i in range(1000):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py")]
        embeddings.append(mock_embedding(blob_sha=blob_sha, content=f"content {i}", chunk_index=0))

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()  # Create IVF-PQ index

    query_vector = [0.1] * 3072

    start = time.time()
    results = store.search(query_vector, limit=10)
    elapsed = time.time() - start

    # Verify results returned
    assert len(results) > 0

    # Configurable threshold for different hardware
    max_latency_ms = int(os.getenv("GITCTX_SEARCH_LATENCY_MS", "100"))
    latency_ms = elapsed * 1000
    assert latency_ms < max_latency_ms, (
        f"Search too slow: {latency_ms:.1f}ms (target: <{max_latency_ms}ms)"
    )
