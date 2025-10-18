# STORY-0001.4.5: TUI Performance & Usability

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 5
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer using gitctx
I want clear real-time progress for all long-running operations
So that I understand what gitctx is doing, how long it will take, and when work is complete (instead of staring at long pauses wondering if it's frozen)

## Acceptance Criteria

### Progress Indicator Requirements

- [ ] Walking phase shows: `Walking commit graph: 1,234/5,000 commits (24%)  ETA 00:03:45  250 commits/sec`
  - [ ] Total commits known upfront from git tree walk
  - [ ] Current count updates in real-time
  - [ ] Throughput calculated from elapsed time
  - [ ] ETA calculated from remaining work / throughput (rolling average over last 100 items)
  - [ ] ETA shows "calculating..." until sufficient samples collected (>10 items)
  - [ ] Manual verification: Final ETA within ±20% of actual completion time (test on 1K+ file repo)

- [ ] Embedding phase shows:
  ```
  → Generating embeddings using OpenAI text-embedding-3-large ($0.13/M tokens)
    Total Costs: $0.00045 (942 blobs) | Saved using repo cache: $0.00032 (292 blobs)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1234/1234 blobs (100%)  ETA 00:00:00  45 blobs/sec
  ```
  - [ ] Model name and pricing from registry (cents_per_million_tokens)
  - [ ] Running cost total updates as fresh blobs are embedded
  - [ ] Cache savings calculated from cached embedding metadata
  - [ ] Progress bar shows blob count (not chunk count)
  - [ ] Throughput averaged over last min(100, processed_count) blobs (handles repos with <100 blobs gracefully)

- [ ] Saving phase shows: `Saving index: 2,000/2,000 chunks (100%)  ETA 00:00:00  200 chunks/sec`
  - [ ] Total chunks known after embedding completes
  - [ ] Current count updates per LanceDB batch
  - [ ] Throughput measured from batch timings
  - [ ] ETA based on remaining chunks

- [ ] Progress bar updates every 100ms (10 Hz refresh rate) without terminal flicker or cursor jumping
- [ ] All progress lines overwrite previous line (no spam/scrolling)
- [ ] Consistent format across all phases:
  - [ ] All phases use same Rich.Progress column layout (TextColumn, BarColumn, count, ETA, throughput)
  - [ ] Progress bars have consistent width (default: fills terminal width proportionally)
  - [ ] Phase markers use `SYMBOLS['arrow']` (→) for in-progress and `SYMBOLS['success']` (✓) for completion
  - [ ] Count format consistent: "N/M items (XX%)"
  - [ ] ETA format consistent: "ETA HH:MM:SS" or "ETA --:--:--" when calculating
  - [ ] Throughput format consistent: "N items/sec"
- [ ] Progress updates every 100ms (10 Hz) - no gaps >500ms between updates
  - [ ] Manual verification: Run indexing on 10K file repo, measure update intervals with timestamped logs
  - [ ] Pass criteria: 95% of intervals <150ms, 100% of intervals <500ms

### Output Mode Refactoring

- [ ] Current "terse" mode renamed to "quiet" mode
- [ ] Current "verbose" mode becomes the DEFAULT
- [ ] Config setting: `output.mode = "default" | "quiet"` (if config exists)
- [ ] Default mode shows all progress with full metrics
- [ ] Quiet mode shows only: `"Indexed 150 commits (1,234 unique blobs, 292 cached) in 12.5s"`
- [ ] Remove all references to "terse" and "verbose" terminology
- [ ] CLI flags: remove `--verbose`, add `--quiet` (default=False)

### Statistics Display

- [ ] Single newline between "✓ Indexing Complete" and "Statistics:"
- [ ] Statistics show: `Unique blobs: 1,234 (292 cached)`
- [ ] Cost shows only fresh API costs (cached blobs = $0)
- [ ] Quiet mode shows: `Indexed 150 commits (1,234 unique blobs, 292 cached) in 12.5s`

### Progress Error Handling

- [ ] Terminal detection using Rich Console:
  - [ ] Use `Console(stderr=True).is_terminal` to detect TTY (Rich handles platform differences)
  - [ ] Non-TTY stderr (redirected to file) → Disable progress bars, show phase completions only
  - [ ] Dumb terminal (`Console.is_dumb_terminal`) → Fallback to simple text updates (no ANSI codes)
  - [ ] Rich automatically handles legacy Windows cmd.exe via `Console.legacy_windows`

- [ ] Progress update exceptions:
  - [ ] Rich.Progress exception → Log warning, continue without progress display (wrap in try/except)
  - [ ] Terminal resize handled automatically by Rich (no special code needed)
  - [ ] No crash on progress failures - indexing continues

- [ ] BDD scenario:
  ```gherkin
  Given I have a repository with 100 files
  When I run "gitctx index 2>/tmp/output.txt" (stderr redirected)
  Then indexing should complete successfully
  And output file should contain phase markers without ANSI codes
  And no progress bars should be written
  ```

## BDD Scenarios

### Scenario: Default mode shows multi-phase progress

```gherkin
Given I have a repository with 100 files
When I run "gitctx index"
Then I should see "→ Walking commit graph" with progress bar
And I should see "→ Generating embeddings" with cost breakdown and progress bar
And I should see "→ Saving index" with progress bar
And I should see "✓ Indexing Complete" followed by statistics table
```

### Scenario: Quiet mode shows minimal output

```gherkin
Given I have a repository with 100 files
When I run "gitctx index --quiet"
Then I should see only final summary: "Indexed N commits (M blobs, X cached) in Ys"
And I should NOT see progress bars or phase markers
```

### Scenario: Cache savings displayed during embedding

```gherkin
Given I have previously indexed a repository
When I run "gitctx index" again with 50% cached blobs
Then embedding phase should show "Total Costs: $X (N blobs) | Saved using repo cache: $Y (M blobs)"
And saved cost should equal sum of cached embedding costs
```

### Scenario: ETA updates based on throughput

```gherkin
Given I am indexing a large repository
When embedding phase starts
Then ETA should update every second based on current throughput
And throughput should be calculated from last 100 blobs processed
```

### Scenario: Throughput calculation handles small repositories

```gherkin
Given I have a repository with 50 files
When I run "gitctx index"
Then embedding phase should calculate throughput over min(100, 50) blobs
And throughput should show "blobs/sec" metric
And progress bar should complete without division-by-zero errors
```

### Scenario: Progress bar updates smoothly without flicker

```gherkin
Given I have a repository with 50 files
When I run "gitctx index"
Then I should see progress bars for walking, embedding, and saving phases
And each progress bar should overwrite the previous line (no scrolling)
And the final statistics should display after completion
```

## Technical Design

### Components to Modify

**1. `src/gitctx/models/registry.py`** (Add pricing to ModelSpec)

```python
class ModelSpec(TypedDict):
    dimensions: int
    max_tokens: int
    provider: str
    cents_per_million_tokens: int  # NEW: Pricing in cents

MODELS: dict[str, ModelSpec] = {
    "text-embedding-3-large": {
        "dimensions": 3072,
        "max_tokens": 8191,
        "provider": "openai",
        "cents_per_million_tokens": 13,  # $0.13/1M tokens (verified: 2025-01)
    },
    "text-embedding-3-small": {
        "dimensions": 1536,
        "max_tokens": 8191,
        "provider": "openai",
        "cents_per_million_tokens": 2,  # $0.02/1M tokens (verified: 2025-01)
    },
}

# Pricing Maintenance: Values verified quarterly against https://openai.com/api/pricing/
# Each entry includes "verified: YYYY-MM" date. Future EPIC will add automated staleness detection.
```

**2. `src/gitctx/indexing/progress.py`** (Enhance existing ProgressReporter)

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

class IndexingStats:
    """Statistics for indexing progress."""
    total_commits: int = 0
    total_blobs: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cached_blobs: int = 0  # NEW
    cached_cost_usd: float = 0.0  # NEW (savings)
    errors: int = 0
    start_time: float = 0.0

class ProgressReporter:
    """Report indexing progress with Rich.Progress bars."""

    def __init__(self, quiet: bool = False, model_name: str = "text-embedding-3-large"):
        """Initialize progress reporter.

        Args:
            quiet: If True, show minimal output (old "terse" mode)
            model_name: Embedding model for pricing display
        """
        self.quiet = quiet
        self.model_name = model_name
        self.model_spec = get_model_spec(model_name)
        self.stats = IndexingStats()
        self.current_phase: str = ""
        self.progress_ctx: Progress | None = None

    def phase(self, name: str, total: int | None = None) -> None:
        """Start a new phase with Rich.Progress bar.

        Args:
            name: Phase name (e.g., "Walking commit graph")
            total: Total items for progress bar (None = indeterminate)
        """
        self.current_phase = name

        if self.quiet:
            return  # No output in quiet mode

        # Phase marker
        if name == "Generating embeddings":
            # Special formatting for embedding phase with pricing
            price = self.model_spec["cents_per_million_tokens"] / 100
            print(
                f"{SYMBOLS['arrow']} {name} using OpenAI {self.model_name} "
                f"(${price:.2f}/M tokens)",
                file=sys.stderr
            )
        else:
            print(f"{SYMBOLS['arrow']} {name}", file=sys.stderr)

        # Create Rich.Progress context
        if total is not None:
            self.progress_ctx = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total} ({task.percentage:.0f}%)"),
                TextColumn("ETA {task.fields[eta]}"),
                TextColumn("{task.fields[throughput]}"),
                console=Console(stderr=True)
            )
            self.task_id = self.progress_ctx.add_task(
                name,
                total=total,
                eta="calculating...",
                throughput=""
            )
            self.progress_ctx.start()

    def update(
        self,
        commits: int = 0,
        blobs: int = 0,
        chunks: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
        cached_blobs: int = 0,
        cached_cost: float = 0.0,
    ) -> None:
        """Update statistics and progress bar."""
        # Update stats
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
        if cached_blobs:
            self.stats.cached_blobs = cached_blobs
        if cached_cost:
            self.stats.cached_cost_usd = cached_cost

        # Update progress bar (if active)
        if self.progress_ctx and not self.quiet:
            # Calculate ETA and throughput from rolling average
            elapsed = time.time() - self.stats.start_time
            completed = self.stats.total_blobs  # Current phase metric
            throughput = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / throughput if throughput > 0 else 0

            self.progress_ctx.update(
                self.task_id,
                completed=completed,
                eta=f"{timedelta(seconds=int(eta))}",
                throughput=f"{throughput:.0f} items/sec"
            )

        # Show cost breakdown for embedding phase
        if self.current_phase == "Generating embeddings" and not self.quiet:
            fresh_blobs = self.stats.total_blobs - self.stats.cached_blobs
            print(
                f"  Total Costs: ${self.stats.total_cost_usd:.5f} ({fresh_blobs} blobs) | "
                f"Saved using repo cache: ${self.stats.cached_cost_usd:.5f} "
                f"({self.stats.cached_blobs} blobs)",
                file=sys.stderr
            )

    def finish(self) -> None:
        """Print final summary."""
        if self.progress_ctx:
            self.progress_ctx.stop()

        elapsed = self.stats.elapsed_seconds()

        if self.quiet:
            self._print_quiet_summary(elapsed)
        else:
            self._print_default_summary(elapsed)

    def _print_default_summary(self, elapsed: float) -> None:
        """Print detailed statistics (default mode)."""
        print(f"{SYMBOLS['success']} Indexing Complete\n", file=sys.stderr)

        print("Statistics:", file=sys.stderr)
        print(f"  Commits:      {format_number(self.stats.total_commits)}", file=sys.stderr)
        print(
            f"  Unique blobs: {format_number(self.stats.total_blobs)} "
            f"({self.stats.cached_blobs} cached)",
            file=sys.stderr
        )
        print(f"  Chunks:       {format_number(self.stats.total_chunks)}", file=sys.stderr)
        print(f"  Tokens:       {format_number(self.stats.total_tokens)}", file=sys.stderr)
        print(f"  Cost:         {format_cost(self.stats.total_cost_usd)}", file=sys.stderr)
        print(f"  Time:         {timedelta(seconds=int(elapsed))!s}", file=sys.stderr)

    def _print_quiet_summary(self, elapsed: float) -> None:
        """Print minimal summary (quiet mode)."""
        print(
            f"Indexed {format_number(self.stats.total_commits)} commits "
            f"({format_number(self.stats.total_blobs)} unique blobs, "
            f"{self.stats.cached_blobs} cached) in {format_duration(elapsed)}"
        )
        print(
            f"Tokens: {format_number(self.stats.total_tokens)} | "
            f"Cost: {format_cost(self.stats.total_cost_usd)}"
        )
