"""Unit test fixtures and helpers.

This file contains fixtures specific to unit tests that don't require
subprocess isolation. For E2E fixtures, see tests/e2e/conftest.py.
"""

from pathlib import Path

import pytest


@pytest.fixture
def isolated_env(temp_home: Path, monkeypatch):
    """
    Complete environment isolation for unit tests.

    Provides isolated HOME directory and clears sensitive environment variables
    that could interfere with config tests.

    This consolidates the common pattern of:
        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    Usage:
        def test_something(isolated_env):
            # temp_home is already set as HOME
            # OPENAI_API_KEY is already cleared
            config = UserConfig()  # Will use isolated HOME
            ...

    Returns:
        Path: The isolated home directory (temp_home)

    See also:
    - temp_home: Creates isolated ~/.gitctx directory
    - isolated_cli_runner: Full CLI isolation with working directory
    """
    monkeypatch.setenv("HOME", str(temp_home))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return temp_home


# === Fixture Factories ===


@pytest.fixture
def git_repo_factory(git_isolation_base, tmp_path):
    """
    Factory for creating git repositories for unit tests.

    This is a unit-test version of e2e_git_repo_factory that creates
    repos using subprocess git commands (for simplicity and reliability).

    Returns:
        callable: Factory function(num_commits, files) -> Path

    Usage:
        def test_something(git_repo_factory):
            repo = git_repo_factory(num_commits=5)
            # Test with 5 commits...
    """
    import subprocess

    def _make_repo(num_commits: int = 1, files: dict[str, str] | None = None) -> Path:
        """Create git repo with N commits."""
        repo_path = tmp_path / f"test_repo_{id(files)}"
        repo_path.mkdir(exist_ok=True)

        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            env=git_isolation_base,
            check=True,
            capture_output=True,
        )

        # Configure git
        for cmd in [
            ["git", "config", "user.name", "Test User"],
            ["git", "config", "user.email", "test@example.com"],
            ["git", "config", "commit.gpgsign", "false"],
        ]:
            subprocess.run(cmd, cwd=repo_path, env=git_isolation_base, check=True)

        # Create files
        if files:
            for filename, content in files.items():
                file_path = repo_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
        else:
            (repo_path / "main.py").write_text('print("Hello")')

        # Create commits
        for i in range(num_commits):
            if i > 0:
                # Modify file for subsequent commits
                (repo_path / "main.py").write_text(f'print("Commit {i + 1}")')

            subprocess.run(
                ["git", "add", "."],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i + 1}"],
                cwd=repo_path,
                env=git_isolation_base,
                check=True,
            )

        return repo_path

    return _make_repo


@pytest.fixture
def partial_clone_repo(tmp_path, git_isolation_base):
    """
    Create repository with partial clone marker.

    Partial clones have .git/objects/info/alternates file, which indicates
    the repo is missing some objects and relies on a remote.
    """
    import subprocess

    repo_path = tmp_path / "partial_repo"
    repo_path.mkdir()

    # Initialize git
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create alternates file (marker for partial clone)
    alternates_file = repo_path / ".git" / "objects" / "info" / "alternates"
    alternates_file.parent.mkdir(parents=True, exist_ok=True)
    alternates_file.write_text("/fake/remote/objects\n")

    return repo_path


@pytest.fixture
def shallow_clone_repo(tmp_path, git_isolation_base):
    """
    Create repository with shallow clone marker.

    Shallow clones have .git/shallow file containing SHAs of shallow commits.
    """
    import subprocess

    repo_path = tmp_path / "shallow_repo"
    repo_path.mkdir()

    # Initialize git
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Configure git
    for cmd in [
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, cwd=repo_path, env=git_isolation_base, check=True)

    # Create a commit (needed for valid repo)
    (repo_path / "README.md").write_text("Shallow repo")
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
        text=True,
    )

    # Get the actual commit SHA to use in shallow file
    commit_sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = commit_sha_result.stdout.strip()

    # Create shallow file (marker for shallow clone) with actual commit SHA
    shallow_file = repo_path / ".git" / "shallow"
    shallow_file.write_text(f"{commit_sha}\n")

    return repo_path


