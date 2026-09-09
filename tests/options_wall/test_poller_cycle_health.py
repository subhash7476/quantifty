"""The regression bar: replay the outage and see it within one cycle."""
import json

import pytest

from core.data.options_provider import OptionChainRow
from core.options_wall.poller import WallPoller


class _FakeProvider:
    def get_weekly_expiry(self, sym):
        return "2026-08-18"

    def fetch_option_chain(self, sym, expiry):
        return [OptionChainRow(strike=100.0, option_type="CE", instrument_key="NSE_FO|1",
                               tradingsymbol="T1", expiry=expiry, ltp=5.0,
                               underlying_ltp=100.0)]


def test_a_raising_executor_degrades_the_heartbeat_and_scan_persist_still_runs(
        tmp_path, monkeypatch):
    import duckdb
    persisted = []
    monkeypatch.setattr("core.options_wall.poller.UpstoxMarketData",
        lambda: type("M", (), {"fetch_quotes_batch": lambda self, k: {"quotes": {}}})())
    p = WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                   snapshot_db_path=tmp_path / "w.duckdb",
                   results_db_path=tmp_path / "res.duckdb")
    monkeypatch.setattr(p, "_analytics_for", lambda sym, rows, expiry: (object(), 9.0))

    def _boom(name, sym, rows, structural, rv):
        raise duckdb.ConstraintException('Duplicate key "trade_id: 1"')

    monkeypatch.setattr(p, "_executor_step", _boom)
    monkeypatch.setattr(p, "_scan_persist_step",
                        lambda name, sym, rows, structural, rv, quotes:
                        persisted.append(name))
    p._poll_cycle(_FakeProvider())

    hb = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert hb["status"] == "DEGRADED"
    executor = hb["steps"]["NIFTY"]["executor"]
    assert executor["ok"] is False
    assert executor["kind"] == "structural"
    assert executor["error_type"] == "ConstraintException"
    assert hb["steps"]["NIFTY"]["scan_persist"]["ok"] is True
    assert set(persisted) == {"NIFTY", "BANKNIFTY", "SENSEX"}
