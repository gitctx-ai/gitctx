# STORY-0001.2.4: LanceDB Vector Storage

**Parent**: [EPIC-0001.2](../README.md)
**Status**: ✅ Complete
**Story Points**: 3
**Progress**: ██████████ 100% (4/4 tasks complete)
**BDD Result**: 10/10 scenarios passing ✅

## User Story

As the indexing system (serving developers and AI agents)
I want to store embeddings with denormalized metadata in LanceDB
So that semantic search can retrieve precise code locations with full git context in a single query

## Acceptance Criteria

- [x] Store embeddings in LanceDB with 3072-dimensional vectors (text-embedding-3-large)
- [x] Use denormalized schema (embed blob location metadata with each chunk)
- [x] Support batch insertion for efficient indexing (1000+ chunks at once)
- [x] Create IVF-PQ index automatically when table has >256 vectors
- [x] Store metadata: blob_sha, chunk_index, file_path, line numbers, commit_sha, author, date, message
- [x] Support incremental updates (add new chunks without full re-index)
- [x] Track index state (last commit, indexed blobs, timestamps)
- [x] Provide statistics (total chunks, files, languages, index size)
- [x] Handle schema evolution (detect dimension mismatches gracefully)
- [x] Store in `.gitctx/lancedb/` directory (gitignored)

## BDD Scenarios

```gherkin
Feature: LanceDB Vector Storage

  Scenario: Store embeddings with denormalized metadata
    Given 100 embeddings from 10 blobs
    And each embedding has associated BlobLocation metadata
    When I store embeddings in LanceDB
    Then each vector should be stored with denormalized metadata
    And metadata should include: blob_sha, chunk_index, file_path, line range, commit info
    And I should be able to query and get complete context in one operation

  Scenario: Batch insertion for efficiency
    Given 5000 embeddings to store
    When I insert in batches
    Then all 5000 should be inserted successfully
    And insertion should take <10 seconds total
    And batch size should be configurable (default 1000)

  Scenario: Automatic IVF-PQ indexing
    Given a table with 300 vectors
    When I call optimize()
    Then an IVF-PQ index should be created automatically
    And index should use cosine similarity metric
    And partitions should be adaptive (row_count // 256)
    And subvectors should be adaptive (dimensions // 16)

  Scenario: Incremental updates
    Given an existing index with 1000 chunks
    And 50 new chunks from 5 new blobs
    When I add the new chunks
    Then index should contain 1050 chunks total
    And old chunks should remain unchanged
    And new chunks should be immediately searchable

  Scenario: Index state tracking
    Given indexing completed at commit abc123
    When I save index metadata
    Then metadata should include: last_commit = abc123
    And metadata should include: indexed_blobs list
    And metadata should include: last_indexed timestamp
    And metadata should include: embedding_model name

  Scenario: Schema validation
    Given an existing index with 3072-dimensional vectors
    When I attempt to insert 1024-dimensional vectors
    Then I should get clear error: "Dimension mismatch: expected 3072, got 1024"
    And no data should be written
    And user should be advised to re-index

  Scenario: Statistics reporting
    Given an index with 5000 chunks from 100 files
    When I request statistics
    Then I should get:
      | Metric         | Value        |
      |----------------|--------------|
      | total_chunks   | 5000         |
      | total_files    | 100          |
      | index_size_mb  | <150 (approx)|
      | total_blobs    | 500 (approx) |

  Scenario: Query with blob location context
    Given embeddings stored with denormalized BlobLocation data
    When I search for similar vectors
    Then results should include complete context without joins:
      - chunk content
      - file_path
      - line_range (start_line, end_line)
      - blob_sha
      - commit_sha, author, date, message
      - is_head flag

  Scenario: Empty index handling
    Given a newly initialized LanceDB store
    When I query for statistics
    Then total_chunks should be 0
    And total_files should be 0
    And index_size_mb should be ~0

  Scenario: Storage location
    Given .gitctx directory in repo root
    When I initialize LanceDB
    Then database should be created at .gitctx/lancedb/
    And .gitctx should be in .gitignore
    And database files should not be committed to git
```

