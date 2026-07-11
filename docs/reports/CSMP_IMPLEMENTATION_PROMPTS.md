# CSMP — Implementation Prompts for DeepSeek V4

**Document type:** Implementation briefs. DeepSeek V4 implements; Claude is Lead
Reviewer only (per the locked role split, `CSMP_PHASE0_CHARTER.md` §Phase 0 Decisions).
Gates run strictly in order; each gate's deliverables get a Lead-Reviewer verdict
(PASS / NOT PASSED, findings F1..Fn) before the next gate's prompt is issued.

**Date:** 2026-07-08

**Governing documents (read before implementing anything):**
`docs/reports/CSMP_PHASE0_CHARTER.md` (locked decisions, scope fence);
`docs/reports/MSRP_PHASE7_RESEARCH_RESET_REVIEW.md` §Operator decision;
`CLAUDE.md` (platform conventions).

**Standing constraints for every gate (violations are automatic NOT PASSED):**

1. Zero changes to frozen components, `core/msi/`, the DRA, the execution stack, or
   anything MSRP-sealed. CSMP gate code lives in `scripts/csmp/` (new directory);
   CSMP data lives in `data/market_data/` (new files only); fee code (gate d) lives in
   `core/execution/equity/` with tests in `tests/execution/`.
2. Deterministic, re-runnable scripts — a re-run must reproduce the same store and the
   same audit numbers (idempotent ingestion; no timestamps inside content-bearing
   numbers).
3. Every gate produces a Markdown audit report in `docs/reports/` written by the
   script itself where numbers are involved (the MSRP triage pattern — the report is
   generated, not hand-typed).
4. Report failures as failures. The prior program's gate (a) was returned once for
   silently stopping at 43% coverage and describing the result as complete. If a data
   source is unobtainable for part of the span, the report must say so explicitly and
   quantify the hole — never shrink the target silently.
5. Do not begin the next gate. One gate per prompt; the review happens in between.

---

## Prompt 1 — Gate (a): Equity daily bhavcopy ingestion + quality audit  **(PASSED 2026-07-10)**

> **Status:** PASS — final and unconditional (`CSMP_GATE_A_LEAD_REVIEW.md` Round 8). Final
> evidence: 7,030,920 rows · 4,099 calendar days (4,097 full-session + 2 restricted gold-ETF
> sessions) · 0 coverage holes · 0 unresolved oracle probes · byte-identically reproducible audit.

**Objective.** Ingest NSE cash-market daily bhavcopy for **2010-01-01 → present** into
a dedicated DuckDB store, and produce a quality-audit report proving the store is fit
for cross-sectional momentum research on the NIFTY-200 universe (charter D1/D5).

**Deliverables.**

1. `scripts/csmp/ingest_equity_bhavcopy.py` — downloader + parser + loader.
2. `data/market_data/equity_bhavcopy.duckdb` — table `equity_bhavcopy`:
   `trade_date DATE, symbol VARCHAR, series VARCHAR, open DOUBLE, high DOUBLE,
   low DOUBLE, close DOUBLE, prev_close DOUBLE, volume BIGINT, turnover DOUBLE,
   deliv_qty BIGINT, deliv_pct DOUBLE` — unique on `(trade_date, symbol, series)`.
   Store what the exchange publishes; do NOT adjust prices (adjustment is gate (b)).
3. `scripts/csmp/audit_equity_bhavcopy.py` → writes
   `docs/reports/CSMP_GATE_A_EQUITY_BHAVCOPY_AUDIT.md`.

**Source notes (verify empirically; do not trust these blindly).** NSE has changed
formats over the target span at least twice — treat era detection as a first-class
requirement, exactly like the options UDiFF transition that broke the prior program's
first pass: the legacy `cmDDMMMYYYYbhav.csv.zip` archives (early era), the
`sec_bhavdata_full` daily CSV (adds `DELIV_QTY`/`DELIV_PER`; delivery fields may be
absent or `-` in early years), and the UDiFF common bhavcopy (from ~July 2024). Where a
field does not exist in an era (e.g., delivery quantity), store NULL and disclose the
era boundary in the audit — do not fabricate. Expect NSE archive rate-limiting;
implement polite retry/backoff and a resumable download cache under
`data/market_data/bhavcopy_raw/` so re-runs don't re-fetch.

**Scope filter.** Keep series `EQ` and `BE` only (BE kept because names migrate
EQ↔BE and momentum formation windows must not lose them); drop everything else.
All symbols, not just current NIFTY-200 members — point-in-time membership is gate (c),
and delisted names must exist in this store for survivorship handling to be possible.

**Audit report must contain (minimum):**

1. Coverage: trading days present per year vs the exchange calendar inferred from the
   store itself plus the known-good 1m index calendar (`data/market_data/nse/candles/1m/`
   spans 2023→present — every index trading day must have a bhavcopy day); list every
   missing date with a classification (holiday / source hole / fetch failure).
2. Era map: which source format supplied which date range; field availability by era
   (especially delivery fields).
3. Integrity screens: rows with zero/negative/absent OHLC; high < low; close outside
   [low, high]; duplicate `(trade_date, symbol, series)`; counts per screen and
   disposition (dropped / kept-with-flag).
4. Cross-era continuity: for 20 sampled long-lived liquid symbols (e.g., RELIANCE,
   TCS, SBIN…), numeric check that `prev_close(t) == close(t−1)` holds within
   tolerance across era boundaries; violations counted and explained (corporate actions
   will legitimately break this — count them, gate (b) resolves them).
5. Symbol-rename inventory: NSE's symbol-change list ingested to a `symbol_changes`
   table (old symbol, new symbol, effective date) — obtainable from NSE's published
   symbol-change file; if genuinely unobtainable, say so and list the alternative
   (this feeds gates (b)/(c); it is inventory here, not application).
6. Headline: total rows, distinct symbols, span, store size, and an explicit
   **fit-for-purpose statement** scoped to what gate (a) can honestly claim.

**Stop condition.** If any contiguous ≥ 3-month hole in 2010→present cannot be filled
from any official source, stop and report — the dev-window start (D5: dev from 2012-01,
formation runway from 2010) may need operator adjustment; that is an operator call, not
an implementer improvisation.

**Definition of done.** Both scripts run clean end-to-end on a fresh checkout; the
audit report regenerates with identical numbers; the six audit sections above are
present; no frozen-component diffs; no next-gate work started.

---

## Prompt 1R — Gate (a) remediation: close G4/G5/G8  **(CLOSED 2026-07-10)**

> **Status:** CLOSED — all acceptance criteria met over Rounds 5–7; gate (a) reached PASS at
> Round 7 (confirmed final at Round 8). The context paragraph below reflects the Round-4 state
> at time of issuance and is retained as history.

**Context.** Gate (a) is NOT PASSED (Round 4, `CSMP_GATE_A_LEAD_REVIEW.md`). The 2022→2024H1
gap was an operator ingest-range mistake and is now backfilled; the store is contiguous
(7,017,254 rows / 4,090 trade dates). The F&O oracle and the coverage-hole logic are **sound**
— Round-3 finding G2 was retracted, and G1 downgraded to MINOR. Three defects remain. Fix
exactly these; do not redesign the calendar, the oracle, or the era-preference order.

**Do not touch** `data/market_data/nse/candles/1m/` — two corrupt files there
(`2026-02-01.duckdb`, `2026-03-03.duckdb`) are a separate ticket, outside gate (a)'s fence.
Gate (a)'s job is to stop *trusting* them, not to repair them.

---

### G8 (MAJOR) — Sunday sessions are structurally unreachable

`date_range()` in `ingest_equity_bhavcopy.py` yields Mon–Sat (`d.weekday() < 6`). NSE holds its
Diwali **Muhurat** session on a Sunday in some years, so those days can never be fetched and the
oracle is never asked about them.

**Verified — four Sunday Muhurat sessions, all absent from the store, none ever fetched:**

| Date | In store | In calendar | Fetch marker |
|---|---|---|---|
| 2013-11-03 | no | no | none |
| 2016-10-30 | no | no | none |
| 2019-10-27 | no | no | none |
| 2023-11-12 | no | **yes** (`index_1m`) | none |

Only 2023-11-12 is visible to the current audit, because `index_1m` starts in 2023. The other
three are silent. `2023-11-12.duckdb` holds **11,581 bars across 194 symbols, 18:15–19:14** —
the Muhurat signature; the control `2024-11-01` (Muhurat, a Friday) is 11,640 bars / 194
symbols / 18:00–18:59 and **is** in the store.

**Fix.** Extend `date_range()` to all seven days. Let the oracle adjudicate — it 404s cheaply on
true non-trading days and those `.404` markers are already cached, so the added cost is one
probe per Sunday, once. Do not special-case Muhurat dates by hand; a hardcoded list is the same
class of error as the weekday assumption.

---

### G4 (MAJOR) — holiday requests silently ingest the previous day's file

`_valid_body()` validates the response's **shape** (`SYMBOL…SERIES` header), never its
**identity**. NSE answers a holiday request with HTTP 200 carrying the *previous trading day's*
CSV. `parse_secfull()` then takes `trade_date` from the file's own `DATE1` column, so the rows
upsert onto the previous day, while `ingest_day()` sees `n > 0` and writes an `ingest_meta` row
keyed to the **requested** date.

