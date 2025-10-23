"""Model metadata registry for embedding models."""

from typing import TypedDict


class ModelSpec(TypedDict):
    """Metadata for an embedding model.

    Attributes:
        dimensions: Embedding vector dimensions
        max_tokens: Maximum tokens per embedding request
        provider: Provider name (e.g., "openai", "ollama")
        cents_per_million_tokens: API cost in cents per 1M tokens
    """

    dimensions: int
    max_tokens: int
    provider: str
    cents_per_million_tokens: int


# Pricing Maintenance: Values verified against https://openai.com/api/pricing/
# Each entry includes "verified: YYYY-MM-DD" date.
# Update pricing when API costs change (check quarterly or when OpenAI announces changes).

MODELS: dict[str, ModelSpec] = {
    "text-embedding-3-large": {
        "dimensions": 3072,
        "max_tokens": 8191,
        "provider": "openai",
        "cents_per_million_tokens": 13,  # $0.13/1M tokens (verified: 2025-10-23)
    },
    "text-embedding-3-small": {
        "dimensions": 1536,
        "max_tokens": 8191,
        "provider": "openai",
        "cents_per_million_tokens": 2,  # $0.02/1M tokens (verified: 2025-10-23)
    },
}


def get_model_spec(name: str) -> ModelSpec:
    """Get model metadata or raise if unsupported.

    Args:
        name: Model name (e.g., "text-embedding-3-large")

    Returns:
        ModelSpec with dimensions, max_tokens, provider

    Raises:
        ValueError: If model name is not in registry

    Examples:
        >>> spec = get_model_spec("text-embedding-3-large")
        >>> spec["dimensions"]
        3072
    """
    if name not in MODELS:
        supported = ", ".join(MODELS.keys())
        raise ValueError(f"Unsupported model: {name}. Supported models: {supported}")
    return MODELS[name]
