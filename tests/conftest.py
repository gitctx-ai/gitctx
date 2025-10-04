"""
=== FIXTURE ARCHITECTURE ===

SECURITY: All git operations must use isolation fixtures to prevent
access to developer credentials, SSH keys, and GPG keys.

Current Fixtures: 2 core fixtures
Future Expansion: See roadmap in comments below

Author: gitctx team
"""

import os

# CRITICAL: Set environment variables BEFORE any CLI module imports
# This ensures Rich Console objects are created without ANSI escape codes
# Console checks these at __init__ time, so they must be set before import
os.environ["TTY_COMPATIBLE"] = "0"  # Rich 2025 standard - disables ANSI codes
os.environ["NO_COLOR"] = "1"  # Standard fallback for no color
os.environ["TERM"] = "dumb"  # Simple terminal type

import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import step definitions to register them with pytest-bdd
pytest_plugins = ["tests.e2e.steps.cli_steps"]

# === PHASE 1: Core Security Fixtures (Current) ===


@pytest.fixture
def git_isolation_base() -> dict[str, str]:
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
    """
    return {
        # Disable git configuration access
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "/bin/false",
        # Completely disable SSH
        "GIT_SSH_COMMAND": "/bin/false",
        "SSH_AUTH_SOCK": "",
        "SSH_ASKPASS": "/bin/false",
        # Disable GPG signing
        "GPG_TTY": "",
        "GNUPGHOME": "/dev/null",
    }


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """
    Create isolated HOME directory for tests.

    Returns:
        Path: Temporary home directory with .gitctx subdir
    """
    home = tmp_path / "test_home"
    home.mkdir()
    (home / ".gitctx").mkdir()
    return home


@pytest.fixture
def cli_runner():
    """
    CLI test runner for unit tests.

    Returns CliRunner for testing Typer CLI commands in-process.

    Note: Console colors are disabled globally via TTY_COMPATIBLE=0 set at
    module level (top of this file). This must be done before CLI modules
    are imported, as Console checks environment at __init__ time.

    For E2E tests with subprocess isolation, use e2e_cli_runner instead.
    """
    from typer.testing import CliRunner

    return CliRunner()


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
