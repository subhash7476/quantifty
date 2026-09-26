# Implementer Prompt — SPAN Daily Ingest (Part A) + SE-1 Counting Pass (Part B)

**Date:** 2026-08-04
**Author role:** research lead (prompt + review only — the implementer writes the code)
**Origin:** `docs/reports/STRUCTURAL_ALPHA_DOSSIER_2.md` §Part III.2 and §Part III.4
**Status:** authorized to implement. **Neither part is a research read. Neither part opens a sealed window. Neither part computes a return.**

---

## 0. Discipline that applies to both parts

1. **Falsifiable predictions before the run.** Each part states predictions below. Record PASS/FAIL against each in the report. A FAIL is a finding, not a failure — do not adjust the prediction after seeing results.
2. **No over-engineering.** No abstractions for one-time use, no retry frameworks, no config layers. A crash with a clear traceback beats a swallowed exception.
3. **Catch only the specific exception intended.** CLAUDE.md's pitfall register is explicit: a broad `except` around a download turns *"we failed"* into *"the source doesn't have it"*, and that claim then gets written into a governance report as a fact about the world. 46 downloadable NSE sessions were lost that way.
4. **Report to `docs/reports/`** before presenting anything. Script-generated numbers only — no hand-edited figures.
5. **Read the file before modifying it.**

---

# PART A — SPAN daily ingest

## A.1 Why this exists

`STRUCTURAL_ALPHA_DOSSIER_2.md` SE-5 proposes margin-regime shocks as an exogenous forced-deleveraging event cross-section. It is **blocked on data**: NSE Clearing publishes SPAN files for the current day only, and historical daily archives are not distributed at retail scale.

**This part builds no research and tests no hypothesis.** It starts the clock. Every day not archived is a day permanently lost. The payoff is in ~2028.

**Scope discipline:** do not build analysis, do not build a margin-change detector, do not touch SE-5's construct. Archive the files correctly and stop.

## A.2 What already exists — verified at source this session

| Component | State |
|---|---|
| `core/risk/span/parser_v400.py` — NSE SPAN v4.00 XML parser | **Exists, feature-frozen (MM9.5)** |
| `core/risk/span/span_snapshot.py` — `SpanSnapshot`, `SpanRiskArray` | Exists, frozen |
| `core/risk/span/span_repository.py` — read-only archive access | Exists, frozen. Globs `nse_fo_span_*.parquet`; `load()` does `pickle.load` |
| `core/risk/span/span_pipeline.py` — `download_span_data`, `promote_snapshot`, `list_archive_dates`, `latest_archive_date` | Exists |
| `core/risk/span/span_freshness.py` — `expected_span_date()` | Exists |
| `scripts/fetch_span_params.py` — the fetch job | **Exists as a stub. Four defects, below.** |
| `docs/reports/SPAN_XML_SCHEMA_AND_MM9_MAPPING.md` | **Complete schema spec** — PC-SPAN `fileFormat` 4.00, XML, CRLF, latin-1 |
| `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn` | **A real 57.2 MB sample file on disk** |
| `data/span/` | **Does not exist. The archive is empty.** |

**The parser exists and the archive does not.** That is the exact shape of CLAUDE.md's standing pitfall — a certified parser pointed at nothing is not a data asset.

## A.3 The four defects in `scripts/fetch_span_params.py`

Cite these by line in your report; do not take them on trust, re-verify each.

**A.3-1 — `promote_snapshot` is guaranteed to early-return, so no `.parquet` is ever written.**
- `fetch_span_params.py:67` sets `dest_path = SPAN_DATA_DIR / f"nse_fo_span_{trading_date.isoformat()}.zip"`.
- `span_pipeline.download_span_data` (line 50) writes exactly that path.
- `promote_snapshot` (lines 77–79) returns early **if `zip_path` already exists** — and `zip_path` is computed to the same string.

So on every successful run, the raw zip lands and `promote_snapshot` immediately skips. `SpanRepository.latest_version()` globs `*.parquet` and would return `None` forever while zips accumulate. **An archive that reports empty while filling up** — the "container checks are not content checks" family from the pitfall register.

