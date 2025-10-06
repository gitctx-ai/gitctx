"""Unit tests for tips system."""

from gitctx.cli.tips import show_tip


def test_show_tip_with_undefined_command(capsys):
    """Should gracefully handle commands with no tip defined."""
    # Call with a command that has no tip defined
    show_tip("nonexistent_command")
    captured = capsys.readouterr()
    # Should not crash - graceful return with no output
    assert captured.out == ""


def test_show_tip_with_valid_command(capsys):
    """Should display tip for commands that have tips defined."""
    # "config" has a tip defined in TIPS dictionary
    show_tip("config")
    captured = capsys.readouterr()
    # Should show tip content
    assert "Tip" in captured.out or "tip" in captured.out.lower()
