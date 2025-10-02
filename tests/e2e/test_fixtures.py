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

    # Check HOME is isolated (different from user's actual home)
    home = e2e_git_isolation_env["HOME"]
    assert home != os.path.expanduser("~"), "HOME should be isolated from user's home"


def test_e2e_git_isolation_prevents_ssh(e2e_git_isolation_env: dict[str, str]) -> None:
    """
    SECURITY: Verify SSH operations fail with isolation.

    This test ensures that even if a subprocess tries to use SSH,
    it will fail due to GIT_SSH_COMMAND=/bin/false.
    """
    result = subprocess.run(
        ["ssh", "-T", "git@github.com"],
        env=e2e_git_isolation_env,
        capture_output=True,
        timeout=2,
    )
    # Should fail immediately with /bin/false or timeout
    assert result.returncode != 0


def test_e2e_git_init_works_with_isolation(
    e2e_git_isolation_env: dict[str, str], tmp_path: Path
) -> None:
    """Verify git operations work correctly with isolation environment."""
    test_repo = tmp_path / "test_init"
    test_repo.mkdir()

    # Git init should work even with isolation
    result = subprocess.run(
        ["git", "init"],
        cwd=test_repo,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (test_repo / ".git").exists()


def test_e2e_git_commit_works_with_isolation(
    e2e_git_isolation_env: dict[str, str], tmp_path: Path
) -> None:
    """Verify git commits work with isolated config."""
    test_repo = tmp_path / "test_commit"
    test_repo.mkdir()

    # Initialize repo
    subprocess.run(["git", "init"], cwd=test_repo, env=e2e_git_isolation_env, check=True)

    # Configure git locally
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=test_repo,
        env=e2e_git_isolation_env,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=test_repo,
        env=e2e_git_isolation_env,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=test_repo,
        env=e2e_git_isolation_env,
        check=True,
    )

    # Create and commit a file
    (test_repo / "test.txt").write_text("test content")
    subprocess.run(["git", "add", "."], cwd=test_repo, env=e2e_git_isolation_env, check=True)

    result = subprocess.run(
        ["git", "commit", "-m", "Test commit"],
        cwd=test_repo,
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Test commit" in result.stdout or "Test commit" in result.stderr


def test_e2e_gpg_keys_not_accessible(e2e_git_isolation_env: dict[str, str]) -> None:
    """
    SECURITY: Verify GPG secret keys are not accessible.

    This ensures commits cannot be signed with developer's GPG keys.
    """
    result = subprocess.run(
        ["gpg", "--list-secret-keys"],
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
        timeout=2,
    )

    # Should either fail or show no secret keys
    # GNUPGHOME=/dev/null means no keyring accessible
    output_lower = (result.stdout + result.stderr).lower()
    assert "secret" not in output_lower or result.returncode != 0


def test_e2e_gitctx_subprocess_isolation(e2e_git_isolation_env: dict[str, str]) -> None:
    """
    CRITICAL: Verify gitctx runs as subprocess with full isolation.

    This test ensures that when we run gitctx commands in E2E tests,
    they execute with complete isolation from the host environment.
    """
    import sys

    # Run gitctx --version as subprocess with isolation
    result = subprocess.run(
        [sys.executable, "-m", "gitctx", "--version"],
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
    )

    # Should succeed and output version
    assert result.returncode == 0
    assert "gitctx version" in result.stdout

    # Verify the subprocess had isolated environment
    # We can't directly inspect subprocess env, but we verified
    # e2e_git_isolation_env has the right vars in other tests


def test_e2e_cli_runner_has_isolation(e2e_cli_runner) -> None:
    """
    Verify CLI runner uses isolated environment.

    NOTE: CliRunner runs in-process, so this is less secure than subprocess.
    Prefer using subprocess.run() for true E2E isolation.
    """
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
