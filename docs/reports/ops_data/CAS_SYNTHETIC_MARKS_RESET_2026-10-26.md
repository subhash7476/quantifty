# CAS `is_synthetic` marks missing from 2026-09-04: root cause

**Found:** 2026-10-26, while diagnosing the 10-23 DownloadAll failure (`DOWNLOAD_ALL_FAILURE_2026-10-23.md`).
**Status:** cause confirmed read-only. Fix implemented on `fix/cas-nightly-synthetic-marks` after operator OK (2026-10-26: "go, fail loud, snapshots are fine"). Live 1m files have not been mutated by this investigation; the one-off remediation below is still to run.

## Symptom

Every post-CAS file in `data/market_data/nse/candles/1m/` from **2026-09-04 → 2026-10-22** has **0** rows with `is_synthetic = TRUE`. Sessions 2026-08-03 → 09-03 carry 2,700–2,930 marked bars each. 10-23 has 2,769 marks, because the PR #53 remediation re-ran the marker on it at 15:58 today.

The bars themselves are still there. The same probe counts 2,940–2,983 flat, zero-volume `NSE_EQ` bars in 15:15–15:29 on every unmarked session, the same population as the marked ones. Only the flag is lost.

## Cause

The nightly 1m step wipes the flag on every session it re-fetches, and nothing in the nightly path puts it back.

1. **`download_all_data.py` step 6** calls `fetch_upstox_historical.py` over `[latest 1m file − 7 days, today]`.
2. **The fetcher upserts** with `ON CONFLICT … DO UPDATE SET … is_synthetic = FALSE` (`scripts/fetch_upstox_historical.py:264-270`). Every re-fetched session loses its marks.
3. **Nothing in `download_all_data.py` runs `scripts/cas/mark_synthetic_bars.py`.** The marker only ran by hand, or from `backfill_fo_1m.py` / `backfill_n100_1m.py`, which mark the files they touch.
4. **`data/cas/cas_category.duckdb` was stale.** Until today it ended `effective_to = 2026-09-11`, so the marker could not have run past that date anyway. `run()` raises on an empty list. It was rebuilt to 2026-10-23 at 15:58 today (baseline `data/_baselines/cas_category_pre_rebuild_2026-10-26/`).

## Evidence that the boundary is the lookback

| Sessions | `is_synthetic` | `.pre_cas_mark` snapshot | File mtime | Reading |
|---|---|---|---|---|
| 08-03 → 09-03 | ~2.7–2.9k | yes (09-11) | 09-11 / 09-13 | Marked by hand on 09-11 and 09-13. Since then they have been outside every nightly window. |
| **09-04 → 09-11** | **0** | **yes (09-11)** | **09-15 09:23** | Marked once on 09-13 (the "10 sessions, 28,660 bars" pass in CLAUDE.md), then **reset** by the 09-15 09:10 morning catch-up. |
| 09-15 → 10-22 | 0 | no | each session's own 22:0x run, or a later one | Never marked. `cas_category` ended 09-11, and no step in the pipeline runs the marker. |
| 10-23 | 2,769 | no (backfill baseline in `data/_baselines/`) | 10-26 15:58 | Re-marked by the `backfill_fo_1m.py --apply` run for PR #53. |

- **The window start matches the break exactly.** At the 09-15 09:23 run, the store head was 09-11. 09-11 − 7 days = **09-04**, the first unmarked session. 09-03 sits just outside that window and kept its marks.
- **Both scheduled entry points reset marks.** The morning `--download-only` catch-up runs the same step 6 as the 22:00 DownloadAll, as the 09-15 09:23, 09-16 08:08 and 09-18 12:18 mtimes show. A marker placed in `build_derived()` would miss the morning path.
- **This recurs every night, not once.** Each run re-upserts the trailing ~7 calendar days, about 5 sessions. **Tonight's 22:00 run will reset 10-23 again** unless the fix is on `main` in `F:\Nifty` first.

## Side checks

