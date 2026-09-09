# Duplication Audit — Scripts and Stores

**Date:** 2026-09-04 · **Method:** read-only. No process was running during the audit (verified: zero Python processes). Nothing was written, deleted, or compacted.
**Scope:** the live trading-window path (orchestrator children + Options-Wall + live buffer). Complements — does not restate — `DATABASE_CENSUS_2026-09-03.md`, which measured *footprint*; this measures *duplication*.

---

## 1. Headline

| Question asked | Verdict |
|---|---|
| Are databases duplicating **rows**? | **No.** 653,371 rows across the 8 live-path tables listed in §2, **zero** duplicate keys. Not a repo-wide verdict — `data/mrlc_test/` and `data/nifty_shield/` are active and were not audited. |
| Are databases duplicating **storage**? | **Yes — severely.** 15.9 GB on disk holds **30 MB** of data. One root cause, four stores. |
| Are scripts duplicating **tasks**? | **One real overlap** (two pollers fetch the same Nifty chain every 5 s), one latent, one by-design. |
| Orchestration hygiene | Three dead surfaces found (stale OS task, unexecuted scheduler table, missing fallback store). |

---

## 2. Row duplication — CLEAN

Checked with an explicit `GROUP BY <key> HAVING count(*) > 1`.

> Method note: an initial pass used `count(distinct (a,b))`. On a 2-column tuple DuckDB collapsed this to a single-column distinct and reported a false 562,623 duplicates on the chain store. **The `GROUP BY … HAVING` form below is the reliable one** and is what every number here comes from.

| Store | Table | Rows | Key | Dup groups | Excess rows |
|---|---|--:|---|--:|--:|
| `wall_scan_results` | `scan_results` | 6,310 | ts, underlying, expiry, strike, option_type, structure | 0 | 0 |
| `wall_scan_results` | `session_regime` | 1,193 | trade_date, underlying, ts | 0 | 0 |
| `wall_scan_results` | `oi_baseline` | 4,283 | underlying, trade_date, strike, option_type | 0 | 0 |
| `wall_scan_results` | `trades` | 7 | trade_id | 0 | 0 |
| `wall_chain_snapshots/2026-09-04` | `option_chain_snapshot` | 564,966 | snapshot_ts, underlying, expiry, strike, option_type | 0 | 0 |
| `live_buffer/candles_today` | `candles` | 11,219 | symbol, timeframe, timestamp | 0 | 0 |
| `live_buffer/ticks_today` | `ticks` | 64,353 | symbol, timestamp, price, volume | 0 | 0 |
| `chain_cache` | `option_chain_snapshot` | 340 | snapshot_ts, expiry, strike, option_type | 0 | 0 |

The append-only discipline and the `INSERT OR IGNORE` guards are holding. `purge_synthetic_rows.py` has never run (no `.pre_purge_*` snapshot exists), so these are **not** post-cleanup numbers.

**Retention is also correct.** Both `live_buffer` files contain exactly one date — 2026-09-04, 204 symbols in candles, 3 in ticks. This **corrects §4 of the 09-03 census**, which flagged `ticks_today.duckdb` as *"accumulating across sessions rather than rotating."* It rotates. `_handle_purge` works. The 10 GB has a different cause, below.

---

## 3. Storage duplication — the real defect

Measured by rebuilding each store into a fresh DuckDB (`ATTACH … READ_ONLY` + `CREATE TABLE AS SELECT`) and comparing file sizes. Same rows in, both times.

| Store | On disk | Compacted | Bloat |
|---|--:|--:|--:|
| `live_buffer/ticks_today.duckdb` | 10,083 MB | 0.80 MB † | **>12,000×** |
| `live_buffer/candles_today.duckdb` | 4,266 MB | 0.80 MB † | **>5,000×** |
| `options/wall_scan_results.duckdb` | 836 MB | 7.9 MB | **106×** |
| `options/wall_chain_snapshots/2026-09-04.duckdb` | 721 MB | 20.5 MB | **35×** |
| **Total** | **15.9 GB** | **30 MB** | **~530×** |
| `options/chain_cache.duckdb` *(control)* | 1.7 MB | — | **~1×** |

