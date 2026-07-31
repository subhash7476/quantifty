# EOD Automation Scheduler — Design

**Date:** 2026-07-31
**Status:** Design approved, pending implementation plan
**Topic:** UI-toggleable nightly job: download market data at 20:00 Mon–Fri, retry until data arrives, run the strategy chain, report via Telegram.

---

## 1. Goal

Add an option to the existing data page (`/data/`) that enables a nightly automated pipeline:

1. Fire at **20:00 local, Monday–Friday**.
2. Run `scripts/download_all_data.py`.
3. If no new data arrived: determine whether today is a trading day. If not, stop. If it is, retry every 30 minutes.
4. Once data has arrived, run in sequence: `refresh_all_strategies.py` → `ts_basis_daily_signals.py` → `ts_basis_daily_options.py`.
5. Report download success and the options book to Telegram.

---

## 2. Decisions taken (locked during design)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Scheduler home | **Standalone worker process** | Flask runs `debug=True` (`scripts/run_flask.py:33`), so the Werkzeug reloader forks two processes — an in-process thread would double-fire and die on every restart. |
| D2 | Trading-day authority | **Peer-feed inference** | No holiday list exists in the repo, and `trading_calendar` is derived *from* the downloads (circular). |
| D3 | Retry ceiling | **Stop at 23:30 same day** | Bounded to one evening; never collides with the next run. |
| D4 | Chain failure | **Abort at first failure + alert** | The chain is a real dependency; continuing emits authoritative-looking options from stale signals. |
| D5 | Telegram options format | **Reformatted compact list** | The script prints a 109-char-wide table that wraps unreadably on mobile. |
| D6 | Worker start | **Manual launch, documented** | Explicit and observable; a heartbeat makes a stopped worker visible in the UI. |

---

## 3. Architecture

Three components, one responsibility each.

| Component | Responsibility |
|---|---|
| `core/scheduler/eod_job.py` | All logic: feed probing, trading-day inference, retry state machine, chain runner, Telegram formatting. Pure functions where possible; unit-testable without a scheduler. |
| `scripts/schedule_worker.py` | Thin daemon. Ticks every 60 s, decides "is it time?", calls `eod_job`. Contains no business logic. |
| `data/_eod_automation.sqlite` | Control plane: enabled flag, worker heartbeat, run log. The **only** channel between Flask and the worker. |

Flask never executes the job. The UI writes `enabled` and reads status; the worker polls. Consequences: toggling works mid-retry, and no web request can hang on a multi-hour job.

### 3.1 Why SQLite, not DuckDB, for the control store

**This is the single most important implementation constraint in this document.**

DuckDB does not support concurrent multi-process read-write access to one file — it takes an exclusive file lock. Flask and the always-running worker would both need to write (`enabled` from the UI, heartbeat/run-log from the worker), which produces intermittent `Could not set lock on file` errors — a failure that appears only under timing coincidence and is therefore easy to ship.

SQLite in WAL mode is built for exactly this pattern, is in the standard library (no new dependency), and this is a **control-plane** store, not market data — so the "DuckDB is the single source of truth" principle in `CLAUDE.md` is untouched. All market data reads remain DuckDB.

The existing `data/_schedule.duckdb` / `scheduled_jobs` table is **not** reused. Nothing has ever executed those rows (`DataFacade.compute_next_run` is dead code — defined, never called), and repurposing the table would silently change the meaning of any existing rows.

### 3.2 Control schema

```sql
CREATE TABLE IF NOT EXISTS eod_automation (
    id               INTEGER PRIMARY KEY CHECK (id = 1),  -- single row
    enabled          INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT,
    worker_heartbeat TEXT,     -- ISO timestamp, written each tick
    worker_pid       INTEGER
);

CREATE TABLE IF NOT EXISTS eod_run_log (
    run_date    TEXT NOT NULL,     -- 'YYYY-MM-DD'
    attempt     INTEGER NOT NULL,  -- 1-based
    started_at  TEXT,
    finished_at TEXT,
    phase       TEXT,   -- 'download' | 'chain' | 'done'
    outcome     TEXT,   -- 'success' | 'retry' | 'holiday' | 'exhausted' | 'chain_failed'
    detail      TEXT,
    PRIMARY KEY (run_date, attempt)
);
```

---

## 4. Trading-day and success detection

One cheap snapshot of the four independent feeds, reusing the existing helper pattern in `download_all_data._max_trade_date`:

| Feed | Store | Table |
|---|---|---|
| Equity | `data/market_data/equity_bhavcopy.duckdb` | `equity_bhavcopy` |
| Futures | `data/market_data/futures_bhavcopy.duckdb` | `futures_bhavcopy` |
| Stock options | `data/market_data/stock_options_bhavcopy.duckdb` | `stock_options_bhavcopy` |
| Index 1d | `data/market_data/nse/candles/1d/` | file stems (`YYYY-MM-DD.duckdb`) |

Definitions:

- **`data_arrived`** = futures `max(trade_date) == today`.
  Futures is the gate because `refresh_all_strategies.py` consumes exactly that feed (`_latest_source_date()` reads `futures_bhavcopy WHERE inst_type='FUTSTK'`). Declaring success on a feed the chain does not consume would run the chain on absent data.
- **`trading_day`** = **any** of the four feeds has `today`.

### 4.1 Decision table (evaluated after each download attempt)

| Condition | Action |
|---|---|
| `data_arrived` | Run the chain → done for today |
| Some feed has today, futures does not | Trading day, incomplete → retry in 30 min |
| No feed has today, **before 21:00** | Ambiguous (NSE may be late) → retry in 30 min |
| No feed has today, **at/after 21:00** | Declare holiday → stop, send info message |

### 4.2 The 21:00 grace — a deliberate addition to the original request

The original spec says: if no data, check trading day; if not a trading day, stop. At 20:00 sharp, "NSE is late publishing everything" and "today is a holiday" are **indistinguishable** under peer-feed inference — every feed reads yesterday in both cases. Stopping immediately would silently skip a genuine trading day.

The grace window requires the all-feeds-stale condition to persist to 21:00 (≥ 2 failed attempts) before a holiday is declared. On an actual holiday this costs two no-op probes and one message ~1 hour later than it could have come.

---

## 5. Scheduling and retry

- Fires at **20:00 local, Mon–Fri**. The worker logs its resolved timezone/UTC offset at startup; a host not on IST is a footgun and must be visible, not assumed.
- Retry interval **30 min**, hard stop **23:30** → attempts at 20:00, 20:30, …, 23:30 (max 8). On exhaustion: Telegram failure alert, `outcome='exhausted'`.
- **Idempotent per date.** A date with `outcome='success'` is never re-run; restarting the worker mid-evening resumes rather than restarts.
- **Single-instance lock.** A PID/lock file prevents two workers double-downloading. A second instance exits with a clear message.
- **Missed-fire policy.** A worker started at 21:15 on an un-run trading day joins the window at the next tick rather than waiting until tomorrow. Started after 23:30, it does nothing until the next weekday.
- **Kill switch.** `enabled` is re-read every tick, so disabling from the UI halts an in-flight retry loop before the next attempt (it does not kill a subprocess already running).

---

## 6. The chain

On `data_arrived`, run sequentially with `cwd=ROOT`:

1. `scripts/refresh_all_strategies.py`
2. `scripts/ts_basis_daily_signals.py`
3. `scripts/ts_basis_daily_options.py`

Abort at the first non-zero exit; send a Telegram alert naming the step and its last ~20 lines of stderr; do not run downstream steps; record `outcome='chain_failed'`.

**Windows-specific requirements (both are known failure modes in this repo):**

- Subprocess capture **must** use `encoding='utf-8', errors='replace'`. Console output in this repo contains `—`, `→`, `₹`; the default Windows code page raises `UnicodeDecodeError` mid-run. The mojibake visible in recent pipeline logs is this same issue.
- Every step needs an explicit `timeout` so a hung child cannot wedge the worker until morning.

---

## 7. Telegram

Reuses `core/alerts/telegram_notifier.py` (env `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`).

