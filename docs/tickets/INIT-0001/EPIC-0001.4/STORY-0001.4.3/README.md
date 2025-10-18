# STORY-0001.4.3: File-Grouped Result Presentation

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 5
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer reviewing search results
I want results grouped by file (not raw chunks)
So that I understand the file context and can see all relevant chunks from the same file together

## Acceptance Criteria

- [ ] Search results grouped by `file_path` before display
- [ ] Each file group shows: best chunk, file path, commit info, HEAD indicator
- [ ] Terse format shows: one line per file with chunk count indicator (e.g., "[3 chunks]")
- [ ] Verbose format shows: ALL chunks from each file with syntax highlighting
- [ ] MCP format includes: all chunks in JSON structure with file metadata
- [ ] File groups sorted by best chunk's boosted score (highest scoring chunk determines file rank)
- [ ] Minimal changes to existing formatters (extend, don't rewrite)

## BDD Scenarios

### Scenario: Results grouped by file path

```gherkin
Given a repository with files:
  | file_path         | chunks                                    |
  | src/auth.py       | ["class Auth", "def login", "def logout"] |
  | src/user.py       | ["class User", "def get_user"]            |
When I search for "authentication"
Then results should be grouped by file_path
And each group should show the file path once
```

### Scenario: Terse format shows chunk count

```gherkin
Given a search result with 3 chunks from "src/auth.py"
When I view results in terse format
Then output should include "[3 chunks]" indicator
And only the best-scoring chunk should be shown
```

### Scenario: Verbose format shows all chunks

```gherkin
Given a search result with 3 chunks from "src/auth.py"
When I view results in verbose format with --verbose
Then output should show all 3 chunks
And each chunk should have syntax highlighting
And chunks should be in score order (best first)
```

### Scenario: MCP format includes all chunks in JSON

```gherkin
Given a search result with 3 chunks from "src/auth.py"
When I view results in MCP format with --mcp
Then JSON should include all 3 chunks in "chunks" array
And each chunk should have: content, line_range, score
And file metadata should include: path, language, total_chunks
```

### Scenario: File groups sorted by best chunk score

```gherkin
Given search results:
  | file_path    | chunks         | best_score |
  | src/auth.py  | ["Auth", "..."] | 0.95      |
  | src/user.py  | ["User", "..."] | 0.85      |
When I view results
Then "src/auth.py" should appear before "src/user.py"
And files should be ordered by highest-scoring chunk
```

## Technical Design

### Components to Modify

**1. `src/gitctx/formatters/terse.py`** (Minimal changes)

Add chunk count indicator to output:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in terse mode."""

    # Group by file_path
    grouped = self._group_by_file(results)

    for file_path, chunks in grouped.items():
        best_chunk = chunks[0]  # Already sorted by score

        # Show chunk count if multiple chunks
        chunk_indicator = f"[{len(chunks)} chunks]" if len(chunks) > 1 else ""

        # Existing terse format + chunk indicator
        console.print(
            f"{file_path}:{best_chunk.start_line} "
            f"(score: {best_chunk.score:.2f}) {chunk_indicator}"
        )
        console.print(f"  {best_chunk.content[:100]}...")
```

**2. `src/gitctx/formatters/verbose.py`** (Minimal changes)

Show ALL chunks per file:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in verbose mode."""

    # Group by file_path
    grouped = self._group_by_file(results)

    for file_path, chunks in grouped.items():
        # File header
        console.print(f"\n[bold]{file_path}[/bold] ({len(chunks)} chunks)")

        # Show ALL chunks (not just best)
        for chunk in chunks:
            console.print(f"\nLines {chunk.start_line}-{chunk.end_line} (score: {chunk.score:.2f})")
            # Syntax highlighting using existing Pygments integration
            highlighted = self._highlight_code(chunk.content, chunk.language)
            console.print(highlighted)
```

**3. `src/gitctx/formatters/mcp.py`** (Minimal changes)

Include all chunks in JSON structure:

```python
def format(self, results: list[SearchResult], console: Console, **kwargs) -> None:
    """Format grouped results in MCP mode."""

    # Group by file_path
    grouped = self._group_by_file(results)

    output = []
    for file_path, chunks in grouped.items():
        best_chunk = chunks[0]

        output.append({
            "file_path": file_path,
            "language": best_chunk.language,
            "best_score": best_chunk.score,
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "content": chunk.content,
                    "line_range": [chunk.start_line, chunk.end_line],
                    "score": chunk.score,
                    "is_head": chunk.is_head,
                }
                for chunk in chunks
            ],
        })

    console.print_json(data=output)
