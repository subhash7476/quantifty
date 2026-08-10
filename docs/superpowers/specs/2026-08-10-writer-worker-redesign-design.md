# Writer-Worker Redesign — Live-Buffer Ingestion (F1/F3/F4)

**Date:** 2026-08-10
**Branch:** `feat/ops-orchestrator`
**Status:** Design approved (operator sign-off 2026-08-10). Implementation not started.
**Author split:** Claude writes spec + plan and reviews; DeepSeek implements (per the
standing role split).

---

## 1. Problem

The 2026-08-10 shakedown (`docs/reports/OPS_SHAKEDOWN_2026-08-10_INGESTION_FAULTS.md`)
surfaced three causally-linked ingestion-core faults. They are **one fix**, not three:

- **F3** — WebSocket `1011 keepalive ping timeout` reconnect storm. The WS message
  handler runs inline on the asyncio event loop and performs a synchronous DuckDB write
  (plus protobuf parse and per-tick timezone conversion) on the loop thread. With ~200
  symbols the loop is blocked past the `websockets` default `ping_timeout` → the client
  self-closes 1011 and reconnects in a loop.
- **F4** — `DBTickAggregator` opens **one** `live_buffer_writer()` RW connection and
  holds it for the entire ~200-symbol batch. DuckDB allows only one RW holder per file,
  so cross-process readers (13:00 day-type publisher, preflight VIX,
  `LiveDuckDBMarketDataProvider`) cannot open `candles_today.duckdb` read-only during the
  hold.
- **F1** — `market_ingestor._try_connect` runs `RecoveryManager.run_recovery` (a
  sequential ~200-symbol Upstox intraday backfill) **before** the WS connects, delaying
  the live feed by minutes at every startup.

### 1.1 Empirically-established facts (DuckDB locking probe, 2026-08-10)

A probe of raw DuckDB locking semantics settled the design scope:

1. **DuckDB locks per-file.** While one process held `ticks_today.duckdb` RW, a second
   process opened `candles_today.duckdb` **both** read-only and read-write successfully.
   → The 0.5 s tick flush currently opening `candles` RW (via `live_buffer_writer()`,
   which opens both files) is **manufactured contention** — the tick path never writes
   candles.
2. **Cross-process read-only cannot coexist with a cross-process read-write on the same
   file** (opening `ticks` RO failed while another process held `ticks` RW). This is why
   readers of `candles` require short-lived writers plus bounded retry rather than a
   long-lived RW holder.