## Child Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.2.4.1](TASK-0001.2.4.1.md) | Write ALL 10 BDD Scenarios | ✅ | 2 | 0/10 (all failing) |
| [TASK-0001.2.4.2](TASK-0001.2.4.2.md) | Implement LanceDBStore with batch insertion | ✅ | 4 | 0/10 (BDD skipped) |
| [TASK-0001.2.4.3](TASK-0001.2.4.3.md) | Core Storage Operations & Indexing | ✅ | 3 | 0/10 (BDD skipped) |
| [TASK-0001.2.4.4](TASK-0001.2.4.4.md) | BDD Implementation & Final Integration | ✅ | 8 | 10/10 passing ✅ |

**Total**: 17 hours (revised from 12 due to inherited BDD technical debt)

## Technical Design

### Denormalized Schema

Following the architecture decision from STORY-0001.2.1, use denormalized schema for optimal read performance:

```python
# src/gitctx/storage/schema.py

import pyarrow as pa
from lancedb.pydantic import LanceModel, Vector

class CodeChunkRecord(LanceModel):
    """LanceDB document model for code chunks with denormalized metadata.

    Design Decision: Denormalized for single-query context retrieval.
    - Embed BlobLocation data directly in chunk records
    - 3.4% storage overhead vs normalized (PyArrow columnar compression)
    - 100x faster queries (no joins needed)
    - Optimal for read-heavy workload (searches >> updates)
    """

    # Schema Design: Embedding Model Flexibility
    #
    # Current: text-embedding-3-large (3072 dims, $0.13/1M tokens)
    # Future support: text-embedding-3-small (1536 dims, $0.02/1M tokens) for cost optimization
    #
    # Migration strategy:
    # 1. Schema versioning: Store embedding_model and dimensions in table metadata
    # 2. Dimension detection: Read from metadata on table open, validate on insert
    # 3. Model changes: Require full re-index (detected via metadata.embedding_model field)
    # 4. Multi-model support (post-MVP): Separate tables per model:
    #    - .gitctx/lancedb/text-embedding-3-large/ (3072 dims)
    #    - .gitctx/lancedb/text-embedding-3-small/ (1536 dims)
    #    - .gitctx/lancedb/text-embedding-ada-002/ (1536 dims, legacy)
    #    Query router selects table based on configured model
    #    Allows gradual migration: re-index subsets with different models for cost/quality tradeoffs

    # Vector and content
    vector: Vector(3072)  # Default: text-embedding-3-large (configurable via embedding_model metadata)
    chunk_content: str
    token_count: int

    # Chunk positioning
    blob_sha: str         # Links to git blob
    chunk_index: int      # Position within blob (0, 1, 2, ...)
    start_line: int       # Line number where chunk starts
    end_line: int         # Line number where chunk ends
    total_chunks: int     # Total chunks for this blob

    # File context (denormalized from BlobLocation)
    file_path: str        # Path in commit tree
    language: str         # Programming language

    # Commit context (denormalized from BlobLocation)
    commit_sha: str       # Commit where blob appears
    author_name: str      # Commit author
    author_email: str     # Commit author email
    commit_date: int      # Unix timestamp
    commit_message: str   # First line of commit message
    is_head: bool         # True if blob appears in HEAD tree
    is_merge: bool        # True if commit is a merge

    # Metadata
    embedding_model: str  # Model used (e.g., "text-embedding-3-large")
    indexed_at: str       # ISO timestamp when indexed


# PyArrow schema (for manual table creation)
CHUNK_SCHEMA = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), 3072)),
    pa.field("chunk_content", pa.string()),
    pa.field("token_count", pa.int32()),
    pa.field("blob_sha", pa.string()),
    pa.field("chunk_index", pa.int32()),
    pa.field("start_line", pa.int32()),
    pa.field("end_line", pa.int32()),
    pa.field("total_chunks", pa.int32()),
    pa.field("file_path", pa.string()),
    pa.field("language", pa.string()),
    pa.field("commit_sha", pa.string()),
    pa.field("author_name", pa.string()),
    pa.field("author_email", pa.string()),
    pa.field("commit_date", pa.int64()),
    pa.field("commit_message", pa.string()),
    pa.field("is_head", pa.bool_()),
    pa.field("is_merge", pa.bool_()),
    pa.field("embedding_model", pa.string()),
    pa.field("indexed_at", pa.string()),
])
```

