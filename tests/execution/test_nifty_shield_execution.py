"""
NiftyShield v1 — execution-side unit tests (Stage-1 prompt §2.B / §5).

Covers, against synthetic marks fixtures:
- Sizing (D4): declared lots from base_lots/regime_mult/vix_reduce; margin
  ceiling clamp.
- Group assembly (§3.3/D5): legs sharing a group_id -> one OrderGroup with the
  correct group type and leg sides/quantities.
- Exit-manager (D5): each trigger (TP / SL / time / delta) fires exactly when
  the trigger condition holds, and holds otherwise.
"""
from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

import pytest

from core.events import OHLCVBar, SignalEvent, SignalType
from core.execution.groups.group_pnl import GroupPnLTracker
from core.execution.groups.group_tracker import GroupTracker
from core.execution.groups.order_group import OrderGroupType
from core.execution.options.nifty_shield_exit import NiftyShieldExitManager
from core.execution.options.nifty_shield_groups import assemble_group, group_type_for
from core.execution.options.nifty_shield_sizing import (
    declared_lots, final_lots, margin_clamped_lots, structure_margin_over_engine,
)
from core.execution.order_lifecycle import FillEvent
from core.execution.order_tracker import OrderTracker

from strategies.nifty_shield_v1 import build_signal_source
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

_TS = datetime(2023, 1, 4, 13, 0, 0)
_GROUP_ID = "11111111-2222-3333-4444-555555555555"
_UNDERLYING = "NSE_INDEX|Nifty 50"


