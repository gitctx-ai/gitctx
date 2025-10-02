"""
=== E2E FIXTURE ARCHITECTURE ===

CRITICAL: E2E tests spawn subprocesses. Monkeypatch DOES NOT WORK.
Must use actual environment dictionaries for isolation.

Current Fixtures: 4 fixtures for CLI/subprocess testing
Future Expansion: See roadmap in comments below

Author: gitctx team
"""

import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

# === PHASE 1: Core E2E Fixtures (Current) ===


@pytest.fixture
def e2e_git_isolation_env(git_isolation_base: dict[str, str], temp_home: Path) -> dict[str, str]:
    """
    Complete environment dict for subprocess/CLI testing.

    SECURITY: This environment prevents:
    - Access to real SSH keys
    - GPG signing operations
    - Git credential access
    - Push to remote repos

    Args:
        git_isolation_base: Security isolation vars
        temp_home: Isolated HOME directory

    Returns:
        dict: Complete isolated environment for subprocess.run()

    Example:
        def test_git_operations(e2e_git_isolation_env):
            result = subprocess.run(
                ["git", "init"],
                env=e2e_git_isolation_env,
                capture_output=True
            )
    """
    # Start with minimal safe environment
    isolated_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(temp_home),
        "USER": "testuser",
        "TERM": "dumb",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }

    # Add git isolation
    isolated_env.update(git_isolation_base)

    # Create minimal .gitconfig in isolated home
    gitconfig = temp_home / ".gitconfig"
    gitconfig.write_text("""[user]
    name = Test User
    email = test@example.com
[commit]
    gpgsign = false
[core]
    sshCommand = /bin/false
""")

    return isolated_env


@pytest.fixture
def e2e_cli_runner(e2e_git_isolation_env: dict[str, str]) -> CliRunner:
    """
    CLI runner with isolated environment.

    Uses CliRunner with complete environment isolation for testing
    gitctx CLI commands safely.

    Returns:
        CliRunner: Runner configured with isolated environment

    Example:
        def test_cli_command(e2e_cli_runner):
            result = e2e_cli_runner.invoke(app, ["--version"])
            assert result.exit_code == 0
    """
    return CliRunner(env=e2e_git_isolation_env)


@pytest.fixture
def e2e_git_repo(e2e_git_isolation_env: dict[str, str], tmp_path: Path) -> Path:
    """
    Create basic git repository with isolation.

    Creates a git repo with one Python file, proper .gitignore,
    and complete isolation from system git configuration.

    Returns:
        Path: Repository root directory

    Example:
        def test_with_repo(e2e_git_repo, e2e_cli_runner):
            os.chdir(e2e_git_repo)
            result = e2e_cli_runner.invoke(app, ["index"])
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git with isolation
    result = subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"git init failed: {result.stderr}")

    # Configure git locally (not globally)
    for cmd in [
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, cwd=repo_path, env=e2e_git_isolation_env, check=True)

    # Add basic files
    (repo_path / "main.py").write_text('print("Hello from gitctx test")')
    (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/\n.gitctx/\n")

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=repo_path, env=e2e_git_isolation_env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        env=e2e_git_isolation_env,
        check=True,
    )

    return repo_path


@pytest.fixture
def e2e_env_factory(e2e_git_isolation_env: dict[str, str]):
    """
    Factory for creating custom environments with isolation.

    SECURITY: Prevents overriding critical security variables.

    Returns:
        callable: Factory function that creates custom env dicts

    Example:
        def test_with_api_key(e2e_env_factory):
            env = e2e_env_factory(OPENAI_API_KEY="sk-test123")
            result = subprocess.run(["gitctx", "search"], env=env)
    """

    def _make_env(**kwargs: str) -> dict[str, str]:
        env = e2e_git_isolation_env.copy()

        # Security check - don't allow overriding critical vars
        forbidden = {"GIT_SSH_COMMAND", "SSH_AUTH_SOCK", "GNUPGHOME", "GPG_TTY"}
        if forbidden & set(kwargs.keys()):
            raise ValueError(
                f"Cannot override security-critical vars: {forbidden & set(kwargs.keys())}"
            )

        env.update(kwargs)
        return env

    return _make_env


# === PHASE 2: Repository Variants (TODO - Next Sprint) ===
# TODO: e2e_empty_git_repo - Just git init, no files
# TODO: e2e_git_repo_with_history - Multiple commits for history testing
# TODO: e2e_git_repo_with_branches - Multiple branches for branch testing
# TODO: e2e_large_git_repo - 1000+ files for performance testing

# === PHASE 3: Advanced Fixtures (TODO - Future) ===
# TODO: e2e_indexed_repo - Repository with completed indexing
# TODO: e2e_git_repo_factory - Parameterized repo builder
# TODO: mock_openai_api - Subprocess-safe OpenAI mock

# === COMPOSITION PATTERNS ===
#
# PATTERN 1: Extending existing fixtures
# @pytest.fixture
# def e2e_repo_with_config(e2e_git_repo):
#     """Add .gitctx config to repo."""
#     config_path = e2e_git_repo / ".gitctx" / "config.yml"
#     config_path.parent.mkdir(exist_ok=True)
#     config_path.write_text("model: gpt-4")
#     return e2e_git_repo
#
# PATTERN 2: Parameterized fixtures
# @pytest.fixture
# def e2e_repo_with_files(request, e2e_git_repo, e2e_git_isolation_env):
#     """Create repo with custom files via params."""
#     for filename, content in request.param.items():
#         (e2e_git_repo / filename).write_text(content)
#     subprocess.run(
#         ["git", "add", "-A"],
#         cwd=e2e_git_repo,
#         env=e2e_git_isolation_env,
#         check=True
#     )
#     return e2e_git_repo

# === SECURITY VERIFICATION ===
#
# To verify isolation is working, these commands should FAIL in tests:
# - subprocess.run(["git", "push"], env=e2e_git_isolation_env)  # No SSH
# - subprocess.run(["ssh", "-T", "git@github.com"], env=e2e_git_isolation_env)  # No SSH
# - subprocess.run(["gpg", "--list-secret-keys"], env=e2e_git_isolation_env)  # No GPG
