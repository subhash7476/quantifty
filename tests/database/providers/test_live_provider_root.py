"""Regression: the live market-data provider must read the ingestor's live
buffer (platform data root), not the session's evidence root.

The NiftyShield session builds one process-wide `DatabaseManager` rooted at its
evidence dir (`data/nifty_shield`, needed for the trade ledger). The live buffer
is a platform-global store the ingestor writes under the default `data` root.
Because `DatabaseManager` is a singleton, the provider inherited the session's
root and read `data/nifty_shield/live_buffer/` — which never exists — so the
driver processed 0 bars and the 13:00 fact never fired. The fix decouples the
live-buffer root from `data_root` via `set_live_buffer_root`.
"""
import duckdb
import pytest
from datetime import datetime
from pathlib import Path

from core.database.manager import DatabaseManager
from core.database.providers.live_market import LiveDuckDBMarketDataProvider
from core.database.schema import MARKET_CANDLES_SCHEMA

SYM = "NSE_INDEX|Nifty 50"


def _write_candles(platform_root: Path, rows):
    """Write candles straight to <platform_root>/live_buffer (as the ingestor
    would), independent of the manager under test."""
    buf = platform_root / "live_buffer"
    buf.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(buf / "candles_today.duckdb"))
    con.execute(MARKET_CANDLES_SCHEMA)
    for ts, price in rows:
        con.execute(
            "INSERT INTO candles (symbol, instrument_key, timeframe, timestamp, "
            "open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?,?)",
            [SYM, SYM, "1m", ts, price, price, price, price, 0],
        )
    con.close()


@pytest.fixture(autouse=True)
def _reset_singleton():
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


def test_live_buffer_root_defaults_to_data_root(tmp_path):
    """No behavior change by default: existing callers keep data_root-relative
    live buffers (the ingestor-test contract)."""
    db = DatabaseManager(tmp_path / "data" / "nifty_shield")
    assert db.live_buffer_root == db.data_root


def test_provider_reads_platform_buffer_when_root_set(tmp_path):
    """The fix: a session-rooted manager pointed at the platform live-buffer
    root delivers the ingestor's bars to the provider."""
    platform = (tmp_path / "data").resolve()
    _write_candles(platform, [
        (datetime(2026, 8, 11, 9, 15), 100.0),
        (datetime(2026, 8, 11, 9, 16), 101.0),
    ])

    db = DatabaseManager(tmp_path / "data" / "nifty_shield")
    db.set_live_buffer_root(platform)
    provider = LiveDuckDBMarketDataProvider([SYM], db)

    latest = provider.get_latest_bar(SYM)
    assert latest is not None
    assert latest.close == 101.0
    # _initialize_symbols seeds off the platform buffer, so a newer bar flows.
    _write_candles(platform, [(datetime(2026, 8, 11, 9, 17), 102.0)])
    nxt = provider.get_next_bar(SYM)
    assert nxt is not None and nxt.close == 102.0


def test_provider_reads_nothing_without_root_override(tmp_path):
    """Reproduces the 0-bars defect: manager rooted at the session evidence dir,
    live buffer written at the platform root -> provider sees nothing."""
    platform = (tmp_path / "data").resolve()
    _write_candles(platform, [(datetime(2026, 8, 11, 9, 15), 100.0)])

    db = DatabaseManager(tmp_path / "data" / "nifty_shield")  # no override
    provider = LiveDuckDBMarketDataProvider([SYM], db)

    assert provider.get_latest_bar(SYM) is None
