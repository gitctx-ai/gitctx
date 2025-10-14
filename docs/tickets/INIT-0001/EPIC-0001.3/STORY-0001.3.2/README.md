# STORY-0001.3.2: Vector Similarity Search

**Parent Epic**: [EPIC-0001.3](../README.md)
**Status**: 🟡 In Progress
**Story Points**: 6
**Progress**: ████████░░ 60%

## User Story

As a developer
I want to search my indexed codebase using semantic similarity
So that I can find relevant code based on meaning rather than exact keyword matches

## BDD Progress: 4/13 scenarios passing 🟡

## Acceptance Criteria

- [ ] Query accepts variadic arguments (no quotes needed):
  - `gitctx search auth middleware` → query = `"auth middleware"`
  - `gitctx search --limit 5 find all refs` → query = `"find all refs"`
  - Flags can appear anywhere (Typer parses correctly)
- [ ] Query from stdin when no args provided:
  - `echo "query" | gitctx search` → reads from stdin
  - `gitctx search < file.txt` → reads from file
  - Empty stdin + no args → exit 2, `"Error: Query required (from args or stdin)"`
  - Interactive terminal + no args → exit 2, `"Error: Query required (from args or stdin)"`
- [ ] Search returns denormalized result metadata:
  - Fields: `file_path, start_line, end_line, _distance (score), commit_sha, commit_message, commit_date, author_name, is_head, language, chunk_content`
  - Results sorted by `_distance` ascending (0.0 = perfect match shown first, 1.0 = no match shown last)
  - Scores always in range [0.0, 1.0]
- [ ] Configurable result limit (default 10, range 1-100):
  - `--limit 0` → exit 2, `"Error: --limit must be between 1 and 100 (got 0)"`
  - `--limit 101` → exit 2, `"Error: --limit must be between 1 and 100 (got 101)"`
- [ ] Missing index detection (exit code 8):
  - Check `.gitctx/db/lancedb/` exists
  - Error: `"Error: No index found\nRun: gitctx index"`
- [ ] Corrupted index detection (exit code 1):
  - Catch `lancedb.TableNotFoundError` when opening `code_chunks` table
  - Error: `"Error: Index corrupted (missing code_chunks table)\nFix with: gitctx clear && gitctx index"`
- [ ] Empty result set (exit code 0):
  - Display: `"0 results in {duration:.2f}s"`
  - No error, successful completion
- [ ] Search performance (validated in separate @performance CI workflow):
  - p95 latency <2.0 seconds for 10K vector index (100 queries)
    - Calculate using `numpy.percentile(latencies, 95)`
    - Test fails if p95 >= 2.0 seconds
  - All requests complete within 5.0 seconds
  - Uses VCR cassettes (no real API calls in CI)
- [ ] Memory usage: peak <500MB for 100K vectors (measured with `memory_profiler`)

## BDD Scenarios

**Total**: 13 test scenarios (12 E2E Gherkin + 1 unit test for mocking)

**E2E Scenarios (12):**

```gherkin
# Added to tests/e2e/features/search.feature

Scenario: Search with unquoted multi-word query
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication middleware"
  Then the exit code should be 0
  And results should match query "authentication middleware"

Scenario: Search with flags before query terms
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search --limit 5 find all api references"
  Then the exit code should be 0
  And exactly 5 results should be shown

Scenario: Search from stdin (pipeline)
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I pipe "authentication middleware" to "gitctx search"
  Then the exit code should be 0
  And results should match query "authentication middleware"

Scenario: Search returns results sorted by similarity score
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search authentication middleware"
  Then the exit code should be 0
  And results should be sorted by _distance ascending (0.0 = best match first)
  And each result should show cosine similarity score between 0.0 and 1.0

Scenario: Search with result limit
  Given an indexed repository with 20+ chunks containing "database" keyword
    (use e2e_git_repo_factory with database-focused test files)
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search database --limit 5"
  Then the exit code should be 0
  And exactly 5 results should be shown

Scenario: Search with no results
  Given an indexed repository
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search nonexistent_function_xyz"
  Then the exit code should be 0
  And the output should contain "0 results in"

Scenario: Search before indexing (exit code 8)
  Given no index exists at .gitctx/db/lancedb/
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run "gitctx search test"
  Then the exit code should be 8
  And the output should contain "Error: No index found"
  And the output should contain "Run: gitctx index"

Scenario: Empty stdin with no args (exit code 2)
  Given an indexed repository
  When I run "gitctx search" with empty stdin in non-interactive terminal
  Then the exit code should be 2
  And the output should contain "Error: Query required (from args or stdin)"

Scenario: Invalid result limit too low (exit code 2)
  Given an indexed repository
  When I run "gitctx search test --limit 0"
  Then the exit code should be 2
  And the output should contain "Error: --limit must be between 1 and 100 (got 0)"

Scenario: Invalid result limit too high (exit code 2)
  Given an indexed repository
  When I run "gitctx search test --limit 150"
  Then the exit code should be 2
  And the output should contain "Error: --limit must be between 1 and 100 (got 150)"

@performance
Scenario: Search performance meets p95 latency target
  Given an indexed repository with 10000 chunks
    (use e2e_git_repo_factory with num_files=1000, avg_size=500 tokens)
  And environment variable "OPENAI_API_KEY" is "$ENV"
  When I run search 100 times with query "authentication"
  Then p95 response time should be under 2.0 seconds
  And all requests should complete within 5.0 seconds
```