3. **Same-process, two DuckDB connections to one file conflict** ("different
   configuration"). In the ingestor this never actually fires today because
   `_get_thread_lock('live_buffer')` already serializes every in-process live-buffer
   open. **The only readers that truly contend are cross-process, and they only ever read
   `candles`.**
4. **Short-lived writes + bounded-retry readers works.** Against 13 short-lived candle RW
   open→write→close cycles in 0.6 s, a retrying reader landed **37 of 40** opens; retry
   absorbed the 3 collisions. This is the chain-poller "readers don't contend" outcome
   adapted to a continuously-appended store.

**Consequence:** the reader-facing problem reduces to `candles` being held RW too long
and by the wrong code path. Two levers close it — (a) stop the high-frequency tick flush
from touching `candles` at all, and (b) make candle writes short-lived instead of one
200-symbol hold. F3 is separately about getting the parse + write off the event loop.

---

## 2. Architecture — single writer worker

**Invariant:** exactly one thread — the `LiveBufferWriter` worker — ever opens
`ticks_today.duckdb` or `candles_today.duckdb` **read-write**. Every other component
that needs to mutate the live buffer enqueues a command. Cross-process readers open
read-only with bounded retry.

This closes the F3↔F4 seam at its root: no live-buffer write ever runs on the asyncio
loop (F3), and no RW holder outlives a single short chunk (F4). It also gives one
auditable owner of the locking discipline on the ingestion core, where the fault bit us.

### 2.1 Components

| Unit | Role after redesign |
|---|---|
| `core/database/ingestors/live_buffer_writer.py` (**new**) | The worker thread + bounded `queue.Queue`. Sole RW owner of the live buffer. Drains commands, each a short-lived open→write→close on the narrowest file set. |
| `websocket_ingestor.py` | `_handle_message` enqueues **raw frame bytes** only. `TickBuffer` (the in-loop buffered writer) is removed. WS connect sets explicit ping params. |
| `db_tick_aggregator.py` | Aggregation logic invoked **by the worker** on an `Aggregate` command; writes candles in bounded chunks (never one 200-symbol hold). |
| `recovery_manager.py` | Recovered bars are **enqueued** to the worker, not written via a direct `live_buffer_writer()`. |
| `manager.py` | `live_buffer_reader()` candles-open gains bounded retry; live-buffer DDL bootstrapped once, not per open. |
| `market_ingestor.py` | Owns the worker lifecycle; reorders startup to connect-then-async-backfill; posts the periodic `Aggregate` signal. |

### 2.2 Command model

The worker consumes a bounded `queue.Queue` of commands:

- `TickFrame(raw_bytes)` — posted by the WS handler per message. Worker parses the
  protobuf, extracts LTP/LTT/LTQ, converts to naive IST, coalesces into a batch, and
  appends via a **ticks-file-only** short-lived RW cycle.
- `Aggregate(symbols)` — posted by the main loop every 1.5 s. Worker runs the aggregation
  SQL (ticks read, candles write) in **bounded chunks**, each its own short open→write→
  close on `candles`.
- `RecoverBars(rows)` — posted by the background recovery thread. Worker inserts synthetic
  candles (short-lived, candles-file-only).
- `Purge(cutoff)` — posted at startup / EOD rollover. Worker deletes rows before `cutoff`
  (the one command that legitimately opens both files).

### 2.3 Backpressure & shutdown (operator-approved policy)

- **Backpressure: drop-oldest tick frames.** The queue is bounded. On overflow, the
  worker (or the enqueue path) drops the **oldest `TickFrame`** items and increments a
  warned counter — preserving today's "drop old ticks to prevent memory overflow" intent.
  `Aggregate`, `RecoverBars`, and `Purge` are **never** dropped.
- **Shutdown drain.** `stop()` posts a sentinel and joins the worker so buffered ticks are
  flushed before exit. (Today `WebSocketIngestor.stop()` flushes synchronously; under a
  queue, ticks are silently lost without an explicit drain — this is a required test.)

---

## 3. F3 — event-loop offload

`_handle_message` does **only** `queue.put`/`put_nowait` of the raw frame bytes:

- **No `ParseFromString`, no per-tick `datetime.fromtimestamp`, no DB** on the loop thread.
  Offloading only the DB write would leave the protobuf parse and timezone conversion
  inline and F3 would not fully close. Parsing moves to the worker.
- **Hoist `pytz.timezone('Asia/Kolkata')` to module level.** It is currently constructed
  once per tick inside the per-symbol loop (`websocket_ingestor.py:208`), on the exact hot
  path that starves the loop.
- **Set explicit `ping_interval` / `ping_timeout`** on `websockets.connect(wss_url)`
  (operator-approved: belt-and-suspenders). Values pinned in the plan; the intent is a
  keepalive budget comfortably larger than a worst-case enqueue, which is now O(µs).

---

## 4. F4 — short-lived, per-file writes + reader hardening

- **Tick-append opens `ticks` only.** The worker's tick path never opens `candles`,
  removing the manufactured 0.5 s contention (fact 1).
- **Candle writes are chunked and short-lived.** The `Aggregate` command writes candles in
  bounded per-symbol / small-N-symbol chunks, each its own open→write→close — no holder
  outlives ~milliseconds (fact 4).
- **Reader bounded-retry hardening.** `live_buffer_reader()`'s candles open
  (`manager.py:268`) currently propagates on a transient "used by another process"
  collision. Add the **same bounded-retry pattern already committed in
  `ChainSnapshotMarksSource._connect`** (the R1 fix, `nifty_shield_marks.py`): retry a
  small bounded number of times on a transient open failure, raise only after the bound.
  This is the template; readers of the live buffer adopt it.
- **DDL once, not per open.** `live_buffer_writer()` runs `MARKET_TICKS_SCHEMA` and
  `MARKET_CANDLES_SCHEMA` on every entry (`manager.py:240-241`). Under short-lived cycles
  this pays DDL per chunk. Bootstrap the live-buffer schema **once** at worker start.

---

## 5. F1 — connect-then-async-backfill

`_try_connect` reorders:

1. **Start the WS first** so live ticks flow immediately.
2. Run `RecoveryManager` on a **background thread** whose recovered bars are **enqueued**
   to the same worker (`RecoverBars`) rather than written through a direct
   `live_buffer_writer()`. Recovery is currently a 4th direct RW writer of synthetic
   candles; under the invariant it must route through the worker.

Recovery already no-ops when the detected gap is < 2 min (`recovery_manager.py:76`), so a
clean at-open start costs nothing; the async path matters for mid-session restarts with a
real gap.

---

## 6. Correctness notes (no extra guards needed)

- **Synthetic vs real precedence is order-safe both ways.** Recovery writes
  `INSERT OR IGNORE ... is_synthetic=TRUE`; the aggregator writes
  `ON CONFLICT (symbol,timeframe,timestamp) DO UPDATE ... is_synthetic=FALSE`. Real data
  overwrites synthetic; synthetic no-ops over real. Running recovery concurrently with
  live aggregation (both now serialized through the single worker anyway) needs **no
  sequencing guard** — do not add one.
- **In-process serialization already exists.** `_get_thread_lock('live_buffer')`
  serializes all in-process live-buffer opens; the single-writer invariant supersedes the
  need to reason about it for writes, but readers still take it and that is fine.

---

## 7. Testing

Load-bearing here is behavioral correctness of the concurrency seam, not line coverage.

**Unit**
- WS handler enqueues without opening any DB: mock the queue, feed a frame, assert
  `_handle_message` performs no live-buffer open and no parse.
- Worker parses a known protobuf frame → exactly the expected tick row(s) (LTP/LTT/LTQ →
  naive IST).
- Tick-append path opens **`ticks` only** — assert the candles file is never opened on a
  `TickFrame` drain.
- `Aggregate` writes candles in bounded chunks — assert no single open covers the whole
  symbol set.
- Backpressure: filling the queue past bound drops oldest `TickFrame`s and never drops
  `Aggregate`/`RecoverBars`/`Purge`; counter increments.

**Integration**
- **Cross-process reader lands during active writing** (the probe, as a regression test):
  a reader retrying against a stream of short-lived candle writes achieves near-100 %
  success and never raises past the retry bound.
- **Shutdown drain loses zero buffered ticks:** enqueue N ticks, call `stop()`, assert all
  N are persisted.
- **Connect-before-backfill ordering:** WS `start()` is invoked before
  `RecoveryManager.run_recovery`; recovery runs on a background thread.
- **No long hold:** assert no single live-buffer RW open exceeds a small time bound under a
  full-batch aggregate.

**Standing discipline** — deterministic reproducibility of aggregation output (same ticks
→ identical candles) is preserved; the redesign changes *where* writes run, not *what* they
compute.

---

## 8. Blast radius & files

| File | Change |
|---|---|
| `core/database/ingestors/live_buffer_writer.py` | **New** — worker thread + queue + command handlers. |
| `core/database/ingestors/websocket_ingestor.py` | Remove `TickBuffer`; handler enqueues raw frames; hoist tz; set ping params. |
| `core/database/ingestors/db_tick_aggregator.py` | Aggregation invoked by the worker; chunked short-lived candle writes. |
| `core/database/ingestors/recovery_manager.py` | Enqueue recovered bars instead of direct RW write. |
| `core/database/manager.py` | `live_buffer_reader()` bounded retry on candles open; DDL-once bootstrap for the live buffer. |
| `scripts/market_ingestor.py` | Own worker lifecycle; connect-then-async-backfill; post periodic `Aggregate`; route purge through the worker. |
| `tests/database/ingestors/` (or nearest existing home) | New unit + integration tests per §7. |

This is ingestion-core surgery with a broad blast radius; DeepSeek implements from the
plan, Claude reviews.
