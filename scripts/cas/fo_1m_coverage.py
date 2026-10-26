"""F&O equity names in the per-day 1m store, and their continuous-session closes.

Since CAS (2026-08-03) the official close of an F&O (Category I) stock is the
closing-auction print, struck after continuous trading stops at 15:15 while
futures trade on to 15:40. The continuous-session close is the last traded 1m
bar before the cash_cat1 window ends.

Both helpers expect the futures store attached as `fut` and the equity store as `eq`.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402

from core.market.session_schedule import session_window  # noqa: E402

CANDLES_1M_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
UPSTOX_MASTER_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"


def _upstox_isins(master_db: Path, symbols: list[str]) -> dict[str, str]:
    """{symbol: isin} for `symbols` from the latest Upstox master snapshot's EQ rows."""
    if not symbols or not Path(master_db).exists():
        return {}
    con = duckdb.connect(str(master_db), read_only=True)
    try:
        return dict(con.execute("""
            SELECT tradingsymbol, any_value(isin) FROM instruments
            WHERE instrument_type = 'EQ' AND isin IS NOT NULL
              AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
              AND tradingsymbol IN (SELECT UNNEST(?::VARCHAR[]))
            GROUP BY 1
        """, [symbols]).fetchall())
    finally:
        con.close()


def fo_equity_keys(con, on: date, master_db: Path = UPSTOX_MASTER_DB) -> tuple[dict[str, str], list[str]]:
    """({underlying: 'NSE_EQ|<isin>'}, underlyings with no EQ ISIN) for FUTSTK names trading on `on`.

    instrument_master carries each symbol's current ISIN; symbol_isin keeps pre-split
    ISINs the 1m store no longer uses. instrument_master is refreshed only by
    build_universe.py, so a renamed symbol (ICICIPRULI -> ICICILIFE, 2026-10-23) falls
    back to the latest Upstox master snapshot, which the orchestrator refreshes daily.
    """
    rows = con.execute("""
        SELECT DISTINCT f.underlying, im.isin
        FROM fut.futures_bhavcopy f
        LEFT JOIN eq.instrument_master im ON im.symbol = f.underlying AND im.series = 'EQ'
        WHERE f.inst_type = 'FUTSTK' AND f.trade_date = ?
    """, [on]).fetchall()
    isins = {u: isin for u, isin in rows if isin}
    isins.update(_upstox_isins(master_db, sorted(u for u, isin in rows if not isin)))
    keys = {u: f"NSE_EQ|{isin}" for u, isin in isins.items()}
    return keys, sorted({u for u, _ in rows} - set(keys))


def load_continuous_closes(con, dates, candles_dir: Path = CANDLES_1M_DIR) -> None:
    """Temp table cont_close(trade_date, underlying, close, bars): last traded bar before 15:15.

    `bars` counts every 1m row the name has that day, so a name present only as
    zero-volume bars is told apart from one the store never received.
    """
    con.execute("CREATE OR REPLACE TEMP TABLE cont_close "
                "(trade_date DATE, underlying VARCHAR, close DOUBLE, bars BIGINT)")
    for d in dates:
        path = candles_dir / f"{d}.duckdb"
        if not path.exists():
            continue
        keys, _ = fo_equity_keys(con, d)
        con.execute("CREATE OR REPLACE TEMP TABLE fo_keys (underlying VARCHAR, symbol VARCHAR)")
        con.executemany("INSERT INTO fo_keys VALUES (?, ?)", list(keys.items()))
        con.execute(f"ATTACH '{path}' AS m1 (READ_ONLY)")
        try:
            con.execute("""
                INSERT INTO cont_close
                SELECT ?, k.underlying,
                       arg_max(c.close, c.timestamp) FILTER (WHERE c.volume > 0 AND CAST(c.timestamp AS TIME) < ?),
                       COUNT(*)
                FROM m1.candles c JOIN fo_keys k ON k.symbol = c.symbol
                GROUP BY k.underlying
            """, [d, session_window("cash_cat1", d)[1]])
        finally:
            con.execute("DETACH m1")
