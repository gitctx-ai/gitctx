"""Unit tests for indexing pipeline signal handling and cost estimation."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from gitctx.indexing.pipeline import index_repository


def create_mock_blob_location(
    commit_sha: str = "test_commit",
    file_path: str = "test.py",
    is_head: bool = True,
    author_name: str = "Test Author",
    author_email: str = "test@example.com",
    commit_date: int = 1234567890,
    commit_message: str = "Test commit",
    is_merge: bool = False,
):
    """Helper to create mock BlobLocation with sensible defaults."""
    from gitctx.core.models import BlobLocation

    return BlobLocation(
        commit_sha=commit_sha,
        file_path=file_path,
        is_head=is_head,
        author_name=author_name,
        author_email=author_email,
        commit_date=commit_date,
        commit_message=commit_message,
        is_merge=is_merge,
    )


def create_mock_blob_record(
    sha: str = "test_sha",
    content: bytes = b"test content",
    locations: list | None = None,
):
    """Helper to create mock BlobRecord with sensible defaults."""
    from gitctx.core.models import BlobRecord

    if locations is None:
        locations = [create_mock_blob_location()]

    return BlobRecord(
        sha=sha,
        content=content,
        size=len(content),
        locations=locations,
    )


@pytest.mark.anyio
async def test_keyboard_interrupt_shows_interrupted_message(tmp_path, capsys):
    """Test that KeyboardInterrupt shows 'Interrupted' message and exits 130."""
    # Create a minimal test repo
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Mock settings
    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Mock CommitWalker to raise KeyboardInterrupt
    with patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls:
        mock_walker = Mock()
        mock_walker.walk_blobs.side_effect = KeyboardInterrupt()
        mock_walker_cls.return_value = mock_walker

        # Should raise SystemExit with code 130
        with pytest.raises(SystemExit) as exc_info:
            await index_repository(repo_path, mock_settings)

        assert exc_info.value.code == 130

    # Check stderr for "Interrupted" message
    captured = capsys.readouterr()
    assert "Interrupted" in captured.err

    # Verify finish() was called (check for output from ProgressReporter.finish())
    # finish() prints the summary, so we should see "Indexed" in output
    assert "Indexed" in captured.out


@pytest.mark.anyio
async def test_keyboard_interrupt_shows_partial_statistics(tmp_path, capsys):
    """Test that KeyboardInterrupt shows partial statistics before exiting."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    with patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls:
        mock_walker = Mock()
        # Simulate some work before interrupt
        mock_walker.walk_blobs.side_effect = KeyboardInterrupt()
        mock_walker_cls.return_value = mock_walker

        with pytest.raises(SystemExit) as exc_info:
            await index_repository(repo_path, mock_settings)

        assert exc_info.value.code == 130

    # Verify finish() was called - check for stats in output
    captured = capsys.readouterr()
    output = captured.out
    # finish() shows tokens and cost
    assert "Tokens:" in output
    assert "Cost:" in output


@pytest.mark.anyio
async def test_non_keyboard_interrupt_does_not_exit_130(tmp_path, capsys):
    """Test that other exceptions don't trigger special interrupt handling."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    with patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls:
        # Raise a different exception
        mock_walker = Mock()
        mock_walker.walk_blobs.side_effect = RuntimeError("Some error")
        mock_walker_cls.return_value = mock_walker

        # Should raise RuntimeError, not SystemExit
        with pytest.raises(RuntimeError, match="Some error"):
            await index_repository(repo_path, mock_settings)

    # finish() should still be called in finally block - check for output
    captured = capsys.readouterr()
    assert "Indexed" in captured.out


@pytest.mark.anyio
async def test_dry_run_shows_cost_estimation(tmp_path, capsys):
    """Test that dry_run=True shows cost estimation without indexing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Mock CostEstimator
    with patch("gitctx.indexing.pipeline.CostEstimator") as mock_estimator_cls:
        mock_estimator = Mock()
        mock_estimator.estimate_repo_cost.return_value = {
            "total_files": 10,
            "total_lines": 1000,
            "estimated_tokens": 5000,
            "estimated_cost": 0.0025,
            "min_cost": 0.002,
            "max_cost": 0.003,
        }
        mock_estimator_cls.return_value = mock_estimator

        # Call with dry_run=True
        await index_repository(repo_path, mock_settings, dry_run=True)

    # Verify cost estimation output
    captured = capsys.readouterr()
    assert "Files:        10" in captured.out
    assert "Lines:        1,000" in captured.out
    assert "Est. tokens:  5,000" in captured.out
    assert "Est. cost:    $0.0025" in captured.out
    assert "Range:        $0.0020 - $0.0030 (±20%)" in captured.out

    # Verify estimator was called
    mock_estimator.estimate_repo_cost.assert_called_once_with(repo_path)


