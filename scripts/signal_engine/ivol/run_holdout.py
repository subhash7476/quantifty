"""IVOL section 9 -- HOLDOUT read (gate 3).

Evaluates the SAME frozen signal (z_ivol_neut, built once by build_ivol.py) on the
HOLDOUT window (2021-01-31 -> 2022-12-31). Gate-3 criterion per the pre-reg: the
negative sign and positive net spread persist from TRAIN. No parameter is touched
between TRAIN and HOLDOUT -- the build and harness are frozen.

For self-verification, TRAIN values are re-derived in-script and must match the
frozen IVOL_TRAIN_REPORT.md; a mismatch is flagged.

Output: docs/reports/IVOL_HOLDOUT_REPORT.md
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
EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "IVOL_HOLDOUT_REPORT.md"

TRAIN_LO = date(2017, 2, 28)
TRAIN_HI = date(2020, 12, 31)
HOLDOUT_LO = date(2021, 1, 31)
HOLDOUT_HI = date(2022, 12, 31)

# Frozen TRAIN reference values (from IVOL_TRAIN_REPORT.md, commit 15ed26c) for the
# self-check that the re-derived TRAIN figures match.
TRAIN_REF_IC = -0.054596
TRAIN_REF_NET = 0.0596

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
SELFCHECK_TOL = 1e-3  # TRAIN_REF values are display-truncated (4-6 decimals); 1e-3 catches gross errors, not float noise


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
        V = Vn
        prev_held = all_held
        turnovers.append((len(entering) + len(exiting)) / max(n_held, 1))
    npd = len(scored_by_date)
    if npd == 0:
        return 0.0, 0.0, 0.0
    ann_net = (V / CAP) ** (MONTHLY_PPY / npd) - 1
    ann_gross = float(np.prod([1 + g for g in grets]) ** (MONTHLY_PPY / npd) - 1)
    drag_bp = (ann_gross - ann_net) * 10000
    return ann_gross, ann_net, (float(np.mean(turnovers)) if turnovers else 0.0)


def _evaluate_window(con, lo, hi):
    rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_ivol_neut, s.fwd_ret_1m
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{lo}'
          AND s.formation_date <= DATE '{hi}'
          AND s.z_ivol_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
        ORDER BY s.formation_date, s.z_ivol_neut
    """).fetchall()
    if not rows:
        return None
    by_date = defaultdict(list)
    for r in rows:
        by_date[r[0]].append(list(r))
    formation_dates = sorted(by_date.keys())

    ic_list = []
    scored_by_date = []
    for fdate in formation_dates:
        flist = by_date[fdate]
        present = [(r[2], r[3]) for r in flist if r[3] is not None]
        if len(present) < MIN_NAMES:
            continue
        rho, _ = spearmanr([p[0] for p in present], [p[1] for p in present])
        ic_list.append(float(rho))
        scored_by_date.append(flist)
    if len(ic_list) < 2:
        return None
    ic = np.array(ic_list)
    mean_ic, sd_ic, tstat, pval_pos = _one_sided_t(ic)
    pval_neg = 1.0 - pval_pos
    ac1 = _ac1(ic)

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
    ann_gross, ann_net, turnover = _quintile_spread(scored_by_date, fee_map)

    return {
        "n_formations": len(formation_dates),
        "n_ic": len(ic_list),
        "mean_names": float(np.mean([len(by_date[d]) for d in formation_dates])),
        "mean_ic": mean_ic, "sd_ic": sd_ic, "tstat": tstat, "pval_neg": pval_neg,
        "ac1": ac1, "ann_gross": ann_gross, "ann_net": ann_net, "turnover": turnover,
        "ic_series": ic_list, "ic_dates": formation_dates,
    }


