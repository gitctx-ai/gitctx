"""Protocol definitions for vector storage interfaces."""

from typing import Any, Protocol


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
