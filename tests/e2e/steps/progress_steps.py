"""Step definitions for progress tracking and cost estimation tests.

Pattern Reuse:
- e2e_git_repo_factory: Create test repos with customizable structure
- e2e_git_isolation_env: Secure subprocess environment (prevents SSH key access)
- context fixture: Store CLI results between Given/When/Then steps
- VCR.py cassettes: Record real OpenAI API responses, replay in CI (zero-cost)

All scenarios use VCR.py cassettes for fast, deterministic, zero-cost CI execution.

VCR Recording Workflow:
1. Developer records cassettes once with real OPENAI_API_KEY
2. Cassettes committed to git (API keys stripped)
3. CI/CD replays cassettes (no API key needed, instant execution)

See tests/e2e/cassettes/README.md for recording instructions.
"""

import re
import subprocess
from typing import Any

from pytest_bdd import given, parsers, then, when

# ============================================================================
# Given Steps - Setup Test Repositories
# ============================================================================


@given(parsers.parse("a repository with {n:d} files to index"))
def setup_repo_with_files(n: int, e2e_git_repo_factory, context: dict[str, Any]) -> None:
    """Create a test repository with N files for indexing.

    Uses e2e_git_repo_factory to create repo with secure git operations.
    Stores repo path in context for subsequent steps.

    Args:
        n: Number of files to create in the repository
        e2e_git_repo_factory: Fixture from tests/e2e/conftest.py:254-356
        context: BDD context fixture from tests/e2e/steps/cli_steps.py:12-15
    """
    # Create N Python files with simple content
    files = {}
    for i in range(n):
        files[f"file{i + 1}.py"] = f"""def function_{i + 1}():
    '''Function {i + 1} in test file.'''
    return {i + 1}
"""

    # Create repo with files and commit
    repo_path = e2e_git_repo_factory(files=files, num_commits=1)
    context["repo_path"] = repo_path


