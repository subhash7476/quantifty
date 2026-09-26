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
from datetime import datetime, timedelta

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
    ChainSnapshotMarksSource, MarksSourceUnavailable, StaticMarksSource,
)
from core.execution.options.nifty_shield_pricing import sigma_bracket
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.event_journal import EventType, RuntimeEventJournal

from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

FIXED_DT = datetime(2023, 1, 4, 13, 0, 0, tzinfo=pytz.UTC)
GROUP_ID = "11111111-2222-3333-4444-555555555555"
UNDERLYING = "NSE_INDEX|Nifty 50"


def _leg_signal(role: str, ot: str, strike: int, signal_type: SignalType,
                structure: str = "iron_fly", ts: datetime = FIXED_DT,
                **md_over):
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
        "spot": 18150.0,
        "dte": 6,
        "exit": {"bracket_sigma": 1.0, "tp_min_fee_multiple": 3.0,
                 "hard_exit": "15:35", "max_portfolio_delta": 500},
    }
    md.update(md_over)
    return SignalEvent(strategy_id="nifty_shield_v1",
                       symbol="NIFTY10JAN23" + str(strike) + ot,
                       timestamp=ts, signal_type=signal_type,
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
                   initial_capital=1_000_000.0, clock_start: datetime = FIXED_DT):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(clock_start)
    config = nifty_shield_execution_config(initial_capital=initial_capital)
    dm = DatabaseManager(data_root=tmp_path)
    # Bootstrap the SQLite trade ledger so save_trade persists fills (the
    # audit tool / metrics report read it).
    from core.database.schema import TRADING_TRADES_SCHEMA
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
    if marks is None:
        marks = StaticMarksSource(_entry_marks())
    elif not hasattr(marks, "marks"):              # a plain dict -> static source
        marks = StaticMarksSource(marks)
    return NiftyShieldExecutionHandler(
        db_manager=dm,
        clock=clock,
        broker=PaperBroker(clock),
        config=config,
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
        journal=journal,
        marks_source=marks,
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
    assert cfg.max_position_size == 130.0         # 2 lots x 65
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
    src.check_available()                        # valid cache -> no raise
    assert src.marks(["NIFTY10JAN2318150CE", "MISSING"]) == {
        "NIFTY10JAN2318150CE": 100.0}


def test_chain_snapshot_raises_when_cache_unavailable(tmp_path):
    """F3: a missing/corrupt cache is loud (MarksSourceUnavailable), never a
    silent {} that reads as 'market closed'."""
    missing = tmp_path / "nope.duckdb"
    src = ChainSnapshotMarksSource(str(missing))
    with pytest.raises(MarksSourceUnavailable):
        src.check_available()
    with pytest.raises(MarksSourceUnavailable):
        src.marks(["NIFTY10JAN2318150CE"])

    corrupt = tmp_path / "corrupt.duckdb"
    corrupt.write_bytes(b"not a duckdb file at all")
    src2 = ChainSnapshotMarksSource(str(corrupt))
    with pytest.raises(MarksSourceUnavailable):
        src2.marks(["NIFTY10JAN2318150CE"])


def test_chain_snapshot_returns_empty_only_when_valid_but_no_rows(tmp_path):
    """F3: a VALID cache with no snapshot is legitimately 'no marks' -> {} (the
    market-closed path), distinct from an unavailable cache (which raises)."""
    import duckdb
    db = tmp_path / "chain.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        CREATE TABLE option_chain_snapshot (
            tradingsymbol VARCHAR, ltp DOUBLE, snapshot_timestamp TIMESTAMP
        )
    """)
    con.close()
    src = ChainSnapshotMarksSource(str(db))
    src.check_available()                        # valid cache, empty -> ok
    assert src.marks(["NIFTY10JAN2318150CE"]) == {}


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
        assert pos.quantity == 130.0            # 2 lots x 65

    # Group registered under the source group_id with the right type.
    group = handler.group_tracker.get_group(__import__("uuid").UUID(GROUP_ID))
    assert group is not None
    assert group.group_type is OrderGroupType.IRON_CONDOR
    assert len(group.legs) == 4

    # Structure credit derived from fills (net premium collected).
    credit = handler.structure_credit(group.group_id)
    assert credit == pytest.approx((100.0 + 100.0 - 20.0 - 20.0) * 130.0)

    # Margin evidence journaled (F).
    events = [json.loads(l) for l in
              open(str(tmp_path / "journal.jsonl"), encoding="utf-8")]
    margin = [e for e in events if e["event_type"] == EventType.ENTRY_MARGIN.value]
    assert margin, "no ENTRY_MARGIN journal line"
    assert margin[0]["metadata"]["group_id"] == GROUP_ID
    assert margin[0]["metadata"]["margin_total"] > 0.0
    assert margin[0]["metadata"]["lots"] == 2


def test_a_span_snapshot_never_reaches_the_option_margin_backstop(tmp_path, monkeypatch):
    """ADR-025: NseMarginEngine is futures-only — the v400 snapshot carries one
    risk array per underlying ("NIFTY"), and SpanMarginCalculator looks up the
    contract symbol, so every option leg raises MissingRiskArray. Once the SPAN
    archive was backfilled (2026-09-26) a live session would have handed the
    snapshot to the handler and failed every entry. The handler keeps the
    flat-rate backstop it ran on for the whole E008 window."""
    from datetime import date as _date
    from core.risk.span.span_snapshot import SpanRiskArray, SpanSnapshot
    snapshot = SpanSnapshot(
        snapshot_date=_date(2023, 1, 9), schema_version="v400", exchange="NSE",
        segment="FO", file_hash="x", is_settlement=True,
        risk_arrays={"NIFTY": SpanRiskArray(
            symbol="NIFTY", risk_metrics={"scan_risk": 2153.96})},
        metadata={})
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=tmp_path)
    from core.database.schema import TRADING_TRADES_SCHEMA
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = NiftyShieldExecutionHandler(
        db_manager=dm, clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=nifty_shield_execution_config(initial_capital=1_000_000.0),
        metrics_path=str(tmp_path / "metrics.json"), load_db_state=True,
        initial_capital=1_000_000.0, journal=journal,
        marks_source=StaticMarksSource(_entry_marks()),
        strategy_config=dict(DEFAULT_CONFIG), span_snapshot=snapshot)

    assert type(handler.margin_tracker).__name__ != "NseMarginEngine"
    results = [handler.process_signal(s, 24000.0) for s in _iron_fly_signals()]
    assert results[3] is not None


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


class _RaisingMarksSource:
    """F3 fixture: a marks source whose cache is unavailable (loud)."""

    def marks(self, symbols):
        raise MarksSourceUnavailable("chain cache corrupt")


def test_entry_journals_critical_on_marks_outage(tmp_path, monkeypatch):
    """F3: a cache-unavailable marks source at entry is journaled CRITICAL and
    blocks the entry — never a silent 'missing marks' skip."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, journal=journal,
                             marks=_RaisingMarksSource())
    results = [handler.process_signal(s, 24000.0) for s in _iron_fly_signals()]
    assert results == [None, None, None, None]
    events = [json.loads(l) for l in
              open(str(tmp_path / "journal.jsonl"), encoding="utf-8")]
    critical = [e for e in events
                if e["event_type"] == EventType.ENTRY_SKIPPED.value
                and e["severity"] == "CRITICAL"]
    assert critical
    assert "marks source unavailable" in critical[0]["metadata"]["reason"]
    offenders = [s for s in _entry_marks()
                 if handler.position_tracker.get_position(s).side.value != "FLAT"]
    assert not offenders, f"positions opened despite marks outage: {offenders}"


