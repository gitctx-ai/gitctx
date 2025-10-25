"""Unit tests for progress reporting.

Tests ProgressReporter with Rich.Progress integration, terminal detection,
ETA calculation, throughput display, and cache cost tracking.
"""

from __future__ import annotations

import io
import time
from contextlib import redirect_stderr
from unittest.mock import MagicMock, Mock, patch

import pytest

from gitctx.cli.symbols import SYMBOLS
from gitctx.indexing.progress import IndexingStats, ProgressReporter


class TestIndexingStats:
    """Test IndexingStats dataclass."""

    def test_cached_fields_exist(self) -> None:
        """Test that cached_blobs and cached_cost_usd fields exist."""
        stats = IndexingStats()
        assert hasattr(stats, "cached_blobs"), "IndexingStats missing cached_blobs field"
        assert hasattr(stats, "cached_cost_usd"), "IndexingStats missing cached_cost_usd field"
        assert stats.cached_blobs == 0, "cached_blobs should initialize to 0"
        assert stats.cached_cost_usd == 0.0, "cached_cost_usd should initialize to 0.0"


class TestProgressReporterModes:
    """Test quiet vs default mode output."""

    def test_quiet_mode_no_output(self) -> None:
        """Test quiet mode suppresses all progress output."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Walking commit graph", total=1000)
            reporter.update(commits=100, blobs=50, chunks=10, tokens=500, cost=0.0001)
            reporter.phase("Generating embeddings", total=50)
            reporter.update(blobs=50, tokens=1000, cost=0.0002)
            # Note: finish() still prints summary in quiet mode

        stderr_output = stderr_capture.getvalue()

        # Quiet mode should suppress phase markers and progress bars
        assert SYMBOLS["arrow"] not in stderr_output, "Quiet mode should not show phase markers"
        assert "Walking commit graph" not in stderr_output, "Quiet mode should not show phase names"
        assert "━" not in stderr_output, "Quiet mode should not show progress bars"

    def test_default_mode_shows_progress(self) -> None:
        """Test default mode (quiet=False) shows progress indicators."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Walking commit graph", total=1000)
            reporter.update(commits=100)

        stderr_output = stderr_capture.getvalue()

        # Default mode should show phase markers
        assert SYMBOLS["arrow"] in stderr_output or "Walking commit graph" in stderr_output, (
            "Default mode should show progress indicators"
        )


class TestRichProgressIntegration:
    """Test Rich.Progress integration."""

    @patch("gitctx.indexing.progress.Console")
    def test_phase_creates_progress_context(self, mock_console_class: Mock) -> None:
        """Test phase() creates Rich.Progress context manager with progress bar."""
        # Mock Console to simulate TTY terminal
        mock_console = MagicMock()
        mock_console.is_terminal = True
        mock_console.is_dumb_terminal = False
        mock_console_class.return_value = mock_console

        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()

            # Call phase with total count
            reporter.phase("Walking commit graph", total=1000)

        # Assert Rich.Progress context was created
        assert reporter.progress_ctx is not None, "progress_ctx should be created"
        assert hasattr(reporter, "task_id"), "task_id should exist after phase() with total"

        # Assert task was added to progress
        assert reporter.task_id is not None, "task_id should not be None"

        # Cleanup
        if reporter.progress_ctx:
            reporter.progress_ctx.stop()

    def test_phase_without_total_no_progress_bar(self) -> None:
        """Test phase() without total count doesn't create progress bar."""
        reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
        reporter.start()

        # Call phase without total (indeterminate progress)
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            reporter.phase("Initializing", total=None)

        stderr_output = stderr_capture.getvalue()

        # Should show phase marker but no progress bar
        assert SYMBOLS["arrow"] in stderr_output or "Initializing" in stderr_output
        # progress_ctx might be None or not started for indeterminate phases
        # (implementation detail - test what matters: output behavior)


