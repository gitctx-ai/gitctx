"""Aggregates user and repo config with smart routing."""

import os
from pathlib import Path
from typing import Any

import yaml

from .repo_config import RepoConfig
from .user_config import UserConfig


class GitCtxSettings:
    """Aggregator that routes config by key pattern.

    Routes:
    - api_keys.* → UserConfig (~/.gitctx/config.yml)
    - search.*, index.*, model.* → RepoConfig (.gitctx/config.yml)
    """

    def __init__(self) -> None:
        """Initialize user and repo configs."""
        self.user = UserConfig()
        self.repo = RepoConfig()

    def get(self, key: str) -> Any:
        """Get config value, routing by key pattern."""
        if key.startswith("api_keys."):
            return self._get_from_user(key)
        else:
            return self._get_from_repo(key)

    def _get_from_user(self, key: str) -> Any:
        """Get value from user config by navigating nested attributes.

        Recursively traverses the user config object using dot-separated path segments.
        Automatically unwraps Pydantic SecretStr values to return plain strings for
        user-facing display while maintaining security benefits.

        Args:
            key: Dot-separated path to config value (e.g., "api_keys.openai").
                 Each segment represents an attribute to access.

        Returns:
            The config value at the specified path, or None if the path doesn't exist.
            SecretStr values are automatically unwrapped via get_secret_value().

        Examples:
            >>> config._get_from_user("api_keys.openai")
            "sk-abc123..."  # Unwrapped from SecretStr

            >>> config._get_from_user("api_keys.nonexistent")
            None
        """
        parts = key.split(".")
        current: Any = self.user
        for part in parts:
            current = getattr(current, part, None)
            if current is None:
                return None

        # Handle SecretStr
        if hasattr(current, "get_secret_value"):
            return current.get_secret_value()
        return current

    def _get_from_repo(self, key: str) -> Any:
        """Get value from repo config by navigating nested attributes.

        Recursively traverses the repo config object using dot-separated path segments.
        Used for team settings like search limits, index parameters, and model configuration.

        Args:
            key: Dot-separated path to config value (e.g., "search.limit").
                 Each segment represents an attribute to access.

        Returns:
            The config value at the specified path, or None if the path doesn't exist.

        Examples:
            >>> config._get_from_repo("search.limit")
            10

            >>> config._get_from_repo("search.nonexistent")
            None
        """
        parts = key.split(".")
        current: Any = self.repo
        for part in parts:
            current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def set(self, key: str, value: Any) -> None:
        """Set config value, routing by key pattern."""
        if key.startswith("api_keys."):
            self._set_in_user(key, value)
            self.user.save()  # → ~/.gitctx/config.yml
        else:
            self._set_in_repo(key, value)
            self.repo.save()  # → .gitctx/config.yml

    def _set_in_user(self, key: str, value: Any) -> None:
        """Set value in user config."""
        parts = key.split(".")
        current: Any = self.user
        for part in parts[:-1]:
            current = getattr(current, part)
        setattr(current, parts[-1], value)

    def _set_in_repo(self, key: str, value: Any) -> None:
        """Set value in repo config with Pydantic validation."""
        parts = key.split(".")
        if len(parts) != 2:
            raise AttributeError(f"Invalid repo config key: {key}")

        section, field = parts
        # Get current section model
        section_model = getattr(self.repo, section)
        # Build updated dict with type coercion
        updated_dict = section_model.model_dump()
        updated_dict[field] = value
        # Rebuild model to trigger validation and type coercion
        new_section = type(section_model)(**updated_dict)
        setattr(self.repo, section, new_section)

    def _get_api_key_source(self, key: str) -> str:
        """Determine source for API key configuration.

        Args:
            key: API key config path (e.g., "api_keys.openai")

        Returns:
            Source indicator string (e.g., "(from OPENAI_API_KEY)")
        """
        # Check OPENAI_API_KEY env var
        if key == "api_keys.openai" and os.getenv("OPENAI_API_KEY"):
            return "(from OPENAI_API_KEY)"

        # Check user config file
        user_home = Path(os.environ.get("HOME", str(Path.home())))
        user_config_path = user_home / ".gitctx" / "config.yml"
        if user_config_path.exists():
            try:
                with user_config_path.open() as f:
                    config_data = yaml.safe_load(f) or {}
                if "api_keys" in config_data:
                    return "(from user config)"
            except Exception:
                pass

        return "(default)"

    def _get_repo_setting_source(self, key: str) -> str:
        """Determine source for repo setting configuration.

        Args:
            key: Repo setting config path (e.g., "search.limit")

        Returns:
            Source indicator string (e.g., "(from GITCTX_SEARCH__LIMIT)")
        """
        # Check GITCTX_* env vars
        env_key = f"GITCTX_{key.upper().replace('.', '__')}"
        if os.getenv(env_key):
            return f"(from {env_key})"

        # Check repo config file
        repo_config_path = Path(".gitctx/config.yml")
        if repo_config_path.exists():
            try:
                with repo_config_path.open() as f:
                    config_data = yaml.safe_load(f) or {}
                # Navigate nested dict
                parts = key.split(".")
                current = config_data
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return "(default)"
                return "(from repo config)"
            except Exception:
                pass

        return "(default)"

    def get_source(self, key: str) -> str:
        """Get the source of a configuration value."""
        if key.startswith("api_keys."):
            return self._get_api_key_source(key)
        else:
            return self._get_repo_setting_source(key)


def init_repo_config() -> None:
    """Initialize .gitctx/ structure."""
    gitctx_dir = Path(".gitctx")
    gitctx_dir.mkdir(exist_ok=True)

    # Create config.yml
    config_file = gitctx_dir / "config.yml"
    if not config_file.exists():
        RepoConfig().save()

    # Create .gitignore
    gitignore_content = """# LanceDB vector database - never commit
db/

# Application logs - never commit
logs/
*.log
"""
    (gitctx_dir / ".gitignore").write_text(gitignore_content)
