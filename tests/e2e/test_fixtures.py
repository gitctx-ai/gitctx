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
    from tests.conftest import get_platform_null_device, get_platform_ssh_command

    # Platform-specific expectations
    expected_ssh_cmd = get_platform_ssh_command()
    expected_null_device = get_platform_null_device()

    # Check SSH is disabled (platform-specific command)
    assert e2e_git_isolation_env["GIT_SSH_COMMAND"] == expected_ssh_cmd
    assert e2e_git_isolation_env["SSH_AUTH_SOCK"] == ""

    # Check GPG is isolated (uses temp directory, not user's real GNUPGHOME)
    gnupghome = e2e_git_isolation_env["GNUPGHOME"]
    assert "gnupg_isolated" in gnupghome, "GNUPGHOME should be isolated temp directory"
    assert gnupghome != os.path.expanduser("~/.gnupg"), (
        "GNUPGHOME should not be user's real directory"
    )
    assert e2e_git_isolation_env["GPG_TTY"] == ""

    # Check git config is isolated
    assert e2e_git_isolation_env["GIT_CONFIG_GLOBAL"] != os.path.expanduser("~/.gitconfig")
    assert e2e_git_isolation_env["GIT_CONFIG_SYSTEM"] == expected_null_device

    # Check HOME is isolated (different from user's actual home)
    home = e2e_git_isolation_env["HOME"]
    assert home != os.path.expanduser("~"), "HOME should be isolated from user's home"


def test_e2e_git_isolation_prevents_ssh(e2e_git_isolation_env: dict[str, str]) -> None:
    """
    SECURITY: Verify SSH operations fail with isolation.

    This test ensures that even if a subprocess tries to use SSH,
    it will fail due to GIT_SSH_COMMAND setting.

    On Windows, SSH may not be available or may timeout (expected behavior).
    On Unix, it should fail immediately with our blocked command.
    """
    import platform

    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"],
            env=e2e_git_isolation_env,
            capture_output=True,
            timeout=2,
        )
        # Should fail immediately on Unix with /bin/false
        # On Windows, may not have ssh command - that's okay
        assert result.returncode != 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Windows: SSH may timeout or not be found - both are acceptable
        # This proves SSH is not easily accessible in the isolated environment
        if platform.system() != "Windows":
            raise  # On Unix, timeout is unexpected


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
    GNUPGHOME points to an empty temp directory, so GPG should find no keys.
    """
    result = subprocess.run(
        ["gpg", "--list-secret-keys", "--batch", "--no-tty"],
        env=e2e_git_isolation_env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # GPG should run successfully but find no keys in the empty temp directory
    # If ANY secret keys are found, we have a CRITICAL security violation
    output = result.stdout + result.stderr

    # Acceptable outputs (no keys found):
    # - Empty output
    # - "gpg: no valid OpenPGP data found"
    # - Contains path to isolated gnupg directory
    assert "gnupg_isolated" in e2e_git_isolation_env["GNUPGHOME"]

    # CRITICAL: No secret keys should be listed
    # If we see key IDs or "sec" markers, isolation failed
    assert "sec " not in output.lower(), "SECURITY VIOLATION: Secret keys accessible!"
    assert "ssb " not in output.lower(), "SECURITY VIOLATION: Secret subkeys accessible!"


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
    from tests.conftest import get_platform_ssh_command

    # The env should be set on the runner
    assert e2e_cli_runner.env is not None
    expected_ssh_cmd = get_platform_ssh_command()
    assert e2e_cli_runner.env["GIT_SSH_COMMAND"] == expected_ssh_cmd


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


# === Context Fixture Tests ===


def test_e2e_context_fixture_shared(context):
    """Verify shared context fixture works across steps."""
    assert isinstance(context, dict)
    context["test_key"] = "test_value"
    assert context["test_key"] == "test_value"


def test_e2e_context_fixture_empty_by_default(context):
    """Verify context starts empty for each test."""
    assert context == {} or len(context) == 0


# === Indexed Repo Fixture Tests ===


def test_e2e_indexed_repo_structure(e2e_indexed_repo: Path):
    """Verify indexed repo has expected structure."""
    assert e2e_indexed_repo.exists()
    assert (e2e_indexed_repo / ".git").exists()
    assert (e2e_indexed_repo / "main.py").exists()
    # Verify index created
    index_path = e2e_indexed_repo / ".gitctx" / "db" / "lancedb"
    assert index_path.exists(), f"Index not found at {index_path}"
    # Verify it's a directory with data
    assert index_path.is_dir()
    assert list(index_path.iterdir()), "Index directory is empty"


def test_e2e_indexed_repo_isolation(e2e_indexed_repo: Path, e2e_git_isolation_env: dict[str, str]):
    """SECURITY: Verify indexed repo used isolated environment."""
    import subprocess

    # Try to add remote
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:test/test.git"],
        cwd=e2e_indexed_repo,
        env=e2e_git_isolation_env,
    )

    # Try to push (should fail due to SSH blocking)
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=e2e_indexed_repo,
        env=e2e_git_isolation_env,
        capture_output=True,
        timeout=2,
    )
    assert result.returncode != 0, "Push should fail with isolated environment"


def test_e2e_indexed_repo_uses_same_runner(
    e2e_indexed_repo: Path,
    e2e_cli_runner,
):
    """Verify indexed repo fixture uses same runner instance as test."""
    # If fixture created separate runner, isolation might be broken
    # This test verifies the runner's env is still isolated
    assert e2e_cli_runner.env is not None
    from tests.conftest import get_platform_ssh_command

    expected_ssh = get_platform_ssh_command()
    assert e2e_cli_runner.env["GIT_SSH_COMMAND"] == expected_ssh


def test_e2e_indexed_repo_no_side_effects(e2e_indexed_repo: Path, tmp_path: Path):
    """Verify using fixture doesn't pollute working directory."""
    import os

    cwd = Path(os.getcwd())
    # Should be in tmp_path due to autouse fixture
    assert cwd == tmp_path or tmp_path in cwd.parents


