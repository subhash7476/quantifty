# EOD Automation — Checkpoint A Lead Review

**Reviewed:** 2026-07-31
**Branch:** `feat/eod-automation-scheduler` @ `8fcb3fe` (4 commits above `main` @ `963ae64`)
**Scope:** Tasks 1–4 — control store, decision logic, Telegram formatters, chain runner
**Implementer:** DeepSeek V4 · **Reviewer:** Claude

## Verdict: **PASS**

All four tasks delivered to plan. One deviation, independently reproduced and **justified** —
it fixes a real defect in the plan. No existing file was touched. Checkpoint B may be issued.

---

## 1. Independent verification performed

Nothing below was accepted from the implementer's report; each was re-run by the reviewer.

| # | Check | Method | Result |
|---|---|---|---|
| 1 | 4 commits exist | `git log --oneline main..HEAD` | Confirmed |
| 2 | **Zero existing files modified** | `git diff --diff-filter=M --stat main..HEAD` | **Empty** — 11 pure additions, 735 insertions |
| 3 | Test suite | `python -m pytest tests/scheduler/ -q` re-run | **37 passed** in 5.86s |
| 4 | Deviation justified | Reproduced both variants in a subprocess harness | **Confirmed** — see §2 |
| 5 | `CHAIN_STEPS` paths resolve | Filesystem check of all 3 + download script | All 4 present |
| 6 | `probe_feeds()` against real stores | Executed live (untested by unit tests) | Returns correct dates |
| 7 | `decide()` on real feed data | Executed at 20:00 / 21:00 / futures-fresh | All three branches correct |
| 8 | Non-negotiable constraints | `grep` of the delivered source | All hold — see §3 |

## 2. The deviation — reproduced and accepted

`core/scheduler/eod_chain.py:44` adds `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`.

Reviewer reproduced both variants with a child script printing `carry — basis → ₹100`:

```
PLAN version   (no PYTHONIOENCODING): rc=1  UnicodeEncodeError: 'charmap' codec
                                            can't encode character '→'
DEEPSEEK version (PYTHONIOENCODING) : rc=0
```

**The plan was wrong and the implementer was right.** Parent-side `encoding="utf-8",
errors="replace"` governs only how the parent *decodes* the pipe. The child Python process
encodes to the pipe using the Windows ANSI code page and dies with **`UnicodeEncodeError`
before emitting any bytes**. Both halves are required.

Note the plan's and design spec's stated rationale ("the Windows default code page raises
`UnicodeDecodeError`") named the wrong direction — the real failure is an *encode* error in
the child. The constraint was right; its explanation and its implementation were both
half-complete. `PYTHONIOENCODING` additionally propagates to the chained scripts' own
subprocesses, which matters because `download_all_data.py` itself spawns children.

**Accepted as-is. No change requested.**

## 3. Constraint compliance

| Constraint | Evidence |
|---|---|
| Control store SQLite, never DuckDB | `eod_store.py:9` `import sqlite3`; `grep duckdb` → no match |
| WAL mode | `eod_store.py:21` `PRAGMA journal_mode=WAL` |
| Telegram plain text, no `parse_mode` | Only occurrence is the comment asserting absence |
| 4096-char truncation | `eod_telegram.py:18` `TELEGRAM_LIMIT = 4096` |
| Explicit timeouts everywhere | store `timeout=30`, telegram `timeout=20`, chain `timeout=timeout` |
| utf-8 subprocess capture | `eod_chain.py:42-44` — both halves |
| Orchestrated scripts unmodified | Zero modified files (§1 check 2) |
| `_schedule.duckdb` untouched | Zero modified files; new store is `_eod_automation.sqlite` |

## 4. Test count discrepancy — resolved, reviewer's error

The plan predicted 11 tests for `test_eod_store.py`; actual is 13. The implementer's
explanation is correct and verified: the file contains 10 test functions, one of which is
`@parametrize`d over the 4 members of `TERMINAL_OUTCOMES`, giving 9 + 4 = 13 collected.
**The plan's "11" was simply the reviewer's miscount** — no test was added or removed, and
the plan's test code was used verbatim. Totals reconcile: 13 + 10 + 9 + 5 = 37.

## 5. Findings

### MINOR-1 — index freshness is inferred from filenames, not row contents

`eod_decision.py:48-52` — `_max_index_date()` derives the index feed's latest date from
`*.duckdb` **filename stems**, never opening the files. This is the precise failure mode
`CLAUDE.md` records as a hard-won lesson: *"A gate that tests file existence cannot certify
row existence"* — a 59-session hole once passed all six Gate-A checks because every file was
present at 25/28 rows.

**Bounded impact, which is why this is Minor not Important.** The `index` feed is only
corroborating evidence for *"is today a trading day"*. The gating decision — whether to run
the chain — keys on `feeds["futures"]`, which **is** a row-level `MAX(trade_date)`. So a
present-but-empty index file cannot cause a wrong chain run. Worst case: a false "trading day
confirmed" defers the holiday verdict, costing extra retries until the 23:30 stop.

**Recommendation:** accept for now; if tightened later, have `_max_index_date()` read
`MAX(trade_date)` from the newest file's `candles` table where `symbol = 'NSE_INDEX|Nifty 50'`
rather than trusting the stem. Not a blocker for Checkpoint B.

### CARRY-FORWARD to Checkpoint B (Task 6 review)

`is_due()` computes the next attempt from `last_started + 30 min`. If an attempt's total
runtime exceeds 30 minutes — plausible: `download_all_data.py` alone ran ~4–8 min before the
recent optimization, and the chain adds more — the next attempt becomes due the instant the
previous one returns, collapsing the retry spacing. Confirm this is intended when reviewing
Task 6, or switch to a fixed 20:00/20:30/21:00 slot grid.

## 6. Not covered by this checkpoint

By design, these remain unproven until later checkpoints and must not be assumed working:

- `send_sync()` has never contacted Telegram. Formatters and truncation are tested; delivery
  is Checkpoint D with the operator's credentials.
- `run_chain()` has never executed the real three scripts — only synthetic fixtures.
- No daemon has run; no scheduling has occurred.

## 7. Authorisation

**Checkpoint B (Tasks 5–6: orchestrator + worker daemon) is authorised to be issued.**
