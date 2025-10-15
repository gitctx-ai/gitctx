# STORY-0001.4.3: Search Performance Optimization

**Parent Epic**: [EPIC-0001.4](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 5
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer
I want search results in under 2 seconds (p95)
So that I can quickly find relevant code without waiting

## Acceptance Criteria

- [ ] p95 search latency under 2.0 seconds for 10K chunk index
- [ ] p99 search latency under 5.0 seconds
- [ ] Peak memory usage under 500MB for 100K vector index
- [ ] LanceDB IVF-PQ index tuning applied (optimal nlist, nprobes values)
- [ ] Query embedding caching implemented (avoid redundant API calls)
- [ ] Cold cache vs warm cache scenarios tested
- [ ] Performance tests expanded beyond TASK-0001.3.2.4 baseline
- [ ] Memory profiling with @profile decorator + mprof plot
- [ ] Regression detection enabled in CI

## Dependencies

**Prerequisites:**
- STORY-0001.4.1 (Infrastructure) - ⚠️ MUST COMPLETE FIRST (needs ProtocolBenchmark framework)
- STORY-0001.4.2 (Indexing Performance) - ⚠️ CRITICAL DEPENDENCY (search testing needs fast indexing for test data generation)
- EPIC-0001.3 (Search) - Complete ✅ (provides implementation to optimize)
- TASK-0001.3.2.4 - Complete ✅ (provides baseline performance test)

**Notes:**
- Originally planned as STORY-0001.3.4 in EPIC-0001.3
- Moved to EPIC-0001.4 due to indexing speed dependency
- Cannot create 10K chunk test repos efficiently until indexing optimized

## Technical Notes

- Deferred from STORY-0001.3.2 (see line 16, 46-49 in STORY-0001.3.2 README)
- Performance test infrastructure exists (TASK-0001.3.2.4):
  - @pytest.mark.performance marker
  - .github/workflows/performance.yml
  - VCR cassettes for zero-cost CI
- Optimization areas:
  - LanceDB IVF-PQ tuning (nlist = sqrt(N), nprobes = 10-20% of nlist)
  - Query embedding caching (avoid repeated OpenAI API calls for same query)
  - Result set size optimization (limit parameter tuning)
  - Memory profiling with memory_profiler

## Tasks

**Note:** Full task breakdown via `/plan-story STORY-0001.4.3`

Estimated tasks:
1. Expand performance tests (cold/warm cache scenarios)
2. Tune LanceDB IVF-PQ parameters (nlist, nprobes)
3. Implement query embedding caching
4. Memory profiling (<500MB for 100K vectors)
5. Verify p95 <2.0s target met
6. Add regression tests

---

**Created**: 2025-10-14
**Last Updated**: 2025-10-14
