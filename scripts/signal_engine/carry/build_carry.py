"""Carry §3 — signal construction.

Builds formation signals from the basis panel:
  1. Raw basis (annualized)
  2. Dividend adjustment (ex-date dividends in holding period)
  3. Common-financing removal (cross-sectional demean)
  4. Winsorized z-score

Usage:
  Monthly (default): python build_carry.py
  Weekly:            python build_carry.py --weekly
Output:
  Monthly: data/signal_engine/carry/signals.duckdb
  Weekly:  data/signal_engine/carry/weekly_signals.duckdb
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
import contract_arms as A

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SIG_DB_MONTHLY = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
SIG_DB_WEEKLY = ROOT / "data" / "signal_engine" / "carry" / "weekly_signals.duckdb"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"

# Liquidity screen: trailing 20-day median futures turnover >= Rs 5 cr
ADV_THRESHOLD_CR = 5.0
ADV_WINDOW_DAYS = 30  # calendar-day window for ~20 trading days
WINSORIZE_SD = 3.0
TRAIN_LO = date(2016, 3, 31)
TRAIN_HI = date(2020, 12, 31)
HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)


def _formation_grid_monthly(con):
    """Monthly formation dates: last trading day of each completed calendar month.

    A month is 'completed' when bhavcopy contains at least one trading day
    in the following month. Excludes the current unfinished month to prevent
    spurious mid-month formations.
    """
    rows = con.execute("""
        WITH monthly AS (
            SELECT trade_date, ROW_NUMBER() OVER (
                PARTITION BY year(trade_date), month(trade_date) ORDER BY trade_date DESC
            ) AS rn
            FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK'
        ),
        last_of_month AS (
            SELECT trade_date, year(trade_date) AS yr, month(trade_date) AS mo
            FROM monthly WHERE rn = 1
        )
        SELECT l.trade_date
        FROM last_of_month l
        WHERE EXISTS (
            SELECT 1 FROM fut.futures_bhavcopy
            WHERE inst_type='FUTSTK'
              AND year(trade_date) = CASE WHEN l.mo = 12 THEN l.yr + 1 ELSE l.yr END
              AND month(trade_date) = CASE WHEN l.mo = 12 THEN 1 ELSE l.mo + 1 END
        )
        ORDER BY l.trade_date
    """).fetchall()
    return [r[0] for r in rows]


def _formation_grid_weekly(con):
    """Weekly formation dates: last trading day of each ISO week."""
    return [
        r[0] for r in con.execute("""
            WITH ranked AS (
                SELECT trade_date, ROW_NUMBER() OVER (
                    PARTITION BY year(trade_date), week(trade_date) ORDER BY trade_date DESC
                ) AS rn
                FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK'
            )
            SELECT trade_date FROM ranked WHERE rn = 1 ORDER BY trade_date
        """).fetchall()
    ]


def _formation_grid(con, weekly=False):
    if weekly:
        return _formation_grid_weekly(con)
    return _formation_grid_monthly(con)


def _load_sector_map():
    """Load sector classification CSV into {symbol: sector}."""
    m = {}
    with open(SECTOR_CSV) as f:
        next(f)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                m[parts[0]] = parts[1]
    return m


def _adv_at_date(con, fdate, lookback=ADV_WINDOW_DAYS):
    """Trailing 20-trading-day median val_in_lakh per underlying."""
    rows = con.execute(f"""
        SELECT underlying, MEDIAN(val_in_lakh) AS adv_lakh
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM fut.futures_bhavcopy
            WHERE inst_type='FUTSTK'
              AND trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{lookback} days'
        )
        WHERE rn <= 20
        GROUP BY underlying
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def main():
    weekly = "--weekly" in sys.argv
    mode = "weekly" if weekly else "monthly"
    SIG_DB = SIG_DB_WEEKLY if weekly else SIG_DB_MONTHLY

    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")

    print(f"Building basis panel [{mode}]...")
    n_cells = A.build_basis_panel(con)
    print(f"  {n_cells:,} cells")

    print(f"Computing formation grid [{mode}]...")
    fmt_dates = _formation_grid(con, weekly=weekly)
    print(f"  {len(fmt_dates)} formations: {fmt_dates[0]} -> {fmt_dates[-1]}")

    sector_map = _load_sector_map()
    print(f"  {len(sector_map)} symbols in sector map")

    if SIG_DB.exists():
        SIG_DB.unlink()
    sig = duckdb.connect(str(SIG_DB))
    sig.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    sig.execute("SET threads=2")

    sig.execute("""
        CREATE TABLE formations (
            formation_date DATE PRIMARY KEY,
            fwd_formation_date DATE,
            n_liquid INT,
            n_scored INT,
            mean_basis DOUBLE,
            sd_basis DOUBLE
        )
    """)
    sig.execute("""
        CREATE TABLE signals (
            formation_date DATE,
            underlying VARCHAR,
            entity VARCHAR,
            sector VARCHAR,
            raw_ann_basis DOUBLE,
            div_adj_basis DOUBLE,
            resid_carry DOUBLE,
            z_carry DOUBLE,
            z_carry_neut DOUBLE,
            beta DOUBLE,
            fwd_ret_1m DOUBLE,
            liquid BOOLEAN,
            PRIMARY KEY (formation_date, underlying)
        )
    """)

    # Build a date->index lookup for forward return computation
    fwd_map = {}
    for i, d in enumerate(fmt_dates):
        if i + 1 < len(fmt_dates):
            fwd_map[d] = fmt_dates[i + 1]
        else:
            fwd_map[d] = None

    n_total = len(fmt_dates)
    for idx, fdate in enumerate(fmt_dates):
        if (idx + 1) % 10 == 0:
            print(f"  formation {idx+1}/{n_total}: {fdate}")

        nfdate = fwd_map.get(fdate)

        # 3a. Get basis data + spot close at this formation date
        rows = con.execute(f"""
            SELECT bp.underlying, bp.entity, bp.annualized_basis,
                   bp.raw_basis_ratio, bp.spot_close, bp.days_to_expiry,
                   bp.expiry_dt
            FROM basis_panel bp
            WHERE bp.trade_date = DATE '{fdate}'
              AND bp.spot_close IS NOT NULL
              AND bp.annualized_basis IS NOT NULL
        """).fetchall()

        if not rows:
            print(f"    WARNING: no data at {fdate}")
            continue

        # 3b. ADV / liquidity screen
        adv = _adv_at_date(con, fdate)
        adv_prev = {u: v for u, v in adv.items() if v is not None and v >= ADV_THRESHOLD_CR * 100}
        del adv

        # 3c. Dividend adjustment
        div_rows = con.execute(f"""
            SELECT bp.underlying,
                   COALESCE(SUM(CAST(json_extract_string(ca.raw_json, '$.Details') AS DOUBLE)), 0) AS div_sum
            FROM basis_panel bp
            LEFT JOIN eq.corporate_actions ca
                ON ca.symbol = bp.underlying
               AND ca.action_type = 'DIVIDEND'
               AND ca.ex_date > bp.trade_date
               AND ca.ex_date <= bp.expiry_dt
            WHERE bp.trade_date = DATE '{fdate}'
              AND bp.spot_close IS NOT NULL
            GROUP BY bp.underlying
        """).fetchall()
        div_map = {r[0]: r[1] for r in div_rows}

        # 3d. Compute per-name values in Python
        name_data = []
        for u, ent, ann_basis, raw_ratio, spot, dte, exp in rows:
            is_liquid = u in adv_prev
            div_sum = div_map.get(u, 0.0)
            if dte is None or dte < 1:
                continue
            div_yield_ann = (div_sum / spot) * (365.0 / dte) if spot > 0 else 0.0
            div_adj = ann_basis - div_yield_ann
            sector = sector_map.get(u, "UNKNOWN")

            name_data.append({
                "underlying": u,
                "entity": ent or u,
                "sector": sector,
                "raw_ann_basis": ann_basis,
                "div_adj_basis": div_adj,
                "liquid": is_liquid,
            })

        if not name_data:
            continue

        # 3e. Cross-sectional demeaning & z-score
        nd = np.array([d["div_adj_basis"] for d in name_data], dtype=float)
        mean_b = float(np.mean(nd))
        sd_b = float(np.std(nd, ddof=1)) if len(nd) > 1 else 0.0

        if sd_b > 0:
            resid = nd - mean_b
            resid_clipped = np.clip(resid, -WINSORIZE_SD * sd_b, WINSORIZE_SD * sd_b)
            sd_clip = float(np.std(resid_clipped, ddof=1))
            z = resid_clipped / sd_clip if sd_clip > 0 else np.zeros_like(resid_clipped)
        else:
            resid = nd - mean_b
            z = np.zeros_like(resid)

        for i, d in enumerate(name_data):
            d["resid_carry"] = float(resid[i])
            d["z_carry"] = float(z[i])

        n_liquid = sum(1 for d in name_data if d["liquid"])
        n_scored = len(name_data)

        # Store formation metadata
        sig.execute(
            "INSERT INTO formations VALUES (?, ?, ?, ?, ?, ?)",
            [fdate, nfdate, n_liquid, n_scored, mean_b, sd_b],
        )

        # Store signals
        sig_con = sig.cursor()
        for d in name_data:
            sig_con.execute(
                "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)",
                [fdate, d["underlying"], d["entity"], d["sector"],
                 d["raw_ann_basis"], d["div_adj_basis"], d["resid_carry"],
                 d["z_carry"], d["liquid"]],
            )

    # 4. Forward returns: one-month adjusted spot returns (bulk update)
    print("Computing forward returns...")
    sig.close()
    sig = duckdb.connect(str(SIG_DB))
    sig.execute("SET threads=1")
    sig.execute("SET memory_limit='4GB'")
    sig.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    sig.execute("""
        CREATE TEMP TABLE fwd_returns AS
        SELECT s.formation_date, s.underlying,
               (a2.close - a1.close) / a1.close AS fwd_ret
        FROM signals s
        JOIN eq.equity_bhavcopy_adjusted a1
            ON a1.symbol = s.underlying AND a1.trade_date = s.formation_date AND a1.series='EQ'
            AND a1.close IS NOT NULL AND a1.close > 0
        JOIN formations f ON f.formation_date = s.formation_date AND f.fwd_formation_date IS NOT NULL
        JOIN eq.equity_bhavcopy_adjusted a2
            ON a2.symbol = s.underlying AND a2.trade_date = f.fwd_formation_date AND a2.series='EQ'
            AND a2.close IS NOT NULL AND a2.close > 0
    """)
    sig.execute("""
        UPDATE signals s
        SET fwd_ret_1m = fr.fwd_ret
        FROM fwd_returns fr
        WHERE fr.formation_date = s.formation_date AND fr.underlying = s.underlying
    """)
    sig.execute("DROP TABLE IF EXISTS fwd_returns")

    # Summary
    total_sig = sig.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    print(f"\nDone: {total_sig:,} signals, {len(fmt_dates)} formations")
    print(f"  Signals DB: {SIG_DB}")

    sig.close()
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
