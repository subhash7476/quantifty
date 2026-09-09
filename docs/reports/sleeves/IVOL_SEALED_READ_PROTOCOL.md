# IVOL — SEALED Read Protocol

**Status:** To be **FROZEN** (SHA-256) before the read. Governs the **one-shot** SEALED
confirmation of the IVOL sleeve (negative sign) — the final gate mandated by
`IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 5.
**Window:** SEALED **2023-01-01 → 2026-07-20** (~42 monthly formations). Untouched to date.
**What is being tested:** **IVOL-only**, negative sign (long low-vol, short high-vol). Not the
composite (the composite cleared gate 4; SEALED validates the standalone sleeve, exactly as
Carry's SEALED validated Carry-only — `CARRY_SEALED_READ_PROTOCOL.md` §4).

---

## 1. Preconditions — ALL must pass before the SEALED read is authorized

The SEALED window is a single, unrepeatable resource. It is not opened until:

1. **Net-of-fee gate (PASS required on BOTH prior windows).** IVOL's net long/short spread
   must be **> 0, annualized, after the §8 futures fee model**, on both TRAIN and HOLDOUT.
   - TRAIN (2017-02 → 2020-12): net **+5.96%** (`IVOL_TRAIN_REPORT.md`). PASS.
   - HOLDOUT (2021-01 → 2022-12): net **+2.16%** (`IVOL_HOLDOUT_REPORT.md`). PASS.
2. **Combination frozen.** SEALED tests **IVOL-only**. No composite weighting, no Carry —
   nothing tunable enters the final read. (The composite cleared gate 4 separately;
   re-introducing it here would spend IVOL's one clean confirmation on an unresolved
   weighting question.)
3. **Construction frozen.** `IVOL_PHASE0_PRE_REGISTRATION.md` §3–§4 SHA-256 unchanged;
   declared sign = **−1** (high vol → low return); `governance/rfa/declarations/ivol.py`
   frozen (SHA `d7ebcbcc…`).

---

## 2. The one-shot rule (non-negotiable)

- The SEALED read is run **exactly once.** No re-run, no second look, no parameter change
  after seeing it — for any reason.
- The run is **snapshotted and logged** (inputs, code SHA, timestamp, outputs) before results
  are interpreted, so the read is reconstructible.
- No result from SEALED may feed back into construction, sign, weights, or fees. Discovering
  a "fix" after the read is the post-hoc reasoning the whole protocol exists to prevent.

---

## 3. What the read reports (script-generated, no hand-edited numbers)

On SEALED 2023-01 → 2026-07, for the frozen IVOL-only construct:

**Portfolio (pinned): top-minus-bottom quintile, equal-weight.** Long the **bottom** quintile
(low z_ivol = low vol), short the **top** quintile (high z_ivol = high vol). This is the
conservative base case and the construction the acceptance gate (§5) is evaluated on. The
z-weighted variant is reported only as a secondary reference — it concentrates in extreme-z
names where the slippage assumption is generous, so it must not be the gate. Pinning this now
removes the last degree of freedom; choosing quintile-vs-z *after* the read would be post-hoc
selection.

- Mean rank-IC (negative-sign, one-sided in the pre-committed direction), AC₁-corrected t and p.
- Net long/short spread under the §8 fee model — **STT tier 0.0200%** applies 2024-10 onward,
  0.0125% for 2023-04 → 2024-09, 0.0100% pre-2023-04 (all inside SEALED) — annualized, gross
  and net.
- Realized turnover and fee drag (bp/yr) with full component breakdown.
- Sign confirmation vs the −1 declaration.

Output: `docs/reports/IVOL_SEALED_REPORT.md` + `docs/reports/IVOL_SEALED_SNAPSHOT.json`.

---

## 4. Why IVOL-only, and where the composite goes

IVOL cleared gate 4 (composite power 0.9854 with Carry). But the composite is a *combination*
of two sleeves; spending IVOL's one clean SEALED confirmation on a weighted combination would
(a) entangle the result with Carry's already-confirmed read and (b) introduce a tunable
(weight choice) into the final gate. **Therefore SEALED validates IVOL-only**, exactly as
Carry's SEALED validated Carry-only. The composite's standalone validity rests on each sleeve
clearing its own TRAIN/HOLDOUT/SEALED — IVOL's SEALED is that confirmation.

---

## 5. Acceptance (pre-committed)

**PASS** (both required):
- Negative-sign rank-IC significant at **α = 0.05, one-sided** in the negative direction
  (the sign is HOLDOUT-confirmed, so SEALED is corroboration of an established effect), and
- Net long/short spread **> 0** under fees.

**PASS → IVOL is a validated alpha** across discovery (TRAIN) + two out-of-sample windows
(HOLDOUT, SEALED). Combined with Carry (already SEALED-validated) and the gate-4 composite
clearance, the **2-sleeve engine is research-complete.** Work moves to implementation design
(sizing via `NseMarginEngine`, execution, risk limits).

**FAIL** (sign flips, insignificant, or net ≤ 0) → the effect did not survive the true
holdout. **IVOL is dead; the sealed window is spent.** An honest terminal result, reported
as-is.

---

## 6. Freeze

On approval: SHA-256 over this file; §1 (preconditions), §2 (one-shot rule), §4 (IVOL-only),
§5 (acceptance) immutable. The read may be run only after §1 all-pass and this freeze.
