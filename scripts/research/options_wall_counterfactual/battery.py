"""Options-Wall counterfactual structure battery.

Replays the wall chain snapshots (data/options/wall_chain_snapshots/*.duckdb) and
prices a grid of option structures at fixed entry times, marking them off live
bid/ask mids, with real fees (core/execution/options/fees.py). Descriptive only:
nine sessions is anecdote, not a sample. Nothing here is a gated read.
"""
from __future__ import annotations

import glob
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.execution.options.fees import option_order_fees  # noqa: E402

SNAP_DIR = "data/options/wall_chain_snapshots"
SCAN_DB = "data/options/wall_scan_results.duckdb"
OUT_CSV = "data/scratch/options_wall_counterfactual.csv"

ENTRY_TIMES = [time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30), time(12, 0),
               time(12, 30), time(13, 0), time(13, 30), time(14, 0), time(14, 30)]
INTRADAY_EXIT = time(15, 15)
OVERNIGHT_ENTRY = time(15, 10)
OVERNIGHT_EXIT = time(9, 35)
SNAP_TOLERANCE = timedelta(minutes=3)
TREND_MIN_PCT = 0.10

UNDERLYINGS = ["NSE_INDEX|Nifty 50", "BSE_INDEX|SENSEX", "NSE_INDEX|Nifty Bank"]

# (side, type, offset % of spot). Directional templates are the bull case; the bear
# case mirrors CE<->PE and negates offsets.
NONDIR = {
    "iron_fly":        [("SELL", "CE", 0.0), ("SELL", "PE", 0.0), ("BUY", "CE", 1.5), ("BUY", "PE", -1.5)],
    "short_straddle":  [("SELL", "CE", 0.0), ("SELL", "PE", 0.0)],
    "short_strangle":  [("SELL", "CE", 1.0), ("SELL", "PE", -1.0)],
    "iron_condor":     [("SELL", "CE", 1.0), ("SELL", "PE", -1.0), ("BUY", "CE", 2.0), ("BUY", "PE", -2.0)],
    "long_straddle":   [("BUY", "CE", 0.0), ("BUY", "PE", 0.0)],
    "long_strangle":   [("BUY", "CE", 1.0), ("BUY", "PE", -1.0)],
}
DIR_BULL = {
    "debit_spread":   [("BUY", "CE", 0.0), ("SELL", "CE", 1.0)],
    "credit_spread":  [("SELL", "PE", -1.0), ("BUY", "PE", -2.0)],
    "long_atm":       [("BUY", "CE", 0.0)],
}
DIRECTION_RULES = ["trend_open", "contra_open", "prev_day", "bull", "bear"]


def mirror(legs):
    flip = {"CE": "PE", "PE": "CE"}
    return [(s, flip[t], -o) for s, t, o in legs]


@dataclass
class Book:
    ts: np.ndarray
    spot: np.ndarray
    strikes: List[float]
    bid: Dict[Tuple[float, str], np.ndarray]
    ask: Dict[Tuple[float, str], np.ndarray]
    lot: int
    expiry: date
    session_open: float
    regime: pd.Series


def load_book(path: str, underlying: str, regime_df: pd.DataFrame) -> Optional[Book]:
    c = duckdb.connect(path, read_only=True)
    df = c.execute("""select snapshot_timestamp ts, strike_price k, option_type ot, best_bid b, best_ask a,
                             underlying_ltp spot, lot_size lot, expiry_date exp
                      from option_chain_snapshot where underlying_symbol = ?
                        and abs(strike_price/underlying_ltp - 1) < 0.035""", [underlying]).df()
    c.close()
    if df.empty:
        return None
    df["b"] = df["b"].where(df["b"] > 0)
    df["a"] = df["a"].where(df["a"] > 0)
    ts_idx = np.sort(df["ts"].unique())
    spot = df.groupby("ts")["spot"].max().reindex(ts_idx).to_numpy()
    bid, ask = {}, {}
    for (k, ot), g in df.groupby(["k", "ot"]):
        g = g.drop_duplicates("ts").set_index("ts").reindex(ts_idx)
        bid[(k, ot)] = g["b"].to_numpy(dtype=float)
        ask[(k, ot)] = g["a"].to_numpy(dtype=float)
    reg = regime_df[regime_df.underlying == underlying].set_index("ts")["regime"].sort_index()
    return Book(ts=ts_idx, spot=spot, strikes=sorted({k for k, _ in bid}), bid=bid, ask=ask,
                lot=int(df["lot"].iloc[0]), expiry=pd.Timestamp(df["exp"].iloc[0]).date(),
                session_open=float(spot[0]), regime=reg)


