# CLAUDE.md - TDD Guidelines for tests/unit

This document defines the **mandatory TDD approach** for all unit tests in gitctx.

**Related Documentation:**

- [Root CLAUDE.md](../../CLAUDE.md) - Overview and workflow
- [BDD Testing](../e2e/CLAUDE.md) - End-to-end testing
- [Architecture](../../docs/architecture/CLAUDE.md) - Technical design

## 🚨 CRITICAL: The TDD Cycle

**NEVER write implementation before tests!** Follow this exact cycle:

```
┌─────────────┐
│   🔴 RED    │ Write a failing test
└──────┬──────┘
       │
┌──────▼──────┐
│  🟢 GREEN   │ Write minimal code to pass
└──────┬──────┘
       │
┌──────▼──────┐
│ 🔄 REFACTOR │ Improve code while tests pass
└─────────────┘
```

## Directory Structure Requirements

**Unit tests MUST mirror the src/ structure exactly:**

```
tests/unit/
├── cli/                    # Mirror of src/gitctx/cli/
│   ├── test_main.py       # Tests for cli/main.py
│   ├── test_config.py     # Tests for cli/config.py
│   └── test_commands.py   # Tests for cli/commands.py
├── core/                   # Mirror of src/gitctx/core/
│   ├── test_chunker.py    # Tests for core/chunker.py
│   ├── test_scanner.py    # Tests for core/scanner.py
│   └── test_embedder.py   # Tests for core/embedder.py
├── search/                 # Mirror of src/gitctx/search/
│   ├── test_engine.py     # Tests for search/engine.py
│   └── test_reranker.py   # Tests for search/reranker.py
├── storage/                # Mirror of src/gitctx/storage/
│   ├── test_cache.py      # Tests for storage/cache.py
│   └── test_lancedb.py    # Tests for storage/lancedb.py
└── conftest.py            # Shared fixtures
```

## Writing Unit Tests - TDD Workflow

### Step 1: RED - Write Failing Test

```python
def test_chunker_respects_max_tokens():
    """Test that chunker splits text respecting token limits."""
    chunker = Chunker(max_tokens=100)  # Will fail - Chunker doesn't exist
    chunks = chunker.chunk(" ".join(["word"] * 200))
    for chunk in chunks:
        assert chunker.count_tokens(chunk) <= 100
```

### Step 2: GREEN - Minimal Implementation

```python
class Chunker:
    def __init__(self, max_tokens=100):
        self.max_tokens = max_tokens

    def chunk(self, text):
        words = text.split()
        chunks, current = [], []
        for word in words:
            current.append(word)
            if len(current) >= self.max_tokens:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
        return chunks

    def count_tokens(self, text):
        return len(text.split())
```

### Step 3: REFACTOR - Improve Quality

Add proper types, use tiktoken for accurate token counting, add metadata.
See full implementation patterns in source code.

## Test Structure (AAA Pattern)

Every test MUST follow the Arrange-Act-Assert pattern:

```python
def test_search_engine_finds_relevant_results():
    # ARRANGE - Set up test data and dependencies
    engine = SearchEngine()
    engine.index_document("auth.py", "def authenticate(user): pass")
    engine.index_document("login.py", "def login(username): pass")

    # ACT - Perform the action being tested
    results = engine.search("authentication")

    # ASSERT - Check the outcome
    assert len(results) > 0
    assert "auth.py" in results[0].file_path
    assert results[0].score > 0.5
```

## Test Naming Conventions

### Test Class Names

```python
class TestSearchEngine:      # For testing SearchEngine class
class TestChunker:           # For testing Chunker class
class TestConfigManager:     # For testing ConfigManager class
```

### Test Method Names

```python
# Pattern: test_[method]_[condition]_[expected_result]

def test_chunk_empty_text_returns_empty_list():
    """Handle empty input gracefully."""
    pass

def test_search_with_no_matches_returns_empty():
    """Search returns empty list when no matches."""
    pass

def test_config_get_missing_key_returns_none():
    """Config returns None for missing keys."""
    pass

def test_scanner_ignores_gitignored_files():
    """Scanner respects .gitignore patterns."""
    pass

# BAD examples - too vague
def test_scanner():  # What about scanner?
def test_1():       # Meaningless name
def test_works():   # What works?
```

