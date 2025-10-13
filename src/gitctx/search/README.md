# search/

Search pipeline for semantic code search.

## Current Implementation (STORY-0001.3.1)

- **embeddings.py** - `QueryEmbedder` generates query embeddings with caching
- **query.py** - `QueryProcessor` orchestrates query processing (placeholder)
- **errors.py** - Search-specific exceptions

## Usage

```python
from gitctx.search.embeddings import QueryEmbedder
from gitctx.config.settings import load_settings
from gitctx.storage.lancedb_store import LanceDBStore

settings = load_settings()
store = LanceDBStore(settings)

embedder = QueryEmbedder(settings, store)
query_vector = embedder.embed_query("authentication logic")
# Returns: np.ndarray with shape (3072,)
```

## Error Handling

- `ValidationError` (exit 2): Empty query, whitespace-only, token limit exceeded
- `ConfigurationError` (exit 4): Missing API key
- `EmbeddingError` (exit 5): API errors (rate limit, timeout, connection)

## Caching

Query embeddings cached in LanceDB `query_embeddings` table:
- Cache key: SHA256(query_text + model_name)
- No TTL (cache indefinitely until `gitctx clear`)
- Concurrent writes: last-write-wins (no locking)

## Future (STORY-0001.3.2)

- **retriever.py** - Vector search execution
- **ranking.py** - Result ranking strategies
- **reranking.py** - LLM-based reranking (INIT-0002)
