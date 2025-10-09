"""Unit tests for OpenAI embedder configuration integration.

Tests configuration integration with GitCtxSettings following TDD:
- RED: Write failing tests first
- GREEN: Minimal implementation to pass
- REFACTOR: Clean up while tests protect

See:
- src/gitctx/embeddings/openai_embedder.py
- src/gitctx/core/config.py
"""

from pathlib import Path

import pytest

from gitctx.core.config import GitCtxSettings
from gitctx.core.exceptions import ConfigurationError
from gitctx.embeddings.openai_embedder import OpenAIEmbedder


class TestConfigIntegration:
    """Test OpenAIEmbedder integration with GitCtxSettings."""

    def test_embedder_reads_api_key_from_settings(self, isolated_env: Path) -> None:
        """OpenAIEmbedder uses API key from GitCtxSettings.

        Given: GitCtxSettings configured with OpenAI API key
        When: I initialize OpenAIEmbedder with key from settings
        Then: Embedder initializes successfully
        """
        # ARRANGE - Set up config with API key
        config_dir = isolated_env / ".gitctx"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yml"
        config_file.write_text("api_keys:\n  openai: sk-test-key-from-config\n")

        # ACT - Create embedder with key from settings
        settings = GitCtxSettings()
        api_key = settings.get("api_keys.openai")
        embedder = OpenAIEmbedder(api_key=api_key)

        # ASSERT - Embedder should be initialized
        assert embedder is not None
        assert embedder.MODEL == "text-embedding-3-large"

    def test_embedder_raises_if_no_api_key(self, isolated_env: Path) -> None:
        """OpenAIEmbedder raises ConfigurationError when API key missing.

        Given: GitCtxSettings has no OpenAI API key configured
        When: I attempt to initialize OpenAIEmbedder with None
        Then: ConfigurationError is raised with helpful message
        """
        # ARRANGE - Ensure no API key in settings
        settings = GitCtxSettings()
        api_key = settings.get("api_keys.openai")
        assert api_key is None, "API key should not be configured"

        # ACT & ASSERT - Should raise ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            OpenAIEmbedder(api_key=api_key)  # type: ignore

        # Verify error message is helpful
        error_msg = str(exc_info.value)
        assert "OpenAI API key required" in error_msg
        assert "sk-" in error_msg
        assert "OPENAI_API_KEY" in error_msg or "settings" in error_msg

    def test_embedder_respects_env_var(self, isolated_env: Path, monkeypatch) -> None:
        """OpenAIEmbedder can use OPENAI_API_KEY env var.

        Given: OPENAI_API_KEY environment variable is set
        When: I initialize OpenAIEmbedder with key from env var
        Then: Embedder initializes successfully
        """
        # ARRANGE - Set env var (overriding isolated_env)
        api_key = "sk-test-key-from-env-var"  # pragma: allowlist secret
        monkeypatch.setenv("OPENAI_API_KEY", api_key)

        # ACT - Create embedder with env var key
        embedder = OpenAIEmbedder(api_key=api_key)

        # ASSERT - Embedder should be initialized
        assert embedder is not None
        assert embedder.MODEL == "text-embedding-3-large"

    def test_embedder_requires_sk_prefix(self, isolated_env: Path) -> None:
        """OpenAIEmbedder validates API key format (must start with 'sk-').

        Given: An invalid API key not starting with 'sk-'
        When: I attempt to initialize OpenAIEmbedder
        Then: ConfigurationError is raised
        """
        # ARRANGE - Invalid API key
        invalid_key = "invalid-key-without-prefix"

        # ACT & ASSERT - Should raise ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            OpenAIEmbedder(api_key=invalid_key)

        # Verify error message mentions format
        error_msg = str(exc_info.value)
        assert "sk-" in error_msg

    def test_embedder_rejects_empty_api_key(self, isolated_env: Path) -> None:
        """OpenAIEmbedder rejects empty API key.

        Given: An empty string as API key
        When: I attempt to initialize OpenAIEmbedder
        Then: ConfigurationError is raised
        """
        # ARRANGE - Empty API key
        empty_key = ""

        # ACT & ASSERT - Should raise ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            OpenAIEmbedder(api_key=empty_key)

        # Verify error message is helpful
        error_msg = str(exc_info.value)
        assert "required" in error_msg.lower()
