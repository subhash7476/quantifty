"""IVOL section 3 -- signal construction (idiosyncratic realized volatility).

Builds monthly formation signals from the continuous futures series:
  1. Trailing 60-session realized volatility (annualized)
  2. Cross-sectional z-score (winsorize +-3 sigma) -> z_ivol (high = high vol)
  3. Beta + sector neutralization -> z_ivol_neut (the IVOL / BAB signal)

The predicted IC of z_ivol vs forward returns is NEGATIVE (high vol -> low return).
Long low-z_ivol (low vol), short high-z_ivol (high vol).

Reads continuous.duckdb (built by Trend's build_continuous.py, reused unchanged).
Output: data/signal_engine/ivol/signals.duckdb

Construction frozen by IVOL_PHASE0_PRE_REGISTRATION.md sections 3-4 (SHA on file).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CONT_DB = ROOT / "data" / "signal_engine" / "trend" / "continuous.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
NIFTY_DB = ROOT / "data" / "signal_engine" / "carry" / "nifty50.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "ivol" / "signals.duckdb"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"

VOL_WINDOW = 60  # trailing sessions for realized vol (matches Trend VOL_WINDOW)
WINSORIZE_SD = 3.0
ADV_THRESHOLD_CR = 5.0
BETA_DAYS = 252
BETA_MIN_OBS = 200


def _adv_at_date(con, fdate):
    rows = con.execute(f"""
        SELECT underlying, MEDIAN(val_in_lakh) AS adv_lakh
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM fut.futures_bhavcopy
            WHERE inst_type='FUTSTK'
              AND trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '30 days'
        )
        WHERE rn <= 20
        GROUP BY underlying
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _realized_vol(con, underlying, fdate, nrows):
    prices = con.execute(f"""
        SELECT adj_close
        FROM cont.trend_continuous
        WHERE underlying = '{underlying}'
          AND trade_date <= DATE '{fdate}'
        ORDER BY trade_date DESC
        LIMIT {nrows}
    """).fetchall()
    if len(prices) < VOL_WINDOW + 2:
        return None
    p_arr = np.array([r[0] for r in reversed(prices)], float)
    log_rets = np.log(p_arr[1:] / p_arr[:-1])
    if len(log_rets) < VOL_WINDOW:
        return None
    rv = float(np.std(log_rets[-VOL_WINDOW:], ddof=1) * np.sqrt(252))
    return rv if rv > 0 else None


