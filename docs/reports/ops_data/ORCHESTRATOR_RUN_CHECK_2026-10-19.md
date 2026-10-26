# Orchestrator run check — 2026-10-19 (first session after PRs #45–#52)

Checked at ~11:57 IST, mid-session. Checkout `F:\Nifty` = `main` @ `11251bd` (#52), fast-forwarded
2026-10-18 21:37, i.e. before today's 09:10 start.

## Start sequence — clean

| Step | Time | Result |
|---|---|---|
| Scheduled start (`run_if_session.py`) | 09:10:01 | START logged |
| Instrument master | 09:10:15 | 69,183 rows published |
| Token gate | 09:10:56 | phone approval, ~50 s |
| Park for derivatives open | 09:10:58 → 09:15 | parked, then started |
| Warm-up | 09:15:30 | marks cold (heartbeat 236,136 s old, i.e. since Friday), VIX warm; proceeded |
| Catch-up download (`--download-only`) | 09:15:33 | ran to `ALL DONE` |
| Supervision | 09:15:34 | "supervising until 15:50" |

## Children

| Child | State at 11:57 |
|---|---|
| Market ingestor | CONNECTED, heartbeat current |
| NiftyShield E008 session | running; 161 bars, `data_healthy`, `kill_switched: false`, 0 trades so far |
| Options-Wall poller | polling NIFTY + SENSEX; paper trades below |
| `ts_combo` | `ok / up to date`, last formation 2026-10-16 |
| Flask | up, no errors today |

**One transient:** Upstox HTTPS connection errors 11:52–11:55 (`SSLError`, `ConnectionAbortedError
10053`) in `options_provider` and the wall poller. Recovered by itself by 11:56; the E008 bar count
stalled at 159 for ~1 min and resumed. No kill-switch trip, no `KILL_SWITCH_*` journal event.

## Fix-by-fix

| PR | Fix | Verified today? |
|---|---|---|
| #52 | E008 ledger + lots; hash re-pin | **Yes (identity).** `execution_hash()` of the running tree = `7a1bc61f…8bb1`, matching the ledger's `WINDOW_START 2026-10-19` condition (merged before 09:10). Startup: recovery → `RECONCILIATION_PASS` → running. Lot sizing not exercised yet (no entry so far). `meta.json` is written at session end — confirm its `execution_hash` after 15:50. |
| #51 | Wall time stop on last session before expiry | **Logic checked, not yet fired.** `time_stop_day` gives 10-19→10-16, 10-22→**10-21** (skips the 10-20 holiday), 10-27→10-26. Open SENSEX trade 72 (expiry 10-22) will time-stop 10-21 15:35. Trade 73 (NIFTY, expiry 10-19) was opened Fri 10-16 under the old code and carried over the weekend — exactly the defect #51 fixes; it closed on TP at 09:15:39 today. |
| #45 | Wall entries honour `STOP` | Indirect: no STOP file, entries opened (trades 74, 75). The STOP branch itself was not exercised. |
| #50 | `orchestrator stop` shuts the orchestrator down first | Not exercised (no manual stop). The 15:50 self-stop is due later today. |
| #47, #49 | Live Upstox order path, fill-poll release, V3 placement | **Not exercisable** — LIVE-broker code; today is PAPER. Only check possible: the driver changes in `core/runtime/driver.py` run cleanly in PAPER (no errors, bars advancing). |

## Options-Wall paper trades today

| ID | Underlying | Expiry | Entry | Exit | Reason | Net P&L |
|---|---|---|---|---|---|---|
| 73 | NIFTY | 10-19 | 10-16 10:43 | 10-19 09:15 | tp | +2,858 |
| 74 | NIFTY | 10-19 | 10-19 09:30 | 10-19 11:56 | tp | +2,213 |
| 75 | NIFTY | 10-19 | 10-19 11:56 | 10-19 15:20 | tp | +1,905 |
| 72 | SENSEX | 10-22 | 10-16 09:30 | open | — | — |

## Observation (not a defect in #51)

`ScanConfig.min_dte = 0` admits expiry-day flies by design, so trades 74/75 open **on** NIFTY expiry
day and the time stop (time_stop_day 10-16 ≤ today) fires at 15:35 today. #51 keeps flies from being
*carried* into expiry day; it does not stop new entries on it. Whether expiry-day entries are wanted is
a strategy question, left open.

## End-of-day check (after 15:50) — all four pass

1. **Day-end stop:** at 15:50:04 the log reads "trading day over — stopping the stack", the
   LoopDriver logs `STOPPING`→`STOPPED`, and the scheduler logs `END orchestrator 2026-10-19 exit 0`
   at 15:50:14. `straddle_capture` ran 15:15 (exit 0).
2. **#52 identity:** `sessions/2026-10-19/meta.json` has `platform_commit 11251bd` and
   `execution_hash 7a1bc61f…8bb1`. So today is the first session inside the new window.
   395 driver bars, 1,210 marks calls, 2 signals.
3. **Wall trade 75:** closed on **TP at 15:20:46** (net +1,905), before the 15:35 time stop, so the
   expiry-day `time_stop` path did not fire today. All three NIFTY trades closed on TP
   (+2,858, +2,213, +1,905). SENSEX trade 72 stays open into its 10-21 15:35 time stop.
4. **#52 lots:** E008 entered at 13:01, 2 legs on the 27-Oct expiry: SELL 22900 CE and BUY 23150 CE,
   `1 lots x 65`. The lot of 65 matches the instrument master `lot_size` and the wall's qty. Margin
   was Rs 39,391 on the Upstox basket. The structure closed on `time_exit` at 15:35. It wrote
   **two `trades` rows**, one per leg. The fills total 4 × 65, and both legs are FLAT in `positions`.
   **Journal:** the only WARNING today is the expected SPAN-unavailable note (ADR-025). There is no
   ERROR and no `KILL_SWITCH` event. The wall poller logged no errors after 12:00.

Still unexercised: #45 (STOP present), #50 (manual `orchestrator stop`), and #47/#49 (LIVE broker
path). Exercising them needs a deliberate STOP drill, a manual stop, or a LIVE session.
