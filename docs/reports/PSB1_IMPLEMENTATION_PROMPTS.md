# PSB-1 Implementation Prompts

Prompts issued by the Lead Reviewer (Claude) to the implementation party (DeepSeek V4).
One prompt per phase gate; a prompt is binding only after it appears in this file.
Governing documents: `PSB1_PROTOCOL.md` (**FROZEN Rev 2**, ratified 2026-07-13) and
`PSB1_PHASE0_RESEARCH_RECORD.md` (operator decisions D1–D4).

Standing constraints (every prompt, non-negotiable):

- The protocol is frozen. Implement it **exactly as written**; if a section is
  ambiguous or unimplementable, STOP and report — do not resolve ambiguity in code.
- Zero changes to feature-frozen components (`CLAUDE.md` table) and zero changes to
  any `scripts/csmp/` file. PSB-1 code lives in `scripts/psb1/` (+ `tests/psb1/`).
- Store opened `read_only=True`. Every real-data load asserts **and prints** the dev
  fence: `MAX(trade_date) <= 2022-12-31` (protocol §1/§10). Sole exception: the §7
  sealed-grid count (dates only, from `trading_calendar`).
- Deterministic, re-runnable to byte-identical output. Failures reported as failures.
- Reports are script-generated, stamped with code commit and the store's row count +
  `MAX(trade_date)` at run time.

---

## Prompt 1 — Phase 1: screening harness + synthetic dev-proof (ISSUED 2026-07-13)

### Mission

Build the PSB-1 screening harness and prove it on **synthetic data only**. This prompt
authorizes **no candidate score on real data** — not as a smoke test, not "just to
check wiring." Real-data schema probes (row counts, date ranges, column presence) are
permitted; anything that produces an IC, spread, or score distribution from real data
is Phase 2 and requires the Phase-1 Lead Review PASS first (protocol §11.1–11.2).

### Deliverables

1. `scripts/psb1/screening_harness.py` — the library:
   - **Loading** (protocol §2): derive from `run_a2_validation.load_window()` at
     commit `0ae1dc4` (keep the ever-member entity restriction and the
     `rn=1` turnover-primary listing dedup), re-fenced to 2022-12-31, extended to
     carry `deliv_pct` **through the same `rn=1` pick as the price** (named
     acceptance criterion AC-3).
   - **Grids** (§3): weekly (last full-session day per ISO week) and monthly (last
     full-session day per month) from `trading_calendar` with `n_symbols >= 200`.
   - **Scoring** (§5): C1–C5 exactly as written, including every completeness rule
     (≥40/52 beta weeks, ≥3/5 delivery days, ≥40/60 baseline days, σ > 0 guards,
     ≥200/252 vol days), the §4 direction convention, and percentile ranks with
     average ties.
   - **Metrics** (§4/§6): per-date Spearman IC; series mean/SD/n, one-sided t and p;
     net top-quintile spread with gate-(d) fees + κ=5bp/side on turnover-derived
     notional, baseline leg charged on its own churn, C5 banded; the §4.2
     worst-realized-forward-return imputation as a parallel robustness column; AC₁ of
     the IC series with the Newey–West (lag 4) robustness t when |AC₁| > 0.1;
     exclusion counts per date.
   - **Power** (§7): exact sealed-grid `n*` from `trading_calendar` dates; noncentral-t
     projected power at δ = dev mean IC (and reported-only at δ/2, and NW-SE variant
     when triggered).
2. `scripts/psb1/run_synthetic_devproof.py` — builds a synthetic panel (its own
   DuckDB file under `data/psb1_synthetic/`, never the real store), runs the harness
   end-to-end, and writes the script-generated report
   `docs/reports/PSB1_PHASE1_HARNESS_REPORT.md`.
3. `tests/psb1/test_scoring.py` — unit tests for each §5 scoring function on
   hand-built fixtures (known inputs → hand-computed scores), the completeness rules,
   and the §4.2 imputation.

### Synthetic dev-proof — falsifiable predictions (state, then run)

The synthetic panel: ≥200 names × ≥150 weekly grid dates, with prices, `deliv_pct`,
a synthetic `trading_calendar`, synthetic universe membership, and planted delistings.
The report must show, in this order:

- **P1 (planted signal):** forward returns constructed as `a·score + noise` with known
  `a` and noise scale chosen so the analytic expected rank IC is ≈ 0.05. Measured mean
  IC within ±0.02 of the analytic expectation.
- **P2 (null):** `a = 0` → the 95% CI of mean IC covers 0.
- **P3 (sign wiring):** plant reversal (forward return negatively proportional to past
  5-day return) → **C1** mean IC is positive; plant delivery-direction (forward return
  positively proportional to abnormal delivery) → **C3** mean IC is positive. This
  proves the §4 direction convention end-to-end, not just in unit tests.
- **P4 (F2 machinery):** plant delistings concentrated among past losers → the §4.2
  imputed column shows **lower** C1 mean IC than the primary column (direction of the
  known bias), and the report prints both.
- **P5 (fees):** the fee model is called with era-correct synthetic dates; total fees
  > 0 on both the top-quintile and baseline legs; net spread < gross spread.
- **P6 (determinism):** the entire dev-proof run twice produces **byte-identical**
  reports (hash printed for both runs).
