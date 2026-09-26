"""NiftyShield — execution composition (Decomposition Spec D3/D4/D5, E007 A/F).

Wires the Stage-1 execution services (group assembly, sizing, exit manager)
into the runtime for a PAPER window, WITHOUT touching the frozen strategy:

- `NiftyShieldExecutionHandler(ExecutionHandler)` — buffers the per-leg
  `SignalEvent`s a structure emits (they share a `group_id`), and on the
  complete leg set: prices the legs against REAL option marks (E7-4), sizes the
  structure via `final_lots` (declared lots clamped by the BROKER's basket
  margin — Upstox `POST /v2/charges/margin`, operator decision 2026-09-08),
  routes each leg through the standard `process_signal` gate path (so
  idempotency / risk / greek / margin / fill / ledger all run per leg),
  registers the assembled OrderGroup, and journals that margin evidence (§7.7).
  A basket the broker cannot price SKIPS the entry — it never degrades to the
  local engine, which without a SPAN snapshot understated the 2026-09-07 spread
  by 17x (Rs 4,619 vs Rs 79,902).

  The handler's inherited per-leg `_check_margin_budget` computes F&O margin as
  `quantity x lot_size` (quantity treated as lots). NiftyShield's `quantity` is
  already in units (lots x lot_size), so the subclass overrides the gate for its
  own strategy to pass `lot_size=1.0` — keeping the engine figure on the real
  units. That per-leg gate stays on the local engine: it is a backstop that runs
  after the basket clamp has already sized the structure (LOW-2).

- `NiftyShieldExitDriver` — a `rebalance_hook`-shaped callable that evaluates
  every open structure against real marks and closes it on a trigger
  (TP / SL / time / delta-flatten, D5). Driven per bar and, in LIVE, on idle
  ticks too (throttled): the underlying's 1m bars stop at the 15:29 cash
  auction print while the options trade to 15:40, so a purely bar-driven exit
  could never reach the 15:35 hard flatten. Close is close-only: EXIT
  signals per leg routed through the handler — no dynamic hedge (D1).
"""
from __future__ import annotations

import dataclasses
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.events import SignalEvent, SignalType
from core.execution.groups.order_group import OrderGroup
from core.execution.groups.group_pnl import GroupPnLTracker
from core.execution.handler import ExecutionHandler
from core.execution.options.fees import option_order_fees
from core.execution.options.nifty_shield_exit import NiftyShieldExitManager
from core.execution.options.nifty_shield_groups import group_type_for
from core.execution.options.nifty_shield_wall import shadow_record
from core.execution.options.nifty_shield_pricing import (
    Bracket, fair_structure_credit, marked_structure_credit, sigma_bracket,
)
from core.execution.options.nifty_shield_marks import (
    MarksSourceUnavailable, OptionMarksSource, StaticMarksSource,
)
from core.execution.options.nifty_shield_sizing import (
    UpstoxMarginUnavailable, final_lots, structure_margin_over_upstox_basket,
)
from core.runtime.event_journal import EventType, Severity

STRATEGY_ID = "nifty_shield_v1"

LEG_COUNTS: Dict[str, int] = {
    "iron_fly": 4,
    "short_straddle": 2,
    "short_strangle": 2,
    "bull_put_spread": 2,
    "bear_call_spread": 2,
}



def _expected_legs(structure: str) -> int:
    return LEG_COUNTS.get(structure, 4)


