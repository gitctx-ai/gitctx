# STORY-0001.4.1: Hybrid Search with Protocol Design

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 3
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer searching for code
I want both keyword and semantic search capabilities
So that I can find exact matches (class names, functions) AND conceptually related code in a single query

## Acceptance Criteria

- [ ] LanceDB hybrid search enabled with RRF (Reciprocal Rank Fusion) combining BM25 + vector scores
- [ ] SearchStrategy protocol created for storage-agnostic search interface
- [ ] LanceDBStore implements SearchStrategy protocol with hybrid search
- [ ] Search results include both keyword matches (BM25) and semantic matches (vector)
- [ ] RRF normalization constant k=60 (LanceDB default, proven effective)
- [ ] Existing vector-only search replaced with hybrid search (no feature flag needed)
- [ ] All existing search BDD scenarios pass with hybrid search

## BDD Scenarios

### Scenario: Hybrid search finds exact keyword matches

```gherkin
Given a repository with files:
  | file_path              | content                          |
  | src/auth/middleware.py | class AuthMiddleware             |
  | src/auth/handlers.py   | def authenticate_user            |
When I search for "AuthMiddleware"
Then the first result should be "src/auth/middleware.py"
And the result should have BM25 score > 0.7 (keyword match)
```

### Scenario: Hybrid search finds semantic matches

```gherkin
Given a repository with files:
  | file_path              | content                          |
  | src/auth/middleware.py | class AuthMiddleware             |
  | src/auth/handlers.py   | def authenticate_user            |
When I search for "user authentication logic"
Then results should include both "middleware.py" and "handlers.py"
And results should have vector scores > 0.7 (semantic match)
```

### Scenario: Hybrid search combines keyword and semantic ranking

```gherkin
Given a repository with files:
  | file_path              | content                               |
  | src/auth/jwt.py        | class JWTAuthMiddleware               |
  | src/auth/oauth.py      | class OAuthMiddleware                 |
  | docs/auth_guide.md     | Authentication middleware overview    |
When I search for "JWT auth middleware class"
Then "src/auth/jwt.py" should rank first (keyword + semantic match)
And "src/auth/oauth.py" should rank second (semantic match)
And "docs/auth_guide.md" should rank lower (partial semantic match)
```

## Technical Design

### Components to Create

**1. `src/gitctx/storage/protocols.py`** (NEW SearchStrategy protocol)

```python
from typing import Protocol
import numpy as np
from gitctx.indexing.types import SearchResult

class SearchStrategy(Protocol):
    """Protocol for vector search implementations (storage-agnostic)."""

    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        filter_head_only: bool = False,
        max_distance: float = 1.0,
    ) -> list[SearchResult]:
        """Execute search and return ranked results.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results to return
            filter_head_only: If True, only return HEAD chunks
            max_distance: Maximum cosine distance (1.0 - min_similarity)

        Returns:
            List of SearchResult objects, ranked by relevance
        """
        ...

**Note:** Protocol intentionally minimal - no lifecycle methods (initialize/close) needed. LanceDBStore manages its own connection lifecycle via existing __init__/table property.
```

**2. `src/gitctx/storage/lancedb_store.py`** (Modify existing)

Update `search()` method to use hybrid query:

```python
def search(
    self,
    query_vector: np.ndarray,
    query_text: str,
    limit: int = 10,
    filter_head_only: bool = False,
    max_distance: float = 1.0,
) -> list[SearchResult]:
    """Hybrid search using BM25 + vector with RRF fusion."""
    from lancedb import rerankers

    # LanceDB hybrid query with RRF
    rrf = rerankers.RRFReranker(K=60, return_score="all")
    results = (
        self.table.search(query_type="hybrid")
        .vector(query_vector)
        .text(query_text)  # Text query required for BM25
        .limit(limit)
        .rerank(rrf)  # Apply RRF reranking
        .to_list()
    )

    # Post-filter by distance (LanceDB limitation - see issue #745)
    filtered = [r for r in results if r["_distance"] <= max_distance]

    # Convert to SearchResult objects
    return [self._to_search_result(r) for r in filtered]
```

**3. `src/gitctx/indexing/types.py`** (Extend SearchResult)

Add fields for BM25/vector score breakdown:

```python
@dataclass
class SearchResult:
    # ... existing fields (chunk_content, file_path, distance, commit_sha, etc.) ...

    # Score breakdown fields (added in STORY-0001.4.1)
    bm25_score: float | None = None  # BM25 keyword score from _score field
    vector_score: float | None = None  # Cosine similarity: 1.0 - _distance
    hybrid_score: float | None = None  # RRF combined score from _relevance_score field
```

### Implementation Strategy

1. **Create SearchStrategy protocol** (src/gitctx/storage/protocols.py)
   - Define storage-agnostic search interface
   - Document protocol contract

