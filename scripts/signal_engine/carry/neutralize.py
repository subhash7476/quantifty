"""Carry §4 — beta and sector neutralization.

Reads signals from build_carry.py, computes trailing 252-day beta to Nifty 50,
then residualizes z_carry against beta + sector dummies via cross-sectional OLS
per formation date.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]

FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "weekly_signals.duckdb"
NIFTY_DB = ROOT / "data" / "signal_engine" / "carry" / "nifty50.duckdb"

BETA_DAYS = 252
BETA_MIN_OBS = 200


def main():
    if not SIG_DB.exists():
        print("ERROR: signals DB not found. Run build_carry.py first.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_WRITE)")
    con.execute(f"ATTACH '{NIFTY_DB}' AS ndx (READ_ONLY)")
    con.execute("SET threads=4")

    nix_rows = con.execute("SELECT COUNT(*) FROM ndx.nifty50").fetchone()[0]
    print(f"Nifty 50 rows: {nix_rows:,}")

    sector_csv = ROOT / "governance" / "carry" / "sector_classification.csv"
    sector_map = {}
    with open(sector_csv) as f:
        next(f)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                sector_map[parts[0]] = parts[1]

    formations = con.execute("""
        SELECT DISTINCT s.formation_date
        FROM sig.signals s
        WHERE s.z_carry IS NOT NULL
        ORDER BY s.formation_date
    """).fetchall()

    n_form = len(formations)
    print(f"Neutralizing {n_form} formations...")

    # Pre-build Nifty 50 daily returns as {date: ret}
    nifty_rows = con.execute("""
        SELECT trade_date, close FROM ndx.nifty50 ORDER BY trade_date
    """).fetchall()
    nifty_map = {}
    prev = None
    for td, close in nifty_rows:
        if prev is not None and prev[1] > 0 and close > 0:
            ret = (close - prev[1]) / prev[1]
            nifty_map[str(td)] = ret
        prev = (td, close)
    print(f"  Nifty daily returns: {len(nifty_map)}")

    for fi, (fdate,) in enumerate(formations):
        if (fi + 1) % 20 == 0 or fi == 0:
            print(f"  {fi+1}/{n_form}: {fdate}")
            sys.stdout.flush()

        names = con.execute(f"""
            SELECT underlying, entity, sector, z_carry
            FROM sig.signals
            WHERE formation_date = DATE '{fdate}'
              AND z_carry IS NOT NULL
              AND liquid = TRUE
        """).fetchall()

        if len(names) < 5:
            continue

        # Build beta for each name using daily returns
        beta_results = []
        for u, ent, sec, z in names:
            equity_rets = con.execute(f"""
                WITH prices AS (
                    SELECT trade_date, close
                    FROM eq.equity_bhavcopy
                    WHERE symbol = '{u}' AND series = 'EQ'
                      AND trade_date <= DATE '{fdate}'
                      AND close IS NOT NULL AND close > 0
                    ORDER BY trade_date DESC
                    LIMIT {BETA_DAYS + 5}
                )
                SELECT p.trade_date, (p.close / LAG(p.close) OVER (ORDER BY p.trade_date) - 1) AS ret
                FROM prices p
            """).fetchall()

            eq_rets = []
            nf_rets = []
            for td, ret in equity_rets:
                if ret is None:
                    continue
                td_s = str(td)
                nret = nifty_map.get(td_s)
                if nret is not None:
                    eq_rets.append(float(ret))
                    nf_rets.append(nret)

            if len(eq_rets) < BETA_MIN_OBS:
                continue

            eq_arr = np.array(eq_rets, float)
            nf_arr = np.array(nf_rets, float)
            beta = float(np.cov(eq_arr, nf_arr)[0, 1] / np.var(nf_arr)) if np.var(nf_arr) > 0 else 0.0
            beta_results.append((u, ent, sec, z, beta))

        if len(beta_results) < 5:
            continue

        z_vals = np.array([r[3] for r in beta_results], float)
        beta_vals = np.array([r[4] for r in beta_results], float)
        sectors = [r[2] if r[2] and r[2] != "UNKNOWN" else sector_map.get(r[0], "UNKNOWN") for r in beta_results]
        all_sectors = sorted(set(sectors))
        n = len(beta_results)
        k = len(all_sectors)

        if k <= 1:
            X = np.column_stack([np.ones(n), beta_vals])
        else:
            dummy = np.zeros((n, k))
            for i, s in enumerate(sectors):
                dummy[i, all_sectors.index(s)] = 1.0
            X = np.column_stack([np.ones(n), beta_vals, dummy[:, 1:]])

        try:
            beta_hat = np.linalg.lstsq(X, z_vals, rcond=None)[0]
            resid = z_vals - X @ beta_hat
        except np.linalg.LinAlgError:
            continue

        resid_sd = float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0
        neut = resid / resid_sd if resid_sd > 0 else resid

        for i, (u, _, _, _, bv) in enumerate(beta_results):
            con.execute(f"""
                UPDATE sig.signals
                SET z_carry_neut = ?, beta = ?
                WHERE formation_date = DATE '{fdate}' AND underlying = '{u}'
            """, [float(neut[i]), bv])

    total = con.execute("SELECT COUNT(*) FROM sig.signals WHERE z_carry_neut IS NOT NULL").fetchone()[0]
    n_f = con.execute("SELECT COUNT(DISTINCT formation_date) FROM sig.signals WHERE z_carry_neut IS NOT NULL").fetchone()[0]
    print(f"\nDone: {total:,} neutralized signals across {n_f} formations")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
