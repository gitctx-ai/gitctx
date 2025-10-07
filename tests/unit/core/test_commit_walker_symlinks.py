"""Unit tests for CommitWalker symlink handling.

Tests cover:
- Symlink detection and skipping
- Regular files still indexed when symlinks present
- Platform-specific behavior (Unix/Linux/macOS only)

Note: These tests are skipped on Windows where symlinks are not reliably supported.
"""

import pytest
from tests.conftest import is_windows

from gitctx.core.commit_walker import CommitWalker
from gitctx.core.config import GitCtxSettings


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
