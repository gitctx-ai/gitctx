"""Unit tests for CommitWalker edge cases.

Tests cover:
- Partial clone detection
- Shallow clone detection
- Bare repository handling
- Nested directory traversal
"""

import subprocess

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


class TestNestedDirectoryTraversal:
    """Test nested directory tree traversal (covers lines 152-156)."""

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
    """Test git submodule handling (covers non-blob/non-tree entry types)."""

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
