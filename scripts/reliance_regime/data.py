"""Data layer for the RELIANCE regime research.

One aligned panel: RELIANCE daily CA-adjusted bhavcopy (2010-01-04 ->
present, 4,141 rows, zero gaps, entity-continuous, 2 bonus events adjusted)
joined with Nifty 50 and India VIX daily context from the 1d index store.
All series are causal as loaded; signal construction is the only
transformation step.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

EQUITY_DB = Path(r"F:\Nifty\data\market_data\equity_bhavcopy.duckdb")
INDEX_1D_DIR = Path(r"F:\Nifty\data\market_data\nse\candles\1d")

NIFTY = "NSE_INDEX|Nifty 50"
VIX = "NSE_INDEX|India VIX"


def load_reliance_daily() -> pd.DataFrame:
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    try:
        df = con.execute("""
            SELECT trade_date AS date, open, high, low, close, prev_close,
                   volume, turnover, deliv_pct, series
            FROM equity_bhavcopy_adjusted
            WHERE symbol = 'RELIANCE'
            ORDER BY trade_date
        """).df()
    finally:
        con.close()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.set_index("date")
    df = df[~df.index.duplicated(keep="first")]
    return df


def load_index_context() -> pd.DataFrame:
    """Nifty 50 + India VIX daily closes from the per-date 1d store."""
    rows = []
    for path in sorted(INDEX_1D_DIR.glob("*.duckdb")):
        con = duckdb.connect(str(path), read_only=True)
        try:
            for sym in (NIFTY, VIX):
                r = con.execute(
                    "SELECT timestamp, close FROM candles WHERE symbol = ?",
                    [sym]).fetchone()
                if r is not None:
                    rows.append((r[0].date(), sym, float(r[1])))
        finally:
            con.close()
    df = pd.DataFrame(rows, columns=["date", "symbol", "close"])
    piv = df.pivot_table(index="date", columns="symbol", values="close")
    piv = piv.rename(columns={NIFTY: "nifty", VIX: "vix"})
    return piv.sort_index()


def build_panel() -> pd.DataFrame:
    rel = load_reliance_daily()
    ctx = load_index_context()
    panel = rel.join(ctx, how="left")
    panel["ret"] = panel["close"].pct_change()
    return panel


def panel_span(panel: pd.DataFrame) -> str:
    return f"{panel.index.min()} -> {panel.index.max()} ({len(panel)} rows)"