```

**3. `src/gitctx/cli/index.py`** (Update CLI flags)

```python
def index_command(
    # REMOVE: verbose: bool = typer.Option(False, "--verbose", "-v", ...)
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    # ... other params ...
) -> None:
    """Index repository with default progress display."""

    settings = GitCtxSettings()

    # Create progress reporter (default mode shows full progress)
    reporter = ProgressReporter(
        quiet=quiet,
        model_name=settings.repo.model.embedding
    )

    # ... rest of implementation ...
```

**4. `src/gitctx/indexing/embeddings.py`** (Track cache hits with cost)

```python
async def embed_with_cache(
    chunker: ChunkerProtocol,
    embedder: EmbedderProtocol,
    cache: EmbeddingCache,
    blob_record: BlobRecord,
) -> tuple[list[Embedding], bool, float]:
    """Generate embeddings with cache tracking.

    Returns:
        Tuple of (embeddings, was_cached, cached_cost)
    """
    # Check cache first
    cached = cache.get(blob_record.sha)
    if cached is not None:
        # Calculate what we would have paid (savings)
        cached_cost = sum(emb.cost_usd for emb in cached)
        logger.info(f"Cache hit for blob {blob_record.sha[:8]} (saved ${cached_cost:.6f})")
        return (cached, True, cached_cost)

    # Cache miss - generate embeddings
    embeddings = # ... existing logic ...
    cache.set(blob_record.sha, embeddings)

    return (embeddings, False, 0.0)