**Unit Test Scenarios (corrupted database):**

Testing corrupted database requires mocking LanceDB exceptions, which is cleaner in unit tests than E2E:

```python
# tests/unit/cli/test_search.py

def test_corrupted_index_missing_table():
    """Test search with missing code_chunks table."""
    with patch('lancedb.connect') as mock_connect:
        mock_db = Mock()
        mock_db.open_table.side_effect = lancedb.TableNotFoundError("code_chunks not found")
        mock_connect.return_value = mock_db

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 1
        assert "Error: Index corrupted" in result.output
        assert "gitctx clear && gitctx index" in result.output
```

## Technical Design

### Variadic Query Arguments with stdin Support

```python
# src/gitctx/cli/search.py
@app.command()
def search(
    query: Optional[list[str]] = typer.Argument(None, help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, help="Maximum results"),
    format: str = typer.Option("terse", "--format", help="Output format (terse, verbose, mcp)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Alias for --format verbose"),
    mcp: bool = typer.Option(False, "--mcp", help="Alias for --format mcp"),
):
    """Search indexed code using semantic similarity.

    Examples:
        gitctx search authentication middleware
        gitctx search --limit 5 find all api references
        echo "database setup" | gitctx search
        gitctx search < query.txt
    """
    import sys
    from gitctx.cli.symbols import SYMBOLS

    console = Console()

    # 1. Get query from args or stdin
    # If query provided as args, join and use
    if query:
        query_text = " ".join(query)
    # No args - check stdin
    elif sys.stdin.isatty():
        # Interactive terminal with no piped input
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
        )
        raise typer.Exit(2)
    else:
        # Read from piped stdin
        query_text = sys.stdin.read().strip()
        if not query_text:
            console_err.print(
                f"[red]{SYMBOLS['error']}[/red] Error: Query required (from args or stdin)"
            )
            raise typer.Exit(2)

    # 2. Validate limit (Typer handles this, but explicit for clarity)
    if not (1 <= limit <= 100):
        console.print(
            f"[red]{SYMBOLS['error']}[/red] Error: --limit must be between 1 and 100 (got {limit})",
            file=sys.stderr
        )
        raise typer.Exit(2)

    # 3. Initialize LanceDB store
    db_path = Path(".gitctx/db/lancedb")
    if not db_path.exists():
        console.print(
            f"[red]{SYMBOLS['error']}[/red] Error: No index found\n"
            f"Run: gitctx index",
            file=sys.stderr
        )
        raise typer.Exit(8)

    settings = GitCtxSettings()

    try:
        store = LanceDBStore(
            db_path=db_path,
            embedding_model=settings.repo.model.embedding,
            embedding_dimensions=settings.repo.model.embedding_dimensions
        )
        # Validate table exists
        chunk_count = store.count()
        if chunk_count == 0:
            console.print(
                f"[red]{SYMBOLS['error']}[/red] Error: No index found\n"
                f"Run: gitctx index",
                file=sys.stderr
            )
            raise typer.Exit(8)
    except lancedb.TableNotFoundError:
        console.print(
            f"[red]{SYMBOLS['error']}[/red] Error: Index corrupted (missing code_chunks table)\n"
            f"Fix with: gitctx clear && gitctx index",
            file=sys.stderr
        )
        raise typer.Exit(1)

    # 4. Generate query embedding (STORY-0001.3.1)
    start_time = time.time()

    try:
        # Import from STORY-0001.3.1: src/gitctx/search/embeddings.py
        # Usage: QueryEmbedder(settings, store).embed_query(query) -> NDArray[np.floating]
        # Returns: numpy array with shape (dimensions,) where dimensions from settings.repo.model.embedding
        #          - text-embedding-3-large: 3072 dimensions
        #          - text-embedding-3-small: 1536 dimensions
        from gitctx.search.embeddings import QueryEmbedder

        embedder = QueryEmbedder(settings, store)
        query_vector = embedder.embed_query(query_text)
    except ValidationError as e:
        console.print(f"[red]{SYMBOLS['error']}[/red] {e}", file=sys.stderr)
        raise typer.Exit(2)
    except ConfigurationError as e:
        console.print(f"[red]{SYMBOLS['error']}[/red] {e}", file=sys.stderr)
        raise typer.Exit(4)
    except EmbeddingError as e:
        console.print(f"[red]{SYMBOLS['error']}[/red] {e}", file=sys.stderr)
        raise typer.Exit(5)

    # 5. Search LanceDB vector database using cosine distance metric
    results = store.search(
        query_vector=query_vector,  # NDArray[np.floating] from QueryEmbedder.embed_query()
        limit=limit,  # int between 1-100, validated by Typer
        filter_head_only=False  # Search all commits, not just HEAD
    )
    # Returns: list[dict] with 11 denormalized fields per result:
    #   file_path, start_line, end_line, _distance, commit_sha,
    #   commit_message, commit_date, author_name, is_head, language, chunk_content

    duration = time.time() - start_time

    # 6. Format and display results
    # NOTE: Output formatting delegated to STORY-0001.3.3
    # For now, display raw results count and duration only

    # Summary line
    console.print(f"\n{len(results)} results in {duration:.2f}s")
```

