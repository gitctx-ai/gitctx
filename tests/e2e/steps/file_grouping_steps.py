"""BDD step definitions for file-grouped result presentation.

This module contains smoke test steps that verify user-visible behavior
(file grouping works, formats differ, filtering works), NOT implementation
details (exact chunk counts, specific scores, format strings).

Detailed format validation happens in unit tests (fast, deterministic).
BDD tests validate complete user workflow (index → search → format → output).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pytest_bdd import given, parsers, then, when

if TYPE_CHECKING:
    from pathlib import Path


# ============================================================================
# Given Steps - Test Data Setup
# ============================================================================


@given(parsers.parse('an indexed repository with files containing "{keyword}" keyword'))
def indexed_repo_with_keyword(
    keyword: str,
    e2e_indexed_repo_factory: Callable[..., Path],
    e2e_session_api_key: str,
    context: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create and index a repository with files containing the specified keyword.

    This step sets up test data for file grouping scenarios.
    """
    # Create test files with semantically rich content
    # Use the keyword extensively to ensure semantic match
    files = {
        f"src/{keyword}.py": f"""'''User {keyword} module with authentication functions.'''

def handle_{keyword}_request(username, password):
    '''Process user {keyword} request with credentials.

    This function handles the {keyword} workflow including:
    - Validating {keyword} credentials
    - Creating {keyword} session
    - Returning {keyword} token
    '''
    if not username or not password:
        raise ValueError("Username and password required for {keyword}")
    return perform_{keyword}(username, password)

def perform_{keyword}(username, password):
    '''{keyword.capitalize()} the user with the provided credentials.'''
    # {keyword.capitalize()} logic here
    session = create_{keyword}_session(username)
    return session

def create_{keyword}_session(username):
    '''Create a {keyword} session for the authenticated user.'''
    return {{"user": username, "{keyword}": True}}
""",
        f"lib/{keyword}_helper.py": f"""'''Helper utilities for user {keyword} operations.'''

class {keyword.capitalize()}Helper:
    '''Helper class for managing {keyword} processes.

    This class provides utilities for:
    - User {keyword} validation
    - {keyword.capitalize()} session management
    - {keyword.capitalize()} error handling
    '''

    def __init__(self):
        self.{keyword}_attempts = 0
        self.{keyword}_sessions = {{}}

    def validate_{keyword}_credentials(self, username, password):
        '''Validate {keyword} credentials for the user.'''
        self.{keyword}_attempts += 1
        return username and password and len(password) >= 8

    def process_{keyword}(self, username, password):
        '''{keyword.capitalize()} the user and create a session.'''
        if not self.validate_{keyword}_credentials(username, password):
            raise ValueError("Invalid {keyword} credentials")
        return self.{keyword}_sessions.get(username)
""",
    }

    # Create and index the repository
    repo_path = e2e_indexed_repo_factory(files=files, num_commits=1)

    # Store repo path for later steps
    context["repo_path"] = repo_path

    # Set up API key for search commands (auto-merged by e2e_cli_runner)
    context["custom_env"] = {"OPENAI_API_KEY": e2e_session_api_key}

    # Change to repo directory
    monkeypatch.chdir(repo_path)


@given("an indexed repository with multiple files")
def indexed_repo_with_multiple_files(
    e2e_indexed_repo_factory: Any,
    e2e_session_api_key: str,
    context: dict[str, Any],
    monkeypatch: Any,
) -> None:
    """Create and index a repository with multiple files for filtering tests.

    Creates files with different semantic distances to test score-based filtering.
    """
    # Create files with different semantic relevance to query "database connection"
    # File 1: High relevance (database connection implementation)
    # File 2: Medium relevance (database-related but different topic)
    # File 3: Low relevance (unrelated topic)
    files = {
        "src/db_connection.py": """'''Database connection pool manager.'''

def create_database_connection(host, port, username, password):
    '''Create a new database connection with connection pooling.

    This function establishes a database connection using the provided
    credentials and sets up connection pooling for better performance.
    '''
    pool = ConnectionPool(host=host, port=port)
    return pool.get_connection(username, password)

def close_database_connection(connection):
    '''Close the database connection and return it to the pool.'''
    connection.close()
    return True
""",
        "src/auth_db.py": """'''Database operations for authentication system.'''

def store_user_credentials(username, hashed_password):
    '''Store user credentials in the authentication database.

    Uses secure hashing and stores in the user authentication table.
    '''
    db = get_auth_database()
    db.insert({"username": username, "password": hashed_password})

def verify_user_credentials(username, password):
    '''Verify user credentials against the authentication database.'''
    db = get_auth_database()
    user = db.query({"username": username})
    return verify_password(user.password, password)
""",
        "src/utils.py": """'''General utility functions.'''

def format_timestamp(timestamp):
    '''Format Unix timestamp to human-readable string.'''
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def validate_email(email):
    '''Validate email address format using regex.'''
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None
""",
    }

    # Create and index the repository
    repo_path = e2e_indexed_repo_factory(files=files, num_commits=1)

    # Store repo path for later steps
    context["repo_path"] = repo_path

    # Set up API key for search commands (auto-merged by e2e_cli_runner)
    context["custom_env"] = {"OPENAI_API_KEY": e2e_session_api_key}

    # Change to repo directory
    monkeypatch.chdir(repo_path)


