# EPIC-0001.4: Performance Optimization & Observability

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🔵 Not Started
**Estimated**: 21 story points
**Progress**: ░░░░░░░░░░ 0% (0/21 points complete)

## Overview

Establish protocol-based performance testing infrastructure and optimize indexing and search pipelines. This epic emerged from the recognition that "any protocol deserves performance monitoring" and the discovery that search performance optimization is blocked by slow indexing speed.

## Goals

- Create reusable protocol-based performance testing framework
- Optimize indexing pipeline to >100 files/sec for typical repositories
- Achieve search p95 latency <2.0 seconds for realistic codebases
- Ensure memory usage <500MB for large vector indexes (100K+ vectors)
- Establish LangSmith integration for prompt performance evaluation
- Enable performance regression detection in CI

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-0001.4.1](STORY-0001.4.1/README.md) | Protocol Performance Testing Infrastructure | 🔵 Not Started | 3 |
| [STORY-0001.4.2](STORY-0001.4.2/README.md) | Indexing Performance Optimization | 🔵 Not Started | 8 |
| [STORY-0001.4.3](STORY-0001.4.3/README.md) | Search Performance Optimization | 🔵 Not Started | 5 |
| [STORY-0001.4.4](STORY-0001.4.4/README.md) | LangSmith Integration & Prompt Evals | 🔵 Not Started | 5 |

**Planning Status**: Epic outline created. Stories need full planning via `/plan-story STORY-ID`.

## BDD Specifications

```gherkin
# High-level epic scenarios (detailed scenarios in story READMEs)

Feature: Performance Optimization
  As a developer
  I want fast indexing and search
  So that I can efficiently work with large codebases

  Background:
    Given a realistic repository with 10,000 files and 1M LoC

  Scenario: Fast indexing
    When I run "gitctx index"
    Then indexing should complete in under 100 seconds
    And throughput should exceed 100 files/second

  Scenario: Fast search
    Given an indexed repository
    When I run "gitctx search 'authentication middleware'" 100 times
    Then p95 latency should be under 2.0 seconds
    And all queries should complete within 5.0 seconds

  Scenario: Memory efficiency
    Given an indexed repository with 100K chunks
    When I run "gitctx search 'database'"
    Then peak memory usage should be under 500MB

  Scenario: Performance regression detection
    Given performance baselines established
    When CI runs on a new commit
    Then performance tests should detect >10% regressions
    And CI should fail if critical thresholds exceeded
```

## Technical Design

### Protocol-Based Performance Testing Architecture

```python
# Created in STORY-0001.4.1: tests/performance/protocol_benchmarks.py

from abc import abstractmethod
from typing import Protocol, TypeVar, Generic
import time
import psutil
from dataclasses import dataclass

T = TypeVar('T', bound=Protocol)

@dataclass
class PerformanceResult:
    """Performance measurement result."""
    metric_name: str
    value: float
    unit: str
    baseline: float
    target: float
    passed: bool

class ProtocolBenchmark(Generic[T]):
    """Base class for protocol performance testing."""

    protocol: type[T]
    metric: str  # e.g., "tokens_per_second", "files_per_second", "query_latency_p95"
    baseline: float  # Current performance
    target: float  # Goal performance

    @abstractmethod
    def setup(self) -> dict:
        """Setup test environment and return context."""
        pass

    @abstractmethod
    def measure(self, implementation: T, context: dict) -> float:
        """Measure performance of protocol implementation."""
        pass

    def run(self, implementation: T) -> PerformanceResult:
        """Run benchmark and return results."""
        context = self.setup()
        value = self.measure(implementation, context)
        passed = value >= self.target

        return PerformanceResult(
            metric_name=self.metric,
            value=value,
            unit=self._get_unit(),
            baseline=self.baseline,
            target=self.target,
            passed=passed
        )

# Usage in STORY-0001.4.2 (Indexing)
class ChunkerBenchmark(ProtocolBenchmark[ChunkerProtocol]):
    protocol = ChunkerProtocol
    metric = "tokens_per_second"
    baseline = 50000  # Current measured performance
    target = 100000  # 2x improvement goal

# Usage in STORY-0001.4.3 (Search)
class SearchBenchmark(ProtocolBenchmark[VectorStoreProtocol]):
    protocol = VectorStoreProtocol
    metric = "query_latency_p95"
    baseline = 3.5  # Current p95 (seconds)
    target = 2.0  # Goal p95 (seconds)
```

