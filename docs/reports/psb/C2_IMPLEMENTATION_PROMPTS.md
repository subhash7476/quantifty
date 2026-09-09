# C2 Roadmap — Implementation Prompts

Work orders for DeepSeek V4 under the standing role split: **DeepSeek implements from written prompts; Claude is Lead Reviewer only** (writes prompts, audits deliverables, issues PASS/NOT PASSED before the next phase). Governing plan: `docs/reports/C2_DEPLOYMENT_ROADMAP.md`. Append-only; prompts are issued one at a time and later prompts are HELD until the preceding review passes.

---

## Prompt 0.2 — MTO Delivery Backfill (ISSUED 2026-07-17)

### Context

PSB-2 closed with C2 (fortnightly delivery-% anomaly) recommended; its known weakness is a power projection resting on a 55-observation SD, because `deliv_pct` in `data/market_data/equity_bhavcopy.duckdb` is non-NULL only from 2020-01-01. The Phase 0.1 feasibility probe **PASSED** (`docs/reports/PSB2_MTO_PROBE_REVIEW.md`): NSE's MTO archive serves per-symbol delivery data for the entire 2010–2020 span; 2,717 files are already downloaded to `data/mto_probe/`; on the 2020 overlap MTO matches the store's SECFULL values **exactly** (deliv_qty 1,515/1,515 and 1,481/1,481 on the two reconciled dates); pre-2020 symbol joins are 100.0% on all sampled dates.

Your task: backfill `deliv_qty`/`deliv_pct` for pre-2020 EQ rows from those files, **on a copy of the store**, with a script-generated audit. The live store file is NOT swapped in this prompt — the swap is a separate step after Lead Review.

### Pinned facts (verified 2026-07-17 — do not re-derive differently; if your observations disagree, STOP and report)

- Store schema: `equity_bhavcopy(trade_date DATE, symbol VARCHAR, series VARCHAR, open/high/low/close/prev_close DOUBLE, volume BIGINT, turnover DOUBLE, deliv_qty BIGINT, deliv_pct DOUBLE)`. All pre-2020 `deliv_qty`/`deliv_pct` are NULL.
- Provenance: `ingest_meta(trade_date DATE, source VARCHAR)` — per-date, values `legacy` (2010-01-04→2022-08-08) and `secfull` (2020-01-01→2026-07-09). No per-row source column exists.
- MTO file format (stable across 2010–2020): comma-separated; data records are `20,<srno>,<SYMBOL>,<SERIES>,<qty_traded>,<deliv_qty>,<deliv_pct>` — **7 fields**. The human-readable column-header line lists only **6** columns (it omits the series column the data rows carry): **parse by record type and position, never by the header line.** The 2020-era `Trade Date <...>` line drops the Settlement No/Date fields — do not key on that line's field count.
- MTO carries series EQ, SM, GB, N*, etc. — **no BE rows**. SECFULL also provides no BE delivery (0 of 318,766 post-2020 BE rows non-NULL), so BE stays NULL. **EQ-only backfill.**
- MTO `qty_traded` equals store `volume` exactly where sampled (1,493/1,493 on 2019-01-02) — this becomes audit arm B below.
- 13 pre-2020 store trading days have no MTO file yet because the probe fetched weekdays only. All are weekend special sessions: 2010-02-06, 2010-05-16, 2012-01-07, 2012-03-03, 2012-04-28, 2012-09-08, 2012-11-11, 2013-05-11, 2013-11-03, 2014-03-22, 2015-02-28, 2016-10-30, 2019-10-27. (2020-02-01 and 2020-11-14 are also missing but SECFULL-covered — do not fetch, do not use.)

### Deliverables

1. **`scripts/csmp/parse_mto.py`** — MTO parser. `parse_mto_file(path) -> list of (symbol, series, qty_traded, deliv_qty, deliv_pct)`. Positional record-type-`20` parsing; malformed lines are **rejected and itemized** (returned separately), never guessed (the `ca_parse_rejects` discipline). Unit tests with synthetic fixtures covering: the 6-column-header trap, the 2020 `Trade Date` variant, malformed rows, non-EQ series pass-through.
2. **Weekend-session fetch** — extend or reuse the probe's primed-session fetch (`scripts/probe_historical_mto.py` `get_session()` pattern) to download exactly the 13 dates above into `data/mto_probe/`. Date list must be **derived from `trading_calendar` minus existing files**, not hardcoded — the hardcoded list above is for verification only. If any of the 13 is ABSENT at NSE, itemize it as a coverage exception; do not fail the run.
3. **`scripts/csmp/backfill_mto_delivery.py`** — copy-first backfill runner:
   - Copies `equity_bhavcopy.duckdb` → `equity_bhavcopy_mto_backfill.duckdb` (never opens the original for write).
   - For every `trading_calendar` date 2010-01-04→2019-12-31: parse the MTO file, `UPDATE` the copy's EQ rows joined on `(trade_date, symbol, series='EQ')`, filling **only NULL** `deliv_qty`/`deliv_pct` cells with the MTO values as published (no recomputation).
   - Adds a `deliv_source VARCHAR` column to `ingest_meta` in the copy: `'mto'` for backfilled dates, `'secfull'` for dates ≥ 2020-01-01 with source `secfull`, NULL otherwise. Price-source `source` column untouched.
   - Runs all audit arms (below), writes the audit report, prints the digest, exits non-zero if any hard-fail arm trips.
   - Deterministic: re-running against the same inputs regenerates the audit report **byte-identically**.
