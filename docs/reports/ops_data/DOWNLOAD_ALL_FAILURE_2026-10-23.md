# DownloadAll failure — 2026-10-23 (Friday)

**Investigated:** 2026-10-26 · **Status:** RESOLVED 2026-10-26. Option A merged (PR #53, `5247806`) and the catch-up run after the 15:50 stop.

**Resolution log (2026-10-26, after 15:50):**
1. Merged PR #53 (`fo_equity_keys()` falls back to the Upstox master) and pulled `F:\Nifty` to `5247806`.
2. `backfill_fo_1m.py --apply` first refused, correctly: "no Category I symbols for 2026-10-23". `cas_category` ended 2026-09-11. Rebuilt it per the standing CLAUDE.md obligation. The rebuild went to scratch first and the diff was additive only: 366 → 370 intervals, 210 ends extended, 4 new starts (ANANDRATHI, ENRIN, UJJIVANSFB from 09-30; ICICILIFE from 10-23), 0 removed or shrunk. Baseline: `data/_baselines/cas_category_pre_rebuild_2026-10-26/`.
3. Backfill re-run: 375 ICICILIFE bars written for 10-23. The CAS marker flagged 2,769 carry-forward bars on that file, coverage shows 0 gaps, rc 0.
4. `refresh_all_strategies.py` rc 0. TS Basis Daily 10-23 formation built (212 post-CAS cells priced). Facts now run to 2026-10-23 with 211 names; ICICILIFE is gated out by MIN_OBS as expected.

10-26 ICICILIFE bars arrive with tonight's 22:00 run, now that the mapping is fixed. Open follow-up: 1m `is_synthetic` marks are missing on every file 2026-09-04 → 10-22. Only 10-23 is re-marked.

## What failed

`data/ops/scheduled_runs.log`: `2026-10-23T22:05:11 END download 2026-10-23 exit 1`.

Every download step and both builds succeeded: equity, futures, index, VIX, corp-actions, stock-options, 1m, SPAN, nifty50, and continuous. Only **STEP 3 `refresh_all_strategies.py`** exited 1.

| Store | Max formation | Last write |
|---|---|---|
| source `futures_bhavcopy` | 2026-10-23 | — |
| carry weekly + facts | 2026-10-23 | 10-23 22:05:04 ✅ |
| ts_basis | 2026-10-09 (forward-return lag, normal) | no-op, exit 0 |
| **ts_basis_daily** | **2026-10-22** | **build failed — 10-23 formation missing** |

## Root cause — a symbol rename: ICICIPRULI → ICICILIFE (effective 2026-10-23)

- `futures_bhavcopy` and `equity_bhavcopy` show the name as `ICICILIFE` from 10-23. `ICICIPRULI` ends on 10-22. ISIN `INE726G01019` is unchanged.
- `equity_bhavcopy.duckdb::instrument_master` comes from NSE `EQUITY_L` and is refreshed **only** by `scripts/csmp/build_universe.py`, which does not run nightly. It still has `ICICIPRULI`.
- `fo_equity_keys()` (`scripts/cas/fo_1m_coverage.py`) maps FUTSTK names to 1m keys through `instrument_master`, so it has no key for ICICILIFE. The nightly 1m step logged `1 FUTSTK names have no EQ ISIN in instrument_master and are not fetched: ['ICICILIFE']`. The 10-23 1m file has **no bars at all** for `NSE_EQ|INE726G01019`.
- `build_ts_basis_daily.py --incremental` hard-fails on a post-CAS F&O cell with no continuous-session close, as designed.

**Reproduced against scratch copies (no live store touched):**

```
DAILY FAIL: RuntimeError 1 post-CAS cells have no continuous-session 1m close ... 2026-10-23: ICICILIFE
TS rc 0
```

`backfill_fo_1m.py` (plan mode) reports "0 absent cells" because it silently skips unmapped names. It lists ICICILIFE only under "cannot fetch".

**Tonight's 22:00 run will fail the same way.** ICICILIFE also traded on 10-26.

## Why the log showed no traceback

`scripts/ops/run_if_session.py` tees output by swapping `sys.stdout`/`sys.stderr` inside its own Python process. Grandchild subprocesses (every step `download_all_data` launches) write to the inherited OS handles and bypass the tee. Their output, the RuntimeError included, never reaches `data/ops/logs/download_<date>.log`. Follow-up: tee at the fd level, or pipe child output.

## Knock-on effects

1. **TS Basis Daily / combo paper book.** No 10-23 formation was built, so today's `ts_combo` had nothing new (`last_formation: 2026-10-22`). The book holds **ICICIPRULI SHORT ₹185k** (formation 10-22). When 10-23 is processed, `book_returns` counts it as unpriced (0 P&L, `n_unpriced_fut=1`). The hook then CLOSEs it because the symbol has left the facts. That close is caused by the rename, not by the signal.
2. **Entity continuity.** Every symbol-keyed store treats ICICILIFE as a new name. It has no z-history and is gated out by `MIN_OBS=12` for about 12 sessions, and ICICIPRULI's history is orphaned (CLAUDE.md pitfall: an entity is not one symbol for all time).
3. **STOCK-STRADDLE-M10 cycle 1 (expiry 10-27, T-1 exit capture today 15:15): safe.** The 10-12 entry captured 37 ICICIPRULI contract keys, and all 37 are still live under ICICILIFE in today's Upstox master. `exit_prices()` joins on `instrument_key`, so the exit quotes match.
4. The Upstox instrument master (`nse_fo_instruments.duckdb`) already maps `ICICILIFE → INE726G01019` in the 2026-10-26 snapshot. The 10-23 snapshot did not.

## Fix options (operator decision)

- **A. Durable (recommended):** `fo_equity_keys()` falls back to the latest Upstox master snapshot (`tradingsymbol`, `instrument_type='EQ'`) when `instrument_master` has no row. This is code-only, needs a test and a PR, and touches no substrate.
- **B. Refresh `instrument_master` from EQUITY_L.** The only committed path is a full `build_universe.py` run, which also rewrites the certified universe and `symbol_entity_intervals` tables. Substrate mutation, baseline first. NSE's EQUITY_L may also still lag the rename.

After either fix, run `scripts/cas/backfill_fo_1m.py --apply` after 15:50. It fetches 10-23 (+10-26) for ICICILIFE and runs the CAS synthetic marker. Then run `refresh_all_strategies.py`. Running it while the orchestrator is live risks a facts `os.replace` under the `ts_combo` reader.
