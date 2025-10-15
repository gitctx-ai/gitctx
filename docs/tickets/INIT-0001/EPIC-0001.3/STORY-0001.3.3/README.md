# STORY-0001.3.3: Result Formatting & Output

**Parent Epic**: [EPIC-0001.3](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 3
**Progress**: ████████░░ 60%

## User Story

As a developer
I want search results formatted appropriately for my context (human reading, detailed review, or AI consumption)
So that I can quickly understand results or integrate them into AI workflows

## Acceptance Criteria

**Default Output (Scenarios 1-2, 5):**
- [ ] Default (terse) output format (one line per result):
  - Format: `{file_path}:{start_line}:{score:.2f} {head_marker} {sha[:7]} ({date}, {author}) "{msg[:50]}"`
  - Example: `src/auth.py:45:0.92 ● f9e8d7c (2025-10-02, Alice) "Add OAuth support"`
  - HEAD marker: `SYMBOLS["head"]` (● on modern terminals, [HEAD] on legacy Windows cmd.exe)
  - Historic commits: no marker (space character)

**Verbose Output (Scenario 3):**
- [ ] Verbose output format (multi-line per result):
  - Header: `{file_path}:{start}-{end} ({score:.2f}) {marker} {sha[:7]}`
  - Metadata: `[dim]{commit_message}[/dim]` (grayed out)
  - Code block: Rich.Syntax with `line_numbers=True, start_line={start}, theme="monokai"`
  - Blank line separator between results

**MCP Output (Scenario 4):**
- [ ] MCP output format (structured markdown):
  - YAML frontmatter with array of results: `file_path, line_numbers, score, commit_sha`
  - Markdown body with `## {file}:{start}-{end}` headers
  - Code blocks with language tags: ` ```{language}`
  - Metadata line: `**Score:** {score:.3f} | **Commit:** {sha[:7]}`

**Results Summary (All Formats):**
- [ ] Results summary line (all formats):
  - Format: `{count} results in {duration:.2f}s`
  - Displayed after all results
  - Zero results: `0 results in {duration:.2f}s`

**Flag Validation (Scenario 6):**
- [ ] Output flag validation:
  - `--mcp --verbose` → exit 2, `"Error: --mcp and --verbose are mutually exclusive"`
  - `--format mcp --verbose` → exit 2, same error

**Language Detection (Scenario 7):**
- [ ] Language detection for syntax highlighting:
  - Use `language` field from result metadata (from chunker)
  - Fallback to `"markdown"` if language unknown (LLM-friendly)
  - Never fallback to plain text

**Terminal Symbols (Scenarios 1-2):**
- [ ] Terminal-aware symbols via `SYMBOLS` dict:
  - Modern terminals: ● ✓ ✗ ⚠ 💡 →
  - Legacy Windows cmd.exe: [HEAD] [OK] [X] [!] [i] ->
  - Auto-detection via `rich.console.Console.legacy_windows`

**Terminal Width:**
- [ ] Terminal width handling:
  - Rich Console auto-wraps long lines
  - Test on 80-character width terminals
  - File paths/messages truncated intelligently by Rich

## BDD Scenarios

**E2E Scenarios:**

```gherkin
# Added to tests/e2e/features/search.feature

Scenario: Default terse output format
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication"
  Then the exit code should be 0
  And each line should match pattern: ".*:\d+:\d\.\d\d .*"
  And output should contain commit SHA
  And output should contain author name
  And output should contain commit date
  And output should contain results summary: "{N} results in {X.XX}s"

Scenario: HEAD commit marked with symbol
  Given an indexed repository with HEAD and historic commits
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication"
  Then the exit code should be 0
  And HEAD results should show "●" or "[HEAD]" marker
  And historic results should have no marker

Scenario: Verbose output with syntax highlighting
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication --verbose"
  Then the exit code should be 0
  And output should contain syntax-highlighted code blocks
  And code blocks should show line numbers
  And output should contain file paths with line ranges

Scenario: MCP output with structured markdown
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication --mcp"
  Then the exit code should be 0
  And output should start with "---"
  And output should contain "results:"
  And YAML frontmatter should parse successfully
  And YAML should contain "file_path" keys
  And output should contain code blocks with language tags

Scenario: Zero results display
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search nonexistent_xyz_function"
  Then the exit code should be 0
  And the output should contain "0 results in"

Scenario: Conflicting output flags rejected
  Given an indexed repository
  When I run "gitctx search test --mcp --verbose"
  Then the exit code should be 2
  And the output should contain "Error"
  And the output should contain "mutually exclusive"

Scenario: Unknown language fallback to markdown
  Given an indexed repository with unknown file type (.xyz)
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search test --verbose"
  Then syntax highlighting should use "markdown" language
  And code should still be displayed with formatting
```

## Technical Design

### Formatter Protocol & Registry

Extensible formatter architecture for easy community contributions:

```python
# src/gitctx/formatters/base.py (new file)
"""Base protocol for result formatters."""

from typing import Protocol
from rich.console import Console

class ResultFormatter(Protocol):
    """Contract for search result formatters."""

    name: str
    description: str

    def format(self, results: list[dict], console: Console) -> None:
        """Format and output results to console."""
        ...
```

### Terse Formatter (Default)

```python
# src/gitctx/formatters/terse.py (new file)
"""Terse single-line format (TUI_GUIDE compliant)."""

from rich.console import Console
from gitctx.cli.symbols import SYMBOLS

class TerseFormatter:
    """Default human-readable format."""

    name = "terse"
    description = "Terse single-line format (default)"

    def format(self, results: list[dict], console: Console) -> None:
        """Format results as single lines.

        Format: {file}:{line}:{score:.2f} {marker} {sha[:7]} ({date}, {author}) "{msg[:50]}"
        """
        for r in results:
            head_marker = f" {SYMBOLS['head']}" if r["is_head"] else ""
            console.print(
                f"{r['file_path']}:{r['start_line']}:{r['_distance']:.2f}"
                f"{head_marker} {r['commit_sha'][:7]} "
                f"({r['commit_date']}, {r['author_name']}) "
                f'"{r["commit_message"][:50]}"'
            )
```

### Verbose Formatter

```python
# src/gitctx/formatters/verbose.py (new file)
"""Detailed output with syntax-highlighted code context."""

from rich.console import Console
from rich.syntax import Syntax
from gitctx.cli.symbols import SYMBOLS

class VerboseFormatter:
    """Verbose output with code blocks."""

    name = "verbose"
    description = "Verbose output with code context"

    def format(self, results: list[dict], console: Console) -> None:
        """Format results with syntax-highlighted code.

        Shows:
        - Header: {file}:{start}-{end} ({score:.2f}) {marker} {sha[:7]}
        - Metadata: commit message (grayed out)
        - Code block: Rich.Syntax with line numbers
        """
        for r in results:
            # Header line
            head_marker = SYMBOLS['head'] if r["is_head"] else " "
            console.print(
                f"\n{r['file_path']}:{r['start_line']}-{r['end_line']} "
                f"({r['_distance']:.2f}) {head_marker} {r['commit_sha'][:7]}"
            )
            console.print(f"[dim]{r['commit_message']}[/dim]")

            # Syntax-highlighted code
            language = r.get("language", "markdown")  # Fallback to markdown for LLMs
            syntax = Syntax(
                r["chunk_content"],
                language,
                line_numbers=True,
                start_line=r["start_line"],
                theme="monokai"
            )
            console.print(syntax)
```

### MCP Formatter

```python
# src/gitctx/formatters/mcp.py (new file)
"""Structured markdown optimized for LLM consumption."""

from rich.console import Console

class MCPFormatter:
    """Machine-readable markdown format."""

    name = "mcp"
    description = "Structured markdown for AI tools"

    def format(self, results: list[dict], console: Console) -> None:
        """Format as markdown with YAML frontmatter.

        Structure:
        - YAML frontmatter: array of results with metadata
        - Markdown body: headers + code blocks
        """
        # YAML frontmatter
        console.print("---")
        console.print("results:")
        for r in results:
            console.print(f"  - file_path: {r['file_path']}")
            console.print(f"    line_numbers: {r['start_line']}-{r['end_line']}")
            console.print(f"    score: {r['_distance']:.3f}")
            console.print(f"    commit_sha: {r['commit_sha']}")
        console.print("---\n")

        # Markdown body
        for r in results:
            console.print(f"## {r['file_path']}:{r['start_line']}-{r['end_line']}")
            console.print(f"**Score:** {r['_distance']:.3f} | **Commit:** {r['commit_sha'][:7]}")

            language = r.get("language", "markdown")
            console.print(f"```{language}")
            console.print(r["chunk_content"])
            console.print("```\n")
```

### Registry & CLI Integration

```python
# src/gitctx/formatters/__init__.py (new file)
"""Formatter registry for search results."""

from .terse import TerseFormatter
from .verbose import VerboseFormatter
from .mcp import MCPFormatter

FORMATTERS = {
    "terse": TerseFormatter(),
    "verbose": VerboseFormatter(),
    "mcp": MCPFormatter(),
}

def get_formatter(name: str):
    """Get formatter by name.

    Args:
        name: Formatter name (terse, verbose, mcp)

    Returns:
        Formatter instance

    Raises:
        ValueError: If formatter not found
    """
    if name not in FORMATTERS:
        available = ", ".join(FORMATTERS.keys())
        raise ValueError(f"Unknown formatter: {name}. Available: {available}")
    return FORMATTERS[name]
```

```python
# src/gitctx/cli/search.py (extend from STORY-0001.3.2)
from gitctx.formatters import get_formatter

@app.command()
def search(
    query: Optional[list[str]] = typer.Argument(None),
    limit: int = typer.Option(10, "--limit", "-n"),
    format: str = typer.Option("terse", "--format", help="Output format (terse, verbose, mcp)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Alias for --format verbose"),
    mcp: bool = typer.Option(False, "--mcp", help="Alias for --format mcp"),
):
    # ... (query processing, embedding generation, search from STORY-0001.3.2)

    # Resolve format from convenience flags
    if verbose and mcp:
        console.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --mcp and --verbose are mutually exclusive",
            file=sys.stderr
        )
        raise typer.Exit(2)

    if verbose:
        format = "verbose"
    elif mcp:
        format = "mcp"

    # Format results
    formatter = get_formatter(format)
    formatter.format(results, console)

    # Summary line
    console.print(f"\n{len(results)} results in {duration:.2f}s")
