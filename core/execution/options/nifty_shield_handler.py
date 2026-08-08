"""NiftyShield — execution composition (Decomposition Spec D3/D4/D5, E007 A/F).

Wires the Stage-1 execution services (group assembly, sizing, exit manager)
into the runtime for a PAPER window, WITHOUT touching the frozen strategy:

- `NiftyShieldExecutionHandler(ExecutionHandler)` — buffers the per-leg
  `SignalEvent`s a structure emits (they share a `group_id`), and on the
  complete leg set: prices the legs against REAL option marks (E7-4), sizes the
  structure via `final_lots` (declared lots margin-clamped by the
  `NseMarginEngine` — the sole sizing authority), routes each leg through the
  standard `process_signal` gate path (so idempotency / risk / greek / margin /
  fill / ledger all run per leg), registers the assembled OrderGroup, and
  journals the SPAN+ELM margin evidence (§7.7).

  The handler's inherited per-leg `_check_margin_budget` computes F&O margin as
  `quantity x lot_size` (quantity treated as lots). NiftyShield's `quantity` is
  already in units (lots x lot_size), so the subclass overrides the gate for its
  own strategy to pass `lot_size=1.0` — keeping the SPAN+ELM figure on the real
  units. The sizing clamp (`final_lots`) enforces the 25% budget pre-entry; the
  handler gate is the backstop (LOW-2).

- `NiftyShieldExitDriver` — a `rebalance_hook`-shaped callable that evaluates
  every open structure once per bar against real marks and closes it on a
  trigger (TP / SL / time / delta-flatten, D5). Close is close-only: EXIT
  signals per leg routed through the handler — no dynamic hedge (D1).
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.events import SignalEvent, SignalType
from core.execution.groups.order_group import OrderGroup
from core.execution.groups.group_pnl import GroupPnLTracker
from core.execution.handler import ExecutionHandler
from core.execution.options.nifty_shield_exit import NiftyShieldExitManager
from core.execution.options.nifty_shield_groups import group_type_for
from core.execution.options.nifty_shield_marks import (
    MarksSourceUnavailable, OptionMarksSource, StaticMarksSource,
)
from core.execution.options.nifty_shield_sizing import final_lots
from core.runtime.event_journal import EventType, Severity
from core.risk.nse_margin_engine import NseMarginEngine

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
    the same kwargs) plus the execution-layer seams: `marks_source` (E7-4) and
    `strategy_config` (the frozen certified config for sizing/lot size).
    """

    def __init__(
        self,
        *args,
        marks_source: Optional[OptionMarksSource] = None,
        strategy_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._marks_source = marks_source or StaticMarksSource({})
        self._strategy_cfg = dict(strategy_config or {})
        self._pending: Dict[str, List[SignalEvent]] = {}
        self._closed_groups: Dict[str, str] = {}

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

        # --- sizing (D4): declared lots margin-clamped by the margin engine ---
        lot_size = int(self._strategy_cfg.get("lot_size", 75))
        margin_budget = self._margin_budget()
        leg_specs = [{"symbol": s.symbol, "side": s.signal_type.value,
                      "option_type": s.metadata["option_type"]} for s in signals]

        def _structure_margin(lots: int) -> float:
            # Real-engine convention: get_incremental_margin(symbol, lots, price,
            # lot_size) prices `lots x lot_size` units (the Stage-1 helper
            # structure_margin_over_engine passes units-as-lots and is not used
            # here — see E007 finding).
            total = 0.0
            for spec in leg_specs:
                price = marks.get(spec["symbol"])
                if price is None:
                    continue
                total += self.margin_tracker.get_incremental_margin(
                    spec["symbol"], lots, price, lot_size=lot_size)
            return total

        lots = final_lots(signals[0].metadata, _structure_margin, margin_budget)
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
            self._journal_margin(group, lots, lot_size, marks,
                                 signals[0].metadata)
        return routed[-1] if routed else None

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
                        marks: Dict[str, float],
                        leg_metadata: Dict[str, Any]) -> None:
        """Journal the entry's margin evidence (§7.7, datasheet §11 open item).

        The figure is NseMarginEngine-computed (SPAN + ELM) when a SPAN snapshot
        is present, else the flat-rate MarginTracker fallback (noted as such).
        """
        total = 0.0
        for leg in group.legs:
            price = marks.get(leg.symbol, 0.0)
            total += self.margin_tracker.get_incremental_margin(
                leg.symbol, lots, price, lot_size=lot_size)
        span, elm = None, None
        if isinstance(self.margin_tracker, NseMarginEngine):
            # get_incremental_margin = span + elm; elm = rate x lot_size x lots
            # x price (NseMarginEngine.get_incremental_margin), computed read-only.
            elm = 0.0
            for leg in group.legs:
                price = marks.get(leg.symbol, 0.0)
                rate = self.margin_tracker._resolve_elm_rate(leg.symbol)
                elm += rate * lot_size * lots * price
            span = max(0.0, total - elm)
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
            engine=type(self.margin_tracker).__name__,
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
                 marks_source: Optional[OptionMarksSource] = None):
        self._handler = handler
        self._marks_source = marks_source or handler._marks_source
        self._exit_managers: Dict[str, NiftyShieldExitManager] = {}

    def __call__(self, timestamp: datetime,
                 execution_handler: Optional[Any] = None) -> bool:
        handler = self._handler
        group_ids = handler.open_nifty_shield_groups()
        if not group_ids:
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
            credit = handler.structure_credit(gid)
            manager = self._manager_for(group.legs[0].metadata)
            portfolio_delta = self._portfolio_delta(marks)
            reason = manager.evaluate(
                gid, credit, marks, timestamp, portfolio_delta=portfolio_delta)
            if reason is not None:
                handler.close_group(gid, reason, timestamp, marks)
        return False

    def _manager_for(self, metadata: Any) -> NiftyShieldExitManager:
        # group.legs[0].metadata is an OrderMetadata; its dict surface is
        # strategy_metadata (the source's signal metadata dict).
        if hasattr(metadata, "strategy_metadata"):
            metadata = metadata.strategy_metadata
        cfg_key = str(metadata.get("group_id"))
        if cfg_key not in self._exit_managers:
            exit_md = metadata.get("exit", {})
            cfg = {
                "profit_target_pct": exit_md.get("tp_pct", 0.50),
                "stop_loss_multiplier": exit_md.get("sl_mult", 2.0),
                "exit_time": {"hour": 15, "minute": 15},
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
