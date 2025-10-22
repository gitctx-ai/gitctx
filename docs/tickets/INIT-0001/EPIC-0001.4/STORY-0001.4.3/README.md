# STORY-0001.4.3: File-Grouped Result Presentation

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 4 (16 hours estimated = 4 points)
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer reviewing search results
I want results grouped by file showing HEAD chunks by default
So that I understand the current file context and can see matching chunks organized naturally for my use case

## Acceptance Criteria

### File Grouping (All Formats)

- [ ] Search results grouped by `file_path` before display
- [ ] **NEW --filter flag** added to search command (default: head):
  - CLI implementation: `src/gitctx/cli/search.py` (added in TASK-0001.4.3.2)
  - `--filter=head`: Show only HEAD chunks (is_head == true) [DEFAULT]
  - `--filter=history`: Show only historical chunks (is_head == false)
  - `--filter=all`: Show both HEAD and historical chunks
  - Passed to formatters via kwargs: `format(results, console, filter='head', min_similarity=0.5, ...)`
  - FormatterBase._filter_and_group() receives filter_mode parameter
- [ ] All formatters filter chunks by minimum similarity threshold (default: 0.5, configurable via --min-similarity flag, existing in CLI)
- [ ] **Files with zero chunks after filtering are completely omitted** (no header, no empty section)
- [ ] Chunk count uses proper singular/plural: `(1 chunk)` vs `(2 chunks)`
- [ ] **SearchResult.score property** added to simplify formatter code:
  - Returns `hybrid_score` (if available) or `vector_score` (fallback) or 0.0
  - Formatters use `chunk.score` instead of explicit field selection
  - Property added in TASK-0001.4.3.2 alongside FormatterBase
- [ ] --min-similarity flag validation (in CLI layer, src/gitctx/cli/search.py):
  - Accept float values -1.0 to 1.0 (inclusive)
  - Reject values < -1.0 or > 1.0 with error: "Error: --min-similarity must be between -1.0 and 1.0 (got: {value})" and exit code 2
  - Reject non-numeric values with error: "Error: --min-similarity must be a number (got: {value})" and exit code 2
  - Convert to max_distance for LanceDB: max_distance = 1.0 - min_similarity
  - FormatterBase._filter_and_group() receives min_similarity value, filters on SearchResult.score property
- [ ] Edge cases: similarity=-1.0 shows all chunks (including opposite meaning), similarity=1.0 shows only perfect matches (similarity = 1.0)
- [ ] Files sorted by best chunk's boosted score (highest scoring chunk determines file rank)

### Terse Format (Score-Focused)

- [ ] Chunks sorted by score descending within each file (best matches first for quick scanning)
  - Tie-breaking: score descending → line number ascending → content lexicographically
  - Handles edge case: identical scores at same line number (e.g., duplicate chunks)
- [ ] One line per chunk format: `:LINE_NUM  SCORE  PREVIEW`
  - File header: `src/auth.py (3 chunks):`
  - Preview: first line only, max 80 chars, add '...' if truncated
  - Score shown prominently for relevance scanning
  - Example:
    ```
    src/auth.py (3 chunks):
      :45   0.95  class AuthMiddleware:
      :67   0.87  def process_request(self):
      :103  0.75  def validate_token(self):

    src/user.py (1 chunk):
      :12   0.82  class User:
    ```

### Verbose Format (Code-Reading)

- [ ] Chunks sorted by line order ascending within each file (natural reading order)
  - Tie-breaking: line number ascending → score descending → content lexicographically
  - Ensures stable sort even with duplicate metadata (e.g., multiple chunks at line 0)
- [ ] Best-scoring chunk marked with comment-style indicator (copy-pasteable):
  - Best chunk: `# {SYMBOLS["best_match"]} Lines 45-60 (score: 0.95, best match)` (⭐ on modern terminals, * on legacy)
  - Other chunks: `# Lines 10-20 (score: 0.75)`
  - Uses `SYMBOLS["best_match"]` from `gitctx.cli.symbols` for platform-aware rendering
- [ ] All chunks shown with full syntax highlighting
  - File header: `src/auth.py (3 chunks)` (bold, no colon)

### MCP Format (Programmatic)

