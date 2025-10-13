"""Unit tests for base provider class."""

import pytest

from gitctx.models.base import BaseProvider


def test_base_provider_loads_spec() -> None:
    """Test that BaseProvider loads model spec correctly."""
    provider = BaseProvider("text-embedding-3-large")
    assert provider.max_tokens == 8191
    assert provider.dimensions == 3072
    assert provider.provider == "openai"


def test_base_provider_small_model() -> None:
    """Test BaseProvider with small model."""
    provider = BaseProvider("text-embedding-3-small")
    assert provider.max_tokens == 8191
    assert provider.dimensions == 1536
    assert provider.provider == "openai"


def test_base_provider_invalid_model() -> None:
    """Test that invalid model raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported model"):
        BaseProvider("invalid-model")


def test_base_provider_model_name_stored() -> None:
    """Test that model name is stored."""
    provider = BaseProvider("text-embedding-3-large")
    assert provider.model_name == "text-embedding-3-large"
