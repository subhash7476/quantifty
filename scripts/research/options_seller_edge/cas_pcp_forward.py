"""CAS auction window: put-call-parity implied spot vs the frozen underlying_ltp print."""
import duckdb, glob, pandas as pd, numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = str(ROOT / "data" / "scratch" / "options_seller_edge")
Path(SP).mkdir(parents=True, exist_ok=True)
out = []
for p in sorted(glob.glob(r"data\options\wall_chain_snapshots\2026-09-*.duckdb")):
    day = p[-17:-7]
    if day == "2026-09-11":
        continue
    c = duckdb.connect(p, read_only=True)
    df = c.execute("""
      with m as (
        select snapshot_timestamp ts, underlying_symbol sym, expiry_date, strike_price k, option_type ot, underlying_ltp u,
               case when best_bid>0 and best_ask>0 then (best_bid+best_ask)/2 else ltp end mid
        from option_chain_snapshot where snapshot_timestamp::time >= '14:30'
      ), w as (
        select ts, sym, expiry_date, k, any_value(u) u,
               max(case when ot='CE' then mid end) ce, max(case when ot='PE' then mid end) pe
        from m group by all
      ), r as (
        select *, row_number() over (partition by ts, sym order by abs(k-u)) rn from w where ce>0 and pe>0
      )
      select ts, sym, expiry_date, any_value(u) u, median(k + ce - pe) fwd from r where rn <= 5 group by all order by ts
    """).df()
    c.close()
    df["day"] = day
    out.append(df)
df = pd.concat(out)
df["t"] = df.ts.dt.strftime("%H:%M")
df["dte"] = (pd.to_datetime(df.expiry_date) - pd.to_datetime(df.day)).dt.days
# calibrate carry/basis on the last continuous 30 minutes (14:45-15:14)
cal = df[(df.t >= "14:45") & (df.t < "15:15")].groupby(["day", "sym"]).apply(lambda g: (g.fwd - g.u).median(), include_groups=False).rename("basis")
df = df.join(cal, on=["day", "sym"])
df["implied_spot"] = df.fwd - df.basis
df["gap_pts"] = df.implied_spot - df.u
df["gap_bp"] = df.gap_pts / df.u * 1e4

def bucket(t):
    for lo, hi, lab in (("14:45", "15:15", "14:45-15:14 (continuous)"), ("15:15", "15:20", "15:15-15:19"),
                        ("15:20", "15:25", "15:20-15:24"), ("15:25", "15:30", "15:25-15:29"),
                        ("15:30", "15:35", "15:30-15:34"), ("15:35", "15:41", "15:35-15:40")):
        if lo <= t < hi: return lab
df["bucket"] = df.t.map(bucket)
d = df.dropna(subset=["bucket"])
summ = d.groupby(["day", "sym", "bucket"]).agg(distinct_u=("u", "nunique"), implied_moves=("implied_spot", lambda x: x.max() - x.min()),
                                            abs_gap_bp_med=("gap_bp", lambda x: x.abs().median()), abs_gap_bp_max=("gap_bp", lambda x: x.abs().max()))
pd.set_option("display.width", 220)
print(summ.round(1).to_string())

# compare with official Nifty close
res = []
for day in sorted(df.day.unique()):
    try:
        c = duckdb.connect(fr"data\market_data\nse\candles\1d\{day}.duckdb", read_only=True)
        cl = c.execute("select close from candles where symbol='NSE_INDEX|Nifty 50'").fetchone()
        c.close()
    except Exception as e:
        cl = None
    g = df[(df.day == day) & (df.sym == "NSE_INDEX|Nifty 50")]
    row = {"day": day, "official_close": cl[0] if cl else None}
    for tt in ("15:14", "15:20", "15:25", "15:29", "15:32", "15:36"):
        x = g[g.t <= tt].tail(1)
        if len(x):
            row[f"ltp@{tt}"] = x.u.iloc[0]; row[f"impl@{tt}"] = round(x.implied_spot.iloc[0], 1)
    res.append(row)
print(pd.DataFrame(res).to_string())
df.to_parquet(SP + r"\cas_pcp.parquet")

