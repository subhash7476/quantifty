# Orchestrator "10:01 crash" — diagnosis (2026-08-11)

**Report by:** debugging session, 2026-08-11 ~11:00 IST
**Trigger:** operator: "orchestrator.py crashed at exactly 10:01 am, i had to restart it again."
**Last console line of the failed run (operator-supplied):** `start sequence: timeout:warmup`

---

## TL;DR

1. **It did not crash.** `start_sequence` returned `timeout:warmup`; `_cmd_start` printed that
   line, ran `sup.shutdown()` (tore down the children it had started), and exited `1`. This is
   the orchestrator's designed fail-safe, not an exception.
2. **The ~10:01 event and the 10:49 restart are TWO different failures** with the same disease
   (a live-feed child going cold), reached through different BLOCK checks.
3. **~10:01 = poller stall.** The chain poller's last successful poll was **10:01:17**, then
   silence until the 10:49 restart. Its heartbeat (`chain_poller_heartbeat.json`) stopped
   updating; 60 s later `marks_warm` went False and the warm-up gate could no longer hold GO.
4. **10:49 = VIX permanently cold.** Only **2 VIX bars exist all day (09:57, 09:58)**; every
   later start finds the last VIX bar tens of minutes stale, so `vix_warm` (`bar_age <= 300 s`)
   is False for the entire window → guaranteed `timeout:warmup` → whole stack torn down.
5. **Blocking finding:** the warm-up gate is **unobservable** — steps 5b/7 poll up to 60×
   and log nothing, then emit one `timeout:warmup` that names no check. Root-causing this class
   of failure from logs is archaeology. **The one non-premature fix is instrumentation.**

---

## Evidence

### The exit path (not a crash)
`scripts/ops/orchestrator.py:302-317` — `_cmd_start` wraps `start_sequence` + the supervise
loop in a `try` that catches **only `KeyboardInterrupt`**. On any non-`started` outcome it calls
`sup.shutdown()` and returns 1. `start_sequence` returns `timeout:warmup` from step **5b**
(`:142-147`) or step **7** (`:155-162`) — both require `NOT(marks_warm AND vix_warm)` sustained
for the counted window. No other path yields that string (a warm-stack NO-GO returns
`blocked:preflight`).

### ~10:01 — chain poller stalled
`logs/chain_poller.log`, last lines before the 10:49 restart:
```
2026-08-11 10:01:04,349 - chain_poller - INFO - chain polled: 226 rows @ 2026-08-11
2026-08-11 10:01:11,347 - chain_poller - INFO - chain polled: 226 rows @ 2026-08-11
2026-08-11 10:01:17,828 - chain_poller - INFO - chain polled: 226 rows @ 2026-08-11
   <no further polls until the operator's 10:49 restart>
```
`marks_warm` (`preflight.check_marks`) requires `marks_heartbeat_age_s <= 60 s` off
`chain_poller_heartbeat.json`. Poller frozen at 10:01:17 ⇒ marks cold by ~10:02:17 ⇒ gate
cannot stay GO. **The same stall recurred after the restart:** heartbeat later froze at
**10:52:48**, and poller pid 17036 is dead now.

> Confidence: the poller stall at 10:01:17 is a hard fact. Because the gate logs nothing, we
> cannot prove with 100 % certainty that the tripped BLOCK check at 10:01 was `marks` rather
> than `_ingestor_alive` — but the stall time aligns exactly with the operator's "10:01" and
> with the marks path. Instrumentation (below) removes this ambiguity next time.

### VIX freshness did NOT cause the ~10:01 timeout (arithmetic)
Last VIX bar **09:58:00**; `VIX_BAR_MAX_S = 300`. VIX was fresh until ~10:03 — after the poller
had already stalled. VIX explains the **10:49** failure, not the 10:01 one. Do not merge them.

### 10:49 — VIX permanently cold
`data/live_buffer/candles_today.duckdb`:
```
VIX  min/max/count : (09:57, 09:58, 2)       # only two VIX bars all day
ALL  min/max       : (09:15, 10:48)          # other symbols kept flowing to 10:48
```
The ingestor process was alive and writing *other* candles until 10:48, but **India VIX ticks
stopped landing after 09:58**. Any start after ~10:03 fails `vix_warm` for the whole window.

### Current state (11:03 IST, market open)
No `orchestrator.pid`, no `session.pid`; flask/ingestor/poller/eod pids all dead. **The entire
PAPER stack is down.** Live preflight:
```
[!!] BLOCK marks_warm  marks not warm (rows=226 priceable=182 hb_age=251s)   # poller frozen 10:52:48
[!!] BLOCK live_vix    VIX not flowing (ingestor_alive=False bar_age=3540s)   # ingestor pid dead 10:52:55
VERDICT: NO-GO
```

---

## Root cause