def test_exit_driver_raises_loudly_on_marks_outage(tmp_path, monkeypatch):
    """F3: a mid-window marks outage cannot paper over an unpriced book — the
    exit driver journals CRITICAL and re-raises (the loop stops loudly)."""
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, _RaisingMarksSource())
    with pytest.raises(MarksSourceUnavailable):
        driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))


# --------------------------------------------------------------------------- #
# Exit driver (D5)
# --------------------------------------------------------------------------- #
def _enter_iron_fly(tmp_path, monkeypatch, journal=None):
    handler = _build_handler(tmp_path, monkeypatch, journal=journal)
    for s in _iron_fly_signals():
        handler.process_signal(s, 24000.0)
    return handler


def test_exit_driver_time_exit_at_1535(tmp_path, monkeypatch):
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()))
    # Flat marks -> no TP/SL. 15:16 no longer closes (the old 15:15 exit);
    # 15:36 does.
    driver(datetime(2023, 1, 4, 15, 16, 0, tzinfo=pytz.UTC))
    assert not handler._closed_groups
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"


def test_exit_driver_throttles_idle_invocations(tmp_path, monkeypatch):
    """LIVE drives the hook every 0.5s poll so the book stays managed past the
    underlying's last bar; without a floor that reads the chain cache twice a
    second. The floor must not swallow the eventual evaluation."""
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()),
                                  min_interval_s=3600.0)
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"

    handler2 = _enter_iron_fly(tmp_path / "b", monkeypatch)
    throttled = NiftyShieldExitDriver(handler2, StaticMarksSource(_entry_marks()),
                                      min_interval_s=3600.0)
    throttled(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))   # holds
    throttled(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))   # inside floor
    assert not handler2._closed_groups


