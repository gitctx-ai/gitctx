"""Git commit walker with validation and metadata extraction."""

from collections.abc import Iterator
from pathlib import Path

import pygit2

from .config import GitCtxSettings
from .models import CommitMetadata


class GitRepositoryError(Exception):
    """Base exception for git repository errors."""

    pass


class PartialCloneError(GitRepositoryError):
    """Raised when repository is a partial clone."""

    pass


class ShallowCloneError(GitRepositoryError):
    """Raised when repository is a shallow clone."""

    pass


class CommitWalker:
    """Walk git commit graph and extract commit metadata.

    Responsibilities:
    - Initialize with repository path validation
    - Detect and error on partial/shallow clones
    - Support bare repositories
    - Walk commits in reverse chronological order
    - Extract commit metadata (author, date, message, is_merge)
    - Support multiple refs with commit-level deduplication

    Does NOT (deferred to other tasks):
    - Extract blobs from trees (TASK-0001.2.1.2)
    - Track blob locations (TASK-0001.2.1.3)
    - Filter blobs (TASK-0001.2.1.4)
    - Report progress (TASK-0001.2.1.5)
    """

    def __init__(
        self,
        repo_path: str,
        config: GitCtxSettings,
    ):
        """Initialize commit walker with repository validation.

        Args:
            repo_path: Path to git repository (can be bare or normal)
            config: GitCtxSettings instance

        Raises:
            GitRepositoryError: If repo is invalid or inaccessible
            PartialCloneError: If partial clone detected
            ShallowCloneError: If shallow clone detected
        """
        self.repo_path = Path(repo_path)
        self.config = config

        # Validate repository type BEFORE opening (Windows pygit2 fails on invalid shallow files)
        self._validate_repository()

        # Open repository
        try:
            self.repo = pygit2.Repository(str(self.repo_path))
        except Exception as e:
            raise GitRepositoryError(f"Failed to open repository: {e}") from e

        # Get refs from config
        self.refs = config.repo.index.refs

        # Track seen commits for deduplication
        self.seen_commits: set[str] = set()

    def _validate_repository(self) -> None:
        """Validate repository is not partial or shallow clone.

        Raises:
            PartialCloneError: If .git/objects/info/alternates exists
            ShallowCloneError: If .git/shallow exists
        """
        # Determine git directory (could be bare repo or regular repo with .git subdir)
        if (self.repo_path / "objects").exists():
            # Bare repository
            git_dir = self.repo_path
        else:
            # Regular repository with .git subdirectory
            git_dir = self.repo_path / ".git"

        # Check for partial clone
        alternates_file = git_dir / "objects" / "info" / "alternates"
        if alternates_file.exists():
            raise PartialCloneError(
                "Repository is a partial clone (missing objects). Please clone the full repository."
            )

        # Check for shallow clone
        shallow_file = git_dir / "shallow"
        if shallow_file.exists():
            raise ShallowCloneError(
                "Repository is a shallow clone (incomplete history). "
                "Run 'git fetch --unshallow' to fetch complete history."
            )

    def _walk_commits(self) -> Iterator[CommitMetadata]:
        """Walk commits from configured refs in reverse chronological order.

        Yields:
            CommitMetadata for each unique commit (deduplicated across refs)
        """
        # Set up walker for reverse chronological order (newest first)
        # GIT_SORT_TOPOLOGICAL gives us newest->oldest by default (children before parents)
        # This is what we want for reverse chronological order
        walker = self.repo.walk(
            self.repo.head.target,
            int(pygit2.GIT_SORT_TOPOLOGICAL),  # type: ignore[arg-type]
        )

        for commit in walker:
            commit_sha = str(commit.id)

            # Skip if already seen (deduplication across refs)
            if commit_sha in self.seen_commits:
                continue
            self.seen_commits.add(commit_sha)

            # Extract metadata
            metadata = CommitMetadata(
                commit_sha=commit_sha,
                author_name=commit.author.name,
                author_email=commit.author.email,
                commit_date=commit.commit_time,
                commit_message=commit.message,
                is_merge=len(commit.parent_ids) > 1,
            )

            yield metadata
