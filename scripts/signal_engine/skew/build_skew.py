"""Skew §3 — signal construction.

Builds monthly formation signals from option-implied skew:
  1. Load option chain from stock_options_bhavcopy
  2. Compute IV per contract via Black76 inversion
  3. Find nearest monthly expiry with ≥10 days to expiry
  4. Interpolate IV at 25-delta strikes for CE/PE
  5. Skew = IV(25Δ put) − IV(25Δ call)
  6. Winsorize ±3σ, cross-sectional z-score
  7. Liquidity screen: top 50–100 by 20-day option turnover

Output: data/signal_engine/skew/signals.duckdb
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "skew"))
from volatility import VolatilityInversion

OPT_DB = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "skew" / "signals.duckdb"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"

# Constants
RISK_FREE_RATE = 0.07  # 7% RBI repo rate baseline
LIQUIDITY_WINDOW_DAYS = 30  # calendar-day window for ~20 trading days
TOP_N_LIQUID = 100  # top N by option turnover
MIN_DAYS_TO_EXPIRY = 10
MIN_OPTION_PRICE = 0.1  # skip penny options
WINSORIZE_SD = 3.0
TRAIN_LO = date(2016, 7, 31)
TRAIN_HI = date(2020, 12, 31)
HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)


def _formation_grid(con):
    """Monthly formation dates: last trading day of each calendar month."""
    return [
        r[0] for r in con.execute("""
            WITH ranked AS (
                SELECT trade_date, ROW_NUMBER() OVER (
                    PARTITION BY year(trade_date), month(trade_date) ORDER BY trade_date DESC
                ) AS rn
                FROM opt.stock_options_bhavcopy
                WHERE trade_date >= DATE '2016-07-01' AND trade_date <= DATE '2022-12-31'
            )
            SELECT DISTINCT trade_date FROM ranked WHERE rn = 1 ORDER BY trade_date
        """).fetchall()
    ]


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


def _liquidity_rank(con, fdate, lookback=LIQUIDITY_WINDOW_DAYS):
    """Top N underlyings by trailing 20-day option turnover."""
    rows = con.execute(f"""
        SELECT underlying, SUM(val_in_lakh) AS total_turnover
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM opt.stock_options_bhavcopy
            WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{lookback} days'
        )
        WHERE rn <= 20 AND val_in_lakh IS NOT NULL
        GROUP BY underlying
        ORDER BY total_turnover DESC
        LIMIT {TOP_N_LIQUID}
    """).fetchall()
    return {r[0] for r in rows}


def _get_nearest_monthly_expiry(con, fdate):
    """Find nearest monthly expiry with ≥10 days to expiry."""
    row = con.execute(f"""
        SELECT expiry_dt
        FROM opt.stock_options_bhavcopy
        WHERE trade_date = DATE '{fdate}'
          AND expiry_dt > DATE '{fdate}'
          AND (DATEDIFF('day', DATE '{fdate}', expiry_dt) >= {MIN_DAYS_TO_EXPIRY})
          AND expiry_dt <= DATE '{fdate}' + INTERVAL 60 days
        GROUP BY expiry_dt
        ORDER BY ABS(DATEDIFF('day', DATE '{fdate}', expiry_dt) - 30)
        LIMIT 1
    """).fetchone()
    return row[0] if row else None


def _get_spot_price(con, fdate, underlying):
    """Get raw spot close for underlying at formation date."""
    row = con.execute(f"""
        SELECT close FROM eq.equity_bhavcopy
        WHERE symbol = '{underlying}' AND series = 'EQ'
          AND trade_date = DATE '{fdate}'
          AND close IS NOT NULL AND close > 0
    """).fetchone()
    return row[0] if row else None


def main():
    if not OPT_DB.exists():
        print("ERROR: stock_options_bhavcopy.duckdb not found.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{OPT_DB}' AS opt (READ_ONLY)")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute("SET threads=4")

    print("Computing formation grid...")
    fmt_dates = _formation_grid(con)
    print(f"  {len(fmt_dates)} formations: {fmt_dates[0]} -> {fmt_dates[-1]}")

    sector_map = _load_sector_map()
    print(f"  {len(sector_map)} symbols in sector map")

    SIG_DB.parent.mkdir(parents=True, exist_ok=True)
    if SIG_DB.exists():
        SIG_DB.unlink()
    sig = duckdb.connect(str(SIG_DB))
    sig.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    sig.execute("SET threads=2")

    sig.execute("""
        CREATE TABLE formations (
            formation_date DATE PRIMARY KEY,
            fwd_formation_date DATE,
            expiry_dt DATE,
            n_liquid INT,
            n_scored INT,
            mean_skew DOUBLE,
            sd_skew DOUBLE
        )
    """)
    sig.execute("""
        CREATE TABLE signals (
            formation_date DATE,
            underlying VARCHAR,
            entity VARCHAR,
            sector VARCHAR,
            iv_25d_call DOUBLE,
            iv_25d_put DOUBLE,
            skew DOUBLE,
            z_skew DOUBLE,
            z_skew_neut DOUBLE,
            beta DOUBLE,
            fwd_ret_1m DOUBLE,
            liquid BOOLEAN,
            PRIMARY KEY (formation_date, underlying)
        )
    """)

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
            sys.stdout.flush()

        nfdate = fwd_map.get(fdate)
        expiry_dt = _get_nearest_monthly_expiry(con, fdate)
        if not expiry_dt:
            continue

        days_to_expiry = (expiry_dt - fdate).days
        T = days_to_expiry / 365.0

        liquid_set = _liquidity_rank(con, fdate)

        option_rows = con.execute(f"""
            SELECT underlying, strike, option_type, close
            FROM opt.stock_options_bhavcopy
            WHERE trade_date = DATE '{fdate}'
              AND expiry_dt = DATE '{expiry_dt}'
              AND close IS NOT NULL AND close > {MIN_OPTION_PRICE}
              AND open_int > 0
        """).fetchall()

        if not option_rows:
            continue

        name_skew = {}
        for u in liquid_set:
            spot = _get_spot_price(con, fdate, u)
            if not spot or spot <= 0:
                continue

            ce_strikes = []
            pe_strikes = []
            ce_prices = {}
            pe_prices = {}

            for ud, strike, opt_type, price in option_rows:
                if ud != u:
                    continue
                if opt_type == 'CE':
                    ce_strikes.append(strike)
                    ce_prices[strike] = price
                else:
                    pe_strikes.append(strike)
                    pe_prices[strike] = price

            if not ce_strikes or not pe_strikes:
                continue

            iv_ce_map = {}
            iv_pe_map = {}

            for K, market_price in ce_prices.items():
                iv = VolatilityInversion.calculate_iv(
                    F=spot, K=K, T=T, r=RISK_FREE_RATE,
                    market_price=market_price, option_type='CE'
                )
                if iv:
                    iv_ce_map[K] = iv

            for K, market_price in pe_prices.items():
                iv = VolatilityInversion.calculate_iv(
                    F=spot, K=K, T=T, r=RISK_FREE_RATE,
                    market_price=market_price, option_type='PE'
                )
                if iv:
                    iv_pe_map[K] = iv

            if not iv_ce_map or not iv_pe_map:
                continue

            ce_ivs = sorted(iv_ce_map.items())
            pe_ivs = sorted(iv_pe_map.items())

            atm_iv = None
            for K, iv in ce_ivs:
                if abs(K - spot) / spot < 0.02:
                    atm_iv = iv
                    break

            if not atm_iv:
                if ce_ivs:
                    idx = min(range(len(ce_ivs)), key=lambda i: abs(ce_ivs[i][0] - spot))
                    atm_iv = ce_ivs[idx][1]

            if not atm_iv:
                continue

            strike_25d_ce = VolatilityInversion.find_strike_at_delta(
                F=spot, T=T, r=RISK_FREE_RATE, sigma=atm_iv,
                target_delta=0.25, option_type='CE', strikes=[k for k, _ in ce_ivs]
            )
            strike_25d_pe = VolatilityInversion.find_strike_at_delta(
                F=spot, T=T, r=RISK_FREE_RATE, sigma=atm_iv,
                target_delta=0.25, option_type='PE', strikes=[k for k, _ in pe_ivs]
            )

            if not strike_25d_ce or not strike_25d_pe:
                continue

            def interpolate_iv(strike_map, target_strike):
                if not strike_map:
                    return None
                ks = sorted(strike_map.keys())
                if len(ks) == 1:
                    return strike_map[ks[0]]
                if target_strike <= ks[0]:
                    return strike_map[ks[0]]
                if target_strike >= ks[-1]:
                    return strike_map[ks[-1]]
                for i in range(len(ks) - 1):
                    if ks[i] <= target_strike <= ks[i + 1]:
                        w = (target_strike - ks[i]) / (ks[i + 1] - ks[i])
                        return (1 - w) * strike_map[ks[i]] + w * strike_map[ks[i + 1]]
                return None

            iv_25d_ce = interpolate_iv(iv_ce_map, strike_25d_ce)
            iv_25d_pe = interpolate_iv(iv_pe_map, strike_25d_pe)

            if iv_25d_ce is None or iv_25d_pe is None:
                continue

            skew = iv_25d_pe - iv_25d_ce
            name_skew[u] = {
                "iv_25d_ce": iv_25d_ce,
                "iv_25d_pe": iv_25d_pe,
                "skew": skew,
                "liquid": True,
            }

        if not name_skew:
            continue

        skew_vals = np.array([d["skew"] for d in name_skew.values()], dtype=float)
        mean_s = float(np.mean(skew_vals))
        sd_s = float(np.std(skew_vals, ddof=1)) if len(skew_vals) > 1 else 0.0

        if sd_s > 0:
            resid = skew_vals - mean_s
            resid_clipped = np.clip(resid, -WINSORIZE_SD * sd_s, WINSORIZE_SD * sd_s)
            sd_clip = float(np.std(resid_clipped, ddof=1))
            z = resid_clipped / sd_clip if sd_clip > 0 else np.zeros_like(resid_clipped)
        else:
            z = np.zeros_like(skew_vals)

        for u, d in name_skew.items():
            d["z_skew"] = float(z[list(name_skew.keys()).index(u)])
            d["entity"] = u
            d["sector"] = sector_map.get(u, "UNKNOWN")

        sig.execute(
            "INSERT INTO formations VALUES (?, ?, ?, ?, ?, ?, ?)",
            [fdate, nfdate, expiry_dt, len(name_skew), len(name_skew), mean_s, sd_s],
        )

        sig_con = sig.cursor()
        for u, d in name_skew.items():
            sig_con.execute(
                "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)",
                [fdate, u, d["entity"], d["sector"], d["iv_25d_ce"],
                 d["iv_25d_pe"], d["skew"], d["z_skew"], d["liquid"]],
            )

    print("\nComputing forward returns...")
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

    total_sig = sig.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    n_f = sig.execute("SELECT COUNT(DISTINCT formation_date) FROM signals").fetchone()[0]
    print(f"\nDone: {total_sig:,} signals across {n_f} formations")
    print(f"  Signals DB: {SIG_DB}")

    sig.close()
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())