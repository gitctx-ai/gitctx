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