4. **Script-generated audit report** — `docs/reports/C2_PHASE0_2_MTO_BACKFILL_AUDIT.md`. Every number script-emitted; no hand-carried figures. The integrity digest is computed over the **entire report content including all verdict lines** (the PSB-2 MEDIUM-1 lesson: nothing sits outside the seal, no hardcoded PASS strings — every PASS/FAIL is computed).
5. **Four-arm re-certification** — run `scripts/psb1/certify_substrate.py` against the backfilled copy; its summary (all arms, pass/fail) is embedded in the audit report. The substrate certification is void until this is green.
6. **Tests** — parser unit tests plus backfill invariant tests (synthetic mini-store fixture: build a tiny DuckDB with known rows, run the backfill path, assert arms C/D/E behave). Follow the `tests/psb1/` conventions for location and style. Full existing suite must remain green.

### Audit arms (falsifiable predictions stated now, before the run)

| Arm | Check | Prediction | On violation |
|---|---|---|---|
| **A. Coverage** | Every `trading_calendar` date 2010-01-04→2019-12-31 parsed, or itemized | 0 exceptions after weekend fetch (≤13 if NSE lacks weekend files) | Itemize; hard-fail if a non-itemized weekday is missing |
| **B. Join integrity** | For every backfilled row: MTO `qty_traded` == store `volume` | ~100% exact (sampled 1,493/1,493) | Itemize; **hard-fail if >0.1% of rows on any date mismatch** — that signals a mis-keyed date/symbol, STOP and report, do not guess |
| **C. Immutability** | Full-table `EXCEPT` diff original-vs-copy over **all non-delivery columns**, all rows; row counts identical; rows with `trade_date ≥ 2020-01-01` bit-identical in every column | 0 differences | Hard-fail |
| **D. Plausibility** | `0 ≤ deliv_pct ≤ 100`; `deliv_qty ≤ volume`; `|deliv_pct − 100·deliv_qty/volume| ≤ 0.05` (MTO publishes 2dp) | ≈ 0 violations | Itemize; hard-fail if > 0.01% of backfilled rows |
| **E. No overwrites** | Backfill touched only cells that were NULL before | 0 non-NULL cells modified | Hard-fail |
| **F. Unmatched rows** | Store EQ rows on a date with no MTO row stay NULL, counted; MTO EQ rows with no store row counted (probe saw 25 on 2020-06-01 era) | ≈ 0 store-side unmatched pre-2020 | Itemize only |
| **G. Certification** | Four-arm contract suite green on the copy | Green (backfill adds no price changes, so continuity/CA arms should be unaffected) | Hard-fail |

### Prohibitions

