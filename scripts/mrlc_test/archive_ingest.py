"""Archive ingest: stream Nifty 100 1m CSVs from Downloads/archive.zip,
resample to 1h/4h/1d, store in data/mrlc_test/archive_candles.duckdb.

Filters: rows outside the cash session (09:15-15:30) are dropped (the archive
carries a stray after-hours row); zero-volume bars are kept (vendor artifact
handled downstream by the engine's median-volume logic).
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ARCHIVE = Path.home() / "Downloads" / "archive.zip"
OUT_DB = ROOT / "data" / "mrlc_test" / "archive_candles.duckdb"

SESSION_START = (9 * 60 + 15)  # 09:15
SESSION_END = 15 * 60 + 30      # 15:30


def resample(sym_df):
    ts = pd.to_datetime(sym_df["ts"])
    minutes = ts.dt.hour * 60 + ts.dt.minute
    ok = (minutes >= SESSION_START) & (minutes <= SESSION_END)
    df = sym_df[ok].copy()
    df["date"] = ts[ok].dt.normalize()
    df["h_bucket"] = (minutes[ok] - SESSION_START) // 60
    df["h4_bucket"] = (minutes[ok] - SESSION_START) // 240

    def build(keys):
        g = df.groupby(keys, sort=True).agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"),
            close=("close", "last"), volume=("volume", "sum")).reset_index()
        return g

    c1h = build(["date", "h_bucket"])
    c1h["ts"] = c1h["date"] + pd.to_timedelta(c1h["h_bucket"], unit="h") + pd.Timedelta(hours=9, minutes=15)
    c4h = build(["date", "h4_bucket"])
    c4h["ts"] = c4h["date"] + pd.to_timedelta(c4h["h4_bucket"] * 4, unit="h") + pd.Timedelta(hours=9, minutes=15)
    c1d = build(["date"])
    c1d["ts"] = c1d["date"]
    cols = ["ts", "open", "high", "low", "close", "volume"]
    return c1h[cols], c4h[cols], c1d[cols]


def main():
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = duckdb.connect(str(OUT_DB))
    for t in ("c1h", "c4h", "c1d"):
        con.execute(f"CREATE TABLE {t} (symbol VARCHAR, ts TIMESTAMP, open DOUBLE, "
                    "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")

    import zipfile
    total_rows = 0
    with zipfile.ZipFile(str(ARCHIVE)) as zf:
        names = sorted(n for n in zf.namelist() if n.startswith("NIFTY50/") and n.endswith(".csv"))
        print(f"{len(names)} files in archive")
        for i, name in enumerate(names):
            sym = name.split("/")[-1].replace(".csv", "")
            with zf.open(name) as fh:
                df = pd.read_csv(fh, parse_dates=["date"])
            df = df.rename(columns={"date": "ts"})
            df = df[["ts", "open", "high", "low", "close", "volume"]].dropna()
            total_rows += len(df)
            c1h, c4h, c1d = resample(df)
            con.register("c1h_data", c1h)
            con.register("c4h_data", c4h)
            con.register("c1d_data", c1d)
            con.execute("INSERT INTO c1h SELECT ?, ts, open, high, low, close, volume "
                        "FROM c1h_data", [sym])
            con.execute("INSERT INTO c4h SELECT ?, ts, open, high, low, close, volume "
                        "FROM c4h_data", [sym])
            con.execute("INSERT INTO c1d SELECT ?, ts, open, high, low, close, volume "
                        "FROM c1d_data", [sym])
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(names)} symbols ({total_rows:,} 1m rows)")
    for t in ("c1h", "c4h", "c1d"):
        n = con.execute(f"SELECT count(*), count(DISTINCT symbol), min(ts), max(ts) FROM {t}").fetchone()
        print(f"{t}: {n[0]:,} bars, {n[1]} symbols, {n[2]} -> {n[3]}")
    con.close()
    print(f"raw 1m rows streamed: {total_rows:,}")


if __name__ == "__main__":
    main()
