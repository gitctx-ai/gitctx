"""Unit tests for config command."""


from gitctx.cli.main import app



def test_config_command_exists(cli_runner):
    """Verify config command group is registered."""
    result = cli_runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
    assert "Manage" in result.stdout or "configuration" in result.stdout.lower()


def test_config_set_command(cli_runner):
    """Verify config set subcommand works."""
    result = cli_runner.invoke(app, ["config", "set", "api_keys.openai", "sk-test123"])
    assert result.exit_code == 0
    assert "set" in result.stdout.lower() or "saved" in result.stdout.lower()


def test_config_get_command(cli_runner):
    """Verify config get subcommand works and masks API keys."""
    # First set a value
    cli_runner.invoke(app, ["config", "set", "api_keys.openai", "sk-test123"])
    # Then get it
    result = cli_runner.invoke(app, ["config", "get", "api_keys.openai"])
    assert result.exit_code == 0
    # Should mask API key in output (show first 3 and last 3)
    assert "sk-...123" in result.stdout


def test_config_list_command(cli_runner):
    """Verify config list subcommand works."""
    # Set a value first so list has something to show
    cli_runner.invoke(app, ["config", "set", "test.key", "value"])
    result = cli_runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    # Should show key=value format
    assert "=" in result.stdout or ":" in result.stdout


def test_config_set_requires_value(cli_runner):
    """Verify set command requires both key and value."""
    result = cli_runner.invoke(app, ["config", "set", "test.key"])
    assert result.exit_code != 0
    # Typer will show error about missing VALUE argument


def test_config_get_requires_key(cli_runner):
    """Verify get command requires key."""
    result = cli_runner.invoke(app, ["config", "get"])
    assert result.exit_code != 0
    # Typer will show error about missing KEY argument


def test_config_env_override(cli_runner, monkeypatch):
    """Verify environment variables override config."""
    # Set config value
    cli_runner.invoke(app, ["config", "set", "api_keys.openai", "sk-config123"])
    # Set environment variable (should take precedence)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env123")
    result = cli_runner.invoke(app, ["config", "get", "api_keys.openai"])
    assert result.exit_code == 0
    # Should show env value (masked)
    assert "sk-...123" in result.stdout
    # Should indicate it's from environment
    assert "env" in result.stdout.lower() or "environment" in result.stdout.lower()


def test_config_dot_notation(cli_runner):
    """Verify dot notation works for nested keys."""
    result = cli_runner.invoke(app, ["config", "set", "search.limit", "20"])
    assert result.exit_code == 0
    result = cli_runner.invoke(app, ["config", "get", "search.limit"])
    assert result.exit_code == 0
    assert "20" in result.stdout


def test_config_list_masks_sensitive(cli_runner):
    """Verify list command masks sensitive values."""
    cli_runner.invoke(app, ["config", "set", "api_keys.openai", "sk-secret123"])
    result = cli_runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    # Should show masked value in list
    assert "sk-...123" in result.stdout
    # Should NOT show full secret
    assert "sk-secret123" not in result.stdout


def test_config_get_nonexistent_key(cli_runner):
    """Verify getting a non-existent key shows helpful message."""
    result = cli_runner.invoke(app, ["config", "get", "nonexistent.key"])
    assert result.exit_code == 0  # Not an error, just not set
    assert "not set" in result.stdout.lower() or "not found" in result.stdout.lower()