@pytest.mark.anyio
async def test_dry_run_does_not_index(tmp_path):
    """Test that dry_run=True does not perform actual indexing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()

    # Mock CostEstimator
    with patch("gitctx.indexing.pipeline.CostEstimator") as mock_estimator_cls:
        mock_estimator = Mock()
        mock_estimator.estimate_repo_cost.return_value = {
            "total_files": 1,
            "total_lines": 10,
            "estimated_tokens": 100,
            "estimated_cost": 0.0001,
            "min_cost": 0.00008,
            "max_cost": 0.00012,
        }
        mock_estimator_cls.return_value = mock_estimator

        # Mock the actual indexing components - they should NOT be called
        with (
            patch("gitctx.core.commit_walker.CommitWalker") as mock_walker,
            patch("gitctx.core.chunker.LanguageAwareChunker") as mock_chunker,
            patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder") as mock_embedder,
        ):
            # Call with dry_run=True
            await index_repository(repo_path, mock_settings, dry_run=True)

            # Verify indexing components were NOT instantiated
            mock_walker.assert_not_called()
            mock_chunker.assert_not_called()
            mock_embedder.assert_not_called()


@pytest.mark.anyio
async def test_empty_repository_exits_early(tmp_path, capsys):
    """Test that empty repository (no blobs) exits gracefully."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500

    with (
        patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls,
        patch("gitctx.core.chunker.LanguageAwareChunker"),
        patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder"),
        patch("gitctx.storage.lancedb_store.LanceDBStore"),
    ):
        # Mock walker to return no blobs
        mock_walker = Mock()
        mock_walker.walk_blobs.return_value = iter([])  # Empty iterator
        mock_walker_cls.return_value = mock_walker

        await index_repository(repo_path, mock_settings)

    # Verify "No files to index" message
    captured = capsys.readouterr()
    assert "No files to index" in captured.out


@pytest.mark.anyio
async def test_indexing_processes_single_blob(tmp_path, capsys):
    """Test that indexing processes a single blob successfully."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Create mock blob record
    mock_blob = create_mock_blob_record(
        sha="abc123",
        content=b"def authenticate(user):\n    pass",
        locations=[create_mock_blob_location(commit_sha="def456", file_path="auth.py")],
    )

    # Create mock chunks
    from gitctx.core.models import CodeChunk

    mock_chunk = CodeChunk(
        content="def authenticate(user):\n    pass",
        start_line=1,
        end_line=2,
        token_count=10,
        metadata={},
    )

    # Create mock protocol embedding
    from gitctx.core.protocols import Embedding as ProtocolEmbedding

    mock_proto_embedding = ProtocolEmbedding(
        vector=[0.1] * 1536,
        chunk_index=0,
        token_count=10,
        cost_usd=0.0001,
        blob_sha="abc123",
        model="text-embedding-3-small",
    )

    with (
        patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls,
        patch("gitctx.core.chunker.LanguageAwareChunker") as mock_chunker_cls,
        patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder") as mock_embedder_cls,
        patch("gitctx.storage.lancedb_store.LanceDBStore") as mock_store_cls,
        patch("gitctx.core.language_detection.detect_language_from_extension") as mock_detect_lang,
    ):
        # Mock walker
        mock_walker = Mock()
        mock_walker.walk_blobs.return_value = iter([mock_blob])
        mock_walker.get_stats.return_value = Mock(commits_seen=1, blobs_indexed=1)
        mock_walker_cls.return_value = mock_walker

        # Mock chunker
        mock_chunker = Mock()
        mock_chunker.chunk_file.return_value = [mock_chunk]
        mock_chunker_cls.return_value = mock_chunker

        # Mock embedder with async support
        mock_embedder = Mock()
        mock_embedder.embed_chunks = AsyncMock(return_value=[mock_proto_embedding])
        mock_embedder_cls.return_value = mock_embedder

        # Mock store
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        # Mock language detection
        mock_detect_lang.return_value = "python"

        await index_repository(repo_path, mock_settings)

        # Verify components were called
        mock_chunker.chunk_file.assert_called_once()
        mock_embedder.embed_chunks.assert_called_once()
        mock_store.add_chunks_batch.assert_called_once()

    # Verify output shows completion
    captured = capsys.readouterr()
    assert "Indexed" in captured.out


@pytest.mark.anyio
async def test_indexing_handles_unicode_decode_error(tmp_path, capsys):
    """Test that binary files (UnicodeDecodeError) are skipped gracefully."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Create mock blob with binary content (cannot decode)
    mock_blob = create_mock_blob_record(
        sha="binary123",
        content=b"\xff\xfe\x00\x00",  # Binary data
        locations=[create_mock_blob_location(commit_sha="def456", file_path="image.png")],
    )

    with (
        patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls,
        patch("gitctx.core.chunker.LanguageAwareChunker"),
        patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder"),
        patch("gitctx.storage.lancedb_store.LanceDBStore"),
    ):
        # Mock walker
        mock_walker = Mock()
        mock_walker.walk_blobs.return_value = iter([mock_blob])
        mock_walker.get_stats.return_value = Mock(commits_seen=1, blobs_indexed=1)
        mock_walker_cls.return_value = mock_walker

        await index_repository(repo_path, mock_settings)

    # Verify error was recorded (check output for "Errors: 1")
    captured = capsys.readouterr()
    assert "Errors: 1" in captured.err