**A.3-2 — the URL is a flagged guess and is almost certainly wrong.**
`fetch_span_params.py:34–40` carries an explicit comment that `NSE_SPAN_URL_TEMPLATE` must be confirmed at implementation time. It guesses `https://www.nseindia.com/span/span_{ddmmyyyy}.zip`. The on-disk sample is named `nsccl.20260625.i01.spn` inside `nsccl.20260625.i1/` — an **NSCCL** naming convention, not that pattern. **Determine the real URL empirically. Do not ship a guess.**

**A.3-3 — the file is never parsed.**
`fetch_span_params.py:88` hardcodes `risk_arrays={}`, and the comment at 77–79 claims "actual NSE CSV parsing will be implemented" — **which is wrong: the format is XML, and `ParserV400` already parses it.** Even with a correct URL, this job would archive empty snapshots.

**A.3-4 — over-broad exception handling.**
`fetch_span_params.py:70–74` wraps the download in `except Exception` and maps everything to exit 1 ("download failure"). A parse or disk-write failure is thereby recorded as a source failure.

## A.4 What to build

Repair `scripts/fetch_span_params.py`. Do not create a parallel script.

**A.4-1 — Determine the real source URL.** Empirically, against NSE Clearing. Record in the report: the exact URL template, how you confirmed it, the HTTP status for a known-good recent trading day, and whether headers/cookies are required. Note `span_pipeline._default_download` (lines 26–29) uses a bare `urllib.request.urlopen` with no headers — NSE commonly rejects that. If browser-like headers are needed, add them **in `_default_download`**, minimally.

**A.4-2 — Raw-first retention. This is the load-bearing requirement.**
The raw file is the irreplaceable asset; parsing can be redone in 2028, a missed day cannot. Therefore:
- Write the raw payload to disk **first**, before any parse is attempted.
- **A parse failure must never prevent raw retention, and must never delete the raw file.**
- Exit non-zero on parse failure so the operator sees it — but with the raw already durable.

**A.4-3 — Fix the `promote_snapshot` collision (A.3-1).** Either download to a staging path distinct from the archive path, or change the append-only guard to key on the `.parquet`. Whichever you choose, state it and add a test that a full run leaves **both** a `.zip` and a `.parquet` on disk and that `SpanRepository.load()` returns a snapshot with **non-empty `risk_arrays`**. That assertion is the whole point — a test that only checks file existence would reproduce A.3-1.

**A.4-4 — Wire in `ParserV400`.** Use the frozen parser via the registry; do not write a second parser and do not modify the frozen one. Validate against `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn`.

**A.4-5 — Record `isSetl` and `setlQualifier` in snapshot metadata.** Per the schema doc §1.1, `isSetl` is `0` for an intraday snapshot and `1` for end-of-day settlement. **SE-5 needs the settlement file, not intraday snapshots.** If the daily job silently archives intraday files, the 2028 panel is the wrong panel and nobody will know. `SpanSnapshot` already carries `is_settlement` — populate it from the file, never hardcode it.

**A.4-6 — Miss-caching discipline.** If you cache "this date has no file", follow `_may_cache_miss()` in `scripts/ingest_equity_bhavcopy.py`:
- Classify a date MISSING **only** on a non-200 HTTP status — never on a parse or write failure.
- **Never cache a miss for a date that has not yet closed.** A prior run wrote 289 permanent `.404` markers for future dates and would have silently skipped ingestion for five months.

**A.4-7 — Schedule it.** Hook into the existing daily chain (`scripts/schedule_worker.py` / the EOD automation). Two requirements, both from the pitfall register:
- The SPAN result must be **asserted, not merely printed**. `eod_decision.decide()` gating on one feed made every other feed optional, and a stale-feed value that was printed in every Telegram message but consumed by no code is documentation, not a control.
- Report SPAN archive freshness as a **checked condition** whose failure is visible.

## A.5 Explicit non-goals

- No backfill. Historical SPAN is not retrievable; do not write code that implies otherwise, and do not record absence of history as a source limitation without evidence.
- No margin-change detection, no event extraction, no analysis.
- No modification to any MM9.5/MM10-frozen component.