### LanceDB Store Implementation

Following prototype pattern from `/Users/bram/Code/codectl-ai/gitctx`:

```python
# src/gitctx/storage/lancedb_store.py

import lancedb
import pyarrow as pa
from pathlib import Path
from datetime import UTC, datetime

class LanceDBStore:
    """LanceDB vector store with denormalized schema.

    Implementation notes from prototype:
    - Uses LanceDB's Rust-based embedded database
    - Automatic IVF-PQ indexing for >256 vectors
    - Zero-copy data sharing with PyArrow
    - Native versioning and time-travel capabilities
    - 100x faster than traditional vector stores
    """

    def __init__(self, db_path: Path):
        """Initialize LanceDB store.

        Args:
            db_path: Path to .gitctx/lancedb directory
        """
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Connect to LanceDB
        self.db = lancedb.connect(str(db_path))

        # Table names
        self.chunks_table_name = "code_chunks"
        self.metadata_table_name = "index_metadata"

        # Initialize tables
        self.chunks_table = None
        self.metadata_table = None
        self._init_tables()

    def _init_tables(self):
        """Initialize or open existing tables."""
        # Chunks table
        if self.chunks_table_name in self.db.table_names():
            self.chunks_table = self.db.open_table(self.chunks_table_name)
        else:
            # Create with schema
            self.chunks_table = self.db.create_table(
                self.chunks_table_name,
                schema=CHUNK_SCHEMA
            )

        # Metadata table for index state tracking
        if self.metadata_table_name in self.db.table_names():
            self.metadata_table = self.db.open_table(self.metadata_table_name)
        else:
            metadata_schema = pa.schema([
                pa.field("key", pa.string()),
                pa.field("last_commit", pa.string()),
                pa.field("indexed_blobs", pa.string()),  # JSON list
                pa.field("last_indexed", pa.string()),
                pa.field("embedding_model", pa.string()),
                pa.field("total_chunks", pa.int64()),
                pa.field("total_blobs", pa.int64()),
            ])
            self.metadata_table = self.db.create_table(
                self.metadata_table_name,
                schema=metadata_schema
            )

    def add_chunks_batch(
        self,
        embeddings: list[Embedding],
        blob_locations: dict[str, list[BlobLocation]]
    ):
        """Add chunks in batch with denormalized metadata.

        Args:
            embeddings: List of Embedding objects from embedder
            blob_locations: Map of blob_sha -> BlobLocation list (from walker)
        """
        records = []

        for emb in embeddings:
            # Get BlobLocation for this chunk's blob
            locations = blob_locations.get(emb.blob_sha, [])
            if not locations:
                logger.warning(f"No location found for blob {emb.blob_sha}")
                continue

            # Use first location (all have same file context)
            # In denormalized schema, we duplicate this per chunk
            loc = locations[0]

            record = {
                "vector": emb.vector,
                "chunk_content": emb.chunk_content,
                "token_count": emb.token_count,
                "blob_sha": emb.blob_sha,
                "chunk_index": emb.chunk_index,
                "start_line": emb.start_line,
                "end_line": emb.end_line,
                "total_chunks": emb.total_chunks,
                "file_path": loc.file_path,
                "language": emb.language,
                "commit_sha": loc.commit_sha,
                "author_name": loc.author_name,
                "author_email": loc.author_email,
                "commit_date": loc.commit_date,
                "commit_message": loc.commit_message,
                "is_head": loc.is_head,
                "is_merge": loc.is_merge,
                "embedding_model": emb.model,
                "indexed_at": datetime.now(UTC).isoformat(),
            }
            records.append(record)

        # Batch insert
        if records:
            self.chunks_table.add(records)
            logger.info(f"Inserted {len(records)} chunks into LanceDB")

    def optimize(self):
        """Create IVF-PQ index for fast vector search.

        Only creates index if we have enough vectors (>256).
        """
        row_count = self.count()

        if row_count < 256:
            logger.info(f"Not enough vectors ({row_count}) for indexing")
            return

        logger.info(f"Creating IVF-PQ index for {row_count} vectors...")

        self.chunks_table.create_index(
            metric="cosine",
            num_partitions=min(row_count // 256, 256),
            num_sub_vectors=min(3072 // 16, 96),  # For 3072-dim embeddings
        )

        logger.info("Vector index created successfully")

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filter_head_only: bool = False
    ) -> list[dict]:
        """Search for similar chunks.

        Args:
            query_vector: Query embedding (3072-dim)
            limit: Max results to return
            filter_head_only: Only return chunks from HEAD tree

        Returns:
            List of chunk records with all denormalized metadata
        """
        query = self.chunks_table.search(query_vector).limit(limit)

        if filter_head_only:
            query = query.where("is_head = true")

        results = query.to_pandas()
        return results.to_dict("records")

    def count(self) -> int:
        """Count total chunks in index."""
        if self.chunks_table is None:
            return 0
        return len(self.chunks_table.to_pandas())

    def save_index_state(
        self,
        last_commit: str,
        indexed_blobs: list[str],
        embedding_model: str
    ):
        """Save index state metadata.

        Args:
            last_commit: Git commit SHA from last indexing
            indexed_blobs: List of blob SHAs that were indexed
            embedding_model: Model used for embeddings
        """
        import json

        # Delete old state
        try:
            self.metadata_table.delete("key = 'index_state'")
        except:
            pass  # Table might be empty

        # Insert new state
        state = {
            "key": "index_state",
            "last_commit": last_commit,
            "indexed_blobs": json.dumps(indexed_blobs),
            "last_indexed": datetime.now(UTC).isoformat(),
            "embedding_model": embedding_model,
            "total_chunks": self.count(),
            "total_blobs": len(indexed_blobs),
        }

        self.metadata_table.add([state])
        logger.info(f"Saved index state: {len(indexed_blobs)} blobs")

    def get_statistics(self) -> dict:
        """Get index statistics."""
        df = self.chunks_table.to_pandas()

        return {
            "total_chunks": len(df),
            "total_files": df["file_path"].nunique(),
            "total_blobs": df["blob_sha"].nunique(),
            "languages": df["language"].value_counts().to_dict(),
            "index_size_mb": self._get_db_size_mb(),
        }

    def _get_db_size_mb(self) -> float:
        """Calculate database size in MB."""
        total = sum(
            f.stat().st_size
            for f in self.db_path.rglob("*")
            if f.is_file()
        )
        return total / (1024 * 1024)
```

