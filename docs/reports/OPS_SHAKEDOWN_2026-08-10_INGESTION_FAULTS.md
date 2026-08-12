# Ops Shakedown 2026-08-10 — Ingestion-Layer Fault Stack

**Context:** First real full-stack bring-up of the trading window via the new
`scripts/ops/orchestrator.py` (branch `feat/ops-orchestrator`). The orchestrator +
preflight worked as designed — preflight correctly returned NO-GO on a cold VIX feed
and the orchestrator refused to start the PAPER session blind. What the run exposed is
a stack of **pre-existing data-ingestion faults** underneath. This is the backlog for a
post-market `systematic-debugging` pass. **No live code fixes were made** (operator
decision: stand down, fix after close), except one stopgap noted below.

Status at hand-off: session NOT started (correctly gated); India VIX / index bars
frozen at 09:13; single ingestor (PID 14084) up but in a WebSocket reconnect storm.

---

## Fix status (post-market pass, 2026-08-10, branch `feat/ops-orchestrator`)

| Fault | Status | Where |
|---|---|---|
| **F2** | **FIXED** (symmetric warm-up park on marks+VIX; final gate retries/park on "still warming", only a warm-stack NO-GO is a genuine block) | `scripts/ops/orchestrator.py` `start_sequence`; design spec §5.1 updated; 4 new tests |
| **F3** | **FIXED** (writer-worker redesign — WS handler enqueues raw frames only; parse+tz+DB moved to the `LiveBufferWriter` worker thread; explicit ping params). **Live-morning close-out check below** | `core/database/ingestors/websocket_ingestor.py`, `core/database/ingestors/live_buffer_writer.py` (new) |
| **F4** | **FIXED** (single-writer worker: tick path opens `ticks` only, candle writes chunked per-symbol short-lived, reader bounded-retry on candles open, DDL bootstrapped once). **Live-morning close-out check below** | `core/database/ingestors/live_buffer_writer.py` (new), `db_tick_aggregator.py`, `manager.py` |
| **F1** | **FIXED** (connect-then-async-backfill — WS starts first; `RecoveryManager` runs on a background thread, recovered bars enqueued to the worker as `RecoverBars`) | `scripts/market_ingestor.py` `_try_connect` |
| **F5** | **FIXED** — idempotent config-schema bootstrap applied at ingestor + Flask startup | `core/database/schema.py::bootstrap_config_db`; 2 new tests |
| **F6** | **FIXED** — dead `scripts.daily_historical_fill` reference removed (module never existed in git; superseded by startup recovery) | `scripts/market_ingestor.py` |

---

## F1 — Startup recovery gates the WebSocket connect (minutes-long)
**Severity:** HIGH (blocks the live feed at every startup).
**Evidence:** `scripts/market_ingestor.py:195` calls
`RecoveryManager.run_recovery(self.symbols)` BEFORE the WS connects; `run_recovery`
(`core/database/ingestors/recovery_manager.py:37-41`) loops **sequentially over ~200
symbols**, each an Upstox intraday backfill fetch. Log showed "Running initial
recovery/backfill…" at 09:22:36 with the WS only starting at 10:55.
**Fix direction:** connect the WS first and backfill asynchronously; or skip recovery
when starting at/after open; or parallelize/bound the per-symbol fetch. The live
session needs the live feed, not a synchronous historical backfill.

## F2 — Orchestrator park is asymmetric + hard-shutdown on a not-warm-yet gate
**Severity:** HIGH. **This is the one defect in the NEW ops code.**
**Evidence:** `scripts/ops/orchestrator.py` `start_sequence` parks on `marks_warm`
(poller) only, not on ingestor/VIX warmth. With F1 making the ingestor slow to warm,
the sequence advanced to the final preflight gate while VIX was cold → `verdict`
NO-GO → `_cmd_start` called `sup.shutdown()`, which terminated the still-warming
ingestor. The morning's repeated "dead ingestor pids" were the orchestrator killing
its own child, not crashes.
**Fix direction:** (a) the warm-up park must also wait on VIX/ingestor freshness,
symmetric with marks; (b) a "not warm yet" preflight failure at the final gate must
be distinguished from a genuine BLOCK — retry/park rather than hard-shutdown the
stack. Update the design spec §5.1 accordingly.

## F3 — WebSocket 1011 keepalive-ping-timeout reconnect storm
**Severity:** HIGH (feed cannot stay up). **Root cause CONFIRMED (post-market pass).**
**Evidence:** After the WS started (10:55:26), repeated
`sent 1011 (internal error) keepalive ping timeout; no close frame received.
Reconnecting in 1.0s…`. Confirmed **single** ingestor process (PID 14084) — NOT a
duplicate-token connection.
**Root cause (confirmed by code trace):** the WS message handler runs **inline on
the asyncio event loop** (`websocket_ingestor.py:175-180` — `async for message in
ws: … self._handle_message(message)`), and `_handle_message` → `TickBuffer.add_tick`
→ `TickBuffer.flush()` performs **synchronous DuckDB writes on the loop thread**:
`live_buffer_writer()` (open 2 RW connections + `CREATE TABLE IF NOT EXISTS` +
`executemany`), a `WriterLock` file lock, and a `time.sleep` retry path. With ~200
symbols at 100-tick/0.5s flush cadence, plus contention for the buffer's
thread/file lock with the main-thread aggregator (see F4), the loop is blocked well
past `websockets`' default keepalive `ping_timeout` → the client self-closes 1011.
**Fix direction (not yet implemented):** offload the DuckDB write off the event loop
(queue + worker thread, so `_handle_message` only buffers in memory) and/or tune
`ping_interval`/`ping_timeout`; combined with F4's short-lived buffer writes.

