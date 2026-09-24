"""Nifty weekly ATM straddle: (a) seller return by entry point in the weekly cycle, held to cash
settlement; (b) overnight vs intraday decomposition of daily seller return; (c) weekend."""
import duckdb, pandas as pd, numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = str(ROOT / "data" / "scratch" / "options_seller_edge")
Path(SP).mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.execute(r"ATTACH 'data\market_data\options_bhavcopy.duckdb' AS i (READ_ONLY)")
con.execute(r"ATTACH 'data\market_data\futures_bhavcopy.duckdb' AS f (READ_ONLY)")
opt = con.execute("""select expiry_dt, strike, option_type, open, close, contracts, trade_date
    from i.option_bhavcopy where trade_date >= '2019-02-11' and expiry_dt - trade_date <= 8""").df()
fut = con.execute("""select trade_date, expiry_dt, close, settle from f.futures_bhavcopy
    where inst_type='FUTIDX' and underlying='NIFTY' and trade_date >= '2019-02-01'""").df()
days = sorted(con.execute("select distinct trade_date from i.option_bhavcopy where trade_date >= '2019-02-01'").df().trade_date)
di = {d: k for k, d in enumerate(days)}
front_fut = fut.sort_values("expiry_dt").groupby("trade_date").first()        # near-month future as forward proxy
settle_px = fut[fut.trade_date == fut.expiry_dt].groupby("expiry_dt").settle.first()  # monthly only
# weekly settlement = Nifty close on expiry day; near-month future close on that day is within basis of it,
# so use the expiring week's own ATM parity instead: S ≈ K + C − P at the expiry-day close for the most-traded strike
opt["expiry_dt"] = pd.to_datetime(opt.expiry_dt); opt["trade_date"] = pd.to_datetime(opt.trade_date)
ed = opt[opt.trade_date == opt.expiry_dt]
tr = ed[ed.contracts > 0].pivot_table(index=["expiry_dt", "strike"], columns="option_type", values=["close", "contracts"])
tr = tr.dropna()
tr["n"] = tr[("contracts", "CE")] + tr[("contracts", "PE")]
tr["S"] = tr.index.get_level_values("strike") + tr[("close", "CE")] - tr[("close", "PE")]
settle = tr.sort_values("n").groupby(level="expiry_dt").S.last()
wk_exp = sorted(set(opt.expiry_dt) & set(settle.index))
days = [pd.Timestamp(d) for d in days]; di = {d: k for k, d in enumerate(days)}
front_fut.index = pd.to_datetime(front_fut.index)

legs = opt[opt.contracts > 0].set_index(["trade_date", "expiry_dt", "strike", "option_type"])[["open", "close"]]
def straddle(d, e):
    try:
        f = front_fut.loc[d, "close"]
        x = legs.xs((d, e), level=("trade_date", "expiry_dt")).unstack("option_type").dropna()
    except KeyError:
        return None
    if x.empty: return None
    k = min(x.index, key=lambda s: abs(s - f))
    if abs(k / f - 1) > 0.02: return None
    r = x.loc[k]
    return k, r[("close", "CE")], r[("close", "PE")], r[("open", "CE")], r[("open", "PE")]

rows = []
for e in wk_exp:
    if e not in di: continue
    S = settle[e]
    for k in (4, 3, 2, 1):
        j = di[e] - k
        if j < 0: continue
        d = days[j]
        if (e - d).days > 8: continue
        s = straddle(d, e)
        if s is None: continue
        K, c, p = s[0], s[1], s[2]
        pay = abs(S - K)
        rows.append(dict(expiry=e, entry=f"close T-{k}", entry_date=d, prem=c + p, payoff=pay, ret=(c + p - pay) / (c + p)))
    s = straddle(days[di[e] - 1], e) if di[e] > 0 else None  # DTE-0: strike fixed at the PRIOR close (no look-ahead)
    if s is not None:
        try:
            r0 = legs.loc[(e, e, s[0])]
        except KeyError:
            r0 = None
        if r0 is not None and len(r0) == 2 and (r0.open > 0).all():
            K = s[0]; o = r0.open.sum()
            rows.append(dict(expiry=e, entry="open T-0", entry_date=e, prem=o, payoff=abs(S - K), ret=(o - abs(S - K)) / o))
cyc = pd.DataFrame(rows)

# overnight vs intraday: ATM chosen at prior close, same contract next day
import os
on = []
for j in (range(1, len(days)) if not os.environ.get('SKIP_ON') else []):
    d0, d1 = days[j - 1], days[j]
    for e in [x for x in wk_exp if x > d1 and (x - d1).days <= 7][:1]:
        s0 = straddle(d0, e)
        if s0 is None: continue
        K = s0[0]
        try:
            r1 = legs.loc[(d1, e, K)]
        except KeyError:
            continue
        if len(r1) < 2 or (r1.open <= 0).any(): continue
        c0 = s0[1] + s0[2]; o1 = r1.open.sum(); cl1 = r1.close.sum()
        on.append(dict(date=d1, expiry=e, dte=di[e] - j, weekend=(d1 - d0).days > 1,
                       overnight=(c0 - o1) / c0, intraday=(o1 - cl1) / c0, full=(c0 - cl1) / c0))
on = pd.DataFrame(on)
cyc.to_parquet(SP + r"\nifty_weekly_cycle.parquet"); on.to_parquet(SP + r"\nifty_overnight.parquet")

def report(lo, hi, label):
    print(f"\n######## {label}: {lo}..{hi}")
    c = cyc[(cyc.entry_date >= lo) & (cyc.entry_date <= hi)]
    g = c.groupby("entry").ret.agg(["count", "mean", "median", "std", lambda x: (x > 0).mean(), "min"])
    g["t"] = g["mean"] / g["std"] * np.sqrt(g["count"])
    print(g.round(4).to_string())
    if on.empty: return
    o = on[(on.date >= lo) & (on.date <= hi)]
    for nm, sub in (("all", o), ("weekday", o[~o.weekend]), ("weekend", o[o.weekend])):
        s = sub[["overnight", "intraday", "full"]]
        t = s.mean() / s.std() * np.sqrt(len(s))
        print(f"  {nm:8s} n={len(s):4d}  mean seller ret on prior-close premium: " +
              "  ".join(f"{k} {s[k].mean():+.2%} (t {t[k]:+.2f})" for k in s.columns))
    byd = o.groupby("dte")[["overnight", "intraday"]].agg(["mean", "count"])
    print(byd.round(4).to_string())

report(pd.Timestamp("2019-02-11"), pd.Timestamp("2022-12-31"), "DISCOVERY")
report(pd.Timestamp("2023-01-01"), pd.Timestamp("2026-07-17"), "LATER (MSRP-exposed index side)")
