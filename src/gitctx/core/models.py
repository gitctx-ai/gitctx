"""Data models for commit walker."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CommitMetadata:
    """Metadata extracted from a git commit.

    This dataclass captures commit information needed for denormalized
    LanceDB storage (see STORY-0001.2.1 Technical Design - Architecture
    Decision: Denormalized LanceDB).

    Attributes:
        commit_sha: Full SHA-1 hash of the commit
        author_name: Commit author name
        author_email: Commit author email
        commit_date: Unix timestamp of commit
        commit_message: Full commit message for AI context
        is_merge: True if commit has 2+ parents
    """

    commit_sha: str
    author_name: str
    author_email: str
    commit_date: int
    commit_message: str
    is_merge: bool


@dataclass
class BlobLocation:
    """Where a blob appears in git history with commit context.

    This dataclass captures blob location information for denormalized
    LanceDB storage (see STORY-0001.2.1 Technical Design).

    Attributes:
        commit_sha: Full SHA-1 hash of the commit containing this blob
        file_path: Path to file in commit tree
        is_head: True if blob exists in HEAD tree
        author_name: Commit author name (denormalized)
        author_email: Commit author email (denormalized)
        commit_date: Unix timestamp of commit (denormalized)
        commit_message: Full commit message (denormalized)
        is_merge: True if commit has 2+ parents (denormalized)
    """

    commit_sha: str
    file_path: str
    is_head: bool
    author_name: str
    author_email: str
    commit_date: int
    commit_message: str
    is_merge: bool


@dataclass
class BlobRecord:
    """A unique blob and all its locations in git history (walker output).

    This dataclass represents the primary output of CommitWalker.walk_blobs():
    one record per unique blob SHA-1 hash, with all locations (commits and file paths)
    where that blob appears in the repository history.

    This structure is designed for denormalized storage in LanceDB (see STORY-0001.2.1
    Technical Design - Architecture Decision: Denormalized LanceDB), enabling efficient
    retrieval of all commit/file locations for a given blob. All relevant commit metadata
    is included in the nested BlobLocation objects for each location.

    Attributes:
        sha: Blob SHA-1 hash (40 hex chars), uniquely identifies the blob content.
        content: Raw blob content as bytes.
        size: Blob size in bytes.
        locations: List of BlobLocation objects, each describing a commit and file path
            where this blob appears, with denormalized commit metadata.
    """

    sha: str
    content: bytes
    size: int
    locations: list[BlobLocation]


@dataclass
class WalkProgress:
    """Progress information during commit walking.

    This dataclass provides real-time progress updates during the commit
    walk operation, allowing callers to track walker state and provide
    user feedback.

    Attributes:
        commits_seen: Number of commits processed so far
        total_commits: Total number of commits to process (if known)
        unique_blobs_found: Count of unique blobs discovered
        current_commit: Metadata of commit currently being processed
    """

    commits_seen: int
    total_commits: int | None
    unique_blobs_found: int
    current_commit: CommitMetadata | None


@dataclass
class WalkError:
    """Error information from commit walking.

    This dataclass captures non-fatal errors encountered during the walk,
    allowing the walker to continue processing while recording issues.

    Attributes:
        error_type: Classification of error (e.g., 'blob_read', 'tree_parse')
        blob_sha: SHA of blob that caused error (if applicable)
        commit_sha: SHA of commit being processed when error occurred
        message: Human-readable error description
    """

    error_type: str
    blob_sha: str | None
    commit_sha: str
    message: str


@dataclass
class WalkStats:
    """Statistics collected during commit walking.

    This dataclass accumulates statistics throughout the walk operation,
    providing a summary of what was processed and any errors encountered.

    Attributes:
        commits_seen: Total commits processed
        blobs_indexed: Total blobs successfully indexed
        blobs_skipped: Total blobs skipped (filtered or errored)
        errors: List of all non-fatal errors encountered
    """

    commits_seen: int = 0
    blobs_indexed: int = 0
    blobs_skipped: int = 0
    errors: list[WalkError] | None = None

    def __post_init__(self) -> None:
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata.

    Design notes:
    - Simple dataclass for easy FFI serialization (future Rust optimization)
    - All fields use primitive types (str, int, dict)
    - No Path objects (use strings for Rust compatibility)

    Attributes:
        content: Chunk text content
        start_line: Line number where chunk starts (1-indexed)
        end_line: Line number where chunk ends (inclusive)
        token_count: Exact token count via tiktoken
        metadata: Additional metadata (blob_sha, chunk_index, language, etc.)

    Examples:
        >>> chunk = CodeChunk(
        ...     content="def foo():\\n    pass",
        ...     start_line=10,
        ...     end_line=11,
        ...     token_count=8,
        ...     metadata={"language": "python", "chunk_index": 0}
        ... )
        >>> chunk.token_count
        8
    """

    content: str
    start_line: int
    end_line: int
    token_count: int
    metadata: dict[str, Any]
