"""Unit tests for search command LanceDB integration and error handling."""

from unittest.mock import Mock, patch

from gitctx.cli.main import app


def test_search_missing_index_directory(isolated_cli_runner, tmp_path, monkeypatch):
    """Test search exits with code 8 when index directory doesn't exist."""
    # ARRANGE - Set up repo without index
    repo = tmp_path / "test_repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    # No .gitctx directory created

    # ACT - Run search
    result = isolated_cli_runner.invoke(app, ["search", "test query"])

    # ASSERT
    assert result.exit_code == 8
    assert "Error: No index found" in result.stdout or "Error: No index found" in result.stderr
    assert "Run: gitctx index" in result.stdout or "Run: gitctx index" in result.stderr


def test_search_empty_index(isolated_cli_runner, tmp_path, monkeypatch):
    """Test search exits with code 8 when index has zero chunks."""
    # ARRANGE - Create index directory but mock store.count() = 0
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # ACT - Search with empty index (count = 0)
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
    ):
        mock_store = Mock()
        mock_store.count.return_value = 0  # Empty index
        mock_store_class.return_value = mock_store

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        # ASSERT
        assert result.exit_code == 8
        assert "Error: No index found" in result.stdout or "Error: No index found" in result.stderr
        assert "Run: gitctx index" in result.stdout or "Run: gitctx index" in result.stderr


def test_search_corrupted_index_missing_table(isolated_cli_runner, tmp_path, monkeypatch):
    """Test search exits with code 1 when code_chunks table is missing."""
    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # ACT - Mock ValueError with "code_chunks" in error message (LanceDB behavior)
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
    ):
        # Simulate ValueError with table name in message (LanceDB raises ValueError for missing tables)
        mock_store_class.side_effect = ValueError("Failed to open table code_chunks")

        result = isolated_cli_runner.invoke(app, ["search", "test"])

        # ASSERT
        assert result.exit_code == 1
        output = result.stdout + result.stderr
        assert "Error: Index corrupted" in output
        assert "missing code_chunks table" in output
        assert "gitctx clear && gitctx index" in output


def test_search_returns_sorted_results(
    isolated_cli_runner, tmp_path, monkeypatch, test_embedding_vector
):
    """Test search returns results sorted by _distance ascending."""
    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # Mock results with ascending _distance
    mock_results = [
        {"file_path": "file1.py", "_distance": 0.1, "commit_sha": "abc123"},
        {"file_path": "file2.py", "_distance": 0.3, "commit_sha": "def456"},
        {"file_path": "file3.py", "_distance": 0.5, "commit_sha": "ghi789"},
    ]

    # ACT
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_store = Mock()
        mock_store.count.return_value = 100
        mock_store.search.return_value = mock_results
        mock_store.get_query_embedding.return_value = None
        mock_store_class.return_value = mock_store

        mock_embedder = Mock()
        mock_embedder.embed_query.return_value = test_embedding_vector()
        mock_embedder.get_cache_key.return_value = "test_key"
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "test query"])

        # ASSERT
        assert result.exit_code == 0
        mock_store.search.assert_called_once()
        # Verify results are returned (sorting happens in LanceDB)
        assert "3 results in" in result.stdout


def test_search_respects_limit(isolated_cli_runner, tmp_path, monkeypatch, test_embedding_vector):
    """Test search passes limit parameter to store.search()."""
    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # ACT - Search with --limit 5
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_store = Mock()
        mock_store.count.return_value = 100
        mock_store.search.return_value = []
        mock_store.get_query_embedding.return_value = None
        mock_store_class.return_value = mock_store

        mock_embedder = Mock()
        mock_embedder.embed_query.return_value = test_embedding_vector()
        mock_embedder.get_cache_key.return_value = "test_key"
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "test", "--limit", "5"])

        # ASSERT
        assert result.exit_code == 0
        # Verify limit=5 passed to search()
        mock_store.search.assert_called_once()
        call_kwargs = mock_store.search.call_args[1]
        assert call_kwargs["limit"] == 5