† **Floor-limited, so treat the two live-buffer multipliers as lower bounds, not precise figures.** Both compacted files are byte-identical at 798,720 = 3 × 256 KiB blocks + header, despite holding different tables with 11,219 vs 64,353 rows. An empty single-column DuckDB is already 274,432 bytes, so 0.80 MB is DuckDB's small-file floor rather than a measurement of these rows. Row counts were verified inside each compacted copy (11,219 and 64,353 — nothing was lost in the rebuild). The honest statement is *"both compact to under 1 MB."*

`pragma database_size` reports `ticks_today` at 38,454 used blocks against 10 free — whatever the internal reason, the file is not carrying reclaimable free space that a reopen would reuse.

### Root cause — isolated experimentally

Every write in the bloated stores opens a **fresh read-write DuckDB connection and closes it immediately** (`core/database/manager.py` `live_ticks_writer` / `live_candles_writer`; `core/options_wall/persistence.py` `_connect_rw`), and every bloated table **carries at least one index**. Closing the last connection forces a full checkpoint, and a checkpoint serialises the whole index.

A 2×2 on an isolated harness — same rows, same batch count, only the index and the connection pattern varied — shows it takes **both** to bloat:

| | close-per-batch | one held connection |
|---|--:|--:|
| **indexed (PK)** | **265.56 MB** | 1.32 MB |
| **unindexed** | 1.32 MB | — |

*1,000 batches of 10 rows.* Only one cell is bad, and it is exactly the production configuration. It scales: 0.27 MB per checkpoint × the ~38,000 flushes a session drives at the 0.05 s queue timeout ≈ the 10 GB `ticks_today`.

**`chain_cache.duckdb` is the control that confirms it.** `chain_poller.py` writes a *fresh* DB per cycle and `os.replace`s it into position (its docstring, constraint §2.1) — so its index is built once per file, never re-serialised. Same 5-second cadence, same data, same session: **1.7 MB, 7 blocks.**

### Why the obvious fix is not available

Holding one write connection open for the session is the cheapest fix and is **blocked**. Tested directly on DuckDB 1.4.3 / Windows: while a read-write connection is held, a second process opening the same file **read-only** fails with `IOException: ... being used by another process` — before *and* after an explicit `CHECKPOINT`; it succeeds only once the writer closes. The open/close pattern is therefore load-bearing for `live_buffer_reader`, `publish_live_fact.py`, preflight, and the dashboard. That leaves the index arm and the checkpoint-count arm.

### Consequences

- ~16 GB/session of avoidable disk churn; `wall_chain_snapshots` writes a fresh ~700 MB file **every trading day** and keeps them.
- This is the mechanism behind the already-recorded operational symptom: *"wall store append locks 3–8 s, readers need ~15 s retry."* Checkpointing an 836 MB file to append one row is why an append holds the write lock for seconds. The bounded retries in `_connect_ro` / `_connect_rw` (30 × 0.5 s) are compensating for this defect, not for normal contention.

### Fix applied (2026-09-04)

Four changes, all on the index/checkpoint-count arms since the connection arm is closed:

1. **Dropped every index on the hot append tables — including the surrogate primary key.** `options_wall_store.init_schema` no longer builds `idx_wall_{underlying,expiry,strike,timestamp}`, and `persistence._SCHEMA` no longer builds `idx_scan_{underlying,ts}`, `idx_regime_underlying`, `idx_trades_underlying`. Both `init_schema` functions now `DROP INDEX IF EXISTS` so existing stores shed them on next open. Verified first that no reader needs them: `latest_snapshot` and `snapshot_timestamps` filter on `underlying_symbol` / `expiry_date` / `MAX(snapshot_timestamp)`, never on `strike_price`, over ≤600 k single-day rows.

   **Removing the secondary indexes alone was not enough** — measured at only 1.1× (93.86 → 82.33 MB over 300 real `append_snapshot` cycles), because `PRIMARY KEY (snapshot_id)` is an ART index like any other and was still being re-serialised on every checkpoint. `snapshot_id` is written by a sequence and **read by nothing** (no query in `core/`, `scripts/`, `flask_app/` or `app_facade/` selects or filters it), so the constraint was pure cost; the column stays, the index goes. That is what actually fixed it. The primary keys on `oi_baseline` (`INSERT OR IGNORE`) and `trades` (identity) are **kept** — load-bearing, small, and written a handful of times a session; measurement below confirms they cost nothing at that write rate.
