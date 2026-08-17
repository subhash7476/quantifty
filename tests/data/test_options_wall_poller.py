"""Tests for the Options-Wall chain poller's one-cycle fetch+append.

The poller is the sole writer of the snapshot store; this pins that a cycle
appends both indices and writes a heartbeat, using a stubbed provider and a temp
store (no network, no token).
"""
from pathlib import Path

from core.data import options_wall_store as store
from core.data.options_provider import OptionChainRow
from core.options_wall.poller import WallPoller


class _FakeProvider:
    def __init__(self, rows_by_sym):
        self._rows = rows_by_sym

    def get_weekly_expiry(self, sym):
        return "2026-08-18"

    def fetch_option_chain(self, sym, expiry):
        return self._rows.get(sym, [])


def _row(strike, otype):
    return OptionChainRow(
        strike=strike, option_type=otype, instrument_key=f"K{strike}{otype}",
        tradingsymbol=f"K{strike}{otype}", expiry="2026-08-18", ltp=5.0,
    )


def test_poll_cycle_appends_and_heartbeats(tmp_path):
    db = tmp_path / "wall.duckdb"
    heartbeat = tmp_path / "heartbeat.json"
    pid = tmp_path / "poller.pid"
    rows = [_row(100.0, "CE"), _row(100.0, "PE")]
    provider = _FakeProvider({
        "NSE_INDEX|Nifty 50": rows,
        "NSE_INDEX|Nifty Bank": rows,
    })

    poller = WallPoller(heartbeat_path=heartbeat, pid_path=pid, snapshot_db_path=db)
    poller._poll_cycle(provider)

    assert len(store.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)) == 2
    assert len(store.latest_snapshot("NSE_INDEX|Nifty Bank", "2026-08-18", db_path=db)) == 2
    assert heartbeat.exists()
