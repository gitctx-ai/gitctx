"""Unit tests for OpenAI provider (search/query interface)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from gitctx.models.providers.openai import OpenAIProvider

# Import will be added after implementation
# from gitctx.models.providers.openai import OpenAIProvider


@pytest.fixture
def mock_openai_embeddings():
    """Mock LangChain OpenAIEmbeddings."""
    with patch("gitctx.models.providers.openai.OpenAIEmbeddings") as mock:
        yield mock


def test_openai_provider_init(mock_openai_embeddings):
    """Test OpenAIProvider initialization."""

    provider = OpenAIProvider("text-embedding-3-large", "fake-key")
    assert provider.model_name == "text-embedding-3-large"
    assert provider.dimensions == 3072
    # Has BaseProvider properties (via composition)
    assert hasattr(provider, "max_tokens")
    assert hasattr(provider, "provider")


def test_embed_query_shape(mock_openai_embeddings):
    """Test embed_query returns correct numpy array shape."""

    # Mock embed_query to return list of floats
    mock_client = MagicMock()
    mock_client.embed_query.return_value = [0.1] * 3072
    mock_openai_embeddings.return_value = mock_client

    provider = OpenAIProvider("text-embedding-3-large", "fake-key")
    result = provider.embed_query("test query")

    assert isinstance(result, np.ndarray)
    assert result.shape == (3072,)
    assert result.dtype in (np.float64, np.float32)


def test_embed_documents_shape(mock_openai_embeddings):
    """Test embed_documents returns list of numpy arrays."""

    # Mock embed_documents to return list of lists
    mock_client = MagicMock()
    mock_client.embed_documents.return_value = [
        [0.1] * 3072,
        [0.2] * 3072,
    ]
    mock_openai_embeddings.return_value = mock_client

    provider = OpenAIProvider("text-embedding-3-large", "fake-key")
    results = provider.embed_documents(["test1", "test2"])

    assert len(results) == 2
    assert all(isinstance(r, np.ndarray) for r in results)
    assert all(r.shape == (3072,) for r in results)


def test_openai_provider_uses_base_provider(mock_openai_embeddings):
    """Test that OpenAIProvider extends BaseProvider."""

    provider = OpenAIProvider("text-embedding-3-small", "fake-key")

    # Should have BaseProvider properties
    assert provider.max_tokens == 8191
    assert provider.dimensions == 1536
    assert provider.provider == "openai"


def test_openai_provider_passes_api_key(mock_openai_embeddings):
    """Test that API key is passed to LangChain."""

    OpenAIProvider("text-embedding-3-large", "test-api-key-123")

    # Verify OpenAIEmbeddings was called with correct params
    mock_openai_embeddings.assert_called_once()
    call_kwargs = mock_openai_embeddings.call_args[1]

    assert call_kwargs["model"] == "text-embedding-3-large"
    assert call_kwargs["dimensions"] == 3072