def _leg_signal(role: str, ot: str, strike: int, signal_type: SignalType,
                structure: str = "iron_fly", **md_over):
    md = {
        "group_id": _GROUP_ID,
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
    return SignalEvent(strategy_id="nifty_shield_v1", symbol="NIFTY10JAN23" + str(strike) + ot,
                       timestamp=_TS, signal_type=signal_type, confidence=0.9,
                       metadata=md)


def _iron_fly_signals():
    return [
        _leg_signal("short_ce", "CE", 18150, SignalType.SELL),
        _leg_signal("short_pe", "PE", 18150, SignalType.SELL),
        _leg_signal("wing_ce", "CE", 18250, SignalType.BUY),
        _leg_signal("wing_pe", "PE", 18050, SignalType.BUY),
    ]


# --------------------------------------------------------------------------- #
# Sizing (D4)
# --------------------------------------------------------------------------- #
def test_declared_lots_choppy_full():
    assert declared_lots({"base_lots": 2, "regime_mult": 1.0,
                          "vix_reduce": False, "structure": "iron_fly"}) == 2


def test_declared_lots_bear_half():
    assert declared_lots({"base_lots": 2, "regime_mult": 0.5,
                          "vix_reduce": False, "structure": "bear_call_spread"}) == 1


def test_declared_lots_vix_reduce_non_strangle():
    # VIX-reduce shaves a lot only for non-strangle structures.
    assert declared_lots({"base_lots": 2, "regime_mult": 1.0, "vix_reduce": True,
                          "structure": "iron_fly"}) == 1
    # strangle is exempt (already shifted OTM)
    assert declared_lots({"base_lots": 2, "regime_mult": 1.0, "vix_reduce": True,
                          "structure": "short_strangle"}) == 2


def test_margin_clamped_lots_reduces_to_ceiling():
    def margin_at(lots):
        return lots * 60_000.0
    assert margin_clamped_lots(2, margin_at, margin_budget=100_000.0) == 1
    assert margin_clamped_lots(2, margin_at, margin_budget=250_000.0) == 2
    assert margin_clamped_lots(2, margin_at, margin_budget=None) == 2


def test_final_lots_end_to_end():
    md = {"base_lots": 2, "regime_mult": 1.0, "vix_reduce": False,
          "structure": "iron_fly"}
    assert final_lots(md, lambda lots: lots * 50_000.0, 60_000.0) == 1
    assert final_lots(md, lambda lots: lots * 50_000.0, 200_000.0) == 2


def test_structure_margin_over_engine_uses_engine():
    calls = []

    class FakeMarginEngine:
        def get_incremental_margin(self, symbol, quantity, price, lot_size=1.0):
            calls.append((symbol, quantity))
            return quantity * price * 0.2

    legs = [
        {"symbol": "NIFTY10JAN2318150CE", "side": "SELL"},
        {"symbol": "NIFTY10JAN2318150PE", "side": "SELL"},
    ]
    prices = {"NIFTY10JAN2318150CE": 150.0, "NIFTY10JAN2318150PE": 150.0}
    margin_at = structure_margin_over_engine(legs, FakeMarginEngine(), prices,
                                             lot_size=75)
    assert margin_at(1) == pytest.approx(2 * 75 * 150 * 0.2)
    assert margin_at(2) == pytest.approx(2 * 2 * 75 * 150 * 0.2)


# --------------------------------------------------------------------------- #
# Group assembly (§3.3 / D5)
# --------------------------------------------------------------------------- #
def test_group_type_mapping():
    assert group_type_for("short_straddle") is OrderGroupType.STRADDLE
    assert group_type_for("short_strangle") is OrderGroupType.STRANGLE
    assert group_type_for("iron_fly") is OrderGroupType.IRON_CONDOR
    assert group_type_for("bull_put_spread") is OrderGroupType.SPREAD
    assert group_type_for("bear_call_spread") is OrderGroupType.SPREAD


def test_assemble_iron_fly_group():
    group = assemble_group(_iron_fly_signals(), _UNDERLYING, lots=2, lot_size=75)
    assert group.group_type is OrderGroupType.IRON_CONDOR
    assert group.group_id == UUID(_GROUP_ID)
    assert len(group.legs) == 4
    sides = {leg.side.value for leg in group.legs}
    assert sides == {"BUY", "SELL"}
    shorts = [l for l in group.legs if l.side.value == "SELL"]
    assert all(l.quantity == 2 * 75 for l in shorts)


def test_assemble_requires_single_group_id():
    sigs = _iron_fly_signals()
    sigs[1] = _leg_signal("short_pe", "PE", 18150, SignalType.SELL,
                          **{"group_id": "99999999-0000-0000-0000-000000000000"})
    with pytest.raises(ValueError, match="group_ids"):
        assemble_group(sigs, _UNDERLYING, lots=2, lot_size=75)


def test_assemble_rejects_empty():
    with pytest.raises(ValueError):
        assemble_group([], _UNDERLYING, lots=2, lot_size=75)


# --------------------------------------------------------------------------- #
# Exit-manager (D5) — each trigger against synthetic marks fixtures.
# --------------------------------------------------------------------------- #
def _make_tracker(legs, entry_map):
    ot = OrderTracker()
    for leg in legs:
        ot.add_order(leg, persist=False)
        st = ot.get_order(leg.correlation_id)
        st.average_price = entry_map[leg.symbol]
        st.filled_quantity = float(leg.quantity)
    gt = GroupTracker(ot)
    gt.create_group(group_type_for("iron_fly"), legs)
    return GroupPnLTracker(gt, ot)


def _manager_with_tracker(legs, entry_map, **cfg_over):
    pnl = _make_tracker(legs, entry_map)
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(cfg_over)
    return NiftyShieldExitManager(pnl, cfg), pnl


def _current_prices(legs, marks):
    return {leg.symbol: marks.get(leg.symbol, 0.0) for leg in legs}


def test_take_profit_triggers():
    legs = _iron_fly_signals()
    legs = assemble_group(legs, _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}          # shorts + wings all at 100
    # Group P&L = sum (current - entry) * qty * dir. Shorts profit when current
    # falls; wings profit when they rise. Simulate shorts at 40 (profit 60 each).
    marks = {l.symbol: (40.0 if l.side.value == "SELL" else 100.0) for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 60.0 * 75 * 2 + 60.0 * 75 * 2            # premium collected per leg
    reason = manager.evaluate(UUID(_GROUP_ID), credit,
                              _current_prices(legs, marks), _TS)
    assert reason == "take_profit"


def test_stop_loss_triggers():
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}
    # Shorts at 240 -> loss 140 each on 2 shorts, wings flat.
    marks = {l.symbol: (240.0 if l.side.value == "SELL" else 100.0) for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 100.0 * 75 * 2
    reason = manager.evaluate(UUID(_GROUP_ID), credit,
                              _current_prices(legs, marks), _TS)
    assert reason == "stop_loss"


def test_time_exit_triggers_at_1515():
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 100.0 * 75 * 2
    # Flat marks -> no TP/SL; after 15:15 the hard exit fires.
    flat = _current_prices(legs, {l.symbol: 100.0 for l in legs})
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat,
                            datetime(2023, 1, 4, 15, 16, 0)) == "time_exit"
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat,
                            datetime(2023, 1, 4, 15, 14, 0)) is None


def test_delta_flatten_gate_closes_no_hedge():
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 100.0 * 75 * 2
    flat = _current_prices(legs, {l.symbol: 100.0 for l in legs})
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat, _TS,
                            portfolio_delta=600.0) == "delta_flatten"
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat, _TS,
                            portfolio_delta=400.0) is None


def test_holds_when_no_trigger():
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 100.0 * 75 * 2
    flat = _current_prices(legs, {l.symbol: 100.0 for l in legs})
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat, _TS) is None
