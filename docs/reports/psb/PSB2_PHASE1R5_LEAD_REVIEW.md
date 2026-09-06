# PSB-2 / PSB-1 — Prompt 1R5 Lead Review

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `0d155b9` → `cfbbcee`.
**Against:** `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 1R5, acceptance criteria 1–11.
**Predecessor:** `PSB2_PHASE1R4_LEAD_REVIEW.md` (HALT — B1…B7).
**Date:** 2026-07-17.

---

## Verdict: **ACCEPT** — with one corrective turn. **§11.1 and §11.2 are met.**

**B1…B7 are all genuinely closed.** I verified each against the code and the regenerated artifact rather than the close-out table, and this time the claims hold.

**The factor direction is correct, and it is now proven rather than asserted.** The regenerated report shows INDOSOLAR at **+65.1%** (was +16,406.7%) and CLCIND at **−88.1%** (was +1,094.7%) — script-generated, matching the reviewer's independent derivations of `+0.6507` and `−0.8805`. NEUEON and DELPHIFX held at **+110.2%** / **+31.4%**, confirming no factor was registered where none was due.

**One corrective turn, non-blocking on the numbers: the certification report's stamp is false.** It reads `Code commit 0d155b9`; the code that produced it is `cfbbcee`'s. See §C1. This is R2-8's exact class, and it has a one-commit precedent.

---

## The item that decides the round: §2's mutation is real

Prompt 1R5 said §1's assertion is only worth what its failure mode proves. **That proof exists:**

```
§2: Inverted factor mutation (0.01) produces +16505.6667, assertion FAILS
```

**This number is independent evidence the mutation ran.** `173.32 / (1.05 × 0.01) − 1 = 16505.6667` exactly. My prompt estimated the inverted boundary at *"≈ +1,650,571%"* — the true value is **+1,650,566.7%**. **The implementer's number is more precise than the source it would have been copied from**, which transcription cannot produce. §2 was executed, and it failed as predicted.

The mechanism is real code, not a claim:

```python
cc.execute("UPDATE adjustment_factors SET factor=? WHERE symbol=? AND ex_date=?",
           [0.01, "INDOSOLAR", date(2022, 6, 28)])
ICA.build_adjusted_view(cc)
...
try:
    _assert_boundaries(arm_b2, arm_b_excl2, "§2 (inverted)")
    print("  !! §2 assertion PASSED — check lacks teeth (expected FAIL)")
except AssertionError as e:
    print(f"  §2 assertion FAILED as expected: {e}")
```

**The 100× direction hazard raised in B4 is closed.** `"SPLIT"` with factor 100 resolves, in this store's convention, to price × 100 — the consolidation semantics we wanted. That was unknowable from `0d155b9`; it is now demonstrated.

---

## B1…B7 — closed

### B2 / B4 — the boundary returns are computed and asserted ✅

`ret` is no longer discarded. `_assert_boundaries` reads it straight off `arm_b.splices` and asserts against a pinned table:

```python
EXPECTED = {
    ("INDOSOLAR", date(2025, 6, 19)): (+0.6507, 0.001),
    ("CLCIND",    date(2026, 1, 30)): (-0.8805, 0.001),
    ("NEUEON",    date(2025, 12, 23)): (+1.1022, 0.001),
    ("DELPHIFX",  date(2020, 4, 21)): (+0.3136, 0.001),
}
```

Asserted on the scratch copy (§1), under mutation (§2), after register removal (§6), **and again on the real store after apply** (`_assert_boundaries(arm_b4, ..., "Real store")` with `assert len(halt4) == 0`). The post-apply re-verification was not something I asked for; it is the right instinct.

### B3 — the residuals are out of the register ✅

```diff
-        "factor 100 applied; 1473 missed sessions; boundary +65.1% after adjustment",
+        "factor 100 applied; 1473 missed sessions",
```

All four stripped. **The register now carries evidence; the report carries the number** — ISIN pair, rename record, capital event or its absence, missed sessions in the reason string; the boundary in the report's generated `Return` column. Exactly the split specified.

### B5 — `P3`'s literal is gone, replaced by a real check ✅

```python
ntl = con.execute(
    "SELECT COUNT(*) FROM adjustment_factors WHERE symbol='NTL' AND action_type='SPLIT'"
).fetchone()[0]
assert ntl == 0, f"NTL has {ntl} factor(s) — none expected (FV-only)"
```

A computed verdict that can fail, and **it lives in `ingest_corporate_actions.py`** — so it guards every rebuild, not just this runner's execution. Better placement than the prompt asked for.

### B6 — the factors are committed code ✅ (the most important fix in the round)

```python
RELISTING_FACTORS = [
    ("INDOSOLAR", date(2022, 6, 28), 100.0, "SPLIT", "nclt_order_2022_06_28_1to100_..."),
    ("SPENTEX",   date(2024, 1, 12), 100.0, "SPLIT", "nse_cml_72500_2024_01_12_1to100_..."),
]
```

`register_relisting_factors(con)` is wired into `main()` immediately after `apply_factor_overrides` — the DVL→DTIL precedent, followed rather than reinvented. **A store rebuild from committed code alone now reproduces both factors.** The trap B6 identified — rebuild drops the factors while `RE_LISTINGS` survives and silently excuses a resurrected +16,406.7% fabrication — is closed. **The rule holds: a disposition may only depend on state that is committed.**

### B7 — criterion 7 run, with hard assertions ✅

```python
assert removed_key in arm_b_excl3, f"Key {removed_key} not in register"
assert len(halt3) > 0, f"Expected >=1 halting splice after removing {removed_key}"
```

Register entry removed → splice HALTs → restored. **The ratchet is proven, not assumed.** Given that the register is the only thing between a splice and a pass, this was the most important check in the suite, and it now has the hardest assertions.

### B1 — the artifact exists ✅

`PSB1_SUBSTRATE_CERTIFICATION.md` is regenerated and committed:

| Arm | Result |
|---|---|
| **Arm A** intra-symbol CA-shape | PASS — 78 residue, 78 dispositioned, **0** undocumented |
| **Arm B** cross-symbol handoff | **PASS** — 4 splices, 4 dispositioned, **0** undocumented |
| **Arm C** prev_close identity | PASS — 0 violations |
| **Arm D** factor evidence | PASS — 1116 tested, 16 flagged, 16 dispositioned, **0** undocumented |

`**CERTIFICATION INCOMPLETE — HALT items above must be resolved.**` → `**SUBSTRATE CERTIFIED — the four-arm contract holds.**`

The Arm B table now carries post-factor returns and a Disposition column. Registering the two factors did not disturb Arms A/C/D, and the continuity invariant holds at 0 view-induced fabrications — the 4,761-row back-adjustment was clean.

---

## Corrective turn

### C1 — The certification report's stamp is false (R2-8's class, third occurrence)

```
**Script-generated** — `scripts/psb1/certify_substrate.py`. Code commit `0d155b9`.
```

**The code that produced this report is `cfbbcee`'s, not `0d155b9`'s.** The proof is in the report itself: its Disposition column shows the **stripped** reason strings, which exist only in `cfbbcee`. Check out `0d155b9`, re-run, and the column comes back reading *"boundary +65.1% after adjustment"*. **The report is not reproducible from the commit it names.**

This is a provenance defect in the artifact that certifies the substrate — and provenance is most of what a certification is worth. It is also cheap, with an established precedent: `c0dfb92` ("regenerate report with true commit stamp (R2-8)") and `0d155b9` ("regenerate report with true commit stamp (a6d1fb4)") are the same fix. **Regenerate stamped `cfbbcee`, commit.**

### C2 — §2's "lacks teeth" path warns instead of stopping

```python
    print("  !! §2 assertion PASSED — check lacks teeth (expected FAIL)")
