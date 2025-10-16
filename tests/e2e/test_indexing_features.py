"""E2E tests for indexing features (STORY-0001.2.6)."""

from pytest_bdd import scenarios

# Import shared step definitions
from tests.e2e.steps.cli_steps import (  # noqa: F401
    check_exit_code,
    check_exit_code_zero,
    check_output_contains,
    check_output_not_contains,
    check_stderr_contains,
    check_stderr_not_contains,
    gitctx_installed,
    setup_env_var,
)

# Import indexing-specific step definitions
from tests.e2e.steps.indexing_steps import *  # noqa: F403

# Automatically discover all scenarios in indexing.feature
scenarios("features/indexing.feature")
