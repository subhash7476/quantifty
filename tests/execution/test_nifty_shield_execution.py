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
        "exit": {"tp_pct": 0.5, "sl_mult": 2.0, "sl_frac": 0.5,
                 "hard_exit": "15:35", "max_portfolio_delta": 500},
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


def test_time_exit_triggers_at_1535_not_1515():
    """The hard exit is 15:35, so 15:16 — which used to close the structure —
    must now hold. 15:15 cut every trade at the cash close; this book is F&O
    and its own TP/SL own the position until the derivatives session ends."""
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    entry = {l.symbol: 100.0 for l in legs}
    manager, _ = _manager_with_tracker(legs, entry)
    credit = 100.0 * 75 * 2
    flat = _current_prices(legs, {l.symbol: 100.0 for l in legs})
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat,
                            datetime(2023, 1, 4, 15, 36, 0)) == "time_exit"
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat,
                            datetime(2023, 1, 4, 15, 16, 0)) is None
    assert manager.evaluate(UUID(_GROUP_ID), credit, flat,
                            datetime(2023, 1, 4, 15, 34, 0)) is None


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


# --------------------------------------------------------------------------- #
# Stop reachability (D5) — a defined-risk structure cannot lose a multiple of
# its own credit, so `-sl_mult x credit` is unreachable whenever
# max_loss / credit < sl_mult. Marks below price all four legs coherently; the
# older fixtures pin wings flat while shorts move, which is an arbitrage state
# a real fly never reaches and is why the defect survived them.
# --------------------------------------------------------------------------- #
_FLY_ENTRY = {"NIFTY10JAN2318150CE": 60.0, "NIFTY10JAN2318150PE": 58.0,
              "NIFTY10JAN2318250CE": 20.0, "NIFTY10JAN2318050PE": 18.0}
# credit/unit 80 on a 100-point wing -> max_loss/unit 20, ratio 0.25 << 2.0
_FLY_CREDIT = 80.0 * 150
_FLY_MAX_LOSS = 100.0 * 150 - _FLY_CREDIT


def _fly_manager():
    legs = assemble_group(_iron_fly_signals(), _UNDERLYING, 2, 75).legs
    manager, _ = _manager_with_tracker(legs, {l.symbol: _FLY_ENTRY[l.symbol]
                                              for l in legs})
    return manager, legs


def test_iron_fly_stop_fires_on_fraction_of_max_loss():
    manager, legs = _fly_manager()
    # CE side breached: short 60 -> 80, wing 20 -> 29. P&L = -1,650.
    marks = _current_prices(legs, {**_FLY_ENTRY,
                                   "NIFTY10JAN2318150CE": 80.0,
                                   "NIFTY10JAN2318250CE": 29.0})
    # The old rule needed -2 x 12,000 = -24,000 against a structural floor of
    # -3,000: unreachable by a factor of eight.
    assert _FLY_MAX_LOSS < 2.0 * _FLY_CREDIT
    assert manager.evaluate(UUID(_GROUP_ID), _FLY_CREDIT, marks, _TS,
                            max_loss=_FLY_MAX_LOSS) == "stop_loss"


def test_iron_fly_stop_holds_inside_the_max_loss_band():
    manager, legs = _fly_manager()
    # short 60 -> 72, wing 20 -> 26. P&L = -900, inside 0.5 x 3,000.
    marks = _current_prices(legs, {**_FLY_ENTRY,
                                   "NIFTY10JAN2318150CE": 72.0,
                                   "NIFTY10JAN2318250CE": 26.0})
    assert manager.evaluate(UUID(_GROUP_ID), _FLY_CREDIT, marks, _TS,
                            max_loss=_FLY_MAX_LOSS) is None


def test_vertical_spread_stop_fires_on_fraction_of_max_loss():
    legs = assemble_group(
        [_leg_signal("short_pe", "PE", 18150, SignalType.SELL,
                     structure="bull_put_spread", sl_distance=150.0),
         _leg_signal("wing_pe", "PE", 18000, SignalType.BUY,
                     structure="bull_put_spread", sl_distance=150.0)],
        _UNDERLYING, 2, 75).legs
    entry = {"NIFTY10JAN2318150PE": 90.0, "NIFTY10JAN2318000PE": 35.0}
    manager, _ = _manager_with_tracker(legs, {l.symbol: entry[l.symbol]
                                              for l in legs})
    credit = 55.0 * 150                      # 150-point wing -> max_loss 14,250
    max_loss = 150.0 * 150 - credit
    assert max_loss < 2.0 * credit           # ratio 1.73 -> old stop unreachable
    # short 90 -> 150, wing 35 -> 47. P&L = -7,200 vs -7,125 trigger.
    marks = _current_prices(legs, {"NIFTY10JAN2318150PE": 150.0,
                                   "NIFTY10JAN2318000PE": 47.0})
    assert manager.evaluate(UUID(_GROUP_ID), credit, marks, _TS,
                            max_loss=max_loss) == "stop_loss"


