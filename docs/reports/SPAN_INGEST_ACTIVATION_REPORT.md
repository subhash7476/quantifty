# SPAN Ingest Activation Report

**Date:** 2026-08-04
**Author role:** implementer
**Origin:** `docs/reports/SE1_COUNTING_PASS_AND_SPAN_INGEST_PROMPT.md` Part A
**Lead review:** `docs/reports/SE1_AND_SPAN_LEAD_REVIEW.md` — ACCEPT; CRITICAL-1 (§6 retention claim falsified) closed in this revision, including the backfill.
**Status:** archive activated and **backfilled to the retention edge** (2026-08-04). The daily F&O end-of-day settlement SPAN file is archived to `data/span/`, the daily chain asserts it, and the ~14-month retrievable window has been walked backward and preserved.

---

## 1. The real source URL — determined empirically, not guessed

**Stub guess (`fetch_span_params.py` as found):**
```
https://www.nseindia.com/span/span_{ddmmyyyy}.zip
```

**Real URL, confirmed 2026-08-04:**
```
https://www.archive.nseclearing.in/content/allreports/fno/{DD-MM-YYYY}/nsccl.{YYYYMMDD}.s.zip
```
e.g. `.../fno/03-08-2026/nsccl.20260803.s.zip` → HTTP 200, ZIP, 8.9 MB.

### 1.1 How it was confirmed (evidence chain)

1. `https://www.nseindia.com/span/span_25062026.zip` (the stub) → **HTTP 404** for the known-good date 2026-06-25 (an NSE HTML 404 page, 229 KB). The `nseindia.com` SPAN paths are bot-blocked or discontinued.
2. Guessed patterns on `nseclearing.in`, `nsearchives.nseindia.com`, `archives.nseindia.com` → all 404.
3. The NSCCL SPAN pages (`/risk-management/equity-derivatives/nsccl-span`, `/pc-span`, `/span-risk-parameters`) are JS-driven; no static file link.
4. The **Market Reports SPA** (`https://www.archive.nseclearing.in/marketreports/marketreport/derivative/equities`) is Angular; its API is `GET https://www.archive.nseclearing.in/allreports/{code}`. Code **`DCEDD`** (equity-derivatives daily) returns the F&O daily report set. On 2026-08-04 it listed:
   - `F&O-Begin day SPAN file  → .../fno/04-08-2026/nsccl.20260804.i1.zip`
   - `F&O-1st/2nd/3rd Intra-day SPAN file → .../i2.zip / i3.zip / i4.zip`
   - previous day (03-08-2026): `.../i1.zip` … `.../i5.zip` and **`F&O-End of day SPAN File → nsccl.20260803.s.zip`**
5. Direct GET on `.../fno/31-07-2026/nsccl.20260731.s.zip` → **HTTP 200**, PK-zip, 8.93 MB. Its inner `.spn` carries `isSetl=1`, `setlQualifier=final`, `created=202607311608`. The `.s.zip` is the **end-of-day settlement file** — the one SE-5 needs.

**File naming convention (NSCCL, PC-SPAN 4.00):** per trading day NSE Clearing publishes
- `nsccl.{YYYYMMDD}.i1.zip` — begin-day (intraday, `isSetl=0`)
- `nsccl.{YYYYMMDD}.iN.zip` (N=2..5) — intraday updates (`isSetl=0`)
- `nsccl.{YYYYMMDD}.s.zip` — **end-of-day settlement** (`isSetl=1`, `setlQualifier=final`)

**Headers/cookies:** a browser **User-Agent is required**. A bare `urllib.request.urlopen` (the old `_default_download`) was connection-reset (`WinError 10054`) against `archive.nseclearing.in`; the same request with a `User-Agent` header returned HTTP 200. No cookies required. Added the header in `span_pipeline._default_download`, minimally.

## 2. The four defects — re-verified at implementation time

| # | Claim | Line evidence (as found) | Verified |
|---|---|---|---|
| A.3-1 | `promote_snapshot` guaranteed to early-return; no `.parquet` ever written | `fetch_span_params.py:67` sets `dest_path = SPAN_DATA_DIR / f"nse_fo_span_{date}.zip"`; `download_span_data` (`span_pipeline.py:50`) writes exactly that; `promote_snapshot` (`span_pipeline.py:77-79`) returns early **if `zip_path` exists** — the same string | **Confirmed empirically**: with the old flow, a run that reaches `promote_snapshot` leaves `nse_fo_span_2026-06-25.zip` on disk, **no** `.parquet`, and `list_archive_dates()` returns `[]` — an archive that reports empty while filling up |
| A.3-2 | URL is a flagged guess and almost certainly wrong | `fetch_span_params.py:34-40` guesses `https://www.nseindia.com/span/span_{ddmmyyyy}.zip` | **Confirmed**: 404 on a known-good date; real URL is the `archive.nseclearing.in` `/content/allreports/fno/.../nsccl.{yyyymmdd}.s.zip` pattern (§1) |
| A.3-3 | The file is never parsed | `fetch_span_params.py:88` hardcodes `risk_arrays={}`; comment claims "actual NSE CSV parsing will be implemented" — the format is XML | **Confirmed**: format is XML (`fileFormat 4.00`), and the frozen `ParserV400` (via the registry, key `"4.00"`) parses it; the stub archived empty snapshots |
| A.3-4 | Over-broad exception handling | `fetch_span_params.py:70-74` wraps the download in `except Exception`, mapping every failure to exit 1 "download failure" | **Confirmed**: a parse or write failure would have been recorded as a source failure |

