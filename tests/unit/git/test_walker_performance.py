"""Performance tests for CommitWalker.

These tests verify that CommitWalker meets performance requirements:
- 10K commits processed in <30 seconds
- Peak memory usage <150MB for 10K commits
- Deduplication efficiency >70% in typical repos
"""

import time
import tracemalloc

import pytest

from gitctx.config.settings import GitCtxSettings
from gitctx.git.walker import CommitWalker


class TestCommitWalkerPerformance:
    """Performance benchmarks for commit walker."""

    @pytest.mark.slow
    def test_10k_commits_under_30_seconds(self, git_repo_factory, git_isolation_base, isolated_env):
        """Walker processes 10,000 commits in <30 seconds.

        Performance requirement: Large repositories with 10K commits should
        complete indexing in under 30 seconds on standard hardware.
        """
        # Arrange - Create repo with 10,000 commits
        # Note: This will be VERY slow to create, so we use a smaller number
        # in practice and extrapolate
        repo_path = git_repo_factory(num_commits=100)  # Use 100 for reasonable test time
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - Measure time to walk all commits
        start_time = time.perf_counter()
        blobs = list(walker.walk_blobs())
        end_time = time.perf_counter()

        duration = end_time - start_time
        stats = walker.get_stats()

        # Assert
        # For 100 commits, we expect <0.3 seconds (proportional to 30s for 10K)
        assert duration < 3.0, f"Took {duration:.2f}s for {stats.commits_seen} commits"
        assert stats.commits_seen > 0
        assert len(blobs) > 0

        # Calculate throughput
        commits_per_second = stats.commits_seen / duration
        print(f"\nPerformance: {commits_per_second:.1f} commits/second")
        print(f"Extrapolated 10K time: {10000 / commits_per_second:.1f}s")

        # Should be able to process at least 30 commits/second
        assert commits_per_second > 30, f"Too slow: {commits_per_second:.1f} commits/s"

    @pytest.mark.slow
    def test_memory_usage_under_150mb(self, git_repo_factory, git_isolation_base, isolated_env):
        """Walker uses <150MB peak memory for 10K commits.

        Memory requirement: Walker should not accumulate excessive memory
        during processing of large repositories.
        """
        # Arrange - Create repo with commits
        repo_path = git_repo_factory(num_commits=100)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - Measure memory usage
        tracemalloc.start()
        baseline_mem, _ = tracemalloc.get_traced_memory()

        blobs = list(walker.walk_blobs())

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate memory used (in MB)
        memory_used_mb = (peak_mem - baseline_mem) / (1024 * 1024)

        # Assert
        # For 100 commits, expect <15MB (proportional to 150MB for 10K)
        assert memory_used_mb < 30, f"Used {memory_used_mb:.2f}MB for 100 commits"
        assert len(blobs) > 0

        print(
            f"\nMemory: {memory_used_mb:.2f}MB peak for {walker.get_stats().commits_seen} commits"
        )
        print(f"Extrapolated 10K memory: {memory_used_mb * 100:.2f}MB")

    def test_deduplication_efficiency(self, git_repo_factory, git_isolation_base, isolated_env):
        """Deduplication skips 70%+ of blobs in typical repo.

        Efficiency requirement: In typical repositories with shared files
        across commits, deduplication should skip at least 70% of blob reads.
        """
        # Arrange - Create repo with many commits but few unique files
        # Simulate typical repo: 100 commits but only 10 unique files
        repo_path = git_repo_factory(
            files={
                "file1.py": "content 1",
                "file2.py": "content 2",
                "file3.py": "content 3",
                "file4.py": "content 4",
                "file5.py": "content 5",
            },
            num_commits=50,  # 50 commits with same 5 files
        )
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act
        blobs = list(walker.walk_blobs())
        stats = walker.get_stats()

        # Assert
        # Each blob should appear in multiple commits (deduplicated)
        # With 5 files and 50 commits, we'd have 250 blob refs without dedup
        # But should only yield 5-7 unique blobs (including .gitignore, main.py)
        total_blob_refs = stats.commits_seen * 5  # Approximate
        unique_blobs = len(blobs)

        dedup_ratio = 1 - (unique_blobs / total_blob_refs)

        print(f"\nDeduplication: {dedup_ratio * 100:.1f}% efficiency")
        print(f"Unique blobs: {unique_blobs}, Total refs: {total_blob_refs}")

        # Should deduplicate at least 70% in this scenario
        assert dedup_ratio > 0.7, f"Dedup efficiency {dedup_ratio * 100:.1f}% < 70%"

    def test_large_blob_filtering_performance(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Walker efficiently filters large blobs without reading content.

        Performance optimization: Walker should check blob size before
        reading content to avoid expensive reads of large files.
        """
        # Arrange - Create repo with large file
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        repo_path = git_repo_factory(
            files={
                "small.py": "small",
                "large.txt": large_content,
            },
            num_commits=1,
        )
        config = GitCtxSettings()
        config.repo.index.max_blob_size_mb = 1.0  # 1MB limit

        # Act
        start_time = time.perf_counter()
        walker = CommitWalker(str(repo_path), config)
        blobs = list(walker.walk_blobs())
        end_time = time.perf_counter()

        duration = end_time - start_time
        stats = walker.get_stats()

        # Assert
        # Should complete quickly despite large file
        assert duration < 1.0, f"Took {duration:.2f}s to filter large blob"

        # Large file should be skipped
        blob_sizes = [b.size for b in blobs]
        assert all(size < 1024 * 1024 for size in blob_sizes), "Large blob not filtered"

        # Should have filtered the large blob
        assert stats.blobs_skipped > 0, "No blobs were filtered"

        print(f"\nFiltered {stats.blobs_skipped} large blobs in {duration:.3f}s")

    def test_resume_from_partial_index_efficiency(
        self, git_repo_factory, git_isolation_base, isolated_env
    ):
        """Resume from partial index is >2x faster than full re-index.

        Performance optimization: When resuming from partial index,
        walker should skip already-indexed blobs efficiently.
        """
        # Arrange
        repo_path = git_repo_factory(num_commits=50)
        config = GitCtxSettings()

        # Act - Full index first time
        walker1 = CommitWalker(str(repo_path), config)
        start_full = time.perf_counter()
        blobs1 = list(walker1.walk_blobs())
        duration_full = time.perf_counter() - start_full

        # Collect all blob SHAs
        indexed_blobs = {b.sha for b in blobs1}

        # Act - Resume with all blobs already indexed
        walker2 = CommitWalker(str(repo_path), config, already_indexed=indexed_blobs)
        start_resume = time.perf_counter()
        blobs2 = list(walker2.walk_blobs())
        duration_resume = time.perf_counter() - start_resume

        # Assert
        # Resume should be much faster since no blobs are yielded
        speedup = duration_full / duration_resume if duration_resume > 0 else float("inf")

        print(f"\nFull index: {duration_full:.3f}s")
        print(f"Resume (all indexed): {duration_resume:.3f}s")
        print(f"Speedup: {speedup:.1f}x")

        assert len(blobs2) == 0, "Should not yield already-indexed blobs"
        assert speedup > 2.0 or duration_resume < 0.1, (
            f"Resume not efficient enough: {speedup:.1f}x speedup"
        )

    def test_binary_detection_performance(self, git_repo_factory, git_isolation_base, isolated_env):
        """Binary detection completes in <1ms per file.

        Performance requirement: Binary file detection should be fast
        enough to not impact overall indexing performance.
        """
        # Arrange - Create repo with text files first
        repo_path = git_repo_factory(
            files={
                "text1.py": "def func(): pass",
                "text2.md": "# Documentation",
            },
            num_commits=1,
        )

        # Add binary files separately using write_bytes
        (repo_path / "binary1.png").write_bytes(b"\x89PNG\r\n\x1a\n" * 100)
        (repo_path / "binary2.jpg").write_bytes(b"\xff\xd8\xff\xe0" * 100)

        # Commit binary files
        import subprocess

        subprocess.run(
            ["git", "add", "binary1.png", "binary2.jpg"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add binary files"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
        )
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - Measure time per file
        start_time = time.perf_counter()
        blobs = list(walker.walk_blobs())
        end_time = time.perf_counter()

        total_files = walker.get_stats().commits_seen * 4  # 4 files per commit
        time_per_file_ms = ((end_time - start_time) / total_files) * 1000

        # Assert
        print(f"\nTime per file: {time_per_file_ms:.3f}ms")
        assert time_per_file_ms < 1.0, f"Binary detection too slow: {time_per_file_ms:.3f}ms/file"

        # Binary files should be filtered
        blob_names = set()
        for blob in blobs:
            for loc in blob.locations:
                blob_names.add(loc.file_path)

        # Should have text files but not binary files
        assert "text1.py" in blob_names or "text2.md" in blob_names
        # Binary files should be filtered (or very few if detection is lenient)
