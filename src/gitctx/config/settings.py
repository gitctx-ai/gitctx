"""Unified configuration management for gitctx.

This module aggregates user-level config (API keys) and repo-level config
(team settings) with smart routing and precedence handling.

Precedence:
- User config: OPENAI_API_KEY env var > ~/.gitctx/config.yml > defaults
- Repo config: GITCTX_* env vars > .gitctx/config.yml > defaults
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# ===================================================================
# User Config Components (API Keys)
# ===================================================================


class MaskedSecretStr(SecretStr):
    """SecretStr that displays first 3 and last 3 characters when printed.

    Inherits all security benefits of SecretStr (prevents logging, repr protection)
    but provides custom masking format for user-facing display.

    Example:
        >>> secret = MaskedSecretStr("sk-abc123")
        >>> str(secret)
        'sk-...123'
    """

    def __repr__(self) -> str:
        """Return masked representation for debugging."""
        return f"MaskedSecretStr('{self._mask()}')"

    def __str__(self) -> str:
        """Return masked string for display."""
        return self._mask()

    def _mask(self) -> str:
        """Mask the secret value showing first/last 3 chars.

        Returns:
            Masked string in format 'abc...xyz' if length > 6, else '***'
        """
        value = self.get_secret_value()
        if len(value) > 6:
            return f"{value[:3]}...{value[-3:]}"
        return "***"


def _get_user_home() -> Path:
    """Get user home directory, respecting HOME env var.

    On Unix, Path.home() respects HOME environment variable.
    On Windows, Path.home() ignores HOME and uses USERPROFILE.
    This helper ensures HOME is used when set (critical for testing).

    Returns:
        Path: User home directory
    """
    return Path(os.environ.get("HOME", str(Path.home())))


class ApiKeys(BaseModel):
    """API key configuration."""

    openai: MaskedSecretStr | None = Field(default=None, description="OpenAI API key")


class ProviderEnvSource(PydanticBaseSettingsSource):
    """Custom source for OPENAI_API_KEY env var."""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """This method is required by Pydantic's settings source interface, but is not used in this custom source.

        Only the __call__ method is invoked by Pydantic when loading settings from this source.
        See: https://docs.pydantic.dev/latest/concepts/settings/#customise-sources
        """
        raise NotImplementedError()

    def __call__(self) -> dict[str, Any]:
        """Load OPENAI_API_KEY from environment."""
        d: dict[str, Any] = {}
        if openai_key := os.getenv("OPENAI_API_KEY"):
            d["api_keys"] = {"openai": openai_key}
        return d


class UserConfig(BaseSettings):
    """User config (~/.gitctx/config.yml) - API keys only.

    Precedence:
    1. OPENAI_API_KEY env var (highest)
    2. User YAML file
    3. Defaults
    """

    api_keys: ApiKeys = Field(default_factory=ApiKeys)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls: type["UserConfig"],
        init_settings: Any,
        env_settings: Any,  # noqa: ARG003
        dotenv_settings: Any,  # noqa: ARG003
        file_secret_settings: Any,  # noqa: ARG003
    ) -> tuple[Any, ...]:
        """Customize settings sources to support OPENAI_API_KEY precedence."""
        # Create YAML source with dynamic path
        yaml_file = _get_user_home() / ".gitctx" / "config.yml"
        if yaml_file.exists():
            # Check file permissions for security
            stat = yaml_file.stat()
            # Check if group or others have any permissions (should be 0600)
            if stat.st_mode & 0o077:  # Group (o70) or others (o07) have access
                import sys

                # Use stderr to avoid interfering with command output
                current_perms = oct(stat.st_mode)[-3:]
                # Use simple text for cross-platform compatibility (no Unicode symbols)
                warning = (
                    f"Warning: User config has insecure permissions "
                    f"(current: {current_perms}, should be 0600)\n"
                )
                sys.stderr.write(warning)

            yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        else:

            def empty_source() -> dict[str, Any]:
                return {}

            yaml_source = empty_source  # type: ignore[assignment]

        return (
            init_settings,
            ProviderEnvSource(settings_cls),  # OPENAI_API_KEY
            yaml_source,
        )

    def save(self) -> None:
        """Save API keys to user config file."""
        config_path = _get_user_home() / ".gitctx" / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if self.api_keys.openai is not None:
            # Handle both SecretStr and plain string (str accepted via validation)
            if isinstance(self.api_keys.openai, SecretStr):
                openai_value = self.api_keys.openai.get_secret_value()
            else:
                openai_value = str(self.api_keys.openai)
            data["api_keys"] = {"openai": openai_value}

        # Secure permissions
        old_umask = os.umask(0o077)
        try:
            with config_path.open("w") as f:
                yaml.dump(data, f, default_flow_style=False)
        finally:
            os.umask(old_umask)
        config_path.chmod(0o600)


# ===================================================================
# Repo Config Components (Team Settings)
# ===================================================================


class SearchSettings(BaseModel):
    """Search configuration."""

    limit: int = Field(default=10, gt=0, le=100)
    rerank: bool = True


class IndexSettings(BaseModel):
    """Indexing configuration."""

    # Chunking settings (STORY-0001.2.2)
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    # Safety margin below text-embedding-3-large's 8191 limit to account for
    # token estimation errors (chunker uses char-to-token ratio approximation)
    max_chunk_tokens: int = Field(
        default=1000,
        ge=100,
        le=8000,
        description="Maximum tokens per chunk",
    )
    chunk_overlap_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=0.5,
        description="Chunk overlap ratio (0.0-0.5)",
    )

    # Walker settings (STORY-0001.2.1)
    max_blob_size_mb: int = Field(
        default=5,
        gt=0,
        le=100,
        description="Maximum blob size to index (MB)",
    )
    refs: list[str] = Field(
        default_factory=lambda: ["HEAD"],
        description="Git refs to index",
    )
    respect_gitignore: bool = Field(
        default=True,
        description="Skip gitignored files",
    )
    skip_binary: bool = Field(
        default=True,
        description="Skip binary files",
    )


class ModelSettings(BaseModel):
    """Model configuration."""

    embedding: str = "text-embedding-3-large"


class RepoConfig(BaseSettings):
    """Repo config (.gitctx/config.yml) - team settings only.

    Precedence:
    1. GITCTX_* env vars (highest)
    2. Repo YAML file
    3. Defaults

    Default YAML content (created by config init):
    ```yaml
    search:
      limit: 10
      rerank: true
    index:
      chunk_size: 1000
      chunk_overlap: 200
      max_chunk_tokens: 1000
      chunk_overlap_ratio: 0.2
    model:
      embedding: text-embedding-3-large
    ```
    """

    search: SearchSettings = Field(default_factory=SearchSettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)

    model_config = SettingsConfigDict(
        env_prefix="GITCTX_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls: type["RepoConfig"],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,  # noqa: ARG003
        file_secret_settings: Any,  # noqa: ARG003
    ) -> tuple[Any, ...]:
        """Customize settings sources to support dynamic YAML file path."""

        # Create YAML source with dynamic path
        yaml_file = Path(".gitctx/config.yml")
        if yaml_file.exists():
            yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        else:

            def empty_source() -> dict[str, Any]:
                return {}

            yaml_source = empty_source  # type: ignore[assignment]

        return (
            init_settings,
            env_settings,  # GITCTX_* env vars
            yaml_source,
        )

    def save(self) -> None:
        """Save team settings to repo config file."""
        config_path = Path(".gitctx/config.yml")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "search": self.search.model_dump(),
            "index": self.index.model_dump(),
            "model": self.model.model_dump(),
        }

        with config_path.open("w") as f:
            yaml.dump(data, f, default_flow_style=False)
        config_path.chmod(0o644)  # Safe to commit


# ===================================================================
# Config Aggregator (Smart Routing)
# ===================================================================


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
        user_home = _get_user_home()
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


# ===================================================================
# Initialization Helper
# ===================================================================


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
