"""Skew §6 — TRAIN read.

Computes rank-IC, quintile spreads, and evidence metrics for the TRAIN period
(2016-07 -> 2020-12). Reads the sign from TRAIN (two-sided test).

Generates script-generated report: SKEW_TRAIN_REPORT.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]

SIG_DB = ROOT / "data" / "signal_engine" / "skew" / "signals.duckdb"
REPORT = ROOT / "docs" / "reports" / "SKEW_TRAIN_REPORT.md"

TRAIN_LO = "2016-07-01"
TRAIN_HI = "2020-12-31"
FEE_DRAG_BP = 35.2  # futures fee model, same as Carry
SLIPPAGE_BP = 5.0  # per-side slippage


def main():
    if not SIG_DB.exists():
        print("ERROR: signals DB not found. Run build_skew.py and neutralize.py first.")
        return 1

    con = duckdb.connect(str(SIG_DB))
    con.execute("SET threads=4")

    print(f"TRAIN period: {TRAIN_LO} -> {TRAIN_HI}")

    rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_skew_neut,
               s.fwd_ret_1m, f.formation_date AS fwd_date
        FROM signals s
        JOIN formations f ON f.formation_date = s.formation_date
        WHERE s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.z_skew_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
          AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    if not rows:
        print("ERROR: No TRAIN signals found.")
        con.close()
        return 1

    print(f"  {len(rows)} signal-return pairs")

    ics = []
    formation_data = {}

    for fdate, u, z, fwd, _ in rows:
        if fdate not in formation_data:
            formation_data[fdate] = {"z": [], "ret": []}
        formation_data[fdate]["z"].append(z)
        formation_data[fdate]["ret"].append(fwd)

    for fdate in sorted(formation_data.keys()):
        z_vals = np.array(formation_data[fdate]["z"])
        ret_vals = np.array(formation_data[fdate]["ret"])

        if len(z_vals) < 2:
            continue

        ic, _ = stats.spearmanr(z_vals, ret_vals)
        if not np.isnan(ic):
            ics.append(ic)

    ics = np.array(ics)
    mean_ic = float(np.mean(ics)) if len(ics) > 0 else 0.0
    sd_ic = float(np.std(ics, ddof=1)) if len(ics) > 1 else 0.0
    n_form = len(ics)

    print(f"  {n_form} formations with IC")
    print(f"  Mean IC: {mean_ic:.4f}")
    print(f"  SD IC: {sd_ic:.4f}")

    if n_form < 10:
        print("ERROR: Insufficient formations for inference.")
        con.close()
        return 1

    t_stat = mean_ic / (sd_ic / np.sqrt(n_form)) if sd_ic > 0 else 0.0
    df = n_form - 1
    p_two_sided = 2 * (1 - stats.t.cdf(abs(t_stat), df)) if df > 0 else 1.0

    print(f"  t-stat: {t_stat:.4f}")
    print(f"  p-value (two-sided): {p_two_sided:.4e}")

    mean_abs_ic = float(np.mean(np.abs(ics))) if len(ics) > 0 else 0.0
    print(f"  Mean |IC|: {mean_abs_ic:.4f}")

    sign_positive = mean_ic >= 0
    print(f"  Sign: {'POSITIVE' if sign_positive else 'NEGATIVE'} (steep skew -> {'higher' if sign_positive else 'lower'} returns)")

    print("\nComputing quintile spreads...")
    quintile_returns = {i: [] for i in range(5)}

    for fdate in sorted(formation_data.keys()):
        z_vals = np.array(formation_data[fdate]["z"])
        ret_vals = np.array(formation_data[fdate]["ret"])

        if len(z_vals) < 5:
            continue

        q5 = np.percentile(z_vals, [20, 40, 60, 80])

        for i in range(5):
            if i == 0:
                mask = z_vals <= q5[0]
            elif i == 4:
                mask = z_vals >= q5[3]
            else:
                mask = (z_vals >= q5[i - 1]) & (z_vals <= q5[i])

            if np.sum(mask) > 0:
                quintile_returns[i].append(float(np.mean(ret_vals[mask])))

    q_mean = {}
    for i in range(5):
        if quintile_returns[i]:
            q_mean[i] = float(np.mean(quintile_returns[i]))
        else:
            q_mean[i] = 0.0

    print(f"  Q1: {q_mean[0]:.4f}")
    print(f"  Q2: {q_mean[1]:.4f}")
    print(f"  Q3: {q_mean[2]:.4f}")
    print(f"  Q4: {q_mean[3]:.4f}")
    print(f"  Q5: {q_mean[4]:.4f}")

    q5_q1_gross = q_mean[4] - q_mean[0]
    print(f"  Q5 - Q1 gross: {q5_q1_gross:.4f}")

    fee_annual = (FEE_DRAG_BP + 2 * SLIPPAGE_BP) / 10000
    fee_per_formation = fee_annual / 12.0

    turnover = 0.8
    fee_drag = turnover * fee_per_formation

    q5_q1_net = q5_q1_gross - fee_drag

    print(f"  Fee drag per formation: {fee_drag:.6f}")
    print(f"  Q5 - Q1 net: {q5_q1_net:.4f}")

    ann_net = q5_q1_net * 12.0 * 100.0
    print(f"  Annualized net: {ann_net:.2f}%")

    print("\nGenerating report...")
    lines = [
        "# Skew Sleeve — TRAIN Report\n",
        f"**Generated:** {REPORT.stat().st_mtime if REPORT.exists() else 'N/A'}",
        "**Metric:** rank-IC (two-sided)",
        "**Signal construction:** option-implied skew = IV(25-delta put) - IV(25-delta call)",
        f"**Metric:** rank-IC (two-sided)",
        f"**TRAIN period:** {TRAIN_LO} -> {TRAIN_HI}",
        "",
        "---",
        "",
        "## 1. Existence Test (rank-IC)\n",
        f"**Mean IC:** {mean_ic:.4f}",
        f"**SD IC:** {sd_ic:.4f}",
        f"**n:** {n_form} formations",
        f"**t-statistic:** {t_stat:.4f}",
        f"**p-value (two-sided):** {p_two_sided:.4e}",
        f"**Mean |IC|:** {mean_abs_ic:.4f}",
        "",
        f"**Result:** {'**PASS**' if p_two_sided < 0.05 else 'FAIL'} (significant at 5% level)" if p_two_sided < 0.05 else "**FAIL**",
        "",
        "---",
        "",
        "## 2. Sign Read (from TRAIN)\n",
        f"**Sign:** {'**POSITIVE**' if sign_positive else '**NEGATIVE**'}",
        f"**Interpretation:** Steeper put skew -> {'**higher**' if sign_positive else '**lower**'} forward returns",
        f"**Literature alignment:** {'Steep put skew -> lower returns (informed pessimism) -> OPPOSITE to TRAIN' if not sign_positive else 'Steep put skew -> higher returns (crowding/hedging-unwind) -> aligned with crowding reading'}",
        "",
        "---",
        "",
        "## 3. Quintile Spread (Fees and Slippage)\n",
        f"**Q1 (low skew):** {q_mean[0]:.4f}",
        f"**Q5 (high skew):** {q_mean[4]:.4f}",
        f"**Gross Q5 - Q1:** {q5_q1_gross:.4f} ({q5_q1_gross * 100:.2f}%)",
        "",
        f"**Fee model:** {FEE_DRAG_BP} bp/yr + {SLIPPAGE_BP * 2} bp/yr slippage = {FEE_DRAG_BP + SLIPPAGE_BP * 2} bp/yr",
        f"**Turnover:** {turnover:.1f} (assumed)",
        f"**Fee drag per formation:** {fee_drag:.6f}",
        "",
        f"**Net Q5 - Q1:** {q5_q1_net:.4f} ({q5_q1_net * 100:.2f}%)",
        f"**Annualized net:** {ann_net:.2f}%",
        "",
        f"**Result:** {'**PASS**' if q5_q1_net > 0 else 'FAIL'} (net > 0 under fees)",
        "",
        "---",
        "",
        "## 4. IC SD Validation\n",
        f"**IC SD:** {sd_ic:.4f}",
        f"**Allowed band:** [0.10, 0.18]",
        f"**Result:** {'**PASS**' if 0.10 <= sd_ic <= 0.18 else '**FAIL**'}",
        "",
        "---",
        "",
        "## 5. TRAIN Summary\n",
        "| Test | Result | Detail |",
        "|---|:--:|---|",
        f"| Rank-IC two-sided significant | {'PASS' if p_two_sided < 0.05 else '**FAIL**'} | t={t_stat:.4f}, p={p_two_sided:.4e} |",
        f"| Net quintile spread > 0 | {'PASS' if q5_q1_net > 0 else '**FAIL**'} | {ann_net:.2f}% annualized |",
        f"| IC SD inside band | {'PASS' if 0.10 <= sd_ic <= 0.18 else '**FAIL**'} | {sd_ic:.4f} vs [0.10, 0.18] |",
        "",
        f"**TRAIN verdict:** {'**PASS** — proceed to HOLDOUT' if p_two_sided < 0.05 and q5_q1_net > 0 and 0.10 <= sd_ic <= 0.18 else '**FAIL** — do not proceed to HOLDOUT'}",
        "",
        "---",
        "",
        "## 6. Next Steps\n",
        "If TRAIN passes:",
        "1. HOLDOUT read (2021-01 -> 2022-12): confirm sign persists, net > 0",
        "2. If HOLDOUT passes: Skew feeds the composite; 0.80 binds on composite",
        "3. SEALED read (2023-01 -> 2026-07): final read, reported as-is",
        "",
        "If TRAIN fails:",
        "1. Stop — two-sided test failed on TRAIN, no basis to proceed",
        "2. No post-hoc parameter tuning allowed (pre-registration frozen)",
        "",
        "---",
        "",
        "## 7. Evidence (Pre-registered Predictions)\n",
        "From SKEW_PHASE0_PRE_REGISTRATION.md §7:\n",
        "1. **PREDICTION 1:** Skew rank-IC is two-sided significant on TRAIN.",
        f"   - **Result:** {'**CONFIRMED**' if p_two_sided < 0.05 else '**REJECTED**'} (p={p_two_sided:.4e})",
        "2. **PREDICTION 2:** Its sign persists from TRAIN to HOLDOUT (sign flip = noise = dead).",
        "   - **Status:** PENDING HOLDOUT",
        "3. **PREDICTION 3:** IC survives beta/sector neutralization (neutralized magnitude ≥ 60% of raw).",
        "   - **Status:** NOT TESTED (z_skew_neut used directly; raw vs neutralized comparison not computed)",
        "4. **PREDICTION 4:** Net quintile spread > 0 under futures fees on liquid subset.",
        f"   - **Result:** {'**CONFIRMED**' if q5_q1_net > 0 else '**REJECTED**'} ({ann_net:.2f}% annualized)",
        "",
        "---",
        "",
        "## 8. Data Completeness\n",
        f"**Total signal-return pairs:** {len(rows)}",
        f"**Formations with IC:** {n_form}",
        f"**Date range:** {TRAIN_LO} -> {TRAIN_HI}",
        "",
        "---",
        "",
        "## 9. Notes and Caveats\n",
        "- IV computed via Black76 inversion from option prices; 7% risk-free rate assumed",
        "- 25-delta strikes interpolated from available strikes using ATM vol as approximation",
        "- Top 100 underlyings by 20-day option turnover per formation",
        "- Minimum option price filter: 0.1 to skip penny options",
        "- Minimum 10 days to expiry to avoid expiry microstructure noise",
        "- Winsorization: ±3σ on skew before z-score",
        "- Beta/sector neutralization applied using trailing 252-day equity beta to Nifty 50",
        "",
        "---",
        "",
        "*Report generated by run_train.py (script-generated, no hand-edited numbers)*",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nReport written to {REPORT}")

    if p_two_sided < 0.05 and q5_q1_net > 0 and 0.10 <= sd_ic <= 0.18:
        print("\n**TRAIN VERDICT: PASS** — Proceed to HOLDOUT")
        return 0
    else:
        print("\n**TRAIN VERDICT: FAIL** — Do not proceed to HOLDOUT")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())