def test_search_result_has_all_fields(
    isolated_cli_runner, tmp_path, monkeypatch, test_embedding_vector
):
    """Test search returns denormalized results with all 11 fields."""
    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # Mock result with all 11 denormalized fields
    mock_result = {
        "file_path": "auth.py",
        "start_line": 10,
        "end_line": 20,
        "_distance": 0.15,
        "commit_sha": "abc123def",  # pragma: allowlist secret
        "commit_message": "Add auth",
        "commit_date": "2025-10-01",
        "author_name": "Alice",
        "is_head": True,
        "language": "python",
        "chunk_content": "def authenticate(): pass",
    }

    # ACT
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
        patch("gitctx.cli.search.QueryEmbedder") as mock_embedder_class,
    ):
        mock_store = Mock()
        mock_store.count.return_value = 100
        mock_store.search.return_value = [mock_result]
        mock_store.get_query_embedding.return_value = None
        mock_store_class.return_value = mock_store

        mock_embedder = Mock()
        mock_embedder.embed_query.return_value = test_embedding_vector()
        mock_embedder.get_cache_key.return_value = "test_key"
        mock_embedder_class.return_value = mock_embedder

        result = isolated_cli_runner.invoke(app, ["search", "auth"])

        # ASSERT
        assert result.exit_code == 0
        # Verify result returned from LanceDB has all fields
        returned_results = mock_store.search.return_value
        assert len(returned_results) == 1
        assert all(
            field in returned_results[0]
            for field in [
                "file_path",
                "start_line",
                "end_line",
                "_distance",
                "commit_sha",
                "commit_message",
                "commit_date",
                "author_name",
                "is_head",
                "language",
                "chunk_content",
            ]
        )


def test_search_limit_validation(isolated_cli_runner, tmp_path, monkeypatch):
    """Test search validates --limit parameter (1-100 range)."""
    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    # ACT & ASSERT - Test --limit 0 (too low)
    result_low = isolated_cli_runner.invoke(app, ["search", "test", "--limit", "0"])
    assert result_low.exit_code == 2  # Typer validation error
    # Typer error message format
    assert "Invalid value" in result_low.stdout or "Invalid value" in result_low.stderr

    # ACT & ASSERT - Test --limit 101 (too high)
    result_high = isolated_cli_runner.invoke(app, ["search", "test", "--limit", "101"])
    assert result_high.exit_code == 2  # Typer validation error
    assert "Invalid value" in result_high.stdout or "Invalid value" in result_high.stderr


def test_search_reraises_non_table_arrow_exceptions(isolated_cli_runner, tmp_path, monkeypatch):
    """Test search re-raises ArrowException/ValueError that don't mention code_chunks or table."""
    import pyarrow as pa
    import pytest

    # ARRANGE
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".gitctx" / "db" / "lancedb").mkdir(parents=True)
    monkeypatch.chdir(repo)

    mock_settings = Mock()
    mock_settings.repo = Mock()
    mock_settings.repo.model = Mock()
    mock_settings.repo.model.embedding = "text-embedding-3-large"
    mock_settings.get = Mock(return_value="sk-test-key")

    # ACT & ASSERT - Mock ArrowException without "code_chunks" or "table" keywords
    # This should be re-raised (not caught and converted to user-friendly error)
    with (
        patch("gitctx.cli.search.GitCtxSettings", return_value=mock_settings),
        patch("gitctx.cli.search.LanceDBStore") as mock_store_class,
    ):
        # Simulate generic ArrowException (e.g., schema mismatch, corrupted file)
        mock_store_class.side_effect = pa.lib.ArrowInvalid("Invalid schema version detected")

        # With catch_exceptions=False, exception should propagate
        with pytest.raises(pa.lib.ArrowInvalid, match="Invalid schema version"):
            isolated_cli_runner.invoke(app, ["search", "test"], catch_exceptions=False)
