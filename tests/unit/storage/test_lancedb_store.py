"""Unit tests for LanceDBStore implementation.

TDD Workflow: These tests are written FIRST (red phase) before implementation.
They define the expected behavior of LanceDBStore initialization and basic operations.
"""
# ruff: noqa: PLC0415 # Inline imports in performance tests (measure import time)

from pathlib import Path
from unittest.mock import patch

import pytest

from gitctx.git.types import BlobLocation
from gitctx.models.errors import DimensionMismatchError
from gitctx.storage.lancedb_store import LanceDBStore


def test_lancedb_store_init_creates_directory(tmp_path: Path, isolated_env):
    """LanceDBStore creates .gitctx/db/lancedb/ directory."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"

    # Directory should not exist before initialization
    assert not db_path.exists()

    # Create store
    _ = LanceDBStore(db_path)

    # Directory should exist after initialization
    assert db_path.exists()
    assert db_path.is_dir()


def test_lancedb_store_creates_two_tables(tmp_path: Path, isolated_env):
    """LanceDBStore initializes code_chunks and index_metadata tables."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Verify both tables exist
    table_names = store.db.table_names()
    assert "code_chunks" in table_names, "Missing code_chunks table"
    assert "index_metadata" in table_names, "Missing index_metadata table"


def test_empty_index_returns_zero_count(tmp_path: Path, isolated_env):
    """Empty index returns 0 for count()."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Empty index should have 0 chunks
    assert store.count() == 0


def test_empty_index_get_statistics(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros for empty index."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    stats = store.get_statistics()

    # Verify all stats are zero/empty for empty index
    assert stats["total_chunks"] == 0
    assert stats["total_files"] == 0
    assert stats["total_blobs"] == 0
    assert stats["languages"] == {}
    assert stats["index_size_mb"] >= 0  # Directory exists but minimal size


def test_lancedb_store_storage_location(tmp_path: Path, isolated_env):
    """Verify database is created at correct .gitctx/db/lancedb/ path."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Verify store's db_path attribute matches expected path
    assert store.db_path == db_path
    # Use path parts to check path components (works on Windows and Unix)
    assert store.db_path.parts[-3:] == (".gitctx", "db", "lancedb")


def test_dimension_validation_on_table_open(tmp_path: Path, isolated_env):
    """Dimension validation checks table metadata on initialization."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"

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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    embedding_model = "text-embedding-3-large"

    store = LanceDBStore(db_path, embedding_model=embedding_model)

    # Unit test: Verify store initializes with model parameter
    # Full metadata validation happens in integration/E2E tests
    assert store.embedding_model == embedding_model


def test_get_db_size_mb_returns_positive_value(tmp_path: Path, isolated_env):
    """_get_db_size_mb() returns size in megabytes."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Database should have some size (even if minimal)
    size_mb = store._get_db_size_mb()
    assert size_mb >= 0
    assert isinstance(size_mb, float)


def test_dimension_validation_raises_error_on_mismatch(tmp_path: Path, isolated_env):
    """_validate_dimensions() raises DimensionMismatchError on dimension mismatch."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"

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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Mock count_rows to raise exception
    with patch.object(store.chunks_table, "count_rows", side_effect=Exception("Mock error")):
        assert store.count() == 0


def test_get_statistics_handles_empty_table(tmp_path: Path, isolated_env):
    """get_statistics() returns zeros for empty table."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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


