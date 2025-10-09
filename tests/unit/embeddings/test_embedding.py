"""Unit tests for Embedding dataclass."""

from dataclasses import asdict

import pytest

from gitctx.core.protocols import Embedding


class TestEmbeddingDataclass:
    """Test Embedding dataclass structure and behavior."""

    def test_embedding_creation_with_all_fields(self):
        """Test creating Embedding with all required fields."""
        # ARRANGE & ACT
        embedding = Embedding(
            vector=[0.1, 0.2, 0.3],
            token_count=100,
            model="text-embedding-3-large",
            cost_usd=0.000013,
            blob_sha="abc123",
            chunk_index=0,
        )

        # ASSERT
        assert embedding.vector == [0.1, 0.2, 0.3]
        assert embedding.token_count == 100
        assert embedding.model == "text-embedding-3-large"
        assert embedding.cost_usd == 0.000013
        assert embedding.blob_sha == "abc123"
        assert embedding.chunk_index == 0

    def test_embedding_uses_primitive_types(self):
        """Test Embedding uses only primitive types (FFI-compatible)."""
        embedding = Embedding(
            vector=[0.1, 0.2],
            token_count=50,
            model="test-model",
            cost_usd=0.00001,
            blob_sha="sha256",
            chunk_index=1,
        )

        # ASSERT - All primitives, no numpy/Path
        assert isinstance(embedding.vector, list)
        assert all(isinstance(v, float) for v in embedding.vector)
        assert isinstance(embedding.token_count, int)
        assert isinstance(embedding.model, str)
        assert isinstance(embedding.cost_usd, float)
        assert isinstance(embedding.blob_sha, str)
        assert isinstance(embedding.chunk_index, int)

    def test_embedding_vector_dimensions(self):
        """Test Embedding accepts 3072-dimensional vectors."""
        vector_3072 = [0.1] * 3072
        embedding = Embedding(
            vector=vector_3072,
            token_count=200,
            model="text-embedding-3-large",
            cost_usd=0.000026,
            blob_sha="test_sha",
            chunk_index=0,
        )
        assert len(embedding.vector) == 3072

    def test_embedding_immutability(self):
        """Test Embedding is immutable (frozen dataclass)."""
        embedding = Embedding(
            vector=[0.1, 0.2],
            token_count=50,
            model="test-model",
            cost_usd=0.00001,
            blob_sha="sha",
            chunk_index=0,
        )

        # ASSERT - Should raise error on mutation (FrozenInstanceError or AttributeError)
        with pytest.raises((AttributeError, TypeError)):
            embedding.token_count = 100  # type: ignore

    def test_embedding_serialization(self):
        """Test Embedding can be serialized with asdict()."""
        embedding = Embedding(
            vector=[0.1, 0.2],
            token_count=50,
            model="test-model",
            cost_usd=0.00001,
            blob_sha="sha",
            chunk_index=0,
        )

        # ACT
        data = asdict(embedding)

        # ASSERT
        assert data["vector"] == [0.1, 0.2]
        assert data["token_count"] == 50
        assert data["model"] == "test-model"
