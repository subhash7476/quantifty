"""TS Basis Daily — signal construction (DuckDB-optimised, incremental).

Computes time-series basis z-scores per (formation_date, underlying) at
**daily** cadence:
  z_ts = (basis_now - trailing_mean) / trailing_std

Usage:
  Full build:    python build_ts_basis_daily.py
  Incremental:   python build_ts_basis_daily.py --incremental
Output: data/signal_engine/ts_basis_daily/ts_signals.duckdb
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
import contract_arms as A

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
OUT_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"

LOOKBACK_ROWS = 252
MIN_OBS = 12
ADV_THRESHOLD_LAKH = 500


def main():
    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    incremental = "--incremental" in sys.argv
    t0 = time.time()

    # Validate existing DB
    existing_dates = set()
    if incremental and OUT_DB.exists():
        ec = None
        try:
            ec = duckdb.connect(str(OUT_DB), read_only=True)
            existing_dates = {r[0] for r in ec.execute(
                "SELECT DISTINCT formation_date FROM signals"
            ).fetchall()}
        except Exception:
            print("  Existing DB corrupt/incomplete, rebuilding from scratch")
        finally:
            if ec is not None:
                try:
                    ec.close()
                except Exception:
                    pass
        if not existing_dates:
            try:
                OUT_DB.unlink()
            except Exception:
                pass
        else:
            print(f"Found {len(existing_dates)} existing formations, last={max(existing_dates)}")

    # Single connection for everything
    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")

    # Attach output DB (creates if missing)
    fresh = not OUT_DB.exists()
    con.execute(f"ATTACH '{OUT_DB}' AS out")

    # Build basis_panel in the same connection
    print("Building basis_panel...")
    n_cells = A.build_basis_panel(con)
    print(f"  {n_cells:,} cells")

    all_fmt_dates = [r[0] for r in con.execute(
        "SELECT DISTINCT trade_date FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK' ORDER BY trade_date"
    ).fetchall()]

    fmt_dates = [d for d in all_fmt_dates if d not in existing_dates]
    if not fmt_dates:
        print("  All formations already built — nothing to do.")
        con.close()
        return 0

    print(f"  {len(all_fmt_dates)} total, {len(fmt_dates)} new: {fmt_dates[0]} -> {fmt_dates[-1]}")

    # ADV lookup
    print("  Building ADV lookup...")
    con.execute("""
        CREATE TEMP TABLE adv_lookup AS
        SELECT trade_date, underlying,
               MEDIAN(val_in_lakh) OVER (
                   PARTITION BY underlying ORDER BY trade_date
                   ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
               ) AS adv_lakh
        FROM (
            SELECT DISTINCT trade_date, underlying, val_in_lakh
            FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK' AND val_in_lakh IS NOT NULL
        )
    """)
    con.execute("""
        CREATE TEMP TABLE adv_filled AS
        SELECT DISTINCT trade_date, underlying,
               LAST_VALUE(adv_lakh IGNORE NULLS) OVER (
                   PARTITION BY underlying ORDER BY trade_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS adv_lakh
        FROM adv_lookup
    """)

    new_date_str = ", ".join(f"DATE '{d}'" for d in fmt_dates)
    print("  Inserting new daily signals...")

    if fresh:
        con.execute(f"""
            CREATE TABLE out.signals AS
            SELECT DISTINCT ON (bp.trade_date, bp.underlying)
                   CAST(bp.trade_date AS DATE) AS formation_date,
                   bp.underlying,
                   bp.annualized_basis AS raw_ann_basis,
                   CAST(NULL AS DOUBLE) AS z_ts,
                   CAST(NULL AS DOUBLE) AS fwd_ret_1m,
                   COALESCE(a.adv_lakh, 0) >= {ADV_THRESHOLD_LAKH} AS liquid
            FROM basis_panel bp
            LEFT JOIN adv_filled a ON a.trade_date = bp.trade_date AND a.underlying = bp.underlying
            WHERE bp.spot_close IS NOT NULL AND bp.annualized_basis IS NOT NULL
        """)
        con.execute("CREATE INDEX idx_sig_date ON out.signals (formation_date)")
        con.execute("CREATE INDEX idx_sig_und ON out.signals (underlying)")
    else:
        con.execute(f"""
            INSERT INTO out.signals
            SELECT DISTINCT ON (bp.trade_date, bp.underlying)
                   CAST(bp.trade_date AS DATE) AS formation_date,
                   bp.underlying,
                   bp.annualized_basis AS raw_ann_basis,
                   CAST(NULL AS DOUBLE) AS z_ts,
                   CAST(NULL AS DOUBLE) AS fwd_ret_1m,
                   COALESCE(a.adv_lakh, 0) >= {ADV_THRESHOLD_LAKH} AS liquid
            FROM basis_panel bp
            LEFT JOIN adv_filled a ON a.trade_date = bp.trade_date AND a.underlying = bp.underlying
            WHERE bp.spot_close IS NOT NULL AND bp.annualized_basis IS NOT NULL
              AND bp.trade_date IN ({new_date_str})
        """)

    n_raw = con.execute("SELECT COUNT(*) FROM out.signals").fetchone()[0]
    print(f"    {n_raw:,} total signals in DB")

    # z_ts: compute only for new dates (window function uses full history)
    print("  Computing z_ts...")
    con.execute(f"""
        UPDATE out.signals s SET z_ts = z.z_ts
        FROM (
            SELECT formation_date, underlying,
                   CASE WHEN COUNT(raw_ann_basis) OVER w >= {MIN_OBS}
                        AND STDDEV_SAMP(raw_ann_basis) OVER w > 1e-8
                   THEN GREATEST(-3.0, LEAST(3.0,
                        (raw_ann_basis - AVG(raw_ann_basis) OVER w)
                        / STDDEV_SAMP(raw_ann_basis) OVER w))
                   ELSE NULL END AS z_ts
            FROM out.signals WHERE raw_ann_basis IS NOT NULL
            WINDOW w AS (PARTITION BY underlying ORDER BY formation_date
                         ROWS BETWEEN {LOOKBACK_ROWS} PRECEDING AND 1 PRECEDING)
        ) z
        WHERE z.formation_date = s.formation_date AND z.underlying = s.underlying
          AND s.formation_date IN ({new_date_str})
    """)
    n_z = con.execute("SELECT COUNT(*) FROM out.signals WHERE z_ts IS NOT NULL").fetchone()[0]
    print(f"    {n_z:,} z-scored")

    # Forward returns: only for new dates
    print("  Computing forward returns...")
    con.execute("""
        CREATE TEMP TABLE fmt AS
        SELECT formation_date, LEAD(formation_date) OVER (ORDER BY formation_date) AS nxt
        FROM (SELECT DISTINCT formation_date FROM out.signals)
    """)

    # Pre-filter equity to new date range for efficiency
    sym_rows = con.execute(f"""
        SELECT DISTINCT underlying FROM out.signals
        WHERE formation_date IN ({new_date_str})
    """).fetchall()
    all_syms = [r[0] for r in sym_rows]

    if all_syms:
        sym_str = ", ".join(f"'{s}'" for s in all_syms)
        lo = fmt_dates[0]
        hi = fmt_dates[-1]
        con.execute(f"""
            CREATE TEMP TABLE eq_sub AS
            SELECT symbol, trade_date, close
            FROM eq.equity_bhavcopy_adjusted
            WHERE symbol IN ({sym_str})
              AND trade_date >= DATE '{lo}'
              AND trade_date <= DATE '{hi}'
              AND series = 'EQ' AND close IS NOT NULL AND close > 0
        """)

        con.execute(f"""
            UPDATE out.signals SET fwd_ret_1m = sub.fwd_ret
            FROM (
                SELECT s2.formation_date, s2.underlying,
                       (a2.close - a1.close) / a1.close AS fwd_ret
                FROM out.signals s2
                JOIN fmt f ON f.formation_date = s2.formation_date AND f.nxt IS NOT NULL
                JOIN eq_sub a1 ON a1.symbol = s2.underlying AND a1.trade_date = s2.formation_date
                JOIN eq_sub a2 ON a2.symbol = s2.underlying AND a2.trade_date = f.nxt
                WHERE s2.formation_date IN ({new_date_str})
            ) sub
            WHERE out.signals.formation_date = sub.formation_date
              AND out.signals.underlying = sub.underlying
        """)

    n_fw = con.execute("SELECT COUNT(*) FROM out.signals WHERE fwd_ret_1m IS NOT NULL").fetchone()[0]
    print(f"    {n_fw:,} with fwd_ret")

    total = con.execute("SELECT COUNT(*) FROM out.signals").fetchone()[0]
    n_form = con.execute("SELECT COUNT(DISTINCT formation_date) FROM out.signals").fetchone()[0]
    con.close()

    elapsed = time.time() - t0
    print(f"\nDone: {total:,} signals, {n_form} formations -> {OUT_DB} ({elapsed:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
