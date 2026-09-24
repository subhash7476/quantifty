"""Stage-1 panel: calendar, ratio-adjusted bars, PIT membership and G-7 events (freeze §6, §7).

`load_panel` is the only function in P-3 that reads the stores. It reads nothing after Z and nothing
before the window start. It is called only by the guarded entry point.

- Calendar 𝒟: `trading_calendar` in [window start, Z] minus `NON_SESSIONS`.
- Panel entities: every entity that is a Nifty-100 PIT member on at least one session of 𝒟.
  Membership is `n100_membership`, half-open [valid_from, valid_to); symbol → entity through
  `symbol_entity_intervals`, half-open, time-aware. `universe_eligibility` is never read.
- Bars: `equity_bhavcopy` series EQ and BE, as traded. A duplicate (entity, session) hard-fails.
- Ratio basis: BONUS and SPLIT factors only (special dividends are G-7 events, not adjustments).
  Adjusted = raw × Π factor over ex-dates in (t, Z]. That is the basis dated at Z, which gives the
  same comparisons as the as-of-t basis (v0.8 §3.10, basis).
- G-7 ex-dates: the frozen P-2 CSV rows with `g7_event = True`, never re-derived.
"""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

from scripts.ptms.gann.calendar import Calendar
from scripts.ptms.gann.constants import NON_SESSIONS, RATIO_ACTION_TYPES, SAMPLE_END_Z, WINDOW_START

ROOT = Path(__file__).resolve().parents[3]
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
N100_DB = ROOT / "data" / "isd" / "n100_membership.duckdb"
G7_CSV = ROOT / "docs" / "reports" / "ptms" / "PTMS_GANN_P2_CA_EVENTS_2026-09-19.csv"


@dataclass(frozen=True)
class Panel:
    cal: Calendar
    entities: tuple
    high: np.ndarray         # (T, N) ratio-adjusted, NaN = no bar
    low: np.ndarray
    close: np.ndarray
    close_raw: np.ndarray    # as traded (D-PL only)
    member: np.ndarray       # (T, N) bool, PIT membership on the session
    g7_ord: tuple            # per column: sorted np.ndarray of G-7 ex-date ordinals


def adjust(raw: np.ndarray, sessions, factors_by_col) -> np.ndarray:
    """raw (T, N) × Π factor over the column's ex-dates strictly after each session."""
    out = raw.copy()
    for j, events in factors_by_col.items():
        for ex_date, factor in events:
            out[np.array([d < ex_date for d in sessions]), j] *= factor
    return out


def g7_by_entity(path=G7_CSV):
    events = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["g7_event"] == "True":
                events.setdefault(row["entity"], set()).add(row["ex_date"])
    return events


def index_intervals(rows):
    by_symbol = {}
    for symbol, f, t, e in rows:
        by_symbol.setdefault(symbol, []).append((f, t, e))
    return by_symbol


def _entity_at(intervals, symbol, day):
    hits = [e for f, t, e in intervals.get(symbol, ()) if f <= day and (t is None or day < t)]
    if len(hits) > 1:
        raise SystemExit(f"{symbol} {day}: {len(hits)} entity intervals")
    return hits[0] if hits else None


def _factor_entity(intervals, symbol, ex_date):
    entity = _entity_at(intervals, symbol, ex_date)
    if entity is not None:
        return entity
    owners = {e for _, _, e in intervals.get(symbol, ())}
    if len(owners) > 1:
        raise SystemExit(f"orphan factor on recycled ticker {symbol} {ex_date}")
    return owners.pop() if owners else None


def load_panel(eq_db=EQ_DB, n100_db=N100_DB, g7_csv=G7_CSV) -> Panel:
    lo, hi = WINDOW_START, SAMPLE_END_Z
    eq = duckdb.connect(str(eq_db), read_only=True)
    sessions = [d for (d,) in eq.execute(
        "SELECT trade_date FROM trading_calendar WHERE trade_date BETWEEN ? AND ? ORDER BY 1", [lo, hi]).fetchall()
        if d not in NON_SESSIONS]
    cal = Calendar(sessions)
    intervals = index_intervals(eq.execute(
        "SELECT symbol, valid_from, valid_to, entity FROM symbol_entity_intervals").fetchall())

    n1 = duckdb.connect(str(n100_db), read_only=True)
    spans = n1.execute("SELECT symbol, valid_from, valid_to FROM n100_membership "
                       "WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)", [hi, lo]).fetchall()
    n1.close()
    member_cells = set()
    for symbol, vf, vt in spans:
        for d in sessions:
            if vf <= d and (vt is None or d < vt):
                entity = _entity_at(intervals, symbol, d)
                if entity is None:
                    raise SystemExit(f"member {symbol} on {d} has no entity interval")
                member_cells.add((entity, d))
    entities = tuple(sorted({e for e, _ in member_cells}))
    col = {e: j for j, e in enumerate(entities)}
    T, N = len(sessions), len(entities)

    raw = {k: np.full((T, N), np.nan) for k in ("high", "low", "close")}
    seen = set()
    rows = eq.execute("SELECT trade_date, symbol, high, low, close FROM equity_bhavcopy "
                      "WHERE series IN ('EQ', 'BE') AND trade_date BETWEEN ? AND ?", [lo, hi]).fetchall()
    panel_symbols = {s for s, ivs in intervals.items() if any(e in col for _, _, e in ivs)}
    for d, symbol, h, l, c in rows:
        if d not in cal.index or symbol not in panel_symbols:
            continue
        entity = _entity_at(intervals, symbol, d)
        if entity not in col:
            continue
        if (entity, d) in seen:
            raise SystemExit(f"duplicate bar {entity} {d}")
        seen.add((entity, d))
        t, j = cal.index[d], col[entity]
        raw["high"][t, j], raw["low"][t, j], raw["close"][t, j] = h, l, c

    placeholders = ", ".join("?" for _ in RATIO_ACTION_TYPES)
    factors = {}
    for symbol, ex_date, factor in eq.execute(
            f"SELECT symbol, ex_date, factor FROM adjustment_factors WHERE action_type IN ({placeholders}) "
            "AND ex_date > ? AND ex_date <= ?", [*RATIO_ACTION_TYPES, lo, hi]).fetchall():
        entity = _factor_entity(intervals, symbol, ex_date)
        if entity in col:
            factors.setdefault(col[entity], []).append((ex_date, factor))
    eq.close()

    member = np.zeros((T, N), dtype=bool)
    for entity, d in member_cells:
        member[cal.index[d], col[entity]] = True
    g7 = g7_by_entity(g7_csv)
    g7_ord = tuple(np.array(sorted(date.fromisoformat(x).toordinal() for x in g7.get(e, ())), dtype=np.int64)
                   for e in entities)
    return Panel(cal, entities, adjust(raw["high"], sessions, factors), adjust(raw["low"], sessions, factors),
                 adjust(raw["close"], sessions, factors), raw["close"], member, g7_ord)
