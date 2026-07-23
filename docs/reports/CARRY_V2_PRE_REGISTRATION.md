# Carry Sleeve v2 — Re-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256). Amends **only the sign** of
`CARRY_PHASE0_PRE_REGISTRATION.md` (v1); every construction detail is inherited unchanged.
**Supersedes:** v1's sign, which was falsified. v1 remains on record as CLOSED / FAIL.

---

## 0. Why v2 exists (the honest origin)

v1 registered **short high residual carry** (negative IC). Its TRAIN read (2016-03 → 2020-12)
returned rank-IC **+0.041, p = 1.8e-4** — highly significant, with the sign **opposite** to
what v1 declared. Per v1 §1's falsification clause ("if realized IC is significant with the
opposite sign, the hypothesis is falsified, not re-labelled"), **v1 is closed as FAIL.**

A significant wrong-sign result is not a null — it is evidence of a **real** cross-sectional
carry effect in the direction v1 bet against. v2 registers that direction (the canonical carry
direction) and confirms it **only on windows v1 did not spend.**

---

## 1. Hypothesis (positive sign — frozen)

Cross-sectional residual futures carry predicts forward returns **positively**: **long high
residual carry, short low.** Sign declared and unflippable.

**Defended ex-ante, not from the TRAIN result:** this is the **canonical carry direction** —
Koijen–Moskowitz–Pedersen–Vrugt (2018, *Carry*) establish across asset classes (equities
included) that high carry predicts high returns; long-high / short-low is *the* carry
portfolio. It is the *more standard* prior than v1's contrarian mean-reversion reading. A
reasonable researcher would have registered this sign first; registering the contrarian sign
was the error being corrected.

---

## 2. Prior exposure — the discipline core (mandatory)

**v1's TRAIN window has been seen.** The positive sign is therefore **discovered-on-TRAIN, not
predicted.** Three consequences, all binding:

1. **TRAIN (2016-03 → 2020-12) carries ZERO confirmatory weight for v2 and is NOT re-read.**
   It is burned for the Carry sign. This is the price of the v1 sign error, paid honestly.
2. **Confirmation comes only from windows v1 never spent:** HOLDOUT (2021–22) then SEALED
   (2023–26). Both remain clean.
3. **Multiplicity:** Carry has now been tested at sign(−) [v1] and sign(+) [v2] → **m = 2.**
   v2's evidence floor deflates accordingly: significance at **Bonferroni α = 0.025**, not 0.05.

---

## 3. Construction — UNCHANGED from v1 (frozen by reference)

Basis formula, dividend adjustment, common-financing demean, winsorization, cross-sectional
z-score, roll T−3, **beta + sector neutralization**, monthly cadence, ADV floor (₹5 cr), κ cap
(10% of 20-day ADV), 0.25σ no-trade band, and the era-accurate futures fee model are inherited
**verbatim** from `CARRY_PHASE0_PRE_REGISTRATION.md` §2–§8. **The position-mapping sign is the
ONLY parameter that changes.** No construction value may be touched — the sign is the single
degree of freedom, and that is what keeps v2 an out-of-sample confirmation rather than a refit.

---

## 4. Acceptance (revised for burned TRAIN)

1. **HOLDOUT 2021–22 (~24 monthly formations):** rank-IC with the **positive** sign; net
   quintile spread > 0 under §8 fees; magnitude in the v1 band. Significance at **Bonferroni
   α = 0.025.** *Note: 24 formations is underpowered for a standalone 0.80 — HOLDOUT is a
   **sign + magnitude + net-of-cost persistence** gate, not a standalone power clearance. If the
   sign is negative or net ≤ 0, Carry is dead.*
2. **Composite:** if HOLDOUT persists, Carry⁺ feeds the realized composite; **0.80 binds on the
   composite** (`CARRY_PHASE0_PRE_REGISTRATION.md` §13 rule 3), not on Carry alone.
3. **SEALED 2023–26:** one final read, reported whatever it shows.

---

## 5. Falsifiable predictions (before the HOLDOUT read)

1. HOLDOUT rank-IC is **positive-signed** and clears Bonferroni α = 0.025.
2. Net quintile spread > 0 under futures fees.
3. Magnitude is comparable to TRAIN (≈ +0.03 to +0.045).

If HOLDOUT is negative-signed or insignificant **and** net ≤ 0, the positive-carry hypothesis
is falsified and **Carry is terminally dead** — there is **no v3**, because you would be out of
clean sign-discovery windows (HOLDOUT spent, only SEALED left, and SEALED is not a
sign-discovery surface).

---

## 6. What would make v2 illegitimate (explicit guardrail)

Any one of these converts a disciplined OOS confirmation into a post-hoc rescue and is
**prohibited**: touching any construction parameter besides the sign; re-reading TRAIN as
confirmation; relaxing the m = 2 / α = 0.025 floor; spending SEALED before HOLDOUT; or running
HOLDOUT more than once.

---

## 7. Freeze

**FROZEN 2026-07-23.** SHA-256: `74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec`

On approval: SHA-256 over this file; record in `governance/rfa/declarations/carry.py`
(sign = +1). §1 (sign), §2 (prior-exposure rules), §3 (unchanged construction), §4 (acceptance)
are immutable. Any change starts a new pre-registration.
