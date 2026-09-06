# C2 Phase 0.5 — Turnover-Reduction Mini-Battery — FROZEN Pre-Registration

**Status:** FROZEN on operator ratification 2026-07-18. No parameter below may change once a run has touched dev data. A revision requires a new dated protocol, not an edit.
**Governing plan:** `docs/reports/C2_DEPLOYMENT_ROADMAP.md` (Phase 0). **Predecessor:** `C2_PHASE0_4_LEAD_REVIEW.md` — go/no-go ruled path (a): improve C2 on dev before spending the sealed read.
**Roles:** Claude writes this protocol + reviews deliverables; DeepSeek implements; operator ratifies. Promotion never happens inside the battery — clearing G0.5 earns only the *right to spend the sealed read* on the improved construct, not deployment.

---

## 1. Premise and why this exists

Phase 0.4 established (independently re-derived) that C2 survives falsification but projects **power 0.69 < 0.80** at n*=84 with **net spread 0.78%/yr**. The binding constraint is **fee+slippage drag** (gross 3.0% − ~2.2% drag = 0.78% net), driven by turnover 0.277 — not the signal. This mini-battery attempts to lift net spread and power above deployable/sealed-read hurdles **by reducing turnover only**, leaving the delivery-z score frozen, then confirms the winner on an untouched dev holdout before any sealed read is authorized.

**Prior-exposure disclosure (D2 discipline).** The analyst has seen the dev-wide C2 IC/SD (Phase 0.4). The mini-battery's integrity therefore rests **not** on analyst blindness but on: a variant slate pinned before any run, a single confirmation look at the holdout, m=3 deflation, and a terminal no-re-roll rule. This is disclosed, not hidden.

## 2. Fence and data split (PINNED)

- **Scored dev range:** ~2011-01 → 2022-12 (delivery-z needs a 252-day baseline; ~2010 formations produce no scores — the 260/311 fact from Phase 0.4).
- **TRAIN:** formation dates **2011-01-01 → 2018-12-31** — used for variant selection.
- **HOLDOUT:** formation dates **2019-01-01 → 2022-12-31** — used **once**, for confirmation only. Never used in selection.
- **SEALED:** 2023-01-01 → 2026-07-09 — **never read** in this phase. Fence proven each run (fenced MAX ≠ store MAX), as in Phase 0.4.

## 3. Frozen scoring

The C2 delivery-z score (`score_c2_psb2`) is **frozen unchanged** from the PSB-2 harness (fidelity tests `tests/psb2/test_fidelity.py` must be green before any run). Only rebalance mechanics vary, via existing `evaluate_candidate_psb2` parameters (`cadence`, `banded`, `exit_band`, `is_staggered`) — the same machinery C2/C3/C4 already use. No new scoring code.

## 4. Variant slate (m = 3, PINNED EXACTLY)

| ID | Cadence | Exit band | Hold | Mechanism |
|---|---|---|---|---|
| **V1** | monthly | 0.40 | single | halves rebalance frequency |
| **V2** | fortnightly | **0.60** | single | wider band → fewer names churn per period |
| **V3** | fortnightly | 0.40 | **staggered: 1/3 of book re-formed each fortnight, 3-period hold** | smooths turnover across sub-books |
| ref | fortnightly | 0.40 | single | **incumbent C2 — reference only, NOT counted in m** |

No variant outside this table may be run. m = 3.

## 5. Power convention (PINNED — the honest tension)

Power for each variant is computed at **that variant's own sealed-window formation count** `n* = sealed_grid_count_psb2(store, cadence)` via the frozen noncentral-t `_power` (α = 0.05, one-sided). **V1 (monthly) therefore faces a smaller n\*** (~42) than V2/V3 (~84): reducing turnover via monthly cadence also shrinks the sealed sample, and V1 must overcome that. This is intentional — the protocol does not let a variant borrow fortnightly n* while trading monthly.

## 6. Selection rule (TRAIN only)

1. Score all three variants on TRAIN (2011–2018): mean IC, SD_IC, net spread, turnover, power (§5), AC₁.
2. **Winner = the variant with the highest TRAIN net spread among those with TRAIN power ≥ 0.80.** If none clears TRAIN power ≥ 0.80 → **no winner; phase fails at selection** (fall back to retire/shelve). Ties broken by higher power, then lower turnover.
3. Exactly one winner advances. HOLDOUT is not touched in this step.