- [ ] Chunks sorted by score descending (default for relevance ranking; consumers can re-sort by line_range)
- [ ] All chunks in JSON structure with file metadata (filtered by threshold)
  - Each file entry: `file_path`, `language`, `best_score`, `total_chunks`
  - Each chunk: `content`, `line_range`, `score`, `is_head`

**Design Rationale**:
- **Default order (score)**: MCP consumers typically want to process best matches first for:
  - LLM context prioritization (send highest-scoring chunks to model)
  - Relevance filtering (discard low-scoring chunks programmatically)
  - Search result ranking (display most relevant first in tools)
- **Re-sorting option**: Consumers needing code reading order can re-sort: `chunks.sort(key=lambda c: c['line_range'][0])`
- **Trade-off**: Score order optimizes for relevance, line order optimizes for comprehension

### Test Coverage

- [ ] Test coverage complete:
  - [ ] 55+ unit tests passing (18+ base, 15+ terse, 12+ verbose, 10+ MCP)
  - [ ] 3/3 BDD scenarios passing (file grouping, format selection, filtering)
  - [ ] >90% code coverage on all formatters
  - [ ] 100% coverage on SearchResult.score property
  - [ ] 100% coverage on CLI --filter flag

## BDD Scenarios

**Testing Strategy**: This story uses **unit-test-heavy approach** with BDD smoke tests:
- **Unit tests** (20+ tests): Detailed format validation, sorting, edge cases (fast, deterministic)
- **BDD tests** (3 scenarios): User workflow integration smoke tests (realistic, end-to-end)

**Rationale**: File grouping and formatting are implementation details best tested with mocked SearchResult objects. BDD validates the complete user journey (index → search → format → output) works correctly.

**3 BDD smoke test scenarios** (integration testing):

### Scenario 1: File grouping works across all formats (Smoke Test)

```gherkin
Given an indexed repository with files containing "auth" keyword
When I search for "auth"
Then results should be grouped by file path
And each file should appear exactly once as a header
And all chunks should appear under their respective file headers
And this behavior should be consistent across terse, verbose, and MCP formats
```

**Purpose**: Verifies the core file grouping workflow works end-to-end with real indexing.

**Step Definitions**: Implemented in TASK-0001.4.3.2 (FormatterBase)

### Scenario 2: Format selection produces different outputs (Smoke Test)

```gherkin
Given an indexed repository with files containing "login" keyword
When I search for "login" with default format (terse)
Then I see compact output with one line per chunk
When I search for "login" with --format=verbose
Then I see full code blocks with syntax highlighting
When I search for "login" with --format=mcp
Then I get valid JSON with chunks array
```

**Purpose**: Verifies that format selection actually produces visibly different output styles.

**Step Definitions**: Implemented in TASK-0001.4.3.5 (final integration task)

### Scenario 3: Score filtering removes low-scoring chunks (Smoke Test)

```gherkin
Given an indexed repository with multiple files
When I search with --min-similarity=0.8
Then only high-scoring chunks appear in results
And low-scoring chunks are filtered out
And files with no chunks passing threshold are omitted entirely
```

**Purpose**: Verifies that similarity threshold filtering works correctly through the entire pipeline.

**Step Definitions**: Implemented in TASK-0001.4.3.2 (FormatterBase)

---

**Detailed format validation moved to unit tests** (see individual TASK files for 20+ unit tests covering exact format strings, sorting algorithms, edge cases, etc.)

## Technical Design

### Components to Modify

**1. `src/gitctx/formatters/terse.py`** (NEW design: one line per chunk, score-focused)