```

### Unit Test Requirements

**Formatter Tests (`tests/unit/formatters/test_formatters.py`):**

```python
from io import StringIO
from rich.console import Console
from gitctx.formatters import TerseFormatter, VerboseFormatter, MCPFormatter

def test_terse_formatter_output():
    """Test terse formatter produces correct format."""
    results = [{
        "file_path": "src/auth.py",
        "start_line": 45,
        "_distance": 0.92,
        "is_head": True,
        "commit_sha": "f9e8d7c1234",
        "commit_date": "2025-10-02",
        "author_name": "Alice",
        "commit_message": "Add OAuth support"
    }]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = TerseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "src/auth.py:45:0.92" in result
    assert "f9e8d7c" in result
    assert "Alice" in result
    assert "●" in result  # HEAD marker

def test_mcp_formatter_yaml_frontmatter():
    """Test MCP formatter produces valid YAML."""
    import yaml

    results = [{
        "file_path": "test.py",
        "start_line": 10,
        "end_line": 20,
        "_distance": 0.85,
        "commit_sha": "abc123",
        "chunk_content": "def test(): pass",
        "language": "python"
    }]

    output = StringIO()
    console = Console(file=output, legacy_windows=False, markup=False)
    formatter = MCPFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert result.startswith("---")

    # Extract YAML frontmatter
    yaml_content = result.split("---")[1]
    data = yaml.safe_load(yaml_content)

    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["file_path"] == "test.py"

