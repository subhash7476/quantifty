"""Seller economics + cross-sectional VRP rank IC for short ATM stock straddles.
Usage: python analyze_stock_straddles.py START END   (entry_date window, inclusive)"""
import sys, pandas as pd, numpy as np
from scipy import stats

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = str(ROOT / "data" / "scratch" / "options_seller_edge")
Path(SP).mkdir(parents=True, exist_ok=True)
start, end = pd.Timestamp(sys.argv[1]), pd.Timestamp(sys.argv[2])
df = pd.read_parquet(SP + r"\stock_straddles.parquet")
df["entry_date"] = pd.to_datetime(df.entry_date)
df = df[(df.entry_date >= start) & (df.entry_date <= end)]
n0 = len(df)
df = df[(df.ca_in_hold.fillna(0) == 0) & df.ce_exit.notna() & df.pe_exit.notna() & df.fut_exit.notna()
        & (df.n20 >= 15) & (df.n60 >= 40) & (df.rv20 > 0)].copy()
print(f"window {start.date()}..{end.date()}  rows {n0} -> clean {len(df)}")

df["prem"] = df.ce + df.pe
df["prem_exit"] = df.ce_exit + df.pe_exit
df["ret"] = (df.prem - df.prem_exit) / df.prem             # seller return on premium
df["pnl_f"] = (df.prem - df.prem_exit) / df.fut_entry      # seller P&L as % of notional
df["iv"] = df.prem / df.fut_entry / (0.7979 * np.sqrt(df.sess_to_exp / 252))
df["vrp20"] = np.log(df.iv / df.rv20)
df["vrp60"] = np.log(df.iv / df.rv60)
df["exit_stale"] = (df.ce_exit_n == 0) | (df.pe_exit_n == 0)
# fees as fraction of entry premium: STT sell (era), exch+GST both legs, stamp on buy, brokerage ~0.3%
stt = np.select([df.entry_date < "2023-04-01", df.entry_date < "2024-10-01"], [0.0005, 0.000625], 0.001)
exch = np.where(df.entry_date < "2024-10-01", 0.00053, 0.000350) * 1.18
df["fees"] = stt + exch * (1 + df.prem_exit / df.prem) + 0.00003 * df.prem_exit / df.prem + 0.003
# liquidity tier: cross-sectional rank of entry option turnover within (variant, expiry)
df["liq_rank"] = df.groupby(["variant", "expiry_dt"]).val_lakh.rank(pct=True)

def net(d, s):  # s = relative bid/ask spread paid half on entry, half on exit
    return d.ret - d.fees - s / 2 * (1 + d.prem_exit / d.prem)

def ts_stats(x):
    x = x.dropna(); return len(x), x.mean(), x.std(), x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
for v, d in df.groupby("variant"):
    print(f"\n===== variant {v}  n={len(d)}  expiries={d.expiry_dt.nunique()}  exit_stale={d.exit_stale.mean():.1%}")
    print(f"  median iv {d.iv.median():.3f}  rv20 {d.rv20.median():.3f}  iv>rv20 {(d.iv>d.rv20).mean():.1%}")
    by_e = d.groupby("expiry_dt")
    for s in (0.0, 0.01, 0.02, 0.04):
        n, m, sd, t = ts_stats(by_e.apply(lambda g: net(g, s).mean()))
        print(f"  ALL names, spread {s:.0%}: mean seller ret/expiry {m:+.2%} sd {sd:.2%} t {t:+.2f} (n={n}); pct pos trades {(net(d,s)>0).mean():.1%}")
    print(f"  gross pnl % notional per cycle: mean {d.pnl_f.mean():+.3%} median {d.pnl_f.median():+.3%}; worst 1% trade {d.pnl_f.quantile(.01):+.2%}")
    # cross-sectional IC
    for sig in ("vrp20", "vrp60", "iv"):
        ic = by_e.apply(lambda g: stats.spearmanr(g[sig], g.ret).correlation if len(g) > 20 else np.nan).dropna()
        print(f"  IC {sig:6s}: mean {ic.mean():+.4f} sd {ic.std():.4f} t {ic.mean()/ic.std()*np.sqrt(len(ic)):+.2f} n={len(ic)} pos {(ic>0).mean():.0%}")
    d = d.copy()
    d["q"] = d.groupby("expiry_dt").vrp20.transform(lambda x: pd.qcut(x.rank(method="first"), 5, labels=False) + 1)
    tab = []
    for q, g in d.groupby("q"):
        pe = g.groupby("expiry_dt")
        row = {"q": q, "n": len(g), "vrp20": g.vrp20.median(), "iv": g.iv.median(), "rv20": g.rv20.median(),
               "gross": pe.ret.mean().mean(), "pnl_f": pe.pnl_f.mean().mean(), "hit": (g.ret > 0).mean(),
               "p1_pnl_f": g.pnl_f.quantile(.01)}
        for s in (0.01, 0.02, 0.04):
            n_, m_, sd_, t_ = ts_stats(pe.apply(lambda x: net(x, s).mean()))
            row[f"net@{s:.0%}"] = m_; row[f"t@{s:.0%}"] = t_
        tab.append(row)
    print(pd.DataFrame(tab).round(4).to_string(index=False))
    top = d[d.q == 5]
    g5 = top.groupby("expiry_dt")
    # break-even spread for top quintile: mean(ret - fees) = s/2 * mean(1+exit/prem)
    be = (top.ret - top.fees).mean() / (0.5 * (1 + top.prem_exit / top.prem).mean())
    print(f"  Q5 break-even relative spread: {be:.2%}")
    liq = top[top.liq_rank >= 0.5]
    n, m, sd, t = ts_stats(liq.groupby("expiry_dt").apply(lambda x: net(x, 0.02).mean()))
    print(f"  Q5 & liquid half, net@2%: mean {m:+.2%} t {t:+.2f} n={n}  trades {len(liq)}")
    yr = top.assign(y=top.entry_date.dt.year).groupby("y").apply(lambda x: pd.Series({"n": len(x), "net@2%": net(x, .02).mean(), "pnl_f": x.pnl_f.mean()}))
    print(yr.round(4).T.to_string())
