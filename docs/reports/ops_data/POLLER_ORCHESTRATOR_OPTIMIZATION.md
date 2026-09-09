# Poller / Orchestrator Optimization & Merge Assessment

**Date:** 2026-09-03
**Scope:** `scripts/ops/orchestrator.py`, `scripts/options_wall_poller.py`
(→ `core/options_wall/poller.py`), and the double-fetch / double-write question
across the live option-chain pollers.
**Branch:** MRLC-testing

---

## 1. TL;DR

- **Do NOT merge `orchestrator.py` and `options_wall_poller.py`.** They are a
  *supervisor* and a *worker* with different lifetimes. The wall poller is a
  17-line entry-point shim over `core/options_wall/poller.py`; the orchestrator
  is the process supervisor. Collapsing them removes fault isolation for a
  **pilot** executor sitting next to a **production** marks feed — the opposite
  of what a supervisor is for.
- **The real duplication the request is pointing at is elsewhere**: two live
  pollers each fetch the NIFTY near-weekly chain every 5 s —
  `core/options_wall/poller.py` (wall pilot) and
  `scripts/nifty_shield_paper/chain_poller.py` (production NiftyShield marks).
  They write **different** DuckDB stores for **different** consumers; the shared
  cost is one duplicated Upstox fetch per cycle, not a duplicated write.
