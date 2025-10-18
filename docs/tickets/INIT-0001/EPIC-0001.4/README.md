# EPIC-0001.4: Search Quality & Performance

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🟡 In Progress
**Estimated**: 18 story points
**Progress**: ░░░░░░░░░░ 0% (0/18 points complete)

## Overview

**MVP Viability Epic**: Current search results are insufficient for production use - pure vector search misses exact keyword matches, results are presented as raw chunks rather than files, and historical code ranks equally with current code. This epic makes gitctx viable by implementing hybrid search (BM25 + vector), recency boosting, file-grouped results, compressed embeddings, and essential TUI usability improvements.

**Key Insight from Research**: The core problem isn't search performance (speed) - it's search relevance (quality). Users need to find the RIGHT code, not just find code FAST.

## Goals

- Enable hybrid search (BM25 + vector) for both keyword and semantic matching
- Boost HEAD code 1.5x over historical versions (recency matters, conservative multiplier)
- Present results as files (not raw chunks) for better context
- Compress embedding cache with zstd (~8% additional size reduction over safetensors, minimal overhead for long-term benefit)
- Improve TUI responsiveness from batch updates (up to 120s freezes) to real-time streaming (<100ms updates) with accurate ETA and throughput metrics
- Maintain protocol-based architecture (storage-agnostic search)

## Story Mapping

This epic delivers 5 focused stories, each addressing a specific MVP viability gap:

| # | Story Title | Points | Epic Goal Addressed | Dependencies |
|---|-------------|--------|---------------------|--------------|
| 1 | Hybrid Search with Protocol Design | 3 | Enable BM25 + vector search | None (start immediately) |
| 2 | Recency & Relevance Boosting | 3 | Boost HEAD code 2x | Story 1 (extends hybrid) |
| 3 | File-Grouped Result Presentation | 5 | Present results as files | Story 2 (uses boosted scores) |
| 4 | Safetensors Compression with zstd | 2 | Compress cache 2-3x | None (parallel with Story 1) |
| 5 | TUI Performance & Usability | 5 | Improve indexing UX | None (independent) |

**Total**: 18 points

**Implementation Strategy**:
- **Week 1**: Stories 1 + 4 in parallel (independent, no blocking)
- **Week 2**: Stories 2 → 3 sequentially (Story 3 depends on Story 2)
- **Week 3**: Story 5 (TUI improvements after core search quality complete)

## Child Stories

| ID | Title | Status | Points | Priority |
|----|-------|--------|--------|----------|
| [STORY-0001.4.1](STORY-0001.4.1/README.md) | Hybrid Search with Protocol Design | 🔵 Not Started | 3 | **CRITICAL** |
| [STORY-0001.4.2](STORY-0001.4.2/README.md) | Recency & Relevance Boosting | 🔵 Not Started | 3 | **HIGH** |
| [STORY-0001.4.3](STORY-0001.4.3/README.md) | File-Grouped Result Presentation | 🔵 Not Started | 5 | **HIGH** |
| [STORY-0001.4.4](STORY-0001.4.4/README.md) | Safetensors Compression with zstd | 🔵 Not Started | 2 | **MEDIUM** |
| [STORY-0001.4.5](STORY-0001.4.5/README.md) | TUI Performance & Usability | 🔵 Not Started | 5 | **MEDIUM** |

**Total**: 18 story points

## BDD Specifications