# ============================================================================
# When Steps - User Actions
# ============================================================================


@when(parsers.parse('I search for "{query}"'))
def search_for_query(
    query: str, e2e_cli_runner: Any, context: dict[str, Any], monkeypatch: Any
) -> None:
    """Execute a search command with the specified query.

    This is a generic search step that runs with default settings.
    For format-specific searches, use 'I search for "X" with --format=Y'.
    """
    from gitctx.cli.main import app  # noqa: PLC0415

    # Change to repo directory if provided
    repo_path = context.get("repo_path")
    if repo_path:
        monkeypatch.chdir(repo_path)

    # Run search with default settings
    # Use --min-similarity=-1.0 to ensure we get ALL results (BDD smoke test)
    # Note: 0.0 excludes results due to >= threshold check, -1.0 gets everything
    # Environment (API key) is automatically merged from context["custom_env"]
    result = e2e_cli_runner.invoke(app, ["search", query, "--min-similarity=-1.0"])

    # DON'T clear custom_env - we need it for subsequent searches in the scenario

    # Store result for later steps
    context["result"] = result
    context["stdout"] = result.stdout
    context["terse_output"] = result.stdout  # Also store as terse_output for format comparison
    context["query"] = query  # Store query for multi-format testing
    context["exit_code"] = result.exit_code


@when(parsers.parse('I search for "{query}" with default format (terse)'))
def search_with_default_format(
    query: str, e2e_cli_runner: Any, context: dict[str, Any], monkeypatch: Any
) -> None:
    """Execute a search command using the default terse format.

    This step explicitly tests the default format behavior (terse).
    """
    from gitctx.cli.main import app  # noqa: PLC0415

    # Change to repo directory if provided
    repo_path = context.get("repo_path")
    if repo_path:
        monkeypatch.chdir(repo_path)

    # Run search with default format (terse)
    # Use --min-similarity=-1.0 to ensure we get ALL results (BDD smoke test)
    # Note: 0.0 excludes results due to >= threshold check, -1.0 gets everything
    # Environment (API key) is automatically merged from context["custom_env"]
    result = e2e_cli_runner.invoke(app, ["search", query, "--min-similarity=-1.0"])

    # DON'T clear custom_env - we need it for subsequent searches in the scenario

    # Store result with terse-specific key
    context["result"] = result
    context["terse_output"] = result.stdout
    context["exit_code"] = result.exit_code


@when(parsers.parse('I search for "{query}" with --format={format}'))
def search_with_format(
    query: str, format: str, e2e_cli_runner: Any, context: dict[str, Any], monkeypatch: Any
) -> None:
    """Execute a search command with a specific output format.

    This step tests format selection (verbose, mcp, etc.).
    """
    from gitctx.cli.main import app  # noqa: PLC0415

    # Change to repo directory if provided
    repo_path = context.get("repo_path")
    if repo_path:
        monkeypatch.chdir(repo_path)

    # Run search with specified format
    # Use --min-similarity=-1.0 to ensure we get ALL results (BDD smoke test)
    # Note: 0.0 excludes results due to >= threshold check, -1.0 gets everything
    # Environment (API key) is automatically merged from context["custom_env"]
    result = e2e_cli_runner.invoke(
        app, ["search", query, f"--format={format}", "--min-similarity=-1.0"]
    )

    # DON'T clear custom_env - we might need it for subsequent searches in the scenario

    # Store result with format-specific key
    context["result"] = result
    context[f"{format}_output"] = result.stdout
    context[f"{format}_raw_output"] = result.raw_stdout  # With ANSI codes
    context["exit_code"] = result.exit_code


