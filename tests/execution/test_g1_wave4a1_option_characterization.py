"""
Gate G1 — Wave 4A.1 option-path characterization expansion (M1–M6).

Pins the CURRENT behavior of the live forward F&O *option* order path before the
#4 migration (selector → CanonicalInstrument-derived Option) and the O2 EXIT leg.
Per G1_WAVE4_OPTION_PATH_REVIEW.md §4, the existing Wave-2A net covers only
NIFTY / BUY→CALL / master-present at the handler level. These six tests close the
remaining axes and MUST be green on current code (zero production change).

  M1  handler-level option build, master ABSENT      -> INDEX_LOT_SIZES fallback (75)
  M2  BANKNIFTY option build                          -> master-resolved lot (30), step-100
  M3  SELL -> PUT option build                        -> OptionType.PUT, side SELL
  M4  option EXIT identity                            -> else->parse->Option(lot 1), qty from position
  M5  CanonicalInstrument containment tripwire        -> NormalizedOrder.instrument is legacy Option
  M6  option-order persist + restore round-trip       -> symbol/side/qty parity across restart

Every literal is an OBSERVED byte (recorded from the same selector/parser the
handler uses on 2026-06-09 against the present instrument master), not an
idealized value — so a #4 migration that changes a payload byte goes red.

Mirrors the harness of test_g1_characterization.py: a REAL ExecutionHandler wired
to a spy PaperBroker over an ISOLATED tmp ExecutionStore + DatabaseManager(tmp).
Changes ZERO production code.
"""
import sqlite3
from datetime import date, datetime

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import OrderSide, OrderType
from core.instruments.instrument_base import InstrumentType
from core.instruments.option import Option, OptionType
from core.instruments.canonical import CanonicalInstrument
from core.instruments.resolver import InstrumentResolver
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)

NIFTY_UNDERLYING = "NSE_INDEX|Nifty 50"
NIFTY_PRICE = 22500.0
NIFTY_CALL_SYMBOL = "NIFTY16JUN2622500CE"   # selector date/strike math (master-independent)
NIFTY_PUT_SYMBOL = "NIFTY16JUN2622500PE"
NIFTY_MASTER_LOT = 65                        # present master (F4 materialization 75->65)
NIFTY_FALLBACK_LOT = 75                      # INDEX_LOT_SIZES["NSE_INDEX|Nifty 50"]

BANKNIFTY_UNDERLYING = "NSE_INDEX|Nifty Bank"
BANKNIFTY_PRICE = 52000.0                    # step-100 ATM (round(52000/100)*100)
BANKNIFTY_EXPIRY = date(2026, 6, 17)         # default weekly Wednesday expiry
BANKNIFTY_SYMBOL = "BANKNIFTY17JUN2652000CE"
# The 2026-06-09 snapshot carries only MONTHLY BANKNIFTY contracts, so the computed
# WEEKLY contract is not in the master -> resolve_option returns None and the lot
# falls back to INDEX_LOT_SIZES["NSE_INDEX|Nifty Bank"] (35). This is today's reality
# for a default BANKNIFTY option signal. (The master-resolved monthly lot is 30, but
# reaching it requires a policy expiry_date override, which carries a date object that
# is itself non-JSON-serializable through order persistence — a separate latent finding,
# out of #4 scope.)
BANKNIFTY_FALLBACK_LOT = 35


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


def _signal(symbol, quantity, signal_type=SignalType.BUY, metadata=None):
    meta = {
        "quantity": quantity,
        "sl_distance": 5.0,
        "risk_r": 1.0,
        "signal_id": f"sig-{symbol}-{quantity}-{signal_type.value}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1w4a1",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=signal_type,
        confidence=1.0,
        metadata=meta,
    )


def _option_meta(policy=None):
    meta = {"execution_mode": "option"}
    if policy is not None:
        meta["option_policy"] = policy
    return meta


# --------------------------------------------------------------------------- #
# M1 — handler-level forward option build, master ABSENT
# --------------------------------------------------------------------------- #

def test_m1_option_build_master_absent_falls_back_to_index_lot(tmp_path, monkeypatch):
    """ADR-003: with the master absent the handler still builds an Option, the
    symbol is byte-identical, and the lot is the INDEX_LOT_SIZES fallback (75).
    The selector hardcodes OptionsContractSelector() (no injected resolver), so we
    point its internally-constructed resolver at an absent DB — the exact surface
    the #4 migration edits. The derived type must NOT flip on DB presence."""
    absent_db = tmp_path / "absent.duckdb"
    monkeypatch.setattr(
        "core.execution.options.selector.InstrumentResolver",
        lambda *a, **k: InstrumentResolver(db_path=absent_db),
    )
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    sig = _signal(NIFTY_UNDERLYING, 75, metadata=_option_meta())
    order = handler.process_signal(sig, current_price=NIFTY_PRICE)

    assert order is not None
    assert order.symbol == NIFTY_CALL_SYMBOL                 # master-independent symbol math
    assert order.instrument_type == InstrumentType.OPTION
    assert order.instrument.lot_size == NIFTY_FALLBACK_LOT   # fallback, not master 65
    assert order.side == OrderSide.BUY
    assert order.quantity == 75
    assert order.order_type == OrderType.MARKET

    assert len(broker.received) == 1
    assert broker.received[0].symbol == NIFTY_CALL_SYMBOL