```gherkin
# High-level epic scenarios mapped to stories (detailed scenarios in story READMEs)

Feature: Search Quality & Usability
  As a developer searching for code
  I want accurate, relevant results with good UX
  So that I can find the RIGHT code quickly and understand context

  Background:
    Given a repository with authentication code:
      | file | content | is_head |
      | src/auth/middleware.py | class AuthMiddleware | true |
      | src/auth/handlers.py | def authenticate_user | true |
      | src/old/auth_v1.py | class OldAuth | false |
    And the repository is indexed with hybrid search enabled

  # Story 1: Hybrid Search with Protocol Design
  Scenario: Hybrid search finds keywords AND concepts
    When I search for "AuthMiddleware"
    Then the first result should be "src/auth/middleware.py" (exact keyword match via BM25)
    When I search for "user authentication logic"
    Then results should include both middleware.py and handlers.py (semantic match via vector)
    When I search for "JWT auth middleware class"
    Then results should combine keyword + semantic ranking via RRF

  # Story 2: Recency & Relevance Boosting
  Scenario: Current code ranks higher than historical
    When I search for "auth"
    Then "src/auth/middleware.py" (HEAD) should rank above "src/old/auth_v1.py"
    And HEAD results should have 2x relevance boost applied post-RRF
    And recent commits (<90 days) should have 1.2x boost
    And complete files (1 chunk) should have 1.3x boost

  # Story 3: File-Grouped Result Presentation
  Scenario: Results grouped by file with metadata
    When I search for "authentication"
    Then results should be grouped by file_path (not raw chunks)
    And each file should show: best chunk, total chunks, HEAD status, relevance score
    And output should display "[3 chunks]" for files with multiple matches
    And terse/verbose/mcp output formats should all use file grouping

  # Story 4: Safetensors Compression with zstd
  Scenario: Embedding cache compressed efficiently
    When I run "gitctx index" on 100 files
    Then embedding cache should be compressed with zstd level 3
    And cache size should be <5MB (vs ~12MB uncompressed safetensors, ~60MB JSON)
    And .safetensors.zst files should be committed to git
    And decompression should be transparent on read

  # Story 5: TUI Performance & Usability
  Scenario: Progress indicators show accurate, real-time updates
    When I run "gitctx index" on 500 files
    Then progress bar should update in real-time (not just at end)
    And ETA should be accurate within 20% after first 10 files
    And throughput (files/sec) should be displayed
    And indexing should feel responsive (<100ms UI updates)
```

## Technical Design

This section maps technical components to the 5 planned stories.

### Story 1: Storage-Agnostic Search Protocol + Hybrid Search

**Key Design Principle**: Search strategy decoupled from storage backend (LanceDB today, Qdrant/Pinecone/Weaviate tomorrow).

**Components to implement:**
1. `SearchStrategy` protocol in `src/gitctx/search/protocols.py`
2. `LanceDBHybridSearch` implementation in `src/gitctx/search/strategies/lance_hybrid.py`
3. Reciprocal Rank Fusion (RRF) merge logic

```python
# In src/gitctx/search/protocols.py
from typing import Protocol, Any

class SearchStrategy(Protocol):
    """Protocol for search strategies (storage-agnostic)."""

    def search(
        self,
        query_text: str,
        query_vector: list[float],  # From our cache!
        limit: int,
        params: dict[str, Any],     # Generic params
    ) -> list[dict[str, Any]]:
        """Execute search and return ranked results."""
        ...

# In src/gitctx/search/strategies/lance_hybrid.py
class LanceDBHybridSearch:
    """Hybrid search for LanceDB."""

    def __init__(self, table):  # LanceDB-specific injected here
        self.table = table

    def search(self, query_text, query_vector, limit, params):
        # Use LanceDB explicit API (preserves our caching)
        return self.table.search(query_type="hybrid") \
            .vector(query_vector) \  # Our cached embedding
            .text(query_text) \       # For FTS/BM25
            .limit(limit * 2).to_list()  # Get more for RRF merge
```

**Hybrid Search Flow:**

1. **Vector search**: Semantic similarity using cached query embeddings
2. **BM25/FTS**: Keyword matching on chunk_content
3. **Merge**: RRF combines rankings from both paths
4. **Boost**: Custom recency/relevance multipliers (Story 2)

**Why explicit API (.vector() + .text())?**
- ✅ Preserves our query embedding cache (QueryEmbedder from EPIC-0001.3)
- ✅ Cost control (we track OpenAI API calls)
- ✅ Offline capability (cached embeddings work without API)
- ❌ Simple API auto-generates embeddings (bypasses cache, expensive)

