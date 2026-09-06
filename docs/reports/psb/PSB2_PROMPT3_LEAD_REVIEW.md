# PSB-2 Prompt 3 — Lead Review (§8 Selection Report)

**Reviewer:** Claude (lead review role — implementation by DeepSeek V4)
**Artifact under review:** `docs/reports/PSB2_SELECTION_REPORT.md` @ `ed0dbb3`
**Runner:** `scripts/psb2/run_phase3.py` @ `abfdbc3`
**Date:** 2026-07-17

## Verdict

**ACCEPT.** The outcome — **C2 recommended for promotion** — is correct. Every §8 gating number was re-derived independently from the committed candidate reports and reproduces exactly. One MEDIUM finding on report-integrity labelling; the remainder are notes. **Nothing found touches the C2 recommendation.**

## What was verified (independently, not by reading the prediction table)

Method: the committed candidate reports (`PSB2_C{2,3,4}_REPORT.md`, reviewed and accepted in Phase 2) were treated as the source of truth. The selection report was checked to *restate* them, not recompute them differently. Statistics were re-derived from the reported mean/SD/n with `scipy`, not read back from the artifact.

### Provenance

| Check | Result |
|---|---|
| HEAD = `ed0dbb3`, report on disk | PASS |
| `ed0dbb3` diff = report file only (121 insertions, no code) | PASS |
| Report's code stamp `abfdbc3` accurate — no code drift between run and commit | PASS |

### Gating numbers — reconciled against candidate reports

Every value in the §8 eligibility table matches its candidate report to the last digit:

| Candidate | Mean IC | Net spread | Power | One-sided p | Digest |
|---|---|---|---|---|---|
| C2 | 0.034892 ✓ | 0.045733 ✓ | 0.9198 ✓ | 7.994592e-03 ✓ | `41e3732909f9bf8d` ✓ |
| C3 | 0.008312 ✓ | −0.011015 ✓ | 0.1816 ✓ | 2.754768e-01 ✓ | `ff780cb8de509a98` ✓ |
| C4 | 0.046550 ✓ | 0.028667 ✓ | 0.4110 ✓ | 5.968292e-03 ✓ | `b3569ade45003899` ✓ |

Prediction 7 ("restates, does not recompute") and Prediction 1 (digests unchanged) are therefore **independently confirmed true** — see MEDIUM-1 on how the report evidences them.

### Statistics — re-derived from scratch

| Candidate | ncp re-derived | ncp reported | Power re-derived | Power reported | p re-derived | p reported |
|---|---|---|---|---|---|---|
| C2 | 3.0739 | 3.0740 | **0.9198** | 0.9198 | 7.995276e-03 | 7.994592e-03 |
| C3 | 0.7417 | 0.7416 | **0.1816** | 0.1816 | 2.754653e-01 | 2.754768e-01 |
| C4 | 1.4438 | 1.4438 | **0.4110** | 0.4110 | 5.968744e-03 | 5.968292e-03 |

Powers reproduce to 4 dp; p-values to ~4 significant figures (residual is rounding of the 6-dp mean/SD inputs I fed back in, not a computational discrepancy). **The §7 power projection is sound.**

### §8 rule compliance (against frozen `PSB2_PROTOCOL.md` §8)

| §8 clause | Implementation | Verdict |
|---|---|---|
| Eligibility (i)∧(ii)∧(iii) | Computed from results, `POWER_HURDLE` from harness | PASS |
| Eligible set = {C2} | C3 fails (ii) net<0 **and** (iii); C4 fails (iii) | PASS |
| Winner = highest-power eligible | `ranked_power[0]` → C2 (0.9198) | PASS |
| Evidence floor: min(1, 3·p) < 0.05 | 3 × 7.994592e-03 = **0.023984 < 0.05** → PASS | PASS |
| Bonferroni m = 3 | `H.BONFERRONI_M = 3`, matches §8 pinned value | PASS |
| No cascade | Floor evaluated for `winner` only; no fall-through to C3/C4. Live-reachable branch | PASS |
| Discrepancy clause | Singleton eligible set — cannot engage. Correctly declared inapplicable | PASS |
| Tie-break (0.02 band) | Not engaged — singleton | PASS |
| Sub-window robustness, non-gating | Reported; correctly excluded from eligibility | PASS |

**Sub-window claim checked, not assumed:** `C2_DEV_LO = C3_DEV_LO = COMMON_SUBWINDOW_LO = 2020-09-04`. The report's "Declared window IS the sub-window" for C2/C3 is genuinely true, not a shortcut. C4's n = 27 over a 28-date monthly grid (last formation has no forward return) with lookback untruncated — consistent with restricting formations, not history.

---

## Findings

### MEDIUM-1 — The determinism digest does not cover the section that most needs covering

**The report's claims are true; its stated mechanism is overstated.** This is a labelling and scope defect, not a numerical one.

`run_phase3.py:363` computes the digest over `body` — the report as accumulated *up to that point*. The §10 section and the entire **"Predictions verified"** section are appended *after* the hash is taken. Confirmed empirically:

- sha256 of report body through §7 = `fad88aac14decee3` — **matches the stated digest**
- sha256 of the full report as committed = `d48380747fbca884` — **not the stated digest**

The report labels this "Digest (sha256 of **full report**)". It is not; it is the digest of the body through §7.