# --------------------------------------------------------------------------- #
# M2 — BANKNIFTY forward option build (non-NIFTY, master-resolved lot)
# --------------------------------------------------------------------------- #

def test_m2_banknifty_default_option_build_falls_back_to_index_lot(tmp_path, monkeypatch):
    """Pins the non-NIFTY underlying: short name BANKNIFTY, strike step 100, default
    weekly Wednesday expiry. The 2026-06-09 master carries only monthly BANKNIFTY, so
    the computed weekly contract is unresolved and the lot is the INDEX_LOT_SIZES
    fallback (35). No policy override -> the metadata is JSON-serializable and the
    order persists cleanly (contrast the date-override path)."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    sig = _signal(BANKNIFTY_UNDERLYING, 30, metadata=_option_meta())
    order = handler.process_signal(sig, current_price=BANKNIFTY_PRICE)

    assert order is not None
    assert order.symbol == BANKNIFTY_SYMBOL
    assert order.instrument_type == InstrumentType.OPTION
    assert order.instrument.lot_size == BANKNIFTY_FALLBACK_LOT   # fallback 35 (weekly unresolved)
    assert order.instrument.strike == 52000.0                    # step-100 ATM
    assert order.instrument.expiry == BANKNIFTY_EXPIRY
    assert order.instrument.expiry.weekday() == 2                # Wednesday
    assert order.instrument.option_type == OptionType.CALL
    assert order.side == OrderSide.BUY
    assert order.quantity == 30
    assert order.order_type == OrderType.MARKET

    assert len(broker.received) == 1
    assert broker.received[0].symbol == BANKNIFTY_SYMBOL


# --------------------------------------------------------------------------- #
# M3 — SELL -> PUT forward option build
# --------------------------------------------------------------------------- #

def test_m3_sell_signal_builds_put_option(tmp_path, monkeypatch):
    """The option_type branch (selector.py:97) at the handler level: SELL -> PUT.
    Only BUY->CALL was pinned before. Symbol switches the CE->PE suffix; lot stays
    master-resolved (65); side is SELL."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    sig = _signal(NIFTY_UNDERLYING, 75, signal_type=SignalType.SELL,
                  metadata=_option_meta())
    order = handler.process_signal(sig, current_price=NIFTY_PRICE)

    assert order is not None
    assert order.symbol == NIFTY_PUT_SYMBOL
    assert order.instrument_type == InstrumentType.OPTION
    assert order.instrument.option_type == OptionType.PUT
    assert order.instrument.lot_size == NIFTY_MASTER_LOT
    assert order.side == OrderSide.SELL
    assert order.quantity == 75
    assert order.order_type == OrderType.MARKET

    assert len(broker.received) == 1
    assert broker.received[0].symbol == NIFTY_PUT_SYMBOL


# --------------------------------------------------------------------------- #
# M4 — option EXIT identity (the O2 leg)
# --------------------------------------------------------------------------- #

