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
**Severity:** HIGH (feed cannot stay up). **Root cause not yet confirmed.**
**Evidence:** After the WS started (10:55:26), repeated
`sent 1011 (internal error) keepalive ping timeout; no close frame received.
Reconnecting in 1.0s…`. Confirmed **single** ingestor process (PID 14084) — NOT a
duplicate-token connection. Prime suspect: event-loop starvation — the tick handler /
1.5s aggregation blocks the asyncio loop so the keepalive pong is processed too late
and the client self-closes 1011.
**Investigate:** `core/database/ingestors/websocket_ingestor.py` — is the DuckDB tick
write done inline on the event loop? What are `ping_interval`/`ping_timeout`? **Fix
direction:** offload the write off the event loop (queue + worker thread) and/or tune
ping settings.

## F4 — Live-buffer DuckDB held RW-locked; readers contend
**Severity:** HIGH (blocks the 13:00 day-type fact even if the WS is healthy).
**Evidence:** with the ingestor up, a read-only open of
`data/live_buffer/candles_today.duckdb` fails: `Cannot open file … being used by
another process … already open in … PID 14084`. DuckDB permits only one read-write
holder. The 13:00 publisher (`scripts/daytype/publish_live_fact.py` opens the buffer
`read_only`), the preflight VIX check, and `LiveDuckDBMarketDataProvider` all read the
same file and will contend.
**Fix direction:** the ingestor must not hold a persistent RW connection during the
read window — either the temp-DB + `os.replace` pattern the chain poller uses, short-
lived per-flush writes, or a reader-friendly access mode. Design decision required.

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
1. **F2** (our code; smallest, unblocks the one-command start's core behavior).
2. **F4** (buffer lock) and **F3** (WS storm) — the two that actually gate a live feed;
   needs `systematic-debugging` on `websocket_ingestor.py` + the buffer access pattern.
3. **F1** (recovery gating) — restructure connect-then-backfill.
4. **F5**, **F6** — schema bootstrap + missing module (quick).
