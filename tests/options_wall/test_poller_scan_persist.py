"""The poll cycle persists scan_results + session_regime (poller = sole writer).

The poller now owns the results DB: each cycle it scans the in-memory chain it
already fetched and writes scan_results + session_regime, throttled below the 5s
executor cadence. These tests drive `_poll_cycle` with a canned structural + a
stub scanner so they assert the persistence wiring, not analytics correctness.
"""
from datetime import datetime

import duckdb

from core.analytics.chain_scanner import ScanResult
from core.analytics.options_analytics import (
    GEXResult, OIAnalysisResult, OptionsStructuralData, PCRResult,
)
from core.data.options_provider import OptionChainRow
from core.options_wall import persistence
from core.options_wall.poller import WallPoller

NIFTY = "NSE_INDEX|Nifty 50"


class _FakeProvider:
    def get_weekly_expiry(self, sym):
        return "2026-09-08"

    def fetch_option_chain(self, sym, expiry):
        rows = []
        for k in (99, 100, 101):
            for t in ("CE", "PE"):
                rows.append(OptionChainRow(
                    strike=float(k), option_type=t, instrument_key=f"{t}{k}",
                    tradingsymbol=f"{t}{k}", expiry=expiry, ltp=1.0, iv=15.0,
                    oi=1000, volume=100, underlying_ltp=100.0))
        return rows


class _FakeMarketData:
    def fetch_quotes_batch(self, keys):
        return {"quotes": {}}


class _StubScanner:
    """Returns one deterministic farm row so scan_results is never empty."""

    def __init__(self, config=None):
        pass

    def scan_chain(self, chain, structural, rv, quotes):
        return [ScanResult(
            underlying="x", expiry="2026-09-08", strike=100.0, option_type="CE",
            screen="farm", structure="iron_fly", regime="Positive GEX (Stable)",
            score=1.0, credit=50.0, iv_minus_rv=3.0, pin_conviction=0.8,
            reason="stub")]


def _structural():
    gex = GEXResult(net_gamma_total=10.0, net_gamma_ce=1.0, net_gamma_pe=1.0,
                    gamma_by_strike={100.0: 10.0, 101.0: 1.0}, zero_gamma_level=None,
                    regime="Positive GEX (Stable)", net_gex_cr=250.0,
                    gex_cr_by_strike={100.0: 230.0, 101.0: 20.0},
                    gamma_ce_by_strike={100.0: 6.0, 101.0: 1.0},
                    gamma_pe_by_strike={100.0: 4.0}, side_coverage=0.9,
                    side_reliable=True)
    return OptionsStructuralData(
        underlying=NIFTY, underlying_ltp=100.0, expiry="2026-09-08",
        timestamp=datetime.now(), pcr=PCRResult(pcr=1.0, total_ce_oi=1, total_pe_oi=1),
        gex=gex, oi_analysis=OIAnalysisResult())


def _make_poller(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setattr("core.options_wall.poller.UpstoxMarketData", _FakeMarketData)
    monkeypatch.setattr("core.options_wall.engine.ChainScanner", _StubScanner)
    p = WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                   snapshot_db_path=tmp_path / "w.duckdb",
                   results_db_path=tmp_path / "res.duckdb", **kwargs)
    # Canned analytics: no market-data / candle-store dependency in the test.
    monkeypatch.setattr(p, "_analytics_for", lambda sym, rows, expiry: (_structural(), 9.0))
    # The executor's own persistence is exercised elsewhere; keep this focused.
    monkeypatch.setattr(p, "_executor_step",
                        lambda name, sym, rows, structural, rv: None)
    return p


def _distinct_scan_ts(db, sym):
    conn = duckdb.connect(str(db), read_only=True)
    try:
        return conn.execute(
            "SELECT count(DISTINCT ts) FROM scan_results WHERE underlying = ?",
            [sym]).fetchone()[0]
    finally:
        conn.close()


def test_poll_cycle_persists_scan_results_and_regime(tmp_path, monkeypatch):
    db = tmp_path / "res.duckdb"
    p = _make_poller(tmp_path, monkeypatch)

    p._poll_cycle(_FakeProvider())

    ts, rows = persistence.latest_scan_results(NIFTY, db_path=db)
    assert ts is not None
    assert len(rows) == 1 and rows[0]["structure"] == "iron_fly"

    river = persistence.regime_river(NIFTY, 1, db_path=db)
    assert len(river) == 1
    assert river[0]["regime"] == "Positive GEX (Stable)"
    assert river[0]["net_gex_cr"] == 250.0


def test_scan_persist_throttled_within_interval(tmp_path, monkeypatch):
    db = tmp_path / "res.duckdb"
    p = _make_poller(tmp_path, monkeypatch, scan_persist_interval_s=30.0)

    p._poll_cycle(_FakeProvider())
    p._poll_cycle(_FakeProvider())

    # Second cycle is inside the throttle window → no new scan_results ts.
    assert _distinct_scan_ts(db, NIFTY) == 1


def test_scan_persist_writes_each_cycle_when_interval_zero(tmp_path, monkeypatch):
    db = tmp_path / "res.duckdb"
    p = _make_poller(tmp_path, monkeypatch, scan_persist_interval_s=0.0)

    p._poll_cycle(_FakeProvider())
    p._poll_cycle(_FakeProvider())

    # Interval 0 disables the throttle → both cycles persist a distinct ts.
    assert _distinct_scan_ts(db, NIFTY) == 2
