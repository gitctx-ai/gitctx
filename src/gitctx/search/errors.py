"""Search-specific errors."""

from __future__ import annotations

from gitctx.exceptions import GitCtxError


class SearchError(GitCtxError):
    """Base error for search operations."""


class ValidationError(SearchError):
    """Query validation error."""


class EmbeddingError(SearchError):
    """Embedding generation error."""


class QueryError(SearchError):
    """Query processing error."""
