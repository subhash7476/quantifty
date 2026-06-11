"""
Gate G1 — Wave 3A restore characterization suite.

Pins the CURRENT (defective) restore reality identified by
docs/reports/G1_WAVE3_RESTORE_REVIEW.md BEFORE any Wave 3 migration, the same
discipline F-PARSE-1 received on the forward path (Wave 2A). NO production code
is changed by this suite; the defect assertions below are INTENTIONAL.

The restore path under characterization (file:line, verified):

  ExecutionHandler.__init__(load_db_state=True)        handler.py:186-187
    -> _replay_state()                                 handler.py:219
         orders = order_repo.get_all()                 handler.py:224
           -> InstrumentParser.parse(row[1])           order_repository.py:60   (site #8)
         fills  = fill_repo.get_all()                  handler.py:231
           -> position_tracker.update_from_fill(fill)  handler.py:234
                -> get_position(symbol) -> parse       position_tracker.py:31   (site #7)

  InstrumentParser.parse (instrument_parser.py:8-46) has only an Option regex +
  an Equity fallback — no Future branch — and hardcodes Option lot_size=1
  (instrument_parser.py:39). Only the display `symbol` survives persistence
  (execution_store.py:24-63), so ALL structural identity is re-derived from it.

Pinned defects (DO NOT "fix" these assertions — they are the red->green
tripwires for the Wave 3 Option-B post-gate canonicalization pass):

  H1 — a futures order built FUTURE on the forward path (Wave 2 #1) restores
       as EQUITY (restore never saw the Wave 2 fix).
  H2 — an option order built with master-resolved lot_size=65 on the forward
       path (#4 selector) restores with the parser's hardcoded lot_size=1.
  H3 — reconciliation keys on the raw symbol string, never on instrument_type
       / canonical identity / instrument_key.
  H6 — the `positions` snapshot table is write-only on restore: positions are
       rebuilt exclusively by replaying fills (position_repository.load_all has
       no caller repo-wide).

Fixture pattern mirrors tests/execution/test_g1_characterization.py: a REAL
ExecutionHandler wired to a spy PaperBroker over an ISOLATED tmp ExecutionStore
+ DatabaseManager(data_root=tmp).
"""
import sqlite3
from datetime import datetime

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import OrderSide, OrderType
from core.instruments.instrument_base import InstrumentType
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
FUTURES_SYMBOL = "NIFTY26JUNFUT"
OPTION_UNDERLYING = "NSE_INDEX|Nifty 50"
OPTION_PRICE = 22500.0

# Observed forward-path option payload (same literals as the Wave 2A suite):
# symbol is pure date/strike math; lot 65 is the master-resolved value present
# in this environment (F4 — unverified against the exchange, pinned as-is).
EXPECTED_OPTION_SYMBOL = "NIFTY16JUN2622500CE"
FORWARD_OPTION_LOT = 65
# What InstrumentParser.parse hardcodes on restore (instrument_parser.py:39).
RESTORED_OPTION_LOT = 1


class SpyPaperBroker(PaperBroker):
    def __init__(self, clock):
        super().__init__(clock)
        self.received = []

    def place_order(self, order):
        self.received.append(order)
        return super().place_order(order)


def _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore", lambda *a, **k: ExecutionStore(str(store_path))
    )
    clock = ReplayClock(FIXED_DT)
    broker = SpyPaperBroker(clock)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=broker,
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=load_db_state,
    )
    return handler, broker


def _signal(symbol, quantity, metadata=None):
    meta = {
        "quantity": quantity,
        "sl_distance": 5.0,
        "risk_r": 1.0,
        "signal_id": f"sig-restore-{symbol}-{quantity}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1restore",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=1.0,
        metadata=meta,
    )


def _persist_future(tmp_path, monkeypatch, store_path):
    """Handler A: build + persist a futures order (forward path, Wave 2 #1)."""
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path)
    order = handler_a.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)
    assert order is not None
    return order


def _persist_option(tmp_path, monkeypatch, store_path):
    """Handler A: build + persist an option order (forward path, #4 selector)."""
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path)
    sig = _signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"})
    order = handler_a.process_signal(sig, current_price=OPTION_PRICE)
    assert order is not None
    return order


