"""Model and embedding-specific errors."""

from gitctx.exceptions import GitCtxError


class ModelError(GitCtxError):
    """Base error for model operations."""


class DimensionMismatchError(ModelError):
    """Raised when embedding dimensions don't match expected dimensions.

    Examples:
        >>> raise DimensionMismatchError("Expected 3072 dimensions, got 1536")
    """


class NetworkError(GitCtxError):
    """Raised when network/API is unreachable after retries.

    Examples:
        >>> raise NetworkError("OpenAI API unavailable. Retry in a few moments.")
    """


class RateLimitError(ModelError):
    """Raised when API rate limit is exceeded after retries.

    Examples:
        >>> raise RateLimitError("API rate limit exceeded. Wait 60 seconds and retry.")
    """


class APIError(ModelError):
    """API request failed."""


class ModelNotFoundError(ModelError):
    """Model not found in registry."""
