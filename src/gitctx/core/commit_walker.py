"""Git commit walker with validation and metadata extraction."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pygit2

from .blob_filter import BlobFilter
from .config import GitCtxSettings
from .models import BlobLocation, BlobRecord, CommitMetadata, WalkError, WalkProgress, WalkStats


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
    - Track blob locations with is_head flag (TASK-0001.2.1.3 ✅)

    Does NOT (deferred to other tasks):
    - Filter blobs (TASK-0001.2.1.4)
    - Report progress (TASK-0001.2.1.5)
    """

    def __init__(
        self,
        repo_path: str,
        config: GitCtxSettings,
        already_indexed: set[str] | None = None,
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

        # Track seen blobs for deduplication (O(1) membership check)
        # Copy the set to avoid modifying the caller's set
        self.seen_blobs: set[str] = set(already_indexed) if already_indexed else set()

        # Accumulate blob locations for denormalized storage
        self.blob_locations: dict[str, list[BlobLocation]] = {}

        # Cache unique blob count for O(1) progress reporting
        self._unique_blobs_count: int = 0

        # Build HEAD tree blob set for O(1) is_head lookup
        # For bare repos, this will be empty (no HEAD working tree)
        self.head_blobs: set[str] = self._build_head_tree()

        # Initialize blob filter
        gitignore_content = self._read_gitignore_from_head()
        self.blob_filter = BlobFilter(
            max_blob_size_mb=config.repo.index.max_blob_size_mb,
            gitignore_patterns=gitignore_content,
            skip_binary=config.repo.index.skip_binary,
        )

        # Initialize walk statistics
        self.stats = WalkStats()

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

    def _collect_tree_blobs(  # type: ignore[no-any-unimported]
        self,
        tree: pygit2.Tree,  # type: ignore[name-defined]
        blob_set: set[str],
    ) -> None:
        """Recursively collect all blob SHAs from a tree.

        Args:
            tree: pygit2 Tree object to traverse
            blob_set: Set to accumulate blob SHAs into
        """
        for entry in tree:
            if entry.type_str == "blob":
                blob_set.add(str(entry.id))
            elif entry.type_str == "tree":
                # Recurse into subdirectory
                subtree = self.repo.get(entry.id)
                if subtree:
                    self._collect_tree_blobs(subtree, blob_set)  # type: ignore[arg-type, no-any-unimported]

    def _read_gitignore_from_head(self) -> str:
        """Read .gitignore from HEAD tree.

        Returns:
            Gitignore content as string, or empty string if no .gitignore
        """
        # Bare repos have no HEAD
        if self.repo.is_bare:
            return ""

        try:
            head_commit = self.repo.head.peel(pygit2.Commit)
        except (pygit2.GitError, AttributeError):
            return ""

        # Try to find .gitignore in HEAD tree
        try:
            gitignore_entry = head_commit.tree[".gitignore"]
            gitignore_blob = self.repo.get(gitignore_entry.id)
            if not gitignore_blob:
                return ""
            return gitignore_blob.data.decode("utf-8", errors="ignore")  # type: ignore[attr-defined, no-any-return, union-attr]
        except (KeyError, AttributeError):
            # No .gitignore in HEAD
            return ""

    def _build_head_tree(self) -> set[str]:
        """Build set of all blob SHAs in HEAD tree for O(1) is_head lookup.

        For bare repositories, returns empty set (no HEAD working tree).

        Returns:
            Set of blob SHAs present in HEAD tree
        """
        head_blobs: set[str] = set()

        # Bare repositories have no HEAD working tree
        if self.repo.is_bare:
            return head_blobs

        # Get HEAD commit (may fail if repo has no commits)
        try:
            head_commit = self.repo.head.peel(pygit2.Commit)
        except (pygit2.GitError, AttributeError):
            # No HEAD (empty repo) - return empty set
            return head_blobs

        # Recursively collect all blob SHAs from HEAD tree
        self._collect_tree_blobs(head_commit.tree, head_blobs)  # type: ignore[arg-type]
        return head_blobs

    def _walk_commits(self) -> Iterator[CommitMetadata]:
        """Walk commits from configured refs in reverse chronological order.

        Yields:
            CommitMetadata for each unique commit (deduplicated across refs)
        """
        # Walk commits from all configured refs
        for ref in self.refs:
            # Resolve ref to commit
            try:
                if ref == "HEAD":
                    commit_oid = self.repo.head.target
                else:
                    # Try to resolve as branch/tag ref
                    commit_oid = self.repo.resolve_refish(ref)[0].id
            except (KeyError, AttributeError):
                # Skip invalid refs
                continue

            # Set up walker for this ref
            walker = self.repo.walk(
                commit_oid,
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

    def _accumulate_blob_locations(  # type: ignore[no-any-unimported]
        self,
        tree: pygit2.Tree,  # type: ignore[name-defined]
        commit_metadata: CommitMetadata,
        path_prefix: str = "",
    ) -> None:
        """Recursively accumulate blob locations from a tree.

        Args:
            tree: pygit2 Tree object to traverse
            commit_metadata: Metadata for the current commit
            path_prefix: Path prefix for nested directories
        """
        from .models import BlobLocation

        for entry in tree:
            # Build full path for this entry
            entry_path: str = str(f"{path_prefix}{entry.name}" if path_prefix else entry.name)

            if entry.type_str == "blob":
                # Skip symlinks (mode 0o120000)
                # Symlinks are stored as blobs with target path as content
                # We don't want to index them as they point to files already indexed
                if entry.filemode == 0o120000:
                    continue

                blob_sha = str(entry.id)

                # Skip already-indexed blobs (resume from partial index)
                if blob_sha in self.seen_blobs:
                    continue

                # Get blob content for filtering (with error handling)
                try:
                    blob_obj = self.repo.get(blob_sha)
                    if not blob_obj:
                        # Log error and continue
                        error = WalkError(
                            error_type="blob_read",
                            blob_sha=blob_sha,
                            commit_sha=commit_metadata.commit_sha,
                            message=f"Blob {blob_sha} not found in repository",
                        )
                        self.stats.errors.append(error)  # type: ignore[union-attr]
                        self.stats.blobs_skipped += 1
                        continue
                    blob_content = blob_obj.data  # type: ignore[attr-defined]
                except Exception as e:
                    # Log error and continue walking
                    error = WalkError(
                        error_type="blob_read",
                        blob_sha=blob_sha,
                        commit_sha=commit_metadata.commit_sha,
                        message=str(e),
                    )
                    self.stats.errors.append(error)  # type: ignore[union-attr]
                    self.stats.blobs_skipped += 1
                    continue

                # Apply filters
                should_filter, reason = self.blob_filter.should_filter(
                    entry_path,
                    blob_content,
                )
                if should_filter:
                    # Track filtered blobs in WalkStats
                    self.stats.blobs_skipped += 1
                    continue

                # Create BlobLocation for this occurrence
                location = BlobLocation(
                    commit_sha=commit_metadata.commit_sha,
                    file_path=entry_path,
                    is_head=blob_sha in self.head_blobs,  # O(1) set lookup
                    author_name=commit_metadata.author_name,
                    author_email=commit_metadata.author_email,
                    commit_date=commit_metadata.commit_date,
                    commit_message=commit_metadata.commit_message,
                    is_merge=commit_metadata.is_merge,
                )

                # Accumulate location
                if blob_sha not in self.blob_locations:
                    self.blob_locations[blob_sha] = []
                    self._unique_blobs_count += 1
                self.blob_locations[blob_sha].append(location)

            elif entry.type_str == "tree":
                # Recurse into subdirectory
                subtree = self.repo.get(entry.id)
                if subtree:
                    self._accumulate_blob_locations(
                        subtree,  # type: ignore[arg-type, no-any-unimported]
                        commit_metadata,
                        f"{entry_path}/",
                    )

    def walk_blobs(
        self,
        progress_callback: Callable[[WalkProgress], None] | None = None,
    ) -> Iterator[BlobRecord]:
        """Walk commits and yield unique blobs with location metadata.

        Args:
            progress_callback: Optional callback for progress updates (every 10 commits)

        Yields:
            BlobRecord containing:
            - sha: str (blob SHA)
            - content: bytes (blob content)
            - size: int (blob size in bytes)
            - locations: List[BlobLocation] (all commits/paths)

        Algorithm:
        1. First pass: Walk all commits and accumulate all locations for all blobs
        2. Second pass: Yield BlobRecords with complete location lists
        """
        from .models import BlobRecord

        # First pass: Accumulate all locations for all blobs
        for commit_metadata in self._walk_commits():
            # Increment commits seen
            self.stats.commits_seen += 1

            # Invoke progress callback every 10 commits
            if progress_callback and self.stats.commits_seen % 10 == 0:
                progress = WalkProgress(
                    commits_seen=self.stats.commits_seen,
                    total_commits=None,  # Unknown total
                    unique_blobs_found=self._unique_blobs_count,
                    current_commit=commit_metadata,
                )
                progress_callback(progress)

            commit = self.repo.get(commit_metadata.commit_sha)
            assert commit is not None, f"Commit {commit_metadata.commit_sha} not found"

            # Recursively accumulate blob locations from commit tree
            self._accumulate_blob_locations(commit.tree, commit_metadata)  # type: ignore[arg-type]

        # Second pass: Yield unique blobs with complete locations
        for blob_sha, locations in self.blob_locations.items():
            self.seen_blobs.add(blob_sha)

            # Yield blob record with complete locations list
            blob_obj = self.repo.get(blob_sha)
            assert blob_obj is not None, f"Blob {blob_sha} not found"
            # pygit2 Blob object has data and size attributes
            blob = blob_obj  # type: ignore[assignment]

            # Track indexed blobs
            self.stats.blobs_indexed += 1

            yield BlobRecord(
                sha=blob_sha,
                content=blob.data,  # type: ignore[attr-defined]
                size=blob.size,  # type: ignore[attr-defined]
                locations=locations,
            )

    def get_stats(self) -> WalkStats:
        """Return walk statistics.

        Returns:
            WalkStats containing commits_seen, blobs_indexed, blobs_skipped, errors
        """
        return self.stats
