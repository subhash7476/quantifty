# NiftyShield — stale India VIX history cache (2026-10-09)

**Status:** Root cause found. Measured. Fix built on `fix/vix-history-refresh` but **not merged**.
Merging it changes what NiftyShield trades during the E008 window, so it needs the operator's
OK and a ledger note first (§6).

## 1. Summary

- `data/nifty_shield/vix_history.duckdb` ends at **2026-09-07** (3,040 rows from 2014-05-14).
- The 1d index store is **not** the cause. Every session file from 2026-09-08 to 2026-10-08
  carries `NSE_INDEX|India VIX`. The 21 missing sessions are all there; 09-14 and 10-02 are
  NSE holidays. The cache simply never reads them.
- The live 13:00 fact therefore ranks today's VIX against a 756-session window that **ends on
  2026-09-07**. The frozen config declares that window as the *trailing* 756 sessions
  (`strategies/nifty_shield_v1/config.py`: `vix_pctile_lookback_sessions = 756`).
- **Effect so far is small.** Across all 21 live sessions since 09-08, the most any stored
  `vix_pctile` moves is **0.53 pp**, and **no session crosses the 36.8 or 59.0 gate**. Every
  traded structure would have been the same.
- **The effect grows with staleness.** At 1 month stale, 2.5% of Choppy decisions flip
  structure. At 6 months it is 16% (§4). Two recent Choppy sessions sat within 1 pp of a gate.

## 2. Root cause: two layers

1. **Nothing ever called `refresh()`.**
   - The `vix_percentile.py` docstring says the EOD chain runs it.
   - `core/scheduler/eod_chain.py` `CHAIN_STEPS` never included it.
   - The cache file was last written 2026-09-08 23:38 (mtime), the day the percentile gates were
     re-anchored. No scheduled caller of `refresh()` exists anywhere in the repo.
2. **The EOD chain itself is off.**
   - `data/_eod_automation.sqlite` has `enabled = 0` since 2026-09-11T18:40.
   - The last chain run was 2026-09-16.
   - The only caller of `run_chain` is `scripts/schedule_worker.py`. It fires at ≥ 20:00, but it
     runs as an orchestrator child, and the orchestrator now stops itself at 15:50.
   - So a step added to `CHAIN_STEPS` would never run. **The task's suggested fix would have
     been inert.**

The nightly path that *does* run is `\Nifty\DownloadAll` at 22:00, which calls
`scripts/download_all_data.py` and has exited 0 every session in `data/ops/scheduled_runs.log`.
The same `download_data()` also runs as the orchestrator's `--download-only` morning catch-up.
SPAN archiving was lost the same way and fixed in the same place (`tests/ops/test_download_span_step.py`).

## 3. Measurement

**Method**
- Copied the live fact store `data/nifty_shield/facts.duckdb` and the cache to a scratchpad.
  Production files were not touched.
- Appended the 21 sessions from the 1d store to the copy.
- Recomputed `percentile(vix_at_checkpoint, session)` against the stale copy and the fresh copy.

**Checks that the method is sound**
- The stale recompute reproduces every stored `vix_pctile` exactly. The live path really did
  use this cache.
- The last 20 cached closes match the 1d store exactly.
- Running the real `refresh()` on a copy of the stale cache adds the same 21 rows. The result
  is byte-for-byte identical to the targeted top-up.

**Which store is live.** The live fact store is `data/nifty_shield/facts.duckdb`, written by the
session's driver hook. `data/features/day_type/day_type_facts.duckdb` is the research/backfill
store and was last written 2026-09-10. Do not read it as the live record.

| Session | Regime | VIX @13:00 | Stored pctile | Fresh pctile | Δ pp | Structure (stored → fresh) |
|---|---|--:|--:|--:|--:|---|
| 09-08 | BearTrend | 11.18 | — ¹ | 13.23 | — | bear_call_spread |
| 09-09 | BullTrend | 11.59 | 20.11 | 20.24 | +0.13 | bull_put_spread |
| 09-11 | BullTrend | 12.30 | 33.20 | 33.20 | 0.00 | bull_put_spread |
| 09-15 | BearTrend | 12.81 | 39.95 | 39.95 | 0.00 | bear_call_spread |
| **09-16** | **Choppy** | 13.12 | 43.65 | 43.52 | −0.13 | iron_fly → iron_fly |
| 09-17 | BullTrend | 12.34 | 33.60 | 33.47 | −0.13 | bull_put_spread |
| **09-18** | **Choppy** | 11.55 | 19.97 | 20.11 | +0.14 | short_straddle → short_straddle |
| 09-21 | BullTrend | 11.41 | 18.65 | 18.92 | +0.27 | bull_put_spread |
| 09-22 | BearTrend | 11.17 | 13.23 | 13.23 | 0.00 | bear_call_spread |
| 09-23 | BullTrend | 10.43 | 4.89 | 4.89 | 0.00 | bull_put_spread |
| 09-24 | BearTrend | 11.70 | 22.22 | 22.49 | +0.27 | bear_call_spread |
| **09-25** | **Choppy** | 12.69 | 37.96 | 37.57 | −0.39 | iron_fly → iron_fly (**0.77 pp** above 36.8) |
| 09-28 | BearTrend | 13.78 | 55.82 | 55.82 | 0.00 | bear_call_spread |
| **09-29** | **Choppy** | 14.03 | 59.92 | 59.92 | 0.00 | short_strangle → short_strangle (**0.92 pp** above 59.0) |
| 09-30 | BullTrend | 12.95 | 41.40 | 40.87 | −0.53 | bull_put_spread |
| 10-01 | BearTrend | 15.29 | 75.26 | 75.26 | 0.00 | bear_call_spread |
| 10-05 | BearTrend | 15.22 | 74.47 | 74.47 | 0.00 | bear_call_spread |
| 10-06 | BullTrend | 13.89 | 58.07 | 57.80 | −0.27 | bull_put_spread |
| **10-07** | **Choppy** | 13.86 | 57.54 | 57.28 | −0.26 | iron_fly → iron_fly |
| 10-08 ² | BearTrend | 15.09 | 73.81 | 73.81 | 0.00 | bear_call_spread |
| 10-09 ³ | BullTrend | 14.61 | 69.05 | 68.78 | −0.27 | bull_put_spread |