## Testing Edge Cases

Every component MUST test:

- Empty input
- Single item
- Boundary conditions
- Unicode/special characters
- Large datasets

```python
class TestChunker:
    def test_empty_text(self):
        assert Chunker().chunk("") == []

    def test_unicode_text(self):
        text = "Hello 世界 🌍"
        chunks = Chunker().chunk(text)
        assert chunks[0].content == text
```

## Deterministic Test Data

**CRITICAL: Never use `np.random.rand()` in tests - it creates non-deterministic data that makes debugging impossible when tests fail intermittently.**

### Embedding Vectors

Use the `test_embedding_vector` fixture for all embedding vector generation:

```python
def test_cache_hit_returns_embedding(tmp_path, test_embedding_vector):
    """Test that cache hit returns embedding."""
    store = LanceDBStore(tmp_path / "lancedb")

    # Create deterministic 3072-dim vector (text-embedding-3-large)
    expected_vector = test_embedding_vector()

    store.cache_query_embedding(cache_key, "test query", expected_vector, model)
    result = store.get_query_embedding(cache_key)

    # Vectors are predictable and reproducible
    np.testing.assert_array_almost_equal(result, expected_vector, decimal=6)

def test_small_model_embedding(test_embedding_vector):
    """Test with different embedding dimensions."""
    # text-embedding-3-small uses 1536 dimensions
    vector_small = test_embedding_vector(1536)

    # text-embedding-ada-002 also uses 1536 dimensions
    vector_ada = test_embedding_vector(1536)

    # Custom dimensions for future models
    vector_custom = test_embedding_vector(2048)
```

**Why this matters:**
- Tests fail consistently if there's a bug (not randomly)
- Debugging is possible with reproducible data
- CI/CD results are reliable
- Code reviews can reason about test behavior

**Anti-pattern:**
```python
# ❌ NEVER do this
vector = np.random.rand(3072)  # Non-deterministic, breaks debugging

# ❌ Even with seed, avoid in tests
np.random.seed(42)
vector = np.random.rand(3072)  # Fixture pattern is clearer

# ✅ ALWAYS use the fixture
vector = test_embedding_vector()  # Deterministic, debuggable, clear intent
```

### Other Random Data

For non-embedding random data, use seeded generators within tests:

```python
def test_random_repo_names():
    """Test with random repo names."""
    import random

    random.seed(42)  # Explicit seed for reproducibility
    repo_names = [f"repo_{random.randint(1000, 9999)}" for _ in range(10)]
    # Test with deterministic "random" names
```

## Mocking and Test Isolation

```python
from unittest.mock import Mock, patch

def test_embedder_handles_api_errors():
    """Test retry on API errors."""
    with patch('openai.Embedding.create') as mock:
        mock.side_effect = [Exception("API Error"), {"data": [{"embedding": [0.1]}]}]
        result = Embedder().generate("test")
        assert mock.call_count == 2  # Retried

def test_scanner_mocked_filesystem():
    with patch('pathlib.Path.rglob') as mock:
        mock.return_value = [Path("file1.py"), Path("node_modules/lib.js")]
        files = FileScanner(Path("/fake")).scan()
        assert len(files) == 1  # node_modules excluded
```

### Common Fixtures (conftest.py)

```python
@pytest.fixture
def temp_repo(tmp_path):
    """Create test repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "main.py").write_text("print('hello')")
    return repo

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI API."""
    client = Mock()
    client.embeddings.create.return_value = Mock(
        data=[Mock(embedding=[0.1] * 1536)]
    )
    return client
```

## Parametrized Tests

```python
@pytest.mark.parametrize("query,expected_count", [
    ("authentication", 5),
    ("database", 3),
    ("", 0),
])
def test_search_results(query, expected_count, search_engine):
    results = search_engine.search(query)
    assert len(results) == expected_count
```

Use for testing multiple inputs with same logic.

## Testing Async Code

```python
@pytest.mark.anyio
async def test_async_embedder():
    embedder = AsyncEmbedder()
    embeddings = await embedder.generate_batch(["text1", "text2"])
    assert len(embeddings) == 2
```

