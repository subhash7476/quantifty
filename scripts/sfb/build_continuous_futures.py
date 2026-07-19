"""SFB Phase -1 / D2 — Near-month continuous forward-adjusted futures series.

Reads from the raw futures_bhavcopy store (D1). For each underlying with stock
futures (FUTSTK), builds a near-month continuous series with ratio
forward-adjustment, pinned convention:

  - Forward-adjustment: anchor the oldest bar, cum starts at 1.0.
  - Roll date rd = last day near contract is held (volume-crossover day or
    calendar fallback T-1 before expiry).
  - On rd: row still priced off old near, cum unchanged. roll_flag=TRUE.
  - From rd+1 onward: cum_next = cum_near * near_close(rd)/next_close(rd).
    adj = raw * cum for the active contract on each date.
  - roll_ratio stored on rd = near_close(rd) / next_close(rd).

This ensures adj_close(rd+1)/adj_close(rd) = next_close(rd+1)/next_close(rd),
the economic next-contract return, not the raw contract gap.

Usage:
    python scripts/sfb/build_continuous_futures.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

MAX_GAP_DAYS = 10  # Max calendar days between rows in one segment.

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stock_futures_continuous (
    underlying  VARCHAR   NOT NULL,
    trade_date  DATE      NOT NULL,
    adj_open    DOUBLE,
    adj_high    DOUBLE,
    adj_low     DOUBLE,
    adj_close   DOUBLE,
    raw_close   DOUBLE,
    contracts   BIGINT,
    open_int    BIGINT,
    roll_flag   BOOLEAN   DEFAULT FALSE,
    roll_ratio  DOUBLE,
    segment_id  INTEGER   DEFAULT 0,
    PRIMARY KEY (underlying, trade_date)
);
"""


def _resolve_roll_dates(con, underlying: str) -> list:
    """Determine roll dates for one underlying.

    For each expiry pair (near, next), find the first trade date where
    next-month volume exceeds near-month volume, capped at T-1 before
    near-month expiry. Uses only data <= that date (causal).

    Returns list of (roll_date, near_expiry, next_expiry, ratio_near_next).
    """
    rows = con.execute("""
        WITH expiries AS (
            SELECT DISTINCT expiry_dt
            FROM futures_bhavcopy
            WHERE underlying = ? AND inst_type = 'FUTSTK'
            ORDER BY expiry_dt
        ),
        ordered AS (
            SELECT expiry_dt,
                   LAG(expiry_dt) OVER (ORDER BY expiry_dt) AS prev_expiry
            FROM expiries
        )
        SELECT prev_expiry AS near_expiry, expiry_dt AS next_expiry
        FROM ordered
        WHERE prev_expiry IS NOT NULL
        ORDER BY near_expiry
    """, [underlying]).fetchall()

    roll_dates = []
    for near_exp, next_exp in rows:
        last_hold = near_exp - timedelta(days=1)

        vol_data = con.execute("""
            WITH near_vol AS (
                SELECT trade_date, contracts AS near_ctr
                FROM futures_bhavcopy
                WHERE underlying = ? AND expiry_dt = ? AND trade_date <= ?
            ),
            next_vol AS (
                SELECT trade_date, contracts AS next_ctr
                FROM futures_bhavcopy
                WHERE underlying = ? AND expiry_dt = ?
            )
            SELECT nv.trade_date
            FROM near_vol nv
            JOIN next_vol nv2 ON nv2.trade_date = nv.trade_date
            WHERE nv.near_ctr IS NOT NULL AND nv2.next_ctr IS NOT NULL
              AND nv2.next_ctr > nv.near_ctr
            ORDER BY nv.trade_date
            LIMIT 1
        """, [underlying, near_exp, last_hold, underlying, next_exp]).fetchone()

        roll_date = vol_data[0] if vol_data else last_hold

        near_row = con.execute("""
            SELECT close FROM futures_bhavcopy
            WHERE underlying = ? AND expiry_dt = ? AND trade_date = ?
        """, [underlying, near_exp, roll_date]).fetchone()
        next_row = con.execute("""
            SELECT close FROM futures_bhavcopy
            WHERE underlying = ? AND expiry_dt = ? AND trade_date = ?
        """, [underlying, next_exp, roll_date]).fetchone()

        if near_row and next_row and near_row[0] and next_row[0] and next_row[0] > 0:
            ratio = near_row[0] / next_row[0]
        else:
            ratio = 1.0

        roll_dates.append((roll_date, near_exp, next_exp, ratio))

    return roll_dates


