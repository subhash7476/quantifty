"""TS Basis Daily combo forward-paper state + P&L store.

One row per processed formation in `combo_daily`, the held book after that
formation in `combo_book`, the executed deltas in `combo_trades`. The runner
resumes from `last_state()`, so a restart continues the same forward record
instead of re-opening a book from flat.

Every call opens and closes its own connection, so another process (the
Flask page) can read the store between writes. DuckDB still locks the file
while a connection is open, so a reader and this writer can collide: any
cross-process reader needs a bounded retry. A crash mid-`record` rolls back,
and the runner resumes from the last committed formation.
No primary keys or indexes: a date is replaced by DELETE + INSERT in one
transaction (an indexed table written open-close bloats on checkpoint).

P&L is recorded twice for the book held from `prev_date` close to
`formation_date` close:
  - futures: close-to-close of the nearest contract expiring strictly after
    `formation_date`, priced at both ends — the tradeable series. It differs
    from the signal's T-3 roll in the last ~3 sessions before expiry, and no
    roll cost is charged;
  - spot: `signals.fwd_ret_1m` of `prev_date` (adjusted equity close to the
    next formation) — the research scoring, comparable to the backtest.
Unpriced names contribute 0 and are counted.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

import duckdb

DDL = [
    """CREATE TABLE IF NOT EXISTS combo_daily (
        formation_date DATE, prev_date DATE, n_long INTEGER, n_short INTEGER,
        traded_value DOUBLE, fees DOUBLE, slippage DOUBLE,
        fut_long_ret DOUBLE, fut_short_ret DOUBLE, fut_pnl DOUBLE,
        spot_long_ret DOUBLE, spot_short_ret DOUBLE, spot_pnl DOUBLE,
        n_unpriced_fut INTEGER, n_unpriced_spot INTEGER,
        net_pnl_fut DOUBLE, cum_net_pnl_fut DOUBLE, drawdown_pct DOUBLE,
        written_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS combo_book (
        formation_date DATE, underlying VARCHAR, side VARCHAR, cap DOUBLE)""",
    """CREATE TABLE IF NOT EXISTS combo_trades (
        formation_date DATE, underlying VARCHAR, action VARCHAR,
        held_side VARCHAR, held_cap DOUBLE, target_side VARCHAR, target_cap DOUBLE)""",
    """CREATE TABLE IF NOT EXISTS combo_meta (key VARCHAR, value VARCHAR)""",
]

PNL_FIELDS = ("prev_date", "fut_long_ret", "fut_short_ret", "fut_pnl",
              "spot_long_ret", "spot_short_ret", "spot_pnl",
              "n_unpriced_fut", "n_unpriced_spot", "net_pnl_fut")


def _leg(caps: Dict[str, float], rets: Dict[str, float]):
    """(cap-weighted leg return, rupee P&L, n unpriced) for one leg."""
    total = sum(caps.values())
    pnl = sum(c * rets[u] for u, c in caps.items() if u in rets)
    missing = sum(1 for u in caps if u not in rets)
    return (pnl / total if total > 0 else None), pnl, missing


def book_returns(prev_date: date, fdate: date, longs: Dict[str, float],
                 shorts: Dict[str, float], fut_db, sig_db) -> dict:
    """Futures and spot P&L of the book held from prev_date to fdate."""
    names = sorted(set(longs) | set(shorts))
    fut_ret: Dict[str, float] = {}
    spot_ret: Dict[str, float] = {}
    if names:
        con = duckdb.connect(str(fut_db), read_only=True)
        rows = con.execute("""
            WITH c AS (
                SELECT underlying, MIN(expiry_dt) AS exp FROM futures_bhavcopy
                WHERE inst_type = 'FUTSTK' AND trade_date = ? AND expiry_dt > ?
                  AND underlying IN (SELECT UNNEST(?::VARCHAR[]))
                GROUP BY underlying)
            SELECT c.underlying, b.close / a.close - 1
            FROM c
            JOIN futures_bhavcopy a ON a.underlying = c.underlying AND a.expiry_dt = c.exp
                 AND a.trade_date = ? AND a.inst_type = 'FUTSTK'
            JOIN futures_bhavcopy b ON b.underlying = c.underlying AND b.expiry_dt = c.exp
                 AND b.trade_date = ? AND b.inst_type = 'FUTSTK'
            WHERE a.close > 0 AND b.close IS NOT NULL
        """, [fdate, fdate, names, prev_date, fdate]).fetchall()
        con.close()
        fut_ret = {u: float(r) for u, r in rows}

        con = duckdb.connect(str(sig_db), read_only=True)
        rows = con.execute("""
            SELECT underlying, fwd_ret_1m FROM signals
            WHERE formation_date = ? AND fwd_ret_1m IS NOT NULL
              AND underlying IN (SELECT UNNEST(?::VARCHAR[]))
        """, [prev_date, names]).fetchall()
        con.close()
        spot_ret = {u: float(r) for u, r in rows}

    fl, fl_pnl, fl_miss = _leg(longs, fut_ret)
    fs, fs_pnl, fs_miss = _leg(shorts, fut_ret)
    sl, sl_pnl, sl_miss = _leg(longs, spot_ret)
    ss, ss_pnl, ss_miss = _leg(shorts, spot_ret)
    return {
        "prev_date": prev_date,
        "fut_long_ret": fl, "fut_short_ret": fs, "fut_pnl": fl_pnl - fs_pnl,
        "spot_long_ret": sl, "spot_short_ret": ss, "spot_pnl": sl_pnl - ss_pnl,
        "n_unpriced_fut": fl_miss + fs_miss, "n_unpriced_spot": sl_miss + ss_miss,
    }


class ComboPaperStore:
    def __init__(self, path, capital: float = 10_000_000.0):
        self._path = Path(path)
        self._capital = capital
        self._path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(self._path))
        for ddl in DDL:
            con.execute(ddl)
        con.close()

    def write_meta(self, meta: Dict[str, str]):
        con = duckdb.connect(str(self._path))
        con.execute("BEGIN")
        for k, v in meta.items():
            con.execute("DELETE FROM combo_meta WHERE key = ?", [k])
            con.execute("INSERT INTO combo_meta VALUES (?, ?)", [k, str(v)])
        con.execute("COMMIT")
        con.close()

    def last_state(self) -> Optional[dict]:
        con = duckdb.connect(str(self._path), read_only=True)
        row = con.execute("""
            SELECT formation_date, cum_net_pnl_fut FROM combo_daily
            ORDER BY formation_date DESC LIMIT 1""").fetchone()
        if row is None:
            con.close()
            return None
        book = con.execute("SELECT underlying, side, cap FROM combo_book WHERE formation_date = ?",
                           [row[0]]).fetchall()
        con.close()
        return {
            "formation_date": row[0],
            "cum_net_pnl_fut": float(row[1] or 0.0),
            "longs": {u: c for u, s, c in book if s == "LONG"},
            "shorts": {u: c for u, s, c in book if s == "SHORT"},
        }

    def record(self, fdate: date, *, longs, shorts, trades, costs, pnl):
        """Persist one formation atomically; re-recording a date replaces it."""
        con = duckdb.connect(str(self._path))
        con.execute("BEGIN")
        for table in ("combo_daily", "combo_book", "combo_trades"):
            con.execute(f"DELETE FROM {table} WHERE formation_date = ?", [fdate])
        prior = con.execute("""
            SELECT cum_net_pnl_fut FROM combo_daily WHERE formation_date < ?
            ORDER BY formation_date DESC LIMIT 1""", [fdate]).fetchone()
        peak = con.execute("SELECT MAX(cum_net_pnl_fut) FROM combo_daily WHERE formation_date < ?",
                           [fdate]).fetchone()[0]
        net = pnl.get("net_pnl_fut") or 0.0
        cum = (prior[0] if prior else 0.0) + net
        peak_equity = self._capital + max(peak if peak is not None else 0.0, cum, 0.0)
        drawdown = ((self._capital + cum) / peak_equity - 1.0) * 100.0
        p = [pnl.get(f) for f in PNL_FIELDS]
        con.execute(
            "INSERT INTO combo_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [fdate, p[0], len(longs), len(shorts), costs["traded_value"],
             costs["fees"], costs["slippage"], *p[1:], cum, drawdown, datetime.now()])
        for side, book in (("LONG", longs), ("SHORT", shorts)):
            for u, c in book.items():
                con.execute("INSERT INTO combo_book VALUES (?,?,?,?)", [fdate, u, side, c])
        for t in trades:
            con.execute("INSERT INTO combo_trades VALUES (?,?,?,?,?,?,?)",
                        [fdate, t["underlying"], t["action"], t["held_side"],
                         t["held_cap"], t["target_side"], t["target_cap"]])
        con.execute("COMMIT")
        con.close()
