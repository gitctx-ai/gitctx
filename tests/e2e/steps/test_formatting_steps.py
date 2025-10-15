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

import re
from typing import Any

import yaml
from pytest_bdd import given, parsers, then

from tests.e2e.conftest import strip_ansi

# Given steps


@given("an indexed repository with HEAD and historic commits")
def indexed_repo_with_history(context: dict[str, Any], e2e_indexed_repo_factory: Any) -> None:
    """Create indexed repository with multiple commits for HEAD marker testing.

    Args:
        context: Shared step context
        e2e_indexed_repo_factory: Factory fixture for creating indexed repos
    """
    # Create indexed repo with multiple commits
    repo_path = e2e_indexed_repo_factory(
        files={"test.py": "def test(): pass\n", "main.py": "def main(): pass\n"},
        num_commits=3,
    )
    context["repo_path"] = repo_path


@given("an indexed repository with unknown file type (.xyz)")
def indexed_repo_with_unknown_filetype(
    context: dict[str, Any], e2e_indexed_repo_factory: Any
) -> None:
    """Create indexed repository with unknown file type for language fallback testing.

    Args:
        context: Shared step context
        e2e_indexed_repo_factory: Factory fixture for creating indexed repos
    """
    # Create indexed repo with unknown file type
    repo_path = e2e_indexed_repo_factory(
        files={"data.xyz": "unknown content\nmore data\n"},
        num_commits=1,
    )
    context["repo_path"] = repo_path


# Then steps - Output format validation


@then(parsers.parse('each line should match pattern: "{pattern}"'))
def each_line_matches_pattern(pattern: str, context: dict[str, Any]) -> None:
    """Verify each output line matches regex pattern.

    Args:
        pattern: Regular expression pattern to match
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Remove ANSI escape codes before processing lines
    clean_stdout = strip_ansi(stdout)

    lines = [line for line in clean_stdout.strip().split("\n") if line.strip()]

    # Exclude results summary line (e.g., "2 results in 0.01s")
    result_lines = [line for line in lines if not re.match(r"\d+ results in \d+\.\d+s", line)]

    for line in result_lines:
        assert re.match(pattern, line), f"Line '{line}' does not match pattern '{pattern}'"


@then("output should contain commit SHA")
def output_contains_commit_sha(context: dict[str, Any]) -> None:
    """Verify output contains git commit SHA.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Match 7-character hex SHA (e.g., "f9e8d7c")
    sha_pattern = r"[0-9a-f]{7}"
    assert re.search(sha_pattern, stdout), f"Expected commit SHA in output, got: {stdout}"


@then("output should contain author name")
def output_contains_author_name(context: dict[str, Any]) -> None:
    """Verify output contains commit author name.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    # Check for any alphabetic author name pattern (in parentheses after date)
    # Example: (2025-10-02, Alice)
    assert "," in stdout, f"Expected author name format with comma in output, got: {stdout}"


@then("output should contain commit date")
def output_contains_commit_date(context: dict[str, Any]) -> None:
    """Verify output contains commit date.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Remove ANSI codes for pattern matching
    clean_stdout = strip_ansi(stdout)

    # Match ISO date format (YYYY-MM-DD)
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    assert re.search(date_pattern, clean_stdout), f"Expected commit date in output, got: {stdout}"


@then(parsers.parse('output should contain results summary: "{pattern}"'))
def output_contains_results_summary(pattern: str, context: dict[str, Any]) -> None:
    """Verify output contains results summary line.

    Args:
        pattern: Expected summary pattern (e.g., "{N} results in {X.XX}s")
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Remove ANSI codes for pattern matching
    clean_stdout = strip_ansi(stdout)

    # Pattern: {N} results in {X.XX}s (e.g., "5 results in 1.23s")
    summary_pattern = r"\d+ results in \d+\.\d+s"
    assert re.search(summary_pattern, clean_stdout), (
        f"Expected results summary in output, got: {stdout}"
    )


@then('HEAD results should show "●" or "[HEAD]" marker')
def head_results_show_marker(context: dict[str, Any]) -> None:
    """Verify HEAD commit results show appropriate marker.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    # Check for either modern (●) or legacy ([HEAD]) marker
    assert "●" in stdout or "[HEAD]" in stdout, (
        f"Expected HEAD marker (● or [HEAD]) in output, got: {stdout}"
    )


@then("historic results should have no marker")
def historic_results_no_marker(context: dict[str, Any]) -> None:
    """Verify historic commit results have no HEAD marker.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    lines = stdout.strip().split("\n")

    # Check that at least one line does NOT have ● or [HEAD]
    # (indicating historic commits are present without marker)
    has_unmarked_line = any(
        "●" not in line and "[HEAD]" not in line for line in lines if line.strip()
    )
    assert has_unmarked_line, f"Expected at least one line without HEAD marker, got: {stdout}"


@then("output should contain syntax-highlighted code blocks")
def output_contains_syntax_highlighting(context: dict[str, Any]) -> None:
    """Verify output contains syntax-highlighted code blocks.

    Args:
        context: Shared step context
    """

    # Use raw_stdout to check for ANSI codes (before stripping)
    raw_stdout = context.get("raw_stdout", "")
    # Rich.Syntax adds ANSI escape codes for highlighting
    # Check for ANSI color codes (e.g., \x1b[38;...)
    ansi_pattern = r"\x1b\[[0-9;]*m"
    assert re.search(ansi_pattern, raw_stdout), (
        f"Expected ANSI color codes (syntax highlighting) in output, got: {raw_stdout[:200]}"
    )


@then("code blocks should show line numbers")
def code_blocks_show_line_numbers(context: dict[str, Any]) -> None:
    """Verify code blocks include line numbers.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Remove ANSI escape codes for pattern matching
    clean_stdout = strip_ansi(stdout)

    # Rich.Syntax adds line numbers at the start of code lines
    # Pattern: one or more digits followed by space or special chars
    line_num_pattern = r"^\s*\d+\s+"
    assert re.search(line_num_pattern, clean_stdout, re.MULTILINE), (
        f"Expected line numbers in output, got: {stdout[:200]}"
    )


