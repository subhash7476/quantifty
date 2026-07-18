# C2 Phase 0.4 — SD Re-Estimation — Independent Lead Re-Derivation

**Reviewer:** Claude (Lead Reviewer)
**Date:** 2026-07-18
**Under review:** `docs/reports/C2_PHASE0_4_SD_REESTIMATION.md`, `scripts/c2_sd_reestimate.py`
**Method:** re-ran the scoring through the frozen PSB-2 harness (fidelity tests 6/6 green → scoring machinery provably unchanged), then **recomputed every summary statistic from the raw per-formation IC vector (`result.ic`) with my own numpy/scipy** — not by re-running the report script. Provenance of the underlying store checked directly.

---

## Verdict: numbers ARITHMETICALLY CORRECT and reproduce exactly — but the report has a **material reporting defect (n)**, an **out-of-sequence production swap**, and an **over-stated conclusion**. G0's IC/SD-consistency claim stands; "ALL PASS / SD is just a sample-size artifact" oversells it.

---

## What reproduced exactly (independent recompute from the IC vector)

| Metric | Report | My recompute from `result.ic` | Δ |
|---|--:|--:|--:|
| mean IC | 0.024563 | 0.024563 | 0 |
| SD_IC (ddof=1) | 0.104209 | 0.104209 | 0 |
| t-stat | 3.8006 | 3.8006 | 0 |
| one-sided p | 8.9997e-05 | 8.9997e-05 | 0 |
| power (noncentral-t, α=0.05, n*=84) | 0.6907 | 0.6907 | 0 |
| AC₁ | −0.041441 | −0.041958 (Pearson lag-1) | 5e-4 (immaterial; both ≪ 0.10 trigger) |

The scoring is the frozen PSB-2 C2 machinery over an extended window; the aggregation is correct. **C2 is not falsified** on the extended history — the effect persists (t=3.80, p≈9e-5) with the SD essentially unchanged.

**Drag reconciliation (the advisor's 14 bp gap — resolved):** gross−net spread drag = 222.2 bp; `fee_slip_drag_bp` = 235.8 bp; difference = **13.6 bp = the base-quintile leg's drag**. `fee_slip_drag_bp` measures the top-quintile leg only; the long/short spread nets out the base leg. No error — internally consistent.

**Fence:** observed formation MAX = 2022-12-30 ≤ 2022-12-31; sealed 2023–2026 unread. `n*`=84 is a sealed-window grid **count**, not a value read. ✓

---

## Findings

### H1 (HIGH, governance) — the production store WAS swapped, contrary to "the store has not been swapped"
Direct check: the **live** `equity_bhavcopy.duckdb` now has non-NULL `deliv_pct` spanning **2010-01-04 → 2026-07-09 (3,524,484 pre-2020 cells)** — byte-for-byte the same coverage as `equity_bhavcopy_mto_backfill.duckdb`. In the Phase 0.2 Lead Review earlier today the live store had **0** pre-2020 non-null cells (that is what made Arm E vacuous). So the live store was modified after that review — the backfilled delivery is now in production. This happened **outside the gated sequence**: the swap was authorized on data grounds, but B1-R2 (sealing the audit artifact) and a post-swap `certify_substrate.py` run on the live store were its conditions, and Phase 0.4 was to run *after* that. Whether by a formal swap or a direct backfill-to-live, the copy-first gate was not followed to the letter. **Action: confirm a timestamped pre-swap backup of the live store exists; run `certify_substrate.py` on the now-live store and record it; reconcile the process record.**

### H2 (MEDIUM, reporting defect) — "Formations (n) = 311" is the grid count, NOT the estimation sample
`n_dates = len(formation_dates) = 311` is the count of fortnightly grid dates in the window. But mean IC, SD, t, and the whole estimate are computed on **`len(result.ic) = 260`** scored formations — 51 early formations (≈2010, before a 252-day delivery baseline exists) return no scores and are dropped. Confirmed by the t-stat: 0.024563/(0.104209/√260) = 3.80 (matches); √311 would give 4.16 (does not). The report prints "Formations (n) | 311", which **overstates the estimation sample by 51** and inflates the "55 → 311" narrative; the true increase is 55 → **260**. Fix: report the scored n (260) for the statistics, and label 311 as the grid count if kept at all.

### H3 (substantive framing) — power 0.6907 < 0.80, and the driver is a ~30% drop in mean IC, not SD
The report's conclusion — *"the 55-observation SD is confirmed as a sample-size artifact, ALL PASS"* — tells half the story. SD held (0.0994 → 0.1042). What weakened is the **mean IC (0.0349 → 0.0246, ~30% lower)**, so effect size d fell to 0.236 and projected **power fell 0.92 → 0.69**, below the 0.80 the successor pre-registration needs. G0 as *designed* tests IC/SD consistency only (power is correctly not a G0 gate), and the tabled criteria genuinely pass — but the honest headline is **"survives falsification; effect size and power materially lower than the PSB-2 sample suggested."** Net spread reinforces this: 4.57% → **0.78%**, clearing only a trivial `>0` bar.

### M1 (MEDIUM, governance) — tolerances are unverifiable as pre-registered
`c2_sd_reestimate.py` and the 0.4 report are **untracked, with no git history**; the G0 tolerances (`MEAN_IC_TOL = 1.5·SE₅₅`, SD band [0.5×, 2×], net-spread `>0`) are hardcoded in that untracked script. There is no version-control anchor proving they were pinned *before* the run (roadmap G0 requires pre-pinning). Not evidence they were fitted — but not provable-in-advance either. The bands are also loose (IC ±0.0201 ≈ 58% of baseline; net-spread `>0`), so G0 is a weak falsification test. Commit the tolerances (and the script) as a pre-registration artifact for any future re-run.

---

## Bottom line for the roadmap
- **G0 IC/SD consistency: genuinely PASS.** C2 is not falsified; the estimate is arithmetically sound and reproduces exactly.
- **But the report must be corrected** (n = 260 not 311) and **re-framed** (power 0.69 < 0.80, mean IC down ~30%, net spread 0.78%). These are the facts **Phase 1 (C2-VAL) pre-registration must own** before the one-shot sealed read — the successor must pin its own view on a 0.69-power construct, not carry forward the "ALL PASS / vindicated" reading.
- **Resolve H1 before proceeding**: confirm the pre-swap backup and post-swap live certification, and reconcile the "not swapped" record. Production data state and the process log currently disagree.

*Re-derivation numbers are script-generated from the frozen harness + independent recompute. Sealed window untouched.*
