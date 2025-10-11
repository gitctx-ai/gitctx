"""Progress reporting for indexing operations.

Follows TUI_GUIDE.md patterns:
- Default mode: Terse single-line output (git-like)
- Verbose mode: Phase-by-phase progress with statistics
- Spinner: Shows after 5s for long operations
"""

import sys
import time
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class IndexingStats:
    """Statistics for indexing progress."""

    total_commits: int = 0
    total_blobs: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time


class ProgressReporter:
    """Report indexing progress per TUI_GUIDE.md patterns.

    Default mode: Terse single-line output (git-like) with spinner for >5s operations
    Verbose mode: Phase-by-phase progress with statistics
    Spinner: ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ (10 frames, updated every 0.1s)
    """

    def __init__(self, verbose: bool = False):
        """Initialize progress reporter.

        Args:
            verbose: If True, show detailed phase-by-phase progress
        """
        self.verbose = verbose
        self.stats = IndexingStats()
        self.current_phase: str = ""
        self.spinner_active: bool = False
        self.spinner_frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_start_time: float | None = None
        self.last_spinner_update: float = 0.0

    def start(self) -> None:
        """Start progress tracking."""
        self.stats.start_time = time.time()
        # In verbose mode, announce start
        if self.verbose:
            print("→ Starting indexing...\n", file=sys.stderr)
        # In terse mode, spinner will show after 5s (handled in update loop)

    def phase(self, name: str) -> None:
        """Start a new phase (verbose mode only).

        Args:
            name: Phase name (e.g., "Walking commit graph")
        """
        self.current_phase = name
        if self.verbose:
            print(f"→ {name}", file=sys.stderr)

    def update(
        self,
        commits: int = 0,
        blobs: int = 0,
        chunks: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Update statistics (silent in default mode).

        Args:
            commits: Number of commits processed (absolute count)
            blobs: Number of blobs processed (absolute count)
            chunks: Number of chunks created (incremental)
            tokens: Tokens consumed (incremental)
            cost: Cost in USD (incremental)
        """
        # Update stats (use assignment for totals, += for incremental)
        if commits:
            self.stats.total_commits = commits
        if blobs:
            self.stats.total_blobs = blobs
        if chunks:
            self.stats.total_chunks += chunks
        if tokens:
            self.stats.total_tokens += tokens
        if cost:
            self.stats.total_cost_usd += cost

        # In verbose mode, show progress for phase milestones
        if self.verbose and blobs > 0 and blobs % 100 == 0:
            print(f"  Processed {blobs} blobs...", file=sys.stderr)

    def record_error(self) -> None:
        """Record an error (silent tracking)."""
        self.stats.errors += 1

    def finish(self) -> None:
        """Print final summary (both modes).

        Default mode: Single terse line per TUI_GUIDE.md:208-209
        Verbose mode: Detailed table per TUI_GUIDE.md:246-256
        """
        elapsed = self.stats.elapsed_seconds()

        if self.verbose:
            self._print_verbose_summary(elapsed)
        else:
            self._print_terse_summary(elapsed)

    def _print_terse_summary(self, elapsed: float) -> None:
        """Print terse single-line summary (default mode)."""
        # Format: "Indexed 5678 commits (1234 unique blobs) in 8.2s"
        print(
            f"Indexed {self.stats.total_commits:,} commits "
            f"({self.stats.total_blobs:,} unique blobs) in {elapsed:.1f}s"
        )

        # Always show cost summary on next line
        print(f"Tokens: {self.stats.total_tokens:,} | Cost: ${self.stats.total_cost_usd:.4f}")

        if self.stats.errors > 0:
            print(f"Errors: {self.stats.errors}", file=sys.stderr)

    def _print_verbose_summary(self, elapsed: float) -> None:
        """Print detailed statistics table (verbose mode)."""
        print("\n✓ Indexing Complete\n", file=sys.stderr)

        # Statistics table (simplified, no Rich dependencies)
        print("Statistics:", file=sys.stderr)
        print(f"  Commits:      {self.stats.total_commits:,}", file=sys.stderr)
        print(f"  Unique blobs: {self.stats.total_blobs:,}", file=sys.stderr)
        print(f"  Chunks:       {self.stats.total_chunks:,}", file=sys.stderr)
        print(f"  Tokens:       {self.stats.total_tokens:,}", file=sys.stderr)
        print(f"  Cost:         ${self.stats.total_cost_usd:.4f}", file=sys.stderr)
        print(f"  Time:         {str(timedelta(seconds=int(elapsed)))}", file=sys.stderr)

        if self.stats.errors > 0:
            print(f"  Errors:       {self.stats.errors}", file=sys.stderr)
