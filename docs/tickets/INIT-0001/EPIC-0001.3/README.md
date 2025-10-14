# EPIC-0001.3: Vector Search Implementation

**Parent Initiative**: [INIT-0001](../README.md)
**Status**: 🟡 In Progress
**Estimated**: 13 story points
**Progress**: ████████░░ 77% (10/13 points complete)

## Overview

Replace mock search results with actual vector similarity search using LanceDB. Query embeddings are generated, compared against indexed embeddings, and results are ranked and formatted for display.

## Goals

- Query existing LanceDB vector database populated by EPIC-0001.2
- Generate query embeddings via OpenAI API
- Implement similarity search with ranking
- Format results with syntax highlighting via Rich
- Reduce search latency from baseline ~5s to <2s p95 (measured via `time gitctx search 'query'` over 100 queries on 10K vector index) through IVF-PQ indexing and LanceDB native caching

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-0001.3.1](STORY-0001.3.1/README.md) | Query Embedding Generation | ✅ Complete | 4 |
| [STORY-0001.3.2](STORY-0001.3.2/README.md) | Vector Similarity Search | ✅ Complete | 6 |
| [STORY-0001.3.3](STORY-0001.3.3/README.md) | Result Formatting & Output | 🔵 Not Started | 3 |

**Planning Status**: All 3 stories fully planned (15 tasks total, 60-61 hours estimated). Implementation order: STORY-0001.3.1 → STORY-0001.3.2 → STORY-0001.3.3 (strict sequence due to dependencies). Ready for implementation.

## BDD Specifications

```gherkin
# tests/e2e/features/search.feature

Feature: Code Search
  As a developer
  I want to search my codebase
  So that I can find relevant code quickly

  Background:
    Given an indexed repository

  Scenario: Basic search
    When I run "gitctx search 'authentication middleware'"
    Then results should be returned within 2 seconds
    And results should show file paths
    And results should show line numbers
    And results should be syntax highlighted

  Scenario: Search with no results
    When I run "gitctx search 'nonexistent_function_xyz'"
    Then the output should say "0 results in"
    And the exit code should be 0

  Scenario: Search with limit
    When I run "gitctx search 'database' --limit 5"
    Then exactly 5 results should be shown
    And results should be sorted by similarity score (descending)

  Scenario: Search with MCP output
    When I run "gitctx search 'api endpoint' --mcp"
    Then output should be valid markdown with YAML frontmatter (schema: file_path, line_numbers, score)
    And markdown should contain file paths and code blocks
    And markdown should contain similarity scores and metadata

  Scenario: Search shows relevance
    When I run "gitctx search 'user authentication'"
    Then each result should show a cosine similarity score (0.0-1.0)
    And scores should be between 0 and 1
    And results should be ordered by score

  Scenario: Search with empty query
    When I run "gitctx search ''"
    Then the output should say "Error: missing argument: QUERY"
    And the exit code should be 1

  Scenario: Search before indexing
    Given no index exists at .gitctx/db/lancedb/
    When I run "gitctx search 'test'"
    Then the output should say "Error: no index found"
    And the output should contain "Run: gitctx index"
    And the exit code should be 8

  Scenario: Search with invalid limit
    When I run "gitctx search 'test' --limit 0"
    Then the output should say "Error: invalid value for --limit"
    And the output should contain "Expected: integer (1-100)"
    And the exit code should be 1

  Scenario: Search with corrupted database
    Given .gitctx/db/lancedb/ exists but code_chunks table is missing
    When I run "gitctx search 'test'"
    Then the output should say "Error: index corrupted"
    And the output should contain "Fix with:"
    And the output should contain "gitctx clear && gitctx index"
    And the exit code should be 1

  Scenario: Search performance meets p95 latency target
    Given an indexed repository with 10000 chunks
    When I run "gitctx search 'authentication'" 100 times
    Then p95 response time should be under 2.0 seconds
    And all requests should complete within 5.0 seconds
    And cache hit rate should be >30% after first 10 queries (LanceDB default behavior)

  Scenario: Search with OpenAI API failure
    Given an indexed repository
    And OpenAI API is unreachable (mock network failure)
    When I run "gitctx search 'test query'"
    Then the output should say "Error: network error"
    And the output should contain "Failed to connect to OpenAI API"
    And the exit code should be 5
```

## Technical Design

### Search CLI Implementation (Reusing Existing Components)

