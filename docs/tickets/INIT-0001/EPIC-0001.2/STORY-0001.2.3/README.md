# STORY-0001.2.3: OpenAI Embedding Generation

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 5
**Progress**: ░░░░░░░░░░ 0% (0/5 tasks complete)

## User Story

As the indexing system (serving developers and AI agents)
I want to generate embeddings for code chunks using OpenAI's text-embedding-3-large model
So that chunks can be semantically searched with high-quality vector representations while tracking costs accurately

## Acceptance Criteria

- [ ] Generate embeddings using OpenAI text-embedding-3-large model (3072 dimensions)
- [ ] Batch chunk requests to maximize throughput (up to 2048 chunks per API call)
- [ ] Track token usage and API costs per chunk and in aggregate
- [ ] Handle API errors gracefully (rate limits, network errors, invalid requests)
- [ ] Implement exponential backoff retry logic for transient failures
- [ ] Cache embeddings by blob SHA to avoid re-computing unchanged content
- [ ] Support async/await for concurrent embedding generation
- [ ] Validate embedding dimensions match expected model output (3072)
- [ ] Log progress (chunks embedded, tokens used, estimated cost)
- [ ] Read API key from GitCtxSettings with proper validation

## BDD Scenarios

See full story file for 10 detailed BDD scenarios covering:
- Basic embedding generation
- Batch processing
- API error handling (rate limits, network errors)
- Caching by blob SHA
- Cost tracking and validation
- Dimension validation
- Progress logging

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.2.3.1](TASK-0001.2.3.1.md) | Define EmbedderProtocol and embedding dataclasses | 🔵 | 2 |
| [TASK-0001.2.3.2](TASK-0001.2.3.2.md) | Implement OpenAIEmbedder with batching and retry logic | 🔵 | 6 |
| [TASK-0001.2.3.3](TASK-0001.2.3.3.md) | Integrate EmbeddingCache for blob-based caching | 🔵 | 3 |
| [TASK-0001.2.3.4](TASK-0001.2.3.4.md) | BDD scenarios and integration tests | 🔵 | 4 |
| [TASK-0001.2.3.5](TASK-0001.2.3.5.md) | Unit tests with mock API responses | 🔵 | 5 |

**Total**: 20 hours = 5 story points

## Technical Design

Uses AsyncOpenAI with batching, exponential backoff, and blob-based caching.
Reuses existing EmbeddingCache from prototype.
Cost: $0.13 per 1M tokens (text-embedding-3-large).

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