class NiftyShieldExecutionHandler(ExecutionHandler):
    """ExecutionHandler that owns NiftyShield structures as OrderGroups.

    Construction identical to the base handler (the PAPER composition root passes
    the same kwargs) plus the execution-layer seams: `marks_source` (E7-4),
    `strategy_config` (the frozen certified config for sizing/lot size) and
    `use_broker_margin` (which authority sizes the structure).

    `use_broker_margin` is a COMPOSITION decision, never inferred at runtime.
    A live window opts in and the entry is sized by the broker's basket margin;
    an offline path (REPLAY, the smoke run, tests) leaves it False and is sized
    by the local engine, because there is no broker session to ask and a
    deterministic replay must not depend on one. Inferring it from whether the
    marks source happens to carry instrument keys would make "no broker
    identity" silently mean "size it locally" — the fallback this design
    removes.
    """

    def __init__(
        self,
        *args,
        marks_source: Optional[OptionMarksSource] = None,
        strategy_config: Optional[Dict[str, Any]] = None,
        use_broker_margin: bool = False,
        **kwargs,
    ):
        # ADR-025: NseMarginEngine is futures-only (one v400 risk array per
        # underlying, looked up by contract symbol), so it raises
        # MissingRiskArray on every option leg. The per-leg backstop stays on
        # the flat-rate tracker; the snapshot is session evidence, not a
        # margin input here.
        kwargs.pop("span_snapshot", None)
        super().__init__(*args, **kwargs)
        self._marks_source = marks_source or StaticMarksSource({})
        self._strategy_cfg = dict(strategy_config or {})
        self._use_broker_margin = bool(use_broker_margin)
        self._pending: Dict[str, List[SignalEvent]] = {}
        self._closed_groups: Dict[str, str] = {}
        self._brackets: Dict[str, Optional[Bracket]] = {}

    # ------------------------------------------------------------------ #
    # Public execution surface (used by the exit driver and the runner)
    # ------------------------------------------------------------------ #
    def marks(self, symbols: List[str]) -> Dict[str, float]:
        """Real option marks for the struck legs (E7-4)."""
        return self._marks_source.marks(symbols)

    def warm_marks(self, symbols: List[str]) -> None:
        """Warm the handler price cache from the marks source (no synthetic fill)."""
        for symbol, price in self.marks(symbols).items():
            self.update_market_price(symbol, price)

    def open_nifty_shield_groups(self) -> List[UUID]:
        """group_ids of NiftyShield structures with at least one open leg."""
        out: List[UUID] = []
        for group in list(self.group_tracker._groups.values()):
            legs = group.legs
            if not legs or legs[0].strategy_id != STRATEGY_ID:
                continue
            gid = group.group_id
            if self._group_flat(gid):
                continue
            out.append(gid)
        return out

    def structure_credit(self, group_id: UUID) -> float:
        """Net premium collected at entry, derived from fills (restart-safe).

        SELL legs contribute (+) premium x qty, BUY legs (-). The exit manager's
        TP/SL thresholds scale off this.
        """
        group = self.group_tracker.get_group(group_id)
        if group is None:
            return 0.0
        total = 0.0
        for leg in group.legs:
            state = self.order_tracker.get_order(leg.correlation_id)
            if state is None:
                continue
            sign = 1.0 if leg.side.value == "SELL" else -1.0
            total += sign * state.average_price * state.filled_quantity
        return total

    def structure_bracket(self, group_id: UUID) -> Optional[Bracket]:
        """The structure's take-profit / stop bracket, sized from its fills.

        Each leg's vol is solved from its own fill price at the signal's spot
        and DTE, and the take-profit is disabled below `tp_min_fee_multiple` x
        the round trip (every leg opened on one side and closed on the other).
        Fills and signal metadata are both persisted, so a restart recomputes
        the same bracket. Cached per group and journaled once: ENTRY_BRACKET at
        INFO, or at CRITICAL when none can be sized — the structure then has no
        take-profit or stop, and the clock and delta gate still bound it.
        """
        key = str(group_id)
        if key in self._brackets:
            return self._brackets[key]
        group = self.group_tracker.get_group(group_id)
        if group is None or not group.legs:
            return None
        md = group.legs[0].metadata
        md = getattr(md, "strategy_metadata", md)
        exit_md = md.get("exit") or {}
        cfg = self._strategy_cfg
        sigma_mult = float(exit_md.get("bracket_sigma", cfg.get("bracket_sigma", 1.0)))
        fee_mult = float(exit_md.get("tp_min_fee_multiple",
                                     cfg.get("tp_min_fee_multiple", 3.0)))

        legs, round_trip = [], 0.0
        for leg in group.legs:
            state = self.order_tracker.get_order(leg.correlation_id)
            if state is None or not state.filled_quantity:
                continue
            leg_md = getattr(leg.metadata, "strategy_metadata", leg.metadata)
            qty, price = float(state.filled_quantity), float(state.average_price)
            legs.append({"side": leg.side.value, "strike": leg_md.get("strike"),
                         "option_type": leg_md.get("option_type"),
                         "price": price, "qty": qty})
            round_trip += sum(
                option_order_fees(premium=price, quantity=int(qty), side=side,
                                  trade_date=leg.timestamp.date()).total
                for side in ("BUY", "SELL"))

        bracket = sigma_bracket(
            legs, spot=float(md.get("spot") or 0.0), dte_days=float(md.get("dte") or 0.0),
            rate=float(cfg.get("risk_free_rate", 0.065)), sigma_mult=sigma_mult,
            hold_hours=float(cfg.get("hold_hours", 2.5)),
            session_hours=float(cfg.get("session_hours", 6.25)),
            fee_floor_rs=fee_mult * round_trip)
        self._brackets[key] = bracket
        if bracket is None:
            self._record(
                EventType.ENTRY_BRACKET,
                "no exit bracket could be sized: the structure has NO take-profit "
                "or stop (hard exit and delta gate still apply)",
                severity=Severity.CRITICAL, group_id=key,
                reason="bracket unavailable", spot=md.get("spot"), dte=md.get("dte"),
                filled_legs=len(legs))
        else:
            self._record(
                EventType.ENTRY_BRACKET,
                f"exit bracket: TP {bracket.tp_rs:.0f} Rs "
                f"({'on' if bracket.tp_enabled else 'off'}), SL {bracket.sl_rs:.0f} Rs "
                f"at +/-{sigma_mult:g} sigma = {bracket.sigma_pts:.1f} pts",
                group_id=key, tp_rs=round(bracket.tp_rs, 2),
                sl_rs=round(bracket.sl_rs, 2), sigma_pts=round(bracket.sigma_pts, 2),
                leg_ivs=[round(iv, 4) for iv in bracket.leg_ivs],
                fee_floor_rs=round(bracket.fee_floor_rs, 2),
                tp_enabled=bracket.tp_enabled, sigma_mult=sigma_mult)
        return bracket

    def close_group(self, group_id: UUID, reason: str, bar_time: datetime,
                    marks: Dict[str, float]) -> None:
        """Close every leg of the structure (close-only, D1 — no hedge)."""
        group = self.group_tracker.get_group(group_id)
        if group is None:
            return
        for leg in group.legs:
            mark = marks.get(leg.symbol)
            if mark is None:
                continue
            exit_signal = SignalEvent(
                strategy_id=STRATEGY_ID,
                symbol=leg.symbol,
                timestamp=bar_time,
                signal_type=SignalType.EXIT,
                confidence=1.0,
                metadata={"group_id": str(group_id), "exit_reason": reason},
            )
            try:
                self.process_signal(exit_signal, mark)
            except Exception as exc:  # a failing exit leg must not block the rest
                self.logger.error("close_group leg failed for %s: %s",
                                  leg.symbol, exc)
        self._closed_groups[str(group_id)] = reason
        self._record(
            EventType.STRUCTURE_CLOSE,
            f"structure closed: {reason}",
            group_id=str(group_id),
            reason=reason,
            bar_time=bar_time.isoformat() if bar_time is not None else None,
            session=(bar_time.date().isoformat()
                     if bar_time is not None else None),
        )

    def _group_flat(self, group_id: UUID) -> bool:
        group = self.group_tracker.get_group(group_id)
        if group is None:
            return True
        # A restored CLOSED group carries its EXIT orders as legs, so every
        # leg symbol has both a BUY and a SELL order (a full round trip) —
        # that is authoritative. Position-only checking misclassifies such a
        # group as open when a NEW structure re-enters one of its symbols
        # (2026-08-21: the orphan group looked open off the straddle's 24250PE
        # position, and the exit driver stop-lossed the straddle's leg under
        # the orphan's group id).
        by_symbol: Dict[str, set] = {}
        for leg in group.legs:
            by_symbol.setdefault(leg.symbol, set()).add(leg.side.value)
        if all({"SELL", "BUY"} <= sides for sides in by_symbol.values()):
            return True
        for leg in group.legs:
            pos = self.position_tracker.get_position(leg.symbol)
            if pos is not None and pos.side.value != "FLAT":
                return False
        return True

    # ------------------------------------------------------------------ #
    # Signal intake override
    # ------------------------------------------------------------------ #
    def process_signal(self, signal: SignalEvent,
                       current_price: float) -> Optional[Any]:
        if signal.strategy_id != STRATEGY_ID:
            return super().process_signal(signal, current_price)
        if signal.signal_type is SignalType.EXIT:
            return super().process_signal(signal, current_price)
        return self._route_entry(signal)

    def _route_entry(self, signal: SignalEvent) -> Optional[Any]:
        md = signal.metadata
        group_id = str(md["group_id"])
        structure = str(md["structure"])
        self._pending.setdefault(group_id, []).append(signal)
        if len(self._pending[group_id]) < _expected_legs(structure):
            return None                       # wait for the full leg set
        signals = self._pending.pop(group_id)
        return self._enter_structure(group_id, structure, signals)

    def _journal_wall_shadow(self, group_id: str, structure: str,
                             signals: List[SignalEvent]) -> None:
        """Record what the Options-Wall poller was saying at this entry.

        Observe-only (audit Q4a): changes nothing about the trade. It exists so
        the two regime reads accumulate paired observations and can eventually
        be compared on evidence rather than on three sessions of overlap.
        Never raises — an entry must not be lost to a logging dependency.
        """
        try:
            ts = signals[0].timestamp
            shorts = [s for s in signals if s.signal_type.value == "SELL"]
            md = getattr(shorts[0].metadata, "strategy_metadata",
                         shorts[0].metadata) if shorts else {}
            ctx = signals[0].context
            rec = shadow_record(
                session_date=ts.date().isoformat(), at=ts,
                daytype_regime=getattr(ctx, "regime_state", None),
                structure=structure,
                short_strike=md.get("strike"),
            )
            self._record(EventType.ENTRY_DIAGNOSTIC,
                         "options-wall shadow read (observe-only, no effect on the trade)",
                         severity=Severity.INFO, group_id=group_id, **rec)
        except Exception as exc:                              # noqa: BLE001
            self._record(EventType.ENTRY_DIAGNOSTIC,
                         f"options-wall shadow read failed: {exc}",
                         severity=Severity.WARNING, group_id=group_id,
                         reason="wall shadow unavailable")

    def _credit_gate_rejects(self, group_id: str, structure: str,
                             signals: List[SignalEvent],
                             marks: Dict[str, float]) -> bool:
        """Refuse an entry whose real credit falls short of its reference price.

        Structure selection picks a shape and then took whatever credit the
        market happened to offer; it never asked whether that credit was good.
        This compares the marked net premium against Black-Scholes for the same
        legs at the session's own implied vol and skips the entry below
        `credit_fair_frac` of it — a pure no-trade filter that fires on stale or
        badly-spread quotes, never on a view.

        Missing inputs disable the gate rather than block the trade: an entry is
        the strategy's decision, and a gate that cannot compute its reference
        has no grounds to overrule it. That is journaled, not silent.
        """
        frac = float(self._strategy_cfg.get("credit_fair_frac", 0.0))
        if frac <= 0.0:
            return False
        md = signals[0].metadata
        md = getattr(md, "strategy_metadata", md)
        # Each leg is priced at ITS OWN implied vol, read from the same chain
        # snapshot the marks come from. The strategy's `iv` (India VIX) sizes the
        # strike offsets and is NOT a leg price input — using it here overstated
        # a 6-DTE vertical by ~30% and made the floor unreachable.
        ivs = self._marks_source.implied_vols([s.symbol for s in signals])
        legs = [{"symbol": s.symbol, "side": s.signal_type.value,
                 "strike": (getattr(s.metadata, "strategy_metadata", s.metadata)
                            ).get("strike"),
                 "option_type": (getattr(s.metadata, "strategy_metadata",
                                         s.metadata)).get("option_type"),
                 "iv": ivs.get(s.symbol)}
                for s in signals]
        fair = fair_structure_credit(
            legs, float(md.get("spot") or 0.0), float(md.get("dte") or 0.0),
            float(self._strategy_cfg.get("risk_free_rate", 0.065)))
        actual = marked_structure_credit(legs, marks)
        if fair is None or actual is None or fair <= 0.0:
            # NOT an ENTRY_SKIPPED: nothing was skipped. Using the skip event
            # for a gate that declined to act would corrupt the one signal an
            # operator reads to find lost entries.
            self._record(
                EventType.ENTRY_DIAGNOSTIC,
                "credit gate not evaluated: no reference price available "
                f"(per-leg IV present for {len(ivs)}/{len(legs)} legs)",
                severity=Severity.WARNING,
                group_id=group_id, structure=structure,
                reason="credit gate unavailable",
                fair_credit=fair, marked_credit=actual,
            )
            return False
        if actual < frac * fair:
            self._record(
                EventType.ENTRY_SKIPPED,
                f"structure entry skipped: credit {actual:.2f} is "
                f"{actual / fair * 100:.0f}% of the {fair:.2f} reference "
                f"(floor {frac * 100:.0f}%)",
                severity=Severity.WARNING,
                group_id=group_id, structure=structure,
                reason="credit below fair-value floor",
                fair_credit=round(fair, 2), marked_credit=round(actual, 2),
                credit_fair_frac=frac,
            )
            return True
        return False

    def _enter_structure(self, group_id: str, structure: str,
                         signals: List[SignalEvent]) -> Optional[Any]:
        leg_symbols = [s.symbol for s in signals]
        try:
            marks = self.marks(leg_symbols)
        except MarksSourceUnavailable as exc:
            # F3: cache-unavailable is infra, not market state — journal at
            # CRITICAL so the audit surfaces it; never a silent "missing marks".
            self._record(
                EventType.ENTRY_SKIPPED,
                f"structure entry skipped: marks source unavailable: {exc}",
                severity=Severity.CRITICAL,
                group_id=group_id, structure=structure,
                reason="marks source unavailable", error=str(exc),
            )
            return None
        missing = [s for s in signals if s.symbol not in marks]
        if missing:
            self._record(EventType.ENTRY_SKIPPED,
                          "structure entry skipped: missing option marks",
                          group_id=group_id, structure=structure,
                          reason="missing option marks (E7-4, no synthetic fallback)",
                          missing_legs=[s.symbol for s in missing])
            return None

        self.warm_marks(leg_symbols)

        if self._credit_gate_rejects(group_id, structure, signals, marks):
            return None

        self._journal_wall_shadow(group_id, structure, signals)

        # --- sizing (D4): declared lots clamped by the BROKER's basket margin --
        # The clamp prices the whole structure through Upstox rather than
        # summing per-leg engine margins: it is the figure that carries the
        # hedge's spread benefit, and it does not collapse to a flat 20%-of-
        # premium rate when today's SPAN snapshot is missing (which understated
        # the 2026-09-07 spread by 17x). Operator decision 2026-09-08; see
        # nifty_shield_sizing for the ADR-011/013 departure this records.
        lot_size = int(self._strategy_cfg.get("lot_size", 75))
        margin_budget = self._margin_budget()
        leg_specs = [{"symbol": s.symbol, "side": s.signal_type.value,
                      "option_type": s.metadata["option_type"]} for s in signals]

        try:
            _structure_margin = self._structure_margin_fn(
                leg_specs, leg_symbols, marks, lot_size)
            lots = final_lots(signals[0].metadata, _structure_margin,
                              margin_budget)
            structure_margin_rs = _structure_margin(lots)
        except UpstoxMarginUnavailable as exc:
            # Never degrade to the flat-rate engine: that is the understatement
            # this path removes, and doing it quietly would turn "we could not
            # ask the broker" into "the structure is cheap".
            self._record(
                EventType.ENTRY_SKIPPED,
                f"structure entry skipped: broker basket margin unavailable: {exc}",
                severity=Severity.CRITICAL,
                group_id=group_id, structure=structure,
                reason="Upstox basket margin unavailable", error=str(exc),
            )
            return None

        # margin_clamped_lots floors at 1 lot and returns it even when that lot
        # does not fit. Unreachable while the flat rate understated 17x; with
        # real broker figures it is not, so refuse rather than route a
        # structure over the datasheet §9 budget.
        if margin_budget > 0 and structure_margin_rs > margin_budget:
            self._record(
                EventType.ENTRY_SKIPPED,
                f"structure entry skipped: {lots} lot(s) needs "
                f"{structure_margin_rs:.0f} Rs against a {margin_budget:.0f} Rs "
                f"budget — below the minimum size",
                severity=Severity.WARNING,
                group_id=group_id, structure=structure,
                reason="margin budget exceeded at minimum lots",
                margin_total=round(structure_margin_rs, 2),
                margin_budget=round(margin_budget, 2), lots=lots,
            )
            return None
        qty = lots * lot_size

        # --- route each leg through the standard gate path, at the real mark ---
        routed = []
        for signal in signals:
            sized = dataclasses.replace(
                signal, metadata={**signal.metadata, "quantity": qty})
            routed.append(super().process_signal(sized, marks[signal.symbol]))

        if not any(routed):
            self._record(EventType.ENTRY_SKIPPED,
                          "structure entry skipped: every leg rejected by a gate",
                          group_id=group_id, structure=structure,
                          reason="every leg rejected by a handler gate")
            return None
        if len([r for r in routed if r is not None]) < len(routed):
            self._record(EventType.ENTRY_SKIPPED,
                          "structure entry partial: some legs rejected by a gate",
                          group_id=group_id, structure=structure,
                          reason="partial leg rejection (see handler logs)",
                          filled_legs=[s.symbol for r, s in zip(routed, signals)
                                       if r is not None],
                          rejected_legs=[s.symbol for r, s in zip(routed, signals)
                                         if r is None])

        # --- assemble the OrderGroup from the TRACKED orders (real correlation
        # ids) so GroupPnLTracker can price it, under the source's group_id ---
        group = self._register_group(group_id, structure, signals)
        if group is not None:
            self._journal_margin(group, lots, lot_size, structure_margin_rs,
                                 signals[0].metadata)
        return routed[-1] if routed else None

    def _structure_margin_fn(self, leg_specs, leg_symbols, marks, lot_size):
        """The margin callable the sizing clamp walks: broker basket, or engine.

        Broker basket (live): one call per lot count for the whole structure, so
        the figure carries the hedge's spread benefit and does not collapse to a
        flat rate when today's SPAN snapshot is missing.

        Engine (offline): per-leg incremental margin. Real-engine convention is
        get_incremental_margin(symbol, lots, price, lot_size) pricing
        `lots x lot_size` units — the Stage-1 helper structure_margin_over_engine
        passes units-as-lots and is not used here (E007 finding).
        """
        if self._use_broker_margin:
            keys = self._marks_source.instrument_keys(leg_symbols)
            return structure_margin_over_upstox_basket(leg_specs, keys, lot_size)

        def margin_at(lots: int) -> float:
            total = 0.0
            for spec in leg_specs:
                price = marks.get(spec["symbol"])
                if price is None:
                    continue
                total += self.margin_tracker.get_incremental_margin(
                    spec["symbol"], lots, price, lot_size=lot_size)
            return total

        return margin_at

    def _register_group(self, group_id: str, structure: str,
                        signals: List[SignalEvent]) -> Optional[OrderGroup]:
        from core.execution.groups.order_group import OrderGroup
        leg_symbols = set(s.symbol for s in signals)
        tracked = {
            state.order.symbol: state.order
            for state in self.order_tracker.order_states()
            if state.order.strategy_id == STRATEGY_ID
            and state.order.symbol in leg_symbols
        }
        legs = [tracked[sym] for sym in [s.symbol for s in signals]
                if sym in tracked]
        if not legs:
            self._record(EventType.ENTRY_SKIPPED,
                          "structure entry skipped: no tracked orders after routing",
                          group_id=group_id, structure=structure,
                          reason="no tracked orders after routing")
            return None
        group = OrderGroup(group_type=group_type_for(structure), legs=legs,
                           group_id=UUID(group_id))
        self.group_tracker._groups[group.group_id] = group
        for leg in legs:
            self.group_tracker._order_map[leg.correlation_id] = group.group_id
        return group

    # ------------------------------------------------------------------ #
    # Margin gate correctness for NiftyShield option legs (see module doc)
    # ------------------------------------------------------------------ #
    def _check_margin_budget(self, order, current_price) -> tuple:
        if order.strategy_id == STRATEGY_ID:
            # order.quantity is already in units (lots x lot_size); the margin
            # engine's `quantity` is in lots, so pass lot_size=1.0 for the
            # incremental. The used-portion is the handler's own open structures
            # summed per-leg at the real units — the base MarginTracker's
            # get_used_margin treats option position.quantity as lots (overstate
            # by lot_size), so it cannot price a NiftyShield option book.
            if self.metrics.cash_balance <= 0:
                return True, 0.0
            prices = {sym: snap.price for sym, snap in self._price_cache.items()}
            used = self._nifty_shield_used_margin(prices)
            incr = self.margin_tracker.get_incremental_margin(
                order.symbol, order.quantity, current_price, lot_size=1.0)
            utilisation = (used + incr) / self.metrics.cash_balance
            return utilisation <= self.config.max_capital_utilisation, utilisation
        return super()._check_margin_budget(order, current_price)

    def _calculate_fees(self, order, price) -> float:
        if order.strategy_id == STRATEGY_ID:
            # The base schedule is equity intraday: STT at 0.025% on every leg.
            # Options pay STT on sell-leg premium only (0.15% from 2026-04-01),
            # stamp duty on buys only, and a ~10x higher exchange charge — the
            # base understated a 2026-09-11 spread's round trip by Rs 16
            # (Finding #2, NIFTY_SHIELD_REMEDIATION_2026-09-08).
            return option_order_fees(
                premium=price, quantity=int(order.quantity),
                side=order.side.value, trade_date=order.timestamp.date()).total
        return super()._calculate_fees(order, price)

    def _nifty_shield_used_margin(self, prices: Dict[str, float]) -> float:
        """Used margin = per-leg incremental margin of open NiftyShield legs,
        computed at the real units (lots x lot_size). Restart-safe (derives from
        fills)."""
        lot_size = int(self._strategy_cfg.get("lot_size", 75))
        total = 0.0
        for gid in self.open_nifty_shield_groups():
            group = self.group_tracker.get_group(gid)
            if group is None:
                continue
            for leg in group.legs:
                state = self.order_tracker.get_order(leg.correlation_id)
                price = prices.get(leg.symbol)
                if state is None or state.filled_quantity <= 0 or price is None:
                    continue
                lots = state.filled_quantity / lot_size
                total += self.margin_tracker.get_incremental_margin(
                    leg.symbol, lots, price, lot_size=lot_size)
        return total

    def _margin_budget(self) -> float:
        """25% of the PAPER cash base (datasheet §7/§9)."""
        return 0.25 * self.metrics.cash_balance

    # ------------------------------------------------------------------ #
    # Evidence journaling (F / E7-2)
    # ------------------------------------------------------------------ #
    def _record(self, event_type, message, *,
                severity=None, **metadata) -> None:
        if self._journal is None:
            return
        try:
            self._journal.record(event_type, message,
                                 severity=severity,
                                 source_component="NiftyShieldExecutionHandler",
                                 metadata=metadata)
        except Exception:
            self.logger.exception("journal write failed")

    def _journal_margin(self, group: OrderGroup, lots: int, lot_size: int,
                        total: float, leg_metadata: Dict[str, Any]) -> None:
        """Journal the entry's margin evidence (§7.7, datasheet §11 open item).

        `total` is the figure the sizing clamp actually used, and `engine` names
        which authority produced it. `span` / `elm` are None under the broker
        basket: Upstox does not decompose it, and inventing a split would be
        worse evidence than admitting there is none.
        """
        span, elm = None, None
        now = self.clock.now()
        self._record(
            EventType.ENTRY_MARGIN,
            f"structure margin: {total:.2f} Rs over {lots} lots x {lot_size}",
            group_id=str(group.group_id),
            structure=group.group_type.value,
            lots=lots,
            lot_size=lot_size,
            margin_total=round(total, 2),
            span=round(span, 2) if span is not None else None,
            elm=round(elm, 2) if elm is not None else None,
            engine=("UpstoxBasketMargin" if self._use_broker_margin
                    else type(self.margin_tracker).__name__),
            session=now.date().isoformat() if now is not None else None,
            leg_symbols=[leg.symbol for leg in group.legs],
            # F2: the declared risk_r is the pinned R base; if the leg metadata
            # lacks it (a source/regression defect) journal None so the metrics
            # report surfaces R as vacuous rather than silently 0.0.
            risk_r=(float(leg_metadata["risk_r"])
                    if leg_metadata.get("risk_r") else None),
        )


