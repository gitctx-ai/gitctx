"""BDD scenarios for hybrid search functionality.

This file tests hybrid search combining BM25 keyword and vector semantic search
using pytest-bdd. Step definitions are in tests/e2e/steps/hybrid_search_steps.py
"""

import pytest
from pytest_bdd import scenarios

# Import common step definitions
from tests.e2e.steps.cli_steps import (  # noqa: F401
    gitctx_installed,
)

# Import hybrid search step definitions
from tests.e2e.steps.hybrid_search_steps import *  # noqa: F403

# Import common fixtures (e2e_indexed_repo_factory, etc.)
from tests.e2e.steps.indexing_steps import *  # noqa: F403

# Mark all tests in this module with anyio and vcr
# - anyio: Enable event loop for async operations
# - vcr: Record/replay OpenAI API calls via cassettes
pytestmark = [pytest.mark.anyio, pytest.mark.vcr]

# Auto-discover hybrid search scenarios
scenarios("features/hybrid_search.feature")
