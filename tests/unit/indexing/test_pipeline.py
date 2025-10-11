"""Unit tests for indexing pipeline signal handling."""

from unittest.mock import Mock, patch

import pytest

from gitctx.indexing.pipeline import index_repository


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
