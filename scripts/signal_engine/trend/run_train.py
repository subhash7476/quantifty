"""Trend §9 — TRAIN read.

Evaluates the Trend signal on TRAIN window (2017-02-28 → 2021-12-31):
  - Mean rank-IC, AC1-corrected t
  - Quintile spread under §8 fees
  - IC SD band check
  - Power projection

Output: docs/reports/TREND_TRAIN_REPORT.md
"""
from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
from screening_harness import _one_sided_t, _ac1, _nw_se, _power
from core.execution.futures.futures_fees import futures_fees

SIG_DB = ROOT / "data" / "signal_engine" / "trend" / "signals.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TREND_TRAIN_REPORT.md"

TRAIN_LO = date(2017, 2, 28)
TRAIN_HI = date(2021, 12, 31)
HOLDOUT_LO = date(2022, 1, 31)
HOLDOUT_HI = date(2023, 12, 31)

MIN_NAMES = 5
QUINTILE = 0.20
KAPPA = 0.0005
CAP = 1e7
ALPHA = 0.05
POWER_HURDLE = 0.80
AC1_TRIGGER = 0.10
NW_LAG = 4
MONTHLY_PPY = 12
N_STAR = 31
IC_SD_LO = 0.10
IC_SD_HI = 0.18


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def _quintile_spread(scored_by_date, fee_map):
    prev_held = set()
    V = CAP
    grets = []
    nrets = []
    total_fee = 0.0
    turnovers = []

    for flist in scored_by_date:
        rows = sorted(flist, key=lambda r: r[2])
        n = len(rows)
        nq = max(1, round(QUINTILE * n))
        long_set = {r[1] for r in rows[:nq]}
        short_set = {r[1] for r in rows[-nq:]}
        all_held = long_set | short_set
        t = rows[0][0]

        long_ret = float(np.mean([r[3] for r in rows if r[1] in long_set and r[3] is not None])) if long_set else 0.0
        short_ret = float(np.mean([r[3] for r in rows if r[1] in short_set and r[3] is not None])) if short_set else 0.0
        gross = long_ret - short_ret
        grets.append(gross)

        n_held = len(all_held)
        entering = all_held - prev_held
        exiting = prev_held - all_held

        fee = 0.0
        slip = 0.0
        if n_held > 0:
            pos_value = V / n_held
            for u in entering:
                f = fee_map.get(t, {}).get(u, None)
                fee += f if f is not None else futures_fees(side="BUY", trade_value=pos_value, trade_date=t).total
                slip += KAPPA * pos_value
            for u in exiting:
                f = fee_map.get(t, {}).get(u, None)
                fee += f if f is not None else futures_fees(side="SELL", trade_value=pos_value, trade_date=t).total
                slip += KAPPA * pos_value

        total_fee += fee + slip
        V -= fee + slip
        Vn = V * (1 + gross)
        nret = Vn / V - 1.0
        nrets.append(nret)
        V = Vn
        prev_held = all_held
        turnovers.append((len(entering) + len(exiting)) / max(n_held, 1))

    npd = len(scored_by_date)
    if npd == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0, np.array([]), np.array([])

    ann_net = (V / CAP) ** (MONTHLY_PPY / npd) - 1
    ann_gross = float(np.prod([1 + g for g in grets]) ** (MONTHLY_PPY / npd) - 1)
    avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0
    drag_bp = (ann_gross - ann_net) * 10000

    last = sorted(scored_by_date[-1], key=lambda r: r[2])
    nq_last = max(1, round(QUINTILE * len(last)))
    q1 = float(np.mean([r[3] for r in last[:nq_last] if r[3] is not None]))
    q5 = float(np.mean([r[3] for r in last[-nq_last:] if r[3] is not None]))

    return ann_gross, ann_net, q1 - q5, drag_bp, avg_turnover, np.array(nrets), np.array(grets)


