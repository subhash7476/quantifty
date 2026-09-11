"""TS Basis Daily — signal construction (DuckDB-optimised, incremental).

Computes time-series basis z-scores per (formation_date, underlying) at
**daily** cadence:
  raw_z = (basis_now - trailing_mean) / trailing_std
  z_ts  = raw_z clamped to [-3, 3]

Usage:
  Full rebuild:  python build_ts_basis_daily.py
                 (builds beside the store, copies the old store to data/_baselines, then replaces it)
  Incremental:   python build_ts_basis_daily.py --incremental
Output: data/signal_engine/ts_basis_daily/ts_signals.duckdb
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
import contract_arms as A

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
BASELINE_DIR = ROOT / "data" / "_baselines"

LOOKBACK_ROWS = 252
MIN_OBS = 12
ADV_THRESHOLD_LAKH = 500
ADV_SESSIONS = 30
Z_CLAMP = 3.0

SIGNAL_COLUMNS = ("formation_date", "underlying", "raw_ann_basis", "raw_z", "z_ts", "fwd_ret_1m", "liquid")


def _existing_dates(path: Path) -> set:
    con = duckdb.connect(str(path), read_only=True)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info('signals')").fetchall()]
        if tuple(cols) != SIGNAL_COLUMNS:
            raise SystemExit(
                f"{path} has columns {cols}, expected {list(SIGNAL_COLUMNS)} — "
                f"run build_ts_basis_daily.py without --incremental for a full rebuild")
        return {r[0] for r in con.execute("SELECT DISTINCT formation_date FROM signals").fetchall()}
    finally:
        con.close()


def _build(out_path: Path, existing_dates: set) -> tuple[int, int]:
    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")
    fresh = not out_path.exists()
    con.execute(f"ATTACH '{out_path}' AS out")

    print("Building basis_panel...")
    print(f"  {A.build_basis_panel(con):,} cells")

    all_fmt_dates = [r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK' ORDER BY trade_date"
    ).fetchall()]
    fmt_dates = [d for d in all_fmt_dates if d not in existing_dates]
    if not fmt_dates:
        print("  All formations already built — nothing to do.")
        con.close()
        return 0, 0
    print(f"  {len(all_fmt_dates)} total, {len(fmt_dates)} new: {fmt_dates[0]} -> {fmt_dates[-1]}")

    con.execute("BEGIN")
    con.execute("CREATE TEMP TABLE new_dates (d DATE)")
    con.executemany("INSERT INTO new_dates VALUES (?)", [(d,) for d in fmt_dates])

    # ADV: median of daily total turnover (all contracts summed) over the trailing sessions
    con.execute(f"""
        CREATE TEMP TABLE adv_lookup AS
        SELECT trade_date, underlying,
               MEDIAN(day_val) OVER (
                   PARTITION BY underlying ORDER BY trade_date
                   ROWS BETWEEN {ADV_SESSIONS - 1} PRECEDING AND CURRENT ROW
               ) AS adv_lakh
        FROM (
            SELECT trade_date, underlying, SUM(val_in_lakh) AS day_val
            FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK' AND val_in_lakh IS NOT NULL
            GROUP BY trade_date, underlying
        )
    """)

    # A name leaving F&O has no next contract to roll into, so the panel keeps pricing it
    # off the expiring one, where 365 / days_to_expiry blows a small basis up. Drop those cells.
    exiting = con.execute(f"""
        DELETE FROM basis_panel bp USING td_cal tc, exp_cal ec
        WHERE tc.trade_date = bp.trade_date AND ec.trade_date = bp.expiry_dt
          AND ec.td_idx - tc.td_idx <= {A.ROLL_TRADING_DAYS}
    """).fetchone()[0]
    print(f"  {exiting:,} cells dropped: expiring contract, no next contract")

    if fresh:
        con.execute("""
            CREATE TABLE out.signals (
                formation_date DATE, underlying VARCHAR, raw_ann_basis DOUBLE, raw_z DOUBLE,
                z_ts DOUBLE, fwd_ret_1m DOUBLE, liquid BOOLEAN)
        """)
    con.execute(f"""
        INSERT INTO out.signals
        SELECT CAST(bp.trade_date AS DATE), bp.underlying, bp.annualized_basis,
               NULL, NULL, NULL, COALESCE(a.adv_lakh, 0) >= {ADV_THRESHOLD_LAKH}
        FROM basis_panel bp
        JOIN new_dates n ON n.d = bp.trade_date
        LEFT JOIN adv_lookup a ON a.trade_date = bp.trade_date AND a.underlying = bp.underlying
        WHERE bp.spot_close IS NOT NULL AND bp.annualized_basis IS NOT NULL
    """)
    dups = con.execute("""
        SELECT COUNT(*) FROM (SELECT formation_date, underlying FROM out.signals
                              GROUP BY 1, 2 HAVING COUNT(*) > 1)
    """).fetchone()[0]
    if dups:
        raise RuntimeError(f"{dups} duplicate (formation_date, underlying) keys — basis_panel fanned out")
    if fresh:
        con.execute("CREATE INDEX idx_sig_date ON out.signals (formation_date)")
        con.execute("CREATE INDEX idx_sig_und ON out.signals (underlying)")

    print("  Computing z...")
    con.execute(f"""
        UPDATE out.signals s SET raw_z = z.raw_z,
               z_ts = CASE WHEN z.raw_z IS NULL THEN NULL
                           ELSE GREATEST(-{Z_CLAMP}, LEAST({Z_CLAMP}, z.raw_z)) END
        FROM (
            SELECT formation_date, underlying,
                   CASE WHEN COUNT(raw_ann_basis) OVER w >= {MIN_OBS}
                        AND STDDEV_SAMP(raw_ann_basis) OVER w > 1e-8
                   THEN (raw_ann_basis - AVG(raw_ann_basis) OVER w) / STDDEV_SAMP(raw_ann_basis) OVER w
                   ELSE NULL END AS raw_z
            FROM out.signals WHERE raw_ann_basis IS NOT NULL
            WINDOW w AS (PARTITION BY underlying ORDER BY formation_date
                         ROWS BETWEEN {LOOKBACK_ROWS} PRECEDING AND 1 PRECEDING)
        ) z
        WHERE z.formation_date = s.formation_date AND z.underlying = s.underlying
          AND s.formation_date IN (SELECT d FROM new_dates)
    """)

    # Forward (next-formation) returns: the new dates plus the formation just before
    # them, whose next close only exists now.
    print("  Computing forward returns...")
    con.execute("""
        CREATE TEMP TABLE fmt AS
        SELECT formation_date, LEAD(formation_date) OVER (ORDER BY formation_date) AS nxt
        FROM (SELECT DISTINCT formation_date FROM out.signals)
    """)
    con.execute("""
        CREATE TEMP TABLE pending AS
        SELECT s.formation_date, s.underlying, f.nxt
        FROM out.signals s JOIN fmt f ON f.formation_date = s.formation_date
        WHERE s.fwd_ret_1m IS NULL AND f.nxt IS NOT NULL
          AND s.formation_date >= COALESCE(
              (SELECT MAX(formation_date) FROM fmt WHERE formation_date < (SELECT MIN(d) FROM new_dates)),
              (SELECT MIN(d) FROM new_dates))
    """)
    if con.execute("SELECT COUNT(*) FROM pending").fetchone()[0]:
        con.execute("""
            CREATE TEMP TABLE eq_sub AS
            SELECT symbol, trade_date, close
            FROM eq.equity_bhavcopy_adjusted
            WHERE symbol IN (SELECT DISTINCT underlying FROM pending)
              AND trade_date >= (SELECT MIN(formation_date) FROM pending)
              AND trade_date <= (SELECT MAX(nxt) FROM pending)
              AND series = 'EQ' AND close IS NOT NULL AND close > 0
        """)
        con.execute("""
            UPDATE out.signals SET fwd_ret_1m = sub.fwd_ret
            FROM (
                SELECT p.formation_date, p.underlying, (a2.close - a1.close) / a1.close AS fwd_ret
                FROM pending p
                JOIN eq_sub a1 ON a1.symbol = p.underlying AND a1.trade_date = p.formation_date
                JOIN eq_sub a2 ON a2.symbol = p.underlying AND a2.trade_date = p.nxt
            ) sub
            WHERE out.signals.formation_date = sub.formation_date
              AND out.signals.underlying = sub.underlying
        """)
    con.execute("COMMIT")

    total = con.execute("SELECT COUNT(*) FROM out.signals").fetchone()[0]
    n_form = con.execute("SELECT COUNT(DISTINCT formation_date) FROM out.signals").fetchone()[0]
    con.close()
    return total, n_form


def _replace_with_baseline(built: Path):
    if OUT_DB.exists():
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        baseline = BASELINE_DIR / f"ts_basis_daily_signals_{datetime.now():%Y%m%d_%H%M%S}.duckdb"
        shutil.copy2(OUT_DB, baseline)
        if baseline.stat().st_size != OUT_DB.stat().st_size or baseline.stat().st_size == 0:
            raise RuntimeError(f"baseline copy {baseline} does not match {OUT_DB} — store left untouched")
        print(f"  Baseline: {baseline}")
    os.replace(built, OUT_DB)


def main():
    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    incremental = "--incremental" in sys.argv
    t0 = time.time()

    if incremental and OUT_DB.exists():
        existing = _existing_dates(OUT_DB)
        print(f"Found {len(existing)} existing formations, last={max(existing) if existing else None}")
        total, n_form = _build(OUT_DB, existing)
    else:
        built = OUT_DB.with_name(OUT_DB.stem + ".rebuild.duckdb")
        built.unlink(missing_ok=True)
        total, n_form = _build(built, set())
        if not n_form:
            raise RuntimeError(f"full rebuild produced no formations — {OUT_DB} left untouched")
        _replace_with_baseline(built)

    print(f"\nDone: {total:,} signals, {n_form} formations -> {OUT_DB} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
