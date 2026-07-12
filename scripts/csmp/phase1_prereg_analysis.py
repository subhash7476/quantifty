"""CSMP Phase-1 pre-registration analysis (DEV-WINDOW ONLY, 2012-01 -> 2022-12).

Reproduces the load-bearing numbers the Phase-1 dossier cites:
  B1 - dev triage re-run under the §5.2 delisting convention (rule-1 last-price,
       rule-2 0% / -100% stress); confirms gate-(e) CONTINUE survives.
  B3 - slippage drag at kappa=5bps/side (traded notional = 2x the gate-(e) two_way).
  S2 - block-bootstrap (L=12) vs iid CI width on dev; sealed n=42 under-coverage sim.
  S6 - dev-window risk metrics (vol, Sharpe, max drawdown) for both arms.
  B2 - power of the §3.4 gate at n=42 (analytic + MC).

Sealed window (2023-01 -> 2026-06) is NEVER read: every query is fenced
MAX(trade_date) <= 2022-12-31. Deterministic (seed 20260711).
"""
import bisect
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import norm, spearmanr
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.execution.equity.delivery_fees import delivery_equity_fees  # noqa: E402

DEV_END = date(2022, 12, 31)
DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SEED = 20260711
CAP = 1e7
KAPPA = 0.0005  # 5 bps per traded side


def load():
    con = duckdb.connect(str(DB), read_only=True)
    grid = [r[0] for r in con.execute("""
      WITH m AS (SELECT trade_date, EXTRACT(YEAR FROM trade_date)::INT y,
                        EXTRACT(MONTH FROM trade_date)::INT mo
                 FROM trading_calendar WHERE n_symbols>=200 AND trade_date<=?)
      SELECT MAX(trade_date) FROM m GROUP BY y,mo ORDER BY 1""", [DEV_END]).fetchall()]
    memb = defaultdict(list)
    for rd, sym, rk, ent in con.execute("""
      SELECT um.rebalance_date, um.symbol, um.rank, e.entity
      FROM universe_membership um JOIN universe_eligibility e ON e.symbol=um.symbol
      WHERE um.rebalance_date<=? ORDER BY um.rebalance_date, um.rank""", [DEV_END]).fetchall():
        memb[rd].append((sym, rk, ent))
    rows = con.execute("""
      SELECT entity, trade_date, adj_close FROM (
        SELECT e.entity, a.trade_date, a.close adj_close, a.turnover, a.symbol,
          ROW_NUMBER() OVER (PARTITION BY e.entity,a.trade_date
                             ORDER BY a.turnover DESC NULLS LAST,a.symbol) rn
        FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol
        WHERE a.trade_date<=?) WHERE rn=1""", [DEV_END]).fetchall()
    con.close()
    px = {}
    ent_dates = defaultdict(list)
    for ent, d, cl in rows:
        px[(ent, d)] = float(cl)
        ent_dates[ent].append(d)
    for e in ent_dates:
        ent_dates[e].sort()
    assert max(d for (_, d) in px) <= DEV_END, "SEALED-WINDOW LEAK"
    print(f"Sealed fence OK: MAX(trade_date)={max(d for (_,d) in px)} <= {DEV_END}")
    return grid, memb, px, ent_dates


def block_ci(series, L=12, reps=20000, seed=SEED):
    s = np.asarray(series, float); n = len(s)
    rng = np.random.default_rng(seed)
    nb = math.ceil(n / L)
    starts = rng.integers(0, n - L + 1, size=(reps, nb))
    idx = starts[:, :, None] + np.arange(L)[None, None, :]
    m = s[idx].reshape(reps, nb * L)[:, :n].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def fwd(ent, t, tp1, px, ent_dates, rule2):
    pa = px.get((ent, t))
    if not pa or pa <= 0:
        return None, 'noentry'
    pb = px.get((ent, tp1))
    if pb and pb > 0:
        return pb / pa - 1.0, 'full'
    dates = ent_dates[ent]
    seg = dates[bisect.bisect_right(dates, t):bisect.bisect_right(dates, tp1)]
    if seg:
        return px[(ent, seg[-1])] / pa - 1.0, 'rule1'
    return rule2, 'rule2'


