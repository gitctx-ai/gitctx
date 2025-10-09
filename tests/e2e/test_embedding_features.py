"""BDD scenarios for OpenAI embedding generation functionality.

This file specifically tests embedding scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/test_embedding.py
"""

from pytest_bdd import scenarios

# Import all necessary step definitions and fixtures
from tests.e2e.steps.cli_steps import (  # noqa: F401
    context,
    gitctx_installed,
)

# Import all embedding step definitions
from tests.e2e.steps.test_embedding import *  # noqa: F401, F403

# Auto-discover embedding scenarios
scenarios("features/embedding.feature")
