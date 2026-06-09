"""
Gate G1 — Section 4 characterization suite (Wave 2A).

Pins the CURRENT behavior of the live, *exercisable* order path before any
identity-site migration (#1/#2/#4). Per G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md:

  - No production code wires a real ExecutionHandler to any broker.
  - UpstoxAdapter.place_order is unexercised AND incompatible with NormalizedOrder
    (reads order.signal_id_reference -> AttributeError; enum-vs-str side -> always SELL).
  - The only broker that accepts the handler's NormalizedOrder output is PaperBroker.

So these tests construct a REAL ExecutionHandler wired to a spy PaperBroker over an
ISOLATED tmp ExecutionStore + DatabaseManager(data_root=tmp), and pin the four
golden paths against the PaperBroker + NormalizedOrder contract:

  1. Build order   — process_signal (equity/non-option parse branch #1 + option-via-selector #4)
                     -> assert NormalizedOrder (symbol, side, quantity, order_type) AND the
                        order the broker received, byte-for-byte (values are OBSERVED, derived
                        from the same selector/parser the handler uses — not idealized).
  2. Persist       — order + fill rows written to the tmp SQLite ledger.
  3. Restore       — second handler with load_db_state=True over the same ledger -> round-trip.
  4. Reconcile     — restored ledger vs broker-position fixture -> verdict (PASS + mismatch).

Plus an isolation guard: the real data/execution.db is never touched.

These assert the broker-facing payload explicitly: the G1/4C.7 tripwire. If a payload
byte changes during the #1/#2/#4 migration, one of these goes red.

NOTE: changes ZERO production code. The always-SELL / signal_id_reference defects on the
Upstox side are documented findings (F-UPX-1/2), not fixed here.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

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
EQUITY_SYMBOL = "RELIANCE"
FUTURES_SYMBOL = "NIFTY26JUNFUT"
OPTION_UNDERLYING = "NSE_INDEX|Nifty 50"
OPTION_PRICE = 22500.0

# Observed, master-resolved option payload for OPTION_UNDERLYING @ OPTION_PRICE on
# FIXED_DT (2026-06-09). The symbol is pure date/strike math (master-independent);
# lot_size is resolved through the present instrument master (F4 materialization,
# 75->65). If the master is absent, the selector falls back to INDEX_LOT_SIZES (75) —
# a red test then is a *meaningful* divergence, not a flake. These are hardcoded
# literals (not a re-call of select()) so the test is a genuine byte-for-byte tripwire:
# Wave 2 #4 edits select() in place, and a self-referential assertion would move in
# lockstep and never catch a payload change.
EXPECTED_OPTION_SYMBOL = "NIFTY16JUN2622500CE"
EXPECTED_OPTION_LOT = 65


class SpyPaperBroker(PaperBroker):
    """PaperBroker that records exactly what object the handler hands to place_order."""

    def __init__(self, clock):
        super().__init__(clock)
        self.received = []

    def place_order(self, order):
        self.received.append(order)
        return super().place_order(order)


def _build_handler(tmp_path, monkeypatch, store_path, load_db_state):
    """Construct a REAL ExecutionHandler over an isolated tmp store + db_manager."""
    # Redirect the internally-constructed ExecutionStore (handler.py:145, default
    # data/execution.db) to the tmp ledger. Bound name is core.execution.handler.ExecutionStore.
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
        "signal_id": f"sig-{symbol}-{quantity}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1char",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=1.0,
        metadata=meta,
    )


# --------------------------------------------------------------------------- #
# Test 1 — Build order
# --------------------------------------------------------------------------- #

def test_build_order_equity_non_option_branch(tmp_path, monkeypatch):
    """#1/#2 territory: non-option signal -> InstrumentParser.parse build path."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    order = handler.process_signal(_signal(EQUITY_SYMBOL, 50), current_price=2500.0)

    assert order is not None
    assert order.symbol == "RELIANCE"           # literal: parse is identity passthrough for equity
    assert order.instrument_type == InstrumentType.EQUITY
    assert order.side == OrderSide.BUY
    assert order.quantity == 50
    assert order.order_type == OrderType.MARKET

    # Broker-facing payload (PaperBroker contract): same object, same identity field.
    assert len(broker.received) == 1
    sent = broker.received[0]
    assert sent is order
    assert sent.symbol == "RELIANCE"
    assert sent.side.value == "BUY"
    assert sent.quantity == 50


def test_build_order_futures_currently_falls_back_to_equity(tmp_path, monkeypatch):
    """#1 migration target — the highest-value tripwire (post-migration).

    Name retained from Wave 2A (the named artifact the migration was expected to
    flip). Before #1, InstrumentParser.parse had only an Option regex + Equity
    fallback, so a futures-style symbol was mistyped as **Equity**. Wave 2 #1
    routes the non-option branch through `resolve_future -> CanonicalInstrument ->
    derive Future`, so the type is now **FUTURE** — while `symbol` stays
    byte-identical (the broker payload is preserved; the G1/4C.7 boundary holds).
    The instrument_type assertion is the corrected expectation; every symbol/side/
    quantity/order_type assertion is unchanged from the pinned reality.
    """
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    order = handler.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    assert order is not None
    assert order.symbol == FUTURES_SYMBOL                     # payload identity — preserved across #1
    assert order.instrument_type == InstrumentType.FUTURE     # #1: resolve_future -> derive Future
    assert order.side == OrderSide.BUY
    assert order.quantity == 50
    assert order.order_type == OrderType.MARKET

    assert len(broker.received) == 1
    assert broker.received[0].symbol == FUTURES_SYMBOL


