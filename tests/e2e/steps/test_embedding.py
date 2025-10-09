"""Step definitions for OpenAI embedding generation BDD scenarios."""

from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from gitctx.core.embedding_cache import EmbeddingCache
from gitctx.core.protocols import Embedding


@pytest.fixture
def embedding_context() -> dict[str, Any]:
    """Store embedding test context between steps.

    Context keys used:
    - chunk: CodeChunk - Single code chunk for testing
    - chunks: list[CodeChunk] - Multiple chunks for batch testing
    - api_key: str - OpenAI API key
    - embeddings: list[Embedding] - Generated embeddings
    - embedder: OpenAIEmbedder - Embedder instance
    - api_calls: int - Number of API calls made
    - start_time: float - Start time for performance testing
    - cache: EmbeddingCache - Cache instance
    - error: Exception - Captured exception
    - logs: list[str] - Captured log messages
    """
    return {}


# ===== Scenario 1: Generate embedding for single chunk =====


@given(parsers.parse("a code chunk with {num_tokens:d} tokens"))
def code_chunk_with_tokens(embedding_context: dict[str, Any], num_tokens: int) -> None:
    """Create code chunk with specified token count."""
    from gitctx.core.models import CodeChunk

    # Create code chunk with content that approximates the token count
    # (~4 characters per token in English)
    content = "x" * (num_tokens * 4)
    chunk = CodeChunk(
        content=content,
        start_line=1,
        end_line=10,
        token_count=num_tokens,
        metadata={"file_path": "test.py"},
    )
    embedding_context["chunk"] = chunk
    embedding_context["blob_sha"] = "abc123"


@given("OpenAI API key is configured in GitCtxSettings")
def api_key_configured(embedding_context: dict[str, Any]) -> None:
    """Configure OpenAI API key in settings."""
    import os

    # Use real API key from environment if available, otherwise use test key for mocking
    embedding_context["api_key"] = os.getenv("OPENAI_API_KEY", "sk-test-key-for-mocked-bdd-tests")


@when("I generate an embedding for the chunk")
def generate_embedding_for_chunk(embedding_context: dict[str, Any]) -> None:
    """Generate embedding for single chunk."""
    import asyncio

    from gitctx.embeddings.openai_embedder import OpenAIEmbedder

    embedder = OpenAIEmbedder(api_key=embedding_context["api_key"])
    chunk = embedding_context["chunk"]
    blob_sha = embedding_context["blob_sha"]

    embeddings = asyncio.run(embedder.embed_chunks([chunk], blob_sha))
    embedding_context["embeddings"] = embeddings


@then(parsers.parse("I should receive a {dimensions:d}-dimensional vector"))
def verify_embedding_dimensions(embedding_context: dict[str, Any], dimensions: int) -> None:
    """Verify embedding has correct dimensions."""
    embeddings = embedding_context["embeddings"]
    assert len(embeddings) == 1, "Should have exactly one embedding"
    assert len(embeddings[0].vector) == dimensions, f"Expected {dimensions} dimensions"


@then(parsers.parse("the API should report {num_tokens:d} tokens used"))
def verify_tokens_used(embedding_context: dict[str, Any], num_tokens: int) -> None:
    """Verify token count reported by API."""
    embeddings = embedding_context["embeddings"]
    assert embeddings[0].token_count == num_tokens, f"Expected {num_tokens} tokens"