def snap_at(book: Book, when: datetime) -> Optional[int]:
    i = int(np.searchsorted(book.ts, np.datetime64(when)))
    if i >= len(book.ts):
        return None
    if pd.Timestamp(book.ts[i]) - pd.Timestamp(when) > SNAP_TOLERANCE:
        return None
    return i


def regime_at(book: Book, when: datetime) -> str:
    if book.regime.empty:
        return "n/a"
    i = book.regime.index.searchsorted(when, side="right") - 1
    return "n/a" if i < 0 else str(book.regime.iloc[i])


def nearest_quoted(book: Book, i: int, target: float, ot: str) -> Optional[float]:
    cands = [k for k in book.strikes if (k, ot) in book.bid
             and not np.isnan(book.bid[(k, ot)][i]) and not np.isnan(book.ask[(k, ot)][i])]
    return min(cands, key=lambda k: abs(k - target)) if cands else None


@dataclass
class Leg:
    side: str
    ot: str
    k: float
    entry_mid: float
    entry_cross: float


def open_legs(book: Book, i: int, template) -> Optional[List[Leg]]:
    spot = book.spot[i]
    legs, used = [], set()
    for side, ot, off in template:
        k = nearest_quoted(book, i, spot * (1 + off / 100.0), ot)
        if k is None or (k, ot) in used:
            return None
        used.add((k, ot))
        b, a = book.bid[(k, ot)][i], book.ask[(k, ot)][i]
        legs.append(Leg(side, ot, k, (a + b) / 2.0, a if side == "BUY" else b))
    return legs


def leg_mark(book: Book, leg: Leg, i: int) -> Tuple[Optional[float], Optional[float]]:
    if (leg.k, leg.ot) not in book.bid:
        return None, None
    b, a = book.bid[(leg.k, leg.ot)][i], book.ask[(leg.k, leg.ot)][i]
    if np.isnan(b) or np.isnan(a):
        return None, None
    mid = (a + b) / 2.0
    cross = b if leg.side == "BUY" else a
    return mid, cross


def pnl_path(book: Book, legs: List[Leg], i0: int, i1: int, lot: int) -> np.ndarray:
    out = np.zeros(i1 - i0 + 1)
    for leg in legs:
        b, a = book.bid[(leg.k, leg.ot)][i0:i1 + 1], book.ask[(leg.k, leg.ot)][i0:i1 + 1]
        mid = (a + b) / 2.0
        sgn = 1.0 if leg.side == "BUY" else -1.0
        out += sgn * (mid - leg.entry_mid)
    if np.isnan(out).any():
        out = pd.Series(out).ffill().fillna(0.0).to_numpy()
    return out * lot


def fees_for(prices: List[float], sides: List[str], lot: int, d: date) -> float:
    return sum(option_order_fees(premium=p, quantity=lot, side=s, trade_date=d).total
               for p, s in zip(prices, sides))


def evaluate(book: Book, legs: List[Leg], i0: int, i1: int, exit_book: Book, d0: date, d1: date,
             tp_sl: bool) -> Optional[dict]:
    lot = book.lot
    entry_cf_mid = sum((l.entry_mid if l.side == "SELL" else -l.entry_mid) for l in legs) * lot
    entry_cf_cross = sum((l.entry_cross if l.side == "SELL" else -l.entry_cross) for l in legs) * lot
    entry_fees = fees_for([l.entry_mid for l in legs], [l.side for l in legs], lot, d0)
    exit_i, reason = i1, "time"
    path = pnl_path(book, legs, i0, i1, lot) if exit_book is book else None
    if tp_sl and path is not None:
        prem = abs(entry_cf_mid)
        tp, sl = (0.5 * prem, -2.0 * prem) if entry_cf_mid > 0 else (0.5 * prem, -0.5 * prem)
        hit = np.where((path >= tp) | (path <= sl))[0]
        if len(hit):
            exit_i = i0 + int(hit[0])
            reason = "tp" if path[hit[0]] >= tp else "sl"
    marks = [leg_mark(exit_book, l, exit_i) for l in legs]
    if any(m[0] is None for m in marks):
        return None
    close_sides = ["BUY" if l.side == "SELL" else "SELL" for l in legs]
    exit_cf_mid = sum((-m[0] if l.side == "SELL" else m[0]) for l, m in zip(legs, marks)) * lot
    exit_cf_cross = sum((-m[1] if l.side == "SELL" else m[1]) for l, m in zip(legs, marks)) * lot
    exit_fees = fees_for([m[0] for m in marks], close_sides, lot, d1)
    gross_mid = entry_cf_mid + exit_cf_mid
    gross_cross = entry_cf_cross + exit_cf_cross
    fees = entry_fees + exit_fees
    return dict(entry_cf=entry_cf_mid, gross_mid=gross_mid, net_mid=gross_mid - fees,
                net_cross=gross_cross - fees, fees=fees, exit_reason=reason,
                mfe=float(path.max()) if path is not None else np.nan,
                mae=float(path.min()) if path is not None else np.nan,
                exit_ts=pd.Timestamp(exit_book.ts[exit_i]),
                legs=";".join(f"{l.side} {l.ot} {l.k:g}@{l.entry_mid:.2f}" for l in legs))