def main():
    con = duckdb.connect()
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{CONT_DB}' AS cont (READ_ONLY)")
    con.execute(f"ATTACH '{NIFTY_DB}' AS ndx (READ_ONLY)")
    con.execute("SET threads=4")

    sector_map = {}
    with open(SECTOR_CSV) as f:
        next(f)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                sector_map[parts[0]] = parts[1]

    fmt_dates = [
        r[0] for r in con.execute("""
            WITH ranked AS (
                SELECT trade_date, ROW_NUMBER() OVER (
                    PARTITION BY year(trade_date), month(trade_date) ORDER BY trade_date DESC
                ) AS rn
                FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK'
            )
            SELECT trade_date FROM ranked WHERE rn = 1 ORDER BY trade_date
        """).fetchall()
    ]
    fmt_dates = [d for d in fmt_dates if d >= date(2017, 2, 1)]
    print(f"Formations: {len(fmt_dates)} ({fmt_dates[0]} -> {fmt_dates[-1]})")

    SIG_DB.parent.mkdir(parents=True, exist_ok=True)
    if SIG_DB.exists():
        SIG_DB.unlink()
    sig = duckdb.connect(str(SIG_DB))
    sig.execute("SET threads=2")
    sig.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    sig.execute(f"ATTACH '{NIFTY_DB}' AS ndx (READ_ONLY)")
    sig.execute(f"ATTACH '{CONT_DB}' AS cont (READ_ONLY)")

    sig.execute("""
        CREATE TABLE formations (
            formation_date DATE PRIMARY KEY,
            fwd_formation_date DATE,
            n_liquid INT,
            n_scored INT,
            mean_ivol DOUBLE,
            sd_ivol DOUBLE
        )
    """)
    sig.execute("""
        CREATE TABLE signals (
            formation_date DATE,
            underlying VARCHAR,
            entity VARCHAR,
            sector VARCHAR,
            ivol_raw DOUBLE,
            z_ivol DOUBLE,
            z_ivol_neut DOUBLE,
            beta DOUBLE,
            fwd_ret_1m DOUBLE,
            liquid BOOLEAN,
            PRIMARY KEY (formation_date, underlying)
        )
    """)

    fwd_map = {}
    for i, d in enumerate(fmt_dates):
        fwd_map[d] = fmt_dates[i + 1] if i + 1 < len(fmt_dates) else None

    n_form = len(fmt_dates)
    sig_con = sig.cursor()
    nrows = VOL_WINDOW + 10

    for idx, fdate in enumerate(fmt_dates):
        if (idx + 1) % 10 == 0:
            print(f"  {idx+1}/{n_form}: {fdate}")
            sys.stdout.flush()

        nfdate = fwd_map.get(fdate)
        adv = _adv_at_date(con, fdate)
        liquid_set = {u for u, v in adv.items() if v is not None and v >= ADV_THRESHOLD_CR * 100}
        if not liquid_set:
            continue

        name_data = []
        for u in liquid_set:
            rv = _realized_vol(con, u, fdate, nrows)
            if rv is None:
                continue
            name_data.append({
                "underlying": u,
                "entity": u,
                "sector": sector_map.get(u, "UNKNOWN"),
                "ivol_raw": rv,
            })

        if len(name_data) < 5:
            continue

        raw_vals = np.array([d["ivol_raw"] for d in name_data], float)
        mean_v = float(np.mean(raw_vals))
        sd_v = float(np.std(raw_vals, ddof=1)) if len(raw_vals) > 1 else 0.0
        if sd_v > 0:
            resid = raw_vals - mean_v
            clipped = np.clip(resid, -WINSORIZE_SD * sd_v, WINSORIZE_SD * sd_v)
            sd_clip = float(np.std(clipped, ddof=1))
            z = clipped / sd_clip if sd_clip > 0 else np.zeros_like(clipped)
        else:
            z = np.zeros_like(raw_vals)
        for i, d in enumerate(name_data):
            d["z_ivol"] = float(z[i])

        sig.execute("INSERT INTO formations VALUES (?, ?, ?, ?, ?, ?)",
                    [fdate, nfdate, len(name_data), len(name_data), mean_v, sd_v])
        for d in name_data:
            sig_con.execute(
                "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)",
                [fdate, d["underlying"], d["entity"], d["sector"],
                 d["ivol_raw"], d["z_ivol"], True],
            )

    print("Computing forward returns...")
    sig.execute("""
        CREATE TEMP TABLE fwd_t AS
        SELECT s.formation_date, s.underlying,
               (a2.close - a1.close) / NULLIF(a1.close, 0) AS fwd_ret
        FROM signals s
        JOIN eq.equity_bhavcopy_adjusted a1
            ON a1.symbol = s.underlying AND a1.trade_date = s.formation_date AND a1.series='EQ'
            AND a1.close > 0
        JOIN formations f ON f.formation_date = s.formation_date AND f.fwd_formation_date IS NOT NULL
        JOIN eq.equity_bhavcopy_adjusted a2
            ON a2.symbol = s.underlying AND a2.trade_date = f.fwd_formation_date AND a2.series='EQ'
            AND a2.close > 0
    """)
    sig.execute("""
        UPDATE signals s
        SET fwd_ret_1m = ft.fwd_ret
        FROM fwd_t ft
        WHERE ft.formation_date = s.formation_date AND ft.underlying = s.underlying
    """)
    sig.execute("DROP TABLE IF EXISTS fwd_t")

    print("Neutralizing: beta + sector...")
    nifty_rows = con.execute("SELECT trade_date, close FROM ndx.nifty50 ORDER BY trade_date").fetchall()
    nifty_map = {}
    for i in range(1, len(nifty_rows)):
        td, c = nifty_rows[i]
        _, pc = nifty_rows[i - 1]
        if pc > 0 and c > 0:
            nifty_map[str(td)] = float(c / pc - 1.0)

    formations = sig.execute(
        "SELECT DISTINCT formation_date FROM signals WHERE z_ivol IS NOT NULL ORDER BY formation_date"
    ).fetchall()

    for fi, (fdate,) in enumerate(formations):
        if (fi + 1) % 20 == 0:
            print(f"  neut {fi+1}/{len(formations)}: {fdate}")
            sys.stdout.flush()
        names = sig.execute(f"""
            SELECT underlying, entity, sector, z_ivol
            FROM signals WHERE formation_date = DATE '{fdate}' AND z_ivol IS NOT NULL
        """).fetchall()
        if len(names) < 5:
            continue
        sym_list = "','".join(r[0] for r in names)
        dates = con.execute(f"""
            SELECT DISTINCT trade_date FROM eq.equity_bhavcopy
            WHERE series='EQ' AND trade_date <= DATE '{fdate}'
            ORDER BY trade_date DESC LIMIT {BETA_DAYS + 5}
        """).fetchall()
        d_min = str(dates[-1][0])
        d_max = str(dates[0][0])
        eq_all = con.execute(f"""
            SELECT symbol, trade_date, close FROM eq.equity_bhavcopy
            WHERE symbol IN ('{sym_list}') AND series='EQ'
              AND trade_date >= DATE '{d_min}' AND trade_date <= DATE '{d_max}'
              AND close > 0
            ORDER BY symbol, trade_date
        """).fetchall()
        eq_map = {}
        cur_sym = None
        for sym, td, close in eq_all:
            if sym != cur_sym:
                cur_sym = sym
                eq_map[sym] = []
            eq_map[sym].append((str(td), float(close)))
        beta_results = []
        for u, ent, sec, z in names:
            prices = eq_map.get(u, [])
            if len(prices) < BETA_MIN_OBS + 1:
                continue
            eq_r, nf_r = [], []
            for td_str, close in prices:
                nret = nifty_map.get(td_str)
                if nret is not None:
                    eq_r.append(close)
                    nf_r.append(nret)
            if len(eq_r) < BETA_MIN_OBS + 1:
                continue
            eq_arr = np.array(eq_r, float)
            nf_arr = np.array(nf_r, float)
            eq_rets = eq_arr[1:] / eq_arr[:-1] - 1.0
            nf_rets_aligned = nf_arr[1:] / nf_arr[:-1] - 1.0
            beta = float(np.cov(eq_rets, nf_rets_aligned)[0, 1] / np.var(nf_rets_aligned)) if np.var(nf_rets_aligned) > 0 else 0.0
            beta_results.append((u, ent, sec, z, beta))
        if len(beta_results) < 5:
            continue
        z_vals = np.array([r[3] for r in beta_results], float)
        beta_vals = np.array([r[4] for r in beta_results], float)
        sectors = [r[2] if r[2] != "UNKNOWN" else sector_map.get(r[0], "UNKNOWN") for r in beta_results]
        all_sec = sorted(set(sectors))
        n, k = len(beta_results), len(all_sec)
        if k <= 1:
            X = np.column_stack([np.ones(n), beta_vals])
        else:
            dmat = np.zeros((n, k))
            for i, s in enumerate(sectors):
                dmat[i, all_sec.index(s)] = 1.0
            X = np.column_stack([np.ones(n), beta_vals, dmat[:, 1:]])
        try:
            bh = np.linalg.lstsq(X, z_vals, rcond=None)[0]
            resid = z_vals - X @ bh
        except np.linalg.LinAlgError:
            continue
        rsd = float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0
        neut = resid / rsd if rsd > 0 else resid
        for i, (u, _, _, _, bv) in enumerate(beta_results):
            sig.execute(f"""
                UPDATE signals SET z_ivol_neut = ?, beta = ?
                WHERE formation_date = DATE '{fdate}' AND underlying = '{u}'
            """, [float(neut[i]), bv])

    total = sig.execute("SELECT COUNT(*) FROM signals WHERE z_ivol_neut IS NOT NULL").fetchone()[0]
    n_f = sig.execute("SELECT COUNT(DISTINCT formation_date) FROM signals WHERE z_ivol_neut IS NOT NULL").fetchone()[0]
    print(f"\nDone: {total:,} neutralized signals across {n_f} formations")
    sig.close()
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
