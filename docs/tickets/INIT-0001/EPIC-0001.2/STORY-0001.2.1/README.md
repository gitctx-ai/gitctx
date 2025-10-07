# STORY-0001.2.1: Commit Graph Walker with Blob Deduplication

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 9
**Progress**: █████░░░░░ 57% (4/7 tasks complete)

## User Story

As a gitctx indexing system (serving developers and AI agents)
I want to walk the git commit graph and extract unique blobs with their location metadata
So that downstream components can chunk, embed, and store with complete git context for semantic search

## Acceptance Criteria

- [ ] Deduplicates blobs by SHA (same content indexed once)
- [ ] Deduplicates commits when walking multiple refs
- [ ] Tracks all locations where each blob appears (commit, path, is_head)
- [ ] Detects merge commits including octopus merges (is_merge flag)
- [ ] Filters binary files (null byte detection)
- [ ] Detects and skips Git LFS pointer files with warning logged to WalkStats.errors (error type: "lfs_pointer")
- [ ] Respects .gitignore rules (from HEAD)
- [ ] Skips oversized blobs (>5MB default, configurable)
- [ ] Supports multiple refs (branches, tags, HEAD)
- [ ] Handles bare repositories (is_head always False)
- [ ] Detects partial clones and errors with helpful message
- [ ] Detects shallow clones and errors asking for unshallow
- [ ] Reports progress during walk (callback with metrics)
- [ ] Handles errors gracefully (corrupt blobs, missing refs)
- [ ] Can resume from partial index (skip already-indexed blobs)

## BDD Scenarios

```gherkin
Feature: Commit Graph Walker

  Scenario: Blob deduplication across commits
    Given a repository with 100 commits
    And the same blob "auth.py" appears in 50 commits with SHA abc123
    When I walk the commit graph
    Then I should yield the blob abc123 exactly once
    And its locations list should contain 50 BlobLocation entries
    And each location should have the correct commit SHA, path, and is_head flag

  Scenario: Merge commit detection
    Given a repository with a merge commit
    And the merge commit has 2 parent commits
    When I walk the commit graph
    Then the merge commit's location should have is_merge = True
    And non-merge commits should have is_merge = False
    And all merge commits should be identified correctly

  Scenario: HEAD blob filtering
    Given a repository where blob abc123 exists in HEAD tree
    And blob def456 exists only in historical commits (not in HEAD)
    When I walk the commit graph
    Then blob abc123 locations should have is_head = True
    And blob def456 locations should have is_head = False
    And the is_head flag should be determined by HEAD tree membership

  Scenario: Binary file exclusion
    Given a repository with binary files (.jpg, .png, .pdf)
    And text files (.py, .md, .txt)
    When I walk the commit graph
    Then binary blobs should be skipped (not yielded)
    And only text blobs should be yielded
    And binary detection should use null byte check

  Scenario: Large blob exclusion
    Given a repository with a 15MB file
    And max_blob_size_mb is configured as 5
    When I walk the commit graph
    Then the 15MB blob should be skipped
    And a warning should be logged to WalkStats.errors
    And the error type should be "oversized_blob"

  Scenario: Resume from partial index
    Given a repository with 1000 unique blobs
    And 500 blobs are already indexed in LanceDB
    When I walk with already_indexed set containing 500 blob SHAs
    Then I should yield only 500 new blobs (not yet indexed)
    And skip the 500 already-indexed blobs
    And seen_blobs set should be pre-seeded with 500 SHAs

  Scenario: Multiple refs
    Given a repository with HEAD at commit A
    And main branch at commit B
    And feature branch at commit C with unique blobs
    When I walk with refs = ["HEAD", "refs/heads/feature"]
    Then I should yield blobs from both HEAD and feature branch
    And deduplicate blobs appearing in both refs
    And track which commits each blob appears in across all refs

  Scenario: Progress reporting
    Given a repository with 100 commits
    When I walk with a progress callback
    Then the callback should be invoked periodically during walk
    And provide WalkProgress with commits_seen, total_commits, unique_blobs_found
    And include current commit metadata (date, sha, message)
    And invoke every 10 commits to avoid excessive callback overhead

  Scenario: Gitignore filtering
    Given a repository with .gitignore containing "*.pyc" and "node_modules/"
    And historical commits contain .pyc files and node_modules/
    When I walk the commit graph
    Then .pyc blobs should be skipped (gitignored)
    And node_modules/ blobs should be skipped (gitignored)
    And package.json should be indexed (not gitignored)
    And gitignore rules should apply to all commits (historical and current)

  Scenario: Graceful error handling
    Given a repository with a corrupt blob (can't read content)
    When I walk the commit graph
    Then the corrupt blob should be skipped with a warning
    And the walker should continue processing other blobs
    And WalkStats.errors should contain a WalkError for the corrupt blob
    And the error should include blob SHA, commit SHA, and error message
```