def test_exit_driver_unthrottled_by_default(tmp_path, monkeypatch):
    """REPLAY bars arrive in milliseconds of real time; every one must be
    evaluated, so the default floor is zero."""
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"


class _StaleMarks(StaticMarksSource):
    """Static marks that report an age — the shape ChainSnapshotMarksSource has."""

    def __init__(self, marks, age_s):
        super().__init__(marks)
        self._age_s = age_s

    def snapshot_age_s(self, now=None):
        return self._age_s


def test_exit_driver_holds_and_journals_on_stale_marks(tmp_path, monkeypatch):
    """Past the 15:29 auction print no bars arrive, so nothing but the snapshot
    itself says the feed is alive. Deciding TP/SL on a frozen snapshot can fire
    a take-profit at a price that no longer exists; holding cannot."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter_iron_fly(tmp_path, monkeypatch, journal=journal)
    driver = NiftyShieldExitDriver(
        handler, _StaleMarks(_entry_marks(), age_s=300.0), max_marks_age_s=60.0)

    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert not handler._closed_groups          # held, not decided

    events = [json.loads(l) for l in
              (tmp_path / "journal.jsonl").read_text().splitlines() if l.strip()]
    stale = [e for e in events
             if (e.get("metadata") or {}).get("reason") == "option marks stale"]
    assert len(stale) == 1                     # edge-triggered, not per tick
    assert stale[0]["severity"] == "CRITICAL"

    driver(datetime(2023, 1, 4, 15, 37, 0, tzinfo=pytz.UTC))
    events = [json.loads(l) for l in
              (tmp_path / "journal.jsonl").read_text().splitlines() if l.strip()]
    assert len([e for e in events
                if (e.get("metadata") or {}).get("reason") == "option marks stale"]) == 1


def test_exit_driver_decides_on_fresh_marks(tmp_path, monkeypatch):
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(
        handler, _StaleMarks(_entry_marks(), age_s=5.0), max_marks_age_s=60.0)
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"


def test_exit_driver_skips_the_freshness_check_without_a_limit(tmp_path, monkeypatch):
    """REPLAY passes no limit: its snapshots are historical by construction."""
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler,
                                   _StaleMarks(_entry_marks(), age_s=1e6))
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups.get(GROUP_ID) == "time_exit"


def test_exit_updates_entry_keyed_trade_ledger(tmp_path, monkeypatch):
    """2026-08-19 incident: the exit fill id was passed to update_trade_exit
    while the trades table is keyed by the ENTRY fill id, so the exit UPDATE
    matched 0 rows and the ledger kept exit_price=0.0 / pnl=0.0. A closing
    fill must resolve and update its open (entry-keyed) trade row."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter_iron_fly(tmp_path, monkeypatch, journal=journal)

    dm = handler.db_manager
    with dm.trading_reader() as conn:
        before = conn.execute(
            "SELECT trade_id, exit_price, pnl FROM trades ORDER BY symbol"
        ).fetchall()
    assert len(before) == 4
    assert all(r[1] == 0.0 and r[2] == 0.0 for r in before)

    profit_marks = {
        "NIFTY10JAN2318150CE": 40.0,
        "NIFTY10JAN2318150PE": 40.0,
        "NIFTY10JAN2318250CE": 20.0,
        "NIFTY10JAN2318050PE": 20.0,
    }
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(profit_marks))
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))      # hard exit at these marks

    with dm.trading_reader() as conn:
        after = conn.execute(
            "SELECT trade_id, symbol, exit_price, pnl, fees "
            "FROM trades ORDER BY symbol"
        ).fetchall()
    assert len(after) == 4
    # Every leg's exit landed on the SAME (entry-keyed) row it was opened with.
    assert {r[0] for r in before} == {r[0] for r in after}
    for trade_id, symbol, exit_price, pnl, fees in after:
        assert exit_price == pytest.approx(40.0 if "18150" in symbol else 20.0)
        assert fees > 0.0                      # entry + exit fees accumulated
        expected = (100.0 - 40.0) * 130.0 if "18150" in symbol else 0.0
        assert pnl == pytest.approx(expected)