### Performance Testing Infrastructure

**pytest marker:**
```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "performance: marks tests as performance validation (separate CI workflow)",
]
```

**GitHub Actions workflow:**
```yaml
# .github/workflows/performance.yml (new file)
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:      # Manual trigger
  push:
    branches: [main]      # Run on main commits

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-extras

      - name: Run performance tests
        run: uv run pytest -m performance -v
        # No OPENAI_API_KEY needed - uses VCR cassettes!
```

**Regular CI update:**
```yaml
# .github/workflows/test.yml (modify existing)
- run: uv run pytest -m "not performance"  # Exclude performance tests
```

## Pattern Reuse

**Reused Patterns:**
- **e2e_git_repo_factory** - Create test repo with N files:
  ```python
  repo = e2e_git_repo_factory(num_files=1000, avg_size=500)
  # Returns: Path to temporary git repo with realistic Python files
  # avg_size=500 tokens → ~10 chunks per file → ~10K total chunks
  ```

- **VCR cassettes with automatic environment** - Record OpenAI API calls:
  ```python
  # In Gherkin Given step: Sets API key in context (shared across scenario)
  @given(parsers.re(r'environment variable "(?P<var>[^"]+)" is "(?P<value>.*)"'))
  def setup_env_var(var: str, value: str, context: dict[str, Any]) -> None:
      if "custom_env" not in context:
          context["custom_env"] = {}
      context["custom_env"][var] = value  # e.g., OPENAI_API_KEY = "sk-test"

  # In When step: Just invoke - e2e_cli_runner auto-merges context["custom_env"]!
  @when('I run "gitctx search query"')
  def run_search(e2e_cli_runner, context: dict[str, Any]) -> None:
      result = e2e_cli_runner.invoke(app, ["search", "query"])
      context.pop("custom_env", None)  # Clear after final invoke
      # VCR intercepts API calls automatically - no code changes needed!

  # Recording: direnv exec . uv run pytest tests/e2e/test_search_features.py --vcr-record=once
  # First run: Records API call with real key to tests/e2e/cassettes/{test_name}.yaml
  # CI/subsequent runs: Replays from cassette (no API key needed)
  ```

