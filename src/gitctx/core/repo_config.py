"""Repo-level configuration (team settings only)."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class SearchSettings(BaseModel):
    """Search configuration."""

    limit: int = Field(default=10, gt=0, le=100)
    rerank: bool = True


class IndexSettings(BaseModel):
    """Indexing configuration."""

    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)


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
