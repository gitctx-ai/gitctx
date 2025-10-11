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


@pytest.fixture(autouse=True, scope="function")
def auto_isolate_e2e_working_directory(tmp_path: Path, monkeypatch):
    """
    Automatically isolate E2E test working directory.

    CRITICAL: All E2E tests run in tmp_path to prevent:
    - Creating .gitctx directories in actual repo
    - Polluting developer's working directory
    - Test interference

    This is autouse=True, so it applies to ALL tests in tests/e2e/.
    No conditional logic - explicit and obvious behavior.
    """
    monkeypatch.chdir(tmp_path)
    yield tmp_path


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
    # Start with minimal environment for security isolation
    # SECURITY: Prevents exposure of developer credentials (API keys, tokens, etc.)
    # Only include necessary system variables for subprocess execution
    isolated_env = {
        "HOME": str(temp_home),
        "USER": "testuser",
        "TERM": "dumb",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",  # Disable colors for consistent test output
    }

    # Always preserve PATH for subprocesses to find commands
    if "PATH" in os.environ:
        isolated_env["PATH"] = os.environ["PATH"]

    # On Windows, preserve required system variables
    # USERPROFILE: Needed for Path.home() fallback when HOME doesn't work
    # SystemRoot, windir, COMSPEC, PATHEXT: Required to avoid WinError 10106
    # (Winsock initialization failure)
    # See: https://github.com/python/cpython/issues/120836
    if os.name == "nt":
        for var in ["SystemRoot", "windir", "COMSPEC", "PATHEXT", "USERPROFILE"]:
            if var in os.environ:
                isolated_env[var] = os.environ[var]

    # Enable coverage for subprocesses (for E2E tests that spawn gitctx)
    # This ensures subprocess.run() calls still contribute to coverage
    # Add tests/ to PYTHONPATH so sitecustomize.py is found
    tests_dir = Path(__file__).parent.parent
    project_root = tests_dir.parent
    pythonpath = str(tests_dir)
    if "PYTHONPATH" in os.environ:
        pythonpath = f"{os.environ['PYTHONPATH']}:{pythonpath}"
    isolated_env["PYTHONPATH"] = pythonpath

    # Set COVERAGE_PROCESS_START to enable subprocess coverage
    # Point to pyproject.toml in project root
    pyproject_toml = project_root / "pyproject.toml"
    if pyproject_toml.exists():
        isolated_env["COVERAGE_PROCESS_START"] = str(pyproject_toml)

    # Pass through other coverage environment variables
    for cov_var in [
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
    ]:
        if cov_var in os.environ:
            isolated_env[cov_var] = os.environ[cov_var]

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

    # Initialize git with isolation and set default branch to 'main'
    result = subprocess.run(
        ["git", "init", "-b", "main"],
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
        # Prevent re-enabling prompts, SSH, GPG, or git config access
        forbidden = {
            "GIT_SSH_COMMAND",
            "SSH_AUTH_SOCK",
            "SSH_ASKPASS",
            "GNUPGHOME",
            "GPG_TTY",
            "GIT_ASKPASS",
            "GIT_TERMINAL_PROMPT",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_SYSTEM",
        }
        if forbidden & set(kwargs.keys()):
            raise ValueError(
                f"Cannot override security-critical vars: {forbidden & set(kwargs.keys())}"
            )

        env.update(kwargs)
        return env

    return _make_env


# === PHASE 2: Repository Variants & Factories ===


@pytest.fixture
def e2e_git_repo_factory(e2e_git_isolation_env: dict[str, str], tmp_path: Path):
    """
    Factory for creating git repositories with various structures.

    This factory allows tests to create customized git repositories without
    duplicating git setup code. Supports different numbers of files, commits,
    and branches.

    Returns:
        callable: Factory function that creates git repos

    Usage:
        def test_with_custom_repo(e2e_git_repo_factory):
            # Create repo with 5 Python files and 3 commits
            repo = e2e_git_repo_factory(
                files={"file1.py": "code1", "file2.py": "code2"},
                num_commits=3,
                branches=["feature1", "feature2"]
            )
            # Test with repo...

    Parameters for factory function:
    - files: dict[str, str] = {} - Files to create (filename -> content)
    - num_commits: int = 1 - Number of commits to create
    - branches: list[str] = [] - Additional branches to create
    - add_gitignore: bool = True - Whether to add .gitignore

    See also:
    - e2e_git_repo: Pre-configured basic repo (use for simple tests)
    - e2e_git_isolation_env: Environment for git operations
    """

    def _make_repo(
        files: dict[str, str] | None = None,
        num_commits: int = 1,
        branches: list[str] | None = None,
        add_gitignore: bool = True,
    ) -> Path:
        """Create a git repository with specified structure."""
        repo_path = tmp_path / f"test_repo_{id(files)}"  # Unique name per call
        repo_path.mkdir(exist_ok=True)

        # Initialize git with isolation and set default branch to 'main'
        result = subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo_path,
            env=e2e_git_isolation_env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"git init failed: {result.stderr}")

        # Configure git locally
        for cmd in [
            ["git", "config", "user.name", "Test User"],
            ["git", "config", "user.email", "test@example.com"],
            ["git", "config", "commit.gpgsign", "false"],
        ]:
            subprocess.run(cmd, cwd=repo_path, env=e2e_git_isolation_env, check=True)

        # Add .gitignore
        if add_gitignore:
            (repo_path / ".gitignore").write_text("*.pyc\n__pycache__/\n.gitctx/\n")

        # Add custom files or default file
        if files:
            for filename, content in files.items():
                file_path = repo_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
        else:
            (repo_path / "main.py").write_text('print("Hello from gitctx test")')

        # Create commits
        for i in range(num_commits):
            # Modify a file for subsequent commits
            if i > 0:
                (repo_path / "main.py").write_text(f'print("Commit {i + 1}")')

            subprocess.run(
                ["git", "add", "."], cwd=repo_path, env=e2e_git_isolation_env, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i + 1}"],
                cwd=repo_path,
                env=e2e_git_isolation_env,
                check=True,
            )

        # Create branches
        if branches:
            for branch in branches:
                subprocess.run(
                    ["git", "branch", branch],
                    cwd=repo_path,
                    env=e2e_git_isolation_env,
                    check=True,
                )

        return repo_path

    return _make_repo


