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

```gherkin
Feature: OpenAI Embedding Generation

  Scenario: Generate embedding for single chunk
    Given a code chunk with 200 tokens
    And OpenAI API key is configured in GitCtxSettings
    When I generate an embedding for the chunk
    Then I should receive a 3072-dimensional vector
    And the API should report 200 tokens used
    And the cost should be $0.000026 (200 tokens * $0.13/1M)

  Scenario: Batch process multiple chunks efficiently
    Given 500 code chunks from a repository
    And max batch size is 2048 chunks
    When I generate embeddings with batching enabled
    Then chunks should be batched into 1 API call
    And all 500 embeddings should be 3072 dimensions
    And total API calls should be 1 (not 500)
    And processing time should be <5 seconds

  Scenario: Handle rate limit errors with exponential backoff
    Given the OpenAI API is returning 429 rate limit errors
    And exponential backoff is configured (base delay: 1s, max retries: 5)
    When I attempt to generate embeddings
    Then the system should retry with delays: 1s, 2s, 4s, 8s, 16s
    And eventually succeed when rate limit clears
    And log each retry attempt with timestamp

  Scenario: Handle network errors gracefully
    Given the OpenAI API is unreachable (network error)
    When I attempt to generate embeddings
    Then the system should retry up to 5 times with exponential backoff
    And if all retries fail, raise a clear NetworkError
    And log the error with context (chunk count, blob SHA)

  Scenario: Cache embeddings by blob SHA
    Given a blob with SHA "abc123" was previously embedded
    And the embedding is cached in EmbeddingCache
    When I request an embedding for SHA "abc123"
    Then the cached embedding should be returned
    And no API call should be made
    And the cache hit should be logged

  Scenario: Generate new embeddings for uncached blobs
    Given a blob with SHA "def456" is not in the cache
    When I request an embedding for SHA "def456"
    Then an API call should be made to OpenAI
    And the embedding should be stored in the cache with key "def456"
    And the cache miss should be logged

  Scenario: Validate embedding dimensions
    Given an embedding is generated from the API
    When I validate the embedding
    Then it should have exactly 3072 dimensions
    And if dimensions don't match, raise DimensionMismatchError
    And log the error with expected vs actual dimensions

  Scenario: Track API costs accurately
    Given I embed 10,000 chunks totaling 2,000,000 tokens
    When I review the cost tracking
    Then total cost should be $0.26 (2M tokens * $0.13/1M)
    And cost should be tracked per chunk
    And aggregate cost should be logged

  Scenario: Log progress during batch processing
    Given 1000 chunks to embed
    When I generate embeddings with progress logging enabled
    Then progress should be logged every 100 chunks
    And logs should include: chunks processed, tokens used, estimated cost
    And final log should show totals

  Scenario: Validate API key on initialization
    Given GitCtxSettings has no OpenAI API key configured
    When I attempt to initialize the OpenAIEmbedder
    Then a ConfigurationError should be raised
    And the error message should indicate missing API key
    And suggest how to configure the key
```

## Child Tasks

**BDD/TDD Workflow**: BDD scenarios first, implement incrementally with each task, all scenarios pass at end

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.2.3.1](TASK-0001.2.3.1.md) | Write BDD scenarios for embedding generation | 🔵 | 2 | 0/10 scenarios (all failing) |
| [TASK-0001.2.3.2](TASK-0001.2.3.2.md) | Define EmbedderProtocol and embedding dataclasses (with tests) | 🔵 | 3 | 1/10 scenarios passing |
| [TASK-0001.2.3.3](TASK-0001.2.3.3.md) | Implement OpenAIEmbedder with batching and retry logic (TDD) and BDD scenarios | 🔵 | 10 | 7/10 scenarios passing |
| [TASK-0001.2.3.4](TASK-0001.2.3.4.md) | Integration with EmbeddingCache, configuration, and final BDD scenarios | 🔵 | 5 | 10/10 scenarios passing ✅ |

**Total**: 20 hours = 5 story points

## Technical Design

### Protocol-Based Design

Follow protocol-based design pattern for future Rust optimization:

