"""Unit tests for user configuration (API keys only)."""

import os


class TestUserConfigLoading:
    """Test user config loading from various sources."""

    def test_user_config_loads_from_yaml(self, isolated_env):
        """Config should load API keys from YAML file.

        NOTE: isolated_env provides temp_home with .gitctx/ subdirectory!
        """
        from gitctx.core.user_config import UserConfig

        # isolated_env already sets HOME and clears OPENAI_API_KEY
        # Write config (isolated_env / ".gitctx" already exists!)
        config_file = isolated_env / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-file123\n")

        # Act
        config = UserConfig()

        # Assert - will FAIL (no implementation)
        assert config.api_keys.openai.get_secret_value() == "sk-file123"

    def test_openai_api_key_env_var_precedence(self, temp_home, monkeypatch):
        """OPENAI_API_KEY should override YAML."""
        from gitctx.core.user_config import UserConfig

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-provider789")

        # Write config with different value
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-file123\n")

        # Act
        config = UserConfig()

        # Assert - OPENAI_API_KEY wins
        assert config.api_keys.openai.get_secret_value() == "sk-provider789"

    def test_yaml_used_when_no_env_vars(self, isolated_env):
        """YAML should be used when no env vars are set."""
        from gitctx.core.user_config import UserConfig

        # isolated_env provides HOME and clears OPENAI_API_KEY
        # Write config
        config_file = isolated_env / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-file123\n")

        # Act
        config = UserConfig()

        # Assert
        assert config.api_keys.openai.get_secret_value() == "sk-file123"

    def test_user_config_handles_missing_file(self, isolated_env):
        """Config should use defaults when YAML file doesn't exist.

        Note: isolated_env fixture is required for test isolation (sets HOME, clears env vars)
        even though it's not directly referenced in the test body.
        """
        from gitctx.core.user_config import UserConfig

        # isolated_env provides HOME and clears OPENAI_API_KEY (used implicitly)
        # Act - no config file exists
        config = UserConfig()

        # Assert - should use None default
        assert config.api_keys.openai is None

    def test_insecure_permissions_shows_warning(self, isolated_env, capsys):
        """Config should warn when file has insecure permissions."""

        from tests.conftest import is_windows

        from gitctx.core.user_config import UserConfig

        if is_windows():
            # Skip on Windows - permissions work differently
            import pytest

            pytest.skip("Permission checks not applicable on Windows")

        # isolated_env provides HOME and clears OPENAI_API_KEY
        # Write config with insecure permissions
        config_file = isolated_env / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-test123\n")
        config_file.chmod(0o644)  # Insecure: readable by group and others

        # Act - loading config should show warning
        UserConfig()

        # Assert - warning displayed on stderr (not stdout)
        captured = capsys.readouterr()
        assert "insecure permissions" in captured.err.lower()
        assert "644" in captured.err
        assert "600" in captured.err

    def test_windows_acl_file_permissions(self, isolated_env):
        """Windows: User config file should be accessible by owner only."""
        import os
        import platform

        import pytest
        from pydantic import SecretStr

        from gitctx.core.user_config import UserConfig

        if platform.system() != "Windows":
            pytest.skip("Windows-only test")

        # Create and save config
        config = UserConfig()
        config.api_keys.openai = SecretStr("sk-test123")
        config.save()

        config_file = isolated_env / ".gitctx" / "config.yml"
        assert config_file.exists()

        # Verify owner can read/write (Windows doesn't use Unix 0600)
        assert os.access(config_file, os.R_OK), "Config file should be readable by owner"
        assert os.access(config_file, os.W_OK), "Config file should be writable by owner"

    def test_windows_userprofile_path_expansion(self):
        """Windows: %USERPROFILE% should expand correctly via Path.home()."""
        import platform
        from pathlib import Path

        import pytest

        if platform.system() != "Windows":
            pytest.skip("Windows-only test")

        # Path.home() should work on Windows
        home = Path.home()
        assert home.exists(), "User home directory should exist"
        assert "Users" in str(home), "Windows home path should contain 'Users'"

        # Config path should use Windows separators (or accept both)
        config_path = home / ".gitctx" / "config.yml"
        path_str = str(config_path)
        assert "\\" in path_str or "/" in path_str, "Path should use valid separators"