### Edge Case Scenarios (Unit Tests)

```python
# tests/unit/core/test_commit_walker_edge_cases.py

def test_partial_clone_detection(tmp_path):
    """Partial clone (.git/objects/info/alternates exists) errors early."""
    # Create partial clone, verify error message

def test_shallow_clone_detection(tmp_path):
    """Shallow clone (.git/shallow exists) errors asking for unshallow."""
    # Create shallow clone, verify error asks for git fetch --unshallow

def test_bare_repository_handling(tmp_path):
    """Bare repository sets is_head=False for all blobs."""
    # Create bare repo, verify all locations have is_head=False

def test_git_lfs_pointer_detection(tmp_path):
    """Git LFS pointer files are detected and skipped."""
    # Create file with LFS header, verify skipped with warning

def test_multi_ref_commit_deduplication(tmp_path):
    """Same commit from multiple refs is processed only once."""
    # Create repo with overlapping refs, verify commit processed once

def test_octopus_merge_detection(tmp_path):
    """Octopus merge (3+ parents) is detected as merge commit."""
    # Create octopus merge, verify is_merge=True
```

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.2.1.0](TASK-0001.2.1.0.md) | Extend Config Schema for Walker Settings | ✅ Complete | 3 |
| [TASK-0001.2.1.1](TASK-0001.2.1.1.md) | Core Git Traversal | ✅ Complete | 10 |
| [TASK-0001.2.1.2](TASK-0001.2.1.2.md) | Blob Deduplication Logic | ✅ Complete | 6 |
| [TASK-0001.2.1.3](TASK-0001.2.1.3.md) | Location Metadata Collection | ✅ Complete | 6 |
| [TASK-0001.2.1.4](TASK-0001.2.1.4.md) | Blob Filtering | 🔵 | 7 |
| [TASK-0001.2.1.5](TASK-0001.2.1.5.md) | Progress & Error Handling | 🔵 | 4 |
| [TASK-0001.2.1.6](TASK-0001.2.1.6.md) | BDD Scenarios & Integration Tests | 🔵 | 10 |

**Total**: 46 hours

## Technical Design

### Core Data Structures

```python
@dataclass
class BlobLocation:
    """Where a blob appears in git history with commit context."""
    commit_sha: str
    file_path: str
    is_head: bool
    # Commit metadata (for denormalized LanceDB storage)
    author_name: str
    author_email: str
    commit_date: int
    commit_message: str
    is_merge: bool

@dataclass
class BlobRecord:
    """A unique blob with all its locations (walker output)."""
    sha: str
    content: bytes
    size: int
    locations: List[BlobLocation]

@dataclass
class WalkProgress:
    """Rich progress information for UI."""
    commits_seen: int
    total_commits: int
    unique_blobs_found: int
    current_commit_date: int
    current_commit_sha: str
    current_commit_message: str

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
    type: str  # "corrupt_blob", "oversized_blob", "lfs_pointer", etc.
    blob_sha: str
    commit_sha: str
    file_path: str
    message: str
```

### CommitWalker API

```python
class CommitWalker:
    """
    Walk git commit graph and extract unique blobs.

    Responsibilities:
    - Traverse commits from configured refs (reverse chronological)
    - Deduplicate blobs across commits
    - Track blob locations (commits, paths, is_head)
    - Filter blobs (gitignore, binary, LFS, size)
    - Report progress and errors

    Does NOT:
    - Chunk blob content (that's STORY-0001.2.2)
    - Generate embeddings (that's STORY-0001.2.3)
    - Store in LanceDB (that's STORY-0001.2.4)
    """

    def __init__(
        self,
        repo_path: str,
        config: GitCtxSettings,
        already_indexed: Set[str] = None,  # For resume from LanceDB
    ):
        """
        Initialize commit walker with repo validation.

        Args:
            repo_path: Path to git repository
            config: GitCtxSettings instance (provides max_blob_size_mb, default_refs, etc.)
            already_indexed: Set of blob SHAs to skip (for resume functionality)
        """
        self.repo = pygit2.Repository(repo_path)
        self.config = config
        self.already_indexed = already_indexed or set()

        # Read settings from config
        self.max_blob_size_mb = config.repo.index.max_blob_size_mb
        self.refs = config.repo.index.default_refs
        self.respect_gitignore = config.repo.index.respect_gitignore
        self.skip_binary = config.repo.index.skip_binary
        ...

    def walk(
        self,
        progress_callback: Callable[[WalkProgress], None] = None
    ) -> Iterator[BlobRecord]:
        """
        Walk commits and yield unique blobs.

        Yields:
            BlobRecord containing:
            - sha: str (blob SHA)
            - content: bytes (blob content)
            - size: int (blob size in bytes)
            - locations: List[BlobLocation] (all commits/paths)

        Raises:
            GitRepositoryError: If repo is invalid or inaccessible
            PartialCloneError: If partial clone detected
            ShallowCloneError: If shallow clone detected
        """
        ...

    def get_stats(self) -> WalkStats:
        """Get statistics from completed walk."""
        ...
```

