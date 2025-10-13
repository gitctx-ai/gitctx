"""Query embedding generation with caching."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np
import openai
import requests.exceptions  # type: ignore[import-untyped]
import tiktoken

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

    def embed_query(self, query: str) -> np.ndarray:  # type: ignore[no-any-unimported]
        """Generate or retrieve cached query embedding.

        Args:
            query: Query text to embed

        Returns:
            numpy array of shape (dimensions,)

        Raises:
            ValidationError: If query validation fails
        """
        # Validate query
        self._validate_query(query)

        # Check cache
        cache_key = hashlib.sha256(f"{query}{self.model_name}".encode()).hexdigest()
        cached_vector = self.store.get_query_embedding(cache_key)
        if cached_vector is not None:
            return cached_vector  # type: ignore[no-any-return]

        # Generate embedding with error handling
        try:
            embedder = get_embedder(self.model_name, self.settings)
            query_vector = embedder.embed_query(query)
        except openai.RateLimitError as err:
            raise EmbeddingError("API rate limit exceeded. Wait 60 seconds and retry.") from err
        except openai.APIStatusError as err:
            if err.status_code >= 500:
                raise EmbeddingError("OpenAI API unavailable. Retry in a few moments.") from err
            raise
        except requests.exceptions.Timeout as err:
            raise EmbeddingError("Request timeout after 30s. Check network and retry.") from err
        except requests.exceptions.ConnectionError as err:
            raise EmbeddingError("Cannot connect to OpenAI API. Verify network access.") from err

        # Cache result
        self.store.cache_query_embedding(cache_key, query, query_vector, self.model_name)

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
            raise ValidationError("Query cannot be empty")

        # Check not whitespace only
        if not query.strip():
            raise ValidationError("Query cannot be whitespace only")

        # Check token limit
        spec = get_model_spec(self.model_name)
        encoder = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoder.encode(query))

        if token_count > spec["max_tokens"]:
            raise ValidationError(
                f"Query exceeds {spec['max_tokens']} tokens (got {token_count}). "
                f"Try a shorter, more specific query."
            )
