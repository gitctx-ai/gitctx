# STORY-0001.2.5: Progress Tracking and Cost Estimation

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 3
**Progress**: ░░░░░░░░░░ 0% (0/4 tasks complete)

## User Story

As a developer using gitctx
I want to see accurate progress and cost estimates during indexing
So that I can monitor long-running operations and understand the financial impact of indexing my codebase

## Acceptance Criteria

- [ ] Display real-time progress during indexing (percentage complete, chunks processed, time elapsed)
- [ ] Show estimated time remaining based on current throughput
- [ ] Track and display token usage across all embedding API calls
- [ ] Calculate and display costs in USD (accurate to 4 decimal places)
- [ ] Show breakdown: tokens used, cost per operation, total cost
- [ ] Display progress using Rich progress bars and live displays
- [ ] Update progress every N chunks (configurable, default 100)
- [ ] Log final summary: total chunks, total tokens, total cost, time elapsed
- [ ] Handle cancellation gracefully (show partial progress, costs incurred)
- [ ] Provide cost estimates before starting (based on repo size analysis)

## BDD Scenarios

```gherkin
Feature: Progress Tracking and Cost Estimation

  Scenario: Real-time progress display during indexing
    Given a repository with 1000 blobs to index
    When I run "gitctx index"
    Then I should see a progress bar
    And progress should show: percentage, chunks processed, ETA
    And progress should update in real-time
    And console output should use Rich formatting

  Scenario: Accurate token counting
    Given indexing processes 5000 chunks
    And each chunk averages 400 tokens
    When indexing completes
    Then total tokens should be reported as 2,000,000
    And token count should match sum of individual chunk token counts
    And accuracy should be ±1%

  Scenario: Cost calculation accuracy
    Given 2,000,000 tokens processed
    And text-embedding-3-large costs $0.13 per 1M tokens
    When I view the final summary
    Then total cost should be displayed as $0.2600
    And cost should be accurate to 4 decimal places
    And cost breakdown should show: tokens × rate = cost

  Scenario: Pre-indexing cost estimate
    Given a repository with 500 files totaling 2MB
    When I run "gitctx index --dry-run"
    Then I should see estimated tokens: ~1.5M
    And estimated cost: ~$0.20
    And estimate should include confidence range (±20%)
    And user should be prompted to confirm before proceeding

  Scenario: Progress breakdown by phase
    Given indexing with multiple phases
    When I monitor progress
    Then I should see breakdown:
      | Phase              | Status      | Progress |
      |--------------------|-------------|----------|
      | Walking commits    | Complete    | 100%     |
      | Chunking blobs     | In Progress | 45%      |
      | Generating embeddings | Pending  | 0%       |
      | Storing vectors    | Pending     | 0%       |

  Scenario: Throughput metrics
    Given indexing in progress
    When I view live stats
    Then I should see:
      | Metric              | Value        |
      |---------------------|--------------|
      | Chunks/second       | 125.3        |
      | Tokens/second       | 48,500       |
      | Cost/minute         | $0.0038      |
      | Time elapsed        | 00:02:34     |
      | ETA                 | 00:03:15     |

  Scenario: Cache hit rate tracking
    Given EmbeddingCache is enabled
    And 40% of blobs are unchanged
    When indexing completes
    Then cache hit rate should be displayed: 40%
    And cache stats should show: 400 hits, 600 misses
    And actual cost should only include cache misses
    And estimated savings should be shown: $0.05 saved via cache

  Scenario: Graceful cancellation
    Given indexing is 60% complete
    And user presses Ctrl+C
    When cancellation is detected
    Then indexing should stop cleanly
    And partial progress should be saved
    And summary should show: 60% complete, $0.08 spent
    And user should be informed: "Resume with 'gitctx index --resume'"

  Scenario: Final summary report
    Given indexing completed successfully
    When I view the final output
    Then summary should include:
      | Metric              | Value        |
      |---------------------|--------------|
      | Total blobs         | 523          |
      | Total chunks        | 4,892        |
      | Total tokens        | 1,845,203    |
      | Total cost          | $0.2399      |
      | Cache hit rate      | 42%          |
      | Time elapsed        | 00:05:23     |
      | Avg chunks/sec      | 15.2         |

  Scenario: Error rate tracking
    Given 5 blobs fail to process (corrupt, binary, etc.)
    When indexing completes
    Then error rate should be displayed: 5/528 (0.9%)
    And errors should be logged with details
    And user should be advised: "Check .gitctx/logs/index.log"
```

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.2.5.1](TASK-0001.2.5.1.md) | Implement ProgressTracker with Rich integration | 🔵 | 3 |
| [TASK-0001.2.5.2](TASK-0001.2.5.2.md) | Add CostEstimator for pre-indexing estimates | 🔵 | 2 |
| [TASK-0001.2.5.3](TASK-0001.2.5.3.md) | Integrate progress tracking into indexing pipeline | 🔵 | 3 |
| [TASK-0001.2.5.4](TASK-0001.2.5.4.md) | BDD scenarios and integration tests | 🔵 | 4 |

