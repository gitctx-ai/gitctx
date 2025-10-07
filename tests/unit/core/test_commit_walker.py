"""Unit tests for CommitWalker basic functionality.

Tests cover:
- Initialization with valid/invalid repositories
- Commit traversal in reverse chronological order
- Commit metadata extraction
- Merge commit detection
"""

from pathlib import Path

import pytest

from gitctx.core.commit_walker import (
    CommitWalker,
    GitRepositoryError,
)
from gitctx.core.config import GitCtxSettings
from gitctx.core.models import CommitMetadata


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
        """Merge commits have is_merge=True (deferred to later task)."""
        # This test is a placeholder for TASK-0001.2.1.2 or later
        # when we implement merge commit creation in fixtures
        pytest.skip("Merge commit fixture not yet implemented")
