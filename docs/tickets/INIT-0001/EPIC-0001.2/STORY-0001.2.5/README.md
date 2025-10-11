# STORY-0001.2.5: Progress Tracking and Cost Estimation

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 2
**Progress**: █████░░░░░ 50% (2/4 tasks complete)

## User Story

As a developer using gitctx
I want to see progress and cost information during indexing
So that I can monitor operations and understand the financial impact of indexing my codebase

**Note**: This story follows TUI_GUIDE.md design principles - terse by default with --verbose for details.

## Acceptance Criteria

**Default Mode (Terse - TUI_GUIDE compliant)**:
- [ ] Default output: single-line summary "Indexed N blobs in Xs" (git-like)
- [ ] Show spinner only for operations >5 seconds: "⠋ Indexing... 8.3s"
- [ ] Final summary: total chunks, total tokens, total cost (4 decimal places), time elapsed

**Verbose Mode (--verbose flag)**:
- [ ] Phase-by-phase progress indicators (→ Walking, → Chunking, → Embedding, → Storing)
- [ ] Statistics after completion: commits, blobs, chunks, tokens, cost, dedup rate
- [ ] Format follows TUI_GUIDE.md INDEX command verbose output

**Cost Tracking**:
- [ ] Track token usage across all embedding API calls
- [ ] Calculate costs in USD formatted to 4 decimal places (accuracy ±0.001%)
- [ ] Display in final summary: total tokens, total cost

**Error Handling**:
- [ ] Handle cancellation on SIGINT (Ctrl+C):
  - Graceful shutdown within 5 seconds
  - Show partial stats: chunks processed, tokens used, cost incurred
  - Exit with code 130
- [ ] Display error count in final summary: "Errors: N"
- [ ] Log errors to stderr during indexing
- [ ] Handle empty repository (no indexable files): display "No files to index", exit code 0
  - Indexable files: any file with supported extension (60+ extensions) or defaulted to markdown

**Cost Estimation (--dry-run flag)**:
- [ ] Analyze repository and show estimated tokens and cost
- [ ] Display confidence range: "Range: $MIN - $MAX (±20%)"
- [ ] Always use 4 decimal places for all costs (e.g., "$0.0001", "$1.2345")

## BDD Scenarios

**Note**: Revised to 5 E2E scenarios per TUI_GUIDE.md patterns. Tests both default (terse) and verbose modes. Calculation logic covered by unit tests in TASK-2 and TASK-3.

```gherkin
Feature: Progress Tracking and Cost Estimation

  Scenario: Default terse output (TUI_GUIDE.md:208-209)
    Given a repository with 10 files to index
    When I run "gitctx index" with mocked embedder
    Then I should see single-line output matching "Indexed \d+ commits \(\d+ unique blobs\) in \d+\.\d+s"
    And cost summary should show format "$\d+\.\d{4}"

  Scenario: Verbose mode with phase progress (TUI_GUIDE.md:230-256)
    Given a repository with 10 files to index
    When I run "gitctx index --verbose" with mocked embedder
    Then I should see phase markers: "→ Walking commit graph", "→ Generating embeddings"
    And final summary should show statistics:
      | Field        | Format          |
      | Commits      | \d+             |
      | Unique blobs | \d+             |
      | Chunks       | \d+             |
      | Tokens       | \d+,\d+         |
      | Cost         | $\d+\.\d{4}     |
      | Time         | \d+:\d+:\d+     |

  Scenario: Pre-indexing cost estimate with --dry-run
    Given a repository with 5 files totaling 2KB
    When I run "gitctx index --dry-run"
    Then I should see estimated tokens
    And estimated cost formatted as "$\d+\.\d{4}"
    And confidence range: "Range: $\d+\.\d{4} - $\d+\.\d{4} \(±20%\)"

  Scenario: Graceful cancellation (TUI_GUIDE.md:377-387)
    Given indexing is in progress with 20 files
    When I send SIGINT to the process
    Then I should see "Interrupted" message
    And partial stats with tokens and cost
    And exit code should be 130

  Scenario: Empty repository handling
    Given an empty repository with no indexable files
    When I run "gitctx index"
    Then I should see "No files to index"
    And exit code should be 0
    # Note: "No indexable files" = zero files matching 60+ supported extensions
```

**Unit Test Coverage** (not E2E):
- Cost calculation accuracy (various token counts, formula validation)
- Confidence range calculation (±20%)
- Format validation (always 4 decimal places)
- Empty repository handling (no indexable files)
- Large repository handling (2M+ tokens)
- Zero division edge cases

**Rationale for 5 E2E Scenarios:**
- TUI_GUIDE compliant: Tests both default (terse) and verbose modes
- Cost-effective: No real API calls (mocked embedders)
- Fast CI: Small repos (5-20 files, <50KB total)
- Comprehensive: Covers CLI behavior end-to-end
- Unit tests handle calculation logic with large numbers

