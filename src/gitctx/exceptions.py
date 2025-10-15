"""Base exception for all gitctx errors."""


class GitCtxError(Exception):
    """Base exception for all gitctx errors.

    All domain-specific exceptions inherit from this base class,
    enabling catch-all error handling when needed.

    Examples:
        >>> try:
        ...     # gitctx operation
        ... except GitCtxError as e:
        ...     print(f"gitctx error: {e}")
    """
