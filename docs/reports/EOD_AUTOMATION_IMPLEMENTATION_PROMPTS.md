# EOD Automation — Implementation Prompts

**Program:** EOD Automation Scheduler
**Opened:** 2026-07-31
**Branch:** `feat/eod-automation-scheduler` (branched from `main` @ `963ae64`)
**Design spec:** `docs/superpowers/specs/2026-07-31-eod-automation-scheduler-design.md`
**Implementation plan:** `docs/superpowers/plans/2026-07-31-eod-automation-scheduler.md`

**Role split (standing):** DeepSeek V4 implements from these prompts. Claude writes the
prompts and reviews the delivered work at checkpoints, issuing PASS / NOT PASSED. Claude
does not implement. Prompts for later checkpoints are **HELD** until the previous
checkpoint's review verdict.

| Checkpoint | Tasks | Status |
|---|---|---|
| A | 1–4 — control store, decision logic, Telegram, chain runner | **PASSED** 2026-07-31 (`EOD_AUTOMATION_CHECKPOINT_A_REVIEW.md`) |
| **B** | 5–6 — orchestrator, worker daemon | **ISSUED** |
| C | 7–8 — facade + API, UI tab | HELD |
| D | 9 — end-to-end verification | HELD |

---

## Prompt A — Tasks 1 through 4

### Context

You are implementing the first four tasks of a nightly data-automation feature for a
production algorithmic-trading platform. The four modules in this checkpoint are pure and
independently testable: they have no dependency on the scheduler daemon or Flask, which
come in later checkpoints.

`docs/superpowers/plans/2026-07-31-eod-automation-scheduler.md` is the **authoritative
source**. It contains, for each task, the exact file paths, the complete test code, the
complete implementation code, the command to run, and the expected result. Follow it
literally. Where this prompt and the plan differ, the plan wins — but report the
discrepancy.

### Working agreement

1. Work on branch `feat/eod-automation-scheduler`. Confirm with `git branch --show-current`
   before starting. Do not create additional branches.
2. Implement **Tasks 1, 2, 3, and 4 only**, in that order. **Stop after Task 4.** Do not
   begin Task 5.
3. Follow the TDD cycle exactly as written in each task:
   - Step 1 write the failing test → Step 2 **run it and confirm it fails for the stated
     reason** → Step 3 implement → Step 4 run and confirm it passes → Step 5 commit.
   - Step 2 is not a formality. If a test passes before implementation, or fails for a
     different reason than the plan states, stop and report — the premise is wrong.
4. Commit at the end of each task using the commit message given in the plan. Four tasks →
   four commits.
5. Run tests from repo root `F:\Nifty` with `python -m pytest`.

### Non-negotiable constraints

These come from the design spec and are the reason the design is shaped this way. Do not
"improve" them.

- **The control store is SQLite, never DuckDB.** DuckDB takes an exclusive file lock and
  does not support concurrent multi-process read-write; Flask and the worker both write.
  Market-data reads stay DuckDB, read-only.
- **All subprocess capture uses `encoding="utf-8", errors="replace"`.** Console output in
  this repo contains `—`, `→`, `₹`; the Windows default code page raises
  `UnicodeDecodeError` mid-run.
- **Every subprocess call passes an explicit `timeout`.**
- **Telegram sends plain text — no `parse_mode`.** Tickers containing `_` or `*` return
  HTTP 400 under Markdown and the message is lost silently.
- **Telegram messages truncate to 4096 characters** with an explicit `… truncated` marker.
- **Terminal outcomes** are exactly `success`, `holiday`, `exhausted`, `chain_failed`.
  `retry` is deliberately not terminal.
- Do **not** modify `download_all_data.py`, `refresh_all_strategies.py`,
  `ts_basis_daily_signals.py`, or `ts_basis_daily_options.py`. This feature orchestrates
  them; it does not change them.
- Do **not** reuse or modify the existing `data/_schedule.duckdb` or its `scheduled_jobs`
  table. Nothing has ever executed those rows; repurposing the table would silently change
  the meaning of existing data.
- Do not add dependencies. `sqlite3` is stdlib; `duckdb`, `requests`, and `pytest` are
  already present.

### Repo conventions that apply

- No over-engineering: no error handling, helpers, or abstractions for single-caller paths.
- No docstrings or comments on code you did not change.
- No backwards-compatibility shims.
- Read a file before modifying it.

### Deliverables

Four commits on `feat/eod-automation-scheduler`:

| Task | Creates | Tests |
|---|---|---|
| 1 | `core/scheduler/__init__.py`, `core/scheduler/eod_store.py` | `tests/scheduler/test_eod_store.py` |
| 2 | `core/scheduler/eod_decision.py` | `tests/scheduler/test_eod_decision.py` |
| 3 | `core/scheduler/eod_telegram.py` | `tests/scheduler/test_eod_telegram.py` |
| 4 | `core/scheduler/eod_chain.py` | `tests/scheduler/test_eod_chain.py` |

