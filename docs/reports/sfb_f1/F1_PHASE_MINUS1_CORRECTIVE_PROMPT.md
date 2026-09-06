# F1 / SFB-1 — Phase −1 Corrective Implementer Prompt: Fix & Actually Certify the Futures Substrate

**For:** the implementer (DeepSeek V4), per the standing role split — *implementer builds from this written prompt; Claude writes the prompt and reviews; the operator decides.*
**Supersedes execution of:** `F1_PHASE_MINUS1_INGESTION_PROMPT.md` (the original build spec — still the governing spec for anything this document does not change).
**Driven by:** `F1_PHASE_MINUS1_LEAD_REVIEW.md` (verdict: REJECT — substrate not certified). Read that review first; every correction below is keyed to one of its findings.
**Authorization:** the Phase −1 ingestion authorization from 2026-07-18 still stands. This is the same pre-battery step, re-opened to fix defects. **No freeze, no scoring, no signal, no sealed-window path read.**

---

## §0 Why this exists

The first pass delivered *code that compiles and unit-tests green*, but (a) the substrate was **never actually built** (`futures_bhavcopy.duckdb` does not exist), (b) the certification report was **never generated**, and (c) the roll adjustment is **wrong** — proven by running the real builder: every roll splice leaks the raw contract gap into the "continuous" return series, and Arm F-A **fails 1 violation/roll** when finally run against real builder output. The unit tests passed only because the cert arm was tested against a hand-built fixture, never against `build_continuous()`.

**The non-negotiable rule this time:** *nothing is "done" until it has run against the real store and the numbers are in the script-generated D6.* Green unit tests on synthetic fixtures are not certification.

---

## §1 Prohibitions (unchanged, restated)

- No candidate scoring, signal, factor, or bracket logic. Nothing in `core/strategies/`.
- No forward-return / excursion / path computation on any window.
- No sealed-window path read. The 2023→present window may be ingested and structurally certified; it is never scored here.
- **Copy-first** — validate-then-apply; never mutate a raw store in place.
- **Deterministic** — same inputs → byte-identical outputs. A full rebuild from the raw store must reproduce the continuous series and the certification numbers exactly.

---

## §2 Corrections (each keyed to a lead-review finding)

### C1 — Fix the roll back-adjustment (review Finding 1, CRITICAL)

The convention below is **pinned**. Implement exactly this; do not choose an alternative.

**Amendment to the pre-registration §4 (stated for transparency):** the DRAFT stub said "scale the entire pre-roll *history*" (back-adjustment, anchor the newest contract). This corrective prompt pins **forward-adjustment** instead — anchor the *oldest* bar, scale forward — for one concrete reason: under forward-adjustment a bar's stored adjusted level depends only on rolls that occurred **before** that bar, so every TRAIN/HOLDOUT bar's stored level is provably independent of any sealed-window roll ratio. Returns and ATR/price are identical under either convention; forward-adjustment additionally guarantees the stored substrate cannot encode sealed-window information. This amended pin must be recorded when `F1_PROTOCOL.md` freezes.

**The pinned convention (forward-adjustment, ratio):**

- Iterate trade dates ascending. Maintain a cumulative factor `cum`, initialised `cum = 1.0` for the oldest era.
- Define the **roll date `rd`** as the last day the near contract is held (the volume-crossover day, or the calendar fallback `expiry − 1` — unchanged from the original trigger logic, which is causal and correct).
- On the roll date `rd`, the row is still priced off the **old near** contract, at the current `cum`. `cum` is **not** changed on `rd`.
- Starting the **first day priced off the next contract** (`rd+1` onward), multiply `cum` by the splice factor
  ```
  f = near_close(rd) / next_close(rd)
  ```
  i.e. `cum_next = cum_near × near_close(rd) / next_close(rd)`. **Note the direction: `near/next`, not `next/near`.** This is the fix for the wrong-direction defect.
- `adj_x = raw_x × cum` for the active near contract's OHLC on each date.

