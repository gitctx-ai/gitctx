"""Configuration-specific errors."""

from gitctx.exceptions import GitCtxError


class ConfigurationError(GitCtxError):
    """Raised when configuration is invalid or missing.

    Attributes:
        key: Optional config key that caused the error

    Examples:
        >>> raise ConfigurationError("API key missing", key="api_keys.openai")
    """

    def __init__(self, message: str, key: str | None = None):
        """Initialize configuration error.

        Args:
            message: Error message
            key: Optional config key that caused the error
        """
        super().__init__(message)
        self.key = key


class ValidationError(ConfigurationError):
    """Raised when configuration value fails validation.

    Examples:
        >>> raise ValidationError("chunk_size must be > 0", key="index.chunk_size")
    """

    pass