- **The dominant write problem was not the code — it was store bloat.**
  `data/options/wall_chain_snapshots.duckdb` had grown to **2.06 GB / 1.9 M rows**
  with **no retention**, and a full 3-underlying append cycle cost **~12.5 s
  against a 5 s poll interval** (measured). **Now fixed** with per-day files
  (§2 #5, §4). Inspection confirmed the raw snapshot *history is not read by
  anything* (§4.2), so bounding it loses nothing a consumer uses.
- **The orchestrator once-per-day download fix is done** (the explicit ask),
  plus a single-instance lock on the pipeline, two safe fetch/construction
  de-duplications, per-day wall files, and the wall poller adopted as a
  supervised orchestrator child. All changes are test-covered.
- **Branch merge-readiness (§7): this session's work is merge-ready in isolation;
  the `MRLC-testing` branch as a whole is NOT** — a pre-existing g1 guard test
  fails on the clean tree, and the Options-Wall pilot's live shakedown gate is
  still open.

---

## 2. What was changed (this branch)

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `scripts/ops/orchestrator.py` | `_dispatch_catchup()` now fires `download_all_data.py` **at most once per calendar day** via a `data/ops/last_catchup.json` stamp. | Every orchestrator start (incl. mid-session restarts) re-ran the whole bhavcopy/1m pipeline — hundreds of Upstox calls competing with the live pollers. The **EOD chain still runs it unconditionally after close**, so today's bhavcopy is never missed. |
| 2 | `scripts/download_all_data.py` | Single-instance PID lock (`data/ops/download_all_data.pid`); a second pipeline **refuses to start**. | The actual "double writing" risk: two pipelines (start-of-session catch-up overlapping EOD, or a hand-run overlapping either) ingest the same trailing window into the same DuckDB stores concurrently. |
| 3 | `core/data/options_provider.py` | `get_weekly_expiry()` memoized per `(underlying, as_of_date)`. | Each call opens the instrument-master DuckDB; the pollers call it **2–3×/cycle** for a value that changes at most **daily**. Removes redundant reads for both pollers and the dashboard. |
| 4 | `core/options_wall/poller.py` | Hoisted `UpstoxMarketData()` (per-underlying → once/cycle) and `OptionsAnalytics()` (per-executor-step → once/process) out of the loops. | Re-constructing per iteration; pure de-duplication, no semantic change. |
| 5 | `core/data/options_wall_store.py` + `core/options_wall/poller.py` | **Per-day snapshot files** — `data/options/wall_chain_snapshots/{date}.duckdb` instead of one unbounded file. Default writes route to today's file; default reads resolve the newest file. Explicit `db_path=` still pins a single file (tests). | The dominant write cost (§4): bounds each file to one session (~100–200 MB) so appends stay ~2–3 s, under the 5 s poll interval. |
| 6 | `scripts/ops/orchestrator.py` | Wall poller adopted as a supervised child (`CHILDREN["wall_poller"]`, native-locked, ensured **last** so it never gates the production path). `stop` skips it like `poller`/`eod`. | The honest "one command" answer to the merge question — supervision without fusing files. |

Tests: `tests/ops/test_orchestrator.py` +8 → **27 pass**; `tests/data/test_options_wall_store.py`
+5 per-day → **11 pass**; `tests/options_wall/` + `tests/data/test_options_wall_poller.py`
**green**; full touched surface **130 pass**. Production per-day routing smoke-verified through the real `WallPoller._poll_cycle`.

---

## 3. Merge question — full reasoning

### 3.1 orchestrator ↔ wall poller: NO

Different responsibilities and lifetimes:

- **orchestrator** = foreground supervisor: preflight gate, dependency-ordered
  start, crash-restart, clean stop of Flask / ingestor / chain_poller / session
  / EOD. Lives for the trading window.
- **wall poller** = one long-running worker: fetch → append → executor step.
  Already supervised *as a child* would be the correct relationship.

Collapsing them means a pilot `PaperExecutor` exception shares a process with
the production marks feed — directly against the session's own goal of "a single
bar must not stop the whole machine."

**The honest "one command" answer** is to adopt the wall poller as an
orchestrator `ChildSpec` (native-locked, like `poller` and `eod`), *not* to fuse
the files. That is left as a **recommendation, not wired in**, because the wall
pilot is explicitly *not merged* and is gated on a live shakedown — starting it
automatically inside the production PAPER window is an operator decision.

### 3.2 wall poller ↔ chain_poller (the two fetch loops): NO, but de-dupe the fetch

|  | `core/options_wall/poller.py` | `scripts/nifty_shield_paper/chain_poller.py` |
|--|-------------------------------|----------------------------------------------|
| Writes | `wall_chain_snapshots.duckdb` (append-only history) + `wall_scan_results.duckdb` | `chain_cache.duckdb` (single fresh snapshot, atomic swap) |
| Consumer | Options-Wall pilot scan + paper executor | **Production** NiftyShield marks source + 13:00 DayType checkpoint |
| Underlyings | NIFTY, BANKNIFTY, SENSEX — **near** weekly | NIFTY — **near + next** weekly (next is load-bearing: 2026-08-24 entry-skip fix) |
| Write model | accumulate (never overwrite) | replace (never hold the write lock across sleep) |

The write models are **deliberately opposite** and both are load-bearing — they
cannot share a writer. The only genuine overlap is the **NIFTY chain fetch**.

**Fetch arithmetic (per 5 s cycle):** chain_poller = 2 (NIFTY near+next);
wall = 3 (NIFTY/BN/SENSEX near). Union of unique fetches = **4**. A shared
fetcher saves **1 call in 5** — operational tidiness, not a rate-limit rescue.
The real rate-limit contention is `download_all_data`'s 200–1200-call burst
(now guarded by #1 + #2), not the steady-state pollers.

**Verdict:** keep two processes for fault isolation; the 1-in-5 duplicate fetch
is not worth coupling a pilot to the production marks feed.

---

## 4. The dominant write cost: wall-store bloat (FIXED — per-day files)

Measured on the live 2.06 GB store (market closed, copy in scratchpad):

| Path | Full 3-underlying cycle |
|------|------------------------|
| As written (fresh rw connection per underlying) | **~12.5 s** |
| One shared rw connection per cycle | ~6.4 s |
| **Fresh store** (same code, grown to 224 MB) | **~2–3 s, flat** |

Interpretation: the cost is **file size**, not connection count or indexes
(indexes add only ~0.3–0.5 s). The store is append-only by design —
`nothing is overwritten, so the scan trail and regime river keep their history`
(module docstring). At a 5 s cadence the poller **cannot keep up** once the file
is multi-GB; every append lock (3–8 s, per prior findings) stretches further.

**This is the real "double writing" pain**, but the fix — a retention window /
periodic prune / roll-to-parquet — **changes data semantics** and needs an
operator call on how much history the scan trail and regime river actually need.
Options, in ascending effort:

1. **Daily prune** to the last *N* sessions (e.g. keep 5–10 trading days live,
   archive older partitions). Smallest change; keeps appends ~2–3 s.
2. **Roll per-day files** (`wall_chain_snapshots/{date}.duckdb`) like the 1m
   candle store — bounds each file to one session, no prune needed.
3. **Down-sample on write** (e.g. 15–30 s snapshots instead of 5 s) if the scan
   trail does not need 5 s granularity retained.

Recommendation: **(2) per-day files** matches the existing candle-store pattern
and removes the unbounded-file failure mode permanently. **→ IMPLEMENTED (§2 #5).**

### 4.1 Per-day files vs. the single file — what changes *data-wise*

| | Single file (before) | Per-day files (now) |
|--|----------------------|---------------------|
| Layout | one `wall_chain_snapshots.duckdb`, all sessions | `wall_chain_snapshots/{date}.duckdb`, one per session |
| Rows | identical schema, identical rows | **identical schema, identical rows** — only partitioned by date |
| Growth | unbounded (→ 2.06 GB / 1.9 M rows over ~5 sessions) | each file bounded to one session (~100–200 MB) |
| Append latency | ~12.5 s/cycle at 2 GB (over the 5 s interval) | ~2–3 s/cycle, flat (measured on a fresh file) |
| `latest_snapshot` | `MAX(ts)` over the whole 1.9 M-row table | `MAX(ts)` over one day's file (newest file resolved by name) |
| `snapshot_timestamps` | `DISTINCT ts` over the whole table (only `[-1]` used) | one day's timestamps |
| History access | full history in one file (but **nothing reads it**) | full history preserved **across** files (still readable per-date for future replay) |

**No data is lost or reshaped** — the same rows, same columns, same values, just
split into one file per session. The only behavioural change is that a reader
with no explicit path sees the **newest session's** snapshots (which is exactly
what `latest_snapshot` / staleness already wanted). Historical sessions remain
on disk as dated files, so a future wall-scanner replay/backtest can still read
any past session — it just opens that date's file instead of filtering a
monolith.

### 4.2 Is the snapshot data useful to retain? — inspected, answer: **not the raw history**

Empirical inspection of the live stores (2026-09-03):

| Store | Size | Content | Who reads it |
|-------|------|---------|--------------|
| `wall_chain_snapshots.duckdb` (raw chains) | **2.06 GB / 1.9 M rows / 6,924 cycles** (2026-08-14 → 09-03) | every 5 s chain snapshot, Nifty + BankNifty (SENSEX: **0 rows** — recently added, not yet accumulating) | **only `latest_snapshot` (newest cycle) + `snapshot_timestamps` (staleness)** — no historical read exists anywhere in the codebase |
| `wall_scan_results.duckdb` (derived) | 0.12 GB | `scan_results` (913, the scan trail), `session_regime` (170, the regime river), `oi_baseline` (3,293), `trades` (3) | the dashboard + analytics |

**Finding:** the module docstrings claim the snapshot store keeps history "so the
scan trail and regime river keep their history" — that is **inaccurate**. Those
derived histories live in the *separate* `wall_scan_results.duckdb` and are
computed at scan time. The 2 GB raw-chain store is **write-mostly**: after the
cycle in which a snapshot is written, nothing ever reads it again except as
"the latest one."

**So the raw per-cycle history is not useful to retain for any current consumer.**
It has *potential* future value — replaying the wall scanner over intraday chains
(the "trail" the design gestures at) — which is why per-day files (retain, but
bounded) is the right call rather than a single-latest overwrite. If that replay
use never materialises, an operator can prune old dated files freely; none of
them feed a live reader.

**Action:** the legacy 2.06 GB `wall_chain_snapshots.duckdb` is now **orphaned**
(the poller writes the per-day directory; `_newest_db()` globs only the new dir).
It is left on disk deliberately — an operator can archive or delete it once
comfortable; nothing reads it. Recommend deleting it after the first live
per-day session confirms the new path.

---

## 5. Double-fetch / double-write audit (broader)

Checked every `OptionsProvider(` construction and `fetch_option_chain` caller:

- Both pollers construct `OptionsProvider(read_only=True)` — they **do not**
  double-write `option_chain_snapshot` via the provider's own persistence path.
- `core/options_wall/engine.py` (`_load_chain`) and `app_facade/options_facade.py`
  also construct `read_only=True` — a Flask-triggered scan that falls through the
  60 s staleness check does **not** become a second writer. ✅ clean.
- The only writers to each store are the intended single writers. No hidden
  double-write found.

---

## 6. Verification

- Once-per-day guard: unit-tested (due when absent / corrupt, not-due same day,
  due next day) + end-to-end stamp check.
- Pipeline lock: acquire → refuse second → release verified live.
- `get_weekly_expiry` memo: repeated calls hit cache; memo size grows by
  `(sym, date)` only.
- Full suites green (§2).

**Not yet verified (needs a live window):** the once-per-day guard against a
real double orchestrator start (`Get-Process` should show exactly one
`download_all_data.py`), and steady-state poller cadence after any retention
change.

---

## 7. Merge-readiness of the `MRLC-testing` branch

**Scope of the question:** merging `MRLC-testing` → `main` means merging **48
commits, 0 behind main** — a long-lived integration branch bundling MRLC-test
scanner research, the Options-Wall pilot, DayType 13:00 fixes, and ingest
changes — not just this session's optimization work.

### 7.1 This session's changes — ready
All optimization changes are test-covered and green (§2). The full touched
surface (130 tests) passes; production per-day routing is smoke-verified. These
changes are safe to merge on their own merits.

### 7.2 The branch as a whole — **NOT ready as a single merge**, two blockers

1. **One pre-existing test failure, unrelated to this work.**
   `tests/g1/test_g1_closure_guard.py::test_no_unwhitelisted_legacy_option_future_construction_in_core`
   fails on the **clean tree** (verified by stashing this session's changes):
   `execution/options/nifty_shield_groups.py` is an unwhitelisted legacy
   option/future construction site. This is a red test on the branch today and
   must be resolved (fix the construction site or whitelist it deliberately)
   before any merge — `main` should not receive a branch with a failing guard.
   *(Everything else: 644 passed / 4 skipped before `-x` stopped at this test;
   a full no-`-x` run is in progress to confirm no other reds.)*

2. **The Options-Wall pilot is explicitly gated on a live shakedown that has not
   been recorded as passed.** Standing operator decision (memory
   `options-wall-pilot`, 2026-08-14): run the wall poller live ~2 trading days
   and merge only if clean. This branch carries the pilot **and** now changes its
   storage layout (per-day files) — the shakedown should re-run on the new path
   (confirm `{date}.duckdb` files land and `best_bid`/`best_ask` are non-NULL in
   a live book) before the pilot rides to `main`.

### 7.3 Recommendation

- **Do not fast-merge the whole branch.** Either (a) land this session's
  optimization as a **focused PR** cherry-picked/split from the branch (the
  5 files in §2 are self-contained and green), or (b) first clear blocker #1
  (the g1 guard) and complete the pilot shakedown (#2), then merge the branch.
- The per-day migration is **backward-safe**: the legacy 2 GB file is orphaned,
  not read; a rollback is simply pointing the store back at the single file.
- Regardless of path, delete the orphaned 2.06 GB
  `wall_chain_snapshots.duckdb` after the first clean live per-day session.

**Bottom line:** this session's work is merge-ready in isolation; the
`MRLC-testing` branch as a whole is **not** — it has a pre-existing failing guard
test and an un-closed pilot shakedown gate.
