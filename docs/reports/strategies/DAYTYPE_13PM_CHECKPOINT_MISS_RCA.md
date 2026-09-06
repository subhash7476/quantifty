# DayType 13:00 Checkpoint — Root-Cause Analysis and Fix

**Date:** 2026-09-02 · **Branch:** MRLC-testing · **Sessions affected:** 2026-08-31, 2026-09-01, 2026-09-02

## 1. Summary

Three consecutive sessions produced no 13:00 DayType fact. They reported **three different
messages**, which is why the previous two fix attempts (retry-budget increases) did not stop the
bleeding — each round fixed the message it saw, not the shared defect underneath.

| Session | Journalled reason | Actual mechanism |
|---|---|---|
| 2026-08-31 | `no 13pm checkpoint produced` (×11) | Stack started 11:39 — no local source held the 09:15 morning |
| 2026-09-01 | `no 13pm checkpoint produced`, then `no India VIX at 13:00` (×10) | Stack started 12:03 — same coverage gap; buffer write-lock on top |
| 2026-09-02 | `insufficient bars up to 13:00` (×11) | Partial per-day store shadowed a complete live buffer |

There are **two causes**, not three.

## 2. Cause A — a source that does not cover 13:00 was accepted or not fallen back from

`compute_13pm_state` needs **226 bars** (`n = min(len(nf), len(bn), TARGET_BAR + 1)`, and the
engine emits `checkpoint == '13pm'` only at bar index `CHECKPOINT_BARS['13pm'] = 225`). The source
gate used `MIN_BARS = 100`. **The two numbers disagreed**, and everything in the 100–225 gap fell
through the crack:

- A frame of 100–225 bars passes the gate, then silently fails three call-frames later as the
  opaque `no 13pm checkpoint produced` — **2026-08-31 and 2026-09-01**.
- Worse, this was a live near-miss for a *silently wrong fact*: had the ingest run at 11:30 rather
  than 09:58 on 2026-09-02, the per-day file would have carried ~135 bars, cleared `MIN_BARS`, and
  published a row stamped `checkpoint='13pm'` computed from a window truncated at 11:29.

`_today_bars` also documented a per-day-store → live-buffer fallback that it did not implement:

```python
if db_path.exists():
    df = _read_candles(db_path, symbol)
    if df is not None:
        return _session_bars_from_df(df)   # returns None; live buffer never tried
```

The fallback fired only when the *read failed*, never when the data was insufficient.

## 3. Cause B — the EOD per-date store was poisoned mid-session

`download_all_data.py` passes `--persist-today` (commits `0ae796e` / `d8e3486`, both landed
2026-09-02). A run at **09:51–09:58** wrote a **43-bar 09:15..09:57** snapshot to
`data/market_data/nse/candles/1m/2026-09-02.duckdb`.

Every consumer treats *"the file for date D exists"* as *"date D is complete."* That assumption
was silently invalidated. Combined with Cause A's missing fallback, the 43-bar file shadowed a live
buffer that held all 226 bars — verified: `NSE_INDEX|Nifty 50`, 226 bars, 09:15 → 13:00.

## 4. Fixes

**`scripts/daytype/publish_live_fact.py`** — coverage-aware ordered source ladder.
Coverage and the 226-bar requirement are now the *same* number, checked once at source selection.
A source short of 13:00 is rejected and the ladder continues; not-ready now names every source and
its coverage in one line instead of a downstream symptom.

**`scripts/fetch_upstox_historical.py`** — `persist_today_to_historical` gated on `_session_closed()`
(post-market close, or a non-trading day). Rows are upserted (`ON CONFLICT DO UPDATE`), so skipping
mid-session loses nothing — the post-close run writes the full session to the same file. Today's
43-bar file therefore **self-heals tonight**; no deletion needed.

## 5. Verification

- Two new regression tests, each pinned to a real session: partial-store fallback, and
  short-source rejection. Both failed before the fix; test 2 reproduced 2026-08-31's exact
  `no 13pm checkpoint produced` message.
- `tests/daytype/ + test_publish_hook_live_dry_run.py + tests/nifty_shield_paper/` — **64 passed**.
- **End-to-end on real production data**: `publish_live_fact.py --date 2026-09-02` against a
  scratch DB now rejects the 43-bar per-day file and publishes from the live buffer —
  `Choppy conf=0.525 vix_at_checkpoint=11.65`. This is the exact computation that failed at 13:00.

## 6. What this does NOT fix — an ops finding

**2026-08-31 and 2026-09-01 were caused by starting the stack at 11:39 and 12:03.** No code change
in the publisher can manufacture bars that were never ingested. Those two misses are an operating
matter: start the stack before 09:15, or commission a deliberate backfill path with its own token
precheck (on 2026-08-31 the ingestor logged `Fresh Upstox token required` at start). Upstox *had*
the full session both days — but that was established at 21:26 that evening, which is not evidence
a fetch at 13:01 would have authenticated. Post-fix, those sessions would still miss, but would say
so in one line naming the short source.

The Sep-1 retry-budget fix (40 × 0.5 s) is deployed in today's running process but **never fired
today** — deployed and unexercised, not validated.

## 7. Flagged, not fixed

The ingestor's `RecoveryManager` backfill runs in a daemon thread whose only failure path is
`logger.warning` and whose success path logs nothing. On 2026-08-31 it left the buffer short of 226
bars and said nothing either way. This is the repo's own pitfall — *"a freshness value that is
printed but never asserted is documentation, not a control"* — in a new place.
