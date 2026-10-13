# Orchestrator run check — 2026-10-12 and 2026-10-13 (Mon, Tue)

Read-only check at 16:16 on 2026-10-13. Nothing was started, stopped or modified.

## Verdict

**The orchestrator ran clean both days; the forward window did not trade either day.**
Both 13:00 NiftyShield entries were skipped as `missing option marks`, for a reason that is not
a data-feed fault: the strategy struck legs on an expiry that does not exist. This is a
deterministic defect and will repeat on 10-14, 10-15 and 10-16 unless something changes.

## Orchestrator runs (clean)

| Day | 09:10 start | Session runner up | 15:50 stop | `scheduled_runs.log` | Orphans after stop |
|---|---|---|---|---|---|
| Mon 10-12 | yes | **09:45:08** (35 min after 09:10) | 15:50:05 | `END orchestrator exit 0` | none |
| Tue 10-13 | yes | 09:15:11 (5 min) | 15:50:05 | `END orchestrator exit 0` | none |

- `orchestrator.py status`: all 7 children `alive=False`; Task Scheduler `\Nifty\Orchestrator`
  `Last Result 0`, `Next Run 14/10 09:10`. The three orphans and `exit 1` from 10-08 did not recur.
- Telemetry clean both days (`telemetry_clean: true`, 0 violations, 1 startup / 1 recovery /
  1 reconciliation / 1 stop; no guard events; no kill switch; `heartbeat.json` `kill_switched: false`).
- Nightly `download` 10-12 22:00 → 22:12:37, exit 0 (longest recent run, ~12.5 min; 10-05..10-09 were ~5 min).
  10-13's 22:00 run had not started at check time.
- `ts_combo`: `state ok`, `last_formation 2026-10-12`, heartbeat 15:49. `combo_daily` has 12 formation
  rows (09-24 → 10-12), none missing. 10-13's formation lands at tomorrow's 09:10 start, as designed.

## What did not work: 13:00 entries skipped both days

| Day | Regime | Structure | Struck expiry | Journal |
|---|---|---|---|---|
| 10-12 | BearTrend 0.877 | bear_call_spread 22400/22700 CE | **2026-10-20** | `ENTRY_SKIPPED` 13:01:12 — `missing option marks (E7-4, no synthetic fallback)`, both legs |
| 10-13 | BullTrend 0.732 | bull_put_spread 22550/22300 PE | **2026-10-20** | `ENTRY_SKIPPED` 13:01:12 — same reason, both legs |

`marks.jsonl` is `{"marks": {}}` on both days. Cumulative metrics did not move
(26 round trips, realized ₹27,245.17 both days); `structures_skipped` 9→10, `missing option marks` 4→5.

### Root cause (verified)

1. **2026-10-20 is an NSE holiday (Dussehra)** — `core/market/nse_holidays.py:` `date(2026, 10, 20)`.
2. NSE moved that week's Nifty weekly expiry to **Monday 2026-10-19**. The instrument master
   (snapshot 2026-10-13) has 3,434 `NIFTY … 19 OCT 26` contracts and **zero** `20 OCT 26` contracts.
3. `strategies/nifty_shield_v1/structures.py:101` `nearest_expiry()` is a pure weekday calculation
   (Tuesday) with no holiday awareness, so it returned 2026-10-20 and the legs were struck on
   symbols that do not exist.
4. The chain poller cannot rescue it: `chain_poller.py:475-485` asks for `near` and then
   `get_weekly_expiry(near + 7d)`; `chain_poller_heartbeat.json` shows it cached
   `["2026-10-13", "2026-10-27"]` — 10-19 and 10-20 were never in the cache.

Contrast 10-09 (Fri): expiry 2026-10-13, a real Tuesday expiry, marks present, entered and closed.

### Why it is not a one-off

- **Remaining affected sessions this week: 10-14, 10-15, 10-16.** (Inferred from the observed picks
  on 10-09 / 10-12 / 10-13: any session whose first Tuesday ≥ date + `expiry_days_min` is 10-20.)
  10-19 (Mon, real expiry day) rolls to 10-27, which exists.
- **Recurs in November:** 2026-11-10 (Diwali-Balipratipada) and 2026-11-24 (Guru Nanak) are also
  Tuesday holidays; the master already lists `09 NOV 26` and `23 NOV 26` as the real weeklies.