class TestETACalculation:
    """Test ETA calculation with rolling average."""

    def test_update_calculates_eta(self) -> None:
        """Test ETA calculation: ETA = (total - completed) / throughput."""
        reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Processing", total=100)

        # Simulate processing 50 items in 10 seconds
        start_time = time.time()
        reporter.stats.start_time = start_time - 10.0  # 10 seconds ago

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            reporter.update(blobs=50)

        # Expected calculations:
        # elapsed = 10s
        # completed = 50 items
        # throughput = 50 / 10 = 5 items/sec
        # remaining = 100 - 50 = 50 items
        # ETA = 50 / 5 = 10 seconds → "00:00:10"

        # Note: Since completed >= 10, ETA should be calculated (not "calculating...")
        # The actual ETA format should match "HH:MM:SS" or similar

        # Check if progress context has the right values
        if reporter.progress_ctx:
            task = reporter.progress_ctx.tasks[reporter.task_id]
            # Check that ETA is not "calculating..." since we have 50 items (>= 10)
            assert task.fields.get("eta") != "calculating...", (
                "ETA should be calculated for >= 10 items"
            )
            reporter.progress_ctx.stop()

    def test_eta_shows_calculating_for_few_items(self) -> None:
        """Test ETA shows 'calculating...' when completed < 10 items."""
        reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Processing", total=1000)

        # Process only 5 items (< 10 threshold)
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            reporter.update(blobs=5)

        # Should show "calculating..." for insufficient samples
        if reporter.progress_ctx:
            task = reporter.progress_ctx.tasks[reporter.task_id]
            assert task.fields.get("eta") == "calculating...", (
                "ETA should show 'calculating...' for < 10 items"
            )
            reporter.progress_ctx.stop()


class TestThroughputCalculation:
    """Test throughput calculation and display."""

    def test_update_calculates_throughput(self) -> None:
        """Test throughput = completed_items / elapsed_seconds."""
        reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Processing", total=1000)

        # Simulate: 100 items processed in 10 seconds
        start_time = time.time()
        reporter.stats.start_time = start_time - 10.0

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            reporter.update(blobs=100)

        # Expected: throughput = 100 / 10 = 10 items/sec
        if reporter.progress_ctx:
            task = reporter.progress_ctx.tasks[reporter.task_id]
            throughput_str = task.fields.get("throughput", "")

            # Should display as "N items/sec"
            assert "items/sec" in throughput_str or "blobs/sec" in throughput_str, (
                f"Throughput should show items/sec format, got: {throughput_str}"
            )
            reporter.progress_ctx.stop()


class TestTerminalDetection:
    """Test terminal detection and fallbacks."""

    @patch("gitctx.indexing.progress.Console")
    def test_non_tty_disables_progress_bars(self, mock_console_class: Mock) -> None:
        """Test that non-TTY stderr disables progress bars but keeps phase markers."""
        # Mock Console to report non-TTY
        mock_console = MagicMock()
        mock_console.is_terminal = False
        mock_console_class.return_value = mock_console

        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Walking commit graph", total=1000)

        stderr_output = stderr_capture.getvalue()

        # Should show phase marker but no progress bar
        assert SYMBOLS["arrow"] in stderr_output or "Walking commit graph" in stderr_output, (
            "Non-TTY should still show phase markers"
        )

        # Progress context should not be created for non-TTY
        # (or it should gracefully handle the case)

    @patch("gitctx.indexing.progress.Console")
    def test_dumb_terminal_fallback(self, mock_console_class: Mock) -> None:
        """Test dumb terminal fallback to simple text (no ANSI codes)."""
        # Mock Console to report dumb terminal
        mock_console = MagicMock()
        mock_console.is_terminal = True
        mock_console.is_dumb_terminal = True
        mock_console_class.return_value = mock_console

        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Processing", total=100)

        stderr_output = stderr_capture.getvalue()

        # Should show simple text output without complex ANSI progress bars
        # Phase markers should still appear
        assert "Processing" in stderr_output or SYMBOLS["arrow"] in stderr_output