def test_option_legs_are_charged_the_option_fee_schedule(tmp_path, monkeypatch):
    """Finding #2 (NIFTY_SHIELD_REMEDIATION_2026-09-08): legs were charged the
    equity-intraday schedule — STT on every leg at 0.025% of turnover — instead
    of STT on sell-leg premium and stamp duty on buys only."""
    from core.execution.options.fees import option_order_fees

    handler = _enter_iron_fly(tmp_path, monkeypatch)
    with handler.db_manager.trading_reader() as conn:
        rows = conn.execute("SELECT symbol, side, fees FROM trades").fetchall()
    assert len(rows) == 4
    for symbol, side, fees in rows:
        premium = _entry_marks()[symbol]
        expected = option_order_fees(premium=premium, quantity=130, side=side,
                                     trade_date=FIXED_DT.date()).total
        assert fees == pytest.approx(expected), symbol


def test_non_nifty_shield_orders_keep_the_equity_fee_schedule(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    order = type("Order", (), {"strategy_id": "other", "quantity": 10.0})()
    # Rs 5,000 turnover: 20 + 0.1725 exch + 0.005 SEBI + 1.25 STT + 0.15 stamp
    # + 18% GST on (20 + 0.1725 + 0.005).
    assert handler._calculate_fees(order, 500.0) == pytest.approx(25.20945)


def test_exit_driver_holds_before_any_trigger(tmp_path, monkeypatch):
    handler = _enter_iron_fly(tmp_path, monkeypatch)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_entry_marks()))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert not handler._closed_groups          # flat marks, before 15:35


