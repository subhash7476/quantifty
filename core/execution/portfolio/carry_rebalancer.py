"""Carry portfolio rebalancer — WS-C execution layer.

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §4.1 — book-level batch, not per-symbol
streaming. Called by LoopDriver on every bar via the rebalance hook; executes
only on formation dates.

The rebalancer is split into two concerns:
1. CORE (testable): compute_target_book + compute_deltas — the construction logic
   that must reproduce research-identical results.
2. EXECUTION: place_fill — the integration with broker/position_tracker.

For the PARITY sub-check (GATE C): feed research signal facts to the core;
verify target book + deltas match the research harness.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import duckdb
import numpy as np

from core.execution.order_lifecycle import FillEvent
from core.execution.futures.futures_fees import futures_fees as _calc_fees
from core.execution.position_models import PositionSide

_logger = logging.getLogger(__name__)

QUINTILE_FRAC = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25
SLIPPAGE_BP = 5


@dataclass
class TargetBook:
    """The rebalancer's target: what the portfolio SHOULD hold after rebalance."""
    formation_date: date
    longs: Dict[str, float]   # underlying -> capital_rs
    shorts: Dict[str, float]  # underlying -> capital_rs


@dataclass
class Delta:
    """A single rebalance delta: the change needed for one underlying."""
    underlying: str
    target_side: Optional[str]   # 'LONG', 'SHORT', or None
    target_cap: float
    held_side: Optional[str]
    held_cap: float
    delta_cap: float
    action: str    # 'OPEN', 'CLOSE', 'SCALE_UP', 'SCALE_DOWN', 'FLIP', 'NOOP'
    suppressed: bool = False  # suppressed by no-trade band


@dataclass
class CapitalState:
    """Minimal capital snapshot for gross-exposure policy decisions."""
    starting_capital: float
    current_equity: float
    realized_pnl: float
    current_drawdown_pct: float


PAPER_GROSS = 10_000_000.0  # Rs 1 Cr — research-identical


def paper_gross_exposure_policy(state: CapitalState) -> float:
    """PAPER-mode policy: returns the fixed research-identical gross.

    Ignores capital state — PAPER has no real capital to conserve, and
    the point is testing signal and mechanics at the validated book size.
    """
    return PAPER_GROSS


def live_gross_exposure_policy(state: CapitalState) -> float:
    """LIVE-mode policy: NOT YET DESIGNED.

    A PnL-reactive sizing rule is new behavior never present in
    TRAIN/HOLDOUT/parity, and designing it is its own pre-registered
    decision, not something to fall out of this integration task
    (bridge §8 no-re-optimization guardrail).
    """
    raise NotImplementedError(
        "LIVE gross-exposure policy is a separate, reviewed decision — "
        "see bridge §8 no-re-optimization guardrail"
    )


def compute_target_book(
    facts: List[Tuple],   # (underlying, z_carry_neut, ...) — extra fields ignored
    gross_exposure: float,
    adva: Optional[Dict[str, float]] = None,
) -> TargetBook:
    """Core construction: research-identical, re-ranks by z_carry_neut.

    facts: list of (underlying, z_carry_neut, ...) — caller MUST pre-filter
           (ADV availability, fwd_ret presence, etc.) before passing.
    gross_exposure: total Rs gross (long + short legs combined).
    adva: {underlying: adv_rs} for ADV capping. If None, no caps applied.

    Returns TargetBook with per-name capital allocations.
    """
    half_gross = gross_exposure / 2.0
    n = len(facts)
    nq = max(1, round(QUINTILE_FRAC * n))
    sorted_by_z = sorted(facts, key=lambda r: r[1])
    long_set = {r[0] for r in sorted_by_z[-nq:]}
    short_set = {r[0] for r in sorted_by_z[:nq]}

    longs: Dict[str, float] = {}
    shorts: Dict[str, float] = {}

    for in_set, side_map in [(long_set, longs), (short_set, shorts)]:
        n_leg = len(in_set)
        if n_leg == 0:
            continue
        cap_each = half_gross / n_leg
        for u in in_set:
            max_pos = (adva.get(u, float('inf')) * ADV_CAP_FRAC
                       if adva else cap_each)
            side_map[u] = min(cap_each, max_pos if max_pos > 0 else cap_each)
        total = sum(side_map.values())
        if total > 0:
            scale = half_gross / total
            side_map.update({u: v * scale for u, v in side_map.items()})

    return TargetBook(formation_date=date.today(), longs=longs, shorts=shorts)