The live-feed children (chain poller; ingestor's VIX write path) **stall or die mid-session**.
Because `marks_warm` and `vix_warm` are **BLOCK** checks, any such stall makes the warm-up gate
unpassable, and the orchestrator's fail-safe response is to **tear the whole stack down and
exit** — which the operator experiences as a crash. Two instances this morning:
poller-stall (10:01) and VIX-cold (10:49).

This is consistent with the documented, in-progress ingestor "writer-worker" instability
(F3/F4; live-buffer reader/writer contention on `candles_today.duckdb`).

---

## Recommended next step — instrument first, then decide (do NOT pre-fix the gate)

**1. Make the warm-up gate observable. — DONE 2026-08-11.** `scripts/ops/orchestrator.py`:
the step-5b and step-7 loops now log `marks_warm`/`vix_warm` each iteration and, at timeout,
a `Deps.gate_status()` string naming the failing BLOCK checks with full detail (e.g.
`marks_warm: marks not warm (rows=226 priceable=182 hb_age=946s); live_vix: VIX not flowing
(ingestor_alive=False bar_age=4235s)`). `gate_status` is a defaulted, injectable Deps field
(no-op in tests); 17/17 `tests/ops/test_orchestrator.py` green. The next `timeout:warmup`
will name the cold feed in the console + log instead of failing silently.

**Deferred design items (raise separately, do not bundle into this fix):**

- **`timeout:warmup` tears down the entire (partly healthy) stack** and forces a full manual
  restart. Reconsider whether a transient cold feed should nuke flask/ingestor/poller.
- **Heavy work in the BLOCK hot loop.** Each warm-up iteration calls `build_context()` 2–3×
  (`_marks_warm`, `_vix_warm`, and step-7 `preflight()` each build separately). Every build runs
  `_feed_fresh()` → `probe_feeds()`: 3 bhavcopy DuckDB opens (incl. the 98M-row
  `stock_options_bhavcopy.duckdb`) + a 3,563-file glob of the 1d index dir — all to feed a
  **WARN-tier** check that has no business in a BLOCK gate. Two effects: (a) `waited += poll_s`
  counts 2.0/iter while wall-clock burns far more, so the "120 s" budget is really several
  minutes; (b) `_vix_bar_age_s` opens `candles_today.duckdb` read-only 2–3×/iter — plausible
  reader/writer contention with the ingestor's VIX writes (cf. commits `5fb89fc`, `3767b27`).
  Hypothesis to test with the instrumentation, not assert.
- **Why do India VIX ticks stop ~09:58 while other symbols continue?** The deeper feed defect;
  belongs to the ingestor writer-worker redesign.

---

---

## Addendum (2026-08-11) — the VIX feed root cause: Upstox "full"-mode subscription cap

"Why do India VIX ticks stop ~09:58" — investigated. **It is not a VIX bug and not a
writer-worker bug.** It is a positional subscription cap in the Upstox V3 WebSocket feed.

### Evidence
- At 09:58 the live feed collapsed from **all 203 subscribed symbols to exactly the first
  42** (`market_universe.json` keys 0–41, all `NSE_EQ`), sustained ~50 min to 10:48.
- All three index symbols stopped together (India VIX, Nifty 50, Nifty Bank — each `n=2`,
  09:57 + 09:58 only), plus every equity at universe position ≥ 42. The first 42 equities
  kept live ticks (`n=94`, bars 09:15 backfill → 10:48).
- The cut is **positional and exact** (contiguous keys 0–41), which rules out the writer's
  drop-oldest queue (temporal, whole multi-symbol frames) and the aggregator
  (`Aggregate(self.symbols)` passes all 203; `_aggregate_one` iterates every symbol). The
  writer's `_parse` has no per-symbol cap. So ticks for keys ≥ 42 simply **stopped arriving**
  in the `ticks` table → no candles built.
- `market_ingestor._load_universe()` returns `symbols + REQUIRED_INDEX_SYMBOLS` deduped —
  so **the 3 required indices are appended LAST** (positions ~200–202). They are always
  outside the surviving first-~42 window ⇒ **VIX is guaranteed to go dark every morning**,
  which is exactly the `live_vix` BLOCK that stops the orchestrator.

### Mechanism
`websocket_ingestor.py` subscribes all 203 keys in a single `{"mode":"full", ...}` message.
Upstox delivers an initial snapshot for all (the 09:57–09:58 burst), then sustains continuous
`full`-mode updates for only ~the first 42 keys. (Exact documented per-connection `full`-mode
instrument limit to be confirmed against Upstox V3 docs; the positional evidence is
conclusive that a cap exists regardless of the exact number.)

### This is NOT covered by the writer-worker redesign
The writer-worker work (F1/F3/F4 — landed in commits `b44466b`, `d4d17b6`, `99582cc`,
`62e53c2`, `3767b27`) fixes event-loop starvation and live-buffer reader/writer contention.
It does nothing about the feed only carrying 42 symbols. This is a **separate, newly-found
defect** in the subscription layer.

### Fix directions (not yet implemented — needs operator decision)
1. **Cheap mitigation (does not fix breadth):** put `REQUIRED_INDEX_SYMBOLS` **first** in the
   subscribed list so VIX/Nifty/BankNifty fall inside the surviving window. Unblocks the
   orchestrator immediately; equities beyond the cap still starve.
2. **Correct fix:** respect Upstox's per-mode limits — subscribe the bulk universe in a
   higher-limit mode (e.g. `ltpc`, which is all the aggregator uses anyway — `_extract_ltp`
   only reads LTP/LTT/LTQ), reserving `full` for the few instruments that truly need depth;
   and/or shard the universe across the allowed subscription budget / multiple connections.
   Confirm the exact V3 mode limits against Upstox docs first.

---

## What this is NOT
- Not an unhandled exception / traceback.
- Not a token, STOP-file, or preflight-WARN problem.
- Not (at 10:01) a VIX-freshness problem — that was the 10:49 failure.