def test_restart_restores_groups_and_exit_driver_closes(tmp_path, monkeypatch):
    """2026-08-20 incident: a restart orphaned the open structure — the
    in-memory OrderGroup registry was lost (orders carried no group_id), so
    the exit driver saw zero open structures and the hard time-exit never
    fired. The group must be rebuilt from restored orders so a fresh handler
    still closes the structure at the hard exit."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter_iron_fly(tmp_path, monkeypatch, journal=journal)
    assert handler.open_nifty_shield_groups()

    restored = _build_handler(tmp_path, monkeypatch, marks=_entry_marks())
    groups = restored.open_nifty_shield_groups()
    assert len(groups) == 1                    # rebuilt from restored orders

    driver = NiftyShieldExitDriver(restored, StaticMarksSource(_entry_marks()))
    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert restored._closed_groups.get(GROUP_ID) == "time_exit"
    for sym in _entry_marks():
        pos = restored.position_tracker.get_position(sym)
        assert pos.side.value == "FLAT"

    # The closing fills updated the ENTRY-keyed ledger rows (defect-1 fix).
    with restored.db_manager.trading_reader() as conn:
        rows = conn.execute(
            "SELECT trade_id, exit_price FROM trades").fetchall()
    assert len(rows) == 4
    assert all(r[1] != 0.0 for r in rows)


def test_restored_closed_group_not_reopened_by_new_structure(tmp_path, monkeypatch):
    """2026-08-21: the restore adds a closed group's EXIT orders to its leg
    set; _group_flat checked positions by symbol, so a NEW structure
    re-entering a shared symbol made the closed group look open and the exit
    driver stop-lossed the new structure's leg (journaled under the old
    group's id). A group whose own legs net to zero is closed regardless of
    the shared position."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    h1 = _enter_iron_fly(tmp_path, monkeypatch, journal=journal)
    driver1 = NiftyShieldExitDriver(h1, StaticMarksSource(_entry_marks()))
    driver1(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))   # time_exit
    assert h1._closed_groups.get(GROUP_ID) == "time_exit"

    restored = _build_handler(tmp_path, monkeypatch, marks=_entry_marks(),
                              clock_start=FIXED_DT + timedelta(days=1))
    assert restored.open_nifty_shield_groups() == []   # rebuilt, closed

    # A NEW structure (next session) re-enters symbols the old group had.
    new_gid = "99999999-0000-0000-0000-000000000000"
    later = FIXED_DT + timedelta(days=1)
    for s in (_leg_signal("short_pe", "PE", 18150, SignalType.SELL,
                          structure="short_straddle", group_id=new_gid, ts=later),
              _leg_signal("short_ce", "CE", 18150, SignalType.SELL,
                          structure="short_straddle", group_id=new_gid, ts=later)):
        restored.process_signal(s, 24000.0)

    open_gids = [str(g) for g in restored.open_nifty_shield_groups()]
    assert open_gids == [new_gid]                # old group stays closed
    driver2 = NiftyShieldExitDriver(restored, StaticMarksSource(_entry_marks()))
    driver2(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    # The old group must not have been closed (again) off the new position.
    assert str(GROUP_ID) not in restored._closed_groups
    for sym in ("NIFTY10JAN2318150PE", "NIFTY10JAN2318150CE"):
        pos = restored.position_tracker.get_position(sym)
        assert pos.side.value == "SHORT"         # the new structure's legs


# --------------------------------------------------------------------------- #
# structure_bracket — the sigma bracket, sized from real fills (restart-safe).
# Bull put spread, 2 lots x 65: SELL 18150PE @ 90, BUY 18000PE @ 35, spot
# 18150, 6 DTE. Group P&L with the wing flat is (90 - short_mark) x 130.
# --------------------------------------------------------------------------- #
_QTY = 130
_BULL_PUT = {"NIFTY10JAN2318150PE": 90.0, "NIFTY10JAN2318000PE": 35.0}


def _bull_put_signals(**md_over):
    return [_leg_signal("short_pe", "PE", 18150, SignalType.SELL,
                        structure="bull_put_spread", **md_over),
            _leg_signal("wing_pe", "PE", 18000, SignalType.BUY,
                        structure="bull_put_spread", **md_over)]


def _enter(tmp_path, monkeypatch, signals, marks, journal=None):
    handler = _build_handler(tmp_path, monkeypatch, marks=marks, journal=journal)
    for s in signals:
        handler.process_signal(s, 24000.0)
    return handler


def _expected_bull_put_bracket():
    from core.execution.options.fees import option_order_fees
    legs = [{"side": "SELL", "strike": 18150.0, "option_type": "PE",
             "price": 90.0, "qty": _QTY},
            {"side": "BUY", "strike": 18000.0, "option_type": "PE",
             "price": 35.0, "qty": _QTY}]
    # every leg is opened on one side and closed on the other
    round_trip = sum(option_order_fees(premium=leg["price"], quantity=_QTY, side=side,
                                       trade_date=FIXED_DT.date()).total
                     for leg in legs for side in ("BUY", "SELL"))
    return sigma_bracket(legs, spot=18150.0, dte_days=6,
                         rate=DEFAULT_CONFIG["risk_free_rate"], sigma_mult=1.0,
                         hold_hours=2.5, session_hours=6.25,
                         fee_floor_rs=3.0 * round_trip)


def _short_mark_for_pnl(pnl_rs: float) -> dict:
    return {**_BULL_PUT, "NIFTY10JAN2318150PE": 90.0 - pnl_rs / _QTY}


def _journal_events(tmp_path):
    return [json.loads(l) for l in
            (tmp_path / "journal.jsonl").read_text().splitlines() if l.strip()]


def test_structure_bracket_is_the_sigma_bracket_of_the_fills(tmp_path, monkeypatch):
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT)
    gid = handler.open_nifty_shield_groups()[0]
    expected = _expected_bull_put_bracket()
    got = handler.structure_bracket(gid)
    assert got.tp_rs == pytest.approx(expected.tp_rs)
    assert got.sl_rs == pytest.approx(expected.sl_rs)
    assert got.fee_floor_rs == pytest.approx(expected.fee_floor_rs)
    assert got.tp_enabled is True