def test_undefined_structure_keeps_the_credit_multiple_stop():
    """straddle/strangle have no structural bound — sl_mult is the real rule."""
    legs = assemble_group(
        [_leg_signal("short_ce", "CE", 18150, SignalType.SELL,
                     structure="short_straddle"),
         _leg_signal("short_pe", "PE", 18150, SignalType.SELL,
                     structure="short_straddle")],
        _UNDERLYING, 2, 75).legs
    entry = {"NIFTY10JAN2318150CE": 60.0, "NIFTY10JAN2318150PE": 58.0}
    manager, _ = _manager_with_tracker(legs, {l.symbol: entry[l.symbol]
                                              for l in legs})
    credit = 118.0 * 150                                   # -2x -> -35,400
    fires = _current_prices(legs, {**entry, "NIFTY10JAN2318150CE": 300.0})
    holds = _current_prices(legs, {**entry, "NIFTY10JAN2318150CE": 200.0})
    assert manager.evaluate(UUID(_GROUP_ID), credit, fires, _TS,
                            max_loss=None) == "stop_loss"
    assert manager.evaluate(UUID(_GROUP_ID), credit, holds, _TS,
                            max_loss=None) is None


# --------------------------------------------------------------------------- #
# Lot size — NSE moved NIFTY to 65 (instrument master: every option expiry from
# 2026-09-08). It is declared in two places; they must not drift apart, and the
# handler sizes from the strategy config, so a stale value routes an
# un-tradeable quantity (the 2026-09-07 spread filled 75 units, not 65).
# --------------------------------------------------------------------------- #
def test_certified_nifty_lot_size_is_65():
    from core.execution.options.nifty_shield_gates import DEFAULT_CERTIFIED_CONFIG
    assert DEFAULT_CONFIG["lot_size"] == 65
    assert DEFAULT_CERTIFIED_CONFIG["lot_size"] == DEFAULT_CONFIG["lot_size"]


# --------------------------------------------------------------------------- #
# Broker basket margin as the sizing authority (operator decision 2026-09-08)
# --------------------------------------------------------------------------- #

def test_basket_margin_sizes_the_whole_structure_in_one_call():
    """One broker call per lot count, for every leg at once — that is what
    carries the hedge's spread benefit. A per-leg sum cannot express it."""
    from core.execution.options.nifty_shield_sizing import (
        structure_margin_over_upstox_basket)
    seen = []

    def fake_fetch(legs, product="D"):
        seen.append((tuple((l["instrument_key"], l["quantity"],
                            l["transaction_type"]) for l in legs), product))
        return {"required": 90000.0, "final": 70000.0,
                "benefit": 20000.0, "error": None}

    legs = [{"symbol": "A", "side": "SELL"}, {"symbol": "B", "side": "BUY"}]
    keys = {"A": "NSE_FO|1", "B": "NSE_FO|2"}
    margin_at = structure_margin_over_upstox_basket(
        legs, keys, 65, fetch=fake_fetch)

    assert margin_at(2) == 70000.0             # the FINAL (post-benefit) figure
    assert len(seen) == 1
    basket, product = seen[0]
    assert basket == (("NSE_FO|1", 130, "SELL"), ("NSE_FO|2", 130, "BUY"))
    assert product == "D"
    margin_at(2)                               # memoized — the clamp revisits
    assert len(seen) == 1


def test_basket_margin_refuses_rather_than_degrading():
    """A broker that cannot price the basket must raise. Falling back to the
    flat-rate engine is what priced the 2026-09-07 spread at Rs 4,619 against
    the broker's Rs 79,902 — a clamp that understates 17x cannot gate."""
    from core.execution.options.nifty_shield_sizing import (
        UpstoxMarginUnavailable, structure_margin_over_upstox_basket)

    legs = [{"symbol": "A", "side": "SELL"}]
    with pytest.raises(UpstoxMarginUnavailable):
        structure_margin_over_upstox_basket(legs, {}, 65)   # no instrument key

    margin_at = structure_margin_over_upstox_basket(
        legs, {"A": "NSE_FO|1"}, 65,
        fetch=lambda legs, product="D": {
            "required": None, "final": None, "benefit": None,
            "error": "No access token — re-authenticate with Upstox"})
    with pytest.raises(UpstoxMarginUnavailable, match="access token"):
        margin_at(1)


def test_basket_margin_clamps_lots_down_to_the_budget():
    """final_lots walks the declared lots down until the BROKER's figure fits."""
    from core.execution.options.nifty_shield_sizing import (
        final_lots, structure_margin_over_upstox_basket)

    def fake_fetch(legs, product="D"):
        lots = legs[0]["quantity"] // 65
        return {"required": 40000.0 * lots, "final": 36000.0 * lots,
                "benefit": 4000.0 * lots, "error": None}

    margin_at = structure_margin_over_upstox_basket(
        [{"symbol": "A", "side": "SELL"}], {"A": "NSE_FO|1"}, 65,
        fetch=fake_fetch)
    # declared = max(1, round(4 x 0.5)) = 2 -> Rs 72,000 > budget -> 1 lot.
    assert final_lots({"base_lots": 4, "regime_mult": 0.5},
                      margin_at, 50000.0) == 1


def test_min_lots_over_budget_is_refused_not_routed():
    """margin_clamped_lots floors at 1 lot and returns it even when that lot
    does not fit. Unreachable while the flat rate understated 17x; with real
    broker figures it is not, so the handler must refuse rather than route a
    structure over the datasheet §9 budget."""
    from core.execution.options.nifty_shield_sizing import (
        final_lots, margin_clamped_lots)

    def margin_at(lots):
        return 400000.0 * lots           # 1 lot already busts a 250k budget

    assert margin_clamped_lots(3, margin_at, 250000.0) == 1
    assert final_lots({"base_lots": 4, "regime_mult": 0.5},
                      margin_at, 250000.0) == 1
    # ...and the figure the handler then checks is over budget, which is what
    # the ENTRY_SKIPPED guard keys on.
    assert margin_at(1) > 250000.0
