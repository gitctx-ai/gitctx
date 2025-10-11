"""Pytest fixtures for storage unit tests."""

from collections.abc import Callable
from pathlib import Path

import pytest

from gitctx.core.models import BlobLocation, Embedding


@pytest.fixture
def lancedb_store(tmp_path: Path):
    """Create a fresh LanceDBStore in a temporary directory.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        LanceDBStore instance with empty database
    """
    from gitctx.storage.lancedb_store import LanceDBStore

    db_path = tmp_path / ".gitctx" / "lancedb"
    return LanceDBStore(db_path)


@pytest.fixture
def mock_embedding() -> Callable[[str, str, int], Embedding]:
    """Factory for creating test Embedding objects.

    Returns:
        Callable that creates Embedding with specified blob_sha, content, chunk_index
    """

    def _create_embedding(
        blob_sha: str = "a" * 40,
        content: str = "def foo():\n    pass",
        chunk_index: int = 0,
        language: str = "python",
    ) -> Embedding:
        return Embedding(
            vector=[0.1] * 3072,  # 3072-dim vector for text-embedding-3-large
            chunk_content=content,
            token_count=len(content.split()),
            blob_sha=blob_sha,
            chunk_index=chunk_index,
            start_line=1,
            end_line=2,
            total_chunks=1,
            language=language,
            model="text-embedding-3-large",
        )

    return _create_embedding


@pytest.fixture
def mock_blob_location() -> Callable[[str, str, bool], BlobLocation]:
    """Factory for creating test BlobLocation objects.

    Returns:
        Callable that creates BlobLocation with specified commit_sha, file_path, is_head
    """

    def _create_location(
        commit_sha: str = "b" * 40, file_path: str = "src/main.py", is_head: bool = True
    ) -> BlobLocation:
        return BlobLocation(
            commit_sha=commit_sha,
            file_path=file_path,
            author_name="Test Author",
            author_email="test@example.com",
            commit_date=1234567890,
            commit_message="Initial commit",
            is_head=is_head,
            is_merge=False,
        )

    return _create_location


@pytest.fixture
def isolated_env(monkeypatch):
    """Mock environment variables to prevent git config access during tests.

    This fixture ensures tests don't accidentally access the user's real git
    configuration, SSH keys, or other sensitive data.
    """
    # Mock HOME to prevent SSH key access
    monkeypatch.setenv("HOME", "/tmp/fake-home")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test Author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test Author")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
