"""
NiftyShield — Stage-2 PAPER execution wiring tests (E007 A/B/F, E7-4).

Covers the execution composition the prompt's "the running platform is the test"
presumes but which was never wired into the runtime:
- B: datasheet §9 risk-gate ExecutionConfig.
- E7-4: option-marks feed (Static + ChainSnapshot sources; no synthetic fills).
- Handler entry: a structure's leg set buffers, assembles, fills at REAL marks,
  registers the OrderGroup under the source group_id, tracks positions, journals
  SPAN+ELM margin evidence (F); missing marks -> journaled skip.
- Exit driver (D5): per-bar evaluation against marks; TP / time-exit close.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest
import pytz

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.execution.groups.order_group import OrderGroupType
from core.execution.options.nifty_shield_gates import nifty_shield_execution_config
from core.execution.options.nifty_shield_handler import (
    NiftyShieldExecutionHandler, NiftyShieldExitDriver,
)
from core.execution.options.nifty_shield_marks import (
    ChainSnapshotMarksSource, StaticMarksSource,
)
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.event_journal import EventType, RuntimeEventJournal

from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

FIXED_DT = datetime(2023, 1, 4, 13, 0, 0, tzinfo=pytz.UTC)
GROUP_ID = "11111111-2222-3333-4444-555555555555"
UNDERLYING = "NSE_INDEX|Nifty 50"


def _leg_signal(role: str, ot: str, strike: int, signal_type: SignalType,
                structure: str = "iron_fly", **md_over):
    md = {
        "group_id": GROUP_ID,
        "structure": structure,
        "leg_role": role,
        "strike": strike,
        "expiry": "2023-01-10",
        "option_type": ot,
        "base_lots": 2,
        "regime_mult": 1.0,
        "vix_reduce": False,
        "sl_distance": 100.0,
        "risk_r": 15000.0,
        "exit": {"tp_pct": 0.5, "sl_mult": 2.0, "hard_exit": "15:15",
                 "max_portfolio_delta": 500},
    }
    md.update(md_over)
    return SignalEvent(strategy_id="nifty_shield_v1",
                       symbol="NIFTY10JAN23" + str(strike) + ot,
                       timestamp=FIXED_DT, signal_type=signal_type,
                       confidence=0.9, metadata=md)


def _iron_fly_signals():
    return [
        _leg_signal("short_ce", "CE", 18150, SignalType.SELL),
        _leg_signal("short_pe", "PE", 18150, SignalType.SELL),
        _leg_signal("wing_ce", "CE", 18250, SignalType.BUY),
        _leg_signal("wing_pe", "PE", 18050, SignalType.BUY),
    ]


def _entry_marks():
    return {
        "NIFTY10JAN2318150CE": 100.0,
        "NIFTY10JAN2318150PE": 100.0,
        "NIFTY10JAN2318250CE": 20.0,
        "NIFTY10JAN2318050PE": 20.0,
    }


def _build_handler(tmp_path, monkeypatch, *, marks=None, journal=None,
                   initial_capital=1_000_000.0):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    config = nifty_shield_execution_config(initial_capital=initial_capital)
    dm = DatabaseManager(data_root=tmp_path)
    # Bootstrap the SQLite trade ledger so save_trade persists fills (the
    # audit tool / metrics report read it).
    from core.database.schema import TRADING_TRADES_SCHEMA
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
    return NiftyShieldExecutionHandler(
        db_manager=dm,
        clock=clock,
        broker=PaperBroker(clock),
        config=config,
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
        journal=journal,
        marks_source=StaticMarksSource(marks or _entry_marks()),
        strategy_config=dict(DEFAULT_CONFIG),
    )


# --------------------------------------------------------------------------- #
# B — datasheet §9 gate configuration
# --------------------------------------------------------------------------- #
def test_gates_config_matches_datasheet_9():
    cfg = nifty_shield_execution_config(initial_capital=1_000_000.0)
    assert cfg.max_trades_per_day == 4            # one structure's max legs
    assert cfg.max_drawdown_limit == pytest.approx(30000.0 / 1_000_000.0)
    assert cfg.max_capital_utilisation == pytest.approx(0.25)
    assert cfg.max_portfolio_delta == 500.0       # declared |Δ| flatten gate
    assert cfg.max_position_size == 150.0         # 2 lots x 75
    assert cfg.max_portfolio_vega > 1e9           # undeclared -> effectively off
    assert cfg.max_gamma_exposure > 1e9


# --------------------------------------------------------------------------- #
# E7-4 — option-marks feed
# --------------------------------------------------------------------------- #
def test_static_marks_source_returns_only_present():
    src = StaticMarksSource({"A": 10.0})
    assert src.marks(["A", "B"]) == {"A": 10.0}


def test_chain_snapshot_marks_source_reads_latest(tmp_path):
    import duckdb
    db = tmp_path / "chain.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        CREATE TABLE option_chain_snapshot (
            tradingsymbol VARCHAR, ltp DOUBLE, snapshot_timestamp TIMESTAMP
        )
    """)
    con.executemany(
        "INSERT INTO option_chain_snapshot VALUES (?,?,?)",
        [("NIFTY10JAN2318150CE", 100.0, "2023-01-04 13:00:00"),
         ("NIFTY10JAN2318150CE", 0.0, "2023-01-04 12:00:00"),
         ("OTHER", 5.0, "2023-01-04 13:00:00")],
    )
    con.close()
    src = ChainSnapshotMarksSource(str(db))
    assert src.marks(["NIFTY10JAN2318150CE", "MISSING"]) == {
        "NIFTY10JAN2318150CE": 100.0}


