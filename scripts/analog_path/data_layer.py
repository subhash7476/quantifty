"""Era-consistent Nifty-50 session loader for the intraday analog research.

One session = one date = one 1m file. A loaded session exposes the frozen
14-point 09:15->12:30 state (A), the 13-interval return state (B), the
diagnostic return-neutralized shape state (C), the five frozen forward
horizons, and MFE/MAE — all constructed from that day's bars alone
(no cross-day reads, by construction of `read_day`).

Timestamp convention (frozen, audit-verified):
  - end-labelled sessions: first bar 09:16 covers 09:15-09:16; the bar
    stamped t closes AT t.
  - start-labelled sessions: first bar 09:15; the bar stamped t opens AT t.
  - The operational era follows the OBSERVED first-bar stamp (operator
    decision 2026-09-09, AP-D4), not the calendar date: 09:16 -> vendor
    rule, 09:15 -> native rule. This admits the 20 Jan-2023 sessions whose
    provenance metadata disagreed with their actual bar labelling.
  - price at grid time t = close of the bar covering the minute ending at t
    (vendor: bar stamped t; native: bar stamped t-1min), except 09:15,
    which is the first bar's open (A-track D3 opening print).
  - close = close of the bar stamped 15:30 (vendor rule) / 15:29 (native
    rule) — the session's final minute, robust to flat feed-extension tails.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb
import numpy as np

from scripts.analog_path import config

CANDLE_DIR_1M = Path(__file__).resolve().parents[2] / "data" / "market_data" / "nse" / "candles" / "1m"

_BAR_COLS = ("timestamp", "open", "high", "low", "close", "is_synthetic")


def read_day(d: date) -> list[tuple[datetime, float, float, float, float, bool]]:
    """Raw 1m bars for the frozen instrument on date `d`, sorted by timestamp.

    Reads exactly the contract columns (mirrors scripts/isd/read_1m.py), so
    schema drift (e.g. the `instrument_key` column inserted 2026-03-05) is
    handled in one place.
    """
    path = CANDLE_DIR_1M / f"{d.isoformat()}.duckdb"
    if not path.exists():
        return []
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT timestamp, open, high, low, close, "
            "       COALESCE(is_synthetic, false) "
            "FROM candles WHERE symbol = ? ORDER BY timestamp",
            [config.INSTRUMENT]).fetchall()
    finally:
        con.close()
    return [(r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), bool(r[5]))
            for r in rows]


def price_at(bars: list, t: time, labeling: str, first_bar: tuple) -> float:
    """Frozen era-consistent price rule; None if the required bar is absent.

    `labeling` is the OBSERVED bar-labelling mode ("vendor" = end-labelled,
    "native" = start-labelled). 09:15 is the first bar's open (A-track D3)
    in both modes.
    """
    if t == time(9, 15):
        return float(first_bar[1]) if first_bar is not None and first_bar[1] > 0 else None
    stamp = t if labeling == "vendor" else _minus_one_minute(t)
    for ts, o, h, lo, c, _syn in bars:
        if ts.time() == stamp:
            return float(c) if c > 0 else None
    return None


def _minus_one_minute(t: time) -> time:
    return (datetime(2000, 1, 1, t.hour, t.minute) - timedelta(minutes=1)).time()


def _check_integrity(d: date, bars: list) -> tuple[list[str], str | None]:
    defects = []
    if not bars:
        return ["no_rows"], None
    first = bars[0][0]
    if first.date() != d:
        defects.append("first_bar_wrong_date")
    labeling = config.labeling_of(first.time())
    if labeling is None:
        defects.append(f"first_bar_stamp_{first:%H:%M}")
    if len(bars) < config.MIN_BARS:
        defects.append(f"short_session_{len(bars)}")
    morning = sum(1 for ts, *_ in bars if time(9, 15) <= ts.time() <= time(12, 31))
    if morning < config.MIN_MORNING_BARS:
        defects.append(f"morning_incomplete_{morning}")
    stamps = [ts for ts, *_ in bars]
    if any(a >= b for a, b in zip(stamps, stamps[1:])):
        defects.append("non_monotonic_or_dup")
    for ts, o, h, lo, c, _syn in bars:
        if min(o, h, lo, c) <= 0:
            defects.append("nonpositive_price")
            break
        if h < max(o, c) - 1e-9 or lo > min(o, c) + 1e-9:
            defects.append("ohlc_violation")
            break
    return defects, labeling


@dataclass
class Session:
    date: date
    era: str                          # operational era from OBSERVED labelling
    provenance_era: str               # date-based era (A-track boundary)
    bars: list = field(repr=False)
    defects: list[str]
    open: float
    grid_prices: np.ndarray           # 14 prices at 09:15..12:30
    path_state: np.ndarray            # A: 14-dim, P(t)/P(09:15) - 1, first == 0
    interval_state: np.ndarray        # B: 13-dim interval returns
    shape_state: np.ndarray           # C: 14-dim linear detrend of A (diagnostic)
    p_1230: float
    outcomes: dict                    # horizon key -> return (fraction)
    mfe: float                        # max cumulative return after cutoff
    mae: float                        # min cumulative return after cutoff

    @property
    def valid(self) -> bool:
        return not self.defects

    @property
    def open_to_1230(self) -> float:
        return self.p_1230 / self.open - 1.0


def state_c_from_path(path: np.ndarray) -> np.ndarray:
    """Diagnostic State C: the linear detrend of State A.

    C(t_i) = A(t_i) - (i/13) * A(t_13), i = 0..13.
    First and last elements are exactly 0; the total open->12:30 return is
    removed, leaving the deviation from the constant-rate path.
    """
    path = np.asarray(path, dtype=float)
    ramp = np.arange(14, dtype=float) / 13.0 * path[13]
    return path - ramp


def load_session(d: date) -> Session | None:
    """Frozen session load + integrity check + state construction.

    Returns None only when no rows exist; otherwise returns a Session whose
    `defects` list carries every failed integrity check (a session is usable
    iff `valid`).
    """
    bars = read_day(d)
    if not bars:
        return None
    provenance = config.era_of(d)
    defects, labeling = _check_integrity(d, bars)
    first_bar = bars[0]
    open_px = first_bar[1] if first_bar[1] > 0 else float("nan")

    if labeling is not None:
        grid_prices = np.asarray(
            [price_at(bars, t, labeling, first_bar) for t in config.GRID_TIMES],
            dtype=float)
        if np.any(~np.isfinite(grid_prices)) or np.any(grid_prices <= 0):
            defects.append("grid_bar_missing")
        close_stamp = config.close_stamp_of(labeling)
        close_bar = next((b for b in reversed(bars) if b[0].time() == close_stamp), None)
        if close_bar is None or close_bar[4] <= 0:
            defects.append("close_bar_missing")
    else:
        grid_prices = np.full(14, np.nan)
        close_bar = None

    p_1230 = float(grid_prices[-1]) if np.isfinite(grid_prices[-1]) else float("nan")

    outcomes = {}
    for key, t in config.HORIZON_TIMES.items():
        if t is None:
            px = close_bar[4] if close_bar is not None else None
        elif labeling is not None:
            px = price_at(bars, t, labeling, first_bar)
        else:
            px = None
        if px is None or px <= 0 or not np.isfinite(p_1230) or p_1230 <= 0:
            outcomes[key] = np.nan
            defects.append(f"horizon_bar_missing_{key}")
        else:
            outcomes[key] = float(px) / p_1230 - 1.0

    path_state = np.full(14, np.nan)
    interval_state = np.full(13, np.nan)
    shape_state = np.full(14, np.nan)
    if open_px > 0 and np.all(np.isfinite(grid_prices)):
        path_state = grid_prices / open_px - 1.0
        interval_state = grid_prices[1:] / grid_prices[:-1] - 1.0
        shape_state = state_c_from_path(path_state)

    mfe = mae = float("nan")
    if labeling is not None and np.isfinite(p_1230) and p_1230 > 0 \
            and close_bar is not None:
        close_stamp = config.close_stamp_of(labeling)
        cutoff_t = next(b[0].time() for b in reversed(bars)
                        if b[0].time() <= time(12, 30))
        rets = [b[4] / p_1230 - 1.0 for b in bars
                if cutoff_t < b[0].time() <= close_stamp and b[4] > 0]
        if rets:
            mfe = float(np.max(rets))
            mae = float(np.min(rets))

    return Session(d, labeling or "unknown", provenance, bars, defects, open_px,
                   grid_prices, path_state, interval_state, shape_state,
                   p_1230, outcomes, mfe, mae)


def build_outcome_vector(sessions: list[Session], horizon: str) -> np.ndarray:
    return np.asarray([s.outcomes[horizon] for s in sessions], dtype=float)
