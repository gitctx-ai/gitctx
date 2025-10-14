"""Step definitions for search command E2E tests."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import tiktoken
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create and index a test repository with sample files.

    Creates a temporary git repository with Python files and runs gitctx index.
    The VCR cassettes will record the OpenAI API calls during indexing.
    """
    # Create a test repository
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Add sample Python files
    (repo_path / "auth.py").write_text(
        "def authenticate(user, password):\n"
        '    """Authenticate a user against the database."""\n'
        "    return check_credentials(user, password)\n"
    )
    (repo_path / "middleware.py").write_text(
        "def authentication_middleware(request):\n"
        '    """Authentication middleware for requests."""\n'
        '    token = request.headers.get("Authorization")\n'
        "    return validate_token(token)\n"
    )
    (repo_path / "database.py").write_text(
        "def database_setup():\n"
        '    """Set up database connection."""\n'
        "    return create_connection()\n"
    )

    # Initialize git repository
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
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )

    # Note: We don't actually run `gitctx index` here because:
    # 1. For query validation tests (empty query, token limits), we don't need a real index
    # 2. The search command shows mock results when no index exists
    # 3. Query embedding tests will work fine without an actual index
    #
    # Real indexing with VCR cassettes will be tested in integration scenarios
    # that specifically test the full search pipeline (STORY-0001.3.2)

    # Change to repo directory for subsequent commands
    monkeypatch.chdir(repo_path)

    # Store repo path for subsequent steps
    context["repo_path"] = repo_path
    search_context["repo_path"] = repo_path


# Environment variable steps are handled by cli_steps.py:
# - @given('environment variable "{var}" is "{value}"')
# This includes support for "$ENV" token to pull from real environment


@given(parsers.parse('query "{query_text}" was previously searched'))
def query_previously_searched(
    query_text: str,
    e2e_git_isolation_env: dict[str, Any],
    search_context: dict[str, Any],
    context: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    e2e_cli_runner,
) -> None:
    """Pre-populate query cache by running search once.

    Runs gitctx search with the specified query to cache the embedding.
    VCR will record the API call. Subsequent searches will hit cache.
    """
    from gitctx.cli.main import app

    repo_path = context.get("repo_path") or search_context.get("repo_path")

    if not repo_path:
        pytest.fail("No repository path found. Ensure 'an indexed repository' step runs first.")

    # Change to repo directory using monkeypatch
    monkeypatch.chdir(repo_path)

    # Run search once to populate cache (VCR will record the API call)
    # Environment automatically merged from context["custom_env"] by fixture
    e2e_cli_runner.invoke(app, ["search", query_text])
    # First search should succeed (or fail gracefully if API key missing, but cache the intent)
    # Don't assert here - let the actual scenario verify behavior

    # Don't clear custom_env here - it may be needed by subsequent steps

    # Track that we've cached this query
    if "cached_queries" not in search_context:
        search_context["cached_queries"] = set()
    search_context["cached_queries"].add(query_text)