```python
# src/gitctx/cli/search.py
"""Search command implementation using existing LanceDB and OpenAI components."""

from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from gitctx.core.config import GitCtxSettings
from gitctx.storage.lancedb_store import LanceDBStore
from gitctx.core.exceptions import ConfigurationError


def search_command(query: str, limit: int = 10, verbose: bool = False) -> None:
    """Search indexed code using vector similarity.

    Args:
        query: Search query string
        limit: Maximum results to return (1-100)
        verbose: Show code context with syntax highlighting

    Raises:
        ValueError: If query is empty or limit out of range
        ConfigurationError: If LanceDB not initialized or API key missing
    """
    # Validate inputs
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if not 1 <= limit <= 100:
        raise ValueError(f"Limit must be between 1 and 100, got {limit}")

    # Load configuration
    settings = GitCtxSettings()
    api_key = settings.get("api_keys.openai")
    if not api_key:
        raise ConfigurationError(
            "OpenAI API key required. Set OPENAI_API_KEY or run: "
            "gitctx config set api_keys.openai sk-..."
        )

    # Initialize LanceDB store (reuses existing implementation)
    db_path = Path(".gitctx/db/lancedb")
    if not db_path.exists():
        raise ConfigurationError(
            "No index found. Run 'gitctx index' first."
        )

    store = LanceDBStore(
        db_path=db_path,
        embedding_model=settings.repo.model.embedding,  # "text-embedding-3-large"
        embedding_dimensions=3072
    )

    # Check if table exists (detect corrupted DB)
    try:
        chunk_count = store.count()
        if chunk_count == 0:
            raise ConfigurationError("Index is empty. Run 'gitctx index' first.")
    except (lancedb.TableNotFoundError, KeyError) as e:
        # LanceDB raises TableNotFoundError when code_chunks table missing
        raise ConfigurationError(
            "Index corrupted (missing code_chunks table). Run 'gitctx index --force' to rebuild."
        ) from e
    except Exception:
        # Re-raise unexpected errors for debugging
        raise

    # Initialize OpenAI embedder for query embedding generation
    embedder = OpenAIEmbeddings(
        model=settings.repo.model.embedding,
        dimensions=3072,
        api_key=SecretStr(api_key)
    )

    # Generate query embedding
    query_vector = embedder.embed_query(query)

    # Search LanceDB (returns list[dict] with denormalized metadata)
    results = store.search(
        query_vector=query_vector,
        limit=limit,
        filter_head_only=False
    )

    # Display results
    console = Console()

    if not results:
        console.print("0 results")
        return

    for result in results:
        if verbose:
            # Verbose mode: Show syntax-highlighted code context
            head_marker = "●" if result["is_head"] else " "

            console.print(
                f"\n{result['file_path']}:{result['start_line']}-{result['end_line']} "
                f"({result['_distance']:.2f}) {head_marker} {result['commit_sha'][:7]}"
            )
            console.print(f"[dim]{result['commit_message']}[/dim]")

            # Syntax highlight code with Rich
            syntax = Syntax(
                result["chunk_content"],
                result["language"],
                line_numbers=True,
                start_line=result["start_line"],
                theme="monokai"
            )
            console.print(syntax)
        else:
            # Terse mode: File:line:score format (TUI_GUIDE line 425-430)
            head_marker = "●" if result["is_head"] else ""
            console.print(
                f"{result['file_path']}:{result['start_line']}:{result['_distance']:.2f} "
                f"{head_marker}{result['commit_sha'][:7]} "
                f"({result['commit_date']}, {result['author_name']}) "
                f'"{result["commit_message"][:50]}"'
            )

    console.print(f"\n{len(results)} results")
```

### Key Design Decisions

1. **No new classes** - Reuses `LanceDBStore`, `OpenAIEmbeddings`, `GitCtxSettings`
2. **No custom caching** - LanceDB handles result caching internally, embedder has built-in query cache
3. **Rich.Syntax for highlighting** - No custom formatter needed, Rich handles all formatting
4. **TUI_GUIDE alignment** - Terse human-readable by default, code context with `--verbose`, structured markdown for AI consumption with `--mcp` (see TUI_GUIDE.md lines 14, 28-32, 418)
5. **Error handling** - Validates inputs (query length 1-1000 chars, limit 1-100), detects missing/corrupted index (TableNotFoundError), no retry logic (fail fast), timeout 30s (OpenAI default)
6. **Configuration** - Uses existing `GitCtxSettings` for API keys and model selection

## Dependencies

### Story Implementation Order
**⚠️ STRICT SEQUENCE REQUIRED:**
1. STORY-0001.3.1 (Query Embedding) - Must complete first
2. STORY-0001.3.2 (Vector Search) - Depends on STORY-0001.3.1
3. STORY-0001.3.3 (Result Formatting) - Depends on STORY-0001.3.2

### Prerequisites
- **EPIC-0001.1** (CLI Foundation) must be complete
  - Requires Typer CLI framework (`src/gitctx/cli/main.py`)
  - Requires Rich console for output formatting (used by TUI_GUIDE)
  - Without this, no CLI commands can execute
- **EPIC-0001.2** (Real Indexing Implementation) must be complete
  - Requires LanceDB populated at `.gitctx/db/lancedb/`
  - Requires code_chunks table with embeddings and metadata
  - Without this, search has nothing to query