## F4 — Live-buffer DuckDB held RW-locked; readers contend
**Severity:** HIGH (blocks the 13:00 day-type fact even if the WS is healthy).
**Root cause CONFIRMED (post-market pass).**
**Evidence:** with the ingestor up, a read-only open of
`data/live_buffer/candles_today.duckdb` fails: `Cannot open file … being used by
another process … already open in … PID 14084`. DuckDB permits only one read-write
holder. The 13:00 publisher (`scripts/daytype/publish_live_fact.py` opens the buffer
`read_only`), the preflight VIX check, and `LiveDuckDBMarketDataProvider` all read the
same file and will contend.
**Root cause (confirmed by code trace):** `DBTickAggregator.aggregate_outstanding_ticks`
(`db_tick_aggregator.py:30`) opens **one** `live_buffer_writer()` RW connection for the
whole ~200-symbol batch and holds it while iterating (comment: "Open connections once
for the entire batch"). DuckDB allows only one RW holder, and `live_buffer_reader()`
additionally waits on the same in-process `_get_thread_lock('live_buffer')` — so the
hold blocks both external readers and the ingestor's own event-loop tick flush (the
F3 link).
**Fix direction (design decision required):** the chain-poller temp-DB + `os.replace`
pattern is the model the report names, but the live buffer is a continuously-appended
per-day store (ticks + candles), so a snapshot-swap is not a drop-in. Options: (a)
short-lived per-symbol/small-chunk RW transactions so no holder outlives ~ms, with
readers using a bounded retry; (b) a reader-friendly access mode; (c) a dedicated
writer process owning the file with readers served from a replica. The chain poller's
atomic-swap proof (this shakedown: readers never contended with it) is the target
shape.

## F5 — `websocket_status` table missing (config DB never bootstrapped)
**Severity:** MEDIUM (log spam + broken dashboard panel). **Stopgapped live.**
**Evidence:** `market_ingestor._update_websocket_status` (`market_ingestor.py:174`)
does a bare INSERT assuming the table exists; it errored `no such table:
websocket_status` every 1.5s. Root cause: `BOOTSTRAP_STATEMENTS`
(`core/database/schema.py:297`, includes `CONFIG_WEBSOCKET_STATUS_SCHEMA`) is exported
from `core/database/__init__.py` but **never executed anywhere at runtime**, so an
existing config DB predating the table never gets it.
**Stopgap applied (live):** manually created the table in `data/config/config.db`.
**Fix direction:** apply the config schema (run `BOOTSTRAP_STATEMENTS` against the
config DB) at ingestor/Flask startup.

## F6 — Missing module `scripts.daily_historical_fill`
**Severity:** LOW (non-blocking).
**Evidence:** `[DailyFill] Failed (non-blocking): No module named
'scripts.daily_historical_fill'` at ingestor startup (10:55:26).
**Fix direction:** restore the module or remove the dead reference.

---

## F3/F4 close-out — live-morning verification checklist (MANDATORY before trust)

The writer-worker redesign (2026-08-10) is proven by a cross-process integration test
(`tests/database/ingestors/test_reader_no_contention.py`) and 18 ingestor-suite tests,
but the two concrete cross-process readers F4 exists to unblock cannot run headless —
they need the real `data/live_buffer` and a live feed. Run these on the next live
morning before this branch is trusted for a live window:

1. **VIX BLOCK check reads through.** With the ingestor + worker under real load, run
   `python scripts/ops/preflight.py` and confirm the VIX BLOCK check reads
   `candles_today.duckdb` (no "being used by another process") and goes warm.
2. **13:00 day-type publisher.** At/near 13:00, confirm
   `scripts/daytype/publish_live_fact.py` opens `candles_today.duckdb` read-only and
   publishes the day-type fact without a lock error.
3. **No WS keepalive storm.** Confirm the WS stays connected through the open with no
   `1011 keepalive ping timeout` reconnect in the ingestor log (F3 closed).

---

## What worked (do not "fix")
- **Preflight** correctly returned NO-GO on the cold VIX feed (the VIX BLOCK check is
  the safety net that caught the wedged/absent feed `websocket_status=OPEN` would hide).
- **The orchestrator** correctly refused to start the PAPER session against `{}`/cold
  marks+VIX rather than running one blind. The one defect (F2) is that it *tore down*
  the stack instead of *waiting longer* — a park/retry problem, not a gate problem.
- **Chain poller** performed exactly to spec: fresh marks (226 rows, 181 priceable @
  09:22), one snapshot-timestamp per cycle, heartbeat matching, correct near-weekly
  expiry (2026-08-11), and its temp-DB+`os.replace` pattern let readers in without
  contention — the model F4 should follow.

## Suggested fix order (post-market)
1. **F2** — DONE (2026-08-10, `start_sequence` symmetric park + retry-not-teardown gate).
2. **F5**, **F6** — DONE (2026-08-10, config bootstrap + dead reference removed).
3. **F4** (buffer lock) and **F3** (WS storm) — the two that actually gate a live feed;
   root causes confirmed (long-held RW batch vs. sync DuckDB writes on the event loop,
   causally linked); implementation needs a buffer-access design decision + review of
   `websocket_ingestor.py` / `db_tick_aggregator.py`.
4. **F1** (recovery gating) — restructure connect-then-backfill (design decision).
