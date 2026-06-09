"""
MM.4 — LoopDriver instrument-master readiness gate.

Validates MASTER_MATERIALIZATION_POLICY.md §4/§5 and the owner decisions:
- the check runs only on LIVE + derivative universe, AFTER RECOVERY_COMPLETED and
  BEFORE reconciliation (identity must be trustworthy before positions are matched
  through it — Decision 2);
- BLOCK refuses to start (STOPPED + INSTRUMENT_MASTER_UNAVAILABLE/CRITICAL + critical
  alert), mirroring RECONCILIATION_FAIL; reconciliation never runs;
- WARN starts normally + INSTRUMENT_MASTER_STALE/WARNING journal + warning alert;
- equity-only LIVE and REPLAY bypass the check (no behavior change);
- the gate evaluates only — it is handed a verdict, it never resolves a master.
"""

import json
from datetime import date

import pytest

from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.instruments.master_readiness import ReadinessState, ReadinessVerdict

from _doubles import (FakeClock, FakeExecutionHandler, FakeMarketDataProvider,
                      FakeSignalSource, bar_series)

_DERIV = "NSE_FO|53001"
_EQ = "NSE_EQ|INE002A01018"

_FRESH = ReadinessVerdict(ReadinessState.FRESH, None, date(2026, 6, 8), date(2026, 6, 8))
_WARN = ReadinessVerdict(ReadinessState.WARN, None, date(2026, 6, 5), date(2026, 6, 8))
_BLOCK = ReadinessVerdict(ReadinessState.BLOCK, "coverage", date(2026, 6, 8), date(2026, 6, 8))


class _RecordingAlerter:
    def __init__(self):
        self.calls = []

    def info(self, m): self.calls.append(("info", m))
    def warning(self, m): self.calls.append(("warning", m))
    def critical(self, m): self.calls.append(("critical", m))

    @property
    def levels(self):
        return [lvl for lvl, _ in self.calls]


@pytest.fixture
def alerts(monkeypatch):
    """Patch the driver's alerter so tests assert alerting without Telegram I/O."""
    rec = _RecordingAlerter()
    monkeypatch.setattr("core.runtime.driver.alerter", rec)
    return rec


def _cfg(symbols, mode=Mode.LIVE, max_bars=2):
    return DriverConfig(mode=mode, symbols=list(symbols), max_bars=max_bars,
                        poll_interval_s=0.25)


def _driver(cfg, readiness, tmp_path, symbol=_DERIV, source=None):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    return LoopDriver(
        cfg, clock=FakeClock(),
        provider=FakeMarketDataProvider({symbol: bar_series(symbol, 3)}, live=cfg.is_live),
        journal=journal, execution=handler, source=source,
        master_readiness=readiness,
    ), handler