def main():
    if not SIG_DB.exists():
        print("ERROR: signals DB not found. Run build_trend.py first.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_WRITE)")
    con.execute("SET threads=2")

    commit = _git_commit()

    n_neut = con.execute("SELECT COUNT(*) FROM sig.signals WHERE z_trend_neut IS NOT NULL").fetchone()[0]
    print(f"Neutralized signals: {n_neut:,}")

    rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_trend_neut, s.fwd_ret_1m, s.sector, s.entity
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.z_trend_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
        ORDER BY s.formation_date, s.z_trend_neut
    """).fetchall()

    if not rows:
        print("ERROR: no TRAIN signals")
        return 1

    from collections import defaultdict
    by_date = defaultdict(list)
    for r in rows:
        by_date[r[0]].append(list(r))

    formation_dates = sorted(by_date.keys())
    print(f"TRAIN formations: {formation_dates[0]} -> {formation_dates[-1]} ({len(formation_dates)} total)")

    ic_list = []
    ic_dates = []
    scored_by_date = []

    for fdate in formation_dates:
        flist = by_date[fdate]
        s_all = [r[2] for r in flist]
        fwd_all = [r[3] for r in flist]
        present = [(s, f) for s, f in zip(s_all, fwd_all) if f is not None]
        if len(present) < MIN_NAMES:
            continue
        sp = [p[0] for p in present]
        fp = [p[1] for p in present]
        rho, _ = spearmanr(sp, fp)
        ic_list.append(float(rho))
        ic_dates.append(fdate)
        scored_by_date.append(flist)

    ic = np.array(ic_list)
    n_dates = len(ic)
    if n_dates < 2:
        print("ERROR: too few IC observations")
        return 1

    mean_ic, sd_ic, tstat, pval = _one_sided_t(ic)
    ac1 = _ac1(ic)
    nw_t = None
    sd_eff = sd_ic
    if abs(ac1) > AC1_TRIGGER:
        nw_se = _nw_se(ic, lag=NW_LAG)
        nw_t = mean_ic / nw_se if nw_se > 0 else 0.0
        sd_eff = nw_se * math.sqrt(n_dates)

    power_full, power_half = _power(mean_ic, sd_ic, N_STAR)
    power_nw = None
    if nw_t is not None:
        power_nw, _ = _power(mean_ic, sd_eff, N_STAR)

    half = n_dates // 2
    fh_ic = float(np.mean(ic[:half])) if half else float("nan")
    sh_ic = float(np.mean(ic[half:])) if n_dates - half else float("nan")

    # Raw (pre-neutralization) IC for prediction 2
    raw_ic_list = []
    for fdate in ic_dates:
        raws = con.execute(f"""
            SELECT z_trend, fwd_ret_1m FROM sig.signals
            WHERE formation_date = DATE '{fdate}' AND z_trend IS NOT NULL AND fwd_ret_1m IS NOT NULL
        """).fetchall()
        if len(raws) < 5:
            continue
        s_r = np.array([r[0] for r in raws], float)
        f_r = np.array([r[1] for r in raws], float)
        rho_r, _ = spearmanr(s_r, f_r)
        raw_ic_list.append(float(rho_r))
    raw_ic = np.array(raw_ic_list) if raw_ic_list else np.array([0.0])
    mean_raw_ic = float(np.mean(raw_ic))
    same_sign = (mean_raw_ic > 0) == (mean_ic > 0)
    neut_mag_ratio = abs(mean_ic / mean_raw_ic) if mean_raw_ic != 0 else 1.0
    pred2_pass = same_sign and neut_mag_ratio >= 0.60

    # Quintile spread with fees
    date_underlyings = defaultdict(set)
    for flist in scored_by_date:
        for r in flist:
            date_underlyings[r[0]].add(r[1])

    fee_map = defaultdict(dict)
    for fdate, underlyings in date_underlyings.items():
        for u in underlyings:
            pv = CAP / max(len(underlyings), 1)
            bf = futures_fees(side="BUY", trade_value=pv, trade_date=fdate).total
            sf = futures_fees(side="SELL", trade_value=pv, trade_date=fdate).total
            fee_map[fdate][u] = (bf + sf) / 2

    ann_gross, ann_net, q1_q5_gross, drag_bp, turnover, nrets, grets = _quintile_spread(scored_by_date, fee_map)

    sd_in_band = IC_SD_LO <= sd_ic <= IC_SD_HI
    sign_correct = mean_ic > 0  # Trend: long high trend → positive IC
    pred1_pass = sign_correct and (nw_t is not None and nw_t > 1.96 or (nw_t is None and tstat > 1.96))
    preds_ok = [pred1_pass, pred2_pass, ann_net > 0]

    # Report
    w = []
    W = w.append
    W("# Trend Sleeve — TRAIN Report\n")
    W(f"**Script-generated** — `scripts/signal_engine/trend/run_train.py`. "
      f"Code commit `{commit}`.\n")
    W("**Frozen protocol:** `TREND_PHASE0_PRE_REGISTRATION.md` §9 gate 2.\n")
    W("**Windows:** TRAIN 2017-02-28 → 2021-12-31. HOLDOUT and SEALED untouched.\n")

    W("## Substrate\n")
    W(f"| Quantity | Value |")
    W(f"|---|---|")
    W(f"| Formations (total in TRAIN window) | {len(formation_dates)} |")
    W(f"| Formations with >= {MIN_NAMES} scored names | {n_dates} |")
    W(f"| Mean names per formation | {float(np.mean([len(by_date[d]) for d in formation_dates])):.0f} |")
    W(f"| Neutralized signals in TRAIN | {n_neut:,} |")
    W("")

    W("## Rank-IC Results\n")
    W(f"| Metric | Value |")
    W(f"|---|---|")
    W(f"| Mean IC | {mean_ic:.6f} |")
    W(f"| SD(IC) | {sd_ic:.6f} |")
    W(f"| t-stat (simple) | {tstat:.4f} |")
    W(f"| p-value (one-sided) | {pval:.6e} |")
    W(f"| AC1 | {ac1:.4f} |")
    if nw_t is not None:
        W(f"| t-stat (NW SE, lag={NW_LAG}) | {nw_t:.4f} |")
    else:
        W(f"| NW t (|AC1| <= {AC1_TRIGGER}) | below trigger, not computed |")
    W(f"| First-half mean IC | {fh_ic:.6f} |")
    W(f"| Second-half mean IC | {sh_ic:.6f} |")
    W(f"| Sign matches prediction (positive) | {'PASS' if sign_correct else '**FAIL**'} |")
    W("")

    W("## IC SD Band Check\n")
    W(f"| Check | Band | Realized | Result |")
    W(f"|---|---|---|:--:|")
    W(f"| IC SD | [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {sd_ic:.4f} | "
      f"{'PASS' if sd_in_band else '**NOTE** (C2 wide-SD failure pattern)'} |")
    W("")

    W("## Quintile Spread (Net of Fees)\n")
    W(f"| Metric | Value |")
    W(f"|---|---|")
    W(f"| Gross annualized return (L-S) | {ann_gross:.4f} ({ann_gross*100:.2f}%) |")
    W(f"| Net annualized return (L-S) | {ann_net:.4f} ({ann_net*100:.2f}%) |")
    W(f"| Q1-Q5 gross spread (last formation) | {q1_q5_gross:.6f} |")
    W(f"| Fee+slippage drag (annualized) | {drag_bp:.1f} bp |")
    W(f"| Avg turnover per rebalance | {turnover:.4f} |")
    W("")

    W("## Power Projection (n* = 31, sealed window)\n")
    W(f"| Method | Power |")
    W(f"|---|---|")
    W(f"| Noncentral-t (simple SD) | {power_full:.4f} |")
    W(f"| Noncentral-t (half-IC) | {power_half:.4f} |")
    if power_nw is not None:
        W(f"| Noncentral-t (NW SD) | {power_nw:.4f} |")
    W(f"| Hurdle | {POWER_HURDLE:.2f} |")
    W("")

    W("## Prediction Outcomes\n")
    p1 = "PASS" if pred1_pass else "**FAIL**"
    W(f"| # | Prediction | Result | Detail |")
    W(f"|---|---|---|")
    W(f"| 1 | Trend rank-IC positive-signed | {p1} | "
      f"mean_ic={mean_ic:+.4f} (expected > 0). "
      f"AC1-corrected t: {nw_t if nw_t else tstat:.4f} |")
    p2 = "PASS" if pred2_pass else "**FAIL**"
    W(f"| 2 | IC survives neutralization | {p2} | "
      f"raw IC={mean_raw_ic:+.4f}, neut IC={mean_ic:+.4f}, "
      f"same_sign={same_sign}, mag_ratio={neut_mag_ratio:.2f} |")
    p3 = "PASS" if ann_net > 0 else "**FAIL**"
    W(f"| 3 | Net quintile spread > 0 | {p3} | "
      f"net spread={ann_net*100:.2f}% annualized |")
    p4 = "PASS" if sd_in_band else "**NOTE**"
    W(f"| 4 | IC SD in [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {p4} | "
      f"SD={sd_ic:.4f}{' (within band)' if sd_in_band else ' (below band, not a stop condition)'} |")
    W("")

    W("## IC Series (all formations)\n")
    W("| Formation date | IC | Raw IC | Names |")
    W("|---|---|---|---:|")
    for i, d in enumerate(ic_dates):
        rv = raw_ic[i] if i < len(raw_ic) else float("nan")
        W(f"| {d} | {ic[i]:.6f} | {rv:.6f} | {len(by_date[d])} |")
    W("")

    all_pass = all(preds_ok)
    if all_pass:
        W("## S9 Gate 2 — PASS\n")
        W("All predictions hold. TRAIN authorization satisfied. ")
    else:
        W("## S9 Gate 2 — FAIL\n")
        failures = [i+1 for i, p in enumerate(preds_ok) if not p]
        W(f"Predictions {failures} failed. TRAIN authorization NOT satisfied.\n")
        if not pred1_pass:
            W("**Prediction 1 failure is dispositive:** sign or magnitude failure.\n")
        if not (ann_net > 0):
            W("**Prediction 3 failure is dispositive:** net spread < 0.\n")

    report = "\n".join(w) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  Mean IC: {mean_ic:.6f} (t={tstat:.4f}, p={pval:.6e})")
    print(f"  AC1: {ac1:.4f}, SD(IC): {sd_ic:.4f}")
    print(f"  Net spread: {ann_net*100:.2f}%")
    print(f"  Power: {power_full:.4f} (hurdle {POWER_HURDLE:.2f})")
    print(f"  Gate 2: {'PASS' if all_pass else 'FAIL'}")

    con.close()
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