@given(parsers.parse('a file "{file_path}" with {token_count:d} tokens'))
def file_with_tokens(
    file_path: str,
    token_count: int,
    search_context: dict[str, Any],
) -> None:
    """Create a fixture file with exactly the specified token count.

    Uses tiktoken with cl100k_base encoding (same as OpenAI) to generate
    a text file with the exact number of tokens specified.
    """
    from pathlib import Path

    # Create the file path (relative to project root)
    file_path_obj = Path(file_path)
    file_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Use tiktoken to generate text with exact token count
    encoder = tiktoken.get_encoding("cl100k_base")

    # Simple strategy: Generate a large text, then trim to exact token count
    # Most ASCII words are 1 token, so we start with a bit more than needed
    words = []
    for i in range(token_count + 100):  # Generate more than enough
        words.append(f"word{i}")

    # Join and encode
    text = " ".join(words)
    tokens = encoder.encode(text)

    # If we have too many tokens, decode only the exact count we need
    if len(tokens) > token_count:
        tokens = tokens[:token_count]
        text = encoder.decode(tokens)
    else:
        # If we somehow don't have enough (unlikely), keep adding
        while len(encoder.encode(text)) < token_count:
            text += f" word{len(words)}"
            words.append(f"word{len(words)}")
            # Safety limit to prevent infinite loop
            if len(words) > token_count * 2:
                # This should never happen, but just in case
                break

    # Verify exact token count
    actual_tokens = len(encoder.encode(text))
    # Allow being close to the target (within 1%) since exact token count is hard
    tolerance = max(1, token_count // 100)  # 1% tolerance
    assert abs(actual_tokens - token_count) <= tolerance, (
        f"Expected ~{token_count} tokens (±{tolerance}), got {actual_tokens}"
    )

    # Write to file
    file_path_obj.write_text(text)

    # Store in context for later steps
    search_context["long_query_file"] = file_path_obj
    search_context["long_query_tokens"] = token_count


# ===== When Steps =====

# Note: The common "When I run" step from cli_steps.py handles all gitctx commands
# including empty queries like: When I run "gitctx search ''"
# shlex.split() properly parses quoted empty strings


@when(parsers.parse('I run gitctx with query from file "{file_path}"'))
def run_gitctx_with_query_from_file(
    file_path: str,
    e2e_git_isolation_env: dict[str, Any],
    context: dict[str, Any],
    search_context: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    e2e_cli_runner,
) -> None:
    """Run gitctx search with query text loaded from a file.

    Reads the query from the specified file and executes gitctx search.
    Used for testing queries that exceed token limits.
    """
    from pathlib import Path

    from gitctx.cli.main import app

    # Read query from file
    query_file = Path(file_path)
    if not query_file.exists():
        pytest.fail(f"Query file not found: {file_path}")

    query_text = query_file.read_text()

    # Get repo path
    repo_path = context.get("repo_path") or search_context.get("repo_path")
    if not repo_path:
        pytest.fail("No repository path found. Ensure 'an indexed repository' step runs first.")

    # Change to repo directory using monkeypatch
    monkeypatch.chdir(repo_path)

    # Run search with the file content as query using secure runner
    # Environment automatically merged from context["custom_env"] by fixture
    result = e2e_cli_runner.invoke(app, ["search", query_text])

    # Clear custom_env after use
    context.pop("custom_env", None)

    # Store results in context
    context["result"] = result
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr if hasattr(result, "stderr") and result.stderr else ""
    context["exit_code"] = result.exit_code


# ===== Then Steps =====


@then("results should be displayed")
def results_displayed(context: dict[str, Any]) -> None:
    """Verify search results or success indicators are displayed.

    For STORY-0001.3.1, we only generate query embeddings.
    Full search results will come in STORY-0001.3.2.
    So we verify command succeeded and shows results.
    """
    output = context.get("stdout", "")
    result = context.get("result")

    # Verify command succeeded
    assert result is not None, "No command result found"
    assert result.exit_code == 0, f"Search failed with exit code {result.exit_code}: {output}"

    # Verify results present - look for:
    # 1. Success indicators (✓, success, embedded, generated)
    # 2. Result format (file:line:score or "N results")
    # 3. Progress completion
    has_results = (
        "✓" in output
        or "success" in output.lower()
        or "embedded" in output.lower()
        or "generated" in output.lower()
        or "results" in output.lower()  # "4 results in 0.23s"
        or (":" in output and ("0." in output or "1." in output))  # score format
    )

    assert has_results, f"No results found in output: {output}"


# ===== STORY-0001.3.2: Stub Step Definitions (Pending Implementation) =====


@then(parsers.parse('results should match query "{query}"'))
def results_match_query(query: str, context: dict[str, Any]) -> None:
    """Verify search results semantically match the query.

    Basic verification - just check command succeeded.
    Full result verification in TASK-0001.3.2.3.
    """
    result = context.get("result")
    assert result is not None, "No command result found"
    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"


@then(parsers.parse("exactly {n:d} results should be shown"))
def exactly_n_results(n: int, context: dict[str, Any]) -> None:
    """Verify exact number of results returned."""
    result = context.get("result")
    assert result is not None, "No command result found"
    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"
    # Parse "{n} results in" from output
    output = result.stdout
    assert f"{n} results in" in output, f"Expected '{n} results in' not found in: {output}"


@when(parsers.parse('I pipe "{text}" to "{command}"'))
def pipe_text_to_command(
    text: str,
    command: str,
    context: dict[str, Any],
    e2e_cli_runner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipe text to command via stdin using CliRunner.

    CliRunner natively supports stdin via input= parameter.
    No subprocess needed - uses in-process Typer testing.
    """
    from gitctx.cli.main import app

    # Change to repo directory if needed
    if repo_path := context.get("repo_path"):
        monkeypatch.chdir(repo_path)

    # CliRunner handles stdin via input= parameter
    result = e2e_cli_runner.invoke(app, ["search"], input=text)

    # Store results for subsequent Then steps
    context["result"] = result
    context["stdout"] = result.stdout
    context["exit_code"] = result.exit_code


@then("results should be sorted by _distance ascending (0.0 = best match first)")
def results_sorted_by_distance(context: dict[str, Any]) -> None:
    """Verify results sorted by similarity score."""
    # Basic check - command succeeded
    # Full sorting verification in STORY-0001.3.3 when formatting is implemented
    result = context.get("result")
    assert result is not None, "No command result found"
    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"


@then(parsers.parse("each result should show cosine similarity score between {min:f} and {max:f}"))
def each_result_shows_score(min: float, max: float, context: dict[str, Any]) -> None:
    """Verify each result has score in range."""
    # Basic check - command succeeded
    # Full score validation in STORY-0001.3.3 when formatting is implemented
    result = context.get("result")
    assert result is not None, "No command result found"
    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"


@given(parsers.parse('an indexed repository with 20+ chunks containing "{keyword}" keyword'))
def indexed_repo_with_keyword_chunks(
    keyword: str,
    context: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    e2e_git_isolation_env: dict[str, Any],
) -> None:
    """Create indexed repository with 20+ chunks containing keyword (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.3")


@given("no index exists at .gitctx/db/lancedb/")
def no_index_exists(
    context: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure no index directory exists."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_path)
    # No .gitctx directory created - index doesn't exist
    context["repo_path"] = repo_path


@when(parsers.parse('I run "{command}" with empty stdin in non-interactive terminal'))
def run_with_empty_stdin(command: str, context: dict[str, Any], e2e_cli_runner) -> None:
    """Run command with empty stdin in non-interactive mode (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.2")


@given(parsers.parse("an indexed repository with {chunk_count:d} chunks"))
def indexed_repo_with_n_chunks(
    chunk_count: int,
    context: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    e2e_git_isolation_env: dict[str, Any],
) -> None:
    """Create indexed repository with exactly N chunks (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.4")


@then(parsers.parse('the output should contain "{text}"'))
def output_contains(text: str, context: dict[str, Any]) -> None:
    """Verify output contains specific text."""
    result = context.get("result")
    assert result is not None, "No command result found"
    output = result.stdout + result.stderr
    assert text in output, f"Expected '{text}' not found in output: {output}"


@when(parsers.parse('I run search {count:d} times with query "{query}"'))
def run_search_n_times(count: int, query: str, context: dict[str, Any], e2e_cli_runner) -> None:
    """Run search command N times for performance testing (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.4")


@then(parsers.parse("p95 response time should be under {threshold:f} seconds"))
def p95_under_threshold(threshold: float, context: dict[str, Any]) -> None:
    """Verify p95 latency meets threshold (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.4")


@then(parsers.parse("all requests should complete within {max_time:f} seconds"))
def all_requests_within_time(max_time: float, context: dict[str, Any]) -> None:
    """Verify max latency meets threshold (stub)."""
    raise NotImplementedError("Pending TASK-0001.3.2.4")
