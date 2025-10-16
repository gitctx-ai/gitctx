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

    # Generate protocol embeddings (have vectors but no chunk content)
    protocol_embeddings = await embedder.embed_chunks(chunks, blob_record.sha)

    # Convert to storage embeddings (with full chunk metadata)
    storage_embeddings: list[Embedding] = []
    for chunk, proto_emb in zip(chunks, protocol_embeddings, strict=True):
        storage_embeddings.append(
            Embedding(
                vector=proto_emb.vector,
                token_count=proto_emb.token_count,
                model=proto_emb.model,
                cost_usd=proto_emb.cost_usd,
                blob_sha=blob_record.sha,
                chunk_index=proto_emb.chunk_index,
                chunk_content=chunk.content,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                total_chunks=len(chunks),
                language=language,
            )
        )

    # Store in cache
    cache.set(blob_record.sha, storage_embeddings)

    # Log cost and token information
    total_tokens = sum(e.token_count for e in storage_embeddings)
    total_cost = sum(e.cost_usd for e in storage_embeddings)
    logger.info(
        f"Embedded blob {blob_record.sha[:8]}: "
        f"{len(storage_embeddings)} chunks, {total_tokens} tokens, ${total_cost:.6f}"
    )

    return storage_embeddings