def test_build_order_option_via_selector_branch(tmp_path, monkeypatch):
    """#4 territory: execution_mode=option -> OptionsContractSelector synthesis."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    sig = _signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"})
    order = handler.process_signal(sig, current_price=OPTION_PRICE)

    # Hardcoded literals (see module header): genuine byte-for-byte tripwire. Wave 2 #4
    # edits select() in place — a re-call of select() would move in lockstep and never
    # catch a payload change, so we pin the observed bytes instead.
    assert order is not None
    assert order.symbol == EXPECTED_OPTION_SYMBOL
    assert order.instrument.lot_size == EXPECTED_OPTION_LOT
    assert order.instrument_type == InstrumentType.OPTION
    assert order.side == OrderSide.BUY
    assert order.quantity == 75
    assert order.order_type == OrderType.MARKET

    assert len(broker.received) == 1
    assert broker.received[0].symbol == EXPECTED_OPTION_SYMBOL


# --------------------------------------------------------------------------- #
# Test 2 — Persist
# --------------------------------------------------------------------------- #

def test_persist_order_and_fill_rows(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    handler, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    order = handler.process_signal(_signal(EQUITY_SYMBOL, 50), current_price=2500.0)

    conn = sqlite3.connect(str(store_path))
    try:
        orow = conn.execute(
            "SELECT symbol, side, quantity, order_type, signal_id "
            "FROM orders WHERE correlation_id = ?",
            (str(order.correlation_id),),
        ).fetchone()
        frow = conn.execute(
            "SELECT symbol, side, quantity FROM fills WHERE order_id = ?",
            (str(order.correlation_id),),
        ).fetchone()
    finally:
        conn.close()

    assert orow is not None
    assert orow[0] == order.symbol          # symbol string persisted verbatim
    assert orow[1] == "BUY"
    assert orow[2] == 50.0
    assert orow[3] == "MARKET"
    assert orow[4] == "sig-RELIANCE-50"

    assert frow is not None
    assert frow[0] == order.symbol
    assert frow[1] == "BUY"
    assert frow[2] == 50.0


# --------------------------------------------------------------------------- #
# Test 3 — Restore (round-trip)
# --------------------------------------------------------------------------- #

def test_restore_round_trip(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"

    # Handler A: build + persist over an initially empty ledger.
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)
    order = handler_a.process_signal(_signal(EQUITY_SYMBOL, 50), current_price=2500.0)

    # Handler B: restore from the same ledger (the restart-flip; load_db_state=True).
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    restored = handler_b.order_repo.get_all()
    ids = {str(o.correlation_id): o for o in restored}
    assert str(order.correlation_id) in ids
    ro = ids[str(order.correlation_id)]
    assert ro.symbol == order.symbol
    assert ro.side == OrderSide.BUY
    assert ro.quantity == 50

    # Position rebuilt from the replayed BUY fill: net long 50.
    assert handler_b.position_tracker.net_quantity(order.symbol) == 50.0


# --------------------------------------------------------------------------- #
# Test 4 — Reconcile (restored ledger vs broker fixture)
# --------------------------------------------------------------------------- #

def test_reconcile_restored_ledger_against_broker(tmp_path, monkeypatch):
    store_path = tmp_path / "execution.db"
    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)
    order = handler_a.process_signal(_signal(EQUITY_SYMBOL, 50), current_price=2500.0)

    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    # Matching broker state -> PASS (no alerts).
    matching = [{"symbol": order.symbol, "quantity": 50, "side": "LONG"}]
    assert handler_b.reconciliation.reconcile(matching) == []

    # Divergent broker state -> exactly one QUANTITY_MISMATCH.
    divergent = [{"symbol": order.symbol, "quantity": 10, "side": "LONG"}]
    alerts = handler_b.reconciliation.reconcile(divergent)
    assert len(alerts) == 1
    assert alerts[0].issue == "QUANTITY_MISMATCH"
    assert alerts[0].internal_value == 50.0
    assert alerts[0].broker_value == 10.0


# --------------------------------------------------------------------------- #
# Isolation guard — the real ledger is never touched
# --------------------------------------------------------------------------- #

def test_real_execution_db_untouched(tmp_path, monkeypatch):
    real = Path("data/execution.db")
    before = (real.exists(), real.stat().st_mtime_ns if real.exists() else None,
              real.stat().st_size if real.exists() else None)

    store_path = tmp_path / "execution.db"
    handler, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)
    handler.process_signal(_signal(EQUITY_SYMBOL, 50), current_price=2500.0)

    after = (real.exists(), real.stat().st_mtime_ns if real.exists() else None,
             real.stat().st_size if real.exists() else None)
    assert before == after
    # And the tmp ledger is the one that got the order.
    assert store_path.exists()
