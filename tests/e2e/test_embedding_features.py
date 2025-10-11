"""BDD scenarios for OpenAI embedding generation functionality.

This file specifically tests embedding scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/test_embedding.py
"""

import pytest
from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    context,
    gitctx_installed,
)

# Import all embedding step definitions
from tests.e2e.steps.test_embedding import *  # noqa: F401, F403

# Mark all tests in this module with anyio to enable event loop
# This allows step functions to use anyio.from_thread.run() to call async code
pytestmark = pytest.mark.anyio

# Auto-discover embedding scenarios
scenarios("features/embedding.feature")
