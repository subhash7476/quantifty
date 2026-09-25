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
    # F2: R is normalized by the pinned declared risk_r (Rs) — computed, not 0.
    assert m.r_normalized_structures == 2
    assert m.avg_win_r == pytest.approx(9000.0 / 15000.0)
    assert m.avg_loss_r == pytest.approx(-4500.0 / 15000.0)
    assert m.peak_margin_utilisation > 0.0
    assert m.profit_factor is not None and m.profit_factor > 0


def test_metrics_r_is_vacuous_not_zero_when_risk_r_missing(tmp_path):
    """F2: a structure whose risk_r is absent (a source/regression defect) must
    surface the R columns as vacuous (None), never silently compute 0.0."""
    journal = tmp_path / "j.jsonl"
    event = _margin_event()
    event["metadata"]["risk_r"] = None
    _write_journal(journal, [event, _close_event()])
    db = tmp_path / "trades.db"
    _trades_db(db, [
        ("t1", "s1", "2026-06-05", "NIFTY09JUN2623950CE", "SELL", 150, 100.0, 0, 12000, 0, "{}"),
        ("t2", "s2", "2026-06-05", "NIFTY09JUN2624100CE", "BUY", 150, 20.0, 0, -3000, 0, "{}"),
    ])
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    assert m.round_trips == 1
    assert m.avg_win_r is None                 # vacuous surfaced, not 0.0
    assert m.r_normalized_structures == 0
    assert m.per_structure[0]["r"] is None


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


def test_metrics_session_scopes_leg_pnl(tmp_path):
    """2026-08-21: a symbol traded by two structures (24250PE in both the
    08-20 orphan and the 08-21 straddle) must not leak its rows into both
    structures' PnL — per-structure sums are scoped to the structure's
    session."""
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(session="2026-06-05", legs=("A", "B")),
        _close_event(),
        _margin_event(gid="bbbbbbbb-0000-0000-0000-000000000000",
                      session="2026-06-06", legs=("A", "C")),   # re-uses A
        _close_event(gid="bbbbbbbb-0000-0000-0000-000000000000"),
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [
        ("t1", "s1", "2026-06-05", "A", "SELL", 75, 100.0, 0, 1000, 0, "{}"),
        ("t2", "s2", "2026-06-05", "B", "BUY", 75, 20.0, 0, -500, 0, "{}"),
        ("t3", "s3", "2026-06-06", "A", "SELL", 75, 90.0, 0, -200, 0, "{}"),
        ("t4", "s4", "2026-06-06", "C", "BUY", 75, 15.0, 0, 400, 0, "{}"),
    ])
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    by_gid = {p["group_id"]: p for p in m.per_structure}
    assert by_gid["11111111-2222-3333-4444-555555555555"]["pnl_rs"] == 500.0
    assert by_gid["bbbbbbbb-0000-0000-0000-000000000000"]["pnl_rs"] == 200.0
    assert m.total_realized_pnl == pytest.approx(700.0)


def _three_structure_book(tmp_path):
    """A +150 gross / 105 fee trade, a -450 gross / 125 fee trade and a
    +600 gross / 115 fee trade, in that order (2026-09-25 audit shape)."""
    gids = ("11111111-2222-3333-4444-555555555555",
            "bbbbbbbb-0000-0000-0000-000000000000",
            "cccccccc-0000-0000-0000-000000000000")
    sessions = ("2026-06-05", "2026-06-06", "2026-06-08")
    events = []
    for gid, session in zip(gids, sessions):
        events += [_margin_event(gid=gid, session=session, legs=(f"S{session}", f"L{session}")),
                   _close_event(gid=gid, session=session)]
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, events)
    db = tmp_path / "trades.db"
    rows = []
    for i, (session, (gross_s, gross_l, fee_s, fee_l)) in enumerate(zip(sessions, (
            (200.0, -50.0, 55.0, 50.0),
            (-400.0, -50.0, 65.0, 60.0),
            (500.0, 100.0, 60.0, 55.0)))):
        rows += [(f"t{i}s", f"s{i}s", session, f"S{session}", "SELL", 65, 100.0, 0, gross_s, fee_s, "{}"),
                 (f"t{i}l", f"s{i}l", session, f"L{session}", "BUY", 65, 20.0, 0, gross_l, fee_l, "{}")]
    _trades_db(db, rows)
    return journal, db, gids


