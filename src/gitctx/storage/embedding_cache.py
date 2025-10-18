"""Embedding cache using safetensors for persistent storage."""

import logging
from pathlib import Path

import numpy as np
from safetensors import safe_open
from safetensors.numpy import save_file

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
        """Load cached embeddings for a blob.

        Args:
            blob_sha: Git blob SHA

        Returns:
            List of Embedding objects if cached, None if not found
        """
        path = self.cache_dir / f"{blob_sha}.safetensors"
        if not path.exists():
            return None

        try:
            # Load safetensor file with metadata
            with safe_open(str(path), framework="numpy") as f:  # type: ignore[no-untyped-call]
                metadata = f.metadata() or {}

                # Reconstruct Embedding objects from arrays + metadata
                embeddings = []
                chunk_count = int(metadata.get("chunks", 0))

                for i in range(chunk_count):
                    tensor = f.get_tensor(f"chunk_{i}")
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
        """Save embeddings to cache.

        Args:
            blob_sha: Git blob SHA
            embeddings: List of Embedding objects to cache
        """
        path = self.cache_dir / f"{blob_sha}.safetensors"

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

        save_file(tensors, str(path), metadata=metadata)
