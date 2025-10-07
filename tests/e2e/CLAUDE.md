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

### Run All E2E Tests

```bash
uv run pytest tests/e2e/
```

### Run Specific Feature

```bash
uv run pytest tests/e2e/ -k "search"
```

### Run with Verbose Output

```bash
uv run pytest tests/e2e/ -vv
```

### Show Print Statements

```bash
uv run pytest tests/e2e/ -s
```

### Run in Parallel

```bash
uv run pytest tests/e2e/ -n auto
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