# === Indexed Repo Factory Tests ===


def test_e2e_indexed_repo_factory_custom_files(e2e_indexed_repo_factory, monkeypatch):
    """Verify factory creates repo with custom files."""
    files = {
        "custom1.py": "def foo(): pass",
        "custom2.py": "def bar(): pass",
    }
    repo = e2e_indexed_repo_factory(files=files, monkeypatch=monkeypatch)

    assert (repo / "custom1.py").exists()
    assert (repo / "custom2.py").exists()
    assert (repo / ".gitctx" / "db" / "lancedb").exists()

    # Verify content
    assert "def foo():" in (repo / "custom1.py").read_text()
    assert "def bar():" in (repo / "custom2.py").read_text()


def test_e2e_indexed_repo_factory_multiple_calls(e2e_indexed_repo_factory):
    """Verify factory can be called multiple times independently."""
    repo1 = e2e_indexed_repo_factory(files={"file1.py": "code1"})
    repo2 = e2e_indexed_repo_factory(files={"file2.py": "code2"})

    # Should create separate repos
    assert repo1 != repo2
    assert (repo1 / "file1.py").exists()
    assert not (repo1 / "file2.py").exists()
    assert (repo2 / "file2.py").exists()
    assert not (repo2 / "file1.py").exists()


def test_e2e_indexed_repo_factory_num_commits(e2e_indexed_repo_factory, monkeypatch):
    """Verify factory respects num_commits parameter."""
    import subprocess

    repo = e2e_indexed_repo_factory(num_commits=5, monkeypatch=monkeypatch)

    # Count commits
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    commit_count = int(result.stdout.strip())
    assert commit_count == 5


def test_e2e_indexed_repo_factory_branches(e2e_indexed_repo_factory):
    """Verify factory creates requested branches."""
    import subprocess

    repo = e2e_indexed_repo_factory(branches=["feature1", "feature2"])

    # List branches
    result = subprocess.run(
        ["git", "branch"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    branches = result.stdout
    assert "feature1" in branches
    assert "feature2" in branches


def test_e2e_indexed_repo_factory_no_ssh_keys(
    e2e_indexed_repo_factory, e2e_git_isolation_env: dict[str, str]
):
    """SECURITY: Verify SSH keys not accessible during factory indexing."""
    import subprocess

    repo = e2e_indexed_repo_factory()

    # Try SSH operation in repo's isolated environment
    result = subprocess.run(
        ["ssh", "-T", "git@github.com"],
        cwd=repo,
        env=e2e_git_isolation_env,
        capture_output=True,
        timeout=2,
    )
    assert result.returncode != 0, "SSH should be blocked"


def test_e2e_indexed_repo_factory_no_directory_pollution(e2e_indexed_repo_factory, tmp_path: Path):
    """Verify factory doesn't change caller's working directory."""
    import os

    cwd_before = Path(os.getcwd())
    _ = e2e_indexed_repo_factory()
    cwd_after = Path(os.getcwd())

    # Should be back in tmp_path (autouse fixture location)
    assert cwd_before == cwd_after
    assert cwd_after == tmp_path or tmp_path in cwd_after.parents


# TODO: When adding new e2e_* fixtures, add tests here:
# def test_e2e_empty_git_repo(e2e_empty_git_repo):
#     """Verify empty repo has only .git directory."""
#     assert (e2e_empty_git_repo / ".git").exists()
#     # Should have no other files
#     files = list(e2e_empty_git_repo.iterdir())
#     assert len(files) == 1  # Only .git
