"""ISD G3 — the single normalized reader for the native 1m store.

The store has two schema variants (defect D3): files through 2026-03-04 carry
`(symbol, timeframe, timestamp, ...)`, and from 2026-03-05 an `instrument_key`
column was inserted. Every downstream gate reads ONLY through this module so the
drift — and any future drift — is handled in exactly one place.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from scripts.isd import connect_ro

_CONTRACT_COLS = ("symbol", "timestamp", "open", "high", "low", "close",
                  "volume", "is_synthetic")


def read_day(path: Path, eq_only: bool = True) -> pd.DataFrame:
    """Read one per-day file into the uniform contract.

    Returns columns `symbol, timestamp, open, high, low, close, volume,
    is_synthetic` with `timestamp` as naive datetime64 and `is_synthetic` as
    bool. Extra columns (e.g. `instrument_key`) are ignored by construction —
    the SELECT names exactly the contract columns.
    """
    con = connect_ro(path)
    try:
        df = con.execute(f"""
            select symbol, timestamp,
                   open, high, low, close, volume,
                   coalesce(is_synthetic, false) as is_synthetic
            from candles
            {'where symbol like ' + "'NSE_EQ%'" if eq_only else ''}
            order by symbol, timestamp
        """).df()
    finally:
        con.close()
    missing = [c for c in _CONTRACT_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: normalized read missing {missing}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def minute_of_day(ts) -> int:
    """Minutes since midnight for a timestamp-like value."""
    return ts.hour * 60 + ts.minute
