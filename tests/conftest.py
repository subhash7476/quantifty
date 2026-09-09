"""Session-wide isolation from the operator's live surfaces.

`setup_logger` runs at module import time, so the log redirect must take effect
before any test module imports a production module. conftest.py top-level code
runs during collection, which is early enough; an autouse fixture is not.

The Telegram credentials are stripped for the same reason: a structural step
failure alerts by design, so any test that drives one through the poller would
otherwise send a live message on the ops machine, where the token is set. A
per-test fixture is the wrong control for that — it only protects the tests
that remember it.
"""

import os
import tempfile
from pathlib import Path

_TEST_LOGS = Path(tempfile.gettempdir()) / "nifty-test-logs"
_TEST_LOGS.mkdir(parents=True, exist_ok=True)
os.environ["NIFTY_LOG_DIR"] = str(_TEST_LOGS)

os.environ.pop("TELEGRAM_TOKEN", None)
os.environ.pop("TELEGRAM_CHAT_ID", None)