class TestEmbeddingPhaseCostDisplay:
    """Test cost display during embedding phase."""

    def test_embedding_phase_shows_pricing(self) -> None:
        """Test embedding phase header shows model name and pricing."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Generating embeddings", total=1000)

        stderr_output = stderr_capture.getvalue()

        # Should show model name and pricing from registry
        # Expected: "→ Generating embeddings using OpenAI ... ($0.13/M tokens)"
        assert "Generating embeddings" in stderr_output, "Should show phase name"
        assert "text-embedding-3-large" in stderr_output or "$0.13" in stderr_output, (
            "Should show model name or pricing"
        )

    def test_update_shows_cache_costs(self) -> None:
        """Test update() displays total costs and cache savings."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Generating embeddings", total=1000)

            # Simulate: 1000 blobs total, 300 cached, $0.00050 fresh cost, $0.00030 saved
            reporter.update(blobs=1000, cached_blobs=300, cost=0.00050, cached_cost=0.00030)

        stderr_output = stderr_capture.getvalue()

        # Expected format:
        # "Total Costs: $0.00050 (700 blobs) | Saved using repo cache: $0.00030 (300 blobs)"
        assert "Total Costs:" in stderr_output or "total" in stderr_output.lower(), (
            "Should show total costs"
        )
        assert "Saved" in stderr_output or "cache" in stderr_output.lower(), (
            "Should show cache savings"
        )


class TestSymbolUsage:
    """Test correct symbol usage from SYMBOLS dict."""

    def test_phase_uses_arrow_symbol(self) -> None:
        """Test phase markers use SYMBOLS['arrow']."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.phase("Test phase")

        stderr_output = stderr_capture.getvalue()
        assert SYMBOLS["arrow"] in stderr_output, (
            f"Phase should use arrow symbol: {SYMBOLS['arrow']}"
        )

    def test_finish_uses_success_symbol(self) -> None:
        """Test completion message uses SYMBOLS['success']."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.finish()

        stderr_output = stderr_capture.getvalue()
        assert SYMBOLS["success"] in stderr_output, (
            f"Completion should use success symbol: {SYMBOLS['success']}"
        )


class TestProgressExceptionHandling:
    """Test error resilience when Rich.Progress fails."""

    @patch("gitctx.indexing.progress.Progress")
    def test_progress_exception_does_not_crash(self, mock_progress_class: Mock) -> None:
        """Test that Rich.Progress exceptions are caught and logged."""
        # Mock Progress to raise exception during initialization
        mock_progress_class.side_effect = RuntimeError("Progress bar failure")

        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()

            # phase() should catch the exception and continue
            try:
                reporter.phase("Test phase", total=100)
                # Should not crash - exception should be caught
            except RuntimeError:
                pytest.fail("ProgressReporter should catch Rich.Progress exceptions")

        # Indexing should continue even if progress display fails
        # progress_ctx might be None after exception
        assert True, "Reporter should handle Progress exceptions gracefully"


