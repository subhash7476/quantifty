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
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import duckdb
import numpy as np

from core.execution.order_lifecycle import FillEvent
from core.execution.futures.futures_fees import futures_fees as _calc_fees
from core.execution.position_models import PositionSide
from core.execution.portfolio.exit_policy import (
    ExitDecision, ExitPolicy, PositionState,
)

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
    exit_reason: Optional[str] = None  # 'EXIT_TP', 'EXIT_SL', 'EXIT_SIGNAL'


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
    facts: List[Tuple],
    gross_exposure: float,
    adva: Optional[Dict[str, float]] = None,
    nq: Optional[int] = None,
    sector_map: Optional[Dict[str, str]] = None,
    max_per_sector: Optional[int] = None,
) -> TargetBook:
    half_gross = gross_exposure / 2.0
    n = len(facts)
    if nq is None:
        nq = max(1, round(QUINTILE_FRAC * n))
    nq = min(nq, n // 2)
    sorted_by_z = sorted(facts, key=lambda r: r[1])

    longs: Dict[str, float] = {}
    shorts: Dict[str, float] = {}

    def _pick(rows, reverse=False):
        """Select up to nq names, respecting sector constraint."""
        iterable = reversed(rows) if reverse else rows
        picked = []
        sec_counts = {}
        for r in iterable:
            u = r[0]
            sec = sector_map.get(u, "UNKNOWN") if sector_map else "UNKNOWN"
            limit = max_per_sector if max_per_sector is not None else 999
            if sec_counts.get(sec, 0) >= limit:
                continue
            picked.append(u)
            sec_counts[sec] = sec_counts.get(sec, 0) + 1
            if len(picked) >= nq:
                break
        return picked

    long_names = _pick(sorted_by_z, reverse=True)
    short_names = _pick(sorted_by_z, reverse=False)

    for names, side_map in [(long_names, longs), (short_names, shorts)]:
        n_leg = len(names)
        if n_leg == 0:
            continue
        cap_each = half_gross / n_leg
        for u in names:
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


@dataclass
class RebalanceMetrics:
    """Per-formation cost decomposition, recomputed from Deltas.

    Independent of FillEvent.fee (which blends fees + slippage into one field):
    fees and slippage are kept separate, and a FLIP is counted as two legs so
    slippage accrues on both the exit and the entry notional.
    """
    n_exits: int
    n_entries: int
    traded_value_total: float
    fees_total: float
    slippage_total: float
    fee_breakdown: Dict[str, float]


def _rebalance_legs(d: Delta) -> List[Tuple[str, float]]:
    """The (side, trade_value) fills a single non-suppressed Delta produces.

    Mirrors _execute_deltas exactly: OPEN/SCALE_UP/SCALE_DOWN/CLOSE are one
    leg; FLIP is two (exit the held side, then enter the target side)."""
    if d.action == 'OPEN':
        return [('BUY' if d.target_side == 'LONG' else 'SELL', d.target_cap)]
    if d.action == 'CLOSE':
        return [('SELL' if d.held_side == 'LONG' else 'BUY', abs(d.held_cap))]
    if d.action == 'SCALE_UP':
        return [('BUY' if d.target_side == 'LONG' else 'SELL', abs(d.delta_cap))]
    if d.action == 'SCALE_DOWN':
        return [('SELL' if d.held_side == 'LONG' else 'BUY', abs(d.delta_cap))]
    if d.action == 'FLIP':
        return [
            ('SELL' if d.held_side == 'LONG' else 'BUY', abs(d.held_cap)),
            ('BUY' if d.target_side == 'LONG' else 'SELL', d.target_cap),
        ]
    return []


def summarize_rebalance(deltas: List[Delta], trade_date: date,
                        slippage_bp: float = SLIPPAGE_BP) -> RebalanceMetrics:
    """Recompute the cost decomposition for one rebalance from its Deltas.

    Suppressed deltas contribute nothing (they are not executed). Fees come
    from the canonical futures_fees model per leg; slippage is slippage_bp/side
    on each leg's notional — the two are never conflated.
    """
    breakdown = {'brokerage': 0.0, 'stt': 0.0, 'exchange_txn': 0.0,
                 'sebi_fee': 0.0, 'stamp_duty': 0.0, 'gst': 0.0}
    fees_total = 0.0
    slippage_total = 0.0
    traded_value_total = 0.0
    slip_rate = slippage_bp / 10_000.0

    for d in deltas:
        if d.suppressed:
            continue
        for side, tv in _rebalance_legs(d):
            f = _calc_fees(side=side, trade_value=tv, trade_date=trade_date)
            fees_total += f.total
            slippage_total += slip_rate * tv
            traded_value_total += tv
            for k in breakdown:
                breakdown[k] += getattr(f, k)

    executions = [d for d in deltas if not d.suppressed]
    n_exits = sum(1 for d in executions
                  if d.action in ('CLOSE', 'FLIP', 'SCALE_DOWN'))
    n_entries = sum(1 for d in executions
                    if d.action in ('OPEN', 'SCALE_UP', 'FLIP'))

    return RebalanceMetrics(
        n_exits=n_exits,
        n_entries=n_entries,
        traded_value_total=traded_value_total,
        fees_total=fees_total,
        slippage_total=slippage_total,
        fee_breakdown=breakdown,
    )


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
                 bhavcopy_db_path: Optional[str] = None,
                 metrics_sink: Optional[Callable] = None,
                 signals_db_path: Optional[str] = None,
                 max_positions_per_leg: Optional[int] = None,
                 exit_policy: Optional[ExitPolicy] = None,
                 recycle_exit_capital: bool = True,
                 trade_sink: Optional[Callable] = None,
                 sector_csv_path: Optional[str] = None,
                 max_per_sector: Optional[int] = None):
        self._facts_db = Path(facts_db_path)
        self._exec = execution_handler
        self._gross_exposure_policy = gross_exposure_policy
        self._max_positions = max_positions_per_leg
        self._bhavcopy_db = Path(bhavcopy_db_path) if bhavcopy_db_path else None
        self._metrics_sink = metrics_sink
        self._signals_db = Path(signals_db_path) if signals_db_path else None
        self._exit_policy = exit_policy
        self._recycle_exit_capital = recycle_exit_capital
        self._trade_sink = trade_sink
        self._max_per_sector = max_per_sector
        self._sector_map = None
        if sector_csv_path:
            self._sector_map = self._load_sectors(Path(sector_csv_path))
        if self._bhavcopy_db is None:
            _logger.warning(
                "CarryRebalancerHook: bhavcopy_db_path not provided — "
                "ADV capping disabled for this instance"
            )
        if self._exit_policy is not None and self._signals_db is None:
            _logger.warning(
                "CarryRebalancerHook: exit_policy set but signals_db_path not "
                "provided — position P&L tracking disabled, exit policy will "
                "always see cumulative_return=0.0"
            )
        self._last_date: Optional[date] = None
        self._prev_formation_date: Optional[date] = None
        self._formation_dates: set = set()
        self._book_longs: Dict[str, float] = {}
        self._book_shorts: Dict[str, float] = {}
        self._position_entries: Dict[str, dict] = {}  # underlying -> {entry_date, side, cum_ret}
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
            "SELECT underlying, z_carry_neut, quintile, eligible, "
            "raw_z, basis_reverting "
            "FROM carry_facts WHERE formation_date = ?",
            [fdate]
        ).fetchall()
        con.close()

        facts = [(r[0], float(r[1])) for r in rows if r[3]]  # eligible only
        facts_full = [(r[0], float(r[1]), float(r[2]) if r[4] else float(r[1]),
                       r[2], r[5]) for r in rows if r[3]]
        # facts_full: (underlying, z, raw_z, quintile, basis_reverting)

        # Load ADV from bhavcopy and filter
        adva: Dict[str, float] = {}
        if self._bhavcopy_db and self._bhavcopy_db.exists() and facts:
            adva = self._load_adva(facts, fdate)
            facts = [f for f in facts if f[0] in adva]

        if self._signals_db and self._signals_db.exists() and facts:
            fwd_names = self._load_fwd_names(facts, fdate)
            facts = [f for f in facts if f[0] in fwd_names]

        if self._max_positions is not None and len(facts) > 2 * self._max_positions:
            sorted_facts = sorted(facts, key=lambda r: r[1])
            facts = sorted_facts[:self._max_positions] + sorted_facts[-self._max_positions:]

        if len(facts) < 5:
            return

        # Update position P&L from prior formation's forward returns
        if (self._prev_formation_date is not None and self._signals_db is not None
                and self._signals_db.exists() and self._exit_policy is not None):
            self._update_position_pnl(self._prev_formation_date)

        target = compute_target_book(facts, gross_exposure, adva, nq=self._max_positions,
                                      sector_map=self._sector_map,
                                      max_per_sector=self._max_per_sector)
        new_longs, new_shorts, deltas = rebalance_book(
            target, self._book_longs, self._book_shorts, BAND_SIGMA)

        # Apply exit policy overrides
        if self._exit_policy is not None:
            z_map = {f[0]: f[1] for f in facts}
            deltas = self._apply_exit_policy(deltas, fdate, z_map)

        metrics = self._execute_deltas(deltas, target, fdate)

        self._book_longs = new_longs
        self._book_shorts = new_shorts
        self._prev_formation_date = fdate

        # Call trade sink (write-only — never blocks execution)
        if self._trade_sink is not None:
            executions = [d for d in deltas if not d.suppressed]
            self._trade_sink(fdate, executions, dict(self._position_entries),
                             facts_full)

        # Track position entries for exit policy
        if self._exit_policy is not None:
            held_now = set(new_longs) | set(new_shorts)
            for u in held_now:
                if u not in self._position_entries:
                    self._position_entries[u] = {
                        "entry_date": fdate, "cum_ret": 0.0,
                        "side": 'LONG' if u in new_longs else 'SHORT',
                    }
            for u in list(self._position_entries):
                if u not in held_now:
                    del self._position_entries[u]

        if self._metrics_sink is not None:
            held_target = TargetBook(formation_date=fdate, longs=new_longs,
                                      shorts=new_shorts)
            self._metrics_sink(fdate, deltas, held_target, metrics, capital_state)

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

    def _load_fwd_names(self, facts: list, formation_date: date) -> set:
        """HISTORICAL-REPLAY-ONLY — filters on signals.fwd_ret_1m IS NOT NULL.

        This field does not exist for a live formation whose forward period
        has not yet occurred. Enabling this in a forward/live runner will
        silently drop every name. ``signals_db_path`` must remain ``None``
        in carry_paper_runner.py and any live runner.
        """
        ulist = ", ".join(f"'{f[0]}'" for f in facts)
        con = duckdb.connect(str(self._signals_db), read_only=True)
        rows = con.execute(f"""
            SELECT underlying FROM signals
            WHERE formation_date = DATE '{formation_date}'
              AND underlying IN ({ulist})
              AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
        """).fetchall()
        con.close()
        return {r[0] for r in rows}

    @staticmethod
    def _load_sectors(path: Path) -> Dict[str, str]:
        import csv
        sectors = {}
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    sectors[row["symbol"]] = row["sector"]
        except Exception:
            pass
        return sectors

    @staticmethod
    def _underlying_from_sym(sym: str) -> str:
        if sym.endswith("FUT"):
            sym = sym[:-3]
        return sym

    def _update_position_pnl(self, prior_fdate: date):
        """Update cumulative returns for held positions using signal forward returns."""
        held = set(self._book_longs) | set(self._book_shorts)
        if not held:
            return
        ulist = ", ".join(f"'{u}'" for u in held)
        con = duckdb.connect(str(self._signals_db), read_only=True)
        rows = con.execute(f"""
            SELECT underlying, fwd_ret_1m
            FROM signals WHERE formation_date = DATE '{prior_fdate}'
            AND underlying IN ({ulist}) AND fwd_ret_1m IS NOT NULL
        """).fetchall()
        con.close()
        fwd_map = {r[0]: float(r[1]) for r in rows}

        for u in held:
            daily_ret = fwd_map.get(u, 0.0)
            if u in self._book_shorts:
                daily_ret = -daily_ret
            entry = self._position_entries.get(u)
            if entry is not None:
                entry["cum_ret"] = (1 + entry["cum_ret"]) * (1 + daily_ret) - 1

    def _apply_exit_policy(self, deltas: List[Delta], fdate: date,
                           z_map: Dict[str, float]) -> List[Delta]:
        """Override HOLD/SCALE deltas with CLOSE when exit policy fires."""
        modified = []
        # Track which underlyings have a non-CLOSE/FLIP delta
        seen = {d.underlying for d in deltas if d.action not in ('CLOSE', 'FLIP')}

        for d in deltas:
            if d.action in ('CLOSE', 'FLIP'):
                modified.append(d)
                continue

            u = d.underlying
            if u not in self._book_longs and u not in self._book_shorts:
                modified.append(d)
                continue

            side = 'LONG' if u in self._book_longs else 'SHORT'
            entry = self._position_entries.get(u)
            if entry is None:
                entry = {"entry_date": self._prev_formation_date,
                         "side": side, "cum_ret": 0.0}
                self._position_entries[u] = entry

            days_held = (fdate - entry["entry_date"]).days if entry.get("entry_date") else 0
            held_cap = self._book_longs.get(u) or self._book_shorts.get(u) or d.held_cap
            pos = PositionState(
                underlying=u, side=side,
                entry_date=entry.get("entry_date", fdate),
                days_held=days_held,
                cumulative_return=entry.get("cum_ret", 0.0),
                current_z=z_map.get(u, 0.0),
                current_cap=held_cap,
            )
            decision = self._exit_policy.evaluate(pos)

            if decision in (ExitDecision.EXIT_TAKE_PROFIT, ExitDecision.EXIT_STOP):
                reason = 'EXIT_TP' if decision == ExitDecision.EXIT_TAKE_PROFIT else 'EXIT_SL'
                modified.append(Delta(
                    underlying=u, target_side=None, target_cap=0.0,
                    held_side=side, held_cap=held_cap, delta_cap=-held_cap,
                    action='CLOSE', suppressed=False, exit_reason=reason,
                ))
                _logger.info("Exit policy: %s %s — %s (cum_ret=%.4f%%)",
                             side, u, decision.value, entry["cum_ret"] * 100)
            else:
                modified.append(d)

        # Evaluate held positions that have NO delta (held with NOOP)
        for u, cap in {**self._book_longs, **self._book_shorts}.items():
            if u in seen:
                continue
            side = 'LONG' if u in self._book_longs else 'SHORT'
            entry = self._position_entries.get(u)
            if entry is None:
                self._position_entries[u] = {
                    "entry_date": self._prev_formation_date or fdate,
                    "side": side, "cum_ret": 0.0,
                }
                entry = self._position_entries[u]
            days_held = (fdate - entry["entry_date"]).days if entry.get("entry_date") else 0
            pos = PositionState(
                underlying=u, side=side,
                entry_date=entry.get("entry_date", fdate),
                days_held=days_held,
                cumulative_return=entry.get("cum_ret", 0.0),
                current_z=z_map.get(u, 0.0),
                current_cap=cap,
            )
            decision = self._exit_policy.evaluate(pos)
            if decision in (ExitDecision.EXIT_TAKE_PROFIT, ExitDecision.EXIT_STOP):
                reason = 'EXIT_TP' if decision == ExitDecision.EXIT_TAKE_PROFIT else 'EXIT_SL'
                modified.append(Delta(
                    underlying=u, target_side=None, target_cap=0.0,
                    held_side=side, held_cap=cap, delta_cap=-cap,
                    action='CLOSE', suppressed=False, exit_reason=reason,
                ))
                _logger.info("Exit policy (NOOP): %s %s — %s (cum_ret=%.4f%%)",
                             side, u, decision.value, entry["cum_ret"] * 100)

        return modified

    def _execute_deltas(self, deltas: List[Delta], target: TargetBook,
                        trade_date: date):
        executions = [d for d in deltas if not d.suppressed]
        if not executions:
            return

        tracker = self._exec.position_tracker
        ts = datetime.combine(trade_date, time.min)

        # Phase 1: exits first
        for d in executions:
            if d.action in ('CLOSE', 'FLIP'):
                side = 'SELL' if d.held_side == 'LONG' else 'BUY'
                trade_val = abs(d.held_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)

            if d.action == 'SCALE_DOWN':
                side = 'SELL' if d.held_side == 'LONG' else 'BUY'
                trade_val = abs(d.delta_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)

        # Phase 2: entries
        for d in executions:
            if d.action in ('OPEN',):
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = d.target_cap
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)

            if d.action == 'SCALE_UP':
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = abs(d.delta_cap)
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)

            if d.action == 'FLIP':
                side = 'BUY' if d.target_side == 'LONG' else 'SELL'
                trade_val = d.target_cap
                fill = self._build_fill(d.underlying, side, trade_val, trade_date, ts)
                tracker.update_from_fill(fill)

        metrics = summarize_rebalance(executions, trade_date)
        _logger.info("Rebalance done: %d exits, %d entries, "
                      "~Rs %.0f fees + ~Rs %.0f slippage",
                      metrics.n_exits, metrics.n_entries,
                      metrics.fees_total, metrics.slippage_total)
        return metrics

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