- **No sealed-window analytics.** Rows with `trade_date ≥ 2023-01-01` may be touched only by arm C's equality assertion (counts of differences only — no values extracted, nothing scored).
- **No C2 scoring, no formation runs, no IC computation** — that is Phase 0.4, separately prompted after this review passes.
- **No modification** of the live `equity_bhavcopy.duckdb`, of `scripts/psb1/` or `scripts/psb2/` scoring code, or of any frozen protocol/report document.
- **No use of MTO 2020 files for the store** — SECFULL wins from 2020-01-01 (they were already used as the probe's reconciliation arm; that job is done).

### Acceptance criteria

1. Parser handles all 4 fixture classes; rejects are itemized, never guessed.
2. Weekend fetch is calendar-derived; the 13 dates resolve (fetched or itemized ABSENT).
3. Backfilled copy exists; live store byte-identical to its pre-run state.
4. Arms A–G all green (or itemized within their stated tolerances); every verdict computed, none hardcoded.
5. Audit report regenerates byte-identically on a second run; digest covers the full artifact.
6. `certify_substrate.py` green on the copy, summary embedded.
7. New tests green; full existing suite green (report the count).
8. Report lists: rows backfilled, distinct symbols, per-year fill rates, and the resulting non-NULL `deliv_pct` span (expected ≈ 2010-01-04 → present on the copy).

### Deliverable report

Reply with the audit report path plus a short cover note: what was built, any deviations from this prompt (each flagged NEEDS-DECISION, not silently resolved), test counts, and the digest. The Lead Review will re-derive arm results independently before any swap is authorized.

---

## Prompt 0.2-R2 — B1 Determinism Seal (ISSUED 2026-07-18, CLOSED 2026-07-18)

### Context

Lead Review (0.2-R) authorized the store swap on data-integrity grounds and re-verified five of six findings fixed (B2 M1 M2 L1 N1). B1 is **partially closed**: digest integrity is proven (recomputed SHA-256 = `45856cb1…558b07b`, timestamp/digest lines confirmed outside the seal), but **cross-run reproducibility** is not yet demonstrable. The Arm B `mismatch_detail` is sliced `[:20]` from an unordered SELECT (`backfill_mto_delivery.py:212-219`, no `ORDER BY`) that sits inside the sealed region — DuckDB's parallel hash join has no stable row order, so a re-run can reorder those 20 rows and move the digest despite the timestamp fix. The determinism test demanded by the original Prompt 0.2 fix-item-1 was not among the 4 delivered tests.

This is the **PSB-2 MEDIUM-1 discipline**: a terminal artifact's digest must be demonstrably reproducible on re-run. The exact class the B1 finding flagged in the first review.

### Fixes (bounded — no data change, no re-backfill)

1. **Add `ORDER BY m.trade_date, m.symbol`** to the Arm B mismatch query (`backfill_mto_delivery.py:212-219`). This is the sole source of nondeterminism in the sealed content region — `missing_dates` is already sorted. Audit the report generator for any other unordered list emitted into `content_lines` before the digest is computed; if you find any, order them and flag them.
2. **Add a determinism test** to `tests/csmp/test_mto_backfill.py`: build a synthetic mini-store, run the full `generate_report(arms, stats)` path twice on the same inputs, assert byte-identical report content **and** identical SHA-256 digest. The test must fail if the Arm B query or any other list changes ordering between runs.
3. **Re-run `backfill_mto_delivery.py` once** and confirm the digest reproduces exactly against the regenerated copy. The audit report's stated digest updates to the locked value — this is the reproducibility demonstration, not a data change.

### Prohibitions

- No store swap (already authorized separately; operator action).
- No data re-backfill — the copy's values are certified sound.
- No changes to score, formation, or IC code.
- No opening the 2023–2026 sealed window.

### Deliverable

Reply with: the locked digest, the determinism test passing, and the audit report path (updated digest). Short cover note confirming the Arm B query is now ordered and no other source of nondeterminism was found (or itemize any found and fixed).

**Closure:** All six findings independently verified fixed. Audit artifact sealed with reproducible digest (`4e038464…`). 11 backfill+parser tests green; 97 across csmp/psb1/psb2, no regressions. Prompt 0.2 passes in full.

---

## Prompt 0.3 — Store Swap (ISSUED 2026-07-18, HELD on operator execution)

### Context

The backfill `equity_bhavcopy_mto_backfill.duckdb` is certified sound (two independent re-derivations by Lead Review), the audit artifact is sealed with a reproducible digest, and all 97 tests are green. This prompt replaces the live production store with the backfilled copy. **Operator must execute or ratify — irreversible on production.**

### Deliverables

Write and run a swap script at `scripts/csmp/swap_mto_backfill.py`:

1. **Pre-swap backup:** rename the live `data/market_data/equity_bhavcopy.duckdb` → `data/market_data/equity_bhavcopy_preswap_20260718.duckdb` (timestamped, never deleted).
2. **Swap:** move `data/market_data/equity_bhavcopy_mto_backfill.duckdb` → `data/market_data/equity_bhavcopy.duckdb`.
3. **Post-swap verification (REFUSE + ROLLBACK if any check fails):**
   - Row count == `7,030,920` (SELECT COUNT(*) FROM equity_bhavcopy)
   - Non-NULL `deliv_pct` span == `2010-01-04` → `2026-07-09` (MIN/MAX on deliv_pct)
   - `certify_substrate.py` green on the now-live store (all 4 arms pass)
   - **If any check fails:** move the backup back into place, delete the failed swap file, and report the failure. Do not leave a broken live store.

### Prohibitions

- No deleting the backup — keep it.
- No touching scoring, formation, or IC code.
- No opening the 2023–2026 sealed window.

### Deliverable reply

Swap script path, post-swap verification status (row count, deliv span, certification arms), and confirmation the live store is now `equity_bhavcopy.duckdb` with pre-2020 delivery data.

---

## Prompt 0.4 — C2 SD Re-Estimation on Extended Dev Window (HELD — gated on successful Prompt 0.3 swap)

### Pre-flight

**STOP if `equity_bhavcopy.duckdb` still lacks pre-2020 delivery data** — the swap (Prompt 0.3) must be complete and verified before this run.

### Context

PSB-2 closed with C2 (fortnightly delivery-% anomaly) recommended; its known weakness is a power projection resting on a 55-observation, 2.3-year SD estimate because `deliv_pct` was non-NULL only from 2020-01-01. With the MTO backfill now certified and the store swapped, the dev window extends from 2010-01-04 to 2022-12-30, yielding ~230+ fortnightly formations — roughly 4× the PSB-2 sample.

This prompt runs C2 formation on the **extended dev window** against a pre-registered tolerance gate (G0). It does not promote C2, does not touch scoring code, and does not open the sealed window. It produces a re-estimated IC and SD for the successor pre-registration to pin its view on.

### Pinned facts

- Store: `data/market_data/equity_bhavcopy.duckdb` (swapped — operator action complete before you run).
- Dev window: 2010-01-04 → 2022-12-30 (fence proven: `MAX(trade_date)` used ≤ `'2022-12-30'`).
- PSB-2 C2 estimates (the baseline you are re-estimating against): **Mean IC = +0.0349, SD_IC = 0.099396, Net spread = +4.57%, Power δ = 0.9198** (55 formations, fortnightly, banded 0.40 exit).
- C2 formation: exactly as frozen in `scripts/psb2/harness.py` — fortnightly, `deliv_pct` ranked within NIFTY-200 point-in-time universe, long-only, banded exit at 0.40. No parameter changes.
- `deliv_pct` baseline: 252-day rolling window (same as PSB-2).
- 2023–2026 window: **sealed and unread** — your code must fence at `≤ '2022-12-30'` and assert the fence holds (computed MAX != actual MAX of the store's post-2022 data must differ).

### Gate G0 — tolerance pinned before the run

| Criterion | Baseline (PSB-2, n=55) | Tolerance | Gate passes if |
|---|---|---|---|
| Mean IC | +0.0349 | Absolute change ≤ 1.5 × baseline SE | `abs(μ_new − μ_old) ≤ 1.5 × (0.099396 / sqrt(55))` = ≤ 0.0201 |
| SD_IC | 0.099396 | Within [baseline × 0.5, baseline × 2.0] | SD ∈ [0.0497, 0.1988] |
| Net spread | +4.57% | Must stay positive | Net spread > 0 |
| AC₁ | −0.1818 (from PSB-2) | Must stay negative (no positive autocorrelation threat) | AC₁ < 0 |

G0 is a **consistency gate**, not a victory gate. It tests whether the extended-window estimates are consistent with the PSB-2 baseline that C2 was recommended on. A gate failure does not invalidate C2 — it means the larger sample reveals something the smaller sample didn't, and that must be disclosed to the successor.

### Deliverables

1. **Re-run C2 formation** against the swapped store, dev window 2010-01-04 → 2022-12-30, using the frozen `scripts/psb2/harness.py` C2 scoring path. Compute:
   - Number of fortnightly formations (n)
   - Mean IC, SD_IC, AC₁ (Newey–West as in PSB-2)
   - Net quintile spread (Q1–Q5, fee-adjusted per PSB-2 fee model)
   - Power projection against the PSB-2 n* formula (n* = 84 fortnightly formations in a ~3.2-year live window)
2. **Evaluate G0** against the pinned tolerances above — pass/fail each criterion, flag any that fail.
3. **Assert the 2023–2026 fence**: computed `MAX(trade_date)` in your formation window must be `'2022-12-30'` and must differ from the store's actual `MAX(trade_date) > '2022-12-30'`.
4. **Emit a script-generated report** — `docs/reports/C2_PHASE0_4_SD_REESTIMATION.md`.

### Prohibitions

- No parameter changes to C2 scoring.
- No reading the 2023–2026 sealed window — fence assertion only (counts of rows used, no values extracted from sealed rows).
- No touching `scripts/psb2/harness.py` scoring logic, only the dev-window bounds in the runner.
- No promoting C2 — this is a pre-registration input, not a promotion.

### Deliverable report

Reply with the report path plus a short cover note: n, μ_IC, SD_IC, AC₁, net spread, power, which G0 criteria passed/failed, and the fence assertion result.