Show file header and one line per chunk, sorted by score:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in terse mode - one line per chunk."""

    # Filter and group (base class does NOT sort chunks)
    min_similarity = kwargs.get('min_similarity', 0.5)
    filter_mode = kwargs.get('filter', 'head')
    grouped = self._filter_and_group(results, min_similarity, filter_mode)

    for file_path, chunks in grouped.items():
        # Sort by score for quick scanning (best matches first)
        # Tie-breaking: score desc → line asc → content lex
        chunks.sort(key=lambda c: (-c.score, c.start_line, c.content))

        # File header with chunk count (after filtering)
        chunk_word = "chunk" if len(chunks) == 1 else "chunks"
        console.print(f"\n{file_path} ({len(chunks)} {chunk_word}):")

        # One line per chunk
        # Format: :LINE_NUM  SCORE  PREVIEW
        for chunk in chunks:
            # Handle edge cases: empty content, whitespace-only, no newlines
            if not chunk.content or not chunk.content.strip():
                preview = "[empty chunk]"
            else:
                # Extract first line, handling all line ending types (\n, \r\n, \r)
                first_line = chunk.content.splitlines()[0] if chunk.content else ""
                # Edge case: splitlines() handles \n, \r\n, \r consistently
                # Strip leading whitespace for display (preserves readability)
                first_line = first_line.lstrip()
                # Truncate to 80 chars
                preview = first_line[:80]
                if len(first_line) > 80:
                    preview += '...'  # Truncation indicator
            console.print(f"  :{chunk.start_line}  {chunk.score:.2f}  {preview}")
```

**2. `src/gitctx/formatters/verbose.py`** (Code-reading format with best-match indicator)

Show ALL chunks per file, sorted by line order, with best-match indicator:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in verbose mode."""

    # Filter and group (base class does NOT sort chunks)
    min_similarity = kwargs.get('min_similarity', 0.5)
    filter_mode = kwargs.get('filter', 'head')
    grouped = self._filter_and_group(results, min_similarity, filter_mode)

    for file_path, chunks in grouped.items():
        # Identify best chunk for marker (3-level deterministic tie-breaking)
        # 1. Highest score (primary ranking)
        # 2. Earliest line number (definitions usually come first)
        # 3. Content lexicographic (edge case: same score + line)
        best_chunk = max(chunks, key=lambda c: (c.score, -c.start_line, c.content))

        # Sort by line order for natural reading
        # Tie-breaking: line asc → score desc → content lex
        chunks.sort(key=lambda c: (c.start_line, -c.score, c.content))

        # File header with chunk count (after filtering)
        chunk_word = "chunk" if len(chunks) == 1 else "chunks"
        console.print(f"\n[bold]{file_path}[/bold] ({len(chunks)} {chunk_word})")

        # Show ALL chunks with best-match indicator
        for chunk in chunks:
            if chunk == best_chunk:
                console.print(f"\n# ⭐ Lines {chunk.start_line}-{chunk.end_line} (score: {chunk.score:.2f}, best match)")
            else:
                console.print(f"\n# Lines {chunk.start_line}-{chunk.end_line} (score: {chunk.score:.2f})")

            # Apply syntax highlighting with fallback to plain text
            # _highlight_code() contract:
            # - language=None → detect from file extension or use "text"
            # - language unsupported → fall back to "text" lexer
            # - Pygments failure → return raw content (no highlighting)
            # - Always returns Rich Syntax object, never raises
            highlighted = self._highlight_code(chunk.content, chunk.language)
            console.print(highlighted)
```

**3. `src/gitctx/formatters/mcp.py`** (Programmatic format with score sorting)

Include all chunks in JSON structure, sorted by score:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in MCP mode."""

    # Filter and group (base class does NOT sort chunks)
    min_similarity = kwargs.get('min_similarity', 0.5)
    filter_mode = kwargs.get('filter', 'head')
    grouped = self._filter_and_group(results, min_similarity, filter_mode)

    output = []
    for file_path, chunks in grouped.items():
        # Sort by score for relevance ranking (consumers can re-sort by line_range)
        # Tie-breaking: score desc → line asc → content lex
        chunks.sort(key=lambda c: (-c.score, c.start_line, c.content))

        best_chunk = chunks[0]  # Highest score after sorting

        output.append({
            "file_path": file_path,
            "language": best_chunk.language,
            "best_score": best_chunk.score,
            "total_chunks": len(chunks),  # Count after filtering
            "chunks": [
                {
                    "content": chunk.content,
                    "line_range": [chunk.start_line, chunk.end_line],
                    "score": chunk.score,
                    "is_head": chunk.is_head,
                }
                for chunk in chunks  # Already sorted by score
            ],
        })

    console.print_json(data=output)
```

**4. `src/gitctx/formatters/base.py`** (NEW - pure data transformation)

Shared filtering and grouping logic. Does NOT sort chunks within files (formatters decide).

**Note**: Formatters use `chunk.score` property for cleaner code. The `.score` property will be added to SearchResult in TASK-0001.4.3.2, returning `hybrid_score` (preferred) or `vector_score` as fallback.

