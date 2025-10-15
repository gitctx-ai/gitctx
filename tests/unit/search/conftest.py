"""Search module test fixtures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from gitctx.storage.lancedb_store import LanceDBStore


@pytest.fixture
def settings() -> Mock:
    """Create mock GitCtxSettings instance."""
    mock_settings = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get.return_value = "fake-api-key"
    return mock_settings


@pytest.fixture
def store(tmp_path: Path) -> LanceDBStore:
    """Create test LanceDBStore instance."""
    db_path = tmp_path / ".gitctx" / "db" / "lancedb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return LanceDBStore(db_path)