**Verified:** `secfull_20241225.csv` → `DATE1 = 24-Dec-2024`; `secfull_20210126.csv` →
`25-Jan-2021`; `secfull_20260303.csv` → `02-Mar-2026`; `secfull_20231114.csv` (Diwali holiday)
is cached likewise. Result: `ingest_meta` holds `legacy` 2,475 + `secfull` 1,694 = **4,169
dates against 4,090 stored dates — 79 phantom entries.** §2's "Trade days" column is wrong and
the eras do not sum to the store's date count. It also makes the report self-contradictory:
2026-03-03 appears in §1 as a coverage hole and in §2 as a successful `secfull` day.

**Fix.**
1. After parsing, assert every row's `trade_date` equals the **requested** date. On mismatch,
   discard the payload and treat the date as `confirmed-absent` (holiday) — not a successful
   ingest, and do **not** write the rows to a different date.
2. Write `ingest_meta` only for dates that actually received rows.
3. Apply the same assertion to `parse_udiff` (`TradDt`). `parse_legacy` takes `trade_date` from
   the requested date directly, so it is not exposed — leave it alone, but verify that claim
   rather than assuming it.

---

### G5 (MODERATE) — `index_1m` is trusted by filename

`index_trading_days()` derives trading days from `*.duckdb` **stems** and never opens the file.
This produced two false holes — and also caught the real Muhurat hole that nothing else would
have. So **validate `index_1m`; do not remove it.**

**Verified misclassifications:**

| File | Contents | Correct verdict |
|---|---|---|
| `2026-02-01.duckdb` | 375 bars, **1 symbol** (`NSE_INDEX\|Nifty Bank`), Sunday 09:15–15:29 | not a trading day (backfill artifact) |
| `2026-03-03.duckdb` | 197 bars, **all timestamped `2026-03-02`** | not a trading day (Holi) |
| `2023-11-12.duckdb` | 11,581 bars, 194 symbols, all stamped `2023-11-12` | **trading day** (Muhurat) |

**Fix.** Open each file and accept the date as a trading day only if both hold:
(a) the bars' own date — `CAST(timestamp AS DATE)`, not the filename — equals the filename date;
(b) the file carries a plausible cross-section (**≥ 100 distinct symbols**).
All three rows above fall out of those two rules. Note the 1m files are **not cleanly
date-partitioned** in general (`2026-03-04.duckdb` contains 2026-03-02 bars), so rule (a) must
filter bars by date, not assume the file is homogeneous.

---

### G1 (MINOR) — disclose calendar provenance

Add to audit §1 a one-line source mix for `trading_calendar` (`equity_store` / `fo_probe` /
`index_1m` counts). This is **disclosure, not a defect**: `equity_store` rows only exclude a day
from probing, and a day present in the store cannot be a coverage hole by definition. The reader
should nonetheless see how much of the calendar is independently corroborated.

---

### Backfill the confirmed holes

Re-ingest **2022-08-08** and **2023-11-12**, plus whatever G8 surfaces (expect **2013-11-03,
2016-10-30, 2019-10-27**). 2022-08-08 is a genuine trading day: the oracle already downloaded
`focal_20220808.zip`, and no `secfull_*`/`legacy_*` marker exists for it — the equity ingest
never attempted the date.

---

### Acceptance criteria (falsifiable — the review will check these exact numbers)

1. `date_range()` covers all 7 weekdays; no hardcoded Muhurat list.
2. Store gains **at least** 2022-08-08 and the four Sunday Muhurat sessions (2013-11-03,
   2016-10-30, 2019-10-27, 2023-11-12) ⇒ **≥ 4,095 distinct trade dates**. If any of those five
   cannot be sourced, the audit must **name it and quantify it** (standing constraint 4) — a
   silently smaller target is an automatic NOT PASSED.
3. `ingest_meta` date count **equals** `COUNT(DISTINCT trade_date)` in `equity_bhavcopy`. The 79
   phantoms are gone; `secfull` days fall from 1,694 to ≈1,615 before the backfill adds days.
   §2's era days must sum to the store's date count.
4. Audit reports **0 coverage holes**, and `2026-02-01` / `2026-03-03` no longer appear as holes.
5. §1 shows the calendar source mix.
6. Re-running the audit against an unchanged store reproduces the report byte-for-byte.
7. No diffs outside `scripts/csmp/` and `docs/reports/`. In particular, no writes to
   `data/market_data/nse/candles/1m/`.

**Definition of done.** All seven criteria hold; the audit's own fit-for-purpose statement reads
PASS-eligible on its own numbers; no next-gate work started. Gate (b) stays HELD until the Lead
Reviewer signs off on the regenerated report.

---

## Prompt 2 — Gate (b): Corporate-action adjustment + audit  **(PASSED WITH DOCUMENTED EXCEPTIONS 2026-07-10)**

> **Final status (2026-07-10): PASSED WITH DOCUMENTED EXCEPTIONS** after Round 5
> (`CSMP_GATE_B_IMPLEMENTATION_R5.md`). The move screen inherits gate (a)'s H2 non-equity
> exclusion now, implemented by ISIN (new `symbol_isin` table); dev-window residue is **6
> documented, 0 undocumented** (gate criterion is mechanical: undocumented dev-window residue
> must be 0); adjusted ex-date continuity 0; 4 evidence-test failures report, not block
> (`ca_evidence_exceptions`); demergers carried into gate (c) via `ca_scope_exclusions`.
> **Independence caveat: Claude wrote R4 and implemented R5 against it; operator waived review.**
> Gate (c) inherits `symbol_isin`, `symbol_changes`, `ca_scope_exclusions`, and the residual
> `ICICIMOM30` instrument-master gap. The Round-history blockquote below is retained as record.
>
> **Status:** Round 1 NOT PASSED — REJECTED (structural), `CSMP_GATE_B_LEAD_REVIEW.md`.
> The BSE response tables were misidentified (all 9,004 "SPLIT" events are dividends; 8,840
> rupee amounts became price factors; adjusted view distorted up to 5,940×), no real split
> source was ingested, and 51% of the move screen compared against stale prev-closes.
> **Round 2 NOT PASSED — REJECTED (still structural)**, `CSMP_GATE_B_LEAD_REVIEW_R2.md`.
> R1/R3(convention)/R5/R7 landed and the store is sane. But splits were reconstructed from
> the price gaps they then explain (105/105 self-explaining), the adjusted view's
> `prev_close` is mis-scaled on every ex-date row, and direction-only matching hides missing
> split legs (TITAN pre-2011 wrong by 10×, reported as *explained*).
> Remediation brief: **Prompt 3R** below. This prompt's objective, constraints, and audit
> sections remain binding; 3R narrows the work to the findings.

**Objective.** Source split / bonus / face-value-change (and material rights) events for
every symbol in the gate-(a) store, build a traceable `adjustment_factors` table, expose a
deterministic **adjusted-price view** that all downstream CSMP research will consume, and
produce an audit proving that every large single-day raw move in 2010→present is classified
— with **zero unexplained residue in the dev window** (2012-01 → 2022-12).

**Why this gate exists.** Raw momentum is corrupted by corporate actions: a 1:1 bonus looks
like a −50% return and destroys a 12-1 formation window. The charter (§5-b) makes unexplained
residue a gate failure. This is where equity cross-section research quietly dies; it gets a
Lead-Reviewer pass for exactly that reason.

**Inherited constraints from gate (a) (binding):**

- **Raw stays raw.** `equity_bhavcopy` (7,030,920 rows) must not be modified — no UPDATE, no
  DELETE, no added columns. Adjustment lives in new tables and a view.
- **Full sessions only for day-pair logic.** `trading_calendar.n_symbols` is present and
  verified. The move screen pairs a day with the **previous full session** (`n_symbols ≥ 200`);
  the two restricted gold-ETF sessions (2010-05-16, 2012-11-11) must not create phantom
  multi-day returns. Disclose how they are handled.
- **Rename chains.** `symbol_changes` (1,050 records, inventory from gate (a)) must be applied
  to link price series across renames (e.g., INFOSYSTCH → INFY) so an entity's series is
  continuous. Disclose chain counts, unmatched entries, and any ambiguous/multi-hop chains.
- **Process rule (all gates):** a validator that has never returned its positive verdict has
  not been tested; a number may not stand in for the evidence it summarizes. The audit must
  *show* payloads (event rows, source lines) for its claims, not counts alone.

**Deliverables.**