### Embedding Model Configuration (Future-Proofing)

Store embedding model metadata with table for schema evolution:

```python
# Table metadata (stored in LanceDB)
metadata = {
    "embedding_model": "text-embedding-3-large",
    "embedding_dimensions": 3072,
    "cost_per_million_tokens": 0.13,
    "created_at": "2025-10-07T...",
    "schema_version": 1
}

# On table open: validate incoming vectors match metadata.embedding_dimensions
# On model change: detect via metadata.embedding_model, require re-index
```

**Post-MVP multi-model support:**

Table names match embedding model for extreme clarity:
- `.gitctx/lancedb/text-embedding-3-large/` (3072 dims, current default)
- `.gitctx/lancedb/text-embedding-3-small/` (1536 dims, cost optimization)
- `.gitctx/lancedb/text-embedding-ada-002/` (1536 dims, legacy support)

Query router selects table based on user's configured `embedding_model` setting.
Allows gradual migration: re-index subsets of codebase with different models for cost/quality tradeoffs.

**Configuration integration:**

Add to `IndexSettings` in `RepoConfig` (STORY-0001.2.2):

```python
embedding_model: str = Field(
    default="text-embedding-3-large",
    description="OpenAI embedding model (determines table name and vector dimensions: 3-large=3072, 3-small=1536)"
)
```

### Integration with Pipeline