**Files to create/modify:**
- Create: `src/gitctx/search/protocols.py` (SearchStrategy protocol)
- Create: `src/gitctx/search/strategies/lance_hybrid.py` (LanceDBHybridSearch)
- Modify: `src/gitctx/search/query_embedder.py` (integrate with hybrid search)

### Story 2: Recency & Relevance Boosting

**Post-RRF boost multipliers:**

| Factor | Condition | Multiplier | Rationale |
|--------|-----------|------------|-----------|
| HEAD status | `is_head == true` | 1.5x | Current code most relevant (conservative boost, defers tuning to EPIC-0001.5) |
| Recent commit | `<90 days old` | 1.2x | Fresh code > stale code |
| Complete file | `total_chunks == 1` | 1.3x | Whole units > fragments |

**Combined boost example**: HEAD single-chunk file = 2.0 × 1.3 = **2.6x boost**

**Components to implement:**
1. `RecencyBooster` class in `src/gitctx/search/boosters.py`
2. Integration with hybrid search results (post-RRF)
3. Boost configuration in `IndexSettings`

**Files to create/modify:**
- Create: `src/gitctx/search/boosters.py` (RecencyBooster class)
- Modify: `src/gitctx/search/strategies/lance_hybrid.py` (apply boosting)
- Modify: `src/gitctx/config/models.py` (add boost config if needed)

### Story 3: File-Grouped Result Presentation

**Problem**: Raw chunks lack context ("what file is this from? how many matches?")

**Solution**: Group by `file_path`, show best chunk per file + metadata

**Components to implement:**
1. `FileResult` dataclass in `src/gitctx/search/results.py`
2. `group_chunks_by_file()` function
3. Update CLI output formatters (terse, verbose, MCP)

```python
# In src/gitctx/search/results.py
@dataclass
class FileResult:
    file_path: str
    best_chunk: dict      # Highest scored chunk
    all_chunks: list[dict]  # All matching chunks
    chunk_count: int       # len(all_chunks)
    relevance_score: float  # Best chunk's boosted score
    is_head: bool          # From best chunk metadata

def group_chunks_by_file(chunks: list[dict]) -> list[FileResult]:
    """Group chunks by file_path, track best chunk, sort by score."""
    # Group by file_path
    # Select best chunk per file (highest relevance_score)
    # Sort files by best chunk score descending
    # Return list[FileResult]
```

**Files to create/modify:**
- Create: `src/gitctx/search/results.py` (FileResult, grouping logic)
- Modify: `src/gitctx/cli/commands/search.py` (use FileResult)
- Modify: `src/gitctx/cli/output/formatters.py` (all formats use file grouping)

### Story 4: Safetensors Compression with zstd

**Current**: Safetensors (5x smaller than JSON)
**Proposed**: Safetensors + zstd (15x smaller than JSON)

**Components to implement:**
1. Compression wrapper for safetensors save/load
2. Update `EmbeddingCache` to use `.safetensors.zst` format
3. Add `zstandard` package dependency

**File format**: `.safetensors.zst`
**Compression level**: 3 (balance speed/size)
**Transparency**: Automatic decompression on read

**Files to modify:**
- Modify: `src/gitctx/indexing/embedding_cache.py` (add zstd compression)
- Modify: `pyproject.toml` (add zstandard dependency)

### Story 5: TUI Performance & Usability

**Problem**: Current progress indicators may not update in real-time, making indexing feel unresponsive

**Solution**: Refactor to use Rich.Progress with proper task tracking and streaming updates

**Components to implement:**
1. Real-time progress updates during indexing
2. Accurate ETA calculation (based on rolling average)
3. Throughput display (files/sec, chunks/sec)
4. Responsive UI updates (<100ms)

