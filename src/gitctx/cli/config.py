"""Config command for gitctx CLI."""

import os
from typing import Any

import typer
from rich.console import Console

console = Console()

# In-memory storage for mock configuration (NO file I/O for testing isolation)
_config_store: dict[str, Any] = {}

# Create a sub-app for config commands
config_app = typer.Typer(help="Manage gitctx configuration")


def register(app: typer.Typer) -> None:
    """Register the config command group with the CLI app."""
    app.add_typer(config_app, name="config")


def _parse_dot_notation(key: str) -> list[str]:
    """Parse dot notation into nested keys."""
    return key.split(".")


def _get_nested(data: dict[str, Any], keys: list[str]) -> Any:
    """Get value from nested dict using key path."""
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current


def _set_nested(data: dict[str, Any], keys: list[str], value: str) -> None:
    """Set value in nested dict using key path."""
    current = data
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


def _mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive values like API keys."""
    # Check if this is an API key (starts with common prefixes) and long enough to mask
    if (
        any(key.endswith(f".{provider}") for provider in ["openai", "anthropic", "cohere"])
        and len(value) > 6
    ):
        # Show first 3 and last 3 characters: sk-...123
        return f"{value[:3]}...{value[-3:]}"
    return value


def _get_env_value(key: str) -> str | None:
    """Get value from environment variable if it exists."""
    # Map config keys to environment variable names
    env_mapping = {
        "api_keys.openai": "OPENAI_API_KEY",
        "api_keys.anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_mapping.get(key)
    if env_var:
        return os.environ.get(env_var)
    return None


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (supports dot notation)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """
    Set a configuration value.

    Examples:

        $ gitctx config set api_keys.openai sk-abc123
        $ gitctx config set search.limit 20
    """
    keys = _parse_dot_notation(key)
    _set_nested(_config_store, keys, value)
    console.print(f"Set {key}")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key to retrieve"),
) -> None:
    """
    Get a configuration value.

    Environment variables take precedence over config file values.

    Examples:

        $ gitctx config get api_keys.openai
        $ gitctx config get search.limit
    """
    # Check environment variable first (takes precedence)
    env_value = _get_env_value(key)
    if env_value:
        masked = _mask_sensitive_value(key, env_value)
        console.print(f"{key} = {masked} (from environment)")
        return

    # Get from config store
    keys = _parse_dot_notation(key)
    value = _get_nested(_config_store, keys)

    if value is None:
        console.print(f"{key} is not set")
        return

    masked = _mask_sensitive_value(key, value)
    console.print(f"{key} = {masked}")


@config_app.command("list")
def config_list() -> None:
    """
    List all configuration settings.

    Shows current configuration with sensitive values masked.

    Example:

        $ gitctx config list
    """
    if not _config_store:
        console.print("No configuration set")
        return

    def _flatten_dict(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dict to dot notation."""
        items = {}
        for k, v in d.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.update(_flatten_dict(v, new_key))
            else:
                items[new_key] = v
        return items

    flat = _flatten_dict(_config_store)

    for key, value in sorted(flat.items()):
        masked = _mask_sensitive_value(key, str(value))
        console.print(f"{key} = {masked}")
