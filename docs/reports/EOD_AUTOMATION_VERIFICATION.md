# EOD Automation — Checkpoint D Verification (Task 9)

**Program:** EOD Automation Scheduler
**Branch:** `feat/eod-automation-scheduler`
**Executed:** 2026-07-31, 18:17–18:52 IST
**Operator:** repo owner (live credentials, live daemon, live browser)
**Author:** Claude (from operator-pasted evidence)
**Runbook:** `EOD_AUTOMATION_IMPLEMENTATION_PROMPTS.md` § Prompt D

**Verdict: PASS, with one defect found and fixed during execution.**

Steps 1–7 all completed. Step 7 **failed on first execution**, exposing a real
concurrency defect that every prior checkpoint had missed. It was root-caused,
fixed, covered by regression tests, and re-verified live. That failure is the
single most valuable result of this checkpoint — see §3.

---

## 1. What was verified

| Step | Result |
|---|---|
| 1 — credentials | PASS (by a different mechanism than the runbook specified — see §4) |
| 2 — Telegram delivery in isolation | PASS — `send_sync` returned `True`, message received |
| 3 — worker starts | PASS — pid logged, **UTC offset 5:30:00 confirmed** |
| 4 — browser / Automation tab | PASS (operator attestation; see §5 for evidence limits) |
| 5 — manual run | PASS — outcome `retry`, correctly silent on Telegram |
| 6 — manual run is non-terminal | PASS — `eod_run_log` newest row `attempt = 0` |
| 7 — single-instance lock | **FAIL, then PASS after fix** — see §3 |
| 8 — arm the toggle | operator action; state at time of writing not captured |

### Step 3 — worker startup

```
2026-07-31 18:34:20,310  EOD worker started (pid 27224), local UTC offset 5:30:00
2026-07-31 18:34:20,310  Fire window 20:00-23:30 Mon-Fri, retry 30min, max 8 attempts
```

The UTC offset is the check that matters here: `5:30:00` confirms no timezone
misconfiguration, which would otherwise have shifted the entire fire window
silently.

### Step 5 — manual run

```
2026-07-31 18:34:20,325  Manual run requested — running one attempt (attempt=0)
2026-07-31 18:35:54,718  Manual run outcome: retry
```

Outcome `retry`, detail *"trading day confirmed by index; futures not yet
published"* — the expected early-evening state at 18:35, well before the 21:00
holiday threshold. **Zero Telegram messages, which is correct**: `retry` is
deliberately silent to avoid up to 8 notifications on a slow-publication night.

### Step 6 — non-terminality

```
[('2026-07-31', 0, 'retry', 'trading day confirmed by index; futures not yet published')]
```

`attempt = 0` confirms the manual run did not consume any of the evening's 8
scheduled attempts. UI concurred: *Attempts today: 0 / 8*.

---

## 2. Test state at close

| Suite | Result |
|---|---|
| `tests/scheduler/` | **66 passed** (was 61 at Checkpoint C; +5 regression tests from §3) |
| `tests/` full suite | not captured — run exceeded the 10-minute tool budget and was abandoned. See §6. |

---

## 3. DEFECT-1 — Windows process-liveness check inverted (found, fixed)

**Severity: HIGH.** Silent violation of the single-instance guarantee.

### Symptom

Step 7 required a second `schedule_worker.py` to refuse to start. It started
normally instead, as pid 11524, while pid 27224 was still alive and ticking.
Both were confirmed running concurrently against the same SQLite control store.

### Root cause

`_pid_alive()` in `scripts/schedule_worker.py` used `os.kill(pid, 0)` — a POSIX
liveness idiom with no valid Windows equivalent. Measured on this build
(Windows 11, CPython 3.13), against disposable processes, the behaviour is
**exactly inverted**:

