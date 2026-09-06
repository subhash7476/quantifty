# PSB-2 Phase 3 — §8 Selection Report

**Script-generated** — `scripts/psb2/run_phase3.py`. Deterministic run (§10). Code commit `abfdbc3`.

| Field | Value |
|---|---|
| Code commit | `abfdbc3` |
| Fence | fenced MAX=2022-12-30 < cutoff=2022-12-31 < unfenced MAX=2026-07-09 |
| n* fortnightly / monthly | 84 / 42 |
| Bonferroni m | 3 |
| Eligible set | {C2} |

## §8 Eligibility (declared window)

| Candidate | (i) Mean IC > 0 | (ii) Net spread > 0 | (iii) Power ≥ 0.80 | Eligible |
|---|---|---|---|---|
| C2 | 0.034892 (PASS) | 0.045733 (PASS) | 0.9198 (PASS) | **YES** |
| C3 | 0.008312 (PASS) | -0.011015 (FAIL) | 0.1816 (FAIL) | **NO** |
| C4 | 0.046550 (PASS) | 0.028667 (PASS) | 0.4110 (FAIL) | **NO** |

**Eligible set:** `{C2}`.
C3 fails (ii) and (iii); C4 fails (iii). Both are dropped by rule (§7.3: *'A candidate below the hurdle is dropped by rule, whatever its dev IC.'*).

## §8 Power ranking (eligible, declared window)

| Rank | Candidate | Power |
|---|---|---|
| 1 | C2 | 0.9198 |

**Single eligible candidate** — the ranking is the singleton `[C2]`. No contest to adjudicate.

## §8 Declared-window deflated-p (eligible only)

Deflation: `min(1, 3 · p)`. Declared-window p-values from candidate reports.

| Rank | Candidate | One-sided p | Deflated p (m=3) |
|---|---|---|---|
| 1 | C2 | 7.994592e-03 | 0.023984 |

## §8 Cross-ranking discrepancy

Eligible set: `{C2}`.
**The discrepancy clause cannot engage.** §8: *'If the winner differs across these rankings, all are presented and the operator decides.'* Both the power ranking and the deflated-p ranking are computed over the same singleton eligible set. They cannot differ — no cross-ranking discrepancy is structurally possible in this battery. The clause was evaluated and found inapplicable.

## §8 Evidence floor

**Winner (highest-power eligible): C2**

| Field | Value |
|---|---|
| Declared-window one-sided p | 7.994592e-03 |
| Bonferroni m | 3 |
| Deflated p = min(1, 3 × 7.994592e-03) | 0.023984 |
| Threshold | < 0.05 |
| Floor | **PASS** |

**C2 clears the evidence floor.** Deflated p = 0.023984 < 0.05.

**Outcome: C2 recommended for promotion.**

*No-cascade branch implemented and stated (§8). If the highest-power eligible candidate (C2) had failed the floor, the battery would report 'no winner recommended' — it would not fall through to C3 or C4. 'No winner recommended' was a live outcome that did not obtain.*

## §8 Tie-break (0.02 band)

**Not engaged.** Single eligible candidate — projected powers cannot be within 0.02 of each other by definition.

## §8 Common robustness sub-window (2020-09-04 → 2022-12-31)

**Non-gating.** Reported for operator disclosure only. Eligibility and ranking are declared-window only.

| Candidate | Sub-window n | Mean IC | SD IC | Note |
|---|---|---|---|---|
| C2 | 55 | 0.034892 | 0.104033 | Declared window IS the sub-window |
| C3 | 55 | 0.008312 | 0.102717 | Declared window IS the sub-window |
| C4 | 27 | -0.013710 | 0.187067 | C4's 12-month lookback reaches before 2020-09-04; formations are restricted, lookback history is not |

## §6 Disclosures (non-gating)

### 1. §7 AC₁ exposure did not materialize

All three AC₁ values are negative: C2 = -0.1818, C3 = -0.0328, C4 = -0.0244. None exceeds the one-sided 0.1 trigger. C2's power (0.9198) is not flattered by positive autocorrelation. The largest disclosed threat to a fortnightly candidate — inflated simple-t from overlapping formations — is absent in this data.

### 2. C2's turnover exceeded the design estimate and cleared anyway

C2 turnover: 0.2701 (design ~0.15); fee drag: 270.3 bp/yr (design ~78). Gross top-quintile spread: 0.070309; net: 0.045733. The candidate clears fees by a margin that survives the higher-than-expected turnover. No parameter was tuned toward the design estimate.

### 3. C2's SD rests on 2.3 years of data

C2 dev window: 2020-09-04 → 2022-12-31 (55 formations). SD_IC = 0.104033. This is the full available delivery-data span (deliv_pct begins 2020-01-01; the 252-day baseline ending t−21 with ≥ 150 non-NULL pushes the earliest feasible formation to 2020-09-04). Power depends on SD. The successor pre-registration (§12) must pin its own view on this estimate.

### 4. C4's staggered design worked and was not enough

C4: best mean IC (0.046550) and best fee structure (35.2 bp/yr, turnover 0.0776) in the battery. Dropped by rule at power 0.4110 < 0.8 — SD_IC = 0.208949 over 131 formations leaves signal-to-noise ratio too low at n* = 42. This is PSB-1's C5 story repeating: the construct clears fees but the sample is too noisy to project 0.80 power.

### 5. C3 confirms the program's central constraint a third time

C3 gross spread: 0.031002; fee drag: 444.7 bp/yr; net: -0.011015. PSB-1's C3 (weekly delivery z) was killed by weekly fees. PSB-2's C3 (fortnightly delivery-conditioned reversal) is killed by turnover (0.4683) and the resulting fee drag. Three constructs across two batteries — the fee constraint remains the binding limit on delivery-based signals at sub-monthly cadence.

## §7 What 'recommended' means

**C2 is a recommendation, not a promotion.** §12 binds: the winner authorizes nothing except the right to *propose* a successor pre-registration that would pin its own α, execution conventions, and sealed-read mechanics, and would disclose the prior CSMP momentum read as prior exposure (D2).

No sealed read has been consumed here. No strategy code exists. No allocation is authorized.
Promotion happens only through a new, full pre-registration program ratified by the operator — never in this battery.

## §10 Determinism compliance

Digest (sha256 of full report): `fad88aac14decee3`

This report is 100% script-generated. No hand-edited numbers. Re-running the identical code against the identical dev-fenced store yields byte-identical output.

## Predictions verified

1. **All three candidate digests byte-identical** (D3 label fix): C2 `41e3732909f9bf8d`, C3 `ff780cb8de509a98`, C4 `b3569ade45003899` — **PASS** (commit stamps moved, expected — reported per `21cb09f` finding).
2. **Eligible set = {C2}**: C3 fails (ii)/(iii), C4 fails (iii). Neither ranked. — **PASS**
3. **C2 deflated p = min(1, 3 × 7.994592e-03) = 0.023984 < 0.05** → floor PASS → C2 recommended. — **PASS**
4. **Both rankings are [C2]; discrepancy clause cannot engage; tie-break not engaged.** — **PASS**
5. **C4 sub-window: grid 28 monthly dates; realized n = 27** (expected 27-28). — **PASS**
6. **C4 sub-window lookback untruncated** — n = 27 (not ~16). — **PASS**
7. **Selection report restates candidate metrics, does not recompute them differently** — verified by comparison with committed candidate reports. — **PASS**

