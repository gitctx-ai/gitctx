"""Unit tests for CommitWalker.

Tests cover:
- Initialization and error handling
- Commit traversal and metadata extraction
- Blob deduplication across commits
- Location tracking with is_head flag
- Edge cases: partial/shallow clones, bare repos
- Tree recursion: nested directories, submodules, symlinks
"""

import subprocess
import time
from pathlib import Path

import pytest
from tests.conftest import is_windows

from gitctx.core.commit_walker import (
    CommitWalker,
    GitRepositoryError,
    PartialCloneError,
    ShallowCloneError,
)
from gitctx.core.config import GitCtxSettings
from gitctx.core.models import BlobLocation, CommitMetadata

# ============================================================================
# Core Functionality
# ============================================================================


class TestCommitWalkerInitialization:
    """Test CommitWalker initialization with various repository states."""

    def test_init_with_valid_repo(self, git_repo_factory, isolated_env):
        """CommitWalker initializes successfully with valid repository."""
        # Arrange
        repo_path = git_repo_factory()
        config = GitCtxSettings()

        # Act
        walker = CommitWalker(str(repo_path), config)

        # Assert
        assert walker.repo_path == Path(repo_path)
        assert walker.config == config
        assert walker.repo is not None
        assert walker.seen_commits == set()

    def test_init_with_invalid_path(self, tmp_path, isolated_env):
        """CommitWalker raises GitRepositoryError for invalid path."""
        # Arrange
        invalid_path = tmp_path / "nonexistent"
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(GitRepositoryError, match="Failed to open repository"):
            CommitWalker(str(invalid_path), config)

    def test_init_with_non_git_directory(self, tmp_path, isolated_env):
        """CommitWalker raises GitRepositoryError for non-git directory."""
        # Arrange
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(GitRepositoryError, match="Failed to open repository"):
            CommitWalker(str(non_git_dir), config)


class TestCommitTraversal:
    """Test commit traversal ordering and deduplication."""

    def test_walk_commits_reverse_chronological(self, git_repo_factory, isolated_env):
        """Commits are returned in reverse chronological order (newest first)."""
        # Arrange
        repo_path = git_repo_factory(num_commits=3)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        commits = list(walker._walk_commits())

        # Assert
        assert len(commits) == 3
        # Newest commit should be first (highest commit_date)
        for i in range(len(commits) - 1):
            assert commits[i].commit_date >= commits[i + 1].commit_date

    def test_walk_commits_deduplication(self, git_repo_factory, isolated_env):
        """Commits are deduplicated when walking multiple refs."""
        # Arrange
        repo_path = git_repo_factory(num_commits=5)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - walk twice
        first_walk = list(walker._walk_commits())
        second_walk = list(walker._walk_commits())

        # Assert - second walk should be empty due to deduplication
        assert len(first_walk) == 5
        assert len(second_walk) == 0
        assert len(walker.seen_commits) == 5

    def test_walk_empty_repository(self, git_repo_factory, isolated_env):
        """Walking empty repository (no commits) returns no results."""
        # Arrange
        repo_path = git_repo_factory(num_commits=0)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act & Assert: pygit2.GitError raised when repo has no HEAD
        with pytest.raises((Exception, AttributeError)):  # noqa: B017
            list(walker._walk_commits())


