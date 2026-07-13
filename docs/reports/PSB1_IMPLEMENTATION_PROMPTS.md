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