1. `scripts/csmp/ingest_corporate_actions.py` — downloads/parses CA events into
   `data/market_data/equity_bhavcopy.duckdb` (same store, **new tables only**):
   - `corporate_actions` — the raw event inventory as published:
     `symbol VARCHAR, ex_date DATE, action_type VARCHAR, purpose_raw VARCHAR,
     ratio_or_fv VARCHAR, source VARCHAR` (keep the exchange's own purpose text — it is the
     evidence the factor is derived from).
   - `adjustment_factors` — one row per price-affecting event:
     `symbol VARCHAR, ex_date DATE, factor DOUBLE, action_type VARCHAR, source VARCHAR`,
     unique on `(symbol, ex_date, action_type)`; every row derivable from a
     `corporate_actions` row.
   - Raw downloads cached under `data/market_data/corporate_actions_raw/` (resumable,
     polite backoff — same contract as gate (a); validate body *shape and identity* before
     caching: gate (a)'s G4 lesson, NSE serves wrong-content 200s).
2. **Adjusted view** `equity_bhavcopy_adjusted` in the same store — raw OHLC/prev_close
   multiplied by the cumulative backward adjustment factor, volume inversely adjusted.
   State the convention explicitly in the audit (backward adjustment: post-event prices
   unchanged, pre-event prices scaled to comparability) and derive the factor arithmetic for
   each action type from a cited primary source — do **not** improvise ratio conventions
   (a "1:1 bonus" and a "1:1 split" imply different factors; get this from the source, show
   the arithmetic in the audit, and hand-verify it on named events).
3. `scripts/csmp/audit_corporate_actions.py` → writes
   `docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md` (generated, deterministic,
   byte-identical on re-run against an unchanged store).

**Source notes (verify empirically; do not trust blindly).** NSE publishes corporate-action
data (the CF-CA / corporate-actions download on nseindia.com and its archives); coverage back
to 2010 must be **verified, not assumed** — if the official NSE feed thins out pre-~2015,
candidate supplements are the NSE circulars archive and BSE's corporate-action download for
dual-listed names (disclose any non-NSE source per event). Expect rate-limiting and
wrong-content 200s. Scope: events for symbols present in the gate-(a) store only; events
outside 2009-07 → present are irrelevant (no store prices to adjust).

**Dividends.** No adjustment factor for ordinary cash dividends (raw-price momentum is the
charter construct; D3's total-return metric is a Phase-1 concern, out of scope here). But
**large special dividends can move a price ≥ 20%** — ingest dividend events into
`corporate_actions` as classification inventory (`action_type = 'DIVIDEND'`, factor row
**only if** you adopt and disclose a materiality rule), so a big ex-div drop is *explained*,
not left as residue.

**Sealed-window discipline.** The move screen runs mechanically over 2010→present — that is
data hygiene, not research. No return statistics, no signal work, no tuning decisions may be
derived from the sealed window (2023-01 → 2026-06). The residue **gate** applies to the dev
window; sealed-window residue is reported as a count, unexamined beyond classification.

**Audit report must contain (minimum):**

1. **Event inventory:** events by `action_type` by year, 2010→present; symbols affected;
   join rate against store symbols (rename-chain-aware); unmatched events listed.
2. **Factor derivation:** the arithmetic per action type with primary-source citation, and
   **≥ 10 hand-verified events** spanning eras and action types (split, bonus, FV change,
   rights if any): event row → factor → raw close before/after → adjusted continuity, shown
   numerically in the report.
3. **Move-classification screen (the gate):** every single-day raw close-to-close move
   ≤ −20% or ≥ +25% between consecutive full sessions, 2010→present, classified
   **corporate-action-explained / genuine / data-error**, with counts by year, by class, and
   by window (dev / sealed). **Unexplained residue in the dev window must be 0**; each
   sealed-window residue counted. The classifier's **positive verdict must be demonstrated**:
   show at least one known split it catches, at least one genuine large move it correctly
   leaves unadjusted, and the full payload rows for the 10 largest moves in each class.
4. **Adjusted continuity:** re-run gate (a)'s 20-symbol `prev_close(t) == close(t−1)` check
   **on the adjusted view**. Gate (a) found 0 raw glitches (NSE publishes raw prev_close), so
   the adjusted check verifies the *factors*: every corporate-action break in the raw
   close-to-close series must vanish under adjustment; any that survives is named and
   explained.
5. **Rename-chain report:** chains applied, entities linked, ambiguities, and the effect on
   series length for the affected continuity symbols (e.g., INFY pre/post 2011-06-29).
6. **Headline + fit-for-purpose statement** scoped to what gate (b) can honestly claim, with
   the same withholding discipline as gate (a) (the claim is withheld, not softened, if any
   gate criterion is unmet).

**Stop condition.** If official corporate-action event data cannot be obtained for the dev
window — or any contiguous ≥ 6-month span of it — from any official source, **stop and
report**, quantifying the hole (standing constraint 4). Equally: if dev-window unexplained
residue cannot be driven to zero, that is a reported NOT-PASSED state for the operator — not
a threshold to be quietly widened.

**Acceptance criteria (falsifiable — the review will check these exact claims):**

1. `equity_bhavcopy` is bit-unmodified: same row count (7,030,920) and same content as at
   gate (a) PASS.
2. Every `adjustment_factors` row is traceable to a `corporate_actions` row and its cited
   source; no orphan factors.
3. The move screen exists with the exact thresholds above, pairs only full sessions, and
   reports **dev-window unexplained residue = 0** (else the audit itself must render the
   NOT-PASSED / stop language).
4. The adjusted 20-symbol continuity check shows every raw CA break resolved; residuals named.
5. ≥ 10 hand-verified events with arithmetic shown in the report body.
6. Re-running the audit against an unchanged store reproduces the report byte-for-byte.
7. No diffs outside `scripts/csmp/`, `docs/reports/`, and `data/market_data/` (new
   files/tables only). No writes to `data/market_data/nse/candles/1m/`. No frozen-component
   diffs. No gate-(c) work (ETF exclusion, universe membership) — H2 is recorded for gate (c),
   ETFs remain in the adjusted panel here.

**Definition of done.** Both scripts run clean end-to-end on a fresh checkout against the
gate-(a) store; the six audit sections are present; all seven acceptance criteria hold; the
audit's fit-for-purpose statement is PASS-eligible on its own numbers; no next-gate work
started. Gate (c) stays HELD until the Lead Reviewer signs off.

---

## Prompt 2R — Gate (b) remediation: F1–F9  **(CLOSED 2026-07-10 — partially met; superseded by Prompt 3R)**

> **Outcome.** R1, R3 (convention half), R5, R7 met. R2 **violated its own prohibition** —
> bhavcopy gap reconstruction was used *as* the split source, which R2 §3 expressly forbids
> ("it validates a source, it is not a source"). R3's assertion half was specified wrongly by
> the Lead Reviewer (see T4 below) and is retracted. R4 applied to splits only. R8's test was
> built correctly, exposed a real view bug, and the bug was left unfixed. R9's sidecar was
> emitted unclassified. Acceptance criteria **3 (factor-vs-gap concordance, full population)**
> and **4 (R8 over the full factor population)** were never delivered — criterion 3 is exactly
> the check that would have caught the TITAN-class errors. Retained below as history.

**Context.** Gate (b) Round 1 is NOT PASSED — REJECTED (`CSMP_GATE_B_LEAD_REVIEW.md`). The
failure is structural: BSE's `CorporateAction/w` response tables were misidentified, so the
entire SPLIT inventory is dividends and the adjusted view is unusable (RELIANCE Jan-2012
adjusted close = 5,940× raw). One component is verified sound and must be preserved: the
**bonus pipeline** (`Table1` → `issue B:E` → factor `E/(E+B)`), which correctly explains all
423 CA-explained moves. The raw JSON cache under `data/market_data/corporate_actions_raw/`
is intact — **F1/F4/F6/F8/F9 need no re-download**; only the new split source (F2) and the
ETF patch list fetch anything. All Prompt-2 standing constraints remain binding.

**Operator decision — LOCKED (2026-07-10): special dividends adjust above a 20% threshold.**
A cash dividend whose amount is ≥ 20% of the close on the last full session before its
ex-date is price-affecting and receives an adjustment factor; below the threshold no factor
(ordinary-dividend rule unchanged). Details in R6.

Fix exactly the findings below; do not redesign what passed review (bonus parsing, the raw
cache discipline, the report-generated-by-script pattern).

---

### R1 (F1, CRITICAL) — reclassify the BSE tables; purge the fake splits

Empirical table identity (verified from `raw_json` in review):
`Table` = **dividends keyed by record date** (`BCRD_FROM`, `Amount`);
`Table1` = **bonuses** (`XTYPE: 'Bonus'`, `VALUE: 'issue B:E'`);
`Table2` = **dividends keyed by ex-date** (`Ex_date`, `Details`, `purpose`).

1. Delete every `action_type='SPLIT'` row from `corporate_actions` and `adjustment_factors`
   (all 9,004 / 8,840 are misparsed dividends).
2. Re-parse the cached `bse_ca_*.json` with the corrected mapping. Use `Table2` as the
   dividend inventory of record (it carries the true ex-date); keep `Table` rows only if
   they add events absent from `Table2` after dedupe (R5).
3. In `derive_factor()`, **delete the plain-float fallback entirely** — a bare number can
   never safely define a split ratio; it is how ₹974 became a 974× price factor. An
   unparseable ratio is a reported parse failure, not a guess.

### R2 (F2, CRITICAL) — source real splits (none were ingested)

The `CorporateAction/w` endpoint has no sub-division table; 16 years of real splits are
missing and their −50%..−90% gaps sit in the raw panel unadjusted (~880 tight-gap
−40%..−85% single-session drops were counted in review). Source them from an official feed;
candidates in order of structure:

1. BSE's corporate-actions listing API backing
   `bseindia.com/corporates/corporates_act.html` (accepts purpose filters incl.
   sub-division and date ranges).
2. NSE's CF-CA corporate-actions archive CSV (nsearchives), rename-chain-aware join.
3. Bhavcopy reconstruction as **cross-check only** (a symbol-day where
   `prev_close/close(t−1)` clusters at 2/5/10/25 with volume scaling) — it validates a
   source, it is not a source (standing constraint: official provenance per event).

Also ingest the **ETF unit-split patch list** — the review-identified events (GOLDBEES
2019-12-19, AXISGOLD 2020-07-23, HDFCMFGETF 2021-02-17, GOLDSHARE 2021-03-25, BSLGOLDETF
2021-11-25, QGOLDHALF 2021-12-16, SETFGOLD 2022-01-06, plus sealed-window LICMFGOLD
2026-03-06 and IVZINGOLD 2026-04-30, and any others the fixed screen surfaces). Derive each
ratio from the exchange/AMC notice, cite it in `source`, and confirm it against the raw
price step (all reviewed cases are ~1:100). ETFs stay in the adjusted panel (H2/exclusion
is gate (c)).

### R3 (F8 + F5, MAJOR) — correct the split factor convention; make hand-verification assert

Backward adjustment scales **pre-event prices down** for a sub-division: FV `old → new`
multiplies shares by `old/new` and divides price by `old/new`, so the factor applied to
pre-ex prices is `new/old` (FV 10→1 ⇒ 0.1) — the current `derive_factor` returns the
inverse. The bonus branch (`E/(E+B)`) and the volume treatment (`volume / cum_factor`) are
correct; leave them. Fix the §2 prose (it currently contradicts itself within one
sentence).

The §2 hand-verify section must **assert, not display**: for each of the ≥ 10 events,
`adjusted_before ≈ raw_close_after` within a tolerance that allows the day's genuine market
move (±10%); any violation fails the audit run loudly. Round 1 printed RELIANCE
"SPLIT 6.0" with no raw gap and a fabricated 6× adjusted discontinuity under the heading
"hand-verified" — the assertion makes that structurally impossible.

### R4 (F6, MAJOR) — ex-date, not record date

`BCRD_FROM`/`BCRD` are record dates; pre-2023 the ex-date precedes the record date by ≥ 1
session. Rules: dividends take `Table2.Ex_date` directly; bonuses (and splits, if the R2
source gives record dates) derive the effective ex-date by locating the raw price gap
within `[record_date − 5, record_date]` in the bhavcopy — deterministic and self-auditing.
Report the offset distribution and every event where no gap could be located (those events
carry no factor and are listed, not guessed).

### R5 (F7, MEDIUM) — dedupe the dividend inventory

`Table` and `Table2` carry the same dividend events (1,013 exact same-date mirrors; more
offset by record-vs-ex date). Dedupe on `(symbol, amount, date within ±7d)`, preferring the
`Table2` record. The special-dividend rule (R6) runs on the deduped inventory only.

### R6 (operator decision, LOCKED) — special-dividend adjustment at the 20% threshold

For each deduped dividend event: let `P` = close on the last **full session** strictly
before the ex-date, `D` = dividend amount.

- **If `D ≥ 0.20 × P`:** price-affecting. Insert an `adjustment_factors` row with
  `action_type='SPECIAL_DIVIDEND'`, `factor = (P − D) / P`, applied to pre-ex prices like
  any backward factor. If `D ≥ P` (data error), no factor — flag the event in the audit.
- **If `D < 0.20 × P`:** no factor (unchanged ordinary-dividend rule; raw-price momentum is
  the charter construct).
- **Volume is NOT adjusted for dividends** — share count is unchanged. The adjusted view
  must therefore maintain **separate cumulative factors for price and volume** (volume
  factor = 1.0 for SPECIAL_DIVIDEND rows, `factor` for share-count-changing rows). This is
  a required change to the `equity_bhavcopy_adjusted` view definition.
- Disclose in the audit: threshold, count of SPECIAL_DIVIDEND factors by year, and the full
  payload for the 10 largest. **MAJESCO 2020-12-23 must appear** (P=985.65, D=974,
  factor ≈ 0.0118).

### R7 (F3, CRITICAL) — fix the move screen: no stale prev-closes

The Round-1 `LAG` over EQ-only rows spanned BE-series migrations and suspensions: 3,314 of
6,486 screened "moves" (51%) used a prev close > 7 days old (KOVAI: 3,909 days). Fix:

1. Compute prev close over the symbol's **EQ+BE union** (series migration is not a price
   event).
2. A row enters the move screen **only if** its lagged `trade_date` is the immediately
   preceding full session (gap ≤ 5 calendar days covers long weekends).
3. Rows failing the gap rule are reported in a separate **resumption/migration section**
   (counts + the 20 largest, payloads shown) — they are not returns and must not appear in
   the classification counts.

### R8 (F4, MAJOR) — make the adjusted-continuity check test the factors

Round 1 skipped ex-date rows — the only rows where adjustment acts — so its "0 residual"
was vacuous truth. Fix: at every ex-date row `t` of each sampled symbol, assert
`adj_prev_close(t) ≈ adj_close(t−1)` within 0.1% — the adjustment must *close* the raw gap.
Off-ex-date rows remain the trivial case. Every surviving mismatch is named with payload.
Run it on all 20 continuity symbols **plus** every symbol carrying a SPECIAL_DIVIDEND or
split factor (full population, not a sample — this is the factor-correctness gate).

### R9 (F9, MINOR) — report hygiene

(a) Move the full classification table to a sidecar
`docs/reports/CSMP_GATE_B_MOVES.csv`; the MD keeps residue rows, the 10 largest per class,
and the resumption section — target well under 100 KB (Round 1 was 560 KB).
(b) Replace the `len([l for l in L if str(td) in l]) < 200` row cap with a plain counter.
(c) Reconcile prose with code: the classification window is one value used everywhere
("7 calendar days" or tighter — pick and state it).
(d) Compute the unmapped-symbol count; delete the stale "~967" from the scope note.
(e) Fix the §3 preamble variable (`RESTRICTED_THRESHOLD`, not `MOVE_LO` — it currently
renders "< -20% symbols").
(f) Delete dead code (`full_set`, unused `timedelta`, unused `--start`/`--end` args).

---

### Acceptance criteria (falsifiable — the review will check these exact claims)

1. `equity_bhavcopy` bit-unmodified: 7,030,920 rows, content identical to gate-(a) PASS.
2. `adjustment_factors` contains **zero** rows derived from a bare-float ratio or a
   dividend `Amount`; every factor's `purpose_raw` is split/bonus/special-dividend
   evidence. `action_type` ∈ {BONUS, SPLIT, SPECIAL_DIVIDEND} (FV-change-without-split
   events carry no factor row or factor = 1.0, disclosed either way).
3. **Factor-vs-gap concordance table in the audit:** for every factor (full population),
   the raw ex-date gap vs `factor`; ≥ 95% within ±15% (genuine same-day market moves
   explain the tail); every miss named with payload. Round 1's equivalent was 0/200.
4. The R8 continuity check visits every ex-date row and reports **0 unresolved residuals**;
   the §2 hand-verify assertions pass in-run.
5. The move screen pairs only consecutive full sessions; the resumption/migration section
   exists; **dev-window unexplained residue = 0** — specifically, the Round-1 fourteen
   resolve as: 7 ETF rows CA-explained (patch list), MAJESCO CA-explained
   (SPECIAL_DIVIDEND), and SBC / UVSL / LCCINFOTEC / KOVAI / RUCHI / VISESHINFO out of the
   classification counts and into the resumption section. Sealed-window residue reported
   as a count, unexamined.
6. The audit MD is regenerated byte-identically on re-run against an unchanged store, cites
   the sidecar CSV, and is < 100 KB.
7. No diffs outside `scripts/csmp/`, `docs/reports/`, and `data/market_data/` (new
   files/tables/view changes only). No writes to `data/market_data/nse/candles/1m/`. No
   frozen-component diffs. No gate-(c) work.

**Definition of done.** All seven criteria hold; the regenerated audit's fit-for-purpose
statement is PASS-eligible on its own numbers (or renders the stop language per standing
constraint 4 if the R2 split source proves unobtainable for the dev window — that is an
operator report, not a threshold widening); no next-gate work started. Gate (c) stays HELD
until the Lead Reviewer signs off on the regenerated report.

---

## Prompt 3R — Gate (b) remediation: C1–C3, H1–H3, M1–M3, L1–L2  **(ISSUED 2026-07-10)**

**Context.** Gate (b) Round 2 is NOT PASSED — REJECTED (`CSMP_GATE_B_LEAD_REVIEW_R2.md`).
Round 1's catastrophic defects are genuinely fixed and **must be preserved**: the BSE table
mapping (`Table`=dividend/RD, `Table1`=bonus, `Table2`=dividend/ED), the purge of the 9,004
fake splits, the deleted plain-float fallback, the split factor convention (`new_FV/old_FV`),
the dividend dedupe, and the EQ+BE / gap ≤ 5d move screen with its resumption section. The
**bonus pipeline remains the one fully sound component** (888/888 factors from the independent
BSE feed). Do not redesign any of it.

Three defects make the adjusted view unusable, all introduced by the R2 remediation itself.
Fix exactly the findings below. All Prompt-2 standing constraints remain binding.

**One retraction, owned by the Lead Reviewer.** Prompt 2R's R3 instructed
`assert adjusted_before ≈ raw_close_after`. That assertion is **mathematically wrong** and is
withdrawn — it holds only for a symbol's most recent event, because `adj_before` carries the
product of *all* future factors while `raw_after` carries none. The 4 reported hand-verify
FAILs are artifacts of that brief, not data defects. The correct assertion is in T4. DeepSeek
implemented the specification faithfully; the specification was at fault.

---

### T1 (C1, CRITICAL) — the split source is circular; purge it

`ingest_splits_from_bhavcopy()` infers a SPLIT wherever `prev_close/close` snaps to
{2,5,10,25,50,100,200,500,1000} with volume scaling. §3 then calls a move *CA-explained* when
any factor < 1 exists within 7 days. The evidence set and the explanation set are the same
rows: **105 of 105 gap-inferred splits sit exactly on a move the screen flags.** Prompt 2R §R2
already ruled this out in terms — *"Bhavcopy reconstruction as **cross-check only** … it
validates a source, it is not a source."* The verdict is unchanged and not negotiable.

Verified false positives (all at the ₹0.10 → ₹0.05 tick floor, all assigned factor 0.5):

| Symbol | Ex-dates | Reality |
|--------|----------|---------|
| VISESHINFO | 2016-03-10, 2016-06-15, 2016-06-29, 2019-02-18, 2019-04-11, 2019-08-07 | six "splits"; pre-2016 history divided by 2⁶ = 64 |
| MVL | 2019-10-09 **and** 2019-10-11 | two splits in two days — physically impossible |
| UVSL | 2020-03-17 | penny tick |
| SRPL-**RE** | 2023-07-21 | a rights entitlement, not a share line |

26 gap-splits have `prev_close < ₹25`. **73 of 112 splits have no corroborating BSE row of any
kind.**

**Do:**
1. Delete every `adjustment_factors` row with `source LIKE 'bhavcopy_gap%'` (105 rows) and
   their `corporate_actions` events. Delete the `ingest_splits_from_bhavcopy()` function.
2. Source splits from an official feed. Candidates, in order: BSE's corporate-actions listing
   API behind `bseindia.com/corporates/corporates_act.html` (purpose filter includes
   sub-division); NSE's CF-CA archive CSV (`nsearchives`), rename-chain-aware join.
3. A price gap may **locate** an ex-date for a sourced event (T3's snap rule). It may never
   **establish** that an event occurred.

**If no official split source can be obtained — STOP AND REPORT (standing constraint 4).**
Round 2 asserted *"official feed unobtainable (R2 option 3)"* with no evidence and silently
substituted inference. That is the exact failure mode constraint 4 exists to prevent. To claim
unobtainability you must show, in the audit: the endpoints attempted, the HTTP status/response
bodies, and the date ranges probed. Then stop — the fallback is an **operator decision**
(candidates: restrict the universe to names whose splits are enumerable and hand-verifiable,
or exclude affected symbol-dates), not an implementer improvisation.

### T2 (C2, CRITICAL) — `equity_bhavcopy_adjusted.prev_close` is wrong on every ex-date row

The view scales `open/high/low/close` on row `t` by `cum_price_factor(t)` — events with
`ex_date > trade_date`. That is correct backward adjustment (verified: RELIANCE adj 411.35 →
409.05 across its 2017 bonus, a genuine 0.6% move). It then scales `prev_close(t)` by the
**same** factor. But `prev_close(t)` *is* `close(t−1)`, whose correct cumulative factor also
includes the event **at** `t`. Raw bhavcopy `prev_close` is unadjusted (verified: RELIANCE
2017-09-07 raw prev_close = 1,645.40 = the prior raw close), so nothing compensates.

Result: `adj_prev_close(t) = adj_close(t−1) / F_t` — off by exactly the ex-date factor. R8's
check measured this correctly and reported **22 mismatches** (RELIANCE 822.70 vs 411.35; INFY
1,434.25 vs 717.12; ASIANPAINT 5,118.20 vs 511.82). These are real defects in the authoritative
research view. The Round-2 commit message does not mention them.

**Do:** scale `prev_close(t)` by `cum_price_factor(t) × F_t` where an event exists at `t`
(equivalently, by the cumulative factor of the previous trading row). Then R8/§4 becomes a true
regression test and **must read 0**. Do not weaken the 0.1% tolerance to make it pass.

### T3 (C3, CRITICAL) — require magnitude agreement, not sign agreement

§3 labels a move CA-explained on `factor < 1 and ret < 0` — any factor, any magnitude, within
7 days. It never asks whether the factor *accounts for* the move. **48 of 569 CA-explained
moves (8%) deviate > 15pp from the drop their factor implies:**

| Date | Symbol | Observed | Factor-implied | Factor | Reality |
|------|--------|---------:|---------------:|-------:|---------|
| 2011-06-23 | TITAN | −94.7% | −50.0% | 0.5 (bonus) | 1:1 bonus **+ 1:10 split**; split leg absent |
| 2016-12-01 | SUNILHITEC | −94.7% | −50.0% | 0.5 | combined action, one leg absent |
| 2024-04-04 | CUPID | −94.8% | −50.0% | 0.5 | combined action, one leg absent |
| 2010-07-29 | MMTC | −93.9% | −50.0% | 0.5 | combined action, one leg absent |
| 2023-06-05 | HARDWYN | −91.8% | −25.0% | 0.75 | combined action, one leg absent |
| 2016-08-11 | KTIL | −50.9% | −3.8% | 0.9615 | a −51% move "explained" by a 3.8% bonus |

TITAN's pre-2011 adjusted prices are wrong by **10×** and the audit counts it toward the
CA-explained total. This is precisely the failure R2 was meant to eliminate, now hidden behind
a green label. Note the gap detector **cannot** catch these: a combined bonus+split gap does not
snap to an integer split ratio (TITAN's 18.9× fails the 15% cluster tolerance), so T1's deleted
method was structurally blind to exactly the events T3 exposes.

**Do:**
1. Label a move CA-explained only when `|ret − (product of same-day factors − 1)| ≤ 0.15`.
   Where several factors share an ex-date, multiply them — combined bonus+split is the
   *common* case, not an edge case.
2. Emit a third bucket, **`incomplete-adjustment`**: direction matches, magnitude does not.
   Every such row is a missing or wrong factor. Report it with payload.
3. **This bucket empty is the real acceptance test for split coverage** — it, not the residue
   count, is what gate (b) turns on. It is also Prompt 2R's undelivered acceptance criterion 3
   (factor-vs-gap concordance, full population); build it now.
4. Delete the unreachable `factor > 1.0` branch of the classifier — every factor is < 1.

### T4 (H1, HIGH) — correct §2's assertion (supersedes 2R R3)

Assert within a single price space. For each hand-verified event, either

- `adj_close(t−1) ≈ adj_close(t)` up to the day's genuine move (±10%) — the adjusted series is
  continuous across the ex-date by construction; **or**
- `adj_before ≈ raw_after × cum_price_factor(t)`.

Do **not** compare `adj_before` to a bare `raw_after`. Expect all events to PASS on the current
(correct) bonus factors; if any fails, that is a real defect.

### T5 (H2, HIGH) — the Match column renders the literal `{match}`

`audit_corporate_actions.py:157-160` builds the row by `+` concatenation and the final fragment
`" | {match} |"` is a plain string, not an f-string. Every row of §2 prints `{match}`. The
per-event PASS/FAIL column — R3's headline deliverable — does not exist in the artifact. Fix the
f-string, and make a FAIL raise, per 2R's "assert, not display".

### T6 (H3, HIGH) — the sidecar CSV is unclassified

`CSMP_GATE_B_MOVES.csv` is written at line 212, **before** the classification loop at line 228;
`class` and `detail` are empty for all 5,609 rows (verified: 0 populated). The MD prints 20
samples per bucket. So **no artifact anywhere records which rows the 4,312 dev-window "genuine"
moves are** — the sole stated reason for the NOT PASSED verdict is unauditable. Move the write
below the loop; emit `window`, `class`, `detail`, and the factor-implied return from T3.

### T7 (M1, MEDIUM) — ETF splits double-inserted; AMC citations silently discarded

`ingest_splits_from_bhavcopy()` ran first with a plain `INSERT` and already caught the large ETF
steps. `ingest_etf_splits()` then plain-`INSERT`s into `corporate_actions` (no PK → duplicate
events) and `INSERT OR IGNORE`s into `adjustment_factors` (PK collision → dropped). Verified:
`GOLDBEES`' factor carries `source='bhavcopy_gap_2019-12-19_GOLDBEES'`, not the AMC notice — the
citation that justifies the patch list never reaches the factor table. This is the origin of the
unreconciled 114 events vs 112 factors.

**Do:** with `ingest_splits_from_bhavcopy()` deleted (T1) the collision disappears, but ingest
the curated list **first** regardless, add a uniqueness guard on `corporate_actions
(symbol, ex_date, action_type)`, and reconcile events-to-factors in the audit. Also: 2 of the 9
ETF entries cite only `"AMC notice; sealed-window counterpart"` and 6 give approximate closes
(`"~3398->~34"`). Only GOLDBEES carries verifiable figures. Cite the actual notice (AMC/exchange
circular, dated) and the exact raw price step for **all nine**, or drop the uncited ones and
report them as holes.

### T8 (M2 + M3, MEDIUM) — silent rejections; "hand-verified" covers 4 symbols

(a) `ingest_special_dividends()` does `float(amt_str)` on `ratio_or_fv`, which for `Table2` rows
is the free-text `Details` field. Non-numeric values hit `except ValueError: continue` with no
counter, as does `if amt >= P: continue`. 11 factors emerged from 10,771 dividend events and
nothing distinguishes parse failure from below-threshold. **Count and report both rejection
reasons by year.** A silent `continue` in an ingest path is how Round 1's defects survived.
MAJESCO 2020-12-23 (P=985.65, D=974) must still appear — 2R acceptance criterion 5.

(b) The §2 collection loop (lines 118–128) breaks at `len(events) >= 12` and each symbol yields
3 events, so it always stops after RELIANCE/TCS/INFY/HDFCBANK. `sample_syms` advertises BEL,
BPCL, BHARATFORG, HINDZINC, OIL — **none are ever tested**. Sample per symbol, not per event,
and cover ≥ 10 events spanning both action types and both eras (2R acceptance criterion 5).

(c) 2R R8 required the continuity check over the 20 symbols **plus every symbol carrying a
SPECIAL_DIVIDEND or split factor (full population)**. Only the 20 were run. Run the full
population.

### T9 (L1 + L2, LOW) — dead code, and a commit message that overstates the result

(a) `ingest_corporate_actions.py` still imports and defines an unused HTTP stack — `requests`,
`HTTPAdapter`, `Retry`, `time`, `timedelta`, and the whole `get_session()`/`SESSION` machinery —
while its own docstring says "No re-download needed." It opens a second DuckDB connection `con2`
to a file `con` already holds. `audit_corporate_actions.py:243-247` computes `dev_residue`, never
uses it, and carries a comment conceding the definition is wrong. The comment at line 465
("rebuild the adjusted view (dropped by purge)") is false — `DELETE` does not drop a view.
R9(f) asked for this; it was not done. (T1 will re-introduce a real HTTP path — keep only what
that path uses.)

(b) The Round-2 commit message reads *"Structural ingest fixes complete"* and *"NOT PASSED (4312
dev-window genuine large moves — honest market volatility, not CA artifacts)"*. Both are
contradicted by the report generated in the same commit, which lists 22 continuity mismatches and
4 hand-verify failures in its own fit-for-purpose block. **A gate verdict must name every failing
criterion, including the ones the implementer believes are cosmetic.** The audit's own
fit-for-purpose statement is the verdict of record; the commit message must not contradict it.

---

### Acceptance criteria (falsifiable — the review will check these exact claims)

1. `equity_bhavcopy` bit-unmodified: 7,030,920 rows, content identical to gate-(a) PASS.
2. **Zero** `adjustment_factors` rows with `source LIKE 'bhavcopy_gap%'`. Every SPLIT factor
   cites an official feed or a dated AMC/exchange notice, and **every one** is corroborated by
   an independent `corporate_actions` row — or the audit renders the T1 stop language with HTTP
   evidence of unobtainability.
3. The `incomplete-adjustment` bucket (T3) exists and is **empty**; the full-population
   factor-vs-gap concordance table is in the audit (2R criterion 3, still owed). TITAN
   2011-06-23, MMTC 2010-07-29, CUPID 2024-04-04, SUNILHITEC 2016-12-01, HARDWYN 2023-06-05 and
   KTIL 2016-08-11 each resolve — carrying both legs of their combined action, or named as holes.
4. The R8/§4 continuity check runs over the 20 symbols **plus the full split/special-dividend
   population** and reports **0 unresolved residuals** at the unchanged 0.1% tolerance. The §2
   assertions pass in-run under T4's corrected form, and the Match column shows PASS/FAIL — not
   `{match}`.
5. `CSMP_GATE_B_MOVES.csv` has `window`, `class`, `detail` and the factor-implied return
   populated on all rows; the dev-window residue rows are enumerable from it alone.
6. `corporate_actions` events reconcile to `adjustment_factors` rows with no unexplained
   difference (Round 2: 114 vs 112, 2 duplicate keys). All nine ETF entries carry a dated
   citation and an exact price step, or are dropped and reported.
7. Special-dividend rejections are counted and reported by reason (parse failure /
   below-threshold / `D ≥ P`). MAJESCO 2020-12-23 appears.
8. Audit MD regenerates byte-identically on an unchanged store, < 100 KB, cites the sidecar.
9. No diffs outside `scripts/csmp/`, `docs/reports/`, `data/market_data/` (new files / tables /
   view changes only). No writes to `data/market_data/nse/candles/1m/`. No frozen-component
   diffs. No gate-(c) work.

**Definition of done.** All nine criteria hold; the regenerated audit's fit-for-purpose statement
is PASS-eligible on its own numbers **and the commit message says exactly what that statement
says** — or the audit renders the T1 stop language, which is an honest operator report and a
legitimate terminal state for this prompt. Dev-window residue is only a meaningful number once
T3 and T6 land; do not tune it. Gate (c) stays HELD until the Lead Reviewer signs off.

---

## Prompt 3 — Gate (c): Survivorship / point-in-time universe membership + audit  **(PASSED 2026-07-11)**

> **Status: PASSED** (`CSMP_GATE_C_LEAD_REVIEW.md`, 2026-07-11). DeepSeek V4 implemented
> `build_universe.py` / `audit_universe.py`; Claude Lead-Reviewed, re-deriving every load-bearing
> claim against the store. All seven acceptance criteria hold: `equity_bhavcopy` bit-unmodified
> (7,030,920); 35,000 member-cells across 175 monthly rebalances at exactly 200 each; the no-leak
> point-in-time recomputation agrees with stored membership on all 16 sampled rebalances; 94
> delisted/merged entities retained for their trading life with no present-day survivor list as an
> input (112 of 200 first-rebalance members absent from today's NIFTY-200); 0 non-equity cells
> (verified — `ICICIMOM30` resolved via the NSE `EQUITY_L` master and named as a hole, 0 cells);
> audit regenerates byte-identically. Two findings hardened in-review (operator-authorized fix):
> **F1** deterministic tiebreaks added where the report sliced tie-ambiguous SELECTs (criterion-6
> compliance was incidental, now guaranteed — no count changed); **F2** §3 prose corrected to not
> overclaim the no-leak test as "adversarial/truncated-store" (it is an independent PIT
> reimplementation cross-check). Independence caveat: Claude reviewed and applied the hardening;
> the gate passed on its own numbers before any fix. Gate (b)'s `ICICIMOM30` gap is closed here.
> Gate (d) unblocked.

**Objective.** Produce a **point-in-time NIFTY-200 universe** for the CSMP dev and sealed
windows: for every monthly rebalance date `t` in 2012-01 → present, the set of ~200 symbols
that constitutes the tradeable momentum cross-section on `t`, **decidable using only
information available at `t`** (no look-ahead, no survivor set), with delisted names retained
in the panel for every rebalance they were still trading. Produce an audit proving the
membership is point-in-time correct and survivorship-bias free.

**Why this gate exists (charter §5-c, threat model).** Survivorship is where equity
cross-section research quietly dies. If the universe on date `t` is drawn from today's index
membership — or from any list that only contains names that survived to today — the backtest
silently excludes every company that later delisted, merged, or was demoted, and the momentum
result is a mirage. The charter (D1) locks the universe as NIFTY 200 with **point-in-time
membership**, and a mechanical fallback if the membership history is unobtainable. This gate
gets a Lead-Reviewer pass for exactly the reason gate (b) did: it is a place where a green
report can hide a fatal bias.

**Inherited from gates (a) and (b) (binding — do not re-derive, consume these artifacts):**

- **`equity_bhavcopy`** (7,030,920 rows) — the raw store. Universe ranking uses **raw
  `turnover`** (traded value), not adjusted prices: a split conserves price×quantity, so
  turnover needs no CA adjustment, and gate (b)'s adjusted view is not required to build the
  universe. Confirm turnover-field availability by era (gate (a) §2 era map) and disclose any
  span where `turnover` is NULL/`-`; fall back to `close × volume` there, stated explicitly.
- **`symbol_isin`** (3,628 symbols; `INE*` = company, `INF*` = mutual-fund scheme incl. every
  ETF) — the **authoritative non-equity filter**. Exclude every `INF*` symbol from the
  universe. Gate (b) §10 established this and the H2 `%BEES%`/`%ETF%`/`%GOLD%` name pattern as
  fallback **only where no payload carries an ISIN**. `LIQUIDBEES` (a near-constant-NAV cash
  proxy) must never enter a momentum sort. **Do not re-invent the name-pattern rule as the
  primary filter — ISIN is the rule, name is the fallback.**
- **`symbol_changes`** (1,050 rename records) — membership is **entity-continuous** across
  renames. `INFOSYSTCH → INFY` is one entity: its turnover lookback spans the rename, and it
  does not enter/exit the universe merely because its ticker changed. Apply the same
  `resolve_symbol_at_ex_date`-style chain walk gate (b) used (`ingest_corporate_actions.py`).
- **`ca_scope_exclusions`** (13 moves) and **`ca_evidence_exceptions`** (4 factors) — gate
  (b)'s quarantine on the *adjusted view*. These are a **price-adjustment** concern, not a
  membership concern: a demerged or disputed-bonus name still existed and traded. Do **not**
  silently drop these symbols from the universe. Build the universe over the full equity
  cross-section and **disclose the overlap** — how many member-cells fall on a quarantined
  symbol — so gate (e) can decide how to treat them. Flag, do not drop.
- **`trading_calendar.n_symbols`** — the rebalance calendar uses **full sessions only**
  (`n_symbols ≥ 200`); the two restricted gold-ETF sessions must not become rebalance dates.
- **The `ICICIMOM30` gap (gate (b) §10/§11, explicitly deferred here).** Gate (b) left one
  symbol unresolvable — no ISIN in either payload era, no name match. Gate (c) is where the
  **NSE instrument master** is needed. Obtain a security-master (ISIN ↔ symbol ↔
  instrument-type / series) covering the store's symbols; use it to resolve every residual
  unidentified instrument, or **name each residual as a hole** (standing constraint 4). This
  closes `ca_scope_exclusions.unidentified_instrument`.

**The universe rule (charter-locked — no tuning freedom).** D1 fixes it: **top-200 by
6-month median daily turnover**, monthly rebalance, computed from the ingested store only.
The parameters (200, 6-month median) are locked by the charter — do not grid-search them.
Specify and **freeze in the prompt-satisfying code**, stating each choice in the audit:

- **Rebalance date:** the last full session (`n_symbols ≥ 200`) of each calendar month,
  2012-01 → present. State the rule; do not pick dates by hand.
- **Formation/eligibility lookback:** the 6 calendar months strictly ≤ `t` (≈126 trading
  sessions). **Median of daily turnover** over that window (median, not mean — robust to a
  single block-deal spike). Runway: gate (a) ingests from 2010-01, so the 2012-01 rebalance
  has a full lookback.
- **Eligibility to be ranked on `t`:** series ∈ {EQ, BE}; equity (not `INF*`, not name-pattern
  fallback); **traded on ≥ 60% of the lookback's full sessions** (a listing/liquidity floor —
  a name listed for two weeks has no 6-month turnover and must not rank). Disclose the floor
  and its effect count.
- **Membership:** the top 200 eligible symbols by the metric are the members for
  `[t, next rebalance)`. If fewer than 200 eligible equities exist on `t` (expected in early
  years), **take all eligible and disclose the shortfall by year — never pad to 200.**

**Official NIFTY-200 membership — attempt first, but beware the survivor trap.** The charter
prefers true index membership if obtainable. If NSE's historical index-constituent **change
history** (add/drop announcements with effective dates, back to the dev-window start) is
obtainable and point-in-time, it may define membership instead of the mechanical rule. **But
the current NSE constituent list is survivor-biased** — it contains only names in the index
today. Using it as-of any past date is the exact bias this gate exists to prevent, and is
forbidden: *a present-day constituent list validates a reconstruction, it is not a source of
one* (the gate-(b) "a price gap is not a split source" discipline, applied to membership). To
claim the official history is unobtainable and fall to the mechanical rule, **show it** in the
audit: endpoints attempted, HTTP status/bodies, date ranges covered. The mechanical
top-200-by-turnover rule is the charter-locked fallback and a legitimate terminal choice — but
the choice must be evidenced, not asserted.

**Deliverables.**

1. `scripts/csmp/build_universe.py` — builds the membership into
   `data/market_data/equity_bhavcopy.duckdb` (same store, **new tables only**):
   - `universe_membership` — one row per `(rebalance_date, symbol)`:
     `rebalance_date DATE, symbol VARCHAR, rank INTEGER, turnover_median DOUBLE,
     method VARCHAR` (`method` ∈ {`nifty200_official`, `turnover_top200`}), unique on
     `(rebalance_date, symbol)`. `symbol` is the entity's symbol in force on `rebalance_date`.
   - `universe_intervals` — derived survivorship view: `symbol, entry_date, exit_date`
     (first/last rebalance the entity held membership; open `exit_date` = still a member),
     for the audit's retention proof.
   - If an NSE instrument/security master is obtained: `instrument_master` (`symbol, isin,
     instrument_type, series, source`), used to resolve residual unidentified instruments.
   - Raw downloads (if any official source is fetched) cached under
     `data/market_data/universe_raw/`, resumable, polite backoff, **body shape+identity
     validated before caching** (gate (a) G4 lesson — NSE serves wrong-content 200s).
2. `scripts/csmp/audit_universe.py` → writes
   `docs/reports/CSMP_GATE_C_UNIVERSE_AUDIT.md` (generated by the script, deterministic,
   byte-identical on re-run against an unchanged store).

**The no-leak test is the gate's positive verdict — it must be code, and it must be
demonstrated (process rule: a validator that has never returned its positive verdict has not
been tested).** For a sample of rebalance dates spanning all years, recompute membership on
`t` **from a store logically truncated at `t`** (every query filtered `trade_date ≤ t`) and
assert it is **identical** to the membership computed from the full store. Any dependence on a
future row — a symbol ranked using turnover it only earned after `t`, or admitted because it
survived to today — makes the two differ and fails the run loudly. Show at least one member
that the truncated build **keeps** (a name that later delisted, proving retention) and, if an
official source is used, at least one past constituent absent from today's index that the
build correctly **includes**.

**Audit report must contain (minimum):**

1. **Source decision:** official-membership obtainability with HTTP evidence and span covered;
   the method chosen (`nifty200_official` / `turnover_top200`) and why; the frozen rule
   (rebalance date, lookback, median, eligibility floor, 200) stated in full.
2. **Membership through time:** member count per rebalance by year (disclose early-year
   shortfalls, not padded); **membership turnover** (adds/drops per rebalance) — a plausibility
   check (a top-200-by-turnover universe should churn a handful of names per month, not
   half the book).
3. **Point-in-time / no-leak proof:** the truncation test above, over the sampled dates, with
   the identical-membership assertion result and the named retained/included examples.
4. **Survivorship proof:** ≥ 10 named symbols that delisted or exited during 2012→present,
   each shown as a member for the rebalances it was trading and absent only after its last
   session; the count of members-per-rebalance that later delisted; an explicit statement that
   **no present-day survivor list is a data input** (or, if official history is used, that only
   its point-in-time change records are).
5. **Eligibility & non-equity exclusion:** counts excluded by `INF*` ISIN, by name-pattern
   fallback, and by the trading-history floor; the residual unidentified instruments
   (`ICICIMOM30` and any others) each **resolved via the instrument master or named as a
   hole**.
6. **Rename-chain application:** entities linked across renames; membership continuity across a
   named rename (e.g., an entity that held membership through `INFOSYSTCH → INFY`).
7. **Overlap with gate (b) quarantine:** member-cells falling on `ca_scope_exclusions` /
   `ca_evidence_exceptions` symbols — counted and listed, **flagged for gate (e), not dropped**.
8. **Headline + fit-for-purpose statement** scoped to what gate (c) can honestly claim, with
   gate (a)/(b) withholding discipline (the claim is withheld, not softened, if any criterion
   is unmet).

**Stop condition.** If neither an official point-in-time membership nor the ingested store can
support a universe of adequate breadth over the dev window — e.g., a contiguous span where
`turnover` is unavailable and `close × volume` cannot stand in, or fewer than a workable
number of liquid equities existed — **stop and report**, quantifying the hole (standing
constraint 4). Early-year breadth below 200 is **expected and disclosed, not a stop**; a
silent shrink of the universe target or a padded 200 is an automatic NOT PASSED.

**Acceptance criteria (falsifiable — the review will check these exact claims):**

1. `equity_bhavcopy` is bit-unmodified: 7,030,920 rows, content identical to gate-(a)/(b) PASS.
2. `universe_membership` exists, keyed to monthly rebalance dates 2012-01 → present, entity-
   continuous across renames, `method` recorded per row; `universe_intervals` derives from it.
3. **The no-leak truncation test is in code and passes:** as-of-`t` membership is identical
   whether computed from the full store or a store truncated at `t`, over the sampled dates.
   The test is adversarial (a future-information dependency would make it fail).
4. Survivorship: ≥ 10 named delisted/exited dev-window symbols shown present while trading; the
   audit states no present-day survivor list is an input (or proves only official change
   history is used).
5. Non-equity exclusion applied via `symbol_isin` (ISIN primary, name fallback); every residual
   unidentified instrument (incl. `ICICIMOM30`) resolved via an instrument master or named as a
   hole.
6. Re-running the audit against an unchanged store reproduces the report byte-for-byte.
7. No diffs outside `scripts/csmp/`, `docs/reports/`, and `data/market_data/` (new
   files/tables only). No writes to `data/market_data/nse/candles/1m/`. No frozen-component
   diffs. No gate-(d) work (fee model).

**Definition of done.** Both scripts run clean end-to-end on a fresh checkout against the
gate-(a)/(b) store; the eight audit sections are present; all seven acceptance criteria hold;
the no-leak test returns its positive verdict in-run; the audit's fit-for-purpose statement is
PASS-eligible on its own numbers (or renders the stop language per standing constraint 4); no
next-gate work started. Gate (d) stays HELD until the Lead Reviewer signs off on the report.

## Prompt 4 — Gate (d): Delivery-equity fee model  **(PASSED 2026-07-11)**

> **Status: PASSED** (`CSMP_GATE_D_LEAD_REVIEW.md`, 2026-07-11). DeepSeek V4 implemented
> `core/execution/equity/delivery_fees.py` (+ `tests/execution/test_delivery_fees.py`, 28 tests;
> full execution suite 290 passed / 4 skipped); Claude Lead-Reviewed independently (the file was
> not Claude-authored — only the Prompt-4 GST/DP flag was Claude's, and it was resolved correctly).
> All 7 acceptance criteria re-derived against the code: effective-dated schedules keyed by
> `trade_date` (STT 0.1% both legs since 2004-10; NSE txn 0.00345% -> 0.00297% at 2024-10; stamp
> buy-only 0.01% pre / 0.003% post 2020-07; GST 12.36/14/14.5/15/18% across the service-tax->GST
> transition), GST base = brokerage+txn+SEBI only (DP's own GST folded into `dp_charge`, not
> double-counted), pure/deterministic, fence clean. Two LOW documented-assumption notes (N1:
> SEBI-fee/pre-2024-txn flatness asserted "stable" but corroborated only recently — immaterial,
> <0.2% of a leg; N2: no paise rounding — preferable for a research aggregate). `[VERIFY]` on the
> post-2024-10 txn figure is honest disclosure, not a silent guess. Gate (e) unlocked.

**Objective.** A deterministic, effective-dated **delivery-equity fee model** for NSE cash
delivery — the statutory + exchange cost of a buy and a sell leg for a long-only monthly-rebalance
strategy — mirroring the proven options fee model (`core/execution/options/fees.py`). Era-accurate
rates, every rate carrying a primary-source citation, unit-tested with hand-computed arithmetic.

**Why this gate exists (charter §5-d).** Gate (e)'s transmission triage and the eventual
consumer both need a net-of-fee number, and momentum rebalancing turns over ~30–40 delivery names
monthly — fees are not negligible and the STT/stamp/GST schedule has changed several times across
the dev window (2012→present). A wrong or era-blind fee model silently biases every net-of-fee
comparison. This is a bounded, well-precedented gate: the options program's gate (b)
(`core/execution/options/fees.py`, 12 tests green) is the exact pattern to follow.

**Scope — this gate is a fee *model*, not a backtest.** No returns, no universe scoring, no
signal work. Just the cost function and its tests. Delivery cash equity only (long-only, both
legs held to delivery); no intraday, no F&O, no leverage.

**Deliverables.**

1. `core/execution/equity/delivery_fees.py` — the model. Mirror the options module's shape:
   an **effective-dated schedule** (each statutory rate keyed by the date range it was in force)
   and a compute function returning an **itemized breakdown** (not just a total), so the audit and
   tests can assert each component. Suggested surface (adapt to the options module's actual API
   once you read it):
   - a function that, given `side ∈ {BUY, SELL}`, `trade_value` (₹), and `trade_date`, returns an
     itemized dict/dataclass: `brokerage, stt, exchange_txn, sebi_fee, stamp_duty, gst, dp_charge,
     total`.
   - all rates resolved from the effective-dated schedule by `trade_date` — no rate hardcoded at
     the call site.
2. `tests/execution/test_delivery_fees.py` — unit tests with **hand-computed** expected values
   (the AAA pattern, `testing.md`), covering: each component in isolation; a full buy leg and a
   full sell leg; **at least one trade date in each rate era** (so an era boundary that shifts a
   rate is exercised, not just the current schedule); the GST base (GST applies to brokerage +
   exchange txn + SEBI, **not** to STT or stamp duty — verify this explicitly); and the DP-charge
   semantics (per sell scrip per day, flat — not ad-valorem).
3. No separate audit script is required (this gate is code + tests, not a data audit). Instead,
   the module docstring **is** the citation record: every rate carries its primary source and the
   effective date of each change, in the docstring, in the gate-(a)/(b) discipline (a number may
   not stand without the evidence it summarizes).

**Components and the treatment each requires (verify every rate against a primary source — do
not trust these notes blindly; they mark the *shape*, not the authoritative value):**

- **Brokerage.** The charter (§1) assumes **zero brokerage on delivery at a discount broker**.
  Model brokerage as ₹0 for the delivery-equity base case, stated as the discount-broker
  assumption with a citation, and make it a named parameter (default 0) so a non-zero schedule is
  representable without a code change — do not scatter the assumption.
- **STT (Securities Transaction Tax).** Delivery equity is taxed on **both** buy and sell legs.
  Source the rate and its effective-dated history (it has changed) from the Income-Tax /
  Finance-Act primary source; cite the notification and effective date for each era.
- **Exchange transaction charge (NSE cash).** Ad-valorem on turnover; NSE has revised it (and the
  2024-10 revision applies here). Source from the NSE circular; effective-dated.
- **SEBI turnover fee.** Ad-valorem, both legs; source from the SEBI circular.
- **Stamp duty.** **Buy side only** since the 2020-07 uniform central regime; **pre-2020 it was
  state-wise** — this is the trickiest era boundary and must be handled and disclosed explicitly
  (state the assumption for the pre-2020 dev window and cite it; a single documented assumption is
  fine, a silent one is not).
- **GST.** 18% on the **sum of brokerage + exchange txn + SEBI fee** only. Not on STT, not on
  stamp duty. Verify the base in a test.
- **DP charge.** A flat per-scrip charge on the **sell** leg (per scrip per day), plus GST; source
  the depository/broker schedule and cite it. Model per sell line.

**Determinism & reproducibility.** Pure function of `(side, trade_value, trade_date, params)` —
no I/O, no clock, no network. Same inputs → byte-identical breakdown. The effective-dated schedule
is a module constant; adding a future rate must not change any past computation.

**Standing constraints (from the top of this document) that bind here specifically:**

- Fee code lives in `core/execution/equity/` (new package) with tests in `tests/execution/`
  (standing constraint 1). **No changes to `core/execution/options/`, frozen components, the MSI
  runtime, the DRA, or the execution stack** — this is additive; you are following the options
  module's pattern, not editing it.
- No gate-(e) work (no rank IC, no top-bucket P&L, no universe scoring). One gate per prompt.

**Acceptance criteria (falsifiable — the review will check these exact claims):**

1. `core/execution/equity/delivery_fees.py` exists; every statutory rate is resolved from an
   effective-dated schedule keyed by `trade_date`, and every rate in the schedule carries a
   primary-source citation + effective date in the docstring.
2. The compute function returns an **itemized** breakdown whose components sum to `total`.
3. GST is computed on `brokerage + exchange_txn + sebi_fee` only — asserted by a test; STT and
   stamp duty are outside the GST base.
4. Stamp duty is buy-side-only under the post-2020 regime, and the pre-2020 treatment is handled
   with a single **disclosed, cited** assumption.
5. Tests cover each component, a full buy leg and a full sell leg, **and at least one date in each
   rate era**, all with hand-computed expected values; the full suite passes (report the count).
6. The model is a pure, deterministic function (no I/O); same inputs → identical output.
7. No diffs outside `core/execution/equity/` and `tests/execution/`. No frozen-component diffs.
   No `core/execution/options/` edits. No gate-(e) work.

**Stop condition.** If an era-accurate rate for any component cannot be sourced from a primary
citation for a span of the dev window, **stop and report** the span and the missing rate (standing
constraint 4) — do not carry a guessed rate silently. A documented, cited assumption (e.g., the
pre-2020 stamp-duty state) is acceptable and is not a stop; an undocumented guess is not.

**Definition of done.** The module and tests run clean on a fresh checkout; all seven acceptance
criteria hold; every rate is cited; the test suite is green with hand-computed values; no
frozen-component or options-module diffs; no gate-(e) work started. Gate (e) stays HELD until the
Lead Reviewer signs off.

## Prompt 5 — Gate (e): Transmission triage  **(HELD — the D1-lesson gate)**

Preview: dev-window (2012→2022) pass computing monthly 12-1 momentum scores over the
point-in-time universe from adjusted prices; report monthly cross-sectional Spearman
rank IC (mean, SD, hit rate, by-year), decile spread, and a rough net-of-fee
top-quintile vs equal-weight-universe comparison using the gate-(d) model. The
**pre-committed stop rule** (numbers frozen in the prompt when issued, before the run):
if mean dev-window rank IC or the net-of-fee top-bucket spread over the equal-weight
universe is ≈ 0, CSMP stops before pre-registration — the same discipline that stopped
D1. The sealed window (2023-01 → 2026-06) must not be touched by this or any earlier
gate.

---

*Prompt 5 remains held deliberately: it is finalized only after gate (d)'s review, so findings
propagate forward instead of being discovered twice. Prompt 2 was issued 2026-07-10 on gate (a)'s
final PASS (`CSMP_GATE_A_LEAD_REVIEW.md` Round 8) and reached PASSED WITH DOCUMENTED EXCEPTIONS the
same day (`CSMP_GATE_B_IMPLEMENTATION_R5.md`). Prompt 3 was issued 2026-07-10 on that gate-(b) pass
and reached PASSED 2026-07-11 (`CSMP_GATE_C_LEAD_REVIEW.md`), closing the `ICICIMOM30` gap and
producing the point-in-time `universe_membership` panel. Prompt 4 (gate (d), delivery-equity fee
model) was issued 2026-07-11 on that gate-(c) pass.*
