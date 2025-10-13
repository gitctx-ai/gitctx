"""Protocols for git operations."""

from collections.abc import Callable, Iterator
from typing import Protocol, runtime_checkable

from gitctx.git.types import BlobRecord, WalkProgress, WalkStats


@runtime_checkable
class CommitWalkerProtocol(Protocol):
    """Protocol for commit graph walking - can be fulfilled by Python or Rust.

    Enables future optimization: Python implementation now, Rust implementation
    later via PyO3 bindings, without breaking changes to consuming code.

    Design principles for FFI compatibility:
    - Use primitive types (str, int, bool, bytes) - no Path objects
    - Return dataclasses with primitive fields only
    - Stateful protocol: initialization separate from walk operation

    Example usage:
        >>> from gitctx.git import create_walker
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
            - size: int (blob size)
            - locations: list[BlobLocation] (where blob appears)

        Examples:
            >>> for blob in walker.walk_blobs():
            ...     print(f"Blob {blob.sha}: {blob.size} bytes")
        """
        ...

    def get_stats(self) -> WalkStats:
        """Get statistics collected during walk.

        Returns:
            WalkStats with commits_seen, blobs_indexed, blobs_skipped, errors

        Examples:
            >>> walker.walk_blobs()  # Exhaust iterator
            >>> stats = walker.get_stats()
            >>> print(f"Processed {stats.commits_seen} commits")
        """
        ...
