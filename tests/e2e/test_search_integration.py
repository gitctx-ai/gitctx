"""Integration tests for search command E2E workflow.

Tests complete pipeline: index → search with real results.
Validates that all components work together correctly.
"""

import os
import re
from pathlib import Path

import pytest

from gitctx.cli.main import app

# Apply VCR to entire module (covers both tests and fixtures)
pytestmark = pytest.mark.vcr


def test_full_pipeline_index_then_search(context, request):
    """Test complete pipeline: index → search with real results.

    NOTE: This test requires VCR cassettes to be recorded first with a real API key.
    Recording workflow:
        direnv exec . uv run pytest tests/e2e/test_search_integration.py --vcr-record=once

    This test verifies the complete E2E workflow but is skipped in regular CI until
    cassettes are recorded and committed.
    """

    # CRITICAL: Read API key BEFORE loading any fixtures that might clear it
    # Use `or` to handle both None and empty string -> defaults to test key for VCR
    api_key = os.environ.get("OPENAI_API_KEY") or "sk-test-key"

    # NOW load fixtures (lazy loading to control order)
    e2e_indexed_repo = request.getfixturevalue("e2e_indexed_repo")
    e2e_cli_runner = request.getfixturevalue("e2e_cli_runner")

    # Save current directory
    original_dir = os.getcwd()

    try:
        # Change to indexed repo directory (matching fixture pattern)
        os.chdir(e2e_indexed_repo)

        # Verify index created
        assert (Path.cwd() / ".gitctx" / "db" / "lancedb").exists(), "Index directory not created"

        # Set API key for searching (VCR will record/replay) - auto-merged by e2e_cli_runner
        context["custom_env"] = {"OPENAI_API_KEY": api_key}

        # Search for content
        result = e2e_cli_runner.invoke(app, ["search", "function", "definition"])

        # Clean up context
        context.pop("custom_env", None)

        assert result.exit_code == 0, f"Search failed: {result.output}"

        # Verify result format: "{count} results in {duration:.2f}s"
        # Example: "5 results in 1.23s" or "0 results in 0.42s"
        pattern = r"\d+ results in \d+\.\d{2}s"
        assert re.search(pattern, result.stdout), f"Expected format '{pattern}' in: {result.stdout}"
    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_search_empty_result_set_exit_zero(context, request):
    """Test that empty results return exit 0 (not an error).

    NOTE: This test requires VCR cassettes to be recorded first with a real API key.
    Recording workflow:
        direnv exec . uv run pytest tests/e2e/test_search_integration.py --vcr-record=once
    """
    # CRITICAL: Read API key BEFORE loading any fixtures that might clear it
    # Use `or` to handle both None and empty string -> defaults to test key for VCR
    api_key = os.environ.get("OPENAI_API_KEY") or "sk-test-key"

    # NOW load fixtures (lazy loading to control order)
    e2e_indexed_repo = request.getfixturevalue("e2e_indexed_repo")
    e2e_cli_runner = request.getfixturevalue("e2e_cli_runner")

    # Save current directory
    original_dir = os.getcwd()

    try:
        # Change to indexed repo directory (matching fixture pattern)
        os.chdir(e2e_indexed_repo)

        # Set API key for searching (VCR will record/replay) - auto-merged by e2e_cli_runner
        context["custom_env"] = {"OPENAI_API_KEY": api_key}

        # Search for content unlikely to match (random UUID-like string)
        result = e2e_cli_runner.invoke(app, ["search", "zzz_uuid_12345_abcdef_nonexistent_xyz"])

        # Clean up context
        context.pop("custom_env", None)

        # Even with no matches, should return exit code 0 (not an error)
        assert result.exit_code == 0, f"Search should succeed even with 0 results: {result.output}"
        # Verify it shows results format (either "0 results" or "N results")
        pattern = r"\d+ results in \d+\.\d{2}s"
        assert re.search(pattern, result.stdout), f"Expected results format in: {result.stdout}"
    finally:
        # Restore original directory
        os.chdir(original_dir)