### Report back

When Task 4 is committed, report:

1. `git log --oneline main..HEAD` — should show 4 commits.
2. Full output of `python -m pytest tests/scheduler/ -v`.
3. The **actual** test count per file. The plan predicts 11 / 10 / 9 / 5. Those are
   predictions, not measurements — a different number is not automatically wrong, but say
   so explicitly rather than letting it pass unremarked.
4. Any place you deviated from the plan, and why.
5. Any test that failed at Step 2 for a reason **other** than the one the plan states.
6. Confirm `python -m pytest tests/ -q` shows no regressions elsewhere in the suite (report
   the summary line; pre-existing unrelated failures are fine — just identify them as
   pre-existing).

Do not report "all tests pass" without pasting the output. The reviewer re-runs everything.

### Explicitly out of scope for Checkpoint A

- Task 5 (`eod_job.py`), Task 6 (`schedule_worker.py`)
- Any change to `app_facade/data_facade.py`, `flask_app/`, or any template
- Any live Telegram send — Task 3 tests the formatters and truncation only; `send_sync` is
  exercised for real in Checkpoint D with the operator's credentials
- Starting any daemon or scheduling anything

---

## Prompt B — Tasks 5 and 6

**Prerequisite:** Checkpoint A PASSED (`docs/reports/EOD_AUTOMATION_CHECKPOINT_A_REVIEW.md`).
Branch `feat/eod-automation-scheduler` is at the reviewed state. Do not revisit Tasks 1–4.

### Context

Checkpoint A delivered four pure modules. This checkpoint wires them into a working job and
puts a daemon around it. After Task 6 the feature is functionally complete except for the
Flask UI — the worker can run, decide, execute the chain, and report.

Two things make this checkpoint riskier than A, and both are addressed by explicit
instructions below:

- **`_default_book()` is the one code path in this feature that unit tests cannot cover.**
  Tests inject `book` via `Deps`. If that function is wrong, nothing fails until 20:00 in
  production, after the chain has already run.
- **The daemon is a state machine over wall-clock time.** Its bugs are the kind that only
  appear at 23:00 on a Friday.

The authoritative source remains
`docs/superpowers/plans/2026-07-31-eod-automation-scheduler.md`. Follow it literally
**except** for the one mandated change in "Required change to the plan" below.

### Working agreement

1. Branch `feat/eod-automation-scheduler`. Confirm with `git branch --show-current`.
2. Implement **Tasks 5 and 6 only**, in order. **Stop after Task 6.** Do not start Task 7.
3. Same TDD cycle as Checkpoint A: write test → **run and confirm it fails for the stated
   reason** → implement → run → commit. A test that passes before implementation is a
   defect in the premise; stop and report.
4. Commit at the end of each task using the plan's commit message. Plus one extra commit
   for the mandated change below — three commits total.
5. Run tests from repo root `F:\Nifty` with `python -m pytest`.

### Required change to the plan — retry spacing

The plan's `is_due()` computes the next attempt from **`last_started + 30 min`**. This is
wrong when an attempt runs long: if attempt 1 starts at 20:00 and takes 45 minutes, the next
attempt is already overdue the instant it finishes, so attempts fire back-to-back with **no
gap at all** — hammering the NSE archive with zero pause. The intent is "wait 30 minutes,
then try again", which means measuring from when the previous attempt **finished**.

Make these three changes:

1. Add to `core/scheduler/eod_store.py`:

```python
    def last_attempt_finished(self, run_date: date) -> datetime | None:
        attempts = self.attempts_today(run_date)
        if not attempts:
            return None
        return datetime.fromisoformat(attempts[-1]["finished_at"])
```

2. Add this test to `tests/scheduler/test_eod_store.py`:

```python
def test_last_attempt_finished_returns_latest_scheduled(store):
    d = date(2026, 7, 31)
    store.record(d, 1, "download", "retry", "")
    store.record(d, 2, "download", "retry", "")
    assert store.last_attempt_finished(d).date() == d
    assert store.last_attempt_finished(d) >= store.last_attempt_started(d)
```

3. In `scripts/schedule_worker.py`, rename the `is_due` parameter `last_started` to
   `last_finished` (semantics only — the body is unchanged), and call it with
   `store.last_attempt_finished(today)` instead of `store.last_attempt_started(today)`.
   The Task 6 tests in the plan pass a bare `datetime` and are unaffected; keep them as
   written but rename the local fixture variables to match the new meaning.

