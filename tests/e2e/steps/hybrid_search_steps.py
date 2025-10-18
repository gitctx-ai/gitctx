"""Step definitions for hybrid search BDD scenarios.

This module contains step definitions for hybrid search testing.
"""

from typing import Any

from pytest_bdd import given, parsers, then, when

from gitctx.cli.main import app

# ===== Background Steps =====


@given("I am in a git repository")
def in_git_repository() -> None:
    """Background step - repository context provided by e2e_git_repo fixture.

    Implementation: Already handled by pytest fixtures (e2e_git_repo, e2e_indexed_repo_factory)
    """
    # This step is satisfied by the test fixtures


@given("a repository with files:")
def repository_with_files_table(
    context: dict[str, Any], datatable, e2e_indexed_repo_factory, e2e_session_api_key
) -> None:
    """Create repository with specific file structure from Gherkin table.

    Args:
        context: pytest-bdd context object
        datatable: Gherkin data table with file_path and content columns
        e2e_indexed_repo_factory: Factory fixture for creating indexed repositories
        e2e_session_api_key: API key for embedding generation
    """
    # Parse table data from Gherkin scenario
    # datatable is a list of lists: [['file_path', 'content'], ['path1', 'content1'], ...]
    # First row is headers, subsequent rows are data
    files = {}
    for row in datatable[1:]:  # Skip header row
        file_path = row[0]  # First column is file_path
        content = row[1]  # Second column is content
        files[file_path] = content

    # Set API key in custom_env for indexing
    context["custom_env"] = {"OPENAI_API_KEY": e2e_session_api_key}

    # Create indexed repository with specified files
    repo_path = e2e_indexed_repo_factory(files=files)

    # Store repo path in context for subsequent steps
    context["repo_path"] = repo_path


@given("the repository is indexed")
def repository_is_indexed(context: dict[str, Any]) -> None:
    """Index the repository for searching.

    This step is already satisfied by e2e_indexed_repo_factory which indexes
    the repository during creation.

    Args:
        context: pytest-bdd context object
    """
    # Repository already indexed by e2e_indexed_repo_factory
    # This step is a no-op for readability in Gherkin scenarios


# ===== Search Steps =====


@when(parsers.parse('I search for "{query}"'))
def search_with_query(
    query: str, context: dict[str, Any], e2e_cli_runner, monkeypatch, e2e_session_api_key
) -> None:
    """Execute search with given query text.

    Args:
        query: Search query string (used for both BM25 and vector search)
        context: pytest-bdd context object
        e2e_cli_runner: CLI runner fixture
        monkeypatch: pytest monkeypatch fixture
        e2e_session_api_key: API key for embedding generation
    """
    # Change to repository directory
    repo_path = context["repo_path"]
    monkeypatch.chdir(repo_path)

    # Set API key for search (embedding generation)
    context["custom_env"] = {"OPENAI_API_KEY": e2e_session_api_key}

    # Execute search command
    # e2e_cli_runner automatically merges context["custom_env"]
    result = e2e_cli_runner.invoke(app, ["search", query])

    # Clear custom_env to prevent leaking to next command
    context.pop("custom_env", None)

    # Store results in context
    context["result"] = result
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""
    context["exit_code"] = result.exit_code


@then(parsers.parse('the first result should be "{file_path}"'))
def check_first_result(file_path: str, context: dict[str, Any]) -> None:
    """Verify the first search result matches expected file path.

    Args:
        file_path: Expected file path for first result
        context: pytest-bdd context object
    """
    result = context["result"]
    stdout = context["stdout"]
    stderr = context.get("stderr", "")

    # Verify search succeeded
    assert result.exit_code == 0, (
        f"Search failed with exit code {result.exit_code}:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    )

    # Parse search output for file paths
    # Search output format: "File: path/to/file.py"
    lines = stdout.split("\n")
    file_paths = []
    for line in lines:
        if line.strip().startswith("File:"):
            # Extract file path from "File: path/to/file.py"
            path = line.split("File:", 1)[1].strip()
            file_paths.append(path)

    # Verify at least one result
    assert len(file_paths) > 0, f"No search results found in output:\n{stdout}"

    # Verify first result matches expected file path
    first_result = file_paths[0]
    assert first_result == file_path, (
        f"First result mismatch:\n"
        f"  Expected: {file_path}\n"
        f"  Got: {first_result}\n"
        f"Full output:\n{stdout}"
    )


@then("the result should have BM25 score > 0.7")
def check_bm25_score(context) -> None:
    """Verify BM25 score indicates strong keyword match (> 0.7 threshold).

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        "BM25 score verification not implemented yet. "
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then(parsers.parse('results should include both "{file1}" and "{file2}"'))
def check_results_include_both(file1: str, file2: str, context) -> None:
    """Verify search results include both specified files.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        file1: First expected file path
        file2: Second expected file path
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'Results inclusion check for "{file1}" and "{file2}" not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then("results should have vector scores > 0.7")
def check_vector_scores(context) -> None:
    """Verify vector scores indicate strong semantic match (> 0.7 threshold).

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        "Vector score verification not implemented yet. "
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then(parsers.parse('"{file_path}" should rank first'))
def check_rank_first(file_path: str, context) -> None:
    """Verify specified file ranks first in results.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        file_path: Expected file path for first position
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'Rank verification for "{file_path}" at position 1 not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then(parsers.parse('"{file_path}" should rank second'))
def check_rank_second(file_path: str, context) -> None:
    """Verify specified file ranks second in results.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        file_path: Expected file path for second position
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'Rank verification for "{file_path}" at position 2 not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then(parsers.parse('"{file1}" should rank lower than "{file2}"'))
def check_rank_lower(file1: str, file2: str, context) -> None:
    """Verify file1 ranks lower (worse) than file2 in results.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        file1: File path expected to rank lower
        file2: File path expected to rank higher
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'Relative rank verification for "{file1}" < "{file2}" not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )
