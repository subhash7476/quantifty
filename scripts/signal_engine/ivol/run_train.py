"""IVOL section 9 -- TRAIN read.

Evaluates the IVOL signal on TRAIN window (2017-02-28 -> 2020-12-31):
  - Mean rank-IC, AC1-corrected t -- SIGN IS NEGATIVE (high vol -> low return)
  - Structural bet: |IC| >= 0.05 (India-retail amplification)
  - Net quintile spread under section 8 fees (long low-vol, short high-vol)
  - IC SD band check [0.10, 0.18]
  - Neutralization survival (raw vs neut IC)
  - Not-subsumed-by-Carry diagnostic (residualize z_ivol_neut on z_carry_neut)
  - Power projection (n* = 42, sealed window)

Gate-2 is dispositive on prediction 1 (negative-signed + significant) and
prediction 3 (net spread > 0), per IVOL_PHASE0_PRE_REGISTRATION.md section 11.

Output: docs/reports/IVOL_TRAIN_REPORT.md
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
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

SIG_DB = ROOT / "data" / "signal_engine" / "ivol" / "signals.duckdb"
CARRY_SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "IVOL_TRAIN_REPORT.md"

TRAIN_LO = date(2017, 2, 28)
TRAIN_HI = date(2020, 12, 31)
HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)

MIN_NAMES = 5
QUINTILE = 0.20
KAPPA = 0.0005
CAP = 1e7
POWER_HURDLE = 0.80
AC1_TRIGGER = 0.10
NW_LAG = 4
MONTHLY_PPY = 12
N_STAR = 42
IC_SD_LO = 0.10
IC_SD_HI = 0.18
STRUCTURAL_BET_IC = 0.05
TCRIT = 1.96  # one-sided threshold (engine convention, matches Trend/LAG)


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
        long_set = {r[1] for r in rows[:nq]}    # low z_ivol -> low vol -> LONG
        short_set = {r[1] for r in rows[-nq:]}  # high z_ivol -> high vol -> SHORT
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
        print("ERROR: signals DB not found. Run build_ivol.py first.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_WRITE)")
    carry_available = CARRY_SIG_DB.exists()
    if carry_available:
        con.execute(f"ATTACH '{CARRY_SIG_DB}' AS cr (READ_ONLY)")
    con.execute("SET threads=2")

    commit = _git_commit()

    n_neut = con.execute("SELECT COUNT(*) FROM sig.signals WHERE z_ivol_neut IS NOT NULL").fetchone()[0]
    print(f"Neutralized signals: {n_neut:,}")

    rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_ivol_neut, s.fwd_ret_1m, s.sector, s.entity
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.z_ivol_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
        ORDER BY s.formation_date, s.z_ivol_neut
    """).fetchall()

    if not rows:
        print("ERROR: no TRAIN signals")
        return 1

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

    mean_ic, sd_ic, tstat, pval_pos = _one_sided_t(ic)
    pval_neg = 1.0 - pval_pos  # negative-direction one-sided p (H1: mean < 0)
    ac1 = _ac1(ic)
    nw_t = None
    sd_eff = sd_ic
    if abs(ac1) > AC1_TRIGGER:
        nw_se = _nw_se(ic, lag=NW_LAG)
        nw_t = mean_ic / nw_se if nw_se > 0 else 0.0
        sd_eff = nw_se * math.sqrt(n_dates)

    # IVOL sign is negative: power is about detecting |IC|, so pass abs(mean_ic).
    power_full, power_half = _power(abs(mean_ic), sd_ic, N_STAR)
    power_nw = None
    if nw_t is not None:
        power_nw, _ = _power(abs(mean_ic), sd_eff, N_STAR)

    half = n_dates // 2
    fh_ic = float(np.mean(ic[:half])) if half else float("nan")
    sh_ic = float(np.mean(ic[half:])) if n_dates - half else float("nan")

    # Raw (pre-neutralization) IC
    raw_ic_list = []
    for fdate in ic_dates:
        raws = con.execute(f"""
            SELECT z_ivol, fwd_ret_1m FROM sig.signals
            WHERE formation_date = DATE '{fdate}' AND z_ivol IS NOT NULL AND fwd_ret_1m IS NOT NULL
        """).fetchall()
        if len(raws) < 5:
            continue
        rho_r, _ = spearmanr([r[0] for r in raws], [r[1] for r in raws])
        raw_ic_list.append(float(rho_r))
    raw_ic = np.array(raw_ic_list) if raw_ic_list else np.array([0.0])
    mean_raw_ic = float(np.mean(raw_ic))
    same_sign = (mean_raw_ic < 0) == (mean_ic < 0)
    neut_mag_ratio = abs(mean_ic / mean_raw_ic) if mean_raw_ic != 0 else 1.0
    neut_survives = same_sign and neut_mag_ratio >= 0.60

    # Not-subsumed-by-Carry diagnostic (residualize z_ivol_neut on z_carry_neut)
    resid_ic_list = []
    n_carry_join = 0
    if carry_available:
        for fdate in ic_dates:
            joined = con.execute(f"""
                SELECT i.z_ivol_neut, c.z_carry_neut, i.fwd_ret_1m
                FROM sig.signals i
                JOIN cr.signals c
                  ON c.formation_date = i.formation_date AND c.underlying = i.underlying
                WHERE i.formation_date = DATE '{fdate}'
                  AND i.z_ivol_neut IS NOT NULL AND c.z_carry_neut IS NOT NULL
                  AND i.fwd_ret_1m IS NOT NULL
            """).fetchall()
            if len(joined) < 10:
                continue
            n_carry_join += len(joined)
            zi = np.array([r[0] for r in joined], float)
            zc = np.array([r[1] for r in joined], float)
            fwd = np.array([r[2] for r in joined], float)
            X = np.column_stack([np.ones(len(zi)), zc])
            bh = np.linalg.lstsq(X, zi, rcond=None)[0]
            resid = zi - X @ bh
            rho_r, _ = spearmanr(resid, fwd)
            resid_ic_list.append(float(rho_r))
    mean_resid_ic = float(np.mean(resid_ic_list)) if resid_ic_list else float("nan")
    not_subsumed = (not math.isnan(mean_resid_ic)
                    and (mean_resid_ic < 0) == (mean_ic < 0)
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
    sign_correct = mean_ic < 0  # IVOL: negative predicted
    sig_t = nw_t if nw_t is not None else tstat
    pred1_pass = sign_correct and sig_t < -TCRIT
    bet_clears = abs(mean_ic) >= STRUCTURAL_BET_IC

    # Report
    w = []
    W = w.append
    W("# IVOL Sleeve — TRAIN Report\n")
    W(f"**Script-generated** — `scripts/signal_engine/ivol/run_train.py`. "
      f"Code commit `{commit}`.\n")
    W("**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 2 "
      f"(declaration SHA `d7ebcbcc…`).\n")
    W("**Windows:** TRAIN 2017-02-28 → 2020-12-31. HOLDOUT (2021-01 → 2022-12) "
      "and SEALED (2023-01 → 2026-07) untouched.\n")
    W("**Sign:** NEGATIVE (high idiosyncratic vol → low forward return). "
      "Book longs low-z_ivol (low vol), shorts high-z_ivol (high vol).\n")

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
    W(f"| p-value (one-sided, negative direction) | {pval_neg:.6e} |")
    W(f"| AC1 | {ac1:.4f} |")
    if nw_t is not None:
        W(f"| t-stat (NW SE, lag={NW_LAG}) | {nw_t:.4f} |")
    else:
        W(f"| NW t (\\|AC1\\| <= {AC1_TRIGGER}) | below trigger, not computed |")
    W(f"| First-half mean IC | {fh_ic:.6f} |")
    W(f"| Second-half mean IC | {sh_ic:.6f} |")
    W(f"| Sign matches prediction (negative) | {'PASS' if sign_correct else '**FAIL**'} |")
    W(f"| Structural bet (\\|IC\\| >= {STRUCTURAL_BET_IC}) | "
      f"{'**CLEARS**' if bet_clears else 'below bet — India-retail amplification not realized'} |")
    W("")

    W("## IC SD Band Check\n")
    W("| Check | Band | Realized | Result |")
    W("|---|---|---|:--:|")
    W(f"| IC SD | [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {sd_ic:.4f} | "
      f"{'PASS' if sd_in_band else '**NOTE** (C2 wide-SD failure pattern)'} |")
    W("")

    W("## Quintile Spread (Net of Fees — long low-vol / short high-vol)\n")
    W("| Metric | Value |")
    W("|---|---|")
    W(f"| Gross annualized return (L-S) | {ann_gross:.4f} ({ann_gross*100:.2f}%) |")
    W(f"| Net annualized return (L-S) | {ann_net:.4f} ({ann_net*100:.2f}%) |")
    W(f"| Q1-Q5 gross spread (last formation) | {q1_q5_gross:.6f} |")
    W(f"| Fee+slippage drag (annualized) | {drag_bp:.1f} bp |")
    W(f"| Avg turnover per rebalance | {turnover:.4f} |")
    W("")

    W("## Neutralization & Carry-Subsumption\n")
    W("| Check | Value | Result |")
    W("|---|---|:--:|")
    W(f"| Raw IC (pre-neutralization) | {mean_raw_ic:+.6f} | — |")
    W(f"| Neutralized IC / raw IC (same sign, >= 0.60) | {neut_mag_ratio:.2f}, same_sign={same_sign} | "
      f"{'PASS' if neut_survives else '**FAIL**'} |")
    if carry_available:
        ratio = abs(mean_resid_ic) / abs(mean_ic) if mean_ic else float("nan")
        W(f"| IC after residualizing on Carry z_carry_neut | {mean_resid_ic:+.6f} | — |")
        W(f"| Not subsumed by Carry (>= 60% of raw, same sign) | ratio={ratio:.2f} | "
          f"{'PASS' if not_subsumed else '**FAIL** — redundant with Carry'} |")
        W(f"| (joined {n_carry_join:,} name-formation pairs with Carry) | | |")
    else:
        W("| Carry residualization | Carry signals DB not found | NOT TESTED |")
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
    W(f"| 1 | IVOL rank-IC negative-signed + significant | {p1} | "
      f"mean_ic={mean_ic:+.4f} (expected < 0). "
      f"{'AC1-corrected' if nw_t is not None else 'simple'} t: {sig_t:.4f} "
      f"(threshold < -{TCRIT}). Structural bet \\|IC\\| >= {STRUCTURAL_BET_IC}: "
      f"{'YES' if bet_clears else 'NO'} |")
    if carry_available:
        p2 = "PASS" if not_subsumed else "**FAIL**"
        ratio = abs(mean_resid_ic) / abs(mean_ic) if mean_ic else float("nan")
        W(f"| 2 | Not subsumed by Carry (resid IC >= 60% raw) | {p2} | "
          f"resid_ic={mean_resid_ic:+.4f}, raw_ic={mean_ic:+.4f}, ratio={ratio:.2f} |")
    else:
        W(f"| 2 | Not subsumed by Carry | NOT TESTED | Carry signals DB unavailable |")
    p3 = "PASS" if ann_net > 0 else "**FAIL**"
    W(f"| 3 | Net quintile spread > 0 (long low-vol) | {p3} | net spread={ann_net*100:.2f}% annualized |")
    p4 = "PASS" if sd_in_band else "**NOTE**"
    W(f"| 4 | IC SD in [{IC_SD_LO:.2f}, {IC_SD_HI:.2f}] | {p4} | SD={sd_ic:.4f} |")
    W("")

    W("## IC Series (all formations)\n")
    W("| Formation date | IC | Raw IC | Names |")
    W("|---|---|---|---:|")
    for i, d in enumerate(ic_dates):
        rv = raw_ic[i] if i < len(raw_ic) else float("nan")
        W(f"| {d} | {ic[i]:.6f} | {rv:.6f} | {len(by_date[d])} |")
    W("")

    # Gate-2: dispositive on predictions 1 and 3
    gate_pass = pred1_pass and (ann_net > 0)
    if gate_pass:
        W("## §9 Gate 2 — PASS\n")
        W("Dispositive predictions 1 (negative-signed significant IC) and 3 "
          "(net spread > 0) both hold. TRAIN authorization satisfied. ")
        if not bet_clears:
            W(f"\n**Caveat:** \\|IC\\| {abs(mean_ic):.4f} is below the structural-bet "
              f"target {STRUCTURAL_BET_IC} — the India-retail amplification did not fully "
              f"materialize. The gate passed on significance + net, but the composite-power "
              f"projection (gate 4) should use the realized IC, not the declared central.")
        if carry_available and not not_subsumed:
            W("\n**Caveat:** prediction 2 (not subsumed by Carry) failed — IVOL is "
              "partially redundant with Carry. Gate 2 still passes on 1 + 3, but IVOL's "
              "composite breadth contribution is reduced by the Carry correlation.")
    else:
        W("## §9 Gate 2 — FAIL\n")
        fails = []
        if not pred1_pass:
            fails.append("1 (negative-signed significant IC)")
        if not (ann_net > 0):
            fails.append("3 (net spread > 0)")
        W(f"Dispositive prediction(s) {', '.join(fails)} failed. "
          f"TRAIN authorization NOT satisfied.\n")
        if not pred1_pass:
            if not sign_correct:
                W("**Prediction 1 failure is dispositive:** sign is wrong (predicted "
                  "negative). The IVOL anomaly is falsified on this construction — LAG is "
                  "not a viable sleeve.\n")
            else:
                W("**Prediction 1 failure is dispositive:** correct sign but not "
                  "significant. The signal exists in the predicted direction but is "
                  "indistinguishable from noise at this sample size.\n")
        if not (ann_net > 0):
            W("**Prediction 3 failure is dispositive:** net spread < 0.\n")
        W("Per §9: no successor auto-authorized; HOLDOUT and SEALED stay untouched.")

    report = "\n".join(w) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  Mean IC: {mean_ic:.6f} (t={tstat:.4f}, neg-p={pval_neg:.6e})")
    print(f"  AC1: {ac1:.4f}, SD(IC): {sd_ic:.4f}")
    print(f"  Net spread: {ann_net*100:.2f}%")
    print(f"  Power: {power_full:.4f} (hurdle {POWER_HURDLE:.2f})")
    print(f"  Structural bet |IC|>={STRUCTURAL_BET_IC}: {'YES' if bet_clears else 'NO'}")
    if carry_available and not math.isnan(mean_resid_ic):
        print(f"  Carry-residualized IC: {mean_resid_ic:+.6f}")
    print(f"  Gate 2: {'PASS' if gate_pass else 'FAIL'}")

    con.close()
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
