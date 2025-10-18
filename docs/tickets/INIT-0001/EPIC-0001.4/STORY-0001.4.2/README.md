# STORY-0001.4.2: Recency & Relevance Boosting

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 3
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer searching for code
I want current HEAD code to rank higher than historical versions
So that I see the most up-to-date implementation first (not deprecated code from old commits)

## Acceptance Criteria

- [ ] GitHeadBooster class created with HEAD-only boost (1.5x multiplier - mid-range of typical BM25 boost factors 1.2-2.0 per Robertson & Zaragoza 2009, 'The Probabilistic Relevance Framework: BM25 and Beyond', sufficient to break ties without overriding strong semantic matches per Scenario 2, can increase to 2.0x based on EPIC-0001.5 evaluation data)
- [ ] Boost applied AFTER hybrid search RRF ranking (post-processing)
- [ ] HEAD chunks identified by `is_head=True` flag in search results
- [ ] Search results ordered by: `boosted_score = hybrid_score * (1.5 if is_head else 1.0)`
- [ ] BDD scenarios verify HEAD code ranks above historical code for same semantic match
- [ ] No hand-crafted heuristics beyond HEAD boost (defer sophisticated ranking to EPIC-0001.5)

## BDD Scenarios

### Scenario: HEAD code ranks higher than historical code

```gherkin
Given a repository with files at different commits:
  | file_path           | content              | is_head |
  | src/auth/current.py | class AuthMiddleware | true    |
  | src/auth/old.py     | class OldAuth        | false   |
When I search for "auth"
Then "src/auth/current.py" should rank above "src/auth/old.py"
And HEAD results should have 1.5x boost applied
```

### Scenario: Boost applies to hybrid scores, not absolute ranking

```gherkin
Given a repository with files:
  | file_path           | content                    | is_head | hybrid_score |
  | src/auth/current.py | def authenticate           | true    | 0.6          |
  | src/auth/old.py     | class AuthenticationSystem | false   | 0.95         |
When I search for "authentication system"
Then "src/auth/old.py" should rank first (0.95 > 0.6 * 1.5 = 0.9)
And boost does not override semantic relevance
```

### Scenario: Equal semantic matches prefer HEAD code

```gherkin
Given a repository with files:
  | file_path           | content              | is_head | hybrid_score |
  | src/auth/current.py | class AuthMiddleware | true    | 0.8          |
  | src/auth/old.py     | class AuthMiddleware | false   | 0.8          |
When I search for "AuthMiddleware"
Then "src/auth/current.py" should rank first (0.8 * 1.5 = 1.2 > 0.8)
And HEAD boost breaks ties
```

## Technical Design

### Components to Create

**1. `src/gitctx/search/boosting.py`** (NEW)

```python
"""Search result boosting algorithms."""

from dataclasses import replace
from gitctx.indexing.types import SearchResult


class GitHeadBooster:
    """Boost HEAD code over historical versions.

    Simple MVP approach: Apply 1.5x multiplier to HEAD chunks post-RRF.
    Defers sophisticated ranking (recency decay, LLM reranking) to EPIC-0001.5.

    Design rationale:
    - HEAD code is usually more relevant (current implementation)
    - 1.5x is conservative (doesn't override strong semantic matches)
    - Post-RRF ensures hybrid scores are normalized before boosting
    - Simple to understand, test, and reason about

    Future improvements (EPIC-0001.5):
    - Sophisticated bucketing with recency decay (see EPIC-0001.5 README)
    - LLM reranking based on query intent (recommended approach)
    """

    def __init__(self, head_multiplier: float = 1.5):
        """Initialize booster.

        Args:
            head_multiplier: Boost multiplier for HEAD chunks (default: 1.5x)
        """
        self.head_multiplier = head_multiplier

    def boost(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply HEAD boost and re-sort by boosted scores.

        Args:
            results: Search results from hybrid search (post-RRF)

        Returns:
            Results re-sorted by boosted scores
        """
        # Apply boost to HEAD chunks
        boosted = []
        for result in results:
            if result.is_head:
                boosted_score = result.score * self.head_multiplier
                boosted.append(replace(result, score=boosted_score))
            else:
                boosted.append(result)

        # Re-sort by boosted scores (descending)
        return sorted(boosted, key=lambda r: r.score, reverse=True)
```

**2. `src/gitctx/storage/lancedb_store.py`** (Modify existing)

Integrate GitHeadBooster into search pipeline:

```python
from gitctx.search.boosting import GitHeadBooster

class LanceDBStore:
    def __init__(self, db_path: Path):
        # ... existing init ...
        self.booster = GitHeadBooster(head_multiplier=1.5)

    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        filter_head_only: bool = False,
        max_distance: float = 1.0,
    ) -> list[SearchResult]:
        """Hybrid search with HEAD boosting."""

        # 1. Hybrid search with RRF (from STORY-0001.4.1)
        results = self._hybrid_search(query_vector, limit, max_distance)

        # 2. Apply HEAD boost (post-RRF)
        boosted_results = self.booster.boost(results)

        # 3. Apply filter_head_only if requested
        if filter_head_only:
            boosted_results = [r for r in boosted_results if r.is_head]

        return boosted_results[:limit]  # Respect limit after boosting
```

### Implementation Strategy

