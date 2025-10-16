"""Unit tests for OpenAIEmbedder cost distribution logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gitctx.indexing.types import CodeChunk
from gitctx.models.providers.openai import OpenAIEmbedder


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""

    def _create_response(num_chunks: int, total_tokens: int):
        """Create response with specified chunks and tokens."""
        return {
            "data": [{"embedding": [0.1] * 3072} for _ in range(num_chunks)],
            "usage": {"total_tokens": total_tokens},
        }

    return _create_response


@pytest.mark.anyio
class TestCostDistribution:
    """Test cost distribution across chunks in a batch."""

    async def test_batch_cost_distribution_equal_chunks(self, mock_openai_response):
        """Cost is distributed proportionally across equal-sized chunks."""
        # ARRANGE - 3 chunks, 200 tokens each = 600 total
        chunks = [
            CodeChunk(
                content="x" * 800,
                start_line=1,
                end_line=10,
                token_count=200,
                metadata={"chunk_index": i},
            )
            for i in range(3)
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response: 600 total tokens
        mock_response = mock_openai_response(num_chunks=3, total_tokens=600)

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - Each chunk gets 1/3 of total cost
            total_cost = sum(e.cost_usd for e in embeddings)
            expected_total = (600 / 1_000_000) * 0.13  # $0.000078

            # Verify total matches expected
            assert abs(total_cost - expected_total) < 0.0000001

            # Verify each chunk gets equal share (200/600 = 1/3)
            expected_per_chunk = expected_total / 3
            for emb in embeddings:
                assert abs(emb.cost_usd - expected_per_chunk) < 0.0000001

    async def test_batch_cost_distribution_unequal_chunks(self, mock_openai_response):
        """Cost is distributed proportionally across unequal-sized chunks."""
        # ARRANGE - 3 chunks with different token counts
        chunks = [
            CodeChunk(content="x" * 400, start_line=1, end_line=10, token_count=100, metadata={}),
            CodeChunk(content="x" * 800, start_line=11, end_line=20, token_count=200, metadata={}),
            CodeChunk(content="x" * 1200, start_line=21, end_line=30, token_count=300, metadata={}),
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response: 600 total tokens
        mock_response = mock_openai_response(num_chunks=3, total_tokens=600)

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - Total cost correct
            total_cost = sum(e.cost_usd for e in embeddings)
            expected_total = (600 / 1_000_000) * 0.13  # $0.000078
            assert abs(total_cost - expected_total) < 0.0000001

            # Verify proportional distribution
            # Chunk 0: 100/600 = 16.67% of cost
            # Chunk 1: 200/600 = 33.33% of cost
            # Chunk 2: 300/600 = 50.00% of cost
            assert abs(embeddings[0].cost_usd - (expected_total * 100 / 600)) < 0.0000001
            assert abs(embeddings[1].cost_usd - (expected_total * 200 / 600)) < 0.0000001
            assert abs(embeddings[2].cost_usd - (expected_total * 300 / 600)) < 0.0000001

    async def test_single_chunk_batch(self, mock_openai_response):
        """Single chunk gets full cost (no division errors)."""
        # ARRANGE
        chunks = [
            CodeChunk(
                content="x" * 2400,
                start_line=1,
                end_line=10,
                token_count=600,
                metadata={},
            )
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response: 600 tokens
        mock_response = mock_openai_response(num_chunks=1, total_tokens=600)

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - Single chunk gets full cost
            expected_cost = (600 / 1_000_000) * 0.13
            assert len(embeddings) == 1
            assert abs(embeddings[0].cost_usd - expected_cost) < 0.0000001

    async def test_empty_batch_returns_empty_list(self):
        """Empty batch returns empty list without errors."""
        # ARRANGE
        embedder = OpenAIEmbedder(api_key="test-key")

        # ACT
        embeddings = await embedder.embed_chunks([], "test_sha")

        # ASSERT
        assert embeddings == []

    async def test_fallback_to_tiktoken_when_no_api_tokens(self):
        """Falls back to tiktoken estimates when api_token_count is None."""
        # ARRANGE
        chunks = [
            CodeChunk(content="x" * 400, start_line=1, end_line=10, token_count=100, metadata={}),
            CodeChunk(content="x" * 800, start_line=11, end_line=20, token_count=200, metadata={}),
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response WITHOUT usage data
        mock_response = {
            "data": [
                {"embedding": [0.1] * 3072},
                {"embedding": [0.2] * 3072},
            ],
            # No "usage" key - simulates API not returning token count
        }

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - Uses tiktoken estimates
            # Chunk 0: 100 tokens → cost = (100 / 1M) * 0.13
            # Chunk 1: 200 tokens → cost = (200 / 1M) * 0.13
            expected_cost_0 = (100 / 1_000_000) * 0.13
            expected_cost_1 = (200 / 1_000_000) * 0.13

            assert abs(embeddings[0].cost_usd - expected_cost_0) < 0.0000001
            assert abs(embeddings[1].cost_usd - expected_cost_1) < 0.0000001

    async def test_zero_tokens_edge_case(self, mock_openai_response):
        """Handles zero tokens gracefully (no division by zero)."""
        # ARRANGE
        chunks = [
            CodeChunk(content="", start_line=1, end_line=1, token_count=0, metadata={}),
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response: 0 tokens
        mock_response = mock_openai_response(num_chunks=1, total_tokens=0)

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - No division by zero, cost is 0
            assert len(embeddings) == 1
            assert embeddings[0].cost_usd == 0.0


class TestEstimateCost:
    """Test estimate_cost() method directly."""

    def test_estimate_cost_1_million_tokens(self):
        """1 million tokens costs $0.13."""
        embedder = OpenAIEmbedder(api_key="test-key")
        cost = embedder.estimate_cost(1_000_000)
        assert abs(cost - 0.13) < 0.0000001

    def test_estimate_cost_1000_tokens(self):
        """1000 tokens costs $0.00013."""
        embedder = OpenAIEmbedder(api_key="test-key")
        cost = embedder.estimate_cost(1000)
        assert abs(cost - 0.00013) < 0.0000001

    def test_estimate_cost_zero_tokens(self):
        """Zero tokens costs $0."""
        embedder = OpenAIEmbedder(api_key="test-key")
        cost = embedder.estimate_cost(0)
        assert cost == 0.0