```python
from collections import defaultdict
from typing import Literal

from gitctx.indexing.types import SearchResult


class FormatterBase:
    """Base formatter with shared filtering and grouping logic.

    Design: Pure data transformation (filter + group). Does NOT sort chunks
    within files - each formatter decides its own presentation order.
    """

    def _filter_and_group(
        self,
        results: list[SearchResult],
        min_similarity: float = 0.5,
        filter_mode: Literal["head", "history", "all"] = "head"
    ) -> dict[str, list[SearchResult]]:
        """Filter and group results by file_path.

        Args:
            results: Flat list of search results
            min_similarity: Minimum similarity threshold (default 0.5, range -1.0 to 1.0)
            filter_mode: Which chunks to include (head/history/all, default head)

        Returns:
            Dict mapping file_path -> list of chunks (filtered, UNSORTED within each file)
            Files sorted by best chunk score (highest scoring file first)

        Note:
            Assumes valid inputs (validated at CLI layer). Invalid filter_mode will fail
            naturally on list comprehension.
        """
        # Filter by filter_mode (head/history/all)
        if filter_mode == "head":
            results = [r for r in results if r.is_head]
        elif filter_mode == "history":
            results = [r for r in results if not r.is_head]
        # "all" = no filtering

        grouped = defaultdict(list)

        # Group by file_path and filter by similarity
        # Use SearchResult.score property (returns hybrid_score or vector_score)
        for result in results:
            if result.score >= min_similarity:
                grouped[result.file_path].append(result)

        # Remove files with no chunks after filtering
        grouped = {k: v for k, v in grouped.items() if v}

        # Sort FILES by best chunk score (file-level ordering only)
        return dict(sorted(
            grouped.items(),
            key=lambda item: max(c.score for c in item[1]),
            reverse=True
        ))
```

### Implementation Strategy

1. **Create FormatterBase with filtering and grouping logic**
   - Shared `_filter_and_group()` method (pure data transformation)
   - Does NOT sort chunks within files (formatters decide)
   - All formatters inherit from FormatterBase

2. **Update TerseFormatter**
   - Sort chunks by score descending (best first)
   - One line per chunk: `:LINE_NUM  SCORE  PREVIEW`

3. **Update VerboseFormatter**
   - Identify best chunk: `max(chunks, key=lambda c: c.score)`
   - Sort chunks by line order (natural reading)
   - Mark best chunk with `# ⭐ ... (best match)`
   - Preserve syntax highlighting and existing output format

4. **Update MCPFormatter**
   - Sort chunks by score descending (relevance ranking)
   - Add file metadata: total_chunks, best_score

5. **Run BDD scenarios**
   - Verify grouping behavior across all formats
   - Verify format-specific chunk ordering (score vs line)
   - Verify best-match indicator in verbose
   - Verify --filter flag behavior (head/history/all)

**Inheritance Strategy**: Modify 3 existing formatter classes in-place to inherit from FormatterBase (single-level inheritance):
- `class TerseFormatter(FormatterBase)` in `src/gitctx/formatters/terse.py`
- `class VerboseFormatter(FormatterBase)` in `src/gitctx/formatters/verbose.py`
- `class MCPFormatter(FormatterBase)` in `src/gitctx/formatters/mcp.py`

Formatters remain drop-in compatible via `get_formatter()` factory (no breaking changes).

### Output Examples

**Terse Format:**
```text
src/auth/middleware.py (3 chunks):
  :15   0.95  class AuthMiddleware:
  :42   0.87  def process_request(self, request):
  :103  0.75  def validate_token(self, token):

src/auth/handlers.py (1 chunk):
  :42   0.87  def authenticate_user(username, password):
```

**Verbose Format:**
```text
src/auth/middleware.py (3 chunks)

# ⭐ Lines 15-25 (score: 0.95, best match)
class AuthMiddleware:
    def __init__(self):
        self.config = load_config()
        self.validators = []

# Lines 42-58 (score: 0.82)
    def process_request(self, request):
        return self.validate(request)

# Lines 103-115 (score: 0.75)
    def validate_token(self, token):
        return token in self.valid_tokens
```

*Note: Best-match indicator (⭐) from `SYMBOLS["best_match"]` in symbols.py*

