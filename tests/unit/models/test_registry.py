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
    with pytest.raises(ValueError, match="Unsupported model") as exc_info:
        get_model_spec("invalid")

    error_msg = str(exc_info.value)
    assert "text-embedding-3-large" in error_msg
    assert "text-embedding-3-small" in error_msg


def test_models_registry_has_expected_structure() -> None:
    """Test that MODELS registry has expected structure."""
    assert isinstance(MODELS, dict)
    assert len(MODELS) >= 2  # At least 2 models defined

    # Verify all models have required fields
    for spec in MODELS.values():
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
    assert set(spec.keys()) == {"dimensions", "max_tokens", "provider", "cents_per_million_tokens"}


# ============================================================================
# Pricing Tests (TASK-0001.4.5.2)
# ============================================================================


def test_get_model_spec_includes_pricing() -> None:
    """Test that model specs include cents_per_million_tokens field."""
    spec_large = get_model_spec("text-embedding-3-large")
    spec_small = get_model_spec("text-embedding-3-small")

    # Both models should have pricing field
    assert "cents_per_million_tokens" in spec_large
    assert "cents_per_million_tokens" in spec_small


def test_pricing_is_integer_cents() -> None:
    """Test that pricing is stored as integer cents, not float dollars."""
    spec_large = get_model_spec("text-embedding-3-large")
    spec_small = get_model_spec("text-embedding-3-small")

    # Pricing should be int (cents), not float (dollars)
    assert isinstance(spec_large["cents_per_million_tokens"], int)
    assert isinstance(spec_small["cents_per_million_tokens"], int)


def test_all_models_have_pricing() -> None:
    """Test that all models in registry have pricing information."""
    for model_name, spec in MODELS.items():
        assert "cents_per_million_tokens" in spec, f"Model {model_name} missing pricing field"
        assert isinstance(spec["cents_per_million_tokens"], int), (
            f"Model {model_name} pricing must be int (cents)"
        )


def test_pricing_matches_expected_values() -> None:
    """Test that pricing matches verified OpenAI values."""
    spec_large = get_model_spec("text-embedding-3-large")
    spec_small = get_model_spec("text-embedding-3-small")

    # Verified pricing from OpenAI (as of 2025-10-23)
    # text-embedding-3-large: $0.13/1M tokens = 13 cents
    # text-embedding-3-small: $0.02/1M tokens = 2 cents
    assert spec_large["cents_per_million_tokens"] == 13
    assert spec_small["cents_per_million_tokens"] == 2
