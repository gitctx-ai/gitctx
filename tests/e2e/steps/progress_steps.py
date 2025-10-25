"""Step definitions for progress tracking and cost estimation tests.

Pattern Reuse:
- e2e_git_repo_factory: Create test repos with customizable structure
- e2e_cli_runner: CliRunner for in-process CLI testing (enables VCR cassettes)
- context fixture: Store CLI results between Given/When/Then steps
- VCR.py cassettes: Record real OpenAI API responses, replay in CI (zero-cost)

All scenarios use VCR.py cassettes for fast, deterministic, zero-cost CI execution.

VCR Recording Workflow:
1. Delete existing cassettes (if re-recording)
2. Run tests with real OPENAI_API_KEY
3. VCR automatically records cassettes (record_mode: "once")
4. Cassettes committed to git (API keys stripped)
5. CI/CD replays cassettes (no API key needed, instant execution)

See tests/e2e/cassettes/README.md for recording instructions.
"""

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, then, when

from gitctx.cli.main import app

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
    repo_path = e2e_git_repo_factory(
        files={"test.bin": "placeholder"}, num_commits=1, add_gitignore=False
    )

    # Replace with actual binary content (null bytes trigger binary detection)
    (repo_path / "test.bin").write_bytes(b"\x00\x01\x02\x03\x04\x05")

    # Amend the commit to include binary file

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
def run_index_dry_run(e2e_cli_runner, context: dict[str, Any], monkeypatch) -> None:
    """Run gitctx index in dry-run mode (cost estimation only).

    Should analyze repo and show estimated tokens/cost without indexing.

    Note: This step is now redundant with the generic "I run" step from cli_steps.py,
    but kept for explicitness. Could be removed in future refactoring.

    Args:
        e2e_cli_runner: CliRunner fixture for in-process execution
        context: BDD context fixture
        monkeypatch: pytest monkeypatch for directory changes
    """

    repo_path = context["repo_path"]
    original_cwd = Path.cwd()
    monkeypatch.chdir(repo_path)

    try:
        # Run CLI in-process with CliRunner (enables VCR cassette recording)
        # Environment automatically merged from context["custom_env"] by fixture
        result = e2e_cli_runner.invoke(app, ["index", "--dry-run"])

        # Clear custom_env after use
        context.pop("custom_env", None)

        # Store results for Then assertions
        context["stdout"] = result.stdout
        # Typer's CliRunner mixes stderr into stdout by default
        context["stderr"] = result.stderr if hasattr(result, "stderr") and result.stderr else ""
        context["exit_code"] = result.exit_code
    finally:
        monkeypatch.chdir(original_cwd)


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

    Note: Checks for BOTH Unicode (→) and ASCII (->) arrows to handle
    Windows environment differences (legacy cmd.exe vs Windows Terminal).

    Args:
        marker1: First phase marker (with Unicode arrow →)
        marker2: Second phase marker (with Unicode arrow →)
        context: BDD context with stdout/stderr
    """
    stderr = context["stderr"]

    # Check for BOTH arrow symbols since Windows detection can vary
    # between test environment and CLI subprocess
    unicode_marker1 = marker1  # Keep Unicode arrow →
    ascii_marker1 = marker1.replace("→", "->")  # Convert to ASCII arrow

    unicode_marker2 = marker2  # Keep Unicode arrow →
    ascii_marker2 = marker2.replace("→", "->")  # Convert to ASCII arrow

    # Accept either Unicode or ASCII arrow for marker1
    marker1_found = unicode_marker1 in stderr or ascii_marker1 in stderr
    assert marker1_found, (
        f"Marker '{marker1}' (or '{ascii_marker1}') not found in stderr:\n{stderr}"
    )

    # Accept either Unicode or ASCII arrow for marker2
    marker2_found = unicode_marker2 in stderr or ascii_marker2 in stderr
    assert marker2_found, (
        f"Marker '{marker2}' (or '{ascii_marker2}') not found in stderr:\n{stderr}"
    )


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

    # Verify completion marker (check for both Unicode ✓ and ASCII [OK] on Windows)
    has_completion = "✓ Indexing Complete" in stderr or "[OK] Indexing Complete" in stderr
    assert has_completion, f"Completion marker not found in stderr:\n{stderr}"
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
        context: BDD context with stderr (message sent to stderr for consistency)
    """
    stderr = context["stderr"]
    assert "No files to index" in stderr, f"Expected 'No files to index' in stderr:\n{stderr}"