def test_structure_bracket_is_identical_after_restart(tmp_path, monkeypatch):
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT)
    gid = handler.open_nifty_shield_groups()[0]
    before = handler.structure_bracket(gid)

    restored = _build_handler(tmp_path, monkeypatch, marks=_BULL_PUT)
    assert restored.structure_bracket(restored.open_nifty_shield_groups()[0]) == before


def test_exit_driver_take_profit_closes_at_the_bracket_gain(tmp_path, monkeypatch):
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT)
    bracket = handler.structure_bracket(handler.open_nifty_shield_groups()[0])
    driver = NiftyShieldExitDriver(
        handler, StaticMarksSource(_short_mark_for_pnl(bracket.tp_rs + 130.0)))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups[GROUP_ID] == "take_profit"
    for sym in _BULL_PUT:
        assert handler.position_tracker.get_position(sym).side.value == "FLAT"


def test_exit_driver_stop_closes_at_the_bracket_loss(tmp_path, monkeypatch):
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT)
    bracket = handler.structure_bracket(handler.open_nifty_shield_groups()[0])
    driver = NiftyShieldExitDriver(
        handler, StaticMarksSource(_short_mark_for_pnl(-(bracket.sl_rs + 130.0))))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups[GROUP_ID] == "stop_loss"


def test_exit_driver_holds_inside_the_bracket(tmp_path, monkeypatch):
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT)
    bracket = handler.structure_bracket(handler.open_nifty_shield_groups()[0])
    for pnl in (bracket.tp_rs - 130.0, -(bracket.sl_rs - 130.0)):
        driver = NiftyShieldExitDriver(handler, StaticMarksSource(_short_mark_for_pnl(pnl)))
        driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert GROUP_ID not in handler._closed_groups


def test_entry_bracket_is_journaled_once_per_group(tmp_path, monkeypatch):
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(), _BULL_PUT,
                     journal=journal)
    driver = NiftyShieldExitDriver(handler, StaticMarksSource(_BULL_PUT))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    driver(datetime(2023, 1, 4, 13, 31, 0, tzinfo=pytz.UTC))

    brackets = [e for e in _journal_events(tmp_path)
                if e["event_type"] == "ENTRY_BRACKET"]
    assert len(brackets) == 1
    assert brackets[0]["severity"] == "INFO"
    md = brackets[0]["metadata"]
    expected = _expected_bull_put_bracket()
    assert md["group_id"] == GROUP_ID
    assert md["tp_rs"] == pytest.approx(expected.tp_rs, abs=0.01)
    assert md["sl_rs"] == pytest.approx(expected.sl_rs, abs=0.01)
    assert md["tp_enabled"] is True and md["sigma_mult"] == 1.0


