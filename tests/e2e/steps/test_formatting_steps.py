"""Step definitions for result formatting scenarios (STORY-0001.3.3).

This module contains stubbed step definitions for testing result formatting
in different output modes (terse, verbose, MCP).

All steps raise NotImplementedError and will be implemented incrementally across tasks:
- TASK-0001.3.3.2: Basic formatter infrastructure
- TASK-0001.3.3.3: TerseFormatter implementation
- TASK-0001.3.3.4: VerboseFormatter and MCPFormatter
- TASK-0001.3.3.5: Final CLI integration
"""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, parsers, then

# Given steps


@given("an indexed repository with HEAD and historic commits")
def indexed_repo_with_history(context: dict[str, Any]) -> None:
    """Create indexed repository with multiple commits for HEAD marker testing.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: an indexed repository with HEAD and historic commits"
    )


@given("an indexed repository with unknown file type (.xyz)")
def indexed_repo_with_unknown_filetype(context: dict[str, Any]) -> None:
    """Create indexed repository with unknown file type for language fallback testing.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: an indexed repository with unknown file type (.xyz)"
    )


# Then steps - Output format validation


@then(parsers.parse('each line should match pattern: "{pattern}"'))
def each_line_matches_pattern(pattern: str, context: dict[str, Any]) -> None:
    """Verify each output line matches regex pattern.

    Args:
        pattern: Regular expression pattern to match
        context: Shared step context
    """
    raise NotImplementedError(f"Step not implemented: each line should match pattern: {pattern}")


@then("output should contain commit SHA")
def output_contains_commit_sha(context: dict[str, Any]) -> None:
    """Verify output contains git commit SHA.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: output should contain commit SHA")


@then("output should contain author name")
def output_contains_author_name(context: dict[str, Any]) -> None:
    """Verify output contains commit author name.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: output should contain author name")


@then("output should contain commit date")
def output_contains_commit_date(context: dict[str, Any]) -> None:
    """Verify output contains commit date.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: output should contain commit date")


@then(parsers.parse('output should contain results summary: "{pattern}"'))
def output_contains_results_summary(pattern: str, context: dict[str, Any]) -> None:
    """Verify output contains results summary line.

    Args:
        pattern: Expected summary pattern (e.g., "{N} results in {X.XX}s")
        context: Shared step context
    """
    raise NotImplementedError(
        f"Step not implemented: output should contain results summary: {pattern}"
    )


@then('HEAD results should show "●" or "[HEAD]" marker')
def head_results_show_marker(context: dict[str, Any]) -> None:
    """Verify HEAD commit results show appropriate marker.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        'Step not implemented: HEAD results should show "●" or "[HEAD]" marker'
    )


@then("historic results should have no marker")
def historic_results_no_marker(context: dict[str, Any]) -> None:
    """Verify historic commit results have no HEAD marker.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: historic results should have no marker")


@then("output should contain syntax-highlighted code blocks")
def output_contains_syntax_highlighting(context: dict[str, Any]) -> None:
    """Verify output contains syntax-highlighted code blocks.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: output should contain syntax-highlighted code blocks"
    )


@then("code blocks should show line numbers")
def code_blocks_show_line_numbers(context: dict[str, Any]) -> None:
    """Verify code blocks include line numbers.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: code blocks should show line numbers")


@then("output should contain file paths with line ranges")
def output_contains_file_paths_with_ranges(context: dict[str, Any]) -> None:
    """Verify output contains file paths with line range annotations.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: output should contain file paths with line ranges"
    )


@then('output should start with "---"')
def output_starts_with_yaml_delimiter(context: dict[str, Any]) -> None:
    """Verify output starts with YAML frontmatter delimiter.

    Args:
        context: Shared step context
    """
    raise NotImplementedError('Step not implemented: output should start with "---"')


@then('output should contain "results:"')
def output_contains_results_key(context: dict[str, Any]) -> None:
    """Verify output contains 'results:' YAML key.

    Args:
        context: Shared step context
    """
    raise NotImplementedError('Step not implemented: output should contain "results:"')


@then("YAML frontmatter should parse successfully")
def yaml_frontmatter_parses(context: dict[str, Any]) -> None:
    """Verify YAML frontmatter is valid and parseable.

    Args:
        context: Shared step context
    """
    raise NotImplementedError("Step not implemented: YAML frontmatter should parse successfully")


@then('YAML should contain "file_path" keys')
def yaml_contains_file_path_keys(context: dict[str, Any]) -> None:
    """Verify YAML frontmatter contains file_path keys.

    Args:
        context: Shared step context
    """
    raise NotImplementedError('Step not implemented: YAML should contain "file_path" keys')


@then("output should contain code blocks with language tags")
def output_contains_language_tags(context: dict[str, Any]) -> None:
    """Verify output contains code blocks with language specifiers.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: output should contain code blocks with language tags"
    )


@then('the output should contain "0 results in"')
def output_contains_zero_results(context: dict[str, Any]) -> None:
    """Verify output shows zero results message.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    assert "0 results in" in stdout, f"Expected '0 results in' in output, got: {stdout}"


@then('syntax highlighting should use "markdown" language')
def syntax_highlighting_uses_markdown(context: dict[str, Any]) -> None:
    """Verify unknown file types fall back to markdown syntax highlighting.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        'Step not implemented: syntax highlighting should use "markdown" language'
    )


@then("code should still be displayed with formatting")
def code_displayed_with_formatting(context: dict[str, Any]) -> None:
    """Verify code is displayed with formatting even for unknown languages.

    Args:
        context: Shared step context
    """
    raise NotImplementedError(
        "Step not implemented: code should still be displayed with formatting"
    )