# --------------------------------------------------------------------------- #
# Group A — Future restore (H1: forward FUTURE, restored EQUITY)
# --------------------------------------------------------------------------- #

def test_restore_future_order_reverts_to_equity(tmp_path, monkeypatch):
    """H1 pinned: the same futures order is FUTURE fresh and EQUITY restored.

    The EQUITY assertion is INTENTIONAL — it characterizes the current defect
    (order_repository.py:60 re-parses the symbol; parse has no Future branch).
    The Wave 3 post-gate canonicalization pass flips it; until then this is the
    tripwire that proves the asymmetry exists.
    """
    store_path = tmp_path / "execution.db"
    order = _persist_future(tmp_path, monkeypatch, store_path)

    # Forward reality (Wave 2 #1): freshly built order is FUTURE.
    assert order.symbol == FUTURES_SYMBOL
    assert order.instrument_type == InstrumentType.FUTURE

    # Restart: handler B restores from the same ledger.
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)
    restored = {str(o.correlation_id): o for o in handler_b.order_repo.get_all()}
    ro = restored[str(order.correlation_id)]

    # Symbol (the sole persisted identity) is preserved byte-for-byte.
    assert ro.symbol == FUTURES_SYMBOL
    # CURRENT DEFECT (H1): restore re-parses -> Equity. Do not "correct" this.
    assert ro.instrument_type == InstrumentType.EQUITY
    # Non-identity payload fields survive unchanged.
    assert ro.side == OrderSide.BUY
    assert ro.quantity == 50
    assert ro.order_type == OrderType.MARKET
    assert ro.signal_id == f"sig-restore-{FUTURES_SYMBOL}-50"


def test_restore_future_position_rebuilt_as_equity(tmp_path, monkeypatch):
    """Restored futures position identity is EQUITY-typed at construction (Option B).

    Note (updated for Wave 4B #7): the FORWARD position is now canonical-derived
    FUTURE (the live fill seam, handler.py:_handle_broker_fill). The RESTORED
    position still rebuilds EQUITY at construction (restore replays via the
    untouched update_from_fill — Option B / ADR-003); its FUTURE upgrade is the
    separate post-gate canonicalize_restored_positions pass (not run here). So the
    H1 asymmetry now lives between forward (FUTURE) and restore-at-construction
    (EQUITY) until the post-gate pass runs — exactly the restart parity Wave 4B P5
    pins once the pass is applied.
    """
    store_path = tmp_path / "execution.db"
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path)
    handler_a.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    # Forward position: canonical-derived FUTURE at the fill seam (Wave 4B #7).
    fwd_pos = handler_a.position_tracker.get_all_positions()[FUTURES_SYMBOL]
    assert fwd_pos.instrument.type == InstrumentType.FUTURE

    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)
    pos = handler_b.position_tracker.get_all_positions()[FUTURES_SYMBOL]
    assert pos.symbol == FUTURES_SYMBOL
    assert pos.instrument.type == InstrumentType.EQUITY   # restore-at-construction stays legacy (Option B)
    assert handler_b.position_tracker.net_quantity(FUTURES_SYMBOL) == 50.0


# --------------------------------------------------------------------------- #
# Group B — Option restore (H2: forward lot 65, restored lot 1)
# --------------------------------------------------------------------------- #

def test_restore_option_order_lot_drifts_to_one(tmp_path, monkeypatch):
    """H2 pinned: forward option lot == 65, restored option lot == 1.

    The lot==1 assertion is INTENTIONAL — instrument_parser.py:39 hardcodes
    Option(lot_size=1, multiplier=1.0) and restore re-parses the symbol. Any
    sizing/greeks/margin keyed off instrument.lot_size diverges 65x across a
    restart. Do not "correct" this here.
    """
    store_path = tmp_path / "execution.db"
    order = _persist_option(tmp_path, monkeypatch, store_path)

    # Forward reality (#4 selector): master-resolved lot 65 (F4 value, observed).
    assert order.symbol == EXPECTED_OPTION_SYMBOL
    assert order.instrument.lot_size == FORWARD_OPTION_LOT
    assert order.instrument_type == InstrumentType.OPTION

    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)
    restored = {str(o.correlation_id): o for o in handler_b.order_repo.get_all()}
    ro = restored[str(order.correlation_id)]

    # Symbol preserved byte-for-byte; type survives via the Option regex.
    assert ro.symbol == EXPECTED_OPTION_SYMBOL
    assert ro.instrument_type == InstrumentType.OPTION
    # CURRENT DEFECT (H2): the restored instrument carries the parser's
    # hardcoded lot, not the forward selector's master-resolved lot.
    assert ro.instrument.lot_size == RESTORED_OPTION_LOT
    assert ro.instrument.multiplier == 1.0
    # Order quantity (persisted as an absolute number) is unaffected by the drift.
    assert ro.quantity == 75
    assert ro.side == OrderSide.BUY


