"""Unit test fixtures and helpers.

This file contains fixtures specific to unit tests that don't require
subprocess isolation. For E2E fixtures, see tests/e2e/conftest.py.
"""
# ruff: noqa: PLC0415 # Inline imports in fixtures for test isolation

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def anyio_backend():
    """Configure pytest-anyio to use only asyncio backend (no trio)."""
    return "asyncio"


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


def _get_main_branch_name(repo_path, git_isolation_base) -> str:
    """Determine default branch name (main, master, trunk, etc.).

    Uses git branch --list to find which default branch exists in the repo.
    More robust than substring matching - checks for actual branch existence.

    Returns:
        str: Name of the default branch (main, master, trunk, develop, etc.)
    """

    result = subprocess.run(
        ["git", "branch", "--list"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
        text=True,
    )
    branches = result.stdout.strip()

    # Check for common default branch names in order of modern preference
    for branch_name in ["main", "master", "trunk", "develop"]:
        # Match whole words with leading * or whitespace to avoid substring matches
        if f"* {branch_name}" in branches or f"  {branch_name}" in branches:
            return branch_name

    # Fallback: return the first branch found (removing * and whitespace)
    first_branch = branches.split("\n")[0].strip().lstrip("* ").strip()
    return first_branch if first_branch else "main"


def _create_two_way_merge(repo_path, git_isolation_base, num_commits: int) -> None:
    """Create a two-way merge commit (2 parents).

    Args:
        repo_path: Path to git repository
        git_isolation_base: Git isolation environment
        num_commits: Total number of commits (for commit message)
    """

    # Create feature branch from current HEAD
    subprocess.run(
        ["git", "branch", "feature"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    # Switch to feature branch
    subprocess.run(
        ["git", "checkout", "feature"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create commit on feature branch
    (repo_path / "feature.py").write_text("def feature(): pass")
    subprocess.run(
        ["git", "add", "feature.py"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Feature commit"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    # Switch back to main/master
    main_branch = _get_main_branch_name(repo_path, git_isolation_base)
    subprocess.run(
        ["git", "checkout", main_branch],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create merge commit with 2 parents (--no-ff forces merge commit)
    subprocess.run(
        [
            "git",
            "merge",
            "feature",
            "--no-ff",
            "-m",
            f"Merge commit (Commit {num_commits})",
        ],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )


def _create_octopus_merge(repo_path, git_isolation_base, num_commits: int) -> None:
    """Create an octopus merge commit (3+ parents).

    Args:
        repo_path: Path to git repository
        git_isolation_base: Git isolation environment
        num_commits: Total number of commits (for commit message)
    """

    # Create feature1 branch
    subprocess.run(
        ["git", "branch", "feature1"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "feature1"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )
    (repo_path / "feature1.py").write_text("def feature1(): pass")
    subprocess.run(
        ["git", "add", "feature1.py"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Feature1 commit"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    # Switch back to main
    main_branch = _get_main_branch_name(repo_path, git_isolation_base)
    subprocess.run(
        ["git", "checkout", main_branch],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create feature2 branch
    subprocess.run(
        ["git", "branch", "feature2"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "feature2"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )
    (repo_path / "feature2.py").write_text("def feature2(): pass")
    subprocess.run(
        ["git", "add", "feature2.py"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Feature2 commit"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    # Switch back to main
    subprocess.run(
        ["git", "checkout", main_branch],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create octopus merge (3 parents: main + feature1 + feature2)
    # Git supports merging multiple branches at once
    subprocess.run(
        [
            "git",
            "merge",
            "feature1",
            "feature2",
            "--no-ff",
            "-m",
            f"Octopus merge commit (Commit {num_commits})",
        ],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )


def _create_fast_forward_merge(repo_path, git_isolation_base) -> None:
    """Create a fast-forward merge (linear history, no merge commit).

    Args:
        repo_path: Path to git repository
        git_isolation_base: Git isolation environment
    """

    # Create feature branch
    subprocess.run(
        ["git", "branch", "feature"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "feature"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Create commit on feature branch
    (repo_path / "feature.py").write_text("def feature(): pass")
    subprocess.run(
        ["git", "add", "feature.py"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Feature commit"],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
    )

    # Switch back to main and fast-forward merge (default behavior when possible)
    main_branch = _get_main_branch_name(repo_path, git_isolation_base)
    subprocess.run(
        ["git", "checkout", main_branch],
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feature", "--ff-only"],  # Force fast-forward only
        cwd=repo_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )


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

    def _make_repo(
        num_commits: int = 1,
        files: dict[str, str] | None = None,
        create_merge: bool = False,  # DEPRECATED: Use merge_type instead
        merge_type: str | None = None,
    ) -> Path:
        """Create git repo with N commits.

        Args:
            num_commits: Number of commits to create
            files: Optional dict of filename -> content
            create_merge: DEPRECATED - Use merge_type="two-way" instead
            merge_type: Type of merge commit to create:
                       - None: No merge (default)
                       - "two-way": 2-parent merge (requires num_commits >= 3)
                       - "octopus": 3-parent merge (requires num_commits >= 5)
                       - "fast-forward": Linear history, no merge commit

        Raises:
            ValueError: If merge_type requires more commits than num_commits
        """
        # Handle backward compatibility: create_merge=True -> merge_type="two-way"
        if create_merge and merge_type is None:
            merge_type = "two-way"
        elif create_merge and merge_type is not None:
            raise ValueError("Cannot specify both create_merge and merge_type")

        # Validate merge_type requirements
        if merge_type == "two-way" and num_commits < 3:
            raise ValueError("merge_type='two-way' requires num_commits >= 3")
        elif merge_type == "octopus" and num_commits < 5:
            raise ValueError(
                "merge_type='octopus' requires num_commits >= 5 (2 initial, 2 branches, 1 merge)"
            )

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
                file_path.write_text(content, encoding="utf-8")
        else:
            (repo_path / "main.py").write_text('print("Hello")', encoding="utf-8")

        # Determine how many regular commits to create
        if merge_type == "two-way":
            # Reserve last commit for merge
            regular_commits = num_commits - 1  # -1 for merge commit
        elif merge_type == "octopus":
            # Reserve last commit for octopus merge
            regular_commits = num_commits - 1  # -1 for merge commit
        elif merge_type == "fast-forward":
            # Fast-forward doesn't create merge commit, all commits are regular
            regular_commits = num_commits
        else:
            # No merge
            regular_commits = num_commits

        # Create regular commits
        for i in range(regular_commits):
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

        # Create merge commit if requested
        if merge_type == "two-way":
            _create_two_way_merge(repo_path, git_isolation_base, num_commits)
        elif merge_type == "octopus":
            _create_octopus_merge(repo_path, git_isolation_base, num_commits)
        elif merge_type == "fast-forward":
            _create_fast_forward_merge(repo_path, git_isolation_base)

        return repo_path

    return _make_repo


@pytest.fixture
def partial_clone_repo(tmp_path, git_isolation_base):
    """
    Create repository with partial clone marker.

    Partial clones have .git/objects/info/alternates file, which indicates
    the repo is missing some objects and relies on a remote.
    """

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


@pytest.fixture
def submodule_repo(tmp_path, git_isolation_base):
    """
    Create repository with a git submodule.

    Git submodules appear as 'commit' type entries in the tree (not 'blob' or 'tree').
    This tests that CommitWalker handles non-blob/non-tree entries correctly.

    Note: We manually create the submodule structure using pygit2 to avoid
    git submodule command restrictions in test environments.

    Returns:
        Path: Parent repository path containing a submodule

    Usage:
        def test_submodules(submodule_repo):
            # Test submodule handling...
    """
    import subprocess

    import pygit2

    # Create submodule (child) repository first
    submodule_path = tmp_path / "child_module"
    submodule_path.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=submodule_path,
        env=git_isolation_base,
        check=True,
        capture_output=True,
    )

    # Configure submodule repo
    for cmd in [
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, cwd=submodule_path, env=git_isolation_base, check=True)

    # Create file in submodule and get its commit SHA
    (submodule_path / "submodule_file.txt").write_text("Submodule content")
    subprocess.run(
        ["git", "add", "."],
        cwd=submodule_path,
        env=git_isolation_base,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial submodule commit"],
        cwd=submodule_path,
        env=git_isolation_base,
        check=True,
    )

    # Get the submodule commit SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=submodule_path,
        env=git_isolation_base,
        capture_output=True,
        text=True,
        check=True,
    )
    submodule_commit_sha = result.stdout.strip()

    # Create parent repository using pygit2 to manually add submodule entry
    parent_path = tmp_path / "parent_repo"
    parent_path.mkdir()

    # Initialize parent repo with pygit2
    parent_repo = pygit2.init_repository(str(parent_path))

    # Set up git config
    parent_repo.config["user.name"] = "Test User"
    parent_repo.config["user.email"] = "test@example.com"

    # Create regular file
    (parent_path / "parent_file.txt").write_text("Parent content")

    # Create .gitmodules file
    gitmodules_content = f"""[submodule "child"]
\tpath = child
\turl = {submodule_path}
"""
    (parent_path / ".gitmodules").write_text(gitmodules_content)

    # Build tree manually using TreeBuilder to include gitlink
    tree_builder = parent_repo.TreeBuilder()

    # Add regular file as blob
    parent_file_oid = parent_repo.create_blob("Parent content")
    tree_builder.insert("parent_file.txt", parent_file_oid, pygit2.GIT_FILEMODE_BLOB)

    # Add .gitmodules as blob
    gitmodules_oid = parent_repo.create_blob(gitmodules_content)
    tree_builder.insert(".gitmodules", gitmodules_oid, pygit2.GIT_FILEMODE_BLOB)

    # Add submodule as gitlink (commit type) - mode 0o160000
    # Note: We use the commit SHA from the submodule directly
    tree_builder.insert("child", pygit2.Oid(hex=submodule_commit_sha), 0o160000)

    # Write tree
    tree_id = tree_builder.write()

    # Create commit
    author = pygit2.Signature("Test User", "test@example.com")
    committer = author

    parent_repo.create_commit(
        "refs/heads/main",  # reference
        author,
        committer,
        "Add parent file and submodule",
        tree_id,
        [],  # parents
    )

    # Set HEAD to main
    parent_repo.set_head("refs/heads/main")

    return parent_path


@pytest.fixture
def code_blob_factory():
    """Factory for generating code blobs with specific token counts.

    Returns a function that generates deterministic code with exact token count.
    Uses seeded random for reproducibility.

    Returns:
        callable: Factory function(language, target_tokens, seed) -> str

    Usage:
        def test_large_blob(code_blob_factory):
            blob = code_blob_factory("python", target_tokens=5000)
            # blob has ~5000 tokens
    """
    import random

    import tiktoken

    def _make_blob(language: str, target_tokens: int, seed: int = 42) -> str:
        """Generate code blob with target token count."""
        random.seed(seed)
        encoder = tiktoken.get_encoding("cl100k_base")

        # Generate code until we hit target tokens
        lines = []
        current_tokens = 0

        # Language-specific templates
        if language == "python":
            templates = [
                "def func{i}():\n    return {j}\n",
                "class Class{i}:\n    value = {j}\n",
                "# Comment {i}\nresult = {j}\n",
            ]
        elif language in ("js", "ts"):
            templates = [
                "function func{i}() {{ return {j}; }}\n",
                "const val{i} = {j};\n",
                "// Comment {i}\nlet x = {j};\n",
            ]
        else:
            templates = ["line {i} = {j}\n"]

        i = 0
        while current_tokens < target_tokens:
            template = random.choice(templates)
            line = template.format(i=i, j=random.randint(1, 1000))
            lines.append(line)
            current_tokens = len(encoder.encode("".join(lines)))
            i += 1

        return "".join(lines)

    return _make_blob


@pytest.fixture
def test_embedding_vector():
    """
    Factory for creating deterministic embedding vectors of any dimension.

    Uses np.linspace for predictability and ease of debugging.
    DO NOT use np.random.rand() in tests - it creates non-deterministic data.

    Returns:
        callable: Function(dimension=3072) -> np.ndarray

    Usage:
        def test_cache_hit(test_embedding_vector):
            # Default 3072-dim for text-embedding-3-large
            vector = test_embedding_vector()

            # Custom dimensions for other models
            vector_small = test_embedding_vector(1536)  # text-embedding-3-small
            vector_ada = test_embedding_vector(1536)     # text-embedding-ada-002

            store.cache_query_embedding(key, query, vector, model)

    Note:
        Returns float32 to match LanceDB storage format and avoid precision issues.
    """
    import numpy as np

    def _make_vector(dimension: int = 3072) -> np.ndarray:
        """Generate deterministic vector of specified dimension."""
        return np.linspace(0, 1, dimension, dtype=np.float32)

    return _make_vector


@pytest.fixture
def mock_search_result_factory():
    """Factory for creating mock search results with all required fields.

    Provides sensible defaults for all formatter fields while allowing
    customization for specific test scenarios. Reduces duplication across
    test files and ensures consistency when result schema changes.

    Returns:
        callable: Factory function(**kwargs) -> dict[str, Any]

    Usage:
        def test_formatters(mock_search_result_factory):
            # Default result
            result = mock_search_result_factory()

            # Custom values
            result = mock_search_result_factory(
                file_path="auth.py",
                distance=0.95,
                chunk_content="def authenticate(): pass"
            )

            # List of results
            results = [
                mock_search_result_factory(file_path=f"file{i}.py", distance=i*0.1)
                for i in range(3)
            ]

    Available parameters (all optional):
    - file_path: str = "test.py"
    - start_line: int = 1
    - end_line: int | None = None (omitted if None)
    - distance: float = 0.85
    - commit_sha: str = "abc1234"
    - commit_date: int = 1760501897 (Unix timestamp)
    - author_name: str = "TestAuthor"
    - commit_message: str = "Test commit"
    - is_head: bool = True
    - chunk_content: str = "test content"
    - language: str = "python"
    """
    from typing import Any

    def _make_result(
        file_path: str = "test.py",
        start_line: int = 1,
        end_line: int | None = None,
        distance: float = 0.85,
        commit_sha: str = "abc1234",
        commit_date: int = 1760501897,
        author_name: str = "TestAuthor",
        commit_message: str = "Test commit",
        is_head: bool = True,
        chunk_content: str = "test content",
        language: str = "python",
    ) -> dict[str, Any]:
        """Generate mock search result with specified fields."""
        result: dict[str, Any] = {
            "file_path": file_path,
            "start_line": start_line,
            "_distance": distance,
            "commit_sha": commit_sha,
            "commit_date": commit_date,
            "author_name": author_name,
            "commit_message": commit_message,
            "is_head": is_head,
            "chunk_content": chunk_content,
            "language": language,
        }
        if end_line is not None:
            result["end_line"] = end_line
        return result

    return _make_result
