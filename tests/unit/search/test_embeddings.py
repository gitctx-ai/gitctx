"""Unit tests for query embedding generation."""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import openai
import pytest

from gitctx.search.errors import EmbeddingError, ValidationError
from gitctx.storage.lancedb_store import LanceDBStore


def test_empty_query_raises_validation_error(settings: Mock, store: LanceDBStore) -> None:
    """Test that empty query raises ValidationError."""
    from gitctx.search.embeddings import QueryEmbedder

    embedder = QueryEmbedder(settings, store)
    with pytest.raises(ValidationError, match="Query cannot be empty"):
        embedder.embed_query("")


def test_whitespace_only_query_raises_validation_error(settings: Mock, store: LanceDBStore) -> None:
    """Test that whitespace-only query raises ValidationError."""
    from gitctx.search.embeddings import QueryEmbedder

    embedder = QueryEmbedder(settings, store)
    with pytest.raises(ValidationError, match="whitespace only"):
        embedder.embed_query("   \n\t  ")


def test_token_limit_exceeded_raises_validation_error(settings: Mock, store: LanceDBStore) -> None:
    """Test that token limit exceeded raises ValidationError."""
    from gitctx.search.embeddings import QueryEmbedder

    embedder = QueryEmbedder(settings, store)
    long_query = "word " * 10000  # Exceeds 8191 tokens
    with pytest.raises(ValidationError, match="exceeds 8191 tokens"):
        embedder.embed_query(long_query)
    with pytest.raises(ValidationError, match="got "):
        embedder.embed_query(long_query)


def test_valid_query_passes_validation(settings: Mock, test_embedding_vector) -> None:
    """Test that valid query passes validation and returns embedding."""
    from gitctx.search.embeddings import QueryEmbedder

    # Mock store with cache methods
    mock_store = Mock()
    mock_store.get_query_embedding.return_value = None

    # Mock the embedder to return a vector
    expected_vector = test_embedding_vector()

    # Patch OpenAIProvider to avoid real API calls
    with patch("gitctx.models.providers.openai.OpenAIProvider") as MockProvider:
        mock_instance = Mock()
        mock_instance.embed_query.return_value = expected_vector
        MockProvider.return_value = mock_instance

        with patch("gitctx.models.factory.get_embedder", return_value=mock_instance):
            embedder = QueryEmbedder(settings, mock_store)
            result = embedder.embed_query("valid test query")

            # Verify embedding was generated
            assert result.shape == (3072,)
            assert np.array_equal(result, expected_vector)

            # Verify cache was called
            mock_store.cache_query_embedding.assert_called_once()


def test_cache_hit_skips_api_call(settings: Mock, test_embedding_vector) -> None:
    """Test that cache hit skips API call."""
    from gitctx.search.embeddings import QueryEmbedder

    # Mock store with cached embedding
    mock_store = Mock()
    cached_vector = test_embedding_vector()
    mock_store.get_query_embedding.return_value = cached_vector

    with patch("gitctx.models.factory.get_embedder") as mock_get_embedder:
        embedder = QueryEmbedder(settings, mock_store)
        result = embedder.embed_query("cached query")

        # API should NOT be called
        assert not mock_get_embedder.called
        assert np.array_equal(result, cached_vector)


def test_cache_miss_calls_api(settings: Mock, test_embedding_vector) -> None:
    """Test that cache miss calls API."""
    from gitctx.search.embeddings import QueryEmbedder

    # Mock store with no cached embedding
    mock_store = Mock()
    mock_store.get_query_embedding.return_value = None

    expected_vector = test_embedding_vector()

    with patch("gitctx.models.providers.openai.OpenAIProvider") as MockProvider:
        mock_instance = Mock()
        mock_instance.embed_query.return_value = expected_vector
        MockProvider.return_value = mock_instance

        with patch("gitctx.models.factory.get_embedder", return_value=mock_instance):
            embedder = QueryEmbedder(settings, mock_store)
            result = embedder.embed_query("new query")

            # API should be called
            assert mock_instance.embed_query.called
            assert np.array_equal(result, expected_vector)


def test_generated_embedding_cached(settings: Mock, test_embedding_vector) -> None:
    """Test that generated embedding is cached."""
    from gitctx.search.embeddings import QueryEmbedder

    # Mock store
    mock_store = Mock()
    mock_store.get_query_embedding.return_value = None

    generated_vector = test_embedding_vector()

    with patch("gitctx.models.providers.openai.OpenAIProvider") as MockProvider:
        mock_instance = Mock()
        mock_instance.embed_query.return_value = generated_vector
        MockProvider.return_value = mock_instance

        with patch("gitctx.models.factory.get_embedder", return_value=mock_instance):
            embedder = QueryEmbedder(settings, mock_store)
            embedder.embed_query("new query for caching")

            # Cache should be called with the generated vector
            mock_store.cache_query_embedding.assert_called_once()
            call_args = mock_store.cache_query_embedding.call_args[0]
            assert call_args[1] == "new query for caching"
            assert np.array_equal(call_args[2], generated_vector)


@pytest.mark.parametrize(
    "exception,expected_message",
    [
        (
            openai.RateLimitError(
                message="Rate limited",
                response=Mock(status_code=429),
                body=None,
            ),
            "API rate limit exceeded",
        ),
        (
            openai.APIStatusError(
                message="Service unavailable",
                response=Mock(status_code=503),
                body=None,
            ),
            "OpenAI API unavailable",
        ),
        (
            openai.APIStatusError(
                message="Internal server error",
                response=Mock(status_code=500),
                body=None,
            ),
            "OpenAI API unavailable",
        ),
        (
            openai.APITimeoutError(request=Mock()),
            "Request timeout after 30 seconds",
        ),
        (
            openai.APIConnectionError(request=Mock()),
            "Cannot connect to OpenAI API",
        ),
    ],
)
def test_api_errors_transformed(
    settings: Mock, exception: Exception, expected_message: str
) -> None:
    """Test that API errors are transformed to EmbeddingError."""
    from gitctx.search.embeddings import QueryEmbedder

    # Mock store with no cache
    mock_store = Mock()
    mock_store.get_query_embedding.return_value = None

    # Mock at both levels to prevent real API calls
    with patch("gitctx.models.providers.openai.OpenAIProvider") as MockProvider:
        mock_embedder = Mock()
        mock_embedder.embed_query.side_effect = exception
        MockProvider.return_value = mock_embedder

        with patch("gitctx.models.factory.get_embedder", return_value=mock_embedder):
            embedder = QueryEmbedder(settings, mock_store)

            with pytest.raises(EmbeddingError, match=expected_message):
                embedder.embed_query("test query")