```

**4. `src/gitctx/formatters/base.py`** (NEW helper)

Shared grouping logic for all formatters:

```python
from collections import defaultdict
from gitctx.indexing.types import SearchResult


class FormatterBase:
    """Base formatter with shared grouping logic."""

    def _group_by_file(self, results: list[SearchResult]) -> dict[str, list[SearchResult]]:
        """Group results by file_path, sorted by score within each group.

        Args:
            results: Flat list of search results (already sorted by boosted score)

        Returns:
            Dict mapping file_path -> list of chunks (sorted by score, best first)
        """
        grouped = defaultdict(list)

        for result in results:
            grouped[result.file_path].append(result)

        # Sort chunks within each file by score (descending)
        for file_path in grouped:
            grouped[file_path].sort(key=lambda r: r.score, reverse=True)

        # Return as dict sorted by best chunk score (file ranking)
        return dict(sorted(
            grouped.items(),
            key=lambda item: item[1][0].score,  # Best chunk score
            reverse=True
        ))
```

### Implementation Strategy

1. **Create FormatterBase with grouping logic**
   - Shared `_group_by_file()` method
   - All formatters inherit from FormatterBase

2. **Update TerseFormatter**
   - Add chunk count indicator: `[N chunks]`
   - Show only best chunk per file (existing behavior)

3. **Update VerboseFormatter**
   - Show ALL chunks per file (not just best)
   - Preserve syntax highlighting and existing output format

4. **Update MCPFormatter**
   - Include all chunks in JSON `chunks` array
   - Add file metadata: total_chunks, best_score

5. **Run BDD scenarios**
   - Verify grouping behavior across all formats
   - Verify chunk counts and ordering

**Inheritance Strategy**: Modify 3 existing formatter classes in-place to inherit from FormatterBase (single-level inheritance):
- `class TerseFormatter(FormatterBase)` in `src/gitctx/formatters/terse.py`
- `class VerboseFormatter(FormatterBase)` in `src/gitctx/formatters/verbose.py`
- `class MCPFormatter(FormatterBase)` in `src/gitctx/formatters/mcp.py`

Formatters remain drop-in compatible via `get_formatter()` factory (no breaking changes).

### Output Examples

**Terse Format:**
```
src/auth/middleware.py:15 (score: 0.95) [3 chunks]
  class AuthMiddleware:

src/auth/handlers.py:42 (score: 0.87)
  def authenticate_user(username, password):
```

**Verbose Format:**
```
src/auth/middleware.py (3 chunks)

Lines 15-25 (score: 0.95)
class AuthMiddleware:
    def __init__(self):
        ...

Lines 42-58 (score: 0.82)
    def process_request(self, request):
        ...

Lines 103-115 (score: 0.75)
    def validate_token(self, token):
        ...
```

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
| Chunk count indicator unclear | Low | Low | Use clear format: `[N chunks]`, consistent with CLI conventions |
| Verbose mode showing all chunks provides low signal-to-noise (many chunks aren't relevant to query) | Medium | Medium | Acceptable for MVP - users requested comprehensive view; EPIC-0001.5 can improve with relevance highlighting or LLM summarization of multiple chunks |
| MCP format JSON structure breaking clients | Low | Medium | Add `total_chunks` field (backward compatible addition) |
| File grouping breaks score ordering | Low | High | BDD scenario verifies best chunk score determines file rank |

## Tasks

**Note:** Full task breakdown will be created via `/plan-story STORY-0001.4.3`

Estimated tasks:
1. Write BDD scenarios for file grouping (5 scenarios above)
2. Create FormatterBase with grouping logic (TDD)
3. Update TerseFormatter with chunk count (TDD)
4. Update VerboseFormatter to show all chunks (TDD)
5. Update MCPFormatter with chunk array (TDD)
6. Integration testing and BDD verification

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