2. **Update LanceDBStore to implement protocol**
   - Change `.search(query_type="vector")` → `.search(query_type="hybrid")`
   - Add RRF reranking with k=60
   - Add score breakdown to SearchResult objects

3. **Update search command** (src/gitctx/cli/search.py)
   - No changes needed - uses LanceDBStore.search() interface
   - Hybrid search happens transparently

4. **Run existing BDD scenarios**
   - All scenarios should pass (better results, same interface)

### LanceDB Hybrid Search Reference

From LanceDB docs (https://lancedb.github.io/lancedb/hybrid_search/hybrid_search/):
- `query_type="hybrid"` combines BM25 + vector
- RRF reranking: `rerankers.RRFReranker(K=60, return_score="all")`
- RRF constant K=60 is default (proven effective, no tuning needed)
- Post-filtering for distance threshold: https://github.com/lancedb/lancedb/issues/745
- FTS performance: ~470 QPS on 130K documents (prrao87/lancedb-study benchmark on M2 MacBook Pro)

**Response Fields (validated 2025-10-17):**
- `_distance`: Cosine distance from vector search (float, 0-∞, lower = more similar)
- `_score`: BM25 score from full-text search (float or None, higher = better match)
- `_relevance_score`: RRF combined relevance score (float, 0-1, higher = more relevant)

## Pattern Reuse

### Existing Patterns:

1. **Protocol-based Architecture**
   - Pattern: ChunkerProtocol, EmbedderProtocol (src/gitctx/indexing/protocols.py, src/gitctx/models/protocols.py)
   - Reuse: Create SearchStrategy protocol for storage abstraction
   - Enables: Future storage backends (Qdrant, Pinecone) without breaking changes

2. **SearchResult Dataclass**
   - Pattern: CodeChunk, Embedding dataclasses (src/gitctx/indexing/types.py)
   - Reuse: Extend SearchResult with score breakdown fields
   - Maintains: Type safety and IDE autocomplete

3. **LanceDB Integration**
   - Pattern: Existing LanceDBStore (src/gitctx/storage/lancedb_store.py)
   - Reuse: Modify existing search() method
   - Changes: query_type parameter, add rerank() call

### New Patterns Established:

1. **SearchStrategy Protocol**
   - Pattern: Storage-agnostic search interface
   - Reusable: Future search strategies (filtered search, faceted search)
   - Location: src/gitctx/storage/protocols.py

2. **RRF Score Normalization**
   - Pattern: Hybrid search with configurable RRF constant
   - Reusable: Future ranking algorithms (LLM reranking in EPIC-0001.5)
   - Default: k=60 (LanceDB recommendation)

## Dependencies

### Prerequisites:

**None** - Story 1 can start immediately
- Hybrid search is independent of other stories
- Changes are localized to LanceDBStore
- No breaking changes to search CLI or pipeline

### Blocks:

- **STORY-0001.4.2** (Recency & Relevance Boosting) - Needs hybrid scores for post-RRF boosting
- **STORY-0001.4.3** (File-Grouped Results) - Uses search results from hybrid search

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| BM25 requires full-text index creation | Low | Medium | LanceDB creates BM25 index automatically on first hybrid query |
| Hybrid search slower than vector-only | Low | Low | LanceDB optimizes hybrid queries, benchmark on 10K+ file repos |
| RRF k=60 not optimal for code search | Low | Medium | Use LanceDB default (k=60), defer tuning to EPIC-0001.5 (LangSmith evals) |
| Post-filtering affects ranking quality | Medium | Low | Acceptable tradeoff (LanceDB limitation), revisit if users report issues |
| Breaking existing search behavior | Low | High | Run all BDD scenarios, verify results quality equal or better |

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.4.1.1](TASK-0001.4.1.1.md) | Write BDD Scenarios for Hybrid Search | 🔵 Not Started | 2-3 | 0/3 (stubbed) |
| [TASK-0001.4.1.2](TASK-0001.4.1.2.md) | SearchStrategy Protocol and SearchResult Extension | 🔵 Not Started | 3-4 | 0/3 → 1/3 |
| [TASK-0001.4.1.3](TASK-0001.4.1.3.md) | Hybrid Search Implementation in LanceDBStore | 🔵 Not Started | 4-5 | 1/3 → 3/3 |
| [TASK-0001.4.1.4](TASK-0001.4.1.4.md) | Integration Testing and Regression Verification | 🔵 Not Started | 2-3 | 3/3 maintained |

**Total Hours**: 11-15 hours (story: 3 points × 4h/point = 12h ✓)

**Incremental BDD Tracking:**
- TASK-1: 0/3 scenarios (all stubbed, all failing 🔴)
- TASK-2: 1/3 scenarios (protocol + basic checks 🟡)
- TASK-3: 3/3 scenarios (hybrid search complete ✅)
- TASK-4: 3/3 scenarios + regression tests (maintain ✅)

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