¹ The `vix_pctile` column was added after this session's fact was written.
² 10-08 is the first E008 window session (`WINDOW_START`). It was a trend day, so the
percentile did not enter its structure choice.
³ Added after the 13:00 publish on 2026-10-09, the second window session. A trend day, so
the structure was unaffected. The ledger note was declared with this row.

**No threshold crossings.** This holds even if every session is treated as Choppy: no stored vs
fresh pair falls on opposite sides of 36.8 or 59.0.

**Why the effect is small so far.** A 21-session lag swaps at most 21 of 756 window members.
That caps the shift at 21/756 = **2.8 pp**. The realised shift was smaller because the 21 dropped
2023 sessions sat at VIX levels similar to the 21 missing ones.

## 4. How the error grows if left alone

This is a simulation on the fresh cache over the last 750 sessions. Each session's own close
is ranked against a window frozen *k* sessions earlier, compared with the true trailing window.

| Sessions stale | mean \|Δ\| pp | p95 \|Δ\| pp | max \|Δ\| pp | Choppy structure flips |
|--:|--:|--:|--:|--:|
| 21 (≈ 1 month) | 1.22 | 2.78 | 2.78 | 2.5% |
| 42 | 2.38 | 5.29 | 5.56 | 4.4% |
| 63 (≈ 3 months) | 3.47 | 7.94 | 8.33 | 7.3% |
| 126 (≈ 6 months) | 5.88 | 16.01 | 16.67 | 16.0% |
| 252 (≈ 1 year) | 11.73 | 27.65 | 33.33 | 29.2% |

Today's 13:00 fact (2026-10-09) is computed on a window 22 sessions stale. Doing nothing is a
decision too, and its error grows linearly.

## 5. The fix (branch `fix/vix-history-refresh`, worktree `F:\Nifty_vixfix`)

**Changes**
- `scripts/download_all_data.py` `download_data()` gains **step 3b**:
  `_run(scripts/daytype/vix_percentile.py, label="vix-history")`.
  - It runs right after the 1d index ingest, so it reads the file that run just wrote.
  - It sits in `download_data()`, not `build_derived()`, so the 09:10 `--download-only` catch-up
    also tops the cache up before 13:00.
  - It runs as a subprocess through `_run`, never as an inline `refresh()` call. That way a test
    that stubs `_run` cannot write the production cache.
  - A failed refresh fails the download's exit code, the same way SPAN does.
- `scripts/daytype/vix_percentile.py`: the docstrings now name the real caller.
- `tests/ops/test_download_vix_history_step.py` covers three things:
  - the step runs exactly once, after `index-history`;
  - it is the right script;
  - a failed refresh makes `download_data()` return False.
  - Both tests failed before the change and pass after it. `tests/ops/test_download_*`,
    `tests/scheduler` and `tests/daytype` give 92 passed and 8 skipped.

**Deliberately not done**
- **Not added to `CHAIN_STEPS`.** If the EOD worker is ever re-enabled, it calls
  `download_all_data.py` first (`eod_job.run_download`), so this step runs there anyway. A chain
  step would be redundant.

**Cost.** A full `refresh()` takes about 25–30 s whether or not it adds rows. Every run reopens the
roughly 1,100 1d files that carry no VIX row, from 2012 to mid-2014. That is acceptable at 22:00
and in the morning catch-up. Recording the probed-empty dates would remove the cost, but it is
not needed for correctness.

**Timing and lock contention**
- The morning catch-up is dispatched in the background and never gates the session
  (`orchestrator.py` step 6). It has finished by about 09:20–09:47 on recent days, well before
  13:00, so a refresh failure cannot block trading.
