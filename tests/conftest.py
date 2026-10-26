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


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _redirect_live_stores(tmp_path_factory):
    """Point the stores that default to a path under the repo's data/ at a tmp dir.

    ExecutionConfig.trade_recorder_enabled defaults True and TradeRecorder() defaults
    to the live trade_intelligence.duckdb, so every handler a test built recorded its
    fills there (99% of the 8,704 rows were test fixtures); ExecutionStore() likewise
    defaults to data/execution.db. Redirected, not disabled, so handler tests still
    exercise the recorder. Tests that pass an explicit path are unaffected.
    """
    from core.execution.persistence.execution_store import ExecutionStore
    from core.execution.portfolio import trade_recorder

    root = tmp_path_factory.mktemp("live-store-redirect")
    mp = pytest.MonkeyPatch()
    mp.setattr(trade_recorder, "DEFAULT_DB_PATH", root / "trade_intelligence.duckdb")
    mp.setattr(ExecutionStore.__init__, "__defaults__", (str(root / "execution.db"),))
    yield
    mp.undo()