def simulate(permonth, pick, kappa=0.0):
    V = CAP; prev = None; grets = []; nrets = []
    for t, hold_pool in permonth:
        hold = pick(hold_pool)
        hp = [p for p in hold_pool if p[0] in hold]
        N = max(len(hp), 1)
        gross = float(np.mean([p[2] for p in hp])) if hp else 0.0
        cur = set(p[0] for p in hp)
        ent = cur - prev if prev else cur
        ex = prev - cur if prev else set()
        fee = sum(delivery_equity_fees(side="BUY", trade_value=V / N, trade_date=t).total for _ in ent) \
            + sum(delivery_equity_fees(side="SELL", trade_value=V / N, trade_date=t).total for _ in ex)
        slip = kappa * (len(ent) + len(ex)) * (V / N)
        Vn = (V - fee - slip) * (1 + gross)
        nrets.append(Vn / V - 1.0); grets.append(gross); V = Vn; prev = cur
    npd = len(permonth)
    ann_net = (V / CAP) ** (12 / npd) - 1
    ann_gross = np.prod([1 + g for g in grets]) ** (12 / npd) - 1
    return ann_net, ann_gross, np.array(nrets)


def risk(nr):
    vol = nr.std(ddof=1) * math.sqrt(12)
    sharpe = (nr.mean() * 12) / vol
    eq = np.cumprod(1 + nr); mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
    return vol, sharpe, mdd


def run_b1(grid, memb, px, ent_dates, rule2, label):
    gidx = {d: i for i, d in enumerate(grid)}
    scored = [d for d in grid if d in memb and gidx[d] + 1 < len(grid)
              and gidx[d] - 12 >= 0 and grid[gidx[d] + 1] <= DEV_END]
    ic = []; scored_pool = []; alluniv_pool = []
    r1 = defaultdict(int); r2 = defaultdict(int); excl = 0
    for t in scored:
        i = gidx[t]; t12, t1, tp1 = grid[i - 12], grid[i - 1], grid[i + 1]
        scored_names = []; all_names = []
        for sym, rk, ent in memb[t]:
            ret, rule = fwd(ent, t, tp1, px, ent_dates, rule2)
            if rule == 'rule1': r1[t.year] += 1
            elif rule == 'rule2': r2[t.year] += 1
            p12 = px.get((ent, t12)); p1 = px.get((ent, t1))
            has_score = p12 and p1 and p12 > 0
            if ret is not None:
                all_names.append((sym, None, ret))          # true all-200 universe
                if has_score:
                    scored_names.append((sym, p1 / p12 - 1.0, ret))
            if not has_score:
                excl += 1
        if len(scored_names) < 5:
            continue
        rho, _ = spearmanr([x[1] for x in scored_names], [x[2] for x in scored_names])
        ic.append(float(rho))
        scored_pool.append((t, scored_names))
        alluniv_pool.append((t, all_names))
    ic = np.array(ic)
    mean_ic = ic.mean(); sd = ic.std(ddof=1)
    tstat = mean_ic / (sd / math.sqrt(len(ic)))
    lo, hi = block_ci(ic)

    top40 = lambda pool: set(p[0] for p in sorted(pool, key=lambda x: x[1], reverse=True)[:40])
    allset = lambda pool: set(p[0] for p in pool)

    tq_net, tq_g, tq_nr = simulate(scored_pool, top40)
    fc_net, _, fc_nr = simulate(scored_pool, allset)          # formation-complete universe
    a2_net, _, a2_nr = simulate(alluniv_pool, allset)         # true all-200 universe
    tq_net_s, _, _ = simulate(scored_pool, top40, kappa=KAPPA)
    fc_net_s, _, _ = simulate(scored_pool, allset, kappa=KAPPA)

    print(f"\n===== {label} =====")
    print(f"IC n={len(ic)} mean={mean_ic:.4f} SD={sd:.4f} t={tstat:.2f} "
          f"hit={(ic > 0).mean():.4f} CI[{lo:.4f},{hi:.4f}]")
    print(f"affected: rule1={sum(r1.values())} {dict(sorted(r1.items()))} | "
          f"rule2={sum(r2.values())} {dict(sorted(r2.items()))} | form-excl={excl}")
    print(f"top40 net(fees)={tq_net:.4f} gross={tq_g:.4f}")
    print(f"universe FORMATION-COMPLETE net={fc_net:.4f} (stronger bar) | "
          f"universe TRUE-ALL-200 net={a2_net:.4f} (weaker bar)")
    print(f"spread vs formation-complete={tq_net - fc_net:.4f} | "
          f"spread vs all-200={tq_net - a2_net:.4f}")
    print(f"slippage(5bp): top40 drag={(tq_net - tq_net_s) * 1e4:.1f}bp/yr  "
          f"fc-univ drag={(fc_net - fc_net_s) * 1e4:.1f}bp/yr  "
          f"spread-delta={((tq_net - fc_net) - (tq_net_s - fc_net_s)) * 1e4:.1f}bp/yr")
    print(f"net spread (fees+slip, vs formation-complete)={tq_net_s - fc_net_s:.4f}")
    v1, s1, d1 = risk(tq_nr); v2, s2, d2 = risk(fc_nr)
    print(f"RISK top40: vol={v1:.4f} sharpe={s1:.2f} maxDD={d1:.4f} | "
          f"univ(fc): vol={v2:.4f} sharpe={s2:.2f} maxDD={d2:.4f}")
    verdict = "CONTINUE" if (mean_ic > 0.02 and lo > 0 and (tq_net - fc_net) > 0) else "STOP"
    print(f"gate-(e) STOP-RULE (mean_IC>0.02 & CI_lo>0 & spread>0, stronger baseline): {verdict}")
    return ic, sd


