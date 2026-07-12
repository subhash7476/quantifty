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

## Prompt 5 — Gate (e): Transmission triage  **(PASSED 2026-07-11 — CONTINUE, independently confirmed)**

> **Status: PASSED — verdict CONTINUE** (`CSMP_GATE_E_LEAD_REVIEW.md`, independent reviewer
> **DeepSeek V4**). GLM implemented `scripts/csmp/triage_momentum.py`; Claude found and fixed a
> verdict-flipping bug (buckets were selected by `universe_membership.rank` = gate-(c) turnover/liquidity
> rank, not the 12-1 momentum score — corrected at both bucket sites, flipping STOP → CONTINUE;
> corroborated by turnover, momentum top-quintile 23.76%/mo vs ~5% liquidity-sorted). Because Claude
> authored a verdict-flipping change, independence was spent, so DeepSeek V4 Lead-Reviewed — re-deriving
> every number from a scratch re-implementation: mean rank IC **0.0458** (95% CI **[0.0093, 0.0812]**,
> L=12), net-of-fee top-quintile-minus-universe spread **+6.38%** (15.53% vs 9.16%); both locked stop
> rules clear → **CONTINUE**. Byte-identical re-run; sealed window untouched (all three fenced inputs
> MAX = 2022-12-30). Five LOW findings (F1 baseline-subset — conservative, all-200 widens to +6.46%;
> F2 ref-cache path; F3 fence-echo; F4 comment; F5 bucket-size invariant) — F1/F3/F4 applied. Phase-1
> pre-registration unlocked; the sealed window stays sealed until the pre-registered rule is frozen.