def compute_deltas(
    target: TargetBook,
    held_longs: Dict[str, float],   # underlying -> capital_rs
    held_shorts: Dict[str, float],
    band_sigma: float = BAND_SIGMA,
) -> List[Delta]:
    """Compute target - held for each underlying, with no-trade band.

    No-trade band: suppress |delta| < band_sigma * std(target_weights) for
    SCALE_UP/SCALE_DOWN actions. OPEN/CLOSE/FLIP are never suppressed.
    """
    # Target weight std-dev for band threshold
    all_target_caps = list(target.longs.values()) + list(target.shorts.values())
    sigma_w = float(np.std(all_target_caps)) if len(all_target_caps) > 1 else 0.0
    band = band_sigma * sigma_w

    all_names = set(target.longs) | set(target.shorts) | set(held_longs) | set(held_shorts)
    deltas = []

    for u in sorted(all_names):
        target_long = target.longs.get(u, 0.0)
        target_short = target.shorts.get(u, 0.0)
        held_l = held_longs.get(u, 0.0)
        held_s = held_shorts.get(u, 0.0)

        # Determine target side and cap
        if target_long > 0:
            target_side = 'LONG'
            target_cap = target_long
        elif target_short > 0:
            target_side = 'SHORT'
            target_cap = target_short
        else:
            target_side = None
            target_cap = 0.0

        # Determine held side and cap
        if held_l > 0:
            held_side = 'LONG'
            held_cap = held_l
        elif held_s > 0:
            held_side = 'SHORT'
            held_cap = held_s
        else:
            held_side = None
            held_cap = 0.0

        # Classify action
        if target_side is None and held_side is None:
            continue
        elif target_side is None:
            delta_cap = -held_cap
            action = 'CLOSE'
        elif held_side is None:
            delta_cap = target_cap
            action = 'OPEN'
        elif target_side != held_side:
            delta_cap = target_cap + held_cap
            action = 'FLIP'
        elif target_cap > held_cap:
            delta_cap = target_cap - held_cap
            action = 'SCALE_UP'
        elif target_cap < held_cap:
            delta_cap = target_cap - held_cap  # negative
            action = 'SCALE_DOWN'
        else:
            delta_cap = 0.0
            action = 'NOOP'

        if abs(delta_cap) < 1e-6:
            continue

        suppressed = False
        if action in ('SCALE_UP', 'SCALE_DOWN') and abs(delta_cap) < band:
            suppressed = True

        deltas.append(Delta(
            underlying=u,
            target_side=target_side,
            target_cap=target_cap,
            held_side=held_side,
            held_cap=held_cap,
            delta_cap=delta_cap,
            action=action,
            suppressed=suppressed,
        ))

    return deltas


def rebalance_book(
    target: TargetBook,
    held_longs: Dict[str, float],
    held_shorts: Dict[str, float],
    band_sigma: float = BAND_SIGMA,
) -> Tuple[Dict[str, float], Dict[str, float], List[Delta]]:
    """Compute deltas and return new holdings after rebalance.

    Returns: (new_longs, new_shorts, deltas)
    The new holdings incorporate suppressed deltas (hold existing position).
    """
    deltas = compute_deltas(target, held_longs, held_shorts, band_sigma)

    new_longs = dict(held_longs)
    new_shorts = dict(held_shorts)

    for d in deltas:
        if d.suppressed:
            continue
        if d.action in ('CLOSE', 'FLIP'):
            new_longs.pop(d.underlying, None)
            new_shorts.pop(d.underlying, None)
        if d.action in ('OPEN', 'FLIP'):
            if d.target_side == 'LONG':
                new_longs[d.underlying] = d.target_cap
            elif d.target_side == 'SHORT':
                new_shorts[d.underlying] = d.target_cap
        if d.action == 'SCALE_UP':
            if d.target_side == 'LONG':
                new_longs[d.underlying] = d.target_cap
            elif d.target_side == 'SHORT':
                new_shorts[d.underlying] = d.target_cap
        if d.action == 'SCALE_DOWN':
            if d.target_side == 'LONG':
                new_longs[d.underlying] = d.target_cap
            elif d.target_side == 'SHORT':
                new_shorts[d.underlying] = d.target_cap

    return new_longs, new_shorts, deltas