def _expiry_schedule(con, underlying: str, roll_dates: list) -> list:
    """Build sorted list of (expiry_date, roll_date, ratio, next_expiry)."""
    schedule = []
    for rd, near_exp, next_exp, ratio in roll_dates:
        schedule.append((near_exp, rd, ratio, next_exp))
    return schedule


def _all_trade_dates(con, underlying: str) -> list:
    rows = con.execute("""
        SELECT DISTINCT trade_date FROM futures_bhavcopy
        WHERE underlying = ? AND inst_type = 'FUTSTK'
        ORDER BY trade_date
    """, [underlying]).fetchall()
    return [r[0] for r in rows]


def _fetch_raw(con, underlying: str, expiry: date, td: date):
    return con.execute("""
        SELECT open, high, low, close, contracts, open_int
        FROM futures_bhavcopy
        WHERE underlying = ? AND expiry_dt = ? AND trade_date = ?
    """, [underlying, expiry, td]).fetchone()


def build_continuous_for_one(con, underlying: str) -> list:
    """Build continuous series for one underlying. Returns list of row dicts.

    Pinned forward-adjustment convention:
    - cum starts at 1.0 for the oldest era.
    - Roll date rd: last day near contract is held. cum unchanged on rd.
      roll_flag=TRUE, roll_ratio=near_close(rd)/next_close(rd).
    - From rd+1 onward: cum_next = cum_old * roll_ratio
    """
    roll_dates = _resolve_roll_dates(con, underlying)
    if not roll_dates:
        return []

    schedule = _expiry_schedule(con, underlying, roll_dates)
    all_dates = _all_trade_dates(con, underlying)
    if not all_dates:
        return []

    cum = 1.0
    adj_rows = []
    i = 0
    n = len(schedule)
    segment_id = 0
    prev_td = None

    for td in all_dates:
        # Gap guard: start a new segment if gap > MAX_GAP_DAYS
        if prev_td is not None and (td - prev_td).days > MAX_GAP_DAYS:
            cum = 1.0
            segment_id += 1
            i = 0  # reset schedule for the new segment

        if i >= n:
            near_exp = schedule[-1][3] if schedule else None
            if near_exp is None:
                prev_td = td
                continue
            roll_flag = False
            roll_ratio_for_row = None
        else:
            exp, rd, ratio, nxt = schedule[i]
            if td == rd:
                roll_flag = True
                roll_ratio_for_row = ratio
            else:
                roll_flag = False
                roll_ratio_for_row = None

            if td <= rd and i < n:
                near_exp = exp
            elif i < n:
                near_exp = nxt
                cum *= ratio
                i += 1
            else:
                near_exp = nxt if nxt else exp

        row = _fetch_raw(con, underlying, near_exp, td)
        if not row:
            prev_td = td
            continue

        raw_open, raw_high, raw_low, raw_close, ctr, oi = row
        if any(v is None or v == 0 for v in [raw_open, raw_high, raw_low, raw_close]):
            prev_td = td
            continue

        adj_rows.append({
            "underlying": underlying,
            "trade_date": td,
            "adj_open": raw_open * cum,
            "adj_high": raw_high * cum,
            "adj_low": raw_low * cum,
            "adj_close": raw_close * cum,
            "raw_close": raw_close,
            "contracts": ctr,
            "open_int": oi,
            "roll_flag": roll_flag,
            "roll_ratio": roll_ratio_for_row,
            "segment_id": segment_id,
        })

        prev_td = td

    return adj_rows


def build_continuous(con):
    con.execute("DROP TABLE IF EXISTS stock_futures_continuous")
    con.execute(SCHEMA_SQL)

    underlyings = con.execute("""
        SELECT DISTINCT underlying FROM futures_bhavcopy
        WHERE inst_type = 'FUTSTK'
        ORDER BY underlying
    """).fetchall()

    total_rows = 0
    for (und,) in underlyings:
        rows = build_continuous_for_one(con, und)
        if rows:
            df = pd.DataFrame(rows)
            con.execute("INSERT INTO stock_futures_continuous SELECT "
                        "underlying, trade_date, adj_open, adj_high, adj_low, "
                        "adj_close, raw_close, contracts, open_int, "
                        "roll_flag, roll_ratio, segment_id FROM df")
            total_rows += len(rows)
            n_rolls = sum(1 for r in rows if r["roll_flag"])
            print(f"{und}: {len(rows)} rows, {n_rolls} rolls")

    return total_rows


def main():
    con = duckdb.connect(str(DB_PATH))
    n = build_continuous(con)
    con.close()
    print(f"\nTotal continuous rows: {n:,}")


if __name__ == "__main__":
    main()
