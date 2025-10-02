"""
Test E2E fixtures defined in tests/e2e/conftest.py.

CRITICAL: These tests verify security isolation is working.
When adding new E2E fixtures, add tests here.
"""

import os
import subprocess
from pathlib import Path

import pytest


def test_e2e_git_isolation_env_security(e2e_git_isolation_env: dict[str, str]) -> None:
    """Verify environment has all security isolation vars."""
    # Check SSH is disabled
    assert e2e_git_isolation_env["GIT_SSH_COMMAND"] == "/bin/false"
    assert e2e_git_isolation_env["SSH_AUTH_SOCK"] == ""

    # Check GPG is disabled
    assert e2e_git_isolation_env["GNUPGHOME"] == "/dev/null"
    assert e2e_git_isolation_env["GPG_TTY"] == ""

    # Check git config is isolated
    assert e2e_git_isolation_env["GIT_CONFIG_GLOBAL"] != os.path.expanduser("~/.gitconfig")
    assert e2e_git_isolation_env["GIT_CONFIG_SYSTEM"] == "/dev/null"

    # Check HOME is isolated
    assert e2e_git_isolation_env["HOME"] != os.path.expanduser("~")
    home = e2e_git_isolation_env["HOME"]
    assert "tmp" in home.lower() or "temp" in home.lower()


def test_e2e_git_isolation_prevents_ssh(e2e_git_isolation_env: dict[str, str]) -> None:
    """Verify SSH operations fail with isolation."""
    result = subprocess.run(
        ["ssh", "-T", "git@github.com"],
        env=e2e_git_isolation_env,
        capture_output=True,
        timeout=2,
    )
    assert result.returncode != 0


def test_e2e_cli_runner_has_isolation(e2e_cli_runner) -> None:
    """Verify CLI runner uses isolated environment."""
    # The env should be set on the runner
    assert e2e_cli_runner.env is not None
    assert e2e_cli_runner.env["GIT_SSH_COMMAND"] == "/bin/false"


def test_e2e_git_repo_structure(e2e_git_repo: Path) -> None:
    """Verify git repo has expected structure."""
    assert e2e_git_repo.exists()
    assert (e2e_git_repo / ".git").exists()
    assert (e2e_git_repo / "main.py").exists()
    assert (e2e_git_repo / ".gitignore").exists()

    # Verify git config is local only
    config_file = e2e_git_repo / ".git" / "config"
    config_text = config_file.read_text()
    assert "user" in config_text
    assert "test@example.com" in config_text


def test_e2e_git_repo_cannot_push(
    e2e_git_repo: Path, e2e_git_isolation_env: dict[str, str]
) -> None:
    """SECURITY: Verify repo cannot push to remote."""
    # Try to add a remote and push
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:test/test.git"],
        cwd=e2e_git_repo,
        env=e2e_git_isolation_env,
    )

    result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=e2e_git_repo,
        env=e2e_git_isolation_env,
        capture_output=True,
        timeout=2,
    )
    assert result.returncode != 0


def test_e2e_env_factory_blocks_security_overrides(e2e_env_factory) -> None:
    """Verify factory prevents overriding security vars."""
    # Should work for normal vars
    env = e2e_env_factory(CUSTOM_VAR="test")
    assert env["CUSTOM_VAR"] == "test"

    # Should fail for security vars
    with pytest.raises(ValueError, match="security-critical"):
        e2e_env_factory(GIT_SSH_COMMAND="ssh")

    with pytest.raises(ValueError, match="security-critical"):
        e2e_env_factory(SSH_AUTH_SOCK="/tmp/ssh-agent")


# TODO: When adding new e2e_* fixtures, add tests here:
# def test_e2e_empty_git_repo(e2e_empty_git_repo):
#     """Verify empty repo has only .git directory."""
#     assert (e2e_empty_git_repo / ".git").exists()
#     # Should have no other files
#     files = list(e2e_empty_git_repo.iterdir())
#     assert len(files) == 1  # Only .git