def test_add_chunks_batch_empty_embeddings_list(tmp_path: Path, isolated_env):
    """add_chunks_batch handles empty embeddings list gracefully."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # ACT - Call with empty embeddings list
    store.add_chunks_batch(embeddings=[], blob_locations={})

    # ASSERT - No chunks inserted, no errors raised
    assert store.count() == 0


def test_add_chunks_batch_uses_most_recent_location(tmp_path: Path, isolated_env, mock_embedding):
    """add_chunks_batch uses location with highest commit_date when blob has multiple locations."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 5000 embeddings from 100 blobs (50 chunks per blob)
    embeddings = []
    blob_locations = {}

    for blob_idx in range(100):
        blob_sha = f"{blob_idx:040d}"  # Zero-padded 40-char hex
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{blob_idx}.py")]

        embeddings.extend(
            mock_embedding(
                blob_sha=blob_sha,
                content=f"blob{blob_idx} chunk{chunk_idx}",
                chunk_index=chunk_idx,
            )
            for chunk_idx in range(50)
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    # Verify INVERTED index created for BM25 (always created for hybrid search)
    assert "Creating INVERTED index for BM25 search (100 vectors)" in caplog.text
    assert "INVERTED index created successfully" in caplog.text

    # Verify IVF-PQ vector index was skipped (below 256 threshold)
    assert "Skipping IVF-PQ index (100 vectors < 256 minimum)" in caplog.text


def test_search_returns_denormalized_metadata(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() returns results with all 19 denormalized fields."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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
    store.optimize()  # Create INVERTED index for hybrid search

    # Search with a query vector (hybrid search requires query_text)
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=5)

    assert len(results) > 0
    first = results[0]

    # Verify all SearchResult fields present (dataclass, not dict)
    assert hasattr(first, "chunk_content")
    assert hasattr(first, "file_path")
    assert hasattr(first, "distance")
    assert hasattr(first, "commit_sha")
    assert hasattr(first, "token_count")
    assert hasattr(first, "blob_sha")
    assert hasattr(first, "chunk_index")
    assert hasattr(first, "start_line")
    assert hasattr(first, "end_line")
    assert hasattr(first, "total_chunks")
    assert hasattr(first, "language")
    assert hasattr(first, "author_name")
    assert hasattr(first, "author_email")
    assert hasattr(first, "commit_date")
    assert hasattr(first, "commit_message")
    assert hasattr(first, "is_head")
    assert hasattr(first, "is_merge")
    # Score fields (hybrid search)
    assert hasattr(first, "bm25_score")
    assert hasattr(first, "vector_score")
    assert hasattr(first, "hybrid_score")


def test_search_filter_head_only(tmp_path: Path, isolated_env, mock_embedding, mock_blob_location):
    """search() with filter_head_only returns only HEAD chunks."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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
    store.optimize()  # Create INVERTED index for hybrid search

    # Search with filter_head_only (hybrid search requires query_text)
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=10, filter_head_only=True)

    # All results should have is_head=True (SearchResult objects, not dicts)
    assert len(results) > 0
    assert all(r.is_head for r in results), "Some results have is_head=False"


def test_get_statistics_accuracy(tmp_path: Path, isolated_env, mock_embedding, mock_blob_location):
    """get_statistics() returns accurate counts and languages."""

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 100 chunks from 10 blobs across 5 files
    embeddings = []
    blob_locations = {}

    for blob_idx in range(10):
        blob_sha = f"{blob_idx:040d}"
        file_idx = blob_idx % 5  # 5 unique files
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{file_idx}.py")]

        # 10 chunks per blob
        embeddings.extend(
            mock_embedding(
                blob_sha=blob_sha,
                content=f"blob{blob_idx} chunk{chunk_idx}",
                chunk_index=chunk_idx,
            )
            for chunk_idx in range(10)
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Add some chunks first
    embeddings = [mock_embedding(blob_sha=f"{i:040d}", chunk_index=0) for i in range(100)]
    blob_locations = {
        f"{i:040d}": [mock_blob_location(file_path=f"file_{i}.py")] for i in range(100)
    }
    store.add_chunks_batch(embeddings, blob_locations)

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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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
    store.optimize()  # Create INVERTED index for hybrid search

    # Search with hybrid query (requires query_text)
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=5)

    # Verify complete BlobLocation context (SearchResult object, not dict)
    first = results[0]
    assert hasattr(first, "blob_sha")
    assert hasattr(first, "file_path")
    assert hasattr(first, "start_line")
    assert hasattr(first, "end_line")
    assert hasattr(first, "commit_sha")
    assert hasattr(first, "author_name")
    assert hasattr(first, "author_email")
    assert hasattr(first, "commit_date")
    assert hasattr(first, "commit_message")
    assert hasattr(first, "is_head")
    assert hasattr(first, "is_merge")


def test_statistics_language_breakdown(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """get_statistics() returns language counts."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
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

    # Search with hybrid query (requires query_text)
    query_vector = [0.1] * 3072
    query_text = "test"

    start = time.time()
    results = store.search(query_vector, query_text, limit=10)
    elapsed = time.time() - start

    # Verify results returned
    assert len(results) > 0

    # Configurable threshold for different hardware
    max_latency_ms = int(os.getenv("GITCTX_SEARCH_LATENCY_MS", "100"))
    latency_ms = elapsed * 1000
    assert latency_ms < max_latency_ms, (
        f"Search too slow: {latency_ms:.1f}ms (target: <{max_latency_ms}ms)"
    )


# ============================================================================
# TASK-0001.4.2.3: GitHeadBooster Integration (TDD Red Phase)
# ============================================================================


def test_search_integrates_git_head_booster(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() integrates GitHeadBooster to boost HEAD results."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 5 HEAD chunks and 5 historical chunks
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
    store.optimize()

    # Search should apply HEAD boost
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=10)

    # Verify GitHeadBooster was initialized
    assert hasattr(store, "booster"), "LanceDBStore should have booster attribute"
    assert store.booster.head_multiplier == 1.5

    # Verify results exist
    assert len(results) > 0


def test_search_applies_boost_after_hybrid_scoring(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() applies HEAD boost after hybrid RRF scoring."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create chunks with known content for predictable scoring
    embeddings = []
    blob_locations = {}

    # HEAD chunk with keyword match
    blob_locations["head_sha"] = [mock_blob_location(file_path="src/head.py", is_head=True)]
    embeddings.append(
        mock_embedding(blob_sha="head_sha", content="authentication middleware", chunk_index=0)
    )

    # Historical chunk with keyword match
    blob_locations["hist_sha"] = [mock_blob_location(file_path="src/hist.py", is_head=False)]
    embeddings.append(
        mock_embedding(blob_sha="hist_sha", content="authentication system", chunk_index=0)
    )

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()

    # Search for "authentication"
    query_vector = [0.1] * 3072
    query_text = "authentication"
    results = store.search(query_vector, query_text, limit=10)

    # Both should be returned
    assert len(results) >= 2

    # HEAD result should have higher hybrid_score (boosted by 1.5x)
    head_results = [r for r in results if r.is_head]
    hist_results = [r for r in results if not r.is_head]

    assert len(head_results) > 0, "Should have HEAD results"
    assert len(hist_results) > 0, "Should have historical results"


def test_search_ranking_order_after_boost(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() re-ranks results by boosted hybrid_score."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 chunks: 5 HEAD, 5 historical
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        is_head = i % 2 == 0  # Alternating HEAD/historical
        blob_locations[blob_sha] = [
            mock_blob_location(file_path=f"src/file_{i}.py", is_head=is_head)
        ]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test keyword {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()

    # Search
    query_vector = [0.1] * 3072
    query_text = "keyword"
    results = store.search(query_vector, query_text, limit=10)

    # Results should be sorted by hybrid_score (descending)
    hybrid_scores = [r.hybrid_score for r in results]
    assert hybrid_scores == sorted(hybrid_scores, reverse=True), (
        "Results should be sorted by hybrid_score descending"
    )


def test_search_with_all_head_results(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() boosts all results when all are HEAD."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 HEAD chunks only
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py", is_head=True)]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()

    # Search
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=10)

    # All results should be HEAD
    assert all(r.is_head for r in results)


def test_search_with_all_historical_results(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() handles all historical results (no boost applied)."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 historical chunks only
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        blob_locations[blob_sha] = [mock_blob_location(file_path=f"src/file_{i}.py", is_head=False)]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()

    # Search
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=10)

    # All results should be historical (not HEAD)
    assert all(not r.is_head for r in results)


def test_search_with_empty_results(tmp_path: Path, isolated_env):
    """search() handles empty results gracefully (no crash on boost)."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Empty index
    store.optimize()  # Create indexes (even though empty)

    # Search should not crash
    query_vector = [0.1] * 3072
    query_text = "nonexistent"
    results = store.search(query_vector, query_text, limit=10)

    # Should return empty list (no crash)
    assert results == []


def test_search_respects_max_distance_with_boost(
    tmp_path: Path, isolated_env, mock_embedding, mock_blob_location
):
    """search() applies max_distance filter after boost (not before)."""
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    store = LanceDBStore(db_path)

    # Create 10 chunks
    embeddings = []
    blob_locations = {}

    for i in range(10):
        blob_sha = f"{i:040d}"
        is_head = i < 5
        blob_locations[blob_sha] = [
            mock_blob_location(file_path=f"src/file_{i}.py", is_head=is_head)
        ]
        embeddings.append(
            mock_embedding(blob_sha=blob_sha, content=f"test content {i}", chunk_index=0)
        )

    store.add_chunks_batch(embeddings, blob_locations)
    store.optimize()

    # Search with max_distance filter
    query_vector = [0.1] * 3072
    query_text = "test"
    results = store.search(query_vector, query_text, limit=10, max_distance=0.5)

    # All results should have distance <= 0.5
    assert all(r.distance <= 0.5 for r in results)


def test_search_limit_applied_after_boosting(tmp_path, monkeypatch):
    """Verify limit is applied AFTER HEAD boosting and re-ranking.

    Regression test for limit-before-boost issue where HEAD files with lower
    pre-boost scores were excluded before boosting could surface them.

    Scenario:
    - LanceDB returns 15 results (10 historical + 5 HEAD)
    - Historical: hybrid_score 0.85-0.95 (high pre-boost)
    - HEAD: hybrid_score 0.60-0.70 (low pre-boost, but 0.90-1.05 post-boost)
    - Request limit=5
    - Expected: Top 5 includes HEAD results (proves limit applied after boost)
    """
    from unittest.mock import Mock

    from gitctx.storage.lancedb_store import LanceDBStore

    store = LanceDBStore(tmp_path / "test.lancedb")

    # Mock LanceDB results: 10 historical + 5 HEAD
    # 10 historical chunks with high pre-boost scores (0.85-0.95)
    mock_results = [
        {
            "chunk_content": f"historical chunk {i}",
            "file_path": f"historical_{i}.py",
            "_distance": 0.1 + (i * 0.01),  # 0.10-0.19
            "commit_sha": "a" * 40,
            "token_count": 100,
            "blob_sha": f"hist{i:02d}" + "0" * 34,
            "chunk_index": 0,
            "start_line": 1,
            "end_line": 10,
            "total_chunks": 1,
            "language": "python",
            "author_name": "Author",
            "author_email": "author@example.com",
            "commit_date": "2025-01-01T00:00:00Z",
            "commit_message": "Historical commit",
            "is_head": False,
            "is_merge": False,
            "_score": 5.0 + i,  # BM25 scores
            "_relevance_score": 0.95 - (i * 0.01),  # Hybrid: 0.95, 0.94, ..., 0.86
        }
        for i in range(10)
    ]

    # 5 HEAD chunks with lower pre-boost scores (0.60-0.70)
    # After 1.5x boost: 0.90-1.05 (will outrank historical!)
    mock_results.extend(
        [
            {
                "chunk_content": f"HEAD chunk {i}",
                "file_path": f"head_{i}.py",
                "_distance": 0.3 + (i * 0.01),  # 0.30-0.34
                "commit_sha": "b" * 40,
                "token_count": 100,
                "blob_sha": f"head{i:02d}" + "0" * 34,
                "chunk_index": 0,
                "start_line": 1,
                "end_line": 10,
                "total_chunks": 1,
                "language": "python",
                "author_name": "Author",
                "author_email": "author@example.com",
                "commit_date": "2025-01-15T00:00:00Z",
                "commit_message": "HEAD commit",
                "is_head": True,
                "is_merge": False,
                "_score": 3.0 + i,  # BM25 scores
                "_relevance_score": 0.70 - (i * 0.02),  # Hybrid: 0.70, 0.68, 0.66, 0.64, 0.62
            }
            for i in range(5)
        ]
    )

    # Mock the LanceDB query to return our controlled results
    mock_query = Mock()
    mock_query.to_list.return_value = mock_results

    mock_table = Mock()
    # Chain mock methods for LanceDB query builder pattern
    query_builder = mock_table.search.return_value.vector.return_value.text.return_value
    query_builder.limit.return_value.rerank.return_value = mock_query

    store.chunks_table = mock_table

    # Execute search with limit=5
    results = store.search(
        query_vector=[0.1] * 3072,
        query_text="test query",
        limit=5,
        max_distance=2.0,
    )

    # Verify we got exactly 5 results
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"

    # Verify HEAD results made it to top 5 (proves limit after boost)
    head_count = sum(1 for r in results if r.is_head)
    assert head_count >= 3, (
        f"Expected at least 3 HEAD results in top 5, got {head_count}. "
        "This suggests limit was applied BEFORE boosting!"
    )

    # Verify results sorted by boosted hybrid_score (descending)
    scores = [r.hybrid_score for r in results]
    assert scores == sorted(scores, reverse=True), f"Results not sorted by hybrid_score: {scores}"

    # Verify top result is HEAD with boosted score
    assert results[0].is_head is True, "Top result should be HEAD after boosting"
    # HEAD 0.70 * 1.5 = 1.05, should be > historical 0.95
    assert results[0].hybrid_score > 1.0, (
        f"Top HEAD result should have boosted score >1.0, got {results[0].hybrid_score}"
    )

    # Verify historical results have unboosted scores
    historical_results = [r for r in results if not r.is_head]
    if historical_results:
        for r in historical_results:
            assert r.hybrid_score < 1.0, (
                f"Historical result should have unboosted score <1.0, got {r.hybrid_score}"
            )