**Required change — synchronous send.** The existing `TelegramNotifier.send_message` dispatches on a **daemon thread and returns immediately**. A daemon thread is killed when the process exits, so a message sent just before the worker finishes may never leave. The job needs a synchronous send path that returns delivery success and logs failures. This is additive; the existing async method stays for its current callers.

**Parse mode.** The notifier currently hardcodes `parse_mode: "Markdown"`. Ticker/table content containing `_`, `*`, `[` will produce a Telegram **400 Bad Request** and the message is lost. Messages from this job send as plain text, or escape rigorously. Plain text is the default.

**Message set:**

| Trigger | Content |
|---|---|
| Data arrived | Which feeds advanced, to what date, rows inserted |
| Options book | Compact per-position list from `get_book()` — ticker, direction, strike, expiry, premium |
| Chain failure | Failed step name + last ~20 lines of stderr |
| Exhausted / holiday | Attempt count and final feed state |

All messages truncate to stay under Telegram's 4096-character limit, with an explicit `… truncated` marker so silent loss is impossible.

The options message is built from `ts_basis_daily_options.get_book(target, top_n)` (structured data), not by scraping the 109-char console table.

---

## 8. UI

A new card on `/data/`, following the existing blueprint/facade pattern (`flask_app/blueprints/data/routes.py` → `app_facade/data_facade.py`):

- **Enable/disable toggle** → writes `eod_automation.enabled`
- **Status:** last run date + outcome, next fire time, current retry attempt
- **Worker health:** derived from `worker_heartbeat`; shows *"worker not running"* when the heartbeat is older than ~3 min, so a stopped worker cannot fail silently
- **Run now** button → sets a one-shot trigger the worker picks up on its next tick, for testing the full path without waiting until 20:00

**"Run now" semantics (explicit, to avoid two readings):**

- Executes the download + chain **immediately**, regardless of clock, weekday, or the 20:00 window.
- Still honours the §4.1 decision table: on a holiday it reports "no data, not a trading day" rather than retrying.
- Does **not** start the 30-minute retry loop — it is a single attempt.
- Records `attempt = 0` in `eod_run_log` so a manual test is distinguishable from scheduled attempts and **never** marks the date complete. A successful manual run therefore does not suppress that evening's real 20:00 run.
- Works while `enabled = 0`, so the path can be tested before arming the schedule.

The worker heartbeats on every tick **whether or not `enabled` is set**, so the UI distinguishes "worker down" from "worker up, automation off".

New endpoints: `GET /api/eod/status`, `POST /api/eod/toggle`, `POST /api/eod/run-now`.

---

## 9. Testing

| Layer | What is tested |
|---|---|
| Unit | Decision table §4.1 — all four branches, against synthetic feed-date inputs (no real stores) |
| Unit | Retry schedule: fire times, 23:30 ceiling, attempt cap, idempotent skip of a completed date |
| Unit | Grace-window boundary: all-feeds-stale at 20:30 → retry; at 21:00 → holiday |
| Unit | Telegram formatting: truncation at the 4096 limit, plain-text safety of ticker strings |
| Integration | Chain runner aborts on non-zero exit and does not invoke downstream steps (fake scripts) |
| Manual | **Run now** through the real path, verifying both Telegram messages arrive |

Trading-day inference is tested against **synthetic** feed dates, never live stores, so the tests are deterministic and runnable on a holiday.

---

## 10. Out of scope

- Repairing or removing the dead `scheduled_jobs` schedule tab (flagged separately; untouched here).
- Any change to `download_all_data.py` or the three chained scripts. This design only *orchestrates* them.
- Backfill of historical missed days.

---

## 11. Known risks

| Risk | Mitigation |
|---|---|
| Worker not started after reboot | Heartbeat surfaces "worker not running" in the UI |
| Host not on IST | Offset logged at startup |
| NSE publishes after 23:30 | Run is marked `exhausted`; next day's incremental run self-heals via the 7-day lookback window |
| DuckDB lock contention against a running Flask | Control plane is SQLite/WAL; feed probes are short-lived read-only connections |
| Telegram down at report time | Delivery failure is logged and recorded in `eod_run_log.detail`; the data work is already complete and is not rolled back |
