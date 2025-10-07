"""Data models for commit walker."""

from dataclasses import dataclass


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
    """A unique blob with all its locations (walker output).

    This is the primary output of CommitWalker.walk_blobs() - one record
    per unique blob SHA, with all locations where that blob appears.

    Attributes:
        sha: Blob SHA-1 hash (40 hex chars)
        content: Raw blob content as bytes
        size: Blob size in bytes
        locations: list of all locations where this blob appears
    """

    sha: str
    content: bytes
    size: int
    locations: list[BlobLocation]