2. **Time-windowed the live-buffer tick flush.** `live_buffer_writer` accumulates into a pending buffer and writes once per `_TICK_FLUSH_INTERVAL_S = 3.0` (still bounded by `_TICK_COALESCE_MAX`, so bursts flush early). ~38,000 checkpoints/session → ~7,800. The pending buffer is force-flushed before any `Aggregate` — a 1 m bar built while ticks sat unflushed would be written short and `INSERT OR IGNORE` would make that permanent — and drained on shutdown.
3. **Rotation replaces `DELETE` at session start.** `DatabaseManager.rotate_live_buffer` rebuilds each file keeping rows `>= cutoff` and swaps it in; it verifies the retained row count and leaves the original untouched if the counts disagree. The old `DELETE FROM ... WHERE timestamp < cutoff` freed nothing, which is why 4.2 GB of dead space survived into each new session.
4. **`scripts/ops/compact_duckdb_stores.py`** reclaims what is already on disk. Renames the original aside as `<name>.pre_compact_<ts>.duckdb` (a rename, so no extra disk is needed for a 10 GB file) and only swaps after per-table row counts match. Refuses to run while any writer PID or ingestor/poller process is alive, and re-checks immediately before each swap.

### Measured after the fix — real write paths, 300 cycles each

Both figures are per write cycle, which is the unit that scales with session length. The two harnesses ran different workloads (A: 300 chain appends of 192 rows; B: 300 regime writes + 15 scan writes with the `oi_baseline` and `trades` primary keys live in the same file), so compare the per-cycle column, not the totals.

| Store | Before | After |
|---|--:|--:|
| `wall_chain_snapshots` — real `append_snapshot`, 57,600 rows | 313 KB/cycle | **6.2 KB/cycle** |
| `wall_scan_results` — real `write_regime` / `write_scan_results` | ~700 KB/cycle (production: 836 MB over ~1,200 writes) | **6.2 KB/cycle** |

That store B lands at 6.2 KB/cycle *with* the `oi_baseline` (180-row) and `trades` primary keys still present confirms the kept constraints cost nothing at their write rate — the removals were targeted, not indiscriminate.

Both were re-read afterwards through the real readers (`latest_snapshot`, `snapshot_timestamps`, `latest_regime`, `get_oi_baseline`, `regime_river`) — all correct. Extrapolated to a full session, `wall_chain_snapshots` goes from 721 MB/day to roughly 15 MB/day.

**Compaction applied 2026-09-04:** 15.91 GB → 0.04 GB across the four stores, every per-table row count verified, then all stores re-read through the real application readers (771/789/783 snapshot cycles, live regimes and LTPs for all three underlyings, 64,353 ticks, 11,219 candles). Original files retained as `*.pre_compact_20260904_2148*.duckdb` — **they still hold the 15.9 GB until deleted.**

Tests: `tests/database/ingestors/test_live_buffer_rotation.py` (7) covers rotation retention, space reclaim, temp-file cleanup, `Purge` routing, shutdown drain, interval buffering, and the pre-aggregate force-flush. Full suite 658 passed; the one failure (`tests/g1/test_g1_closure_guard.py`) names an unmodified file absent from this diff and is pre-existing on `main`.

---

## 4. Task duplication among scripts

### 4.1 Two pollers fetch the same Nifty chain — REAL

The orchestrator (`scripts/ops/orchestrator.py:67`, `:81`) spawns both:

| | `scripts/nifty_shield_paper/chain_poller.py` | `core/options_wall/poller.py` |
|---|---|---|
| Underlyings | `NSE_INDEX\|Nifty 50` | Nifty 50, Nifty Bank, **BSE** SENSEX |
| Expiries | two nearest weeklies | near weekly |
| Cadence | 5.0 s | 5.0 s |
| Endpoint | `OptionsProvider._fetch_from_upstox` | `OptionsProvider.fetch_option_chain` → same |
| Writes | `chain_cache.duckdb` (overwrite) | `wall_chain_snapshots/{date}.duckdb` (append) |

**The Nifty near-weekly chain is fetched twice every 5 seconds** — confirmed on today's data: `chain_cache` holds expiries 2026-09-08 and 2026-09-15; the wall store holds 771 Nifty cycles on the same near expiry. That is roughly **4,700 redundant calls per session** against a rate-limited endpoint, and two independently-maintained copies of the same chain.

Each poller's separation is individually justified in its own docstring (different consumers, different write patterns, decoupling NiftyShield from the dashboard). What no document addresses is that the *fetch* is duplicated even though the *storage* legitimately differs. The fix is one fetch feeding two sinks, not two fetches — but that couples two deliberately-decoupled components, so it is an operator decision, not a mechanical cleanup.

