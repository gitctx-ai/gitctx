# STORY-0001.2.6: Indexing Cost & Performance Fixes

**Parent Epic**: [EPIC-0001.2](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 2
**Progress**: ███████░░░ 75%

## User Story

As a developer using gitctx
I want accurate cost estimates and efficient caching
So that I avoid surprise charges and can re-index for free

## Context

Production bug discovered during real-world usage on 263-commit repository:

1. **Cost Overrun**: Default mode walked entire git history (263 commits, 1,158 blobs) instead of snapshot (314 files) → 12.8x cost overrun ($42 vs expected $3)

2. **No Caching**: Pipeline bypassed `embed_with_cache()` orchestration → no `.gitctx/embeddings/*.safetensors` files created → every run re-embeds at full cost

3. **Inaccurate Estimates**: Dry-run only counted current files, never checked index mode or walked git history → showed $3 estimate but actual cost was $42

## Acceptance Criteria

**Cost Control:**
- [ ] Default mode is "snapshot" (HEAD tree only, not full history)
- [ ] History mode requires explicit config: `index.index_mode: history`
- [ ] History mode shows warning before indexing with cost implications

**Caching:**
- [ ] Pipeline uses `embed_with_cache()` orchestration (imports from `gitctx.indexing.embeddings`)
- [ ] Creates `.gitctx/embeddings/*.safetensors` cache files (one file per blob SHA + chunk index)
- [ ] Second run cost is $0.00 ±$0.01 with 100% cache hit rate (verified in logs: "Cache hit for blob")

**Accurate Estimation:**
- [ ] Dry-run walks git history to count exact blobs using `walker.count_unique_blobs()` (not heuristic file count)
- [ ] Dry-run respects `index_mode` configuration (snapshot counts HEAD only, history counts all commits)
- [ ] Dry-run output prints exact mode string: "Mode: snapshot (HEAD only)" or "Mode: history (full git)"
- [ ] Estimate matches actual cost within ±10% (measured by: `abs(actual - estimate) / estimate < 0.10`)

## Impact

**Cost Reduction:**
- First run: $42 → $3 (93% reduction)
- Second run: $42 → $0 (100% reduction with cache)
- Total (2 runs): $84 → $3 (96% savings)

**User Trust:**
- Accurate estimates prevent surprise charges
- Cache enables free re-indexing
- Clear mode indication prevents accidental history walks

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.2.6.1](TASK-0001.2.6.1.md) | Add snapshot mode to walker | ✅ Complete | 2 | 0/5 failing |
| [TASK-0001.2.6.2](TASK-0001.2.6.2.md) | Enable embedding cache in pipeline | ✅ Complete | 3 | 1/5 passing |
| [TASK-0001.2.6.3](TASK-0001.2.6.3.md) | Fix dry-run cost estimation | ✅ Complete | 2 | 2/5 passing |
| [TASK-0001.2.6.4](TASK-0001.2.6.4.md) | Add history mode warning | 🔵 Not Started | 1 | 5/5 passing ✅ |

**Total Hours**: 8 hours (≈1.3 story points, rounded to 2)

**Incremental BDD Tracking:**
- TASK-1: 0/5 scenarios (all failing) - snapshot mode implementation
- TASK-2: 1/5 scenarios (dry-run mode display) - cache integration
- TASK-3: 2/5 scenarios (snapshot + history dry-run) - accurate estimation
- TASK-4: 5/5 scenarios (all passing) - warning prompt ✅

## BDD Scenarios

**Testing Strategy**: VCR.py automatically records OpenAI API responses to cassettes (configured in `conftest.py`). Tests use small repos to minimize recording cost.

**Test Repository Size**:
- 5 commits with 3 files each (15 file instances)
- 8 unique blobs after deduplication
- Snapshot mode: 3 blobs (current HEAD only)
- History mode: 8 blobs (all versions across history)
- **One-time recording cost**: ~$0.08 (8 blobs × ~$0.01/blob)
- **Subsequent test runs**: $0.00 (VCR replay from cassettes)

**E2E Scenarios** (added to `tests/e2e/features/indexing.feature`):

