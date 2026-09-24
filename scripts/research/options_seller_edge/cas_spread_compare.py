"""Stock-option bid/ask through the cash closing auction: compare near-month snapshots taken at
12:54 (baseline), 15:05 (pre-auction), 15:18 / 15:24 (auction order entry), 15:31 / 15:37 (post-fix).
Usage: python cas_spread_compare.py DIR  (DIR holds stock_opt_spreads*.parquet)"""
import sys, glob, os
import numpy as np, pandas as pd

d = sys.argv[1]
frames = {}
for p in sorted(glob.glob(os.path.join(d, "stock_opt_spreads*.parquet"))):
    tag = os.path.basename(p).replace("stock_opt_spreads", "").replace(".parquet", "").strip("_") or "1254"
    x = pd.read_parquet(p)
    x = x[(x.expiry == "2026-09-29") & x.fut_ltp.notna()].copy()
    x["two"] = (x.bid > 0) & (x.ask > 0)
    x["mid"] = (x.bid + x.ask) / 2
    x["rs"] = np.where(x.two, (x.ask - x.bid) / x.mid, np.nan)
    x["mny"] = np.where(x.opt_type == "CE", x.strike / x.fut_ltp - 1, 1 - x.strike / x.fut_ltp)
    x = x[x.mny.abs() <= 0.06]
    x["band"] = pd.cut(x.mny, [-0.061, -0.02, 0.02, 0.061], labels=["ITM2-6", "ATM±2", "OTM2-6"])
    frames[tag] = x

rows, paired = [], []
base = frames["1254"].set_index("instrument_key")
for tag, x in frames.items():
    row = {"snap": tag, "n": len(x), "two_sided": x.two.mean()}
    for b, g in x.groupby("band", observed=True):
        row[f"med {b}"] = g.rs.median()
        row[f"p90 {b}"] = g.rs.quantile(0.9)
    rows.append(row)
    if tag != "1254":
        j = base[["rs", "band"]].join(x.set_index("instrument_key")[["rs"]], rsuffix="_now", how="inner").dropna()
        atm = j[j.band == "ATM±2"]
        paired.append({"snap": tag, "pairs vs 12:54": len(j), "median spread ratio ATM": (atm.rs_now / atm.rs).median(),
                       "median ratio all": (j.rs_now / j.rs).median(), "share ATM wider": (atm.rs_now > atm.rs).mean()})
pd.set_option("display.width", 220)
print(pd.DataFrame(rows).round(4).to_string(index=False))
print(pd.DataFrame(paired).round(3).to_string(index=False))
fl = pd.DataFrame({t: s.groupby("underlying").fut_ltp.first() for t, s in frames.items()})
for a, b in (("1505", "1518"), ("1518", "1524"), ("1524", "1531"), ("1531", "1537")):
    if {a, b}.issubset(fl.columns):
        print(f"names whose near future LTP changed {a}->{b}: {(fl[a] != fl[b]).mean():.1%}")
