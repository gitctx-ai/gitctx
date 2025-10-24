"""BDD scenarios for progress tracking and cost estimation functionality.

This file specifically tests progress tracking scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/progress_steps.py
"""

import pytest
from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    check_exit_code,
    run_command,
    setup_env_var,
)

# Import all progress tracking step definitions
from tests.e2e.steps.progress_steps import *  # noqa: F403

# Mark all tests in this module with anyio and vcr
# - anyio: Enable event loop for async step functions (indexing pipeline is async)
# - vcr: Record/replay OpenAI API calls via cassettes
pytestmark = [pytest.mark.anyio, pytest.mark.vcr]

# Auto-discover progress tracking scenarios
scenarios("features/progress_tracking.feature")
