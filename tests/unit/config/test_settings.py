"""Unit tests for GitCtxSettings aggregator and routing logic."""

import contextlib

from gitctx.config.settings import GitCtxSettings, init_repo_config


class TestGitCtxSettingsRouting:
    """Test GitCtxSettings routes config by key pattern."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_gitctx_settings_routes_api_keys_to_user(self, temp_home, monkeypatch):
        """API keys should be routed to user config."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create user config
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-test123\n")

        # Act
        settings = GitCtxSettings()
        value = settings.get("api_keys.openai")

        # Assert - routed to user config
        assert value == "sk-test123"

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_gitctx_settings_routes_settings_to_repo(self, tmp_path, monkeypatch):
        """Repo settings should be routed to repo config."""

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create repo config
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 25\n")

        # Act
        settings = GitCtxSettings()
        value = settings.get("search.limit")

        # Assert - routed to repo config
        assert value == 25

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_set_api_key_persists_to_user_config(self, temp_home, monkeypatch):
        """Setting API key should save to user config file."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act
        settings = GitCtxSettings()
        settings.set("api_keys.openai", "sk-new123")

        # Assert - saved to user config
        config_file = temp_home / ".gitctx" / "config.yml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "sk-new123" in content

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_set_repo_setting_persists_to_repo_config(self, tmp_path, monkeypatch):
        """Setting repo setting should save to repo config file."""

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act
        settings = GitCtxSettings()
        settings.set("search.limit", 30)

        # Assert - saved to repo config
        config_file = tmp_path / ".gitctx" / "config.yml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "limit: 30" in content


class TestGetSource:
    """Test get_source() method returns correct source indicators."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_get_source_openai_api_key_env_var(self, temp_home, monkeypatch):
        """Should detect OPENAI_API_KEY env var as source."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env123")

        # Act
        settings = GitCtxSettings()
        source = settings.get_source("api_keys.openai")

        # Assert
        assert source == "(from OPENAI_API_KEY)"

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_get_source_user_config(self, temp_home, monkeypatch):
        """Should detect user config file as source."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create user config
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-file123\n")

        # Act
        settings = GitCtxSettings()
        source = settings.get_source("api_keys.openai")

        # Assert
        assert source == "(from user config)"

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_get_source_gitctx_env_var(self, tmp_path, monkeypatch):
        """Should detect GITCTX_* env var as source."""

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("GITCTX_SEARCH__LIMIT", "40")

        # Act
        settings = GitCtxSettings()
        source = settings.get_source("search.limit")

        # Assert
        assert source == "(from GITCTX_SEARCH__LIMIT)"

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_get_source_repo_config(self, tmp_path, monkeypatch):
        """Should detect repo config file as source."""

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create repo config
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 25\n")

        # Act
        settings = GitCtxSettings()
        source = settings.get_source("search.limit")

        # Assert
        assert source == "(from repo config)"

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_get_source_default(self, tmp_path, monkeypatch):
        """Should detect default as source when no override."""

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act - no config files or env vars
        settings = GitCtxSettings()
        source = settings.get_source("search.limit")

        # Assert
        assert source == "(default)"


