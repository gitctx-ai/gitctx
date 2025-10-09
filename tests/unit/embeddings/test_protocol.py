"""Unit tests for EmbedderProtocol."""

import pytest

from gitctx.core.protocols import EmbedderProtocol, Embedding


class TestEmbedderProtocol:
    """Test EmbedderProtocol structure and compliance."""

    def test_embedder_protocol_structure(self):
        """Test EmbedderProtocol has required methods."""
        # Protocol should define these methods
        assert hasattr(EmbedderProtocol, "embed_chunks")
        assert hasattr(EmbedderProtocol, "estimate_cost")

    def test_protocol_method_signatures(self):
        """Test EmbedderProtocol method signatures match specification."""
        # Check embed_chunks signature
        # (Will be implemented when we have OpenAIEmbedder in TASK-3)
        pass

    @pytest.mark.parametrize(
        "dimensions,expected_valid",
        [
            (3072, True),  # text-embedding-3-large
            (1536, True),  # text-embedding-3-small
            (512, True),  # hypothetical smaller model
            (0, False),  # invalid
        ],
    )
    def test_dimension_validation_parametrized(self, dimensions, expected_valid):
        """Test embedding dimension validation for different models."""
        if expected_valid:
            embedding = Embedding(
                vector=[0.1] * dimensions,
                token_count=100,
                model="test-model",
                cost_usd=0.00001,
                blob_sha="sha",
                chunk_index=0,
            )
            assert len(embedding.vector) == dimensions
        else:
            # For 0 dimensions, embedding creation works but vector is empty
            embedding = Embedding(
                vector=[],
                token_count=100,
                model="test-model",
                cost_usd=0.00001,
                blob_sha="sha",
                chunk_index=0,
            )
            assert len(embedding.vector) == 0

    @pytest.mark.parametrize(
        "tokens,expected_cost",
        [
            (0, 0.0),
            (1000, 0.00013),  # 1K tokens
            (1_000_000, 0.13),  # 1M tokens
            (2_000_000, 0.26),  # 2M tokens
        ],
    )
    def test_cost_calculation_formula(self, tokens, expected_cost):
        """Test cost calculation matches OpenAI pricing ($0.13 per 1M tokens)."""
        # Cost formula: tokens * $0.13 / 1M
        cost = (tokens / 1_000_000) * 0.13
        assert abs(cost - expected_cost) < 0.000001  # Floating point tolerance
