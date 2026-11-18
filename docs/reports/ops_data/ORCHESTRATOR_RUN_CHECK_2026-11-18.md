# Orchestrator run check — 2026-11-18 (sessions 2026-11-09 → 2026-11-18)

Read-only check of `data/ops/scheduled_runs.log`, `data/ops/logs/*`, `logs/*`, the E008 session
dirs and `scripts/ops/preflight.py`. Nothing was modified.

## 1. Monday 2026-11-16 — root cause of the lost session

| Time | Event |
|---|---|
| 09:10:02 | `Orchestrator` task starts; instrument master refresh OK; Flask up |
| 09:10 | "Upstox approval requested — tap Approve…" printed |
| ~09:20 | "Upstox token required. Opening /ops/login/upstox" (10-min phone-approval fallback fired) |
| — | **No `token_approval ... token received` line, ever.** No marks warm-up, no ingestor, no session, no catch-up |
| 11:25:13 | `shutting down...` — orchestrator stopped by an interrupt, **exit 0** (so `run_if_session.py` sent no Telegram alert) |
| 15:15 / 22:00 | straddle_capture ("not a T-10/T-1 session") and DownloadAll ran normally |

**Cause: the token gate never got a token — neither the phone approval nor the browser fallback was
completed — and the supervisor sat in the gate for 2 h 15 min until it was stopped by hand.** There is
no crash, traceback or code error on that day. Consequences: no E008 session for 11-16 (no
`sessions/2026-11-16/`, no orders), no `catchup_20261116_*.log` (the morning catch-up is dispatched only
after the gate), `ts_combo` not started that day.

Self-healed: 11-17 catch-up and the 22:00 DownloadAll filled 11-16's data (`span` shows 11-16 skipped =
already archived; 1m candles OK).

### The recurring weakness (not an error, but it is what made Monday possible)
Approval latency, orchestrator start 09:10 → token received:

| Day | Latency | Day | Latency |
|---|---|---|---|
| 10-27, 10-29, 10-30, 11-03, 11-04, 11-06, 11-11 | ~1 min | 11-12 | ~2 min |
| 11-13 | ~12 min | 10-28 | 43 min |
| 11-02 | 73 min | 11-05 | 30 min |
| 11-09 | 37 min | 11-17 | 29 min |
| 11-18 | 37 min | **11-16** | **never** |

Six of the 16 sessions since 10-27 started 30–73 min late and one never started. Everything downstream of the
gate (marks warm-up, ingestor, session) waits on a human tap, and **nothing alerts while it waits**:
the gate is silent in Telegram, and a manual stop returns exit 0, which the scheduler treats as success.
Gate wait is also lossy even when approved: today's session started 09:47 (bars 09:15–09:47 not
processed by the driver; harmless for the 13:01 / 15:35 E008 entries, not harmless for anything that
trades the open).

## 2. Errors found in the window (11-09 → 11-18)

| # | Where | What | Severity |
|---|---|---|---|
| E1 | `logs/catchup_20261117_093932.log:623` | `[cas-mark] FAILED: IO Error … candles\1m\2026-11-11.duckdb … used by another process`. The catch-up said `DONE WITH ERRORS`. | Low — self-healed: today's catch-up marked from 11-10 and reported `OK — 14,785 bars newly flagged on 5 sessions`. Another process held a read lock on the 11-11 1m file while the marker needed to write. Unidentified which. |
| E2 | `logs/catchup_20261117_093932.log` | `Evidence failures: 16` | Pre-existing counter, same value in 11-18's log; not new. |
| E3 | `logs/chain_poller.log` | Last ERROR 2026-10-29 (`os.replace … Access is denied`, keeps previous snapshot). None since. | Cleared |
| E4 | `logs/options_wall_poller.log` | No ERROR/Traceback. | Clean |
| E5 | `logs/publish_live_fact.log` | Last warning 11-04 (Bank Nifty `live_buffer short of 13:00`, falls back to next source). None 11-09 onward. | Clean |
| E6 | 11-17 warm-up | `live_vix: VIX not flowing (bar_age=65417s)` and `marks not warm (hb_age=323956s)` at 09:39 | Expected on a late start from a stale buffer; resolved — 13:01 order placed 11-17, today preflight `live_vix OK`. |

Preflight 2026-11-18 11:51: **VERDICT GO** (token fresh, no STOP, marks warm, VIX 132 s old; WARN `span`
snapshot absent — PAPER tolerates it, as before).

## 3. Forward runs

| Run | Status | Evidence |
|---|---|---|
| Orchestrator (Task Scheduler, 09:10) | 11-09, 11-11, 11-12, 11-13, 11-17 ran to 15:50 and exited 0; **11-16 lost (above)**; 11-18 running | `scheduled_runs.log` |
| Day-end stop at 15:50 | Working (every completed day ends 15:50:03–15:50:19) | `scheduled_runs.log` |
| E008 NiftyShield PAPER | Fills 13:01 + 15:35 on 11-09, 11-11, 11-12, 11-13, 11-17 (2+2 each). Gap 11-16 only. 11-17 `execution_hash` = `7a1bc61f…` — **matches the pinned hash**, `platform_commit` c94052c, 371 driver bars, 1,206 marks calls, 2 signals. Not tripped: `kill_switched=false`. 11-18: running, `data_healthy=true`, equity 1,024,039, 0 trades so far (13:01 entry still ahead) | `sessions/2026-11-17/meta.json`, `heartbeat.json` |
| Ingestor | CONNECTED, heartbeat live, started 09:47 | `market_ingestor_status.json` |
| TS Basis Daily combo paper | `state: ok`, "up to date", `last_formation 2026-11-17`, heartbeat live | `data/paper/ts_daily_combo/status.json` |
| Straddle-M10 capture (15:15) | Task fires daily and correctly no-ops outside T-10/T-1. Cycle with expiry 2026-11-23 had its entry capture on 11-06 (218/218 futures, 99.8–99.9 % two-sided, api_fail 0). **Its T-1 capture should fall on 2026-11-20 (Fri) 15:15 (inferred from expiry 11-23 and the "T-10 or T-1 session" rule; not confirmed in code).** | `straddle_capture_2026-11-06.log` |
| DownloadAll (22:00) | exit 0 every night 11-09 → 11-17 (11-11 took 12 min, rest ~6) | `scheduled_runs.log` |

## 4. Not errors, but open

* **Muhurat 2026 (Sun 2026-11-08):** orchestrator/download logged `SKIP … not a trading session` and
  `core/market/session_schedule.py` has no 2026-11 entry. If NSE held a Muhurat session, the 1m store has no
  bars for it and the table was not updated before the date (standing obligation in CLAUDE.md). Not
  verified against NSE's circular here.
* 2027 holidays still due in `nse_holidays.py` / `trading_calendar.py` before the jobs stop on 2027-01-01.

## 5. Suggested fixes (none applied)

1. **Alert while the gate waits.** Telegram ping if no token by ~09:25, and again at the 10-min
   browser-fallback; this is the Monday failure.
2. **Non-zero exit when the stack never started** (gate abandoned/interrupted before `start sequence`), so
   `run_if_session.py` Telegram-alerts instead of logging `exit 0`.
3. **Find the 11-11 file-lock holder** if E1 repeats (cas-mark vs. a reader on the 1m store).
4. Re-ask for the phone approval on a timer (e.g. every 10 min) rather than a single request, since late
   approvals cluster on the days the first push was not seen.
