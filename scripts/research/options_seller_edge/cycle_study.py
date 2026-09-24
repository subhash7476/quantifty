"""Expiry-cycle seller study: short ATM straddle, entry k sessions before monthly expiry, exit T-1.
Usage: python cycle_study.py START END [variant_for_detail]"""
import sys, pandas as pd, numpy as np
from scipy import stats

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = str(ROOT / "data" / "scratch" / "options_seller_edge")
Path(SP).mkdir(parents=True, exist_ok=True)
start, end = pd.Timestamp(sys.argv[1]), pd.Timestamp(sys.argv[2])
detail = sys.argv[3] if len(sys.argv) > 3 else "m10"
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)

def load():
    df = pd.read_parquet(SP + r"\stock_straddles.parquet")
    df["entry_date"] = pd.to_datetime(df.entry_date)
    df = df[(df.entry_date >= start) & (df.entry_date <= end)]
    df = df[(df.ca_in_hold.fillna(0) == 0) & df.ce_exit.notna() & df.pe_exit.notna() & df.fut_exit.notna()
            & (df.n20 >= 15) & (df.n60 >= 40) & (df.rv20 > 0)].copy()
    df["prem"] = df.ce + df.pe
    df["prem_exit"] = df.ce_exit + df.pe_exit
    df["ret"] = (df.prem - df.prem_exit) / df.prem
    df["pnl_f"] = (df.prem - df.prem_exit) / df.fut_entry
    df["hold"] = df.sess_to_exp - 1
    df["iv"] = df.prem / df.fut_entry / (0.7979 * np.sqrt(df.sess_to_exp / 252))
    df["vrp60"] = np.log(df.iv / df.rv60)
    df["exit_traded"] = (df.ce_exit_n > 0) & (df.pe_exit_n > 0)
    df["pcp_err"] = ((df.ce - df.pe) - (df.fut_entry - df.strike)).abs() / df.prem
    stt = np.select([df.entry_date < "2023-04-01", df.entry_date < "2024-10-01"], [0.0005, 0.000625], 0.001)
    exch = np.where(df.entry_date < "2024-10-01", 0.00053, 0.000350) * 1.18
    df["fees"] = stt + exch * (1 + df.prem_exit / df.prem) + 0.00003 * df.prem_exit / df.prem + 0.003
    df["is_index"] = df.underlying == "NIFTY"
    df["liq_rank"] = df[~df.is_index].groupby(["variant", "expiry_dt"]).val_lakh.rank(pct=True)
    return df

def net(d, s):
    return d.ret - d.fees - s / 2 * (1 + d.prem_exit / d.prem)

def tstat(x):
    x = x.dropna()
    return pd.Series({"n": len(x), "mean": x.mean(), "sd": x.std(), "t": x.mean() / x.std() * np.sqrt(len(x)),
                      "worst": x.min(), "pct_pos": (x > 0).mean()})

df = load()
stk = df[~df.is_index]
print(f"window {start.date()}..{end.date()}  stock trades {len(stk)}  nifty trades {df.is_index.sum()}")

rows = []
for v, d in stk.groupby("variant"):
    e = d.groupby("expiry_dt")
    g = tstat(e.ret.mean()); n2 = tstat(e.apply(lambda x: net(x, .02).mean(), include_groups=False))
    nf = df[df.is_index & (df.variant == v)].set_index("expiry_dt").ret
    basket = e.ret.mean()
    diff = (basket - nf).dropna()
    rows.append({"variant": v, "hold_sess": d.hold.median(), "names/exp": e.size().median(),
                 "gross/cycle": g["mean"], "gross/sess": g["mean"] / d.hold.median(), "t_gross": g.t,
                 "net@2%": n2["mean"], "t_net@2%": n2.t, "worst_exp_net": n2.worst, "exp_pos": n2.pct_pos,
                 "pnl%F": e.pnl_f.mean().mean(), "trade_hit": (d.ret > 0).mean(),
                 "NIFTY_gross": nf.mean(), "NIFTY_t": tstat(nf).t, "stock-NIFTY": diff.mean(), "t_diff": tstat(diff).t})
print(pd.DataFrame(rows).set_index("variant").loc[["start", "m15", "m10", "m7", "m5", "m3"]].round(4).to_string())

d = stk[stk.variant == detail].copy()
print(f"\n--- robustness, variant {detail} (net @2% spread, per-expiry basket means) ---")
def line(label, x):
    s = tstat(x.groupby("expiry_dt").apply(lambda g: net(g, .02).mean(), include_groups=False))
    print(f"  {label:38s} trades {len(x):6d}  mean {s['mean']:+.2%}  t {s.t:+.2f}  worst exp {s.worst:+.2%}  exp>0 {s.pct_pos:.0%}")
line("all", d)
line("exit legs both traded", d[d.exit_traded])
line("entry PCP error < 10% of premium", d[d.pcp_err < 0.10])
line("liquid half (entry turnover)", d[d.liq_rank >= 0.5])
line("top-20% liquidity", d[d.liq_rank >= 0.8])
line("net @4% spread, top-20% liq  [see s]", d[d.liq_rank >= 0.8].assign(ret=lambda x: x.ret - 0.01 * (1 + x.prem_exit / x.prem)))
for lo, hi in ((-9, 0), (0, .25), (.25, 9)):
    line(f"vrp60 in [{lo},{hi})", d[(d.vrp60 >= lo) & (d.vrp60 < hi)])
be = (d.ret - d.fees).mean() / (0.5 * (1 + d.prem_exit / d.prem).mean())
print(f"  break-even relative spread (all trades): {be:.2%}")
ic = d.groupby("expiry_dt").apply(lambda g: stats.spearmanr(g.vrp60, g.ret).correlation, include_groups=False).dropna()
print(f"  rank IC vrp60 vs seller ret: mean {ic.mean():+.4f} sd {ic.std():.4f} t {ic.mean()/ic.std()*np.sqrt(len(ic)):+.2f} n {len(ic)}")

e = d.groupby("expiry_dt").apply(lambda g: pd.Series({"net2": net(g, .02).mean(), "pnl_f": g.pnl_f.mean(),
                                                     "fut_move": (g.fut_exit / g.fut_entry - 1).abs().median()}), include_groups=False)
eq = e.pnl_f.cumsum(); dd = (eq - eq.cummax()).min()
print(f"  per-cycle pnl %notional: mean {e.pnl_f.mean():+.3%} sd {e.pnl_f.std():.3%} -> ann Sharpe {e.pnl_f.mean()/e.pnl_f.std()*np.sqrt(12):.2f}; "
      f"skew {stats.skew(e.pnl_f):+.2f}; max DD {dd:+.2%} of notional (sum of cycles)")
print("  worst 6 expiries:"); print(e.sort_values("pnl_f").head(6).round(4).to_string())
yr = d.assign(y=d.entry_date.dt.year).groupby("y").apply(lambda g: pd.Series({"trades": len(g), "net@2%": net(g, .02).mean(), "pnl%F": g.pnl_f.mean()}), include_groups=False)
print(yr.round(4).T.to_string())
