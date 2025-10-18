# EPIC-0001.5: Performance & Observability

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🔵 Not Started
**Estimated**: 21 story points
**Progress**: ░░░░░░░░░░ 0% (0/21 points complete)

## Overview

**Post-MVP Optimization Epic**: After EPIC-0001.4 delivers search quality and basic usability, this epic focuses on performance optimization and observability infrastructure. Key insight from EPIC-0001.4: *"The core problem isn't search performance (speed) - it's search relevance (quality)."* This epic addresses speed AFTER quality is proven.

**Technical Debt from EPIC-0001.4**: The RelevanceBooster algorithm implemented in STORY-0001.4.2 uses simple HEAD-only boost (2x multiplier) for MVP speed. This epic MUST evaluate two alternative approaches:

1. **Sophisticated Bucketing**: Bucket results by hybrid score, apply smooth recency decay within buckets (prevents recency from overriding relevance). See STORY-0001.4.2 planning notes for detailed algorithm.

2. **LLM Reranking** (RECOMMENDED): Use GPT-4o-mini to rerank results based on query intent and task context. Pattern: hybrid search retrieves top 20 → LLM reranks based on query-specific relevance (prioritizes tests/docs for "how does X work", prioritizes implementation for "add feature Y", etc.). Pros: Query-aware intelligence, no hand-crafted heuristics, aligns with "precisely the right context" vision. Cons: Adds latency (~500ms-2s), cost (~$0.001-0.01/query), non-deterministic. **Action**: STORY-0001.5.4 (LangSmith Evals) should compare SimpleBooster vs LLMReranker using canonical queries, measure relevance/latency/cost, make data-driven decision on default approach.

## Goals

- Establish protocol performance testing infrastructure
- Optimize indexing performance for large repositories (>10K files)
- Optimize search performance for sub-second queries
- Add LangSmith integration for prompt evaluation and observability

## Child Stories

| ID | Title | Status | Points | Priority |
|----|-------|--------|--------|----------|
| [STORY-0001.5.1](STORY-0001.5.1/README.md) | Protocol Performance Testing Infrastructure | 🔵 Not Started | 3 | **MEDIUM** |
| [STORY-0001.5.2](STORY-0001.5.2/README.md) | Indexing Performance Optimization | 🔵 Not Started | 8 | **MEDIUM** |
| [STORY-0001.5.3](STORY-0001.5.3/README.md) | Search Performance Optimization | 🔵 Not Started | 5 | **MEDIUM** |
| [STORY-0001.5.4](STORY-0001.5.4/README.md) | LangSmith Integration & Prompt Evals | 🔵 Not Started | 5 | **LOW** |

## Dependencies

### Prerequisites

- **EPIC-0001.4** (Search Quality & Performance) - Must Complete First ✋
  - Provides hybrid search, recency boosting, file grouping, compression, TUI
  - Establishes baseline search quality to optimize
  - Implements protocol-based architecture to test

### Story Dependencies

All stories in this epic depend on EPIC-0001.4 completion.

## Success Criteria

### 1. Performance Targets

| Metric | Current (estimated) | Target | Improvement |
|--------|---------------------|--------|-------------|
| Indexing speed | ~50 files/min | 200+ files/min | **4x faster** |
| Search latency | ~2 seconds | <500ms | **4x faster** |
| Memory usage | ~500MB | <300MB | **40% reduction** |

### 2. Observability

- [ ] Protocol performance metrics tracked
- [ ] LangSmith integration functional
- [ ] Prompt evaluation framework established
- [ ] Performance regressions detected in CI

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Premature optimization | Low | Medium | Wait for EPIC-0001.4 completion + user feedback |
| Complexity without benefit | Medium | High | Measure before/after, only optimize bottlenecks |
| Testing infrastructure overhead | Low | Low | Reuse existing patterns, keep simple |

## Notes

### Origin

Created during EPIC-0001.4 planning to separate search quality (MVP blocker) from performance optimization (post-MVP enhancement).

### Design Decisions

1. **Quality First**: EPIC-0001.4 must complete before this epic starts
2. **Measure, Then Optimize**: Establish baselines before optimization
3. **Protocol-Driven**: Leverage existing protocol architecture for testing

---

**Created**: 2025-10-16
**Last Updated**: 2025-10-16
