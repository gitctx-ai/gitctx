"""BDD scenarios for LanceDB vector storage functionality.

This file specifically tests LanceDB storage scenarios using pytest-bdd.
Step definitions are in tests/e2e/steps/lancedb_storage_steps.py
"""

from pytest_bdd import scenarios

# Import all lancedb storage step definitions
from tests.e2e.steps.lancedb_storage_steps import *  # noqa: F403

# Auto-discover lancedb storage scenarios
scenarios("features/lancedb_storage.feature")
