# Stale-lock TLA+ model and orchestrator shutdown — 2026-09-23

## 1. Model

`docs/tla/StaleLock.tla` models `scripts/ops/pidfile.py` (`lock_alive` / `acquire_lock` /
`release_lock`, commit e98915d): holders acquire, release, or crash without cleanup; the OS
recycles PIDs to unrelated processes. Two configs: `StaleLock_Shipped.cfg` (as shipped) and
`StaleLock_Proposed.cfg` (creation-time stamp + atomic create).

**TLC-verified** (TLC 2.19, JDK 27): Shipped violates both invariants with the traces below;
Proposed passes both, 11,916 distinct states, search exhausted. The independent Python BFS
(`docs/tla/stalelock_bfs.py`) agrees on every verdict and on exact state counts (Shipped
19,050, Proposed 11,916). Bounds: Pids={1,2}, MaxTime=4, MaxSpawns=4, Tol=1.
Run: `bash docs/tla/tlc.sh StaleLock StaleLock_Shipped.cfg` (downloads `tla2tools.jar` if absent;
the jar is git-ignored).

| Mode | Atomic | States | NoFalseAdoption | MutualExclusion |
|---|---|--:|---|---|
| mtime (shipped) | no (shipped) | 19,050 | VIOLATED | VIOLATED |
| mtime | yes | 11,916 | VIOLATED | holds |
| stamp | no | 22,160 | holds | VIOLATED |
| stamp | yes | 11,916 | holds | holds |

Counterexamples (shortest):
- **NoFalseAdoption** — holder starts, writes lock, crashes; the OS reuses its PID within `Tol`
  of the lock write. `started <= mtime + 2 s` passes, so the stranger is adopted. Requires a crash
  *and* PID reuse inside ~2 s of the write — negligible in practice; e98915d fixed the real
  (68-hour) incident.
- **MutualExclusion** — two holders start together, both `Check` see stale, both write. Requires
  two near-simultaneous launches of the same singleton.

Optional hardening, not urgent: store the writer's creation time in the lock and compare exactly;
create the lock atomically (`os.open(..., O_CREAT | O_EXCL)`).

Out of scope of the model: the ingestor's adoption path (published PID + bare `pid_alive` + heartbeat).

## 2. Stop-path bug (confirmed)

`_RemoteProc` (`scripts/ops/orchestrator.py`) has no `terminate()`. `stop_child` calls
`proc.terminate()` for non-session children, catches the `AttributeError`, logs a warning, then
**deletes the pidfile anyway**. Reproduced: `stop_child(flask_spec, _RemoteProc(pid))` →
"terminating flask failed: '_RemoteProc' object has no attribute 'terminate'", pidfile gone.
Affects `orchestrator.py stop` and adopted flask/ingestor at Ctrl+C shutdown: the process keeps
running with no pidfile, and the next start spawns a duplicate beside it.

**Fixed (uncommitted):** `_RemoteProc.terminate = kill`, and `stop_child` returns without
releasing the pidfile when terminate raises. Tests: `test_stop_child_actually_stops_a_remote_proc`
(real subprocess) and `test_stop_child_keeps_the_pid_file_when_terminate_fails`; both RED before,
`tests/ops/` 82 passed after. Residual: `_RemoteProc.kill` shells out to `taskkill` and cannot
report failure, so a taskkill that fails (e.g. access denied) still drops the pidfile.

## 3. Clean shutdown

- **One** Ctrl+C in the orchestrator's own console; wait for the prompt (session finalize ≤ 90 s).
- Never press twice — a second `KeyboardInterrupt` escapes `Supervisor.shutdown()` and the
  remaining children are never stopped.
- Don't close the console window (Windows hard-kills after ~5 s) and don't `taskkill /F`.
- Don't use `orchestrator.py stop` from a second console while the orchestrator runs:
  CTRL_BREAK fails cross-console so the session is hard-killed, natively-locked children are
  skipped, the supervisor respawns within 5 s, and §2 applies.
- `data/_eod_worker.lock` is **always** left after a clean stop — `schedule_worker.py` never
  releases it. Harmless (lock_alive reads it as stale), not a failure.
