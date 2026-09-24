"""Post-confirmation diagnostics (added after §5 was read): does the 10-before seller edge survive
(a) ex-ante liquidity screens and (b) an exit valuation that stale prints cannot flatter?
Reuses cycle_study.load()/net() unchanged. Exit-liquidity filters are deliberately NOT used: requiring
the T-1 legs to trade selects strikes the stock stayed near, i.e. conditions on the seller winning."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

sys.argv = [sys.argv[0], "2016-01-01", "2026-08-24", "m10"]
sys.path.insert(0, str(Path(__file__).parent))
import cycle_study as cs  # noqa: E402  (prints its own full-window tables first)

df = cs.stk[cs.stk.variant == "m10"].copy()
df["min_entry_n"] = df[["ce_n", "pe_n"]].min(axis=1)

# Conservative exit: never below a Black-76 straddle at the T-1 future with ONE session left, priced at the
# ENTRY implied vol (entry IV >= typical T-1 IV, so this overstates what the seller pays to close).
T = 1 / 252
sig = df.iv.clip(lower=0.05)
d1 = (np.log(df.fut_exit / df.strike) + 0.5 * sig ** 2 * T) / (sig * np.sqrt(T))
d2 = d1 - sig * np.sqrt(T)
bs = df.fut_exit * norm.cdf(d1) - df.strike * norm.cdf(d2) + df.strike * norm.cdf(-d2) - df.fut_exit * norm.cdf(-d1)
df_cons = df.copy()
df_cons["prem_exit"] = np.maximum(df.prem_exit, bs)
df_cons["ret"] = (df_cons.prem - df_cons.prem_exit) / df_cons.prem
print(f"\nconservative exit raised the exit premium on {(bs > df.prem_exit).mean():.1%} of trades; "
      f"median uplift where raised {((bs - df.prem_exit) / df.prem)[bs > df.prem_exit].median():.2%} of entry premium")

windows = {"discovery 2016-22": ("2016-01-01", "2022-12-31"), "confirm 2023-26": ("2023-01-01", "2026-08-24"),
           "post-reform 2024-11+": ("2024-11-20", "2026-08-24")}
cuts = {
    "all names": lambda d: d,
    "entry legs >= 100 contracts each": lambda d: d[d.min_entry_n >= 100],
    "entry legs >= 500 contracts each": lambda d: d[d.min_entry_n >= 500],
    "entry option turnover >= Rs 50 cr": lambda d: d[d.val_lakh >= 5000],
    "entry option turnover >= Rs 200 cr": lambda d: d[d.val_lakh >= 20000],
    "top-20% turnover rank (as in §2.3/§5)": lambda d: d[d.liq_rank >= 0.8],
}
rows = []
for exit_label, base in (("observed exit", df), ("conservative exit", df_cons)):
    for wl, (lo, hi) in windows.items():
        w = base[(base.entry_date >= lo) & (base.entry_date <= hi)]
        for cl, f in cuts.items():
            d = f(w)
            e2 = d.groupby("expiry_dt").apply(lambda g: cs.net(g, 0.02).mean(), include_groups=False)
            e4 = d.groupby("expiry_dt").apply(lambda g: cs.net(g, 0.04).mean(), include_groups=False)
            rows.append({"exit": exit_label, "window": wl, "cut": cl, "names/exp": d.groupby("expiry_dt").size().median(),
                         "exp": len(e2), "net@2%": e2.mean(), "t@2%": e2.mean() / e2.std() * np.sqrt(len(e2)),
                         "net@4%": e4.mean(), "t@4%": e4.mean() / e4.std() * np.sqrt(len(e4))})
print("\n\n=== LIQUIDITY / EXIT-VALUATION DIAGNOSTICS (10-before, net, per-expiry basket means) ===")
print(pd.DataFrame(rows).round(4).to_string(index=False))
