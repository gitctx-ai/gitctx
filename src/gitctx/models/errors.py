"""Model and embedding-specific errors."""

from gitctx.exceptions import GitCtxError


class DimensionMismatchError(GitCtxError):
    """Raised when embedding dimensions don't match expected dimensions.

    Examples:
        >>> raise DimensionMismatchError("Expected 3072 dimensions, got 1536")
    """

    pass


class NetworkError(GitCtxError):
    """Raised when network/API is unreachable after retries.

    Examples:
        >>> raise NetworkError("OpenAI API unavailable. Retry in a few moments.")
    """

    pass


class RateLimitError(GitCtxError):
    """Raised when API rate limit is exceeded after retries.

    Examples:
        >>> raise RateLimitError("API rate limit exceeded. Wait 60 seconds and retry.")
    """

    pass