def direction(rule: str, book: Book, i: int, prev_dir: Optional[int]) -> Optional[int]:
    if rule == "bull":
        return 1
    if rule == "bear":
        return -1
    if rule == "prev_day":
        return prev_dir
    mv = (book.spot[i] / book.session_open - 1) * 100
    if abs(mv) < TREND_MIN_PCT:
        return None
    d = 1 if mv > 0 else -1
    return d if rule == "trend_open" else -d


def templates():
    out = [("nondir", n, None, t) for n, t in NONDIR.items()]
    for rule in DIRECTION_RULES:
        for n, t in DIR_BULL.items():
            out.append(("dir", n, rule, t))
    return out


def run() -> pd.DataFrame:
    rc = duckdb.connect(SCAN_DB, read_only=True)
    regime_df = rc.execute(
        "select ts, underlying, regime from session_regime where trade_date >= '2026-09-04'").df()
    rc.close()
    files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.duckdb")))
    days = [date.fromisoformat(os.path.basename(f)[:10]) for f in files]
    books: Dict[Tuple[date, str], Book] = {}
    for f, d in zip(files, days):
        for u in UNDERLYINGS:
            b = load_book(f, u, regime_df)
            if b is not None:
                books[(d, u)] = b
        print("loaded", d, flush=True)
    rows = []
    prev_dir: Dict[str, Optional[int]] = {u: None for u in UNDERLYINGS}
    tmpls = templates()
    for di, d in enumerate(days):
        for u in UNDERLYINGS:
            book = books.get((d, u))
            if book is None:
                continue
            dte = (book.expiry - d).days
            i_exit = snap_at(book, datetime.combine(d, INTRADAY_EXIT))
            for et in ENTRY_TIMES:
                i0 = snap_at(book, datetime.combine(d, et))
                if i0 is None or i_exit is None or i0 >= i_exit:
                    continue
                reg = regime_at(book, datetime.combine(d, et))
                for kind, name, rule, tmpl in tmpls:
                    if kind == "dir":
                        dr = direction(rule, book, i0, prev_dir[u])
                        if dr is None:
                            continue
                        tmpl_use = tmpl if dr > 0 else mirror(tmpl)
                    else:
                        dr, tmpl_use = 0, tmpl
                    legs = open_legs(book, i0, tmpl_use)
                    if legs is None:
                        continue
                    for tp_sl in (False, True):
                        r = evaluate(book, legs, i0, i_exit, book, d, d, tp_sl)
                        if r is None:
                            continue
                        rows.append(dict(day=d, underlying=u, dte=dte, hold="intraday",
                                         entry=et.strftime("%H:%M"), structure=name, rule=rule or "-",
                                         dir=dr, regime=reg, exit_rule="tp_sl" if tp_sl else "time",
                                         spot=book.spot[i0], lot=book.lot, **r))
            if di + 1 < len(days) and (days[di + 1], u) in books:
                nb = books[(days[di + 1], u)]
                i0 = snap_at(book, datetime.combine(d, OVERNIGHT_ENTRY))
                i1 = snap_at(nb, datetime.combine(days[di + 1], OVERNIGHT_EXIT))
                if i1 is None and pd.Timestamp(nb.ts[0]).time() > OVERNIGHT_EXIT:
                    i1 = 0
                if i0 is not None and i1 is not None and nb.expiry == book.expiry:
                    reg = regime_at(book, datetime.combine(d, OVERNIGHT_ENTRY))
                    for kind, name, rule, tmpl in tmpls:
                        if kind == "dir":
                            dr = direction(rule, book, i0, prev_dir[u])
                            if dr is None:
                                continue
                            tmpl_use = tmpl if dr > 0 else mirror(tmpl)
                        else:
                            dr, tmpl_use = 0, tmpl
                        legs = open_legs(book, i0, tmpl_use)
                        if legs is None:
                            continue
                        r = evaluate(book, legs, i0, i1, nb, d, days[di + 1], False)
                        if r is None:
                            continue
                        rows.append(dict(day=d, underlying=u, dte=dte, hold="overnight", entry="15:10",
                                         structure=name, rule=rule or "-", dir=dr, regime=reg,
                                         exit_rule="time", spot=book.spot[i0], lot=book.lot, **r))
            oc = book.spot[-1] / book.session_open - 1
            prev_dir[u] = 1 if oc > 0 else -1
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = run()
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(len(out), "rows written to", OUT_CSV)
