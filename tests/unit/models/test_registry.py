"""Unit tests for model registry."""

import pytest

from gitctx.models.registry import MODELS, get_model_spec


def test_get_model_spec_text_embedding_3_large() -> None:
    """Test retrieving text-embedding-3-large model spec."""
    spec = get_model_spec("text-embedding-3-large")
    assert spec["max_tokens"] == 8191
    assert spec["dimensions"] == 3072
    assert spec["provider"] == "openai"


def test_get_model_spec_text_embedding_3_small() -> None:
    """Test retrieving text-embedding-3-small model spec."""
    spec = get_model_spec("text-embedding-3-small")
    assert spec["max_tokens"] == 8191
    assert spec["dimensions"] == 1536
    assert spec["provider"] == "openai"


def test_get_model_spec_invalid_model() -> None:
    """Test that invalid model name raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported model"):
        get_model_spec("nonexistent-model")


def test_error_message_lists_supported() -> None:
    """Test that error message lists all supported models."""
    try:
        get_model_spec("invalid")
        pytest.fail("Expected ValueError to be raised")
    except ValueError as e:
        assert "text-embedding-3-large" in str(e)
        assert "text-embedding-3-small" in str(e)


def test_models_registry_has_expected_structure() -> None:
    """Test that MODELS registry has expected structure."""
    assert isinstance(MODELS, dict)
    assert len(MODELS) >= 2  # At least 2 models defined

    # Verify all models have required fields
    for _model_name, spec in MODELS.items():
        assert "dimensions" in spec
        assert "max_tokens" in spec
        assert "provider" in spec
        assert isinstance(spec["dimensions"], int)
        assert isinstance(spec["max_tokens"], int)
        assert isinstance(spec["provider"], str)


def test_model_spec_type() -> None:
    """Test that returned spec matches ModelSpec TypedDict."""
    spec = get_model_spec("text-embedding-3-large")

    # TypedDict validation (structural)
    assert isinstance(spec, dict)
    assert set(spec.keys()) == {"dimensions", "max_tokens", "provider"}