- **P7 (fence):** the loader pointed at the real store in a fence-check mode asserts
  and prints `MAX(trade_date) <= 2022-12-31` without computing any score (this is the
  only permitted real-store touch, and it loads dates only).

### Acceptance criteria (Lead Review checks each)

- **AC-1:** all seven predictions P1–P7 pass, shown in the script-generated report.
- **AC-2:** no candidate score computed on real data anywhere (code inspection +
  report).
- **AC-3:** `deliv_pct` flows through the same `rn=1` listing pick as `adj_close`
  (review Prompt-1 caveat) — demonstrated by a unit test with a two-listing synthetic
  symbol where the turnover-primary row differs from the other listing.
- **AC-4:** §5 formulas match the frozen protocol symbol-for-symbol (diff review); all
  pinned parameters read from one constants block that quotes §9.
- **AC-5:** unit tests pass; determinism (P6) holds; the report carries commit hash +
  store stamps.
- **AC-6:** zero diffs outside `scripts/psb1/`, `tests/psb1/`,
  `data/psb1_synthetic/` (gitignored if binary), and the report file.

### On completion

Commit with message prefix `feat(psb1): Prompt 1 —` and report back for Lead Review.
Phase 2 (the battery run, C1→C5 in §11.2 order) begins only after a written PASS.

### Outcome — PASS WITH REQUIRED FIXES (2026-07-13)

Lead Review: `PSB1_PHASE1_LEAD_REVIEW.md`. The §5 formulas, the §7 power function, and
AC-2/AC-3/AC-6 are clean. Two blocking defects (C2 untested; the §4.2 sign-discrepancy
flag unimplemented) plus report-provenance and check-design gaps → **Prompt 1-A**.
Phase 2 remains unauthorized.

---

## Prompt 1-A — Phase 1 remediation (ISSUED 2026-07-13)

### Mission

Close the Phase-1 Lead Review. Same standing constraints as Prompt 1 (protocol frozen;
`scripts/psb1/` + `tests/psb1/` only; **still no candidate score on real data** — the
permitted real-store reads remain dates-only/row-count schema probes). The §5 formulas
are correct and **must not be touched**; this prompt adds tests, a mandated flag, honest
stamps, and two Phase-2 prerequisites.

### Blocking (Phase 2 stays closed until both land)

**D1 — unit-test C2.** Hand-built fixtures with hand-computed expected values, covering:
the OLS α/β fit over the 52 preceding weekly grid returns (formation week excluded); the
≥40-of-52 completeness rule (39 usable weeks → name absent, 40 → present); the σ(ε) > 0
guard (a name whose residuals are exactly zero → absent); and the residual
standardisation sign (`s = −resid/σ`, so a name that *outperformed* its market-implied
return scores negative). Assert against numbers you compute by hand, not against the
harness's own output.

**D2 — implement the §4.2 sign-discrepancy flag.** §4.2/§6: *"If a candidate's mean-IC
sign differs between the primary and imputed columns, the discrepancy is flagged to the
operator — never silently dropped."* Add the detection (not just the two printed columns)
to `CandidateResult` and surface it prominently in every candidate report — a visible
**FLAG** line, not a table cell. Add a unit test, and add a **P4b** prediction to the
dev-proof asserting the flag *fires* on the reversal scenario (C1 primary +0.0453 →
imputed −0.0938 is a sign flip and must trigger it) and *does not* fire on the null
scenario.

### Required to complete

- **D3 — report stamps.** Stamp the actual commit the code was run at. If the report is
  committed alongside the code, stamp the parent and say so explicitly, or regenerate
  post-commit. Add the store's row count.
- **D4** — state in the report only what the code actually verified.
- **S1 — real determinism proof.** Run the whole dev-proof in **two separate interpreter
  processes** with **different `PYTHONHASHSEED`** values and compare **whole-file bytes**
  of the report (excluding only the commit stamp line if it must vary). An in-process
  re-run cannot catch the hash-seed-dependent iteration-order bug P6 exists to catch.