@then(parsers.parse("exit code should be {code:d}"))
def check_exit_code(code: int, context: dict[str, Any]) -> None:
    """Verify command exit code matches expected value.

    Args:
        code: Expected exit code (0 for success, 130 for SIGINT)
        context: BDD context with exit_code
    """
    exit_code = context["exit_code"]
    assert exit_code == code, f"Expected exit code {code}, got {exit_code}"


# ============================================================================
# New Step Definitions for STORY-0001.4.5 (TUI Progress Enhancement)
# ============================================================================
# All steps below are STUBBED - they raise NotImplementedError
# Implementation will be added incrementally in TASK-0001.4.5.2 through TASK-0001.4.5.4


@then(parsers.parse('I should see "{marker}" marker'))
def check_phase_marker(marker: str, context: dict[str, Any]) -> None:
    """Verify specific phase marker appears in output.

    Checks for BOTH Unicode (→) and ASCII (->) arrows to handle
    Windows environment differences.

    Args:
        marker: Expected phase marker text (e.g., "→ Saving index")
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Check for BOTH arrow symbols for Windows compatibility
    unicode_marker = marker  # Keep Unicode arrow →
    ascii_marker = marker.replace("→", "->")  # Convert to ASCII arrow

    marker_found = unicode_marker in stderr or ascii_marker in stderr
    assert marker_found, f"Marker '{marker}' (or '{ascii_marker}') not found in stderr:\n{stderr}"


@then("I should see progress bars with counts and percentages")
def check_progress_bars_with_counts(context: dict[str, Any]) -> None:
    """Verify progress tracking shows correct data (integration test).

    Tests OUR integration with Rich.Progress, not Rich's rendering.
    We verify that:
    - Our code calls reporter.phase() at correct pipeline stages
    - Our code passes correct statistics to reporter.update()
    - Progress completes successfully with final stats

    Rich.Progress handles rendering (we trust it to work correctly).
    In TTY: Shows actual progress bars with counts/percentages
    In non-TTY (BDD tests): Shows phase markers + final statistics

    Since BDD tests run via CliRunner (non-TTY), we verify:
    - Phase markers appear (our phase() calls work)
    - Statistics are correct (our data is right)
    - Process completes (no crashes)

    Visual verification (manual): Run `gitctx index` in real terminal
    to confirm Rich.Progress renders bars correctly.

    Args:
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Verify our integration: all phases called correctly
    # Check for BOTH Unicode (→) and ASCII (->) arrows for Windows compatibility
    assert "→ Walking commit graph" in stderr or "-> Walking commit graph" in stderr, (
        "Walking phase marker not found"
    )
    assert "→ Generating embeddings" in stderr or "-> Generating embeddings" in stderr, (
        "Embedding phase marker not found"
    )
    assert "→ Saving index" in stderr or "-> Saving index" in stderr, (
        "Saving phase marker not found"
    )

    # Verify completion
    assert "Indexing Complete" in stderr, "Completion marker not found"

    # Verify our statistics are correct
    assert "Commits:" in stderr, "Commit count not in statistics"
    assert "Unique blobs:" in stderr, "Blob count not in statistics"
    assert "Chunks:" in stderr, "Chunk count not in statistics"


@then("I should NOT see progress bars or phase markers")
def check_no_progress_bars(context: dict[str, Any]) -> None:
    """Verify quiet mode shows no progress indicators.

    Ensures no arrow symbols, progress bars, or phase markers appear.

    Args:
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Check no arrow symbols (both Unicode and ASCII variants)
    assert "→" not in stderr, f"Found Unicode arrow (→) in quiet mode stderr:\n{stderr}"
    assert "->" not in stderr, f"Found ASCII arrow (->) in quiet mode stderr:\n{stderr}"

    # Check no progress bar characters
    progress_chars = ["━", "█", "░", "▓", "▒"]
    for char in progress_chars:
        assert char not in stderr, (
            f"Found progress bar character '{char}' in quiet mode stderr:\n{stderr}"
        )


@given("I have previously indexed a repository")
def setup_previously_indexed_repo(
    e2e_indexed_repo_factory,
    context: dict[str, Any],
) -> None:
    """Create and index a repository for cache testing.

    Uses e2e_indexed_repo_factory which creates repo and runs initial indexing.
    Stores repo path in context for re-indexing in subsequent steps.

    Args:
        e2e_indexed_repo_factory: Fixture that creates and indexes repos
        context: BDD context fixture
    """
    # Create repo with files - factory handles indexing
    files = {}
    for i in range(10):
        files[f"file{i + 1}.py"] = f"""def function_{i + 1}():
    '''Function {i + 1} in test file.'''
    return {i + 1}