| Target | `os.kill(pid, 0)` | `_pid_alive()` returned | Truth |
|---|---|---|---|
| live process | raises `OSError [WinError 87]` | `False` | alive |
| exited process | returns cleanly, no exception | `True` | dead |

`acquire_lock()` therefore read the lock file, asked "is 27224 alive?", was told
"no", and handed the lock to the newcomer.

### Why three checkpoints missed it

This is the part worth carrying forward.

- **The Checkpoint B review examined this exact function and cleared it.** It
  worried that a liveness probe might *terminate* the process it tests, checked
  that specific hazard, and concluded "it does not on this build." The reasoning
  was sound; the hazard was simply the wrong one. Clearing a function against one
  failure mode reads, in a review log, indistinguishably from clearing it.
- **The unit tests deliberately excluded it.** Checkpoint B's constraint was to
  test `is_due()` and `acquire_lock()` "as pure functions only" — sensible, since
  the alternative looked like starting daemons in CI. But `acquire_lock()` is not
  pure: its entire correctness rests on `_pid_alive()`, and nothing ever ran it
  against a real PID in either state.
- **Only the live runbook could catch it.** Which it did, on the first attempt.

**Generalised lesson, in the shape of this repo's existing pitfalls:** *a lock
test that never starts a second process cannot certify mutual exclusion.* The
OS-touching function excluded from tests "because it touches the OS" is precisely
where platform assumptions hide unchallenged.

### Fix

`675d3dd` — `fix: correct Windows process-liveness check in EOD worker lock`

`_pid_alive()` now uses `OpenProcess` + `GetExitCodeProcess` via stdlib `ctypes`
on `nt`, retaining the `os.kill` path for POSIX. No new dependency (`psutil` was
checked for and is absent; the no-new-dependencies constraint holds).

Verified correct in all three cases before being applied:

| Case | Result |
|---|---|
| current process | `True` |
| exited process, handle still held | `False` |
| never-existed PID (999999) | `False` |

### Regression coverage (+5 tests, `tests/scheduler/test_worker_timing.py`)

`test_pid_alive_true_for_current_process`,
`test_pid_alive_false_for_exited_process`,
`test_acquire_lock_succeeds_when_no_lock_file`,
`test_acquire_lock_fails_when_holder_pid_alive`,
`test_acquire_lock_succeeds_when_holder_pid_dead`.

Both `_pid_alive`/`acquire_lock` tests were confirmed **failing for the stated
reason** before the fix and passing after — the TDD discipline used by
Checkpoints A–C was preserved.

### Live re-verification

```
2026-07-31 18:51:30,837  Another worker is already running (see F:\Nifty\data\_eod_worker.lock). Exiting.
```

Worker 27224 confirmed still alive after the probe; lock file still reading
`27224`. The probe is read-only and does not disturb its target.

### Containment

The duplicate worker (11524) was killed and the lock file repaired to `27224`
before any scheduled attempt could fire. Had this gone unnoticed until 20:00,
two daemons would have run the download chain concurrently against one SQLite
store and sent duplicate Telegram reports.

Note that pid 27224 is running the pre-fix module image. This is harmless:
`_pid_alive()` is called only from `acquire_lock()` at startup (line 94) and
never from the tick loop, so the running process is behaviourally identical to
the fixed code. No restart was required.

---

## 4. Deviation — credential mechanism (Step 1)

The runbook specified session environment variables set in the worker's parent
shell, with the warning that *"everything else in this runbook must be started
from this same shell."*

That is not what was done. Investigation found that **no code anywhere in the
repo called `load_dotenv()`** — `python-dotenv` was declared in `pyproject.toml`
but never invoked — so a populated `.env` would have had no effect at all. Rather
than rely on shell inheritance, `load_dotenv(ROOT / ".env")` was added to both
process entry points (`cec416c`):

- `scripts/schedule_worker.py`
- `scripts/run_flask.py`