# === VCR.py Configuration for API Response Recording ===


@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration for E2E tests.

    Records real OpenAI API responses during dev (with real API key).
    Replays cassettes in CI/CD (no API key needed).

    Workflow:
    1. Developer records cassettes once with OPENAI_API_KEY set
    2. Cassettes committed to git (API keys stripped)
    3. CI/CD replays cassettes (fast, deterministic, zero cost)

    Returns:
        dict: VCR configuration parameters
    """
    return {
        "cassette_library_dir": "tests/e2e/cassettes",
        "record_mode": "once",  # Record once, then replay
        "match_on": ["method", "scheme", "host", "port", "path", "query", "body"],
        "filter_headers": [
            "authorization",  # Strip API keys from cassettes
            "x-api-key",
            "api-key",
        ],
        "filter_post_data_parameters": [
            "api_key",
        ],
        "decode_compressed_response": True,
        "allow_playback_repeats": True,  # Allow same request multiple times
    }


@pytest.fixture
def vcr_cassette_name(request):
    """Auto-generate cassette names from test names.

    Cassette filename format: {test_name}.yaml
    Example: test_default_terse_output.yaml

    Args:
        request: pytest request fixture

    Returns:
        str: Cassette filename
    """
    return f"{request.node.name}.yaml"


# Future repository fixtures (can be built using factory above):
# TODO: e2e_empty_git_repo - Just git init, no files (use factory with files={})
# TODO: e2e_git_repo_with_history - Multiple commits (use factory with num_commits=10)
# TODO: e2e_git_repo_with_branches - Multiple branches (use factory with branches=[...])
# TODO: e2e_large_git_repo - 1000+ files for performance (use factory with many files)

# === PHASE 3: Advanced Fixtures (TODO - Future) ===
# TODO: e2e_indexed_repo - Repository with completed indexing
# TODO: e2e_git_repo_factory - Parameterized repo builder

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
