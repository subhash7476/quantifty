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
| B | 5–6 — orchestrator, worker daemon | **PASSED** 2026-07-31 (`EOD_AUTOMATION_CHECKPOINT_B_REVIEW.md`) |
| C | 7–8 — facade + API, UI tab | **PASSED** 2026-07-31 (`EOD_AUTOMATION_CHECKPOINT_C_REVIEW.md`) |
| **D** | 9 — end-to-end verification | **ISSUED — operator-driven runbook** |

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

---

## Prompt C — Tasks 7 and 8

**Prerequisite:** Checkpoints A and B PASSED
(`EOD_AUTOMATION_CHECKPOINT_A_REVIEW.md`, `EOD_AUTOMATION_CHECKPOINT_B_REVIEW.md`).
Branch `feat/eod-automation-scheduler` is at the reviewed state. Do not revisit Tasks 1–6
except for the mandated change below.

### Context

Checkpoints A and B built a working job and a daemon around it. Everything so far has been
**new files**. This checkpoint is different, and it is the riskiest of the four:

- **You are editing two large existing files** — `app_facade/data_facade.py` (~700 lines,
  inserting methods *inside* an existing class) and `flask_app/templates/data/index.html`
  (790 lines, inserting into an existing JS object literal).
- **Both failure modes are silent.** A method pasted at the wrong indentation lands at module
  scope instead of on the class, and nothing errors until the endpoint is hit. A JS method
  inserted with a missing or doubled comma breaks the entire `DataUI` object — every tab on
  the page stops working, with only a console error to show for it.

The plan's line references (`~line 487`, `~line 280`, `~line 730`) are **approximate**.
Locate the anchors by content, not by line number, and verify placement afterwards using the
mandatory checks below.

Authoritative source remains
`docs/superpowers/plans/2026-07-31-eod-automation-scheduler.md`, except where overridden
here.

### Required change to the plan — distinguish "busy" from "dead" (Checkpoint B IMPORTANT-1)

`run_attempt()` runs **synchronously inside the worker's tick loop**, so no heartbeat is
written for the whole duration of an attempt. The plan's facade treats a heartbeat older
than 180 s as a dead worker. A real attempt takes far longer than 3 minutes
(`download_all_data.py` alone ran 4–8 minutes, plus three chain scripts), so **the UI would
show the worker "not running" during every real run** — exactly when the operator is looking,
and an invitation to start a second worker that the lock will then refuse.

Fix it by having the worker declare that it is busy. Apply all four parts.

**1. `core/scheduler/eod_store.py`** — add two columns to the `eod_automation` CREATE TABLE:

```sql
                    busy_since       TEXT,
                    busy_phase       TEXT
```

and add two methods:

```python
    def set_busy(self, phase: str | None) -> None:
        with self._conn() as con:
            if phase is None:
                con.execute("UPDATE eod_automation SET busy_since=NULL, busy_phase=NULL WHERE id=1")
            else:
                con.execute("UPDATE eod_automation SET busy_since=?, busy_phase=? WHERE id=1",
                            [datetime.now().isoformat(), phase])

    def get_busy(self) -> tuple[str | None, str | None]:
        with self._conn() as con:
            row = con.execute("SELECT busy_since, busy_phase FROM eod_automation WHERE id=1").fetchone()
            return row[0], row[1]
```

There is **no migration path and none is needed** — no `data/_eod_automation.sqlite` exists
yet. If one appeared during your testing, delete it before running.

**2. Add to `tests/scheduler/test_eod_store.py`:**

```python
def test_busy_defaults_clear_and_round_trips(store):
    assert store.get_busy() == (None, None)
    store.set_busy("attempt 2")
    since, phase = store.get_busy()
    assert phase == "attempt 2"
    assert datetime.fromisoformat(since)
    store.set_busy(None)
    assert store.get_busy() == (None, None)
```

