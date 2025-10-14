"""Integration tests for search command E2E workflow.

Tests complete pipeline: index → search with real results.
Validates that all components work together correctly.
"""

import os
import re
from pathlib import Path

import pytest

from gitctx.cli.main import app


@pytest.mark.vcr()
@pytest.mark.skip(reason="Requires cassette recording - see TASK-0001.3.2.5 notes")
def test_full_pipeline_index_then_search(e2e_git_repo, e2e_cli_runner, monkeypatch):
    """Test complete pipeline: index → search with real results.

    NOTE: This test requires VCR cassettes to be recorded first with a real API key.
    Recording workflow:
        direnv exec . uv run pytest tests/e2e/test_search_integration.py --vcr-record=once

    This test verifies the complete E2E workflow but is skipped in regular CI until
    cassettes are recorded and committed.
    """
    # Set API key for indexing (VCR will record/replay)
    monkeypatch.setenv("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-test-key"))

    os.chdir(e2e_git_repo)

    # Index the repository
    result = e2e_cli_runner.invoke(app, ["index"])
    assert result.exit_code == 0, f"Index failed: {result.output}"

    # Verify index created
    assert Path(".gitctx").exists(), "Index directory not created"

    # Search for content
    result = e2e_cli_runner.invoke(app, ["search", "function", "definition"])
    assert result.exit_code == 0, f"Search failed: {result.output}"

    # Verify result format: "{count} results in {duration:.2f}s"
    # Example: "5 results in 1.23s" or "0 results in 0.42s"
    pattern = r"\d+ results in \d+\.\d{2}s"
    assert re.search(pattern, result.stdout), f"Expected format '{pattern}' in: {result.stdout}"


@pytest.mark.vcr()
@pytest.mark.skip(reason="Requires cassette recording - see TASK-0001.3.2.5 notes")
def test_search_empty_result_set_exit_zero(e2e_git_repo, e2e_cli_runner, monkeypatch):
    """Test that empty results return exit 0 (not an error).

    NOTE: This test requires VCR cassettes to be recorded first with a real API key.
    Recording workflow:
        direnv exec . uv run pytest tests/e2e/test_search_integration.py --vcr-record=once
    """
    # Set API key for indexing (VCR will record/replay)
    monkeypatch.setenv("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-test-key"))

    os.chdir(e2e_git_repo)

    # Index first
    result = e2e_cli_runner.invoke(app, ["index"])
    assert result.exit_code == 0

    # Search for non-existent content
    result = e2e_cli_runner.invoke(app, ["search", "nonexistent_function_xyz_123"])
    assert result.exit_code == 0  # Success, just no results
    assert "0 results in" in result.stdout
