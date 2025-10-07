"""BDD scenarios for commit walker functionality.

This file specifically tests commit walker scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/commit_walker_steps.py
"""

from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    context,
    gitctx_installed,
)

# Import all commit walker step definitions
from tests.e2e.steps.commit_walker_steps import *  # noqa: F401, F403

# Auto-discover commit walker scenarios
scenarios("features/commit_walker.feature")
