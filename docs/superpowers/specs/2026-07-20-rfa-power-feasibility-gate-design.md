# RFA — Power-Feasibility Pre-Check Gate (Design)

**Date:** 2026-07-20
**Status:** Design approved, pending implementation plan
**Origin:** CLAUDE.md § SFB-1/F1 — "Any future construct ... must clear a **power-feasibility
pre-check before any construct code is written**." This document specifies that gate.

---

## 1. Purpose and scope

The **Research Feasibility Assessment (RFA)** answers exactly one question:

> Given the formations actually available and an independently defended effect-size band, can
> this construct reach power 0.80 even under assumptions more generous than anyone believes?

If no → **ABANDON**. The gate touches no market data, so it costs nothing and runs *before* a
line of construct code exists.

### Scope — demonstrability only

The RFA covers the power/CI leg and nothing else. It does **not** evaluate fees, MaxDD,
turnover, or economic significance.

- **ABANDON is dispositive.** The construct cannot be demonstrated; do not build it.
- **PROCEED means *not provably infeasible*** — never "feasible", never "authorized".

A candidate can clear the RFA and still die on delivery-equity STT, exactly as PSB-1's C1–C4
did. Presenting PROCEED as broader clearance would rebuild F1's own failure — a decision rule
presented as complete that is not.

### Why this gate exists

The binding constraint in this repo's research history migrated. PSB-1 C1–C4 died on **fees**.
Once constructs were engineered to clear fees by construction (C5, C4, C2), every one died on
**demonstrability** instead — power 0.54, power 0.4110, and for C2 a compound fees-and-power
failure. F1 failed the same way in its own framework (bootstrap CI includes zero).

Demonstrability is sample-size × effect-size. For monthly cross-sectional equity both are
roughly fixed, and no better signal changes the arithmetic. That check is free. It was never
run. This gate runs it.

---

## 2. Governance model

### 2.1 Binding input: independent ranges on δ and SD

The operator declares and defends **two independent bands**:

- `delta_lo` / `delta_hi` — expected effect size
- `sd_lo` / `sd_hi` — expected dispersion of that effect

The gate forms the standardized effect internally.

**Why two bands rather than one ratio.** Power consumes `δ/SD`, so a single standardized band
is mathematically sufficient. It is rejected on governance grounds: two very different research
hypotheses — a small edge with stable outcomes, and a large edge with volatile outcomes — can
produce the same ratio while representing fundamentally different beliefs. Collapsing them
hides both assumptions inside one derived quantity that a reviewer cannot challenge
component-wise.

**This buys review surface, not accuracy.** Two declarations with equal `δ/SD` produce
identical verdicts. The two-band form is not a more precise calculation and must not be
described as one.

**The denominator leak this closes.** If only δ were defended and SD came from anywhere else,
the prior-exposed historical reads would set half the calculation while the report appeared
independently derived. Requiring SD to be declared and defended closes that path.

### 2.2 Provenance — required

Each band carries a mandatory non-empty provenance statement: published literature,
first-principles reasoning, external industry evidence, or another independently defensible
source.

**Historical PSB/SFB results must not define these ranges.** They are prior-exposed
observations. They are recorded separately as context (§5.2) and carry no weight in the
binding inputs.

A `prior_exposure` statement is also required — the operator states what they have already
seen. This, plus the written frozen defense, is the load-bearing control against anchoring.

**Ordering does not confer independence.** Sealing the declaration before generating the
context appendix does not prevent anchoring — the operator has already read those numbers in
CLAUDE.md. No claim of independence-by-ordering is made anywhere in this design. The control
is the written, defended, frozen argument plus explicit disclosure. Nothing else.

### 2.3 Immutability

Once the RFA is approved, `delta_*` and `sd_*` are **frozen project inputs**. They cannot be
revised in response to intermediate results, implementation discoveries, or disappointing
early findings. This is what makes the RFA a prospective checkpoint rather than a post-hoc
justification.

Freeze is enforced by **SHA-256 over the entire declaration file's bytes**, recorded in the
report.

> The digest deliberately covers the whole file. PSB-2's `PSB2_SELECTION_REPORT.md` §10 digest
> covered only the body through §7, leaving its predictions section outside the seal. That
> mistake is not repeated.

---

## 3. Components

### 3.1 Declaration — `governance/rfa/declarations/<NAME>.py`

A governance namespace, deliberately outside `scripts/`. Declarations are governance records
that happen to be written in Python; filing them with executable code invites treating them as
ordinary tunable inputs.

One module per candidate, exposing a single `Declaration`:

| Field | Purpose |
|---|---|
| `name` | Candidate identifier |
| `methodology_version` | RFA methodology version this declaration targets (§3.4) |
| `delta_lo`, `delta_hi` | Defended effect band |
| `sd_lo`, `sd_hi` | Defended dispersion band |
| `delta_provenance` | Prose, required, non-empty |
| `sd_provenance` | Prose, required, non-empty |
| `prior_exposure` | Prose, required — what the operator has already seen |
| `n_available` | Raw formation count, **no autocorrelation haircut** |
| `cadence`, `window` | How `n_available` was derived |
| `test_type` | One- or two-sided; changes the answer, so declared not assumed — **no default; omission is a validation failure** |
| `metric` | `rank_ic` or `per_trade_pnl` — documentation only |

Python is already this repo's config language (`POWER_HURDLE`, `C2_DEV_LO`). Provenance lives
in triple-quoted strings and is reproduced verbatim into the report.

Empty or missing provenance is a hard validation failure, not a warning.

### 3.2 Power core — `scripts/rfa/power.py`

