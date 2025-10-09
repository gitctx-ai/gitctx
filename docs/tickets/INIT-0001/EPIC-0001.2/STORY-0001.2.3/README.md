# STORY-0001.2.3: OpenAI Embedding Generation

**Parent**: [EPIC-0001.2](../README.md)
**Status**: 🔵 Not Started
**Story Points**: 5
**Progress**: ██░░░░░░░░ 20% (1/5 tasks complete)

## User Story

As the indexing system (serving developers and AI agents)
I want to generate embeddings for code chunks using OpenAI's text-embedding-3-large model
So that chunks can be semantically searched with high-quality vector representations while tracking costs accurately

## Acceptance Criteria

- [ ] Generate embeddings using OpenAI text-embedding-3-large model (3072 dimensions)
- [ ] Batch chunk requests to maximize throughput (up to 2048 chunks per API call)
- [ ] Track token usage and API costs per chunk and in aggregate (accurate to ±1% compared to OpenAI billing)
- [ ] Handle API errors gracefully (rate limits, network errors, invalid requests)
- [ ] Implement exponential backoff retry logic for transient failures
- [ ] Cache embeddings by blob SHA to avoid re-computing unchanged content
- [ ] Support async/await for concurrent embedding generation
- [ ] Validate embedding dimensions match expected model output (3072)
- [ ] Log progress (chunks embedded, tokens used, estimated cost)
- [ ] Handle empty chunk lists gracefully (return empty list, no API calls)
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
| [TASK-0001.2.3.1](TASK-0001.2.3.1.md) | Write BDD scenarios for embedding generation | ✅ | 2 | 0/10 scenarios (all failing) |
| [TASK-0001.2.3.2](TASK-0001.2.3.2.md) | Define protocols, models, and EmbeddingCache + add dependencies | 🔵 | 4 | 2/10 scenarios passing |
| [TASK-0001.2.3.3](TASK-0001.2.3.3.md) | Implement OpenAIEmbedder with cache integration (TDD) and BDD | 🔵 | 8 | 8/10 scenarios passing |
| [TASK-0001.2.3.4](TASK-0001.2.3.4.md) | Configuration integration, cost tracking, and final BDD scenarios | 🔵 | 4 | 10/10 scenarios passing ✅ |

**Total**: 18 hours = 5 story points (reduced from 20h due to LangChain handling complexity)

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

### OpenAI API Integration (LangChain v1.0 Alpha)

Use LangChain wrapper for OpenAI embeddings with automatic batching, retry, and rate limiting:

