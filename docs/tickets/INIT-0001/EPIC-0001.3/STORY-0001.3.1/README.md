# STORY-0001.3.1: Query Embedding Generation

**Parent Epic**: [EPIC-0001.3](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 4
**Progress**: ████░░░░░░ 40%

## User Story

As a developer
I want to convert my search queries into embeddings
So that I can perform semantic code search based on meaning rather than exact text matching

## Acceptance Criteria

- [ ] Query text converted to 3072-dimensional embedding vector via OpenAI API using `text-embedding-3-large` model
- [ ] Empty query validation (exit code 2):
  - Empty string `""` → `"Error: Query cannot be empty"`
  - Whitespace-only `"   \n\t  "` → `"Error: Query cannot be whitespace only"`
- [ ] Token limit validation using tiktoken with `cl100k_base` encoding (exit code 2):
  - Count tokens before API call
  - If count > 8191 → `"Error: Query exceeds 8191 tokens (got {count}). Try a shorter, more specific query."`
- [ ] Error message formats follow [TUI_GUIDE.md](../../../TUI_GUIDE.md) standards (relocated to docs/ in TASK-0001.3.1.0)
- [ ] Missing API key detection (exit code 4):
  - Check `OPENAI_API_KEY` env var and `~/.gitctx/config.yml`
  - Error: `"Error: OpenAI API key not configured\nSet with: export OPENAI_API_KEY=sk-...\nOr run: gitctx config set api_keys.openai sk-..."`
- [ ] API error handling via unit tests (exit code 5):
  - HTTP 429 → `"Error: API rate limit exceeded (429). Retry after 60 seconds or check usage limits at https://platform.openai.com/account/rate-limits"`
  - HTTP 5xx → `"Error: OpenAI API unavailable (HTTP {status_code}). Service may be down. Check status at https://status.openai.com and retry in 1-2 minutes."`
  - Timeout (>30s) → `"Error: Request timeout after 30 seconds. Verify internet connection and firewall settings. Retry with shorter query if issue persists."`
  - Connection refused → `"Error: Cannot connect to OpenAI API. Verify network access."`
  - HTTP 401 → `"Error: API key rejected (invalid or revoked). Get new key at https://platform.openai.com/api-keys"`
- [ ] Malformed query validation (exit code 2):
  - Query with null bytes → `"Error: Query contains invalid characters (null bytes)"`
- [ ] Query embeddings cached in LanceDB `query_embeddings` table:
  - Schema: `{cache_key: str (SHA256), query_text: str, embedding: vector[3072], model_name: str, created_at: timestamp}`
  - Cache key: `SHA256(query_text + model_name)`
  - No TTL (cache indefinitely until `gitctx clear`)
  - Concurrent writes: last-write-wins (LanceDB atomic writes, no locking)
  - Read-during-write: May return stale data (acceptable for cache, eventual consistency)

## BDD Scenarios

**E2E Scenarios (via VCR cassettes):**

```gherkin
# Added to tests/e2e/features/search.feature

Scenario: Query embedding generated successfully
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search 'authentication middleware'"
  Then the exit code should be 0
  And results should be displayed

Scenario: Cached query embedding reused (no API call)
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  And query "database setup" was previously searched
  When I run "gitctx search 'database setup'"
  Then the exit code should be 0
  And results should be displayed

Scenario: Missing API key (exit code 4)
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is ""
  When I run "gitctx search 'test query'"
  Then the exit code should be 4
  And the output should contain "Error: OpenAI API key not configured"
  And the output should contain "Set with: export OPENAI_API_KEY=sk-..."
  And the output should contain "Or run: gitctx config set api_keys.openai sk-..."

Scenario: Empty query validation (exit code 2)
  Given an indexed repository
  When I run "gitctx search ''"
  Then the exit code should be 2
  And the output should contain "Error: Query cannot be empty"

Scenario: Query exceeds token limit (exit code 2)
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  And a file "tests/fixtures/long_query_9000_tokens.txt" with 9000 tokens
  When I run gitctx with query from file "tests/fixtures/long_query_9000_tokens.txt"
  Then the exit code should be 2
  And the output should contain "Error: Query exceeds 8191 tokens (got 9000)"
  And the output should contain "Try a shorter, more specific query"
```

## Technical Design

### Model Registry

Create embedding model registry for token limits and dimensions:

```python
# src/gitctx/embeddings/models.py (new file)
"""Embedding model registry with metadata and constraints."""

from typing import TypedDict

class EmbeddingModelSpec(TypedDict):
    """Metadata for a supported embedding model."""
    max_tokens: int
    dimensions: int
    provider: str

EMBEDDING_MODELS: dict[str, EmbeddingModelSpec] = {
    "text-embedding-3-large": {
        "max_tokens": 8191,
        "dimensions": 3072,
        "provider": "openai",
    },
    "text-embedding-3-small": {
        "max_tokens": 8191,
        "dimensions": 1536,
        "provider": "openai",
    },
}

def get_model_spec(model_name: str) -> EmbeddingModelSpec:
    """Get model metadata or raise if unsupported."""
    if model_name not in EMBEDDING_MODELS:
        supported = ", ".join(EMBEDDING_MODELS.keys())
        raise ValueError(
            f"Unsupported embedding model: {model_name}\n"
            f"Supported models: {supported}"
        )
    return EMBEDDING_MODELS[model_name]
```

### Query Embedding with Caching

```python
# src/gitctx/cli/search.py (extend)
import hashlib
import tiktoken
from gitctx.embeddings.models import get_model_spec

def generate_query_embedding(query: str, settings: GitCtxSettings, store: LanceDBStore) -> np.ndarray:
    """Generate or retrieve cached query embedding.

    Args:
        query: Search query string
        settings: GitCtx configuration
        store: LanceDB store for caching

    Returns:
        3072-dimensional embedding vector

    Raises:
        ValueError: If query empty/whitespace or exceeds token limit (exit 2)
        ConfigurationError: If API key missing (exit 4)
        NetworkError: If API unavailable (exit 5)
    """
    # 1. Validate query not empty
    if not query:
        raise ValueError("Error: Query cannot be empty")
    if not query.strip():
        raise ValueError("Error: Query cannot be whitespace only")

    # 2. Get model spec from registry
    model_name = settings.repo.model.embedding
    spec = get_model_spec(model_name)

    # 3. Token count validation (fast, <5ms)
    encoder = tiktoken.get_encoding('cl100k_base')
    token_count = len(encoder.encode(query))

    if token_count > spec["max_tokens"]:
        raise ValueError(
            f"Error: Query exceeds {spec['max_tokens']} tokens (got {token_count}). "
            f"Try a shorter, more specific query."
        )

    # 4. Check LanceDB query cache
    cache_key = hashlib.sha256(f"{query}{model_name}".encode()).hexdigest()
    cached_vector = store.get_query_embedding(cache_key)
    if cached_vector is not None:
        return cached_vector

    # 5. Validate API key
    api_key = settings.get("api_keys.openai")
    if not api_key:
        raise ConfigurationError(
            "Error: OpenAI API key not configured\n"
            "Set with: export OPENAI_API_KEY=sk-...\n"
            "Or run: gitctx config set api_keys.openai sk-..."
        )

    # 6. Generate embedding via OpenAI
    embedder = OpenAIEmbeddings(
        model=model_name,
        dimensions=spec["dimensions"],
        api_key=SecretStr(api_key),
        timeout=30,
    )

    try:
        query_vector = embedder.embed_query(query)
    except openai.RateLimitError:
        raise NetworkError("Error: API rate limit exceeded. Wait 60 seconds and retry.")
    except openai.APIStatusError as e:
        if e.status_code >= 500:
            raise NetworkError("Error: OpenAI API unavailable. Retry in a few moments.")
        raise
    except requests.exceptions.Timeout:
        raise NetworkError("Error: Request timeout after 30s. Check network and retry.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Error: Cannot connect to OpenAI API. Verify network access.")

    # 7. Cache the result
    store.cache_query_embedding(cache_key, query, query_vector, model_name)

    return query_vector
```

### LanceDB Cache Methods

```python
# src/gitctx/storage/lancedb_store.py (extend existing class)

def get_query_embedding(self, cache_key: str) -> Optional[np.ndarray]:
    """Check if query embedding cached.

    Args:
        cache_key: SHA256 hash of (query_text + model_name)

    Returns:
        Cached embedding vector or None if not found
    """
    try:
        table = self.db.open_table("query_embeddings")
        results = table.search().where(f"cache_key = '{cache_key}'").limit(1).to_list()
        return results[0]["embedding"] if results else None
    except Exception:
        return None  # Table doesn't exist yet or query not found

def cache_query_embedding(
    self,
    cache_key: str,
    query_text: str,
    embedding: np.ndarray,
    model_name: str
) -> None:
    """Store query embedding with metadata.

    Args:
        cache_key: SHA256 hash for lookup
        query_text: Original query (for debugging)
        embedding: 3072-dimensional vector
        model_name: Model used to generate embedding
    """
    import time

    # Create table if doesn't exist
    try:
        table = self.db.open_table("query_embeddings")
    except Exception:
        table = self.db.create_table(
            "query_embeddings",
            schema={
                "cache_key": "string",
                "query_text": "string",
                "embedding": f"vector[{len(embedding)}]",
                "model_name": "string",
                "created_at": "float64",
            }
        )

    # Insert (last-write-wins for concurrent access)
    table.add([{
        "cache_key": cache_key,
        "query_text": query_text,
        "embedding": embedding.tolist(),
        "model_name": model_name,
        "created_at": time.time(),
    }])
```

### Unit Test Requirements

**API Error Handling (`tests/unit/embeddings/test_query_embedding.py`):**

```python
import pytest
from unittest.mock import patch, Mock
import openai
import requests

@pytest.mark.parametrize("status_code,expected_message", [
    (429, "Error: API rate limit exceeded. Wait 60 seconds and retry."),
    (503, "Error: OpenAI API unavailable. Retry in a few moments."),
    (500, "Error: OpenAI API unavailable. Retry in a few moments."),
])
def test_api_http_errors(status_code, expected_message):
    """Test API HTTP error responses return correct messages."""
    with patch('openai.OpenAI') as mock_client:
        if status_code == 429:
            mock_client.return_value.embeddings.create.side_effect = openai.RateLimitError(...)
        else:
            mock_client.return_value.embeddings.create.side_effect = openai.APIStatusError(
                message="Server error",
                response=Mock(status_code=status_code),
                body=None
            )

        with pytest.raises(NetworkError, match=expected_message):
            generate_query_embedding("test query", settings, store)

def test_connection_timeout():
    """Test request timeout after 30 seconds."""
    with patch('openai.OpenAI') as mock_client:
        mock_client.return_value.embeddings.create.side_effect = requests.exceptions.Timeout()

        with pytest.raises(NetworkError, match="Error: Request timeout after 30s"):
            generate_query_embedding("test query", settings, store)

def test_connection_refused():
    """Test connection refused (API unreachable)."""
    with patch('openai.OpenAI') as mock_client:
        mock_client.return_value.embeddings.create.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(NetworkError, match="Error: Cannot connect to OpenAI API"):
            generate_query_embedding("test query", settings, store)

def test_whitespace_only_query():
    """Test whitespace-only query rejected."""
    with pytest.raises(ValueError, match="Error: Query cannot be whitespace only"):
        generate_query_embedding("   \n\t  ", settings, store)

def test_empty_query():
    """Test empty query rejected."""
    with pytest.raises(ValueError, match="Error: Query cannot be empty"):
        generate_query_embedding("", settings, store)

def test_token_limit_exceeded():
    """Test query exceeding token limit rejected."""
    long_query = "word " * 10000  # Exceeds 8191 tokens

    with pytest.raises(ValueError, match="Error: Query exceeds 8191 tokens"):
        generate_query_embedding(long_query, settings, store)
```

**Cache Behavior (`tests/unit/storage/test_query_cache.py`):**

```python
def test_cache_hit():
    """Test cache returns existing embedding without API call."""
    store = LanceDBStore(...)
    cache_key = hashlib.sha256(b"test query").hexdigest()
    expected_vector = np.random.rand(3072)

    store.cache_query_embedding(cache_key, "test query", expected_vector, "text-embedding-3-large")
    result = store.get_query_embedding(cache_key)

    np.testing.assert_array_equal(result, expected_vector)

def test_cache_miss():
    """Test cache miss returns None."""
    store = LanceDBStore(...)
    cache_key = hashlib.sha256(b"nonexistent query").hexdigest()

    result = store.get_query_embedding(cache_key)

    assert result is None

def test_concurrent_cache_writes():
    """Test last-write-wins for concurrent writes (no errors)."""
    store = LanceDBStore(...)
    cache_key = hashlib.sha256(b"same query").hexdigest()

    # Simulate 2 processes writing same query
    vector1 = np.random.rand(3072)
    vector2 = np.random.rand(3072)

    store.cache_query_embedding(cache_key, "same query", vector1, "text-embedding-3-large")
    store.cache_query_embedding(cache_key, "same query", vector2, "text-embedding-3-large")

    # Should not raise error, last write wins
    result = store.get_query_embedding(cache_key)
    assert result is not None
```

## Pattern Reuse

**Reused Patterns:**
- **VCR cassettes** (`tests/e2e/conftest.py:370`) - Record/replay OpenAI API responses for E2E tests
- **e2e_git_isolation_env** (`tests/e2e/conftest.py:41`) - Isolated subprocess testing
- **LanceDBStore** (`src/gitctx/storage/lancedb_store.py`) - Extended with cache methods
- **OpenAIEmbeddings** (LangChain) - Existing component from EPIC-0001.2

**New Components:**
- Model registry (`src/gitctx/embeddings/models.py`)
- Query cache table in LanceDB
- Unit tests for error handling

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.3.1.0](./TASK-0001.3.1.0.md) | Architecture refactor for clean module boundaries | ✅ Complete | 5-6 | 0/5 → 0/5 (no BDD, pure refactor) |
| [TASK-0001.3.1.1](./TASK-0001.3.1.1.md) | Write BDD scenarios for query embedding | ✅ Complete | 3 | 0/5 → 0/5 (all failing, red phase) |
| [TASK-0001.3.1.2](./TASK-0001.3.1.2.md) | Model registry and provider infrastructure | 🔵 Not Started | 3 | 0/5 → 1/5 (first scenario with VCR) |
| [TASK-0001.3.1.3](./TASK-0001.3.1.3.md) | Core query embedding implementation (TDD) | 🔵 Not Started | 8 | 1/5 → 4/5 (validation, cache, errors) |
| [TASK-0001.3.1.4](./TASK-0001.3.1.4.md) | Integration and E2E verification | 🔵 Not Started | 2 | 4/5 → 5/5 (all passing ✅) |

