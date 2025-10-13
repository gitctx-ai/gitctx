"""Base provider class with common functionality."""

from gitctx.models.registry import ModelSpec, get_model_spec


class BaseProvider:
    """Abstract base for all model providers.

    Provides common functionality for embedding providers:
    - Model specification loading
    - Token limit access
    - Dimension count access

    Examples:
        >>> provider = BaseProvider("text-embedding-3-large")
        >>> provider.max_tokens
        8191
        >>> provider.dimensions
        3072
    """

    def __init__(self, model_name: str) -> None:
        """Initialize provider with model name.

        Args:
            model_name: Model identifier (e.g., "text-embedding-3-large")

        Raises:
            ValueError: If model not in registry
        """
        self.model_name = model_name
        self.spec: ModelSpec = get_model_spec(model_name)

    @property
    def max_tokens(self) -> int:
        """Maximum token limit for this model."""
        return self.spec["max_tokens"]

    @property
    def dimensions(self) -> int:
        """Embedding dimension count."""
        return self.spec["dimensions"]

    @property
    def provider(self) -> str:
        """Provider name (e.g., 'openai')."""
        return self.spec["provider"]