Use [`anyio`](https://anyio.readthedocs.io/en/stable/testing.html) for async tests.

## Test Coverage Requirements

### Coverage Goals

- **Overall**: >90% coverage
- **Critical paths**: 100% coverage
- **Error handling**: All error paths tested
- **Edge cases**: Comprehensive coverage

### Running with Coverage

```bash
# Run with coverage report
uv run pytest tests/unit/ --cov=src/gitctx --cov-report=term-missing

# Generate HTML coverage report
uv run pytest tests/unit/ --cov=src/gitctx --cov-report=html

# Fail if coverage below threshold
uv run pytest tests/unit/ --cov=src/gitctx --cov-fail-under=90
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src/gitctx"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
precision = 2
```

## Performance Testing

```python
import pytest
import time

def test_search_performance(benchmark, large_dataset):
    """Ensure search completes within performance targets."""
    engine = SearchEngine()
    engine.index_dataset(large_dataset)

    # Use pytest-benchmark
    result = benchmark(engine.search, "test query")

    assert benchmark.stats['mean'] < 2.0  # Mean time < 2 seconds
    assert len(result) > 0

def test_chunker_memory_usage():
    """Ensure chunker doesn't consume excessive memory."""
    import tracemalloc

    tracemalloc.start()

    chunker = Chunker()
    large_text = "word " * 1_000_000
    chunks = chunker.chunk(large_text)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Should use less than 100MB for 1M words
    assert peak / 1024 / 1024 < 100
```

## Common Testing Patterns

### Testing Error Handling

```python
def test_config_handles_corrupted_file():
    """Config gracefully handles corrupted config files."""
    with patch('builtins.open', side_effect=IOError("Corrupted")):
        config = Config()

        # Should use defaults when file is corrupted
        assert config.get("api_key") == ""
        assert config.get("model") == "gpt-4"

def test_api_client_retries_on_rate_limit():
    """API client implements exponential backoff."""
    client = APIClient()

    with patch('time.sleep') as mock_sleep:
        with patch('requests.post') as mock_post:
            mock_post.side_effect = [
                RateLimitError(),
                RateLimitError(),
                {"success": True}
            ]

            result = client.call_api("test")

            assert result == {"success": True}
            assert mock_sleep.call_count == 2
            # Check exponential backoff
            assert mock_sleep.call_args_list[0][0][0] < mock_sleep.call_args_list[1][0][0]
```

### Testing File Operations

```python
def test_cache_creates_directory_if_missing(tmp_path):
    """Cache creates its directory structure."""
    cache_dir = tmp_path / "nonexistent" / "cache"
    cache = Cache(cache_dir)

    cache.store("key", "value")

    assert cache_dir.exists()
    assert cache.get("key") == "value"
```

## 🚫 Common TDD Mistakes to Avoid

### 1. Writing Implementation First

❌ **Wrong**: Write code, then add tests
✅ **Right**: Write test, see it fail, then implement

### 2. Testing Implementation Details

❌ **Wrong**: Testing private methods
✅ **Right**: Test public interface behavior

### 3. Not Running Tests First

❌ **Wrong**: Write test, assume it would fail
✅ **Right**: Always see test fail first

### 4. Skipping Refactor Step

❌ **Wrong**: Leave messy code after green
✅ **Right**: Clean up while tests protect you

### 5. Writing Too Much Code

❌ **Wrong**: Implement features not required by tests
✅ **Right**: Minimal code to pass current test

### 6. Modifying Tests to Pass

❌ **Wrong**: Change test to match broken code
✅ **Right**: Fix code to match test requirements

## Running Unit Tests

### Run All Unit Tests

```bash
uv run pytest tests/unit/
```

### Run Specific Module

```bash
uv run pytest tests/unit/core/test_chunker.py
```

### Run Specific Test

```bash
uv run pytest tests/unit/core/test_chunker.py::test_empty_text
```

### Watch Mode (Continuous Testing)

```bash
uv run pytest-watch tests/unit/
```

### Debug Mode

```bash
uv run pytest tests/unit/ -vvs --pdb
```

## Test Documentation

```python
def test_scanner_respects_gitignore():
    """Scanner skips files matching .gitignore patterns."""
    # Clear, concise docstring required for every test
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) - Kent Beck
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