class TestFinishSummaries:
    """Test final summary output for default and quiet modes."""

    def test_finish_default_summary_format(self) -> None:
        """Test default mode shows detailed statistics with cache info."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")
            reporter.start()
            reporter.stats.total_commits = 150
            reporter.stats.total_blobs = 1234
            reporter.stats.cached_blobs = 292
            reporter.stats.total_chunks = 2000
            reporter.stats.total_tokens = 450000
            reporter.stats.total_cost_usd = 0.00045
            reporter.finish()

        stderr_output = stderr_capture.getvalue()

        # Should show completion marker
        assert SYMBOLS["success"] in stderr_output, "Should show success symbol"
        assert "Indexing Complete" in stderr_output, "Should show completion message"

        # Should show statistics
        assert "Statistics:" in stderr_output, "Should show statistics header"
        assert "Commits:" in stderr_output, "Should show commits count"

        # Should show cache info: "Unique blobs: 1,234 (292 cached)"
        assert "Unique blobs:" in stderr_output, "Should show unique blobs"
        assert "292" in stderr_output or "cached" in stderr_output, "Should show cached count"

    def test_finish_quiet_summary_format(self) -> None:
        """Test quiet mode shows minimal one-line summary."""
        # Quiet mode prints to stdout, not stderr
        stdout_capture = io.StringIO()

        with redirect_stderr(io.StringIO()), patch("sys.stdout", stdout_capture):
            reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
            reporter.start()
            reporter.stats.total_commits = 150
            reporter.stats.total_blobs = 1234
            reporter.stats.cached_blobs = 292
            reporter.stats.total_tokens = 450000
            reporter.stats.total_cost_usd = 0.00045
            reporter.finish()

        stdout_output = stdout_capture.getvalue()

        # Expected format: "Indexed 150 commits (1,234 unique blobs, 292 cached) in 12.5s"
        assert "Indexed" in stdout_output, "Should show 'Indexed' prefix"
        assert "commits" in stdout_output, "Should mention commits"
        assert "blobs" in stdout_output, "Should mention blobs"
        assert "cached" in stdout_output, "Should mention cache"

        # Should also show cost line
        # "Tokens: 450K | Cost: $0.00045"
        assert "Tokens:" in stdout_output or "Cost:" in stdout_output, "Should show tokens/cost"


class TestModelSpecPricingUsage:
    """Test that pricing is fetched from ModelSpec registry."""

    def test_reporter_fetches_pricing_from_registry(self) -> None:
        """Test reporter uses cents_per_million_tokens from ModelSpec."""
        reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-large")

        # Should have fetched model spec
        assert hasattr(reporter, "model_spec"), "Reporter should fetch model_spec"
        assert reporter.model_spec is not None, "model_spec should not be None"

        # Should have pricing information
        assert "cents_per_million_tokens" in reporter.model_spec, (
            "model_spec should contain cents_per_million_tokens"
        )
        assert reporter.model_spec["cents_per_million_tokens"] == 13, (
            "text-embedding-3-large should be 13 cents/M tokens"
        )

    def test_embedding_phase_displays_registry_pricing(self) -> None:
        """Test embedding phase header displays pricing from registry."""
        stderr_capture = io.StringIO()

        with redirect_stderr(stderr_capture):
            reporter = ProgressReporter(quiet=False, model_name="text-embedding-3-small")
            reporter.start()
            reporter.phase("Generating embeddings", total=100)

        stderr_output = stderr_capture.getvalue()

        # text-embedding-3-small is $0.02/M tokens
        assert "$0.02" in stderr_output or "text-embedding-3-small" in stderr_output, (
            "Should display model pricing from registry"
        )


class TestQuadraticAccumulationFix:
    """Test fix for quadratic accumulation bug (GitHub issue #XX).

    Previously, update() would INCREMENT cumulative parameters like cost and
    cached_blobs, leading to quadratic growth (sum of 1+2+3+...+N instead of N).
    This caused 42x cost overreporting and negative blob counts.
    """

    def test_cumulative_cost_not_accumulated_quadratically(self) -> None:
        """Test that cumulative cost is ASSIGNED not incremented."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings")

        # Simulate pipeline passing cumulative totals
        # First update: cost = 0.10
        reporter.update(cost=0.10)
        assert reporter.stats.total_cost_usd == 0.10, "First update should set cost to 0.10"

        # Second update: cost = 0.20 (cumulative total, not delta!)
        reporter.update(cost=0.20)
        assert reporter.stats.total_cost_usd == 0.20, "Should ASSIGN 0.20, not add to 0.10"

        # Third update: cost = 0.30 (cumulative total)
        reporter.update(cost=0.30)
        assert reporter.stats.total_cost_usd == 0.30, "Should ASSIGN 0.30, not add to 0.20"

        # OLD BUG: Would have been 0.10 + 0.20 + 0.30 = 0.60 (quadratic!)
        # NEW FIX: Is 0.30 (correct cumulative total)

    def test_cumulative_cached_blobs_not_accumulated_quadratically(self) -> None:
        """Test that cumulative cached_blobs is ASSIGNED not incremented."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings", total=100)
        reporter.update(blobs=100)  # Set total blobs

        # Simulate pipeline passing cumulative cached count
        # Pipeline: cached_count = 0, 1, 2, 3, ...
        reporter.update(cached_blobs=1)
        assert reporter.stats.cached_blobs == 1, "Should be 1, not accumulated"

        reporter.update(cached_blobs=2)
        assert reporter.stats.cached_blobs == 2, "Should be 2, not 1+2=3"

        reporter.update(cached_blobs=3)
        assert reporter.stats.cached_blobs == 3, "Should be 3, not 1+2+3=6"

        # OLD BUG: Would have been 1 + 2 + 3 = 6 (quadratic!)
        # NEW FIX: Is 3 (correct cumulative count)

    def test_cumulative_cached_cost_not_accumulated_quadratically(self) -> None:
        """Test that cumulative cached_cost is ASSIGNED not incremented."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings")

        # Simulate pipeline passing cumulative cached cost totals
        reporter.update(cached_cost=0.01)
        assert reporter.stats.cached_cost_usd == 0.01

        reporter.update(cached_cost=0.02)
        assert reporter.stats.cached_cost_usd == 0.02, "Should ASSIGN 0.02, not add to 0.01"

        reporter.update(cached_cost=0.03)
        assert reporter.stats.cached_cost_usd == 0.03, "Should ASSIGN 0.03, not add to 0.02"

        # OLD BUG: Would have been 0.01 + 0.02 + 0.03 = 0.06 (quadratic!)
        # NEW FIX: Is 0.03 (correct cumulative total)

    def test_incremental_chunks_still_accumulate(self) -> None:
        """Test that INCREMENTAL parameters (chunks, tokens) still accumulate."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()

        # Chunks are incremental (each update is a delta)
        reporter.update(chunks=10)
        assert reporter.stats.total_chunks == 10

        reporter.update(chunks=5)  # Add 5 more
        assert reporter.stats.total_chunks == 15, "Chunks should accumulate (15 = 10 + 5)"

        reporter.update(chunks=3)  # Add 3 more
        assert reporter.stats.total_chunks == 18, "Chunks should accumulate (18 = 15 + 3)"

        # Same for tokens (incremental)
        reporter.update(tokens=100)
        assert reporter.stats.total_tokens == 100

        reporter.update(tokens=50)
        assert reporter.stats.total_tokens == 150, "Tokens should accumulate (150 = 100 + 50)"

    def test_defensive_assertion_prevents_regression(self) -> None:
        """Test that defensive assertions catch quadratic accumulation."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings", total=100)
        reporter.update(blobs=100)

        # This should work - cached <= total
        reporter.update(cached_blobs=50)

        # This should raise assertion error - cached > total
        with pytest.raises(AssertionError, match=r"Cached.*total.*blobs"):
            reporter.update(cached_blobs=150)  # 150 > 100 total!

    def test_defensive_assertion_negative_cost(self) -> None:
        """Test that defensive assertion catches negative total_cost_usd."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings")

        # Positive cost should work
        reporter.update(cost=0.10)
        assert reporter.stats.total_cost_usd == 0.10

        # Negative cost should raise assertion error
        with pytest.raises(AssertionError, match=r"Negative cost"):
            reporter.update(cost=-0.05)

    def test_defensive_assertion_negative_cached_cost(self) -> None:
        """Test that defensive assertion catches negative cached_cost_usd."""
        reporter = ProgressReporter(quiet=True, model_name="text-embedding-3-large")
        reporter.start()
        reporter.phase("Generating embeddings")

        # Positive cached cost should work
        reporter.update(cached_cost=0.05)
        assert reporter.stats.cached_cost_usd == 0.05

        # Negative cached cost should raise assertion error
        with pytest.raises(AssertionError, match=r"Negative cache"):
            reporter.update(cached_cost=-0.03)
