"""
Gate G1 — Wave 4B forward position-identity characterization (P1–P7).

Pins the CURRENT behavior of the live forward F&O *position* identity before the
#6/#7 migration (canonicalize the open position at the live fill seam). Per
G1_WAVE4B_POSITION_IDENTITY_REVIEW.md §5, these seven must be green on current
code (zero production change) and encode today's reality exactly:

  P1  forward OPTION position identity        -> canonical Option, lot 65, mult 1.0
  P2  forward FUTURES position + margin       -> Future, mult 65.0, exposure x65 (intended)
  P3  forward OPTION margin/PnL                -> MM9.2-S2: margin axis now uses
      lot_size (65); PnL axis still multiplier 1.0 (PnLTracker unchanged)
  P4  FLAT identity inert + get_position legacy
  P5  forward vs restored-canonicalized futures-> PARITY (both Future)
  P6  #6 prove-dead                            -> no Position(symbol=) in core/
  P7  forward EQUITY position carve-out        -> Equity, mult 1.0 (stays)

Net was pinned green on current code first (P1 lot 1, P2 Equity/mult 1, P5 drift),
then the #7 migration flipped exactly three intended axes (P1 lot 1->65, P2
Equity->Future / mult x65, P5 drift->parity) — every assertion delta justified in
G1_WAVE4B_POSITION_IMPLEMENTATION_REPORT. P3/P4/P6/P7 stayed green through #7
(option identity-only — P3's option margin stayed ×1.0, which was the pre-existing
multiplier defect). MM9.2-S2 repaired P3's margin axis (now ×lot_size), leaving
the PnL axis at ×1.0 (PnLTracker unchanged by the fix). P4/P6/P7 are inert/carve-out.
Mirrors the harness of
test_g1_wave4a1: a REAL ExecutionHandler over an ISOLATED tmp store + db_manager.
"""
import pathlib

import pytz
from datetime import datetime

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import PositionSide
from core.execution.margin_tracker import MarginTracker
from core.execution.pnl_tracker import PnLTracker
from core.instruments.instrument_base import InstrumentType
from core.instruments.option import Option
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)

FUTURES_SYMBOL = "NIFTY26JUNFUT"
FUTURES_PRICE = 23000.0

OPTION_UNDERLYING = "NSE_INDEX|Nifty 50"
OPTION_PRICE = 22500.0
OPTION_SYMBOL = "NIFTY16JUN2622500CE"
NIFTY_MASTER_LOT = 65                 # present master (F4 materialization)

EQUITY_SYMBOL = "INFY"
EQUITY_PRICE = 1500.0


def _build_handler(tmp_path, monkeypatch, store_path):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore", lambda *a, **k: ExecutionStore(str(store_path))
    )
    clock = ReplayClock(FIXED_DT)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(),
        initial_capital=1_000_000_000.0,  # MM9.1: ample capital — characterization tests don't exercise the margin gate
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    return handler


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
        strategy_id="g1w4b",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=signal_type,
        confidence=1.0,
        metadata=meta,
    )


def _option_meta():
    return {"execution_mode": "option"}


# --------------------------------------------------------------------------- #
# P1 — forward OPTION position identity (legacy Option, lot 1, mult 1.0)
# --------------------------------------------------------------------------- #
def test_p1_forward_option_position_derives_master_lot(tmp_path, monkeypatch):
    """#7 migrated: the open option position is canonical-derived at the fill seam,
    carrying the master lot (65), no longer the parser's hardcoded 1. The option
    multiplier stays 1.0, so margin/PnL are unchanged (identity-only fix — see P3)."""
    handler = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db")
    handler.process_signal(
        _signal(OPTION_UNDERLYING, 75, metadata=_option_meta()), current_price=OPTION_PRICE
    )

    pos = handler.position_tracker.get_all_positions()[OPTION_SYMBOL]
    assert isinstance(pos.instrument, Option)
    assert pos.instrument.type == InstrumentType.OPTION
    assert pos.instrument.lot_size == NIFTY_MASTER_LOT   # #7: canonical-derived (was 1)
    assert pos.instrument.multiplier == 1.0      # option multiplier unchanged -> margin/PnL stable
    assert pos.symbol == OPTION_SYMBOL           # symbol key preserved
    assert handler.position_tracker.net_quantity(OPTION_SYMBOL) == 75.0


# --------------------------------------------------------------------------- #
# P2 — forward FUTURES position identity + margin (Equity, mult 1.0, exposure x1)
# --------------------------------------------------------------------------- #
def test_p2_forward_futures_position_derives_future_multiplier(tmp_path, monkeypatch):
    """#7 migrated: the open futures position is canonical-derived Future at the fill
    seam (was Equity — parse has no Future branch, H1). multiplier 1.0 -> 65.0, so
    margin/exposure changes x65. This is THE intended behavior change of Wave 4B
    (futures DO carry a lot multiplier; the prior mult-1 was the defect) — justified,
    adopting the master's current value (F4-gated for going live, not for the refactor)."""
    handler = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db")
    handler.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=FUTURES_PRICE)

    pos = handler.position_tracker.get_all_positions()[FUTURES_SYMBOL]
    assert pos.instrument.type == InstrumentType.FUTURE         # was EQUITY (H1 closed)
    assert pos.instrument.multiplier == float(NIFTY_MASTER_LOT)  # 65.0 (was 1.0)
    assert pos.symbol == FUTURES_SYMBOL                          # symbol key preserved

    margin = MarginTracker(handler.position_tracker)
    exposure = margin.get_exposure({FUTURES_SYMBOL: FUTURES_PRICE})
    assert exposure == 50 * FUTURES_PRICE * float(NIFTY_MASTER_LOT)  # x65 (intended margin change)