**MCP Format:**
```json
[
  {
    "file_path": "src/auth/middleware.py",
    "language": "python",
    "best_score": 0.95,
    "total_chunks": 3,
    "chunks": [
      {
        "content": "class AuthMiddleware:\n    def __init__(self):\n        ...",
        "line_range": [15, 25],
        "score": 0.95,
        "is_head": true
      },
      ...
    ]
  }
]
```

## Pattern Reuse

### Existing Patterns:

1. **Formatter Architecture**
   - Pattern: `get_formatter(format_name)` factory (src/gitctx/formatters/__init__.py)
   - Reuse: Extend existing formatters (terse, verbose, mcp)
   - Minimal changes: Add grouping, preserve output style

2. **Rich Console Output**
   - Pattern: `console.print()` with Rich markup (existing formatters)
   - Reuse: Preserve syntax highlighting, colors, formatting
   - No changes: Existing Rich integration

3. **Pygments Syntax Highlighting**
   - Pattern: VerboseFormatter uses Pygments for code highlighting
   - Reuse: Apply to all chunks in verbose mode
   - No changes: Existing highlighting logic

### New Patterns Established:

1. **FormatterBase Class**
   - Pattern: Shared grouping logic via base class
   - Reusable: Future formatters (JSON, CSV, etc.)
   - Location: src/gitctx/formatters/base.py

2. **File-Grouped Results**
   - Pattern: Group chunks by file_path, sort by best chunk score
   - Reusable: Future result aggregation (file summaries, stats)
   - Algorithm: Best chunk determines file rank

## Dependencies

### Prerequisites:

- **STORY-0001.4.2** (Recency & Relevance Boosting) - Must Complete First ✋
  - File grouping uses boosted scores for ranking
  - Best chunk score determines file position
  - Cannot group correctly without final boosted scores

### Blocks:

**None** - Story 3 is a leaf node for search quality

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing formatter output | Medium | High | Extend formatters minimally, run all BDD scenarios |
| Chunk count indicator unclear | Low | Low | Use clear format: `(N chunks)` with colon for terse, without for verbose |
| Verbose mode showing all chunks provides low signal-to-noise (many chunks aren't relevant to query) | Medium | Medium | Acceptable for MVP - users want to see full code context without toggling between search results and files; EPIC-0001.5 can improve with relevance highlighting or LLM summarization of multiple chunks |
| MCP format JSON structure breaking clients | Low | Medium | Add `total_chunks` field (backward compatible addition) |
| File grouping breaks score ordering | Low | High | BDD scenario verifies best chunk score determines file rank |

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.4.3.1](TASK-0001.4.3.1.md) | Write 3 BDD Smoke Test Scenarios | 🔵 Not Started | 2 | 0/3 (all stubbed) |
| [TASK-0001.4.3.2](TASK-0001.4.3.2.md) | Create FormatterBase with _filter_and_group() (TDD + BDD steps) | 🔵 Not Started | 4 | 2/3 passing |
| [TASK-0001.4.3.3](TASK-0001.4.3.3.md) | Update TerseFormatter with Score Sorting (TDD - unit tests only) | 🔵 Not Started | 4 | 2/3 passing |
| [TASK-0001.4.3.4](TASK-0001.4.3.4.md) | Update VerboseFormatter with Line Order + Best-Match Indicator (TDD - unit tests only) | 🔵 Not Started | 3 | 2/3 passing |
| [TASK-0001.4.3.5](TASK-0001.4.3.5.md) | Update MCPFormatter with Score Sorting (TDD + final BDD integration) | 🔵 Not Started | 3 | 3/3 passing ✅ |

**Total Hours**: 16 (4 story points at 4h/point) - **24% faster than BDD-heavy approach**

**Testing Strategy:**
- **Unit tests** (20+ tests): Fast, deterministic validation of format strings, sorting, edge cases
- **BDD smoke tests** (3 scenarios): Integration testing of complete user workflow (index → search → format)

**BDD Progress Tracking:**
- TASK-1: 0/3 scenarios (smoke tests stubbed)
- TASK-2: 2/3 scenarios (file grouping + filtering smoke tests passing)
- TASK-3: 2/3 scenarios (unit tests added, BDD unchanged)
- TASK-4: 2/3 scenarios (unit tests added, BDD unchanged)
- TASK-5: 3/3 scenarios ✅ (format selection smoke test passing, ALL COMPLETE)

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
