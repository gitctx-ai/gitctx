"""Step definitions for hybrid search BDD scenarios.

This module contains stubbed step definitions for hybrid search testing.
All steps raise NotImplementedError until implemented in subsequent tasks.
"""

from typing import Any

from pytest_bdd import given, parsers, then, when


# ===== Background Steps =====


@given("I am in a git repository")
def in_git_repository() -> None:
    """Background step - repository context provided by e2e_git_repo fixture.

    Implementation: Already handled by pytest fixtures (e2e_git_repo, e2e_indexed_repo_factory)
    """
    # This step is satisfied by the test fixtures
    pass


@given("a repository with files:")
def repository_with_files_table(context: dict[str, Any], datatable) -> None:
    """Create repository with specific file structure from Gherkin table.

    Implementation: TASK-0001.4.1.2 (setup test repositories with custom structure)

    Args:
        context: pytest-bdd context object
        datatable: Gherkin data table with file_path and content columns
    """
    raise NotImplementedError(
        "Repository creation from table not implemented yet. "
        "Will be implemented in TASK-0001.4.1.2 using e2e_indexed_repo_factory."
    )


@given("the repository is indexed")
def repository_is_indexed(context: dict[str, Any]) -> None:
    """Index the repository for searching.

    Implementation: TASK-0001.4.1.2 (index test repository)

    Args:
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        "Repository indexing not implemented yet. "
        "Will be implemented in TASK-0001.4.1.2 using e2e_cli_runner."
    )


# ===== Search Steps =====


@when(parsers.parse('I search for "{query}"'))
def search_with_query(query: str, context) -> None:
    """Execute search with given query text.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        query: Search query string (used for both BM25 and vector search)
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'Search with query "{query}" not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
    )


@then(parsers.parse('the first result should be "{file_path}"'))
def check_first_result(file_path: str, context) -> None:
    """Verify the first search result matches expected file path.

    Implementation: TASK-0001.4.1.3 (after hybrid search implemented)

    Args:
        file_path: Expected file path for first result
        context: pytest-bdd context object
    """
    raise NotImplementedError(
        f'First result verification for "{file_path}" not implemented yet. '
        "Will be implemented in TASK-0001.4.1.3 when hybrid search is working."
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


@then(
    parsers.parse(
        'results should include both "{file1}" and "{file2}"'
    )
)
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
