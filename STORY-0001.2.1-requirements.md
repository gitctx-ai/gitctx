# STORY-0001.2.1: Commit Graph Walker with Blob Deduplication - Requirements Capture

**Date**: 2025-10-06
**Status**: Requirements gathering complete, ready for story drafting
**Parent Epic**: EPIC-0001.2 - Real Indexing Implementation

---

## Executive Summary

This document captures the complete requirements gathered during interactive interview for STORY-0001.2.1. Use this with `/write-next-tickets focused` tomorrow to draft the complete story.

---

## Architecture Decisions Confirmed

### Core Design: Blob-Centric LanceDB with Graph Awareness

**Key Principle**: gitctx captures the git graph as rich context for AI agents, not just file deduplication.

**Architecture:**
- ✅ Blob-centric indexing (not file-based like prototype)
- ✅ Denormalized LanceDB schema (location metadata in each chunk row)
- ✅ PyArrow List types for performance
- ✅ Reverse chronological walk order (UX: recent code first)
- ✅ Graph metadata captured (foundation for Tier 2 features)

**Memory Budget**: 150MB peak for 10K commits (actual: 55MB ✓)

---

## 1. BlobLocation Data Structure (FINAL)

### Optimized Structure with Shared Commit Metadata

```python
# Shared metadata (one entry per commit - deduplicated)
commits_metadata: Dict[str, CommitMetadata] = {}

@dataclass
class CommitMetadata:
    """Commit-level metadata, stored once per commit."""
    author_name: str        # ~20 bytes
    author_email: str       # ~30 bytes
    date: int               # 8 bytes (Unix timestamp)
    message: str            # ~500 bytes avg (FULL message for AI context)
    is_merge: bool          # 1 byte (graph foundation)
    # Total: ~559 bytes per commit

@dataclass
class BlobLocation:
    """Where a blob appears in git history."""
    commit_sha: str         # 40 bytes (FK to commits_metadata)
    file_path: str          # ~30 bytes
    is_head: bool           # 1 byte (computed via Option 2 - see below)
    # Total: ~71 bytes per location

@dataclass
class BlobRecord:
    """A unique blob with all its locations (walker output)."""
    sha: str                # Blob SHA
    content: bytes          # Blob content
    size: int               # Blob size
    locations: List[BlobLocation]  # All commits/paths containing this blob
```

### Memory Calculation (10K commits, 3K unique blobs)

```
commits_metadata:   10,000 commits × 559 bytes      = 5.6 MB
blob_locations:     700,000 locations × 71 bytes    = 49.7 MB
seen_blobs:         3,000 blobs × 40 bytes          = 0.12 MB
────────────────────────────────────────────────────────────
Total:                                              = 55.4 MB ✓
```

**Under budget!** (Target: 150MB, Actual: 55MB)

### Key Decisions

**A) Commit Message**: Full message
- ✅ Maximum context for AI agents
- ✅ Stored in shared commits_metadata dict (no duplication)
- ✅ Enables semantic commit message search (future)

**B) Author**: Name + email
- ✅ Enables author deduplication
- ✅ Stored in shared commits_metadata dict
- ✅ Supports "Alice" vs "Alice Smith" = same person queries

**C) is_head Computation: Option 2 (blob in HEAD tree)**

```python
# One-time setup (per walk)
head_tree = repo.head.peel(pygit2.Tree)
head_blobs: Set[str] = set()
for entry in head_tree.walk():
    if entry.type == 'blob':
        head_blobs.add(entry.hex)

# Per blob check (during walk)
is_head = (blob_sha in head_blobs)  # O(1) set lookup
```

**Cost**: 100ms setup + 0.001ms per blob = ~110ms total
**Semantic**: TRUE for any blob currently in HEAD tree
**Why**: Simpler than per-path tracking (Option 3: ~300ms), same result for "search current code" queries

---

## 2. Git Traversal Strategy

### Refs Configuration (Option C)

**Configurable refs with sensible defaults:**