- The earlier 2026-08-24 entry-skip root cause (poller cached only the near weekly) was a different
  defect with the same symptom — which is why this one reads as "feed fault" in the journal.

## Forward window since 2026-10-08 (E008, hash `b33f5c3f…78fa`)

| Session | Structure | Net ₹ | R | Note |
|---|---|---|---|---|
| 10-08 | SPREAD (bear_call 22250/22450) | +645.38 | +0.025 | |
| 10-09 | SPREAD (bull_put 22500/22300, expiry 13-Oct) | +807.91 | +0.031 | time_exit 15:35 |
| 10-12 | — | 0 | — | skipped, nonexistent expiry |
| 10-13 | — | 0 | — | skipped, nonexistent expiry |

Window-to-date: **2 trades in 4 sessions, +₹1,453 net.** 10-07's IRON_CONDOR (+₹29,786) is pre-window
and must stay excluded (open decision from the 10-08 check).

## Other checks

- **Stock straddle M10 capture** (`data/research/straddle_m10/capture.duckdb`): cycle-1 entry
  captured 10-12 — passes c-20/c-10/c-5/c-2 at 15:20/15:30/15:35/15:38, ~7,040 keys each, **0 API failures**,
  `fo_secban` and `ca_forward` artifacts `ok`, expiry 2026-10-27, 213 underlyings. Task ran 15:15 → 15:38
  (expected entry-day length); 10-13's 3-second run is a no-op day. 2,537 of 28,157 quotes have null LTP
  (667 PE, 1,870 CE) — not examined; plausibly deep-OTM no-trade strikes.
- **Recorder:** `prior_capture_merged: false` both days, `span_snapshot_hash: null` (SPAN unavailable is
  the known, ADR-025-covered state). The 10-08 open question about `prior_capture_merged` stands.
- **Preflight is NO-GO** after the stop (poller down) — expected, as on 10-08.

## Not determined

- Why the 10-12 session runner came up at 09:45 (35 min after 09:10) vs 09:15 on 10-13. Probably the
  token-approval wait, but `last_catchup.json` was overwritten and **no orchestrator log exists**
  (finding 5 of the 10-08 check is still open), so this is unverified.
- Whether `expiry_days_min` is 2 — read from observed picks, not from config.
- The 10-13 22:00 download outcome (not yet run at check time).

## Resolution (same day, 16:50) — implemented, not yet merged

Branch `fix/nifty-shield-holiday-expiry`, worktree `F:\Nifty_expiryfix`, uncommitted:

- `nearest_expiry()` is holiday-aware; produced expiries match the instrument master for every
  session 10-14 → 11-06 (the old rule misses from 10-14). Window reset: hash `101bae72…4791`,
  `WINDOW_START 2026-10-14`, ledgered under E008.
- `chain_poller.py` second expiry = next listed after near (was near + 7d, which skipped 10-19).
- `run_if_session.py` tees the target's stdout/stderr to `data/ops/logs/<target>_<date>.log`
  (closes finding 5 of the 10-08 check; orchestrator process only, children not captured).
- 708 tests green across `tests/ops`, `tests/strategies`, `tests/nifty_shield_paper`,
  `tests/execution/test_nifty_shield*`, `tests/runtime`; the one failure
  (`test_driver_calendar_alignment`) needs `data/market_data/futures_bhavcopy.duckdb`, absent in a bare worktree.
- **Deadline:** on `main` in `F:\Nifty` before 09:10 on 10-14, else move `WINDOW_START` to 10-15.

## Decisions for the operator

1. **Fix `nearest_expiry` to snap to the previous session when the weekday date is a holiday
   (use `core/market/nse_holidays.py`), or leave it.**
   - Fixing is inside `EXECUTION_GLOBS` (`strategies/nifty_shield_v1/*.py`) → **re-pin the hash and
     reset the window**, exactly as on 10-07 (ledger note required). It would have to land before
     13:00 on 10-14 to save that session; test case: `2026-10-12 → 2026-10-19`, and the two November
     Tuesdays.
   - Leaving it costs 10-14..10-16 (5 of the window's first 7 sessions skipped) and the same loss on
     the two November weeks; the skips are journaled, so nothing is hidden, but the window would
     systematically never trade holiday-shifted weeks.
2. Give the scheduled orchestrator a log file (carried over from 10-08).
3. Carry-over: stop-or-adopt of orphans is moot this week (none), but 10-07's wing-leg exclusion
   from window metrics is still undecided.