- **S2 — make the fence-check evidential.** `fence_check` must print the store's
  **unfenced** `MAX(trade_date)` and row count beside the loader's fenced observed max,
  and assert `fenced ≤ 2022-12-31 < unfenced`. (For reference, the store today: 7,030,920
  rows, unfenced max `2026-07-09` — 3.5 years of sealed data are physically present and
  the current report's "MAX(trade_date)=2022-12-30" could be misread as denying that.)
  This stays a dates-only/count read.
- **S3 — store stamp = row count + unfenced max + fenced observed max**, in every report.
- **R1 — §11.3 data-integrity stop rule.** Log every >|20%| single-day adjusted move
  inside a formation window and cross-check it against the gate-(b) corporate-action
  record; **halt** only on undocumented residue (an adjustment mismatch), log-and-continue
  on a documented/genuine move. Must exist before any real formation window is scored.
- **R2 — print the real `n*`.** Weekly and monthly sealed-grid counts from the **real**
  `trading_calendar` (dates only — the §1/§7 exception). The synthetic 183/42 is a
  synthetic artifact; the protocol expects ≈182 weekly. `n*` is the denominator of the
  power hurdle.
- **I1/I2 — record the interpretations** in the constants block: C4's `p_i(t)` is ranked
  over the C3-scored set; `MIN_NAMES=5` and `CAP=1e7` are CSMP-inherited (cite
  `phase1_prereg_analysis.py:32,142`). Report the `MIN_NAMES` skipped-date count per
  candidate (expected 0).

### Also do

Make `db_path` a **required** argument on `load_panel` and `evaluate_candidate` — the
defaults currently point at the real store, so an argument-less call silently loads it.
Nothing calls them that way today; remove the footgun before Phase 2.

### Acceptance

All Prompt-1 ACs still hold, plus: D1–D4, S1–S3, R1, R2, I1, I2 closed; the regenerated
`PSB1_PHASE1_HARNESS_REPORT.md` shows P1–P7 **and P4b**; tests green; still zero candidate
scores on real data.

### On completion

Commit with prefix `fix(psb1): Prompt 1-A —` and report back. Phase 2 begins only after a
second written PASS.

### Outcome — FAIL (2026-07-13)

Second Lead Review: `PSB1_PHASE1_LEAD_REVIEW_2.md`. Nine of ten items closed and
independently verified (D1 C2 tests hand-checked; D2 flag; D3/D4 stamps; S1 cross-process
determinism; S2/S3 fence; R2 real n\* = 183/42 recomputed; I1/I2; footgun; 22/22 tests).
**R1 REJECTED** — it is not gate-(b)'s classification and is blind to a missing CA factor.
Chasing it surfaced a larger, operator-level finding: **the scored panel contains ~18
fabricated returns of −49% to −99%** (unadjusted demergers/capital-returns), and C1/C2/C4
rank on them. Phase 2 remains unauthorized.

---

## Prompt 1-B — R1 rebuild (ISSUED 2026-07-13)

### Mission

Rebuild **only** the §11.3 stop rule on gate-(b)'s actual classification. Everything else
from Prompt 1-A stands and **must not be touched**. Standing constraints unchanged
(protocol frozen; `scripts/psb1/` + `tests/psb1/` only; no candidate score on real data —
the §11.3 scan and dates/counts probes are not scores).

The panel-disposition finding (the ~18 unadjusted corporate actions in the scored panel) has
since been **ruled by the operator — decision D5, LOCKED 2026-07-13, pre-result**
(`PSB1_PHASE0_RESEARCH_RECORD.md` §3). Implement it exactly as pinned in the **D5
disposition** section below. Every edge is pinned there; **resolve none of them in code** —
if something is still ambiguous, STOP and report.

### The defect

`scan_data_integrity` halts iff a >|20%| adjusted move lands on a documented ex-date, and
logs everything else as "genuine." Gate-(b)
(`scripts/csmp/audit_corporate_actions.py:279–305`) classifies into five buckets, of which
three are residue:

```
RESIDUE = ("magnitude-mismatch", "direction-mismatch", "CA-shaped-orphan")
```

The current rule therefore (i) routes **CA-shaped-orphan** — *no factor spans the move, but
the surviving ratio sits on a canonical CA ratio; i.e. a **missing factor*** — to "genuine,
log and continue," which is the exact failure §11.3 exists to halt on; (ii) false-halts,
because it applies no magnitude-agreement test; (iii) never consults `ca_scope_exclusions`,
which gate-(b) treats as making a residue row acceptable.

### Required

1. **Reuse gate-(b)'s classification, do not re-invent it.** For every >|20%| single-day
   adjusted move inside a formation window, classify with gate-(b)'s own logic:
   - a factor **spans the interval `ptd < ex_date ≤ td`** (not `td == ex_date` — an ex-date
     can fall on a non-trading day) **and** agrees in direction **and magnitude** (within
     `MAGNITUDE_TOLERANCE`) → `CA-explained`, log;
   - a factor spans but disagrees → `magnitude-mismatch` / `direction-mismatch` → **residue**;
   - no factor spans **and** the surviving ratio sits on `CA_RATIOS` (0.5, 0.4, ⅓, 0.25,
     0.2, ⅙, 0.1, 0.05, 0.02, 0.01 ± `CA_RATIO_TOLERANCE`), applied only where
     `prev_close ≥ CA_RATIO_MIN_PRICE` → `CA-shaped-orphan` → **residue**;
   - otherwise → `genuine`, log.
2. **HALT iff `class ∈ RESIDUE` and `(symbol, move_date) ∉ ca_scope_exclusions`** — the
   literal §11.3 rule ("undocumented residue"). A documented residue row is logged, not
   halting. A genuine move is logged, not halting.
3. `scripts/csmp/` is feature-frozen — **do not edit it**. Either import its constants and
   classifier, or re-implement them in `scripts/psb1/` citing the source lines; if you
   re-implement, add a test asserting your classifier agrees with gate-(b)'s on a fixture
   covering all five buckets.
4. **Tests for all five buckets**, plus the `ca_scope_exclusions` exemption path (a residue
   row that is documented → logged, not halted) and the interval-span case (ex-date on a
   non-trading day → still spanned).
5. **Report** the classification counts per bucket for the dev window, and the full residue
   list with its documented/undocumented disposition — the same shape as gate-(b)'s own
   residue table. This is the artifact the operator's pending decision will be made against,
   so it must be complete and honest, **including the undocumented rows that will halt the
   battery**.
6. Note in the report, without acting on it, that a correct R1 **halts** on the undocumented
   residue and that the panel's disposition of those rows is an open operator decision.

### D5 disposition — unadjusted CAs are a MISSING INPUT (§4.1)

**Operator decision D5:** a price-derived input window that spans an unadjusted corporate
action is an **absent input**; the name is not scorable across that window, exactly as if a
price were missing. No new parameter. Pinned semantics — implement precisely these:

1. **The CA register** = every `(entity, move_date)` your R1 classifier labels **residue**
   (all three residue classes), **whether or not it is documented in `ca_scope_exclusions`.**
   Documenting a row explains it; it does **not** repair the price. Both are unadjusted, so
   both are missing inputs. (This register is a *scoring* input; the R1 **halt** still keys
   only on *undocumented* residue. The two sets are deliberately different — do not merge
   them.)
2. **Formation return** (C1, C4, and C2's `r_i(t−5,t)`): if the window `(t−5, t]` contains a
   register move, the name is **not scored** at *t*.
3. **C2 beta window:** a register move inside a weekly window return `(g−5, g]` makes **that
   week's return missing** — drop the week; it then counts against the **≥40 of 52**
   completeness rule. Do **not** drop the name outright.
4. **C2 market return `r_mkt(w)`:** names whose `r_i(w−5, w)` spans a register move are
   **excluded from the equal-weighted mean.** (A fabricated −99% otherwise corrupts the
   market return for every name that week — this is the edge most likely to be missed.)
5. **C5 vol window:** a register move makes that **daily return missing** — drop the day; it
   counts against the **≥200 of 252** obs rule.
6. **C3:** unaffected. `deliv_pct` is a ratio and is CA-invariant (§2).
7. **Forward return `r(t, t')`:** if the forward window spans a register move, the name is
   **excluded from that date entirely** — it does not enter the IC or the portfolios.
   **It must NOT be routed into the §4.2 missing-forward imputation:** §4.2 imputes the
   date's *worst realized forward return* because a delisting is plausibly catastrophic; a
   corporate action is not a delisting, and imputing it would fabricate a second time.
8. **Counting:** report the CA-exclusion count per formation date as its **own counter**,
   distinct from both the §4.1 formation-incomplete count and the §4.2 missing-forward
   count. Three counters, never merged.

Tests required for each of 2–7, plus a test that the register includes a **documented**
residue row (it is still a missing input) while the R1 halt does **not** fire on it.

### Acceptance

All Prompt-1 and Prompt-1-A criteria still hold; R1 classifies into gate-(b)'s five buckets
and halts only on **undocumented** residue; D5 is implemented on the **full** residue
register per the pinned semantics above; all five buckets, the exemption path, the
interval-span path, and D5 items 2–7 are tested; the dev-window classification table and the
three exclusion counters are in the report; still zero candidate scores on real data.

### On completion

Commit with prefix `fix(psb1): Prompt 1-B —` and report back. Phase 2 begins only after a
third written PASS.

---

## Prompt 2 — entity-grain adjustment repair (ISSUED 2026-07-13)

### Mission

Repair a defect in the **shared substrate**, found by R1's first real run
(`PSB1_PHASE1_LEAD_REVIEW_3.md`). Prompt 1-B **passed** — nothing in `scripts/psb1/` is at
fault and nothing in it needs redoing. This prompt changes **one CSMP function**, re-runs the
view, and re-runs R1 against the repaired panel.

**Operator authorization (2026-07-13):** the standing "do not edit `scripts/csmp/`" constraint
is **lifted for `scripts/csmp/ingest_corporate_actions.py` only**, and only for
`build_adjusted_view()`. Every other file under `scripts/csmp/` remains frozen — in particular
**`audit_corporate_actions.py` must not be touched**.

### The defect

`adjustment_factors` is keyed to **symbol**. An entity's price history spans **two or more**
symbols across a ticker rename. `build_adjusted_view()`
(`scripts/csmp/ingest_corporate_actions.py:508–559`) computes the cumulative backward factor
with `PARTITION BY symbol` (the `cum` CTE, lines 527–536), so a factor attached to the
**post-rename** symbol is applied to post-rename prints and **not** to the pre-rename prints of
the *same entity*. The entity's adjusted series then steps by exactly that factor on the rename
date. The **raw** series is continuous; only the adjusted one breaks:

```
entity INFOSYSTCH        raw_close   adj_close
2011-06-28  INFOSYSTCH     2865.30     2865.30    <- INFY's factors not applied
2011-06-29  INFY           2881.75      360.22    <- raw x 0.125  => adjusted move -87.43%
```

`0.125 = 0.5³` — Infosys' three 1:1 bonuses. The raw move was **+0.6%**. Same mechanism:
`BAJAUTOFIN→BAJFINANCE` (×0.01, −99.02%), `NIITTECH→COFORGE` (×0.2, −80.15%),
`SRTRANSFIN→SHRIRAMFIN` (×0.2), `ANGELBRKG→ANGELONE` (×0.1).

**Scope:** 59 entities carry a fabricated jump (51 dev, 8 sealed); **991 of the 1,050 renames
already adjust correctly and must not be disturbed**. 15 of R1's 235 screened moves span a
rename; the rest are sub-threshold (e.g. DUCON −9.09%) and invisible to R1 — which is why this
must be fixed in the data, not screened out.

### Required

1. **Compute the cumulative factor at the ENTITY grain**, not the symbol grain. The entity map
   is `universe_eligibility(symbol, entity)` — the same map both consumers already use.
   **Symbols with no entity row must fall back to `entity := symbol`** so their behavior is
   byte-identical to today. Report the count of such symbols.
2. **Renames can be multi-hop** (A→B→C). Entity-grain grouping handles this transitively by
   construction — do not special-case single hops.
3. **Do not double-apply a factor.** If one event is recorded against *both* the old and the new
   symbol, entity-grain compounding would square it. **Assert that no `(entity, ex_date)` draws
   factors from more than one symbol. If any does, STOP and report it — do not resolve it in
   code.**
4. **`prev_close` must stay consistent with the new grain.** The `LAG(cum_price) OVER (PARTITION
   BY symbol, series ...)` at line 554 is symbol-partitioned. Work out what it must become so
   that the adjusted `close/prev_close` ratio equals the raw ratio at a rename boundary, and
   **test it** — do not assume.
5. **Re-run the view** (`build_adjusted_view` only — no re-ingest; `corporate_actions`,
   `adjustment_factors`, and every other table stay untouched). Provide the runner you used.
6. **Re-run R1** on the repaired panel and report the new classification table.
7. **Do not touch `scripts/psb1/screening_harness.py`'s scoring, or `audit_corporate_actions.py`.**

### The invariant to test

This is the whole acceptance criterion, and it is exactly checkable:

> For every entity, for every pair of **consecutive trading-day prints**, the **adjusted** return
> must equal the **raw** return — *except* across a true ex-date, where it must equal the raw
> return divided by that ex-date's factor.

A rename is **not** an ex-date. Write this as a test over the real store and report how many
(entity, date) pairs violate it **before** and **after** the fix.

### Falsifiable predictions — state them, then run

Scaling an entity's pre-rename prints by the post-rename factor changes price **levels** but not
**returns** (a constant multiplier over a contiguous segment). Therefore:

1. **Every return in the panel is unchanged except at the 59 rename boundaries.** R1's other 220
   screened moves must come back **identical**. If any other move changes, the fix is wrong —
   STOP and report.
2. The **15** rename-spanning moves disappear from the >|20%| screen (they collapse to their raw
   moves: −0.7%, −2.4%, +0.6%, …). **No new move appears at a rename date.**
3. Residue falls from **7 → 2**: `SINTEX` (documented) and `KWALITY` (undocumented).
4. The halt set falls from **6 → 1**. **KWALITY 2010-06-15 (+45.9%, `direction-mismatch`) still
   HALTs** — it is not a rename artifact. Report it; **do not disposition it** (operator's call).
5. Large `genuine` moves (|ret| ≥ 40%) fall from **43 → 34** — the true unadjusted-CA population.
6. **Watch for one second-order effect and report it:** `is_ca_shaped` is disabled below
   `prev_close < Rs 5`, and this fix *lowers* pre-rename price levels. If any move's
   classification changes because its `prev_close` crossed Rs 5, say so explicitly.

If a prediction fails, **STOP and report** — do not adjust the fix until it passes.

### Blast radius — report, do not fix

Seven consumers read this view. Gate-(b) does **not** (it reads raw `equity_bhavcopy` +
`adjustment_factors`, so its certification is unaffected — confirm this and say so). The others:

`scripts/psb1/screening_harness.py`, `scripts/csmp/run_a2_validation.py`,
`scripts/csmp/phase1_prereg_analysis.py`, `scripts/csmp/phase1_ci_coverage.py`,
`scripts/csmp/triage_momentum.py`, `scripts/csmp/build_devtruncated_store.py`,
`core/msi/artifacts/xs_momentum_v1/model.py`.

**Do not re-run or modify any of them.** CSMP's A2 panel is built with the identical entity-level
dedup and is therefore affected; whether its banked results move is the operator's and the CSMP
owner's call, not yours. List the consumers, state that they are affected, stop there.

### Acceptance

The view computes cumulative factors at the entity grain, transitively across multi-hop renames,
with a symbol fallback for unmapped symbols and a hard assert against double-application; the
raw-vs-adjusted return invariant holds for every entity on the real store; all six predictions
above are confirmed or a failure is reported; R1 re-run shows residue 2 / halt 1 / large-genuine
34; the 220 non-rename moves are unchanged; `audit_corporate_actions.py` and PSB-1 scoring are
untouched; the blast radius is listed and not acted on.

### On completion

Commit with prefix `fix(csmp): Prompt 2 —` and report back. Phase 2 begins only after a Lead
Review PASS on this **and** a re-scoped D5 (**D5-A**), which the operator will rule on once the
repaired R1 shows the true population.

---

## Prompt 3 — time-aware entity resolution (ISSUED 2026-07-14)

### Operator decisions (LOCKED 2026-07-14, pre-result)

**D6 — the `build_universe.py` freeze is BROKEN for this repair.** Entity resolution must become
a function of `(symbol, trade_date)`. The defect is *in* the entity map; a workaround inside
`ingest_corporate_actions.py` would leave every other consumer of `universe_eligibility` still
believing two different companies are one.

**D7 — the BSE corroboration screen is a separate prompt, and it runs SECOND.** The operator
originally sequenced it *first*, on my report that R1's baseline was contaminated by 251 missing
factors. **That report was wrong and I have withdrawn it** (`PSB1_PHASE1_LEAD_REVIEW_4.md`,
"Correction"): the confirmed population is **one** row, not 251. The order is now forced the other
way by a hard constraint — see "Why this must run before the BSE screen" below.

### Mission

Make entity resolution time-aware, split the one entity that wrongly merges two concurrently
listed companies, and remove the `prev_close` fabrication that Prompt 2 introduced. Add the
assertion Prompt 2 assumed but never made.

### The defect (`PSB1_PHASE1_LEAD_REVIEW_4.md`, Finding 1)

`symbol_changes` records a real rename chain, every row labelled *Dhunseri Ventures Limited*:

```
DTIL -> DPTL (2010-07-26)    DPTL -> DPL (2014-11-12)    DPL -> DVL (2019-01-02)
```

`build_universe.py`'s union-find (`uf.find`, line 274) has **no time dimension**, so it collapses
all four symbols into one entity, `DPL`. But **`DTIL` never stopped trading** — it prints
continuously from 2010-01-04 to 2026-07-09, overlapping `DPL` and `DVL` for sixteen years. NSE
**recycled the ticker**: the 2010 rename vacated `DTIL`, and the demerged tea business relisted
under it. They are provably different companies — `DTIL` is BSE scrip **538902** (*Dhunseri Tea &
Industries*), `DVL` is BSE scrip **523736** (*Dhunseri Ventures*).

A symbol is therefore **not** one entity for all time. `DTIL` is two entities, sliced at
2010-07-26. Two consequences in the substrate today:

1. `DVL`'s 2021-08-05 bonus is applied at entity grain across `DTIL`'s concurrent history. It
   lands on the right numbers **only by coincidence** — `DTIL` had an identical 1:2 bonus on the
   identical ex-date, whose factor is missing (that is the BSE screen's job, Prompt 4).
2. `LAG(cum_price) OVER (PARTITION BY entity, series ORDER BY trade_date, symbol)` reaches, for
   `DVL`'s 2021-08-05 row, into **`DTIL`'s 2021-08-05 row** (same date, `'DTIL' < 'DVL'`). Result:
   `adj_prev_close = 300.75` against `adj_close(t-1) = 200.50` — a **+50% fabricated overnight
   gap**, exactly `1 / 0.6667`. It is the only symbol-grain continuity violation in the
   7,030,920-row view, and it did not exist before Prompt 2.

Entity `DPL` is the **only** entity repo-wide with co-trading members. Blast radius today: 4 symbols.

### Why this must run before the BSE screen

If `DTIL` were given its own `BONUS` factor while the bad union still exists, the `events` CTE —
which groups by `(entity, ex_date)` and compounds via `EXP(SUM(LN(factor)))` — would multiply
`DTIL`'s 0.6667 by `DVL`'s 0.6667 to **0.4444**, a double application. `assert_no_double_apply`
would then see two symbols contributing a factor at one `(entity, ex_date)` and halt the build.
**The BSE screen cannot land until the entity is split.**

### Required

1. **Time-aware entity resolution in `build_universe.py`.** A `symbol_changes` edge `old -> new`
   at date `D` means: `old`'s prints **before `D`** belong to the chain; prints of `old` **on or
   after `D`** are a recycled ticker and a **different entity**. Emit an interval table —
   `symbol_entity_intervals(symbol, valid_from, valid_to, entity)`, half-open
   `[valid_from, valid_to)` — that covers every `(symbol, trade_date)` present in
   `equity_bhavcopy` **exactly once**. A symbol with prints on both sides of its own outgoing
   rename date yields two intervals with two different entities.

2. **Resolve entity by date everywhere it is used.** Every join in `build_universe.py` that
   currently maps symbol -> entity — notably `entity_turnover` (line 362-367), which today sums
   `DTIL` + `DVL` turnover into one entity and thereby overstates that entity's liquidity — must
   resolve on `(symbol, trade_date)`.

3. **`build_adjusted_view()` joins the interval table** on `symbol` **and** `trade_date` between
   `valid_from` and `valid_to`, instead of `universe_eligibility`. The `cum`, `events`, and `LAG`
   partitions stay at entity grain — that part of Prompt 2 was right.

4. **Replace the vacuous STOP assertion.** `assert_no_double_apply` tests the wrong precondition:
   it passed only because `DTIL` had *zero* factors. The assertion that matters:

   > **No entity may contain two symbols whose trading spans overlap.**

   Assert it on the repaired map. It is the precondition Prompt 2 silently assumed.

5. **Add a `prev_close` invariant and run it at SYMBOL grain, over the whole panel.** The current
   runner (`repair_adjusted_view.py:33-82`) never references `prev_close` at all, and dedups
   co-trading symbols away before it measures anything — which is why it reported green. Required
   check: `adj_prev_close(t) == adj_close(t-1)` with
   `LAG(...) OVER (PARTITION BY symbol, series ORDER BY trade_date)`, across all 7,030,920 rows —
   not a 20-symbol sample, no entity-grain dedup. **Enumerate** every surviving violation; do not
   characterise them in aggregate and do not dismiss any as sub-threshold.

### Falsifiable predictions — state them, then run

- **P1** Exactly **1** symbol resolves to more than one entity interval: `DTIL`, split at
  2010-07-26. The other 4,131 symbols have exactly one interval each.
- **P2** After the repair, **0** entities contain symbols with overlapping trading spans (the new
  assertion passes). Before: 1.
- **P3** Symbol-grain `prev_close` view-induced violations: **1 -> 0** across the whole panel.
- **P4** `DVL` 2021-08-05: `adj_prev_close` becomes **200.50**, equal to `adj_close(2021-08-04)`.
- **P5 — the expected regression, and it is CORRECT.** `DTIL`'s post-2010 interval becomes its own
  entity with **no factor of its own**, so `cum_price` goes to 1.0 across it and its pre-2021-08-05
  closes revert to raw. The un-adjusted bonus drop then surfaces in `DTIL`'s `close`: the ex-date
  return becomes **≈ −33.5%** (raw 521.15 -> 346.65, i.e. ×0.6652). *(Mind the sign: −33.5% is the
  `DTIL` **close** reverting. The +50% figure elsewhere in this prompt is the `DVL` **`prev_close`**
  cell — a different symbol, a different mechanism. Do not conflate them.)* This is the true state
  of the data: the feed gap, no longer masked by another company's factor. **Do not fix it here.**
  Prompt 4 (BSE corroboration) closes it.

- **P6 — report R1's composition; do not hard-pin it.** Two effects land at once and they interact
  through code this prompt is changing, so **report the full before/after composition rather than
  asserting counts**:
  1. `DTIL`, **if it remains a universe member**, appears as a new move at 2021-08-05. With no
     factor of its own and a CA-shaped ratio it should classify **`CA-shaped-orphan`**
     (`classify_move`, `screening_harness.py:240-252`) → residue 2 -> 3; and being absent from
     `ca_scope_exclusions` it is **undocumented** → halt 1 -> 2 (`KWALITY` + `DTIL`), tripping
     §11.3. **That is expected and pre-authorized by this prompt** — report it, do not disposition
     it, and do not "fix" it.
  2. `load_panel` dedups to one print per `(entity, trade_date)` by turnover (`rn=1`). Today the
     `DPL` entity's series is a **turnover-splice of `DTIL` and `DVL`** — two different companies
     interleaved. Splitting the entity removes the splice, so that entity's price series and its
     move set may change independently.

  Whether `DTIL` is in the panel at all depends on membership (P7): `load_panel` is member-scoped.
  **P6 and P7 are entangled — settle P7 first, then report what R1 actually does.**

- **P7 — STOP AND REPORT.** `entity_turnover` no longer sums `DTIL` + `DVL`, so that entity's
  liquidity falls. If `universe_membership` changes **at all**, **halt and report the diff**. Do
  **not** silently re-cut the universe: CSMP's banked A2 results are computed on it, and whether
  they move is the operator's and the CSMP owner's call, not yours.

If a prediction fails, **STOP and report** — do not adjust the fix until it passes.

### Acceptance

Entity is resolved by `(symbol, trade_date)`; every symbol-date is covered exactly once; the
co-trading assertion passes; the symbol-grain `prev_close` invariant is clean over the whole panel
with every violation enumerated; **P1-P5 confirmed or a failure reported**; **P6 reported as a
before/after composition, not asserted**; the `universe_membership` diff (P7) is reported and **not
acted on**; `audit_corporate_actions.py` and PSB-1 scoring untouched.

### On completion

Commit with prefix `fix(csmp): Prompt 3 —` and report back for Lead Review. Phase 2 remains closed.
Prompt 4 (BSE corroboration screen) is written only after this passes.

---

## Prompt 3 — DISPOSITION (Lead Review 5, 2026-07-14)

**APPROVED. Apply to the real store**, with one amendment. See `PSB1_PHASE1_LEAD_REVIEW_5.md`.

The STOP was correct procedure on a **wrong diagnosis**. Both reported anomalies are adjudicated:

- **Finding A (the "single-name bonus close-return bug") is REJECTED.** `ex_date > trade_date` is the
  standard, correct backward-adjustment convention. **1,043 of 1,106** BONUS/SPLIT ex-dates absorb
  cleanly under it (median residual 3.17%). **Do not touch the close-scaling convention** — the
  proposed fix would have corrupted every one of them. The 63 large jumps are mostly *real*: 51 have
  an open that reconciles with the factor and are genuine ex-date upper-circuit rallies.
- **DVL's +40.2% is a mis-keyed corporate action, not a convention defect.** The NSE CF-CA feed
  attributed **DTIL's** 1:2 bonus to **DVL**. DVL never repriced (`implied_open` = 1.0085; zero >20%
  drops in all of 2021); DTIL repriced exactly ×⅔ on the same date (521.15 → open 330.00, theoretical
  347.4) and BSE carries the correct record (scrip 538902). **Prompt 3 did not introduce this — it
  removed the mask that Prompt 2's entity union had put over it.** P5 is a **pass**.
- **Finding B is benign, and the *check* is what is wrong** — in two ways, not one. Fix the test, not
  the view.

### Amendment before applying

**Fix the P3 invariant** (`repair_entity_intervals.py:59-79`); leave `build_adjusted_view()` alone.
The check's `LAG(...) OVER (PARTITION BY symbol, series)` is mis-specified twice: it crosses the
**entity seam** (recycled ticker) *and* the **series migration** (DTIL trades `BE` 2015-01-20 →
02-03, then `EQ` from 02-04; the exchange's `prev_close` spans `BE → EQ`, a series-partitioned `LAG`
does not). Partition by **entity**, over the **EQ+BE union**, matching exchange semantics.

**Prediction: violations → 0.** Then apply to the real store and commit.

---

## Prompt 4 — CA register evidence audit and re-key

**Runs only after Prompt 3 is applied and committed.** The ordering is forced (Review 4): re-keying
before the entity split would compound DVL's 0.6667 with DTIL's 0.6667 to 0.4444 and halt the build.

### Authorization

`scripts/csmp/ingest_corporate_actions.py` — scoped to `record_evidence_exceptions()` and a new
factor-override path. **`build_adjusted_view()` is OUT OF SCOPE and must not be edited.** PSB-1
scoring and `audit_corporate_actions.py` remain untouched.

### Task 1 — re-key the Dhunseri bonus

Move `(DVL, 2021-08-05, BONUS, 0.6667)` → `(DTIL, 2021-08-05, BONUS, 0.6667)` in
`adjustment_factors`, with the corroborating evidence recorded (BSE scrip 538902 register row + the
price panel). This is a **one-row correction of a confirmed source-feed error**, not a heuristic.
**Do not delete the factor** — deleting fixes DVL and leaves DTIL permanently unadjusted.

- **P1** — DVL's 2021-08-05 adjusted close return goes **+40.2% → ≈ −6.5%** (its raw drift; DVL did
  genuinely go ex a Rs 2.50 dividend that day).
- **P2** — DTIL's 2021-08-05 adjusted close return goes **−33.5% → ≈ 0%** (the bonus is now absorbed).
- **P3** — the `assert_no_double_apply` STOP assertion still passes (DVL and DTIL are now distinct
  entities, so no `(entity, ex_date)` draws a factor from two symbols).

### Task 2 — close the evidence-screen blind spot

`EVIDENCE_TOLERANCE = 0.25` is **relative to `f`**, so a CA that fails to reprice *at all* deviates by
`|f − 1|`, which clears the tolerance only when `f < 0.75`. **Every factor ≥ 0.75 is invisible to the
screen when the corporate action never happened.** Measured: **28 no-reprice CAs sit at `f ≥ 0.75`;
the screen caught 0 of them.**

Add an **absolute** test alongside the existing relative one, separating two distinct questions:

1. **Did the CA happen?** Is `implied_open` closer to **1.0** (no reprice) than to **`f`**?
2. **Is the ratio right?** Given it repriced, how far is `implied_open` from `f`?

These are different defects with different fixes. **AHLEAST (2022-10-06)** is the proof: it *did*
reprice, but by **×0.528** against a registered 0.6667 — the market says 1:1, the register says 1:2.
That is a **wrong ratio**; dropping the factor would leave a real bonus unadjusted.

**Do not apply a blanket rule to the 28.** At `f ≈ 0.909` (a 1:10 bonus) the expected drop is only
~9%, inside the noise of a stock that rallied into its ex-date. **Enumerate them with their evidence
and report; disposition per name.** Only these are unambiguous today:

| symbol | ex_date | f | expected | observed | screen |
|---|---|---:|---:|---:|---|
| SAHPETRO | 2013-07-09 | 0.4524 | −55% | −18% | flagged |
| KWALITY | 2010-06-15 | 0.5833 | −42% | −15% | flagged |
| DVL | 2021-08-05 | 0.6667 | −33% | **+0.8%** | flagged (mis-key — Task 1) |
| **STAMPEDE** | 2017-01-10 | 0.8000 | −20% | **−2.2%** | **MISSED** |

### Task 3 — re-key search (the general mechanism)

When a factor fails the screen, **search for a symbol that *did* reprice by that factor on that
date.** DVL → DTIL would have been caught automatically. The Dhunseri case is one instance of a class,
and a single-source feed with no corroboration is the standing defect (Review 4, Finding 3).

### Task 4 — enumerate the material suspects

**Do not just check OMAXE.** Compute the set directly: **{`f ≥ 0.75` no-reprice suspects} × {universe
membership windows that bracket the suspect's own ex-date}**. That join is the definition of "can
reach the scored panel," and it must be re-run after Task 2 tightens the screen — a suspect the
current screen cannot see may enter the set.

At today's register the join returns **exactly one**:

> **OMAXE, ex 2013-11-11, `f` = 0.7959, `implied_open` = 0.9153** (expected −20%, observed −8.5%) —
> held across its own suspect ex-date at **3 rebalances**.

Every other confirmed-bad CA is immaterial: none holds membership within ±400 days of its bad ex-date,
and **DTIL holds zero memberships ever**, which is why Prompt 3's −33.5% artifact does not contaminate
the panel (and why P6's predicted DTIL halt correctly did not fire). **Report the set; do not
disposition it.**

### STOP rules

- If `universe_membership` changes **at all**, halt and report the diff. CSMP's banked A2 results sit
  on it.
- If a prediction fails, **STOP and report** — do not tune until it passes.
- Report R1's before/after composition; **do not assert counts.**

### Acceptance

The Dhunseri bonus is re-keyed with evidence recorded; the evidence screen detects a no-reprice at any
factor; the `f ≥ 0.75` population is enumerated with per-name evidence and **not** blanket-dispositioned;
OMAXE is reported; `build_adjusted_view()`, `audit_corporate_actions.py` and PSB-1 scoring untouched.

### On completion

Commit with prefix `fix(csmp): Prompt 4 —` and report back for Lead Review.
