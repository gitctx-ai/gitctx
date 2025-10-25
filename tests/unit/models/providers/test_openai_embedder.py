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


@pytest.mark.anyio
class TestBatchSplitting:
    """Test _embed_chunks_split() method for handling token limits."""

    async def test_embed_chunks_split_multiple_batches(self, mock_openai_response):
        """Chunks exceeding 300K tokens are split into multiple API calls."""
        # ARRANGE - 10 chunks of 40K tokens each = 400K total (exceeds 300K limit)
        chunks = [
            CodeChunk(
                content="x" * 160_000,  # ~40K tokens worth of content
                start_line=i * 100 + 1,
                end_line=(i + 1) * 100,
                token_count=40_000,
                metadata={"chunk_index": i},
            )
            for i in range(10)
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Track API calls
        call_count = 0
        call_args_list = []

        async def mock_embed_chunks(batch, blob_sha):
            """Mock embed_chunks to track calls and return embeddings."""
            nonlocal call_count
            call_count += 1
            call_args_list.append((len(batch), sum(c.token_count for c in batch)))

            # Return mock embeddings for this batch
            return [
                MagicMock(
                    vector=[0.1] * 3072,
                    cost_usd=0.0001,
                    token_count=chunk.token_count,
                    blob_sha=blob_sha,
                    chunk_index=i,
                )
                for i, chunk in enumerate(batch)
            ]

        # Patch embed_chunks (not _embed_chunks_split) to avoid recursion
        with patch.object(embedder, "embed_chunks", new=mock_embed_chunks):
            # ACT - Call _embed_chunks_split directly (simulates being called from embed_chunks)
            embeddings = await embedder._embed_chunks_split(chunks, "test_sha")

            # ASSERT - Should split into multiple batches
            # Batch 1: 7 chunks (280K tokens) - fits under 300K limit
            # Batch 2: 3 chunks (120K tokens)
            assert call_count == 2, f"Expected 2 API calls, got {call_count}"
            assert len(embeddings) == 10, "Should return all 10 embeddings"

            # Verify batch sizes
            batch1_chunks, batch1_tokens = call_args_list[0]
            batch2_chunks, batch2_tokens = call_args_list[1]

            assert batch1_chunks == 7, f"Batch 1 should have 7 chunks, got {batch1_chunks}"
            assert batch1_tokens == 280_000, f"Batch 1 should have 280K tokens, got {batch1_tokens}"
            assert batch2_chunks == 3, f"Batch 2 should have 3 chunks, got {batch2_chunks}"
            assert batch2_tokens == 120_000, f"Batch 2 should have 120K tokens, got {batch2_tokens}"

    async def test_embed_chunks_split_boundary_exactly_at_limit(self, mock_openai_response):
        """Chunks totaling exactly 300K tokens should NOT trigger split."""
        # ARRANGE - Exactly 300K tokens (at boundary, not exceeding)
        chunks = [
            CodeChunk(
                content="x" * 600_000,
                start_line=1,
                end_line=100,
                token_count=150_000,
                metadata={},
            ),
            CodeChunk(
                content="x" * 600_000,
                start_line=101,
                end_line=200,
                token_count=150_000,
                metadata={},
            ),
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock API response for normal path (not split)
        mock_response = mock_openai_response(num_chunks=2, total_tokens=300_000)

        with patch.object(
            embedder._embeddings.async_client, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(model_dump=lambda: mock_response)

            # ACT - Call embed_chunks (should NOT trigger split)
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - Should call API once (no split)
            assert mock_create.call_count == 1, "Should make single API call (no split at boundary)"
            assert len(embeddings) == 2

    async def test_embed_chunks_split_boundary_just_over_limit(self, mock_openai_response):
        """Chunks totaling 300K + 1 token should trigger split."""
        # ARRANGE - 300,001 tokens (just over limit)
        chunks = [
            CodeChunk(
                content="x" * 600_000,
                start_line=1,
                end_line=100,
                token_count=150_000,
                metadata={},
            ),
            CodeChunk(
                content="x" * 600_000,
                start_line=101,
                end_line=200,
                token_count=150_001,  # Just 1 token over
                metadata={},
            ),
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Track API calls
        call_count = 0

        async def mock_embed_chunks(batch, blob_sha):
            """Mock embed_chunks to track calls."""
            nonlocal call_count
            call_count += 1
            return [
                MagicMock(
                    vector=[0.1] * 3072,
                    cost_usd=0.0001,
                    token_count=chunk.token_count,
                    blob_sha=blob_sha,
                    chunk_index=i,
                )
                for i, chunk in enumerate(batch)
            ]

        # Patch embed_chunks to avoid recursion
        with patch.object(embedder, "embed_chunks", new=mock_embed_chunks):
            # ACT
            embeddings = await embedder._embed_chunks_split(chunks, "test_sha")

            # ASSERT - Should split (300,001 > 300,000)
            assert call_count == 2, "Should split into 2 batches when just over limit"
            assert len(embeddings) == 2

    async def test_embed_chunks_triggers_split_when_exceeds_limit(self, mock_openai_response):
        """Test embed_chunks() calls _embed_chunks_split when total > 300K tokens."""
        # ARRANGE - 400K tokens (exceeds limit, should trigger split at line 115)
        chunks = [
            CodeChunk(
                content="x" * 160_000,
                start_line=i * 100 + 1,
                end_line=(i + 1) * 100,
                token_count=40_000,
                metadata={},
            )
            for i in range(10)  # 10 * 40K = 400K tokens
        ]

        embedder = OpenAIEmbedder(api_key="test-key")

        # Mock _embed_chunks_split to verify it's called
        split_called = False

        async def mock_split(chunks_arg, blob_sha):
            nonlocal split_called
            split_called = True
            # Return mock embeddings
            return [
                MagicMock(
                    vector=[0.1] * 3072,
                    cost_usd=0.0001,
                    token_count=chunk.token_count,
                    blob_sha=blob_sha,
                    chunk_index=i,
                )
                for i, chunk in enumerate(chunks_arg)
            ]

        with patch.object(embedder, "_embed_chunks_split", new=mock_split):
            # ACT - Call embed_chunks (should trigger split at line 115)
            embeddings = await embedder.embed_chunks(chunks, "test_sha")

            # ASSERT - _embed_chunks_split was called
            assert split_called, "embed_chunks should call _embed_chunks_split when tokens > 300K"
            assert len(embeddings) == 10
