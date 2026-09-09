# Carry — SEALED Read Protocol (DRAFT)

**Status:** DRAFT. To be **FROZEN** (SHA-256) before the read. Governs the **one-shot** SEALED
confirmation of the Carry sleeve (positive sign) — the final gate mandated by
`CARRY_V2_PRE_REGISTRATION.md` §4.3.
**Window:** SEALED **2023-01-01 → 2026-07-20** (~42 monthly formations). Untouched to date.
**What is being tested:** **Carry-only**, positive sign. Not the composite (see §4).

---

## 1. Preconditions — ALL must pass before the SEALED read is authorized

The SEALED window is a single, unrepeatable resource. It is not opened until:

1. **Net-of-fee gate (PASS required).** Carry's net long/short spread (top-minus-bottom
   quintile, or z-weighted) must be **> 0, annualized, after the §8 futures fee model**, on
   **both TRAIN and HOLDOUT**. IC significance is predictive strength; this gate is money. If
   net ≤ 0 on either window, **STOP — Carry is not tradeable and SEALED is not run**, regardless
   of IC. *(Computed by the DeepSeek net-spread task; result recorded in
   `CARRY_NET_SPREAD_REPORT.md`.)*
2. **Combination frozen.** SEALED tests **Carry-only** (§4). No Trend, no weights — nothing
   tunable enters the final read.
3. **Construction frozen.** Carry-v2 §3 construction (= v1 §3–§8) SHA-256 unchanged; declared
   sign = **+1**; `governance/rfa/declarations/carry.py` frozen.

---

## 2. The one-shot rule (non-negotiable)

- The SEALED read is run **exactly once.** No re-run, no second look, no parameter change after
  seeing it — for any reason.
- The run is **snapshotted and logged** (inputs, code SHA, timestamp, outputs) before results
  are interpreted, so the read is reconstructible.
- No result from SEALED may feed back into construction, sign, weights, or fees. Discovering a
  "fix" after the read is the post-hoc reasoning the whole protocol exists to prevent.

---

## 3. What the read reports (script-generated, no hand-edited numbers)

On SEALED 2023-01 → 2026-07, for the frozen Carry-only construct:

**Portfolio (pinned): top-minus-bottom quintile, equal-weight.** This is the conservative base
case and the construction the acceptance gate (§5) is evaluated on. The **z-weighted** variant
is reported only as a secondary, optimistic reference — it concentrates in extreme-z (often
thin) names where the 5 bp slippage assumption is generous, so it must not be the gate. Pinning
this now removes the last degree of freedom; choosing quintile-vs-z *after* the read would be
post-hoc selection.

- Mean rank-IC (positive-sign, one-sided in the pre-committed direction), AC₁-corrected t and p.
- Net long/short spread under the §8 fee model — **STT tier 0.0200%** applies for 2024-10
  onward, 0.0125% for 2023-04 → 2024-09 (both inside SEALED) — annualized, gross and net.
- Realized turnover and fee drag (bp/yr).
- Sign confirmation vs the +1 declaration.

Output: `docs/reports/CARRY_SEALED_REPORT.md`.

---

## 4. Why Carry-only, and where Trend goes

Carry clears power standalone (IR 0.589; projected 0.982 at n\*=42) and the equal-weight
Carry+Trend composite IR (0.566) is **below** Carry alone — Trend does not raise the number.
Testing a combination on the SEALED window would (a) spend Carry's one clean confirmation on an
unresolved weighting question and (b) introduce a tunable into the final gate. Neither is
acceptable. **Therefore SEALED validates Carry-only.**

Trend's only demonstrated value is its **−0.246 correlation** with Carry, i.e. potential
**drawdown / regime-risk reduction**, not IR. That is a legitimate but **separate** question,
evaluated on **TRAIN + HOLDOUT drawdowns** — it does **not** consume the SEALED window. Decide
the Carry+Trend overlay *after* SEALED, as a risk study, if at all.

---

## 5. Acceptance (pre-committed)

**PASS** (both required):
- Positive-sign rank-IC significant at **α = 0.05, one-sided** (the sign is already
  HOLDOUT-confirmed under the m=2 floor, so SEALED is straight corroboration of an established
  effect, not the sole evidence), and
- Net long/short spread **> 0** under fees.

**PASS → Carry is a validated alpha** across discovery (TRAIN) + two out-of-sample windows
(HOLDOUT, SEALED). The research phase closes; work moves to implementation design (sizing via
`NseMarginEngine`, execution, risk limits). **No further sleeve hunting.**

**FAIL** (sign flips, insignificant, or net ≤ 0) → the effect did not survive the true holdout.
**Carry is dead; there is no v3** — the sign-discovery and out-of-sample windows are exhausted.
An honest terminal result, reported as-is.

---

## 6. Freeze

**FROZEN 2026-07-23.** SHA-256: `459411ab20374f07dbe531519724574f9625e784d947511885fbb7d92b7874ba`

On approval: SHA-256 over this file; §1 (preconditions), §2 (one-shot rule), §4 (Carry-only),
§5 (acceptance) immutable. The read may be run only after §1 all-pass and this freeze.