```

If the inverted factor ever **stops** failing the boundary assertion, the runner prints a warning and **continues** — through §6, and on to applying factors to the real store. The standing rule is *"if the mutation cannot fail the check, stop and escalate."* **The warning should be a halt.**

Inert today: the mutation did fail, and correctly. But this is the guard on the guard, and a soft failure in that position is how the next round's tautology gets in.

### C3 — Minor, for the record

- **The NTL check is narrower than its message.** `WHERE symbol='NTL' AND action_type='SPLIT'` would not catch an NTL factor registered under a different `action_type`. The assertion says "none expected"; the query says "no SPLIT expected". Widen the query or narrow the message.
- **`0 undocumented (HALT)` reads oddly.** The `(HALT)` label is hardcoded in the f-string and prints even when the count is zero. Cosmetic; the summary row correctly says PASS.

---

## Acceptance criteria

| # | Criterion | Status |
|---|---|:--:|
| 1 | Boundary returns computed from `ret` and asserted | ✅ |
| 2 | Inverted factor fails the assertion; never reaches real store | ✅ |
| 3 | `RE_LISTINGS` carries evidence only | ✅ |
| 4 | `P3` literal gone; NTL asserted against the store | ✅ |
| 5 | Factors in `ingest_corporate_actions.py`; rebuild reproduces | ✅ |
| 6 | Criterion 7 run and reported | ✅ |
| 7 | Cert report regenerated and committed | ✅ |
| 8 | Arms A/C/D clean; continuity invariant 0 | ✅ |
| 9 | Predictions reproduced by script | ✅ |
| 10 | No hand-edited numbers | ✅ |
| 11 | No candidate score on real data; no §9 change | ✅ |

**Stamp accuracy (C1) is the one gap**, and it is bookkeeping rather than a criterion breach — criterion 7 asked for regeneration and commit, which happened.

## Phase 2 preconditions — status

| Precondition | Status |
|---|---|
| **§11.2** — dev-proof | ✅ **Met** (closed at `0d155b9`) |
| **§11.1** — Arm B reconciliation | ✅ **Met** — 4 splices, 4 dispositioned, 0 undocumented |
| Substrate certified | ✅ **SUBSTRATE CERTIFIED** — all four arms PASS |

**Phase 2 is authorized once C1 lands.** The stamp is one commit, and the certification report is the artifact every downstream candidate report will cite; it should be true before Prompt 2 quotes it. No number moves.

---

## Reviewer's note

**The difference between 1R4 and 1R5 is the spec, not the implementer.** 1R4 handed over four exact residuals labelled "predictions" and asked for them to be reproduced; they were transcribed into prose. 1R5 required the same four numbers to be *asserted* and then required the assertion **to be proven capable of failing** — and the same implementer produced a boundary check, a direction mutation, a ratchet test, and a post-apply re-verification I had not asked for.

**The number that settles it is `+16505.6667`.** It is more precise than the estimate in my own prompt. That is the signature of a value computed rather than copied, and it is the cleanest evidence in five rounds that a check was actually run.

**The pattern worth keeping:** when a prompt supplies the expected answer, the deliverable must be the **mutation**, not the assertion. An assertion against a published number proves nothing about whether it was observed; a mutation that must fail cannot be satisfied by transcription.