class TestUserConfigPersistence:
    """Test saving user configuration."""

    def test_user_config_saves_to_yaml(self, isolated_env):
        """Config.save() should persist to YAML file with 0600 permissions."""
        from pydantic import SecretStr

        from gitctx.core.user_config import UserConfig

        # isolated_env provides HOME and clears OPENAI_API_KEY
        # Create config
        config = UserConfig()
        config.api_keys.openai = SecretStr("sk-test123")

        # Act
        config.save()

        # Assert - file exists
        config_file = isolated_env / ".gitctx" / "config.yml"
        assert config_file.exists()

        # Assert - content is correct
        content = config_file.read_text()
        assert "openai" in content
        assert "sk-test123" in content

        # Assert - file permissions are 0600 (Unix) or just readable/writable (Windows)
        import stat

        from tests.conftest import is_windows

        if is_windows():
            # Windows uses ACLs, not Unix permissions - just verify file is accessible
            assert config_file.exists()
            assert os.access(config_file, os.R_OK | os.W_OK)
        else:
            # Unix: Check exact permissions
            mode = config_file.stat().st_mode
            assert stat.S_IMODE(mode) == 0o600

    def test_user_config_directory_already_exists(self, temp_home, monkeypatch):
        """Config should work when ~/.gitctx/ already exists."""
        from gitctx.core.user_config import UserConfig

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Verify directory exists (created by temp_home fixture)
        assert (temp_home / ".gitctx").exists()
        assert (temp_home / ".gitctx").is_dir()

        # Act - save should work even with existing directory
        config = UserConfig()
        config.save()

        # Assert
        assert (temp_home / ".gitctx" / "config.yml").exists()


class TestSecretStrMasking:
    """Test SecretStr automatically masks API keys."""

    def test_secret_str_masks_api_keys(self):
        """SecretStr should mask API keys in string representation."""
        from gitctx.core.user_config import ApiKeys

        # Act
        api_keys = ApiKeys(openai="sk-test123456")

        # Assert - masked in string repr
        assert "sk-test123456" not in str(api_keys)
        assert "sk-test123456" not in repr(api_keys)

        # Assert - can retrieve with get_secret_value()
        assert api_keys.openai.get_secret_value() == "sk-test123456"


class TestCrossPlatform:
    """Test cross-platform path handling."""

    def test_user_config_windows_path(self, temp_home, monkeypatch):
        """Path.home() should work correctly on all platforms."""
        from gitctx.core.user_config import UserConfig

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Write a config file
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-test\n")

        # Act - config should load from platform-independent path
        config = UserConfig()

        # Assert - config loaded successfully from correct path
        assert config.api_keys.openai is not None
        assert config.api_keys.openai.get_secret_value() == "sk-test"


class TestEdgeCasesUnicode:
    """Test Unicode handling - real scenario: international users."""

    def test_unicode_chinese_in_api_key(self, isolated_env):
        """API key can contain Chinese characters."""
        import platform

        import pytest

        if platform.system() == "Windows":
            pytest.skip("Unicode test skipped on Windows (YAML encoding differences)")

        from gitctx.core.user_config import UserConfig

        config_file = isolated_env / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: 密钥-sk-abc123\n", encoding="utf-8")

        config = UserConfig()
        assert config.api_keys.openai.get_secret_value() == "密钥-sk-abc123"

    def test_unicode_rtl_in_api_key(self, isolated_env):
        """API key can contain RTL (Arabic) text."""
        import platform

        import pytest

        if platform.system() == "Windows":
            pytest.skip("Unicode test skipped on Windows (YAML encoding differences)")

        from gitctx.core.user_config import UserConfig

        config_file = isolated_env / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-العربية123\n", encoding="utf-8")

        config = UserConfig()
        assert config.api_keys.openai.get_secret_value() == "sk-العربية123"


class TestFilesystemEdgeCases:
    """Test filesystem edge cases - real scenario: first-time user."""

    def test_save_creates_missing_parent_directories(self, tmp_path, monkeypatch):
        """save() creates ~/.gitctx/ if missing."""
        from pydantic import SecretStr

        from gitctx.core.user_config import UserConfig

        # Set HOME to a path that doesn't exist yet
        new_home = tmp_path / "nonexistent" / "user" / "home"
        monkeypatch.setenv("HOME", str(new_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Should create all parent directories
        config = UserConfig()
        config.api_keys.openai = SecretStr("sk-test123")
        config.save()

        config_file = new_home / ".gitctx" / "config.yml"
        assert config_file.exists()
        assert "sk-test123" in config_file.read_text()
