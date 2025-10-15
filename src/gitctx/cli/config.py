"""Config command for gitctx CLI."""

from typing import Any

import typer
from pydantic import ValidationError
from rich.console import Console

from gitctx.cli.symbols import SYMBOLS
from gitctx.cli.tips import is_first_run, show_tip
from gitctx.config.settings import GitCtxSettings, init_repo_config

console = Console()
console_err = Console(stderr=True)

# Create a sub-app for config commands
config_app = typer.Typer(help="Manage gitctx configuration")


def _translate_validation_error(e: ValidationError, key: str, value: str) -> str:  # noqa: PLR0911
    """Translate Pydantic ValidationError to user-friendly message.

    Args:
        e: The ValidationError from Pydantic
        key: Config key that was being set
        value: Value that failed validation

    Returns:
        User-friendly error message explaining the validation failure
    """
    # Get first error (most relevant)
    if not e.errors():
        return f"Invalid value '{value}' for {key}"

    error = e.errors()[0]
    error_type = error["type"]
    msg = error.get("msg", "")

    # Translate common Pydantic error types to user-friendly messages
    if "int" in error_type.lower() or "integer" in msg.lower():
        return f"Invalid value '{value}' for {key} - expected a number"
    elif "greater_than" in error_type:
        # Extract the constraint if available
        ctx = error.get("ctx", {})
        min_val = ctx.get("gt", ctx.get("ge", ""))
        if min_val:
            return f"Invalid value '{value}' for {key} - must be greater than {min_val}"
        return f"Invalid value '{value}' for {key} - value too small"
    elif "less_than" in error_type:
        ctx = error.get("ctx", {})
        max_val = ctx.get("lt", ctx.get("le", ""))
        if max_val:
            return f"Invalid value '{value}' for {key} - must be less than {max_val}"
        return f"Invalid value '{value}' for {key} - value too large"
    elif "bool" in error_type.lower():
        return f"Invalid value '{value}' for {key} - expected true or false"
    elif "missing" in error_type:
        return f"Missing required field: {key}"
    else:
        # Generic fallback - use Pydantic's message but make it friendlier
        return f"Invalid value '{value}' for {key} - {msg.lower()}"


