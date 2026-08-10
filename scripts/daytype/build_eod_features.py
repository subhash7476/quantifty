import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.analytics.day_features import (
    compute_session_features, finalize_dataframe, block_a_gap_context,
)

CANDLE_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
OUT_DIR = ROOT / "data" / "features" / "day_type"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "NSE_INDEX|Nifty 50"


def load_session(d: date) -> pd.DataFrame | None:
    db_path = CANDLE_DIR / f"{d.isoformat()}.duckdb"
    if not db_path.exists():
        return None
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        df = con.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? ORDER BY timestamp",
            [SYMBOL],
        ).df()
        con.close()
        if df.empty:
            return None
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        hour_min = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
        df = df[(hour_min >= 555) & (hour_min <= 929)].reset_index(drop=True)
        return df if len(df) >= 5 else None
    except Exception as exc:
        print(f"  WARN {d}: {exc}")
        return None


def build():
    dates = sorted(
        date.fromisoformat(p.stem)
        for p in sorted(CANDLE_DIR.glob("*.duckdb"))
        if p.stem >= "2023-01-01"
    )
    print(f"Scanning {len(dates)} dates from {dates[0]} to {dates[-1]}")

    rows = {}
    skipped = 0
    for i, d in enumerate(dates):
        if i % 100 == 0:
            print(f"  {d} ... ({i}/{len(dates)})")
        df = load_session(d)
        if df is None:
            skipped += 1
            continue
        feats = compute_session_features(df)
        if feats:
            rows[d] = feats

    print(f"Computed features for {len(rows)} sessions, skipped {skipped}")

    if not rows:
        print("No sessions processed. Exiting.")
        return 1

    df_all = pd.DataFrame.from_dict(rows, orient="index")
    df_all.index.name = "date"
    df_all = df_all.sort_index()
    df_all.index = pd.to_datetime(df_all.index)

    # Block A: gap features (needs previous day's open/high/low/close)
    print("Computing Block A gap features...")
    a_feats = {}
    for i in range(len(df_all)):
        a_feats[df_all.index[i]] = block_a_gap_context(i, df_all)
    df_a = pd.DataFrame.from_dict(a_feats, orient="index")
    df_all = pd.concat([df_all, df_a], axis=1)

    print("Finalizing (rolling features, drop internals)...")
    df_final = finalize_dataframe(df_all)

    for year, grp in df_final.groupby(df_final.index.year):
        out_path = OUT_DIR / f"nifty_day_features_{year}.csv"
        grp.to_csv(out_path)
        print(f"  {out_path} ({len(grp)} rows, {grp.shape[1]} cols)")

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