```python
# src/gitctx/core/protocols.py (extend existing)

@dataclass
class Embedding:
    """Represents an embedding vector with metadata.

    Design notes:
    - Simple dataclass for FFI compatibility
    - All fields use primitive types (list[float], not numpy arrays)
    """
    vector: list[float]      # 3072-dimensional embedding
    token_count: int         # Tokens used to generate embedding
    model: str              # Model name (e.g., "text-embedding-3-large")
    cost_usd: float         # Cost in USD for this embedding
    blob_sha: str           # SHA of the blob this embedding represents
    chunk_index: int        # Index of chunk within blob


class EmbedderProtocol(Protocol):
    """Protocol for embedding generation - can be fulfilled by Python or Rust."""

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
        blob_sha: str
    ) -> list[Embedding]:
        """Generate embeddings for code chunks.

        Args:
            chunks: List of code chunks to embed
            blob_sha: SHA of the blob these chunks came from

        Returns:
            List of Embedding objects with vectors and metadata
        """
        ...

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost in USD for embedding token_count tokens."""
        ...
```

### OpenAI API Integration

Use AsyncOpenAI client with batching for maximum throughput:

```python
# src/gitctx/embeddings/openai_embedder.py

from openai import AsyncOpenAI
import asyncio
from typing import List

class OpenAIEmbedder(EmbedderProtocol):
    """OpenAI embedding generator with batching and retry logic.

    Implementation notes:
    - Uses text-embedding-3-large model (3072 dimensions, $0.13/1M tokens)
    - Batches up to 2048 chunks per API call for efficiency
    - Implements exponential backoff for rate limits and network errors
    - Validates embedding dimensions to catch API changes
    """

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 3072
    COST_PER_MILLION_TOKENS = 0.13  # USD
    MAX_BATCH_SIZE = 2048  # OpenAI API limit

    def __init__(self, api_key: str, max_retries: int = 5, base_delay: float = 1.0):
        """Initialize the embedder.

        Args:
            api_key: OpenAI API key
            max_retries: Maximum retry attempts for transient failures
            base_delay: Base delay in seconds for exponential backoff
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
        blob_sha: str
    ) -> list[Embedding]:
        """Generate embeddings for chunks with batching and retry logic."""
        embeddings = []

        # Process in batches of MAX_BATCH_SIZE
        for i in range(0, len(chunks), self.MAX_BATCH_SIZE):
            batch = chunks[i:i + self.MAX_BATCH_SIZE]
            batch_embeddings = await self._embed_batch_with_retry(batch, blob_sha)
            embeddings.extend(batch_embeddings)

        return embeddings

    async def _embed_batch_with_retry(
        self,
        chunks: list[CodeChunk],
        blob_sha: str
    ) -> list[Embedding]:
        """Embed a batch with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await self._embed_batch(chunks, blob_sha)
            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
            except NetworkError:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Network error, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

    async def _embed_batch(
        self,
        chunks: list[CodeChunk],
        blob_sha: str
    ) -> list[Embedding]:
        """Embed a single batch (no retry logic)."""
        # Extract chunk content
        texts = [chunk.content for chunk in chunks]

        # Call OpenAI API
        response = await self.client.embeddings.create(
            input=texts,
            model=self.MODEL,
            dimensions=self.DIMENSIONS
        )

        # Validate and convert to Embedding objects
        embeddings = []
        for idx, (chunk, embedding_data) in enumerate(zip(chunks, response.data)):
            # Validate dimensions
            if len(embedding_data.embedding) != self.DIMENSIONS:
                raise DimensionMismatchError(
                    f"Expected {self.DIMENSIONS} dimensions, got {len(embedding_data.embedding)}"
                )

            embeddings.append(Embedding(
                vector=embedding_data.embedding,
                token_count=chunk.token_count,
                model=self.MODEL,
                cost_usd=self.estimate_cost(chunk.token_count),
                blob_sha=blob_sha,
                chunk_index=chunk.metadata["chunk_index"]
            ))

        return embeddings

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost in USD for embedding token_count tokens."""
        return (token_count / 1_000_000) * self.COST_PER_MILLION_TOKENS
```

### Retry Logic (Exponential Backoff)

Exponential backoff for transient failures:

- **Rate Limits (429)**: Retry with delays 1s, 2s, 4s, 8s, 16s (up to max_retries)
- **Network Errors**: Same exponential backoff pattern
- **Other Errors**: Fail immediately (invalid API key, malformed request, etc.)

### Caching Strategy

Reuse EmbeddingCache from prototype for blob-based caching:

