"""BDD scenarios for query embedding and semantic search functionality.

This file tests query embedding generation, caching, and validation using pytest-bdd.
Step definitions are in tests/e2e/steps/search_steps.py
"""

import pytest
from pytest_bdd import scenarios

# Import common step definitions
from tests.e2e.steps.cli_steps import (  # noqa: F401
    gitctx_installed,
)

# Import all search step definitions (will be created in Phase 3)
from tests.e2e.steps.search_steps import *  # noqa: F403

# Import formatting step definitions (STORY-0001.3.3)
from tests.e2e.steps.test_formatting_steps import *  # noqa: F403

# Mark all tests in this module with anyio and vcr
# - anyio: Enable event loop for async operations
# - vcr: Record/replay OpenAI API calls via cassettes
pytestmark = [pytest.mark.anyio, pytest.mark.vcr]

# Auto-discover search scenarios
scenarios("features/search.feature")