1. **Create GitHeadBooster class** (src/gitctx/search/boosting.py)
   - Simple multiplier-based boosting
   - Post-RRF application (preserves hybrid score normalization)
   - Configurable multiplier (default: 1.5x)

2. **Integrate into LanceDBStore** (src/gitctx/storage/lancedb_store.py)
   - Instantiate booster in `__init__`
   - Apply boost after hybrid search, before filter_head_only
   - Re-sort by boosted scores

3. **Add boosted_score to SearchResult** (src/gitctx/indexing/types.py)
   - Track original hybrid_score and final boosted score
   - Useful for debugging and future LLM reranking

4. **Run BDD scenarios**
   - Verify HEAD code ranks higher for equal semantic matches
   - Verify boost doesn't override strong semantic matches

### Design Decision: Simple HEAD-Only Boost

**Why not recency decay or completeness boost?**

During planning, we researched sophisticated ranking algorithms:
- **Recency decay**: Boost recent commits (<90 days) with smooth decay
- **Completeness boost**: Boost 1-chunk files (complete context)
- **LLM reranking**: Use GPT-4o-mini to rerank based on query intent

**Decision**: Use simple HEAD-only boost (1.5x) for MVP
- **Rationale**:
  - Data-driven decisions require evaluation infrastructure (EPIC-0001.5)
  - Hand-crafted heuristics are hard to justify without user feedback
  - Simple approach is easier to reason about and debug
  - LLM reranking is superior long-term solution (query-aware intelligence)

**Future work (EPIC-0001.5)**:
- Build LangSmith evaluation framework (STORY-0001.5.4)
- Compare SimpleBooster vs LLMReranker using canonical queries
- Measure relevance, latency, cost tradeoffs
- Make data-driven decision on default ranking approach

See EPIC-0001.5 README for detailed discussion of deferred ranking improvements.

## Pattern Reuse

### Existing Patterns:

1. **Dataclass Replacement**
   - Pattern: `from dataclasses import replace`
   - Reuse: Create new SearchResult with boosted score
   - Maintains: Immutability and type safety

2. **SearchResult Sorting**
   - Pattern: `sorted(results, key=lambda r: r.score, reverse=True)`
   - Reuse: Re-sort after applying boost
   - Standard: Python sorting for search results

3. **Post-Processing Pipeline**
   - Pattern: Search → Filter → Sort (existing LanceDBStore)
   - Reuse: Insert boost between search and filter
   - Maintains: Clean pipeline architecture

### New Patterns Established:

1. **Booster Class Pattern**
   - Pattern: Standalone boosting algorithm class
   - Reusable: Future boosters (RecencyDecayBooster, LLMReranker)
   - Location: src/gitctx/search/boosting.py

2. **Score Preservation**
   - Pattern: Store both hybrid_score and final score in SearchResult
   - Reusable: Debugging, A/B testing, LLM reranking evaluation
   - Enables: Transparent score evolution tracking

## Dependencies

### Prerequisites:

- **STORY-0001.4.1** (Hybrid Search) - Must Complete First ✋
  - Provides hybrid_score from RRF normalization
  - Boosting applies to hybrid scores, not raw vector distances
  - Cannot boost without normalized scores

### Blocks:

- **STORY-0001.4.3** (File-Grouped Results) - Uses boosted search results

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 1.5x multiplier too aggressive (ranks HEAD above better historical matches) | Medium | Low | 1.5x is conservative (mid-range of 1.2-2.0 from BM25 literature); BDD scenario verifies high-scoring historical code (0.95) still beats low-scoring HEAD (0.6 * 1.5 = 0.9) |
| 1.5x multiplier too weak | Medium | Low | Easy to increase to 2.0x if 3+ users report HEAD code ranking too low (trackable via GitHub issues) |
| HEAD boost overrides semantic relevance | Low | Medium | BDD scenario verifies high-scoring historical code still ranks well |
| Simple boost insufficient for production | Low | High | Documented as MVP approach, EPIC-0001.5 evaluates LLM reranking |
| Breaking search quality for existing queries | Low | High | Run all existing BDD scenarios, verify equal or better results |

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|-----------------|
| [TASK-0001.4.2.1](TASK-0001.4.2.1.md) | Write BDD Scenarios for HEAD Boosting | 🔵 Not Started | 2 | 0/3 (stubbed) |
| [TASK-0001.4.2.2](TASK-0001.4.2.2.md) | Create GitHeadBooster Class with TDD | 🔵 Not Started | 3-4 | 0/3 → 1/3 |
| [TASK-0001.4.2.3](TASK-0001.4.2.3.md) | Integrate GitHeadBooster into LanceDBStore | 🔵 Not Started | 3-4 | 1/3 → 3/3 |
| [TASK-0001.4.2.4](TASK-0001.4.2.4.md) | Integration Testing and Story Completion | 🔵 Not Started | 2-3 | 3/3 maintained |

**Total Hours**: 10-13 hours (story: 3 points × 4h/point = 12h ✓)

**Incremental BDD Tracking:**
- TASK-1: 0/3 scenarios (all stubbed, all failing 🔴)
- TASK-2: 1/3 scenarios (basic boost applied 🟡)
- TASK-3: 3/3 scenarios (all HEAD boosting complete ✅)
- TASK-4: 3/3 scenarios + 6 edge cases (maintain ✅)

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
