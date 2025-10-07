"""
=== FIXTURE ARCHITECTURE ===

SECURITY: All git operations must use isolation fixtures to prevent
access to developer credentials, SSH keys, and GPG keys.

Current Fixtures: 2 core fixtures
Future Expansion: See roadmap in comments below

Author: gitctx team
"""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# CRITICAL: Disable ANSI colors BEFORE any CLI module imports
# Rich Console checks these environment variables at __init__ time,
# so they must be set before any imports. We set them at module level
# to ensure they're available before pytest starts running tests.
# These are test-only settings and won't affect production code.
os.environ["TTY_COMPATIBLE"] = "0"  # Rich 2025 standard - disables ANSI codes
os.environ["NO_COLOR"] = "1"  # Standard fallback for no color
os.environ["TERM"] = "dumb"  # Simple terminal type

# Import step definitions to register them with pytest-bdd
pytest_plugins = [
    "tests.e2e.steps.cli_steps",
    "tests.e2e.steps.test_chunking",
]


# === UTILITY FUNCTIONS ===


def is_windows() -> bool:
    """Check if running on Windows platform.

    Centralized platform detection to avoid duplication across test files.

    Returns:
        bool: True if running on Windows, False otherwise
    """
    import platform

    return platform.system() == "Windows"


def get_platform_ssh_command() -> str:
    """Get platform-specific SSH blocking command.

    Returns:
        str: "exit 1" on Windows, "/bin/false" on Unix
    """
    return "exit 1" if is_windows() else "/bin/false"


def get_platform_null_device() -> str:
    """Get platform-specific null device path.

    Returns:
        str: "NUL" on Windows, "/dev/null" on Unix
    """
    return "NUL" if is_windows() else "/dev/null"


# === PHASE 1: Core Security Fixtures (Current) ===


@pytest.fixture
def git_isolation_base(tmp_path: Path) -> dict[str, str]:
    """
    Base git isolation configuration.

    SECURITY: This dict contains environment variables that prevent:
    - SSH key access
    - GPG signing
    - Credential helper access
    - Push operations

    All git-related fixtures MUST use this as a base.

    NOTE: Unix-specific paths (/dev/null, /bin/false) are intentional for
    security isolation. Git on Windows typically runs under Unix-like environments
    (WSL, Git Bash, MSYS2). Our CI tests verify this works across all platforms.

    Related fixtures:
    - e2e_git_isolation_env: Extends this with full environment (tests/e2e/conftest.py)
    - e2e_git_repo: Uses this for git operations (tests/e2e/conftest.py)
    - e2e_git_repo_factory: Uses this for creating custom repos (tests/e2e/conftest.py)

    See also: tests/e2e/CLAUDE.md for E2E testing security guidelines
    """
    # For Windows, use a command that fails immediately (exit 1 works cross-platform in Git Bash/MSYS2)
    # For Unix, use /bin/false for explicit blocking
    ssh_block_cmd = "exit 1" if is_windows() else "/bin/false"

    # For Windows, use NUL device; for Unix, use /dev/null
    # This prevents git config from hanging when trying to access these paths
    null_device = "NUL" if is_windows() else "/dev/null"

    # Create an empty GPG home directory to test isolation
    # SECURITY: Using a temp directory instead of NUL/dev/null because:
    # - NUL causes GPG to hang on Windows (timeout masks security violations)
    # - Empty directory allows GPG to run but find no keys (proper test)
    # - If keys ARE found, we have a real security problem
    gpg_home = tmp_path / "gnupg_isolated"
    gpg_home.mkdir(mode=0o700, exist_ok=True)

    return {
        # Disable git configuration access
        "GIT_CONFIG_GLOBAL": null_device,
        "GIT_CONFIG_SYSTEM": null_device,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": ssh_block_cmd,
        # Completely disable SSH
        "GIT_SSH_COMMAND": ssh_block_cmd,
        "SSH_AUTH_SOCK": "",
        "SSH_ASKPASS": ssh_block_cmd,
        # Disable GPG signing - use empty temp directory
        "GPG_TTY": "",
        "GNUPGHOME": str(gpg_home),
    }


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """
    Create isolated HOME directory for tests.

    Creates a temporary home directory with .gitctx subdirectory already
    initialized. Use this when you need direct access to a home directory.

    Returns:
        Path: Temporary home directory with .gitctx subdir

    Related fixtures:
    - isolated_env: Combines temp_home + env var setup (tests/unit/conftest.py)
    - isolated_cli_runner: Uses temp_home for CLI tests (tests/conftest.py)
    - e2e_git_isolation_env: Uses temp_home in environment (tests/e2e/conftest.py)

    Usage:
        def test_config_file(temp_home, monkeypatch):
            monkeypatch.setenv("HOME", str(temp_home))
            config_path = temp_home / ".gitctx" / "config.yml"
            # .gitctx already exists, just write the file
            config_path.write_text("...")

    See also:
    - For most tests, use isolated_env instead (cleaner API)
    """
    home = tmp_path / "test_home"
    home.mkdir()
    (home / ".gitctx").mkdir()
    return home