Commit this as a separate commit before Task 6's commit:
`fix: measure EOD retry interval from attempt finish, not start`

`last_attempt_started` stays on `EodStore` — it is still used by the UI in Checkpoint C.

### Mandatory smoke test for `_default_book()` (Task 5)

After Task 5's tests pass, run this **once** and paste the output:

```bash
python -c "from core.scheduler.eod_job import _default_book; t,c = _default_book(); print('target:', t); print('contracts:', len(c)); print(c[0] if c else 'EMPTY')"
```

Expected: a date, a contract count, and a dict whose keys include `ticker`, `direction`,
`opt_type`, `strike`, `settle`, `premium_cost`. If it raises, **do not paper over it** —
report the traceback. Likely causes to check first: `select_book_options`' keyword is
`min_dte`, and `DEFAULT_MIN_DTE` (= 7) must be passed rather than `None`, because the
parameter is typed as a non-optional `int`.

This is not a unit test and must not become one — it touches live stores. It is a one-off
proof that the untested path works.

### Non-negotiable constraints (carried forward, still binding)

- Control store SQLite, never DuckDB.
- All subprocess capture uses `encoding="utf-8", errors="replace"` **and**
  `env={**os.environ, "PYTHONIOENCODING": "utf-8"}` — Checkpoint A proved both halves are
  required.
- Every subprocess call passes an explicit `timeout`.
- Telegram plain text, no `parse_mode`; 4096-char truncation.
- Terminal outcomes are exactly `success`, `holiday`, `exhausted`, `chain_failed`.
  `retry` is not terminal.
- Do not modify `download_all_data.py`, `refresh_all_strategies.py`,
  `ts_basis_daily_signals.py`, or `ts_basis_daily_options.py`.
- Do not reuse or modify `data/_schedule.duckdb` / `scheduled_jobs`.
- No new dependencies.

### Constraints specific to this checkpoint

- **Never run the worker's `main()` loop during implementation or testing.** It is an
  infinite loop that executes real downloads. Test `is_due()` and `acquire_lock()` as pure
  functions only. Starting the daemon is Checkpoint D, under the operator's control.
- **`run_attempt` must not send Telegram messages on the `retry` path.** A retry is a normal,
  expected outcome on a slow-publication evening; notifying on each would produce up to 8
  messages per night. Only `chain`, `holiday`, and `exhausted` notify.
- **The download step's exit code is deliberately ignored.** `download_all_data.py` exits
  non-zero when any sub-ingest fails, which happens routinely (a 404 on a holiday is normal).
  The feed probe is the authority on whether data arrived, not the exit code. Do not "fix"
  this by checking the return code.
- Manual runs use `attempt=0` and must **not** make the date terminal — this is what lets the
  operator hit "Run now" without cancelling the evening's scheduled attempts. Task 1 already
  enforces it (`attempts_today` filters `attempt >= 1`); do not work around it.

### Deliverables

Three commits on `feat/eod-automation-scheduler`:

| Order | Change | Tests |
|---|---|---|
| 1 | `eod_store.last_attempt_finished()` (mandated change) | `tests/scheduler/test_eod_store.py` (+1) |
| 2 | Task 5 — `core/scheduler/eod_job.py` | `tests/scheduler/test_eod_job.py` |
| 3 | Task 6 — `scripts/schedule_worker.py`, `scripts/__init__.py` if absent | `tests/scheduler/test_worker_timing.py` |

### Report back

1. `git log --oneline main..HEAD`.
2. Full output of `python -m pytest tests/scheduler/ -v`.
3. Actual test count per file. Plan predicts 6 for `test_eod_job.py` and 8 for
   `test_worker_timing.py`; store gains 1 (14 total). These are predictions, not targets —
   report actuals and flag any divergence explicitly.
4. **The `_default_book()` smoke-test output, pasted verbatim.**
5. Any deviation from the plan and why. Checkpoint A's deviation was correct and accepted —
   deviations are welcome when justified, but must be reported, never silent.
6. Any Step-2 test that failed for a reason other than the stated one.
7. `python -m pytest tests/ -q` summary line, identifying pre-existing failures as such.
   Baseline at Checkpoint A: `9 failed, 1853 passed, 4 skipped`.
8. Confirm explicitly that you did not start the worker loop.

### Explicitly out of scope for Checkpoint B

- Task 7 (facade/API), Task 8 (UI), Task 9 (verification)
- Any change to `app_facade/`, `flask_app/`, or any template
- Any live Telegram send
- Running the worker daemon or the real chain end to end
- **MINOR-1 from the Checkpoint A review** (index freshness inferred from filenames rather
  than row contents, `eod_decision.py:48-52`). Reviewed, bounded, and deliberately deferred.
  Do not fix it in this checkpoint.
