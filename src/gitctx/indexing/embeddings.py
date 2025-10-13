"""Embedding generation orchestration.

This module provides helper functions that orchestrate chunking, embedding,
and caching operations for code blobs.

Design:
- Coordinates between chunker, embedder, and cache
- Provides logging for cost tracking and cache hits
- Serves as second use case for EmbeddingCache (STORY-0001.2.4)
"""

import logging

from gitctx.git.types import BlobRecord
from gitctx.indexing.language_detection import detect_language_from_extension
from gitctx.indexing.protocols import ChunkerProtocol
from gitctx.indexing.types import Embedding
from gitctx.models.protocols import EmbedderProtocol
from gitctx.storage.embedding_cache import EmbeddingCache  # TODO: Merge into storage

logger = logging.getLogger("gitctx.embeddings")


async def embed_with_cache(
    chunker: ChunkerProtocol,
    embedder: EmbedderProtocol,
    cache: EmbeddingCache,
    blob_record: BlobRecord,
) -> list[Embedding]:
    """Generate embeddings for a blob with caching.

    Orchestrates the full embedding pipeline:
    1. Check cache by blob SHA
    2. If hit: return cached embeddings (log hit)
    3. If miss: chunk → embed → store in cache → log cost/tokens
    4. Return embeddings

    Args:
        chunker: Chunker implementation for splitting code
        embedder: Embedder implementation (e.g., OpenAI)
        cache: Embedding cache for blob-level caching
        blob_record: Blob to generate embeddings for

    Returns:
        List of Embedding objects (from cache or freshly generated)

    Examples:
        >>> from gitctx.core import create_walker
        >>> from gitctx.core.chunker import Chunker
        >>> from gitctx.embeddings.openai_embedder import OpenAIEmbedder
        >>> from gitctx.storage.embedding_cache import EmbeddingCache
        >>>
        >>> # Set up components
        >>> chunker = Chunker()
        >>> embedder = OpenAIEmbedder(api_key="sk-...")
        >>> cache = EmbeddingCache("/path/to/.gitctx", model="text-embedding-3-large")
        >>>
        >>> # Process blob
        >>> embeddings = await embed_with_cache(chunker, embedder, cache, blob_record)
        >>> # Logs: "Embedded blob abc12345: 3 chunks, 450 tokens, $0.0000585"
    """
    # Check cache first
    cached = cache.get(blob_record.sha)
    if cached is not None:
        logger.info(f"Cache hit for blob {blob_record.sha[:8]}")
        return cached

    # Cache miss - need to generate embeddings
    # Decode blob content
    content = blob_record.content.decode("utf-8", errors="replace")

    # Detect language from first location (if any)
    language = "markdown"  # Default fallback
    if blob_record.locations:
        file_path = blob_record.locations[0].file_path
        language = detect_language_from_extension(file_path)

    # Chunk the content
    chunks = chunker.chunk_file(content, language)

    # Generate embeddings
    embeddings = await embedder.embed_chunks(chunks, blob_record.sha)

    # Store in cache
    cache.set(blob_record.sha, embeddings)

    # Log cost and token information
    total_tokens = sum(e.token_count for e in embeddings)
    total_cost = sum(e.cost_usd for e in embeddings)
    logger.info(
        f"Embedded blob {blob_record.sha[:8]}: "
        f"{len(embeddings)} chunks, {total_tokens} tokens, ${total_cost:.6f}"
    )

    return embeddings
