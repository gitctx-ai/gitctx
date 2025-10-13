"""Unit tests for provider factory."""

from unittest.mock import Mock

import pytest

from gitctx.config.errors import ConfigurationError
from gitctx.models.factory import get_embedder
from gitctx.models.providers.openai import OpenAIProvider


def test_get_embedder_openai():
    """Test get_embedder returns OpenAIProvider for OpenAI models."""
    mock_settings = Mock()
    mock_settings.get.return_value = "fake-api-key"

    embedder = get_embedder("text-embedding-3-large", mock_settings)

    assert isinstance(embedder, OpenAIProvider)
    assert embedder.model_name == "text-embedding-3-large"


def test_get_embedder_missing_key():
    """Test get_embedder raises ConfigurationError when API key missing."""
    mock_settings = Mock()
    mock_settings.get.return_value = None

    with pytest.raises(ConfigurationError, match="API key not configured"):
        get_embedder("text-embedding-3-large", mock_settings)


def test_get_embedder_invalid_model():
    """Test get_embedder raises ValueError for unsupported model."""
    mock_settings = Mock()

    with pytest.raises(ValueError, match="Unsupported model"):
        get_embedder("invalid-model", mock_settings)
