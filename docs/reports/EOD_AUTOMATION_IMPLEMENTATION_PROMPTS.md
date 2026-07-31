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
| **A** | 1–4 — control store, decision logic, Telegram, chain runner | **ISSUED** |
| B | 5–6 — orchestrator, worker daemon | HELD |
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
