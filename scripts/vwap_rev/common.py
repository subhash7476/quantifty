"""VWAP-XREV — shared constants, session loading and universe membership.

Read-only over the certified native 1m store. The worktree carries no `data/`,
so every store path is absolute under DATA_ROOT (the live checkout's data dir).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("F:/Nifty/data")
M1_DIR = DATA_ROOT / "market_data" / "nse" / "candles" / "1m"
OUT_DIR = DATA_ROOT / "research" / "vwap_extreme_reversion"
CACHE_DIR = OUT_DIR / "session_cache"
FUTURES_DB = DATA_ROOT / "market_data" / "futures_bhavcopy.duckdb"
EQUITY_DB = DATA_ROOT / "market_data" / "equity_bhavcopy.duckdb"
OPTIONS_DB = DATA_ROOT / "market_data" / "stock_options_bhavcopy.duckdb"
ISD_PIT_DB = DATA_ROOT / "isd" / "pit_universe.duckdb"
PROTOCOL_PATH = REPO / "docs" / "reports" / "research" / "vwap_extreme_reversion_protocol.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SESSION_FIRST_MIN = 9 * 60 + 15
N_SLOTS = 375                      # 09:15 .. 15:29, start-labelled bars
FIRST_SESSION = dt.date(2023, 1, 2)
LAST_SESSION = dt.date(2026, 9, 29)


def slot_of(hh: int, mm: int) -> int:
    return hh * 60 + mm - SESSION_FIRST_MIN


def regular_sessions() -> list[tuple[dt.date, Path]]:
    """Regular-session 1m files: weekdays only, not in SPECIAL_SESSIONS."""
    from core.market.session_schedule import SPECIAL_SESSIONS

    out = []
    for p in sorted(M1_DIR.glob("*.duckdb")):
        d = dt.date.fromisoformat(p.stem)
        if d < FIRST_SESSION or d > LAST_SESSION:
            continue
        if d.weekday() >= 5 or d in SPECIAL_SESSIONS:
            continue
        out.append((d, p))
    return out


def load_session_dense(path: Path) -> dict:
    """One session -> dense (nsym, 375) float32 arrays. A bar is VALID iff it is a
    stored, non-synthetic row with positive prices and positive volume; every other
    slot is NaN in all five arrays ("a bar is not a trade")."""
    from scripts.isd.read_1m import read_day

    df = read_day(path, eq_only=True)
    df = df[(~df["is_synthetic"]) & (df["volume"] > 0) & (df["open"] > 0)
            & (df["high"] > 0) & (df["low"] > 0) & (df["close"] > 0)]
    syms = np.array(sorted(df["symbol"].unique()))
    idx = {s: i for i, s in enumerate(syms)}
    arrs = {k: np.full((len(syms), N_SLOTS), np.nan, np.float32)
            for k in ("O", "H", "L", "C", "V")}
    row = df["symbol"].map(idx).to_numpy()
    ts = df["timestamp"]
    slot = (ts.dt.hour * 60 + ts.dt.minute - SESSION_FIRST_MIN).to_numpy()
    ok = (slot >= 0) & (slot < N_SLOTS)
    row, slot = row[ok], slot[ok]
    for key, col in (("O", "open"), ("H", "high"), ("L", "low"),
                     ("C", "close"), ("V", "volume")):
        arrs[key][row, slot] = df[col].to_numpy()[ok]
    return {"symbols": syms, **arrs}


def cached_session(d: dt.date, path: Path) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / f"{d.isoformat()}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=False)
        return {k: z[k] for k in z.files}
    s = load_session_dense(path)
    np.savez_compressed(f, **s)
    return s