**3. `scripts/schedule_worker.py`** — wrap **both** `run_attempt` call sites so the marker is
always cleared, including on failure:

```python
                store.set_busy("manual run")
                try:
                    outcome = run_attempt(store, today, 0, now)
                finally:
                    store.set_busy(None)
```

and, in the scheduled branch:

```python
                    store.set_busy(f"attempt {n}")
                    try:
                        outcome = run_attempt(store, today, n, now)
                    finally:
                        store.set_busy(None)
```

**4. Task 7's `get_eod_status`** — use this instead of the plan's version:

```python
    HEARTBEAT_STALE_SECONDS = 180
    BUSY_MAX_SECONDS = 5400  # upper bound on one attempt; a crash mid-attempt ages out

    def get_eod_status(self) -> dict:
        from datetime import date as _date

        from core.scheduler.eod_decision import MAX_ATTEMPTS

        store = self._eod_store
        heartbeat, pid = store.get_heartbeat()
        busy_since, busy_phase = store.get_busy()
        now = datetime.now()

        fresh = False
        if heartbeat:
            fresh = (now - datetime.fromisoformat(heartbeat)).total_seconds() <= self.HEARTBEAT_STALE_SECONDS
        busy = False
        if busy_since:
            busy = (now - datetime.fromisoformat(busy_since)).total_seconds() <= self.BUSY_MAX_SECONDS

        return {
            "enabled": store.is_enabled(),
            "worker_alive": fresh or busy,
            "worker_busy": busy,
            "busy_phase": busy_phase if busy else None,
            "worker_pid": pid,
            "heartbeat": heartbeat,
            "last_run": store.latest_run(),
            "attempts_today": len(store.attempts_today(_date.today())),
            "max_attempts": MAX_ATTEMPTS,
        }
```

**5. Add to `tests/scheduler/test_eod_facade.py`:**

```python
def test_busy_worker_counts_as_alive_despite_stale_heartbeat(facade):
    store = EodStore(facade._eod_store_path)
    store.heartbeat(999)
    store.set_busy("attempt 1")
    stale = (datetime.now() - timedelta(minutes=10)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET worker_heartbeat=? WHERE id=1", [stale])
    con.commit()
    con.close()
    st = facade.get_eod_status()
    assert st["worker_alive"] is True
    assert st["worker_busy"] is True
    assert st["busy_phase"] == "attempt 1"


def test_stale_busy_marker_ages_out(facade):
    store = EodStore(facade._eod_store_path)
    store.set_busy("attempt 1")
    ancient = (datetime.now() - timedelta(hours=3)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET busy_since=? WHERE id=1", [ancient])
    con.commit()
    con.close()
    assert facade.get_eod_status()["worker_alive"] is False
```

**6. Task 8's `_loadEod`** — render busy state. Replace the plan's `worker` expression with:

```javascript
        const worker = s.worker_busy
            ? `<span class="text-amber-400">running — ${s.busy_phase} in progress</span> (pid ${s.worker_pid})`
            : s.worker_alive
            ? `<span class="text-emerald-400">running</span> (pid ${s.worker_pid})`
            : `<span class="text-red-400">not running</span> — start it with <code>python scripts/schedule_worker.py</code>`;
```

Commit parts 1–3 as their own commit before Task 7:
`fix: distinguish a busy EOD worker from a dead one`

### Working agreement

1. Branch `feat/eod-automation-scheduler`. Confirm with `git branch --show-current`.
2. Implement the mandated change, then **Tasks 7 and 8 only**. **Stop after Task 8.**
   Do not start Task 9.
3. Same TDD cycle: write test → run and confirm it fails for the stated reason → implement →
   run → commit. Task 8 is UI and has no unit test; its gate is the browser check below.
4. Three commits total.
5. Read both files you are modifying **before** editing them.

### Mandatory placement verification

Run these after Task 7 and paste the output. They exist because a mis-indented paste is
invisible until runtime.