class NiftyShieldExitDriver:
    """Per-bar exit evaluation for open NiftyShield structures (D5).

    Wired as the LoopDriver's `rebalance_hook`: invoked once per tick after the
    clock advance and before on_bar. Prices each open structure against real
    marks, evaluates the exit triggers (TP / SL / time / delta-flatten) and
    closes the structure when one fires (close-only).
    """

    def __init__(self, handler: NiftyShieldExecutionHandler,
                 marks_source: Optional[OptionMarksSource] = None,
                 min_interval_s: float = 0.0,
                 max_marks_age_s: Optional[float] = None):
        self._handler = handler
        self._marks_source = marks_source or handler._marks_source
        self._exit_managers: Dict[str, NiftyShieldExitManager] = {}
        # LIVE drives this hook on every idle tick too (poll interval 0.5s) so
        # the book stays managed after the underlying's last bar; that cadence
        # would hammer the chain cache, so a live composition passes a floor.
        # 0.0 (default) leaves REPLAY unthrottled — its bars arrive in
        # milliseconds of real time and every one must be evaluated.
        self._min_interval_s = float(min_interval_s)
        self._last_run_monotonic: Optional[float] = None
        # From the 15:29 auction print to the 15:35 hard exit there are no bars,
        # so a bar arriving no longer proves the feed is alive and the snapshot
        # is the ONLY input to a TP/SL decision. Deciding on a frozen snapshot
        # can fire a take-profit at a price that no longer exists; holding
        # cannot. So a stale feed HOLDS and journals, it never decides.
        self._max_marks_age_s = max_marks_age_s
        self._stale_journaled = False

    def __call__(self, timestamp: datetime,
                 execution_handler: Optional[Any] = None) -> bool:
        handler = self._handler
        group_ids = handler.open_nifty_shield_groups()
        if not group_ids:
            return False
        if self._min_interval_s > 0.0:
            now = time.monotonic()
            if (self._last_run_monotonic is not None
                    and now - self._last_run_monotonic < self._min_interval_s):
                return False
            self._last_run_monotonic = now
        if self._marks_are_stale():
            return False
        symbols = []
        for gid in group_ids:
            group = handler.group_tracker.get_group(gid)
            if group is not None:
                symbols.extend(leg.symbol for leg in group.legs)
        try:
            marks = self._marks_source.marks(symbols)
        except MarksSourceUnavailable as exc:
            # F3: a mid-window cache outage cannot be papered over — an unpriced
            # book cannot exit. Journal CRITICAL and stop the loop loudly.
            handler._record(
                EventType.ENTRY_SKIPPED,
                f"exit evaluation halted: marks source unavailable: {exc}",
                severity=Severity.CRITICAL,
                reason="marks source unavailable", error=str(exc),
            )
            raise
        handler.warm_marks(list(marks))

        for gid in group_ids:
            group = handler.group_tracker.get_group(gid)
            if group is None:
                continue
            leg_symbols = [leg.symbol for leg in group.legs]
            if not all(sym in marks for sym in leg_symbols):
                continue                     # unpriced structure -> cannot decide
            manager = self._manager_for(group.legs[0].metadata)
            portfolio_delta = self._portfolio_delta(marks)
            reason = manager.evaluate(
                gid, marks, timestamp, portfolio_delta=portfolio_delta,
                bracket=handler.structure_bracket(gid))
            if reason is not None:
                handler.close_group(gid, reason, timestamp, marks)
        return False

    def _marks_are_stale(self) -> bool:
        """True when the snapshot is too old to price an exit decision on.

        Edge-triggered journaling: the check runs every 15s in LIVE, and a
        CRITICAL line per tick would bury the event it is meant to surface.
        A structure held open past its hard exit because the feed died is a
        journaled condition an operator can act on — a spurious take-profit
        against a frozen snapshot is a wrong trade nobody sees.
        """
        if self._max_marks_age_s is None:
            return False
        age = self._marks_source.snapshot_age_s()
        if age is None or age <= self._max_marks_age_s:
            if self._stale_journaled:
                self._handler._record(
                    EventType.ENTRY_SKIPPED,
                    "exit evaluation resumed: option marks fresh again",
                    severity=Severity.WARNING,
                    reason="marks freshness restored",
                    snapshot_age_s=round(age, 1) if age is not None else None,
                )
                self._stale_journaled = False
            return False
        if not self._stale_journaled:
            self._handler._record(
                EventType.ENTRY_SKIPPED,
                f"exit evaluation held: option marks stale by {age:.0f}s "
                f"(limit {self._max_marks_age_s:.0f}s) — TP/SL/time exits are "
                f"NOT being evaluated while the chain poller is not publishing",
                severity=Severity.CRITICAL,
                reason="option marks stale",
                snapshot_age_s=round(age, 1),
                max_marks_age_s=self._max_marks_age_s,
            )
            self._stale_journaled = True
        return True

    def _manager_for(self, metadata: Any) -> NiftyShieldExitManager:
        # group.legs[0].metadata is an OrderMetadata; its dict surface is
        # strategy_metadata (the source's signal metadata dict).
        if hasattr(metadata, "strategy_metadata"):
            metadata = metadata.strategy_metadata
        cfg_key = str(metadata.get("group_id"))
        if cfg_key not in self._exit_managers:
            exit_md = metadata.get("exit", {})
            cfg = {
                # The hard exit is a strategy parameter, not a literal: it moved
                # to 15:35 so the structure is managed by its own TP/SL for the
                # whole session instead of being cut at 15:15.
                "exit_time": dict(self._handler._strategy_cfg.get(
                    "exit_time", {"hour": 15, "minute": 35})),
                "max_portfolio_delta": exit_md.get("max_portfolio_delta", 500),
            }
            self._exit_managers[cfg_key] = NiftyShieldExitManager(
                GroupPnLTracker(self._handler.group_tracker,
                                self._handler.order_tracker),
                cfg,
            )
        return self._exit_managers[cfg_key]

    def _portfolio_delta(self, marks: Dict[str, float]) -> float:
        try:
            greeks = self._handler.portfolio_greeks.calculate_portfolio_greeks(
                market_prices=marks, volatilities={}, time_to_expiry_map={},
                risk_free_rate=0.05)
            return greeks.delta
        except Exception:
            return 0.0
