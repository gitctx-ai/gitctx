"""Unit tests for MCPFormatter."""

from __future__ import annotations

import re
from io import StringIO

import yaml
from rich.console import Console

from gitctx.formatters.mcp import MCPFormatter


def test_mcp_formatter_has_name_and_description() -> None:
    """Test that MCPFormatter has required name and description attributes."""

    formatter = MCPFormatter()

    assert formatter.name == "mcp"
    assert formatter.description is not None
    assert len(formatter.description) > 0


def test_mcp_formatter_starts_with_yaml_delimiter() -> None:
    """Test that output starts with YAML frontmatter delimiter."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert result.startswith("---")


def test_mcp_formatter_yaml_has_results_key() -> None:
    """Test that YAML frontmatter has 'results:' key."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "results:" in result


def test_mcp_formatter_yaml_array_structure() -> None:
    """Test that results are formatted as YAML array with list items."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should have list item markers in YAML (yaml.safe_dump format: "- key: value")
    assert ("- " in result and "file_path:" in result) or "- file_path:" in result


def test_mcp_formatter_yaml_has_file_path() -> None:
    """Test that YAML contains file_path field."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 10,
            "end_line": 20,
            "_distance": 0.92,
            "commit_sha": "def456",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "file_path: src/auth.py" in result


def test_mcp_formatter_yaml_has_line_numbers() -> None:
    """Test that YAML contains line_numbers field with range."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.85,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "line_numbers: 45-52" in result


def test_mcp_formatter_yaml_has_score_three_decimals() -> None:
    """Test that YAML score has 3 decimal places."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85432,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "score: 0.854" in result
    assert "0.8543" not in result


def test_mcp_formatter_yaml_has_commit_sha() -> None:
    """Test that YAML contains full commit SHA."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "commit_sha": "f9e8d7c1234567890abcdef",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "commit_sha: f9e8d7c1234567890abcdef" in result  # pragma: allowlist secret


def test_mcp_formatter_yaml_parses_successfully() -> None:
    """Test that YAML frontmatter is valid and parseable."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 20,
            "_distance": 0.920,
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Extract YAML frontmatter (between first --- and second ---)
    parts = result.split("---")
    assert len(parts) >= 3
    yaml_content = parts[1]

    # Should parse without error
    data = yaml.safe_load(yaml_content)
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 1
    assert data["results"][0]["file_path"] == "test.py"


def test_mcp_formatter_markdown_headers() -> None:
    """Test that markdown body contains headers with file:line."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "_distance": 0.92,
            "commit_sha": "def456",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "## src/auth.py:45-52" in result


def test_mcp_formatter_metadata_line() -> None:
    """Test that markdown body contains metadata line with score and commit."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 20,
            "_distance": 0.875,
            "commit_sha": "f9e8d7c1234567",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "**Score:** 0.875" in result
    assert "**Commit:** f9e8d7c" in result


def test_mcp_formatter_code_blocks_with_language() -> None:
    """Test that code blocks include language tags."""

    results = [
        {
            "file_path": "test.js",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.85,
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "function test() { return 42; }",
            "language": "javascript",
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "```javascript" in result
    assert "function test() { return 42; }" in result
    assert "```" in result


def test_mcp_formatter_language_fallback_markdown() -> None:
    """Test that missing language falls back to markdown."""

    results = [
        {
            "file_path": "unknown.xyz",
            "start_line": 1,
            "end_line": 5,
            "_distance": 0.75,
            "commit_sha": "ghi789",  # pragma: allowlist secret
            "chunk_content": "some content",
            # No language field
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should use markdown fallback
    assert "```markdown" in result
    assert "some content" in result


def test_mcp_formatter_escapes_yaml_special_chars() -> None:
    """Test that file paths with YAML special chars are properly escaped."""

    # Test paths with YAML special characters
    results = [
        {
            "file_path": 'src/auth.py: "password"',  # Colon + quotes
            "start_line": 10,
            "end_line": 20,
            "_distance": 0.85,
            "commit_sha": "abc123def456",  # pragma: allowlist secret
            "chunk_content": "def test(): pass",
            "language": "python",
        },
        {
            "file_path": "C:\\Users\\file.py",  # Windows path (backslashes)
            "start_line": 30,
            "end_line": 40,
            "_distance": 0.75,
            "commit_sha": "def456ghi789",  # pragma: allowlist secret
            "chunk_content": "# Windows path",
            "language": "python",
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()

    # Extract YAML frontmatter (between --- markers)
    yaml_match = re.search(r"^---\n(.*?)\n---", result, re.DOTALL)
    assert yaml_match, "YAML frontmatter not found"

    yaml_content = yaml_match.group(1)

    # Parse YAML to ensure it's valid
    parsed = yaml.safe_load(yaml_content)

    # Verify structure
    assert "results" in parsed
    assert len(parsed["results"]) == 2
    assert parsed["results"][0]["file_path"] == 'src/auth.py: "password"'
    assert parsed["results"][1]["file_path"] == "C:\\Users\\file.py"