def test_metrics_report_pnl_is_net_of_fees(tmp_path):
    """2026-09-25 audit F1: the ledger's fees were read but never subtracted, so
    the window printed +Rs 846 for a book that was -Rs 1,641 after fees."""
    journal, db, gids = _three_structure_book(tmp_path)
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    by_gid = {p["group_id"]: p for p in m.per_structure}
    assert by_gid[gids[0]]["gross_pnl_rs"] == pytest.approx(150.0)
    assert by_gid[gids[0]]["fees_rs"] == pytest.approx(105.0)
    assert by_gid[gids[0]]["pnl_rs"] == pytest.approx(45.0)
    assert m.total_gross_pnl == pytest.approx(300.0)
    assert m.total_fees == pytest.approx(345.0)
    assert m.total_realized_pnl == pytest.approx(-45.0)


def test_metrics_report_scores_wins_and_profit_factor_net(tmp_path):
    """A trade that is gross-positive but fee-negative is a loss."""
    journal, db, gids = _three_structure_book(tmp_path)
    # the first trade's short leg: gross +150 -> +100, net -5
    con = sqlite3.connect(str(db))
    con.execute("UPDATE trades SET pnl = 150.0 WHERE trade_id = 't0s'")
    con.commit()
    con.close()
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    assert m.wins == 1 and m.losses == 2
    assert m.profit_factor == pytest.approx(485.0 / (5.0 + 575.0))
    assert m.avg_win_r == pytest.approx(485.0 / 15000.0, abs=1e-3)   # r is stored at 3 dp


def test_metrics_report_drawdown_from_net_equity_curve(tmp_path):
    """Drawdown comes from the net per-structure equity curve, not the runtime
    metrics.json (a startup snapshot that read 0.0 across 18 closed trades)."""
    journal, db, _ = _three_structure_book(tmp_path)
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    # net curve: +45 -> -530 -> -45; peak 1,000,045, trough 999,470
    assert m.max_drawdown_rs == pytest.approx(575.0)
    assert m.max_drawdown_pct == pytest.approx(575.0 / 1_000_045.0)


def test_metrics_report_serializes_cleanly(tmp_path):
    """2026-08-19 incident: dataclasses.asdict() on a Counter (Python 3.13
    rebuilds dict subclasses via `type(obj)((k, v) for k, v in obj.items())`,
    so the Counter constructor counts each (key, value) TUPLE as an element and
    the report gains tuple keys) made json.dumps raise "keys must be str ...
    not tuple" and abort finalize_session_evidence. The counters must be plain
    dicts with str keys so the report always serializes."""
    import dataclasses
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(),
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
        {"timestamp": "t", "event_type": EventType.SIGNAL_CONTRACT_REJECTED.value,
         "severity": "WARNING", "source_component": "guard", "message": "x",
         "metadata": {}},
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [])
    m = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    d = dataclasses.asdict(m)
    assert isinstance(d["rejections_by_reason"], dict)
    assert d["rejections_by_reason"] == {"missing option marks": 1}
    assert isinstance(d["guard_events"], dict)
    assert d["guard_events"] == {EventType.SIGNAL_CONTRACT_REJECTED.value: 1}
    json.dumps(d, indent=2, default=str)       # must never raise


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