## 7. Confirmation gate G0.5 (HOLDOUT — SINGLE LOOK)

The single selected winner is scored **once** on HOLDOUT (2019–2022). It must clear **ALL** of:

| Criterion | Threshold (RATIFIED) |
|---|---|
| Power (at variant's sealed n*, §5) | **≥ 0.80** |
| Net spread (annualized) | **≥ 2.0%/yr** |
| Deflated p (= min(1, m × p_one_sided), m=3) | **< 0.05** |
| Mean IC | **> 0** |

- **All PASS →** the winning variant is "C2′". It earns the sealed read; proceed to **Phase 1 (C2-VAL)** pre-registration with C2′ (which must still pin its own α, execution conventions, sealed-read mechanics, and disclose this phase as prior exposure).
- **Any FAIL →** terminal for this round. **No V4, no re-tune, no second HOLDOUT look.** Fall back to retire/shelve C2 (roadmap path b). The HOLDOUT is now spent.

## 8. Anti-overfit guards (the reason this is a battery, not tuning)

- Variant slate pinned pre-run (§4); no variant outside the table.
- HOLDOUT is a **single confirmation look** — never used for selection; a FAIL cannot be re-rolled.
- m = 3 Bonferroni deflation on the confirmation p-value.
- Sealed window (2023–2026) never read; fence proven each run.
- Deterministic + digest-sealed report (the Phase 0.2 B1 lesson): every emitted list has a deterministic `ORDER BY`; the generation timestamp sits **outside** the hashed region; every PASS/FAIL is **computed**, none hardcoded; two runs regenerate byte-identically.

## 9. Deliverables (DeepSeek)

1. **`scripts/c2_phase0_5_minibattery.py`** — runner: patches only the split boundaries; builds the three variants via existing harness params; scores each on TRAIN; applies §6 selection; scores the winner once on HOLDOUT; evaluates G0.5 (§7); writes the report. Reuses the frozen scoring — no change to `scripts/psb2/harness.py` scoring paths. If a variant (e.g., V3 staggered fortnightly) needs a parameter combination the harness does not yet expose, add it as a **thin, tested parameterization**, flagged NEEDS-DECISION, not a scoring change.
2. **Report** — `docs/reports/C2_PHASE0_5_MINIBATTERY.md`, every number script-generated, digest over the full artifact per §8, TRAIN table (all 3 variants) + selection + HOLDOUT confirmation + G0.5 verdict.
3. **Tests** — `tests/` : variant-parameterization unit tests (each variant produces the intended cadence/band/stagger behavior on a synthetic fixture); a determinism test (two runs → identical report + digest); TRAIN/HOLDOUT fence tests (holdout dates never enter selection). Full existing suite green.
4. **Fidelity precondition** — `tests/psb2/test_fidelity.py` green before any dev run (proves score_c2 unchanged).

## 10. Prohibitions

- **No sealed-window read.** Nothing with `trade_date ≥ 2023-01-01` is scored, extracted, or counted (beyond the fence-proof MAX comparison).
- **No change to `score_c2_psb2` or any frozen PSB-1/PSB-2 scoring code.** Only rebalance-mechanics parameters vary.
- **No HOLDOUT use in selection**, and **no re-tuning after a HOLDOUT look.**
- **No variant outside §4**, no change to §5–§7 thresholds once frozen.

## 11. Acceptance criteria (Lead Review will independently re-derive)

1. Fidelity green; fence proven; sealed window provably untouched.
2. All 3 variants scored on TRAIN with the pinned params; selection follows §6 exactly (winner recomputed independently).
3. Winner's HOLDOUT G0.5 verdict recomputed independently from the raw IC vector (the Phase 0.4 method); power at the correct per-variant n*.
4. Report digest reproducible; verdicts computed not hardcoded; new + existing tests green (report counts).
5. Every deviation flagged NEEDS-DECISION, none silently resolved.

*Ratified numbers: TRAIN/HOLDOUT boundary = 2018-12-31; net-spread floor = 2.0%/yr; m = 3; power hurdle = 0.80. Sealed window unread.*
