"""Unit tests for clear command."""

import pytest

from gitctx.cli.main import app


def test_clear_command_exists(cli_runner):
    """Verify clear command is registered."""
    result = cli_runner.invoke(app, ["clear", "--help"])
    assert result.exit_code == 0
    assert "Clear" in result.stdout or "cache" in result.stdout.lower()


def test_clear_requires_confirmation(cli_runner):
    """Verify clear asks for confirmation by default."""
    # Send 'n' to decline confirmation
    result = cli_runner.invoke(app, ["clear", "--all"], input="n\n")
    assert result.exit_code == 0
    assert "confirm" in result.stdout.lower() or "sure" in result.stdout.lower()
    # Should be cancelled
    assert "cancelled" in result.stdout.lower() or "aborted" in result.stdout.lower()


def test_clear_force_flag(cli_runner):
    """Verify --force skips confirmation."""
    result = cli_runner.invoke(app, ["clear", "--all", "--force"])
    assert result.exit_code == 0
    # Should not ask for confirmation
    assert "confirm" not in result.stdout.lower()
    assert "cleared" in result.stdout.lower() or "removed" in result.stdout.lower()


def test_clear_database_flag(cli_runner):
    """Verify --database flag clears database only (preserves embeddings)."""
    result = cli_runner.invoke(app, ["clear", "--database", "--force"])
    assert result.exit_code == 0
    assert "database" in result.stdout.lower()
    # Should NOT clear embeddings
    assert "embeddings" not in result.stdout.lower()


def test_clear_embeddings_flag(cli_runner):
    """Verify --embeddings flag clears both embeddings AND database."""
    result = cli_runner.invoke(app, ["clear", "--embeddings", "--force"])
    assert result.exit_code == 0
    # Should clear both embeddings and database
    assert "embeddings" in result.stdout.lower()
    assert "database" in result.stdout.lower()


def test_clear_all_flag(cli_runner):
    """Verify --all flag clears everything."""
    result = cli_runner.invoke(app, ["clear", "--all", "--force"])
    assert result.exit_code == 0
    # Should indicate clearing all
    lines = result.stdout.lower()
    assert "database" in lines
    assert "embeddings" in lines


def test_clear_short_flags(cli_runner):
    """Verify short flags work."""
    result = cli_runner.invoke(app, ["clear", "-a", "-f"])
    assert result.exit_code == 0


def test_clear_multiple_flags(cli_runner):
    """Verify multiple selective flags work together."""
    result = cli_runner.invoke(app, ["clear", "-d", "-e", "-f"])
    assert result.exit_code == 0
    assert "database" in result.stdout.lower()
    assert "embeddings" in result.stdout.lower()


def test_clear_with_confirmation_yes(cli_runner):
    """Verify confirmation works when user says yes."""
    result = cli_runner.invoke(app, ["clear", "--all"], input="y\n")
    assert result.exit_code == 0
    assert "cleared" in result.stdout.lower() or "removed" in result.stdout.lower()


def test_clear_help_text(cli_runner):
    """Verify help text includes all options."""
    result = cli_runner.invoke(app, ["clear", "--help"])
    assert "--force" in result.stdout
    assert "--database" in result.stdout
    assert "--embeddings" in result.stdout
    assert "--all" in result.stdout


def test_clear_embeddings_shows_cost_warning(cli_runner):
    """Verify clearing embeddings shows API cost warning."""
    result = cli_runner.invoke(app, ["clear", "--embeddings"], input="n\n")
    assert result.exit_code == 0
    # Should warn about API costs
    assert "regenerating embeddings" in result.stdout.lower()
    assert "api cost" in result.stdout.lower()


def test_clear_no_flags(cli_runner):
    """Verify running clear without flags shows helpful message."""
    result = cli_runner.invoke(app, ["clear"])
    assert result.exit_code == 0
    # Should show helpful message about what flags to use
    assert "no data specified" in result.stdout.lower()
    assert "--database" in result.stdout.lower() or "--embeddings" in result.stdout.lower()


def test_clear_database_only(cli_runner):
    """Verify clearing database without embeddings."""
    result = cli_runner.invoke(app, ["clear", "--database", "--force"])
    assert result.exit_code == 0
    assert "database" in result.stdout.lower()


def test_clear_embeddings_only(cli_runner):
    """Verify clearing embeddings without database."""
    result = cli_runner.invoke(app, ["clear", "--embeddings", "--force"])
    assert result.exit_code == 0
    assert "embeddings" in result.stdout.lower() or "embedding" in result.stdout.lower()


@pytest.mark.parametrize(
    ("flags", "expected_in_output", "not_expected"),
    [
        (["--database", "--force"], ["database"], ["embedding"]),
        (["--embeddings", "--force"], ["database", "embedding"], []),
        (["--all", "--force"], ["database", "embedding"], []),
        (["--database", "--embeddings", "--force"], ["database", "embedding"], []),
    ],
)
def test_clear_flag_combinations(cli_runner, flags, expected_in_output, not_expected):
    """Test all flag combinations systematically."""
    result = cli_runner.invoke(app, ["clear", *flags])
    assert result.exit_code == 0
    output_lower = result.stdout.lower()
    for text in expected_in_output:
        assert text in output_lower, f"Expected '{text}' in output"
    for text in not_expected:
        assert text not in output_lower, f"Did not expect '{text}' in output"


@pytest.mark.parametrize(
    ("flags", "should_confirm"),
    [
        (["--database"], True),
        (["--embeddings"], True),
        (["--all"], True),
        (["--database", "--force"], False),
        (["--embeddings", "--force"], False),
        (["--all", "--force"], False),
    ],
)
def test_clear_confirmation_flow(cli_runner, flags, should_confirm):
    """Test confirmation flow for different flag combinations."""
    if should_confirm:
        result = cli_runner.invoke(app, ["clear", *flags], input="n\n")
        assert "confirm" in result.stdout.lower() or "sure" in result.stdout.lower()
    else:
        result = cli_runner.invoke(app, ["clear", *flags])
        assert "confirm" not in result.stdout.lower()
    assert result.exit_code == 0