@when(parsers.parse("I search with --min-similarity={threshold:f}"))
def search_with_similarity_threshold(
    threshold: float, e2e_cli_runner: Any, context: dict[str, Any], monkeypatch: Any
) -> None:
    """Execute a search command with a similarity threshold filter.

    This step tests score-based filtering by setting --min-similarity flag.
    """
    from gitctx.cli.main import app  # noqa: PLC0415

    # Change to repo directory if provided
    repo_path = context.get("repo_path")
    if repo_path:
        monkeypatch.chdir(repo_path)

    # Run search with specified threshold
    # Use "database connection" query for Scenario 3 (matches test data)
    query = "database connection"
    result = e2e_cli_runner.invoke(app, ["search", query, f"--min-similarity={threshold}"])

    # Clear custom_env to prevent leaking to next command
    context.pop("custom_env", None)

    # Store result for later steps
    context["result"] = result
    context["stdout"] = result.stdout
    context["exit_code"] = result.exit_code
    context["threshold"] = threshold


# ============================================================================
# Then Steps - Assertions (Behavior-Based, Not Implementation Details)
# ============================================================================


@then("results should be grouped by file path")
def results_grouped_by_file(context: dict[str, Any]) -> None:
    """Verify that search results are organized by file path.

    Smoke test: Checks that file headers exist (file grouping is active).
    """
    stdout = context.get("stdout", "")

    # File-grouped format has file headers like "src/auth.py (N chunk):"
    # Verify at least one file header exists
    assert re.search(r"\S+\s+\(\d+\s+chunks?\):", stdout), (
        f"No file headers found in output (expected 'path (N chunk):' pattern):\n{stdout[:500]}"
    )


@then("each file should appear exactly once as a header")
def each_file_appears_once(context: dict[str, Any]) -> None:
    """Verify that file headers are not duplicated in output.

    Smoke test: Checks that each file path appears only once as a header.
    """
    stdout = context.get("stdout", "")

    # Extract all file headers: "path (N chunk):"
    file_headers = re.findall(r"(\S+)\s+\(\d+\s+chunks?\):", stdout)

    # Verify no duplicates
    unique_headers = set(file_headers)
    assert len(file_headers) == len(unique_headers), (
        f"Duplicate file headers found!\n"
        f"Total headers: {len(file_headers)}\n"
        f"Unique headers: {len(unique_headers)}\n"
        f"Headers: {file_headers}"
    )


@then("all chunks should appear under their respective file headers")
def chunks_under_file_headers(context: dict[str, Any]) -> None:
    """Verify that chunks are properly nested under file headers.

    Smoke test: Checks that indented chunk lines exist under headers.
    """
    stdout = context.get("stdout", "")

    # Split output into lines
    lines = stdout.split("\n")

    # Verify structure: file headers followed by indented chunk lines
    found_header = False
    found_chunk_under_header = False

    for line in lines:
        # File header: "path (N chunk):"
        if re.search(r"\S+\s+\(\d+\s+chunks?\):$", line):
            found_header = True
            continue

        # Chunk line: indented with line number (starts with whitespace, contains :LINE pattern)
        if found_header and line.startswith(" ") and re.search(r":\d+\s+", line):
            found_chunk_under_header = True
            break

    assert found_chunk_under_header, (
        f"No indented chunk lines found under file headers!\n"
        f"Expected indented lines like '  :1  0.95  ...' under 'path (N chunk):' headers.\n"
        f"Output:\n{stdout[:500]}"
    )


@then("this behavior should be consistent across terse, verbose, and MCP formats")
def consistent_across_formats(
    context: dict[str, Any], e2e_cli_runner: Any, monkeypatch: Any
) -> None:
    """Verify that file grouping works in all three output formats.

    Smoke test: Runs search in all 3 formats, verifies all show file grouping.
    """
    from gitctx.cli.main import app  # noqa: PLC0415

    # Terse output should already exist from the "When I search for X" step
    terse_output = context.get("terse_output", "")
    assert terse_output, "Terse format should produce output (from previous step)"

    # Run verbose and MCP searches to verify they also work
    repo_path = context.get("repo_path")
    if repo_path:
        monkeypatch.chdir(repo_path)

    # Get the original query from context (stored by previous steps)
    # Use "auth" as fallback if not found
    query = context.get("query", "auth")

    # Run verbose search
    verbose_result = e2e_cli_runner.invoke(
        app, ["search", query, "--format=verbose", "--min-similarity=-1.0"]
    )
    verbose_output = verbose_result.stdout

    # Run MCP search
    mcp_result = e2e_cli_runner.invoke(
        app, ["search", query, "--format=mcp", "--min-similarity=-1.0"]
    )
    mcp_output = mcp_result.stdout

    # Verify all formats produced output
    assert verbose_output, "Verbose format should produce output"
    assert mcp_output, "MCP format should produce output"

    # Verify all formats are different (not the same output)
    assert terse_output != verbose_output, "Terse and verbose should differ"
    assert terse_output != mcp_output, "Terse and MCP should differ"
    assert verbose_output != mcp_output, "Verbose and MCP should differ"

    # Each format should show file grouping in its own way
    assert "files:" in mcp_output, "MCP should have 'files:' in YAML frontmatter"