## 3. What was built

### 3.1 `scripts/fetch_span_params.py` — repaired in place (no parallel script)

- **Real URL template** (§1), built from the trading date (`build_url`).
- **Raw-first retention** (load-bearing): the zip is written to `data/span/staging/nsccl_{date}.zip` **before** any parse is attempted. A parse failure exits non-zero (3) but **never deletes the raw** and **never** writes a `.parquet`. Exit 3 logs "raw zip retained at <staging path>".
- **A.3-1 fix** — staging path, chosen over re-keying the append-only guard (which existing tests pin): the download target and the archive path are now distinct, so `promote_snapshot`'s append-only check operates on a clean archive. A full run leaves **both** `nse_fo_span_{date}.zip` and `nse_fo_span_{date}.parquet` in `data/span/`, and `SpanRepository.load()` returns a snapshot with non-empty `risk_arrays` (post-archive assertion in the script, exit 2 on failure).
- **A.3-3 fix** — `ParserV400` via the registry: `span.parse_span_xml("4.00", spn_bytes)` where `spn_bytes` is the single `.spn` extracted from the downloaded zip. No second parser written; the frozen parser untouched.
- **A.4-5 — settlement flag populated from the file, never hardcoded.** `is_settlement` comes from `<isSetl>` (parser). The job targets the `.s` (settlement) file and **asserts** `is_settlement is True`; a non-settlement payload exits non-zero (3) with the raw retained — so the 2028 panel cannot silently become an intraday panel. `setlQualifier` is recorded in `metadata` (via `dataclasses.replace` on the frozen snapshot; the frozen parser is not modified). `file_hash` is the SHA-256 of the **archived zip** (the contract `SpanRepository.load` verifies); the `.spn` hash is kept in `metadata["spn_sha256"]`.
- **A.4-6 — miss-caching discipline.** A date is classified MISSING only on HTTP 404 — never on a parse or write failure. A miss marker (`nsccl_{date}.zip.404`) is written **only** when the date has closed (`d < today`, `_may_cache_miss`); a 404 for today returns exit 1 (retry) and writes nothing — the "289 permanent markers for future dates" failure cannot recur.

### 3.2 `core/risk/span/span_pipeline.py` — minimal change

`_default_download` now sends a browser `User-Agent` (required by the host, §1.5). No other change.

### 3.3 Scheduling — asserted freshness in the daily chain

`core/scheduler/eod_chain.py` `CHAIN_STEPS` gains, **last**:
```
("fetch_span_params.py", SCRIPTS / "fetch_span_params.py")
```
- The SPAN result is **asserted, not printed**: the job exits non-zero if the settlement file cannot be archived or the archived snapshot fails to load with non-empty `risk_arrays`; `run_attempt` surfaces any failure via `format_chain_failure` (Telegram) and records `chain_failed` in `EodStore` — a checked condition whose failure is visible.
- Placed **last** so a late/absent SPAN file fails the chain visibly but never blocks the strategy work above it.

## 4. Predictions A-P1 … A-P5

| # | Prediction | Result |
|---|---|---|
| **A-P1** | The stub's URL template returns a non-200 for a known-good recent trading day | **PASS** — `https://www.nseindia.com/span/span_25062026.zip` → HTTP 404 for 2026-06-25 |
| **A-P2** | Against the current stub, a run that reaches `promote_snapshot` writes a `.zip` and **no** `.parquet` | **PASS** — demonstrated empirically (§2, A.3-1); `list_archive_dates()` returned `[]` with the zip present |
| **A-P3** | `ParserV400` parses `nsccl.20260625.i01.spn` into a snapshot with `len(risk_arrays) > 0` | **PASS** — 239 risk arrays, snapshot_date 2026-06-25, in ~10 s |
| **A-P4** | The sample file has `isSetl` = 1 (settlement) | **FAIL — a finding.** Both on-disk samples (`nsccl.20260625.i01.spn`, `nsccl.20260701.i01.spn`) have `isSetl=0`, `setlQualifier=early` — they are **intraday** snapshots. The settlement file is a distinct publication (`nsccl.{YYYYMMDD}.s.zip`, `isSetl=1`, `setlQualifier=final`). The daily job therefore targets the `.s` file and asserts the flag (§3.1); it does not silently archive intraday files. |
| **A-P5** | After the repair, one full run leaves both artifacts on disk and `SpanRepository.load()` returns non-empty `risk_arrays` | **PASS** — real run for 2026-08-03 archived `nse_fo_span_2026-08-03.zip` + `.parquet`; `SpanRepository.load(date(2026,8,3))` → 236 risk arrays, `is_settlement=True`, `setl_qualifier="final"` |