```gherkin
Scenario: Snapshot mode counts only HEAD blobs
  Given a repository with 5 commits and 3 files
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx index --dry-run"
  Then the output should show "Mode: snapshot (HEAD only)"
  And the output should show "Blobs:        3"
  And the estimated cost should be less than "$0.05"

Scenario: History mode counts all blob versions
  Given a repository with 5 commits and 3 files
  And config file contains "index:\n  index_mode: history"
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx index --dry-run"
  Then the output should show "Mode: history (full git)"
  And the output should show "Blobs:        8"
  And the estimated cost should be between "$0.08" and "$0.12"

Scenario: Cache creates safetensor files on first run
  Given a clean repository with 5 commits and 3 files
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx index"
  Then the directory ".gitctx/embeddings/text-embedding-3-large/" should exist
  And the directory should contain 3 safetensor files
  And each safetensor file should be named by blob SHA

Scenario: Cache hit on second run costs nothing
  Given a repository indexed with 3 cached blobs
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx index --verbose"
  Then the output should contain "Cache hit for blob" 3 times
  And the cost should be "$0.00"
  And the indexing should complete in under 3 seconds

Scenario: History mode requires confirmation
  Given a repository with 5 commits
  And config file contains "index:\n  index_mode: history"
  When I run "gitctx index" and provide input "n"
  Then the output should contain "⚠️  History Mode Enabled"
  And the output should contain "full git history"
  And the output should contain "10-50x higher"
  And the command should exit with code 0
  And the directory ".gitctx/embeddings/" should not exist
```

**BDD Progress Tracking**:
- TASK-1 implements snapshot mode → Scenarios 1-2 pass (2/5)
- TASK-2 implements caching → Scenarios 3-4 pass (4/5)
- TASK-3 implements dry-run → Already covered by scenarios 1-2 (4/5)
- TASK-4 implements warning → Scenario 5 passes (5/5) ✅

**VCR Cassette Recording** (one-time, developer task):

```bash
# Record cassettes with direnv (loads real API key)
direnv exec . uv run pytest tests/e2e/features/indexing.feature::snapshot_mode_counts_only_head_blobs --vcr-record=once
direnv exec . uv run pytest tests/e2e/features/indexing.feature::history_mode_counts_all_blob_versions --vcr-record=once
direnv exec . uv run pytest tests/e2e/features/indexing.feature::cache_creates_safetensor_files_on_first_run --vcr-record=once
direnv exec . uv run pytest tests/e2e/features/indexing.feature::cache_hit_on_second_run_costs_nothing --vcr-record=once

# Scenario 5 needs no VCR (no API calls - just prompt interaction)

# Verify 4 cassettes created
ls tests/e2e/cassettes/ | grep -E "(snapshot_mode|history_mode|cache_creates|cache_hit)" | wc -l
# Expected: 4
```

**CI/CD runs** (no API key needed):
```bash
# Cassettes committed to repo, tests replay them
uv run pytest tests/e2e/features/indexing.feature
# Cost: $0.00
```

**Pattern Reuse**:
- Existing VCR configuration in `tests/e2e/conftest.py` (no changes needed)
- Existing `e2e_cli_runner` fixture (auto-merges `context["custom_env"]`)
- Existing cassette infrastructure (4 new cassettes added to existing set)
- Small repo pattern from `e2e_indexed_repo_factory` (5 commits × 3 files)

## Expected Outputs

### Snapshot Mode (After Fix)

```bash
$ gitctx index --dry-run
Mode:         snapshot (HEAD only)
Blobs:        314        # Exact from git
Est. cost:    $3.27
Range:        $2.94 - $3.60 (±10%)

$ gitctx index
✓ Indexing Complete
  Cost: $3.24          # ✅ Matches estimate!

$ gitctx index --verbose
  Cache hit for blob abc12345
  Cache hit for blob def67890
✓ Indexing Complete
  Cost: $0.00          # ✅ FREE!
```

### History Mode (With Warning)

```bash
$ gitctx config set index.index_mode history
$ gitctx index --dry-run
Mode:         history (full git)
Blobs:        1,158      # Exact! Walked 263 commits
Est. cost:    $40.26
Range:        $36.23 - $44.29 (±10%)

$ gitctx index
⚠️  History Mode Enabled
  Indexing ALL versions across full git history.
  Cost/time may be 10-50x higher than snapshot mode.

Continue? [y/N]: y
✓ Indexing Complete
  Cost: $41.93         # ✅ User made informed decision!
```

## Technical Design

### Fix #1: Snapshot Mode (TASK-0001.2.6.1)

Add `index_mode` config field and early return in walker:

**File**: `src/gitctx/config/settings.py`
```python
class IndexSettings(BaseModel):
    index_mode: Literal["snapshot", "history"] = Field(
        default="snapshot",
        description="snapshot=HEAD only, history=full git graph"
    )
```

