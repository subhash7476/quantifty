"""
NiftyShield — Stage-2 PAPER evidence tooling + wiring tests (E007 C/D/E, E7-1, E7-2).

Covers:
- E7-1: fno_runner.build_runner accepts publish_hook_factory /
  publish_checkpoint_time / handler_factory / mode and wires them through.
- E7-2: the DS2-4 journaled publish hook writes a durable FACT_PUBLISH_SKIPPED
  line on a not-ready result, and nothing on a ready result.
- C: the journal-audit tool traces structures to fills/rejections and flags
  reverse divergence.
- D: the risk-metrics report computes RT/win-rate/profit-factor/conversion/guards.
- E: the telemetry archive validates per-session invariants.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, time as dt_time
from pathlib import Path

import pytest

from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.metrics import (
    InMemoryTelemetrySink, RuntimeMetric, NullTelemetrySink,
)

from scripts.nifty_shield_paper.audit import audit_window
from scripts.nifty_shield_paper.metrics_report import risk_metrics_report
from scripts.nifty_shield_paper.telemetry_archive import archive_session
from scripts.nifty_shield_paper.journal_hook import journaled_publish_hook_factory

ROOT = Path(__file__).resolve().parents[2]


def _write_journal(path: Path, events) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _trades_db(path: Path, rows) -> None:
    con = sqlite3.connect(str(path))
    con.execute("""
        CREATE TABLE trades (
            trade_id TEXT, signal_id TEXT, timestamp TEXT, symbol TEXT,
            side TEXT, quantity REAL, entry_price REAL, exit_price REAL,
            pnl REAL, fees REAL, metadata TEXT
        )
    """)
    con.executemany(
        "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


def _margin_event(gid="11111111-2222-3333-4444-555555555555", session="2026-06-05",
                  structure="SPREAD", legs=("NIFTY09JUN2623950CE", "NIFTY09JUN2624100CE"),
                  margin=18000.0, risk_r=15000.0):
    return {
        "timestamp": f"{session} 13:00:00+05:30", "event_type": EventType.ENTRY_MARGIN.value,
        "severity": "INFO", "source_component": "NiftyShieldExecutionHandler",
        "message": "structure margin", "metadata": {
            "group_id": gid, "session": session, "structure": structure,
            "lots": 2, "lot_size": 75, "margin_total": margin,
            "span": 15000.0, "elm": 3000.0, "engine": "NseMarginEngine",
            "leg_symbols": list(legs), "risk_r": risk_r,
        },
    }


def _close_event(gid="11111111-2222-3333-4444-555555555555", session="2026-06-05",
                 reason="time_exit"):
    return {
        "timestamp": f"{session} 15:16:00+05:30",
        "event_type": EventType.STRUCTURE_CLOSE.value,
        "severity": "INFO", "source_component": "NiftyShieldExecutionHandler",
        "message": "structure closed", "metadata": {
            "group_id": gid, "session": session, "reason": reason,
        },
    }


# --------------------------------------------------------------------------- #
# E7-2 — DS2-4 journaled publish hook
# --------------------------------------------------------------------------- #
def test_journaled_hook_records_not_ready(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "j.jsonl"))
    monkeypatch.setattr(
        "scripts.daytype.publish_live_fact.publish_live",
        lambda db_path, today=None: {"ready": False, "reason": "no VIX",
                                     "session": today})
    factory = journaled_publish_hook_factory(journal, str(tmp_path / "f.duckdb"))
    hook = factory(None)
    hook(datetime(2026, 6, 5, 13, 0, 0))
    lines = [json.loads(l) for l in
             open(str(tmp_path / "j.jsonl"), encoding="utf-8")]
    assert any(e["event_type"] == EventType.FACT_PUBLISH_SKIPPED.value
               and e["metadata"]["reason"] == "no VIX" for e in lines)


def test_journaled_hook_silent_on_ready(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "j.jsonl"))
    monkeypatch.setattr(
        "scripts.daytype.publish_live_fact.publish_live",
        lambda db_path, today=None: {"ready": True, "regime": "Choppy",
                                     "session": today})
    factory = journaled_publish_hook_factory(journal, str(tmp_path / "f.duckdb"))
    hook = factory(None)
    hook(datetime(2026, 6, 5, 13, 0, 0))
    jp = tmp_path / "j.jsonl"
    lines = ([json.loads(l) for l in open(str(jp), encoding="utf-8")]
             if jp.exists() else [])
    assert lines == []                        # ready -> no skipped line


# --------------------------------------------------------------------------- #
# C — journal audit
# --------------------------------------------------------------------------- #
def test_audit_traces_entered_and_skipped(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(),
        _close_event(),
        {
            "timestamp": "2026-06-06 13:00:00+05:30",
            "event_type": EventType.ENTRY_SKIPPED.value,
            "severity": "WARNING", "source_component": "NiftyShieldExecutionHandler",
            "message": "skipped", "metadata": {
                "group_id": "aaaaaaaa-0000-0000-0000-000000000000",
                "session": "2026-06-06", "structure": "STRADDLE",
                "reason": "missing option marks",
                "leg_symbols": ["NIFTY09JUN2623950CE"],
            },
        },
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [
        ("t1", "s1", "2026-06-05", "NIFTY09JUN2623950CE", "SELL", 150, 100.0, 0, 0, 0, "{}"),
        ("t2", "s2", "2026-06-05", "NIFTY09JUN2624100CE", "BUY", 150, 20.0, 0, 0, 0, "{}"),
    ])
    report = audit_window(str(journal), str(db))
    assert len(report.structures) == 2
    entered = [s for s in report.structures if s.status == "entered"]
    skipped = [s for s in report.structures if s.status == "skipped"]
    assert len(entered) == 1 and len(skipped) == 1
    assert entered[0].closed and entered[0].exit_reason == "time_exit"
    assert entered[0].filled_legs == ["NIFTY09JUN2623950CE", "NIFTY09JUN2624100CE"]
    assert not report.reverse_divergence
    assert report.one_directional_only


def test_audit_flags_reverse_divergence(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [_margin_event()])
    db = tmp_path / "trades.db"
    _trades_db(db, [
        ("t9", "s9", "2026-06-05", "NIFTY09JUN2699999CE", "SELL", 150, 100.0, 0, 0, 0, "{}"),
    ])                                        # fill with no strategy intent
    report = audit_window(str(journal), str(db))
    assert report.reverse_divergence == ["NIFTY09JUN2699999CE"]
    assert not report.one_directional_only


def test_audit_guard_counters(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(),
        {"timestamp": "t", "event_type": EventType.STRATEGY_ERROR.value,
         "severity": "WARNING", "source_component": "guard", "message": "x",
         "metadata": {}},
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [])
    report = audit_window(str(journal), str(db))
    assert report.guard_events[EventType.STRATEGY_ERROR.value] == 1


# --------------------------------------------------------------------------- #
# D — risk metrics report
# --------------------------------------------------------------------------- #
def test_metrics_report_round_trip_and_winrate(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(),                                  # structure A: win
        _close_event(),
        {
            "timestamp": "2026-06-05 13:00:01+05:30",
            "event_type": EventType.ENTRY_MARGIN.value,
            "severity": "INFO", "source_component": "x", "message": "m",
            "metadata": {
                "group_id": "bbbbbbbb-0000-0000-0000-000000000000",
                "session": "2026-06-05", "structure": "SPREAD",
                "lots": 1, "lot_size": 75, "margin_total": 9000.0,
                "span": None, "elm": None, "engine": "MarginTracker",
                "leg_symbols": ["NIFTY09JUN2624050CE", "NIFTY09JUN2624060CE"],
                "risk_r": 15000.0},
        },
        _close_event(gid="bbbbbbbb-0000-0000-0000-000000000000"),
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [
        # structure A legs: short CE +12000, long CE -3000 -> net +9000 (win)
        ("t1", "s1", "2026-06-05", "NIFTY09JUN2623950CE", "SELL", 150, 100.0, 0, 12000, 0, "{}"),
        ("t2", "s2", "2026-06-05", "NIFTY09JUN2624100CE", "BUY", 150, 20.0, 0, -3000, 0, "{}"),
        # structure B legs: short CE -6000, long CE +1500 -> net -4500 (loss)
        ("t3", "s3", "2026-06-05", "NIFTY09JUN2624050CE", "SELL", 75, 100.0, 0, -6000, 0, "{}"),
        ("t4", "s4", "2026-06-05", "NIFTY09JUN2624060CE", "BUY", 75, 20.0, 0, 1500, 0, "{}"),
    ])
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    assert m.round_trips == 2
    assert m.structures_entered == 2 and m.structures_skipped == 0
    assert m.signal_fill_conversion == 1.0
    assert m.wins == 1 and m.losses == 1
    assert m.win_rate == pytest.approx(0.5)
    assert m.total_realized_pnl == pytest.approx(12000 - 3000 - 6000 + 1500)
    assert m.peak_margin_utilisation > 0.0
    assert m.profit_factor is not None and m.profit_factor > 0


def test_metrics_report_guard_counters(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        {"timestamp": "t", "event_type": EventType.SIGNAL_CONTRACT_REJECTED.value,
         "severity": "WARNING", "source_component": "guard", "message": "x",
         "metadata": {}},
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [])
    m = risk_metrics_report(str(journal), str(db), initial_capital=100_000.0)
    assert m.guard_events[EventType.SIGNAL_CONTRACT_REJECTED.value] == 1


# --------------------------------------------------------------------------- #
# E — telemetry archive
# --------------------------------------------------------------------------- #
def test_telemetry_clean_snapshot():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.BARS_PROCESSED, 361)
    sink.increment(RuntimeMetric.LOOP_ITERATIONS, 361)
    sink.increment(RuntimeMetric.SIGNALS_RECEIVED, 2)
    sink.increment(RuntimeMetric.SIGNALS_ROUTED, 2)
    sink.increment(RuntimeMetric.EXECUTION_CALLS, 1)
    arch = archive_session("2026-06-05", sink.snapshot())
    assert arch.clean


def test_telemetry_flags_guard_counter():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.STRATEGY_QUARANTINE_EVENTS, 1)
    arch = archive_session("2026-06-05", sink.snapshot())
    assert not arch.clean
    assert any("strategy_quarantine_events" in v for v in arch.violations)


def test_telemetry_flags_routing_inconsistency():
    sink = InMemoryTelemetrySink()
    sink.increment(RuntimeMetric.SIGNALS_RECEIVED, 1)
    sink.increment(RuntimeMetric.SIGNALS_ROUTED, 3)     # routed > received
    arch = archive_session("2026-06-05", sink.snapshot())
    assert not arch.clean
    assert any("signals_received" in v for v in arch.violations)


# --------------------------------------------------------------------------- #
# E7-1 — build_runner wiring seams
# --------------------------------------------------------------------------- #
def test_build_runner_accepts_new_seams(tmp_path, monkeypatch):
    import core.execution.handler as handler_mod
    from core.clock import ReplayClock
    from core.database.manager import DatabaseManager
    from core.execution.persistence.execution_store import ExecutionStore
    from core.execution.handler import ExecutionMode
    from core.runtime.config import Mode
    from core.runtime.signal_source import SignalSource
    from core.events import OHLCVBar
    from scripts.fno_runner import build_runner

    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()

    calls = []

    class _Src(SignalSource):
        def on_bar(self, bar: OHLCVBar):
            return []

    clock = ReplayClock(datetime(2026, 6, 5, 9, 15, 0))
    driver = build_runner(
        source=_Src(),
        symbols=["NSE_EQ|INE001A01036"],
        execution_mode=ExecutionMode.PAPER,
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        journal=None,
        max_bars=1,
        publish_hook_factory=lambda exec_: (lambda ts: calls.append(("publish", ts))),
        publish_checkpoint_time=dt_time(13, 0),
        rebalance_hook_factory=lambda exec_: (lambda ts, eh: calls.append(("exit", ts))),
        mode=Mode.REPLAY,
    )
    assert driver._publish_hook is not None
    assert driver._publish_checkpoint_time == dt_time(13, 0)
    assert driver._rebalance_hook is not None
    assert driver.config.is_replay