```bash
python -c "from app_facade.data_facade import DataFacade; print('on class:', all(hasattr(DataFacade, m) for m in ['get_eod_status','set_eod_enabled','trigger_eod_run_now']))"
```
Expected `on class: True`. If it prints `False`, the methods landed at module scope — fix the
indentation.

```bash
python -c "import flask_app.blueprints.data.routes as r; print('view functions:', [n for n in ('eod_status','eod_toggle','eod_run_now') if hasattr(r, n)])"
```
Expected all three names listed. This proves the module imports cleanly and the decorated
view functions exist — a syntax error or a bad decorator shows up here rather than at runtime.

Then confirm the routes are actually reachable: start Flask and request
`GET /data/api/eod/status`. A **302 redirect or 401** from `@login_required` is a **pass** —
it proves the rule is registered. A **404 is a failure**. Report the status code you saw.

After Task 8, confirm the template edits landed:

```bash
grep -c "tab-content-automation\|eod-toggle\|eod-status\|_loadEod" flask_app/templates/data/index.html
```
Expected: at least 4.

### Constraints (carried forward, still binding)

- Control store SQLite, never DuckDB.
- Subprocess capture keeps both halves: `encoding="utf-8", errors="replace"` **and**
  `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`.
- Telegram plain text, no `parse_mode`; 4096-char truncation.
- Terminal outcomes exactly `success`, `holiday`, `exhausted`, `chain_failed`.
- Do not modify the four orchestrated scripts.
- Do not reuse or modify `data/_schedule.duckdb` / `scheduled_jobs`.
- No new dependencies.
- **Do not start the worker's `main()` loop.** Task 8's browser check requires the worker
  running to show a live pid — that step is **deferred to Checkpoint D**. For Task 8, verify
  the "not running" state renders correctly and the toggle persists across a page reload;
  that is sufficient.
- Match the surrounding style in both edited files. The template uses Tailwind utility
  classes and an object-literal `DataUI`; the facade uses 4-space indentation inside the
  class. Do not reformat surrounding code.

### Deliverables

| Order | Change | Tests |
|---|---|---|
| 1 | Busy/dead marker — `eod_store.py`, `schedule_worker.py` | `test_eod_store.py` (+1) |
| 2 | Task 7 — facade methods + 3 endpoints | `test_eod_facade.py` (6 + 2 = 8) |
| 3 | Task 8 — Automation tab | browser check |

### Report back

1. `git log --oneline main..HEAD`.
2. Full output of `python -m pytest tests/scheduler/ -v`.
3. Actual test count per file. Prediction: store 15, facade 8, total 61. Predictions, not
   targets — report actuals and flag divergence.
4. **Both placement-verification outputs, pasted verbatim** (facade `on class:` line, and the
   route check with the status code you observed).
5. The template `grep -c` count.
6. What you saw in the browser on the Automation tab: does it render, does the toggle persist
   across a reload, does it show "not running" in red.
7. Any deviation and why. Deviations are welcome when justified — Checkpoint A's was correct
   and accepted — but must be reported, never silent.
8. `python -m pytest tests/ -q` summary line. Baseline: `9 failed, 1868 passed, 4 skipped`.
9. Confirm you did not start the worker loop.

### Explicitly out of scope for Checkpoint C

- Task 9 (end-to-end verification)
- Any live Telegram send
- Running the worker daemon or the real chain
- **MINOR-1** (index freshness from filenames) — still deferred, do not fix
- Any change to `download_all_data.py`, `refresh_all_strategies.py`,
  `ts_basis_daily_signals.py`, `ts_basis_daily_options.py`

---

## Prompt D — Task 9: end-to-end verification (OPERATOR RUNBOOK)

**Prerequisite:** Checkpoints A, B, C all PASSED. Implementation is complete; 61 scheduler
tests green.

**This checkpoint is executed by the operator, not by DeepSeek.** It requires Telegram
credentials, starts a daemon that performs real downloads, and includes a visual browser check
no automated client can make. Claude does not handle credentials and will not run these steps.

