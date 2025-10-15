"""Unit tests for MCPFormatter."""

from __future__ import annotations

from io import StringIO

from rich.console import Console


def test_mcp_formatter_has_name_and_description() -> None:
    """Test that MCPFormatter has required name and description attributes."""
    from gitctx.formatters.mcp import MCPFormatter

    formatter = MCPFormatter()

    assert formatter.name == "mcp"
    assert formatter.description is not None
    assert len(formatter.description) > 0


def test_mcp_formatter_starts_with_yaml_delimiter() -> None:
    """Test that output starts with YAML frontmatter delimiter."""
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    # Should have list item markers in YAML
    assert "  - file_path:" in result or "  -file_path:" in result


def test_mcp_formatter_yaml_has_file_path() -> None:
    """Test that YAML contains file_path field."""
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    import yaml

    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
    from gitctx.formatters.mcp import MCPFormatter

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