def _derive_capital_state(tracker, execution) -> CapitalState:
    """Derive CapitalState from execution handler's metrics and position tracker.

    Reads cash_balance from ExecutionHandler.metrics (the real injected
    capital, set from initial_capital in build_runner). Position notional
    from the tracker is NOT used as equity — gross exposure is not the
    same as capital.

    Drawdown is read from metrics.max_drawdown_pct (maintained by the
    handler's equity-update cycle, handler.py:139-146).
    """
    metrics = getattr(execution, 'metrics', None)
    cash_balance = float(metrics.cash_balance) if metrics else 0.0
    max_equity = float(metrics.max_equity) if metrics else cash_balance
    dd_pct = 0.0
    if metrics and max_equity > 0:
        dd_pct = float(getattr(metrics, 'max_drawdown_pct', 0.0) or 0.0)

    realized_pnl = 0.0
    pnl_tracker = getattr(execution, 'pnl_tracker', None)
    if pnl_tracker is not None:
        realized_pnl = float(getattr(pnl_tracker, 'realized_pnl', 0.0) or 0.0)

    starting_capital = cash_balance
    current_equity = cash_balance + realized_pnl
    return CapitalState(
        starting_capital=starting_capital,
        current_equity=max(current_equity, 0.0),
        realized_pnl=realized_pnl,
        current_drawdown_pct=dd_pct,
    )