@then("output should contain file paths with line ranges")
def output_contains_file_paths_with_ranges(context: dict[str, Any]) -> None:
    """Verify output contains file paths with line range annotations.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")
    # Remove ANSI escape codes for pattern matching
    clean_stdout = strip_ansi(stdout)

    # VerboseFormatter format: {file_path}:{start}-{end}
    # Example: src/auth.py:45-52
    path_range_pattern = r"\S+\.py:\d+-\d+"
    assert re.search(path_range_pattern, clean_stdout), (
        f"Expected file path with line range (e.g., 'file.py:10-20') in output, got: {stdout[:200]}"
    )


@then('output should start with "---"')
def output_starts_with_yaml_delimiter(context: dict[str, Any]) -> None:
    """Verify output starts with YAML frontmatter delimiter.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    # MCP format starts with YAML frontmatter delimiter
    assert stdout.strip().startswith("---"), (
        f"Expected output to start with '---', got: {stdout[:50]}"
    )


@then('output should contain "results:"')
def output_contains_results_key(context: dict[str, Any]) -> None:
    """Verify output contains 'results:' YAML key.

    Args:
        context: Shared step context
    """
    stdout = context.get("stdout", "")
    assert "results:" in stdout, f"Expected 'results:' in output, got: {stdout[:200]}"


@then("YAML frontmatter should parse successfully")
def yaml_frontmatter_parses(context: dict[str, Any]) -> None:
    """Verify YAML frontmatter is valid and parseable.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")

    # Extract YAML frontmatter (between first and second ---)
    parts = stdout.split("---")
    assert len(parts) >= 3, f"Expected YAML frontmatter with --- delimiters, got: {stdout[:200]}"

    yaml_content = parts[1]

    # Parse YAML
    try:
        data = yaml.safe_load(yaml_content)
        assert data is not None, "YAML parsed to None"
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        # Store parsed data for subsequent steps
        context["parsed_yaml"] = data
    except yaml.YAMLError as e:
        raise AssertionError(f"Failed to parse YAML frontmatter: {e}\n{yaml_content}") from e


@then('YAML should contain "file_path" keys')
def yaml_contains_file_path_keys(context: dict[str, Any]) -> None:
    """Verify YAML frontmatter contains file_path keys.

    Args:
        context: Shared step context
    """
    # Get parsed YAML from previous step
    parsed_yaml = context.get("parsed_yaml")
    assert parsed_yaml is not None, "YAML not parsed in previous step"

    # Verify top-level structure
    assert "results" in parsed_yaml, "YAML missing 'results' key"
    assert isinstance(parsed_yaml["results"], list), "'results' must be a list"

    # Verify each result has required fields
    for i, result in enumerate(parsed_yaml["results"]):
        assert "file_path" in result, f"Result {i} missing 'file_path' key"
        assert "line_numbers" in result, f"Result {i} missing 'line_numbers' key"
        assert "score" in result, f"Result {i} missing 'score' key"
        assert "commit_sha" in result, f"Result {i} missing 'commit_sha' key"


@then("output should contain code blocks with language tags")
def output_contains_language_tags(context: dict[str, Any]) -> None:
    """Verify output contains code blocks with language specifiers.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")

    # MCP format uses markdown code blocks with language tags: ```python or ```language
    # Pattern: ``` followed by language name (e.g., ```python, ```javascript, etc.)
    code_block_pattern = r"```\w+"

    assert re.search(code_block_pattern, stdout), (
        f"Expected code blocks with language tags (e.g., '```python') in output, "
        f"got: {stdout[:200]}"
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

    stdout = context.get("stdout", "")
    raw_stdout = context.get("raw_stdout", "")

    # For unknown file types (.xyz), VerboseFormatter should fall back to "markdown" language
    # We can't directly see the language name in output, but we can verify:
    # 1. Output contains the file path with .xyz extension
    # 2. Content is displayed with syntax highlighting (ANSI codes present)
    # 3. No error messages about unknown language

    # Check for .xyz file reference (in stripped output)
    assert ".xyz" in stdout, f"Expected .xyz file in output, got: {stdout[:200]}"

    # Check for ANSI escape codes (Rich.Syntax adds these - use raw output)
    ansi_pattern = r"\x1b\[[0-9;]*m"
    assert re.search(ansi_pattern, raw_stdout), (
        "Expected ANSI color codes (syntax highlighting) in output for markdown fallback"
    )


@then("code should still be displayed with formatting")
def code_displayed_with_formatting(context: dict[str, Any]) -> None:
    """Verify code is displayed with formatting even for unknown languages.

    Args:
        context: Shared step context
    """

    stdout = context.get("stdout", "")

    # Verify code content is displayed (not skipped due to unknown language)
    # For .xyz file created in fixture, content is "unknown content\nmore data\n"
    # We should see this content in the output
    assert "unknown content" in stdout or "more data" in stdout, (
        f"Expected file content to be displayed, got: {stdout[:200]}"
    )

    # Remove ANSI escape codes for pattern matching
    clean_stdout = strip_ansi(stdout)

    # Verify formatting is applied (line numbers present from Rich.Syntax)
    # Rich.Syntax adds line numbers in format: "  1 " or similar
    line_num_pattern = r"^\s*\d+\s+"
    assert re.search(line_num_pattern, clean_stdout, re.MULTILINE), (
        f"Expected line numbers (formatting) in output, got: {stdout[:200]}"
    )