### 4.2 A third poller exists but is not spawned — LATENT

`core/messaging/options_publisher.py:222` defines `OptionsPoller` — a 5-second loop over indices calling `options_facade.get_option_chain` → the same Upstox endpoint. Its only entry point is `scripts/run_options_engine.py`, which the orchestrator does **not** spawn. Dormant today; starting it by hand during a session would make it a third concurrent fetcher of the same chain.

### 4.3 `download_all_data.py` twice a day — BY DESIGN, not a defect

`scripts/ops/orchestrator.py:314` dispatches it at startup and `core/scheduler/eod_job.py:24` runs it after close. This is deliberate and guarded: `_catchup_due()` day-stamps the morning dispatch (`data/ops/last_catchup.json`) so a mid-session restart cannot re-fire it, and the orchestrator docstring at line 285 states the EOD run is the one that picks up today's bhavcopy. The pipeline nests cleanly — `download_all_data.py:336` is the sole caller of `refresh_all_strategies.py`; there is no third path into the ingests.

---

## 5. Orchestration hygiene — three dead surfaces

1. **Stale Windows Scheduled Task.** `SE3SpreadCollector` is *Enabled* and points at `F:\Nifty\scripts\se3\schedule_spread_collection.py` — **which does not exist.** Last ran 2026-08-07; `NextRunTime` is empty, so it is inert rather than failing nightly. Its store `data/se3/spread_collection.duckdb` is the one the 09-03 census called "near-orphaned"; the census did not know an OS task still referenced it. Delete the task with the store.
2. **A scheduler UI nothing executes.** `flask_app/blueprints/data/routes.py:166`–`208` exposes full CRUD over a `scheduled_jobs` table in `data/_schedule.duckdb`. **No code anywhere reads that table to run a job** — `app_facade/data_facade.py` is the only file that touches it, and only for CRUD. The table is currently empty, so nothing is silently not-running today; but a job created through that UI would be accepted, persisted, and never fire.
3. **A fallback with no store behind it.** `app_facade/options_facade.py:49` points `OptionsProvider` at `data/market_data/options_poller.duckdb`. That file **does not exist**, and every live construction of `OptionsProvider` passes `read_only=True`, which short-circuits both `_init_db` and `_persist_to_duckdb` — so nothing will ever create it. The `/options/` dashboard's API-failure path (`fetch_option_chain` → `get_cached_option_chain`) therefore falls back to a store that cannot be there.

---

## 6. The `ticks` primary key was discarding ticks — FIXED 2026-09-04

`MARKET_TICKS_SCHEMA` declares `PRIMARY KEY (symbol, timestamp)` and `_flush_ticks` writes with `INSERT OR IGNORE`. Tick timestamps come from the feed's `ltt` truncated to whole seconds (`live_buffer_writer._parse`), so **every tick after the first in any given second is silently dropped.**

Today's buffer shows exactly that, with no ambiguity:

| Symbol | Rows | Distinct timestamps |
|---|--:|--:|
| `NSE_INDEX|Nifty 50` | 21,451 | 21,451 |
| `NSE_INDEX|Nifty Bank` | 21,451 | 21,451 |
| `NSE_INDEX|India VIX` | 21,451 | 21,451 |

One row per symbol per second, across a 22,161-second span — a perfect 1:1. That is not what an index feed delivers; it is the shape left behind after de-duplication on a whole-second key.

`db_tick_aggregator._aggregate_one` builds the 1 m bars from this table with `first(price)` / `max` / `min` / `last(price)` / `sum(volume)`. So intra-second highs and lows never reach the bar, and `sum(volume)` would under-count on any instrument with real volume. **The three symbols currently fed are all `NSE_INDEX`, which carry `volume = 0` on every bar anyway** (a standing repo pitfall), so today's impact is confined to intra-minute OHLC extremes. The moment an `NSE_EQ` symbol joins the tick feed, volume becomes materially wrong.

Note this also means the "zero duplicate rows" result in §2 for `ticks` is not evidence of clean ingestion — the PK guaranteed it by construction, whatever the feed sent.

### What the timestamps actually showed

The row counts alone are ambiguous: "feed emits one update per second" and "PK keeps one update per second" produce identical numbers. Two checks separated them.