**Why this is correct (verify before you run):** the adjusted return across the splice must equal the economic next-contract return.
```
return(rd → rd+1) = adj_close(rd+1) / adj_close(rd)
                  = [next_close(rd+1) × cum_next] / [near_close(rd) × cum_near]
                  = [next_close(rd+1) × near_close(rd)/next_close(rd)] / near_close(rd)
                  = next_close(rd+1) / next_close(rd)   ✓  (economic, not the raw gap)
```
and the return *into* the roll `return(rd−1 → rd) = near_close(rd)/near_close(rd−1)` ✓ (pure near return, uncorrupted).

**`roll_flag` / `roll_ratio` storage convention (pin, so builder and arm agree):**
- Set `roll_flag = TRUE` on the roll date `rd` (the last near-priced day).
- Store `roll_ratio = near_close(rd) / next_close(rd)` on `rd` — the exact multiplicative change applied to `cum` on the following day. (Arm F-A checks the `rd → rd+1` transition; see C2.)

Delete the dead `roll_map` / `near_map` blocks (review Finding 6) while you are in this file.

### C2 — Make the certification arms run against the real pipeline, and harden Arm F-A (review Finding 2, CRITICAL)

Two changes:

1. **Certification runs against the built store, and the arm unit tests run against builder output — never a hand-authored `stock_futures_continuous` table.** Replace the synthetic fixture in `tests/sfb/test_certification_arms.py` with one that (i) inserts a small synthetic **raw** `futures_bhavcopy` (2–3 expiries, a known contango and a known backwardation roll), (ii) calls the **real** `build_continuous()`, then (iii) runs the arms on that output. If an arm and the builder disagree, the test must fail — that is the whole point.

2. **Arm F-A must be non-self-referential.** Do not merely check that the builder reproduced its own stored `roll_ratio`. Independently recompute the economic roll return from the **raw** bhavcopy and assert the adjusted continuous return equals it:
   ```
   assert  adj_close(rd+1)/adj_close(rd)  ≈  next_close(rd+1)/next_close(rd)   within tol
   ```
   where `next_close` is read straight from `futures_bhavcopy` for the next-month expiry. Keep the existing relative tolerance `1e-3` (it is well-justified — tight enough to catch a percent-level basis error, loose enough for float noise). State the falsifiable prediction before running: **0 splices exceed tolerance in a correct build.**

### C3 — Correct the futures-STT schedule and de-self-reference Arm F-E (review Finding 3, HIGH)

`core/execution/futures/futures_fees.py`: the futures STT schedule is wrong. Corrected, source-verified schedule (sell-side only):

| Effective from | Futures STT (sell side) | Source |
|---|---|---|
| 2024-10-01 | **0.02%** (0.0002) | Finance (No. 2) Act 2024 / Budget 2024 — F&O STT hike |
| 2004-10-01* | **0.0125%** (0.000125) | prevailing pre-hike futures rate |
| before | 0.0 | no STT on derivatives |

\* Pin the exact pre-hike effective date/rate against the primary NSE/CBDT circular before committing — the **certain** facts are: pre-hike futures STT = 0.0125% (not the 0.01% currently coded), and it rose to **0.02% on 2024-10-01**, a boundary that lands inside the sealed window. Do not leave 0.01% anywhere.

Then **rewrite Arm F-E's expected values and `tests/sfb/test_futures_fees.py` from the primary source, not from the module.** F-E currently hardcodes the same wrong 0.01% it is meant to police, so it cannot detect a wrong constant. Every F-E expected number must trace to a circular, not to `futures_fees.py`. Add the 2024-10-01 boundary as an explicit F-E test case (one assertion on each side).

While here, action the two lower items the review flagged in this area if cheap: leave the clearing-charge seam as-is (documented, 0), and keep the GST base unchanged (it is correct).

### C4 — Make Arm F-C actually prove no-lookahead (review Finding 4, HIGH)

F-C currently only checks that the next contract has data — near-vacuous. Replace it with a real causality assertion: for every roll, independently recompute, from the raw store, the **first** date `≤ (expiry − 1)` on which next-month volume exceeds near-month volume, and assert the builder's stored `roll_date` equals that date (or, when no crossover exists, equals the calendar fallback `expiry − 1`). This proves the roll decision used only data available at/before `rd`. State the prediction before running: **0 rolls reference future data.**

