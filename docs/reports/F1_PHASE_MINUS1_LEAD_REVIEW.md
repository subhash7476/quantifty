# F1 / SFB-1 Phase −1 — Lead Review of the Futures Substrate Ingestion

**Reviewer:** Claude (lead review, per the standing role split — implementer builds, Claude reviews, operator decides).
**Scope:** DeepSeek's Phase −1 deliverables D1–D6 against `F1_PHASE_MINUS1_INGESTION_PROMPT.md` §4 and §7.
**Date:** 2026-07-18.
**Verdict: REJECT — SUBSTRATE NOT CERTIFIED. Do not freeze `F1_PROTOCOL.md`.**

The code compiles and the unit tests are green, but the substrate does not exist, was never certified, and the two most safety-critical pieces (the roll adjustment and the certification arm that guards it) are provably broken when run against each other. The prior session's "D6 generated / substrate certified" summary is **inaccurate**.

---

## 0. Headline (filesystem evidence)

| Claimed | Actual |
|---|---|
| D1 substrate ingested | **No `data/market_data/futures_bhavcopy.duckdb` exists** anywhere in the repo. Ingestion never ran against NSE. |
| D6 report "Generated to `docs/reports/F1_SUBSTRATE_CERTIFICATION.md`" | **File does not exist.** D5/D6 never ran against real data. |
| "20 tests, all passing" | True, but all are **unit tests over synthetic in-memory fixtures**. None exercises the real pipeline end-to-end. |

Per ingestion-prompt §6, the substrate is certified **iff** D5 arms all return 0 undocumented violations **and** D6 is script-generated. Neither happened. Phase −1 is **not complete**; what was delivered is *code*, not a *certified substrate*.

---

## 1. CRITICAL — D2 roll back-adjustment is wrong (empirically demonstrated)

`build_continuous_futures.py` does **not** remove the roll gap. Two compounding defects:

1. **Wrong direction.** It multiplies a forward cumulative factor by `ratio = next_close(rd)/near_close(rd)` at each roll. Forward-adjustment continuity requires the *inverse* (`near/next`); back-adjustment (what §4 of the prompt literally specifies — "scale the entire pre-roll history") requires scaling the *past* eras by `next/near`. The builder scales the *future* by `next/near`, which **doubles** the basis instead of cancelling it.
2. **Off-by-one splice.** The cumulative factor is bumped on the **roll-date row**, which is still priced off the **old near** contract (`near_exp` on the roll date resolves to the old expiry). So the roll-date return and the first post-roll return are both corrupted.

**Empirical proof** (real `build_continuous()` on a synthetic 2-expiry contango series; script + output retained this session):

```
2020-01-16  raw=105.500  adj=105.500  roll=False
2020-01-17  raw=106.000  adj=117.300  roll=True   <- +10.7% artificial jump on the roll date
2020-01-20  raw=118.325  adj=130.939  roll=False

adjusted return, first post-roll day (2020-01-20): +11.63%
true economic next-contract return over that step:  +0.87%
```