@config_app.command("init")
def config_init(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed output"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress all output except errors"),
) -> None:
    """Initialize repo-level configuration.

    Creates:
      - .gitctx/config.yml (team settings)
      - .gitctx/.gitignore (protects db/ and logs/)

    Run this once per repository before setting repo-level config.
    """
    try:
        init_repo_config()

        if not quiet:
            # Default: terse single-line (TUI_GUIDE.md compliance)
            console.print("Initialized .gitctx/")

            if verbose:
                # Verbose: detailed output with next steps
                console.print("  Created .gitctx/config.yml")
                console.print("  Created .gitctx/.gitignore")
                console.print("\nNext steps:")
                console.print("  1. Set your API key: gitctx config set api_keys.openai sk-...")
                console.print("  2. Index your repo: gitctx index")
                console.print(
                    "  3. Commit to share: git add .gitctx/ && "
                    "git commit -m 'chore: Add gitctx embeddings'"
                )

            # First-run tip (only once)
            if is_first_run("config"):
                show_tip("config")

    except FileExistsError:
        if not quiet:
            console.print(f"[yellow]{SYMBOLS['warning']}[/yellow] .gitctx/ already initialized")
    except PermissionError as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Permission denied: {e}")
        raise typer.Exit(6) from e
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: {e}")
        raise typer.Exit(1) from e


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (supports dot notation)"),
    value: str = typer.Argument(..., help="Configuration value"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show detailed output"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress all output except errors"),
) -> None:
    """Set a configuration value.

    Examples:

        $ gitctx config set api_keys.openai sk-abc123
        $ gitctx config set search.limit 20
    """
    try:
        # Load settings, update value, save
        settings = GitCtxSettings()
        settings.set(key, value)

        if quiet:
            # Quiet: no output
            pass
        elif verbose:
            # Verbose: show which config file was updated
            config_location = "user config" if key.startswith("api_keys.") else "repo config"
            config_path = (
                "~/.gitctx/config.yml" if key.startswith("api_keys.") else ".gitctx/config.yml"
            )
            console.print(f"set {key} in {config_location} ({config_path})")
        else:
            # Default: terse lowercase confirmation (TUI_GUIDE.md compliance)
            console.print(f"set {key}")

    except ValidationError as e:
        # Show user-friendly validation errors (exit code 2 per TUI_GUIDE.md)
        friendly_msg = _translate_validation_error(e, key, value)
        console_err.print(f"[red]{SYMBOLS['error']}[/red] {friendly_msg}")
        raise typer.Exit(2) from e
    except PermissionError as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Permission denied: {e}")
        raise typer.Exit(6) from e
    except AttributeError as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: Unknown configuration key: {key}")
        raise typer.Exit(2) from e
    except FileNotFoundError as e:
        console_err.print(
            f"[red]{SYMBOLS['error']}[/red] Error: "
            "Run 'gitctx config init' first to create .gitctx/"
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: {e}")
        raise typer.Exit(1) from e


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key to retrieve"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show key name and source"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Output value only, no formatting"),
) -> None:
    """Get a configuration value.

    Environment variables take precedence over config file values.

    Examples:

        $ gitctx config get api_keys.openai
        sk-...123

        $ gitctx config get api_keys.openai --verbose
        api_keys.openai = sk-...123 (from user config)
    """
    try:
        settings = GitCtxSettings()

        # For API keys, get the MaskedSecretStr object directly for auto-masking
        if key.startswith("api_keys."):
            # Navigate to the actual field to preserve MaskedSecretStr
            parts = key.split(".")
            current: Any = settings.user
            for part in parts:
                current = getattr(current, part, None)
                if current is None:
                    console.print(f"{key} is not set")
                    raise typer.Exit(1)
            value_for_display = str(current)  # Auto-masks via MaskedSecretStr.__str__()
        else:
            # For non-secret values, use normal get
            value = settings.get(key)
            if value is None:
                console.print(f"{key} is not set")
                raise typer.Exit(1)
            value_for_display = str(value)

        if quiet:
            # Quiet: just the value (for scripting)
            console.print(value_for_display)
        elif verbose:
            # Verbose: key = value (source)
            source = settings.get_source(key)
            console.print(f"{key} = {value_for_display} {source}")
        else:
            # Default: just the value (terse, git-like per TUI_GUIDE.md)
            console.print(value_for_display)

    except AttributeError as e:
        console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: Unknown configuration key: {key}")
        raise typer.Exit(2) from e
    except Exception as e:
        # Catch YAML parsing errors and other config loading errors
        error_msg = str(e).lower()
        if "yaml" in error_msg or "parsing" in error_msg:
            console_err.print(f"[red]{SYMBOLS['error']}[/red] Failed to parse config file: {e}")
        else:
            console_err.print(f"[red]{SYMBOLS['error']}[/red] Error: {e}")
        raise typer.Exit(1) from e


@config_app.command("list")
def config_list(
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show sources for all values including defaults",
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress formatting, show key=value only"
    ),
) -> None:
    """List all configuration settings.

    Shows current configuration with sensitive values masked.

    Examples:

        $ gitctx config list
        api_keys.openai=sk-...123 (from user config)
        search.limit=10

        $ gitctx config list --verbose
        api_keys.openai=sk-...123 (from user config)
        search.limit=10 (default)
        model.embedding=text-embedding-3-large (default)
    """
    settings = GitCtxSettings()

    # Flatten nested models to dot notation
    items = []

    # api_keys.*
    if settings.user.api_keys.openai is not None:
        # MaskedSecretStr auto-masks via __str__()
        masked = str(settings.user.api_keys.openai)
        source = settings.get_source("api_keys.openai")
        items.append(("api_keys.openai", masked, source))

    # search.*
    for field in ["limit", "rerank"]:
        value = getattr(settings.repo.search, field)
        source = settings.get_source(f"search.{field}")
        items.append((f"search.{field}", str(value), source))

    # index.*
    for field in ["chunk_size", "chunk_overlap"]:
        value = getattr(settings.repo.index, field)
        source = settings.get_source(f"index.{field}")
        items.append((f"index.{field}", str(value), source))

    # model.*
    for field in ["embedding"]:
        value = getattr(settings.repo.model, field)
        source = settings.get_source(f"model.{field}")
        items.append((f"model.{field}", str(value), source))

    # Sort and print
    if not items:
        console.print("No configuration set")
        return

    for key, value, source in sorted(items):
        if quiet:
            # Quiet: just key=value
            console.print(f"{key}={value}")
        elif verbose:
            # Verbose: show ALL sources (including defaults)
            console.print(f"{key}={value} {source}")
        # Default: only show source if non-default (TUI_GUIDE.md compliance)
        elif source and "(default)" not in source.lower():
            console.print(f"{key}={value} {source}")
        else:
            console.print(f"{key}={value}")