> **Prior status: ISSUED.** The pre-committed stop-rule thresholds are **LOCKED** (operator, 2026-07-11)
> and frozen before the run — a stop rule chosen after seeing results is not a stop rule (the MSRP
> D1 discipline): **L = 12 months** (fixed a priori from the 12-1 formation-window overlap — adjacent
> monthly scores share 11 months, so serial dependence runs to ~a year; **not** derived from the IC
> autocorrelation, which would be circular since the IC series is this gate's own output), **mean
> rank IC floor = 0.02**, **net top-minus-universe spread floor = 0**. DeepSeek V4 implements; Claude
> Lead-Reviews. Nothing in this gate reads the sealed window.

**Objective.** A dev-window-only (**2012-01 → 2022-12**) triage measuring whether classic 12-1
cross-sectional momentum — computed over the point-in-time NIFTY-200 universe from gate-(b)
adjusted prices — transmits into a **tradeable, net-of-fee edge**, before any pre-registration.
This is the gate that stopped MSRP's D1: a signal can be real and still not transmit into a
strategy, and that must be discovered *before* the sealed window is ever touched.

**Why this gate exists (charter §5-e; the D1 lesson).** MSRP Phase 7 certified a forward-volatility
signal that ranked well (Spearman 0.65 on the target) yet transmitted ≈ nil into the tradeable
construct (0.09), so every Knowledge-gated variant lost to a free baseline — and D1 was correctly
**not** pre-registered. Gate (e) applies that same pre-committed stop discipline to momentum here,
on the dev window, so a non-transmitting signal costs a triage script, not a burned held-out window.

**Scope — triage, not strategy; dev window only.**
- Compute over **2012-01 → 2022-12 ONLY**. The sealed held-out window (2023-01 → 2026-06) must not
  be read, loaded, or touched — its first and only use is the post-pre-registration test (D3), and
  any peek burns it. Assert `MAX(trade_date) ≤ 2022-12-31` on every input query and print it.
- **No tuning, no construct search, no signal engineering.** The construct is charter-locked (D2):
  classic 12-1, monthly rebalance, equal-weight, provisional top-quintile bucket. The triage reports
  what the *locked* construct does; it does not search for a better one.
- No new strategy code; `core/strategies/` stays greenfield until pre-registration.

**Inputs (all from passed gates).**
- `universe_membership` (gate c) — the point-in-time ~200-name cross-section at each monthly
  rebalance; score only names that are members as of that date (gate (c)'s no-leak guarantee).
- `equity_bhavcopy_adjusted` (gate b) — CA-adjusted close (raw momentum is corrupted by
  splits/bonuses; that is why gate (b) exists).
- `symbol_changes` (gate a) — entity continuity across renames over the formation window.
- `delivery_equity_fees` (gate d) — net-of-fee cost of each rebalance turnover leg.

**Method (deterministic; charter-locked).**
1. **Formation** at each rebalance date `t` (last full session of the month — gate (c)'s rebalance
   calendar): for each member, 12-1 momentum = total adjusted return from `t−12m` to `t−1m` (skip
   the most recent month, the standard short-term-reversal guard). Require a complete formation
   window (member present and priced across the lookback via `symbol_changes`); exclude and **count**
   names that fail it.
2. **Rank** members cross-sectionally by score at `t`.
3. **Forward return**: realized adjusted return of each name over `t → t+1` (next rebalance).
4. **Rank IC**: monthly cross-sectional **Spearman** correlation of score(`t`) vs forward
   return(`t→t+1`). Report the series + mean, SD, t-stat, hit rate (fraction of months > 0), by-year.
5. **Bucket spread**: equal-weight top quintile and bottom quintile; report the gross spread series.
6. **Net-of-fee gating baseline (D3)**: equal-weight **top-quintile** portfolio, monthly rebalanced,
   vs the equal-weight **full-universe** portfolio (what a naive investor gets free). Apply gate-(d)
   delivery fees to every buy/sell leg of each rebalance's turnover (each portfolio pays its own
   turnover; the universe portfolio's turnover is only membership churn). Report net annualized
   return, the **net top-minus-universe spread**, and turnover.
7. **Reference arm (if obtainable)**: NIFTY200 Momentum 30 TRI as an external sign/magnitude sanity
   check — obtainability shown with HTTP evidence (gate-(b)/(c) discipline); if unobtainable, say so
   and proceed (it is a reference, not the gating baseline).

**Deliverables.**
1. `scripts/csmp/triage_momentum.py` — deterministic, re-runnable; writes
   `docs/reports/CSMP_GATE_E_TRIAGE.md` (generated, byte-identical on re-run).
2. No production strategy code; no `core/strategies/` work.

**Pre-committed stop rule (LOCKED 2026-07-11 — frozen before the run).**
CSMP **STOPS before pre-registration** if **EITHER** holds on the dev window (2012-2022):
- **(A) No skill** — the mean monthly cross-sectional rank IC is not distinguishable from zero, or is
  economically trivial. STOP if the block-bootstrap 95% CI of the mean monthly IC includes 0 **or**
  the mean rank IC ≤ **0.02**. Block bootstrap on the monthly IC series with block length **L = 12
  months** — fixed a priori from the 12-1 formation-window overlap (adjacent monthly scores share 11
  months of data, so the IC series carries serial dependence to ~a year); **not** derived from the IC
  autocorrelation, which would be circular (the IC series is this gate's own output). ~132 dev-window
  months yield ~11 blocks; the resulting wide CI is the intended conservative bias for a triage.
- **(B) No net edge** — the net-of-fee equal-weight top-quintile portfolio does not beat the
  equal-weight full-universe baseline: annualized net top-minus-universe spread ≤ **0**.

**CONTINUE** to pre-registration only if **BOTH** clear — mean rank IC > 0.02 **and** its bootstrap
95% CI lower bound > 0 (A cleared), **and** net annualized top-minus-universe spread > 0 (B cleared).
These numbers are frozen; the run's verdict is accepted mechanically — **no post-hoc widening** (the
D1 discipline). A STOP is a *pass* of this gate's discipline, not a failure — a null result is a
legitimate, valuable terminal state.

**Standing constraints (bind here).**
- Sealed window untouched — any read of 2023-01→present data is an automatic NOT PASSED.
- No tuning, no construct search, no signal engineering — charter-locked parameters only.
- Deterministic, re-runnable; report generated by the script; byte-identical on re-run.
- Fence: new code in `scripts/csmp/`; report in `docs/reports/`; no `core/strategies/` work; no
  frozen-component diffs.

**Acceptance criteria (falsifiable — the review will check these exact claims).**
1. Scores computed only on point-in-time members from `universe_membership`; formation-window
   completeness enforced, excluded count reported; **no sealed-window rows read** (every input query
   asserts `MAX(trade_date) ≤ 2022-12-31`, printed in the audit).
2. Monthly rank IC series + mean/SD/t/hit-rate/by-year present; the block-bootstrap 95% CI with the
   pre-committed `L` reported.
3. Net-of-fee top-quintile vs equal-weight-universe spread present, using gate-(d) fees on actual
   rebalance turnover; turnover disclosed.
4. The pre-committed stop rule is stated with its locked thresholds and evaluated **mechanically**;
   the audit renders CONTINUE or STOP on its own numbers.
5. Reference-arm obtainability shown (data or HTTP-evidenced hole).
6. Audit regenerates byte-identically on an unchanged store.
7. No diffs outside `scripts/csmp/` and `docs/reports/`; no `core/strategies/` or frozen-component
   diffs.

**Definition of done.** The script runs clean; the audit renders **CONTINUE** or **STOP** on its own
pre-committed numbers; the sealed window is untouched; no tuning occurred. If STOP, CSMP halts before
pre-registration and the operator decides next (the D1 precedent). If CONTINUE, Phase-1
pre-registration unlocks. DeepSeek V4 implements; Claude Lead-Reviews.

---

*Prompt 5 remains held deliberately: it is finalized only after gate (d)'s review, so findings
propagate forward instead of being discovered twice. Prompt 2 was issued 2026-07-10 on gate (a)'s
final PASS (`CSMP_GATE_A_LEAD_REVIEW.md` Round 8) and reached PASSED WITH DOCUMENTED EXCEPTIONS the
same day (`CSMP_GATE_B_IMPLEMENTATION_R5.md`). Prompt 3 was issued 2026-07-10 on that gate-(b) pass
and reached PASSED 2026-07-11 (`CSMP_GATE_C_LEAD_REVIEW.md`), closing the `ICICIMOM30` gap and
producing the point-in-time `universe_membership` panel. Prompt 4 (gate (d), delivery-equity fee
model) was issued 2026-07-11 on that gate-(c) pass.*

---

## Prompt 6 — Phase 1: apply the operator ratification, stamp Rev 6 RATIFIED (author-locked)  **(ISSUED 2026-07-12)**

**Objective.** Apply the operator's ratification (`CSMP_PHASE1_FREEZE_RATIFICATION.md`, 2026-07-12)
to `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md` and stamp it
**Rev 6 — RATIFIED, author-locked, pending Phase-2**. This is a **mechanical application of a
decision already made.** It is the last edit the dossier receives **from its authors** before the
Phase-2 independent review.

> **This prompt does NOT freeze the dossier, and Rev 6 must not contain the word FROZEN.**
> Charter §6 row 2 orders Phase 2 as *"critique; revisions folded in; dossier FROZEN"* — **review
> first, then freeze.** The immutable **FROZEN** stamp lands at **Rev 7**, after Phase-2 findings are
> folded. Author-lock means the *authors* stop revising; it does **not** mean the document is closed
> to correction. Because the sealed window is still untouched, a pre-seal change triggered by the
> Phase-2 reviewer remains fully legitimate — enabling exactly that is why the charter puts the
> review before the freeze.

**Scope of the bars below — read this carefully.** Every constraint in this prompt binds **you,
DeepSeek, on this mechanical application pass.** **None of them binds the Phase-2 reviewer**, whose
job is precisely to stress-test the evidence behind D-i, D-ii, and D-iii and whose findings *are*
foldable. Do not carry these bars into the dossier as if they gagged the reviewer.

**This prompt authorizes NO new work.** For this pass, each of the following is an automatic NOT PASSED:

1. Running, re-running, or modifying **any** script — `phase1_prereg_analysis.py`,
   `phase1_ci_coverage.py`, `phase1_group_sequential.py` are final. Their numbers are final.
2. Introducing **any** number not already in Rev 5 or in the ratification record. No new simulation,
   no new sensitivity, no re-derivation "to check."
3. Touching the sealed window (2023-01 → 2026-06) in any way.
4. Changing the universe, score, holding rule (K=40), metric, baselines, cost model, delisting
   convention (§5.2), or the ratified inference/extension design. The construct fence binds **the
   authors** from now; it becomes **immutable at Rev 7 (freeze)**, after which a change to any of
   these is **a new pre-registration, not an edit**.
5. Reopening D-i, D-ii, or D-iii **on your own initiative**, or re-arguing them. They are ratified.
   Record them; do not relitigate them. *(The Phase-2 reviewer may reopen them; you may not.)*

**Deliverable — one file changed:** `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md`.

**The edits, exhaustively.**

1. **Header `Status:`** — replace the "DRAFT (Rev 5) — NOT yet frozen … await operator ratification"
   block with **RATIFIED (Rev 6) — author-locked, pending Phase-2; NOT yet frozen**, 2026-07-12.
   State that D-i, D-ii, and D-iii are **operator-ratified** (cite
   `CSMP_PHASE1_FREEZE_RATIFICATION.md`); that the authors make no further self-initiated revision;
   that the **Phase-2 independent review by a third frontier model** — neither Claude nor DeepSeek,
   whose independence is spent — is the one remaining step; and that the dossier **FREEZES at Rev 7,
   after Phase-2 findings are folded** (charter §6 order).
2. **Revision provenance** — add **Rev 6**: operator ratification applied; author-locked; **no
   analytical change from Rev 5** (this is the claim the Lead Review will verify). Note that Rev 7
   will carry the freeze.
3. **§1.1** — D-i row: strike "Operator-ratified at freeze" → **"RATIFIED 2026-07-12."** D-iii row:
   the pinned design is **single-shot**, full stop. Move the Pocock boundary vector *out* of the
   pinned-substrate table (nothing about it is pinned any more) and keep it in §3.4 as the
   **declined** alternative, retained for the record. §1.1 must contain only what Phase 6 actually
   builds against.
4. **§3.3 / §3.4** — replace every "awaits operator ratification" / "recommended" / "the operator
   ratifies" hedge with the ratified fact. Keep the D-i coverage table, the power table, and the
   decay table **intact and unchanged** — they are the evidence, and the Phase-2 reviewer must see
   them. Preserve verbatim the guardrail sentence *"select on coverage, NOT on narrowness."* Add the
   record from the ratification §1.2: the rule selected **against** power (Student-t 0.398 vs
   stationary 0.453), which is the evidence it was not reverse-engineered.
5. **§10 row 3 (Inconclusive)** — the one substantive edit. Replace *"This requires the operator to
   explicitly grant a deviation from charter §6 … it must not be assumed"* with the ratified
   **epistemic-condition framing** (`CSMP_PHASE1_FREEZE_RATIFICATION.md` §2), faithfully:

   > Charter §6's Approval precondition is an **epistemic condition, not a risk gate** — "Approved"
   > labels a descriptive claim about the sealed window, not a permission to risk capital, and at
   > PaperBroker scale there is **no capital at risk**. It is **satisfied-in-substance by
   > disclosure**: the consumer is built and run with the artifact disclosed, in code and in every
   > report it emits, as **Not Approved / exploratory**.

   State plainly what is **not** licensed: an Inconclusive result is never reported as a
   confirmation; no LIVE deployment; no parameter change; no re-read. Also drop the parenthetical
   *"(If instead the operator ratifies the Pocock group-sequential design …)"* — the operator did
   not, and the decision table must not offer a road not taken.
6. **§11** — carry the headline in plain words, at the top of the power paragraph:

   > A valid, one-sided, correctly-covered test on 42 months is **~41% powered** against the
   > program's own point estimate. **The single likeliest outcome of Phase 6 is "Inconclusive"
   > (~59%) — even if the hypothesis is exactly true.** This was computed **before the window was
   > spent, not after.**

7. **§13 Sources** — add a row for `CSMP_PHASE1_FREEZE_RATIFICATION.md` (operator ratification and
   author-lock).
8. **Footer** — the dossier is **RATIFIED and author-locked, not yet frozen.** "Remaining before the
   seal" is **exactly two items, in this order**: (1) the **Phase-2 independent review**, whose
   findings are folded in; (2) the **Rev 7 FROZEN** stamp. Retain the standing attestation that
   nothing in the document reports a result computed on the sealed window.

**Acceptance criteria (the Lead Review checks precisely these).**

1. **No number changed.** Every figure in Rev 6 matches Rev 5: mean IC 0.0457; dev CI
   [0.0091, 0.0811]; Student-t 0.957 / 0.049 / 0.398; mb_L12 0.811 / 0.129 / 0.538; single-shot power
   0.41; Pocock 0.24 / 0.73; decay row 0.34; naive-schedule FWER 0.130; net spread +6.24%/yr;
   slippage differential ≈29 bp/yr. **A single changed digit is a NOT PASSED** — this pass is a status
   change, not a revision.
2. Status is **RATIFIED / author-locked / pending Phase-2**. The word **FROZEN must not appear as the
   document's status** (it may appear only as the *future* Rev 7 step). No "recommended", "awaits
   ratification", or "operator decides" language survives anywhere.
3. §10 row 3 carries the epistemic-condition framing and no charter-deviation framing.
4. §1.1 pins **single-shot only**; the Pocock boundary vector appears only in §3.4, marked declined.
5. The construct fence is stated, with its timing correct: it binds the authors now and becomes
   immutable at **Rev 7**, after which any change to universe/score/K/metric/baselines/costs/§5.2/
   inference requires a **new pre-registration**.
6. **The document does not gag the Phase-2 reviewer.** Nothing in Rev 6 may assert that D-i, D-ii, or
   D-iii is closed to challenge, or that the evidence is beyond review. The reviewer's mandate to
   reopen any of them is stated, not merely left unstated.
7. `git diff` touches **exactly one file** — the dossier. No script diffs. No `core/` diffs.
8. The sealed window is untouched, and the document still says so.

**Definition of done.** The dossier reads as a pre-registration whose decisions are made, whose
authors are done, and which is **ready to be attacked** by an independent reviewer — needing nothing
further from Claude or DeepSeek. DeepSeek V4 applies; Claude Lead-Reviews the diff for mechanical
fidelity only — did the ratification get applied, and did anything else move?

---

## Prompt 7 — Phase 1: fold Phase-2 findings F1/F2/F3; stamp Rev 7 FROZEN  **(ISSUED 2026-07-12)**

**Context.** The Phase-2 independent review (GPT-5 / Codex, `CSMP_PHASE2_INDEPENDENT_REVIEW.md`)
returned **PASS WITH REQUIRED REVISIONS**. The Lead Reviewer accepted all three findings and verified
each against the source (`CSMP_PHASE2_LEAD_DISPOSITION.md`); the operator has ratified the two
decisions they forced. **This prompt folds them in and freezes the dossier at Rev 7.**

**Scope is exactly F1 + F2 + F3 + the record correction below. Nothing else reopens.** D-ii, D-iii,
the power analysis, K=40, the cost model, and the decision table were examined by the independent
reviewer and **cleared on their merits** — they are not in play. Reopening them is an automatic NOT
PASSED. The sealed window (2023-01 → 2026-06) stays untouched; the dev-only fence and its assertion
stay in every script.

---

### Step 1 — **F2 first** (it is a precondition for F1, not a parallel task)

`scripts/csmp/phase1_ci_coverage.py` builds its IC population with

```python
if p12 and p1 and pa and pb and p12 > 0 and pa > 0:   # <-- pb required
    pr.append((p1 / p12 - 1.0, pb / pa - 1.0))
```

A name with **no `t+1` price (`pb`) is silently dropped.** That is **the §5.2 survivorship bug** — the
same class of defect §5.2 was written to kill, and that B1 fixed in `phase1_prereg_analysis.py` —
still live in **the script that selects the gate**, while the dossier asserts §5.2 is "binding on every
forward return in the IC set."

**Do:** refactor `dev_ic_series()` to use **the same `fwd()` convention as
`phase1_prereg_analysis.py`** (rule 1: last available close in `(t, t+1]`; rule 2: 0% step; rule 3:
never drop the name). **Do not write a second implementation of §5.2** — reuse the one that exists, so
the two scripts cannot drift apart again. Re-run and publish the corrected coverage table.

> **Falsifiable prediction, recorded before the run** (state it in your report, then run — house
> discipline): *the §5.2 correction shifts the dev IC population negligibly (0.0458 → ~0.0457); the
> selection does **not** flip; Student-t remains closest on one-sided Type-I.*

### Step 2 — **F1**: the rule is ratified; the method is *whatever the corrected table selects*

The old rule ("coverage closest to nominal") never named **which** calibration metric, and under a
literal two-sided reading it selects `iid_perc` (0.949), **not** the ratified Student-t (0.957). The
operator has ratified the disambiguation:

> **D-i selection rule (ratified 2026-07-12).** *Because the primary gate is a one-sided lower bound,
> select the CI method whose **one-sided null rejection rate at n = 42 is closest to nominal 0.050**.
> Two-sided coverage is reported as a sanity check, not used to select. Guardrail, unchanged: select on
> **calibration, NOT on narrowness**.*

**Apply that rule mechanically to the corrected table and take whatever it selects — including
`iid_perc`, if that is what it selects.** You are not permitted to steer this. The script must **print
the selected method and its distance to nominal**, so the choice is made by code, not by prose.

**Also required:** the non-selected candidates are pre-registered as **reported, non-gating arms** at
Phase 6 — `iid_perc` (the two-sided-reading winner) alongside the retired `mb_L12`. Both readings stay
visible in the frozen document, so neither can be silently preferred after the sealed result is seen.

> **STOP CONDITION — do not freeze; escalate instead.** If the corrected table **flips the selected
> method** (one-sided Type-I closeness no longer selects Student-t), **halt.** Do not stamp Rev 7.
> Publish the corrected table, state the flip plainly, and return to the operator — the frozen gate
> would be changing, and the Phase-2 reviewer gets a confirmatory look at the corrected table before
> any freeze.

### Step 3 — **F3**: the PaperBroker path is a **charter amendment**, not a satisfied precondition

The current §10 row 3 framing ("charter §6's Approval precondition is an *epistemic condition* …
satisfied-in-substance by disclosure") **modelled capital risk and nothing else.** It does not answer
**anchoring, sunk cost, or the quiet promotion of a Not-Approved artifact into an operationally trusted
one.** The operator has ratified the reviewer's fix: **record it as an explicit amendment to charter
§6, with controls.**

Rewrite §10 row 3, and add a dated amendment note to `CSMP_PHASE0_CHARTER.md`, saying in substance:

> **Charter §6 amendment (2026-07-12).** An Inconclusive Phase-6 result leaves the artifact **Not
> Approved**. The top-40 PaperBroker consumer may still be built and run, as an explicitly
> **exploratory** deployment, under these controls:
> 1. It is **not** Phase-7 completion, and must not be recorded as such.
> 2. It may **never** appear in Approved / Deployable / certified language — in code, dashboards, or
>    reports.
> 3. It runs under a **separate exploratory runbook**, distinct from the production consumer path.
> 4. Its forward data may enter **only a fresh pre-registration with frozen rules and fresh α** — never
>    a re-read of the spent window, never a retrofit of this one.

**Delete the "satisfied-in-substance by disclosure" language.** It is superseded.

### Step 4 — the record correction (F1 falsifies a claim now in the dossier)

§3.4 / §1.1 currently celebrate that the rule *"selected against power (Student-t 0.398 vs stationary's
0.453)."* That is **inaccurate**: the stationary bootstrap was never the rule's winner under either
reading, and the relevant foil — **`iid_perc`, power 0.418, the literal two-sided winner** — was
**omitted from the comparison entirely.** Replace it with:

> Student-t is the **lowest-power valid candidate** (0.398, vs `iid_perc` 0.418 and stationary 0.453) —
> chosen on **one-sided calibration for a one-sided gate**, not for power. The rule as first written was
> **underspecified** between the one-sided and two-sided readings (Phase-2 **F1**); under a literal
> two-sided reading it selects `iid_perc`. It was **disambiguated to one-sided pre-seal, on a corrected
> table, and disclosed** — not resolved after the fact.

*(Adjust the figures to the corrected table if they move.)* **The disclosure is the point. Do not
restore a triumphant framing.**

### Step 5 — freeze

Stamp the dossier **Rev 7 — FROZEN** (charter §6 order: critique → revisions folded → FROZEN). Header,
revision provenance, and footer updated accordingly. The construct fence becomes **immutable**: any
change to universe / score / K / metric / baselines / cost model / §5.2 / inference or extension design
now requires **a new pre-registration, not an edit**. Add `CSMP_PHASE2_INDEPENDENT_REVIEW.md` and
`CSMP_PHASE2_LEAD_DISPOSITION.md` to §13 Sources.

---

**Acceptance criteria (the Lead Review checks precisely these).**

1. **F2 closed in code, not in prose:** `phase1_ci_coverage.py` reuses `phase1_prereg_analysis.py`'s
   §5.2 `fwd()` convention — **no second implementation** — and the corrected table is published with
   the pre-stated prediction and the actual outcome side by side.
2. **F1 closed by code, not by choice:** the script **prints** the selected method and its distance to
   nominal under the ratified one-sided rule. The dossier's D-i wording matches that rule verbatim. The
   non-selected arms (`iid_perc`, `mb_L12`) are pre-registered as **reported, non-gating**.
3. **The stop condition was honoured:** if the selection flipped, the dossier is **not** frozen and the
   matter is back with the operator.
4. **F3 closed as an amendment:** §10 row 3 and the charter carry the dated §6 amendment with all four
   controls; the "satisfied-in-substance" language is **gone**.
5. **The record correction landed:** no "selected against power (vs stationary)" claim survives
   anywhere; the `iid_perc` foil and the F1 ambiguity are disclosed.
6. **Nothing outside scope moved.** D-ii, D-iii, the power tables, K=40, the cost model, and
   decision-table rows 1 / 2 / 4 are byte-unchanged.
7. `git diff` touches only: the dossier, `phase1_ci_coverage.py`, the charter (amendment note), and the
   coverage output. **No `core/` diffs. No sealed-window reads** (fence asserted and printed).
8. Scripts remain deterministic at seed `20260711` and re-run byte-identically.

**Definition of done.** The pre-registration is **FROZEN**; its gate is defined by a rule a stranger
could apply mechanically to a printed table and land on the same method; its calibration script honours
the same delisting convention as its analysis script; and its one governance deviation is recorded as
an amendment with teeth rather than a reframing. DeepSeek V4 implements; Claude Lead-Reviews.

---

## Prompt 8 — Phase 5 (A1 artifact) + A2 validation harness — **the last build before the sealed read**  **(ISSUED 2026-07-12)**

**Read `CSMP_PHASE1_RESEARCH_DOSSIER.md` (Rev 7, FROZEN) end to end first. It is now immutable and it is
your specification.** Nothing in this prompt may contradict it; where they differ, **the dossier wins,
and you stop and say so.**

### Why this is not Phase 6 — and why that matters more than anything else in this prompt

Charter §6's phase map runs **3/4 (latent variable) → 5 (artifact — "Author") → A2 ("the one required
harness build") → 6 (held-out scoring — "No: uses A2")**. **Phase 6 builds nothing. It *runs* A2, once.**

Today, `grep -rl xs_momentum_score --include=*.py .` returns **nothing**. There is no artifact and no
harness.

> **If the harness were written during Phase 6, any bug found afterwards would be unfixable.** The
> sealed window (2023-01 → 2026-06) can be read **exactly once**, and re-reading it to fix your own code
> is the multiplicity trap D-iii exists to forbid. **The single worst outcome available to this program
> is to spend the sealed window on buggy scoring code.**

**So this prompt builds and *fully proves* the scoring machinery on the dev window, and touches the
sealed window nowhere.** Phase 6 must then be a change of **the date range and nothing else**. Design
for exactly that: **the evaluation window is a parameter, not a hard-coded literal**, and the dev and
sealed code paths are **identical**.

### The hard fence (violation = automatic NOT PASSED)

- Every query is fenced at `DEV_END = 2022-12-31`, and the harness **asserts and prints** the observed
  max `trade_date` — the pattern already in `phase1_prereg_analysis.py` / `phase1_ci_coverage.py`
  (`assert max(d) <= DEV_END, "SEALED LEAK"`).
- **You do not read, inspect, sample, count, or describe the sealed window.** Not to "sanity check",
  not to "confirm the schema", not once.
- The dry run is on the **full store with the code fence** — *not* a truncated store (operator-ratified:
  the harness is *our* code and carries its own fence; a second store would reintroduce exactly the
  drift F2 just closed).

---

### Deliverable 1 — Phase 5 / A1: the artifact

**Conform to the existing MSI precedent; do not invent a shape.** Read first:
`core/msi/contracts/artifact.py` (the `PublishedArtifact` contract) and
`core/msi/artifacts/forward_vol_v2/model.py` (MSRP's artifact — the working MSI-007 v2 example). Build
the CSMP artifact as a **new sibling**, e.g. `core/msi/artifacts/xs_momentum_v1/`.

**Scope note — the one place the standing constraints need interpreting.** The gate-era constraint said
*"zero changes to `core/msi/`"*; that was scoped to gates (a)–(e), which were ingestion work. Phase 5 is
charter-designated **"Author"** and A2 is **"the one required harness build"** — code must exist.
**Adding a new artifact directory is additive and permitted. Modifying MSI runtime, the DRA, the
contracts, frozen components, or anything MSRP-sealed is NOT.** If conforming to MSI-007 appears to
*require* changing shared MSI code, **stop and report** — do not edit shared code to make your artifact
fit.

**The construct is frozen and parameter-free (§7).** Nothing is fitted; there are no coefficients:

- `evaluate()` emits **one `Estimate` per point-in-time universe member**: `value` = the 12-1 score
  (`adj_close(t−1m)/adj_close(t−12m) − 1`), `dimension = <symbol>`, and a **scalar `uncertainty` = the
  SD of the 11 monthly formation sub-returns**.
- **Formation-window completeness is separate metadata — NOT folded into the `uncertainty` scalar.** A
  name lacking a complete formation window is **not scored** and cannot enter the top-40; the excluded
  count is reported.
- `uncertainty` is **reported-not-acted-on** in increment 1: it must **not** enter ranking, K-selection,
  or weighting (charter §4).
- Deterministic and side-effect-free: identical evidence ⇒ identical `MarketState`.

### Deliverable 2 — A2: the validation harness (the one required build)

Precedent: `core/msi/msrp/validation.py` (MSRP's MSI-006 record). Build the CSMP sibling (e.g.
`core/msi/csmp/validation.py`) plus a runner in `scripts/csmp/`.

**Reuse, do not reimplement — this is F2's lesson, and it is now a standing rule:**

- **§5.2 delisting convention:** import `fwd()` from `scripts/csmp/phase1_prereg_analysis.py`. **There
  is ONE implementation of §5.2 in this repo and it stays that way.** A second one is an automatic NOT
  PASSED.
- **Fees:** `core/execution/equity/delivery_fees.py` (gate (d)) — do not re-derive rates.
- **Universe:** `universe_membership` (gate (c), point-in-time). **Prices:** `equity_bhavcopy_adjusted`
  (gate (b)). **Entity continuity:** `universe_eligibility` / `symbol_changes` (gate (a)).

**The gate — pinned, not re-selected.** D-i is **decided**: the gate is the **one-sided 95% Student-t
lower bound** on the monthly `IC_t` series. **The harness applies it. It does not re-run the selection
and it does not reopen D-i.**

- **Approved** iff the one-sided 95% Student-t lower bound of `mean_IC` **> 0**.
- **Deployable** iff additionally `Δ_net > 0` (net top-40 minus the **stronger** of the two universe
  baselines — §3.2 / S1).
- Read **mechanically** against the §10 decision table. **No post-hoc widening.** The harness prints the
  verdict; a human does not choose it.

**Reported, non-gating (all of these — §3.4, §5.2, §9):** the `iid_perc` and `mb_L12` bounds (both
readings stay visible); the `Δ_net` block-bootstrap CI (explicitly non-gating); by-year IC and hit-rate;
§5.2 rule-1/rule-2 counts **by year**, with **every top-40 rule-2 event explicitly highlighted** (a 0%
step on a top-40 name can mask a real delisting loss); the **−100% rule-2 sensitivity**; the sub-period
split (2023-24 vs 2025-26); risk metrics for both arms (annualized vol, Sharpe, max drawdown); the §7
**uncertainty-tercile monotonic-IC calibration test**; the long-short quintile spread (reported, never
traded); the formation-exclusion count.

**All seven MSI-006 domains** per §9: Architectural, Scientific, Temporal, Robustness, Reproducibility,
Operational, Calibration.

### Deliverable 3 — the A1 VOID precondition (implement now; it *executes* at Phase 6)

Per §8: **Step 0 of the Phase-6 run** re-executes gate (b)'s `|move| ≥ 20%` single-day CA-classification
screen over the sealed window. **If unexplained residue > 0 → the run is VOID:** no metric is read, no
verdict rendered, the window re-sealed pending a gate-(b) fix.

**Implement it now and prove it on the dev window** (where gate (b) reports residue 0). It is a
**data-quality** check, not a result, so it preserves the seal. **Wire it as a hard precondition: the
harness must be structurally incapable of emitting a verdict if the VOID check fails.** A single wrong
split factor manufactures ±50% phantom momentum and can inject that name into the top quintile — §12.1
names this the scariest inherited assumption.

### Deliverable 4 — **the mandatory dev-window dry run** (this is the acceptance gate)

Run the **complete** A1 + A2 pipeline end-to-end on **dev (2012-01 → 2022-12)** and emit a **full MSI-006
validation record with a rendered verdict** — exactly as Phase 6 will, but on data that is already spent.

**This is the entire point of the prompt.** It proves the machinery works *before* it is pointed at a
window that cannot be re-read.

- The dry-run record must be **byte-identical on re-run** (seed `20260711`).
- Its dev IC series must **reconcile with `phase1_prereg_analysis.py`**: `n = 131`, `mean_IC = 0.0457`,
  rule-1/rule-2 = **21 / 1**, net spread **+6.24%** (fees) / **+5.95%** (fees + slippage). **A mismatch
  means the harness disagrees with the frozen dossier's own numbers — that is a defect in the harness,
  and it must be found now, not after the seal is broken.**
- Script-generated (not hand-typed) → `docs/reports/CSMP_A2_DEV_DRYRUN.md`.

### Deliverable 5 — close §1.1's remaining build-time fields

Frozen §1.1 leaves exactly one row unpinned: *"Python / duckdb / numpy / scipy versions; store SHA-256;
code commit hash — pin at build."* **Pin them now.** Also pin the **sealed rebalance-date list** from
`trading_calendar` (a non-price calendar fact; target **42** formations, 2022-12 → 2026-05 inclusive).
The count is **VOID-checked, never a tuning lever** — if it is not 42, **report it and stop**; do not
adjust anything to make it 42.

---

**Acceptance criteria (the Lead Review checks precisely these).**

1. **The sealed window was not touched.** Fence asserted *and printed*; observed max `trade_date` ≤
   2022-12-31 everywhere. Checked first, and dispositive.
2. **One §5.2 implementation.** `fwd()` imported from `phase1_prereg_analysis`, never reimplemented.
3. **The dev dry run reconciles with the frozen dossier** on every number in Deliverable 4, and is
   byte-identical on re-run.
4. **The gate is applied, not chosen.** Student-t one-sided lower bound, pinned; the harness renders
   Approved / Not-Approved / Rejected mechanically from §10; `iid_perc` and `mb_L12` reported non-gating.
5. **`uncertainty` does not act.** Ranking, K-selection, and weighting are provably independent of it.
6. **The VOID precondition is structural** — the harness *cannot* emit a verdict if it fails.
7. **Phase 6 is a date change and nothing else.** Demonstrate it: the evaluation window is a parameter;
   dev and sealed code paths are identical. **If Phase 6 would require editing harness logic, this
   prompt is not done.**
8. **No shared-MSI edits.** New artifact/validation directories only; MSI runtime, the DRA, contracts,
   frozen components, and MSRP-sealed code untouched. No `core/execution/` diffs beyond *using*
   `delivery_fees.py`.
9. **The construct fence held.** Universe, score, K=40, metric, baselines, cost model, §5.2, and the
   inference/extension design are exactly as frozen. Any pressure to change them means **stop and
   report** — a change requires a **new pre-registration**, not an edit.

**Definition of done.** The artifact exists, the harness exists, and the harness has **already rendered a
complete verdict on the dev window and reproduced the frozen dossier's numbers**. The sealed window is
still sealed. Phase 6 is then a **ceremony, not a build**: point the same harness at 2023-01 → 2026-06,
run the VOID check, run it once, and read the answer off a decision table written before the data was
seen.

DeepSeek V4 implements; Claude Lead-Reviews. **Do not begin Phase 6.**

---

## Prompt 9 — Close Prompt-8 F1: make the attestation true and the record reproducible  **(ISSUED 2026-07-12)**

**Context.** Prompt 8 is **NOT PASSED** on one HIGH finding (`CSMP_PROMPT8_LEAD_REVIEW.md` §2). Everything
else passed: the numbers reconcile with the frozen dossier, `results.json` is byte-identical, the fence
holds, the VOID gate is structural, and Phase 6 is genuinely a date-flag change. **The science is sound.
This prompt fixes a provenance defect — and it is blocking, because it is the kind of defect that becomes
permanent the instant the seal is broken.**

**Scope is F1 plus the two recorded disclosures. Nothing else reopens.** No construct change, no
re-derivation, no new analysis. The sealed window stays untouched (the dev fence stays asserted and
printed).

---

### The defect, restated so the fix is unambiguous

`run_a2_validation.py`'s `git_commit()` calls `git rev-parse HEAD` **at run time, with no dirty-tree
check**, and that value flows into `methodology.substrate.commit` → `methodology_fingerprint()` →
**`validation_id`**.

You ran the harness while **the harness itself was uncommitted** (HEAD = `4279704`, the *"issue Prompt 8"*
commit), then committed the code afterwards as `49513fe7`. Therefore:

```
$ git ls-tree -r --name-only 42797043 | grep -E "core/msi/csmp|xs_momentum_v1|run_a2_validation"
(empty)
```

**The commit pinned into the FROZEN dossier §1.1 as the reproducibility substrate contains no artifact,
no validation module, and no runner.** Anyone checking it out to reproduce the record finds the code is
not there. **The pin is not stale — it is false.** And because `commit` sits inside the `validation_id`
preimage, the record's identity **drifts with every later commit**: re-running produced a different
`validation_id` purely because HEAD had moved.

**Why it blocks.** Phase 6 reads the sealed window **once** and emits a record naming whatever HEAD
happens to be. If that record names a commit lacking the code — or if its ID moves whenever anyone commits
a typo — then **the one result the entire program exists to produce can never be audited, and cannot be
re-run, because the seal is gone.** Reproducibility is one of the seven MSI-006 domains, and the record
whose job is to attest it is not itself reproducible.

---

### The circularity you will hit — read this before you start

Pinning the code commit into dossier §1.1 **is itself a commit**. So if anything in the record tracks
`HEAD`, the act of recording the pin **immediately invalidates it again**: HEAD moves, the fingerprint
moves, the ID moves. **You cannot fix this by being careful about ordering. You must remove `HEAD` from the
identity entirely.** That is the point of fixes 1 and 2, and it is why the acceptance test in criterion 3
exists.

---

### Fix 1 — the record's identity must not depend on `HEAD`

- **`validation_id`'s preimage must contain no `rev-parse HEAD` value.** Replace the mutable
  `substrate.commit` contribution with **content hashes of the source files that actually produced the
  numbers**: `core/msi/artifacts/xs_momentum_v1/model.py`, `core/msi/csmp/validation.py`,
  `core/msi/csmp/void_precondition.py`, `scripts/csmp/run_a2_validation.py`, and
  `scripts/csmp/phase1_prereg_analysis.py` (the shared §5.2 `fwd()`). **Content hashes identify the code
  exactly and are immune to every later commit.**
- **Record `commit` as the *code commit*, not `HEAD`:** `git log -1 --format=%H -- <those paths>` — the
  last commit that actually touched the harness. It is stable across unrelated later commits (a docs edit
  does not move it) and it **genuinely contains the code**. Keep it as recorded provenance **outside** the
  `validation_id` preimage.
- Net effect: **re-running after an unrelated commit must produce a byte-identical record.**

### Fix 2 — the harness must be structurally incapable of a false attestation

Add a **dirty-tree guard**, held to the same standard as the VOID gate (which *raises* rather than flags):
if `git status --porcelain -- <the harness/artifact/analysis paths>` is **non-empty**, the run **refuses to
emit a record** and raises.

> A record naming a commit that does not contain its own code is a **false attestation**. The harness must
> not be able to produce one — exactly as it must not be able to produce a verdict on a VOID window.

Test it as `assert_void_clear` is tested: dirty a harness file, assert the run raises and writes nothing.

### Fix 3 — re-pin §1.1 truthfully, and regenerate

- Re-pin the §1.1 build-time row to **the real code commit** (the one containing the harness), and add the
  **source content hashes**.
- Regenerate the dev dry-run record. **`docs/reports/csmp_a2_records/` must end with exactly ONE record** —
  the two currently present are artifacts of this bug (they differ *only* in the commit field) and must not
  survive into Phase 6.

**On editing the FROZEN dossier:** §1.1's build-time row is the one place the freeze explicitly sanctions
writing (*"pin at build"*). Correcting a pin to a **true** value is completing that pin, not changing the
construct. **The construct fence — universe, score, K=40, metric, baselines, cost model, §5.2, and the
inference/extension design — is untouched, and touching it is an automatic NOT PASSED.**

### Fix 4 — persist the grid provenance (disclosure 2)

The 42 pinned sealed rebalance dates entered the frozen dossier from an **ad-hoc query with no script**.
The Lead Reviewer re-derived them independently and they **match exactly**, so the *fact* is verified — but
its *provenance* rests on a one-off check, against standing constraint 3 (*"the report is generated, not
hand-typed"*).

Add **`scripts/csmp/pin_sealed_grid.py`**: `trading_calendar` only (`trade_date`, `n_symbols` — **no price
table, no returns**; the non-price calendar-fact exception §1.1 authorises), printing the 42 dates and
asserting `count == 42`. **If the count is not 42 it must fail loudly — this is a VOID-check, never a
tuning lever.**

### Disclosure to carry forward (no code change)

The **`uncertainty` scalar is not a calibrated IC predictor**: the dev tercile IC is **non-monotonic**
(0.0485 / 0.0446 / 0.0496) against §7's stated expectation. **Keep reporting it plainly as a negative
result** in the Phase-6 report — do not soften it. It is non-gating, and it *vindicates* the
reported-not-acted-on fence: had increment 1 weighted or abstained on this scalar, it would have been
acting on a signal that demonstrably does not calibrate.

---

**Acceptance criteria (the Lead Review checks precisely these).**

1. **The attestation is true.** `git ls-tree -r <pinned commit>` **contains** `model.py`, `validation.py`,
   `void_precondition.py`, and `run_a2_validation.py`. *(This is the criterion the whole prompt exists for.
   It is checked first and it is dispositive.)*
2. **`validation_id` is HEAD-independent** — no `rev-parse HEAD` value appears anywhere in its preimage.
3. **The acceptance test — and it must actually be run and shown:** **(a)** run A2 from a clean tree →
   record R₁; **(b)** make an unrelated commit (e.g. a docs line); **(c)** re-run → record R₂. **Assert
   `R₁ == R₂` byte-for-byte, with the same `validation_id`. Paste both hashes into the report.** *This is
   the proof the circularity is broken — an assertion that it is broken is not evidence.*
4. **The dirty-tree guard is structural and tested** — a dirty harness path makes the run **raise** and
   write **nothing**.
5. **Exactly one record** in `docs/reports/csmp_a2_records/`.
6. **The numbers did not move.** The dev dry run still reconciles exactly: `n = 131`, `mean_IC = 0.0457`,
   rule-1/rule-2 = **21/1**, spread **+6.24%** / **+5.95%**. **Any change to a number is an automatic NOT
   PASSED — this prompt touches provenance, not computation.**
7. **`pin_sealed_grid.py` exists**, is calendar-only, reproduces the 42 pinned dates, and asserts the count.
8. **The construct fence held.** The only dossier diff is the §1.1 build-time pin row.
9. **The sealed window was not read.** Fence asserted and printed; observed max `trade_date` ≤ 2022-12-31.
10. **Phase 6 is still a date change and nothing else** — `--eval-lo` / `--eval-hi` / `--price-cutoff`,
    identical code paths.

**Definition of done.** The record says something **true** about the code that produced it, and says the
**same true thing** every time anyone re-runs it — forever, including after the very commit that records
the pin. Then Phase 6 can safely be what it was always meant to be: **a ceremony, not a build.**

DeepSeek V4 implements; Claude Lead-Reviews. **Do not begin Phase 6.**

---

## Prompt 10 — **PHASE 6: THE SINGLE SEALED READ**  **(ISSUED 2026-07-12)**

> **This prompt authorizes the one irreversible act in the entire program.**
>
> The held-out window **2023-01 → 2026-06** has never been read. After this run, it is **spent
> forever**. There is no second read, no re-run with different parameters, no "quick check." Every gate,
> every review, every correction of the last five days existed to make **this one execution** trustworthy.
>
> **You are not building anything. You are not deciding anything. You are running one command and
> reporting what it prints.**

### What is already settled, and is not yours to revisit

- The **pre-registration is FROZEN** (`CSMP_PHASE1_RESEARCH_DOSSIER.md` Rev 7), independently reviewed by
  a third model, with every finding folded in.
- The **gate is pinned**: the one-sided 95% Student-t lower bound of `mean_IC` > 0 → **Approved**;
  additionally `Δ_net > 0` → **Deployable**. **The code applies it. You do not.**
- The **decision table (§10) was written before anyone saw this data.** The harness renders the verdict
  mechanically. **You do not interpret it, adjust it, soften it, or comment on whether it is good news.**
- The **A2 harness is cleared** (`CSMP_PROMPT9_LEAD_REVIEW.md`, PASS on all 10 criteria) and has already
  rendered a complete verdict on the dev window, reproducing the frozen dossier exactly.

---

### Step 0 — the tripwire: prove the harness is the one that was cleared

**Before touching the sealed window**, re-run the **dev** dry run and confirm it still produces:

```
validation_id = a5c113dc8034ae76b0809042501d69715159d82a8b355b4b865806a5758198c6
code_commit   = 983cca082eb3b00588844ac5d4b0d97185b692dd
n = 131 | mean_IC = 0.0457 | rule-1/rule-2 = 21/1 | spread +6.24% / +5.95%
```

**If the `validation_id` differs by a single character, the harness is not the code the Lead Review
cleared. STOP. Do not proceed to the sealed read.** The dev record is a tripwire, and this is the last
moment it can catch a change.

The tree must be **clean** (the dirty-tree guard will enforce this and raise if not).

### Step 1 — the VOID precondition (§8 A1) — the run's own abort switch

The harness re-executes gate (b)'s `|move| ≥ 20%` single-day corporate-action screen **over the sealed
window**. This is a **data-quality** check, not a result — it reads no metric and renders no verdict, so
it does not break the seal.

> **If undocumented residue > 0, the run is VOID.** `assert_void_clear()` raises; **no metric is read and
> no verdict is rendered.** The window is **re-sealed, NOT spent** — because nothing about the hypothesis
> was observed. Report the residue rows, stop, and return to the operator for a gate-(b) fix.
>
> **A VOID is not a failure and it does not consume the read.** It is the safeguard working. A single
> wrong split factor manufactures ±50% phantom momentum and can inject that name straight into the top
> quintile — §12.1 names this the scariest inherited assumption, and this is the check that acts on it.

### Step 2 — the read. **Once.**

```
python scripts/csmp/run_a2_validation.py \
    --phase "6/sealed-read" \
    --eval-lo 2023-01-01 \
    --eval-hi 2026-06-30 \
    --price-cutoff 2026-06-30
```

**That is the entire change: three dates.** No code edit. No parameter tuning. No exploratory pass first.

**Absolutely forbidden — each is an automatic NOT PASSED and a scientific-integrity breach:**

1. **Running it more than once with different arguments.** One execution. If it crashes on a genuine
   infrastructure fault (disk, memory), report the traceback and **stop** — do not "just re-run it."
2. **Any code change after seeing the result.** Not a bug fix, not a formatting tweak, not a comment.
   **The moment the number is known, every subsequent edit is contaminated.** If you find a genuine bug
   after the read, **report it — do not fix it.** The operator and Lead Reviewer decide.
3. **"Sanity-checking" the sealed data.** No extra queries, no eyeballing the top-40 names, no plotting.
4. **Adjusting, re-scoring, or re-grading anything** because the verdict is disappointing.

### Step 3 — report exactly what happened

Script-generated (not hand-typed) → **`docs/reports/CSMP_PHASE6_SEALED_READ.md`**, plus the sealed MSI-006
record.

**The gate (the only thing that decides):**
- `n` (must be **42** — the pinned grid; if not, **STOP**, do not adjust anything to make it 42)
- `mean_IC`, its SD, and the **one-sided 95% Student-t lower bound**
- `Δ_net` vs the **stronger** of the two universe baselines
- **The verdict, rendered by code, verbatim from §10.**

**Reported, non-gating — all of it, whatever it says:**
`iid_perc` and `mb_L12` bounds (both readings stay visible); the `Δ_net` bootstrap CI; by-year IC and
hit-rate; §5.2 rule-1/rule-2 counts by year, with **every top-40 rule-2 event explicitly highlighted**;
the **−100% rule-2 sensitivity**; the sub-period split (2023-24 vs 2025-26); risk metrics for both arms
(vol, Sharpe, max drawdown); the **uncertainty-tercile calibration** (already known non-monotonic on dev —
report the sealed result plainly, whatever it is); the long-short quintile spread (reported, never traded);
the formation-exclusion count. Plus the sealed `validation_id`, `code_commit`, and the VOID screen result.

### Step 4 — the thing that matters more than the result

**Report the outcome faithfully, whatever it is. Do not spin it in either direction.**

The frozen dossier already told us, **before the data was seen**, what to expect:

> **A valid, one-sided, correctly-covered test on 42 months is only ~41% powered against the program's own
> point estimate. "Inconclusive" is the single likeliest outcome (~59%) — even if the hypothesis is exactly
> true.**

So:

- **If the verdict is Inconclusive: that is the modal, expected, non-failing outcome.** It is **not** a
  refutation, and it is **not** a licence to tune. The artifact is **Not Approved**, the window is
  **spent and never re-read**, and the top-40 PaperBroker consumer is still built — under the four
  charter-§6 amendment controls. **State the ~59% pre-registered expectation in the report so the result
  is read in the context that was fixed in advance.**
- **If the verdict is Rejected: say so plainly.** A falsified hypothesis honestly reported is a *successful*
  research outcome, and the program has already proved it can accept one — gate (e) could have returned
  STOP, and MSRP's D1 did.
- **If the verdict is Approved: state it flatly, with no triumph, and note that `Δ_net` decides
  deployability separately.** An Approved artifact whose `Δ_net ≤ 0` substantiates skill *without*
  transmission — the D1 outcome — and is **not deployed**.

**Do not editorialize. Do not recommend next steps. Do not argue with the number.** Print it, and stop.

---

**Acceptance criteria (the Lead Review checks precisely these).**

1. **The tripwire passed** — the dev `validation_id` is exactly `a5c113dc…` before the sealed read.
2. **The VOID screen ran first**, and its result is reported. If it VOIDed, **no verdict exists** and the
   window is re-sealed.
3. **The sealed window was read exactly ONCE.** Evidence: exactly one sealed record; one report; no
   parameter variations anywhere in the shell history or the report.
4. **Zero code diffs** between the cleared commit (`983cca0` harness) and the run. `git diff` over the five
   harness paths is **empty**. The dirty-tree guard makes this structural — do not defeat it.
5. **`n = 42`**, matching the pinned grid.
6. **The verdict is the code's**, rendered mechanically from §10 — not a human's reading.
7. **Every non-gating arm is reported**, including the ones that look bad.
8. **The ~59% Inconclusive pre-registration is stated in the report**, so the outcome is read against the
   expectation that was fixed before the data.
9. **No post-read edits.** Nothing in the repository changes after the number is known, except the
   generated report and record.

**Definition of done.** One command was run, once. The verdict came from a decision table written before
anyone saw the data, applied by code that a stranger can re-derive from a content-addressed record on any
machine. The number is what it is, and it is reported without decoration.

**This is what the last five days bought: the right to believe the answer.**

DeepSeek V4 executes; Claude Lead-Reviews. **Then the operator decides — per §10, and nothing else.**

> ### ⚠ PROMPT 10 IS SUSPENDED — DO NOT EXECUTE
>
> **The sealed read was correctly refused** (2026-07-12). The runner's report generator is
> dev-hardcoded and cannot produce the report Prompt 10 requires. **Prompt 11 remediates it; Prompt 10
> is re-issued (with a new Step-0 tripwire value) only after that passes Lead Review.**
>
> **The sealed window is intact.**

---

## Prompt 11 — Pre-read remediation: parameterize the report generator; re-clear the harness  **(ISSUED 2026-07-12)**

### What happened, and why the refusal was right

DeepSeek was told to execute the sealed read and **declined**, because the run would have spent an
irreversible resource to produce a corrupt artifact. **That judgment was correct, it was verified at the
source, and it is exactly the behaviour this program has been building toward.** The scoring, gate, VOID,
and record paths are all correct and phase-parameterized — **only the human-readable report generator is
dev-specific.** Confirmed:

| Defect | Evidence |
|---|---|
| Report path hardcoded | `run_a2_validation.py:46` — `REPORT = …/CSMP_A2_DEV_DRYRUN.md`. A sealed run would **overwrite the dev tripwire report** instead of creating `CSMP_PHASE6_SEALED_READ.md` (violates Prompt-10 C3) |
| Dev title + a literally false claim | `"# CSMP A2 — Dev-Window Dry Run"`, and `"The sealed window (2023-01 → 2026-06) was not read."` — **printed by the very run that read it** |
| Spurious MISMATCH | The reconciliation block hardcodes the **dev** targets (131 / 0.0457 / 21-1 / +6.24% / +5.95%). At `n=42` every row prints `✗ MISMATCH` and the report declares **"MISMATCH — harness defect, must be fixed before the seal"** — a false alarm baked permanently into the one sealed record |
| Missing required disclosure | `grep -c "59\|Inconclusive"` → **0**. Prompt-10 C8 requires the ~59% pre-registration in the report |
| **`n == 42` is unenforced** *(found in Lead Review — not in DeepSeek's list)* | **No `assert` anywhere.** Prompt-10 C5 says *"n must be 42; if not, STOP"* — but that was **a sentence in a prompt, not a guard in the code.** It must be structural, like the VOID gate |

**Root cause, and it is the Lead Reviewer's:** the Prompt-8 review verified *"Phase 6 = date change only"*
against the **scoring** path (`--eval-lo` / `--eval-hi` / `--price-cutoff`) and **never checked the
reporting path.** Prompt 10 then specified a report the runner could not produce. Recorded so the miss is
on the record, not buried.

---

### Scope — reporting layer and one guard. Nothing else.

**The construct fence is untouched and touching it is an automatic NOT PASSED:** universe, score, K=40,
metric, baselines, cost model, §5.2, the pinned gate, the inference/extension design. **The scoring, gate,
VOID, and record-writing paths are correct — do not refactor them.** This is a *reporting* defect, not a
science one.

**F1 — parameterize `_write_report()`:**

- **Output path by phase:** dev → `CSMP_A2_DEV_DRYRUN.md`; sealed → **`CSMP_PHASE6_SEALED_READ.md`**.
  A sealed run must **never** overwrite the dev tripwire report.
- **Phase-correct title and intro.** The sealed report must **not** claim the sealed window was not read.
  It must state, plainly, that the window **was read, once, and is now spent.**
- **The dev-reconciliation block runs in the dev phase only.** It is the tripwire, and it stays exactly as
  it is for dev — it must not be weakened. In the sealed phase it is **absent**, not "adjusted."
- **Add the required pre-registration disclosure to the sealed report** (Prompt-10 C8), verbatim in
  substance:

  > **Pre-registered before this data was seen:** a valid, one-sided, correctly-covered test on 42 months
  > is only **~41% powered** against the program's own point estimate. **"Inconclusive" is therefore the
  > single likeliest outcome (~59%) even if the hypothesis is exactly true.** This result must be read
  > against that expectation, which was fixed in advance — not against hope.

**F2 — make `n == 42` structural.** In the sealed phase, the harness **asserts the scored-month count
equals the pinned grid count (42) and raises otherwise**, on the `assert_void_clear` model: **no verdict
may be rendered on a window whose shape does not match the pre-registered grid.** A prompt sentence is not
a guard. *(Do not "adjust" anything to reach 42 — a mismatch means something is wrong upstream and the
operator decides.)*

---

### The consequence you must accept, not engineer around

Editing `run_a2_validation.py` **changes its content hash**, so the dev **`validation_id` will change** —
`d0651e10…` becomes something new. **That is correct and honest**, not a regression: the identity is
content-addressed *by design*, and different code legitimately produces a differently-identified record.
**Do not try to preserve `d0651e10…`.** Do not move the reporting code out of the hashed paths to dodge
the churn; the conservative whole-file hash is the property Prompt 9 established and it stays.

**The guardrail that proves the science did not move:** `results.json` must be **byte-identical** before
and after this change. The record's *name* changes; its *content* must not.

---

### Sequence

1. Fix `_write_report()` (F1) and add the `n == 42` guard (F2). **Commit the code first** — the dirty-tree
   guard will otherwise refuse to run, and correctly so.
2. Re-run the **dev** dry run from a clean tree → **new `validation_id`**.
3. **Re-pin** that new `validation_id` in dossier **§1.1** and in **Prompt 10 Step 0** (the tripwire value).
4. Lead Review → then **Phase 6 is re-issued**.

---

**Acceptance criteria (the Lead Review checks precisely these).**

1. **`results.json` is byte-identical** to the `d0651e10…` record's. **The numbers did not move: n=131,
   mean_IC 0.0457, rule-1/2 21/1, +6.24% / +5.95%.** *This is dispositive — a reporting fix that changes a
   result is not a reporting fix.*
2. **Dry-run report path is phase-parameterized**, and a sealed-phase run provably writes
   `CSMP_PHASE6_SEALED_READ.md` — **demonstrate with a dev-fenced dry invocation that exercises the
   sealed-phase report path without reading sealed data** (e.g. `--phase 6/…` with dev dates), or an
   equivalent test. **Do not demonstrate it by reading the sealed window.**
3. **No false claim survives.** The sealed report cannot say the sealed window was not read.
4. **The dev reconciliation block is unchanged for dev** (it is the tripwire) and **absent in the sealed
   phase** — not softened, not reworded.
5. **The ~59% pre-registration disclosure is present** in the sealed report.
6. **`n == 42` raises** in the sealed phase when violated — structural, tested, on the VOID model.
7. **The construct fence held**: no diff to scoring, gate, VOID, or record-writing logic; no dossier diff
   except the §1.1 `validation_id` re-pin.
8. **Exactly one dev record** afterwards (the new one). The stale `d0651e10…` record is removed — it no
   longer corresponds to any code in the tree.
9. **The sealed window was not read.** Fence asserted and printed; observed max `trade_date` ≤ 2022-12-31.
10. **Prompt 10 Step 0 carries the new tripwire `validation_id`.**

**Definition of done.** The harness can produce a truthful, correctly-located, correctly-disclosed sealed
report — and still refuses to score a window whose shape it did not pre-register. Then, and only then,
Phase 6 is re-issued.

**DeepSeek V4 implements; Claude Lead-Reviews. The sealed window stays sealed.**

---

## Prompt 12 — Make sealedness an invariant, not a string  **(ISSUED 2026-07-12)**

**Prompt 11 is NOT PASSED on one HIGH finding** (`CSMP_PROMPT11_LEAD_REVIEW.md`). Everything else is clean —
including the dispositive guardrail: `results.json` is byte-identical (`be662698…`), so the reporting fix
moved no number. **This is the last fix before Phase 6.**

### The finding

The Lead-Review amendment — *derive `sealed` from the data, not the label* — **was not implemented**:

```
scripts/csmp/run_a2_validation.py:356   sealed = str(args.phase).startswith("6")
core/msi/csmp/validation.py:49          if str(phase).startswith("6") and n != expected:
```

**The report's destination, the truthfulness of its central claim, and whether the `n == 42` guard arms at
all — all hang on a prefix match against a CLI string a human types.** And the fence does **not** save you:
`run_a2_validation.py:82` asserts only `observed_max <= price_cutoff`, which **passes while sealed rows are
read** when `--price-cutoff 2026-06-30`.

**Run Phase 6 as `--phase sealed-read` (no leading `6`) and:** the window is read and **spent forever**; the
`n == 42` guard never arms; the report overwrites **`CSMP_A2_DEV_DRYRUN.md`, destroying the tripwire**;
it prints `✗ MISMATCH` on every dev-reconciliation row; and it states, in the artifact produced *by the run
that read the sealed window*, **"The sealed window (2023-01 → 2026-06) was not read."** Every defect Prompt
11 eliminated returns at once — on the one run that cannot be repeated.

### The fix (small; nothing else changes)

1. **Derive sealedness from the data.** It is authoritative — it is the actual condition under which sealed
   rows enter the computation:
   ```python
   sealed = (price_cutoff > DEV_HI) or (eval_hi > DEV_HI)
   ```
2. **Cross-check the label and raise on disagreement**, catching both directions (a sealed window labelled
   dev; a dev window labelled Phase 6):
   ```python
   if str(phase).startswith("6") != sealed:
       raise PhaseWindowMismatchError(...)
   ```
   Raise **before** anything is scored, written, or read.
3. **Key `assert_grid_shape()` off the derived `sealed`**, not the label.

**Scope fence:** reporting/guard layer only. **No change to scoring, the gate, VOID, record-writing, or any
construct parameter.** `results.json` must remain byte-identical (`be662698…`) — a guard fix that moves a
number is not a guard fix.

**Accepted consequence:** the dev `validation_id` and `code_commit` change again (content-addressed by
design). Re-pin them in dossier §1.1 **and** Prompt 10 Step 0; keep exactly one dev record.

---

**Acceptance criteria.**

1. **`results.json` byte-identical** to `be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955`.
   **Dispositive.**
2. **No `startswith("6")` decides anything.** `grep -n 'startswith("6")'` returns **only** the
   label/window cross-check itself.
3. **`sealed` is data-derived** from `price_cutoff` / `eval_hi` against `DEV_HI`.
4. **`PhaseWindowMismatchError` raises in both directions** — tested: sealed dates + dev label → raises;
   dev dates + `6/…` label → raises. **Neither test may read the sealed window** (a *label/date* mismatch is
   detectable before any query — raise on the arguments, not on the data).
5. **`assert_grid_shape()` keys off derived `sealed`**, and still raises on n ≠ 42 in the sealed phase.
6. **Exactly one dev record**; §1.1 and Prompt 10 Step 0 carry the new `validation_id` / `code_commit`.
7. **Sealed window not read.** Fence asserted and printed; observed max ≤ 2022-12-31.
8. **Construct fence held** — no scoring/gate/VOID/record diffs; dossier diff = the §1.1 row only.

**Definition of done.** A mislabelled sealed run is **impossible**, not merely discouraged. The code — not a
typed string, and not an instruction in a prompt — decides what is sealed.

> **The lesson, stated once, because it has now appeared twice.** Prompt 11 existed to fix `n == 42`, which
> had been *"a sentence in a prompt, not a guard in the code."* This finding is the same species. **A
> safeguard that depends on a human typing a label correctly is not a safeguard.** Every protection standing
> between us and an irreversible mistake must be an invariant the machine enforces. Prompt 12 is where that
> stops being a principle and becomes the code.

**DeepSeek V4 implements; Claude Lead-Reviews. Then Phase 6 is re-issued. The sealed window stays sealed.**

---

> **On the refusal.** DeepSeek was given a direct instruction to execute the single most consequential
> command in the program, and it **stopped and escalated instead** — because running it would have burned
> an irreplaceable asset to produce a self-contradictory artifact. Every safeguard in this program exists
> for the moment when someone is holding an irreversible action and something is subtly wrong. **This was
> that moment, and the discipline held.** It is recorded here as the correct precedent: *when the next step
> is irreversible and the artifact is wrong, you stop — even when you have been told to go.*