The +11.6% is the raw near→next contract gap leaking straight into the "continuous" return series — the precise artifact ratio-adjustment is supposed to eliminate. (The +11.6% is inflated by this synthetic scaffold's exaggerated ~11% basis; a real single-stock near/next basis is typically sub-1%, so the production per-seam error is smaller — but still non-zero and still fails F-A.) On a real 2012→present series (~150 rolls) every seam carries a spurious basis-sized return. Any ATR, expectancy, max-DD, or bracket-fill computed downstream is corrupted at every roll boundary.

## 2. CRITICAL — the certification arm never ran against the pipeline it certifies

Arm F-A, run against the **real** builder output above, returns **1 violation per roll** (`ratio_mismatch 0.096`). So the substrate would have failed certification on the first honest run. It "passed" only because:

- `tests/sfb/test_certification_arms.py` hand-builds a `stock_futures_continuous` fixture constructed to satisfy **F-A's own expected pairing** — the cum factor bumped strictly the day *after* the roll (roll-date row at `cum_old`, next row at `cum_new`). The builder uses the *other* convention (bump *on* the roll-date row). So there are two conventions in play: the fixture and F-A share one; the builder has the other. Because the test only ever feeds F-A a fixture built to F-A's own expectation — never `build_continuous()` output — the builder's divergent convention is invisible to the test. Run F-A on real builder output and it fails, 1 violation/roll, as demonstrated above.

This is the repo's documented "contract-shaped certification" failure mode (see the PSB-1 lesson): a cert suite validated against filtered/synthetic inputs that hide the defect. **The arms must be run against the actual built substrate, and the arm unit tests must be fed builder output — not a hand-authored table.** Had that discipline held, F-A would have caught Finding 1 immediately.

## 3. HIGH — futures STT schedule is wrong and Arm F-E cannot catch it

`futures_fees.py` pins futures STT at a flat **0.01% sell-side, "stable through the entire dev window."** That is factually wrong:

- The module pins futures STT at a flat **0.01%** since 2008. Verified against source (Budget 2024 / Finance (No. 2) Act 2024, effective 2024-10-01): futures STT was **0.0125%** and was **raised to 0.02% effective 2024-10-01**. So the module is wrong on **both** sides of that boundary — the pre-hike rate should be 0.0125% (not 0.01%), and the 0.02% post-2024-10-01 level is entirely missing. The module's own docstring even notes the *options* change on that date while asserting futures were unchanged — they were not.
- The missing 2024-10-01 boundary lands **inside the SEALED window (2023→present)** — the exact window F1 will eventually score. The sell-side statutory cost there is understated (0.01% modelled vs 0.02% actual).
- Arm F-E's test cases hardcode the same wrong rate (`0.01% at 2025-01-01`), so F-E validates the model **against itself**, not against source. A self-referential arm cannot detect a wrong constant.

Action: correct the schedule to 0.0125% (pre-2024-10-01) / 0.02% (from 2024-10-01), and rewrite F-E's expected values from the **primary source**, not from the module. (Sources: [caclubindia](https://www.caclubindia.com/articles/securities-transaction-tax-rate-hikes-on-f-amp-o-w-e-f-1st-october-24-55626.asp), [ICICI Direct](https://icicidirect.com/research/equity/finace/new-stt-rules-in-futures-and-options-trading).)

## 4. HIGH — Arm F-C (no-lookahead) is near-vacuous

F-C only checks that the next-month contract *has data on/before the roll date* — which is essentially always true. It does **not** verify that the roll trigger used only information available at/before the roll date. The builder's trigger *is* causal by construction (first volume-crossover date, scanning `trade_date <= last_hold`), so the property holds — but the **arm doesn't test it**. It would pass even if the builder looked ahead. §7 asked for a real no-lookahead proof; this isn't one.

## 5. HIGH — Arm F-D / D3 universe is circular and has no liquidity floor

- **Circular:** `fo_eligible_intervals` is *derived from* the bhavcopy (eligible ⇔ a FUTSTK print exists), and F-D then checks the intervals cover that same data — true by construction. There is no independent eligibility source and no real spot-check, despite §D3 asking for the "historical F&O securities list / eligibility notices" and F-D claiming it "reproduces the historical eligible set at spot-checked dates."
- **No liquidity floor:** presence-of-print admits a single-contract, near-dead future as "eligible." §3 of the pre-registration requires **liquid** single-stock futures and a concentrated ≤10-name book whose whole premise is a tractable impact model. Eligibility with no min-volume/OI/ADV threshold undermines that. Presence-of-print is a defensible PIT-safe *proxy*, but it must be disclosed as such and gated by a liquidity threshold before it feeds the universe.

## 6. MEDIUM

- **`contracts` unit mismatch across the format boundary.** Legacy stores `CONTRACTS` (number of contracts); UDiFF stores `TtlTradgVol`. These are different units spliced into one column mid-2024. The same-day near-vs-next roll trigger is robust to it, but any cross-era volume/liquidity use is not. Document, and normalise if the universe gains a volume floor (Finding 5).
- **Dead code in D2.** `roll_map` and `near_map` (approx. lines 146–163) are built and never used; delete per repo style ("delete unused code completely").
- **Silent parse-fail.** In `ingest_futures_bhavcopy.py`, a parse failure on a real trading day returns `(0, ...)` and is counted as "absent (404)", indistinguishable from a non-trading day. Fine for a first pass, but it can silently drop days; log parse-fails distinctly.

---

## What is actually sound (keep)

- Fee model **architecture** is right: effective-dated schedules, a *model* not a hardcoded constant, sell-side-only STT, buy-side-only stamp duty, GST correctly based on (brokerage + exchange_txn + sebi_fee) only. The **values** need the Finding-3 correction, not the structure.
- Ingestion is copy-first with a raw-cache, handles both legacy and UDiFF formats with a documented boundary, and has a file-date identity check that discards mis-dated files — good discipline.
- Ratio (not difference) adjustment is the correct choice for ATR-relative brackets; the *implementation* of it is what's broken, not the choice.

---

## Required before re-review (copy-first, no freeze until green)

1. Fix D2: back-adjust in the correct direction and pin the splice so the adjusted return across a roll equals the economic next-contract return (not the raw gap). Decide one convention (back- vs forward-adjust) and make builder, arm, and fixture agree on it.
2. Re-point the arm unit tests at **builder output**, not a hand-built table. Add a seam test asserting the post-roll adjusted return equals the economic roll return on a known synthetic case.
3. Correct the futures-STT schedule (2024-10-01 boundary) and rewrite Arm F-E expected values from the primary circular.
4. Make Arm F-C assert the causal trigger, and Arm F-D assert against an independent eligibility signal (or explicitly document presence-of-print-as-proxy + add a liquidity floor).
5. **Actually run** D1 ingestion, D2/D3 builds, and D5/D6 against the real store; certification is claimed only when D6 is script-generated with 0 undocumented violations across the whole panel.

Until then F1 stays blocked at the §6 substrate gate. No protocol freeze, no scoring, no sealed read.