# --------------------------------------------------------------------------- #
# P3 — forward OPTION margin (MM9.2-S2: lot_size now) + PnL (still mult 1.0)
# --------------------------------------------------------------------------- #
def test_p3_forward_option_margin_and_pnl_multiplier_one(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db")
    handler.process_signal(
        _signal(OPTION_UNDERLYING, 75, metadata=_option_meta()), current_price=OPTION_PRICE
    )

    margin = MarginTracker(handler.position_tracker)
    pnl = PnLTracker(handler.position_tracker)

    # MM9.2-S2: MarginTracker now uses lot_size (65) for options instead of
    # multiplier (1.0). Prior to S2 this was 75 * PRICE * 1.0 (the old defect).
    exposure = margin.get_exposure({OPTION_SYMBOL: OPTION_PRICE})
    assert exposure == 75 * OPTION_PRICE * float(NIFTY_MASTER_LOT)
    # avg_price == fill price == OPTION_PRICE (PaperBroker fills at current_price).
    # PnLTracker still uses pos.instrument.multiplier (1.0) — unchanged by S2.
    unreal = pnl.get_unrealized_pnl({OPTION_SYMBOL: OPTION_PRICE + 100.0})
    assert unreal == (100.0) * 75 * 1.0          # multiplier 1.0; UNCHANGED by migration


# --------------------------------------------------------------------------- #
# P4 — FLAT identity inert + get_position stays legacy (the seam is the fill)
# --------------------------------------------------------------------------- #
def test_p4_flat_identity_inert_and_get_position_legacy(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db")
    pt = handler.position_tracker

    assert pt.net_quantity(FUTURES_SYMBOL) == 0.0
    assert pt.has_open_position(FUTURES_SYMBOL) is False

    flat = pt.get_position(FUTURES_SYMBOL)
    assert flat.side == PositionSide.FLAT
    # get_position is NOT the seam: it stays parse-built (Equity for a futures symbol),
    # master-independent (ADR-003). Unchanged by the migration.
    assert flat.instrument.type == InstrumentType.EQUITY


# --------------------------------------------------------------------------- #
# P5 — forward vs restored-canonicalized futures: CURRENT drift (Equity vs Future)
# --------------------------------------------------------------------------- #
def test_p5_forward_vs_restored_canonicalized_futures_parity(tmp_path, monkeypatch):
    """#7 migrated: the forward-built futures position and its restored+canonicalized
    twin now carry byte-identical canonical identity (type + multiplier) — the H1
    position-level drift (forward Equity vs restored Future) is closed, so a restart
    leaves the open position's identity unchanged (no drift). Forward derives at the
    live fill seam; restore stays legacy at construction (Option B) and upgrades via
    the same canonicalize_symbol primitive post-gate — which is why they match."""
    store_path = tmp_path / "execution.db"
    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=FUTURES_PRICE)
    fwd = ha.position_tracker.get_all_positions()[FUTURES_SYMBOL]

    hb = _build_handler(tmp_path, monkeypatch, store_path)
    # Pre-gate restore stays legacy (Option B), then the post-gate pass canonicalizes.
    hb.canonicalize_restored_positions()
    restored = hb.position_tracker.get_all_positions()[FUTURES_SYMBOL]

    # Parity (was drift): both are now canonical-derived Future.
    assert fwd.instrument.type == InstrumentType.FUTURE
    assert restored.instrument.type == InstrumentType.FUTURE
    assert fwd.instrument.type == restored.instrument.type
    assert fwd.instrument.multiplier == restored.instrument.multiplier
    assert fwd.symbol == restored.symbol == FUTURES_SYMBOL


# --------------------------------------------------------------------------- #
# P6 — #6 prove-dead: no production Position(symbol=) constructor in core/
# --------------------------------------------------------------------------- #
def test_p6_no_production_position_symbol_constructor():
    core = pathlib.Path(__file__).resolve().parents[2] / "core"
    # Exclude the definition module itself: position_models.py documents the
    # Position(symbol=) signature in its docstring — that is the ctor definition,
    # not a live caller. Deadness is asserted on CALLERS.
    definition = core / "execution" / "position_models.py"
    offenders = [
        str(p) for p in core.rglob("*.py")
        if p != definition and "Position(symbol=" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []   # #6 parse branch is dead on the live path (no caller)


# --------------------------------------------------------------------------- #
# P7 — forward EQUITY position carve-out (stays legacy Equity, mult 1.0)
# --------------------------------------------------------------------------- #
def test_p7_forward_equity_position_stays_legacy(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db")
    handler.process_signal(_signal(EQUITY_SYMBOL, 10), current_price=EQUITY_PRICE)

    pos = handler.position_tracker.get_all_positions()[EQUITY_SYMBOL]
    assert pos.instrument.type == InstrumentType.EQUITY     # carve-out; unchanged
    assert pos.instrument.multiplier == 1.0
    assert pos.symbol == EQUITY_SYMBOL

    margin = MarginTracker(handler.position_tracker)
    assert margin.get_exposure({EQUITY_SYMBOL: EQUITY_PRICE}) == 10 * EQUITY_PRICE * 1.0