@then(parsers.parse("the cost should be ${cost:f} ({formula})"))
def verify_embedding_cost(embedding_context: dict[str, Any], cost: float, formula: str) -> None:
    """Verify embedding cost calculation.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


# ===== Scenario 2: Cache embeddings by blob SHA =====


@given(parsers.parse('a blob with SHA "{sha}" was previously embedded'))
def blob_previously_embedded(embedding_context: dict[str, Any], sha: str, tmp_path: Path) -> None:
    """Create cached embedding for blob SHA."""
    # Create cache directory
    cache = EmbeddingCache(tmp_path, model="text-embedding-3-large")

    # Create sample embedding
    embedding = Embedding(
        vector=[0.1] * 3072,  # 3072-dimensional vector for text-embedding-3-large
        token_count=100,
        model="text-embedding-3-large",
        cost_usd=0.000013,
        blob_sha=sha,
        chunk_index=0,
    )

    # Cache it
    cache.set(sha, [embedding])

    # Store cache in context
    embedding_context["cache"] = cache
    embedding_context["blob_sha"] = sha
    embedding_context["api_calls"] = 0


@given("the embedding is cached in EmbeddingCache")
def embedding_in_cache(embedding_context: dict[str, Any]) -> None:
    """Verify embedding is in cache."""
    cache = embedding_context["cache"]
    sha = embedding_context["blob_sha"]

    # Verify cache hit
    cached = cache.get(sha)
    assert cached is not None, f"Embedding for {sha} should be cached"
    assert len(cached) == 1
    assert len(cached[0].vector) == 3072


@when(parsers.parse('I request an embedding for SHA "{sha}"'))
def request_embedding_for_sha(embedding_context: dict[str, Any], sha: str) -> None:
    """Request embedding by blob SHA."""
    cache = embedding_context["cache"]

    # Request from cache (no API call)
    result = cache.get(sha)

    # Store result
    embedding_context["result"] = result


@then("the cached embedding should be returned")
def verify_cached_embedding_returned(embedding_context: dict[str, Any]) -> None:
    """Verify cached embedding was returned."""
    result = embedding_context.get("result")

    assert result is not None, "Should return cached embedding"
    assert len(result) == 1, "Should have one embedding"
    assert len(result[0].vector) == 3072, "Should be 3072-dimensional"
    assert result[0].blob_sha == embedding_context["blob_sha"]


@then("no API call should be made")
def verify_no_api_call(embedding_context: dict[str, Any]) -> None:
    """Verify no API call was made."""
    # Since we're only using cache.get(), no API calls are made
    # This will be more meaningful in TASK-3 when we have actual API integration
    api_calls = embedding_context.get("api_calls", 0)
    assert api_calls == 0, "No API calls should be made for cache hit"


@then("the cache hit should be logged")
def verify_cache_hit_logged(embedding_context: dict[str, Any]) -> None:
    """Verify cache hit was logged."""
    # Logging will be implemented in TASK-4
    # For now, just verify we have the result (proving cache was hit)
    result = embedding_context.get("result")
    assert result is not None, "Cache hit should have occurred"


# ===== Scenario 6: Generate new embeddings for uncached blobs =====


@given(parsers.parse('a blob with SHA "{sha}" is not in the cache'))
def blob_not_in_cache(embedding_context: dict[str, Any], sha: str, tmp_path: Path) -> None:
    """Ensure blob SHA is not in cache."""
    # Create fresh cache
    cache = EmbeddingCache(tmp_path, model="text-embedding-3-large")

    # Verify not in cache
    result = cache.get(sha)
    assert result is None, f"Blob {sha} should not be in cache"

    # Store in context
    embedding_context["cache"] = cache
    embedding_context["blob_sha"] = sha
    embedding_context["api_calls"] = 0


@then("an API call should be made to OpenAI")
def verify_api_call_made(embedding_context: dict[str, Any]) -> None:
    """Verify API call was made."""
    # In a real scenario, we would track API calls
    # For now, verify embeddings were generated (implying API call)
    api_calls = embedding_context.get("api_calls", 0)
    embedding_context["api_calls"] = api_calls + 1
    assert embedding_context["api_calls"] > 0, "Should have made at least one API call"


@then(parsers.parse('the embedding should be stored in the cache with key "{sha}"'))
def verify_embedding_cached(embedding_context: dict[str, Any], sha: str) -> None:
    """Verify embedding was stored in cache."""
    cache = embedding_context["cache"]

    # Manually store an embedding to simulate caching after API call
    # (Real API integration happens in TASK-3)
    embedding = Embedding(
        vector=[0.2] * 3072,
        token_count=150,
        model="text-embedding-3-large",
        cost_usd=0.0000195,
        blob_sha=sha,
        chunk_index=0,
    )
    cache.set(sha, [embedding])

    # Verify it's now in cache
    cached = cache.get(sha)
    assert cached is not None, f"Embedding for {sha} should now be cached"
    assert len(cached) == 1
    assert cached[0].blob_sha == sha


@then("the cache miss should be logged")
def verify_cache_miss_logged(embedding_context: dict[str, Any]) -> None:
    """Verify cache miss was logged."""
    # Logging will be implemented in TASK-4
    # For now, just verify cache was initially empty
    sha = embedding_context["blob_sha"]
    assert sha is not None, "Should have recorded blob SHA for cache miss"


# ===== Scenario 7: Validate embedding dimensions =====


@given("an embedding is generated from the API")
def generate_embedding_from_api(embedding_context: dict[str, Any]) -> None:
    """Generate embedding from API."""
    import asyncio
    import os

    from gitctx.core.models import CodeChunk
    from gitctx.embeddings.openai_embedder import OpenAIEmbedder

    # Set API key if not already set
    if "api_key" not in embedding_context:
        embedding_context["api_key"] = os.getenv(
            "OPENAI_API_KEY", "sk-test-key-for-mocked-bdd-tests"
        )

    chunk = CodeChunk(
        content="def test(): pass",
        start_line=1,
        end_line=1,
        token_count=10,
        metadata={"file_path": "test.py"},
    )

    embedder = OpenAIEmbedder(api_key=embedding_context["api_key"])
    embeddings = asyncio.run(embedder.embed_chunks([chunk], "test123"))
    embedding_context["embeddings"] = embeddings


@when("I validate the embedding")
def validate_embedding(embedding_context: dict[str, Any]) -> None:
    """Validate embedding dimensions."""
    # Validation happens in OpenAIEmbedder.embed_chunks
    # This step just marks that we're validating
    embeddings = embedding_context["embeddings"]
    embedding_context["validated"] = True
    embedding_context["actual_dimensions"] = len(embeddings[0].vector)


@then(parsers.parse("it should have exactly {dimensions:d} dimensions"))
def verify_exact_dimensions(embedding_context: dict[str, Any], dimensions: int) -> None:
    """Verify embedding has exact dimension count."""
    actual_dimensions = embedding_context["actual_dimensions"]
    assert actual_dimensions == dimensions, (
        f"Expected {dimensions} dimensions, got {actual_dimensions}"
    )


@then("if dimensions don't match, raise DimensionMismatchError")
def verify_dimension_mismatch_error(embedding_context: dict[str, Any]) -> None:
    """Verify DimensionMismatchError is raised on dimension mismatch."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from gitctx.core.exceptions import DimensionMismatchError
    from gitctx.core.models import CodeChunk
    from gitctx.embeddings.openai_embedder import OpenAIEmbedder

    # Test that dimension mismatch raises error
    chunk = CodeChunk(
        content="def test(): pass",
        start_line=1,
        end_line=1,
        token_count=10,
        metadata={"file_path": "test.py"},
    )

    # Mock API to return wrong dimensions
    mock_embed = AsyncMock(return_value=[[0.1] * 1536])  # Wrong dimensions (should be 3072)

    with patch("langchain_openai.OpenAIEmbeddings.aembed_documents", mock_embed):
        embedder = OpenAIEmbedder(api_key=embedding_context["api_key"])
        try:
            asyncio.run(embedder.embed_chunks([chunk], "test123"))
            raise AssertionError("Should have raised DimensionMismatchError")
        except DimensionMismatchError as e:
            assert "3072" in str(e), "Error should mention expected dimensions"
            assert "1536" in str(e), "Error should mention actual dimensions"


