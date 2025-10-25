"""Unit tests for progress reporting (TDD approach)."""

from unittest.mock import patch

from gitctx.cli.symbols import SYMBOLS
from gitctx.indexing.progress import IndexingStats, ProgressReporter


class TestIndexingStats:
    """Test IndexingStats dataclass."""

    def test_elapsed_seconds(self):
        """Test elapsed_seconds() returns correct time delta."""

        # Create stats with mocked start time
        with patch("time.time") as mock_time:
            # Start time: 100.0
            mock_time.return_value = 100.0
            stats = IndexingStats(start_time=100.0)

            # Current time: 108.5 (8.5 seconds elapsed)
            mock_time.return_value = 108.5
            elapsed = stats.elapsed_seconds()

            assert elapsed == 8.5

    def test_initial_values(self):
        """Test IndexingStats initializes with zero values."""

        stats = IndexingStats()
        assert stats.total_commits == 0
        assert stats.total_blobs == 0
        assert stats.total_chunks == 0
        assert stats.total_tokens == 0
        assert stats.total_cost_usd == 0.0
        assert stats.errors == 0
        assert stats.start_time == 0.0


class TestProgressReporterTerse:
    """Test ProgressReporter in default (terse) mode."""

    def test_terse_mode_output(self, capsys):
        """Test terse mode produces single-line summary."""

        # Create reporter in terse mode
        reporter = ProgressReporter(quiet=True)

        # Start and update with mock time
        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()

            # Update with test data
            reporter.update(commits=5678, blobs=1234, chunks=3456, tokens=125000, cost=0.0163)

            # Finish after 8.2 seconds
            mock_time.return_value = 108.2
            reporter.finish()

        # Capture output
        captured = capsys.readouterr()

        # Assert quiet mode format (includes cached count now)
        assert "Indexed 5,678 commits (1,234 unique blobs, 0 cached) in 8.2s" in captured.out
        assert "Tokens: 125,000" in captured.out
        assert "Cost: $0.0163" in captured.out

    def test_terse_mode_shows_errors(self, capsys):
        """Test terse mode displays error count."""

        reporter = ProgressReporter(quiet=True)

        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()

            # Record some errors
            reporter.record_error()
            reporter.record_error()
            reporter.record_error()

            mock_time.return_value = 105.0
            reporter.finish()

        captured = capsys.readouterr()
        assert "Errors: 3" in captured.err

    def test_empty_repo_no_division_error(self, capsys):
        """Test terse mode handles zero values gracefully."""

        reporter = ProgressReporter(quiet=True)

        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()

            # No updates - all zeros
            mock_time.return_value = 100.1
            reporter.finish()

        captured = capsys.readouterr()
        assert "Indexed 0 commits (0 unique blobs, 0 cached)" in captured.out
        assert "Tokens: 0" in captured.out
        assert "$0.0000" in captured.out


class TestProgressReporterVerbose:
    """Test ProgressReporter in verbose mode."""

    def test_verbose_mode_shows_phases(self, capsys):
        """Test verbose mode displays phase markers."""

        reporter = ProgressReporter(quiet=False)

        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()

            # Announce phases
            reporter.phase("Walking commit graph")
            reporter.phase("Generating embeddings")

            reporter.update(commits=100, blobs=50, chunks=200, tokens=10000, cost=0.0013)

            mock_time.return_value = 110.5
            reporter.finish()

        captured = capsys.readouterr()

        # Assert phase markers in stderr (use platform-appropriate symbols)
        assert f"{SYMBOLS['arrow']} Walking commit graph" in captured.err
        # Generating embeddings includes model pricing in the message
        assert f"{SYMBOLS['arrow']} Generating embeddings" in captured.err
        assert "text-embedding-3-large" in captured.err

        # Assert verbose summary (use platform-appropriate symbols)
        assert f"{SYMBOLS['success']} Indexing Complete" in captured.err
        assert "Statistics:" in captured.err
        assert "Commits:" in captured.err
        assert "Unique blobs:" in captured.err
        assert "cached" in captured.err  # Shows cached count
        assert "Chunks:" in captured.err
        assert "Tokens:" in captured.err
        assert "Cost:" in captured.err
        assert "Time:" in captured.err

    def test_verbose_mode_handles_multiple_updates(self, capsys):
        """Test verbose mode handles multiple updates correctly."""

        reporter = ProgressReporter(quiet=False)

        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()
            reporter.phase("Processing")

            # Multiple updates (simulating incremental progress)
            reporter.update(blobs=100)
            reporter.update(blobs=200)  # This sets total to 200, not increments by 200

            mock_time.return_value = 105.0
            reporter.finish()

        captured = capsys.readouterr()
        # Check that final summary shows correct totals
        assert "Unique blobs: 200" in captured.err
        assert f"{SYMBOLS['success']} Indexing Complete" in captured.err


class TestProgressReporterErrorTracking:
    """Test error tracking functionality."""

    def test_error_counting(self):
        """Test record_error() increments error counter."""

        reporter = ProgressReporter()

        assert reporter.stats.errors == 0

        reporter.record_error()
        assert reporter.stats.errors == 1

        reporter.record_error()
        reporter.record_error()
        assert reporter.stats.errors == 3

    def test_errors_displayed_in_summary(self, capsys):
        """Test errors shown in final summary."""

        reporter = ProgressReporter(quiet=True)

        with patch("time.time") as mock_time:
            mock_time.return_value = 100.0
            reporter.start()

            reporter.record_error()
            reporter.record_error()

            mock_time.return_value = 102.0
            reporter.finish()

        captured = capsys.readouterr()
        assert "Errors: 2" in captured.err
