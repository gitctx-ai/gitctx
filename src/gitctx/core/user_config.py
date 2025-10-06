"""User-level configuration (API keys only)."""

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
