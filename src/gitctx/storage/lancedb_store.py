"""LanceDB vector store implementation.

This module provides a LanceDB-based vector store with denormalized schema for
optimal read performance in semantic code search.
"""

import logging
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

from gitctx.core.exceptions import DimensionMismatchError
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
        db_path: Path to .gitctx/lancedb directory
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
            db_path: Path to .gitctx/lancedb directory
            embedding_model: Model name for metadata tracking
            embedding_dimensions: Vector dimensions for validation
        """
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions

        # Create directory if it doesn't exist
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
            DimensionMismatchError: If dimensions don't match
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
                f"but current model '{self.embedding_model}' produces {self.embedding_dimensions}-dimensional vectors. "
                f"Action required: Delete .gitctx/lancedb/ and re-index with `gitctx index --force`"
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
            Dict with keys: total_chunks, total_files, total_blobs, index_size_mb
        """
        try:
            assert self.chunks_table is not None
            df = self.chunks_table.to_pandas()

            if len(df) == 0:
                return {
                    "total_chunks": 0,
                    "total_files": 0,
                    "total_blobs": 0,
                    "index_size_mb": self._get_db_size_mb(),
                }

            return {
                "total_chunks": len(df),
                "total_files": df["file_path"].nunique(),
                "total_blobs": df["blob_sha"].nunique(),
                "index_size_mb": self._get_db_size_mb(),
            }
        except Exception:
            # If table is empty or conversion fails, return zeros
            return {
                "total_chunks": 0,
                "total_files": 0,
                "total_blobs": 0,
                "index_size_mb": self._get_db_size_mb(),
            }

    def _get_db_size_mb(self) -> float:
        """Calculate database size in MB.

        Returns:
            Database size in megabytes
        """
        total = sum(f.stat().st_size for f in self.db_path.rglob("*") if f.is_file())
        return total / (1024 * 1024)

    def add_chunks_batch(self, embeddings: list[Any], blob_locations: dict[str, list[Any]]) -> None:
        """Add chunks in batch with denormalized metadata.

        Args:
            embeddings: List of Embedding objects from embedder
            blob_locations: Map of blob_sha -> BlobLocation list (from walker)
        """
        # This will be implemented in TASK-0001.2.4.3
        raise NotImplementedError("add_chunks_batch will be implemented in next task")

    def optimize(self) -> None:
        """Create IVF-PQ index for fast vector search."""
        # This will be implemented in TASK-0001.2.4.3
        raise NotImplementedError("optimize will be implemented in next task")

    def search(
        self, query_vector: list[float], limit: int = 10, filter_head_only: bool = False
    ) -> list[dict[str, Any]]:
        """Search for similar chunks.

        Args:
            query_vector: Query embedding vector
            limit: Max results to return
            filter_head_only: Only return chunks from HEAD tree

        Returns:
            List of chunk records with all denormalized metadata
        """
        # This will be implemented in TASK-0001.2.4.3
        raise NotImplementedError("search will be implemented in next task")

    def save_index_state(
        self, last_commit: str, indexed_blobs: list[str], embedding_model: str
    ) -> None:
        """Save index state metadata.

        Args:
            last_commit: Git commit SHA from last indexing
            indexed_blobs: List of blob SHAs that were indexed
            embedding_model: Model used for embeddings
        """
        # This will be implemented in TASK-0001.2.4.3
        raise NotImplementedError("save_index_state will be implemented in next task")