```yaml
# .gitctx/config.yaml
index:
  # Which git refs to index for semantic search
  refs:
    - HEAD
    - refs/heads/main  # Auto-detected during init

  # Alternative examples for power users:
  # refs: ["HEAD"]                    # Only current branch
  # refs: ["refs/heads/*"]            # All branches
  # refs: ["HEAD", "refs/tags/v*"]    # HEAD + version tags
```

**Config init logic:**
```python
# During `gitctx init`
default_refs = ["HEAD"]

# Detect main branch (main vs master)
main_branch = detect_main_branch()
if main_branch:
    default_refs.append(f"refs/heads/{main_branch}")

config.index.refs = default_refs
```

**Implementation:**
```python
def walk(self) -> Iterator[BlobRecord]:
    """Walk commits from all configured refs."""
    for ref in self.refs:
        ref_obj = self.repo.references[ref]
        commit = ref_obj.peel(pygit2.Commit)

        # Walk from this ref...
```

### Commit Order: Reverse Chronological (Newest First)

```python
for commit in self.repo.walk(
    commit.id,
    pygit2.GIT_SORT_TIME | pygit2.GIT_SORT_REVERSE
):
    # Process commits newest → oldest
```

**Why reverse chronological:**

1. ✅ **UX Priority**: Current code indexed first
   - If interrupted at 30%, HEAD is searchable
   - User can start using partial index immediately

2. ✅ **Better Progress UX**:
   ```
   Indexing commits (newest first)...
   [=====>     ] 2,547 / 10,000 commits
   HEAD ✓ | main ✓ | 547 unique blobs found
   ```

3. ✅ **Graph metadata preserved**:
   - Store is_merge flag (graph foundation)
   - Can reconstruct topology at query time
   - Future: Add parent_shas (STORY-0001.2.6 - Tier 2)

4. ✅ **No performance cost**: Git sorting is fast (native libgit2)

**Tradeoff accepted**: Walk order ≠ topological, but we capture graph metadata for future queries

### Merge Commits: Track but Don't Special-Case

**What we capture:**
```python
is_merge = len(commit.parents) > 1  # Store in CommitMetadata
```

**What we DON'T do in MVP:**
- ❌ Skip merge commit tree walks (need all blob locations)
- ❌ Capture parent_shas (defer to Tier 2 - STORY-0001.2.6)
- ❌ Analyze merge diffs (defer to EPIC-0002.X)

**Why:**
- ✅ Captures merge semantics (foundation for graph queries)
- ✅ Doesn't complicate walker logic
- ✅ Enables future "show merge conflict resolutions" queries
- ✅ Tree walking is fast; dedup via seen_blobs set handles efficiency

**Graph context goal**: Foundation for AI agents to understand git graph evolution, defer rich queries to future stories

---

## 3. File Filtering Strategy

### A) .gitignore: Always Respect ✅

**Strategy**: Respect .gitignore for ALL commits (historical and current)

```python
# Parse .gitignore from HEAD (current gitignore rules)
gitignore_spec = parse_gitignore(repo.head.tree)

# Apply to all commits
for commit in walk():
    for blob in commit.tree:
        if gitignore_spec.matches(blob.path):
            continue  # Skip this blob
```

**Why:**
- ✅ **Security**: Prevents indexing accidentally committed secrets (.env files)
- ✅ **Efficiency**: Skips noise (node_modules/, *.pyc, etc.)
- ✅ **Context preserved**: Tracked manifests (package.json, requirements.txt) contain dependency info

