"""LanceDB vector store implementation.

This module provides a LanceDB-based vector store with denormalized schema for
optimal read performance in semantic code search.
"""
# ruff: noqa: PLC0415 # Lazy load LanceDB/pyarrow (heavy dependencies)

import logging
from pathlib import Path
from typing import Any

import lancedb
import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from gitctx.git.types import BlobLocation
from gitctx.indexing.types import Embedding, SearchResult
from gitctx.models.errors import DimensionMismatchError
from gitctx.search.git_head_booster import GitHeadBooster
from gitctx.storage.schema import CHUNK_SCHEMA

logger = logging.getLogger(__name__)


class LanceDBStore:
    """LanceDB vector store with denormalized schema.

    Implementation notes from prototype:
    - Uses LanceDB's Rust-based embedded database
    - Automatic IVF-PQ indexing for >256 vectors
    - Zero-copy data sharing with PyArrow
    - Native versioning and time-travel capabilities
    - 100x faster than traditional vector stores

    Attributes:
        db_path: Path to .gitctx/db/lancedb directory
        db: LanceDB connection
        chunks_table: Main table for code chunks with embeddings
        metadata_table: Table for index state tracking
        embedding_model: Model name (e.g., "text-embedding-3-large")
        embedding_dimensions: Vector dimensions (e.g., 3072)
    """

    def __init__(
        self,
        db_path: Path,
        embedding_model: str = "text-embedding-3-large",
        embedding_dimensions: int = 3072,
    ):
        """Initialize LanceDB store.

        Args:
            db_path: Path to .gitctx/db/lancedb directory
            embedding_model: Model name for metadata tracking
            embedding_dimensions: Vector dimensions for validation
        """
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions

        # Create directory if it doesn't exist
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Connect to LanceDB
        # Use as_posix() to ensure cross-platform path compatibility
        connect_path = str(db_path.as_posix())
        self.db = lancedb.connect(connect_path)

        # Table names
        self.chunks_table_name = "code_chunks"
        self.metadata_table_name = "index_metadata"

        # Initialize tables
        self.chunks_table = None
        self.metadata_table = None
        self._init_tables()

        # Initialize GitHeadBooster for search ranking
        self.booster = GitHeadBooster(head_multiplier=1.5)

    def _init_tables(self) -> None:
        """Initialize or open existing tables."""
        # Chunks table
        if self.chunks_table_name in self.db.table_names():
            self.chunks_table = self.db.open_table(self.chunks_table_name)
            # Validate dimensions if table has metadata
            self._validate_dimensions()
        else:
            # Create with schema and metadata
            self.chunks_table = self.db.create_table(self.chunks_table_name, schema=CHUNK_SCHEMA)
            # Store metadata
            self._set_table_metadata()

        # Metadata table for index state tracking
        if self.metadata_table_name in self.db.table_names():
            self.metadata_table = self.db.open_table(self.metadata_table_name)
        else:
            metadata_schema = pa.schema(
                [
                    pa.field("key", pa.string()),
                    pa.field("last_commit", pa.string()),
                    pa.field("indexed_blobs", pa.string()),  # JSON list
                    pa.field("last_indexed", pa.string()),
                    pa.field("embedding_model", pa.string()),
                    pa.field("total_chunks", pa.int64()),
                    pa.field("total_blobs", pa.int64()),
                ]
            )
            self.metadata_table = self.db.create_table(
                self.metadata_table_name, schema=metadata_schema
            )

    def _set_table_metadata(self) -> None:
        """Set table metadata for dimension tracking."""
        # Note: LanceDB table.schema.metadata is immutable after creation
        # For now, we'll track dimensions in the metadata table
        # This is a known limitation that will be addressed in future versions
        logger.info(
            f"Initialized table with {self.embedding_dimensions}-dim vectors "
            f"({self.embedding_model})"
        )

    def _validate_dimensions(self) -> None:
        """Validate that table dimensions match expected dimensions.

        Raises:
            DimensionMismatchError: If dimensions don't match.
                The error message includes:
                    - The actual dimensions of the existing table vectors
                    - The expected dimensions produced by the current model
                    - The name of the embedding model
                    - A suggested action to delete the LanceDB directory and re-index
                Example error message:
                    "Dimension mismatch: existing table has {actual_dims}-dimensional vectors,
                    but current model '{self.embedding_model}' produces
                    {self.embedding_dimensions}-dimensional vectors. Action required: Delete
                    .gitctx/db/lancedb/ and re-index with `gitctx index --force`"
        """
        # Get vector field from schema
        try:
            assert self.chunks_table is not None
            vector_field = self.chunks_table.schema.field("vector")
            actual_dims = vector_field.type.list_size
        except Exception as e:
            logger.warning(f"Could not validate dimensions: {e}")
            return

        if actual_dims != self.embedding_dimensions:
            raise DimensionMismatchError(
                f"Dimension mismatch: existing table has {actual_dims}-dimensional vectors, "
                f"but current model '{self.embedding_model}' produces "
                f"{self.embedding_dimensions}-dimensional vectors. "
                f"Action required: Delete .gitctx/db/lancedb/ and re-index with "
                f"`gitctx index --force`"
            )

    def count(self) -> int:
        """Count total chunks in index.

        Returns:
            Number of chunks stored
        """
        if self.chunks_table is None:
            return 0

        try:
            # LanceDB count is fast (metadata operation)
            return self.chunks_table.count_rows()
        except Exception:
            # If table is empty or has issues, return 0
            return 0

    def get_statistics(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dict with keys: total_chunks, total_files, total_blobs, languages, index_size_mb
        """
        from collections import Counter

        try:
            assert self.chunks_table is not None
            # Use PyArrow table for efficient columnar operations
            arrow_table = self.chunks_table.to_arrow()

            if arrow_table.num_rows == 0:
                return {
                    "total_chunks": 0,
                    "total_files": 0,
                    "total_blobs": 0,
                    "languages": {},
                    "index_size_mb": self._get_db_size_mb(),
                }

            # Convert relevant columns to Python lists for aggregation
            file_paths = arrow_table.column("file_path").to_pylist()
            blob_shas = arrow_table.column("blob_sha").to_pylist()
            languages = arrow_table.column("language").to_pylist()

            return {
                "total_chunks": arrow_table.num_rows,
                "total_files": len(set(file_paths)),
                "total_blobs": len(set(blob_shas)),
                "languages": dict(Counter(languages)),
                "index_size_mb": self._get_db_size_mb(),
            }
        except Exception:
            # If table is empty or conversion fails, return zeros
            return {
                "total_chunks": 0,
                "total_files": 0,
                "total_blobs": 0,
                "languages": {},
                "index_size_mb": self._get_db_size_mb(),
            }

    def _get_db_size_mb(self) -> float:
        """Calculate database size in MB.

        Returns:
            Database size in megabytes
        """
        total = sum(f.stat().st_size for f in self.db_path.rglob("*") if f.is_file())
        return total / (1024 * 1024)

    def add_chunks_batch(
        self, embeddings: list[Embedding], blob_locations: dict[str, list[BlobLocation]]
    ) -> None:
        """Add chunks in batch with denormalized metadata.

        Args:
            embeddings: List of Embedding objects from embedder
            blob_locations: Map of blob_sha -> BlobLocation list (from walker)
        """
        from datetime import UTC, datetime

        records = []
        skipped_count = 0
        skipped_blob_shas = []
        for emb in embeddings:
            # Get BlobLocation for this chunk's blob
            locations = blob_locations.get(emb.blob_sha, [])
            if not locations:
                logger.warning(f"No location found for blob {emb.blob_sha[:8]}... - skipping chunk")
                skipped_count += 1
                skipped_blob_shas.append(emb.blob_sha[:8])
                continue

            # Use most recent location by commit_date (when blob appears in multiple commits)
            loc = max(locations, key=lambda location: location.commit_date)

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
            assert self.chunks_table is not None
            self.chunks_table.add(records)
            logger.info(f"Inserted {len(records)} chunks into LanceDB")
        elif skipped_count > 0:
            logger.warning(
                f"Skipped {skipped_count} chunks with no blob location: "
                f"{', '.join(skipped_blob_shas)}"
            )

    def optimize(self) -> None:
        """Create indexes for fast hybrid search (vector + BM25).

        Creates two indexes:
        1. INVERTED index for BM25 full-text search (required for hybrid search)
        2. IVF-PQ index for vector search (only if row_count >= 256)

        The INVERTED index is always created because hybrid search requires it
        for BM25 keyword matching. The IVF-PQ index is only created for larger
        datasets where it provides performance benefits.
        """
        row_count = self.count()
        assert self.chunks_table is not None

        # Always create INVERTED index for BM25 (hybrid search requirement)
        logger.info(f"Creating INVERTED index for BM25 search ({row_count} vectors)...")
        self.chunks_table.create_fts_index("chunk_content")
        logger.info("INVERTED index created successfully")

        # Create IVF-PQ index for vector search only if enough vectors
        MIN_VECTORS_FOR_INDEX = 256  # Minimum rows required for IVF-PQ indexing
        if row_count >= MIN_VECTORS_FOR_INDEX:
            logger.info(f"Creating IVF-PQ vector index for {row_count} vectors...")
            self.chunks_table.create_index(
                metric="cosine",
                num_partitions=min(row_count // 256, 256),
                num_sub_vectors=min(self.embedding_dimensions // 16, 96),
            )
            logger.info("IVF-PQ vector index created successfully")
        else:
            logger.info(
                f"Skipping IVF-PQ index ({row_count} vectors < {MIN_VECTORS_FOR_INDEX} minimum)"
            )

    def search(
        self,
        query_vector: list[float],
        query_text: str,
        limit: int = 10,
        filter_head_only: bool = False,
        max_distance: float = 2.0,
    ) -> list[SearchResult]:
        """Hybrid search using BM25 + vector search with RRF (Reciprocal Rank Fusion).

        Combines keyword matching (BM25) and semantic similarity (vector search) to find
        both exact matches and conceptually related code. Uses RRF at K=60 (LanceDB default)
        to merge rankings from both approaches.

        **Hybrid Search Benefits**:

        - Keyword matches: Finds exact class names, function names, variable names
        - Semantic matches: Finds conceptually similar code even with different terminology
        - RRF fusion: Balances both signals without manual weight tuning

        **Similarity Scoring**:

        LanceDB uses cosine distance for vector similarity (not cosine similarity).
        The relationship between these metrics is:

        - cosine_distance = 1 - cosine_similarity
        - cosine_similarity range: -1 (opposite) to 1 (identical)
        - cosine_distance range: 0 (identical) to 2 (maximally dissimilar)

        Lower distances indicate higher similarity. For example:
        - distance 0.0 = perfect match (similarity 1.0)
        - distance 0.3 = highly similar (similarity 0.7)
        - distance 0.5 = moderately similar (similarity 0.5)
        - distance 1.0 = unrelated (similarity 0.0)
        - distance 2.0 = opposite meaning (similarity -1.0)

        **Score Breakdown**:

        Each SearchResult includes three score fields for analysis/debugging:
        - bm25_score: BM25 keyword score (_score field, higher = better match)
        - vector_score: Cosine similarity (1.0 - _distance, 0-1 range)
            For BM25-only matches without vector component, vector_score = -inf
        - hybrid_score: RRF combined score (_relevance_score, 0-1 range, higher = more relevant)

        Note: For rare BM25-only matches (no vector match), distance = inf and vector_score = -inf

        **Post-Filtering**:

        LanceDB does not support WHERE clauses on the _distance field returned by
        vector search (this is a current limitation). Therefore, we apply distance
        filtering after retrieving results using Python filtering:

        1. LanceDB returns top-N results sorted by hybrid relevance
        2. Python filters: keep only results where _distance <= max_distance
        3. Return filtered results (may be fewer than limit if many exceed threshold)

        This pattern is recommended by LanceDB maintainers for distance-based filtering.
        Reference: https://github.com/lancedb/lancedb/issues/745

        **RRF (Reciprocal Rank Fusion)**:

        Uses K=60 constant (LanceDB research-backed default, no tuning needed).
        RRF score formula: sum(1 / (k + rank_i)) for each ranker
        Higher RRF score = more relevant result across both BM25 and vector rankings.

        **Technical References**:

        - LanceDB hybrid search: https://lancedb.github.io/lancedb/hybrid_search/
        - Cosine distance metric: https://lancedb.com/docs/search/vector-search/#distance-metrics
        - Post-filtering pattern: https://github.com/lancedb/lancedb/issues/745
        - RRF reranking: https://lancedb.github.io/lancedb/reranking/

        Args:
            query_vector: Query embedding vector (must match table dimensions)
            query_text: Query text for BM25 keyword search (required, cannot be empty)
            limit: Maximum results to return BEFORE filtering (LanceDB retrieves top-N)
            filter_head_only: Only return chunks from HEAD commit (WHERE clause)
            max_distance: Maximum cosine distance threshold (0.0-2.0).
                         Results with _distance > max_distance are filtered out.
                         Default: 2.0 (no filtering, all results returned)
                         Example: 0.3 keeps only highly similar results (similarity >= 0.7)

        Returns:
            List of SearchResult objects with score breakdown, ranked by hybrid relevance.
            Each SearchResult includes:
            - All chunk fields: chunk_content, file_path, language, etc.
            - All git metadata: commit_sha, author_name, commit_date, etc.
            - Score breakdown: bm25_score, vector_score, hybrid_score

        Example:
            >>> # Hybrid search (keyword + semantic)
            >>> results = store.search(
            ...     query_vector=embedding,
            ...     query_text="authentication middleware",
            ...     limit=10
            ... )
            >>> # Get highly relevant results only (similarity >= 0.7)
            >>> results = store.search(
            ...     query_vector=embedding,
            ...     query_text="JWT auth",
            ...     limit=10,
            ...     max_distance=0.3
            ... )
        """
        # Validate query_text is not empty (required for BM25 keyword matching)
        if not query_text or not query_text.strip():
            msg = "Hybrid search requires non-empty query_text for BM25 keyword matching"
            raise ValueError(msg)

        from lancedb import rerankers

        assert self.chunks_table is not None

        # Create RRF reranker (K=60 is research-backed default, no tuning needed)
        # return_score='all' returns _distance, _score, and _relevance_score fields
        rrf = rerankers.RRFReranker(K=60, return_score="all")

        # Build hybrid search query
        query = (
            self.chunks_table.search(query_type="hybrid")
            .vector(query_vector)  # Vector component
            .text(query_text)  # Text component (required for BM25)
            .limit(limit)
            .rerank(rrf)  # Apply RRF fusion
        )

        if filter_head_only:
            query = query.where("is_head = true")

        # Execute query and get results
        results = query.to_list()

        # Convert to SearchResult objects first (before filtering/boosting)
        search_results = []
        for result in results:
            # Extract score breakdown from LanceDB response
            # LanceDB returns internal fields (_distance, _score, _relevance_score)
            # We map these to public SearchResult fields (distance, bm25_score, hybrid_score)
            # Note: In hybrid search, _distance can theoretically be None for BM25-only matches
            # Use float('inf') to represent "no vector similarity" (infinite distance)
            raw_distance = result.get("_distance")
            distance = raw_distance if raw_distance is not None else float("inf")
            # -inf for no vector match (BM25-only results)
            vector_score = 1.0 - distance if distance != float("inf") else -float("inf")
            bm25_score = result.get("_score")  # BM25 score (may be None)
            hybrid_score = result.get("_relevance_score")  # RRF combined score

            search_result = SearchResult(
                # Core chunk fields (mapped from LanceDB schema)
                chunk_content=result["chunk_content"],
                file_path=result["file_path"],
                distance=distance,  # Mapped from _distance (underscore removed for public API)
                commit_sha=result["commit_sha"],
                token_count=result["token_count"],
                blob_sha=result["blob_sha"],
                chunk_index=result["chunk_index"],
                start_line=result["start_line"],
                end_line=result["end_line"],
                total_chunks=result["total_chunks"],
                language=result["language"],
                # Git metadata fields
                author_name=result["author_name"],
                author_email=result["author_email"],
                commit_date=result["commit_date"],
                commit_message=result["commit_message"],
                is_head=result["is_head"],
                is_merge=result["is_merge"],
                # Score breakdown fields (mapped from LanceDB internal fields)
                bm25_score=bm25_score,  # Mapped from _score
                vector_score=vector_score,  # Computed from _distance
                hybrid_score=hybrid_score,  # Mapped from _relevance_score
            )
            search_results.append(search_result)

        # Apply HEAD boost (1.5x multiplier for HEAD chunks)
        boosted_results = self.booster.boost(search_results)

        # Post-filter by distance (LanceDB doesn't support WHERE on _distance)
        # Apply after boosting to maintain correct filtering behavior
        # Note: _distance can be None for BM25-only matches in hybrid search - keep those
        # Reference: https://github.com/lancedb/lancedb/issues/745
        filtered_results = [
            r for r in boosted_results if r.distance == float("inf") or r.distance <= max_distance
        ]

        # Re-rank by boosted hybrid_score (descending)
        ranked_results = sorted(filtered_results, key=lambda r: r.hybrid_score, reverse=True)

        # Apply limit
        return ranked_results[:limit]

    def save_index_state(
        self, last_commit: str, indexed_blobs: list[str], embedding_model: str
    ) -> None:
        """Save index state metadata.

        Uses upsert pattern: delete old state, insert new state.

        Args:
            last_commit: Git commit SHA from last indexing
            indexed_blobs: List of blob SHAs that were indexed
            embedding_model: Model used for embeddings (e.g., "text-embedding-3-large")
        """
        import json
        from contextlib import suppress
        from datetime import UTC, datetime

        # Delete old state (upsert pattern)
        # Table might be empty on first save - that's OK
        assert self.metadata_table is not None  # Always initialized in __init__
        with suppress(Exception):
            self.metadata_table.delete("key = 'index_state'")

        # Insert new state
        state = {
            "key": "index_state",
            "last_commit": last_commit,
            "indexed_blobs": json.dumps(indexed_blobs),  # Store as JSON string
            "last_indexed": datetime.now(UTC).isoformat(),
            "embedding_model": embedding_model,
            "total_chunks": self.count(),
            "total_blobs": len(indexed_blobs),
        }

        self.metadata_table.add([state])
        logger.info(f"Saved index state: {len(indexed_blobs)} blobs indexed at {last_commit[:8]}")

    def get_query_embedding(self, cache_key: str) -> NDArray[np.floating] | None:  # type: ignore[no-any-unimported]
        """Check if query embedding cached.

        Args:
            cache_key: SHA256 hash of (query_text + model_name)

        Returns:
            Cached embedding vector (float32 array) or None if not found
        """
        try:
            table = self.db.open_table("query_embeddings")
            results = table.search().where(f"cache_key = '{cache_key}'").limit(1).to_list()
            return np.array(results[0]["embedding"]) if results else None
        except Exception:
            # Table doesn't exist yet or query not found
            return None

    def cache_query_embedding(  # type: ignore[no-any-unimported]
        self,
        cache_key: str,
        query_text: str,
        embedding: NDArray[np.floating],
        model_name: str,
    ) -> None:
        """Store query embedding with metadata.

        Concurrency: LanceDB operations are atomic at the operation level (each `table.add()`
        completes fully or not at all). However, LanceDB does NOT support concurrent writes
        from multiple processes - if multiple processes try to write simultaneously, some
        operations may fail. For query caching, this is acceptable: failures are rare and
        users can simply retry their query.

        Note: There is no explicit transaction API in LanceDB Python SDK. The atomicity
        guarantee applies to individual operations only.

        Args:
            cache_key: SHA256 hash for lookup
            query_text: Original query (for debugging)
            embedding: Embedding vector
            model_name: Model used to generate embedding
        """
        import time

        # Create table if doesn't exist
        try:
            table = self.db.open_table("query_embeddings")
        except Exception:
            # Create table with schema
            query_schema = pa.schema(
                [
                    pa.field("cache_key", pa.string()),
                    pa.field("query_text", pa.string()),
                    pa.field("embedding", pa.list_(pa.float32(), 3072)),
                    pa.field("model_name", pa.string()),
                    pa.field("created_at", pa.float64()),
                ]
            )
            table = self.db.create_table("query_embeddings", schema=query_schema)

        # Insert with atomic operation (completes fully or fails)
        # Multiple concurrent processes may conflict, but this is rare for cache usage
        table.add(
            [
                {
                    "cache_key": cache_key,
                    "query_text": query_text,
                    "embedding": embedding.tolist(),
                    "model_name": model_name,
                    "created_at": time.time(),
                }
            ]
        )