# --------------------------------------------------------------------------- #
# Handler entry assembly
# --------------------------------------------------------------------------- #
def test_entry_assembles_group_fills_at_marks_and_journals_margin(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, journal=journal)

    results = [handler.process_signal(s, 24000.0) for s in _iron_fly_signals()]
    # First three legs buffer; the fourth completes the structure.
    assert results[:3] == [None, None, None]
    assert results[3] is not None

    # All four leg positions open at the real marks.
    for sym, mark in _entry_marks().items():
        pos = handler.position_tracker.get_position(sym)
        assert pos is not None and pos.side.value != "FLAT"
        assert pos.quantity == 150.0            # 2 lots x 75

    # Group registered under the source group_id with the right type.
    group = handler.group_tracker.get_group(__import__("uuid").UUID(GROUP_ID))
    assert group is not None
    assert group.group_type is OrderGroupType.IRON_CONDOR
    assert len(group.legs) == 4

    # Structure credit derived from fills (net premium collected).
    credit = handler.structure_credit(group.group_id)
    assert credit == pytest.approx((100.0 + 100.0 - 20.0 - 20.0) * 150.0)

    # Margin evidence journaled (F).
    events = [json.loads(l) for l in
              open(str(tmp_path / "journal.jsonl"), encoding="utf-8")]
    margin = [e for e in events if e["event_type"] == EventType.ENTRY_MARGIN.value]
    assert margin, "no ENTRY_MARGIN journal line"
    assert margin[0]["metadata"]["group_id"] == GROUP_ID
    assert margin[0]["metadata"]["margin_total"] > 0.0
    assert margin[0]["metadata"]["lots"] == 2


def test_entry_skips_when_marks_missing(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, journal=journal,
                             marks={"NIFTY10JAN2318150CE": 100.0})  # partial
    results = [handler.process_signal(s, 24000.0) for s in _iron_fly_signals()]
    assert results == [None, None, None, None]
    events = [json.loads(l) for l in
              open(str(tmp_path / "journal.jsonl"), encoding="utf-8")]
    skipped = [e for e in events
               if e["event_type"] == EventType.ENTRY_SKIPPED.value]
    assert skipped
    assert "missing option marks" in skipped[0]["metadata"]["reason"]


# --------------------------------------------------------------------------- #
# Exit driver (D5)
# --------------------------------------------------------------------------- #
def _enter_iron_fly(tmp_path, monkeypatch, journal=None):
    handler = _build_handler(tmp_path, monkeypatch, journal=journal)
    for s in _iron_fly_signals():
        handler.process_signal(s, 24000.0)
    return handler


def test_exit_driver_take_profit_closes(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter_iron_fly(tmp_path, monkeypatch, journal=journal)
    # Shorts at 40 (profit 60 each), wings flat -> group P&L = 2 x 60 x 150.
    profit_marks = {
        "NIFTY10JAN2318150CE": 40.0,
        "NIFTY10JAN2318150PE": 40.0,
        "NIFTY10JAN2318250CE": 20.0,
        "NIFTY10JAN2318050PE": 20.0,
    }
    driver = NiftyShieldExitDriver(handler,
                                   StaticMarksSource(profit_marks))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))

    for sym in _entry_marks():
        pos = handler.position_tracker.get_position(sym)
        assert pos.side.value == "FLAT"          # structure closed
    assert handler._closed_groups[GROUP_ID] == "take_profit"


def test_exit_driver_time_exit_at_1515(tmp_path, monkeypatch):
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()))
    # Flat marks -> no TP/SL; at 15:16 the hard time exit fires.
    driver(datetime(2023, 1, 4, 15, 16, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"


def test_exit_driver_holds_before_any_trigger(tmp_path, monkeypatch):
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert not handler._closed_groups          # flat marks, before 15:15
