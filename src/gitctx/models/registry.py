"""Model metadata registry for embedding models."""

from typing import TypedDict


class ModelSpec(TypedDict):
    """Metadata for an embedding model.

    Attributes:
        dimensions: Embedding vector dimensions
        max_tokens: Maximum tokens per embedding request
        provider: Provider name (e.g., "openai", "ollama")
    """

    dimensions: int
    max_tokens: int
    provider: str


MODELS: dict[str, ModelSpec] = {
    "text-embedding-3-large": {
        "dimensions": 3072,
        "max_tokens": 8191,
        "provider": "openai",
    },
    "text-embedding-3-small": {
        "dimensions": 1536,
        "max_tokens": 8191,
        "provider": "openai",
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