```

**5. `src/gitctx/indexing/pipeline.py`** (Pass cache metrics to ProgressReporter)

Update to track cached blobs and costs:

```python
async def index_repository(...):
    # ... initialization ...

    fresh_cost = 0.0
    cached_cost = 0.0
    cached_count = 0

    for blob_record in blobs:
        embeddings, was_cached, saved_cost = await embed_with_cache(...)

        if was_cached:
            cached_count += 1
            cached_cost += saved_cost
        else:
            fresh_cost += sum(emb.cost_usd for emb in embeddings)

        reporter.update(
            blobs=total_blobs,
            cached_blobs=cached_count,
            cost=fresh_cost,
            cached_cost=cached_cost
        )
```

**6. `src/gitctx/models/providers/openai.py`** (Use registry pricing)

```python
class OpenAIEmbedder:
    def __init__(self, ...):
        # ... existing init ...
        spec = get_model_spec(self.MODEL)
        self.cents_per_million_tokens = spec["cents_per_million_tokens"]

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost using registry pricing."""
        return (token_count / 1_000_000) * (self.cents_per_million_tokens / 100)
```

### Example Output (Default Mode):

```
→ Walking commit graph
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1234/5000 commits (24%)  ETA 00:03:45  250 commits/sec
→ Generating embeddings using OpenAI text-embedding-3-large ($0.13/M tokens)
  Total Costs: $0.00045 (942 blobs) | Saved using repo cache: $0.00032 (292 blobs)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1234/1234 blobs (100%)  ETA 00:00:00  45 blobs/sec
→ Saving index
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2000/2000 chunks (100%)  ETA 00:00:00  200 chunks/sec
✓ Indexing Complete

Statistics:
  Commits:      150
  Unique blobs: 1,234 (292 cached)
  Chunks:       2,000
  Tokens:       450K
  Cost:         $0.00045
  Time:         12.5s
```

### Example Output (--quiet Mode):

```
Indexed 150 commits (1,234 unique blobs, 292 cached) in 12.5s
Tokens: 450K | Cost: $0.00045
```

## Pattern Reuse

### Existing Patterns:

1. **ProgressReporter Class** (src/gitctx/indexing/progress.py)
   - Already has phase-based tracking with `phase()` method
   - Already has `update()` method for statistics
   - Already has dual output modes (verbose/terse) → rename to default/quiet
   - Extend, don't replace

2. **Rich Library** (from src/gitctx/cli/search.py)
   - `Progress` context manager with custom columns
   - Console error output: `console_err = Console(stderr=True, ...)`
   - Already used for query embedding progress

3. **Symbol Usage** (src/gitctx/cli/symbols.py)
   - `SYMBOLS['arrow']` for phase markers (→)
   - `SYMBOLS['success']` for completion (✓)
   - Platform-aware symbol rendering

4. **Formatting Utilities** (src/gitctx/indexing/formatting.py)
   - `format_cost()` for currency display
   - `format_duration()` for time display
   - `format_number()` for comma-separated numbers

5. **Model Registry** (src/gitctx/models/registry.py)
   - `get_model_spec(model_name)` for model metadata
   - Add `cents_per_million_tokens` field

### New Patterns Established:

1. **Multi-Phase Progress with Rich.Progress**
   - Pattern: Each phase gets its own Rich.Progress task
   - Tasks show: count, percentage, ETA, throughput
   - Reusable for future multi-phase operations

2. **Cache Statistics Tracking**
   - Pattern: Return `(result, was_cached: bool, cached_cost: float)`
   - Enables real-time cache hit/savings display
   - Reusable for future caching (query cache, etc.)

3. **ETA Calculation with Rolling Average**
   - Pattern: Track last N items (100) for throughput calculation
   - Avoids early spikes/jitters in ETA
   - Reusable for any progress tracking

4. **Pricing Display from Registry**
   - Pattern: Fetch pricing from ModelSpec, format in progress output
   - Centralized pricing updates
   - Reusable for cost estimates, billing, etc.

### E2E Test Patterns to Reuse:

**Fixture**: `e2e_git_repo_factory` (from `tests/conftest.py`)
- **Purpose**: Isolated git repository with configurable commits for E2E testing
- **Reuse for**: Story 0001.4.5 BDD scenarios (test progress tracking on 100-file, 500-file repos)
- **Example**: `def test_progress(e2e_git_repo_factory): repo = e2e_git_repo_factory(commits=500)`

### Patterns to Refactor:

1. **Consolidate Cost Constants**
   - Current: `COST_PER_MILLION_TOKENS` duplicated in `openai.py` and `progress.py`
   - New: Single source in `registry.py` as `cents_per_million_tokens`

2. **Verbose/Terse → Default/Quiet**
   - Current: `verbose: bool = False` parameter
   - New: `quiet: bool = False` parameter (inverted semantics)
   - Reason: Full progress becomes the default, quiet is opt-in

## Dependencies

### Prerequisites:

**None** - Story 5 is independent
- Modifies progress display components only
- Doesn't depend on search quality improvements (Stories 1-3)
- Doesn't depend on compression changes (Story 4)
- Progress tracking is orthogonal to search/indexing logic

### Blocks:

**None** - Story 5 is a leaf node

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rich.Progress adds >50ms overhead per update (exceeds 100ms budget) | Medium | Medium | Throttle updates to 100ms intervals (10 Hz max), batch stat updates; benchmark on 10K+ file repos, acceptable if total <10ms per update |
| ETA varies by >50% in first 10 items (insufficient samples) | Low | Low | Show "Calculating ETA..." until 10+ items processed, then display rolling average over last 100 items (stable within 20%) |
| Breaking existing progress tests | Medium | High | Update BDD scenarios in progress_tracking.feature |
| Cache cost calculation incorrect (missing cost_usd in old caches) | Low | Medium | Fallback: `estimated_cost = (tokens / 1_000_000) * (cents_per_million_tokens / 100)` (same formula as OpenAIEmbedder.estimate_cost) |
| Model pricing changes breaking display | Low | Low | Comment in registry points to openai.com/api/pricing/ |
| CLI flag change breaks workflows | Low | Medium | Document in CHANGELOG, no deprecation needed (pre-1.0) |

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.4.5.1](TASK-0001.4.5.1.md) | Write BDD Scenarios for TUI Progress | 🔵 Not Started | 3 | 0/7 (all failing) |
| [TASK-0001.4.5.2](TASK-0001.4.5.2.md) | Add cents_per_million_tokens to ModelSpec Registry | 🔵 Not Started | 2 | 1/7 passing |
| [TASK-0001.4.5.3](TASK-0001.4.5.3.md) | Refactor ProgressReporter with Rich.Progress | 🔵 Not Started | 10 | 5/7 passing |
| [TASK-0001.4.5.4](TASK-0001.4.5.4.md) | Update CLI Flags and Pipeline Integration | 🔵 Not Started | 4 | 7/7 passing ✅ |

**Total Hours:** 19 (story: 5 points × 4h/point = 20h ✓)

**BDD Progress Tracking:**

- TASK-1: 0/7 scenarios (all stubbed, all failing - defines behavior)
- TASK-2: 1/7 scenarios (foundation + basic scenarios)
- TASK-3: 5/7 scenarios (core functionality working)
- TASK-4: 7/7 scenarios (complete ✅)

**Incremental BDD Pattern:** ✅ Validated
- Task 1 writes ALL scenarios first (0/7 stubbed)
- Each subsequent task increases passing scenarios
- Final task reaches 7/7 scenarios passing

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