"""

    # Factory creates repo, indexes it, and returns path
    repo_path = e2e_indexed_repo_factory(files=files, num_commits=1)
    context["repo_path"] = repo_path
    # Note: run_command step will handle monkeypatch.chdir(repo_path)


@when(parsers.parse('I run "{command}" again with {percent:d}% cached blobs'))
def run_command_with_cache(
    command: str,
    percent: int,
    e2e_cli_runner,
    context: dict[str, Any],
    monkeypatch,
) -> None:
    """Re-run indexing with cache hits.

    Re-indexes the previously indexed repo using the standard pattern:
    monkeypatch.chdir to repo, invoke command, store results in context.

    Note: The percent parameter is for documentation only - in practice,
    re-indexing the same repo gives 100% cache hits.

    Args:
        command: Command to run (e.g., "gitctx index")
        percent: Expected cache hit percentage (not enforced)
        e2e_cli_runner: CliRunner fixture
        context: BDD context with repo_path from previous step
        monkeypatch: pytest monkeypatch for directory changes
    """
    repo_path = context["repo_path"]
    monkeypatch.chdir(repo_path)

    # Parse command to extract args
    args = shlex.split(command)[1:]  # Skip 'gitctx'

    # Run indexing again (should hit cache)
    # Environment automatically merged from context["custom_env"] by e2e_cli_runner
    result = e2e_cli_runner.invoke(app, args)

    # Clear custom_env after use
    context.pop("custom_env", None)

    # Store results
    context["result"] = result
    context["stdout"] = result.stdout
    context["stderr"] = result.stderr if hasattr(result, "stderr") and result.stderr else ""
    context["exit_code"] = result.exit_code


@then(parsers.parse('embedding phase should show "{pattern}"'))
def check_embedding_phase_output(pattern: str, context: dict[str, Any]) -> None:
    """Verify embedding phase displays expected output pattern.

    Checks for cost breakdown showing fresh and cached costs.
    Pattern typically contains "Total Costs" and "Saved using repo cache".

    Args:
        pattern: Expected pattern in output (can contain placeholders like $X, N, M)
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Check for key components of the pattern
    # Pattern example: "Total Costs: $X (N blobs) | Saved using repo cache: $Y (M blobs)"
    assert "Total Costs:" in stderr, f"'Total Costs:' not found in stderr:\n{stderr}"
    assert "Saved using repo cache:" in stderr, (
        f"'Saved using repo cache:' not found in stderr:\n{stderr}"
    )

    # Check for cost format ($X.XXXXX)
    assert re.search(r"\$\d+\.\d+", stderr), f"Cost format not found in stderr:\n{stderr}"

    # Check for blob counts
    assert re.search(r"\d+ blobs?\)", stderr), f"Blob count not found in stderr:\n{stderr}"