def test_unavailable_bracket_journals_critical_and_sets_no_tp_or_stop(tmp_path, monkeypatch):
    """A short put priced below intrinsic at the signal's spot has no implied
    vol, so there is no bracket: no fabricated thresholds, and the clock still
    closes the structure."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _enter(tmp_path, monkeypatch, _bull_put_signals(spot=16000.0),
                     _BULL_PUT, journal=journal)
    gid = handler.open_nifty_shield_groups()[0]
    assert handler.structure_bracket(gid) is None

    driver = NiftyShieldExitDriver(
        handler, StaticMarksSource(_short_mark_for_pnl(-50_000.0)))
    driver(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    assert GROUP_ID not in handler._closed_groups
    critical = [e for e in _journal_events(tmp_path)
                if e["event_type"] == "ENTRY_BRACKET" and e["severity"] == "CRITICAL"]
    assert len(critical) == 1

    driver(datetime(2023, 1, 4, 15, 36, 0, tzinfo=pytz.UTC))
    assert handler._closed_groups[GROUP_ID] == "time_exit"


# --------------------------------------------------------------------------- #
# The PRODUCTION wiring: handler <- RecordingMarksSource <- real source
#
# 2026-09-08: every test above builds the handler on a bare marks source, but a
# recorded LIVE session (the production configuration) wraps it in
# RecordingMarksSource. That wrapper forwarded only marks(), so instrument_keys()
# fell through to an "absent" ABC default and the 13:00 entry skipped with
# "broker basket margin unavailable" for legs whose keys were in the cache. The
# bare-source tests all passed. These exercise the wrapped path.
# --------------------------------------------------------------------------- #

class _KeyedMarks(StaticMarksSource):
    """A marks source that DOES have broker identity and a clock."""

    def __init__(self, marks, keys, age_s=5.0):
        super().__init__(marks)
        self._keys = dict(keys)
        self._age_s = age_s

    def instrument_keys(self, symbols):
        return {s: self._keys[s] for s in symbols if s in self._keys}

    def snapshot_age_s(self, now=None):
        return self._age_s


def _keyed_marks():
    return _KeyedMarks(
        _entry_marks(),
        {sym: f"NSE_FO|{i}" for i, sym in enumerate(_entry_marks(), start=1)})


def _recorded(marks):
    from scripts.nifty_shield_paper.recorder import RecordingMarksSource

    class _Sink:
        def __init__(self): self.calls = []
        def record_marks(self, symbols, result, error):
            self.calls.append((tuple(symbols), error))

    return RecordingMarksSource(marks, _Sink())


def test_recording_wrapper_forwards_the_whole_marks_interface():
    """A decorator that forwards only part of its interface answers for the
    rest. Assert the surface, not one method -- that is what was missed."""
    inner = _keyed_marks()
    wrapped = _recorded(inner)
    syms = list(_entry_marks())
    assert wrapped.marks(syms) == inner.marks(syms)
    assert wrapped.instrument_keys(syms) == inner.instrument_keys(syms)
    assert wrapped.instrument_keys(syms)              # non-empty: the defect
    assert wrapped.snapshot_age_s() == inner.snapshot_age_s()


def test_partial_marks_wrapper_cannot_be_constructed():
    """The ABC's instrument_keys/snapshot_age_s are abstract precisely so a
    partial wrapper fails at construction instead of silently reporting
    'absent' in a live window."""
    from core.execution.options.nifty_shield_marks import OptionMarksSource

    class _Partial(OptionMarksSource):
        def marks(self, symbols):
            return {}

    with pytest.raises(TypeError, match="instrument_keys"):
        _Partial()


def test_broker_margin_entry_through_the_recording_wrapper(tmp_path, monkeypatch):
    """End-to-end on the PRODUCTION wiring: a broker-margin handler behind the
    recorder must resolve keys, size, and enter."""
    import core.execution.options.nifty_shield_sizing as sizing_mod
    seen = {}

    def fake_fetch(legs, product="D"):
        seen["legs"] = list(legs)
        return {"required": 90000.0, "final": 70000.0, "benefit": 20000.0,
                "error": None}

    monkeypatch.setattr("core.brokers.upstox_margin.fetch_basket_margin",
                        fake_fetch)

    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch,
                             marks=_recorded(_keyed_marks()), journal=journal)
    handler._use_broker_margin = True

    for sig in _iron_fly_signals():
        handler.process_signal(sig, 100.0)

    assert handler.open_nifty_shield_groups(), "structure did not enter"
    assert len(seen["legs"]) == 4                 # ONE basket, all four legs
    assert {l["instrument_key"] for l in seen["legs"]} == {
        f"NSE_FO|{i}" for i in range(1, 5)}

    events = [json.loads(l) for l in
              (tmp_path / "journal.jsonl").read_text().splitlines() if l.strip()]
    margin = [e for e in events if e["event_type"] == "ENTRY_MARGIN"]
    assert len(margin) == 1
    assert margin[0]["metadata"]["engine"] == "UpstoxBasketMargin"
    assert margin[0]["metadata"]["margin_total"] == 70000.0   # the FINAL figure
    assert not [e for e in events if e["event_type"] == "ENTRY_SKIPPED"]


def test_bracket_is_sized_through_the_recording_wrapper(tmp_path, monkeypatch):
    """The exit bracket on the PRODUCTION wiring (broker margin behind the
    recorder): every other bracket test uses a bare source, which is how the
    2026-09-08 wiring defect passed."""
    monkeypatch.setattr(
        "core.brokers.upstox_margin.fetch_basket_margin",
        lambda legs, product="D": {"required": 60000.0, "final": 40000.0,
                                   "benefit": 20000.0, "error": None})
    wrapped = _recorded(_KeyedMarks(_BULL_PUT, {"NIFTY10JAN2318150PE": "NSE_FO|1",
                                                "NIFTY10JAN2318000PE": "NSE_FO|2"}))
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch, marks=wrapped, journal=journal)
    handler._use_broker_margin = True
    for sig in _bull_put_signals():
        handler.process_signal(sig, 100.0)

    gid = handler.open_nifty_shield_groups()[0]
    bracket = handler.structure_bracket(gid)
    assert bracket is not None and bracket.tp_enabled

    NiftyShieldExitDriver(handler, wrapped)(datetime(2023, 1, 4, 13, 30, 0, tzinfo=pytz.UTC))
    brackets = [e for e in _journal_events(tmp_path) if e["event_type"] == "ENTRY_BRACKET"]
    assert len(brackets) == 1 and brackets[0]["severity"] == "INFO"


def test_broker_margin_entry_skips_when_the_wrapper_hides_the_keys(tmp_path,
                                                                   monkeypatch):
    """The 2026-09-08 failure, pinned: a source with no keys must skip at
    CRITICAL and never silently size on the local engine."""
    journal = RuntimeEventJournal(str(tmp_path / "journal.jsonl"))
    handler = _build_handler(tmp_path, monkeypatch,
                             marks=StaticMarksSource(_entry_marks()),
                             journal=journal)
    handler._use_broker_margin = True

    for sig in _iron_fly_signals():
        handler.process_signal(sig, 100.0)

    assert not handler.open_nifty_shield_groups()
    events = [json.loads(l) for l in
              (tmp_path / "journal.jsonl").read_text().splitlines() if l.strip()]
    skips = [e for e in events if e["event_type"] == "ENTRY_SKIPPED"]
    assert len(skips) == 1
    assert skips[0]["severity"] == "CRITICAL"
    assert skips[0]["metadata"]["reason"] == "Upstox basket margin unavailable"
    assert not [e for e in events if e["event_type"] == "ENTRY_MARGIN"]