### C5 — Give the PIT universe a liquidity floor and stop the circularity (review Finding 5, HIGH)

D3 currently defines eligibility as "any FUTSTK print exists that day" and Arm F-D checks the intervals cover exactly those prints — circular, and it admits single-print near-dead contracts, which breaks the §3 "liquid ≤10-name book / tractable impact" premise.

- Redefine eligibility as **liquidity-gated presence**: an underlying is eligible on date *t* iff it has FUTSTK prints and its **trailing causal liquidity** (e.g. median daily `contracts` over the trailing 63 sessions, computed strictly from data `< t`) is at or above a threshold. Document this openly as a **PIT-safe proxy** for the SEBI F&O-eligibility list (which the repo does not have), not as the eligibility notice itself.
- The exact liquidity threshold and window are an **operator pin** (pre-registration §11 universe item). Propose a concrete default in the D6 report and flag it for ratification; do not silently choose one and bury it.
- Arm F-D must then assert two real properties, not self-consistency: (i) the liquidity floor is actually applied (no member falls below it during its interval), and (ii) the trailing-liquidity computation is causal (uses only `< t` data — no lookahead in the window).
- Resolve the `contracts` unit mismatch across the legacy/UDiFF boundary (review Finding 6) **before** it feeds this liquidity computation — normalise both eras to the same unit (number of contracts) and document the mapping.

### C6 — Medium cleanups (review Finding 6)

- Delete dead code in D2 (done under C1).
- In `ingest_futures_bhavcopy.py`, log a parse-failure on a real trading day distinctly from a genuine 404 (do not silently fold parse-fails into "absent"). A dropped trading day must be visible.

---

## §3 Run it for real — the acceptance-defining step

This is the part that did not happen last time and is now mandatory:

1. Run **D1 ingestion** end-to-end against the NSE archive (both legacy and UDiFF eras) → a real `data/market_data/futures_bhavcopy.duckdb`.
2. Run **D2** (`build_continuous_futures.py`) → `stock_futures_continuous` over the whole panel.
3. Run **D3** (`build_fo_universe.py`, liquidity-gated) → `fo_eligible_intervals`.
4. Run **D5** (`certify_futures_substrate.py`) → **D6** `docs/reports/F1_SUBSTRATE_CERTIFICATION.md`, **script-generated, no hand-edited numbers.**
5. D6 must report, from the real run: raw row count, date coverage per underlying, the legacy→UDiFF format-boundary date, the roll rule actually used per name (volume-trigger vs calendar fallback) and the count of each, the liquidity-floor default used, and every arm's pass/violation count.

State each arm's falsifiable prediction **before** running it (C2, C4 predictions above; F-B unique-key = 0 dupes; F-D = 0 floor/causality violations; F-E = 0 rate mismatches). If any arm violates its prediction, **stop** — that is a substrate defect to repair copy-first, not a tolerance to relax.

---

## §4 Acceptance / stop rules

- Substrate is **certified** iff, on a real end-to-end run: D5 arms all return **0 undocumented violations** (disposition register the only exclusion path) **and** D6 is script-generated with those numbers.
- All of `tests/sfb/` green, with the cert-arm tests now driven by **builder output** (C2), and the fee tests sourced from **circulars** (C3).
- Only a certified substrate unblocks the `F1_PROTOCOL.md` freeze. Freeze, scoring, and any sealed read remain out of scope.
- Deliver back: the regenerated D6, the passing test run, and a short note of the roll rule / liquidity floor actually observed. Claude re-reviews before the operator is asked to certify.

## §5 What Claude re-reviews (not implements)

The corrected roll convention against the C1 math (seam return = economic next return, direction `near/next`, splice on `rd+1`); that Arm F-A recomputes the economic return independently (not from stored `roll_ratio`); the STT schedule against the circular; Arm F-C's causal recomputation; the liquidity-floor PIT safety; and that D6 is genuinely script-generated from a real run (not a fixture). ACCEPT / findings, same lineage as the PSB lead reviews.
