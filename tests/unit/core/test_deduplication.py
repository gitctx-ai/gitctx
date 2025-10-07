"""Unit tests for blob deduplication logic.

Tests cover:
- Blob appears in 50 commits, yielded once
- All 50 locations captured in BlobRecord
- Deduplication across multiple refs
- Resume from partial index (pre-seeded seen_blobs)
- Memory efficiency (Set vs List benchmark)
"""

from gitctx.core.commit_walker import CommitWalker
from gitctx.core.config import GitCtxSettings
from gitctx.core.models import BlobLocation


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
        import subprocess

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

        import subprocess

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

        import subprocess

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
        import time

        start = time.time()
        blob_records = list(walker.walk_blobs())
        duration = time.time() - start

        # Assert - completes in reasonable time (Set ensures O(1) lookups)
        # 1001 blobs should process in <1 second with Set (main.py + 1000 test files)
        assert duration < 1.0
        assert len(blob_records) == 1001

        # Assert - seen_blobs is a Set, not List
        assert isinstance(walker.seen_blobs, set)