def s2_ci(ic, sd):
    n = len(ic); se = sd / math.sqrt(n)
    iid = (ic.mean() - 1.96 * se, ic.mean() + 1.96 * se)
    blk = block_ci(ic)
    print(f"\n===== S2: dev CI (n={n}) =====")
    print(f"iid 95% width={iid[1] - iid[0]:.4f}  block-L12 width={blk[1] - blk[0]:.4f}  "
          f"ratio={(blk[1] - blk[0]) / (iid[1] - iid[0]):.3f}")
    # sealed n=42 under-coverage of the moving-block percentile CI
    def mbb(s, rng, L=12, reps=1500):
        m = len(s); nb = math.ceil(m / L)
        st = rng.integers(0, m - L + 1, size=(reps, nb))
        idx = st[:, :, None] + np.arange(L)[None, None, :]
        mm = s[idx].reshape(reps, nb * L)[:, :m].mean(axis=1)
        return np.percentile(mm, 2.5)
    rng = np.random.default_rng(11)
    for mu in (0.0, sd and ic.mean()):
        p = sum(1 for _ in range(4000)
                if (lambda s: s.mean() > 0 and mbb(s, rng) > 0)(rng.normal(mu, sd, 42)))
        tag = "type-I (mu=0)" if mu == 0.0 else f"power (mu={mu:.4f})"
        print(f"  sealed n=42 block-L12 {tag}: {p / 4000:.3f}")


def b2_power(sd, dev_ic):
    print(f"\n===== B2: power of §3.4 gate (SD={sd:.4f}) =====")
    for n in (41, 42):
        se = sd / math.sqrt(n)
        print(f"  n={n}: SE={se:.4f} two-sided thr(1.96SE)={1.96 * se:.4f} "
              f"one-sided thr(1.645SE)={1.645 * se:.4f}")

    def power(mu, n, one=False):
        se = sd / math.sqrt(n); z = 1.645 if one else 1.96
        return 1 - norm.cdf((z * se - mu) / se)
    print("  power @ true IC (n=42):")
    for mu in (0.02, 0.03, dev_ic, 0.06, 0.064, 0.08, 0.10):
        print(f"    IC={mu:.4f}: two-sided={power(mu, 42):.3f} one-sided={power(mu, 42, True):.3f}")

    def months(mu, tgt, one=False):
        z = 1.645 if one else 1.96
        return ((z - norm.ppf(1 - tgt)) * sd / mu) ** 2
    print(f"  months for power @ true IC={dev_ic:.4f}: "
          f"two-sided 50%={months(dev_ic, .5):.0f} 80%={months(dev_ic, .8):.0f} | "
          f"one-sided 50%={months(dev_ic, .5, True):.0f} 80%={months(dev_ic, .8, True):.0f}")


def main():
    grid, memb, px, ent_dates = load()
    ic, sd = run_b1(grid, memb, px, ent_dates, 0.0, "B1: §5.2 (rule2=0%, liquidated at entry close)")
    run_b1(grid, memb, px, ent_dates, -1.0, "B1 STRESS (S7): rule2=-100%")
    s2_ci(ic, sd)
    b2_power(sd, ic.mean())


if __name__ == "__main__":
    main()
