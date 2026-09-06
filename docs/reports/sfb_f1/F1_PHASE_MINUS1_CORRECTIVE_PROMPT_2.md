# F1 / SFB-1 — Phase −1 Corrective Prompt #2: Fix the Ingestion, Then Acquire the Actual Substrate

**For:** the implementer (DeepSeek Flash), per the standing role split.
**Supersedes:** `F1_PHASE_MINUS1_CORRECTIVE_PROMPT.md` (2026-07-18) — that prompt fixed the roll math, STT schedule, and certification-arm self-referentiality. Its code corrections were correctly implemented and the unit tests pass. This prompt addresses what that corrective pass *did not* fix: the ingestion pipeline's inability to actually acquire TRAIN/HOLDOUT data.
**Driven by:** `F1_PHASE_MINUS1_INGESTION_REVIEW.md` (2026-07-19, lead review). Read that review first.
**Authorization:** unchanged. Phase −1 remains open. No freeze, no scoring, no sealed read.

---

## §0 — What happened and why we are here

Three passes have run against this substrate:

| Pass | What was delivered | Verdict |
|------|-------------------|---------|
| 1 (original) | Code compiles, unit tests green. Roll math wrong, STT wrong, cert arms never ran against real data, `futures_bhavcopy.duckdb` didn't exist. | REJECT |
| 2 (corrective #1) | Code corrections implemented. Real run produced 2-trading-day island. Cert arms returned 0 violations vacuously (nothing to test). | REJECT |
| 3 (after more work) | Code is mechanically correct (parsing, roll math, cert arms pass on 2,266 real splices). **But the substrate is 99.6% SEALED — TRAIN is empty, HOLDOUT is one stray day.** | **NOT CERTIFIED** |

The current `.duckdb` live counts (queried directly, not from the report):

| Window | Purpose | Rows |
|--------|---------|-----:|
| TRAIN 2012–2018 | factor sign + bracket-grid selection + regime map | **0** |
| HOLDOUT 2019–2022 | single out-of-sample confirmation | **602** (one day: 2022-08-08) |
| SEALED 2023→present | untouched; spent at most once after HOLDOUT confirms | **158,399** |

The cache dir tells the same story: **1,698** `focal_*.404` markers against **1** `focal_*.zip`. The legacy NSE archive (where TRAIN-era data lives) was never actually populated — every pre-2024 date was either a genuine weekend/holiday 404 or a network-block 404, and the code cannot distinguish them and never retries.

**The ingestion code is not done.** "Purely data acquisition" is wrong — two code defects (#2, #3 below) will make any clean-IP re-run silently reproduce the empty-TRAIN state.

---

## §1 — Prohibitions (unchanged)

- No candidate scoring, signal, factor, or bracket logic.
- No sealed-window path read. The 2023→present data *exists* and may be structurally certified; it is never scored or read for signal content.
- Copy-first discipline.
- Deterministic — byte-identical rebuild.

---

## §2 — Data Requirement

The substrate must satisfy `F1_DATA_REQUIREMENT_SIZING.md` (read it in full before implementing). Summary:

- **Target span: full 2012–2022 pre-sealed history** (~11 years, ~570 weekly formations), split 2012–2018 TRAIN / 2019–2022 HOLDOUT.
- This is NOT an N-count requirement — it is a **regime-coverage requirement**. HOLDOUT must contain the March 2020 momentum crash to bound MaxDD. A benign-trend window of any length is coverage-degenerate.
- **Before freezing, verify Channel 4 (universe availability):** the ≤10-name concentrated book requires ≥40–50 liquid single-stock futures at every formation date. If `build_fo_universe.py`'s liquidity floor yields fewer in early TRAIN years, the usable window shrinks.

---

## §3 — Corrections

### C0 — PRIMARY CORRECTION: Replace NSE archive-URL scraping with `nsepython` library

**The defect:** the current ingestion strategy (lines 152–218 of `ingest_futures_bhavcopy.py`) scrapes NSE archive URLs (`archives.nseindia.com` and `nsearchives.nseindia.com`) for daily bhavcopy zips. This approach:
- Requires dual-format parsing (legacy CSV shape ≠ UDiFF CSV shape) with a mid-2024 cutover.
- Is the root cause of the blocking/rate-limiting that produced 1,698 failed legacy fetches.
- Requires the `.404` marker cache system that conflates blocks with absences (Findings #2, #3).
- Has a proven multi-week failure track: three passes have not produced a TRAIN window.

**The replacement:** use `nsepython`'s `nse_history_fo()` function — NSE's direct historical F&O data API. The user has confirmed this API is available and working:

```python
from nsepython import nse_history_fo

payload = nse_history_fo(symbol="NIFTY", instrument_type="FUTIDX",
                         expiry_date="27-Aug-2026",
                         start_date="01-Jan-2026", end_date="01-Jul-2026")
# Returns list of dicts with keys: FH_TIMESTAMP, FH_SYMBOL, FH_EXPIRY_DT,
# FH_STRIKE_PRICE, FH_INSTRUMENT, FH_OPEN_PRICE, FH_HIGH_PRICE,
# FH_LOW_PRICE, FH_CLOSE_PRICE, FH_TRADED_QTY, FH_TOT_TRADED_VAL,
# FH_OPEN_INT
```

**Why this is the right approach:**
1. Single format across all eras — no legacy/UDiFF split, no format-boundary date to manage.
2. NSE direct API — designed for programmatic access, not scraping. Does not 503-block legitimate requests.
3. Returns structured data — no zip extraction, no latin-1 decoding, no column-name mapping across formats.
4. Eliminates the `.404` marker system entirely — fetch is stateless and repeatable.
5. `FH_TRADED_QTY` is number of contracts, `FH_TOT_TRADED_VAL` is in rupees — no `÷1e5` conversion ambiguity.

**Implementation plan for the new D1 (`ingest_futures_bhavcopy.py`):**

1. **Add `nsepython` as a dependency.** Verify it imports in this environment. If not present: `pip install nsepython`.
2. **Rewrite D1 to use `nse_history_fo()` as the sole fetcher.** Remove `fetch_fo()`, `legacy_url()`, `udiff_url()`, `_raw_paths()`, `_valid_fo_zip()`, the `RAW_DIR` cache, the `.404` marker system, `parse_legacy()`, `parse_udiff()`, `requests.Session`/`Retry` — all of it. The new ingestion is:
   - For each underlying → expiry pair in the date range, call `nse_history_fo()`.
   - Map the FH_* keys to the existing DuckDB schema columns.
   - Upsert into `futures_bhavcopy`.
3. **Source the (underlying, expiry) pairs from the instrument master** (`data/instruments/nse_fo_instruments.duckdb`). This table knows every contract that ever traded. Query distinct `(symbol, expiry)` pairs covering the target date range, then fetch each.
4. **Fetch with delay.** `nsepython` still needs polite pacing — sleep 0.5s between API calls.
5. **Handle API failures.** If `nse_history_fo()` raises or returns empty, log the date/underlying/expiry and continue — do not write any miss-marker.
6. **Retain the existing DuckDB schema** (columns, grain, upsert logic) — only the fetch layer changes.

**Output comparison with the old approach:**

| Signal | Old (archive scraping) | New (`nsepython`) |
|--------|----------------------|-------------------|
| Source format | Mixed legacy CSV + UDiFF CSV | Uniform structured JSON via API |
| Reliability | Blocked 1,698/1,699 legacy attempts | NSE direct API — designed for this |
| Failure mode | Silent (blocked → counted as absent) | Explicit (exception → logged, retried) |
| Code surface | ~200 lines (parsers, URLs, cache, markers) | ~80 lines (one API call per symbol×expiry) |

**Fallback for pre-2015 dates (if needed):** `nse_history_fo`'s available date range is an empirical question. If the API returns empty for pre-2015 dates, document the earliest available date per underlying in D6. Do NOT reintroduce archive scraping as a "seamless fallback" — a documented range boundary in D6 is better than a silent merge of two formats.

### C1 — (REMOVED by C0) — Blocked/transient vs. 404 distinction is eliminated

C0 replaces the archive-URL fetcher entirely. The `.404` marker system and its absent/blocked conflation are removed with the old code. No fix needed — the entire mechanism is deleted.

### C2 — (SIMPLIFIED by C0) — Purge `.404` markers after C0 rewrite

After C0 rewrites D1, the `bhavcopy_raw/` cache directory and its `.404` markers are dead artifacts from the old fetcher. Delete all `focal_*` and `foudiff_*` files from `bhavcopy_raw/` as part of the switch — the new `nsepython`-based fetcher does not use a file cache. (The equity bhavcopy pipeline uses this directory for equity data; do NOT delete `eq_*` or `bhav_*` files if any exist — only the FO-specific `focal_*` and `foudiff_*` globs.)

### C3 — Add gap-guard to the continuous builder (Review Finding #4)

**The defect:** `build_continuous_futures.py` (D2) currently produces consecutive rows even when the inter-row gap is enormous. The single 2022-08-08 island creates a ~22-month gap to the next row (2024-06-05 for RELIANCE), and the builder treats them as consecutive days — any return computation across that seam produces a silent fabricated return covering a 22-month period.

This auto-resolves once TRAIN/HOLDOUT data fills the gap, but the builder is gap-blind in general and the same defect will appear for any suspended / newly-illiquid / recently-listed name even with full data.

**The fix:** in D2, before computing the continuous series, inspect the per-underlying timeline for gaps. If the inter-row gap exceeds 10 calendar days, start a **new continuous segment** for that underlying:
- Reset `cum = 1.0` at the seam.
- Add a `segment_id` column to `stock_futures_continuous` so downstream consumers (D5 Arm F-A) know to skip cross-seam return checks.

### C4 — Extend the degeneracy floor with session density and window coverage (Review Finding #5)

**The defect:** `certify_futures_substrate.py` (D5) computes `span_days = (max − min).days` and stamps ADEQUATE on `span_days >= 200`. Current span is 1,074 days — but only because of the single 2022 island. Real contiguous coverage is 260 sessions. The floor passes on an artifact and says nothing about TRAIN being empty.

**The fix — add three checks before running certification arms:**

(a) **Session density:** `distinct_trade_dates / span_days >= 0.30`. Current: 260/1074 = 0.24 → FAIL.

(b) **Window coverage (mandatory fitness-for-purpose gate):**
```python
train_rows = COUNT(*) WHERE trade_date <= '2018-12-31'
holdout_rows = COUNT(*) WHERE trade_date > '2018-12-31' AND trade_date <= '2022-12-30'
sealed_rows = COUNT(*) WHERE trade_date > '2022-12-30'
```
If `train_rows == 0 OR holdout_rows < 2500` (50 dates × ~50 FUTSTK) → stamp **"INCOMPLETE — insufficient TRAIN/HOLDOUT coverage"**, do not run arms, do not stamp CERTIFIED.

(c) Keep the existing `span_days >= 200` as a tertiary check, nested inside (a).

**Gate schematic:**
```
density check → PASS? → window coverage check → PASS? → span_days check → PASS? → run arms → D6
                → FAIL any: stamp INCOMPLETE, skip arms, skip CERTIFIED
```

---

## §4 — Run it for real (acceptance-defining step)

Execute in order. Stop on any failure or unexpected result.

1. **Implement C0** — rewrite D1 to use `nsepython.nse_history_fo()`. Delete the old archive-URL fetcher code. Delete `focal_*` and `foudiff_*` cache files from `bhavcopy_raw/`.
2. **Implement C3** — add gap-guard to D2.
3. **Implement C4** — add density + window-coverage checks to D5.
4. **Wipe the DuckDB store:** delete `data/market_data/futures_bhavcopy.duckdb`.
5. **Run D1:**
   ```bash
   python scripts/sfb/ingest_futures_bhavcopy.py --start 2012-01-01 --end 2025-12-31
   ```
   (Range updated per `F1_DATA_REQUIREMENT_SIZING.md` — full 2012–2022 pre-sealed history is the target.)
6. **Verify TRAIN coverage BEFORE proceeding to D2:**
   ```sql
   SELECT COUNT(*), COUNT(DISTINCT trade_date), MIN(trade_date), MAX(trade_date)
   FROM futures_bhavcopy WHERE trade_date <= '2018-12-31'
   ```
   If TRAIN < 50,000 rows → **STOP**. Do not build continuous series. Report the actual coverage.
   Also verify HOLDOUT:
   ```sql
   SELECT COUNT(*), COUNT(DISTINCT trade_date), MIN(trade_date), MAX(trade_date)
   FROM futures_bhavcopy WHERE trade_date > '2018-12-31' AND trade_date <= '2022-12-30'
   ```
7. **Run D2** → `stock_futures_continuous`.
8. **Run D3** → `fo_eligible_intervals`. Verify Channel 4 (universe availability): at least ~40 eligible names per formation week in early TRAIN.
9. **Run D5** → D6, script-generated. Coverage checks (C4) must PASS. All five arms must return 0 violations.
10. **D6 must report:** raw row count, rows per window (TRAIN/HOLDOUT/SEALED), distinct trade dates, session density, earliest/latest date per underlying, roll rule counts per name (volume-trigger vs calendar fallback), liquidity floor default, and every arm's pass/violation count.

---

## §5 — Acceptance / stop rules

- Substrate is **certified** iff: D6 is script-generated from a real run, all five arms = 0 violations, degeneracy floor passes (density + window coverage + span), TRAIN > 50K rows, and HOLDOUT covers the March 2020 crash window.
- All of `tests/sfb/` green.
- Claude re-reviews the regenerated D6 and the passing test run.
- Only then does the F1 protocol freeze unlock.

---

## §6 — What Claude re-reviews

- That `nsepython` is the sole ingestion mechanism — no archive-URL code remains.
- That `bhavcopy_raw/` contains no `focal_*` or `foudiff_*` files.
- That D2's `stock_futures_continuous` has `segment_id` breaks at large gaps (≥10 days).
- That D5's degeneracy floor (C4) correctly flags insufficient TRAIN/HOLDOUT coverage.
- That D6 confirms TRAIN 2012–2018 populated, HOLDOUT 2019–2022 populated, and the March 2020 crash is in the HOLDOUT window.
- That D3's eligible-universe count in early TRAIN years meets the ≥40-name floor.
