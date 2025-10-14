"""Auto-discover and run all BDD scenarios.

This will automatically discover and run all active (non-commented) scenarios
in the features/ directory. Future scenarios are commented out in cli.feature
and will be enabled as commands are implemented.

Note: commit_walker.feature scenarios are in test_commit_walker_features.py
"""

from pytest_bdd import scenarios

# Import all step definitions to register them
from tests.e2e.steps.cli_steps import (  # noqa: F401
    check_exit_code,
    check_exit_code_zero,
    check_output_contains,
    gitctx_installed,
    run_command,
)

# Auto-discover CLI scenarios only (commit_walker has its own test file)
scenarios("features/cli.feature")
