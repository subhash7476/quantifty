"""MRLC-test daily extension: 2012-2022 out-of-sample read for the 1d variant.

Uses the certified equity_bhavcopy_adjusted view (CA-adjusted, point-in-time
symbols, real volume) materialized once, then runs the same sweep/reclaim engine
on daily bars. Era-accurate delivery fees apply automatically (pre-2020 stamp
duty uses the disclosed Maharashtra-representative 0.01% assumption).
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.mrlc_test.engine import run_symbol  # noqa: E402

ADJ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
EXT_DB = ROOT / "data" / "mrlc_test" / "daily_ext.duckdb"
OUT_DIR = ROOT / "data" / "mrlc_test"
LO, HI = "2012-01-01", "2022-12-31"
MIN_SESSIONS = 400


def materialize():
    if EXT_DB.exists():
        EXT_DB.unlink()
    dst = duckdb.connect(str(EXT_DB))
    dst.execute(f"ATTACH '{ADJ_DB.as_posix()}' AS src (READ_ONLY)")
    print("materializing adjusted view 2012-2022 (one-time, ~1-2 min)...")
    dst.execute(
        "CREATE TABLE ext AS "
        "SELECT trade_date, symbol, open, high, low, close, volume "
        "FROM src.equity_bhavcopy_adjusted "
        "WHERE trade_date BETWEEN ? AND ?", [LO, HI])
    n = dst.execute("SELECT count(*) FROM ext").fetchone()[0]
    syms = dst.execute("SELECT count(DISTINCT symbol) FROM ext").fetchone()[0]
    print(f"  {n:,} rows, {syms} symbols")
    dst.close()


def run(stop_mult, news_guard):
    con = duckdb.connect(str(EXT_DB), read_only=True)
    universe = con.execute(
        "SELECT symbol, count(DISTINCT trade_date) n_sess, "
        "median(volume) med_vol FROM ext "
        "GROUP BY symbol HAVING n_sess >= ? AND med_vol > 0", [MIN_SESSIONS]
    ).fetchdf()
    print(f"universe: {len(universe)} symbols with >= {MIN_SESSIONS} sessions 2012-2022")
    all_trades = []
    skipped = [0]
    for sym in universe["symbol"]:
        bars = con.execute(
            "SELECT trade_date AS ts, open, high, low, close, volume "
            "FROM ext WHERE symbol = ? ORDER BY trade_date", [sym]).fetchdf()
        all_trades.extend(run_symbol(bars, bars, stop_mult, sym, "1d_ext",
                                     news_guard=news_guard, skipped_counter=skipped))
    df = pd.DataFrame(all_trades)
    tag = "guard" if news_guard else ""
    out = OUT_DIR / f"trades_ext_{str(stop_mult).replace('.', '_')}{'_' if tag else ''}{tag}.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} trades (skipped {skipped[0]}) -> {out}")
    for t in (10.0, 15.0, 20.0):
        sub = df[df["divergence_pct"] <= -t]
        print(f"  <=-{t:.0f}%: {len(sub)} trades, "
              f"{(sub['r_net'] > 0).sum() if len(sub) else 0} winners, "
              f"avg net R {sub['r_net'].mean() if len(sub) else 0:.2f}")
    con.close()


if __name__ == "__main__":
    materialize()
    run(2.0, False)
    run(2.0, True)
    run(1.5, True)
