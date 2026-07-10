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

## Prompt 2 — Gate (b): Corporate-action adjustment + audit  **(ISSUED 2026-07-10)**

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

## Prompt 3 — Gate (c): Survivorship / universe membership + audit  **(HELD)**

Preview: point-in-time NIFTY-200 membership table (symbol, entry_date, exit_date) from
NSE index-change announcements if obtainable; else the charter's locked fallback — a
mechanical top-200-by-6-month-median-turnover rule computed from the gate-(a) store
only, reconstructable as-of any date. Audit: membership count through time, turnover of
membership per rebalance, delisted-name retention proof (names that later delist must
appear in the universe while listed).
**Inherited from gate (a) — H2 (binding when issued):** 200 ETF symbols (matching
`%BEES%`/`%ETF%`/`%GOLD%`) carry `series = EQ` in the store; the equity momentum universe
must exclude ETFs (`LIQUIDBEES`, a near-constant-NAV cash proxy, would rank pathologically
in any momentum sort).

## Prompt 4 — Gate (d): Delivery-equity fee model  **(HELD)**

Preview: `core/execution/equity/delivery_fees.py` mirroring the options fee model
pattern (`core/execution/options/fees.py`) — effective-dated statutory schedule: STT on
delivery (both sides), stamp duty (buy side), NSE transaction charge, SEBI turnover
fee, GST on the applicable base, DP charge per sell line; era-accurate rates with
primary-source citations in the docstring; unit tests in
`tests/execution/test_delivery_fees.py` with hand-computed arithmetic.

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

*Prompts 3–5 remain held deliberately: each is finalized only after the preceding gate's
review, so findings propagate forward instead of being discovered twice. Prompt 2 was
issued 2026-07-10 on gate (a)'s final PASS (`CSMP_GATE_A_LEAD_REVIEW.md` Round 8).*
