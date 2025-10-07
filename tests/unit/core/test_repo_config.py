"""Unit tests for repo configuration (team settings only)."""

import os

import pytest


class TestRepoConfigLoading:
    """Test repo config loading from various sources."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_repo_config_loads_from_yaml(self, tmp_path, monkeypatch):
        """Config should load settings from YAML file."""
        from gitctx.core.repo_config import RepoConfig

        # Setup - change to test directory
        monkeypatch.chdir(tmp_path)

        # Create config file
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 20\n  rerank: false\n")

        # Act
        config = RepoConfig()

        # Assert
        assert config.search.limit == 20
        assert config.search.rerank is False

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_gitctx_env_var_overrides_yaml(self, tmp_path, monkeypatch):
        """GITCTX_* env vars should override YAML."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITCTX_SEARCH__LIMIT", "30")

        # Create config file with different value
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 10\n")

        # Act
        config = RepoConfig()

        # Assert - env var wins
        assert config.search.limit == 30

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_yaml_used_when_no_env_vars(self, tmp_path, monkeypatch):
        """YAML should be used when no env vars are set."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Create config file
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: 25\n")

        # Act
        config = RepoConfig()

        # Assert
        assert config.search.limit == 25

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_defaults_used_when_no_config(self, tmp_path, monkeypatch):
        """Defaults should be used when no config file exists."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Act - no config file
        config = RepoConfig()

        # Assert - defaults
        assert config.search.limit == 10
        assert config.search.rerank is True
        assert config.index.chunk_size == 1000
        assert config.index.chunk_overlap == 200
        assert config.model.embedding == "text-embedding-3-large"


class TestRepoConfigValidation:
    """Test Pydantic validation of configuration values."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_config_validates_types(self):
        """Config should validate type correctness."""
        from gitctx.core.repo_config import RepoConfig

        # Act
        config = RepoConfig(search={"limit": 20})

        # Assert
        assert config.search.limit == 20
        assert isinstance(config.search.limit, int)

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_config_rejects_invalid_types(self):
        """Config should reject invalid type values."""
        from pydantic import ValidationError

        from gitctx.core.repo_config import RepoConfig

        # Assert
        with pytest.raises(ValidationError) as exc_info:
            RepoConfig(search={"limit": "invalid"})

        assert "validation error" in str(exc_info.value).lower()

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_config_validates_constraints(self):
        """Config should validate field constraints."""
        from pydantic import ValidationError

        from gitctx.core.repo_config import RepoConfig

        # Test negative limit (should fail - must be > 0)
        with pytest.raises(ValidationError):
            RepoConfig(search={"limit": -5})

        # Test limit too high (should fail - must be <= 100)
        with pytest.raises(ValidationError):
            RepoConfig(search={"limit": 150})


class TestRepoConfigPersistence:
    """Test saving repo configuration."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_repo_config_saves_to_yaml(self, tmp_path, monkeypatch):
        """Config.save() should persist to YAML file with 0644 permissions."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Create config
        config = RepoConfig()
        config.search.limit = 25

        # Act
        config.save()

        # Assert - file exists
        config_file = tmp_path / ".gitctx" / "config.yml"
        assert config_file.exists()

        # Assert - content is correct
        content = config_file.read_text()
        assert "limit: 25" in content

        # Assert - file permissions are 0644 (Unix) or just readable (Windows)
        import stat

        from tests.conftest import is_windows

        if is_windows():
            # Windows uses ACLs, not Unix permissions - just verify file is accessible
            assert config_file.exists()
            assert os.access(config_file, os.R_OK)
        else:
            # Unix: Check exact permissions
            mode = config_file.stat().st_mode
            assert stat.S_IMODE(mode) == 0o644

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_repo_config_creates_directory(self, tmp_path, monkeypatch):
        """Config.save() should create .gitctx/ if it doesn't exist."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Verify directory doesn't exist
        assert not (tmp_path / ".gitctx").exists()

        # Act
        config = RepoConfig()
        config.save()

        # Assert - directory and file created
        assert (tmp_path / ".gitctx").exists()
        assert (tmp_path / ".gitctx" / "config.yml").exists()