def test_m4_option_exit_derives_master_lot_and_position_quantity(tmp_path, monkeypatch):
    """O2 migrated (G1 Wave 4 #4 / O2): an EXIT carrying the option SYMBOL takes the
    else branch -> canonicalize_symbol -> master-derived Option(lot_size=65), no
    longer the parser's resolver-blind lot 1. The intended change is the lot byte
    only; every other byte is unchanged. Crucially the exit quantity stays
    current_position.quantity (lot-independent), so the broker payload (symbol /
    side / quantity / order_type) is unaffected by the lot derivation — the close
    is sized off the open position, not the lot. ENTRY and EXIT now agree on the
    master lot (the identity asymmetry O2 closed)."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    # Open a LONG option position via the selector ENTRY path (keyed by the option symbol).
    entry = handler.process_signal(
        _signal(NIFTY_UNDERLYING, 75, metadata=_option_meta()),
        current_price=NIFTY_PRICE,
    )
    assert entry.symbol == NIFTY_CALL_SYMBOL
    assert handler.position_tracker.net_quantity(NIFTY_CALL_SYMBOL) == 75.0

    # EXIT carries the option symbol -> else branch -> canonicalize_symbol (O2).
    exit_order = handler.process_signal(
        _signal(NIFTY_CALL_SYMBOL, 75, signal_type=SignalType.EXIT,
                metadata=_option_meta()),
        current_price=NIFTY_PRICE,
    )

    assert exit_order is not None
    assert exit_order.symbol == NIFTY_CALL_SYMBOL            # byte-identical, unchanged by O2
    assert exit_order.instrument_type == InstrumentType.OPTION
    assert exit_order.instrument.lot_size == NIFTY_MASTER_LOT  # O2: canonical-derived (was 1)
    assert exit_order.side == OrderSide.SELL                 # closing the LONG
    assert exit_order.quantity == 75                         # position-sourced, NOT lot-sized
    assert exit_order.order_type == OrderType.MARKET

    # Broker payload is unaffected by the lot derivation — quantity is the position
    # quantity (lot-independent), proving the O2 lot change does not touch sizing.
    assert broker.received[-1].quantity == 75
    assert broker.received[-1].symbol == NIFTY_CALL_SYMBOL

    # ENTRY (selector) and EXIT (canonical derivation) now agree on the master lot —
    # the identity asymmetry O2 closed (was 65 vs 1).
    assert entry.instrument.lot_size == NIFTY_MASTER_LOT
    assert exit_order.instrument.lot_size == NIFTY_MASTER_LOT


# --------------------------------------------------------------------------- #
# M5 — CanonicalInstrument containment tripwire
# --------------------------------------------------------------------------- #

def test_m5_forward_option_order_carries_legacy_option_not_canonical(tmp_path, monkeypatch):
    """The G1/4C.7 boundary for the forward option path: NormalizedOrder.instrument
    is a legacy Option, never a CanonicalInstrument, and no canonical-only field
    (instrument_key / product) leaks onto the payload. The broker receives the same
    legacy object with the selector-computed symbol."""
    store_path = tmp_path / "execution.db"
    handler, broker = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)

    order = handler.process_signal(
        _signal(NIFTY_UNDERLYING, 75, metadata=_option_meta()),
        current_price=NIFTY_PRICE,
    )

    assert isinstance(order.instrument, Option)
    assert not isinstance(order.instrument, CanonicalInstrument)
    # No canonical identity fields cross into the payload object.
    assert not hasattr(order.instrument, "instrument_key")
    assert not hasattr(order.instrument, "product")
    assert not hasattr(order.instrument, "asset_class")
    # Symbol is the selector-computed string, not a master display_symbol.
    assert order.symbol == NIFTY_CALL_SYMBOL
    assert len(broker.received) == 1
    assert broker.received[0].instrument is order.instrument
    assert broker.received[0].symbol == NIFTY_CALL_SYMBOL


# --------------------------------------------------------------------------- #
# M6 — forward option order: persist + restore round-trip
# --------------------------------------------------------------------------- #

def test_m6_option_order_persist_and_restore_round_trip(tmp_path, monkeypatch):
    """The Section-4 persist/restore net used an equity order; this pins the option
    payload specifically. Handler A builds + persists the forward option order;
    Handler B restores from the same ledger (the restart-flip). Symbol/side/quantity
    survive verbatim and the position is rebuilt from the replayed fill."""
    store_path = tmp_path / "execution.db"

    handler_a, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)
    order = handler_a.process_signal(
        _signal(NIFTY_UNDERLYING, 75, metadata=_option_meta()),
        current_price=NIFTY_PRICE,
    )
    assert order.symbol == NIFTY_CALL_SYMBOL

    # Persisted order row carries the option symbol verbatim.
    conn = sqlite3.connect(str(store_path))
    try:
        orow = conn.execute(
            "SELECT symbol, side, quantity, order_type FROM orders WHERE correlation_id = ?",
            (str(order.correlation_id),),
        ).fetchone()
    finally:
        conn.close()
    assert orow is not None
    assert orow[0] == NIFTY_CALL_SYMBOL
    assert orow[1] == "BUY"
    assert orow[2] == 75.0
    assert orow[3] == "MARKET"

    # Handler B: restore from the same ledger.
    handler_b, _ = _build_handler(tmp_path, monkeypatch, store_path, load_db_state=True)
    restored = {str(o.correlation_id): o for o in handler_b.order_repo.get_all()}
    assert str(order.correlation_id) in restored
    ro = restored[str(order.correlation_id)]
    assert ro.symbol == NIFTY_CALL_SYMBOL
    assert ro.side == OrderSide.BUY
    assert ro.quantity == 75
    assert ro.instrument_type == InstrumentType.OPTION

    # Position rebuilt from the replayed BUY fill: net long 75 on the option symbol.
    assert handler_b.position_tracker.net_quantity(NIFTY_CALL_SYMBOL) == 75.0
