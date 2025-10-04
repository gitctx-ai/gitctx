"""Unit tests for search command."""

from typer.testing import CliRunner

from gitctx.cli.main import app

runner = CliRunner()


def test_search_command_exists():
    """Verify search command is registered."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search the indexed repository" in result.stdout


def test_search_requires_query():
    """Verify search requires a query argument."""
    result = runner.invoke(app, ["search"])
    assert result.exit_code != 0
    # Typer outputs error to stderr
    output = result.stdout + result.stderr
    assert "Missing argument" in output or "QUERY" in output


def test_search_default_output():
    """Verify default mode is terse (file:line:score format)."""
    result = runner.invoke(app, ["search", "authentication"])
    assert result.exit_code == 0
    # Check TUI_GUIDE.md format: file:line:score ● commit
    assert ".py:" in result.stdout or ".md:" in result.stdout
    assert "●" in result.stdout or "[HEAD]" in result.stdout  # Platform-aware
    assert "results in" in result.stdout  # Summary line


def test_search_verbose_mode():
    """Verify --verbose shows code context."""
    result = runner.invoke(app, ["search", "authentication", "--verbose"])
    assert result.exit_code == 0
    # Verbose should include code snippets
    assert "def " in result.stdout or "class " in result.stdout or "##" in result.stdout
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    assert len(lines) > 10  # Multi-line with context


def test_search_limit_option():
    """Verify --limit option works."""
    result = runner.invoke(app, ["search", "test", "--limit", "2"])
    assert result.exit_code == 0
    # Should mention the limit in some way
    assert "2" in result.stdout or "results" in result.stdout


def test_search_short_flags():
    """Verify -n and -v short flags work."""
    result = runner.invoke(app, ["search", "test", "-n", "3"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["search", "test", "-v"])
    assert result.exit_code == 0


def test_search_help_text():
    """Verify help text includes all options."""
    result = runner.invoke(app, ["search", "--help"])
    assert "QUERY" in result.stdout or "query" in result.stdout
    assert "--limit" in result.stdout
    assert "-n" in result.stdout
    assert "Number of results" in result.stdout or "Maximum" in result.stdout


def test_search_shows_history_and_head():
    """Verify search demonstrates both historical and HEAD results."""
    result = runner.invoke(app, ["search", "test"])
    assert result.exit_code == 0
    # Should have HEAD indicator on some results
    has_head = "●" in result.stdout or "[HEAD]" in result.stdout or "HEAD" in result.stdout
    # Should have results with file paths
    lines_with_results = [
        line for line in result.stdout.split("\n") if ".py:" in line or ".md:" in line
    ]
    assert len(lines_with_results) >= 2  # At least 2 results to show mix
    assert has_head  # At least one HEAD result


def test_search_mcp_flag():
    """Verify --mcp flag outputs structured markdown."""
    result = runner.invoke(app, ["search", "test", "--mcp"])
    assert result.exit_code == 0
    # Check for YAML frontmatter
    assert "---" in result.stdout
    assert "status: success" in result.stdout
    assert "query: test" in result.stdout
    # Check for markdown structure
    assert "# Search Results:" in result.stdout
    assert "## Summary" in result.stdout
    assert "## Results" in result.stdout
    # Check for metadata
    assert "**Metadata**:" in result.stdout
    assert "```python" in result.stdout or "```markdown" in result.stdout


def test_search_mcp_has_yaml_frontmatter():
    """Verify MCP mode includes valid YAML frontmatter."""
    result = runner.invoke(app, ["search", "auth", "--mcp"])
    assert result.exit_code == 0
    assert result.stdout.startswith("---\n")
    assert "status: success" in result.stdout
    assert "results_count:" in result.stdout
    assert "duration_seconds:" in result.stdout


def test_search_mcp_with_limit():
    """Verify MCP mode respects limit option."""
    result = runner.invoke(app, ["search", "test", "--mcp", "--limit", "2"])
    assert result.exit_code == 0
    assert "results_count: 2" in result.stdout
    # Should have exactly 2 result sections (numbered ### 1. and ### 2.)
    assert "### 1." in result.stdout
    assert "### 2." in result.stdout
    assert "### 3." not in result.stdout


def test_search_mcp_and_verbose_are_mutually_exclusive():
    """Verify --mcp and --verbose cannot be used together."""
    result = runner.invoke(app, ["search", "test", "--mcp", "--verbose"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "mutually exclusive" in output.lower() or "Error" in output
