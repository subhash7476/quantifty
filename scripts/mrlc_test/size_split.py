"""MRLC-test Step 1: size-split test.

Does the 2012-2022 daily edge survive in the ~196 names we can actually trade
(live 1m universe) and in the top-200-by-turnover names, vs the full 2,300-name
extension? Same engine, same era fees, news guard ON, 2x stop.
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.mrlc_test.engine import run_symbol  # noqa: E402

EXT_DB = ROOT / "data" / "mrlc_test" / "daily_ext.duckdb"
ADJ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
UNIVERSE_CSV = ROOT / "data" / "mrlc_test" / "universe.csv"
OUT_DIR = ROOT / "data" / "mrlc_test"
LO, HI = "2012-01-01", "2022-12-31"
MIN_SESSIONS = 400


def live_universe_tickers():
    uni = pd.read_csv(UNIVERSE_CSV)["symbol"].tolist()
    isins = {s.split("|")[1] for s in uni}
    con = duckdb.connect(str(ADJ_DB), read_only=True)
    rows = con.execute("SELECT symbol, isin FROM symbol_isin").fetchall()
    con.close()
    by_isin = {i: s for s, i in rows}
    tickers = sorted({by_isin[i] for i in isins if i in by_isin})
    missing = isins - set(by_isin)
    print(f"live universe: {len(isins)} ISINs -> {len(tickers)} mapped tickers, "
          f"{len(missing)} unmapped")
    return tickers


def top_turnover_tickers(n=200):
    con = duckdb.connect(str(ADJ_DB), read_only=True)
    con.execute(f"ATTACH '{EXT_DB.as_posix()}' AS ext (READ_ONLY)")
    rows = con.execute(
        "SELECT symbol, median(volume * close) mt FROM ext.ext "
        "GROUP BY symbol ORDER BY mt DESC LIMIT ?", [n]).fetchall()
    con.close()
    return [r[0] for r in rows]


def run(tickers, tag):
    con = duckdb.connect(str(EXT_DB), read_only=True)
    all_trades = []
    skipped = [0]
    for sym in tickers:
        bars = con.execute(
            "SELECT trade_date AS ts, open, high, low, close, volume "
            "FROM ext WHERE symbol = ? ORDER BY trade_date", [sym]).fetchdf()
        if len(bars) < 30:
            continue
        all_trades.extend(run_symbol(bars, bars, 2.0, sym, "1d_ext",
                                     news_guard=True, skipped_counter=skipped))
    df = pd.DataFrame(all_trades)
    out = OUT_DIR / f"trades_{tag}.csv"
    df.to_csv(out, index=False)
    con.close()
    print(f"\n== {tag}: {len(df)} trades (guard skipped {skipped[0]}) == ")
    for t in (10.0, 15.0, 20.0):
        sub = df[df["divergence_pct"] <= -t]
        n = len(sub)
        if n == 0:
            print(f"  <=-{t:.0f}%: 0 trades")
            continue
        mean = sub["r_net"].mean()
        tt = mean / (sub["r_net"].std(ddof=1) / np.sqrt(n))
        print(f"  <=-{t:.0f}%: n={n} win={(sub['r_net'] > 0).mean() * 100:.1f}% "
              f"exp={mean:.3f} t={tt:.2f} total={sub['r_net'].sum():.1f}")
    return df


if __name__ == "__main__":
    live = live_universe_tickers()
    run(live, "live_196")
    top = top_turnover_tickers(200)
    print(f"\ntop-200 by turnover proxy: {len(top)} tickers")
    run(top, "top_200")