@pytest.mark.anyio
async def test_indexing_handles_processing_error(tmp_path, capsys):
    """Test that processing errors are caught and logged."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Create mock blob
    mock_blob = create_mock_blob_record(
        sha="error123",
        content=b"def test(): pass",
        locations=[create_mock_blob_location(commit_sha="def456", file_path="test.py")],
    )

    with (
        patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls,
        patch("gitctx.core.chunker.LanguageAwareChunker") as mock_chunker_cls,
        patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder"),
        patch("gitctx.storage.lancedb_store.LanceDBStore"),
        patch("gitctx.core.language_detection.detect_language_from_extension") as mock_detect_lang,
    ):
        # Mock walker
        mock_walker = Mock()
        mock_walker.walk_blobs.return_value = iter([mock_blob])
        mock_walker.get_stats.return_value = Mock(commits_seen=1, blobs_indexed=1)
        mock_walker_cls.return_value = mock_walker

        # Mock chunker to raise an error
        mock_chunker = Mock()
        mock_chunker.chunk_file.side_effect = RuntimeError("Chunking failed")
        mock_chunker_cls.return_value = mock_chunker

        # Mock language detection
        mock_detect_lang.return_value = "python"

        await index_repository(repo_path, mock_settings)

    # Verify error message printed
    captured = capsys.readouterr()
    assert "Error processing test.py" in captured.err
    assert "Chunking failed" in captured.err
    assert "Errors: 1" in captured.err


@pytest.mark.anyio
async def test_indexing_processes_multiple_chunks(tmp_path):
    """Test that indexing handles files with multiple chunks."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    mock_settings = Mock()
    mock_settings.repo.index.chunk_overlap_ratio = 0.1
    mock_settings.repo.index.max_chunk_tokens = 500
    mock_settings.get.return_value = "sk-test"

    # Create mock blob
    from gitctx.core.models import CodeChunk
    from gitctx.core.protocols import Embedding as ProtocolEmbedding

    mock_blob = create_mock_blob_record(
        sha="large_file",
        content=b"def func1():\n    pass\n\ndef func2():\n    pass\n",
        locations=[create_mock_blob_location(commit_sha="commit1", file_path="large.py")],
    )

    # Create multiple chunks
    mock_chunks = [
        CodeChunk(
            content="def func1():\n    pass", start_line=1, end_line=2, token_count=10, metadata={}
        ),
        CodeChunk(
            content="def func2():\n    pass", start_line=3, end_line=4, token_count=10, metadata={}
        ),
    ]

    # Create multiple embeddings
    mock_embeddings = [
        ProtocolEmbedding(
            vector=[0.1] * 1536,
            chunk_index=0,
            token_count=10,
            cost_usd=0.0001,
            blob_sha="large_file",
            model="text-embedding-3-small",
        ),
        ProtocolEmbedding(
            vector=[0.2] * 1536,
            chunk_index=1,
            token_count=10,
            cost_usd=0.0001,
            blob_sha="large_file",
            model="text-embedding-3-small",
        ),
    ]

    with (
        patch("gitctx.core.commit_walker.CommitWalker") as mock_walker_cls,
        patch("gitctx.core.chunker.LanguageAwareChunker") as mock_chunker_cls,
        patch("gitctx.embeddings.openai_embedder.OpenAIEmbedder") as mock_embedder_cls,
        patch("gitctx.storage.lancedb_store.LanceDBStore") as mock_store_cls,
        patch("gitctx.core.language_detection.detect_language_from_extension") as mock_detect_lang,
    ):
        # Mock walker
        mock_walker = Mock()
        mock_walker.walk_blobs.return_value = iter([mock_blob])
        mock_walker.get_stats.return_value = Mock(commits_seen=1, blobs_indexed=1)
        mock_walker_cls.return_value = mock_walker

        # Mock chunker
        mock_chunker = Mock()
        mock_chunker.chunk_file.return_value = mock_chunks
        mock_chunker_cls.return_value = mock_chunker

        # Mock embedder with async support
        mock_embedder = Mock()
        mock_embedder.embed_chunks = AsyncMock(return_value=mock_embeddings)
        mock_embedder_cls.return_value = mock_embedder

        # Mock store
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        # Mock language detection
        mock_detect_lang.return_value = "python"

        await index_repository(repo_path, mock_settings)

        # Verify store received both embeddings
        assert mock_store.add_chunks_batch.call_count == 1
        call_args = mock_store.add_chunks_batch.call_args
        stored_embeddings = call_args.kwargs["embeddings"]
        assert len(stored_embeddings) == 2
