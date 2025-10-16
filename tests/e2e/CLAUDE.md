# CLAUDE.md - BDD Testing Guidelines for tests/e2e

This document defines the **mandatory BDD testing approach** for all end-to-end tests in gitctx.

**Related Documentation:**

- [Root CLAUDE.md](../../CLAUDE.md) - Overview and workflow
- [Unit Testing](../unit/CLAUDE.md) - TDD practices
- [Documentation](../../docs/CLAUDE.md) - Documentation standards

## 🚨 CRITICAL: BDD Test Requirements

Every user-facing feature MUST have:

1. A Gherkin feature file in `tests/e2e/features/`
2. Step definitions in `tests/e2e/steps/`
3. Tests passing before any feature is considered complete

## BDD Workflow in Story Tasks

**All stories follow incremental BDD implementation across tasks:**

### Correct Task Structure

**Task 1: Write ALL BDD Scenarios**
- Write complete Gherkin scenarios for entire feature
- Create stubbed step definitions that fail (NotImplementedError)
- BDD Progress: **0/N scenarios passing** (all 🔴 RED)
- Purpose: Define complete user-facing behavior upfront

**Tasks 2-N: Implement Features with BDD Steps**
- Implement feature code using TDD (unit tests first)
- Implement relevant BDD step definitions alongside feature
- BDD Progress: **Incremental** (1/N → 5/N → N/N passing)
- Each task specifies which scenarios it will make pass

### Example: Indexing Feature (9 scenarios)

| Task | Implementation | BDD Steps Implemented | Progress |
|------|----------------|----------------------|----------|
| TASK-1 | Write all 9 scenarios | Stub all steps (fail) | 0/9 🔴 |
| TASK-2 | Protocols + models | "Given indexed repo" step | 1/9 🟡 |
| TASK-3 | Core indexer (TDD) | "When I run index", "Then files indexed" | 7/9 🟢 |
| TASK-4 | Integration + CLI | "Then progress shown", final scenario | 9/9 ✅ |

### Key Principles

1. **Never separate "implement BDD" as final task**
   - ❌ WRONG: Task 4 = "Implement all BDD step definitions"
   - ✅ CORRECT: Task 2-4 each implement their relevant steps

2. **Track BDD progress incrementally**
   - Each task shows scenario pass count: 0/9 → 1/9 → 7/9 → 9/9
   - Use "BDD Progress" column in story task table
   - Shows real progress, not just "done/not done"

3. **Stub ALL steps in Task 1**
   ```python
   @when('I run "gitctx index"')
   def run_index_command(cli_runner):
       raise NotImplementedError("Implement in TASK-3")
   ```

4. **Implement steps alongside features**
   - Task builds core indexer → implements "When I run index" step
   - Task adds progress bars → implements "Then I see progress" step
   - Tests and implementation evolve together

### Anti-Patterns to Avoid

❌ **Separate test tasks at end**
```markdown
TASK-3: Implement indexer
TASK-4: Write BDD scenarios
TASK-5: Implement BDD steps
```

❌ **No progress tracking**
```markdown
| Task | BDD Status |
|------|------------|
| 1    | Not started |
| 2    | Not started |
| 3    | Complete    |
```

❌ **Vague step assignment**
```markdown
TASK-2: Implement some BDD steps
TASK-3: Implement more BDD steps
```

✅ **Correct incremental structure**
```markdown
| Task | BDD Progress | Steps This Task |
|------|--------------|-----------------|
| 1    | 0/9 failing  | Stub all 9 scenarios |
| 2    | 1/9 passing  | "Given indexed repo" |
| 3    | 7/9 passing  | "When I index", "Then files indexed" |
| 4    | 9/9 passing  | "Then progress shown" |
```