@pytest.fixture
def bare_repo(tmp_path, git_isolation_base):
    """Create bare git repository (no working tree) with commits."""
    import subprocess

    # First create a regular repo with commits
    source_repo = tmp_path / "source_repo"
    source_repo.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=source_repo,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Configure git
    for cmd in [
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, cwd=source_repo, env=git_isolation_base, check=True)

    # Create 3 commits
    for i in range(3):
        (source_repo / "file.txt").write_text(f"Content {i + 1}")
        subprocess.run(
            ["git", "add", "."],
            cwd=source_repo,
            env=git_isolation_base,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i + 1}"],
            cwd=source_repo,
            env=git_isolation_base,
            check=True,
        )

    # Create bare repo and push to it
    bare_repo_path = tmp_path / "bare_repo.git"
    subprocess.run(
        ["git", "init", "--bare", str(bare_repo_path)],
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Get current branch name (supports both "main" and "master" default branches)
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=source_repo,
        env=git_isolation_base,
        capture_output=True,
        text=True,
        check=True,
    )
    branch_name = branch_result.stdout.strip()

    # Push commits to bare repo using actual branch name
    subprocess.run(
        ["git", "push", str(bare_repo_path), branch_name],
        cwd=source_repo,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    return bare_repo_path


@pytest.fixture
def config_factory():
    """
    Factory for creating test config file content.

    Returns a function that generates YAML config strings with customizable
    settings. Useful for creating consistent test configs without repetition.

    Returns:
        callable: Factory function(**kwargs) -> str (YAML content)

    Usage:
        def test_custom_limit(config_factory, isolated_env):
            config_yaml = config_factory(search_limit=20, embedding_model="text-embedding-3-small")
            config_file = isolated_env / ".gitctx" / "config.yml"
            config_file.write_text(config_yaml)
            # Test with custom config...

    Available parameters (all optional):
    - search_limit: int = 10
    - embedding_model: str = "text-embedding-3-large"
    - chunk_size: int = 512
    - chunk_overlap: int = 50
    - openai_api_key: str | None = None

    See also:
    - isolated_env: For placing config files in isolated HOME
    - temp_home: Direct access to temp home directory
    """

    def _make_config(
        search_limit: int = 10,
        embedding_model: str = "text-embedding-3-large",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        openai_api_key: str | None = None,
    ) -> str:
        """Generate YAML config content with specified settings."""
        config_dict = {
            "search": {"limit": search_limit},
            "model": {
                "embedding": embedding_model,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        }

        # Add API key section if provided
        if openai_api_key:
            config_dict["api_keys"] = {"openai": openai_api_key}

        # Convert to YAML manually (avoid PyYAML dependency in test utils)
        lines = []
        for section, values in config_dict.items():
            lines.append(f"{section}:")
            if isinstance(values, dict):
                for key, val in values.items():
                    lines.append(f"  {key}: {val}")
            else:
                lines.append(f"  {values}")

        return "\n".join(lines) + "\n"

    return _make_config


@pytest.fixture
def symlink_repo(tmp_path, git_isolation_base):
    """
    Create repository with symlinks (Unix/Linux/macOS only).

    This fixture creates a repo with both regular files and symlinks to test
    symlink handling. Symlinks are only reliably supported on Unix-like systems.

    Returns:
        Path: Repository path with symlinks

    Usage:
        @pytest.mark.skipif(is_windows(), reason="symlinks not reliable on Windows")
        def test_symlinks(symlink_repo):
            # Test symlink behavior...

    Note: Import is_windows from tests.conftest for platform detection.
    """
    import subprocess

    from tests.conftest import is_windows

    # Skip fixture creation on Windows
    if is_windows():
        pytest.skip("Symlinks not reliably supported on Windows")

    repo_path = tmp_path / "symlink_repo"
    repo_path.mkdir()

    # Initialize git
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Configure git
    for cmd in [
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "commit.gpgsign", "false"],
        ["git", "config", "core.symlinks", "true"],
    ]:
        subprocess.run(cmd, cwd=repo_path, env=git_isolation_base, check=True)

    # Create regular files
    (repo_path / "real_file.py").write_text("def real(): pass")
    (repo_path / "target.txt").write_text("Target content")

    # Create symlinks (Unix only)
    import os

    os.symlink("real_file.py", repo_path / "symlink_to_file.py")
    os.symlink("target.txt", repo_path / "symlink_to_target")

    # Commit everything
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add files and symlinks"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    return repo_path
