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
from pathlib import Path
from typing import TypedDict

from gitctx.cli.symbols import SYMBOLS


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
        self.spinner_frames = SYMBOLS["spinner_frames"]
        self.spinner_start_time: float | None = None
        self.last_spinner_update: float = 0.0

    def start(self) -> None:
        """Start progress tracking."""
        self.stats.start_time = time.time()
        # In verbose mode, announce start
        if self.verbose:
            print(f"{SYMBOLS['arrow']} Starting indexing...\n", file=sys.stderr)
        # In terse mode, spinner will show after 5s (handled in update loop)

    def phase(self, name: str) -> None:
        """Start a new phase (verbose mode only).

        Args:
            name: Phase name (e.g., "Walking commit graph")
        """
        self.current_phase = name
        if self.verbose:
            print(f"{SYMBOLS['arrow']} {name}", file=sys.stderr)

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
        print(f"\n{SYMBOLS['success']} Indexing Complete\n", file=sys.stderr)

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


class CostEstimate(TypedDict):
    """Cost estimation result."""

    total_files: int
    total_lines: int
    estimated_tokens: int
    estimated_cost: float
    min_cost: float
    max_cost: float


class CostEstimator:
    """Estimate indexing costs before processing.

    Uses conservative token-per-line estimates to provide budget planning
    guidance before running expensive embedding operations.
    """

    # Conservative estimate: 5.0 tokens/line
    # Empirical data: Python ~10, JavaScript ~7, SQL ~11.5 tokens/line
    # Conservative: 5.0 tokens/line (accounts for blank lines, comments)
    # Expected to under-estimate by ~30-50% (safer for budget planning)
    # Source: https://prompt.16x.engineer/blog/code-to-tokens-conversion
    TOKENS_PER_LINE = 5.0

    # Model pricing: text-embedding-3-large
    COST_PER_1K_TOKENS = 0.00013

    def estimate_repo_cost(self, repo_path: Path) -> CostEstimate:
        """Estimate cost for indexing a repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Dictionary with token and cost estimates
        """
        total_lines = self._count_lines(repo_path)
        total_files = self._count_files(repo_path)

        estimated_tokens = int(total_lines * self.TOKENS_PER_LINE)
        estimated_cost = (estimated_tokens / 1000) * self.COST_PER_1K_TOKENS

        # Confidence range (±20%)
        min_cost = estimated_cost * 0.8
        max_cost = estimated_cost * 1.2

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "estimated_tokens": estimated_tokens,
            "estimated_cost": estimated_cost,
            "min_cost": min_cost,
            "max_cost": max_cost,
        }

    def _count_lines(self, repo_path: Path) -> int:
        """Count lines of code in working directory.

        Walks working directory with pathlib, counts lines in ALL text files.
        gitctx supports 60+ extensions across 27 languages, defaulting
        unknown types to markdown. Cost estimator counts everything.

        TASK-0001.2.5.4 will integrate with CommitWalker for commit-aware counting.

        Args:
            repo_path: Path to repository root

        Returns:
            Total line count across all text files
        """
        from gitctx.core.language_detection import EXTENSION_TO_LANGUAGE

        total_lines = 0
        supported_extensions = set(EXTENSION_TO_LANGUAGE.keys())

        for file in repo_path.rglob("*"):
            if not file.is_file():
                continue

            # Exclude .git directory
            if ".git" in file.parts:
                continue

            # Count supported extensions OR extensionless text files (Makefile, Dockerfile, etc.)
            # Avoids trying to read known binary extensions (.exe, .bin, .dll)
            if file.suffix.lower() in supported_extensions or not file.suffix:
                try:
                    total_lines += len(file.read_text().splitlines())
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue  # Skip binary/inaccessible files

        return total_lines

    def _count_files(self, repo_path: Path) -> int:
        """Count indexable files in working directory.

        Counts all text files (60+ extensions + unknown defaulting to markdown).

        Args:
            repo_path: Path to repository root

        Returns:
            Count of indexable files
        """
        from gitctx.core.language_detection import EXTENSION_TO_LANGUAGE

        count = 0
        supported_extensions = set(EXTENSION_TO_LANGUAGE.keys())

        for file in repo_path.rglob("*"):
            if not file.is_file():
                continue

            # Exclude .git directory
            if ".git" in file.parts:
                continue

            # Count supported extensions OR extensionless text files (Makefile, Dockerfile, etc.)
            # Matches _count_lines logic - avoid counting known binary extensions
            if file.suffix.lower() in supported_extensions or not file.suffix:
                count += 1

        return count