**Example**: node_modules/ accidentally committed in 2020
- ❌ Skip node_modules/lodash/* (gitignored, noise)
- ✅ Index package.json (tracked, has "lodash": "3.10.1")
- **Result**: AI can still answer "we used lodash v3" from package.json!

### B) Binary Detection: Null Byte Check (Git's Heuristic) ✅

**Simple, fast, proven approach:**

```python
def is_binary_blob(blob_data: bytes) -> bool:
    """
    Detect binary content using git's heuristic.

    Checks for null bytes in first 8KB (same as git).
    Simple, fast, and good enough for 99% of cases.

    Edge cases (UTF-16 with BOM) can be handled in future stories.
    """
    return b'\0' in blob_data[:8192]
```

**Why null byte over sophisticated detection:**
1. ✅ **Zero dependencies** - No binaryornot, no chardet, no external packages
2. ✅ **Fast** - ~0.1ms per blob (3K blobs = 300ms total)
3. ✅ **Git-compatible** - Same heuristic git uses
4. ✅ **Simple** - 1 line of code, easy to understand
5. ✅ **MVP-appropriate** - Don't over-engineer

**Performance**: 300ms for 3K blobs (vs 60 seconds for embeddings - negligible!)

**Future enhancement path:**
- STORY-0001.2.6: Add binaryornot for better edge case handling (UTF-16, complex encodings)
- EPIC-0002.X: Build PyO3 bindings for Rust `infer` crate (nanosecond performance)

**Edge cases deferred to future stories**: UTF-16 with BOM, complex encodings

### C) Size Limit: 5MB Default, Configurable ✅

```yaml
# .gitctx/config.yaml
index:
  # Maximum blob size to index (in MB)
  max_blob_size_mb: 5
```

**Why 5MB:**
- ✅ Includes package lock files (1-2MB): useful for "what dependencies?" queries
- ✅ Includes large docs (1-3MB): useful context
- ✅ Excludes massive files (videos, datasets >5MB): not useful for semantic search
- ✅ Cost: ~$0.18/file for occasional 5MB file (acceptable)

**Math**: 5MB file = 357 chunks × $0.00013/1K tokens × 800 tokens = $0.37 per file

**Note**: Config file format is YAML (not TOML as initially mentioned)

---

## 4. Memory Management Strategy

### Option D: Accept Memory Usage, Document Limits ✅

**Approach**: Simple implementation, document 50K commit ceiling

```python
# No complex memory optimization in MVP
# Track everything in memory during walk
# 55MB for 10K commits is excellent
```

**Limits documented:**
- Works well for repos up to **50K commits**
- Covers 99% of repositories
- Memory scales linearly: 10K commits = 55MB, 50K commits = 275MB

**Future enhancement**: STORY-0001.2.5 adds incremental indexing for mega-repos

**Alternatives deferred:**
- ❌ Option A: Two-pass walking (slower, lower memory) - unnecessary
- ❌ Option B: Cap locations per blob (lossy data) - unnecessary
- ❌ Option C: Incremental yielding (complex) - unnecessary

**Why Option D for MVP**: 55MB is excellent, simple code, covers 99% of use cases

---

## 5. Progress Reporting Interface

### Option B: Rich Progress Callback ✅

```python
@dataclass
class WalkProgress:
    """Rich progress information for UI."""
    commits_seen: int           # How many commits processed
    total_commits: int          # Total commits to process
    unique_blobs_found: int     # Unique blobs discovered so far
    current_commit_date: datetime  # Date of current commit
    current_commit_sha: str     # Short SHA for display
    current_commit_message: str # First line of commit message

def walk(
    self,
    progress_callback: Callable[[WalkProgress], None] = None
) -> Iterator[BlobRecord]:
    """
    Walk commits and yield unique blobs.

    Args:
        progress_callback: Optional callback for progress updates

    Yields:
        BlobRecord with sha, content, size, locations
    """
    for i, commit in enumerate(commits):
        if progress_callback and i % 10 == 0:  # Every 10 commits
            progress_callback(WalkProgress(
                commits_seen=i,
                total_commits=total_commits,
                unique_blobs_found=len(self.seen_blobs),
                current_commit_date=commit.commit_time,
                current_commit_sha=commit.hex[:7],
                current_commit_message=commit.message.split('\n')[0]
            ))

        # ... walk logic ...
```

**Why rich callback:**
- ✅ Walker knows most about progress (commits, blobs)
- ✅ Enables rich UI: "Processing abc123 (2024-06-15): Fix auth bug"
- ✅ Caller can ignore if not needed (optional parameter)
- ✅ Better UX than simple counter

---

## 6. Error Handling Strategy

### Graceful Degradation ✅

**Philosophy**: 99% of blobs are fine, don't fail entire index for one corrupt blob

```python
@dataclass
class WalkStats:
    """Statistics collected during walk."""
    commits_seen: int = 0
    blobs_indexed: int = 0
    blobs_skipped: int = 0
    errors: List[WalkError] = field(default_factory=list)

@dataclass
class WalkError:
    """Error encountered during walk."""
    type: str  # "corrupt_blob", "missing_parent", "oversized_blob"
    blob_sha: str
    commit_sha: str
    file_path: str
    message: str

def walk(self) -> Iterator[BlobRecord]:
    """Walk with graceful error handling."""
    try:
        # ... walk logic ...
    except CorruptBlobError as e:
        self.stats.errors.append(WalkError(
            type="corrupt_blob",
            blob_sha=blob_sha,
            commit_sha=commit.hex,
            file_path=blob_path,
            message=str(e)
        ))
        logger.warning(f"Skipping corrupt blob {blob_sha[:7]} in {commit.hex[:7]}")
        continue  # Keep going!
```

**Error types handled:**
- **Corrupt blob**: Skip with warning, log error, continue
- **Missing parent**: Log warning, continue (broken history)
- **Oversized blob**: Skip with warning (> max_blob_size_mb)
- **Binary file**: Skip silently (expected filtering)
- **Gitignored file**: Skip silently (expected filtering)

**Return stats at end**: User can review errors and decide if acceptable or if repo needs repair

---

## 7. BDD Scenarios (Complete Coverage)

### Scenario 1: Blob Deduplication Across Commits
```gherkin
Given a repository with 100 commits
And the same blob "auth.py" appears in 50 commits with SHA abc123
When I walk the commit graph
Then I should yield the blob abc123 exactly once
And its locations list should contain 50 BlobLocation entries
And each location should have the correct commit SHA, path, and is_head flag
```

### Scenario 2: Merge Commit Detection
```gherkin
Given a repository with a merge commit
And the merge commit has 2 parent commits
When I walk the commit graph
Then the merge commit's CommitMetadata should have is_merge = True
And non-merge commits should have is_merge = False
And all merge commits should be identified correctly
```

### Scenario 3: HEAD Blob Filtering
```gherkin
Given a repository where blob abc123 exists in HEAD tree
And blob def456 exists only in historical commits (not in HEAD)
When I walk the commit graph
Then blob abc123 locations should have is_head = True
And blob def456 locations should have is_head = False
And the is_head flag should be determined by HEAD tree membership
```

### Scenario 4: Binary File Exclusion
```gherkin
Given a repository with binary files (.jpg, .png, .pdf)
And text files (.py, .md, .txt)
When I walk the commit graph
Then binary blobs should be skipped (not yielded)
And only text blobs should be yielded
And binary detection should use null byte check
```

### Scenario 5: Large Blob Exclusion
```gherkin
Given a repository with a 15MB file
And max_blob_size_mb is configured as 5
When I walk the commit graph
Then the 15MB blob should be skipped
And a warning should be logged to WalkStats.errors
And the error type should be "oversized_blob"
```

### Scenario 6: Resume From Partial Index
```gherkin
Given a repository with 1000 unique blobs
And 500 blobs are already indexed in LanceDB
When I walk with already_indexed set containing 500 blob SHAs
Then I should yield only 500 new blobs (not yet indexed)
And skip the 500 already-indexed blobs
And seen_blobs set should be pre-seeded with 500 SHAs
```

### Scenario 7: Multiple Refs
```gherkin
Given a repository with HEAD at commit A
And main branch at commit B
And feature branch at commit C with unique blobs
When I walk with refs = ["HEAD", "refs/heads/feature"]
Then I should yield blobs from both HEAD and feature branch
And deduplicate blobs appearing in both refs
And track which commits each blob appears in across all refs
```

### Scenario 8: Progress Reporting
```gherkin
Given a repository with 100 commits
When I walk with a progress callback
Then the callback should be invoked periodically during walk
And provide WalkProgress with commits_seen, total_commits, unique_blobs_found
And include current commit metadata (date, sha, message)
And invoke every 10 commits to avoid excessive callback overhead
```

### Scenario 9: Gitignore Filtering
```gherkin
Given a repository with .gitignore containing "*.pyc" and "node_modules/"
And historical commits contain .pyc files and node_modules/
When I walk the commit graph
Then .pyc blobs should be skipped (gitignored)
And node_modules/ blobs should be skipped (gitignored)
And package.json should be indexed (not gitignored)
And gitignore rules should apply to all commits (historical and current)
```

### Scenario 10: Graceful Error Handling
```gherkin
Given a repository with a corrupt blob (can't read content)
When I walk the commit graph
Then the corrupt blob should be skipped with a warning
And the walker should continue processing other blobs
And WalkStats.errors should contain a WalkError for the corrupt blob
And the error should include blob SHA, commit SHA, and error message
```

---

## 8. Task Breakdown (6 Tasks, 38 Hours Total = 8 Story Points)

### TASK-0001.2.1.1: Core Git Traversal (8 hours)
**What**: Implement commit walking with pygit2
- Initialize CommitWalker with refs configuration
- Walk commits in reverse chronological order (pygit2.GIT_SORT_TIME | GIT_SORT_REVERSE)
- Support multiple refs (HEAD, main, feature branches)
- Detect merge commits (is_merge = len(parents) > 1)
- Extract CommitMetadata (author, email, date, message, is_merge)
- Store in commits_metadata dict (one entry per commit SHA)

**Files**:
- `src/gitctx/core/commit_walker.py` (new)
- `tests/unit/core/test_commit_walker.py` (new)

**Tests**:
- Unit: Reverse chronological order verification
- Unit: Multiple refs support
- Unit: Merge commit detection
- Unit: CommitMetadata extraction

### TASK-0001.2.1.2: Blob Deduplication Logic (6 hours)
**What**: Implement unique blob tracking
- Maintain seen_blobs: Set[str] for O(1) dedup checks
- Maintain blob_locations: Dict[str, List[BlobLocation]]
- Accumulate all locations for each blob across commits
- Yield BlobRecord on first encounter of blob SHA
- Continue tracking locations even after yielding (for complete metadata)

**Files**:
- `src/gitctx/core/commit_walker.py` (extend)
- `tests/unit/core/test_deduplication.py` (new)

**Tests**:
- Unit: Blob appears in 50 commits, yielded once
- Unit: All 50 locations captured
- Unit: Dedup across multiple refs
- Unit: Memory efficiency (Set vs List)

### TASK-0001.2.1.3: Location Metadata Collection (6 hours)
**What**: Implement BlobLocation tracking and is_head computation
- Build HEAD tree blob set on walk initialization (for is_head checks)
- For each blob in each commit:
  - Create BlobLocation(commit_sha, file_path, is_head)
  - Add to blob_locations[blob_sha]
- Compute is_head via: blob_sha in head_blobs (O(1) set lookup)
- Build BlobRecord with complete location list

**Files**:
- `src/gitctx/core/commit_walker.py` (extend)
- `src/gitctx/core/models.py` (new - BlobLocation, BlobRecord dataclasses)
- `tests/unit/core/test_location_tracking.py` (new)

**Tests**:
- Unit: is_head = True for HEAD blobs
- Unit: is_head = False for historical blobs
- Unit: Correct file paths tracked
- Unit: HEAD tree build performance

### TASK-0001.2.1.4: Blob Filtering (6 hours)
**What**: Implement gitignore, binary, and size filtering
- Parse .gitignore from HEAD tree using pathspec library
- Create pathspec.PathSpec from .gitignore patterns
- Always exclude .git/ and .gitctx/ directories
- Binary detection: null byte check (b'\0' in blob_data[:8192])
- Size limit: Skip blobs > max_blob_size_mb * 1024 * 1024
- All filtering happens before yielding BlobRecord

**Files**:
- `src/gitctx/core/blob_filter.py` (new)
- `tests/unit/core/test_filtering.py` (new)

**Tests**:
- Unit: .gitignore patterns respected
- Unit: Binary files skipped (null byte detection)
- Unit: Large files skipped (size limit)
- Unit: .git/ and .gitctx/ always excluded
- Unit: Text files pass filter

### TASK-0001.2.1.5: Progress & Error Handling (4 hours)
**What**: Implement progress callbacks and error collection
- Define WalkProgress dataclass
- Invoke progress_callback every 10 commits
- Include: commits_seen, total_commits, unique_blobs, current commit metadata
- Define WalkStats and WalkError dataclasses
- Graceful error handling: catch exceptions, log, continue
- Collect errors in WalkStats.errors list
- Return WalkStats after walk complete

**Files**:
- `src/gitctx/core/commit_walker.py` (extend)
- `src/gitctx/core/models.py` (extend - add WalkProgress, WalkStats, WalkError)
- `tests/unit/core/test_progress.py` (new)
- `tests/unit/core/test_error_handling.py` (new)

**Tests**:
- Unit: Progress callback invoked correctly
- Unit: WalkProgress contains correct data
- Unit: Corrupt blob skipped, error logged
- Unit: Walk continues after errors
- Unit: WalkStats contains all errors

### TASK-0001.2.1.6: BDD Scenarios & Integration Tests (8 hours)
**What**: Write all Gherkin scenarios and step definitions
- Create test fixture repos (with pygit2 or git commands)
- Write 10 Gherkin scenarios (see section 7 above)
- Implement step definitions for each scenario
- Integration test with real git repo (if available)
- Performance test: 10K commits in <30 seconds
- Memory test: Peak memory <150MB

**Files**:
- `tests/e2e/features/commit_walker.feature` (new)
- `tests/e2e/step_defs/test_commit_walker.py` (new)
- `tests/fixtures/test_repos.py` (new - helper to create test repos)

**Tests**:
- BDD: All 10 scenarios from section 7
- Integration: Real repo smoke test
- Performance: 10K commits benchmark
- Memory: Memory profiling test

---

## 9. CommitWalker API (Public Interface)

```python
class CommitWalker:
    """
    Walk git commit graph and extract unique blobs.

    Responsibilities:
    - Traverse commits from configured refs (reverse chronological)
    - Deduplicate blobs across commits
    - Track blob locations (commits, paths, is_head)
    - Filter blobs (gitignore, binary, size)
    - Report progress and errors

    Does NOT:
    - Chunk blob content (that's STORY-0001.2.2)
    - Generate embeddings (that's STORY-0001.2.3)
    - Store in LanceDB (that's STORY-0001.2.4)
    """

    def __init__(
        self,
        repo_path: str,
        refs: List[str] = None,  # Default: ["HEAD"]
        already_indexed: Set[str] = None,  # For resume
        max_blob_size_mb: int = 5,  # Configurable size limit
    ):
        """
        Initialize commit walker.

        Args:
            repo_path: Path to git repository
            refs: Git refs to walk (default: ["HEAD"])
            already_indexed: Set of blob SHAs to skip (for resume)
            max_blob_size_mb: Maximum blob size in MB (default: 5)
        """
        ...

    def walk(
        self,
        progress_callback: Callable[[WalkProgress], None] = None
    ) -> Iterator[BlobRecord]:
        """
        Walk commits and yield unique blobs.

        Args:
            progress_callback: Optional callback for progress updates

        Yields:
            BlobRecord containing:
            - sha: str (blob SHA)
            - content: bytes (blob content)
            - size: int (blob size in bytes)
            - locations: List[BlobLocation] (all commits/paths)

        Raises:
            GitRepositoryError: If repo is invalid or inaccessible
        """
        ...

    def get_stats(self) -> WalkStats:
        """
        Get statistics from completed walk.

        Returns:
            WalkStats with commits_seen, blobs_indexed, errors, etc.
        """
        ...

    def estimate_blob_count(self) -> int:
        """
        Estimate total unique blobs without full walk.

        Quick estimate for progress bar initialization.

        Returns:
            Estimated number of unique blobs
        """
        ...
```

---

## 10. Dependencies

**Python packages** (add to pyproject.toml):
```toml
[project]
dependencies = [
    "pygit2>=1.13.0",  # Git operations via libgit2
    "pathspec>=0.11.0",  # Gitignore pattern matching
]
```

**NO additional dependencies** (null byte check, no binaryornot, no chardet)

---

## 11. Config Schema Updates

**Add to .gitctx/config.yaml**:

```yaml
index:
  # Which git refs to index for semantic search
  refs:
    - HEAD
    - refs/heads/main  # Auto-detected during gitctx init

  # Maximum blob size to index (in MB)
  max_blob_size_mb: 5

  # Respect .gitignore patterns (recommended for security)
  respect_gitignore: true
```

**Config init defaults** (during `gitctx init`):
- refs: ["HEAD", "refs/heads/{detected_main_branch}"]
- max_blob_size_mb: 5
- respect_gitignore: true

---

## 12. Future Enhancement Paths

### Tier 1: MVP (This Story - STORY-0001.2.1)
- ✅ Basic blob deduplication
- ✅ Location tracking (commit, path, is_head)
- ✅ Merge commit awareness (is_merge flag)
- ✅ Simple filtering (gitignore, null byte, size)

### Tier 2: Graph Topology (STORY-0001.2.6)
- Add parent_shas: List[str] to CommitMetadata
- Enable evolution chain queries ("how did this code evolve?")
- Branch membership tracking
- Commit graph visualization data

### Tier 3: Rich Context (EPIC-0002.X)
- Semantic commit message search
- Co-authorship graphs
- Blob modification frequency ("high churn" detection)
- Branch comparison ("what's new in feature branch?")
- PyO3 bindings for Rust performance (infer crate for binary detection)

---

## 13. Success Criteria

**Story is complete when:**
- ✅ All 6 tasks implemented and tested
- ✅ All 10 BDD scenarios pass
- ✅ Unit test coverage >90%
- ✅ Performance: 10K commits in <30 seconds
- ✅ Memory: Peak <150MB for 10K commits (actual: 55MB ✓)
- ✅ Integration: Works with real git repositories
- ✅ Quality gates: ruff, mypy, pytest all pass
- ✅ Documentation: API docstrings complete

**Definition of Done:**
- Code committed with message: `feat(TASK-0001.2.1.X): <description>`
- All tests passing in CI
- Epic README.md updated with story progress
- Ready for STORY-0001.2.2 (Chunker) to consume BlobRecord output

---

## 14. Open Questions / Deferred Decisions

**Questions for future stories:**
1. Commit graph analytics epic? (Defer until after EPIC-0001.2 MVP complete)
2. Incremental indexing for mega-repos? (STORY-0001.2.5)
3. LanceDB schema impact with graph metadata? (STORY-0001.2.4 will decide)
4. PyO3 bindings roadmap? (EPIC-0002.X after product-market fit)

**Assumptions:**
- pygit2 provides all needed git operations
- pathspec handles all gitignore edge cases
- Null byte detection covers 99% of binary files
- 50K commit limit acceptable for MVP

---

## 15. Notes for Tomorrow's Session

**To draft the story with `/write-next-tickets focused`:**

1. Run: `/write-next-tickets focused` → Choose "STORY-0001.2.1" or "next story"
2. Agent will use this requirements file as context
3. All architecture decisions are captured above
4. BDD scenarios are complete (copy directly to story)
5. Task breakdown is complete (38 hours = 8 story points)
6. API interface is defined (copy to Technical Design section)

**Story structure to generate:**
- User story: "As a developer/I want/So that" format
- Acceptance criteria: Based on success criteria above
- BDD scenarios: Copy from section 7
- Technical design: API + architecture from sections 1-2
- Tasks: Copy from section 8
- Story points: 8 (sum of task hours ÷ 5)
- Dependencies: pygit2, pathspec

**Key files to create:**
- `docs/tickets/INIT-0001/EPIC-0001.2/STORY-0001.2.1/README.md`
- `docs/tickets/INIT-0001/EPIC-0001.2/STORY-0001.2.1/TASK-0001.2.1.1.md`
- `docs/tickets/INIT-0001/EPIC-0001.2/STORY-0001.2.1/TASK-0001.2.1.2.md`
- ... (through TASK-0001.2.1.6)

**Parent epic update:**
- Update `docs/tickets/INIT-0001/EPIC-0001.2/README.md`
- Add STORY-0001.2.1 to child stories table
- Update epic progress (this is first story: 0% → ~20%)

---

## End of Requirements Document

**Status**: ✅ Complete - Ready for story drafting
**Next Action**: Run `/write-next-tickets focused` → Select STORY-0001.2.1
**Estimated Drafting Time**: 30-45 minutes (agent writes story from this spec)

Good night! 🌙