Noncentral-t, the same formulation as `scripts/psb1/screening_harness.py:812`. Two functions:

- power at (δ, SD, n)
- its inversion — n required for a target power

**One core, both frameworks.** Power is `standardized_effect × √n` regardless of framework.
For an IC battery the standardized effect is `mean_IC / SD_IC`; for an F1-shaped portfolio
battery it is `mean_trade_PnL / SD_trade_PnL`, a Sharpe-per-trade. Both feed the same core; no
branching on framework. F1 needed block-bootstrap for its *in-battery* test because ≤10 names
break IID-t — but the RFA is not the battery's test, it is a free feasibility upper bound.

Written fresh rather than imported from `psb1`, so a new gate takes no dependency on a closed
battery's module.

### 3.3 Verdict — `scripts/rfa/gate.py`

Evaluate at the **optimistic corner** `(delta_hi, sd_lo, n_available)`. Power is monotone in
all three (↑δ, ↓SD, ↑n), so the corner is a single evaluation — no grid search.

- `max_power < 0.80` → **ABANDON**
- otherwise → **PROCEED (not provably infeasible)**

**The corner is intentionally unrealistic.** Declared independently, `(delta_hi, sd_lo)` may
describe a large edge with unusually stable outcomes — the least plausible combination in
practice and the most generous to the construct. This is deliberate and asymmetric in the safe
direction: it maximizes the burden of proof for ABANDON, so a firing gate is unarguable
("cannot clear 0.80 even at a corner more favorable than anything you believe"), while
correspondingly weakening PROCEED to its stated meaning of *not provably infeasible*.

`n_available` is used raw, with no autocorrelation haircut, for the same reason — the AC
discount belongs to the real battery; here the most generous n is wanted.

The report also reports `n_required` at the corner and at the central and pessimistic points —
the actionable figure, e.g. "needs 350 formations; you have 130."

### 3.4 Methodology version

`METHODOLOGY_VERSION` is a module constant in `scripts/rfa/gate.py`, stamped into every
generated report alongside the declaration digest.

A declaration targets a methodology version. When the methodology evolves, old reports remain
interpretable — a reader can tell which rules produced a given verdict without archaeology.

A mismatch between a declaration's `methodology_version` and the running gate is a **hard
failure — the gate refuses to emit a verdict.** A frozen declaration was defended against a
specific set of rules; silently re-evaluating it under different ones would void the
pre-registration. Clearing a mismatch requires explicit operator re-approval of the
declaration against the current version, which is itself a governance act (§2.3).

---

## 4. Report — `docs/reports/<NAME>_RFA.md`

Script-generated. No hand-edited numbers, consistent with every PSB/SFB artifact in this repo.

Contents:

1. Verdict — ABANDON or PROCEED, computed
2. Methodology version + declaration SHA-256
3. Corner values and the band table
4. `n_required` at corner / central / pessimistic
5. Provenance and prior-exposure statements, verbatim
6. The §1 scope caveat and the §3.3 corner rationale, in the report body
7. Non-binding context appendix (§5.2)

---

## 5. Validation

### 5.1 Tests — `tests/rfa/`

| Test | Guards against |
|---|---|
| Core reproduces IC 0.03 / SD 0.2 / two-sided / 80% → n in [340, 360] | Core arithmetic wrong |
| Bootstrap cross-check against `psb1._power` (§5.3) | Divergence from known-good implementation |
| ABANDON fires on constructed sub-hurdle inputs | Gate never fires |
| PROCEED fires on constructed above-hurdle inputs | Gate always fires |
| **Verdict flips when inputs flip** | **F1's hardcoded-PASS sin — verdict must be computed, never a string** |
| Digest covers full file bytes | PSB-2's partial-seal defect |
| Empty provenance rejected | Governance bypass |

**Caveat on the ~350 target.** That figure is CLAUDE.md's own and is flagged there as strongly
indicated rather than proven. The test confirms this core matches the documented arithmetic —
it is not independent validation that the arithmetic is right.

### 5.2 Retrospective check — non-binding appendix

CLAUDE.md claims this gate "would have saved the back half of C5, C4, C2, and F1." That claim
is tested, not asserted: the gate is run against those four using their recorded numbers, in a
clearly-labelled non-binding appendix.

**If it does not fire on all four, the CLAUDE.md claim is wrong and will be reported as such.**
The gate will not be tuned until it agrees.

Known risk: **F1 has no rank IC.** Its per-trade PnL mean/SD must be recovered from the
screen's outputs. If they are not recoverable, F1 is reported as **untestable** — no
plausible-looking number will be reconstructed.

### 5.3 PSB-1 comparison — bootstrap only

The cross-check against `psb1._power` is a **one-time bootstrap certification** against a
known-good implementation. Once it passes, **RFA is the canonical implementation.** A future
divergence resolves in RFA's favor; `psb1` is a frozen closed-battery artifact and is not
authoritative for new work.

---

## 6. Explicitly out of scope

- Fee modelling, MaxDD, turnover, economic significance
- Any read of market data at gate time
- Any authorization to build — PROCEED is a floor, not a mandate
- Retrofitting the gate onto closed batteries (PSB-1, PSB-2, SFB-1/F1) as anything other than
  the §5.2 non-binding retrospective

---

## 7. Open items for the implementation plan

- Exact `Declaration` dataclass shape and validation error messages
- Whether `n_required` inversion is closed-form or a numerical solve

F1's per-trade PnL recoverability is **not** an open item — §5.2 pins the outcome either way
(recovered, or reported untestable). It is a task for the plan, not a decision.
