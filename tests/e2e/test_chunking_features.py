"""BDD scenarios for blob content chunking functionality.

This file specifically tests chunking scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/test_chunking.py
"""

from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    gitctx_installed,
)

# Import all chunking step definitions
from tests.e2e.steps.test_chunking import *  # noqa: F403

# Auto-discover chunking scenarios
scenarios("features/chunking.feature")
