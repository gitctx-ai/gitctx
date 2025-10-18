# STORY-0001.5.2: Indexing Performance Optimization

**Parent Epic**: [EPIC-0001.5](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 8
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a developer
I want fast indexing (>100 files/sec)
So that I can quickly index large codebases without long wait times

## Acceptance Criteria

- [ ] Baseline performance measured for all indexing components (chunking, embedding, storage)
- [ ] Indexing throughput exceeds 100 files/second for typical repositories (10K LoC)
- [ ] Time-to-index under 100 seconds for 10K file repository
- [ ] Peak memory usage under 2GB during indexing
- [ ] ChunkerProtocol optimized (parallel processing, if applicable)
- [ ] EmbedderProtocol optimized (batching, rate limiting, caching strategies)
- [ ] VectorStoreProtocol optimized (bulk inserts, IVF-PQ index tuning)
- [ ] Performance tests pass with @pytest.mark.performance marker
- [ ] Regression detection enabled in CI

## Dependencies

**Prerequisites:**
- STORY-0001.5.1 (Infrastructure) - ⚠️ MUST COMPLETE FIRST (needs ProtocolBenchmark framework)
- EPIC-0001.2 (Indexing) - Complete ✅ (provides implementation to optimize)

**Blocks:**
- STORY-0001.5.3 (Search Performance) - ⚠️ CRITICAL DEPENDENCY (search testing needs fast indexing for test data generation)

## Technical Notes

- Current indexing speed: "quite poor" per observation during EPIC-0001.3 planning
- Profile hot paths first: chunking vs embedding vs storage (identify bottleneck)
- Embedding likely bottleneck (OpenAI API rate limits):
  - Current: Sequential embedding calls
  - Optimization: Batch embedding (up to 100 texts per API call)
  - Caching: Reuse embeddings for identical content across commits
- Storage optimization:
  - Bulk inserts instead of individual writes
  - IVF-PQ index created after bulk load (not incremental)
- Chunking optimization:
  - Parallel processing if I/O bound
  - Measure first - may not be bottleneck

## Tasks

**Note:** Full task breakdown via `/plan-story STORY-0001.5.2`

Estimated tasks:
1. Measure baseline performance (all components)
2. Profile indexing pipeline to identify bottleneck
3. Optimize EmbedderProtocol (batching, caching)
4. Optimize VectorStoreProtocol (bulk inserts)
5. Optimize ChunkerProtocol (if needed)
6. Verify performance targets met
7. Add regression tests

---

**Created**: 2025-10-14
**Last Updated**: 2025-10-14