# --------------------------------------------------------------------------- #
# C2 — a session-level journal line must not take the window page down.
# 2026-09-07: the SPAN-downgrade notice was journalled as ENTRY_MARGIN, an event
# whose consumers index metadata["group_id"]. audit_window raised KeyError and
# /api/window 500'd. Producing an event is not the same as it being readable.
# --------------------------------------------------------------------------- #
def test_audit_skips_entry_margin_rows_without_a_group(tmp_path):
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [
        _margin_event(),
        {   # session-level line: no structure, therefore no group_id
            "timestamp": "2026-09-07 13:00:00+05:30",
            "event_type": EventType.ENTRY_MARGIN.value,
            "severity": "CRITICAL", "source_component": "nifty_shield_paper_runner",
            "message": "SPAN snapshot unavailable",
            "metadata": {"expected_span_date": "2026-09-07", "engine": "MarginTracker"},
        },
    ])
    db = tmp_path / "trades.db"
    _trades_db(db, [])
    report = audit_window(str(journal), str(db))
    assert len(report.structures) == 1          # the real entry, not the notice
    assert report.structures[0].status == "entered"


def test_span_downgrade_notice_is_readable_by_the_audit(tmp_path, monkeypatch):
    """Producer -> consumer contract: what the runner writes, the audit reads."""
    import scripts.nifty_shield_paper_runner as runner_mod
    journal_path = tmp_path / "j.jsonl"
    journal = RuntimeEventJournal(str(journal_path))
    monkeypatch.setattr(runner_mod.SpanRepository, "load",
                        lambda self, d: (_ for _ in ()).throw(
                            FileNotFoundError("no SPAN snapshot")))

    assert runner_mod._load_span_snapshot(journal) is None
    lines = [json.loads(l) for l in open(str(journal_path), encoding="utf-8")]
    notice = [e for e in lines if e["severity"] == "CRITICAL"]
    assert len(notice) == 1
    assert notice[0]["metadata"]["engine"] == "MarginTracker"

    db = tmp_path / "trades.db"
    _trades_db(db, [])
    report = audit_window(str(journal_path), str(db))   # must not raise
    assert report.structures == []


_SESSION_LEVEL_MARGIN_LINE = {
    "timestamp": "2026-09-07 13:00:00+05:30",
    "event_type": EventType.ENTRY_MARGIN.value,
    "severity": "CRITICAL", "source_component": "nifty_shield_paper_runner",
    "message": "SPAN snapshot unavailable",
    "metadata": {"expected_span_date": "2026-09-07", "engine": "MarginTracker"},
}


def test_metrics_report_does_not_count_a_session_level_margin_line(tmp_path):
    """It also inflated structures_entered, not just raised."""
    from scripts.nifty_shield_paper.metrics_report import risk_metrics_report
    journal = tmp_path / "j.jsonl"
    _write_journal(journal, [_margin_event(), _SESSION_LEVEL_MARGIN_LINE])
    db = tmp_path / "trades.db"
    _trades_db(db, [])
    rep = risk_metrics_report(str(journal), str(db), initial_capital=1_000_000.0)
    assert rep.structures_entered == 1
    assert len(rep.per_structure) == 1


def test_recover_session_ignores_a_session_level_margin_line(tmp_path):
    """The backfill maps leg symbols -> group_id; a groupless line must not raise."""
    import sqlite3
    from scripts.nifty_shield_paper.recover_session import _backfill_group_ids
    line = dict(_SESSION_LEVEL_MARGIN_LINE)
    line["metadata"] = {**line["metadata"], "session": "2026-06-05"}
    _write_journal(tmp_path / "journal.jsonl", [_margin_event(), line])
    con = sqlite3.connect(tmp_path / "execution.db")
    con.execute("CREATE TABLE orders (correlation_id TEXT, symbol TEXT, "
                "group_id TEXT, strategy_id TEXT, timestamp TEXT)")
    con.commit()
    con.close()
    out = _backfill_group_ids(tmp_path, "2026-06-05")     # must not raise
    assert isinstance(out, list)