def _events(tmp_path):
    return [json.loads(l)["event_type"]
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


def _records(tmp_path):
    return [json.loads(l)
            for l in (tmp_path / "runtime_events.jsonl").read_text().splitlines()]


# --------------------------------------------------------------------------- #
# 9. LIVE + derivative + FRESH → RUNNING, no master event, no alert
# --------------------------------------------------------------------------- #
def test_live_derivative_fresh_starts_clean(tmp_path, alerts):
    d, _ = _driver(_cfg([_DERIV]), lambda: _FRESH, tmp_path)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    assert "INSTRUMENT_MASTER_STALE" not in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    assert alerts.calls == []


# --------------------------------------------------------------------------- #
# 10. LIVE + derivative + WARN → RUNNING + STALE journal + warning alert
# --------------------------------------------------------------------------- #
def test_live_derivative_warn_starts_with_journal_and_alert(tmp_path, alerts):
    d, handler = _driver(_cfg([_DERIV]), lambda: _WARN, tmp_path)
    d.run()
    recs = _records(tmp_path)
    ev = [r["event_type"] for r in recs]
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    stale = next(r for r in recs if r["event_type"] == "INSTRUMENT_MASTER_STALE")
    assert stale["severity"] == "WARNING"
    assert alerts.levels == ["warning"]
    # WARN does not suppress reconciliation — it still runs after.
    assert "RECONCILIATION_PASS" in ev


# --------------------------------------------------------------------------- #
# 11 + 17. LIVE + derivative + BLOCK → refuse to start
# --------------------------------------------------------------------------- #
def test_live_derivative_block_refuses_to_start(tmp_path, alerts):
    source = FakeSignalSource()
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(_cfg([_DERIV]), clock=FakeClock(),
                   provider=FakeMarketDataProvider({_DERIV: bar_series(_DERIV, 3)}, live=True),
                   journal=journal, execution=handler, source=source,
                   master_readiness=lambda: _BLOCK)
    d.run()
    recs = _records(tmp_path)
    ev = [r["event_type"] for r in recs]
    assert d.state is RuntimeState.STOPPED
    assert d.bars_processed == 0                     # loop never ran
    assert "RUNNING" not in ev
    block = next(r for r in recs if r["event_type"] == "INSTRUMENT_MASTER_UNAVAILABLE")
    assert block["severity"] == "CRITICAL"
    assert block["metadata"]["reason"] == "coverage"
    assert alerts.levels == ["critical"]
    assert source.started == 0 and source.stopped == 0   # source untouched


# --------------------------------------------------------------------------- #
# 12. Ordering: RECOVERY_COMPLETED < master event < RECONCILIATION < RUNNING
# --------------------------------------------------------------------------- #
def test_master_check_runs_before_reconciliation(tmp_path, alerts):
    d, _ = _driver(_cfg([_DERIV]), lambda: _WARN, tmp_path)
    d.run()
    ev = _events(tmp_path)
    for earlier, later in [("RECOVERY_COMPLETED", "INSTRUMENT_MASTER_STALE"),
                           ("INSTRUMENT_MASTER_STALE", "RECONCILIATION_PASS"),
                           ("RECONCILIATION_PASS", "RUNNING")]:
        assert ev.index(earlier) < ev.index(later)


# --------------------------------------------------------------------------- #
# 13. BLOCK aborts BEFORE reconciliation — reconcile never called
# --------------------------------------------------------------------------- #
def test_block_aborts_before_reconciliation(tmp_path, alerts):
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(_cfg([_DERIV]), clock=FakeClock(),
                   provider=FakeMarketDataProvider({_DERIV: bar_series(_DERIV, 3)}, live=True),
                   journal=journal, execution=handler,
                   broker_positions=lambda: [{"symbol": "x"}],
                   master_readiness=lambda: _BLOCK)
    d.run()
    ev = _events(tmp_path)
    assert handler.reconciliation.reconcile_calls == []     # never reached
    assert "RECONCILIATION_PASS" not in ev
    assert "RECONCILIATION_FAIL" not in ev


# --------------------------------------------------------------------------- #
# 14. LIVE + equity-only → check skipped (no behavior change), even on BLOCK
# --------------------------------------------------------------------------- #
def test_equity_only_live_bypasses_check(tmp_path, alerts):
    d, _ = _driver(_cfg([_EQ]), lambda: _BLOCK, tmp_path, symbol=_EQ)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    assert alerts.calls == []


# --------------------------------------------------------------------------- #
# 15. REPLAY + derivative → check skipped (staleness is a live concept)
# --------------------------------------------------------------------------- #
def test_replay_bypasses_check(tmp_path, alerts):
    cfg = DriverConfig(mode=Mode.REPLAY, symbols=[_DERIV], max_bars=2)
    journal = RuntimeEventJournal(path=str(tmp_path / "runtime_events.jsonl"))
    handler = FakeExecutionHandler(reconcile_alerts=[])
    d = LoopDriver(cfg, clock=FakeClock(),
                   provider=FakeMarketDataProvider({_DERIV: bar_series(_DERIV, 3)}),
                   journal=journal, execution=handler,
                   master_readiness=lambda: _BLOCK)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    assert alerts.calls == []


# --------------------------------------------------------------------------- #
# Vacuous: LIVE + derivative but no checker injected → no check (mirrors the
# vacuous-reconciliation contract; live F&O wiring is deferred)
# --------------------------------------------------------------------------- #
def test_live_derivative_without_checker_is_vacuous_pass(tmp_path, alerts):
    d, _ = _driver(_cfg([_DERIV]), None, tmp_path)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev


# --------------------------------------------------------------------------- #
# MM.7. Production wiring: the REAL resolver-backed factory (not a hand-written
# verdict) drives the gate end-to-end — resolver → checker → startup gate.
# --------------------------------------------------------------------------- #
def test_live_derivative_real_factory_checker_starts_fresh(tmp_path, alerts):
    from scripts.fetch_instrument_master import parse_instruments, write_snapshot
    from core.instruments.master_readiness import build_master_readiness
    from core.instruments.master_freshness import expected_snapshot_date
    from core.database.utils.market_hours import MarketHours

    today = expected_snapshot_date(MarketHours.get_ist_now()).isoformat()
    master = tmp_path / "instruments.duckdb"
    write_snapshot(parse_instruments([
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001", "tradingsymbol": "NIFTYFUT",
         "name": "NIFTY", "expiry": "2027-12-31", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 0.05},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710", "tradingsymbol": "NIFTYCE",
         "name": "NIFTY", "expiry": "2027-12-31", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 0.05},
    ], today), db_path=master)

    checker = build_master_readiness(["NIFTY"], db_path=master)
    d, _ = _driver(_cfg([_DERIV]), checker, tmp_path)
    d.run()
    ev = _events(tmp_path)
    assert d.state is RuntimeState.STOPPED and d.bars_processed == 2
    assert "RUNNING" in ev
    assert "INSTRUMENT_MASTER_UNAVAILABLE" not in ev
    assert "INSTRUMENT_MASTER_STALE" not in ev
    assert alerts.calls == []