**Total**: 12 hours = 3 story points

## Technical Design

### Progress Tracker with Rich

```python
# src/gitctx/indexing/progress.py

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.live import Live
from rich.table import Table
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

@dataclass
class IndexingStats:
    """Statistics for indexing progress."""
    total_blobs: int = 0
    processed_blobs: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    start_time: float = 0.0

    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time

    def chunks_per_second(self) -> float:
        """Calculate chunks processed per second."""
        elapsed = self.elapsed_seconds()
        return self.total_chunks / elapsed if elapsed > 0 else 0.0

    def tokens_per_second(self) -> float:
        """Calculate tokens processed per second."""
        elapsed = self.elapsed_seconds()
        return self.total_tokens / elapsed if elapsed > 0 else 0.0

    def cost_per_minute(self) -> float:
        """Calculate cost per minute."""
        elapsed = self.elapsed_seconds()
        minutes = elapsed / 60 if elapsed > 0 else 0.0
        return self.total_cost_usd / minutes if minutes > 0 else 0.0

    def eta_seconds(self, total_items: int, processed_items: int) -> float:
        """Estimate seconds remaining."""
        if processed_items == 0:
            return 0.0
        elapsed = self.elapsed_seconds()
        rate = processed_items / elapsed
        remaining = total_items - processed_items
        return remaining / rate if rate > 0 else 0.0

    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0


class ProgressTracker:
    """Track and display indexing progress with Rich.

    Provides real-time progress bars, statistics, and cost tracking
    during the indexing process.
    """

    def __init__(self, console: Console | None = None):
        """Initialize progress tracker.

        Args:
            console: Rich console (creates new if not provided)
        """
        self.console = console or Console()
        self.stats = IndexingStats()
        self.progress: Progress | None = None
        self.live: Live | None = None

    def start(self, total_blobs: int):
        """Start progress tracking.

        Args:
            total_blobs: Total number of blobs to process
        """
        self.stats.total_blobs = total_blobs
        self.stats.start_time = time.time()

        # Create progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=True
        )

        # Add tasks for each phase
        self.walking_task = self.progress.add_task(
            "[cyan]Walking commits...", total=total_blobs
        )
        self.chunking_task = self.progress.add_task(
            "[yellow]Chunking blobs...", total=total_blobs
        )
        self.embedding_task = self.progress.add_task(
            "[green]Generating embeddings...", total=None  # Unknown until chunking done
        )
        self.storing_task = self.progress.add_task(
            "[magenta]Storing vectors...", total=None
        )

        # Start live display
        self.live = Live(self._generate_display(), console=self.console, refresh_per_second=4)
        self.live.start()

    def update_walking(self, blobs_processed: int):
        """Update walking progress.

        Args:
            blobs_processed: Number of blobs walked so far
        """
        if self.progress:
            self.progress.update(self.walking_task, completed=blobs_processed)

    def update_chunking(self, blob_sha: str, num_chunks: int):
        """Update chunking progress.

        Args:
            blob_sha: SHA of blob that was chunked
            num_chunks: Number of chunks created
        """
        self.stats.processed_blobs += 1
        self.stats.total_chunks += num_chunks

        if self.progress:
            self.progress.update(self.chunking_task, completed=self.stats.processed_blobs)
            # Update embedding task total now that we know chunk count
            if self.progress.tasks[self.embedding_task].total is None:
                self.progress.update(self.embedding_task, total=self.stats.total_chunks)

    def update_embedding(self, batch_size: int, tokens: int, cost: float, cache_hit: bool):
        """Update embedding progress.

        Args:
            batch_size: Number of chunks embedded in this batch
            tokens: Tokens consumed
            cost: Cost of this batch
            cache_hit: Whether this was a cache hit
        """
        self.stats.total_tokens += tokens
        self.stats.total_cost_usd += cost

        if cache_hit:
            self.stats.cache_hits += 1
        else:
            self.stats.cache_misses += 1

        if self.progress:
            current = self.progress.tasks[self.embedding_task].completed or 0
            self.progress.update(self.embedding_task, completed=current + batch_size)
            # Update storing task total
            if self.progress.tasks[self.storing_task].total is None:
                self.progress.update(self.storing_task, total=self.stats.total_chunks)

    def update_storing(self, num_stored: int):
        """Update storage progress.

        Args:
            num_stored: Number of chunks stored in this batch
        """
        if self.progress:
            current = self.progress.tasks[self.storing_task].completed or 0
            self.progress.update(self.storing_task, completed=current + num_stored)

    def record_error(self, blob_sha: str, error: str):
        """Record an error during processing.

        Args:
            blob_sha: SHA of blob that failed
            error: Error message
        """
        self.stats.errors += 1
        # Log error to file
        # (TASK-0001.2.5.3 will implement logging)

    def stop(self):
        """Stop progress tracking and show final summary."""
        if self.live:
            self.live.stop()

        if self.progress:
            self.progress.stop()

        self._print_final_summary()

    def _generate_display(self) -> Table:
        """Generate live statistics display.

        Returns:
            Rich table with current statistics
        """
        table = Table(title="Indexing Statistics", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        # Progress
        if self.progress:
            for task_id in [self.walking_task, self.chunking_task, self.embedding_task, self.storing_task]:
                task = self.progress.tasks[task_id]
                table.add_row(task.description, f"{task.percentage:.1f}%")

        table.add_section()

        # Throughput
        table.add_row("Chunks/second", f"{self.stats.chunks_per_second():.1f}")
        table.add_row("Tokens/second", f"{self.stats.tokens_per_second():.0f}")

        table.add_section()

        # Costs
        table.add_row("Total tokens", f"{self.stats.total_tokens:,}")
        table.add_row("Total cost", f"${self.stats.total_cost_usd:.4f}")
        table.add_row("Cost/minute", f"${self.stats.cost_per_minute():.4f}")

        table.add_section()

        # Cache
        table.add_row("Cache hit rate", f"{self.stats.cache_hit_rate():.1f}%")
        table.add_row("Cache hits", f"{self.stats.cache_hits}")
        table.add_row("Cache misses", f"{self.stats.cache_misses}")

        if self.stats.errors > 0:
            table.add_section()
            table.add_row("Errors", f"{self.stats.errors}", style="red")

        return table

    def _print_final_summary(self):
        """Print final summary after indexing completes."""
        elapsed = self.stats.elapsed_seconds()

        table = Table(title="🎉 Indexing Complete", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total blobs", f"{self.stats.total_blobs:,}")
        table.add_row("Total chunks", f"{self.stats.total_chunks:,}")
        table.add_row("Total tokens", f"{self.stats.total_tokens:,}")
        table.add_row("Total cost", f"${self.stats.total_cost_usd:.4f}")
        table.add_row("Cache hit rate", f"{self.stats.cache_hit_rate():.1f}%")
        table.add_row("Time elapsed", str(timedelta(seconds=int(elapsed))))
        table.add_row("Avg chunks/sec", f"{self.stats.chunks_per_second():.1f}")

        if self.stats.errors > 0:
            table.add_row("Errors", f"{self.stats.errors}", style="red")
            table.add_row("Error log", ".gitctx/logs/index.log", style="dim")

        self.console.print(table)


class CostEstimator:
    """Estimate indexing costs before processing.

    Analyzes repository to provide cost estimates and confidence ranges.
    """

    # Average tokens per line of code (empirical estimate)
    TOKENS_PER_LINE = 5.0

    # Model pricing
    COST_PER_1K_TOKENS = 0.00013  # text-embedding-3-large

    def estimate_repo_cost(self, repo_path: Path) -> dict:
        """Estimate cost for indexing a repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Dictionary with estimates
        """
        # Analyze repo (simplified - real impl would walk commit graph)
        total_lines = self._count_lines(repo_path)
        total_files = self._count_files(repo_path)

        # Estimate tokens
        estimated_tokens = int(total_lines * self.TOKENS_PER_LINE)

        # Estimate cost
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
            "confidence": "±20%"
        }

    def _count_lines(self, repo_path: Path) -> int:
        """Count lines of code in repository."""
        # Simplified implementation
        # Real version would use walker + chunker
        return 10000  # Placeholder

    def _count_files(self, repo_path: Path) -> int:
        """Count files in repository."""
        # Simplified implementation
        return 100  # Placeholder
```

