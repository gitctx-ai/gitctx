"""OpenAI embedding generator using LangChain wrapper."""

from typing import Any

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from gitctx.core.exceptions import ConfigurationError, DimensionMismatchError
from gitctx.core.models import CodeChunk
from gitctx.core.protocols import Embedding


class OpenAIEmbedder:
    """OpenAI embedding generator wrapping LangChain.

    This class wraps LangChain's OpenAIEmbeddings to generate embeddings
    for code chunks using OpenAI's text-embedding-3-large model.

    Design notes:
    - Uses LangChain for API abstraction and retry logic
    - Validates API key format on initialization
    - Validates embedding dimensions match expected 3072
    - Tracks cost using OpenAI pricing ($0.13 per 1M tokens)
    - Batches requests efficiently (max 2048 chunks per batch)

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
        """Initialize embedder with API key validation.

        Args:
            api_key: OpenAI API key (must start with 'sk-')
            max_retries: Maximum retry attempts for API calls (default: 3)
            show_progress: Show progress bar during embedding (default: False)
            **kwargs: Additional arguments passed to OpenAIEmbeddings

        Raises:
            ConfigurationError: If API key is missing or invalid format

        Examples:
            >>> embedder = OpenAIEmbedder(api_key="sk-test123")
            >>> embedder = OpenAIEmbedder(api_key="sk-...", max_retries=5)
        """
        if not api_key or not api_key.startswith("sk-"):
            raise ConfigurationError(
                "OpenAI API key required (must start with 'sk-'). "
                "Set OPENAI_API_KEY env var or configure in settings."
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