```python
# Integration with existing cache (from STORY-0001.1.3)

async def embed_with_cache(
    chunker: ChunkerProtocol,
    embedder: EmbedderProtocol,
    cache: EmbeddingCache,
    blob_record: BlobRecord
) -> list[Embedding]:
    """Embed blob chunks with caching by blob SHA."""

    # Check cache first
    cached = await cache.get(blob_record.sha)
    if cached:
        logger.info(f"Cache hit for blob {blob_record.sha}")
        return cached

    # Cache miss - generate embeddings
    logger.info(f"Cache miss for blob {blob_record.sha}")
    chunks = chunker.chunk_file(
        content=blob_record.content.decode("utf-8"),
        language=detect_language_from_extension(blob_record.locations[0].file_path),
        max_tokens=800
    )

    embeddings = await embedder.embed_chunks(chunks, blob_record.sha)

    # Store in cache
    await cache.set(blob_record.sha, embeddings)

    return embeddings
```

### Cost Tracking

Track costs at two levels:

1. **Per-Embedding**: Store `cost_usd` in Embedding dataclass
2. **Aggregate**: Sum costs across all embeddings for reporting

```python
# Example aggregate tracking
total_tokens = sum(e.token_count for e in embeddings)
total_cost = sum(e.cost_usd for e in embeddings)
logger.info(f"Embedded {len(embeddings)} chunks, {total_tokens} tokens, ${total_cost:.4f}")
```

### Configuration Integration

Read API key from GitCtxSettings with validation:

```python
# Extend GitCtxSettings (from STORY-0001.1.2)

class GitCtxSettings(BaseSettings):
    """Global configuration."""

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for embedding generation"
    )

    @validator("openai_api_key")
    def validate_api_key(cls, v):
        """Validate API key is configured when embedder is used."""
        if not v or not v.startswith("sk-"):
            raise ConfigurationError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or configure in ~/.gitctx/config.toml"
            )
        return v
```

## Dependencies

### External Libraries

- `openai>=1.0.0,<2.0` - AsyncOpenAI client (1.x API stability)
- `tiktoken>=0.8.0,<1.0` - Token counting (used by chunker, validates chunk tokens)

### Internal Dependencies

- **STORY-0001.2.2** (Blob Chunking) - Provides CodeChunk input
- **STORY-0001.1.3** (Embedding Cache) - Provides EmbeddingCache for caching ✅
- **STORY-0001.1.2** (Configuration) - Provides GitCtxSettings for API key ✅

### Downstream Consumers

- **STORY-0001.2.4** (Vector Storage) - Consumes Embedding objects

## Pattern Reuse

From existing codebase analysis:

**Test Patterns** (follow these):

- Mock API responses: Use `pytest-mock` to mock AsyncOpenAI
- Parametrize error scenarios: Test all retry paths
- Fixture factories: Create test embeddings and chunks

**Source Patterns** (follow these):

- Protocol-based design: EmbedderProtocol enables future Rust impl
- Async/await: Use AsyncOpenAI for concurrency
- Dataclasses with primitives: FFI-friendly (list[float], not numpy)

**Anti-Patterns to Avoid**:

- ❌ Don't use numpy arrays (breaks FFI compatibility)
- ❌ Don't implement custom retry logic (use tenacity or builtin)
- ❌ Don't cache in memory (use EmbeddingCache for persistence)

## Success Criteria

Story is complete when:

- ✅ All 4 tasks implemented and tested
- ✅ All 10 BDD scenarios pass
- ✅ Unit test coverage >90%
- ✅ Batching works correctly (up to 2048 chunks per call)
- ✅ Retry logic handles rate limits and network errors
- ✅ Cache integration works (no re-embedding of unchanged blobs)
- ✅ Cost tracking accurate (±1% of actual API costs)
- ✅ Quality gates: ruff + mypy + pytest all pass
- ✅ Documentation: Protocol and implementation docstrings complete

## Performance Targets

- Throughput: >500 chunks/second with batching
- Latency: <100ms per API call (network permitting)
- Cache hit rate: >80% on typical development workflows (incremental changes)
- Cost accuracy: ±1% of actual OpenAI billing

## Notes

- Follow the prototype in `/Users/bram/Code/codectl-ai/gitctx` closely
- OpenAI text-embedding-3-large: 3072 dimensions, $0.13/1M tokens
- Batching is critical for performance (500x speedup vs individual calls)
- Exponential backoff prevents cascading failures during rate limits
- Cache by blob SHA ensures identical content never re-embedded

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