**File**: `src/gitctx/git/walker.py` (in `_walk_commits()`)
```python
if self.config.repo.index.index_mode == "snapshot":
    head = self.repo.revparse_single("HEAD")
    yield CommitMetadata(...)
    return  # Early exit
```

### Fix #2: Enable Caching (TASK-0001.2.6.2)

Replace ~50 lines of manual chunking/embedding with orchestration:

**File**: `src/gitctx/indexing/pipeline.py`
```python
from gitctx.indexing.embeddings import embed_with_cache
from gitctx.storage.embedding_cache import EmbeddingCache

cache = EmbeddingCache(repo_path / ".gitctx", model="text-embedding-3-large")

# Replace manual logic with:
embeddings = await embed_with_cache(
    chunker=chunker,
    embedder=embedder,
    cache=cache,
    blob_record=blob_record,
)
```

**Net change**: +15 lines, -50 lines = **-35 lines** (major simplification)

### Fix #3: Accurate Dry-Run (TASK-0001.2.6.3)

Add fast count method and use in estimator:

**File**: `src/gitctx/git/walker.py`
```python
def count_unique_blobs(self) -> int:
    """Count blobs without reading content (fast for dry-run)."""
    for commit_metadata in self._walk_commits():
        # Walk and deduplicate, but DON'T read blob.data
        ...
    return len(self.blob_locations)
```

**File**: `src/gitctx/indexing/progress.py`
```python
def estimate_repo_cost(self, repo_path: Path, settings: GitCtxSettings) -> CostEstimate:
    walker = CommitWalker(str(repo_path), settings)
    unique_blob_count = walker.count_unique_blobs()  # Exact, not guessed!
    # ... use for estimation
```

### Fix #4: History Mode Warning (TASK-0001.2.6.4)

**File**: `src/gitctx/cli/index.py`
```python
if not dry_run and settings.repo.index.index_mode == "history":
    console.print("\n[yellow]⚠️  History Mode Enabled[/yellow]")
    console.print("  Indexing ALL versions across full git history.")
    console.print("  Cost/time may be 10-50x higher than snapshot mode.\n")
    if not typer.confirm("Continue?", default=False):
        raise typer.Exit(0)
```

## Testing Strategy

### Unit Tests

**File**: `tests/unit/git/test_walker.py`
- `test_snapshot_mode_only_walks_head_commit()`
- `test_history_mode_walks_all_commits()`
- `test_count_unique_blobs_matches_walk_blobs_count()`

**File**: `tests/unit/indexing/test_cost_estimator.py`
- `test_estimate_uses_exact_git_blob_count()`
- `test_snapshot_vs_history_estimates_differ()`

**File**: `tests/unit/storage/test_embedding_cache.py`
- `test_cache_creates_safetensor_files()`
- `test_cache_hit_returns_embeddings()`

### Manual Testing

```bash
# Clean slate
rm -rf .gitctx/db .gitctx/embeddings

# Test snapshot mode (default)
gitctx index --dry-run  # Should show ~314 blobs
gitctx index            # Should cost ~$3
gitctx index --verbose  # Should show cache hits, $0

# Test history mode
gitctx config set index.index_mode history
gitctx index --dry-run  # Should show ~1,158 blobs
gitctx index            # Should warn and cost ~$42

# Verify cache files
ls -lh .gitctx/embeddings/text-embedding-3-large/
```

## Migration Notes

**Breaking Change**: Default changes from history to snapshot.

**For users wanting full history:**
```bash
gitctx config set index.index_mode history
```

**Recommended for most users:**
```bash
# Delete old index and re-index (much cheaper!)
rm -rf .gitctx/db .gitctx/embeddings
gitctx index  # Now uses snapshot mode by default
```

## Dependencies

**Prerequisites:**
- STORY-0001.2.1 (Walker) - ✅ Complete
- STORY-0001.2.3 (Embeddings) - ✅ Complete
- STORY-0001.2.5 (Progress) - ✅ Complete

**No new packages required** - all fixes use existing infrastructure.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking change disrupts users | Medium | Medium | Clear migration guide, history mode still available |
| Cache file size growth | Low | Low | Document cleanup strategy (.gitctx/embeddings can be deleted) |
| Warning prompt too aggressive | Low | Low | Default=No, requires explicit Yes to continue |

---

**Created**: 2025-10-15
**Last Updated**: 2025-10-15