```python
# src/gitctx/embeddings/openai_embedder.py

from langchain_openai import OpenAIEmbeddings

class OpenAIEmbedder(EmbedderProtocol):
    """OpenAI embedding generator wrapping LangChain.

    Implementation notes:
    - Uses LangChain's OpenAIEmbeddings (langchain_openai v1.0 alpha)
    - LangChain handles batching (up to 2048 chunks), retry, rate limiting
    - Validates embedding dimensions to catch API changes
    - Wraps LangChain for provider abstraction (easy to add Anthropic, Cohere, etc.)

    LangChain Benefits:
    - ✅ Automatic batching via chunk_size parameter
    - ✅ Exponential backoff retry via max_retries
    - ✅ Rate limiting handling (429 errors)
    - ✅ Token counting via tiktoken
    - ✅ Long input handling (auto-split)
    - ✅ Future provider flexibility
    """

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 3072
    COST_PER_MILLION_TOKENS = 0.13  # USD
    MAX_BATCH_SIZE = 2048  # OpenAI API limit

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        show_progress: bool = False,
        **kwargs
    ):
        """Initialize the embedder.

        Args:
            api_key: OpenAI API key (must start with 'sk-')
            max_retries: Maximum retry attempts for transient failures (default: 3)
            show_progress: Show progress bar for batch processing
            **kwargs: Additional args for OpenAIEmbeddings
        """
        if not api_key or not api_key.startswith("sk-"):
            raise ConfigurationError("Invalid OpenAI API key")

        # Wrap LangChain OpenAIEmbeddings
        self._embeddings = OpenAIEmbeddings(
            model=self.MODEL,
            dimensions=self.DIMENSIONS,
            chunk_size=self.MAX_BATCH_SIZE,  # Automatic batching
            max_retries=max_retries,          # Exponential backoff
            show_progress_bar=show_progress,
            tiktoken_enabled=True,            # Token counting
            check_embedding_ctx_length=True,  # Auto-split long inputs
            api_key=api_key,
            **kwargs
        )

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
        blob_sha: str
    ) -> list[Embedding]:
        """Generate embeddings for chunks (LangChain handles batching/retry).

        Args:
            chunks: Code chunks to embed
            blob_sha: Git blob SHA for metadata

        Returns:
            List of Embedding objects with vectors and metadata
        """
        # Extract content from chunks
        contents = [chunk.content for chunk in chunks]

        # Call LangChain (handles batching, retry, rate limiting)
        vectors = await self._embeddings.aembed_documents(contents)

        # Validate dimensions
        for vector in vectors:
            if len(vector) != self.DIMENSIONS:
                raise DimensionMismatchError(
                    f"Expected {self.DIMENSIONS} dimensions, got {len(vector)}"
                )

        # Build Embedding objects with metadata
        embeddings = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            embeddings.append(Embedding(
                vector=vector,
                token_count=chunk.token_count,
                model=self.MODEL,
                cost_usd=self.estimate_cost(chunk.token_count),
                blob_sha=blob_sha,
                chunk_index=idx
            ))

        return embeddings

    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost in USD for embedding token_count tokens.

        Note: LangChain doesn't expose cost automatically, so we calculate manually.
        """
        return (token_count / 1_000_000) * self.COST_PER_MILLION_TOKENS
```

### Retry Logic (Handled by LangChain)

LangChain handles retry logic automatically with exponential backoff:

- **Rate Limits (429)**: LangChain detects HTTP 429 errors and automatically retries with exponential backoff (delays: 4s, 8s, 16s) up to max_retries attempts
- **Network Errors**: Connection errors, timeouts, and transient failures follow same exponential backoff pattern (base delay 1s, max 20s)
- **Configuration**: Control via `max_retries` parameter (default: 3, configurable via constructor)
- **Other Errors**: Fail immediately (invalid API key, malformed request, etc.)

**Complexity Reduction**: ~200 lines of custom retry logic eliminated by using LangChain.

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

- `langchain-core>=1.0.0a0` - Core abstractions (v1.0 alpha, requires Python ≥3.10)
- `langchain-openai>=1.0.0a0` - OpenAI embeddings provider (wraps OpenAI API)
- `tiktoken>=0.5.0` - Token counting (peer dependency for LangChain)

### Internal Dependencies

- **STORY-0001.2.2** (Blob Chunking) - Provides CodeChunk input
- **STORY-0001.1.2** (Configuration) - Provides GitCtxSettings for API key ✅

**Internal Components** (implemented within this story):
- `EmbeddingCache` - Safetensor-based persistent cache (`.gitctx/embeddings/{model}/{blob_sha}.safetensors`)
- `OpenAIEmbedder` - LangChain wrapper with batching, retry logic, cost tracking

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
- ❌ Don't implement custom retry logic (LangChain handles this)
- ❌ Don't cache in memory (use EmbeddingCache for persistence)
- ❌ Don't use direct OpenAI client (use LangChain for provider flexibility)

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

- **LangChain v1.0 Alpha Adoption**: Using latest LangChain for future provider flexibility
- **Provider Abstraction**: Easy to add Anthropic, Cohere, HuggingFace embeddings later
- OpenAI text-embedding-3-large: 3072 dimensions, $0.13/1M tokens
- Batching is critical for performance (500x speedup vs individual calls)
- LangChain handles retry, batching, rate limiting automatically (~200 lines of code saved)
- Cache by blob SHA ensures identical content never re-embedded

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
