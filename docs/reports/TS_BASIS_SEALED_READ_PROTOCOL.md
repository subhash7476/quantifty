# TS Basis — SEALED Read Protocol (DRAFT)

**Status:** DRAFT. To be **FROZEN** (SHA-256) before the read. Governs the **one-shot**
SEALED confirmation of the TS Basis sleeve (positive sign) — the final gate mandated by
`TS_BASIS_PHASE0_PRE_REGISTRATION.md` §8.
**Window:** SEALED **2023-01-01 → 2026-07-20** (~42 monthly formations). Untouched to date.
**What is being tested:** **TS Basis-only**, positive sign. Not the composite.

---

## 1. Preconditions — ALL must pass before the SEALED read is authorized

1. **Net-of-fee gate (PASS required).** TS Basis net long/short spread must be **> 0,
   annualized, after the §5 futures fee model**, on **both TRAIN and HOLDOUT**. If net ≤ 0
   on either window, STOP — SEALED is not run. *(Computed by `run_net_spread.py`;
   result recorded in `TS_BASIS_NET_SPREAD_REPORT.md`.)*
2. **Combination frozen.** SEALED tests **TS Basis-only** — no carry, no trend, no
   weights. Nothing tunable enters the final read.
3. **Construction frozen.** `TS_BASIS_PHASE0_PRE_REGISTRATION.md` §3 construction SHA-256
   unchanged; declared sign = **+1**; `governance/rfa/declarations/ts_basis.py` frozen.

---

## 2. The one-shot rule (non-negotiable)

- The SEALED read is run **exactly once.** No re-run, no second look, no parameter change
  after seeing it — for any reason.
- The run is **snapshotted and logged** (inputs, code SHA, timestamp, outputs) before
  results are interpreted.
- No result from SEALED may feed back into construction, sign, weights, or fees.

---

## 3. What the read reports (script-generated, no hand-edited numbers)

On SEALED 2023-01 → 2026-07, for the frozen TS Basis construct:

**Portfolio (pinned): top-minus-bottom quintile, equal-weight.**

- Mean rank-IC (positive-sign, one-sided in the pre-committed direction).
- Net long/short spread under the §5 fee model, annualized, gross and net.
- Realized turnover and fee drag (bp/yr).
- Sign confirmation vs the +1 declaration.

Output: `docs/reports/TS_BASIS_SEALED_REPORT.md`.

---

## 4. Acceptance (pre-committed)

**PASS** (both required):
- Positive-sign rank-IC significant at **α = 0.05, one-sided**, and
- Net long/short spread **> 0** under fees.

**PASS → TS Basis is a validated alpha** across discovery (TRAIN) + two out-of-sample
windows (HOLDOUT, SEALED). The research phase closes.

**FAIL** (sign flips, insignificant, or net ≤ 0) → the effect did not survive the true
holdout. TS Basis is dead; there is no v2.

---

## 5. Relationship to cross-sectional carry SEALED

The cross-sectional carry SEALED read was one-shot and consumed the 2023–2026 window.
TS Basis is a different signal from the same underlying data. The carry SEALED read
confirms the carry sign on holdout — it does not confirm or deny TS Basis. These are
separate hypotheses.

Using the same SEALED window for TS Basis is a second spend on the same data. This is
explicitly noted: the window is not "clean" in the sense of being untouched by any
analysis. However, the carry SEALED read tested a different construction (cross-sectional
rank after beta/sector neutralization), not the TS Basis signal (time-series z-score).
The operator accepts this as a second read on the same window for a different hypothesis.

---

## 6. Freeze

To be frozen on operator approval. SHA-256 over this file.
