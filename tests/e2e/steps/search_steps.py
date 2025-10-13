"""Step definitions for search command E2E tests."""

from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when


@pytest.fixture
def search_context() -> dict[str, Any]:
    """Store search test context between steps.

    Context keys used:
    - repo_path: Path - Path to test repository
    - query_cache: dict - Cached queries
    - api_key: str - OpenAI API key
    - custom_env: dict - Custom environment variables
    """
    return {}


# ===== Given Steps =====


@given("an indexed repository")
def indexed_repository(
    e2e_git_isolation_env: dict[str, Any],
    search_context: dict[str, Any],
    context: dict[str, Any],
    e2e_cli_runner,
    monkeypatch,
) -> None:
    """Create and index a test repository."""
    import subprocess
    from pathlib import Path

    # Create test repository with sample files
    repo_path = Path.cwd() / "test_repo"
    repo_path.mkdir(exist_ok=True)

    # Add sample Python file
    (repo_path / "auth.py").write_text("""def authenticate_user(username, password):
    '''Authenticate user with credentials.'''
    return validate_credentials(username, password)

def validate_credentials(username, password):
    '''Validate user credentials against database.'''
    return check_database(username, password)
""")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        env={
            **e2e_git_isolation_env,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )

    # Store repo_path in context for subsequent steps
    context["repo_path"] = repo_path
    search_context["repo_path"] = repo_path

    # Index the repository
    from gitctx.cli.main import app

    monkeypatch.chdir(repo_path)
    result = e2e_cli_runner.invoke(app, ["index"])
    assert result.exit_code == 0, f"Index failed: {result.stdout}"


# Environment variable steps are handled by cli_steps.py:
# - @given('environment variable "{var}" is "{value}"')
# This includes support for "$ENV" token to pull from real environment


@given(parsers.parse('query "{query_text}" was previously searched'))
def query_previously_searched(
    query_text: str,
    e2e_git_isolation_env: dict[str, Any],
    search_context: dict[str, Any],
) -> None:
    """Simulate a query that was previously searched and cached.

    Implement in TASK-0001.3.1.4: Run gitctx search once to populate cache, then verify cache hit.
    """
    raise NotImplementedError(
        "Implement in TASK-0001.3.1.4 - Run gitctx search to cache query embedding"
    )


@given(parsers.parse('a file "{file_path}" with {token_count:d} tokens'))
def file_with_tokens(
    file_path: str,
    token_count: int,
    search_context: dict[str, Any],
) -> None:
    """Verify fixture file exists with specified token count."""
    from pathlib import Path

    import tiktoken

    # Check file exists
    fixture_path = Path(file_path)
    if not fixture_path.exists():
        # Create the fixture file if it doesn't exist
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        # Generate text with approximately token_count tokens
        # Each "word " is roughly 1 token
        content = "word " * (token_count // 1)
        fixture_path.write_text(content)

    # Verify token count
    content = fixture_path.read_text()
    encoder = tiktoken.get_encoding("cl100k_base")
    actual_count = len(encoder.encode(content))

    # Allow some tolerance (within 10%)
    tolerance = token_count * 0.1
    assert abs(actual_count - token_count) <= tolerance, (
        f"Expected ~{token_count} tokens, got {actual_count}"
    )

    # Store path for later use
    search_context["fixture_file"] = fixture_path


# ===== When Steps =====


@when(parsers.parse('I run gitctx with query from file "{file_path}"'))
def run_gitctx_with_query_from_file(
    file_path: str,
    e2e_git_isolation_env: dict[str, Any],
    context: dict[str, Any],
    e2e_cli_runner,
    monkeypatch,
) -> None:
    """Run gitctx search with query loaded from file."""
    from pathlib import Path

    from gitctx.cli.main import app

    # Read query from file
    query_file = Path(file_path)
    query = query_file.read_text().strip()

    # Check if custom env vars were set by previous @given steps
    if "custom_env" in context:
        for key, value in context["custom_env"].items():
            monkeypatch.setenv(key, value)
        context.pop("custom_env")

    # Change to repo directory if provided
    cwd = context.get("repo_path")
    if cwd:
        monkeypatch.chdir(cwd)

    # Run search command
    result = e2e_cli_runner.invoke(app, ["search", query])

    # Store result in context
    context["result"] = result
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr if hasattr(result, "stderr") else ""
    context["exit_code"] = result.exit_code


# ===== Then Steps =====


@then("results should be displayed")
def results_displayed(context: dict[str, Any]) -> None:
    """Verify search results are displayed in output."""
    output = context.get("stdout", "")

    # Check for mock result patterns (from search.py mock implementation)
    # Results should show file paths and scores
    assert any(
        pattern in output
        for pattern in [
            "src/auth/login.py",
            "src/auth/middleware.py",
            "docs/authentication.md",
            "tests/test_auth.py",
            ".py:",  # Generic file pattern
            "results in",  # Result summary
        ]
    ), f"Expected search results in output, got: {output}"