def test_restore_option_position_lot_is_one(tmp_path, monkeypatch):
    """Restored option position instrument carries lot_size=1 at construction (Option B).

    Note (updated for Wave 4B #7): the FORWARD position instrument now carries the
    master lot (65) — canonical-derived at the live fill seam. The RESTORED position
    still rebuilds lot 1 at construction (restore replays via the untouched
    update_from_fill — Option B / ADR-003); its lot-65 upgrade is the separate
    post-gate canonicalize_restored_positions pass (not run here). The forward/restore
    lot drift now lives between forward (65) and restore-at-construction (1) until the
    post-gate pass runs.
    """
    store_path = tmp_path / "execution.db"
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path)
    sig = _signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"})
    handler_a.process_signal(sig, current_price=OPTION_PRICE)

    fwd_pos = handler_a.position_tracker.get_all_positions()[EXPECTED_OPTION_SYMBOL]
    assert fwd_pos.instrument.lot_size == FORWARD_OPTION_LOT   # 65: canonical-derived (Wave 4B #7)

    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)
    pos = handler_b.position_tracker.get_all_positions()[EXPECTED_OPTION_SYMBOL]
    assert pos.symbol == EXPECTED_OPTION_SYMBOL
    assert pos.instrument.type == InstrumentType.OPTION
    assert pos.instrument.lot_size == RESTORED_OPTION_LOT
    assert handler_b.position_tracker.net_quantity(EXPECTED_OPTION_SYMBOL) == 75.0


# --------------------------------------------------------------------------- #
# Persistence evidence — only `symbol` survives; snapshot table is dead on restore
# --------------------------------------------------------------------------- #

def test_ledger_schema_persists_only_symbol_identity(tmp_path, monkeypatch):
    """Pins WHY restore must re-parse: no structural identity column exists.

    If a migration ever adds instrument_type/expiry/strike/lot_size/
    instrument_key to the ledger, this goes red — a deliberate schema tripwire
    (persistence changes are a 4C.7-adjacent decision, not a G1 side effect).
    """
    store_path = tmp_path / "execution.db"
    _persist_future(tmp_path, monkeypatch, store_path)

    conn = sqlite3.connect(str(store_path))
    try:
        cols = {
            table: {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for table in ("orders", "fills", "positions")
        }
    finally:
        conn.close()

    assert cols["orders"] == {
        "correlation_id", "symbol", "side", "quantity", "order_type",
        "strategy_id", "signal_id", "timestamp", "metadata",
    }
    assert cols["fills"] == {
        "fill_id", "order_id", "symbol", "quantity", "price", "side",
        "fee", "timestamp",
    }
    assert cols["positions"] == {"symbol", "side", "quantity", "avg_price", "timestamp"}

    structural = {"instrument_type", "expiry", "strike", "option_type",
                  "lot_size", "multiplier", "instrument_key"}
    for table, names in cols.items():
        assert not (names & structural), f"{table} grew a structural identity column"


def test_restore_ignores_positions_snapshot_table(tmp_path, monkeypatch):
    """H6 pinned: positions are rebuilt from fill replay, never from the
    `positions` snapshot table (position_repository.load_all has no caller).

    A corrupted snapshot row is invisible to restore — proof the table is
    write-only. Wiring load_all into restore would create a second position
    truth source (ADR-001 violation); this test documents it stays dead.
    """
    store_path = tmp_path / "execution.db"
    _persist_future(tmp_path, monkeypatch, store_path)

    conn = sqlite3.connect(str(store_path))
    try:
        # Snapshot row exists (written on the live fill)...
        snap = conn.execute(
            "SELECT quantity FROM positions WHERE symbol = ?", (FUTURES_SYMBOL,)
        ).fetchone()
        assert snap is not None and snap[0] == 50.0
        # ...corrupt it.
        conn.execute(
            "UPDATE positions SET quantity = 999 WHERE symbol = ?", (FUTURES_SYMBOL,)
        )
        conn.commit()
    finally:
        conn.close()

    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)
    # Restore reflects the FILLS (50), not the corrupted snapshot (999).
    assert handler_b.position_tracker.net_quantity(FUTURES_SYMBOL) == 50.0


