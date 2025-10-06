"""
Test fixtures defined in tests/conftest.py (root fixtures).

When adding new fixtures to tests/conftest.py, add corresponding
tests here to verify behavior.
"""


def test_git_isolation_base(git_isolation_base: dict[str, str]) -> None:
    """Verify git isolation base contains security vars."""
    from tests.conftest import get_platform_null_device, get_platform_ssh_command

    expected_ssh_cmd = get_platform_ssh_command()
    expected_null_device = get_platform_null_device()

    assert git_isolation_base["GIT_SSH_COMMAND"] == expected_ssh_cmd
    assert git_isolation_base["SSH_AUTH_SOCK"] == ""

    # GNUPGHOME should be an isolated temp directory, not user's real .gnupg
    gnupghome = git_isolation_base["GNUPGHOME"]
    assert "gnupg_isolated" in gnupghome, "GNUPGHOME should be isolated temp directory"

    assert git_isolation_base["GIT_CONFIG_GLOBAL"] == expected_null_device
    assert git_isolation_base["GIT_CONFIG_SYSTEM"] == expected_null_device
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