### Package Dependencies
- `lancedb>=0.3.0` - Vector database (already in pyproject.toml)
- `pyarrow>=14.0.0` - LanceDB backend (already in pyproject.toml)
- `langchain-openai>=1.0.0a0` - OpenAI embeddings API client (exits alpha soon, already in pyproject.toml)
- `rich>=13.7.0` - Terminal formatting and syntax highlighting (includes Pygments dependency, already in pyproject.toml)

### Existing Components (Pattern Reuse)
- **LanceDBStore** (`src/gitctx/storage/lancedb_store.py`) - `.search()`, `.optimize()`, `.count()` methods
- **OpenAIEmbedder** (`src/gitctx/embeddings/openai_embedder.py`) - For generating query embeddings
- **GitCtxSettings** (`src/gitctx/core/config.py`) - Configuration: `repo.model.embedding`, `user.api_keys.openai`

### Testing Patterns (Pattern Reuse by Story)
- **STORY-0001.3.1** (Query Embedding): Use `@pytest.mark.vcr()` for OpenAI API mocking (line 276)
- **STORY-0001.3.2** (Vector Search): Use `e2e_git_repo_factory` for performance testing (line 272)
- **STORY-0001.3.3** (Result Formatting): Use `e2e_git_isolation_env` for CLI subprocess testing (line 274)

### Testing Patterns (General Reuse)
- **e2e_git_repo_factory** (`tests/e2e/conftest.py:262`) - Parameterized git repo creation for search tests
  - Usage: `repo = e2e_git_repo_factory(files={...}, num_commits=10)`
- **e2e_cli_runner** (`tests/e2e/conftest.py:135`) - Isolated CLI runner with environment isolation
  - Usage: `result = e2e_cli_runner.invoke(app, ["search", query])`
- **VCR cassettes** (`tests/e2e/conftest.py:370`) - Record/replay OpenAI API responses for deterministic tests
  - Usage: `@pytest.mark.vcr()` decorator on search tests

## Success Criteria

1. **Fast search** - p95 latency <2.0 seconds for 10K vector index, measured via `time gitctx search 'query'` over 100 queries (see BDD scenario line 92-96)
2. **Result relevance >0.7 average** - Top 5 results have cosine similarity >0.7 when querying gitctx's own codebase with predefined test queries:
   - "authentication middleware" → src/auth.py:15-23 (expected >0.8)
   - "vector search" → src/gitctx/storage/lancedb_store.py:287-307 (expected >0.85)
   - "embedding generation" → src/gitctx/embeddings/openai_embedder.py:44-80 (expected >0.9)
   - Measured by running: `gitctx search 'authentication middleware' | grep 'src/auth.py'` and checking score >0.8
   Verified with BDD scenario `Scenario: Search shows relevance` (line 64-68) comparing actual scores to expected thresholds
3. **Formatted output with syntax highlighting** - Results display exactly as (verified in BDD scenario line 42-46):
   ```
   src/auth.py:15-23 (0.847) ● a1b2c3d
   User authentication middleware
   [syntax-highlighted code block with line numbers 15-23]

   src/login.py:45-52 (0.782)   d4e5f6g
   Login handler implementation
   [syntax-highlighted code block with line numbers 45-52]
   ```
   Format: `{file_path}:{start}-{end} ({score:.3f}) {head_marker} {commit_sha[:7]}`
   - HEAD commits marked with `●`, historic commits with space ` `
   - Code uses `Rich.Syntax(line_numbers=True, start_line=N, theme="monokai")`
   - 1 blank line separator between results
4. **Edge case handling** - Returns documented exit codes and messages (verified by BDD scenarios):

   | Scenario | Exit Code | Message | BDD Scenario |
   |----------|-----------|---------|--------------|
   | Empty query | 1 | "Error: missing argument: QUERY" | Line 71-74 |
   | No index | 8 | "Error: no index found" + "Run: gitctx index" | Line 76-80 |
   | No results | 0 | "0 results in 0.12s" | Line 49-51 |
   | Corrupted DB | 1 | "Error: index corrupted" + "Fix with: gitctx clear && gitctx index" | Line 86-92 |
   | API failure | 5 | "Error: network error" + "Failed to connect to OpenAI API" | Line 99-106 |
5. **Resource efficiency** - Measured with `memory_profiler` on search_command():
   - Peak memory <500MB for 100K vectors (baseline: `mprof run gitctx search 'test' --limit 10` with empty result set)
   - IVF-PQ index auto-created at 256+ vectors (LanceDB default)
   - Query latency <100ms for top-10 results after index build (excludes embedding generation time ~1.8s)
   - Verification: `@profile` decorator + `mprof plot` analysis

## Notes

- LanceDB provides SQL-like queries with vector search
- Caching is critical for responsive UX
- Result formatting makes or breaks usability
- Performance optimization is iterative

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-12 (STORY-0001.3.1 planning complete)