## Child Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.2.5.1](TASK-0001.2.5.1.md) | Write BDD Scenarios for Progress + Cost | ✅ Complete | 2 | 0/5 (all stubbed) |
| [TASK-0001.2.5.2](TASK-0001.2.5.2.md) | ProgressReporter with Terse/Verbose Modes | ✅ Complete | 3 | 2/5 ready (awaits integration) |
| [TASK-0001.2.5.3](TASK-0001.2.5.3.md) | CostEstimator + BDD for Scenario 3 | 🔵 Not Started | 2 | 3/5 passing |
| [TASK-0001.2.5.4](TASK-0001.2.5.4.md) | Pipeline Integration + Final BDD | 🔵 Not Started | 1 | 5/5 passing ✅ |

**Total**: 8 hours = 2 story points

**BDD Progress Tracking:**

- **TASK-1** (2h): Write all 5 E2E scenarios + stub step definitions → 0/5 stubbed (all failing)
- **TASK-2** (3h): ProgressReporter (terse/verbose) + unit tests + Scenarios 1-2 → 2/5 passing
- **TASK-3** (2h): CostEstimator + unit tests + Scenario 3 → 3/5 passing
- **TASK-4** (1h): Pipeline integration + Scenarios 4-5 → 5/5 passing ✅

**Testing Strategy:**

- **E2E Tests**: 5 scenarios per TUI_GUIDE patterns (default/verbose split)
- **Unit Tests**: ~10 tests for cost calculation logic (simpler scope)
- **Cost-Effective**: All E2E tests use small repos (5-20 files, <50KB) with mocked embedders
- **Pattern**: BDD-first workflow with incremental scenario completion

## Technical Design

### TUI_GUIDE-Compliant Progress Reporter

Following TUI_GUIDE.md: terse by default, detailed with --verbose, spinner only for >5s operations.

```python
# src/gitctx/indexing/progress.py

from pathlib import Path
from dataclasses import dataclass
from datetime import timedelta
import time
import sys

@dataclass
class IndexingStats:
    """Statistics for indexing progress (simplified)."""
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

    def start(self):
        """Start progress tracking."""
        self.stats.start_time = time.time()
        # In verbose mode, announce start
        if self.verbose:
            print("→ Starting indexing...\n", file=sys.stderr)
        # In terse mode, show spinner after 5 seconds (handled in update loop)

    def phase(self, name: str):
        """Start a new phase (verbose mode only).

        Args:
            name: Phase name (e.g., "Walking commit graph")
        """
        self.current_phase = name
        if self.verbose:
            print(f"→ {name}", file=sys.stderr)

    def update(self, commits: int = 0, blobs: int = 0, chunks: int = 0,
               tokens: int = 0, cost: float = 0.0):
        """Update statistics (silent in default mode).

        Args:
            commits: Number of commits processed
            blobs: Number of blobs processed
            chunks: Number of chunks created
            tokens: Tokens consumed
            cost: Cost in USD
        """
        if commits: self.stats.total_commits = commits
        if blobs: self.stats.total_blobs = blobs
        if chunks: self.stats.total_chunks += chunks
        if tokens: self.stats.total_tokens += tokens
        if cost: self.stats.total_cost_usd += cost

        # In verbose mode, show progress for phase milestones
        if self.verbose and blobs > 0 and blobs % 100 == 0:
            print(f"  Processed {blobs} blobs...", file=sys.stderr)

    def record_error(self):
        """Record an error (silent tracking)."""
        self.stats.errors += 1

    def finish(self):
        """Print final summary (both modes).

        Default mode: Single terse line per TUI_GUIDE.md:208-209
        Verbose mode: Detailed table per TUI_GUIDE.md:246-256
        """
        elapsed = self.stats.elapsed_seconds()

        if self.verbose:
            self._print_verbose_summary(elapsed)
        else:
            self._print_terse_summary(elapsed)

    def _print_terse_summary(self, elapsed: float):
        """Print terse single-line summary (default mode)."""
        # Format: "Indexed 5678 commits (1234 unique blobs) in 8.2s"
        print(f"Indexed {self.stats.total_commits:,} commits "
              f"({self.stats.total_blobs:,} unique blobs) in {elapsed:.1f}s")

        # Always show cost summary on next line
        print(f"Tokens: {self.stats.total_tokens:,} | "
              f"Cost: ${self.stats.total_cost_usd:.4f}")

        if self.stats.errors > 0:
            print(f"Errors: {self.stats.errors}", file=sys.stderr)

    def _print_verbose_summary(self, elapsed: float):
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


from typing import TypedDict

class CostEstimate(TypedDict):
    """Cost estimation result."""
    total_files: int
    total_lines: int
    estimated_tokens: int
    estimated_cost: float
    min_cost: float
    max_cost: float

class CostEstimator:
    """Estimate indexing costs before processing."""

    # Conservative estimate: 5.0 tokens/line
    # (See STORY README for full rationale from 16x Prompt study)
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
```