- **The rename did not drop ICICILIFE / ICICIPRULI.** `cat1_isin_symbols()` maps `cas_category` tickers to ISINs through the Upstox master (`nse_fo_instruments.duckdb`). Today's snapshot maps both `ICICIPRULI` and `ICICILIFE` to `INE726G01019`, so the rename costs no marks. On 08-03, 09-04, 10-22 and 10-23, 208–213 Cat-I tickers resolve and **0 are unmapped**.
- **A latent silent drop remains.** `cat1_isin_symbols()` drops any Cat-I ticker that is absent from the current master snapshot. A future rename or delisting could under-mark a session without any error. The fix adds a guard.
- **Who reads the flag.** TS Basis Daily is unaffected, because its continuous close filters `volume > 0`. The flag is read by `core/analytics/day_features.py`, `scripts/analog_path/`, `scripts/isd/` (census C3, contiguity gate) and by the PTMS certificate obligations ("filter `is_synthetic = FALSE`"). Any of these that read 09-04 → present saw carry-forward bars as real.

## Fix (operator-approved 2026-10-26)

Add a step 6b to `download_data()` that runs straight after the 1m fetch. It skips only on `--skip-1m`. It also runs when the fetch returned non-zero or timed out, because a partial upsert has still reset the rows it wrote.

1. **Rebuild `cas_category`** (`build_cas_category.build()`). The rebuild runs after step 2, so it sees the futures data that step just fetched. Then **assert it is fresh**: `max(effective_to)` must equal the latest FUTSTK `trade_date`.
2. **Mark** with `mark_synthetic_bars.run(apply=True, since=<the fetch's own start date>)`. `_download_1m_candles` returns the start date it computed (`max − lookback`, or `max − 30` on `--full`), so the marker covers exactly the fetched window. Copy-first: `run()` already snapshots `<file>.pre_cas_mark` and never overwrites an existing one.
3. **Assert the absolute post-condition.** After marking, every post-CAS file in the window must have `count(*) WHERE is_synthetic > 0`. `mark_file()`'s return value cannot serve, because it is a delta: it is 0 both for an already-marked file and for an empty list.
4. **Guard against unmapped tickers.** `cat1_isin_symbols()` fails when a Cat-I ticker has no ISIN in the master, instead of silently dropping it.

As built: steps 1–2 are `_mark_cas_synthetic()` / `_1m_start()` in `scripts/download_all_data.py`. Checks 3–4 are inside `mark_synthetic_bars.run()` / `cat1_isin_symbols()`, so the one-off command below gets them too. The freshness assertion was dropped as tautological: a rebuild from the same futures store always ends on its max date. The real staleness case, a 1m session newer than the futures data, is already refused by `run()`'s empty-list check.

A failed step 6b sets `all_ok = False`. The run then exits 1, and `run_if_session.py` sends a Telegram alert. The next night re-fetches the same window and re-marks it, so the step heals itself.

Tests will point `NATIVE_1M_DIR`, `CATEGORY_DB`, `MASTER_DB`, `FUTURES_DB` and `OUT_DB` at `tmp_path` before the first RED run (CLAUDE.md pitfall: a RED refresh test once rewrote the live facts store).

### Operator decisions (2026-10-26)

1. **Today's futures not yet published at run time → fail loud.** Today's Cat-I list is then empty, step 6b fails, the run exits 1 and Telegram-alerts, and the next night's run re-fetches and re-marks that session. Only the 22:00 run can hit this, because the 09:10 catch-up never persists today.
2. **Snapshot growth accepted.** One `.pre_cas_mark` copy of about 9 MB per new session in the live 1m dir, roughly 2.2 GB a year (48 GB free on F:; existing snapshots total 287 MB).

### Dry run

The marker was run on scratch copies of the live 09-04, 09-15, 10-01 and 10-22 files, using the live `cas_category` and master read-only. It marked 2,753 / 2,926 / 2,968 / 2,779 bars, and the unmapped-ticker guard passed on every post-CAS session 08-03 → 10-23.

## One-off remediation (after the fix is on `main` in `F:\Nifty`, run after 15:50)

```bash
python scripts/cas/mark_synthetic_bars.py --apply --since 2026-09-04
```

- The existing 09-04 → 09-11 snapshots are kept. About 30 new snapshots are written for 09-15 → 10-22 (~270 MB).
- Re-marking 10-23 is a no-op.
- **Verify:** each session's synthetic count should land at 2,700–2,980, within the flat zero-volume auction-window count above.
- If the remediation runs before the fix reaches `main`, the next nightly run resets the trailing 5 sessions. Re-run the command after the first fixed night.