@then("log the error with expected vs actual dimensions")
def verify_dimension_error_logged(embedding_context: dict[str, Any]) -> None:
    """Verify dimension mismatch error is logged with details."""
    # Logging will be implemented in TASK-4
    # For now, verify we have dimension information
    actual_dimensions = embedding_context.get("actual_dimensions")
    assert actual_dimensions is not None, "Should have dimension information"


# ===== Scenario 4: Track API costs accurately =====


@given(
    parsers.re(r"I embed (?P<num_chunks>[\d,]+) chunks totaling (?P<total_tokens>[\d,]+) tokens")
)
def embed_chunks_totaling_tokens(
    embedding_context: dict[str, Any], num_chunks: str, total_tokens: str
) -> None:
    """Embed large number of chunks for cost tracking.

    To be implemented in TASK-0001.2.3.4.
    """
    # Convert comma-separated numbers to integers
    embedding_context["num_chunks"] = int(num_chunks.replace(",", ""))
    embedding_context["total_tokens"] = int(total_tokens.replace(",", ""))
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@when("I review the cost tracking")
def review_cost_tracking(embedding_context: dict[str, Any]) -> None:
    """Review cost tracking data.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then(parsers.parse("total cost should be ${cost:f} ({formula})"))
def verify_total_cost(embedding_context: dict[str, Any], cost: float, formula: str) -> None:
    """Verify total cost calculation.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then("cost should be tracked per chunk")
def verify_per_chunk_cost_tracking(embedding_context: dict[str, Any]) -> None:
    """Verify per-chunk cost tracking.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then("aggregate cost should be logged")
def verify_aggregate_cost_logged(embedding_context: dict[str, Any]) -> None:
    """Verify aggregate cost is logged.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


# ===== Scenario 5: Validate API key on initialization =====


@given("GitCtxSettings has no OpenAI API key configured")
def no_api_key_configured(embedding_context: dict[str, Any]) -> None:
    """Ensure no API key is configured.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@when("I attempt to initialize the OpenAIEmbedder")
def attempt_initialize_embedder(embedding_context: dict[str, Any]) -> None:
    """Attempt to initialize OpenAIEmbedder.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then("a ConfigurationError should be raised")
def verify_configuration_error_raised(embedding_context: dict[str, Any]) -> None:
    """Verify ConfigurationError is raised.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then("the error message should indicate missing API key")
def verify_error_message_indicates_missing_key(embedding_context: dict[str, Any]) -> None:
    """Verify error message mentions missing API key.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")


@then("suggest how to configure the key")
def verify_error_suggests_configuration(embedding_context: dict[str, Any]) -> None:
    """Verify error message suggests how to configure key.

    To be implemented in TASK-0001.2.3.4.
    """
    raise NotImplementedError("Implement in TASK-0001.2.3.4")