@given(parsers.parse("a repository with {n:d} files totaling {size}"))
def setup_repo_with_size(n: int, size: str, e2e_git_repo_factory, context: dict[str, Any]) -> None:
    """Create a test repository with N files totaling specified size.

    Used for cost estimation scenarios where we need specific file sizes.

    Args:
        n: Number of files to create
        size: Target total size (e.g., "2KB", "5MB")
        e2e_git_repo_factory: Fixture from tests/e2e/conftest.py:254-356
        context: BDD context fixture
    """
    # Parse size (e.g., "2KB" -> 2048 bytes)
    size_upper = size.upper()
    if size_upper.endswith("KB"):
        target_bytes = int(size_upper[:-2]) * 1024
    elif size_upper.endswith("MB"):
        target_bytes = int(size_upper[:-2]) * 1024 * 1024
    else:
        raise ValueError(f"Unsupported size format: {size}")

    # Distribute content across n files (within ±10%)
    bytes_per_file = target_bytes // n

    files = {}
    for i in range(n):
        # Create content to approximate bytes_per_file
        # Each line is ~40 bytes with "line X content for testing\n"
        lines_per_file = max(1, bytes_per_file // 40)
        content = "\n".join([f"line {j} content for testing" for j in range(lines_per_file)])
        files[f"file{i + 1}.py"] = content

    # Create repo with files and commit
    repo_path = e2e_git_repo_factory(files=files, num_commits=1)
    context["repo_path"] = repo_path


@given("an empty repository with no indexable files")
def setup_empty_repo(e2e_git_repo_factory, context: dict[str, Any]) -> None:
    """Create an empty git repository with no indexable files.

    "No indexable files" means zero files after blob filtering.
    Creates a repo where all files are filtered out (binary).

    Args:
        e2e_git_repo_factory: Fixture for creating test repos
        context: BDD context fixture
    """
    # Create repo with no .gitignore and only a binary file (will be filtered)
    repo_path = e2e_git_repo_factory(files={"test.bin": "placeholder"}, num_commits=1, add_gitignore=False)

    # Replace with actual binary content (null bytes trigger binary detection)
    (repo_path / "test.bin").write_bytes(b"\x00\x01\x02\x03\x04\x05")

    # Amend the commit to include binary file
    import subprocess
    subprocess.run(
        ["git", "add", "test.bin"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    context["repo_path"] = repo_path


# ============================================================================
# When Steps - Execute CLI Commands
# ============================================================================


@when('I run "gitctx index --dry-run"')
def run_index_dry_run(e2e_git_isolation_env: dict[str, str], context: dict[str, Any]) -> None:
    """Run gitctx index in dry-run mode (cost estimation only).

    Should analyze repo and show estimated tokens/cost without indexing.

    Args:
        e2e_git_isolation_env: Isolated environment fixture
        context: BDD context fixture
    """
    repo_path = context["repo_path"]

    # Run gitctx index --dry-run with isolated environment
    result = subprocess.run(
        ["uv", "run", "gitctx", "index", "--dry-run"],
        cwd=repo_path,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Store results for Then assertions
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr
    context["exit_code"] = result.returncode


# ============================================================================
# Then Steps - Verify Output and Behavior
# ============================================================================


@then(parsers.parse('I should see single-line output matching "{pattern}"'))
def check_output_matches_pattern(pattern: str, context: dict[str, Any]) -> None:
    """Verify stdout matches expected regex pattern.

    Used for terse output validation (TUI_GUIDE.md:208-209).

    Args:
        pattern: Regex pattern to match (e.g., "Indexed \\d+ commits")
        context: BDD context with stdout
    """
    # Unescape Gherkin backslashes for regex
    pattern = pattern.replace("\\\\", "\\")
    stdout = context["stdout"]
    assert re.search(pattern, stdout), f"Pattern '{pattern}' not found in stdout:\n{stdout}"


@then(parsers.parse('cost summary should show format "{pattern}"'))
def check_cost_format(pattern: str, context: dict[str, Any]) -> None:
    """Verify cost is formatted correctly (always 4 decimal places).

    Pattern should match: $\\d+\\.\\d{4}

    Args:
        pattern: Regex pattern for cost format
        context: BDD context with stdout
    """
    # Unescape Gherkin backslashes for regex
    pattern = pattern.replace("\\\\", "\\")
    stdout = context["stdout"]
    assert re.search(pattern, stdout), f"Cost pattern '{pattern}' not found in stdout:\n{stdout}"


@then(parsers.parse('I should see phase markers "{marker1}" and "{marker2}"'))
def check_phase_markers(marker1: str, marker2: str, context: dict[str, Any]) -> None:
    """Verify verbose output shows phase progression markers.

    Expected markers: "→ Walking commit graph", "→ Generating embeddings"
    per TUI_GUIDE.md:230-256.

    Args:
        marker1: First phase marker
        marker2: Second phase marker
        context: BDD context with stdout/stderr
    """
    stderr = context["stderr"]
    assert marker1 in stderr, f"Marker '{marker1}' not found in stderr:\n{stderr}"
    assert marker2 in stderr, f"Marker '{marker2}' not found in stderr:\n{stderr}"


@then("final summary should show statistics table with fields:")
def check_statistics_table(datatable, context: dict[str, Any]) -> None:
    """Verify verbose output includes statistics table with correct formats.

    Table should show: Commits, Unique blobs, Chunks, Tokens, Cost, Time
    with appropriate formatting per TUI_GUIDE.md:246-256.

    Args:
        datatable: pytest-bdd datatable with expected fields and formats
        context: BDD context with stdout/stderr
    """
    stderr = context["stderr"]

    # Verify completion marker
    assert "✓ Indexing Complete" in stderr, f"Completion marker not found in stderr:\n{stderr}"
    assert "Statistics:" in stderr, f"Statistics table not found in stderr:\n{stderr}"

    # Verify each field from the datatable (skip header row)
    for row in datatable[1:]:
        field = row[0]  # First column: Field name
        format_pattern = row[1]  # Second column: Format pattern

        # Unescape Gherkin backslashes: \\d+ becomes \d+ for regex
        # Gherkin escapes backslashes in tables, so we need to unescape them
        format_pattern = format_pattern.replace("\\\\", "\\")

        # Check field exists in output
        assert f"{field}:" in stderr, f"Field '{field}' not found in stderr:\n{stderr}"

        # Extract the value line and verify format
        field_line_match = re.search(rf"{field}:\s+(.+)", stderr)
        if field_line_match:
            value = field_line_match.group(1).strip()
            # Use re.search instead of re.match to find pattern anywhere in value
            assert re.search(format_pattern, value), (
                f"Field '{field}' value '{value}' doesn't match pattern '{format_pattern}'"
            )


@then("I should see estimated tokens")
def check_estimated_tokens(context: dict[str, Any]) -> None:
    """Verify dry-run output shows estimated token count.

    Args:
        context: BDD context with stdout
    """
    stdout = context["stdout"]
    # Look for pattern: "Est. tokens:  \d+,?\d*"
    assert re.search(r"Est\. tokens:\s+\d+,?\d*", stdout), (
        f"Estimated tokens not found in stdout:\n{stdout}"
    )


@then(parsers.parse('estimated cost formatted as "{pattern}"'))
def check_estimated_cost_format(pattern: str, context: dict[str, Any]) -> None:
    """Verify estimated cost uses 4 decimal places format.

    Args:
        pattern: Regex pattern for cost format
        context: BDD context with stdout
    """
    # Unescape Gherkin backslashes for regex
    pattern = pattern.replace("\\\\", "\\")
    stdout = context["stdout"]
    # Look for cost with pattern (e.g., "$\d+\.\d{4}")
    assert re.search(pattern, stdout), f"Cost pattern '{pattern}' not found in stdout:\n{stdout}"


@then(parsers.parse('confidence range "{pattern}"'))
def check_confidence_range(pattern: str, context: dict[str, Any]) -> None:
    """Verify cost estimate includes ±20% confidence range.

    Expected format: "Range: $X.XXXX - $Y.YYYY (±20%)"

    Args:
        pattern: Regex pattern for confidence range
        context: BDD context with stdout
    """
    # Unescape Gherkin backslashes for regex
    pattern = pattern.replace("\\\\", "\\")
    stdout = context["stdout"]
    # Look for range pattern
    assert re.search(pattern, stdout), (
        f"Confidence range pattern '{pattern}' not found in stdout:\n{stdout}"
    )


@then('I should see "No files to index"')
def check_no_files_message(context: dict[str, Any]) -> None:
    """Verify empty repository shows appropriate message.

    Args:
        context: BDD context with stdout
    """
    stdout = context["stdout"]
    assert "No files to index" in stdout, f"Expected 'No files to index' in stdout:\n{stdout}"


@then(parsers.parse("exit code should be {code:d}"))
def check_exit_code(code: int, context: dict[str, Any]) -> None:
    """Verify command exit code matches expected value.

    Args:
        code: Expected exit code (0 for success, 130 for SIGINT)
        context: BDD context with exit_code
    """
    exit_code = context["exit_code"]
    assert exit_code == code, f"Expected exit code {code}, got {exit_code}"
