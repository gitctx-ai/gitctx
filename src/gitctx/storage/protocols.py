"""Protocol definitions for vector storage interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import numpy as np

    from gitctx.indexing.types import SearchResult


class VectorStoreProtocol(Protocol):
    """Protocol defining the interface for vector storage implementations.

    This protocol ensures consistent API across different vector store backends
    (LanceDB, Qdrant, Pinecone, etc.) while allowing implementation-specific
    optimizations.
    """

    def add_chunks_batch(self, embeddings: list[Any], blob_locations: dict[str, list[Any]]) -> None:
        """Add chunks in batch with denormalized metadata.

        Args:
            embeddings: List of Embedding objects from embedder
            blob_locations: Map of blob_sha -> BlobLocation list (from walker)
        """
        ...

    def optimize(self) -> None:
        """Create or update vector index for fast search.

        Implementation-specific: LanceDB uses IVF-PQ, others may differ.
        """
        ...

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
        ...

    def count(self) -> int:
        """Count total chunks in index.

        Returns:
            Number of chunks stored
        """
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dict with keys: total_chunks, total_files, total_blobs, etc.
        """
        ...

    def save_index_state(
        self, last_commit: str, indexed_blobs: list[str], embedding_model: str
    ) -> None:
        """Save index state metadata.

        Args:
            last_commit: Git commit SHA from last indexing
            indexed_blobs: List of blob SHAs that were indexed
            embedding_model: Model used for embeddings
        """
        ...


class SearchStrategy(Protocol):
    """Protocol for search implementations - storage-agnostic search interface.

    This protocol abstracts search operations across different storage backends
    (LanceDB, Qdrant, Pinecone) enabling hybrid search, semantic search, or other
    search strategies without breaking changes to consuming code.

    Design principles:
    - Intentionally minimal (no lifecycle methods like initialize/close)
    - Storage backend manages its own connection lifecycle
    - Returns SearchResult dataclass with primitive types for FFI compatibility
    - Enables future search strategies (filtered search, faceted search, reranking)

    Note: This protocol does NOT include lifecycle methods. Implementations like
    LanceDBStore manage their own connection lifecycle via __init__/table property.
    """

    def search(
        self,
        query_vector: np.ndarray,
        query_text: str,
        limit: int = 10,
        filter_head_only: bool = False,
        max_distance: float = 1.0,
    ) -> list[SearchResult]:
        """Execute search and return ranked results.

        Args:
            query_vector: Query embedding vector (np.ndarray)
            query_text: Query text for keyword search (BM25) - required for hybrid search
            limit: Maximum number of results to return (default: 10)
            filter_head_only: If True, only return chunks from HEAD tree (default: False)
            max_distance: Maximum cosine distance threshold, 1.0 - min_similarity (default: 1.0)

        Returns:
            List of SearchResult objects, ranked by relevance
            (hybrid score, vector score, or BM25 score)

        Examples:
            >>> searcher.search(
            ...     query_vector=np.array([0.1, 0.2, ...]),  # 3072-dim vector
            ...     query_text="authentication middleware",
            ...     limit=5,
            ...     filter_head_only=True,
            ...     max_distance=0.5
            ... )
            [SearchResult(file_path="auth.py", distance=0.12, hybrid_score=0.95, ...), ...]
        """
        ...
