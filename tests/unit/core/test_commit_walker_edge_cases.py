"""Unit tests for CommitWalker edge cases.

Tests cover:
- Partial clone detection
- Shallow clone detection
- Bare repository handling
"""

import pytest

from gitctx.core.commit_walker import (
    CommitWalker,
    PartialCloneError,
    ShallowCloneError,
)
from gitctx.core.config import GitCtxSettings


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