@then("I see compact output with one line per chunk")
def compact_output_one_line_per_chunk(context: dict[str, Any]) -> None:
    """Verify that terse format shows compact single-line chunks.

    Smoke test: Checks format style (single-line chunks with :LINE pattern),
    not exact formatting.
    """
    terse_output = context["terse_output"]
    exit_code = context.get("exit_code")

    # Debug: Print output and exit code if test fails
    if not terse_output:
        import pytest  # noqa: PLC0415

        result = context.get("result")
        error_msg = f"Search returned empty output. Exit code: {exit_code}"
        if result:
            error_msg += f"\nStdout: '{result.stdout}'"
            error_msg += f"\nStderr: '{getattr(result, 'stderr', 'N/A')}'"
        pytest.fail(error_msg)

    # Terse format has single-line chunks with :LINE_NUM pattern
    assert ":LINE" in terse_output or re.search(r":\d+", terse_output), (
        f"Terse output should contain line numbers with :LINE pattern. Got: {terse_output[:200]}"
    )

    # Should NOT have multi-line code blocks (no ```language markers)
    assert "```" not in terse_output, "Terse output should not have code blocks"


@then("I see full code blocks with ANSI color codes")
def full_code_blocks_with_ansi(context: dict[str, Any]) -> None:
    """Verify that verbose format shows multi-line code with ANSI colors.

    Smoke test: Checks for multi-line output and ANSI presence,
    not exact highlighting.
    """
    verbose_raw = context.get("verbose_raw_output", "")

    # Verbose format should have ANSI escape sequences
    # ANSI codes start with \x1b[ (ESC[)
    assert "\x1b[" in verbose_raw or "\033[" in verbose_raw, (
        "Verbose output should contain ANSI color codes"
    )

    # Should have multi-line content (Lines X-Y headers)
    assert "Lines " in context["verbose_output"], "Verbose output should have 'Lines X-Y' headers"


@then("output contains escape sequences for syntax highlighting")
def output_contains_syntax_highlighting(context: dict[str, Any]) -> None:
    """Verify that verbose output includes syntax highlighting escape sequences.

    Smoke test: Checks for ANSI escape codes presence.
    """
    verbose_raw = context.get("verbose_raw_output", "")

    # ANSI escape sequences for colors
    # Format: ESC[XXm where XX is color code
    ansi_pattern = r"\x1b\[\d+m"

    assert re.search(ansi_pattern, verbose_raw), (
        "Verbose output should contain ANSI escape sequences for syntax highlighting"
    )


@then("I get valid YAML frontmatter with file metadata")
def valid_yaml_frontmatter_with_file_metadata(context: dict[str, Any]) -> None:
    """Verify that MCP format produces valid YAML frontmatter with file-grouped metadata.

    Smoke test: Validates YAML structure and file grouping, not exact schema.
    """
    mcp_output = context["mcp_output"]

    # Extract YAML frontmatter (between --- markers)
    yaml_match = re.search(r"^---\n(.*?)\n---", mcp_output, re.DOTALL)
    assert yaml_match, "MCP output should have YAML frontmatter between --- markers"

    yaml_content = yaml_match.group(1)

    # Parse YAML to ensure it's valid
    parsed = yaml.safe_load(yaml_content)
    assert isinstance(parsed, dict), "YAML frontmatter should be a dictionary"

    # Should have "files" key (file-grouped format)
    assert "files" in parsed, "YAML should have 'files' key for file grouping"
    assert isinstance(parsed["files"], list), "'files' should be a list"

    # Each file entry should have required metadata
    if parsed["files"]:  # If there are results
        file_entry = parsed["files"][0]
        assert "file_path" in file_entry, "File entry should have 'file_path'"
        assert "language" in file_entry, "File entry should have 'language'"
        assert "chunks" in file_entry, "File entry should have 'chunks' count"
        assert "best_score" in file_entry, "File entry should have 'best_score'"

        # Type checks
        assert isinstance(file_entry["chunks"], int), "chunks should be an integer"
        assert isinstance(file_entry["best_score"], (int, float)), "best_score should be numeric"


