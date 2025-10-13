# storage/

Storage layer for embeddings, metadata, and cache management using LanceDB.

## Current Implementation

- **lancedb_store.py** - Main LanceDB storage interface
- **embedding_cache.py** - Embedding cache management

## Cache Tables

### query_embeddings
Caches query embeddings to minimize API calls.

**Schema:**
- `cache_key` (string): SHA256(query_text + model_name)
- `query_text` (string): Original query (for debugging)
- `embedding` (vector[3072]): Embedding vector
- `model_name` (string): Model used
- `created_at` (float64): Unix timestamp

**Behavior:**
- No TTL (cache indefinitely)
- Cleared by: `gitctx clear` command
- Concurrent writes: last-write-wins (no locking)

### code_chunks
Stores indexed code chunks with embeddings.

**Schema:**
- `chunk_id` (string): Unique chunk identifier
- `content` (string): Code content
- `embedding` (vector[3072]): Code embedding
- `file_path` (string): Source file path
- `commit_sha` (string): Git commit SHA
- `metadata` (struct): Additional metadata

## Usage

```python
from gitctx.storage.lancedb_store import LanceDBStore
from pathlib import Path

store = LanceDBStore(Path(".gitctx/db/lancedb"))

# Cache query embedding
cache_key = "abc123..."
store.cache_query_embedding(cache_key, "my query", vector, "text-embedding-3-large")

# Retrieve cached embedding
cached_vector = store.get_query_embedding(cache_key)
```
