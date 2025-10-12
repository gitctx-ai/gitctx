"""Unit tests for OpenAI embedder implementation."""

from unittest.mock import AsyncMock, patch

import pytest

from gitctx.core.exceptions import ConfigurationError, DimensionMismatchError
from gitctx.core.models import CodeChunk
from gitctx.core.protocols import Embedding


class TestOpenAIEmbedderInitialization:
    """Test OpenAIEmbedder initialization and configuration."""

    def test_init_with_valid_api_key(self, isolated_env):
        """Test initialization with valid sk-* API key."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(api_key="sk-test123")
        assert embedder is not None
        assert embedder._embeddings is not None

    def test_init_without_api_key_raises_config_error(self, isolated_env):
        """Test initialization without API key raises ConfigurationError."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        with pytest.raises(ConfigurationError) as exc_info:
            OpenAIEmbedder(api_key="")
        assert "OpenAI API key required" in str(exc_info.value)

    def test_init_configures_langchain_correctly(self, isolated_env):
        """Test LangChain configuration has correct model and dimensions."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(api_key="sk-test123", max_retries=5, show_progress=True)
        assert embedder._embeddings.model == "text-embedding-3-large"
        assert embedder._embeddings.dimensions == 3072
        assert embedder._embeddings.chunk_size == 2048
        assert embedder._embeddings.max_retries == 5


class TestOpenAIEmbedderEmbeddingGeneration:
    """Test embedding generation for code chunks."""

    @pytest.mark.anyio
    async def test_embed_single_chunk(self, isolated_env):
        """Test embedding generation for single chunk."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(
            content="def foo(): pass", start_line=1, end_line=1, token_count=5, metadata={}
        )

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}],
            "usage": {"total_tokens": 5},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks([chunk], "abc123")

        assert len(result) == 1
        assert isinstance(result[0], Embedding)
        assert len(result[0].vector) == 3072
        assert result[0].blob_sha == "abc123"
        assert result[0].chunk_index == 0

    @pytest.mark.anyio
    async def test_embed_multiple_chunks(self, isolated_env):
        """Test embedding generation for multiple chunks."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunks = [
            CodeChunk(content="chunk 1", start_line=1, end_line=1, token_count=10, metadata={}),
            CodeChunk(content="chunk 2", start_line=2, end_line=2, token_count=15, metadata={}),
        ]

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}, {"embedding": [0.2] * 3072}],
            "usage": {"total_tokens": 25},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks(chunks, "def456")

        assert len(result) == 2
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1


class TestOpenAIEmbedderErrorHandling:
    """Test error handling in OpenAIEmbedder."""

    @pytest.mark.anyio
    async def test_dimension_mismatch_raises_error(self, isolated_env):
        """Test wrong dimensions raise DimensionMismatchError."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(content="test", start_line=1, end_line=1, token_count=5, metadata={})

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 1536}],  # Wrong dimensions
            "usage": {"total_tokens": 5},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            with pytest.raises(DimensionMismatchError) as exc_info:
                await embedder.embed_chunks([chunk], "test_sha")

        assert "Expected 3072 dimensions" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_empty_chunks_returns_empty_list(self, isolated_env):
        """Test empty chunks list returns empty list."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(api_key="sk-test123")
        result = await embedder.embed_chunks([], "test_sha")
        assert result == []

    @pytest.mark.anyio
    async def test_api_error_propagates(self, isolated_env):
        """Test API errors bubble up correctly."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(content="test", start_line=1, end_line=1, token_count=5, metadata={})

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await embedder.embed_chunks([chunk], "test_sha")

        assert "API Error" in str(exc_info.value)


class TestOpenAIEmbedderCostCalculation:
    """Test cost estimation for embeddings."""

    def test_estimate_cost_formula(self, isolated_env):
        """Test cost calculation uses correct formula."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(api_key="sk-test123")
        assert embedder.estimate_cost(1_000_000) == 0.13
        assert embedder.estimate_cost(500_000) == 0.065
        assert embedder.estimate_cost(200) == pytest.approx(0.000026, rel=1e-6)

    def test_estimate_cost_zero_tokens(self, isolated_env):
        """Test cost estimation with zero tokens."""
        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(api_key="sk-test123")
        assert embedder.estimate_cost(0) == 0.0


class TestOpenAIEmbedderEdgeCases:
    """Test edge cases and special inputs."""

    @pytest.mark.anyio
    async def test_unicode_content(self, isolated_env):
        """Test handling of Unicode/non-ASCII content."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(
            content="def greet(): print('Hello 世界')",
            start_line=1,
            end_line=1,
            token_count=12,
            metadata={},
        )

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}],
            "usage": {"total_tokens": 12},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks([chunk], "unicode_sha")

        assert len(result) == 1
        assert result[0].token_count == 12


class TestOpenAIEmbedderAPITokenUsage:
    """Test actual API token usage tracking from OpenAI responses."""

    @pytest.mark.anyio
    async def test_captures_api_token_count_from_response(self, isolated_env):
        """Test that actual API token usage is captured from OpenAI response."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(
            content="test code", start_line=1, end_line=1, token_count=10, metadata={}
        )

        # Mock the OpenAI response with usage data
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}],
            "usage": {"total_tokens": 42},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks([chunk], "test_sha")

        assert len(result) == 1
        assert result[0].api_token_count == 42

    @pytest.mark.anyio
    async def test_uses_api_tokens_for_cost_calculation(self, isolated_env):
        """Test that cost is calculated from API tokens, not tiktoken estimate."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        # tiktoken says 10 tokens, but API actually used 50 tokens
        chunk = CodeChunk(content="test", start_line=1, end_line=1, token_count=10, metadata={})

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}],
            "usage": {"total_tokens": 50},
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks([chunk], "test_sha")

        # Cost should be based on 50 API tokens, not 10 tiktoken estimate
        expected_cost = (50 / 1_000_000) * 0.13
        assert result[0].cost_usd == pytest.approx(expected_cost)

    @pytest.mark.anyio
    async def test_handles_missing_usage_data_gracefully(self, isolated_env):
        """Test fallback to tiktoken when API doesn't return usage data."""
        from unittest.mock import MagicMock

        from gitctx.embeddings.openai_embedder import OpenAIEmbedder

        chunk = CodeChunk(content="test", start_line=1, end_line=1, token_count=10, metadata={})

        # Mock response without usage data
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "data": [{"embedding": [0.1] * 3072}]
            # No usage field
        }

        embedder = OpenAIEmbedder(api_key="sk-test123")
        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response
            result = await embedder.embed_chunks([chunk], "test_sha")

        # Should fall back to None for api_token_count
        assert result[0].api_token_count is None
        # Cost should use tiktoken estimate
        assert result[0].cost_usd == embedder.estimate_cost(10)
