"""Enable coverage for subprocesses.

This file is automatically imported by Python when it starts.
It enables coverage collection for subprocess calls in E2E tests.
"""

import os

# Only start coverage if we're in a test subprocess
if "COV_CORE_SOURCE" in os.environ or "COVERAGE_PROCESS_START" in os.environ:
    try:
        import coverage

        coverage.process_startup()
    except ImportError:
        pass