@then("I see Markdown code blocks grouped by file")
def markdown_code_blocks_grouped_by_file(context: dict[str, Any]) -> None:
    """Verify that MCP format shows Markdown body with file-grouped code blocks.

    Smoke test: Checks for file headers and code blocks, not exact formatting.
    """
    mcp_output = context["mcp_output"]

    # Should have file headers in Markdown format: ## file_path (N chunks)
    assert re.search(r"##\s+\S+\s+\(\d+\s+chunks?\)", mcp_output), (
        "MCP output should have file headers like '## path (N chunks)'"
    )

    # Should have code blocks with language tags
    assert "```" in mcp_output, "MCP output should have Markdown code blocks"

    # Should have line number indicators: **Lines X-Y**
    assert re.search(r"\*\*Lines\s+\d+-\d+\*\*", mcp_output), (
        "MCP output should have line number headers like '**Lines 10-20**'"
    )

    # Should have score indicators: **Score:** X.XXX
    assert re.search(r"\*\*Score:\*\*\s+\d+\.\d+", mcp_output), (
        "MCP output should have score indicators like '**Score:** 0.920'"
    )


@then("only high-scoring chunks appear in results")
def only_high_scoring_chunks(context: dict[str, Any]) -> None:
    """Verify that low-scoring chunks are filtered out by threshold.

    Smoke test: Checks that all visible scores meet the threshold.
    """
    stdout = context.get("stdout", "")
    threshold = context.get("threshold", 0.0)

    # Extract scores from terse output (format: ":LINE  SCORE  ...")
    # Example: "  :1  0.95  🟢abc123  content"
    score_pattern = r":\d+\s+([\d.]+)\s+"
    scores = [float(match) for match in re.findall(score_pattern, stdout)]

    # If results exist, verify all scores meet threshold
    if scores:
        min_score = min(scores)
        assert min_score >= threshold, (
            f"Found chunk with score {min_score} below threshold {threshold}!\n"
            f"All scores: {scores}\n"
            f"Output:\n{stdout[:500]}"
        )


@then("low-scoring chunks are filtered out")
def low_scoring_chunks_filtered(context: dict[str, Any]) -> None:
    """Verify absence of low-scoring chunks in filtered results.

    Smoke test: Inverse of "only high-scoring chunks" - verifies filtering occurred.
    """
    stdout = context.get("stdout", "")
    threshold = context.get("threshold", 0.0)

    # Extract scores from terse output
    score_pattern = r":\d+\s+([\d.]+)\s+"
    scores = [float(match) for match in re.findall(score_pattern, stdout)]

    # Count how many chunks were filtered (are below threshold)
    # We can't know exact count without running unfiltered search,
    # but we can verify NO low scores appear in output
    low_scores = [s for s in scores if s < threshold]

    assert len(low_scores) == 0, (
        f"Found {len(low_scores)} chunks below threshold {threshold}!\n"
        f"Low scores: {low_scores}\n"
        f"All scores: {scores}\n"
        f"Output:\n{stdout[:500]}"
    )


@then("files with no chunks passing threshold are omitted entirely")
def files_with_no_passing_chunks_omitted(context: dict[str, Any]) -> None:
    """Verify that files with zero chunks after filtering are not shown.

    Smoke test: Verifies that file headers only appear if they have chunks.
    """
    stdout = context.get("stdout", "")

    # Extract all file headers: "path (N chunk):"
    file_headers = re.findall(r"(\S+)\s+\((\d+)\s+chunks?\):", stdout)

    # Verify all file headers have at least 1 chunk shown
    # (If a file had chunks but all filtered out, it shouldn't appear as header)
    for file_path, chunk_count_str in file_headers:
        chunk_count = int(chunk_count_str)
        assert chunk_count > 0, (
            f"File header '{file_path}' shows {chunk_count} chunks - should be omitted if 0!\n"
            f"Output:\n{stdout[:500]}"
        )

    # Additionally verify: if we see a file header, we should see chunk lines under it
    # This ensures headers with 0 actual chunks aren't shown
    if file_headers:
        # At least one chunk line should exist (indented with :LINE pattern)
        chunk_lines = re.findall(r"^\s+:\d+\s+[\d.]+", stdout, re.MULTILINE)
        assert len(chunk_lines) > 0, (
            f"Found {len(file_headers)} file headers but no chunk lines!\n"
            f"Headers: {file_headers}\n"
            f"Output:\n{stdout[:500]}"
        )