**Files to create/modify:**
- Create: `src/gitctx/cli/progress.py` (centralized progress tracking)
- Modify: `src/gitctx/cli/commands/index.py` (use new progress system)
- Modify: `src/gitctx/indexing/indexer.py` (emit progress events)

## Dependencies

### Prerequisites

- **EPIC-0001.2** (Real Indexing Implementation) - Complete ✅
  - Provides LanguageAwareChunker, OpenAIEmbedder, EmbeddingCache
  - Already stores `chunk_content` (needed for FTS)
  - Already stores `is_head` flag (needed for recency boosting)

- **EPIC-0001.3** (Vector Search Implementation) - Complete ✅
  - Provides LanceDBStore, QueryEmbedder (with caching!)
  - Existing query embedding cache critical for explicit hybrid API
  - Current vector-only search to be extended with FTS

### Story Dependencies

- **Hybrid Search** - No dependencies, can start immediately
- **Recency Boosting** - Depends on Hybrid Search (extends reranking)
- **File Grouping** - Depends on Recency Boosting (uses boosted scores)
- **Compression** - No dependencies, can run in parallel with Hybrid Search
- **TUI Performance** - Independent, scheduled after core search quality

**Parallel execution possible**: Hybrid Search + Compression simultaneously (Week 1)

### Package Dependencies

**Existing** (already in pyproject.toml):
- `lancedb` - Vector database with hybrid search support
- `openai` - Embeddings (query cache)
- `safetensors` - Embedding storage format

**New additions required**:
- `zstandard` - zstd compression for safetensors (STORY-0001.4.4)

## Success Criteria

Mapped to the 5 planned stories:

### Story 1: Hybrid Search with Protocol Design

- [ ] SearchStrategy protocol defined in `src/gitctx/search/protocols.py`
- [ ] LanceDBHybridSearch implements SearchStrategy
- [ ] Hybrid search combines BM25 + vector via RRF
- [ ] Query "AuthMiddleware" returns exact match as top result
- [ ] Query "authentication logic" returns semantic matches
- [ ] Query embedding cache still used (explicit API, zero cost increase)
- [ ] All existing search tests pass + new hybrid tests

### Story 2: Recency & Relevance Boosting

- [ ] RecencyBooster class implemented in `src/gitctx/search/boosters.py`
- [ ] HEAD code boosted 2.0x
- [ ] Recent commits (<90 days) boosted 1.2x
- [ ] Complete files (1 chunk) boosted 1.3x
- [ ] Query "auth" ranks HEAD files above historical
- [ ] Boost configuration documented

### Story 3: File-Grouped Result Presentation

- [ ] FileResult dataclass defined in `src/gitctx/search/results.py`
- [ ] group_chunks_by_file() function implemented
- [ ] Results grouped by file_path (not raw chunks)
- [ ] Each file shows: best chunk, chunk count, HEAD status, score
- [ ] "[X chunks]" indicator in all output formats
- [ ] Terse/Verbose/MCP formatters updated
- [ ] All output tests pass

### Story 4: Safetensors Compression with zstd

- [ ] zstandard dependency added to pyproject.toml
- [ ] EmbeddingCache uses `.safetensors.zst` format
- [ ] Compression level 3 (speed/size balance)
- [ ] Decompression transparent on read
- [ ] Cache size <5MB for 100 files (vs 12MB uncompressed)
- [ ] 3x compression improvement over safetensors alone
- [ ] Backward compatibility with existing .safetensors files

### Story 5: TUI Performance & Usability

- [ ] Centralized progress tracking in `src/gitctx/cli/progress.py`
- [ ] Real-time progress updates during indexing
- [ ] ETA accurate within 20% after first 10 files
- [ ] Throughput display (files/sec, chunks/sec)
- [ ] UI updates <100ms (feels responsive)
- [ ] Progress bar updates continuously (not just at end)
- [ ] Indexing 500 files shows smooth, accurate progress

### Overall Epic Success

**Search Quality (Primary Goal):**

Track improvement on canonical queries:

