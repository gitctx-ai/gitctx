"""BDD scenarios for HEAD boosting functionality.

This file tests HEAD code boosting over historical versions using pytest-bdd.
Step definitions are in tests/e2e/steps/head_boosting_steps.py

Scenarios for HEAD boosting are implemented and tested using pytest-bdd.
"""

import pytest
from pytest_bdd import scenarios

# Import common step definitions
from tests.e2e.steps.cli_steps import (  # noqa: F401
    gitctx_installed,
)

# Import head boosting step definitions
from tests.e2e.steps.head_boosting_steps import *  # noqa: F403

# Import common fixtures (e2e_indexed_repo_factory, etc.)
from tests.e2e.steps.indexing_steps import *  # noqa: F403

# Mark all tests in this module with anyio and vcr
# - anyio: Enable event loop for async operations
# - vcr: Record/replay OpenAI API calls via cassettes
pytestmark = [pytest.mark.anyio, pytest.mark.vcr]

# Auto-discover head boosting scenarios
scenarios("features/head_boosting.feature")