class TestErrorHandling:
    """Test error handling for malformed YAML and permission issues."""

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_malformed_yaml_error(self, tmp_path, monkeypatch):
        """Clear error message for malformed YAML."""
        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Create invalid YAML
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("search:\n  limit: [unclosed")

        # Act & Assert - should raise error
        with pytest.raises(Exception) as exc_info:
            RepoConfig()

        # Error message should be helpful
        assert "parsing" in str(exc_info.value).lower() or "yaml" in str(exc_info.value).lower()

    # @pytest.mark.skip(reason="RED phase - module doesn't exist yet")
    def test_permission_denied_error(self, tmp_path, monkeypatch):
        """Clear error message for permission denied."""
        import subprocess

        from tests.conftest import is_windows

        from gitctx.core.repo_config import RepoConfig

        # Setup
        monkeypatch.chdir(tmp_path)

        # Create read-only directory
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()

        if is_windows():
            # Windows: Use icacls to deny write permission
            config_file = config_dir / "config.yml"
            config_file.touch()  # Create file first
            # Remove write permissions using icacls
            # NOTE: Using *S-1-1-0 (Everyone) is safe here because:
            # - We're only modifying permissions on isolated tmp_path test files
            # - Permissions are restored immediately after the test
            # - pytest automatically cleans up tmp_path after test completion
            subprocess.run(
                ["icacls", str(config_file), "/deny", "*S-1-1-0:(W)"],
                check=True,
                capture_output=True,
            )

            # Act & Assert - should raise PermissionError on write
            with pytest.raises(PermissionError):
                config = RepoConfig()
                config.save()

            # Cleanup: restore permissions so pytest can delete temp dir
            subprocess.run(
                ["icacls", str(config_file), "/grant", "*S-1-1-0:(F)"],
                check=True,
                capture_output=True,
            )
        else:
            # Unix: Use chmod
            config_dir.chmod(0o444)  # Read-only

            # Act & Assert - should raise PermissionError
            with pytest.raises(PermissionError):
                config = RepoConfig()
                config.save()


class TestEdgeCasesUnicode:
    """Test Unicode handling - real scenario: international users."""

    def test_unicode_emoji_in_model_name(self, tmp_path, monkeypatch):
        """Model name can contain emoji."""
        from gitctx.core.repo_config import RepoConfig

        monkeypatch.chdir(tmp_path)
        config = RepoConfig()
        config.model.embedding = "text-embedding-🌍-large"
        config.save()

        # Reload and verify
        config2 = RepoConfig()
        assert config2.model.embedding == "text-embedding-🌍-large"


class TestFileCorruption:
    """Test file corruption - real scenario: editor crash, disk full."""

    def test_truncated_yaml_shows_clear_error(self, tmp_path, monkeypatch):
        """Truncated YAML shows clear error message."""
        from gitctx.core.repo_config import RepoConfig

        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        # Truncated in middle of value
        config_file.write_text("search:\n  lim")

        # Should raise with parse/yaml/validation error
        with pytest.raises(Exception) as exc:
            RepoConfig()
        error_msg = str(exc.value).lower()
        # Pydantic validation error is also acceptable (clear error message)
        assert any(word in error_msg for word in ["parse", "yaml", "scan", "validation"])

    def test_malformed_yaml_shows_clear_error(self, tmp_path, monkeypatch):
        """Malformed YAML shows helpful error message."""
        from pydantic import ValidationError

        from gitctx.core.repo_config import RepoConfig

        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        # List instead of dict - wrong type
        config_file.write_text("search:\n- wrong_type\n")

        # Should raise ValidationError (Pydantic catches wrong type)
        with pytest.raises(ValidationError):
            RepoConfig()


