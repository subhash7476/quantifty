# M1c RFA Declaration v4 (FROZEN)

**Status:** FROZEN v4, 2026-09-29. Supersedes v3 (`f4b7e44`, immutable). This version corrects a unit
mismatch identified in review: the band was derived as a strategy-level Sharpe but applied as a
session-series Sharpe. The mapping below reunites them; every H collapses to one power curve, and the
optimistic corner moves to the top of its own derived range. **Verdict: ABANDON (retained), now
HOLDOUT-binding.** Governing protocol v1.3 unchanged. Methodology 2.0.0, hurdle 0.80. No market data
read, no backtest, no TRAIN, no new hypothesis.

## 1. What v2/v3 got wrong and right

- **Wrong (R3-1):** v1 §6 derived the band as a daily-book information ratio (strategy Sharpe, Grinold
  IR = IC·√BR). v2/v3 applied those values to S_x, the standardized mean of the H-day session series —
  a quantity √H larger for the same economics. The H=5/10 power rows therefore understated power, and
  "ABANDON strengthened" was unsupported.
- **Right and retained:** the overlap derivation's algebra (shared-day counts, triangular MA structure),
  Assumption W, the H=1 rows (which are exactly the corrected values), the rescue-threshold arithmetic,
  the fee/selection analysis, and the exclusion framework. v3's session-unit floor
  (ncp ≥ S_x·√(T/H)) remains algebraically true — it is reconciled, not deleted: with S_x = √H·S_strat
  it gives the identical ncp below.

## 2. Corrected mapping (strategy Sharpe → HAC test, all H)

Regroup the session mean by calendar day: Σ_τ x_τ = Σ_d H·b̃_d, where b̃_d averages the cohort slices
active on day d (≈ the strategy's daily book return b_d in steady state: equal cohort sizes up to
day-to-day tail-count variation; O(H/n) edge sessions negligible at n ≈ 250/1,240 — approximations
stated, verdict margins below make their slop immaterial). Hence x̄ ≈ H·b̄ and, under W at book level,
LRV(x) ≈ H²·LRV(b): ncp = H·m·√n/(H·√v_b) = **S_strat·√T for every H**. H differentiates fees and
selection only, never power. W keeps its v3 status (needed for LRV = marginal variance; violations cut
both ways per the retained rescue analysis). Finite-sample HAC over-rejection at n = 250 works against
ABANDON (raises true rejection rates) but cannot bridge 0.26 → 0.80 — disclosed, not quantified beyond
that bound. The sequential rule (both stages ≥ 0.80) is the generous min-formulation; a strict
joint-power rule would fail harder.

## 3. VAL design (α = 0.025, T ≈ 4.96 y, all H identical)

Power = Φ(S·√4.96 − 1.96):

| S=0.2 | S=0.5 | S=1.0 | S=1.8 opt | S=2.0 robustness |
|---|---|---|---|---|
| 0.06 | 0.20 | 0.61 | **0.98** | 0.99 |

MDE 1.26 all H. Sessions required at the optimistic corner: 606 (have ≈1,240).

## 4. HOLDOUT design (250 sessions, α = 0.05, all H identical)

Power = Φ(S − 1.6449):

| S=0.2 | S=0.5 | S=1.0 | S=1.8 opt | S=2.0 robustness |
|---|---|---|---|---|
| 0.07 | 0.13 | 0.26 | **0.56** | 0.64 |

MDE 2.49 all H. Sessions required at the optimistic corner: 478 (have 250).

## 5. Band (corrected range, relabeled corners)

Grinold translation of CB-N50 HOLDOUT IC +0.0294 recomputed: b = 5 → 1.04, b = 15 → 1.80 (v1's "1.0–1.5"
top end was wrong). **Optimistic corner is now 1.8 — the top of its own derived range**, i.e. genuinely
generous: combined (not reversal-only) IC, favorable breadth, full capture, zero costs. Central 0.5 and
pessimistic 0.2 are labeled conventional markers (irrelevant to an optimistic-corner verdict, retained
for context). Added exclusion: **PSB-1 C2** (fortnightly residual-reversal IC +0.035, retired on
extended-history power) cannot anchor an absolute-daily band — residual ≠ absolute construct,
fortnightly ≠ daily mapping, and reusing its in-sample IC repeats the documented C2 error. Robustness
check: even C2-implied S ≈ 2.14 gives HOLDOUT power 0.69 < 0.80 — it cannot flip the verdict, since any
ceiling below 2.49 fails HOLDOUT. One band now applies to all H naturally (strategy-level property).

## 6. PASS / ABANDON (mechanical)

**PASS iff optimistic-corner power ≥ 0.80 at BOTH VAL and HOLDOUT.** Evaluated at S = 1.8: VAL 0.98
(passes), HOLDOUT 0.56 (fails) → **ABANDON, HOLDOUT-binding.** Holds for any ceiling below 2.49 and at
every H. Rescue thresholds retained H-independently (HOLDOUT needs variance ratio ≤ 0.16, i.e.
Σρ ≤ −0.42; VAL ≤ 0.63). Per frozen §12: no data read; protocol returns to draft.

## 7. Pre-read inputs, governance, no-data statement, consistency check

As v3 §§7–8 (band values updated to §5 above; VAL count from `trading_calendar`; companion `.py`
transcription; v1–v3 immutable). No M1c result consulted; mapping is algebra on the frozen
construction, band from adjacent public record. Targeted check: estimand protocol-exact (absolute
session mean, §2 consistent with §6 v1.3); Sharpe consistently strategy-level throughout (§§2–5 use one
definition); H treated identically with derivation, not assumption; VAL/HOLDOUT power recomputed by
hand above (VAL 0.98 / HOLDOUT 0.56 at optimistic); PASS/ABANDON rule unchanged in form, re-evaluated.

## Change Log

- v4 (2026-09-29, FROZEN): unit mismatch corrected (R3-1: strategy- vs session-Sharpe reunited; all H
  collapse to one curve); Grinold range corrected to 1.04–1.80 with optimistic at top (R3-2); C2
  exclusion added with can't-flip arithmetic (R3-2); HAC size-distortion and min-rule generosity noted
  (R3-3); verdict ABANDON retained, HOLDOUT-binding. v1–v3 immutable.