## 5. First archived date and current state

- **First archived date: 2026-08-03** (the latest closed trading day at activation, 14:14 IST on 2026-08-04; today's settlement file publishes ~17:00 IST and the scheduled 20:00 IST run picks it up).
- `data/span/` holds `nse_fo_span_2026-08-03.zip` (raw) + `nse_fo_span_2026-08-03.parquet` (parsed); staging holds the downloaded zip.
- **Backfill (lead review CRITICAL-1):** the retrievable window has been walked backward to the retention edge — see §6 for the exact boundary, counts, and intra-window gaps.

## 6. Retention and backfill — corrected after lead review (CRITICAL-1)

**The original §6 claim — *"no historical backfill is possible"* and *"the market-reports surface retains a short window (current + previous day by design)"* — is falsified.** The activation report itself already contained the contradiction: §1.1 step 5 served `nsccl.20260731.s.zip` (four days old, and not in the SPA listing) with HTTP 200. The SPA *lists* two days; the date-path URL *serves* a rolling window. Those are different questions, and §6 generalised from the listing to the host.

**Measured retention (probes on 2026-08-04, browser UA, ranged GET):**

| Date | Result |
|---|---|
| 2026-07-28 / 2026-07-03 / 2026-02-03 / 2025-08-04 | served |
| 2025-07-01 | **served** |
| 2025-06-16 | **404** |
| 2025-06-02 / 2025-05-05 / 2025-03-03 / 2025-01-06 / 2024-11-04 … 2020-08-04 | 404 |

The retention edge sits **between 2025-06-16 (absent) and 2025-07-01 (served)** — a rolling window of roughly 14 months, not "current + previous day". The exact edge is determined by the backfill walk (below) and recorded there.

**Consequence — the backfill was run (2026-08-04, immediately on the review finding).** **274 trading sessions** of end-of-day settlement SPAN files were archived by walking backward from 2026-08-03 over the trading calendar until the retention edge (a run of 3 consecutive 404s). The repaired path is reused unchanged: raw-first retention, the `is_settlement` assertion, and the settlement-flag check all apply per date. A.4-6 discipline inside the walk: a 404 on a past trading day inside the window is a real miss and is cached (`nsccl_{date}.zip.404`); the run of misses that ends the walk is the **retention edge**, reported separately from source gaps — the two never collapse into one label.

**Backfill result (2026-08-04):**
- Archive now spans **2025-06-19 → 2026-08-03**, **275** settlement snapshots (274 backfilled + the activation date).
- **Retention edge pinned: 2025-06-19 present, 2025-06-18 absent** (tighter than the probe bracket 2025-06-16 → 2025-07-01).
- **Intra-window gaps (genuine absences, cached):** 2025-09-19 + 2025-09-18 (2-day gap), 2025-06-30. Every other trading day in the window served and archived.
- **0 parse/promote errors** across the walk.
- Full run log: `data/span/backfill_2026-08-04.log`.

**What this does not change:** SE-5 is not unblocked. Fourteen months is not a research panel for a margin-shock event study, and the clustering hazard that fired on SE-1 applies with more force here — a volatility spike moves scanning ranges across every contract at once, so nominal contract-events vastly exceed effective ones. What the backfill buys is the ability to probe the observation structure now (event frequency, cross-contract clustering, an `N_eff` estimate) instead of discovering it in 2028. It is not a licence to build SE-5.

**And the decay continues:** the daily job protects the leading edge, but the trailing edge drops off at roughly one session per day. Every day of delay is one more session lost permanently — the cost structure the original §6 correctly identified and then mislocated.

## 6a. Sibling-ingest audit (lead review action 6)

The equity ingest's `.404`-marker forward-probe defect is the documented case; the F&O ingests were recorded as unaudited for it. Audited 2026-08-04: `scripts/sfb/ingest_futures_bhavcopy_v2.py`, `scripts/sfb/ingest_stock_options_bhavcopy.py`, `scripts/msrp/ingest_option_bhavcopy.py` all handle 404s **in-process** (count + consecutive-404 break) and **persist no permanent miss markers** — so a forward probe of an unpublished date writes no state and cannot short-circuit a later run. The only persistent-miss mechanism in the platform is the equity ingest's, which is already guarded by `_may_cache_miss`. The residual unprobed-claim risk is the *retention* family this review just caught (claiming absence without probing the endpoint); the F1 "no futures history before 2016" claims are documented against actual probes (`F1_UPSTOX_INGESTION_DETERMINATION.md`), not assumed.

## 7. Tests

`tests/risk/span/test_fetch_span_params.py` — 7 tests covering A-P3 (real-file parse, skip-guarded), A-P5 (full run → both artifacts + loadable non-empty risk_arrays; append-only re-run), the settlement-flag refusal (raw retained, exit 3), bad-zip parse failure (raw retained, exit 3), miss-caching for closed vs open dates, and the URL shape. Full span + scheduler suites: **310 passed**.