### Integration with Pipeline

```python
# src/gitctx/indexing/pipeline.py

from gitctx.indexing.progress import ProgressTracker, CostEstimator

async def index_repository(repo_path: Path, settings: GitCtxSettings, dry_run: bool = False):
    """Index a repository with progress tracking.

    Args:
        repo_path: Path to git repository
        settings: Configuration settings
        dry_run: If True, only show cost estimate without indexing
    """
    console = Console()

    # Cost estimation
    if dry_run:
        estimator = CostEstimator()
        estimate = estimator.estimate_repo_cost(repo_path)

        table = Table(title="Cost Estimate")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Files", f"{estimate['total_files']:,}")
        table.add_row("Lines", f"{estimate['total_lines']:,}")
        table.add_row("Est. tokens", f"{estimate['estimated_tokens']:,}")
        table.add_row("Est. cost", f"${estimate['estimated_cost']:.4f}")
        table.add_row("Range", f"${estimate['min_cost']:.4f} - ${estimate['max_cost']:.4f}")
        table.add_row("Confidence", estimate['confidence'])

        console.print(table)
        return

    # Initialize components
    tracker = ProgressTracker(console)
    walker = CommitWalker(repo_path, settings)
    chunker = create_chunker()
    embedder = create_embedder(settings.api_keys.openai)
    store = LanceDBStore(repo_path / ".gitctx/lancedb")

    # Start tracking
    # (total_blobs discovered during walking, so we'll estimate)
    tracker.start(total_blobs=1000)  # Placeholder

    try:
        # Walk commits
        for blob_record in walker.walk():
            tracker.update_walking(walker.get_stats().blobs_indexed)

            # Chunk
            chunks = chunker.chunk_file(
                content=blob_record.content.decode("utf-8"),
                language="python",  # Detect language
                max_tokens=800
            )
            tracker.update_chunking(blob_record.sha, len(chunks))

            # Embed
            embedding_batch = await embedder.embed_chunks(chunks, blob_record.sha)
            cache_hit = embedding_batch.total_cost_usd == 0.0
            tracker.update_embedding(
                batch_size=len(embedding_batch.embeddings),
                tokens=embedding_batch.total_tokens,
                cost=embedding_batch.total_cost_usd,
                cache_hit=cache_hit
            )

            # Store
            store.add_chunks_batch(embedding_batch.embeddings, {blob_record.sha: blob_record.locations})
            tracker.update_storing(len(embedding_batch.embeddings))

    except KeyboardInterrupt:
        console.print("\n[yellow]Indexing cancelled by user[/yellow]")
        tracker.stop()
        console.print("[dim]Resume with: gitctx index --resume[/dim]")
        return

    except Exception as e:
        tracker.record_error("unknown", str(e))
        raise

    finally:
        tracker.stop()
```

