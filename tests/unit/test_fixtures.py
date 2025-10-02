"""
Test fixtures defined in tests/conftest.py (root fixtures).

When adding new fixtures to tests/conftest.py, add corresponding
tests here to verify behavior.
"""


def test_git_isolation_base(git_isolation_base: dict[str, str]) -> None:
    """Verify git isolation base contains security vars."""
    assert git_isolation_base["GIT_SSH_COMMAND"] == "/bin/false"
    assert git_isolation_base["SSH_AUTH_SOCK"] == ""
    assert git_isolation_base["GNUPGHOME"] == "/dev/null"
    assert git_isolation_base["GIT_TERMINAL_PROMPT"] == "0"


def test_temp_home(temp_home):
    """Verify temp_home creates proper structure."""
    assert temp_home.exists()
    assert temp_home.is_dir()
    assert (temp_home / ".gitctx").exists()
    assert (temp_home / ".gitctx").is_dir()
    # Verify it's actually temporary
    assert "/tmp" in str(temp_home) or "temp" in str(temp_home).lower()


# TODO: When adding unit_* fixtures, add tests here:
# def test_unit_mock_api_key(unit_mock_api_key):
#     """Verify unit mock API key is set correctly."""
#     import os
#     assert os.environ.get("OPENAI_API_KEY") == "sk-test123"
