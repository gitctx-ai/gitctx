"""BDD scenarios for file-grouped result presentation functionality.

This file specifically tests file grouping scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/file_grouping_steps.py
"""

from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    gitctx_installed,
)

# Import all file grouping step definitions
from tests.e2e.steps.file_grouping_steps import *  # noqa: F403

# Auto-discover file grouping scenarios
scenarios("features/file_grouping.feature")
