# Ops health check — ingestor respawn loop (2026-09-09, live PAPER window)

**Status:** ACTIVE FAULT at time of writing. Preflight verdict is `GO`; the stack is
nevertheless in an unrecoverable supervisor loop.

## 1. Symptom

The operator's console showed `orchestrator.py started` followed by a truncated
traceback from `scripts/market_ingestor.py:317` → `__init__:61` → `ZmqPublisher(...)`.
The traceback is a bind failure on `tcp://127.0.0.1:5555` (`config/zmq.json`
`ports.market_data_pub`), raised by a **duplicate** ingestor.

## 2. What is actually true

The real ingestor is healthy. `logs/market_ingestor_status.json` reports
`status=CONNECTED, pid=12140`, heartbeat age **0.37 s** when probed. PID 12140 has been
up since 09:20:47 and holds port 5555.

`scripts/ops/orchestrator.py` is nevertheless spawning a new `market_ingestor.py` every
~25–40 s. Each duplicate dies on the ZMQ bind. Observed doomed PIDs: 15300 (09:23:55),
21940 (09:24:36), 312, 8128, 19928 (09:36:18). None linger — all confirmed exited.

Direct probe of the supervisor's own liveness test:

```
spec.pid_path   : F:\Nifty\data\ops\market_ingestor.pid
pid in file     : 8128          <- a dead duplicate
lock_alive      : False
status_fresh    : True
child_alive     : False         <- supervisor believes the ingestor is dead
pid_alive(12140): True          <- it is not
status pid      : 12140  age_s: 0.367
```

## 3. Root cause — the loop cannot converge, by construction

`child_alive()` (orchestrator.py:265) reads liveness from
`data/ops/market_ingestor.pid`. `spawn()` (orchestrator.py:274) **unconditionally
overwrites that same file** with the newly spawned PID, without verifying the child
survived. So:

1. Something makes `child_alive` return False once.
2. `Supervisor.tick` spawns a duplicate and overwrites the pidfile with its PID.
3. The duplicate dies immediately (port 5555 held by the healthy incumbent).
4. The pidfile now names a dead process, so `child_alive` is False forever.

**A single false-negative from any cause is permanently unrecoverable.** The original
trigger at ~09:23:55 is not attributable — the pidfile has been overwritten ~25 times,
the failure counter lives only in orchestrator memory, and its log goes to a console
`basicConfig` stream not captured on disk. The trigger is also not load-bearing: the
defect is that the loop has no path back to the healthy child.

The asymmetry is already visible in the repo. `scripts/ops/preflight.py::_ingestor_alive`
reads the pid the **child publishes about itself** (`market_ingestor_status.json`) and
gets the right answer. The orchestrator reads the file it corrupts, and gets the wrong
one. That is why preflight says `GO` while the supervisor thrashes.

## 4. Blast radius (measured, not assumed)

Each duplicate reaches `__init__` line 61 and no further, so:

- **No DuckDB writer contention.** `DatabaseManager.__init__` opens no DuckDB
  connection, and `LiveBufferWriter` / the WebSocket are constructed *after* the ZMQ
  bind — never reached. No second writer on the live buffer.
- **SQLite config DB is touched.** `bootstrap_config_db` runs before the crash, taking
  the cross-process `data/config/.writer.lock` (10 s timeout) and executing idempotent
  `CREATE TABLE IF NOT EXISTS`. Harmless in itself; it does contend briefly with the
  real ingestor's 1.5 s status writes.
- **The supervisor is blind.** Because it is permanently convinced the ingestor is
  dead, a *genuine* ingestor crash would now also never be recovered — the failure
  mode the supervisor exists to prevent.
- **Dirty shutdown.** `_started["ingestor"]` holds a dead handle, so Ctrl+C terminates
  nothing and leaves PID 12140 orphaned; `release_lock` will not unlink the pidfile
  either (the pid does not match).
- Unbounded process churn: ~25 python starts since 09:23:55.

## 5. Preflight (2026-09-09 09:33)

```
[OK ] BLOCK upstox_token       token present and fresh
[OK ] BLOCK stop_file          no STOP file
[OK ] BLOCK marks_warm         266 priceable rows, heartbeat 8.5s
[OK ] BLOCK live_vix           VIX bar 118.4s old
[ ~ ] WARN  span               SPAN snapshot absent (PAPER tolerates flat-rate margin)
[ ~ ] WARN  instrument_master  stale (age 1.00d)
[OK ] WARN  eod_feeds          all EOD feeds fresh
[OK ] WARN  eod_worker         EOD worker alive
VERDICT: GO
```

Both WARNs are pre-existing and unrelated to this fault.

## 6. Immediate circuit breaker (no process is killed)

Write the true PID into the supervisor's oracle:

```
echo 12140 > data/ops/market_ingestor.pid
```

Next `tick()` reads 12140 → `pid_alive` True → `_status_fresh` already True →
`child_alive` True → `continue`. The loop stops on the next 5 s tick. Nothing is
signalled, nothing dies, the session/poller/wall_poller are untouched. The file is
supervisor state that is rewritten constantly, so this is not a risky mutation.