def test_verbose_formatter_syntax_highlighting():
    """Test verbose formatter includes syntax highlighting."""
    results = [{
        "file_path": "main.py",
        "start_line": 1,
        "end_line": 3,
        "_distance": 0.90,
        "is_head": False,
        "commit_sha": "def456",
        "commit_message": "Initial commit",
        "chunk_content": "def main():\n    pass",
        "language": "python"
    }]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    result = output.getvalue()
    assert "main.py:1-3" in result
    assert "def456" in result
    # Rich.Syntax adds ANSI codes for highlighting
    assert "def main" in result

def test_language_fallback_to_markdown():
    """Test unknown language falls back to markdown."""
    results = [{
        "file_path": "unknown.xyz",
        "start_line": 1,
        "end_line": 5,
        "_distance": 0.75,
        "is_head": True,
        "commit_sha": "ghi789",
        "commit_message": "Unknown file",
        "chunk_content": "some content",
        # No language field
    }]

    output = StringIO()
    console = Console(file=output, legacy_windows=False)
    formatter = VerboseFormatter()

    formatter.format(results, console)

    # Should not crash, should use markdown fallback
    result = output.getvalue()
    assert "unknown.xyz" in result
```

## Pattern Reuse

**Reused Patterns:**
- **SYMBOLS dict** (`src/gitctx/cli/symbols.py`) - For HEAD markers
- **Rich Console** (`rich.console.Console`) - For all output
- **Rich.Syntax** (`rich.syntax.Syntax`) - For code highlighting
- **e2e_cli_runner** (`tests/e2e/conftest.py:135`) - For testing output formats

**New Components:**
- `ResultFormatter` Protocol (`src/gitctx/formatters/base.py`)
- `TerseFormatter`, `VerboseFormatter`, `MCPFormatter` classes
- `FORMATTERS` registry dict
- `get_formatter()` function

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.3.3.1](TASK-0001.3.3.1.md) | Write ALL BDD Scenarios (7 total) | ✅ Complete | 1.5 | 0/7 (all failing) |
| [TASK-0001.3.3.2](TASK-0001.3.3.2.md) | Create Formatter Protocol + Registry (TDD) | ✅ Complete | 2 | 0/7 passing |
| [TASK-0001.3.3.3](TASK-0001.3.3.3.md) | Implement TerseFormatter (TDD) | ✅ Complete | 3 | 0/7 passing* |
| [TASK-0001.3.3.4](TASK-0001.3.3.4.md) | Implement VerboseFormatter + MCPFormatter (TDD) | 🔵 Not Started | 5 | 6/7 passing |
| [TASK-0001.3.3.5](TASK-0001.3.3.5.md) | CLI Integration + Final BDD Scenario | 🔵 Not Started | 4 | 7/7 passing ✅ |

*Note: BDD scenarios require CLI integration (TASK-0001.3.3.5) to run. TerseFormatter implementation is complete with 14/14 unit tests passing and 7 BDD step definitions implemented.

**Total Hours**: 19 hours (≈3 story points × 6h/point)

**Incremental BDD Tracking:**
- TASK-1: 0/7 scenarios (all stubbed, all failing)
- TASK-2: 1/7 scenarios (zero results test)
- TASK-3: 4/7 scenarios (terse format + HEAD marker + zero results + conflicting flags)
- TASK-4: 6/7 scenarios (add verbose + MCP formats)
- TASK-5: 7/7 scenarios (language fallback) ✅

## BDD Progress

**Initial**: 0/7 scenarios passing (all pending)

Scenarios will be implemented incrementally across tasks.

## Dependencies

**Prerequisites:**
- **STORY-0001.3.2 (Vector Similarity Search) - ⛔ MUST COMPLETE FIRST** - This story formats the results returned by STORY-0001.3.2's search functionality. Cannot implement any tasks without this dependency. The search command must return structured results (dict with file_path, start_line, end_line, _distance, commit_sha, commit_message, commit_date, author_name, is_head, language, chunk_content) before formatters can consume them.

**Package Dependencies (already in pyproject.toml):**
- `rich` - For console output, syntax highlighting
- `typer` - For CLI flags and validation
- `pyyaml` - For YAML frontmatter validation in tests

**Internal Dependencies:**
- `src/gitctx/cli/symbols.py` - Already exists ✅

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| YAML frontmatter parsing complexity | Low | Low | Use pyyaml in unit tests to validate output structure |
| Terminal width handling | Low | Low | Rich Console handles wrapping automatically, test on 80-char width |
| Code language detection accuracy | Low | Low | Use existing language detection from chunker, fallback to "markdown" for LLMs |
| Formatter registry discoverability | Low | Low | Add "Contributing" section to root README.md with formatter example |
| MCP format stability | Medium | Low | Document format spec in MCPFormatter docstring, make it easy to change |

---

**Created**: 2025-10-12
**Last Updated**: 2025-10-12
