"""Root conftest.py for platform-specific pytest configuration."""

import sys
from pathlib import Path


def pytest_configure(config):
    """Configure pytest based on platform.

    On Windows, set a short basetemp path to avoid MAX_PATH (260 char) issues.
    This affects both CI and local development on Windows.
    """
    # Only set basetemp if not already specified by user
    if sys.platform == "win32" and not config.option.basetemp:
        # Use C:\t for short paths on Windows (avoids 260 char MAX_PATH limit)
        # Note: pytest expects a string, not a Path object
        basetemp_str = "C:\\t"
        Path(basetemp_str).mkdir(exist_ok=True)
        config.option.basetemp = basetemp_str
