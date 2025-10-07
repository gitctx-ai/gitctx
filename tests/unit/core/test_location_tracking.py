"""Unit tests for location metadata tracking.

Tests cover:
- is_head flag for HEAD vs historical blobs
- Commit metadata in BlobLocation
- Bare repository is_head handling
- HEAD tree build performance
"""

import subprocess
import time

from gitctx.core.commit_walker import CommitWalker
from gitctx.core.config import GitCtxSettings


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
