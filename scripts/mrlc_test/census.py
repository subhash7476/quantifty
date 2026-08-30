"""MRLC-test census: verify equity 1m coverage 2023->now and build the universe."""
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ONE_MIN_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
OUT_DIR = ROOT / "data" / "mrlc_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = "2023-01-01"
UNIVERSE_MIN_SESSIONS = 400
UNIVERSE_MIN_AVG_BARS = 300


def main():
    files = sorted(ONE_MIN_DIR.glob("*.duckdb"))
    rows = []
    for f in files:
        d = f.stem
        if d < START:
            continue
        con = duckdb.connect(str(f), read_only=True)
        try:
            q = con.execute(
                """
                SELECT count(*) AS rows_total,
                       sum(CASE WHEN symbol LIKE 'NSE_EQ|%' THEN 1 ELSE 0 END) AS rows_eq,
                       sum(CASE WHEN symbol LIKE 'NSE_EQ|%' AND is_synthetic THEN 1 ELSE 0 END) AS rows_synth,
                       count(DISTINCT CASE WHEN symbol LIKE 'NSE_EQ|%' THEN symbol END) AS syms_eq
                FROM candles
                """
            ).fetchone()
        except Exception as exc:
            print(f"  !! {d}: {exc}")
            con.close()
            continue
        con.close()
        rows.append((d, q[0], q[1], q[2], q[3]))

    df = pd.DataFrame(rows, columns=["date", "rows_total", "rows_eq", "rows_synth", "syms_eq"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    print("=" * 70)
    print("CENSUS — equity 1m coverage 2023 -> now")
    print("=" * 70)
    print(f"files scanned : {len(df)}")
    print(f"span          : {df['date'].min().date()} -> {df['date'].max().date()}")
    eq = df[df["rows_eq"] > 0]
    print(f"dates w/ equity rows : {len(eq)}")
    print(f"avg symbols/day      : {eq['syms_eq'].mean():.1f}  (min {eq['syms_eq'].min()}, max {eq['syms_eq'].max()})")
    print(f"total equity rows    : {eq['rows_eq'].sum():,}")
    print(f"synthetic rows       : {df['rows_synth'].sum():,} (CAS carry-forward, will be excluded)")
    print(f"dates missing equity (gaps): {df[df['rows_eq'] == 0]['date'].dt.date.tolist()}")

    per_sym = []
    for f in files:
        d = f.stem
        if d < START:
            continue
        con = duckdb.connect(str(f), read_only=True)
        q = con.execute(
            """
            SELECT symbol, count(*) AS n, sum(CASE WHEN is_synthetic THEN 1 ELSE 0 END) AS synth
            FROM candles WHERE symbol LIKE 'NSE_EQ|%' GROUP BY symbol
            """
        ).fetchall()
        con.close()
        for sym, n, s in q:
            per_sym.append((d, sym, n, s))
    sym_df = pd.DataFrame(per_sym, columns=["date", "symbol", "bars", "synth"])
    agg = (
        sym_df.groupby("symbol")
        .agg(sessions=("date", "nunique"), avg_bars=("bars", "mean"))
        .reset_index()
    )
    universe = agg[(agg["sessions"] >= UNIVERSE_MIN_SESSIONS) & (agg["avg_bars"] >= UNIVERSE_MIN_AVG_BARS)]
    universe = universe.sort_values("symbol").reset_index(drop=True)
    print()
    print(f"UNIVERSE: {len(universe)} symbols with >= {UNIVERSE_MIN_SESSIONS} sessions and avg >= {UNIVERSE_MIN_AVG_BARS} bars/session")
    print(f"  sessions min/median/max : {universe['sessions'].min()} / {universe['sessions'].median():.0f} / {universe['sessions'].max()}")
    universe.to_csv(OUT_DIR / "universe.csv", index=False)
    print(f"universe saved -> {OUT_DIR / 'universe.csv'}")


if __name__ == "__main__":
    main()