## Dependencies

### External Libraries

- `rich>=13.0.0` - Terminal formatting, progress bars, live displays

### Internal Dependencies

- **STORY-0001.2.1** (Commit Graph Walker) - Provides blob counts and statistics ✅
- **STORY-0001.2.2** (Blob Chunking) - Provides chunk counts
- **STORY-0001.2.3** (OpenAI Embeddings) - Provides token/cost data
- **STORY-0001.2.4** (LanceDB Storage) - Storage progress tracking

## Pattern Reuse

From existing codebase:
- Rich console usage patterns from CLI commands
- Progress bar patterns from prototype

## Success Criteria

Story is complete when:

- ✅ All 4 tasks implemented and tested
- ✅ All 10 BDD scenarios pass
- ✅ Real-time progress updates smoothly (<4Hz refresh)
- ✅ Cost calculations accurate to ±1%
- ✅ Graceful cancellation works (Ctrl+C)
- ✅ Quality gates: ruff + mypy + pytest all pass

## Performance Targets

- Progress update overhead: <5ms per update
- Display refresh rate: 4Hz (250ms intervals)
- Memory overhead: <10MB for progress tracking

## Notes

- Use Rich's Live display for smooth updates
- Track statistics at pipeline level (not in individual components)
- Cost estimates are approximate (±20% confidence)
- Cache hit rate is key metric for re-indexing performance

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
