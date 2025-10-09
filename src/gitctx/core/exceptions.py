"""Exception classes for gitctx core components."""


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class DimensionMismatchError(Exception):
    """Raised when embedding dimensions don't match expected dimensions."""

    pass


class NetworkError(Exception):
    """Raised when network/API is unreachable after retries."""

    pass


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded after retries."""

    pass