**Total Estimated Hours**: 21-22 hours (≈5 story points at 4h/point)

**Task Progression**:
- TASK-0 creates clean module structure for MVP completion and future features
- TASK-1 defines all scenarios (BDD red phase)
- TASK-2 builds model infrastructure foundation
- TASK-3 implements core with TDD (largest task)
- TASK-4 completes integration and verifies all scenarios pass

## BDD Progress

**Initial**: 0/5 scenarios passing (all pending)

Scenarios will be implemented incrementally across tasks.

## Dependencies

**Prerequisites:**
- EPIC-0001.1 (CLI Foundation) - Complete ✅
- EPIC-0001.2 (Real Indexing) - Complete ✅ (provides LanceDBStore, OpenAIEmbeddings)

**Package Dependencies (already in pyproject.toml):**
- `lancedb` - For query cache storage
- `langchain-openai` - For OpenAI embeddings client
- `tiktoken` - For token counting
- `pytest-vcr` - For API response recording/replay

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| VCR cassette recording complexity | Medium | Low | Follow existing embedding.feature patterns, use `$ENV` token |
| LanceDB query cache table schema | Low | Medium | Follow existing code_chunks table pattern |
| Token counting accuracy | Low | Low | Use tiktoken with cl100k_base encoding (same as OpenAI) |
| Cache key collision | Very Low | Low | Use SHA256(query_text + model_name) for uniqueness |

---

**Created**: 2025-10-12
**Last Updated**: 2025-10-12
**Planning Complete**: 2025-10-12 (5 tasks defined, ready for implementation)