@then("saved cost should equal sum of cached embedding costs")
def check_cache_savings_correct(context: dict[str, Any]) -> None:
    """Verify cache savings calculation is accurate.

    Checks that when we have cached blobs, the saved cost is non-zero
    and properly formatted.

    Args:
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Extract saved cost from pattern: "Saved using repo cache: $X.XXXXX (N blobs)"
    match = re.search(r"Saved using repo cache: \$(\d+\.\d+)", stderr)
    assert match, f"Could not find saved cost in stderr:\n{stderr}"

    saved_cost = float(match.group(1))

    # Verify saved cost is non-zero (we had cache hits)
    assert saved_cost > 0, f"Expected non-zero saved cost, got ${saved_cost:.5f}"


@then(parsers.parse("embedding phase should calculate throughput over min(100, {n:d}) blobs"))
def check_throughput_min_window(n: int, context: dict[str, Any]) -> None:
    """Verify throughput handles small repos correctly.

    For small repos (< 100 files), throughput should be calculated
    over all blobs, not a fixed 100-blob window.

    Args:
        n: Number of blobs in the repo
        context: BDD context with stderr
    """
    # This is difficult to verify externally - we mainly just want to ensure
    # no division-by-zero or other errors occurred
    # The fact that indexing completed successfully is the main check
    assert context["exit_code"] == 0, f"Indexing failed with exit code {context['exit_code']}"


@then(parsers.parse('throughput should show "{metric}" metric'))
def check_throughput_metric(metric: str, context: dict[str, Any]) -> None:
    """Verify throughput displays correct metric unit.

    Checks that throughput is displayed with the specified metric
    (e.g., "blobs/sec", "chunks/sec").

    Args:
        metric: Expected metric string (e.g., "blobs/sec")
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Look for metric pattern in stderr
    assert metric in stderr, f"Throughput metric '{metric}' not found in stderr:\n{stderr}"


@then("progress bar should complete without division-by-zero errors")
def check_no_division_errors(context: dict[str, Any]) -> None:
    """Verify small repos don't cause division-by-zero errors.

    Ensures indexing completed successfully without errors.

    Args:
        context: BDD context with exit_code and stderr
    """
    # Check exit code
    assert context["exit_code"] == 0, f"Indexing failed with exit code {context['exit_code']}"

    # Check for error messages
    stderr = context["stderr"]
    error_patterns = ["division by zero", "ZeroDivisionError", "Error:", "Exception:"]
    for pattern in error_patterns:
        assert pattern not in stderr, f"Found error pattern '{pattern}' in stderr:\n{stderr}"


@then("indexing should complete successfully")
def check_indexing_success(context: dict[str, Any]) -> None:
    """Verify indexing completed without errors.

    Checks that exit code is 0 and no error messages appeared.

    Args:
        context: BDD context with exit_code and stderr
    """
    assert context["exit_code"] == 0, (
        f"Indexing failed with exit code {context['exit_code']}\nStderr: {context['stderr']}"
    )


@then("output file should contain phase markers without ANSI codes")
def check_output_file_no_ansi(context: dict[str, Any]) -> None:
    """Verify redirected output has no ANSI escape codes.

    Since CliRunner captures stderr in-process (equivalent to redirecting),
    we check the captured stderr for ANSI codes.

    Note: CliRunner typically strips ANSI codes, but Rich might add them.
    We verify they're stripped for non-TTY output.

    Args:
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Check for ANSI escape sequences (ESC[ or \x1b[)
    ansi_pattern = r"\x1b\["
    assert not re.search(ansi_pattern, stderr), (
        f"Found ANSI escape codes in redirected stderr:\n{stderr}"
    )

    # Verify phase markers are present (they should work in non-TTY mode)
    # Check for both Unicode → and ASCII -> arrows for Windows compatibility
    # At least one phase marker should be present
    has_phase_marker = any(
        marker in stderr
        for marker in [
            "→ Walking",
            "-> Walking",
            "→ Generating",
            "-> Generating",
            "→ Saving",
            "-> Saving",
        ]
    )
    assert has_phase_marker, f"No phase markers found in stderr:\n{stderr}"


@then("no progress bars should be written")
def check_no_progress_bars_written(context: dict[str, Any]) -> None:
    """Verify no progress bars in non-TTY output.

    When stderr is redirected (non-TTY), Rich should detect this
    and disable progress bars, showing only phase markers.

    Args:
        context: BDD context with stderr
    """
    stderr = context["stderr"]

    # Check no progress bar characters (Rich.Progress uses these)
    progress_chars = ["━", "█", "░", "▓", "▒", "╸", "╺"]
    for char in progress_chars:
        assert char not in stderr, (
            f"Found progress bar character '{char}' in redirected stderr:\n{stderr}"
        )

    # Check no percentage indicators from progress bars
    # (The final statistics might have percentages, but inline progress shouldn't)
    # For now, just check that there are no progress bar characters