- **Every one of the 64,353 timestamps lands on a whole second** (zero microsecond component). So Upstox stamps `ltt` at 1-second granularity — the PK was **not** truncating sub-second timestamps.
- **Consecutive-gap distribution is 21,447 gaps of exactly 1 s**, plus three long gaps (52 s, 604 s, 57 s — reconnects). A perfectly regular one-per-second series.

So the discarded rows were **later updates within a second that carried a different price**. The index value moves continuously while `ltt` only advances once a second; `INSERT OR IGNORE` on `(symbol, timestamp)` kept the first and dropped every subsequent move.

### The fix

1. **`MARKET_TICKS_SCHEMA`**: `PRIMARY KEY (symbol, timestamp)` removed; a `seq BIGINT DEFAULT nextval('tick_seq')` column added.
2. **`_flush_ticks`**: `INSERT OR IGNORE` → `INSERT`.
3. **`db_tick_aggregator`**: `first(price ORDER BY timestamp ASC, seq ASC)` / `last(... , seq ASC)`.

   Point 3 is why `seq` exists rather than just deleting the constraint. Once several rows share a timestamp, `first(price ORDER BY timestamp)` and `last(...)` have no defined winner, so a minute's **open and close would have become non-deterministic** — trading correctness for a different defect. `max`/`min` were already order-independent. `seq` restores a total order.
4. **`_drop_unchanged`**: a tick identical to the immediately preceding one for that symbol is suppressed in the writer. Removing the key removed the only thing suppressing repeats, and the feed re-sends current state on every reconnect (three today). An unchanged tick adds no information and would double-count in `sum(volume)`.

**Migration:** old stores are 6-column and lack `seq`. `rotate_live_buffer` and the compaction script now copy the **intersection** of source and destination columns, letting `seq` take its default. Applied to the live store: 64,353 rows preserved, `seq` 1…64,353 all distinct, 4.7 MB → **0.8 MB** (the ART index was the rest), and the real aggregator query verified against it.

**Carried caveat — not solved here.** `volume` is `ltq` (last traded quantity), and summing it across ticks is an approximation of minute volume either way: the old behaviour under-counted by dropping updates, the new one can over-count if the feed reports one trade in two updates. Today this is inert — all three fed symbols are `NSE_INDEX`, which carry `volume = 0` on every bar. It becomes real the moment an `NSE_EQ` symbol joins the tick feed, and reconstructing true minute volume from `ltq` is a separate problem.

Tests: `tests/database/ingestors/test_ticks_same_second.py` (7) — distinct prices in one second all persist, intra-second high/low reach the bar, `seq` ordering is deterministic, identical repeats collapse, a repeat *after* a change is kept, suppression is per-symbol, and a pre-`seq` store migrates through rotation.

---

## 7. Carried forward, not re-derived

Two items already recorded in `CLAUDE.md` remain **unaudited** and were not opened here:

- The futures and options bhavcopy ingests have never been checked for the `.404` permanent-miss-cache pattern that `_may_cache_miss()` fixed in the equity ingest.
- `eod_decision.decide()` still gates the whole EOD chain on the futures feed alone, so a failed equity ingest still yields `success`.

The 09-03 census's delete list (≈9.2 GB of closed-project and archival stores) is a separate, already-scoped decision and was deliberately left untouched by this audit.

---

## 8. Priority

| # | Finding | Severity | State |
|---|---|---|---|
| 1 | 15.9 GB storage bloat from index-checkpointing (§3) | **HIGH** — recurred every session, and caused the 3–8 s append locks | **FIXED** — indexes dropped, flush batched, rotation replaces DELETE, compaction script added |
| 2 | `ticks` PK discards every tick after the first per second (§6) | **HIGH** — corrupted intra-minute OHLC | **FIXED** — PK removed, `seq` added for deterministic open/close, repeats suppressed in the writer, live store migrated |
| 3 | Nifty chain fetched twice per 5 s by two pollers (§4.1) | **MEDIUM** — rate-limit pressure, two sources of truth | **OPEN** — operator decision: one fetch, two sinks |
| 4 | Scheduler UI writes jobs nothing executes (§5.2) | **MEDIUM** — silent-failure shape | **OPEN** — wire an executor or remove the surface |
| 5 | Stale `SE3SpreadCollector` OS task → deleted script (§5.1) | **LOW** — inert | **OPEN** — delete task + store together |
| 6 | `/options/` fallback store cannot exist (§5.3) | **LOW** | **OPEN** |
| 7 | Row duplication (§2) | **NONE** | No action |