Work through the steps in order. **Each step states what you should see.** If what you see
does not match, stop and check §Troubleshooting before continuing — a mismatch early makes
everything after it meaningless.

### Before you start

```bash
git branch --show-current          # expect: feat/eod-automation-scheduler
python -m pytest tests/scheduler/ -q   # expect: 61 passed
ls data/_eod_worker.lock data/_eod_automation.sqlite   # expect: neither exists
```

If a lock or store file exists from earlier experimentation, delete both before starting —
the schema has no migration path and a stale lock will block the worker.

**Timing note:** today is Friday. If you leave the toggle **Enabled**, the job fires tonight
at 20:00 for real. Leave it **Disabled** until this runbook passes; step 8 covers turning it on
deliberately.

---

### Step 1 — Set credentials (operator only)

PowerShell:

```
$env:TELEGRAM_TOKEN="<your bot token>"
$env:TELEGRAM_CHAT_ID="<your chat id>"
```

**Everything else in this runbook must be started from this same shell**, because the worker
inherits these variables from its parent process. A worker launched from a different terminal
will silently fail to send — `send_sync` logs a warning and returns `False`, it does not crash.

Do not commit these values, do not paste them into a file, and do not paste them back to
Claude.

### Step 2 — Prove Telegram delivery in isolation

```bash
python -c "from core.scheduler.eod_telegram import send_sync; print(send_sync('EOD automation test message'))"
```

**Expect:** prints `True`, and the message arrives on your phone.

**Do not continue past a `False`.** Every later step depends on delivery working; debugging it
inside a full run is far harder. See §Troubleshooting.

### Step 3 — Start the worker

In the same shell:

```bash
python scripts/schedule_worker.py
```

**Expect** two log lines immediately:

```
EOD worker started (pid NNNNN), local UTC offset 5:30:00
Fire window 20:00-23:30 Mon-Fri, retry 30min, max 8 attempts
```

Confirm the **UTC offset reads 5:30:00** — this is the one place a timezone misconfiguration
would surface, and it would otherwise shift the whole schedule silently. Leave this window
running; it ticks once a minute.

### Step 4 — Browser check (closes the Checkpoint C evidence gap)

In a **second** terminal: `python scripts/run_flask.py`
Open `http://127.0.0.1:5000/data/` → **Automation** tab.

**Expect:**
- The panel renders — heading, description, "Run now" and toggle buttons, status lines.
- Worker shows **green "running" with the pid** from step 3 (within 60 s of the worker start).
- Toggle reads **Disabled**.

Click the toggle to **Enabled**, reload the page, confirm it still reads Enabled — then click
it back to **Disabled** for now.

This is the first time the tab has rendered in a real browser. Look at it properly: layout,
alignment, whether the status lines read sensibly. Report anything that looks wrong even if it
functions.

### Step 5 — Manual run

Click **Run now**.

**Expect within ~60 s**, in the worker terminal:

```
Manual run requested — running one attempt (attempt=0)
```

then a `download_all_data.py` run (several minutes), then one of:

| Situation | Worker log | Telegram |
|---|---|---|
| Data arrived | `Manual run outcome: success` | **2 messages** — download summary, then the options book |
| No data, at/after 21:00 | `Manual run outcome: holiday` | **1 message** — EOD STOPPED |
| No data, before 21:00 | `Manual run outcome: retry` | **none — this is correct** |
| A chain script failed | `Manual run outcome: chain_failed` | **1 message** with the failing step and stderr tail |

> **Important, and the most likely thing to confuse you:** a `retry` outcome sends **no
> Telegram message at all**. That is deliberate — on a slow-publication evening the scheduled
> job can retry up to 8 times, and notifying each would mean 8 messages a night. If you click
> Run now before 21:00 on a day whose data has not published, you will correctly see *nothing*
> on your phone. Check the worker log and the tab's "Last run" line instead. This is not a bug.