Caveat: this does not repair the stale `_started["ingestor"]` handle. On Ctrl+C the
orchestrator will still leave 12140 running. **Verify 12140 is actually dead before any
restart** — it is the single writer of the live buffer.

## 7. Durable fix (two changes, not started)

1. **Trust the child's self-published identity.** Where a `ChildSpec` has a
   `status_path`, `child_alive` should take the pid from that file — the child writes it
   about itself and the supervisor never overwrites it — rather than from the pidfile
   `spawn()` clobbers. This is what `preflight._ingestor_alive` already does correctly.
2. **Acquire the singleton lock before any side effect.** `market_ingestor.__init__`
   opens the config DB and bootstraps schema before the ZMQ bind, and `_acquire_lock()`
   runs later still (in `run()`). Moving the lock acquisition to the top of `__init__`
   makes a duplicate exit with *"another instance is already running (PID 12140)"*
   instead of a raw `ZMQError` traceback, and stops it touching any store.

   Note on `_acquire_lock` (market_ingestor.py:153): it probes the incumbent with
   `os.kill(pid, 0)`, which `scripts/ops/pidfile.py`'s docstring warns is destructive on
   Windows. **Tested on this interpreter (CPython 3.13, Win11): it does not kill** — a
   throwaway child survived `os.kill(pid, 0)` intact. So reordering is not armed as a
   footgun here. Switching it to `pidfile.pid_alive` is still the right call for a
   different reason: `os.kill` cannot distinguish a zombie handle from a live process,
   which is exactly the bug `pid_alive` was written to fix.

Out of scope: this is a distinct defect from the agreed writer-worker redesign (F1/F3/F4)
and should not be folded into it. Note also that the working tree carries 19 modified
files of unrelated NiftyShield work on `fix/options-wall-tp-sl-thresholds`, so an
orchestrator fix committed here lands mixed in.

---

## 8. Breaker applied — 2026-09-09 09:40

Operator chose: breaker now, durable fix after the close.

`12140` written to `data/ops/market_ingestor.pid` (verified alive immediately before the
write; the file then held `20708`, another dead duplicate).

Verified over 30 s: `pidfile=12140, child_alive=True` on every 5 s tick — the file was
not re-clobbered, so the supervisor is reading the healthy child again. Process list now
shows **exactly one** `market_ingestor.py`, PID 12140, from 09:20:47. Churn stopped.

Still outstanding: §7 (the two durable changes) and the stale `_started["ingestor"]`
handle, which means Ctrl+C on this orchestrator will still leave 12140 running. Confirm
12140 is dead before restarting anything.

---

## 9. Recurrence — 2026-09-15, and §7 item 1 fixed

Same fault, same shape. Orchestrator started 09:15:05; the real ingestor (PID 11628,
09:15:11) held port 5555 with `status=CONNECTED` and a sub-second heartbeat, while
`data/ops/market_ingestor.pid` was rewritten every ~20 s (observed 15864 → 18188 → 22348
→ 24408 → 18204, each a dead duplicate). The loop was already running at 11:35:26 (pidfile
mtime at the morning health check); the original trigger is again unattributable because the
supervisor's restart log goes only to its console.

A probe of the supervisor's own test: `pidfile pid 24408 lock_alive=False`,
`status pid 11628 pid_alive=True hb age 0.65 s`, `status_fresh=True`, **`child_alive=False`**.

**Breaker applied 12:22:13** via `pidfile.write_pid(..., 11628)` after asserting 11628 was
alive and was the status file's pid (not `echo >` — PowerShell writes a BOM that `read_pid`
parses as no pid). Verified over 30 s: pidfile held 11628, `child_alive=True` on every sample;
the process list shows exactly one `market_ingestor.py` (11628).

**§7 item 1 — DONE.** `child_alive` now takes the pid from the child's self-published status
file when one exists (`_published_pid`), falling back to the pidfile only when the status file
is absent or carries no pid. A clobbered pidfile can no longer outvote the live child, so the
loop converges on the next tick after any false negative. Verified live against the real
status file with a scratch pidfile holding a dead pid: `child_alive=True`. Tests:
`test_child_alive_trusts_the_published_pid_over_a_clobbered_pidfile`,
`test_child_alive_false_when_the_published_pid_is_dead`.

Still outstanding: **§7 item 2** (the ingestor's own singleton lock is commented out; the
two-lock-namespace decision in the startup audit §5 is unmade), the **stale
`_started["ingestor"]` handle** (Ctrl+C on the 09:15 orchestrator will leave 11628 running —
confirm it is dead before restarting), and the **trigger** itself — a false negative is now
survivable, but nothing records why it happened.

---

**Companion audit:** the rest of the 2026-09-09 startup sequence (live-buffer purge, catch-up download, CAS marking, instrument master) is audited in `OPS_STARTUP_SEQUENCE_AUDIT_2026-09-09.md`. Note that its §5 **corrects §7 item 2 above**: `_acquire_lock()` is commented out, so the fix is not a reorder.
