"""CSMP Phase-1 D-i (CI-method) coverage simulation — DEV-WINDOW ONLY.

Operationalizes the operator's pre-registered selection rule (§3.4): pick the CI
method whose empirical coverage at the sealed n (=42) is closest to nominal, judged
on COVERAGE, not narrowness. Population = the empirical distribution of the 131
dev-window monthly rank ICs (mean 0.046, SD 0.208); iid resampling is justified by
the near-zero serial dependence of that series (block-L12 CI is 1.011x the iid CI at
n=131). No sealed-window data is read (fence asserted). Deterministic (seed 20260711).

For each candidate CI method it reports, at n=42, over two populations
(null: mean 0; alt: mean = dev mean):
  - two-sided 95% coverage of the true mean            (target 0.950)
  - two-sided gate rejection  P(CI_lo > 0)             (null=Type-I target 0.025; alt=power)
  - one-sided gate rejection  P(lower95 > 0)           (null=Type-I target 0.050; alt=power)
"""
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
import sys

import duckdb
import numpy as np
from scipy.stats import spearmanr, t as tdist

sys.path.insert(0, r"F:\Nifty")
DEV_END = date(2022, 12, 31)
DB = Path(r"F:\Nifty\data\market_data\equity_bhavcopy.duckdb")
N_SEALED = 42
SEED = 20260711


def dev_ic_series():
    con = duckdb.connect(str(DB), read_only=True)
    grid = [r[0] for r in con.execute("""
      WITH m AS (SELECT trade_date, EXTRACT(YEAR FROM trade_date)::INT y,
                        EXTRACT(MONTH FROM trade_date)::INT mo
                 FROM trading_calendar WHERE n_symbols>=200 AND trade_date<=?)
      SELECT MAX(trade_date) FROM m GROUP BY y,mo ORDER BY 1""", [DEV_END]).fetchall()]
    memb = defaultdict(list)
    for rd, sym, ent in con.execute("""
      SELECT um.rebalance_date, um.symbol, e.entity
      FROM universe_membership um JOIN universe_eligibility e ON e.symbol=um.symbol
      WHERE um.rebalance_date<=? ORDER BY um.rebalance_date""", [DEV_END]).fetchall():
        memb[rd].append((sym, ent))
    rows = con.execute("""
      SELECT entity, trade_date, adj_close FROM (
        SELECT e.entity, a.trade_date, a.close adj_close, a.turnover, a.symbol,
          ROW_NUMBER() OVER (PARTITION BY e.entity,a.trade_date
                             ORDER BY a.turnover DESC NULLS LAST,a.symbol) rn
        FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol
        WHERE a.trade_date<=?) WHERE rn=1""", [DEV_END]).fetchall()
    con.close()
    px = {(e, d): float(c) for e, d, c in rows}
    assert max(d for (_, d) in px) <= DEV_END, "SEALED LEAK"
    gidx = {d: i for i, d in enumerate(grid)}
    scored = [d for d in grid if d in memb and gidx[d] + 1 < len(grid)
              and gidx[d] - 12 >= 0 and grid[gidx[d] + 1] <= DEV_END]
    ic = []
    for tt in scored:
        i = gidx[tt]; t12, t1, tp1 = grid[i - 12], grid[i - 1], grid[i + 1]
        pr = []
        for sym, ent in memb[tt]:
            p12, p1, pa, pb = (px.get((ent, t12)), px.get((ent, t1)),
                               px.get((ent, tt)), px.get((ent, tp1)))
            if p12 and p1 and pa and pb and p12 > 0 and pa > 0:
                pr.append((p1 / p12 - 1.0, pb / pa - 1.0))
        if len(pr) >= 5:
            ic.append(float(spearmanr([a for a, _ in pr], [b for _, b in pr])[0]))
    return np.array(ic)


def boot_iid(s, B, rng):
    n = len(s); return s[rng.integers(0, n, size=(B, n))].mean(1)

def boot_mb(s, B, rng, L):
    n = len(s); nb = math.ceil(n / L)
    st = rng.integers(0, n - L + 1, size=(B, nb))
    idx = st[:, :, None] + np.arange(L)[None, None, :]
    return s[idx].reshape(B, nb * L)[:, :n].mean(1)

def boot_stationary(s, B, rng, Lm):
    n = len(s); p = 1.0 / Lm
    out = np.empty((B, n), np.int64); out[:, 0] = rng.integers(0, n, size=B)
    for j in range(1, n):
        out[:, j] = np.where(rng.random(B) < p, rng.integers(0, n, size=B),
                             (out[:, j - 1] + 1) % n)
    return s[out].mean(1)


def method_bounds(s, B, rng):
    n = len(s); se = s.std(ddof=1) / math.sqrt(n); m = s.mean()
    out = {}
    out["Student_t"] = (m - tdist.ppf(.975, n - 1) * se, m + tdist.ppf(.975, n - 1) * se,
                        m - tdist.ppf(.95, n - 1) * se)
    for name, bm in (("iid_perc", boot_iid(s, B, rng)),
                     ("mb_L12", boot_mb(s, B, rng, 12)),
                     ("stationary_L3", boot_stationary(s, B, rng, 3))):
        out[name] = (np.percentile(bm, 2.5), np.percentile(bm, 97.5), np.percentile(bm, 5))
    return out


def run(dev, outer=5000, B=1500):
    rng = np.random.default_rng(SEED)
    centered = dev - dev.mean()
    methods = ["Student_t", "iid_perc", "mb_L12", "stationary_L3"]
    C = {m: defaultdict(int) for m in methods}
    for mu in (0.0, dev.mean()):
        pop = centered + mu; tag = "null" if mu == 0 else "alt"
        for _ in range(outer):
            s = pop[rng.integers(0, len(pop), size=N_SEALED)]
            for m, (lo, hi, l95) in method_bounds(s, B, rng).items():
                if lo <= mu <= hi:
                    C[m][tag + "_cov"] += 1
                if lo > 0:
                    C[m][tag + "_2s"] += 1
                if l95 > 0:
                    C[m][tag + "_1s"] += 1
    print(f"\n{'method':14}| 2s cover | 2s Type-I | 2s power | 1s Type-I | 1s power")
    print("-" * 74)
    for m in methods:
        print(f"{m:14}| {C[m]['null_cov']/outer:8.3f} | {C[m]['null_2s']/outer:9.3f} | "
              f"{C[m]['alt_2s']/outer:8.3f} | {C[m]['null_1s']/outer:9.3f} | {C[m]['alt_1s']/outer:7.3f}")
    print(f"{'NOMINAL':14}| {0.95:8.3f} | {0.025:9.3f} | {'—':>8} | {0.05:9.3f} | {'—':>7}")


if __name__ == "__main__":
    dev = dev_ic_series()
    print(f"dev IC: n={len(dev)} mean={dev.mean():.4f} SD={dev.std(ddof=1):.4f} "
          f"skew={((dev-dev.mean())**3).mean()/dev.std()**3:+.2f}  (sealed-fenced <= {DEV_END})")
    print(f"Selection rule: coverage closest to nominal at n={N_SEALED}; guardrail = coverage NOT narrowness.")
    run(dev)
