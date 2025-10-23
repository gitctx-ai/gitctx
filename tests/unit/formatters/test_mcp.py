"""Unit tests for MCPFormatter."""

from __future__ import annotations

import re
from io import StringIO

import yaml
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS
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
            "distance": 0.85,
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
    """Test that YAML frontmatter has 'files:' key (file-grouped format)."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,  # score 0.85 (above default min_similarity 0.5)
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
    assert "files:" in result


def test_mcp_formatter_yaml_array_structure() -> None:
    """Test that files are formatted as YAML array with list items."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,
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
            "distance": 0.08,  # score = 1.0 - 0.08 = 0.92
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
    """Test YAML has chunks count (line_numbers moved to Markdown body)."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 45,
            "end_line": 52,
            "distance": 0.15,
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
    # New format: line numbers in Markdown body, not YAML
    assert "chunks: 1" in result
    assert "**Lines 45-52**" in result


def test_mcp_formatter_yaml_has_score_three_decimals() -> None:
    """Test that YAML score has 3 decimal places."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.14568,  # score = 1.0 - 0.14568 = 0.85432
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "best_score: 0.854" in result
    assert "0.8543" not in result


def test_mcp_formatter_markdown_has_commit_sha() -> None:
    """Test that Markdown body contains short commit SHA with HEAD marker."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,  # score 0.85
            "commit_sha": "f9e8d7c1234567890abcdef",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Check Markdown body has commit SHA (short form, 7 chars)
    assert "**Commit:**" in result
    assert "f9e8d7c" in result  # pragma: allowlist secret
    # Should have HEAD indicator before SHA
    assert f"{SYMBOLS['head']}f9e8d7c" in result


def test_mcp_formatter_yaml_parses_successfully() -> None:
    """Test that YAML frontmatter is valid and parseable with file grouping."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 20,
            "distance": 0.08,  # score 0.92
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
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
    assert "files" in data, "YAML should have 'files' key (file-grouped format)"
    assert isinstance(data["files"], list)
    assert len(data["files"]) == 1
    assert data["files"][0]["file_path"] == "test.py"
    assert data["files"][0]["chunks"] == 1


def test_mcp_formatter_markdown_headers() -> None:
    """Test that markdown body contains file-grouped headers."""

    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 45,
            "end_line": 52,
            "distance": 0.08,  # score 0.92
            "commit_sha": "def456",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "## src/auth.py (1 chunk)" in result


