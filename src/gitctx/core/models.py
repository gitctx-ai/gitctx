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