| Query | Current | After EPIC-0001.4 | Story |
|-------|---------|-------------------|-------|
| "AuthMiddleware" | Misses or ranks low | ✅ Top result (BM25 exact match) | Story 1 |
| "authentication logic" | OK semantic | ✅ Excellent (hybrid) | Story 1 |
| "JWT middleware class" | Poor | ✅ Excellent (hybrid + boost) | Stories 1+2 |
| Recent vs old code | Same rank | ✅ HEAD ranks 1.5x higher | Story 2 |
| Multiple file matches | Raw chunks | ✅ Grouped by file | Story 3 |

**Current Baseline**: ~50% of keyword queries miss exact matches (pure vector search limitation)
**Target**: 90%+ of queries show most relevant file in top 3 results (hybrid search + boosting)

**Storage Efficiency:**

| Metric | Before | After | Story |
|--------|--------|-------|-------|
| Cache size (100 files) | 12 MB | 4 MB | Story 4 |
| Compression ratio | 5x (vs JSON) | 15x (vs JSON) | Story 4 |
| Git repo size impact | Baseline | -67% cache | Story 4 |

**User Experience:**

| Metric | Before | After | Story |
|--------|--------|-------|-------|
| Progress updates | Batch/delayed | Real-time | Story 5 |
| ETA accuracy | Unknown | Within 20% | Story 5 |
| Indexing feels | Unresponsive | Responsive | Story 5 |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FTS index creation slow on large repos | Low | Medium | Profile first; LanceDB FTS is fast (26ms queries) |
| Boosting weights suboptimal | Medium | Medium | Start conservative (2x, 1.2x, 1.3x); tune based on feedback |
| File grouping confuses users | Low | Medium | Clear "[X chunks]" indicator; good documentation |
| Compression overhead | Low | Low | zstd level 3 is fast (~5MB/s); negligible impact |
| Query cache invalidation | Low | Low | Explicit API preserves cache; no breaking changes |

## Notes

### Origin & Evolution

This epic emerged from deep research into search relevance problems:

- **Problem discovered**: Pure vector search misses exact keyword matches ("AuthMiddleware" class)
- **Root cause**: Blob-only indexing + vector-only search + no recency bias + raw chunk output
- **Research**: Analyzed competitors (Sourcegraph, GitHub, MCP servers), academic papers (cAST, hybrid search)
- **Key insight**: Search QUALITY matters more than search SPEED for MVP viability
- **Scope evolution**: Originally "Performance & Observability" with 26 points across 6 stories
  - Rewritten 2025-10-14: Focus shifted from speed to quality based on MVP research
  - Split 2025-10-16: Performance/observability work moved to EPIC-0001.5 (21 points)
  - Final scope: 5 stories (18 points) focused on search quality + basic usability

### Design Decisions

1. **No AST parsing**: Too complex for 1-person OSS; Langchain splitters sufficient
2. **Hybrid search mandatory**: Not optional, not configurable - it's just how search works
3. **Explicit vector API**: Preserves our query embedding cache (critical for cost/offline)
4. **Protocol-based**: Storage-agnostic design (LanceDB today, others tomorrow)
5. **Embeddings committed**: Cache in git (design principle #4), only db/ gitignored
6. **TUI in scope**: Basic usability (progress indicators) is MVP-critical, but speed optimization deferred
7. **5-story breakdown**: Each story is independently testable and delivers user-visible value

### Related Epics

- **[EPIC-0001.5](../EPIC-0001.5/README.md)**: Performance & Observability (21 points) - Post-MVP optimization of indexing/search speed and LangSmith integration

---

**Created**: 2025-10-14
**Last Updated**: 2025-10-16
**Changelog**:
- 2025-10-14: Initial creation with performance focus
- 2025-10-14: Complete rewrite → Search Quality focus based on MVP research
- 2025-10-16: Scope clarification - Split performance work to EPIC-0001.5, added TUI usability (Story 5), detailed story mapping and technical design
