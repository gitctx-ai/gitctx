"""Embedding cache using safetensors for persistent storage."""

import json
import logging
import struct
from pathlib import Path

import numpy as np
import zstandard as zstd
from safetensors.numpy import load, save

from gitctx.indexing.types import Embedding

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Persistent filesystem cache for embeddings by blob SHA.

    Uses safetensors format for:
    - Security: No arbitrary code execution (unlike pickle)
    - Performance: Efficient binary format with compression
    - Safety: Built-in validation

    Cache structure:
        .gitctx/embeddings/{model}/{blob_sha}.safetensors

    Example:
        >>> cache = EmbeddingCache(Path(".gitctx"), model="text-embedding-3-large")
        >>> embeddings = [Embedding(...), Embedding(...)]
        >>> cache.set("abc123", embeddings)
        >>> loaded = cache.get("abc123")  # Returns embeddings
        >>> missing = cache.get("nonexistent")  # Returns None
    """

    # Level 3: Balance of speed and ratio (zstd recommendation)
    COMPRESSION_LEVEL = 3

    def __init__(self, cache_dir: Path, model: str = "text-embedding-3-large"):
        """Initialize cache for a specific model.

        Args:
            cache_dir: Root cache directory (.gitctx/)
            model: Model name for namespacing (default: text-embedding-3-large)
        """
        self.cache_dir = cache_dir / "embeddings" / model
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = model

    def get(self, blob_sha: str) -> list[Embedding] | None:
        """Load cached embeddings with transparent decompression.

        Args:
            blob_sha: Git blob SHA

        Returns:
            List of Embedding objects if cached, None if not found
        """
        path = self.cache_dir / f"{blob_sha}.safetensors.zst"
        if not path.exists():
            return None

        try:
            # Decompress
            compressed = path.read_bytes()
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress(compressed)

            # Extract metadata from safetensors header
            # (Standard safetensors pattern for bytes - see https://huggingface.co/docs/safetensors/metadata_parsing)
            header_size = struct.unpack("<Q", decompressed[:8])[0]
            json_header = decompressed[8 : 8 + header_size].decode("utf-8")
            header = json.loads(json_header)
            metadata = header.get("__metadata__", {})

            # Load tensors from decompressed bytes
            tensors = load(decompressed)

            # Reconstruct Embedding objects from tensors + metadata
            embeddings = []
            chunk_count = int(metadata.get("chunks", 0))
            for i in range(chunk_count):
                tensor = tensors[f"chunk_{i}"]
                vector = tensor.tolist()
                embeddings.append(
                    Embedding(
                        vector=vector,
                        token_count=int(metadata.get(f"chunk_{i}_tokens", 0)),
                        model=self.model,
                        cost_usd=float(metadata.get(f"chunk_{i}_cost", 0.0)),
                        blob_sha=blob_sha,
                        chunk_index=i,
                    )
                )
            return embeddings

        except Exception as e:
            # Corrupted file - log and return None
            logger.warning(f"Failed to load cache for {blob_sha[:8]}: {e}")
            return None

    def set(self, blob_sha: str, embeddings: list[Embedding]) -> None:
        """Save embeddings with zstd compression.

        Args:
            blob_sha: Git blob SHA
            embeddings: List of Embedding objects to cache
        """
        path = self.cache_dir / f"{blob_sha}.safetensors.zst"

        # Convert Embedding list to numpy arrays for safetensors
        tensors = {}
        metadata = {}

        for i, emb in enumerate(embeddings):
            tensors[f"chunk_{i}"] = np.array(emb.vector, dtype=np.float32)
            metadata[f"chunk_{i}_tokens"] = str(emb.token_count)
            metadata[f"chunk_{i}_cost"] = str(emb.cost_usd)

        metadata["model"] = self.model
        metadata["blob_sha"] = blob_sha
        metadata["chunks"] = str(len(embeddings))

        # Serialize to bytes (NOT file)
        safetensors_bytes = save(tensors, metadata=metadata)

        # Compress with zstd
        cctx = zstd.ZstdCompressor(level=self.COMPRESSION_LEVEL)
        compressed = cctx.compress(safetensors_bytes)

        # Write compressed bytes
        path.write_bytes(compressed)
