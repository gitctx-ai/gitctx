"""Protocol definitions for gitctx core components.

Protocols enable:
1. Type checking without inheritance
2. Duck typing with static verification
3. Future optimization (Python → Rust via PyO3)

All protocols use primitive types for FFI compatibility.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from gitctx.core.models import BlobRecord, CodeChunk, WalkProgress, WalkStats

if TYPE_CHECKING:
    from gitctx.core.config import GitCtxSettings


class ChunkerProtocol(Protocol):
    """Protocol for code chunking - can be fulfilled by Python or Rust.

    Enables future optimization: Python implementation now, Rust implementation
    later via PyO3 bindings, without breaking changes to consuming code.

    Design principles:
    - Use primitive types (str, int) for FFI compatibility
    - Return dataclasses with primitive fields (CodeChunk)
    - No Path objects or complex types
    """

    def chunk_file(self, content: str, language: str, max_tokens: int = 1000) -> list[CodeChunk]:
        """Split file content into semantic chunks.

        Args:
            content: File content to chunk (str, not bytes)
            language: Programming language for language-aware splitting
                     (from detect_language_from_extension)
            max_tokens: Maximum tokens per chunk (embedding model specific)

        Returns:
            List of CodeChunk objects with metadata

        Examples:
            >>> chunker.chunk_file("def foo(): pass", "python", max_tokens=800)
            [CodeChunk(content="def foo(): pass", start_line=1, ...)]
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens (using cl100k_base encoding)

        Examples:
            >>> chunker.count_tokens("Hello world")
            2
        """
        ...


class CommitWalkerProtocol(Protocol):
    """Protocol for commit graph walking - can be fulfilled by Python or Rust.

    Enables future optimization: Python implementation now, Rust implementation
    later via PyO3 bindings, without breaking changes to consuming code.

    Design principles for FFI compatibility:
    - Use primitive types (str, int, bool, bytes) - no Path objects
    - Return dataclasses with primitive fields only
    - Stateful protocol: initialization separate from walk operation

    Example usage:
        >>> from gitctx.core import create_walker
        >>> walker = create_walker("/path/to/repo", config)
        >>> for blob in walker.walk_blobs():
        ...     print(f"Blob {blob.sha} in {len(blob.locations)} commits")
        >>> stats = walker.get_stats()
        >>> print(f"Indexed {stats.blobs_indexed} blobs")
    """

    def walk_blobs(
        self,
        progress_callback: Callable[[WalkProgress], None] | None = None,
    ) -> Iterator[BlobRecord]:
        """Walk commits and yield unique blobs with location metadata.

        Args:
            progress_callback: Optional callback invoked every 10 commits
                             with WalkProgress metrics (commits_seen, unique_blobs, etc.)

        Yields:
            BlobRecord containing:
            - sha: str (blob SHA-1 hash)
            - content: bytes (blob content)
            - size: int (blob size in bytes)
            - locations: list[BlobLocation] (all commits/paths where blob appears)

        Raises:
            PartialCloneError: If repository is a partial clone (missing objects)
            ShallowCloneError: If repository is a shallow clone (incomplete history)
            GitRepositoryError: If repository is invalid or inaccessible

        Design note:
            Returns Iterator (not list) for memory efficiency with large repositories.
            Blobs are yielded one at a time as they're discovered during the walk.
        """
        ...

    def get_stats(self) -> WalkStats:
        """Get statistics from completed or in-progress walk.

        Returns:
            WalkStats with commits_seen, blobs_indexed, blobs_skipped, errors

        Design note:
            Can be called during walk for real-time stats or after completion
            for final statistics.
        """
        ...


def create_walker(
    repo_path: str,
    config: "GitCtxSettings",
    already_indexed: set[str] | None = None,
) -> CommitWalkerProtocol:
    """Factory function to create a commit walker.

    This allows easy swapping of implementations in the future
    (e.g., Rust implementation via PyO3) without changing consuming code.

    Args:
        repo_path: Path to git repository (str for FFI compatibility, not Path)
        config: GitCtxSettings instance with walker configuration
        already_indexed: Set of blob SHAs to skip (for resume from partial index)

    Returns:
        Walker instance implementing CommitWalkerProtocol

    Raises:
        PartialCloneError: If repository is a partial clone
        ShallowCloneError: If repository is a shallow clone
        GitRepositoryError: If repository path is invalid

    Example:
        >>> from gitctx.core import create_walker
        >>> from gitctx.core.config import GitCtxSettings
        >>> config = GitCtxSettings()
        >>> walker = create_walker("/path/to/repo", config)
        >>> for blob in walker.walk_blobs():
        ...     print(f"Found blob {blob.sha} in {len(blob.locations)} commits")
    """
    from gitctx.core.commit_walker import CommitWalker

    return CommitWalker(repo_path, config, already_indexed)


@dataclass(frozen=True)
class Embedding:
    """Embedding vector with metadata.

    Design notes:
    - Frozen dataclass for immutability and thread-safety
    - All fields use primitive types (FFI-compatible for future Rust optimization)
    - No numpy arrays or Path objects (breaks FFI)

    Attributes:
        vector: Embedding vector (3072 dimensions for text-embedding-3-large)
        token_count: Number of tokens in source chunk
        model: Model name (e.g., "text-embedding-3-large")
        cost_usd: Cost in USD for generating this embedding
                  TODO(TASK-0001.2.3.3): MUST use actual token count from OpenAI API response,
                  not tiktoken estimates. Required accuracy: ±1% vs OpenAI billing.
                  Verify LangChain exposes API usage data or use direct OpenAI SDK.
        blob_sha: Git blob SHA this embedding represents
        chunk_index: Index of chunk within blob's chunks
    """

    vector: list[float]
    token_count: int
    model: str
    cost_usd: float
    blob_sha: str
    chunk_index: int


class EmbedderProtocol(Protocol):
    """Protocol for embedding generation - provider-agnostic interface.

    This protocol enables multiple embedding providers (OpenAI, Anthropic, Cohere, etc.)
    while maintaining type safety and enabling future Rust optimization.

    Example:
        >>> embedder = OpenAIEmbedder(api_key="sk-...")
        >>> chunks = [CodeChunk(...), CodeChunk(...)]
        >>> embeddings = await embedder.embed_chunks(chunks, "abc123")
        >>> cost = embedder.estimate_cost(1000)  # $0.00013
    """

    async def embed_chunks(self, chunks: list[CodeChunk], blob_sha: str) -> list[Embedding]:
        """Generate embeddings for code chunks.

        Args:
            chunks: List of code chunks to embed
            blob_sha: Git blob SHA for metadata tracking

        Returns:
            List of Embedding objects with vectors and metadata

        Raises:
            NetworkError: If API is unreachable after retries
            RateLimitError: If rate limit exceeded after retries
            ConfigurationError: If API key is invalid
        """
        ...

    def estimate_cost(self, token_count: int) -> float:
        """Estimate API cost for embedding token_count tokens.

        Args:
            token_count: Number of tokens to embed

        Returns:
            Estimated cost in USD

        Example:
            >>> embedder.estimate_cost(1_000_000)
            0.13  # $0.13 for 1M tokens with text-embedding-3-large
        """
        ...