**While the run is in progress**, refresh the Automation tab. It should show amber
**"running — manual run in progress"**. That is Checkpoint B's IMPORTANT-1 fix working; if it
instead shows red "not running" during the run, report it.

### Step 6 — Confirm the manual run did not consume the evening

```bash
python -c "import sqlite3;print(sqlite3.connect('data/_eod_automation.sqlite').execute('SELECT run_date,attempt,outcome,detail FROM eod_run_log ORDER BY started_at DESC LIMIT 5').fetchall())"
```

**Expect:** the newest row has **`attempt = 0`**.

That is what makes a manual run non-terminal — the scheduled attempts for tonight are still
free to run. If it shows `attempt = 1`, stop and report: the manual path is wrongly consuming
scheduled attempts.

### Step 7 — Single-instance lock

In a **third** terminal: `python scripts/schedule_worker.py`

**Expect:** it exits immediately with

```
Another worker is already running (see ...\data\_eod_worker.lock). Exiting.
```

Then confirm the **first** worker is still alive and ticking. (This was checked in review
because on some Python builds a liveness probe can terminate the very process it is testing;
it does not on this build, but confirm it directly here.)

### Step 8 — Arm it

Only once steps 1–7 all matched: on the Automation tab, set the toggle to **Enabled** and
leave the worker running.

The job will fire at **20:00** on the next weekday. On a normal evening you should receive two
messages. Nothing further is required from you.

### Step 9 — Report back to Claude

Paste back:

1. Step 2's output (`True` / `False`).
2. The worker's two startup lines, **including the UTC offset**.
3. What the Automation tab looked like — and anything visually off.
4. Step 5: the outcome line, which of the four situations occurred, and the Telegram messages
   received (paste their text).
5. Whether the amber busy state appeared during the run.
6. Step 6's `eod_run_log` rows.
7. Step 7's lock message.
8. Anything that did not match expectations.

Claude will write `docs/reports/EOD_AUTOMATION_VERIFICATION.md` from that and commit it,
closing the program. **Do not paste your token or chat id.**

---

### Troubleshooting

**Step 2 printed `False`.**
The log line above it says why. Most likely: the variables are not set *in this shell* — check
with `echo $env:TELEGRAM_TOKEN`. Otherwise: HTTP 401 means a bad token; HTTP 400 usually means
a bad chat id. Note messages send as plain text by design, so a ticker containing `_` cannot
be the cause.

**Tab shows "not running" but the worker terminal is alive.**
Give it 60 seconds — the heartbeat is written once per tick. If it persists, the worker is
probably writing to a different store than Flask is reading; confirm both were started from
`F:\Nifty` and that `data/_eod_automation.sqlite` exists.

**Tab shows "not running" *during* a long run.**
That is the defect Checkpoint C fixed. Report it — it means the busy marker is not being
written.

**Worker refuses to start with "Another worker is already running" but none is.**
A stale lock from a killed process. Delete `data/_eod_worker.lock` and start again.

**Run now produced no Telegram message and no obvious error.**
Almost certainly the `retry` outcome — see the callout in step 5. Confirm via the worker log
and the `eod_run_log` query in step 6.

**The chain failed.**
The Telegram message names the failing step and the last 20 stderr lines. `corp-actions` inside
`download_all_data.py` is *not* a chain step and its failure does not stop the chain — the feed
probe, not the exit code, decides whether data arrived.

### Kill switch

- **Stop tonight's run:** set the toggle to **Disabled** on the Automation tab. Takes effect
  within 60 seconds; no restart needed.
- **Stop the worker entirely:** Ctrl+C in its terminal, then delete `data/_eod_worker.lock`.
- **Full reset:** stop the worker, delete both `data/_eod_worker.lock` and
  `data/_eod_automation.sqlite`. This clears all run history and returns the toggle to
  Disabled. It touches no market data.