- `refresh()` holds the cache open read-write for its whole ~25 s scan. After a mid-day restart,
  the catch-up can overlap 13:00: on 2026-10-07 the orchestrator restarted at 13:00:15 and the
  catch-up was dispatched at 13:01. In that case the publisher's read-only open can raise.
- The driver retries the publish hook on every bar through the 30-minute entry window
  (`CHECKPOINT_DEADLINE`). So an overlap delays the fact by a bar or so; it does not lose the
  session.
- Shrinking the write lock to the insert alone (read `have` read-only, scan, then write) would
  remove the overlap entirely. That is optional and not in this branch.

**After the fix, the cache is point-in-time correct.** `percentile()` filters
`session_date < asof`, so once the cache is complete every session sees exactly the trailing
756 sessions before it. Only sessions recorded during the stale period are affected.

**Replay of stale-window sessions will not reproduce `vix_pctile`.**
- A session package (`marks`, `signals`, `bars`, `facts`, `meta`) records no VIX history.
- `replay.py` re-publishes the 13:00 fact through `publish_live`, which ranks against the
  default *production* cache, and the strategy then trades off that recomputed value.
- After the top-up, replaying any session recorded on the stale window (10-08, 10-09, … up to
  the merge) recomputes `vix_pctile` on the fresh window.
  - 10-08 recomputes identically (Δ 0.00, and it was a trend day).
  - A Choppy session within ~2.9 pp of a gate could replay to a different structure and report
    signal-stream FAIL.
- Replay parity is **reported, not gating**:
  - `assemble_report.load_window_evidence` counts a session on recorded + telemetry-clean +
    ≥1 closed structure + window start + identity.
  - The replay rows only feed the report's evidence line.
  - `_read_fact_row` does not select `vix_pctile`, so the fact-identity diff will not flag it.
- Replay was never hermetic in VIX history: it uses whatever cache exists at replay time.
  Recording the session's `vix_pctile` (or its window) in the package would close that, as a
  separate change.

**Execution hash is unaffected.** `scripts/nifty_shield_paper/identity.py` `EXECUTION_GLOBS` covers:
- `strategies/nifty_shield_v1/*.py`
- `core/execution/options/nifty_shield_*.py`
- `fees.py`, `handler.py`, `watchdog.py`
- the paper runner

Neither `scripts/download_all_data.py` nor `scripts/daytype/*` is hashed, so
`FROZEN_EXECUTION_HASH b33f5c3f…78fa` and `WINDOW_START 2026-10-08` do not move. That is exactly
why this needs a ledger note rather than relying on the hash gate: the fix changes structure
selection in live sessions, and nothing in the identity check would detect it.

## 6. Operator decision required

**What the operator is approving**
- (a) Merging the branch.
- (b) A one-time top-up of the production cache: +21 sessions now, +22 after today. It happens
  automatically on the first 22:00 `DownloadAll` after the merge. To do it by hand, run
  `python scripts/daytype/vix_percentile.py` from `F:\Nifty` **after 15:50 only**.
  - `refresh()` writes the cache.
  - The 13:00 publisher opens that file read-only.
  - On Windows a concurrent writer makes that open raise, and `percentile()` does not catch it.

**Draft ledger note** (for the E008 block in `docs/STRATEGY_PROMOTION_LEDGER.md`, added before
the first session that uses the refreshed cache; not edited on main by this branch):

> - **VIX-history refresh restored — declared 2026-10-__ (before the session of 2026-10-__)** — a
>   note, not a grant. NiftyShield's Choppy structure gate ranks the 13:00 India VIX against the
>   trailing `vix_pctile_lookback_sessions = 756` sessions (frozen config) in
>   `data/nifty_shield/vix_history.duckdb`. That cache had no refresher: it froze at 2026-09-07,
>   so every live `vix_pctile` from 09-08 on was ranked against a window ending 09-07. The fix
>   adds `vix_percentile.py` to `download_all_data.py` (step 3b), restoring the declared trailing
>   window; it is a return to declared behaviour, not a parameter change. Measured on all 21 live
>   sessions 09-08 → 10-08: max |Δ vix_pctile| 0.53 pp, **zero** structure changes; the window
>   sessions banked so far (10-08 [, 10-09 …]) were ranked on the stale window, max lag 2.9 pp,
>   and stay in the window. Execution hash `b33f5c3f…78fa` and `WINDOW_START 2026-10-08`
>   unchanged; no execution-glob file touched. Report:
>   `docs/reports/NIFTY_SHIELD_VIX_HISTORY_STALE_2026-10-09.md`.

**Open choice for the operator.** Should window sessions already banked on the stale window
stay in the window?
- This note keeps them in, on the measured evidence of zero structure changes. Replay parity
  does not gate inclusion (§5), so no rule forces them out.
- Before declaring, check every session from 10-09 to the merge the same way: was it Choppy,
  and was it within 2.9 pp of a gate?
- If one was, its replay may show a signal-stream FAIL after the top-up. Name it in the note.
- Merging before the next Choppy session close to a gate keeps the affected set to 10-08/10-09.