def main():
    if not SIG_DB.exists():
        print("ERROR: signals DB not found. Run build_ivol.py first.")
        return 1

    con = duckdb.connect()
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_WRITE)")
    con.execute("SET threads=2")
    commit = _git_commit()

    # Self-check: re-derive TRAIN, confirm it matches the frozen TRAIN report.
    tr = _evaluate_window(con, TRAIN_LO, TRAIN_HI)
    if tr is None:
        print("ERROR: could not evaluate TRAIN window")
        return 1
    ic_match = abs(tr["mean_ic"] - TRAIN_REF_IC) < SELFCHECK_TOL
    net_match = abs(tr["ann_net"] - TRAIN_REF_NET) < SELFCHECK_TOL
    print(f"TRAIN self-check: IC {tr['mean_ic']:.6f} (ref {TRAIN_REF_IC}) -> {'OK' if ic_match else 'MISMATCH'}; "
          f"net {tr['ann_net']:.4f} (ref {TRAIN_REF_NET}) -> {'OK' if net_match else 'MISMATCH'}")

    ho = _evaluate_window(con, HOLDOUT_LO, HOLDOUT_HI)
    if ho is None:
        print("ERROR: could not evaluate HOLDOUT window")
        return 1
    print(f"HOLDOUT: {ho['n_formations']} formations, IC {ho['mean_ic']:.6f}, net {ho['ann_net']*100:.2f}%")

    # Gate 3: sign persists AND net spread persists.
    train_sign_neg = tr["mean_ic"] < 0
    holdout_sign_neg = ho["mean_ic"] < 0
    sign_persists = train_sign_neg == holdout_sign_neg and holdout_sign_neg
    net_persists = ho["ann_net"] > 0
    gate3_pass = sign_persists and net_persists

    # Report
    w = []
    W = w.append
    W("# IVOL Sleeve — HOLDOUT Report\n")
    W(f"**Script-generated** — `scripts/signal_engine/ivol/run_holdout.py`. "
      f"Code commit `{commit}`.\n")
    W("**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 3 "
      f"(declaration SHA `d7ebcbcc…`).\n")
    W("**Windows:** HOLDOUT 2021-01-31 → 2022-12-31. SEALED (2023-01 → 2026-07) "
      "still untouched.\n")
    W("**No parameter touched between TRAIN and HOLDOUT** — the frozen "
      "`build_ivol.py` signal is evaluated unchanged on the HOLDOUT window.\n")

    W("## Self-check (TRAIN re-derived, must match frozen TRAIN report)\n")
    W("| Quantity | Re-derived | Frozen ref | Match |")
    W("|---|---|---|:--:|")
    W(f"| TRAIN mean IC | {tr['mean_ic']:.6f} | {TRAIN_REF_IC:.6f} | "
      f"{'PASS' if ic_match else '**MISMATCH**'} |")
    W(f"| TRAIN net spread | {tr['ann_net']:.4f} | {TRAIN_REF_NET:.4f} | "
      f"{'PASS' if net_match else '**MISMATCH**'} |")
    if not (ic_match and net_match):
        W("\n**WARNING:** TRAIN re-derivation does not match the frozen TRAIN report. "
          "Do not proceed until reconciled.")
    W("")

    W("## HOLDOUT Results\n")
    W("| Metric | TRAIN | HOLDOUT |")
    W("|---|---|---|")
    W(f"| Formations | {tr['n_ic']} | {ho['n_ic']} |")
    W(f"| Mean names/formation | {tr['mean_names']:.0f} | {ho['mean_names']:.0f} |")
    W(f"| Mean IC | {tr['mean_ic']:+.6f} | {ho['mean_ic']:+.6f} |")
    W(f"| SD(IC) | {tr['sd_ic']:.6f} | {ho['sd_ic']:.6f} |")
    W(f"| t-stat (simple) | {tr['tstat']:.4f} | {ho['tstat']:.4f} |")
    W(f"| p-value (neg-direction) | — | {ho['pval_neg']:.6e} |")
    W(f"| AC1 | {tr['ac1']:.4f} | {ho['ac1']:.4f} |")
    W(f"| Gross annualized (L-S) | {tr['ann_gross']*100:.2f}% | {ho['ann_gross']*100:.2f}% |")
    W(f"| Net annualized (L-S) | {tr['ann_net']*100:.2f}% | {ho['ann_net']*100:.2f}% |")
    W(f"| Avg turnover | {tr['turnover']:.4f} | {ho['turnover']:.4f} |")
    W("")

    W("## Gate-3 Persistence Check\n")
    W("| Check | TRAIN | HOLDOUT | Result |")
    W("|---|---|---|:--:|")
    W(f"| Sign persists (negative) | {tr['mean_ic']:+.4f} | {ho['mean_ic']:+.4f} | "
      f"{'PASS' if sign_persists else '**FAIL**'} |")
    W(f"| Net spread persists (> 0) | {tr['ann_net']*100:.2f}% | {ho['ann_net']*100:.2f}% | "
      f"{'PASS' if net_persists else '**FAIL**'} |")
    W("")
    W("**Note on significance:** gate 3 tests *persistence* of sign and net spread, "
      "not re-significance (the HOLDOUT window is short — "
      f"{ho['n_ic']} formations). Significance is reported above for transparency: "
      f"HOLDOUT t = {ho['tstat']:.4f}, p = {ho['pval_neg']:.4e}.")
    W("")

    W("## HOLDOUT IC Series\n")
    W("| Formation date | IC | Names |")
    W("|---|---|---:|")
    for i, d in enumerate(ho["ic_dates"]):
        W(f"| {d} | {ho['ic_series'][i]:.6f} | — |")
    W("")

    if gate3_pass:
        W("## §9 Gate 3 — PASS\n")
        W("The negative sign and positive net spread both persist from TRAIN to "
          "HOLDOUT. No parameter was touched. HOLDOUT authorization satisfied.\n")
        W("**Next:** §9 gate 4 (composite power check with Carry) and gate 5 "
          "(the one-shot SEALED read, 2023-01 → present). The SEALED window is "
          "the final, unrepeatable resource — opened only after the composite "
          "check is cleared.")
    else:
        W("## §9 Gate 3 — FAIL\n")
        fails = []
        if not sign_persists:
            fails.append("sign did not persist")
        if not net_persists:
            fails.append("net spread did not persist")
        W(f"HOLDOUT {', '.join(fails)}. IVOL does not advance to SEALED.\n")
        W("Per §9: no successor auto-authorized; SEALED window stays untouched.")

    report = "\n".join(w) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    print(f"  HOLDOUT IC: {ho['mean_ic']:.6f} (t={ho['tstat']:.4f}, neg-p={ho['pval_neg']:.4e})")
    print(f"  HOLDOUT net: {ho['ann_net']*100:.2f}%")
    print(f"  Gate 3: {'PASS' if gate3_pass else 'FAIL'}")

    con.close()
    return 0 if gate3_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