## A.6 Falsifiable predictions — state PASS/FAIL for each

| # | Prediction |
|---|---|
| **A-P1** | The stub's URL template returns a non-200 for a known-good recent trading day. |
| **A-P2** | Against the current stub, a run that reaches `promote_snapshot` writes a `.zip` and **no** `.parquet` (confirming A.3-1). |
| **A-P3** | `ParserV400` parses `nsccl.20260625.i01.spn` into a snapshot with **`len(risk_arrays) > 0`**. |
| **A-P4** | The sample file has `isSetl` = 1 (settlement), matching the schema doc's `<isSetl>` field. |
| **A-P5** | After the repair, one full run leaves both artifacts on disk and `SpanRepository.load()` returns non-empty `risk_arrays`. |

If **A-P3 fails**, stop and report. It would mean the frozen parser does not handle the file NSE currently publishes, which is a materially larger finding than this task — do not work around it by writing a second parser.

## A.7 Deliverables
- Repaired `scripts/fetch_span_params.py` (+ minimal `span_pipeline.py` changes if needed).
- Tests under `tests/risk/span/` covering A-P3 and A-P5.
- Scheduled daily invocation with an asserted freshness condition.
- `docs/reports/SPAN_INGEST_ACTIVATION_REPORT.md` — URL determination and evidence, the four defects re-verified by line, predictions A-P1…A-P5 with PASS/FAIL, first archived date, and a plain statement that **no historical backfill is possible**.

---

# PART B — SE-1 counting pass

## B.1 Why this exists, and what it is not

`STRUCTURAL_ALPHA_DOSSIER_2.md` ranks **SE-1 (forced passive rebalancing flow)** first, on the claim that index reconstitution yields *"several hundred name-events, √n ≈ 21, δ/sd ≈ 0.13 suffices."*

**That claim is under-tested and this pass exists to test it.** The events are not independent: every name added in a given March review shares one market environment, one flow wave, one liquidity regime. This is structurally the same failure that gave **OSC `N_eff = 1.9` against 283 nominal cells/day**. The dossier applied the effective-breadth test hard to SE-3 and not hard enough to SE-1.

The platform's standing gate — *every new research construct must clear the RFA before any construct code is written* — needs `n`. This pass produces `n`, honestly bounded.

**This is a counting exercise.** It reads no price data, computes no return, and takes no position on whether the effect exists.

## B.2 Hard prohibitions

- **Do not read any price, return, OHLCV, futures, or options data.** Not for context, not for a sanity check.
- **Do not compute an abnormal return, an event study, or any P&L.**
- **Do not write an RFA declaration.** This pass feeds one; it is not one.
- If you find yourself wanting to "just look at whether adds outperform" — that is the prior-exposure contamination that cost TS Basis Daily its windows. Stop and report the temptation instead.

## B.3 What exists

| Component | State |
|---|---|
| `scripts/download_mcwb_archives.py` | Downloads **monthly** Nifty Indices MCWB archives; validates `nifty50_mcwb.csv` present with 50 constituents + weights; manifest at `data/reference/mcwb_manifest.json` |
| `scripts/csmp/build_universe.py` | PIT membership + `symbol_entity_intervals` + ISIN issuer linkage |
| CB-N50 substrate certification | Used official NSE MCWB PIT membership at a **0.024% miss rate** |

**Note the resolution limit up front:** MCWB is **monthly**. Diffing consecutive months yields the *event list* and a month-resolution effective window. **It does not yield the announcement date**, and announcement-vs-effective is the entire mechanism of SE-1. Treat MCWB as the instrument for *enumerating* events, never for timestamping them.

## B.4 Steps

**B.4-1 — Enumerate candidate change events.** Diff the Nifty 50 constituent set across consecutive MCWB months over the full available span. Report the span actually covered and any missing months (a gap fabricates or hides events at both edges — do not interpolate).

Also report whether the MCWB archives contain indices beyond `nifty50_mcwb.csv`. If Nifty Next 50 / Nifty 100 are present, count them separately — they change the arithmetic and the decision.