class CarryRebalancerHook:
    """LoopDriver rebalance hook for the Carry sleeve.

    Instantiated with facts DB path and execution handler. Called by LoopDriver
    on each bar (rebalance_hook parameter). On formation dates: reads facts,
    computes target book + deltas, places fills.

    The core (compute_target_book, compute_deltas, rebalance_book) is stateless
    and independently testable. This class owns the I/O and execution.
    """

    def __init__(self, facts_db_path: str, execution_handler,
                 gross_exposure_policy: Callable[[CapitalState], float] = paper_gross_exposure_policy,
                 bhavcopy_db_path: Optional[str] = None):
        self._facts_db = Path(facts_db_path)
        self._exec = execution_handler
        self._gross_exposure_policy = gross_exposure_policy
        self._bhavcopy_db = Path(bhavcopy_db_path) if bhavcopy_db_path else None
        if self._bhavcopy_db is None:
            _logger.warning(
                "CarryRebalancerHook: bhavcopy_db_path not provided — "
                "ADV capping disabled for this instance"
            )
        self._last_date: Optional[date] = None
        self._formation_dates: set = set()
        self._load_calendar()

    def _load_calendar(self):
        con = duckdb.connect(str(self._facts_db), read_only=True)
        rows = con.execute(
            "SELECT DISTINCT formation_date FROM carry_facts ORDER BY formation_date"
        ).fetchall()
        con.close()
        self._formation_dates = {r[0] for r in rows}

    def __call__(self, ts, execution):
        bar_date = ts.date() if hasattr(ts, 'date') else ts
        if bar_date not in self._formation_dates:
            return False
        if self._last_date == bar_date:
            return False
        self._last_date = bar_date

        _logger.info("CarryRebalancer: executing %s", bar_date)
        self._execute(bar_date)
        return True

    def _execute(self, fdate: date):
        tracker = self._exec.position_tracker
        capital_state = _derive_capital_state(tracker, self._exec)
        gross_exposure = self._gross_exposure_policy(capital_state)

        MARGIN_RATE = 0.20
        MAX_CAPITAL_UTILISATION = 0.80

        required_margin = gross_exposure * MARGIN_RATE
        available = capital_state.current_equity * MAX_CAPITAL_UTILISATION
        if required_margin > available:
            _logger.warning(
                "CarryRebalancer: margin check FAILED for %s — "
                "gross=Rs %.1f Cr, required_margin=Rs %.0f, "
                "available=Rs %.0f (%.0f%% utilisation cap on Rs %.0f equity). "
                "Skipping rebalance.",
                fdate, gross_exposure / 1e7, required_margin,
                available, MAX_CAPITAL_UTILISATION * 100,
                capital_state.current_equity,
            )
            return

        con = duckdb.connect(str(self._facts_db), read_only=True)
        rows = con.execute(
            "SELECT underlying, z_carry_neut, quintile, eligible "
            "FROM carry_facts WHERE formation_date = ?",
            [fdate]
        ).fetchall()
        con.close()

        facts = [(r[0], float(r[1])) for r in rows if r[3]]  # eligible only

        # Load ADV from bhavcopy and filter
        adva: Dict[str, float] = {}
        if self._bhavcopy_db and self._bhavcopy_db.exists() and facts:
            adva = self._load_adva(facts, fdate)
            facts = [f for f in facts if f[0] in adva]

        if len(facts) < 5:
            return

        positions = tracker.get_all_positions()

        held_longs: Dict[str, float] = {}
        held_shorts: Dict[str, float] = {}
        for sym, pos in positions.items():
            side = pos.side
            if side == PositionSide.FLAT:
                continue
            capital = abs(pos.quantity) * pos.avg_price if pos.avg_price > 0 else abs(pos.quantity)
            underlying = self._underlying_from_sym(sym)
            if side == PositionSide.LONG:
                held_longs[underlying] = capital
            elif side == PositionSide.SHORT:
                held_shorts[underlying] = capital

        target = compute_target_book(facts, gross_exposure, adva)
        new_longs, new_shorts, deltas = rebalance_book(
            target, held_longs, held_shorts, BAND_SIGMA)

        self._execute_deltas(deltas, target, fdate)

    def _load_adva(self, facts: list, formation_date: date) -> dict:
        """Trailing 20-day ADV per underlying from futures bhavcopy."""
        ulist = ", ".join(f"'{f[0]}'" for f in facts)
        con = duckdb.connect(str(self._bhavcopy_db), read_only=True)
        rows = con.execute(f"""
            SELECT underlying, AVG(val_in_lakh) * 100000.0
            FROM (
                SELECT underlying, val_in_lakh,
                       ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
                FROM futures_bhavcopy
                WHERE trade_date <= DATE '{formation_date}'
                  AND trade_date > DATE '{formation_date}' - INTERVAL '30 days'
                  AND underlying IN ({ulist}) AND inst_type = 'FUTSTK'
            )
            WHERE rn <= 20 AND val_in_lakh IS NOT NULL
            GROUP BY underlying HAVING COUNT(*) >= 10
        """).fetchall()
        con.close()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _underlying_from_sym(sym: str) -> str:
        if sym.endswith("FUT"):
            sym = sym[:-3]
        return sym

    def _execute_deltas(self, deltas: List[Delta], target: TargetBook,
                        trade_date: date):
        executions = [d for d in deltas if not d.suppressed]
        if not executions:
            return

        tracker = self._exec.position_tracker
        ts = datetime.combine(trade_date, time.min)

        total_fee = 0.0
        total_slippage = 0.0

        # Phase 1: exits first
        for d in executions:
            if d.action in ('CLOSE', 'FLIP'):
                side = 'SELL' if d.held_side == 'LONG' else 'BUY'
                trade_val = abs(d.held_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)
                total_fee += fill.fee

            if d.action == 'SCALE_DOWN':
                side = 'SELL' if d.held_side == 'LONG' else 'BUY'
                trade_val = abs(d.delta_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)
                total_fee += fill.fee

        # Phase 2: entries
        for d in executions:
            if d.action in ('OPEN',):
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = d.target_cap
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)
                total_fee += fill.fee

            if d.action == 'SCALE_UP':
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = abs(d.delta_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)
                total_fee += fill.fee

            if d.action == 'FLIP':
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = d.target_cap
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)
                total_fee += fill.fee

        n_exits = sum(1 for d in executions if d.action in ('CLOSE', 'FLIP', 'SCALE_DOWN'))
        n_entries = sum(1 for d in executions if d.action in ('OPEN', 'SCALE_UP', 'FLIP'))
        total_slippage = sum((SLIPPAGE_BP / 10000) * (
            abs(d.delta_cap) if d.action in ('SCALE_UP', 'SCALE_DOWN', 'OPEN')
            else abs(d.held_cap) if d.action in ('CLOSE',)
            else d.target_cap
        ) for d in executions)
        _logger.info("Rebalance done: %d exits, %d entries, "
                      "~Rs %.0f fees + ~Rs %.0f slippage",
                      n_exits, n_entries, total_fee, total_slippage)

    def _build_fill(self, underlying: str, side: str, trade_val: float,
                    trade_date: date, ts: datetime) -> FillEvent:
        """Construct a FillEvent with real futures fees and injected slippage."""
        f = _calc_fees(side=side, trade_value=trade_val, trade_date=trade_date)
        slippage = (SLIPPAGE_BP / 10000) * trade_val
        return FillEvent(
            fill_id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            symbol=underlying + "FUT",
            quantity=trade_val,
            price=1.0,
            timestamp=ts,
            side=side,
            fee=f.total + slippage,
        )