```python
# Pipeline orchestration (implements full indexing flow):

from gitctx.core.commit_walker import CommitWalker, BlobRecord
from gitctx.core.chunker import create_chunker
from gitctx.core.embedder import create_embedder
from gitctx.storage.lancedb_store import LanceDBStore
from gitctx.indexer.embedding_cache import EmbeddingCache

# Initialize components
walker = CommitWalker(repo_path=".", config=settings)
chunker = create_chunker(chunk_overlap_ratio=0.2)
cache = EmbeddingCache(Path(".gitctx"), "text-embedding-3-large", "3072")
embedder = create_embedder(api_key=settings.api_keys.openai, cache=cache)
store = LanceDBStore(Path(".gitctx/lancedb"))

# Track all blob locations for denormalization
all_blob_locations = {}

# Process each blob
for blob_record in walker.walk():
    # Track locations for denormalization later
    all_blob_locations[blob_record.sha] = blob_record.locations

    # Chunk blob
    chunks = chunker.chunk_file(
        content=blob_record.content.decode("utf-8"),
        language=detect_language(blob_record.locations[0].file_path),
        max_tokens=800
    )

    # Generate embeddings (with caching)
    embedding_batch = await embedder.embed_chunks(chunks, blob_record.sha)

    # Store with denormalized BlobLocation metadata
    store.add_chunks_batch(
        embeddings=embedding_batch.embeddings,
        blob_locations={blob_record.sha: blob_record.locations}
    )

# Optimize index
store.optimize()

# Save index state
walker_stats = walker.get_stats()
store.save_index_state(
    last_commit=repo.head.target.hex,
    indexed_blobs=list(all_blob_locations.keys()),
    embedding_model="text-embedding-3-large"
)

# Print statistics
stats = store.get_statistics()
print(f"Indexed {stats['total_chunks']} chunks from {stats['total_blobs']} blobs")
print(f"Cost: ${embedder.total_cost_usd:.4f}")
```

## Dependencies

### External Libraries

- `lancedb>=0.3.0` - Embedded vector database
- `pyarrow>=14.0.0` - Arrow schema and zero-copy data

### Internal Dependencies

- **STORY-0001.2.1** (Commit Graph Walker) - Provides BlobRecord with locations ✅
- **STORY-0001.2.2** (Blob Chunking) - Provides chunks to embed
- **STORY-0001.2.3** (OpenAI Embeddings) - Provides embeddings to store

### Downstream Consumers

- **EPIC-0001.3** (Vector Search) - Will query this storage

## Pattern Reuse

From prototype analysis:

**Existing Components** (reuse these):
- LanceDB schema patterns from `src/gitctx/vector_store/lancedb_store.py`
- Metadata tracking from `IndexMetadataDocument` pattern

**Test Fixtures** (reuse these):
- `temp_git_repo` for integration tests

**Anti-Patterns to Avoid**:
- ❌ Normalized schema (breaks single-query context retrieval)
- ❌ Storing embeddings as numpy arrays (use list[float])
- ❌ Manual index creation (use LanceDB auto-indexing)

## Success Criteria

Story is complete when:

- ✅ All 4 tasks implemented and tested
- ✅ All 10 BDD scenarios pass
- ✅ Unit test coverage >90%
- ✅ Can store 10K chunks in <30 seconds
- ✅ Query returns complete context without joins
- ✅ IVF-PQ index auto-creates at 256+ vectors
- ✅ Integration: Works with embedder output
- ✅ Quality gates: ruff + mypy + pytest all pass

## Performance Targets

- Insertion speed: >300 chunks/second (batched)
- Search latency: <100ms for top-10 results
- Index size: ~150MB for 10K chunks (3072-dim)
- Denormalization overhead: <5% vs normalized

## Notes

- Denormalized schema is a deliberate trade-off (see STORY-0001.2.1 ADR)
- LanceDB's columnar compression makes denormalization cheap (~3.4% overhead)
- Single-query context retrieval is 100x faster than joins
- IVF-PQ indexing is automatic and adaptive
- Store in `.gitctx/lancedb/` (add to .gitignore)

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