def test_mcp_formatter_metadata_line() -> None:
    """Test that markdown body contains metadata line with score and commit."""

    results = [
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 20,
            "distance": 0.125,  # score = 0.875
            "commit_sha": "f9e8d7c1234567",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "**Score:** 0.875" in result
    assert "**Commit:**" in result
    assert "f9e8d7c" in result  # pragma: allowlist secret


def test_mcp_formatter_code_blocks_with_language() -> None:
    """Test that code blocks include language tags."""

    results = [
        {
            "file_path": "test.js",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,  # score 0.85
            "commit_sha": "abc1234",  # pragma: allowlist secret
            "chunk_content": "function test() { return 42; }",
            "language": "javascript",
            "is_head": True,
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
    """Test that missing language field is handled gracefully."""

    results = [
        {
            "file_path": "unknown.xyz",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.25,  # score 0.75
            "commit_sha": "ghi789",  # pragma: allowlist secret
            "chunk_content": "some content",
            "is_head": True,
            # No language field - will use get("language", "markdown") fallback
        }
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    # Should have code block (language handled by _ResultWrapper)
    assert "```" in result
    assert "some content" in result


def test_mcp_formatter_escapes_yaml_special_chars() -> None:
    """Test that file paths with YAML special chars are properly escaped."""

    # Test paths with YAML special characters
    results = [
        {
            "file_path": 'src/auth.py: "password"',  # Colon + quotes
            "start_line": 10,
            "end_line": 20,
            "distance": 0.15,  # score 0.85
            "commit_sha": "abc123def456",  # pragma: allowlist secret
            "chunk_content": "def test(): pass",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "C:\\Users\\file.py",  # Windows path (backslashes)
            "start_line": 30,
            "end_line": 40,
            "distance": 0.25,  # score 0.75
            "commit_sha": "def456ghi789",  # pragma: allowlist secret
            "chunk_content": "# Windows path",
            "language": "python",
            "is_head": True,
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

    # Verify structure (file-grouped format)
    assert "files" in parsed, "YAML should have 'files' key (file-grouped format)"
    assert len(parsed["files"]) == 2
    assert parsed["files"][0]["file_path"] == 'src/auth.py: "password"'
    assert parsed["files"][1]["file_path"] == "C:\\Users\\file.py"


# ===== NEW TESTS FOR FILE GROUPING (TDD for TASK-0001.4.3.5) =====


def test_mcp_groups_results_by_file() -> None:
    """Test that MCP formatter groups multiple chunks by file in YAML frontmatter."""
    results = [
        {
            "file_path": "src/auth.py",
            "start_line": 15,
            "end_line": 25,
            "distance": 0.05,  # distance 0.05 = score 0.95
            "commit_sha": "abc1234567890",  # pragma: allowlist secret
            "chunk_content": "class AuthMiddleware:\n    pass",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "src/auth.py",
            "start_line": 42,
            "end_line": 58,
            "distance": 0.18,  # distance 0.18 = score 0.82
            "commit_sha": "abc1234567890",  # pragma: allowlist secret
            "chunk_content": "def process_request(self, request):\n    pass",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "src/auth.py",
            "start_line": 103,
            "end_line": 115,
            "distance": 0.25,  # distance 0.25 = score 0.75
            "commit_sha": "abc1234567890",  # pragma: allowlist secret
            "chunk_content": "def validate_token(self, token):\n    pass",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "src/login.py",
            "start_line": 10,
            "end_line": 20,
            "distance": 0.12,  # distance 0.12 = score 0.88
            "commit_sha": "def4567890",  # pragma: allowlist secret
            "chunk_content": "def authenticate_user():\n    pass",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "src/login.py",
            "start_line": 30,
            "end_line": 40,
            "distance": 0.30,  # distance 0.30 = score 0.70
            "commit_sha": "def4567890",  # pragma: allowlist secret
            "chunk_content": "def logout_user():\n    pass",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result_text = output.getvalue()

    # Extract and parse YAML frontmatter
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    assert yaml_match, "YAML frontmatter not found"
    parsed = yaml.safe_load(yaml_match.group(1))

    # Should have "files" array (not "results")
    assert "files" in parsed, "YAML should have 'files' key"
    assert len(parsed["files"]) == 2, "Should have 2 file entries (not 5 chunks)"

    # Verify first file entry structure
    file1 = parsed["files"][0]
    assert file1["file_path"] == "src/auth.py"
    assert file1["language"] == "python"
    assert file1["chunks"] == 3, "src/auth.py should have 3 chunks"
    assert file1["best_score"] == 0.950, "Best score should be 0.95 (highest in file)"

    # Verify second file entry
    file2 = parsed["files"][1]
    assert file2["file_path"] == "src/login.py"
    assert file2["chunks"] == 2, "src/login.py should have 2 chunks"
    assert file2["best_score"] == 0.880, "Best score should be 0.88"

    # Verify Markdown has file headers
    assert "## src/auth.py (3 chunks)" in result_text
    assert "## src/login.py (2 chunks)" in result_text


def test_mcp_file_entry_metadata_in_yaml() -> None:
    """Test that each file entry has complete metadata in YAML."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.05,  # score 0.95
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code1",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.18,  # score 0.82
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code2",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 20,
            "end_line": 25,
            "distance": 0.25,  # score 0.75
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code3",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    # Parse YAML frontmatter
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Verify file entry has all required keys
    file_entry = parsed["files"][0]
    assert "file_path" in file_entry
    assert "language" in file_entry
    assert "chunks" in file_entry
    assert "best_score" in file_entry

    # Verify types
    assert isinstance(file_entry["chunks"], int)
    assert isinstance(file_entry["best_score"], float)

    # Verify values
    assert file_entry["file_path"] == "test.py"
    assert file_entry["language"] == "python"
    assert file_entry["chunks"] == 3
    assert file_entry["best_score"] == 0.950  # max(0.95, 0.82, 0.75)


def test_mcp_respects_min_similarity_filter() -> None:
    """Test that chunks below min_similarity are filtered out."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.05,  # score 0.95 (keep)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code1",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.40,  # score 0.60 (keep)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code2",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 20,
            "end_line": 25,
            "distance": 0.75,  # score 0.25 (filter out)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code3",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console, min_similarity=0.5)

    # Parse YAML
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Should have 1 file with 2 chunks (0.25 filtered out)
    assert len(parsed["files"]) == 1
    assert parsed["files"][0]["chunks"] == 2

    # Verify only 2 code blocks in Markdown (not 3)
    assert result_text.count("```python") == 2


def test_mcp_respects_filter_mode_head() -> None:
    """Test that filter='head' only shows HEAD chunks."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "HEAD chunk 1",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.20,
            "commit_sha": "old456",  # pragma: allowlist secret
            "chunk_content": "HISTORY chunk 1",
            "language": "python",
            "is_head": False,
        },
        {
            "file_path": "test.py",
            "start_line": 20,
            "end_line": 25,
            "distance": 0.18,
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "HEAD chunk 2",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 30,
            "end_line": 35,
            "distance": 0.22,
            "commit_sha": "old789",  # pragma: allowlist secret
            "chunk_content": "HISTORY chunk 2",
            "language": "python",
            "is_head": False,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console, filter="head")  # Default

    # Parse YAML
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Should have 1 file with 2 HEAD chunks (HISTORY filtered out)
    assert len(parsed["files"]) == 1
    assert parsed["files"][0]["chunks"] == 2

    # Verify content
    assert "HEAD chunk 1" in result_text
    assert "HEAD chunk 2" in result_text
    assert "HISTORY chunk 1" not in result_text
    assert "HISTORY chunk 2" not in result_text


def test_mcp_respects_filter_mode_all() -> None:
    """Test that filter='all' shows both HEAD and HISTORY chunks."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "HEAD chunk",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.20,
            "commit_sha": "old456",  # pragma: allowlist secret
            "chunk_content": "HISTORY chunk",
            "language": "python",
            "is_head": False,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console, filter="all")

    # Parse YAML
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Should have 1 file with 2 chunks (both HEAD and HISTORY)
    assert parsed["files"][0]["chunks"] == 2

    # Verify both appear
    assert "HEAD chunk" in result_text
    assert "HISTORY chunk" in result_text


def test_mcp_files_sorted_by_best_chunk_score() -> None:
    """Test that files are sorted by best chunk score (descending)."""
    results = [
        # File 1: best score 0.75
        {
            "file_path": "file1.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.25,  # score 0.75
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
        # File 2: best score 0.95 (should be first)
        {
            "file_path": "file2.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.05,  # score 0.95
            "commit_sha": "def456",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
        # File 3: best score 0.82
        {
            "file_path": "file3.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.18,  # score 0.82
            "commit_sha": "ghi789",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    # Parse YAML
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Verify file order: file2 (0.95), file3 (0.82), file1 (0.75)
    assert parsed["files"][0]["file_path"] == "file2.py"
    assert parsed["files"][0]["best_score"] == 0.950
    assert parsed["files"][1]["file_path"] == "file3.py"
    assert parsed["files"][1]["best_score"] == 0.820
    assert parsed["files"][2]["file_path"] == "file1.py"
    assert parsed["files"][2]["best_score"] == 0.750


def test_mcp_chunks_sorted_by_score_within_file() -> None:
    """Test that chunks within each file are sorted by score descending."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 20,
            "end_line": 25,
            "distance": 0.25,  # score 0.75 (should be 3rd)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "chunk3",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.05,  # score 0.95 (should be 1st)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "chunk1",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.18,  # score 0.82 (should be 2nd)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "chunk2",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result_text = output.getvalue()

    # Extract Markdown body (after second ---)
    markdown = result_text.split("---")[2]

    # Verify chunk order by checking positions
    pos_chunk1 = markdown.find("chunk1")
    pos_chunk2 = markdown.find("chunk2")
    pos_chunk3 = markdown.find("chunk3")

    assert pos_chunk1 < pos_chunk2 < pos_chunk3, "Chunks should be in score order: 0.95, 0.82, 0.75"


def test_mcp_empty_results_after_filtering() -> None:
    """Test that empty YAML is output when all chunks are filtered."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.75,  # score 0.25 (below threshold)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
        {
            "file_path": "test.py",
            "start_line": 10,
            "end_line": 15,
            "distance": 0.80,  # score 0.20 (below threshold)
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console, min_similarity=0.9)

    # Parse YAML
    result_text = output.getvalue()
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    parsed = yaml.safe_load(yaml_match.group(1))

    # Should have empty files array
    assert parsed["files"] == []

    # Markdown body should have no code blocks
    markdown = result_text.split("---")[2] if len(result_text.split("---")) > 2 else ""
    assert "```python" not in markdown


def test_mcp_chunk_count_singular_plural() -> None:
    """Test that chunk count uses singular/plural correctly."""
    # Test singular (1 chunk)
    results_single = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results_single, console)
    result_single = output.getvalue()

    assert "## test.py (1 chunk)" in result_single
    assert "(1 chunks)" not in result_single

    # Test plural (3 chunks)
    results_multiple = [
        {
            "file_path": "test.py",
            "start_line": i,
            "end_line": i + 5,
            "distance": 0.15 + (i * 0.05),
            "commit_sha": "abc123",  # pragma: allowlist secret
            "chunk_content": f"code{i}",
            "language": "python",
            "is_head": True,
        }
        for i in range(1, 4)
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results_multiple, console)
    result_multiple = output.getvalue()

    assert "## test.py (3 chunks)" in result_multiple
    assert "(3 chunk)" not in result_multiple  # Verify not using singular


def test_mcp_preserves_existing_yaml_fields() -> None:
    """Test that existing YAML structure is maintained (backward compatibility check)."""
    results = [
        {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "distance": 0.15,
            "commit_sha": "abc1234567890",  # pragma: allowlist secret
            "chunk_content": "code",
            "language": "python",
            "is_head": True,
        },
    ]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, width=200, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result_text = output.getvalue()

    # Should still start with --- and end with ---
    assert result_text.startswith("---\n")
    assert "\n---\n" in result_text

    # Should still have Markdown body with code blocks
    assert "```python" in result_text
    assert "```\n" in result_text

    # Should still format as YAML (parseable)
    yaml_match = re.search(r"^---\n(.*?)\n---", result_text, re.DOTALL)
    assert yaml_match
    parsed = yaml.safe_load(yaml_match.group(1))
    assert isinstance(parsed, dict)