- **e2e_git_isolation_env** - Isolated environment dict:
  ```python
  # Used internally by e2e_cli_runner - provides base isolation
  # Contains: {'HOME': temp_dir, 'GIT_CONFIG_GLOBAL': '/dev/null', ...}
  # Prevents test pollution of user's git config
  ```

- **LanceDBStore.search()** - Existing method at `src/gitctx/storage/lancedb_store.py:290`:
  ```python
  results = store.search(
      query_vector=query_vector,  # list[float] or NDArray - duck typing works
      limit=limit,                  # int, default 10
      filter_head_only=False       # bool, default False (search all commits)
  )
  # Returns: list[dict] with 11 fields (see acceptance criteria line 26)
  ```

**New Components:**
- Variadic query argument handling (Typer)
- stdin pipeline support
- Performance marker and separate CI workflow

## Tasks

| ID | Title | Status | Hours | BDD Progress |
|----|-------|--------|-------|--------------|
| [TASK-0001.3.2.1](TASK-0001.3.2.1.md) | Write ALL BDD Scenarios (13 total) | ✅ Complete | 3 (est 3) | 0/13 (all failing) |
| [TASK-0001.3.2.2](TASK-0001.3.2.2.md) | Variadic Args + stdin Support (TDD) | ✅ Complete | 3 (est 4) | 3/13 passing |
| [TASK-0001.3.2.3](TASK-0001.3.2.3.md) | LanceDB Integration + Error Handling (TDD) | ✅ Complete | 6 (est 6) | 4/13 passing |
| [TASK-0001.3.2.4](TASK-0001.3.2.4.md) | Performance Test Infrastructure + CI Workflow | 🔵 Not Started | 4 | 11/13 passing |
| [TASK-0001.3.2.5](TASK-0001.3.2.5.md) | Final Integration + Complete BDD Suite | 🔵 Not Started | 3 | 12/13 passing ✅ |

**Total Hours**: 20 hours (≈6 story points × 3.3h/point)

**Incremental BDD Tracking:**
- TASK-1: 0/13 scenarios (all stubbed, all failing)
- TASK-2: 3/13 scenarios (variadic args, flags, stdin)
- TASK-3: 10/13 scenarios (core search + error handling + corrupted DB unit test)
- TASK-4: 11/13 scenarios (performance validation)
- TASK-5: 12/13 scenarios (final E2E integration) ✅

**Note:** 12 E2E scenarios + 1 unit test scenario (corrupted DB) = 13 total. Network/API errors tested at unit level only.

## BDD Progress

**Initial**: 0/13 scenarios passing (all pending)

Scenarios will be implemented incrementally across tasks.

## Dependencies

**Prerequisites:**
- **STORY-0001.3.1 (Query Embedding Generation) - ⛔ MUST COMPLETE FIRST** - This story calls `generate_query_embedding()` defined in STORY-0001.3.1 (line 246). Cannot implement TASK-2 or TASK-3 without this dependency.
- EPIC-0001.2 (Real Indexing) - Complete ✅ (provides LanceDBStore.search())

**Package Dependencies (already in pyproject.toml):**
- `lancedb` - For vector search
- `langchain-openai` - For embeddings
- `pytest-vcr` - For API response recording

**CI Requirements:**
- VCR cassettes committed to git ✅
- New workflow file: `.github/workflows/performance.yml`
- Update existing workflow: `.github/workflows/test.yml` to exclude performance marker

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| stdin detection across platforms | Low | Medium | Test stdin scenarios on all platforms in CI matrix (Windows, macOS, Linux) |
| Performance test VCR cassette size | Low | Low | Use single query repeated 100× (1 cassette, replayed 100×) |
| LanceDB index corruption detection | Medium | Medium | Catch `TableNotFoundError` specifically, add unit tests for mocking |
| Query argument parsing edge cases | Low | Low | Typer handles `--flag-like-text` correctly, add test for edge case |
| Memory testing at 100K scale | Medium | Low | Use `memory_profiler` with `@profile` decorator, document baseline |

---

**Created**: 2025-10-12
**Last Updated**: 2025-10-12