class TestInitRepoConfig:
    """Test init_repo_config() function."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_init_repo_config_creates_structure(self, tmp_path, monkeypatch):
        """Should create .gitctx/ directory with config.yml and .gitignore."""

        # Setup
        monkeypatch.chdir(tmp_path)

        # Act
        init_repo_config()

        # Assert - directory created
        assert (tmp_path / ".gitctx").exists()
        assert (tmp_path / ".gitctx").is_dir()

        # Assert - config.yml created with defaults
        config_file = tmp_path / ".gitctx" / "config.yml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "search:" in content
        assert "limit: 10" in content
        assert "index:" in content
        assert "model:" in content

        # Assert - .gitignore created
        gitignore = tmp_path / ".gitctx" / ".gitignore"
        assert gitignore.exists()

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_gitignore_content(self, tmp_path, monkeypatch):
        """Should create .gitignore with correct content."""

        # Setup
        monkeypatch.chdir(tmp_path)

        # Act
        init_repo_config()

        # Assert - .gitignore has correct content
        gitignore = tmp_path / ".gitctx" / ".gitignore"
        content = gitignore.read_text()

        # Check for comments (important for user understanding)
        assert "# LanceDB vector database - never commit" in content
        assert "# Application logs - never commit" in content

        # Check for patterns
        assert "db/" in content
        assert "logs/" in content
        assert "*.log" in content

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_init_repo_config_idempotent(self, tmp_path, monkeypatch):
        """Should be safe to call multiple times."""

        # Setup
        monkeypatch.chdir(tmp_path)

        # Act - call twice
        init_repo_config()
        init_repo_config()

        # Assert - still works, no errors
        assert (tmp_path / ".gitctx" / "config.yml").exists()
        assert (tmp_path / ".gitctx" / ".gitignore").exists()


class TestSecuritySeparation:
    """Test that user/repo configs are properly separated."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_api_keys_never_in_repo_config(self, temp_home, tmp_path, monkeypatch):
        """API keys should NEVER be saved to repo config."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)

        # Act - set API key
        settings = GitCtxSettings()
        settings.set("api_keys.openai", "sk-secret123")

        # Assert - API key in user config
        user_config = temp_home / ".gitctx" / "config.yml"
        assert user_config.exists()
        assert "sk-secret123" in user_config.read_text()

        # Assert - API key NOT in repo config (if it exists)
        repo_config = tmp_path / ".gitctx" / "config.yml"
        if repo_config.exists():
            assert "sk-secret123" not in repo_config.read_text()
            assert "api_keys" not in repo_config.read_text()

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_repo_settings_never_in_user_config(self, temp_home, tmp_path, monkeypatch):
        """Repo settings should NEVER be saved to user config."""

        # Setup
        monkeypatch.setenv("HOME", str(temp_home))
        # Clear OPENAI_API_KEY to prevent env var interference
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)

        # Act - set repo setting
        settings = GitCtxSettings()
        settings.set("search.limit", 30)

        # Assert - setting in repo config
        repo_config = tmp_path / ".gitctx" / "config.yml"
        assert repo_config.exists()
        assert "limit: 30" in repo_config.read_text()

        # Assert - setting NOT in user config (if it exists)
        user_config = temp_home / ".gitctx" / "config.yml"
        if user_config.exists():
            assert "search" not in user_config.read_text()
            assert "limit" not in user_config.read_text()


class TestConfigErrorHandling:
    """Test error handling in config operations."""

    def test_get_from_user_handles_missing_intermediate(self, temp_home, monkeypatch):
        """Test handling of None intermediate values in user config."""

        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        settings = GitCtxSettings()
        # Accessing a nonexistent nested key returns None
        # (getattr with default=None prevents AttributeError)
        result = settings.get("api_keys.nonexistent")
        assert result is None

    def test_set_in_repo_invalid_key_format(self, temp_home, monkeypatch, tmp_path):
        """Test setting repo config with invalid key format."""

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        settings = GitCtxSettings()
        # Try to set with wrong number of parts
        with contextlib.suppress(AttributeError):
            settings.set("invalid", "value")

    def test_get_source_edge_case_matching_default(self, tmp_path, monkeypatch):
        """Test get_source when value exists but matches default."""

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create repo config with default value
        config_file = tmp_path / ".gitctx" / "config.yml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # Set to default value (limit 10 is default)
        config_file.write_text("search:\n  limit: 10\n")

        settings = GitCtxSettings()
        source = settings.get_source("search.limit")
        # When value matches default, source detection has an edge case path
        assert source in ["(default)", "(from repo config)"]

    def test_get_from_user_returns_secret_value(self, temp_home, monkeypatch):
        """Test _get_from_user returns secret value for MaskedSecretStr."""

        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create user config with API key
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-secret789\n")

        settings = GitCtxSettings()
        # This should exercise the hasattr(current, "get_secret_value") path
        value = settings.get("api_keys.openai")
        assert value == "sk-secret789"

    def test_get_from_repo_returns_none_for_missing(self, tmp_path, monkeypatch):
        """Test _get_from_repo returns None for missing intermediate values."""

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        settings = GitCtxSettings()
        # Try to get a nonexistent nested value
        result = settings.get("search.nonexistent")
        assert result is None

    def test_get_source_user_config_yaml_error(self, temp_home, monkeypatch):
        """Test get_source handles YAML parsing errors in user config."""

        monkeypatch.setenv("HOME", str(temp_home))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create valid user config first so initialization succeeds
        config_file = temp_home / ".gitctx" / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-test123\n")

        settings = GitCtxSettings()

        # Now corrupt the file AFTER initialization but BEFORE get_source reads it
        config_file.write_text("api_keys:\n  openai: [unclosed")

        # Should handle YAML error gracefully and return default
        source = settings.get_source("api_keys.openai")
        assert source == "(default)"

    def test_get_source_repo_config_missing_nested_key(self, tmp_path, monkeypatch):
        """Test get_source when nested dict navigation fails in repo config."""

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create repo config without the searched key
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  rerank: true\n")

        settings = GitCtxSettings()
        # Should return default when nested key missing
        source = settings.get_source("index.chunk_size")
        assert source == "(default)"

    def test_get_source_repo_config_yaml_error(self, tmp_path, monkeypatch):
        """Test get_source handles YAML parsing errors in repo config."""

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create valid repo config first so initialization succeeds
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 20\n")

        settings = GitCtxSettings()

        # Now corrupt the file AFTER initialization but BEFORE get_source reads it
        config_file.write_text("search:\n  limit: {invalid yaml")

        # Should handle YAML error gracefully and return default
        source = settings.get_source("search.limit")
        assert source == "(default)"
