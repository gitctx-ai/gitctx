"""OpenAI embedding generator using LangChain wrapper."""
# ruff: noqa: PLC0415 # Dynamic OpenAI client import (lazy load)

from __future__ import annotations

from typing import Any

import numpy as np
from langchain_openai import OpenAIEmbeddings
from numpy.typing import NDArray
from pydantic import SecretStr

from gitctx.config.errors import ConfigurationError
from gitctx.indexing.types import CodeChunk, Embedding
from gitctx.models.errors import DimensionMismatchError


class OpenAIEmbedder:
    """OpenAI embedding generator wrapping LangChain.

    This class wraps LangChain's OpenAIEmbeddings to generate embeddings
    for code chunks using OpenAI's text-embedding-3-large model.

    Design notes:
    - Uses LangChain for API abstraction and retry logic
    - Validates embedding dimensions match expected 3072
    - Tracks cost using OpenAI pricing ($0.13 per 1M tokens)
    - Batches requests efficiently (max 2048 chunks per batch)
    - API key validation delegated to OpenAI SDK

    Attributes:
        MODEL: OpenAI model name (text-embedding-3-large)
        DIMENSIONS: Expected embedding dimensions (3072)
        COST_PER_MILLION_TOKENS: Cost in USD per 1M tokens ($0.13)
        MAX_BATCH_SIZE: Maximum chunks per API batch (2048)

    Examples:
        >>> embedder = OpenAIEmbedder(api_key="sk-...")
        >>> chunks = [CodeChunk(...), CodeChunk(...)]
        >>> embeddings = await embedder.embed_chunks(chunks, "abc123")
        >>> cost = embedder.estimate_cost(1000)  # $0.00013
    """

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 3072
    COST_PER_MILLION_TOKENS = 0.13
    MAX_BATCH_SIZE = 2048

    def __init__(
        self, api_key: str, max_retries: int = 3, show_progress: bool = False, **kwargs: Any
    ) -> None:
        """Initialize embedder with OpenAI API key.

        Args:
            api_key: OpenAI API key
            max_retries: Maximum retry attempts for API calls (default: 3)
            show_progress: Show progress bar during embedding (default: False)
            **kwargs: Additional arguments passed to OpenAIEmbeddings

        Raises:
            ConfigurationError: If API key is missing

        Examples:
            >>> embedder = OpenAIEmbedder(api_key="sk-test123")
            >>> embedder = OpenAIEmbedder(api_key="sk-...", max_retries=5)

        Note:
            API key format is not validated - OpenAI SDK will handle validation.
        """
        if not api_key:
            raise ConfigurationError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or configure in settings."
            )

        self._embeddings = OpenAIEmbeddings(
            model=self.MODEL,
            dimensions=self.DIMENSIONS,
            chunk_size=self.MAX_BATCH_SIZE,
            max_retries=max_retries,
            show_progress_bar=show_progress,
            tiktoken_enabled=True,
            check_embedding_ctx_length=True,
            api_key=SecretStr(api_key),
            **kwargs,
        )

    async def embed_chunks(self, chunks: list[CodeChunk], blob_sha: str) -> list[Embedding]:
        """Generate embeddings for code chunks.

        Args:
            chunks: List of code chunks to embed
            blob_sha: Git blob SHA for metadata tracking

        Returns:
            List of Embedding objects with vectors and metadata

        Raises:
            DimensionMismatchError: If returned embeddings have wrong dimensions
            Exception: API errors from OpenAI (network, rate limit, etc.)

        Examples:
            >>> chunks = [CodeChunk(content="def foo(): pass", ...)]
            >>> embeddings = await embedder.embed_chunks(chunks, "abc123")
            >>> len(embeddings[0].vector)  # 3072
        """
        if not chunks:
            return []

        contents = [chunk.content for chunk in chunks]

        # Call OpenAI API directly to get usage data
        response = await self._embeddings.async_client.create(
            input=contents,
            model=self.MODEL,
            dimensions=self.DIMENSIONS,
        )

        # Extract vectors and usage data
        response_dict = response.model_dump() if not isinstance(response, dict) else response

        vectors = [item["embedding"] for item in response_dict["data"]]
        api_token_count = response_dict.get("usage", {}).get("total_tokens")

        # Validate dimensions
        for vector in vectors:
            if len(vector) != self.DIMENSIONS:
                raise DimensionMismatchError(
                    f"Expected {self.DIMENSIONS} dimensions, got {len(vector)}"
                )

        # Build Embeddings with metadata
        embeddings = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
            # Use API token count if available, otherwise fall back to tiktoken estimate
            cost = (
                self.estimate_cost(api_token_count)
                if api_token_count is not None
                else self.estimate_cost(chunk.token_count)
            )

            embeddings.append(
                Embedding(
                    vector=vector,
                    token_count=chunk.token_count,
                    model=self.MODEL,
                    cost_usd=cost,
                    blob_sha=blob_sha,
                    chunk_index=idx,
                    api_token_count=api_token_count,
                )
            )

        return embeddings

    def estimate_cost(self, token_count: int) -> float:
        """Estimate API cost for embedding token_count tokens.

        Uses OpenAI pricing for text-embedding-3-large: $0.13 per 1M tokens.

        Args:
            token_count: Number of tokens to embed

        Returns:
            Estimated cost in USD

        Examples:
            >>> embedder.estimate_cost(1_000_000)  # 0.13
            >>> embedder.estimate_cost(1000)       # 0.00013
            >>> embedder.estimate_cost(0)          # 0.0
        """
        return (token_count / 1_000_000) * self.COST_PER_MILLION_TOKENS


