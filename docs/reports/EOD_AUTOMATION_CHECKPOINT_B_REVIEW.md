# EOD Automation — Checkpoint B Lead Review

**Reviewed:** 2026-07-31
**Branch:** `feat/eod-automation-scheduler` @ `b7b54eb`
**Scope:** Tasks 5–6 + mandated retry-spacing fix — orchestrator, worker daemon
**Implementer:** DeepSeek V4 · **Reviewer:** Claude

## Verdict: **PASS**

All three commits delivered to prompt. The mandated retry-spacing change was applied *and*
wired — verified behaviourally, not just structurally. No unrequested deviations. One
**Important** finding raised that must be fixed in Checkpoint C.

---

## 1. Independent verification performed

| # | Check | Method | Result |
|---|---|---|---|
| 1 | 3 commits exist | `git log --oneline main..HEAD` | Confirmed |
| 2 | Only the mandated file modified | `git diff --diff-filter=M --stat d33bc2b..HEAD` | Exactly `eod_store.py` (+6) and its test (+8); all else pure additions |
| 3 | Test suite | `python -m pytest tests/scheduler/ -q` re-run | **52 passed** in 2.19s |
| 4 | Retry fix **wired**, not just present | `grep` of signature + call site | `is_due(now, last_finished, …)` ← `store.last_attempt_finished(today)` |
| 5 | Retry fix **works** | Behavioural simulation | **Confirmed** — see §2 |
| 6 | `retry` path sends no Telegram | Read `eod_job.py:57-59` | Records only; no `deps.send` |
| 7 | Worker loop not started | `ls data/_eod_worker.lock data/_eod_automation.sqlite` | Neither exists |
| 8 | State machine correctness | Read `schedule_worker.py:87-108` | Sound — see §4 |

## 2. The mandated retry fix — behaviourally proven

A store method can exist and still never be reached. Simulated an attempt that starts at
20:00 and runs 45 minutes, probing one minute after it finishes:

```
attempt started 20:00, finished 20:45, probing at 20:46
  OLD started-based  -> due=True    (fires back-to-back, no pause)
  NEW finished-based -> due=False   (waits until 21:15)
```

The defect the prompt described is real, and the fix eliminates it. Attempts are now
guaranteed a genuine 30-minute gap regardless of how long any one of them runs.

## 3. `_default_book()` smoke test — the previously untested path

Output shows a real, live-anchored contract:

```
target: 2026-07-29   contracts: 10
VOLTAS LONG CE strike 1340.0 exp 2026-08-25 settle 47.35 lot 375
premium_cost 17756.25  anchor_source 'live'  screen 'pass'  spread_pct 0.0132
```

Every key `format_options_book` consumes is present (`ticker`, `direction`, `opt_type`,
`expiry`, `strike`, `settle`, `lot_size`, `premium_cost`, `screen`, `screen_reason`).
`anchor_source: 'live'` confirms it reached the live chain and the tradeability screen ran.
**The one path unit tests cannot cover is proven working.**

*Observation, not a defect:* `target` is 2026-07-29 while the futures store holds 2026-07-30
— the options book keys off the latest formation in `ts_facts.duckdb`, which lags when the
daily facts publish has not run. In production the chain runs refresh → signals → options
before the book is read, so it will be current. Confirm during Checkpoint D.

## 4. State machine review (`schedule_worker.py:87-108`)

Correct as written:

- Heartbeat written every tick, before any work.
- Manual run consumes the one-shot trigger and runs with `attempt=0`, so it cannot mark the
  date terminal — the operator can hit "Run now" without cancelling the evening.
- Scheduled branch correctly gated on `is_enabled() AND NOT is_date_terminal(today)`.
- Attempt numbering `len(attempts) + 1` derives from the store, so a worker restart resumes
  the sequence rather than restarting it.
- `except Exception` around the whole tick with `logger.exception` — the loop survives a
  failed attempt instead of dying silently. Appropriate despite the repo's
  no-broad-except convention: a daemon that exits on one bad evening is worse.

## 5. Findings

### IMPORTANT-1 — the UI will report the worker dead while it is busiest (fix in Checkpoint C)

`run_attempt()` is called **synchronously inside the tick loop** (`schedule_worker.py:103`),
so no heartbeat is written for the entire duration of an attempt. The Checkpoint C facade
defines `HEARTBEAT_STALE_SECONDS = 180` (3 minutes).

A normal attempt runs far longer than 3 minutes: `download_all_data.py` alone took ~4–8
minutes before the recent optimization, and the chain adds `refresh_all_strategies` plus two
further scripts. **So during every real run the Automation tab will show the worker as "not
running" (red) — precisely when the operator is most likely to be looking.** A false death
signal also invites starting a second worker, which the lock refuses, compounding confusion.

This is not a Checkpoint B defect: the code matches the plan, and the threshold lives in
Checkpoint C's facade. It must be fixed there. Options, cheapest first:

1. Raise `HEARTBEAT_STALE_SECONDS` above the longest plausible attempt (~2700 s).
   Trade-off: genuine worker death then takes that long to surface.
2. Have the worker record a `busy_since` / current-phase marker before a long call, and let
   the UI render "running — attempt N in progress" rather than judging on heartbeat age.

Option 2 is preferred: it distinguishes *busy* from *dead*, which is the actual question the
UI is trying to answer. This becomes a required change in Prompt C.

### Carry-forward status

- Checkpoint A's **MINOR-1** (index freshness read from filenames) — correctly left
  untouched as instructed. Still deferred.

## 6. Not covered by this checkpoint

- `send_sync()` has still never contacted Telegram.
- `run_chain()` has still never executed the real three scripts.
- The worker `main()` loop has never run — correctly so; Checkpoint D, operator-controlled.

## 7. Regression check

Full suite `9 failed, 1868 passed, 4 skipped` against Checkpoint A's baseline
`9 failed, 1853 passed, 4 skipped` — identical failure set, +15 passing = exactly the 15 new
scheduler tests. No new regressions.

## 8. Authorisation

**Checkpoint C (Tasks 7–8: facade + API, UI tab) is authorised to be issued**, and must
carry the IMPORTANT-1 heartbeat fix as a mandated change.
