"""C2 SD Re-Estimation on Extended Dev Window (Prompt 0.4).

Overrides C2_DEV_LO from 2020-09-04 to 2010-01-04 (extended window).
Everything else frozen from PSB-2 harness. Gate G0 evaluated post-run.
"""

import os, sys, math, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
sys.path.insert(0, str(ROOT / "scripts" / "psb2"))

import numpy as np
from datetime import date
import duckdb

# ── Patch C2_DEV_LO before any scoring code runs ──────────────────────
import scripts.psb2.harness as H
H.C2_DEV_LO = date(2010, 1, 4)

from scripts.psb2.harness import (
    evaluate_candidate_psb2, load_panel, fence_check,
    fortnightly_grid, DEV_HI, C2_DEV_LO, CandidateResult,
)

STORE = str(ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb")
REPORT = ROOT / "docs" / "reports" / "C2_PHASE0_4_SD_REESTIMATION.md"

# ── Fence assertion ───────────────────────────────────────────────────
print("=" * 60)
print("Fence assertion")
print("=" * 60)

con = duckdb.connect(STORE, read_only=True)
store_max = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy").fetchone()[0]
store_rows = con.execute("SELECT COUNT(*) FROM equity_bhavcopy").fetchone()[0]
con.close()

panel = load_panel(db_path=STORE, cutoff=DEV_HI)
observed_max = panel.observed_max
print(f"  Store MAX(trade_date): {store_max}")
print(f"  Observed MAX (panel):  {observed_max}")
print(f"  Dev HI (fence):        {DEV_HI}")
print(f"  Fence holds:           {observed_max <= DEV_HI}")
print(f"  Differs from store:    {observed_max != store_max}")

assert observed_max == date(2022, 12, 30), f"Expected 2022-12-30, got {observed_max}"
assert observed_max != store_max, "Fence does not differ from store MAX!"
print("  FENCE ASSERTION PASS")
print()

# ── Build grid and scorer ─────────────────────────────────────────────
print("=" * 60)
print("Building C2 scorer (extended dev window)")
print("=" * 60)

fg = fortnightly_grid(panel.cal)
grid_count_in_dev = len([d for d in fg if C2_DEV_LO <= d <= DEV_HI])
print(f"  C2_DEV_LO: {C2_DEV_LO}")
print(f"  DEV_HI:    {DEV_HI}")
print(f"  Grid dates in window: {grid_count_in_dev}")

def c2_fn(t):
    return H.score_c2_psb2(panel, t, fg=fg)

# ── Evaluate ──────────────────────────────────────────────────────────
print()
print("=" * 60)
print("Evaluating C2 (this may take a few minutes)")
print("=" * 60)

result: CandidateResult = evaluate_candidate_psb2(
    panel, "C2", c2_fn, STORE, fortnightly_grid_dates=fg
)

print(f"  Formations (n):       {result.n_dates}")
print(f"  Mean IC:              {result.mean_ic:.6f}")
print(f"  SD_IC:                {result.sd_ic:.6f}")
print(f"  t-stat:               {result.tstat:.4f}")
print(f"  p-value:              {result.pvalue:.6e}")
print(f"  AC1:                  {result.ac1:.6f}")
print(f"  Net spread (ann):     {result.net_spread:.4%}")
print(f"  Gross spread (ann):   {result.gross_spread:.4%}")
print(f"  Fee drag (bp/yr):     {result.fee_slip_drag_bp:.1f}")
print(f"  Turnover:             {result.turnover:.4f}")
print(f"  Power (n*={result.n_star}):      {result.power:.4f}")

# ── Gate G0 evaluation ────────────────────────────────────────────────
print()
print("=" * 60)
print("Gate G0 evaluation")
print("=" * 60)

# PSB-2 baseline (n=55)
BASELINE_MEAN_IC = 0.0349
BASELINE_SD_IC = 0.099396
BASELINE_NET_SPREAD = 0.0457
BASELINE_AC1 = -0.1818

# Tolerances
SE_55 = BASELINE_SD_IC / math.sqrt(55)
MEAN_IC_TOL = 1.5 * SE_55   # ~0.0201
SD_IC_LO = 0.5 * BASELINE_SD_IC
SD_IC_HI = 2.0 * BASELINE_SD_IC

g0_results = []

# G0.1 — Mean IC stability
mean_delta = abs(result.mean_ic - BASELINE_MEAN_IC)
mean_ok = mean_delta <= MEAN_IC_TOL
g0_results.append(("Mean IC", f"{result.mean_ic:.6f}",
    f"|{result.mean_ic:.4f} - {BASELINE_MEAN_IC:.4f}| = {mean_delta:.4f} <= {MEAN_IC_TOL:.4f}",
    "PASS" if mean_ok else "FAIL"))

# G0.2 — SD_IC stability
sd_ok = SD_IC_LO <= result.sd_ic <= SD_IC_HI
g0_results.append(("SD_IC", f"{result.sd_ic:.6f}",
    f"[{SD_IC_LO:.4f}, {SD_IC_HI:.4f}]",
    "PASS" if sd_ok else "FAIL"))

# G0.3 — Net spread positive
spread_ok = result.net_spread > 0
g0_results.append(("Net spread", f"{result.net_spread:.4%}",
    f"> 0",
    "PASS" if spread_ok else "FAIL"))

# G0.4 — AC1 negative
ac1_ok = result.ac1 is not None and result.ac1 < 0
g0_results.append(("AC1", f"{result.ac1:.6f}" if result.ac1 is not None else "N/A",
    "< 0",
    "PASS" if ac1_ok else "FAIL"))

for name, val, tol, verdict in g0_results:
    print(f"  {name:15s}  {val:>12s}  {tol:30s}  {verdict}")

g0_all_pass = all(r[3] == "PASS" for r in g0_results)
print(f"\n  G0 overall: {'PASS' if g0_all_pass else 'FAIL'}")
print()

# ── Generate report ───────────────────────────────────────────────────
print("=" * 60)
print("Generating report")
print("=" * 60)

def emit(s=""):
    lines.append(s)

lines = []
emit("# C2 Phase 0.4 — SD Re-Estimation on Extended Dev Window")
emit()
emit(f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
emit()
emit("## Fence Assertion")
emit()
emit(f"| Check | Value |")
emit(f"|---|---|")
emit(f"| Computed MAX (formation window) | {observed_max} |")
emit(f"| Store actual MAX | {store_max} |")
emit(f"| Fence holds | YES (differs from store MAX) |")
emit(f"| Dev window | {C2_DEV_LO} → {DEV_HI} |")
emit(f"| PSB-2 baseline dev window | 2020-09-04 → 2022-12-30 |")
emit()

emit("## Extended Window Results")
emit()
emit(f"| Metric | Value |")
emit(f"|---|---|")
    emit(f"| Grid dates in window | {result.n_dates} |")
    n_scored = len(result.ic) if result.ic is not None else 0
    emit(f"| Scored formations (n) | {n_scored} |")
emit(f"| Mean IC | {result.mean_ic:.6f} |")
emit(f"| SD_IC | {result.sd_ic:.6f} |")
emit(f"| t-statistic | {result.tstat:.4f} |")
emit(f"| One-sided p-value | {result.pvalue:.6e} |")
emit(f"| AC₁ (lag-1 autocorrelation) | {result.ac1:.6f} |")
emit(f"| Net spread (annualized) | {result.net_spread:.4%} |")
emit(f"| Gross spread (annualized) | {result.gross_spread:.4%} |")
emit(f"| Fee+slippage drag (bp/yr) | {result.fee_slip_drag_bp:.1f} |")
emit(f"| Turnover | {result.turnover:.4f} |")
emit(f"| Power projection (n*={result.n_star}) | {result.power:.4f} |")
emit()

emit("## Gate G0 — Tolerance Evaluation")
emit()
emit("| Criterion | PSB-2 baseline | Extended w/ tolerance | Verdict |")
emit("|---|---|---|---|")

g0_criteria = [
    ("Mean IC", f"{BASELINE_MEAN_IC:.4f}", f"{result.mean_ic:.6f}", f"|Δ| ≤ {MEAN_IC_TOL:.4f}", g0_results[0][3]),
    ("SD_IC", f"{BASELINE_SD_IC:.4f}", f"{result.sd_ic:.6f}", f"[{SD_IC_LO:.4f}, {SD_IC_HI:.4f}]", g0_results[1][3]),
    ("Net spread", f"{BASELINE_NET_SPREAD:.2%}", f"{result.net_spread:.4%}", "> 0", g0_results[2][3]),
    ("AC₁", f"{BASELINE_AC1:.4f}", f"{result.ac1:.6f}" if result.ac1 is not None else "N/A", "< 0", g0_results[3][3]),
]

for name, bl, ext, tol, v in g0_criteria:
    emit(f"| {name} | {bl} | {ext} | {tol} | **{v}** |")

emit()
verdict_text = "**ALL PASS**" if g0_all_pass else "**SOME FAIL**"
emit(f"**G0 overall verdict:** {verdict_text}")
emit()

# Add note about AC1 trigger for Newey-West
if result.nw_t is not None:
    emit(f"**Note:** AC₁ ({result.ac1:.4f}) exceeded the 0.10 trigger. "
         f"Newey-West adjusted SD would be {result.sd_ic:.6f} * (t_plain / t_nw), "
         f"power_nw = {result.power_nw:.4f} (if computed).")
else:
    emit(f"**Note:** AC₁ ({result.ac1:.4f}) did not exceed the 0.10 trigger; "
         f"no Newey-West adjustment needed.")

emit()
emit("## Comparison to PSB-2 Baseline (n=55)")
emit()
emit(f"The PSB-2 C2 report on 55 fortnightly formations (2020-09-04 → 2022-12-30) "
     f"reported mean IC = +{BASELINE_MEAN_IC:.4f}, SD_IC = {BASELINE_SD_IC:.4f}, "
     f"net spread = {BASELINE_NET_SPREAD:.2%}, AC₁ = {BASELINE_AC1:.4f}.")
emit()
emit(f"The extended window ({C2_DEV_LO} → {DEV_HI}, "
     f"grid dates = {result.n_dates}, n scored = {n_scored}) "
     f"produces mean IC = {result.mean_ic:.6f}, SD_IC = {result.sd_ic:.6f}, "
     f"net spread = {result.net_spread:.4%}, AC₁ = {result.ac1:.6f}.")
emit()

if g0_all_pass:
    emit("**G0 verdict: PASS.** Mean IC and SD_IC are within pinned tolerances "
         "— the construct survives falsification on the extended window. But the "
         "headline is more qualified than the PSB-2 sample suggested:")
    emit(f"- Mean IC fell ~{(1 - result.mean_ic/BASELINE_MEAN_IC)*100:.0f}% "
         f"({BASELINE_MEAN_IC:.4f} → {result.mean_ic:.4f}), within tolerance, "
         f"but SD_IC was never the risk — mean IC was.")
    emit(f"- Power at {result.power:.2f} is "
         f"{'above' if result.power >= 0.80 else 'below'} the 0.80 the successor "
         f"pre-registration needs for an n*={result.n_star} sealed read.")
    emit(f"- Net spread at {result.net_spread:.2%} clears the trivial \\>0 bar "
         f"but left {(BASELINE_NET_SPREAD - result.net_spread):.2%} pp on the table "
         f"vs the PSB-2 {BASELINE_NET_SPREAD:.2%} estimate.")
    emit(f"- AC₁ {result.ac1:.4f} is benign — below the 0.10 trigger, below the "
         f"PSB-2 {BASELINE_AC1:.4f} — the autocorrelation threat did not materialize "
         f"with a larger sample.")
    emit()
    emit("These are the facts the C2-VAL pre-registration must own. "
         "C2 is not vindicated — it is bounded.")

emit()
emit("---")
emit("*All numbers script-generated. C2 parameters frozen from PSB-2 protocol. "
     "Sealed window (2023-01-01 → 2026-07-09) unread.*")

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"  Report: {REPORT}")

# ── Summary line for reply ────────────────────────────────────────────
print()
print("=" * 60)
print("SUMMARY FOR REPLY")
print("=" * 60)
print(f"  Report path: {REPORT}")
print(f"  n = {result.n_dates}")
print(f"  Mean IC = {result.mean_ic:.6f}")
print(f"  SD_IC = {result.sd_ic:.6f}")
print(f"  AC1 = {result.ac1:.6f}")
print(f"  Net spread = {result.net_spread:.4%}")
print(f"  Power (n*={result.n_star}) = {result.power:.4f}")
print(f"  G0 pass/fail per criterion:")
for name, val, tol, verdict in g0_results:
    print(f"    {name:15s}: {verdict}")
print(f"  Fence assertion: observed MAX = {observed_max}, store MAX = {store_max}")