class OpenAIProvider:
    """OpenAI provider for search/query embedding (simple interface).

    Wraps LangChain OpenAIEmbeddings to provide simple text-to-vector conversion
    for search queries. Unlike OpenAIEmbedder (for indexing), this returns raw
    numpy arrays without metadata.

    Inherits from BaseProvider to access model specifications.

    Examples:
        >>> provider = OpenAIProvider("text-embedding-3-large", "sk-...")
        >>> query_vector = provider.embed_query("authentication logic")
        >>> query_vector.shape
        (3072,)
    """

    def __init__(self, model_name: str, api_key: str) -> None:
        """Initialize provider with model and API key.

        Args:
            model_name: Model identifier (e.g., "text-embedding-3-large")
            api_key: OpenAI API key

        Examples:
            >>> provider = OpenAIProvider("text-embedding-3-large", "sk-...")
        """
        from gitctx.models.base import BaseProvider

        # Initialize BaseProvider to load model spec
        base = BaseProvider(model_name)
        self.model_name = model_name
        self.spec = base.spec

        # Initialize LangChain client
        self._client = OpenAIEmbeddings(
            model=model_name,
            api_key=SecretStr(api_key),
            dimensions=base.dimensions,
        )

    @property
    def max_tokens(self) -> int:
        """Maximum token limit for this model."""
        return self.spec["max_tokens"]

    @property
    def dimensions(self) -> int:
        """Embedding dimension count."""
        return self.spec["dimensions"]

    @property
    def provider(self) -> str:
        """Provider name (e.g., 'openai')."""
        return self.spec["provider"]

    def embed_query(self, text: str) -> NDArray[np.floating]:  # type: ignore[no-any-unimported]
        """Generate embedding for single query text.

        Args:
            text: Query text to embed

        Returns:
            numpy array of shape (dimensions,) with float32 values

        Examples:
            >>> provider = OpenAIProvider("text-embedding-3-large", "sk-...")
            >>> vector = provider.embed_query("authentication")
            >>> vector.shape
            (3072,)
        """
        embedding = self._client.embed_query(text)
        return np.array(embedding)

    def embed_documents(self, texts: list[str]) -> list[NDArray[np.floating]]:  # type: ignore[no-any-unimported]
        """Generate embeddings for multiple documents.

        Args:
            texts: List of document texts to embed

        Returns:
            List of numpy arrays, each of shape (dimensions,) with floating point values

        Examples:
            >>> provider = OpenAIProvider("text-embedding-3-large", "sk-...")
            >>> vectors = provider.embed_documents(["text1", "text2"])
            >>> len(vectors)
            2
        """
        embeddings = self._client.embed_documents(texts)
        return [np.array(emb) for emb in embeddings]