class TestWalkerSettings:
    """Test walker-specific IndexSettings fields."""

    def test_walker_settings_defaults(self, tmp_path, monkeypatch):
        """Walker settings should use correct default values."""
        from gitctx.core.repo_config import RepoConfig

        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act - no config file
        config = RepoConfig()

        # Assert - defaults match walker requirements
        assert config.index.max_blob_size_mb == 5
        assert config.index.refs == ["HEAD"]
        assert config.index.respect_gitignore is True
        assert config.index.skip_binary is True

    def test_walker_settings_load_from_yaml(self, tmp_path, monkeypatch):
        """Walker settings should load from YAML file."""
        from gitctx.core.repo_config import RepoConfig

        # Arrange
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("""
index:
  max_blob_size_mb: 10
  refs:
    - HEAD
    - refs/tags/*
  respect_gitignore: false
  skip_binary: false
""")

        # Act
        config = RepoConfig()

        # Assert
        assert config.index.max_blob_size_mb == 10
        assert config.index.refs == ["HEAD", "refs/tags/*"]
        assert config.index.respect_gitignore is False
        assert config.index.skip_binary is False

    def test_walker_settings_env_var_override(self, tmp_path, monkeypatch):
        """GITCTX_INDEX__* env vars should override YAML."""
        from gitctx.core.repo_config import RepoConfig

        # Arrange
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITCTX_INDEX__MAX_BLOB_SIZE_MB", "15")
        monkeypatch.setenv("GITCTX_INDEX__REFS", '["refs/heads/main"]')
        monkeypatch.setenv("GITCTX_INDEX__RESPECT_GITIGNORE", "false")
        monkeypatch.setenv("GITCTX_INDEX__SKIP_BINARY", "false")

        # Create config file with different values
        config_dir = tmp_path / ".gitctx"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("""
index:
  max_blob_size_mb: 5
  refs: ["HEAD"]
  respect_gitignore: true
  skip_binary: true
""")

        # Act
        config = RepoConfig()

        # Assert - env vars win
        assert config.index.max_blob_size_mb == 15
        assert config.index.refs == ["refs/heads/main"]
        assert config.index.respect_gitignore is False
        assert config.index.skip_binary is False

    def test_walker_settings_validation(self, tmp_path, monkeypatch):
        """Walker settings should validate constraints."""
        import pytest
        from pydantic import ValidationError

        from gitctx.core.repo_config import RepoConfig

        # Test max_blob_size_mb must be > 0
        with pytest.raises(ValidationError):
            RepoConfig(index={"max_blob_size_mb": 0})

        # Test max_blob_size_mb must be <= 100
        with pytest.raises(ValidationError):
            RepoConfig(index={"max_blob_size_mb": 150})

        # Test refs must be a list
        with pytest.raises(ValidationError):
            RepoConfig(index={"refs": "HEAD"})

        # Test respect_gitignore must be bool-coercible (reject dict)
        with pytest.raises(ValidationError):
            RepoConfig(index={"respect_gitignore": {"invalid": "object"}})

        # Test skip_binary must be bool-coercible (reject list)
        with pytest.raises(ValidationError):
            RepoConfig(index={"skip_binary": ["invalid", "list"]})

    def test_walker_settings_persist_to_yaml(self, tmp_path, monkeypatch):
        """Walker settings should be saved to YAML file."""
        from gitctx.core.repo_config import RepoConfig

        # Arrange
        monkeypatch.chdir(tmp_path)
        config = RepoConfig()
        config.index.max_blob_size_mb = 8
        config.index.refs = ["HEAD", "refs/remotes/origin/main"]
        config.index.respect_gitignore = False
        config.index.skip_binary = False

        # Act
        config.save()

        # Assert - file exists with correct content
        config_file = tmp_path / ".gitctx" / "config.yml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "max_blob_size_mb: 8" in content
        assert "- HEAD" in content
        assert "- refs/remotes/origin/main" in content
        assert "respect_gitignore: false" in content
        assert "skip_binary: false" in content
