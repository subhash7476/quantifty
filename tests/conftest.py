"""Redirect logging away from `logs/` for the whole test session.

`setup_logger` runs at module import time, so this must take effect before any
test module imports a production module. conftest.py top-level code runs during
collection, which is early enough; an autouse fixture is not.
"""

import os
import tempfile
from pathlib import Path

_TEST_LOGS = Path(tempfile.gettempdir()) / "nifty-test-logs"
_TEST_LOGS.mkdir(parents=True, exist_ok=True)
os.environ["NIFTY_LOG_DIR"] = str(_TEST_LOGS)