# --------------------------------------------------------------------------- #
# Group C — Reconciliation safety (H3: keys on symbol string only)
# --------------------------------------------------------------------------- #

def test_reconciliation_matches_restored_future_by_symbol_string(tmp_path, monkeypatch):
    """A restored futures position (mistyped EQUITY) still reconciles PASS
    against a broker book keyed on the same symbol string — the broker fixture
    carries NO instrument_type/identity field, so the H1 mistype is invisible
    to reconciliation. That is the safety property Wave 3 must preserve.
    """
    store_path = tmp_path / "execution.db"
    _persist_future(tmp_path, monkeypatch, store_path)
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)

    # Restored identity is the H1 mistype...
    pos = handler_b.position_tracker.get_all_positions()[FUTURES_SYMBOL]
    assert pos.instrument.type == InstrumentType.EQUITY
    # ...and reconciliation matches on the symbol string regardless.
    matching = [{"symbol": FUTURES_SYMBOL, "quantity": 50, "side": "LONG"}]
    assert handler_b.reconciliation.reconcile(matching) == []

    divergent = [{"symbol": FUTURES_SYMBOL, "quantity": 10, "side": "LONG"}]
    alerts = handler_b.reconciliation.reconcile(divergent)
    assert len(alerts) == 1
    assert alerts[0].issue == "QUANTITY_MISMATCH"
    assert alerts[0].symbol == FUTURES_SYMBOL


def test_reconciliation_matches_restored_option_by_symbol_string(tmp_path, monkeypatch):
    """The H2 lot drift (restored lot=1) does not affect reconciliation:
    matching consults net_quantity (raw fill units) and the symbol string only —
    instrument.lot_size is never read by the engine.
    """
    store_path = tmp_path / "execution.db"
    _persist_option(tmp_path, monkeypatch, store_path)
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)

    pos = handler_b.position_tracker.get_all_positions()[EXPECTED_OPTION_SYMBOL]
    assert pos.instrument.lot_size == RESTORED_OPTION_LOT   # drift present...
    matching = [{"symbol": EXPECTED_OPTION_SYMBOL, "quantity": 75, "side": "LONG"}]
    assert handler_b.reconciliation.reconcile(matching) == []   # ...and irrelevant


def test_reconciliation_keys_on_raw_symbol_not_canonical_identity(tmp_path, monkeypatch):
    """H3 pinned: matching is raw-string equality on `symbol`
    (reconciliation.py:54,57 — broker_map keys and _positions keys), NOT
    instrument_type / canonical identity / instrument_key. A broker book
    emitting the same instrument under a different symbol format fails to
    match on both sides. The Wave 3 pass must therefore preserve `.symbol`
    byte-for-byte; canonicalization does not by itself fix this.
    """
    store_path = tmp_path / "execution.db"
    _persist_future(tmp_path, monkeypatch, store_path)
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path)

    # Same instrument, broker-formatted symbol (e.g. canonical instrument_key
    # style) -> no match: internal side mismatches AND broker side orphans.
    broker_book = [{"symbol": "NSE_FO|NIFTY26JUNFUT", "quantity": 50, "side": "LONG"}]
    alerts = handler_b.reconciliation.reconcile(broker_book)
    issues = {(a.issue, a.symbol) for a in alerts}
    assert ("QUANTITY_MISMATCH", FUTURES_SYMBOL) in issues
    assert ("ORPHANED_BROKER_POSITION", "NSE_FO|NIFTY26JUNFUT") in issues
    assert len(alerts) == 2