### Integration with Pipeline

```python
# src/gitctx/indexing/pipeline.py

from gitctx.indexing.progress import ProgressReporter, CostEstimator

async def index_repository(repo_path: Path, settings: GitCtxSettings,
                           dry_run: bool = False, verbose: bool = False):
    """Index a repository with progress tracking (TUI_GUIDE compliant).

    Args:
        repo_path: Path to git repository
        settings: Configuration settings
        dry_run: If True, only show cost estimate without indexing
        verbose: If True, show detailed phase-by-phase progress
    """
    # Cost estimation mode
    if dry_run:
        estimator = CostEstimator()
        estimate = estimator.estimate_repo_cost(repo_path)

        print(f"Files:        {estimate['total_files']:,}")
        print(f"Lines:        {estimate['total_lines']:,}")
        print(f"Est. tokens:  {estimate['estimated_tokens']:,}")
        print(f"Est. cost:    ${estimate['estimated_cost']:.4f}")
        print(f"Range:        ${estimate['min_cost']:.4f} - ${estimate['max_cost']:.4f} (±20%)")
        return

    # Initialize components
    reporter = ProgressReporter(verbose=verbose)
    walker = CommitWalker(repo_path, settings)
    chunker = create_chunker()
    embedder = create_embedder(settings.api_keys.openai)
    store = LanceDBStore(repo_path / ".gitctx/lancedb")

    reporter.start()

    try:
        # Phase 1: Walk commits
        reporter.phase("Walking commit graph")
        for blob_record in walker.walk():
            reporter.update(commits=walker.get_stats().commits_walked,
                          blobs=walker.get_stats().blobs_indexed)

        # Phase 2: Chunk and embed
        reporter.phase("Generating embeddings")
        for blob_record in walker.walk():
            chunks = chunker.chunk_file(blob_record.content.decode("utf-8"))
            reporter.update(chunks=len(chunks))

            # Embed chunks
            embedding_batch = await embedder.embed_chunks(chunks, blob_record.sha)
            reporter.update(tokens=embedding_batch.total_tokens,
                          cost=embedding_batch.total_cost_usd)

            # Store
            store.add_chunks_batch(embedding_batch.embeddings,
                                  {blob_record.sha: blob_record.locations})

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        reporter.finish()  # Show partial stats
        sys.exit(130)

    except Exception as e:
        reporter.record_error()
        raise

    finally:
        reporter.finish()
```

## Dependencies

### External Libraries

None required beyond standard library for progress tracking. Cost calculations use standard Python arithmetic.

### Internal Dependencies

- **STORY-0001.2.1** (Commit Graph Walker) - Provides blob counts and statistics ✅
- **STORY-0001.2.2** (Blob Chunking) - Provides chunk counts ✅
- **STORY-0001.2.3** (OpenAI Embeddings) - Provides token/cost data ✅
- **STORY-0001.2.4** (LanceDB Storage) - Storage operations ✅

## Pattern Reuse

**Mocked Embedder Pattern** (follows existing test patterns):
- Tests use `isolated_env` fixture which clears `OPENAI_API_KEY` ([tests/unit/conftest.py:19-46](../../../tests/unit/conftest.py#L19-L46))
- Mock OpenAI API directly with `AsyncMock` ([tests/unit/embeddings/test_openai_embedder.py:70-75](../../../tests/unit/embeddings/test_openai_embedder.py#L70-L75))
- No "skip if no key" pattern - all tests use mocks for zero-cost CI

**Example from existing tests**:
```python
embedder = OpenAIEmbedder(api_key="sk-test123")
with patch.object(embedder._embeddings.async_client, "create", new_callable=AsyncMock) as mock_create:
    mock_create.return_value = mock_response
    result = await embedder.embed_chunks([chunk], "abc123")
```

## Success Criteria

Story is complete when:

- ✅ All 4 tasks implemented and tested
- ✅ All 5 BDD scenarios pass
- ✅ Default mode shows terse single-line output per TUI_GUIDE.md
- ✅ Verbose mode (-v) shows phase-by-phase progress per TUI_GUIDE.md
- ✅ Cost calculations accurate to ±0.001%
- ✅ Graceful cancellation works (SIGINT → exit 130 within 5s)
- ✅ Empty repository handled correctly
- ✅ Quality gates: ruff + mypy + pytest all pass

## Performance Targets

- Progress update overhead: <1ms per update (no complex rendering)
- Memory overhead: <1MB for progress tracking (no live displays)
- Fast execution: No performance impact vs no progress tracking

## Notes

- TUI_GUIDE compliant: terse by default, verbose on request
- No Rich progress bars (not allowed by TUI_GUIDE.md:1050)
- Simple print() statements for progress (fast, low overhead)
- Cost estimates are approximate (±20% confidence range)
- Spinner can be added in future if needed for >5s operations

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
