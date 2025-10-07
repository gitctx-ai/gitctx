"""Blob filtering for gitignore, binary, LFS, and size limits."""

from __future__ import annotations

import pathspec


class BlobFilter:
    """Filter blobs based on gitignore, binary, LFS, and size rules.

    Responsibilities:
    - Detect binary files via null byte heuristic
    - Detect Git LFS pointer files
    - Enforce size limits
    - Match gitignore patterns via pathspec
    - Always exclude .git/ and .gitctx/ directories

    Does NOT:
    - Walk git trees (that's CommitWalker)
    - Track blob locations (that's CommitWalker)
    """

    def __init__(
        self,
        max_blob_size_mb: int = 5,
        gitignore_patterns: str = "",
        skip_binary: bool = True,
    ):
        """Initialize blob filter.

        Args:
            max_blob_size_mb: Maximum blob size in megabytes
            gitignore_patterns: Gitignore patterns as string (one per line)
            skip_binary: Whether to skip binary files
        """
        self.max_blob_size_mb = max_blob_size_mb
        self.max_blob_bytes = max_blob_size_mb * 1024 * 1024
        self.skip_binary = skip_binary

        # Build pathspec from gitignore patterns
        self.pathspec: pathspec.PathSpec | None
        if gitignore_patterns:
            self.pathspec = pathspec.PathSpec.from_lines(
                "gitwildmatch", gitignore_patterns.splitlines()
            )
        else:
            self.pathspec = None

    def is_binary(self, content: bytes) -> bool:
        """Detect binary files using null byte heuristic.

        Git's approach: Check first 8192 bytes for null byte.
        This is fast and catches 99% of binary files.

        Args:
            content: Blob content as bytes

        Returns:
            True if binary (contains null byte in first 8192 bytes)
        """
        # Check first 8192 bytes for null byte (same as git)
        check_size = min(len(content), 8192)
        return b"\x00" in content[:check_size]

    def is_lfs_pointer(self, content: bytes) -> bool:
        """Detect Git LFS pointer files.

        LFS pointer files have format:
        ```
        version https://git-lfs.github.com/spec/v1
        oid sha256:abc123...
        size 1048576
        ```

        Args:
            content: Blob content as bytes

        Returns:
            True if Git LFS pointer file
        """
        # Check for LFS header (case-sensitive)
        lfs_header = b"version https://git-lfs.github.com/spec"
        return content.startswith(lfs_header)

    def exceeds_size_limit(self, content: bytes) -> bool:
        """Check if blob exceeds size limit.

        Args:
            content: Blob content as bytes

        Returns:
            True if blob exceeds max_blob_size_mb
        """
        return len(content) > self.max_blob_bytes

    def is_gitignored(self, file_path: str) -> bool:
        """Check if file path matches gitignore patterns.

        Args:
            file_path: Path to check (relative to repo root)

        Returns:
            True if path matches gitignore patterns
        """
        if not self.pathspec:
            return False
        return self.pathspec.match_file(file_path)

    def is_security_path(self, file_path: str) -> bool:
        """Check if path is in security-critical directory.

        Always exclude:
        - .git/ directory
        - .gitctx/ directory

        Args:
            file_path: Path to check (relative to repo root)

        Returns:
            True if path is in .git/ or .gitctx/
        """
        # Normalize path for consistent checking
        path_parts = file_path.split("/")

        # Check if .git or .gitctx is in path
        return ".git" in path_parts or ".gitctx" in path_parts

    def should_filter(
        self,
        file_path: str,
        content: bytes,
    ) -> tuple[bool, str | None]:
        """Check if blob should be filtered.

        Returns:
            Tuple of (should_filter, reason)
            - should_filter: True if blob should be skipped
            - reason: None if not filtered, or reason string
        """
        # Security: Always exclude .git/ and .gitctx/
        if self.is_security_path(file_path):
            return (True, "security_path")

        # Check gitignore
        if self.is_gitignored(file_path):
            return (True, "gitignored")

        # Check binary (if enabled)
        if self.skip_binary and self.is_binary(content):
            return (True, "binary")

        # Check LFS
        if self.is_lfs_pointer(content):
            return (True, "lfs_pointer")

        # Check size
        if self.exceeds_size_limit(content):
            return (True, "oversized_blob")

        return (False, None)