@pytest.fixture
def unit_cli_runner():
    """
    CLI test runner for pure unit tests (NO filesystem isolation).

    Returns CliRunner for testing Typer CLI commands in-process.

    WARNING: This fixture does NOT isolate the filesystem or environment.
    Only use this for tests that:
    - Test --help output
    - Test error messages
    - Do NOT create files or directories
    - Do NOT invoke git operations

    For most tests, use `cli_runner` (alias for isolated_cli_runner) instead.
    For E2E tests with subprocess isolation, use e2e_cli_runner instead.

    Note: Console colors are disabled globally via TTY_COMPATIBLE=0 set at
    module level (top of this file).
    """
    from typer.testing import CliRunner

    return CliRunner()


@pytest.fixture
def isolated_cli_runner(tmp_path: Path, monkeypatch):
    """
    CLI test runner with complete filesystem and environment isolation.

    Returns CliRunner that runs in a temporary directory with isolated HOME.

    CRITICAL: This is the SAFE DEFAULT for CLI testing. Use this fixture for
    any test that:
    - Creates files or directories (like .gitctx)
    - Invokes git operations
    - Reads/writes config files
    - When in doubt, use this!

    Isolation provided:
    - Working directory: tmp_path
    - HOME directory: tmp_path/home
    - Environment: OPENAI_API_KEY cleared

    For E2E tests with subprocess isolation, use e2e_cli_runner instead.
    """
    from typer.testing import CliRunner

    # Create isolated home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    # Isolate both working directory and HOME
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(fake_home))

    # Clear OPENAI_API_KEY to prevent env var interference
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    return CliRunner()


@pytest.fixture
def cli_runner(isolated_cli_runner):
    """
    Default CLI test runner (SAFE by default).

    This is an alias for isolated_cli_runner, making the safe choice the default.
    Use this fixture for most CLI tests.

    For pure unit tests that don't touch the filesystem, you can explicitly
    use unit_cli_runner instead.
    """
    return isolated_cli_runner


# === PHASE 2: Repository Fixtures (TODO - Next Sprint) ===
# TODO: unit_git_repo - Simple repo for unit tests (monkeypatch)
# TODO: unit_mock_filesystem - Mock file operations

# === PHASE 3: Service Mocks (TODO - Future) ===
# TODO: mock_openai_client - Mock OpenAI API responses
# TODO: mock_embeddings - Pre-generated test embeddings

# === EXPANSION GUIDELINES ===
#
# When adding new fixtures:
# 1. MUST use git_isolation_base for any git operations
# 2. Prefix with unit_ for monkeypatch-based fixtures
# 3. Document security implications
# 4. Add to appropriate phase in roadmap
