"""RELIANCE vendor-1m intraday access for entry-timing research.

The vendor store (`1m_vendor/reliance.duckdb`, table `vendor_1m`) covers
2015-02-02 -> 2025-08-06: 2,605 sessions, start-labelled bars (first 09:15,
last 15:29 — same convention as the native 1m era), volume populated, zero
duplicates, zero non-positive prices. 46 irregular sessions (Muhurat
evenings, Saturday specials, outage days) and any date outside the span
fall back to the daily store's OHLC — counted and disclosed, never
fabricated.

PROVENANCE SEAM (verified 2026-09-10): the vendor price LEVEL differs from
the repo's CA-adjusted daily series by a smooth ~5% pre-2024 factor — the
vendor series carries a different corporate-action lineage (both bonus
adjustments plus an accumulating dividend adjustment; daily/vendor close
ratios 0.93->1.00 across 2015-2025). Mixing the two levels would corrupt
cross-day returns. Resolution (frozen): every vendor day used is RESCALED
by its own same-day close ratio  daily_close(d)/vendor_close(d), which
aligns the level to the daily series while preserving the intraday shape
(open/vwap/low relative to close) exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

VENDOR_DB = r"F:\Nifty\data\market_data\nse\candles\1m_vendor\reliance.duckdb"
VENDOR_FIRST = date(2015, 2, 2)
VENDOR_LAST = date(2025, 8, 6)

_cache: dict[date, pd.DataFrame | None] = {}


def load_day(d: date) -> pd.DataFrame | None:
    """1m bars for day d (vendor store only). Cached. None if absent."""
    if d in _cache:
        return _cache[d]
    if not (VENDOR_FIRST <= d <= VENDOR_LAST):
        _cache[d] = None
        return None
    con = duckdb.connect(VENDOR_DB, read_only=True)
    try:
        df = con.execute(
            "SELECT ts, open, high, low, close, volume FROM vendor_1m "
            "WHERE CAST(ts AS DATE) = ? ORDER BY ts",
            [d.isoformat()]).df()
    finally:
        con.close()
    if len(df) == 0:
        _cache[d] = None
        return None
    df["ts"] = pd.to_datetime(df["ts"])
    df = df[df["ts"].dt.time < pd.Timestamp("15:30").time()].reset_index(drop=True)
    if len(df) < 30:
        _cache[d] = None
        return None
    _cache[d] = df
    return df


@dataclass
class DayProfile:
    open: float
    close: float
    low: float
    high: float
    vwap: float
    twap30: float
    sourced_from: str  # "vendor_1m" or "daily_fallback"


def profile(d: date, daily_row: dict | None) -> DayProfile | None:
    """Open/close/VWAP/TWAP30/low/high for day d, in DAILY-ADJUSTED units.

    Vendor prices are rescaled by daily_close(d)/vendor_close(d) so the
    level matches the repo's daily adjusted series; intraday shape is
    preserved. VWAP and TWAP need vendor 1m; on fallback they equal the
    daily row's approximations (open for twap30, close for vwap), and
    sourced_from records the substitution.
    """
    df = load_day(d)
    if df is not None:
        vclose = float(df["close"].iloc[-1])
        scale = float(daily_row["close"]) / vclose if daily_row is not None \
            and vclose > 0 else 1.0
        first = df.iloc[0]
        last = df.iloc[-1]
        vwap = float((df["close"] * df["volume"]).sum() / df["volume"].sum())
        first30 = df[df["ts"] <= df["ts"].iloc[0] + pd.Timedelta(minutes=30)]
        twap30 = float(first30["close"].mean())
        return DayProfile(open=float(first["open"]) * scale,
                          close=float(last["close"]) * scale,
                          low=float(df["low"].min()) * scale,
                          high=float(df["high"].max()) * scale,
                          vwap=vwap * scale, twap30=twap30 * scale,
                          sourced_from="vendor_1m")
    if daily_row is None:
        return None
    return DayProfile(open=float(daily_row["open"]), close=float(daily_row["close"]),
                      low=float(daily_row["low"]), high=float(daily_row["high"]),
                      vwap=float(daily_row["close"]), twap30=float(daily_row["open"]),
                      sourced_from="daily_fallback")


def dip_fill(d: date, limit: float, daily_row: dict | None) -> float | None:
    """Limit-order entry at `limit` (daily-adjusted units): fill at limit if
    the day's low touches it, else fill at the close. Returns the fill
    price or None."""
    df = load_day(d)
    if df is not None:
        vclose = float(df["close"].iloc[-1])
        scale = float(daily_row["close"]) / vclose if daily_row is not None \
            and vclose > 0 else 1.0
        low = float(df["low"].min()) * scale
        if low <= limit:
            return limit
        return float(df["close"].iloc[-1]) * scale
    if daily_row is None:
        return None
    if float(daily_row["low"]) <= limit:
        return limit
    return float(daily_row["close"])
