"""Provider factory for model selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gitctx.config.errors import ConfigurationError
from gitctx.config.settings import GitCtxSettings
from gitctx.models.registry import get_model_spec

if TYPE_CHECKING:
    from gitctx.models.providers.openai import OpenAIProvider


def get_embedder(model_name: str, settings: GitCtxSettings) -> OpenAIProvider:
    """Get embedding provider for model.

    Args:
        model_name: Model identifier (e.g., "text-embedding-3-large")
        settings: Application settings

    Returns:
        Provider instance with embed_query and embed_documents methods

    Raises:
        ValueError: If model not supported
        ConfigurationError: If API key missing

    Examples:
        >>> from gitctx.config.settings import GitCtxSettings
        >>> settings = GitCtxSettings()
        >>> embedder = get_embedder("text-embedding-3-large", settings)
    """
    # Validate model exists in registry
    spec = get_model_spec(model_name)

    # Route to provider based on spec
    if spec["provider"] == "openai":
        # Get API key from settings
        api_key = settings.get("api_keys.openai")
        if not api_key:
            raise ConfigurationError(
                "Error: OpenAI API key not configured\n"
                "Set with: export OPENAI_API_KEY=sk-...\n"
                "Or run: gitctx config set api_keys.openai sk-..."
            )

        # Return OpenAIProvider
        from gitctx.models.providers.openai import OpenAIProvider

        return OpenAIProvider(model_name, api_key)

    # Unknown provider
    raise ValueError(f"Unknown provider: {spec['provider']}")