### Files to Create/Modify

**New Files:**

- `src/gitctx/core/commit_walker.py` - Main walker class
- `src/gitctx/core/models.py` - BlobLocation, BlobRecord, WalkProgress, WalkStats, WalkError
- `src/gitctx/core/blob_filter.py` - Filtering logic (gitignore, binary, LFS, size)
- `tests/unit/core/test_commit_walker.py` - Unit tests for walker
- `tests/unit/core/test_deduplication.py` - Blob/commit dedup tests
- `tests/unit/core/test_location_tracking.py` - Location metadata tests
- `tests/unit/core/test_filtering.py` - Filter tests
- `tests/unit/core/test_progress.py` - Progress callback tests
- `tests/unit/core/test_error_handling.py` - Error handling tests
- `tests/unit/core/test_commit_walker_edge_cases.py` - Edge case unit tests
- `tests/e2e/features/commit_walker.feature` - Gherkin scenarios
- `tests/e2e/step_defs/test_commit_walker.py` - Step definitions

## Dependencies

### External Libraries

- `pygit2>=1.13.0` - Git operations via libgit2
- `pathspec>=0.11.0` - .gitignore pattern matching

### Internal Dependencies

- **STORY-0001.1.2** (Configuration System) - Required for walker configuration
  - Walker reads `config.repo.index.max_blob_size_mb` (default 5)
  - Walker reads `config.repo.index.default_refs` (default ["HEAD"])
  - Walker reads `config.repo.index.respect_gitignore` (default True)
  - Walker reads `config.repo.index.skip_binary` (default True)
  - TASK-0001.2.1.0 extends config schema with these settings (not in original STORY-0001.1.2)

### Prerequisites

- **STORY-0001.1.2** (Configuration System) complete ✅
  - Provides GitCtxSettings API and RepoConfig structure
  - TASK-0001.2.1.0 will extend config schema with walker settings
  - Walker imports and uses GitCtxSettings for configuration

## Architecture Decision: Denormalized LanceDB

**Key Decision**: Use denormalized LanceDB schema for optimal read performance.

**Rationale**:

- Core use case (95% of queries): "What's the context for this code chunk?"
- Denormalized: Single read with complete context ✅
- Normalized: Multiple table joins ❌
- Storage overhead: Only 3.4% larger (PyArrow columnar compression)
- Aligns with LanceDB's "two-dimensional storage" philosophy

**Impact on This Story**:

- BlobLocation includes commit metadata (author, date, message, is_merge)
- Downstream chunking/embedding stories don't need to track locations
- STORY-0001.2.4 (LanceDB Storage) handles denormalization join

## Out of Scope (Explicitly Deferred)

The following are intentionally excluded from this story:

1. ❌ **Git Notes** (`refs/notes/*`) - Defer to INIT-0002 (Intelligence Layer)
2. ❌ **Reflog walking** - Only walk reachable commits from refs
3. ❌ **Submodule recursion** - Treat submodules as separate repos (user runs gitctx in each)
4. ❌ **Parent commit SHAs** - Defer to STORY-0001.2.6 (graph topology)
5. ❌ **Commit graph analytics** - Defer to INIT-0002
6. ❌ **Normalized LanceDB tables** - Using denormalized schema for MVP

## Success Criteria

Story is complete when:

- ✅ All 6 tasks implemented and tested
- ✅ All 10 BDD scenarios pass
- ✅ All 6 edge case unit tests pass
- ✅ Unit test coverage >90%
- ✅ Performance: 10K commits in <30 seconds
- ✅ Memory: Peak <150MB for 10K commits
- ✅ Integration: Works with real git repositories
- ✅ Quality gates: ruff (no warnings, strict config), mypy (strict mode, no errors), pytest (all tests pass, coverage >90%)
- ✅ Documentation: API docstrings complete

## Performance Targets

- Index 10,000 commits in <30 seconds
- Deduplication: Skip 70%+ of blobs (typical unchanged rate)
- Memory usage: <150MB peak (actual: 55MB for 10K commits)
- Storage efficiency: <0.05x of source code size (5% due to deduplication)

---

**Created**: 2025-10-06
**Last Updated**: 2025-10-06