### Performance Optimization Priority

**Story Implementation Order (STRICT SEQUENCE):**

1. **STORY-0001.4.1** - Infrastructure ← Build framework first
2. **STORY-0001.4.2** - Indexing ← CRITICAL: Unblocks search testing
3. **STORY-0001.4.3** - Search ← Now has fast indexing for test data
4. **STORY-0001.4.4** - LangSmith ← Future AI features

**Why this order:**
- Indexing must be fast before search performance can be tested
- Search performance testing requires creating large (10K+) chunk indexes
- Currently "quite poor" indexing speed makes search perf tests impractical
- Infrastructure (STORY-0001.4.1) provides shared patterns for both

## Dependencies

### Prerequisites

- **EPIC-0001.2** (Real Indexing Implementation) - Complete ✅
  - Provides ChunkerProtocol, EmbedderProtocol, VectorStoreProtocol implementations
  - Without this, no performance to optimize

- **EPIC-0001.3** (Vector Search Implementation) - Complete ✅
  - Provides search functionality and basic performance infrastructure
  - TASK-0001.3.2.4 created @pytest.mark.performance pattern
  - Without this, no search performance to optimize

### Story Dependencies

- **STORY-0001.4.2** depends on STORY-0001.4.1 (needs ProtocolBenchmark framework)
- **STORY-0001.4.3** depends on STORY-0001.4.1 (needs framework) AND STORY-0001.4.2 (needs fast indexing)
- **STORY-0001.4.4** depends on STORY-0001.4.1 (needs framework)

### Package Dependencies

All existing in pyproject.toml:
- `pytest` - Testing framework
- `pytest-benchmark` - Performance benchmarking (may need to add)
- `memory-profiler` - Memory profiling
- `numpy` - Statistical calculations (percentiles)
- `psutil` - System resource monitoring
- `langsmith` - Prompt evals (STORY-0001.4.4, may need to add)

## Success Criteria

1. **Indexing Performance** - Measured with ProtocolBenchmark:
   - Throughput: >100 files/sec for typical repo (10K LoC)
   - Time-to-index: <100 seconds for 10K file repo
   - Memory: <2GB peak during indexing
   - Verification: `pytest -m performance tests/performance/test_indexing.py`

2. **Search Performance** - Measured with existing @performance tests:
   - p95 latency: <2.0 seconds for 10K chunk index
   - p99 latency: <5.0 seconds
   - Memory: <500MB for 100K vector index
   - Verification: `pytest -m performance tests/e2e/test_search_performance.py`

3. **Performance Infrastructure** - Reusable patterns:
   - ProtocolBenchmark base class for all protocols
   - GitHub Actions artifact archiving (performance trends over time)
   - Regression detection (fail CI if >10% slower)
   - Documentation: Performance testing guide

4. **LangSmith Integration** - Prompt quality measurement:
   - Eval metrics defined (accuracy, relevance, cost, latency)
   - Baseline measurements established
   - CI integration for regression detection
   - Documentation: Eval development workflow

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Indexing optimization insufficient | Medium | High | Profile hot paths first (chunking vs embedding vs storage), optimize biggest bottleneck |
| Search optimization blocked too long | Medium | Medium | Complete STORY-0001.4.2 first (strict dependency), use fast indexing for test data |
| Performance tests too slow for CI | Low | Medium | Use VCR cassettes (zero API cost), separate performance workflow (TASK-0001.3.2.4 pattern) |
| Memory profiling unreliable | Low | Low | Use `memory_profiler` + `psutil`, run multiple iterations, take median |
| LangSmith costs | Low | Medium | Use eval caching, limit eval frequency, budget alerts |

## Notes

- This epic emerged from `/plan-epic EPIC-0001.3` gap analysis
- Key insight: "Any protocol deserves performance monitoring"
- Indexing speed currently "quite poor" - blocks search performance testing
- Performance testing infrastructure (TASK-0001.3.2.4) provides foundation
- Protocol-based architecture enables systematic performance optimization
- LangSmith integration prepares for future AI features (RAG, code generation, etc.)

---

**Created**: 2025-10-14
**Last Updated**: 2025-10-14 (Epic outline created during EPIC-0001.3 gap analysis)
