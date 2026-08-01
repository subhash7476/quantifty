"""
Load Nifty 50 and Bank Nifty data from per-day DuckDB candle files.
Supports 1m intraday and 1d EOD timeframes.

1d data: 2010-01-04 to 2026-07-31 (~4100 files, contains Nifty, BankNifty, India VIX)
1m data: 2023-01-02 to 2026-07-03 (~868 files, contains Nifty, BankNifty)

Index volume is always 0 — use close prices only.
"""
from pathlib import Path
from typing import Optional, Literal

import duckdb
import numpy as np
import pandas as pd

DATA_ROOT = Path("F:/Nifty/data/market_data/nse/candles")

NIFTY_KEY = "NSE_INDEX|Nifty 50"
BANKNIFTY_KEY = "NSE_INDEX|Nifty Bank"


def _load_symbol_from_db(db_path: Path, symbol: str) -> pd.DataFrame:
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        df = conn.execute(
            "SELECT timestamp, close FROM candles WHERE symbol = ? ORDER BY timestamp",
            [symbol],
        ).fetchdf()
        return df
    finally:
        conn.close()


def load_1d_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load daily close data for Nifty and BankNifty.

    Returns DataFrame with columns: date, nifty_close, banknifty_close
    """
    data_dir = DATA_ROOT / "1d"
    files = sorted(data_dir.glob("*.duckdb"))

    if start:
        files = [f for f in files if f.stem >= start]
    if end:
        files = [f for f in files if f.stem <= end]

    rows = []
    for f in files:
        conn = duckdb.connect(str(f), read_only=True)
        try:
            result = conn.execute(
                "SELECT symbol, timestamp, close FROM candles WHERE symbol IN (?, ?)",
                [NIFTY_KEY, BANKNIFTY_KEY],
            ).fetchall()
            for sym, ts, close in result:
                rows.append({"date": ts.date(), "symbol": sym, "close": close})
        except Exception:
            pass
        finally:
            conn.close()

    if not rows:
        return pd.DataFrame(columns=["date", "nifty_close", "banknifty_close"])

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["date", "symbol"], keep="last")
    pivot = df.pivot(index="date", columns="symbol", values="close")
    pivot = pivot.rename(columns={NIFTY_KEY: "nifty_close", BANKNIFTY_KEY: "banknifty_close"})
    return pivot.dropna().sort_index()


def load_1m_data(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load 1-minute close data for Nifty and BankNifty.

    Returns DataFrame with columns: timestamp, nifty_close, banknifty_close
    """
    data_dir = DATA_ROOT / "1m"
    files = sorted(data_dir.glob("*.duckdb"))

    if start:
        files = [f for f in files if f.stem >= start]
    if end:
        files = [f for f in files if f.stem <= end]

    rows = []
    for f in files:
        conn = duckdb.connect(str(f), read_only=True)
        try:
            result = conn.execute(
                "SELECT symbol, timestamp, close FROM candles WHERE symbol IN (?, ?)",
                [NIFTY_KEY, BANKNIFTY_KEY],
            ).fetchall()
            for sym, ts, close in result:
                rows.append({"timestamp": ts, "symbol": sym, "close": close})
        except Exception:
            pass
        finally:
            conn.close()

    if not rows:
        return pd.DataFrame(columns=["timestamp", "nifty_close", "banknifty_close"])

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["timestamp", "symbol"], keep="last")
    pivot = df.pivot(index="timestamp", columns="symbol", values="close")
    pivot = pivot.rename(columns={NIFTY_KEY: "nifty_close", BANKNIFTY_KEY: "banknifty_close"})
    return pivot.dropna().sort_index()


def resample_to_minute_bars(df_1m: pd.DataFrame) -> pd.DataFrame:
    """Ensure 1m data is on a regular grid. Already 1m from source."""
    return df_1m


def compute_returns(df: pd.DataFrame, nifty_col="nifty_close", banknifty_col="banknifty_close") -> pd.DataFrame:
    df = df.copy()
    df["nifty_ret"] = df[nifty_col].pct_change()
    df["banknifty_ret"] = df[banknifty_col].pct_change()
    df["ratio"] = df[banknifty_col] / df[nifty_col]
    df["log_ratio"] = np.log(df["ratio"])
    df["spread"] = df[banknifty_col] - df[nifty_col]
    return df.dropna()