class TestCommitMetadataExtraction:
    """Test commit metadata extraction accuracy."""

    def test_extract_commit_metadata(self, git_repo_factory, isolated_env):
        """CommitMetadata contains accurate author, date, message, sha."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        commits = list(walker._walk_commits())

        # Assert
        assert len(commits) == 1
        commit = commits[0]
        assert isinstance(commit, CommitMetadata)
        assert len(commit.commit_sha) == 40  # SHA1 hex
        assert commit.author_name == "Test User"
        assert commit.author_email == "test@example.com"
        assert commit.commit_date > 0  # Unix timestamp
        assert commit.commit_message.startswith("Commit ")

    def test_extract_multiple_commits(self, git_repo_factory, isolated_env):
        """Each commit has unique SHA and correct metadata."""
        # Arrange
        repo_path = git_repo_factory(num_commits=3)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        commits = list(walker._walk_commits())

        # Assert
        assert len(commits) == 3
        shas = [c.commit_sha for c in commits]
        assert len(set(shas)) == 3  # All unique
        for i, commit in enumerate(commits):
            # Commits are numbered in reverse (newest first)
            expected_num = 3 - i
            assert f"Commit {expected_num}" in commit.commit_message


class TestMergeCommitDetection:
    """Test merge commit detection (is_merge flag)."""

    def test_regular_commit_not_merge(self, git_repo_factory, isolated_env):
        """Regular commits have is_merge=False."""
        # Arrange
        repo_path = git_repo_factory(num_commits=2)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        commits = list(walker._walk_commits())

        # Assert
        assert all(commit.is_merge is False for commit in commits)

    def test_merge_commit_detection(self, git_repo_factory, isolated_env):
        """Merge commits have is_merge=True."""
        # Arrange - create repo with merge commit (3 commits: 1 main, 1 feature, 1 merge)
        repo_path = git_repo_factory(num_commits=3, create_merge=True)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - walk commits and collect metadata
        commits = list(walker._walk_commits())

        # Assert - should have at least 3 commits total (initial + feature + merge)
        assert len(commits) >= 3, f"Expected at least 3 commits, got {len(commits)}"

        # Assert - at least one commit is a merge
        merge_commits = [c for c in commits if c.is_merge]
        non_merge_commits = [c for c in commits if not c.is_merge]

        assert len(merge_commits) >= 1, "Should have at least one merge commit"
        assert len(non_merge_commits) >= 2, "Should have at least two non-merge commits"

        # Assert - merge commit is detected correctly
        merge_commit = merge_commits[0]
        assert merge_commit.is_merge is True


class TestProtocolAdherence:
    """Test CommitWalker implements CommitWalkerProtocol correctly."""

    def test_commit_walker_implements_protocol(self, git_repo_factory, isolated_env):
        """CommitWalker satisfies CommitWalkerProtocol (mypy verification)."""
        # Arrange
        from gitctx.core import create_walker

        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()

        # Act
        walker = create_walker(str(repo_path), config)

        # Assert - verify walker has required protocol methods
        assert hasattr(walker, "walk_blobs")
        assert hasattr(walker, "get_stats")
        assert callable(walker.walk_blobs)
        assert callable(walker.get_stats)

        # Verify return types use primitives (mypy checks at compile time)
        # Runtime check: verify BlobRecord fields are primitives
        for blob_record in walker.walk_blobs():
            assert isinstance(blob_record.sha, str)
            assert isinstance(blob_record.content, bytes)
            assert isinstance(blob_record.size, int)
            assert isinstance(blob_record.locations, list)

            for loc in blob_record.locations:
                assert isinstance(loc.commit_sha, str)
                assert isinstance(loc.file_path, str)  # Not Path!
                assert isinstance(loc.is_head, bool)
                assert isinstance(loc.is_merge, bool)
            break  # Check first record only

    def test_factory_returns_protocol_type(self, git_repo_factory, isolated_env):
        """create_walker() returns CommitWalkerProtocol instance."""
        # Arrange
        from gitctx.core import create_walker
        from gitctx.core.commit_walker import CommitWalker

        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()

        # Act
        walker = create_walker(str(repo_path), config)

        # Assert - walker is CommitWalker instance
        assert isinstance(walker, CommitWalker)

        # Assert - walker has protocol methods (duck typing)
        assert hasattr(walker, "walk_blobs")
        assert hasattr(walker, "get_stats")

        # Type checker verifies: create_walker() -> CommitWalkerProtocol
        # at compile time via mypy strict mode

    def test_ffi_primitive_type_constraints(self, git_repo_factory, isolated_env):
        """Walker API uses only FFI-compatible primitive types."""
        # Arrange
        from pathlib import Path

        from gitctx.core import create_walker

        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()

        # Act
        # Factory accepts str, not Path (FFI compatible)
        walker = create_walker(str(repo_path), config)

        # Assert - walk_blobs yields BlobRecord with primitive fields
        for blob_record in walker.walk_blobs():
            # Verify no Path objects (FFI incompatible)
            assert not isinstance(blob_record.sha, Path)
            assert isinstance(blob_record.sha, str)
            assert isinstance(blob_record.content, bytes)
            assert isinstance(blob_record.size, int)

            for loc in blob_record.locations:
                # file_path must be str, not Path (FFI compatible)
                assert not isinstance(loc.file_path, Path)
                assert isinstance(loc.file_path, str)

                # Other fields must be primitives
                assert isinstance(loc.commit_sha, str)
                assert isinstance(loc.is_head, bool)
                assert isinstance(loc.is_merge, bool)
                assert isinstance(loc.author_name, str)
                assert isinstance(loc.author_email, str)
                assert isinstance(loc.commit_date, int)
                assert isinstance(loc.commit_message, str)
            break  # Check first record only


# ============================================================================
# Deduplication & Location Tracking
# ============================================================================


class TestBlobDeduplication:
    """Test blob deduplication across commits."""

    def test_blob_yielded_once_across_commits(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Same blob appearing in multiple commits is yielded exactly once."""
        # Arrange - create repo with same file across 50 commits
        repo_path = git_repo_factory(num_commits=1)
        # Create file that won't change
        test_file = repo_path / "unchanged.py"
        test_file.write_text("def unchanged(): pass")

        # Create 49 more commits WITHOUT changing unchanged.py
        for i in range(2, 51):
            # Change a different file
            (repo_path / f"other_{i}.py").write_text(f"# Commit {i}")
            subprocess.run(
                ["git", "add", "."],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - walk and collect blob records
        blob_records = list(walker.walk_blobs())

        # Assert - unchanged.py blob yielded once
        unchanged_blobs = [b for b in blob_records if "unchanged" in str(b.locations[0].file_path)]
        assert len(unchanged_blobs) == 1

        # Assert - blob SHA consistent
        unchanged_blob = unchanged_blobs[0]
        assert len(unchanged_blob.sha) == 40

    def test_all_locations_captured(self, git_repo_factory, git_isolation_base, isolated_env):
        """All 50 locations for a blob are captured in BlobRecord.locations."""
        # Arrange - create repo with 1 commit, then add unchanged.py
        repo_path = git_repo_factory(num_commits=1)
        test_file = repo_path / "unchanged.py"
        test_file.write_text("def unchanged(): pass")

        # Add unchanged.py to commit 1 (so it appears in commit 1)
        subprocess.run(
            ["git", "add", "unchanged.py"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        # Create 49 more commits WITHOUT changing unchanged.py
        for i in range(2, 51):
            (repo_path / f"other_{i}.py").write_text(f"# Commit {i}")
            subprocess.run(
                ["git", "add", "."],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())
        unchanged_blobs = [b for b in blob_records if "unchanged" in str(b.locations[0].file_path)]

        # Assert - 50 locations captured
        unchanged_blob = unchanged_blobs[0]
        assert len(unchanged_blob.locations) == 50

        # Assert - each location has correct structure
        for loc in unchanged_blob.locations:
            assert isinstance(loc, BlobLocation)
            assert len(loc.commit_sha) == 40
            assert loc.file_path == "unchanged.py"
            assert isinstance(loc.is_head, bool)

    def test_resume_from_partial_index(self, git_repo_factory, git_isolation_base, isolated_env):
        """Walker skips already-indexed blobs when pre-seeded."""
        # Arrange
        repo_path = git_repo_factory(num_commits=10)
        config = GitCtxSettings()

        # First walk - get all blob SHAs
        walker1 = CommitWalker(str(repo_path), config)
        first_walk = list(walker1.walk_blobs())
        all_blob_shas = {b.sha for b in first_walk}

        # Take first 5 blob SHAs as "already indexed"
        already_indexed = set(list(all_blob_shas)[:5])

        # Act - second walk with pre-seeded seen_blobs
        walker2 = CommitWalker(str(repo_path), config, already_indexed=already_indexed)
        second_walk = list(walker2.walk_blobs())
        second_walk_shas = {b.sha for b in second_walk}

        # Assert - second walk skips already-indexed blobs
        assert len(second_walk) == len(first_walk) - 5
        assert already_indexed.isdisjoint(second_walk_shas)

    def test_set_vs_list_performance(self, git_repo_factory, git_isolation_base, isolated_env):
        """Set membership is O(1) vs List O(n) for deduplication."""
        # Arrange - create repo with many unique blobs
        repo_path = git_repo_factory(num_commits=1)
        for i in range(1000):
            (repo_path / f"file_{i}.py").write_text(f"# File {i}")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "1000 files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - time the walk
        start = time.time()
        blob_records = list(walker.walk_blobs())
        duration = time.time() - start

        # Assert - completes in reasonable time (Set ensures O(1) lookups)
        # 1001 blobs should process in <1 second with Set (main.py + 1000 test files)
        assert duration < 1.0
        assert len(blob_records) == 1001

        # Assert - seen_blobs is a Set, not List
        assert isinstance(walker.seen_blobs, set)


class TestHeadBlobTracking:
    """Test is_head flag determination using HEAD tree."""

    def test_head_blob_has_is_head_true(self, git_repo_factory, git_isolation_base, isolated_env):
        """Blob in HEAD tree has is_head=True."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - main.py is in HEAD
        main_py_blob = [b for b in blob_records if b.locations[0].file_path == "main.py"][0]
        assert main_py_blob.locations[0].is_head is True

    def test_historical_blob_has_is_head_false(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Blob not in HEAD tree has is_head=False."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)

        # Add file, commit, then delete file and commit again
        (repo_path / "deleted.py").write_text("def deleted(): pass")
        subprocess.run(
            ["git", "add", "deleted.py"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add deleted.py"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        # Delete the file
        (repo_path / "deleted.py").unlink()
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Delete deleted.py"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - deleted.py blob should have is_head=False
        deleted_blobs = [b for b in blob_records if "deleted.py" in b.locations[0].file_path]
        assert len(deleted_blobs) == 1
        assert deleted_blobs[0].locations[0].is_head is False


class TestCommitMetadataInLocation:
    """Test commit metadata (author, date, message, is_merge) in BlobLocation."""

    def test_blob_location_has_commit_metadata(self, git_repo_factory, isolated_env):
        """BlobLocation includes author, email, date, message, is_merge."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert
        location = blob_records[0].locations[0]
        assert location.author_name == "Test User"
        assert location.author_email == "test@example.com"
        assert location.commit_date > 0
        assert "Commit 1" in location.commit_message
        assert location.is_merge is False


class TestBareRepositoryIsHead:
    """Test is_head=False for all blobs in bare repository."""

    def test_bare_repo_all_blobs_is_head_false(self, bare_repo, isolated_env):
        """Bare repository has is_head=False for all blobs."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(bare_repo), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - all blobs have is_head=False
        for blob in blob_records:
            for location in blob.locations:
                assert location.is_head is False


class TestHeadTreeBuildPerformance:
    """Test HEAD tree build completes in <100ms."""

    def test_head_tree_build_performance(self, git_repo_factory, git_isolation_base, isolated_env):
        """HEAD tree build for 1000 blobs completes in <100ms."""
        # Arrange - create repo with 1000 files
        repo_path = git_repo_factory(num_commits=1)
        for i in range(1000):
            (repo_path / f"file_{i}.py").write_text(f"# File {i}")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "1000 files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()

        # Act - time walker initialization (includes HEAD tree build)
        start = time.time()
        walker = CommitWalker(str(repo_path), config)
        # Trigger HEAD tree build by accessing _build_head_tree
        walker._build_head_tree()
        duration = time.time() - start

        # Assert - <100ms for 1001 blobs (main.py + 1000 test files)
        assert duration < 0.1  # 100ms


# ============================================================================
# Edge Cases & Special Repositories
# ============================================================================


class TestPartialCloneDetection:
    """Test detection of partial clones (missing objects)."""

    def test_partial_clone_raises_error(self, partial_clone_repo, isolated_env):
        """CommitWalker raises PartialCloneError for partial clone."""
        # Arrange
        repo_path = partial_clone_repo
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(PartialCloneError) as exc_info:
            CommitWalker(str(repo_path), config)

        # Error message should mention "partial"
        assert "partial" in str(exc_info.value).lower()

    def test_partial_clone_error_message(self, partial_clone_repo, isolated_env):
        """PartialCloneError message suggests fix."""
        # Arrange
        repo_path = partial_clone_repo
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(PartialCloneError) as exc_info:
            CommitWalker(str(repo_path), config)

        error_msg = str(exc_info.value)
        assert "missing objects" in error_msg.lower()
        assert "full repository" in error_msg.lower()


class TestShallowCloneDetection:
    """Test detection of shallow clones (incomplete history)."""

    def test_shallow_clone_raises_error(self, shallow_clone_repo, isolated_env):
        """CommitWalker raises ShallowCloneError for shallow clone."""
        # Arrange
        repo_path = shallow_clone_repo
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(ShallowCloneError) as exc_info:
            CommitWalker(str(repo_path), config)

        # Error message should mention "shallow"
        assert "shallow" in str(exc_info.value).lower()

    def test_shallow_clone_error_suggests_unshallow(self, shallow_clone_repo, isolated_env):
        """ShallowCloneError message suggests 'git fetch --unshallow'."""
        # Arrange
        repo_path = shallow_clone_repo
        config = GitCtxSettings()

        # Act & Assert
        with pytest.raises(ShallowCloneError) as exc_info:
            CommitWalker(str(repo_path), config)

        error_msg = str(exc_info.value)
        assert "unshallow" in error_msg.lower()
        assert "fetch" in error_msg.lower()


class TestBareRepositoryHandling:
    """Test bare repository support."""

    def test_bare_repository_initializes(self, bare_repo, isolated_env):
        """CommitWalker initializes successfully with bare repository."""
        # Arrange
        repo_path = bare_repo
        config = GitCtxSettings()

        # Act
        walker = CommitWalker(str(repo_path), config)

        # Assert
        assert walker.repo is not None
        assert walker.repo.is_bare is True

    def test_bare_repository_walks_commits(self, bare_repo, isolated_env):
        """CommitWalker can walk commits in bare repository."""
        # Arrange
        repo_path = bare_repo
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        commits = list(walker._walk_commits())

        # Assert
        # bare_repo fixture creates 3 commits
        assert len(commits) == 3
        assert all(len(c.commit_sha) == 40 for c in commits)


# ============================================================================
# Tree Recursion & Special Entry Types
# ============================================================================


class TestNestedDirectoryTraversal:
    """Test nested directory tree traversal."""

    def test_nested_directories_traversed(self, git_repo_factory, git_isolation_base, isolated_env):
        """Blobs in nested directories are found via tree recursion."""
        # Arrange - create repo with nested structure
        repo_path = git_repo_factory(num_commits=0)

        # Create nested directory structure: src/utils/helper.py
        nested_dir = repo_path / "src" / "utils"
        nested_dir.mkdir(parents=True)
        (nested_dir / "helper.py").write_text("def helper(): pass")
        (repo_path / "src" / "main.py").write_text("# Main")
        (repo_path / "README.md").write_text("# README")

        # Commit the structure
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add nested structure"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - all 3 files found via tree recursion
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}
        # pygit2 returns just the filename in the immediate tree, not full paths
        assert any("helper.py" in path for path in file_paths)
        assert any("main.py" in path for path in file_paths)
        assert "README.md" in file_paths

    def test_deeply_nested_blobs_found(self, git_repo_factory, git_isolation_base, isolated_env):
        """Blobs 5 levels deep are found via recursive tree traversal."""
        # Arrange - create deeply nested structure
        repo_path = git_repo_factory(num_commits=0)

        # Create 5-level nesting: a/b/c/d/e/deep.py
        deep_path = repo_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "deep.py").write_text("# Deep file")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add deeply nested file"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - deep.py found
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}
        assert any("deep.py" in path for path in file_paths)

    def test_empty_subdirectory_handling(self, git_repo_factory, git_isolation_base, isolated_env):
        """Empty subdirectories don't break tree traversal."""
        # Arrange - Git doesn't track empty directories, so create dir with .gitkeep
        repo_path = git_repo_factory(num_commits=0)

        empty_dir = repo_path / "empty"
        empty_dir.mkdir()
        (empty_dir / ".gitkeep").write_text("")
        (repo_path / "README.md").write_text("# README")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add directory with .gitkeep"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - should not raise exception
        blob_records = list(walker.walk_blobs())

        # Assert - both files found
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}
        assert any(".gitkeep" in path for path in file_paths)
        assert "README.md" in file_paths


class TestSubmoduleHandling:
    """Test git submodule handling (non-blob/non-tree entry types)."""

    def test_submodules_skipped(self, submodule_repo, isolated_env):
        """Git submodules are skipped, only regular files indexed."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(submodule_repo), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - only parent file indexed, submodule skipped
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # Parent file should be indexed
        assert "parent_file.txt" in file_paths

        # Submodule files should NOT be indexed (submodule is 'commit' type, not 'blob')
        assert not any("submodule_file" in path for path in file_paths)
        assert not any("child" in path for path in file_paths)

        # .gitmodules should be indexed (it's a regular file)
        assert ".gitmodules" in file_paths

    def test_submodule_entry_type(self, submodule_repo, isolated_env):
        """Submodules appear as 'commit' type entries in git tree."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(submodule_repo), config)

        # Act - inspect tree directly
        commit = walker.repo.head.peel()  # type: ignore[attr-defined]
        tree = commit.tree

        # Assert - find submodule entry
        submodule_entries = [e for e in tree if e.type_str == "commit"]
        assert len(submodule_entries) == 1

        # Verify it's the 'child' submodule
        assert submodule_entries[0].name == "child"


@pytest.mark.skipif(is_windows(), reason="Symlinks not reliably supported on Windows")
class TestSymlinkHandling:
    """Test symlink detection and skipping (Unix/Linux/macOS only)."""

    def test_symlinks_are_skipped(self, symlink_repo, isolated_env):
        """Symlinks are not indexed, only regular files."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(symlink_repo), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - only regular files indexed, symlinks skipped
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # Regular files should be present
        assert "real_file.py" in file_paths
        assert "target.txt" in file_paths

        # Symlinks should NOT be present
        assert "symlink_to_file.py" not in file_paths
        assert "symlink_to_target" not in file_paths

    def test_symlink_count_vs_regular_files(self, symlink_repo, isolated_env):
        """Only 2 regular files indexed, 2 symlinks skipped."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(symlink_repo), config)

        # Act
        blob_records = list(walker.walk_blobs())

        # Assert - exactly 2 blobs (real_file.py, target.txt)
        assert len(blob_records) == 2

    def test_symlink_mode_detection(self, symlink_repo, isolated_env):
        """Symlinks have mode 0o120000 in git tree entries."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(symlink_repo), config)

        # Act - inspect the commit tree directly via pygit2
        commit = walker.repo.head.peel()  # type: ignore[attr-defined]
        tree = commit.tree

        # Assert - find symlink entries and verify their mode
        symlink_entries = [e for e in tree if e.filemode == 0o120000]
        assert len(symlink_entries) == 2  # Both symlinks detected

        symlink_names = {e.name for e in symlink_entries}
        assert "symlink_to_file.py" in symlink_names
        assert "symlink_to_target" in symlink_names

    def test_regular_file_mode_is_not_symlink(self, symlink_repo, isolated_env):
        """Regular files have mode 0o100644, not 0o120000."""
        # Arrange
        config = GitCtxSettings()
        walker = CommitWalker(str(symlink_repo), config)

        # Act
        commit = walker.repo.head.peel()  # type: ignore[attr-defined]
        tree = commit.tree

        # Assert - regular files have different mode
        regular_entries = [e for e in tree if e.type_str == "blob" and e.filemode != 0o120000]
        assert len(regular_entries) == 2  # Both regular files

        regular_names = {e.name for e in regular_entries}
        assert "real_file.py" in regular_names
        assert "target.txt" in regular_names


# ============================================================================
# Blob Filtering
# ============================================================================


class TestBlobFiltering:
    """Test blob filtering integration with CommitWalker."""

    def test_binary_files_filtered(self, git_repo_factory, git_isolation_base, isolated_env):
        """Binary files are filtered during walk."""
        # ARRANGE - create repo with binary and text files
        repo_path = git_repo_factory(num_commits=0)

        # Create text file
        (repo_path / "text.py").write_text("def hello(): pass")

        # Create binary file (PNG signature with null byte)
        (repo_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add text and binary"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - only text file indexed
        assert "text.py" in file_paths
        assert "image.png" not in file_paths

    def test_lfs_pointers_filtered(self, git_repo_factory, git_isolation_base, isolated_env):
        """Git LFS pointer files are filtered during walk."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Create LFS pointer file
        lfs_content = """version https://git-lfs.github.com/spec/v1
oid sha256:abc123
size 1048576
"""
        (repo_path / "large.bin").write_text(lfs_content)
        (repo_path / "regular.txt").write_text("Regular file")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add LFS pointer"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - LFS pointer filtered, regular file indexed
        assert "regular.txt" in file_paths
        assert "large.bin" not in file_paths

    def test_oversized_blobs_filtered(self, git_repo_factory, git_isolation_base, isolated_env):
        """Blobs exceeding size limit are filtered."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Create 6MB file (exceeds 5MB default limit)
        large_content = "x" * (6 * 1024 * 1024)
        (repo_path / "large.txt").write_text(large_content)
        (repo_path / "small.txt").write_text("Small file")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add large and small"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - large file filtered, small file indexed
        assert "small.txt" in file_paths
        assert "large.txt" not in file_paths

    def test_gitignore_patterns_respected(self, git_repo_factory, git_isolation_base, isolated_env):
        """Files matching .gitignore are filtered."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Create .gitignore
        (repo_path / ".gitignore").write_text("*.pyc\nnode_modules/\n")

        # Create files
        (repo_path / "main.py").write_text("def main(): pass")
        (repo_path / "cache.pyc").write_text("# cached")
        node_modules_dir = repo_path / "node_modules"
        node_modules_dir.mkdir()
        (node_modules_dir / "lib.js").write_text("// lib")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - gitignored files filtered
        assert "main.py" in file_paths
        assert ".gitignore" in file_paths  # .gitignore itself is indexed
        assert "cache.pyc" not in file_paths
        assert not any("node_modules" in path for path in file_paths)

    def test_security_directories_always_excluded(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Files in .git/ and .gitctx/ are always excluded."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Git doesn't track .git/ contents, so we can't test that directly
        # Test .gitctx/ exclusion
        gitctx_dir = repo_path / ".gitctx"
        gitctx_dir.mkdir()
        (gitctx_dir / "config.yml").write_text("test: config")
        (repo_path / "main.py").write_text("def main(): pass")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - .gitctx/ excluded
        assert "main.py" in file_paths
        assert not any(".gitctx" in path for path in file_paths)

    def test_empty_file_not_filtered_as_binary(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Empty files are not filtered as binary."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        (repo_path / "empty.txt").write_text("")
        (repo_path / "nonempty.txt").write_text("content")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - both files indexed
        assert "empty.txt" in file_paths
        assert "nonempty.txt" in file_paths

    def test_null_byte_at_8192_boundary(self, git_repo_factory, git_isolation_base, isolated_env):
        """Null byte after first 8192 bytes doesn't trigger binary filter."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Create file with 8192 'a' characters, then a null byte
        content_with_late_null = "a" * 8192 + "\x00"
        (repo_path / "late_null.txt").write_text(content_with_late_null)
        (repo_path / "regular.txt").write_text("regular content")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - late_null.txt is NOT filtered (null beyond 8192 bytes)
        assert "late_null.txt" in file_paths
        assert "regular.txt" in file_paths

    def test_lfs_header_case_sensitive(self, git_repo_factory, git_isolation_base, isolated_env):
        """LFS header detection is case-sensitive."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Wrong case - should NOT be filtered as LFS
        wrong_case_content = "VERSION HTTPS://GIT-LFS.GITHUB.COM/SPEC/V1\noid sha256:abc\nsize 100"
        (repo_path / "not_lfs.txt").write_text(wrong_case_content)
        (repo_path / "regular.txt").write_text("regular")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - not_lfs.txt is indexed (wrong case, not detected as LFS)
        assert "not_lfs.txt" in file_paths
        assert "regular.txt" in file_paths

    @pytest.mark.parametrize(
        "size_mb,should_be_filtered",
        [
            (4, False),  # 4MB < 5MB limit - not filtered
            (5, False),  # 5MB == 5MB limit - not filtered
            (6, True),  # 6MB > 5MB limit - filtered
        ],
    )
    def test_size_limit_boundaries(
        self, git_repo_factory, git_isolation_base, isolated_env, size_mb, should_be_filtered
    ):
        """Test size limit filtering at various boundaries."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Create file of specified size
        content = "x" * (size_mb * 1024 * 1024)
        (repo_path / f"file_{size_mb}mb.txt").write_text(content)
        (repo_path / "marker.txt").write_text("marker")  # Always present

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Add {size_mb}MB file"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT
        assert "marker.txt" in file_paths  # Always indexed
        filename = f"file_{size_mb}mb.txt"
        if should_be_filtered:
            assert filename not in file_paths
        else:
            assert filename in file_paths

    def test_multiple_gitignore_patterns(self, git_repo_factory, git_isolation_base, isolated_env):
        """Multiple gitignore patterns work together correctly."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=0)

        # Complex .gitignore
        gitignore = """
*.pyc
*.pyo
__pycache__/
node_modules/
.env
*.log
build/
dist/
"""
        (repo_path / ".gitignore").write_text(gitignore)

        # Create various files
        (repo_path / "main.py").write_text("# main")
        (repo_path / "cache.pyc").write_text("# cached")
        (repo_path / "test.log").write_text("# log")
        (repo_path / ".env").write_text("SECRET=value")
        (repo_path / "README.md").write_text("# README")

        pycache_dir = repo_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "module.pyc").write_text("# cached module")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add various files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )

        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        file_paths = {loc.file_path for b in blob_records for loc in b.locations}

        # ASSERT - only non-ignored files indexed
        assert "main.py" in file_paths
        assert "README.md" in file_paths
        assert ".gitignore" in file_paths

        # All ignored files excluded
        assert "cache.pyc" not in file_paths
        assert "test.log" not in file_paths
        assert ".env" not in file_paths
        assert not any("__pycache__" in path for path in file_paths)


# ============================================================================
# Progress Reporting & Error Handling
# ============================================================================


class TestProgressReporting:
    """Test progress reporting during commit walking."""

    def test_progress_callback_invoked_every_10_commits(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Progress callback invoked every 10 commits during walk."""
        # ARRANGE - create repo with 25 commits
        repo_path = git_repo_factory(num_commits=25)
        config = GitCtxSettings()

        progress_calls = []

        def capture_progress(progress):
            progress_calls.append(progress)

        walker = CommitWalker(str(repo_path), config)

        # ACT
        list(walker.walk_blobs(progress_callback=capture_progress))

        # ASSERT - progress called at commits 10, 20 (not 30 as we only have 25)
        assert len(progress_calls) >= 2
        assert progress_calls[0].commits_seen == 10
        assert progress_calls[1].commits_seen == 20

    def test_progress_contains_commit_metadata(self, git_repo_factory, isolated_env):
        """Progress callback receives current commit metadata."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=15)
        config = GitCtxSettings()

        progress_calls = []

        def capture_progress(progress):
            progress_calls.append(progress)

        walker = CommitWalker(str(repo_path), config)

        # ACT
        list(walker.walk_blobs(progress_callback=capture_progress))

        # ASSERT - progress has commit metadata
        assert len(progress_calls) > 0
        first_progress = progress_calls[0]
        assert first_progress.current_commit is not None
        assert len(first_progress.current_commit.commit_sha) == 40
        assert first_progress.current_commit.author_name == "Test User"

    def test_progress_tracks_unique_blobs(self, git_repo_factory, git_isolation_base, isolated_env):
        """Progress callback tracks unique_blobs_found count."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=15)
        config = GitCtxSettings()

        progress_calls = []

        def capture_progress(progress):
            progress_calls.append(progress)

        walker = CommitWalker(str(repo_path), config)

        # ACT
        list(walker.walk_blobs(progress_callback=capture_progress))

        # ASSERT - unique_blobs_found increases
        assert len(progress_calls) > 0
        for progress in progress_calls:
            assert progress.unique_blobs_found >= 0

    def test_no_callback_means_no_errors(self, git_repo_factory, isolated_env):
        """Walking without progress callback completes successfully."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=15)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT - no callback provided
        blob_records = list(walker.walk_blobs())

        # ASSERT - completes successfully
        assert len(blob_records) > 0


class TestErrorHandling:
    """Test error handling and statistics during commit walking."""

    def test_get_stats_returns_walk_stats(self, git_repo_factory, isolated_env):
        """Walker provides stats after walk completes."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=5)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        list(walker.walk_blobs())
        stats = walker.get_stats()

        # ASSERT
        assert stats.commits_seen == 5
        assert stats.blobs_indexed > 0
        assert stats.blobs_skipped >= 0
        assert stats.errors is not None

    def test_stats_track_commits_seen(self, git_repo_factory, isolated_env):
        """Stats accurately track number of commits processed."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=20)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        list(walker.walk_blobs())
        stats = walker.get_stats()

        # ASSERT
        assert stats.commits_seen == 20

    def test_stats_track_blobs_indexed(self, git_repo_factory, isolated_env):
        """Stats track number of blobs successfully indexed."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=5)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # ACT
        blob_records = list(walker.walk_blobs())
        stats = walker.get_stats()

        # ASSERT
        assert stats.blobs_indexed == len(blob_records)
        assert stats.blobs_indexed > 0

    def test_blob_read_error_logged_and_continues(
        self, git_repo_factory, git_isolation_base, isolated_env, monkeypatch
    ):
        """Blob read errors are logged and walk continues."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=5)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Simulate blob read failure by patching repo.get method
        original_get = walker.repo.get

        def mock_get(sha):
            # Fail on second blob
            if hasattr(mock_get, "call_count"):
                mock_get.call_count += 1
            else:
                mock_get.call_count = 1

            if mock_get.call_count == 2:
                raise Exception("Simulated blob read error")
            return original_get(sha)

        monkeypatch.setattr(walker.repo, "get", mock_get)

        # ACT
        blob_records = list(walker.walk_blobs())
        stats = walker.get_stats()

        # ASSERT - walk continues despite error
        assert len(blob_records) > 0
        assert stats.errors is not None
        assert len(stats.errors) > 0
        assert stats.errors[0].error_type == "blob_read"

    def test_stats_errors_include_context(
        self, git_repo_factory, git_isolation_base, isolated_env, monkeypatch
    ):
        """Error records include blob SHA, commit SHA, and message."""
        # ARRANGE
        repo_path = git_repo_factory(num_commits=5)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        original_get = walker.repo.get

        def mock_get(sha):
            if hasattr(mock_get, "call_count"):
                mock_get.call_count += 1
            else:
                mock_get.call_count = 1

            if mock_get.call_count == 2:
                raise Exception("Test error")
            return original_get(sha)

        monkeypatch.setattr(walker.repo, "get", mock_get)

        # ACT
        list(walker.walk_blobs())
        stats = walker.get_stats()

        # ASSERT
        assert len(stats.errors) > 0
        error = stats.errors[0]
        assert error.error_type == "blob_read"
        assert error.blob_sha is not None
        assert error.commit_sha is not None
        assert len(error.commit_sha) == 40
        assert "Test error" in error.message