**B.4-2 — Entity-resolve every diff.** A raw set-diff will report spurious changes from renames, demergers, ISIN re-issues and recycled tickers. CLAUDE.md records three distinct classes of this: entity-grain rename seams, the recycled DTIL ticker, and PHILIPCARB/PCBL ISIN issuer fragmentation. Use `symbol_entity_intervals` and ISIN **issuer-prefix** linkage — full-ISIN matching severs a company at exactly the corporate action it must adjust for.

Report **raw diffs**, **entity-resolved genuine changes**, and the delta between them, itemised. The delta is a finding.

**B.4-3 — Classify each genuine event** as scheduled (semi-annual review) or ad-hoc (M&A, suspension, regulatory). Ad-hoc events have different announcement dynamics and may cluster differently.

**B.4-4 — Source announcement dates, for the enumerated events only.** From the contemporaneous NSE Indices press release / circular. Record for each: announcement date, effective date, and the lag. **Where an announcement date cannot be sourced, record it as `UNKNOWN` — never impute it, never substitute the effective date.** Report the coverage rate; if it is low, that is the single most important output of this pass, because it bounds what SE-1 can ever be.

**B.4-5 — Compute the clustering structure.** This is the point of the exercise.
- `n_nominal` = genuine name-events
- `n_clusters` = distinct announcement dates
- ratio `n_nominal / n_clusters`
- distribution of names per cluster (min / median / max)
- calendar span of clusters

**B.4-6 — Run the power arithmetic both ways**, using `scripts/rfa/power.py` — do not hand-derive it. For `n = n_nominal` and for `n = n_clusters`, report the required `δ/sd` for two-sided power 0.80. Present them side by side.

## B.5 Falsifiable predictions — state PASS/FAIL for each

| # | Prediction |
|---|---|
| **B-P1** | Genuine entity-resolved Nifty-50 name-events over the MCWB span fall in **40–100**. |
| **B-P2** | Distinct change-clusters number **< 30**. |
| **B-P3** | `n_nominal / n_clusters` lies in **2–4**. |
| **B-P4** | Raw set-diffs **exceed** entity-resolved genuine changes (corporate actions inflate the naive count). |
| **B-P5** | Announcement dates are sourceable for **≥ 80%** of genuine events. |

## B.6 The decision rule — pin this before running

> **If `n_clusters < 30` and `n_nominal / n_clusters ≥ 3`, then the honest observation unit is the cluster, `√n ≤ 5.5`, and the required `δ/sd` is roughly triple the dossier's figure. SE-1's arithmetic is then NOT comfortable, and its #1 ranking in `STRUCTURAL_ALPHA_DOSSIER_2.md` must be revised in writing before any RFA declaration is drafted.**

This does not necessarily kill SE-1 — inclusion premia are measured in whole percent, so a high `δ/sd` may still be defensible. But it must be argued explicitly, against published effect sizes, and not inherited from this dossier's optimistic framing.

Stating the rule now is what makes the run informative. **Do not revise it after seeing the counts.**

## B.7 Deliverables
- `scripts/se1/count_index_events.py` — enumeration, entity resolution, clustering, power arithmetic.
- A committed event register (dated, itemised, with `UNKNOWN` announcement dates preserved as `UNKNOWN`).
- Tests for the entity-resolution path — at minimum a rename, a recycled ticker, and an ISIN re-issue must each resolve to one entity and not to a spurious add+drop pair.
- `docs/reports/SE1_EVENT_COUNTING_REPORT.md` — the two counts, the ratio, the cluster distribution, announcement-date coverage, both power arithmetics side by side, predictions B-P1…B-P5 with PASS/FAIL, and an explicit verdict against §B.6.

---

## Sequencing

Part A and Part B are independent. **Part A first if only one can be started** — it has a decay cost (every unarchived day is lost permanently); Part B does not.

## What happens next

- **Part A** → the archive begins accumulating. Nothing else changes until ~2028.
- **Part B** → feeds an RFA declaration for SE-1, or forces the dossier's ranking to be rewritten. Either outcome is worth the cost, which is one script and no market data.

Both reports return to the research lead for review before any construct work proceeds.