**See [Root CLAUDE.md](../../CLAUDE.md#task-breakdown-pattern-bddtdd) for complete task breakdown patterns.**

## Directory Structure

```bash
tests/e2e/
├── features/          # Gherkin feature files
│   ├── cli.feature
│   ├── indexing.feature
│   ├── search.feature
│   └── context.feature
├── steps/             # Step definitions
│   ├── __init__.py
│   ├── common_steps.py
│   └── [feature]_steps.py
├── conftest.py       # Shared fixtures
└── test_features.py  # pytest-bdd runner
```

## Writing Feature Files

### Feature Structure Template

```gherkin
Feature: [User-focused feature name]
  As a [type of user]
  I want [goal]
  So that [benefit]

  Background:
    Given [common setup for all scenarios]

  Scenario: [Specific behavior description]
    Given [context/precondition]
    When [action taken by user]
    Then [expected outcome]
    And [additional outcomes]

  Scenario Outline: [Parameterized test]
    When I run "<command>" with "<option>"
    Then I should see <expected_result>

    Examples:
      | command | option | expected_result |
      | search  | --json | JSON output     |
      | index   | --force| Fresh index     |
```

### Feature File Best Practices

1. **One feature per file** - Keep features focused and manageable
2. **User language** - Write from the user's perspective, not implementation
3. **Concrete examples** - Use specific values, avoid vague descriptions
4. **Independent scenarios** - Each scenario should run standalone
5. **Use Background** - Extract common setup to reduce duplication

## Testing Interactive CLI with Typer

### Simulating User Input with CliRunner

**Pattern discovered**: Use `runner.invoke(app, args, input="y\n")` to simulate user input, NOT `sys.stdout.isatty()` mocking.

#### Why This Matters

Typer's `confirm()` function handles TTY detection internally. When using `CliRunner`, it:
1. Accepts input from the `input=` parameter (simulates user typing)
2. Raises `typer.Abort` exception in non-interactive mode (no input provided)

#### Correct Implementation Pattern

**In source code** (e.g., `src/gitctx/cli/index.py`):

```python
# ✅ CORRECT: Let Typer handle TTY detection, catch exception
try:
    if not typer.confirm("Continue?", default=False):
        console_err.print("Cancelled")
        raise typer.Exit(0)
except typer.Abort:
    # Non-interactive environment without --yes flag
    console_err.print("Error: requires confirmation")
    console_err.print("Use --yes to skip confirmation in non-interactive environments")
    raise typer.Exit(code=1) from None

# ❌ WRONG: Manual TTY check prevents testing
if not sys.stdout.isatty():
    console_err.print("Error: requires confirmation")
    raise typer.Exit(code=1)
```

**In E2E test steps**:

```python
# ✅ CORRECT: Simulate user input with input= parameter
@when('I run "gitctx index" interactively and accept')
def run_index_interactively_accept(e2e_cli_runner, context):
    from gitctx.cli.main import app

    # Simulate user typing 'y' at prompt
    result = e2e_cli_runner.invoke(app, ["index"], input="y\n")

    context["result"] = result
    context["exit_code"] = result.exit_code

@when('I run "gitctx index" interactively and decline')
def run_index_interactively_decline(e2e_cli_runner, context):
    from gitctx.cli.main import app

    # Simulate user typing 'n' at prompt
    result = e2e_cli_runner.invoke(app, ["index"], input="n\n")

    context["result"] = result
    context["exit_code"] = result.exit_code

# ❌ WRONG: Mocking isatty() doesn't work with CliRunner
from unittest.mock import patch

@when('I run "gitctx index" interactively')
def run_index_interactively_wrong(e2e_cli_runner, context):
    from gitctx.cli.main import app

    # This won't work - CliRunner replaces stdout entirely
    with patch("sys.stdout.isatty", return_value=True):
        result = e2e_cli_runner.invoke(app, ["index"])
```

#### Why Mocking isatty() Doesn't Work

1. **CliRunner replaces stdout**: `CliRunner` creates a new `StringIO` for stdout, so patching `sys.stdout.isatty` doesn't affect the actual check inside the CLI command
2. **Typer handles detection internally**: `typer.confirm()` already knows how to handle both TTY and non-TTY environments
3. **input= bypasses TTY check**: When `input=` is provided, Typer reads from it directly (doesn't need TTY)

#### Complete Example

**Feature file** (`tests/e2e/features/indexing.feature`):

```gherkin
Scenario: History mode requires confirmation in interactive terminal (accept)
  Given a repository with history mode enabled
  When I run "gitctx index" interactively and accept
  Then the exit code should be 0
  And the error should contain "History Mode Enabled"
  And the error should contain "10-50x higher"
  And indexing should complete successfully
```

**Step definition** (`tests/e2e/steps/indexing_steps.py`):

```python
@when('I run "gitctx index" interactively and accept')
def run_index_interactively_accept(e2e_cli_runner, context: dict[str, Any]) -> None:
    """Run index command with user accepting confirmation.

    Uses CliRunner's input= parameter to simulate user typing 'y' at the prompt.
    This bypasses TTY detection - typer.confirm() accepts the input directly.
    """
    from gitctx.cli.main import app

    # Simulate user input (accept with 'y')
    result = e2e_cli_runner.invoke(app, ["index"], input="y\n")

    context["result"] = result
    context["exit_code"] = result.exit_code
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr or ""
```

#### Reference Implementation

See Typer's own test suite:
- [`/tmp/typer/tests/test_tutorial/test_prompt/test_tutorial001.py`](file:///tmp/typer/tests/test_tutorial/test_prompt/test_tutorial001.py) - Uses `input="Camila\n"` to simulate user input
- Pattern: `runner.invoke(app, input="value\n")` for all interactive prompts

#### Testing stderr vs stdout

Interactive warnings typically go to stderr, so check the right stream:

```python
# ✅ CORRECT: Check stderr for warnings/errors
@then(parsers.parse('the error should contain "{text}"'))
def check_stderr_contains(text: str, context: dict[str, Any]) -> None:
    stderr = context["stderr"]
    assert text in stderr, f"Expected '{text}' in stderr, got: {stderr}"

# Import in test file:
from tests.e2e.steps.cli_steps import check_stderr_contains
```

## Writing Step Definitions

### Basic Step Implementation

```python
# tests/e2e/steps/common_steps.py
import pytest
from pytest_bdd import given, when, then, parsers
from typer.testing import CliRunner
from pathlib import Path

@given("gitctx is installed")
def gitctx_installed():
    """Verify gitctx is available."""
    from gitctx.cli.main import app
    assert app is not None

@given("an indexed repository")
def indexed_repository(tmp_path, sample_repo):
    """Create and index a sample repository."""
    repo_path = tmp_path / "test_repo"
    sample_repo.copy_to(repo_path)

    # Mock or real indexing
    runner = CliRunner()
    result = runner.invoke(app, ["index"], cwd=repo_path)
    assert result.exit_code == 0

    return repo_path

@when(parsers.parse('I run "{command}"'))
def run_command(command, cli_runner):
    """Execute a CLI command."""
    from gitctx.cli.main import app
    args = command.split()
    result = cli_runner.invoke(app, args)
    return result

@then(parsers.parse("the output should contain {text}"))
def check_output_contains(text, result):
    """Verify text appears in output."""
    assert text in result.output

@then("the exit code should be 0")
def check_success(result):
    """Verify command succeeded."""
    assert result.exit_code == 0
```

### Parametrized Steps

```python
@when(parsers.cfparse('I run "gitctx search \'{query}\' --limit {limit:d}"'))
def search_with_limit(query, limit, cli_runner):
    """Search with a result limit."""
    from gitctx.cli.main import app
    result = cli_runner.invoke(app, ["search", query, "--limit", str(limit)])
    return result

@then(parsers.cfparse("I should see {count:d} results"))
def check_result_count(count, result):
    """Verify number of results."""
    # Count result markers in output
    actual_count = result.output.count("File:")
    assert actual_count == count, f"Expected {count} results, got {actual_count}"
```

### Regular Expression Steps

```python
@when(parsers.re(r'I search for "(?P<query>[^"]+)" in (?P<lang>\w+) files'))
def search_by_language(query, lang, cli_runner):
    """Search within specific language files."""
    from gitctx.cli.main import app
    result = cli_runner.invoke(app, [
        "search", query, "--language", lang
    ])
    return result
```

## Common Fixtures

### Common Test Fixtures

```python
# tests/e2e/conftest.py
@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def sample_repo(tmp_path):
    """Create test repository."""
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "main.py").write_text("def auth(): pass")
    (repo / ".gitignore").write_text("*.pyc\n.gitctx/\n")
    subprocess.run(["git", "init"], cwd=repo)
    subprocess.run(["git", "add", "."], cwd=repo)
    subprocess.run(["git", "commit", "-m", "Init"], cwd=repo)
    return repo

@pytest.fixture
def mock_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
```

## Running BDD Tests

### With VCR Cassettes (CI and Normal Development)

Most of the time, tests replay recorded cassettes (no API key needed):

```bash
# Run all e2e tests (uses cassettes)
uv run pytest tests/e2e/

# Run specific feature
uv run pytest tests/e2e/test_search_features.py

# Run with verbose output
uv run pytest tests/e2e/ -vv

# Show print statements
uv run pytest tests/e2e/ -s
```

### With Real API Keys (Debugging and Cassette Recording)

Use `direnv exec .` to load API keys from `.envrc` for real API calls:

```bash
# Debug failing test with real API
direnv exec . uv run pytest tests/e2e/test_search_features.py::test_search_with_no_results -vvs

# Re-record all cassettes
direnv exec . uv run pytest tests/e2e/ --vcr-record=all

# Re-record specific test
direnv exec . uv run pytest tests/e2e/test_embedding_features.py --vcr-record=once

# Run tests that need fresh API responses
direnv exec . uv run pytest tests/e2e/test_search_features.py -vv
```

**When to use direnv:**
- ✅ Debugging test failures (see actual API responses)
- ✅ Recording/re-recording VCR cassettes
- ✅ Validating API behavior changes
- ✅ Developing new tests before recording cassettes

**When NOT to use direnv:**
- ❌ Normal test runs (cassettes are faster and free)
- ❌ CI/CD pipelines (should always use cassettes)
- ❌ Running full test suite (expensive API costs)

### Running in Parallel

```bash
# Run tests in parallel (cassettes only)
uv run pytest tests/e2e/ -n auto

# Parallel with real API (use with caution - rate limits!)
direnv exec . uv run pytest tests/e2e/ -n 2
```

### Generate HTML Report

```bash
uv run pytest tests/e2e/ --html=report.html --self-contained-html
```

## Debugging BDD Tests

```python
@then("something complex happens")
def complex_check(result):
    # Use pdb for debugging
    import pdb; pdb.set_trace()
    assert False, f"Unexpected: {result.output}"
```

Tips:

- Use `pytest -s` to show print statements
- Use `pytest --pdb` to debug failures
- Capture failures to files for analysis

## Test Isolation

```python
@pytest.fixture(autouse=True)
def isolate_tests(monkeypatch):
    """Isolate from system."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("HOME", "/tmp/test-home")
```

Always mock external dependencies and clean up after tests.

## VCR.py Cassette Recording

E2E tests use VCR.py to record real OpenAI API responses and replay them in CI.

### Benefits

- **Real API responses**: Guaranteed to match actual behavior
- **Zero CI costs**: Cassettes replay locally, no API calls
- **No mock maintenance**: Re-record when API changes
- **Deterministic tests**: Same responses every run
- **Fast execution**: Cassette replay is instant

### Which Tests Use VCR?

| Test File | VCR? | Scenarios | Reason |
|-----------|------|-----------|--------|
| `test_embedding_features.py` | ✅ | 7 | OpenAI API calls for embeddings |
| `test_progress_tracking_features.py` | ✅ | 5 | OpenAI calls via indexing pipeline |
| `test_commit_walker_features.py` | ❌ | - | No external APIs (git only) |
| `test_chunking_features.py` | ❌ | - | No external APIs (text processing) |
| `test_lancedb_storage_features.py` | ❌ | - | Local storage only (no API calls) |

**Total**: 12 cassettes (7 embedding + 5 progress tracking)

### Recording Workflow

**One-Time Recording (Developer):**

```bash
# Record cassettes with direnv (loads API key from .envrc)
direnv exec . uv run pytest tests/e2e/test_embedding_features.py --vcr-record=once
direnv exec . uv run pytest tests/e2e/test_progress_tracking_features.py --vcr-record=once

# Verify 12 cassettes created
ls tests/e2e/cassettes/ | wc -l
# Expected output: 12
```

**Re-Recording When API Changes:**

```bash
# Force re-record all cassettes
direnv exec . uv run pytest tests/e2e/ --vcr-record=all
```

**CI/CD Usage (No API Key):**

```bash
# Cassettes in git, tests replay them
uv run pytest tests/e2e/  # Uses cassettes, no API key needed
```

### Cassette Structure

Cassettes are YAML files containing:
- HTTP requests (method, URL, headers, body)
- HTTP responses (status, headers, body)
- Sanitized (API keys removed)

Example: `tests/e2e/cassettes/test_default_terse_output.yaml`

```yaml
version: 1
interactions:
- request:
    method: POST
    uri: https://api.openai.com/v1/embeddings
    body:
      string: '{"input":["def function_1():..."],"model":"text-embedding-3-large"}'
  response:
    status: {code: 200, message: OK}
    body:
      string: '{"data":[{"embedding":[0.123,...]}],"usage":{"total_tokens":42}}'
```

### Pattern Reuse

- Use standard `environment variable "OPENAI_API_KEY" is "sk-test123"` pattern
- VCR intercepts OpenAI client calls automatically
- No code changes needed in step definitions
- Works transparently with subprocess-based E2E tests

### Configuration

VCR configured in `tests/e2e/conftest.py`:

```python
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "cassette_library_dir": "tests/e2e/cassettes",
        "record_mode": "once",
        "filter_headers": ["authorization"],
        ...
    }
```

See `tests/e2e/cassettes/README.md` for detailed recording instructions and troubleshooting.

### Working with CliRunner and Custom Environments

**AUTOMATIC**: The `e2e_cli_runner` fixture automatically merges `context["custom_env"]` into the environment when `invoke()` is called. No boilerplate needed!

#### How It Works

The fixture wraps `CliRunner.invoke()` to automatically merge custom environment variables:

```python
@pytest.fixture
def e2e_cli_runner(e2e_git_isolation_env, monkeypatch, request) -> CliRunner:
    runner = CliRunner(env=e2e_git_isolation_env)

    # Wrap invoke() to auto-merge context["custom_env"]
    original_invoke = runner.invoke
    def invoke_with_auto_env(*args, **kwargs):
        if 'env' not in kwargs:
            context = request.getfixturevalue('context')
            env = runner.env.copy()
            if "custom_env" in context:
                env.update(context["custom_env"])
            kwargs['env'] = env
        return original_invoke(*args, **kwargs)

    runner.invoke = invoke_with_auto_env
    return runner
```

#### Writing Steps (The Easy Way)

Just call `invoke()` normally - environment merges automatically:

```python
@when('I run "gitctx search query"')
def run_search(e2e_cli_runner, context: dict[str, Any], monkeypatch) -> None:
    """Custom When step with API calls."""
    from gitctx.cli.main import app

    # Change directory if needed
    if repo_path := context.get("repo_path"):
        monkeypatch.chdir(repo_path)

    # Just invoke - environment merges automatically!
    result = e2e_cli_runner.invoke(app, ["search", "query"])

    # Optional: Clear custom_env if you want
    context.pop("custom_env", None)

    # Store results
    context["result"] = result
    context["stdout"] = result.stdout
    context["exit_code"] = result.exit_code
```

**No boilerplate needed!** The fixture handles everything.

#### When to Clear `custom_env`

**Clear in "final" invoke steps** (typically `@when` steps):
- Prevents env leaking to next command in scenario
- Use `context.pop("custom_env", None)`

**Don't clear in "setup" steps** (typically `@given` steps):
- Allows multiple invokes to share same env
- Example: `query_previously_searched` → `run_command`

#### Override Behavior (Advanced)

Pass `env=` explicitly if you need custom behavior:

```python
# Bypass auto-merge, use completely custom env
result = e2e_cli_runner.invoke(app, args, env={"CUSTOM": "value"})
```

#### Why This Matters for VCR

With automatic environment merging:
- ✅ No boilerplate at invoke sites
- ✅ API calls succeed with real key during recording
- ✅ VCR creates cassettes automatically
- ✅ CI/CD replays cassettes (no key needed)
- ✅ Less to remember for future test writers

See working examples in:
- `tests/e2e/steps/cli_steps.py` - `run_command()`
- `tests/e2e/steps/progress_steps.py` - `run_index_dry_run()`
- `tests/e2e/steps/search_steps.py` - `query_previously_searched()`

## Fixture Architecture

### Core Fixtures

#### `context` - Shared Scenario State

```python
@pytest.fixture
def context() -> dict[str, Any]:
    """Shared context between BDD steps in a scenario."""
```

- **Purpose**: Pass data between Given/When/Then steps
- **Common keys**: `repo_path`, `custom_env`, `result`, `stdout`, `stderr`, `exit_code`
- **Location**: `tests/e2e/conftest.py` (single source of truth)
- **Usage**: Auto-injected into step definitions

#### `e2e_indexed_repo` - Pre-indexed Repository

```python
@pytest.fixture
def e2e_indexed_repo(
    e2e_git_repo,
    e2e_cli_runner,
    context,
    e2e_session_api_key,
    monkeypatch
) -> Path:
    """Create and index a basic git repository with VCR cassette recording."""
```

- **Purpose**: Provides indexed repo for search tests
- **Security**: Uses `e2e_git_isolation_env` (no SSH/GPG access)
- **VCR**: Records OpenAI API calls to cassettes
- **Auto-merge**: API key auto-merged via `context["custom_env"]`
- **Cleanup**: `monkeypatch.chdir()` ensures directory restored

#### `e2e_indexed_repo_factory` - Custom Indexed Repos

```python
@pytest.fixture
def e2e_indexed_repo_factory(...):
    """Factory for creating indexed repositories with custom content."""
    def _make_indexed_repo(files=None, num_commits=1, branches=None, add_gitignore=True):
        ...
    return _make_indexed_repo
```

- **Purpose**: Create indexed repos with specific structure
- **Parameters**:
  - `files`: Dict of {path: content}
  - `num_commits`: Number of commits to create
  - `branches`: List of branch names
  - `add_gitignore`: Whether to add .gitignore
- **Directory handling**: Uses `os.chdir()` with try/finally (can't use monkeypatch in closure)
- **Example**: `repo = e2e_indexed_repo_factory(files={"test.py": "..."}, num_commits=5)`

### Security Isolation Pattern

All fixtures maintain security isolation by:
1. **Base environment**: `e2e_git_isolation_env` blocks SSH keys, GPG keys, git config
2. **Auto-merge pattern**: `e2e_cli_runner` automatically merges `context["custom_env"]`
3. **No cleanup needed**: pytest's monkeypatch/autouse fixtures handle restoration

See `tests/e2e/test_fixtures.py` for 13 comprehensive fixture tests validating this behavior.

## Common Patterns

### Testing CLI Output

```python
@then("the output should be formatted as JSON")
def check_json_output(result):
    import json
    try:
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))
    except json.JSONDecodeError:
        pytest.fail(f"Output is not valid JSON: {result.output}")
```

### Testing File Creation

```python
@then("a .gitctx directory should exist")
def check_gitctx_dir(repo_path):
    gitctx_dir = repo_path / ".gitctx"
    assert gitctx_dir.exists(), f"Directory {gitctx_dir} does not exist"
    assert gitctx_dir.is_dir()

    # Check expected structure
    assert (gitctx_dir / "embeddings").exists()
    assert (gitctx_dir / "manifest.json").exists()
```

### Testing Error Handling

```python
@when("I run an invalid command")
def run_invalid_command(cli_runner):
    from gitctx.cli.main import app
    result = cli_runner.invoke(app, ["invalid-command"])
    assert result.exit_code != 0
    return result

@then("I should see an error message")
def check_error_message(result):
    assert "error" in result.output.lower() or "Error" in result.output
```

### Progress Testing

```python
@then("I should see a progress bar")
def check_progress_bar(result):
    assert any(c in result.output for c in ["%", "━", "■"])
```

## CI/CD Integration

Run BDD tests in CI:

```yaml
# .github/workflows/bdd-tests.yml
jobs:
  bdd-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - run: |
        pip install uv
        uv sync --all-extras
        uv run pytest tests/e2e/ --junit-xml=junit.xml
```

## Tips and Tricks

### 1. Use scenarios() for Auto-discovery

```python
# tests/e2e/test_features.py
from pytest_bdd import scenarios

# Automatically discover all .feature files
scenarios('../features')
```

### 2. Share Steps Across Features

```python
# tests/e2e/steps/common_steps.py
from pytest_bdd import given

@given("gitctx is configured")
def gitctx_configured(mock_api_key, temp_config_dir):
    """Shared setup for all features."""
    # This step can be used in any feature file
    pass
```

### 3. Use Pytest Markers

```python
@pytest.mark.slow
@scenario('features/indexing.feature', 'Index large repository')
def test_large_repo():
    """Mark slow tests for selective running."""
    pass

# Run only fast tests: pytest -m "not slow"
```

### 4. Table-Driven Tests

```gherkin
Scenario Outline: Search with different queries
  When I run "gitctx search '<query>'"
  Then results should include "<expected>"

  Examples:
    | query          | expected        |
    | authentication | login function  |
    | database       | connection pool |
    | api endpoint   | route handler   |
```

## 🚫 Common Mistakes to Avoid

1. **Writing implementation-specific scenarios** - Focus on user behavior
2. **Overly complex step definitions** - Keep steps simple and reusable
3. **Not isolating tests** - Always mock external dependencies
4. **Skipping scenarios** - Fix them or remove them, never skip
5. **Testing too much in one scenario** - One behavior per scenario

## Resources

- [pytest-bdd documentation](https://pytest-bdd.readthedocs.io/)
- [Gherkin reference](https://cucumber.io/docs/gherkin/reference/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
