"""Query embedding generation with caching."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np
import openai
import tiktoken
from numpy.typing import NDArray

from gitctx.config.errors import ConfigurationError
from gitctx.models.factory import get_embedder
from gitctx.models.registry import get_model_spec
from gitctx.search.errors import EmbeddingError, ValidationError

if TYPE_CHECKING:
    from gitctx.config.settings import GitCtxSettings
    from gitctx.storage.lancedb_store import LanceDBStore


class QueryEmbedder:
    """Generates query embeddings with validation and caching."""

    def __init__(self, settings: GitCtxSettings, store: LanceDBStore) -> None:
        """Initialize query embedder.

        Args:
            settings: Application settings
            store: LanceDB store for caching
        """
        self.settings = settings
        self.store = store
        self.model_name = settings.repo.model.embedding

    def get_cache_key(self, query: str) -> str:
        """Generate cache key for query.

        Args:
            query: Query text

        Returns:
            SHA256 hash of query + model name
        """
        return hashlib.sha256(f"{query}{self.model_name}".encode()).hexdigest()

    def embed_query(self, query: str) -> NDArray[np.floating]:  # type: ignore[no-any-unimported]
        """Generate or retrieve cached query embedding.

        Args:
            query: Query text to embed

        Returns:
            numpy array of shape (dimensions,) with float32 values

        Raises:
            ValidationError: If query validation fails
        """
        # Validate query
        self._validate_query(query)

        # Check cache
        cache_key = self.get_cache_key(query)
        cached_vector = self.store.get_query_embedding(cache_key)
        if cached_vector is not None:
            return cached_vector

        # Generate embedding with error handling
        try:
            embedder = get_embedder(self.model_name, self.settings)
            query_vector = embedder.embed_query(query)
        except openai.AuthenticationError as err:
            raise EmbeddingError(
                "API key rejected (invalid or revoked). "
                "Get new key at https://platform.openai.com/api-keys"
            ) from err
        except openai.RateLimitError as err:
            raise EmbeddingError(
                "API rate limit exceeded (429). Retry after 60 seconds or "
                "check usage limits at https://platform.openai.com/account/rate-limits"
            ) from err
        except openai.APITimeoutError as err:
            raise EmbeddingError(
                "Request timeout after 30 seconds. Verify internet connection and "
                "firewall settings. Retry with shorter query if issue persists."
            ) from err
        except openai.APIConnectionError as err:
            raise EmbeddingError("Cannot connect to OpenAI API. Verify network access.") from err
        except openai.APIStatusError as err:
            HTTP_SERVER_ERROR = 500  # 5xx status codes indicate server errors
            if err.status_code >= HTTP_SERVER_ERROR:
                raise EmbeddingError(
                    f"OpenAI API unavailable (HTTP {err.status_code}). Service may be down. "
                    "Check status at https://status.openai.com and retry in 1-2 minutes."
                ) from err
            # Re-raise unexpected status codes for visibility
            raise
        except ConfigurationError:
            # Re-raise configuration errors (e.g., missing API key)
            # so CLI can handle with exit code 4
            raise
        except Exception as err:
            # Safety net for unexpected errors
            raise EmbeddingError(f"Unexpected error during embedding generation: {err}") from err

        # Cache result
        self.store.cache_query_embedding(cache_key, query, query_vector, self.model_name)  # type: ignore[no-any-unimported]

        return query_vector

    def _validate_query(self, query: str) -> None:
        """Validate query input.

        Args:
            query: Query text to validate

        Raises:
            ValidationError: If query is invalid
        """
        # Check not empty
        if not query:
            raise ValidationError("Error: Query cannot be empty")

        # Check not whitespace only
        if not query.strip():
            raise ValidationError("Error: Query cannot be whitespace only")

        # Check token limit
        spec = get_model_spec(self.model_name)
        encoder = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoder.encode(query))

        if token_count > spec["max_tokens"]:
            raise ValidationError(
                f"Error: Query exceeds {spec['max_tokens']} tokens (got {token_count}). "
                f"Try a shorter, more specific query."
            )
