"""LAG section 9 -- TRAIN read.

Evaluates the LAG signal on TRAIN window (2017-02-28 -> 2020-12-31):
  - Mean rank-IC, AC1-corrected t (structural bet: IC >= 0.04)
  - Net quintile spread under section 8 fees
  - IC SD band check [0.10, 0.18]
  - Neutralization survival (raw vs neut IC)
  - Not-subsumed-by-Trend diagnostic (residualize z_lag_neut on z_trend_neut)
  - Power projection (n* = 42, sealed window)

Gate-2 is dispositive on prediction 1 (positive-signed + significant) and
prediction 4 (net spread > 0), per LAG_PHASE0_PRE_REGISTRATION.md section 11.

Output: docs/reports/LAG_TRAIN_REPORT.md
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

SIG_DB = ROOT / "data" / "signal_engine" / "lag" / "signals.duckdb"
TREND_SIG_DB = ROOT / "data" / "signal_engine" / "trend" / "signals.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "LAG_TRAIN_REPORT.md"

TRAIN_LO = date(2017, 2, 28)
TRAIN_HI = date(2020, 12, 31)
HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)

MIN_NAMES = 5
QUINTILE = 0.20
KAPPA = 0.0005
CAP = 1e7
ALPHA = 0.05
POWER_HURDLE = 0.80
AC1_TRIGGER = 0.10
NW_LAG = 4
MONTHLY_PPY = 12
N_STAR = 42
IC_SD_LO = 0.10
IC_SD_HI = 0.18
STRUCTURAL_BET_IC = 0.04


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

        V -= fee + slip
        Vn = V * (1 + gross)
        nrets.append(Vn / V - 1.0)
        V = Vn
        prev_held = all_held
        turnovers.append((len(entering) + len(exiting)) / max(n_held, 1))

    npd = len(scored_by_date)
    if npd == 0:
        return 0.0, 0.0, 0.0, 0.0, np.array([]), np.array([])

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
        print("ERROR: signals DB not found. Run build_lag.py first.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_WRITE)")
    trend_available = TREND_SIG_DB.exists()
    if trend_available:
        con.execute(f"ATTACH '{TREND_SIG_DB}' AS trd (READ_ONLY)")
    con.execute("SET threads=2")

    commit = _git_commit()

    n_neut = con.execute("SELECT COUNT(*) FROM sig.signals WHERE z_lag_neut IS NOT NULL").fetchone()[0]
    print(f"Neutralized signals: {n_neut:,}")

    rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_lag_neut, s.fwd_ret_1m, s.sector, s.entity
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.z_lag_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
        ORDER BY s.formation_date, s.z_lag_neut
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
        present = [(r[2], r[3]) for r in flist if r[3] is not None]
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

    # Raw (pre-neutralization) IC for neutralization-survival check
    raw_ic_list = []
    for fdate in ic_dates:
        raws = con.execute(f"""
            SELECT z_lag, fwd_ret_1m FROM sig.signals
            WHERE formation_date = DATE '{fdate}' AND z_lag IS NOT NULL AND fwd_ret_1m IS NOT NULL
        """).fetchall()
        if len(raws) < 5:
            continue
        rho_r, _ = spearmanr([r[0] for r in raws], [r[1] for r in raws])
        raw_ic_list.append(float(rho_r))
    raw_ic = np.array(raw_ic_list) if raw_ic_list else np.array([0.0])
    mean_raw_ic = float(np.mean(raw_ic))
    same_sign = (mean_raw_ic > 0) == (mean_ic > 0)
    neut_mag_ratio = abs(mean_ic / mean_raw_ic) if mean_raw_ic != 0 else 1.0
    neut_survives = same_sign and neut_mag_ratio >= 0.60

    # Not-subsumed-by-Trend diagnostic (residualize z_lag_neut on z_trend_neut)
    resid_ic_list = []
    n_trend_join = 0
    if trend_available:
        for fdate in ic_dates:
            joined = con.execute(f"""
                SELECT l.z_lag_neut, t.z_trend_neut, l.fwd_ret_1m
                FROM sig.signals l
                JOIN trd.signals t
                  ON t.formation_date = l.formation_date AND t.underlying = l.underlying
                WHERE l.formation_date = DATE '{fdate}'
                  AND l.z_lag_neut IS NOT NULL AND t.z_trend_neut IS NOT NULL
                  AND l.fwd_ret_1m IS NOT NULL
            """).fetchall()
            if len(joined) < 10:
                continue
            n_trend_join += len(joined)
            zl = np.array([r[0] for r in joined], float)
            zt = np.array([r[1] for r in joined], float)
            fwd = np.array([r[2] for r in joined], float)
            X = np.column_stack([np.ones(len(zl)), zt])
            bh = np.linalg.lstsq(X, zl, rcond=None)[0]
            resid = zl - X @ bh
            rho_r, _ = spearmanr(resid, fwd)
            resid_ic_list.append(float(rho_r))
    mean_resid_ic = float(np.mean(resid_ic_list)) if resid_ic_list else float("nan")
    not_subsumed = (not math.isnan(mean_resid_ic)
                    and (mean_resid_ic > 0) == (mean_ic > 0)
                    and abs(mean_resid_ic) >= 0.60 * abs(mean_ic))

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
    sign_correct = mean_ic > 0
    sig_t = nw_t if nw_t is not None else tstat
    pred1_pass = sign_correct and sig_t > 1.96
    bet_clears = mean_ic >= STRUCTURAL_BET_IC

    # Report
    w = []
    W = w.append
    W("# LAG Sleeve — TRAIN Report\n")
    W(f"**Script-generated** — `scripts/signal_engine/lag/run_train.py`. "
      f"Code commit `{commit}`.\n")
    W("**Frozen protocol:** `LAG_PHASE0_PRE_REGISTRATION.md` §9 gate 2 "
      f"(declaration SHA `0092919c…`).\n")
    W("**Windows:** TRAIN 2017-02-28 → 2020-12-31. HOLDOUT (2021-01 → 2022-12) "
      "and SEALED (2023-01 → 2026-07) untouched.\n")

    W("## Substrate\n")
    W("| Quantity | Value |")
    W("|---|---|")
    W(f"| Formations (total in TRAIN window) | {len(formation_dates)} |")
    W(f"| Formations with >= {MIN_NAMES} scored names | {n_dates} |")
    W(f"| Mean names per formation | {float(np.mean([len(by_date[d]) for d in formation_dates])):.0f} |")
    W(f"| Neutralized signals in TRAIN | {n_neut:,} |")
    W("")

    W("## Rank-IC Results\n")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| Mean IC | {mean_ic:.6f} |")
    W(f"| SD(IC) | {sd_ic:.6f} |")
    W(f"| t-stat (simple) | {tstat:.4f} |")
    W(f"| p-value (one-sided) | {pval:.6e} |")
    W(f"| AC1 | {ac1:.4f} |")
    if nw_t is not None:
        W(f"| t-stat (NW SE, lag={NW_LAG}) | {nw_t:.4f} |")
    else:
        W(f"| NW t (\\|AC1\\| <= {AC1_TRIGGER}) | below trigger, not computed |")
    W(f"| First-half mean IC | {fh_ic:.6f} |")
    W(f"| Second-half mean IC | {sh_ic:.6f} |")
    W(f"| Sign matches prediction (positive) | {'PASS' if sign_correct else '**FAIL**'} |")
    W(f"| Structural bet (IC >= {STRUCTURAL_BET_IC}) | "
      f"{'**CLEARS**' if bet_clears else 'below bet — India delay not enlarged vs US'} |")
    W("")

    W("## IC SD Band Check\n")
    W("| Check | Band | Realized | Result |")
    W("|---|---|---|:--:|")
    W(f"| IC SD | [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {sd_ic:.4f} | "
      f"{'PASS' if sd_in_band else '**NOTE** (C2 wide-SD failure pattern)'} |")
    W("")

    W("## Quintile Spread (Net of Fees)\n")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| Gross annualized return (L-S) | {ann_gross:.4f} ({ann_gross*100:.2f}%) |")
    W(f"| Net annualized return (L-S) | {ann_net:.4f} ({ann_net*100:.2f}%) |")
    W(f"| Q1-Q5 gross spread (last formation) | {q1_q5_gross:.6f} |")
    W(f"| Fee+slippage drag (annualized) | {drag_bp:.1f} bp |")
    W(f"| Avg turnover per rebalance | {turnover:.4f} |")
    W("")

    W("## Neutralization & Trend-Subsumption\n")
    W("| Check | Value | Result |")
    W("|---|---|:--:|")
    W(f"| Raw IC (pre-neutralization) | {mean_raw_ic:+.6f} | — |")
    W(f"| Neutralized IC / raw IC (same sign, >= 0.60) | {neut_mag_ratio:.2f}, same_sign={same_sign} | "
      f"{'PASS' if neut_survives else '**FAIL**'} |")
    if trend_available:
        W(f"| IC after residualizing on Trend z_trend_neut | {mean_resid_ic:+.6f} | — |")
        W(f"| Not subsumed by Trend (>= 60% of raw, same sign) | "
          f"ratio={abs(mean_resid_ic)/abs(mean_ic) if mean_ic else float('nan'):.2f} | "
          f"{'PASS' if not_subsumed else '**FAIL** — momentum-in-disguise risk'} |")
        W(f"| (joined {n_trend_join:,} name-formation pairs with Trend) | | |")
    else:
        W("| Trend residualization | Trend signals DB not found | NOT TESTED |")
    W("")

    W("## Power Projection (n* = 42, sealed window)\n")
    W("| Method | Power |")
    W("|---|---|")
    W(f"| Noncentral-t (simple SD) | {power_full:.4f} |")
    W(f"| Noncentral-t (half-IC) | {power_half:.4f} |")
    if power_nw is not None:
        W(f"| Noncentral-t (NW SD) | {power_nw:.4f} |")
    W(f"| Hurdle | {POWER_HURDLE:.2f} |")
    W("")

    W("## Prediction Outcomes (pre-reg section 11)\n")
    W("| # | Prediction | Result | Detail |")
    W("|---|---|---|---|")
    p1 = "PASS" if pred1_pass else "**FAIL**"
    W(f"| 1 | LAG rank-IC positive-signed + significant | {p1} | "
      f"mean_ic={mean_ic:+.4f} (expected > 0). "
      f"{'AC1-corrected' if nw_t is not None else 'simple'} t: {sig_t:.4f}. "
      f"Structural bet IC >= {STRUCTURAL_BET_IC}: "
      f"{'YES' if bet_clears else 'NO'} |")
    W(f"| 2 | Diffusion mechanism (cross-autocorr exists) | "
      f"{'indirectly PASS' if pred1_pass else 'unconfirmed'} | "
      f"a positive significant LAG-IC is itself the demonstration that "
      f"laggards catch up to leaders; no separate stat computed |")
    if trend_available:
        p3 = "PASS" if not_subsumed else "**FAIL**"
        W(f"| 3 | Not subsumed by Trend (resid IC >= 60% raw) | {p3} | "
          f"resid_ic={mean_resid_ic:+.4f}, raw_ic={mean_ic:+.4f}, "
          f"ratio={abs(mean_resid_ic)/abs(mean_ic) if mean_ic else float('nan'):.2f} |")
    else:
        W(f"| 3 | Not subsumed by Trend | NOT TESTED | Trend signals DB unavailable |")
    p4 = "PASS" if ann_net > 0 else "**FAIL**"
    W(f"| 4 | Net quintile spread > 0 | {p4} | net spread={ann_net*100:.2f}% annualized |")
    p5 = "PASS" if sd_in_band else "**NOTE**"
    W(f"| 5 | IC SD in [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {p5} | SD={sd_ic:.4f} |")
    W("")

    W("## IC Series (all formations)\n")
    W("| Formation date | IC | Raw IC | Names |")
    W("|---|---|---|---:|")
    for i, d in enumerate(ic_dates):
        rv = raw_ic[i] if i < len(raw_ic) else float("nan")
        W(f"| {d} | {ic[i]:.6f} | {rv:.6f} | {len(by_date[d])} |")
    W("")

    # Gate-2: dispositive on predictions 1 and 4
    gate_pass = pred1_pass and (ann_net > 0)
    if gate_pass:
        W("## §9 Gate 2 — PASS\n")
        W("Dispositive predictions 1 (positive-signed significant IC) and 4 "
          "(net spread > 0) both hold. TRAIN authorization satisfied. ")
        if not bet_clears:
            W(f"\n**Caveat:** mean IC {mean_ic:+.4f} is below the structural-bet "
              f"target {STRUCTURAL_BET_IC} — the India-friction enlargement did not "
              f"materialize on TRAIN. The gate passed on significance + net spread, "
              f"but the central-case power projection (§7.1) assumed IC ~0.04 and "
              f"will need re-examining at the composite check (gate 4).")
        if trend_available and not not_subsumed:
            W("\n**Caveat:** prediction 3 (not subsumed by Trend) failed — LAG is "
              "partially momentum-in-disguise. Gate 2 still passes on 1 + 4, but "
              "LAG's composite contribution is reduced by its Trend correlation.")
    else:
        W("## §9 Gate 2 — FAIL\n")
        fails = []
        if not pred1_pass:
            fails.append("1 (positive-signed significant IC)")
        if not (ann_net > 0):
            fails.append("4 (net spread > 0)")
        W(f"Dispositive prediction(s) {', '.join(fails)} failed. "
          f"TRAIN authorization NOT satisfied.\n")
        if not pred1_pass:
            W("**Prediction 1 failure is dispositive:** sign or magnitude failure. "
              "LAG is not a viable sleeve.\n")
        if not (ann_net > 0):
            W("**Prediction 4 failure is dispositive:** net spread < 0.\n")
        W("Per §9: no successor auto-authorized; HOLDOUT and SEALED stay untouched.")

    report = "\n".join(w) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  Mean IC: {mean_ic:.6f} (t={tstat:.4f}, p={pval:.6e})")
    print(f"  AC1: {ac1:.4f}, SD(IC): {sd_ic:.4f}")
    print(f"  Net spread: {ann_net*100:.2f}%")
    print(f"  Power: {power_full:.4f} (hurdle {POWER_HURDLE:.2f})")
    print(f"  Structural bet IC>={STRUCTURAL_BET_IC}: {'YES' if bet_clears else 'NO'}")
    if trend_available and not math.isnan(mean_resid_ic):
        print(f"  Trend-residualized IC: {mean_resid_ic:+.6f}")
    print(f"  Gate 2: {'PASS' if gate_pass else 'FAIL'}")

    con.close()
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