Why this matters more than a wording nit: predictions **1, 2, 4, and 7 are hardcoded literal `**PASS**` strings** (`run_phase3.py:378, 379, 381, 384`). Prediction 1 hardcodes the three candidate digests as literals — the script never reads or compares the candidate reports. Prediction 7 asserts "verified by comparison with committed candidate reports" — no such comparison executes. Only predictions 3, 5, and 6 are computed from live values.

So the one section that is *self-asserted rather than computed* is also the one section sitting **outside the integrity seal**, inside a report whose credibility rests entirely on "100% script-generated. No hand-edited numbers."

To be unambiguous: **I verified all four hardcoded predictions myself and they are true.** The finding is that the report's evidence for them is assertion, and its digest doesn't cover the assertion.

**Recommendation (operator's call, not a unilateral fix):**
- Minimum: relabel to "sha256 of report body (§1–§7)" and mark predictions 1/2/4/7 as operator-asserted rather than script-verified.
- Better: have the script read the three candidate reports and compare digests, making prediction 1 real.
- **Cost to weigh:** any change re-runs the script and *moves the digest*, and this is a terminal artifact. Whether a closing report earns another implement/review cycle for a labelling correction is genuinely the operator's decision, not mine. Documenting the limitation in the close-out is a legitimate alternative to fixing it.

### NOTE-1 — Latent counterfactual branches in the selection code

These would misbehave only under conditions the data forecloses. Per the repo's anti-over-engineering rule for one-time research paths, I flag them for the record and **do not recommend fixing them**:

- `run_phase3.py:142` — `deflated_p4` is computed and never used (dead).
- `run_phase3.py:153` — the deflated-p sort map hardcodes C3/C4 → `None`, then `or 999`. Had C3 or C4 been eligible, they would sort last regardless of their actual p, and `:.6f` on `None` at line 231 would raise `TypeError`. The deflated-p ranking is correct only for a singleton {C2}.
- `run_phase3.py:258` — `elif winner == "C2"` has no `else`. A C3 or C4 winner would emit an **empty** evidence-floor section and state no outcome at all — a silent omission rather than a crash.

Why these are notes, not defects: C2 is simultaneously the sole eligible candidate *and* the highest-power one (0.9198 vs 0.4110 vs 0.1816). `winner == "C2"` is forced by the data. No claim the report actually makes is falsified — the discrepancy clause genuinely is inapplicable for a singleton, and no-cascade genuinely is implemented on the live C2-fails-floor path.

### NOTE-2 — Hardcoded values inside interpolated narrative

Several disclosure sentences mix live f-string interpolation with hand-typed constants: `0.9198` (line 314), `55 formations` (329), `131 formations` (338), `turnover (0.4683)` (347). All are correct today. All would drift silently if the underlying result moved, in a report that claims no hand-edited numbers. Same fix-or-document calculus as MEDIUM-1.

### NOTE-3 — Hardcoded eligibility narrative

`run_phase3.py:199` emits the literal sentence "C3 fails (ii) and (iii); C4 fails (iii)" regardless of the computed `eligible3`/`eligible4` flags. It is correct today and it is contradicted by nothing, but it is a result claim not derived from the result.

---

## Assessment of the disclosures (§6)

The five disclosures are substantively honest and I found no spin:

1. **AC₁ exposure absent** — all three AC₁ negative (C2 −0.1818). Verified against candidate reports. C2's power is genuinely not flattered by overlap; this was the largest disclosed threat to a fortnightly candidate and it did not materialize. Correctly reported as a threat that *didn't* land rather than quietly dropped.
2. **C2 turnover missed its design estimate (0.2701 vs ~0.15) and cleared anyway** — disclosed rather than buried, with the explicit statement that no parameter was tuned toward the estimate. This is the right disclosure to volunteer.
3. **C2's SD rests on 2.3 years / 55 formations** — correctly flagged as the load-bearing weakness. Power is a function of SD, and SD here is estimated on the full available `deliv_pct` span with nothing held in reserve. Properly deferred to the successor pre-registration.
4. **C4's staggered design worked and wasn't enough** — best IC (0.046550) and best fee structure (35.2 bp/yr) in the battery, dropped by rule at power 0.4110. Correctly identified as PSB-1's C5 story repeating.
5. **C3 confirms the fee constraint a third time** — turnover 0.4683 → 444.7 bp/yr drag → net −0.011015. Consistent with the program's central finding.

Disclosure 3 is the one the operator should carry forward: **C2's recommendation is a power projection resting on a 55-observation SD estimate.** The battery is honest about this. The successor pre-registration must pin its own view on it (§12).

## Scope discipline (§12)

The report's "What 'recommended' means" section is correct and I would not soften it. No sealed read consumed, no strategy code, no allocation. C2 earns only the right to *propose* a successor pre-registration, which must pin its own α and execution conventions and disclose the prior CSMP momentum read as prior exposure (D2). Promotion never happens in this battery.

## Recommendation to the operator

**Accept Prompt 3 and C2 as recommended.** The §8 machinery executed to the frozen protocol, the arithmetic is independently reproduced, and the outcome is right.

Then decide MEDIUM-1: correct the digest label and the self-asserted predictions (costs a re-run and moves the digest on a terminal artifact), or record the limitation in the PSB-2 close-out and leave the artifact frozen as-is. I have not edited `run_phase3.py` — implementation is not this role's to perform.
