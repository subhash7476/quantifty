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

## Prompt 1 — Gate (a): Equity daily bhavcopy ingestion + quality audit  **(ISSUED)**

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

## Prompt 2 — Gate (b): Corporate-action adjustment + audit  **(HELD — issued after gate (a) PASS)**

Preview (final prompt after the gate-(a) review): source split/bonus/face-value-change
(and material rights) events for all symbols in the store; build an
`adjustment_factors` table (symbol, ex_date, factor, action_type, source); produce
adjusted-price views used by all downstream CSMP research; audit: every single-day
raw-price move ≤ −20% or ≥ +25% in 2010→present classified (corporate action vs
genuine vs data error) with an unexplained-residue count — nonzero unexplained residue
in the dev window is NOT PASSED.

## Prompt 3 — Gate (c): Survivorship / universe membership + audit  **(HELD)**

Preview: point-in-time NIFTY-200 membership table (symbol, entry_date, exit_date) from
NSE index-change announcements if obtainable; else the charter's locked fallback — a
mechanical top-200-by-6-month-median-turnover rule computed from the gate-(a) store
only, reconstructable as-of any date. Audit: membership count through time, turnover of
membership per rebalance, delisted-name retention proof (names that later delist must
appear in the universe while listed).

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

*Prompts 2–5 are held deliberately: each is finalized only after the preceding gate's
review, so findings propagate forward instead of being discovered twice.*
