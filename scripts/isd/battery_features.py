"""ISD battery — frozen feature/label construction (read-only over certified stores).

Implements ISD_PHASE0_PRE_REGISTRATION §4 exactly:
  F1 opening-drive: feature = (window-end bar close - 09:15 open)/09:15 open;
     entry = next-bar open after the window-end close (09:46 / 10:01);
     label = entry open -> 15:29 close (no overlap, no look-ahead).
  F4 overnight-gap: feature = (09:15 open - prev_close)/prev_close (daily store,
     PIT ISIN join); CA ex-date sessions excluded per symbol;
     entry = {09:16 bar open, 09:16 bar close}; label = entry -> 15:29 close.

Universe: pit_membership (G5) — intraday-present AND PIT-listed per session.
ADV cap: position size capped at 10% of trailing 20-session ADV as of T-1.
"""
from __future__ import annotations

import datetime as dt

import duckdb
import pandas as pd

from scripts.isd import (
    EQUITY_DB, ISD_DATA_DIR, connect_ro,
)
from scripts.isd.read_1m import read_day

M_OPEN = 9 * 60 + 15          # 09:15 auction open (signal start, F1/F4)
M_0945 = 9 * 60 + 45          # 09:45 bar close (F1 window-end, cell A)
M_0946 = 9 * 60 + 46          # 09:46 bar open  (F1 entry, cell A)
M_1000 = 10 * 60              # 10:00 bar close (F1 window-end, cell B)
M_1001 = 10 * 60 + 1          # 10:01 bar open  (F1 entry, cell B)
M_0916 = 9 * 60 + 16          # 09:16 bar open/close (F4 entry cells)
M_EXIT = 15 * 60 + 29         # 15:29 bar close (exit)

MIN_NAMES = 20                # minimum names for a session's IC (harness floor)
ADV_WINDOW = 20               # trailing sessions for the ADV cap
ADV_MIN_SESSIONS = 5          # minimum covered sessions for a valid ADV
ADV_CAP = 0.10                # 10% of trailing ADV per name


def load_daily(sessions: list, lead_days: int = 40):
    """prev_close + volume per (session, NSE_EQ|ISIN) and CA ex-dates, one pass."""
    lo = (min(dt.date.fromisoformat(s) for s in sessions)
          - dt.timedelta(days=lead_days)).isoformat()
    hi = (max(dt.date.fromisoformat(s) for s in sessions)
          + dt.timedelta(days=1)).isoformat()
    con = connect_ro(EQUITY_DB)
    try:
        sym_isin = dict(con.execute(
            "select symbol, isin from symbol_isin where isin is not null"
        ).fetchall())
        rows = con.execute(f"""
            select trade_date, symbol, prev_close, volume
            from equity_bhavcopy
            where series = 'EQ' and trade_date >= DATE '{lo}'
              and trade_date < DATE '{hi}'
        """).fetchall()
        ca = con.execute("""
            select symbol, ex_date from corporate_actions
        """).fetchall()
    finally:
        con.close()
    daily: dict = {}
    for d, sym, pc, vol in rows:
        key = "NSE_EQ|" + sym_isin[sym] if sym in sym_isin else None
        if not key:
            continue
        daily.setdefault(key, {})[d] = (float(pc), float(vol))
    ca_by_key: dict = {}
    for sym, ex in ca:
        key = "NSE_EQ|" + sym_isin[sym] if sym in sym_isin else None
        if key:
            ca_by_key.setdefault(key, set()).add(ex)
    return daily, ca_by_key


def _price_map(df: pd.DataFrame):
    """minute -> {symbol: (open, close, volume)} from one session's frame."""
    out: dict = {}
    for row in df.itertuples(index=False):
        m = row.timestamp.hour * 60 + row.timestamp.minute
        out.setdefault(m, {})[row.symbol] = (row.open, row.close, row.volume)
    return out


def session_frame(path: str) -> pd.DataFrame:
    """One session's per-symbol price snapshot (index = NSE_EQ|ISIN key)."""
    df = read_day(path)
    per_min = _price_map(df)
    syms = sorted(set().union(*per_min.values()))

    def g(m, i):
        b = per_min.get(m, {}).get(sym)
        return b[i] if b else None

    rows = []
    for sym in syms:
        dvol = 0.0
        for bars in per_min.values():
            b = bars.get(sym)
            if b:
                dvol += b[0] * b[2]
        rows.append({
            "open0915": g(M_OPEN, 0), "close0945": g(M_0945, 1),
            "open0946": g(M_0946, 0), "close1000": g(M_1000, 1),
            "open1001": g(M_1001, 0), "open0916": g(M_0916, 0),
            "close0916": g(M_0916, 1), "close1529": g(M_EXIT, 1),
            "dvol": dvol})
    frame = pd.DataFrame(rows).set_index(pd.Index(syms, name="symbol"))
    return frame[frame["open0915"] > 0]


def build(sessions: list) -> list:
    """[(session_iso, per-symbol frame)] for the given sessions."""
    daily, ca = load_daily([s for s, _ in sessions])
    con = connect_ro(ISD_DATA_DIR / "pit_universe.duckdb")
    try:
        pit = con.execute("""
            select session_date, isin, fno_member from pit_membership
        """).fetchall()
    finally:
        con.close()
    pit_by_session: dict = {}
    for d, key, fno in pit:
        pit_by_session.setdefault(d, {})[key] = bool(fno)

    out = []
    for iso, path in sessions:
        d = dt.date.fromisoformat(iso)
        memb = pit_by_session.get(d, {})
        if not memb:
            continue
        frame = session_frame(path)
        keep = [s for s in frame.index if s in memb]
        frame = frame.loc[keep]
        pc = frame.index.map(
            lambda k: (daily.get(k, {}).get(d) or (None, None))[0])
        ex = frame.index.map(lambda k: d in ca.get(k, set()))
        frame["prev_close"] = pd.Series(pc, index=frame.index)
        frame["is_exdate"] = pd.Series(ex, index=frame.index)
        frame["fno"] = frame.index.map(lambda k: memb.get(k, False))
        out.append((iso, frame))
    return out


def adv_series(frames: list, adv_window: int = ADV_WINDOW) -> dict:
    """iso -> {symbol: trailing ADV as of T-1} (mean over prior sessions' dvol)."""
    vols = [df["dvol"].to_dict() for _iso, df in frames]
    adv: dict = {}
    for i, (iso, df) in enumerate(frames):
        prior = vols[max(0, i - adv_window):i]
        if len(prior) < ADV_MIN_SESSIONS:
            continue
        keys = sorted(set().union(*prior))
        s = pd.Series(0.0, index=keys)
        n = pd.Series(0.0, index=keys)
        for p in prior:
            for k, v in p.items():
                if v > 0:
                    s[k] += v
                    n[k] += 1
        adv[iso] = (s / n.clip(lower=1)).to_dict()
    return adv
