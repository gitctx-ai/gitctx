"""Protocols for embedding model providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from gitctx.indexing.types import CodeChunk, Embedding


class EmbedderProtocol(Protocol):
    """Protocol for embedding generation - provider-agnostic interface.

    This protocol enables swapping embedding providers (OpenAI, local models, etc.)
    without changing consuming code. All providers must implement these methods.

    Design principles:
    - Provider-agnostic: Works with any embedding API or local model
    - Async-ready: Can be implemented with async methods
    - Type-safe: Returns typed Embedding objects

    Examples:
        >>> embedder: EmbedderProtocol = OpenAIEmbedder(api_key="...")
        >>> embeddings = await embedder.embed_chunks(chunks, "blob_abc123")
        >>> len(embeddings)
        5
    """

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],  # list[CodeChunk] from indexing.types
        blob_sha: str,
    ) -> list[Embedding]:  # list[Embedding] from indexing.types
        """Generate embeddings for code chunks.

        Args:
            chunks: List of CodeChunk objects to embed
            blob_sha: Blob SHA for metadata tracking

        Returns:
            List of Embedding objects with vectors and metadata

        Examples:
            >>> chunks = [CodeChunk(content="def foo(): pass", ...)]
            >>> embeddings = await embedder.embed_chunks(chunks, "abc123")
            >>> len(embeddings[0].vector)
            3072
        """
        ...

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost in USD for embedding token_count tokens.

        Args:
            token_count: Number of tokens to embed

        Returns:
            Estimated cost in USD

        Examples:
            >>> embedder.estimate_cost(1000)
            0.00013
        """
        ...
