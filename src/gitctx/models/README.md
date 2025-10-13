# models/

Model infrastructure layer providing API clients to all features.

## Current Implementation

- **registry.py** - Model metadata (token limits, dimensions)
- **protocols.py** - ModelProvider protocol
- **base.py** - BaseProvider abstract class
- **factory.py** - Provider selection and instantiation
- **errors.py** - Model-specific errors
- **providers/openai.py** - OpenAI implementation

## Usage Example

```python
from gitctx.models.factory import get_embedder
from gitctx.config.settings import load_settings

settings = load_settings()
embedder = get_embedder("text-embedding-3-large", settings)

# Single query
vector = embedder.embed_query("test query")

# Batch documents
vectors = embedder.embed_documents(["doc1", "doc2", "doc3"])
```

## Supported Models

- `text-embedding-3-large` - 3072 dimensions, 8191 max tokens
- `text-embedding-3-small` - 1536 dimensions, 8191 max tokens

## Adding New Providers (INIT-0004)

1. Create `providers/anthropic.py`
2. Implement `ModelProvider` protocol
3. Register in `factory.py`
4. Add model specs to `registry.py`