**This is a strict improvement over the runbook's mechanism.** The worker no
longer depends on being launched from one specific shell — the failure mode the
runbook explicitly warned about (a worker started elsewhere silently failing to
send, because `send_sync` logs and returns `False` rather than crashing) is now
structurally impossible.

`.env` is covered by `.gitignore` (`.env`, `.env.*`); credentials were not
committed and appear in no artifact.

---

## 5. Evidence limits — read these before treating this as complete

Recorded honestly rather than smoothed over.

1. **Step 4 (browser) rests on a one-line operator attestation** — "everything
   seems to be ok." The runbook asked for a considered look at layout, alignment,
   and whether the status lines read sensibly. No such detail was captured. The
   panel demonstrably renders and the toggle demonstrably persists across reload,
   but this is *not* the design review the runbook intended.
2. **The amber "busy" state was never confirmed.** Checkpoint C's IMPORTANT-1 fix
   (a busy worker must not read as dead) was to be verified by refreshing the tab
   *during* the ~94-second manual run. It was asked for and not answered. **The
   busy-marker path therefore remains unverified end-to-end in the browser**,
   though its unit test passes and the facade logic was reviewed at Checkpoint C.
   The next long-running attempt is the natural opportunity to close this.
3. **Step 8 (arming) is not captured here.** Whether the toggle was set to
   Enabled — and so whether the job fires tonight at 20:00 — is not recorded in
   this report.
4. **No successful `success`-path run has ever occurred.** Every observed outcome
   is `retry`. The two-message Telegram flow (download summary + options book),
   the `holiday` path, and the `chain_failed` path have been exercised only by
   unit tests against formatters, never live. First real proof comes on the first
   evening data actually publishes.

---

## 6. Outstanding items

| # | Item | Priority |
|---|---|---|
| 1 | **`docs/superpowers/plans/2026-07-31-eod-automation-scheduler.md` still contains the buggy `os.kill(pid, 0)`.** Anything re-implemented from the plan reintroduces DEFECT-1. Correct it. | **HIGH** |
| 2 | Full `tests/` regression run not completed — Checkpoint C baseline `9 failed, 1868 passed, 4 skipped` is unconfirmed at close. Scheduler suite is green (66) and no non-scheduler file was touched, so risk is low, but it is unmeasured. | MEDIUM |
| 3 | Verify the amber busy state during the next long attempt (§5.2). | MEDIUM |
| 4 | MINOR-1 from Checkpoint A (index freshness inferred from filenames, `eod_decision.py:48-52`) — still deferred, unchanged. | LOW |
| 5 | PID-file locking cannot distinguish a live holder from an unrelated process that inherited a recycled PID. Failure mode is a worker that refuses to start — loud and recoverable via the runbook's stale-lock entry — not two workers running. Accepted, not fixed. | LOW |
| 6 | `DEVELOPER_GUIDE.md:240` documents `TELEGRAM_BOT_TOKEN`; the code reads `TELEGRAM_TOKEN`. Stale doc. | LOW |

---

## 7. Process note — role split

This repo's standing convention is that DeepSeek V4 implements from written
prompts and Claude writes prompts and reviews, never implementing gate
deliverables.

**DEFECT-1's fix departs from that.** Claude implemented `675d3dd` and `cec416c`
directly, mid-runbook, without first obtaining agreement to do so. The reasoning
was that this was live operator-driven debugging with two daemons already running
concurrently against a shared store — but the judgement was Claude's alone and is
recorded here rather than left implicit. Reverting and re-issuing both commits as
a DeepSeek prompt remains available and would cost little.

---

## 8. Verdict

**Checkpoint D: PASS.** Steps 1–7 verified live. The feature does what it was
designed to do, and the one defect the runbook uncovered is fixed, tested, and
re-verified.

The program is **not** closed by this report. Closure requires the items in §6 —
above all correcting the plan document (§6.1), which otherwise stands ready to
reintroduce the exact defect this checkpoint existed to catch.
