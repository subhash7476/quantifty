"""NiftyShield ops orchestrator — foreground supervisor for the PAPER window.

Manages Flask, market_ingestor, chain_poller, the PAPER session, and the EOD
worker; starts them in dependency order behind a preflight gate; restarts crashed
children; stops them cleanly. See the design spec for the full contract.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.utils.market_hours import MarketHours
from scripts.ops import pidfile

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
OPS_DIR = ROOT / "data" / "ops"

_CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows creationflag


@dataclass(frozen=True)
class ChildSpec:
    name: str
    argv: List[str]
    pid_path: Optional[Path] = None      # orchestrator-owned liveness
    native_lock: Optional[Path] = None   # child writes its own lock
    new_group: bool = False              # spawn in a new process group (session)
    status_path: Optional[Path] = None   # child-published heartbeat, asserted below
    status_max_age_s: float = 120.0      # closed-market cadence is ~60 s


def _status_fresh(spec: ChildSpec) -> bool:
    """Assert a child's published heartbeat, when it publishes one.

    A live PID is not a live child: 19336 was recycled by conhost while the
    ingestor's own status file sat 17 h stale, and the orchestrator adopted it
    (2026-09-08). Absent/unreadable status falls back to PID liveness — never
    spawn a second single-writer on a missing file.
    """
    if spec.status_path is None or not spec.status_path.exists():
        return True
    try:
        payload = json.loads(spec.status_path.read_text(encoding="utf-8"))
        hb = datetime.fromisoformat(payload["last_heartbeat"])
    except (OSError, ValueError, KeyError):
        return True
    return (datetime.now() - hb).total_seconds() <= spec.status_max_age_s


def child_alive(spec: ChildSpec) -> bool:
    lock = spec.native_lock or spec.pid_path
    return bool(lock) and pidfile.lock_alive(lock) and _status_fresh(spec)


def spawn(spec: ChildSpec, *, popen: Callable = subprocess.Popen):
    creationflags = _CREATE_NEW_PROCESS_GROUP if (spec.new_group and os.name == "nt") else 0
    kwargs = {"cwd": str(ROOT), "creationflags": creationflags} if os.name == "nt" \
        else {"cwd": str(ROOT), "start_new_session": spec.new_group}
    proc = popen(spec.argv, **kwargs)
    if spec.pid_path is not None:
        pidfile.write_pid(spec.pid_path, proc.pid)
    return proc


CHILDREN = {
    "flask": ChildSpec(
        "flask", [PY, str(ROOT / "scripts" / "run_flask.py")],
        pid_path=OPS_DIR / "flask.pid"),
    "ingestor": ChildSpec(
        "ingestor", [PY, str(ROOT / "scripts" / "market_ingestor.py")],
        pid_path=OPS_DIR / "market_ingestor.pid",
        status_path=ROOT / "logs" / "market_ingestor_status.json"),
    "poller": ChildSpec(
        "poller", [PY, str(ROOT / "scripts" / "nifty_shield_paper" / "chain_poller.py")],
        native_lock=ROOT / "data" / "options" / "chain_poller.pid"),
    "session": ChildSpec(
        "session",
        [PY, str(ROOT / "scripts" / "nifty_shield_paper" / "session.py"),
         "--data-root", str(ROOT / "data" / "nifty_shield")],
        pid_path=OPS_DIR / "session.pid", new_group=True),
    "eod": ChildSpec(
        "eod", [PY, str(ROOT / "scripts" / "schedule_worker.py")],
        native_lock=ROOT / "data" / "_eod_worker.lock"),
    # Options-Wall pilot poller — its own PID lock, independent of the NiftyShield
    # session. Supervised (crash-restart) but never gates the production start
    # sequence; `stop` skips it like the other natively-locked children.
    "wall_poller": ChildSpec(
        "wall_poller", [PY, str(ROOT / "scripts" / "options_wall_poller.py")],
        native_lock=ROOT / "data" / "options" / "wall_poller.pid"),
}


@dataclass
class Deps:
    spawn: Callable
    child_alive: Callable
    token_fresh: Callable[[], bool]
    open_login: Callable[[], None]
    preflight: Callable[[], str]
    marks_warm: Callable[[], bool]
    vix_warm: Callable[[], bool]
    dispatch_catchup: Callable[[], None]
    refresh_master: Callable[[], None]
    stop_present: Callable[[], bool]
    market_open: Callable[[], bool]
    # The session trades F&O, which runs to 15:40 post-CAS, while `market_open`
    # is the CASH segment and closes at 15:15. Parking the session on the cash
    # clock made its own 15:35 exit unreachable and silently refused to start it
    # after 15:15 (2026-09-08). Only the session's gate moves — flask, the
    # ingestor and the poller start before the park and are untouched.
    derivatives_open: Callable[[], bool]
    sleep: Callable[[float], None]
    now: Callable[[], datetime]
    # Diagnostic only: human string naming the currently-failing BLOCK checks
    # (e.g. "marks_warm: ...; live_vix: ..."). Logged in the warm-up loops so a
    # timeout:warmup names the cold feed instead of failing silently.
    gate_status: Callable[[], str] = lambda: ""
    # Register an already-running child for supervision (no proc handle).
    adopt: Callable = lambda spec: None
    # Restart-crashed-children hook, run inside the warm-up/final-gate waits:
    # start_sequence blocks up to warmup_timeout_s, and a child that dies
    # during that window (e.g. the ingestor at startup, 2026-08-21) must be
    # revived or the feed it owns can never warm up.
    supervise: Callable[[], None] = lambda: None


def _ensure(deps: Deps, name: str) -> None:
    """Adopt a living child; else spawn it. Either way it becomes supervised."""
    spec = CHILDREN[name]
    if not deps.child_alive(spec):
        deps.spawn(spec)
    else:
        # An ADOPTED child was invisible to the supervisor, which iterated only
        # what this process spawned. So a session inherited from a previous
        # orchestrator could exit and never be revived, while the supervise loop
        # ran on reporting nothing wrong (2026-09-08). Register it with no proc
        # handle; liveness comes from its lock, which works for both kinds.
        deps.adopt(spec)


def start_sequence(deps: Deps, *, token_timeout_s: float = 600.0,
                   warmup_timeout_s: float = 120.0, park_timeout_s: float = 21600.0,
                   poll_s: float = 2.0, park_poll_s: float = 30.0) -> str:
    # 1. STOP-file refusal BEFORE any spawn (design §5.1 step 1 / §6) — never
    #    silently clear an operator kill switch.
    if deps.stop_present():
        return "blocked:stop"

    # 1b. Instrument master (non-blocking on failure). Before Flask, whose OAuth
    #     callback also writes the store, and before the poller, which resolves
    #     expiries from it. Needs no token — the source is a public CDN file.
    deps.refresh_master()

    # 2. Flask (needed for the OAuth handshake).
    _ensure(deps, "flask")

    # 3. Token gate — open the login page once, then block-poll until fresh.
    if not deps.token_fresh():
        deps.open_login()
        waited = 0.0
        while not deps.token_fresh():
            if waited >= token_timeout_s:
                return "timeout:token"
            deps.sleep(poll_s)
            waited += poll_s

    # 4. Live feed + marks.
    _ensure(deps, "ingestor")
    _ensure(deps, "poller")

    # 5a. Park until the SESSION's market is open — pre-open the poller idles, so
    #     marks CANNOT be warm (design §5.1 step 5: PARK until market-open +
    #     warm-up). The gate is the DERIVATIVES segment (09:15-15:40 post-CAS),
    #     not cash (09:15-15:15): everything past this point exists to run an F&O
    #     session, and gating it on the cash clock made the window unstartable
    #     for the last 25 minutes of its own trading day. Derivatives hours are a
    #     superset of cash hours, so this never parks when cash is open.
    #     This wait can be long (command run pre-open); the safety cap only
    #     guards a broken clock, it is not a normal exit.
    waited = 0.0
    while not deps.derivatives_open():
        if waited >= park_timeout_s:
            return "timeout:market_open"
        # Parked is a state an operator must be able to SEE. A silent multi-hour
        # park looks identical to a hung start.
        if waited % 300 == 0:
            _logger.info("parked — derivatives segment closed (waited ~%.0fs); "
                         "the session starts when it opens", waited)
        deps.sleep(park_poll_s)
        waited += park_poll_s

    # 5b. Warm-up — once open, wait bounded for marks AND VIX/ingestor to flow
    #     before the runner constructs (F2: the park must be symmetric — a valid-
    #     but-empty marks cache prices nothing, and a cold VIX feed skips the
    #     13:00 fact). A single cold feed holds the whole sequence.
    waited = 0.0
    while True:
        marks_ok, vix_ok = deps.marks_warm(), deps.vix_warm()
        if marks_ok and vix_ok:
            break
        deps.supervise()                        # revive a crashed ingestor now
        if waited >= warmup_timeout_s:
            _logger.warning("warm-up timeout (feed cold) after ~%ss counted — "
                            "marks_warm=%s vix_warm=%s | %s",
                            waited, marks_ok, vix_ok, deps.gate_status())
            return "timeout:warmup"
        _logger.info("warm-up waiting — marks_warm=%s vix_warm=%s | %s",
                     marks_ok, vix_ok, deps.gate_status())
        deps.sleep(poll_s)
        waited += poll_s

    # 6. Background catch-up (non-blocking; never gates the session).
    deps.dispatch_catchup()

    # 7. Final preflight gate — F2: a NO-GO that is only "still warming" (marks
    #     or VIX went cold again after the park) is retried/parked; only a NO-GO
    #     while the stack IS warm is a genuine block (token/STOP) that halts.
    waited = 0.0
    while deps.preflight() != "GO":
        deps.supervise()                        # revive a crashed child now
        if deps.marks_warm() and deps.vix_warm():
            _logger.warning("preflight blocked while feeds warm — %s", deps.gate_status())
            return "blocked:preflight"
        if waited >= warmup_timeout_s:
            _logger.warning("warm-up timeout (final gate) after ~%ss counted — %s",
                            waited, deps.gate_status())
            return "timeout:warmup"
        _logger.info("final gate waiting (feeds re-cooling) — %s", deps.gate_status())
        deps.sleep(poll_s)
        waited += poll_s

    # 8. Start the session (recording ON via CHILDREN["session"]).
    _ensure(deps, "session")

    # 9. Ensure the EOD worker.
    _ensure(deps, "eod")

    # 10. Ensure the Options-Wall pilot poller (independent; last, so it never
    #     gates the production path).
    _ensure(deps, "wall_poller")
    return "started"


_logger = logging.getLogger("ops_orchestrator")
ORCH_LOCK = OPS_DIR / "orchestrator.pid"
SESSION_FINALIZE_BUDGET_S = 90.0


def stop_child(spec: ChildSpec, proc, *, killer=os.kill, term_wait_s: float = SESSION_FINALIZE_BUDGET_S) -> None:
    """Stop one child. The session gets a cooperative group signal + bounded wait
    (its SIGBREAK/SIGTERM handler calls driver.stop() → clean finalize); other
    children get a normal terminate()."""
    if spec.new_group:
        sig = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
        signaled = True
        try:
            killer(proc.pid, sig)
        except Exception as exc:  # noqa: BLE001
            signaled = False
            _logger.warning("signalling %s failed: %s", spec.name, exc)
        if not signaled:
            # A failed signal (e.g. CTRL_BREAK_EVENT cross-console on Windows —
            # the stop command runs in a different console than the session) can
            # never trigger a clean stop, so skip the graceful wait and kill now.
            try:
                proc.kill()
            except Exception:
                pass
        else:
            try:
                proc.wait(timeout=term_wait_s)
            except Exception:
                _logger.error("%s did not exit within %ss — escalating to kill",
                              spec.name, term_wait_s)
                try:
                    proc.kill()
                except Exception:
                    pass
    else:
        try:
            proc.terminate()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("terminating %s failed: %s", spec.name, exc)
    if spec.pid_path is not None:
        pidfile.release_lock(spec.pid_path, getattr(proc, "pid", None))


class Supervisor:
    def __init__(self, *, started: dict, spawn=spawn, child_alive=child_alive,
                 stopper=stop_child, backoff_cap_s: float = 30.0,
                 spawn_grace_s: float = 20.0):
        self._started = started
        self._spawn = spawn
        self._child_alive = child_alive
        self._stopper = stopper
        self._backoff_cap = backoff_cap_s
        self._fails: dict = {}
        # Liveness is now read from the lock rather than a proc handle, so a
        # child that has not yet written its lock would read as dead and be
        # respawned in a loop. Hold off for one grace window after spawning.
        self._spawn_grace_s = spawn_grace_s
        self._spawned_at: dict = {}

    def adopt(self, spec: ChildSpec) -> None:
        """Supervise a child this process did not spawn.

        Resolve a handle from its pidfile where it has one, so shutdown can
        actually stop it — registering it with a bare None would supervise it
        but leave it running on Ctrl+C.
        """
        if spec.name in self._started:
            return
        pid = pidfile.read_pid(spec.pid_path) if spec.pid_path else None
        self._started[spec.name] = _RemoteProc(pid) if pid else None

    def tick(self) -> None:
        for name in list(self._started):
            spec = CHILDREN[name]
            if self._child_alive(spec):
                continue
            # Liveness is the child's LOCK, not our proc handle: an adopted child
            # has no handle, and a child that exits CLEANLY leaves poll() == 0,
            # which the old `proc_dead and not alive` test still required a
            # handle to see. Both are dead the same way and must be revived the
            # same way.
            if self._in_spawn_grace(name):
                continue        # just spawned; its lock may not be written yet
            self._fails[name] = self._fails.get(name, 0) + 1
            _logger.error("child %s is not alive — restart #%d", name,
                          self._fails[name])
            self._started[name] = self._spawn(spec)
            self._spawned_at[name] = time.monotonic()

    def _in_spawn_grace(self, name: str) -> bool:
        at = self._spawned_at.get(name)
        return at is not None and (time.monotonic() - at) < self._spawn_grace_s

    def shutdown(self) -> None:
        # Session first (longest finalize), then the rest. `_started` now also
        # holds adopted children; those carry a _RemoteProc built from their
        # pidfile, or None when they are natively locked and own no pidfile.
        for name in sorted(self._started, key=lambda n: 0 if n == "session" else 1):
            proc = self._started[name]
            if proc is None:
                continue                  # nothing to signal (adopted, no pidfile)
            self._stopper(CHILDREN[name], proc)


CATCHUP_STAMP = OPS_DIR / "last_catchup.json"
CATCHUP_LOG_DIR = ROOT / "logs"


def _catchup_due(*, stamp_path: Path = CATCHUP_STAMP,
                 now: Optional[datetime] = None) -> bool:
    """True when no catch-up download has been dispatched today.

    The catch-up is a whole-pipeline bhavcopy/1m re-walk that costs hundreds of
    Upstox calls; firing it on every orchestrator start meant a restart mid-session
    re-ran it against the same stores while the live pollers competed for the same
    rate limit. The EOD chain (`core/scheduler/eod_job.py`) still runs it
    unconditionally after close — that is the run which picks up today's bhavcopy.
    """
    today = (now or datetime.now()).date().isoformat()
    try:
        return json.loads(Path(stamp_path).read_text(encoding="utf-8")).get("date") != today
    except (OSError, ValueError, AttributeError):
        return True


def _record_catchup(*, stamp_path: Path = CATCHUP_STAMP,
                    now: Optional[datetime] = None) -> None:
    """Stamp the dispatch. Records *dispatched*, not *succeeded* — the ingests
    self-heal on their trailing lookback window and EOD re-runs nightly."""
    at = now or datetime.now()
    stamp_path = Path(stamp_path)
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(
        json.dumps({"date": at.date().isoformat(), "dispatched_at": at.isoformat()}),
        encoding="utf-8")


def _dispatch_catchup(*, stamp_path: Path = CATCHUP_STAMP, log_dir: Path = CATCHUP_LOG_DIR) -> None:
    """Fire download_all_data as a detached background one-shot; never blocks.

    At most once per calendar day (`_catchup_due`). Output goes to a dated log —
    a detached child's console output is otherwise lost, failures included."""
    if not _catchup_due(stamp_path=stamp_path):
        _logger.info("catch-up download already dispatched today — skipping")
        return
    argv = [PY, str(ROOT / "scripts" / "download_all_data.py")]
    flags = _CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    kw = {"cwd": str(ROOT), "stderr": subprocess.STDOUT,
          "env": {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}}
    if os.name == "nt":
        kw["creationflags"] = flags
    else:
        kw["start_new_session"] = True
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"catchup_{datetime.now():%Y%m%d_%H%M%S}.log"
        with open(log_path, "ab") as log:
            subprocess.Popen(argv, stdout=log, **kw)
        _record_catchup(stamp_path=stamp_path)
        _logger.info("background catch-up download dispatched — output: %s", log_path)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("catch-up dispatch failed (non-blocking): %s", exc)


def _refresh_master(*, db_path: Optional[Path] = None, run: Optional[Callable] = None,
                    now: Optional[datetime] = None) -> None:
    """Publish today's instrument-master snapshot before anything reads the store.

    `run_refresh` had no caller, and the OAuth-callback backstop is skipped by a
    surviving token or a CLI login — snapshots stopped at 2026-09-08 while four
    sessions ran. Once per day, so a mid-session restart does not rewrite the store
    under live readers; never fatal, since every failed run keeps the prior snapshot.
    """
    try:
        # The import (duckdb/pyarrow) and the stat are inside the guard too — a broken
        # install must cost one refresh, not the whole window start.
        from scripts import fetch_instrument_master as fim
        db_path = Path(db_path or fim.DB_PATH)
        today = (now or datetime.now()).date()
        if db_path.exists() and datetime.fromtimestamp(db_path.stat().st_mtime).date() == today:
            _logger.info("instrument master already refreshed today — skipping")
            return
        rc = (run or fim.run_refresh)(db_path=db_path)
    except Exception as exc:  # noqa: BLE001 — a failed refresh must never block the window
        _logger.warning("instrument-master refresh failed (non-blocking, prior snapshot kept): %s", exc)
        return
    if rc != fim.EXIT_OK:
        _logger.warning("instrument-master refresh refused with exit %s "
                        "(non-blocking, prior snapshot kept)", rc)
    else:
        _logger.info("instrument-master refresh done")


def _live_deps(started: dict) -> Deps:
    from scripts.ops import preflight
    from core.auth.credentials import credentials

    def _spawn(spec):
        proc = spawn(spec)
        started[spec.name] = proc
        return proc

    def _token_fresh() -> bool:
        credentials._load()
        return credentials.has_upstox_token and not credentials.is_token_expired

    def _open_login():
        url = "http://127.0.0.1:5000/ops/login/upstox"
        print(f"\n>>> Upstox token required. Opening {url}\n"
              f">>> Complete the browser login; the orchestrator will continue "
              f"automatically.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _marks_warm() -> bool:
        ctx = preflight.build_context()
        return preflight.check_marks(ctx).ok

    def _vix_warm() -> bool:
        ctx = preflight.build_context()
        return preflight.check_vix(ctx).ok

    def _gate_status() -> str:
        """Failing BLOCK-check details for the warm-up log (diagnostic only)."""
        try:
            ctx = preflight.build_context()
            cold = [f"{r.name}: {r.detail}"
                    for r in preflight.run_preflight(ctx)
                    if r.tier == "block" and not r.ok]
            return "; ".join(cold) if cold else "all BLOCK checks GO"
        except Exception as exc:  # noqa: BLE001 — never let logging break the gate
            return f"gate_status unavailable: {exc}"

    return Deps(
        spawn=_spawn, child_alive=child_alive, token_fresh=_token_fresh,
        open_login=_open_login,
        preflight=lambda: preflight.verdict(preflight.run_preflight(preflight.build_context())),
        marks_warm=_marks_warm, vix_warm=_vix_warm,
        dispatch_catchup=_dispatch_catchup,
        refresh_master=_refresh_master,
        stop_present=lambda: (ROOT / "STOP").exists(),
        market_open=lambda: MarketHours.is_market_open(),
        derivatives_open=lambda: MarketHours.is_derivatives_open(),
        sleep=time.sleep, now=datetime.now,
        gate_status=_gate_status,
    )


def _cmd_start(dry_run: bool) -> int:
    if dry_run:
        print("DRY-RUN start plan (dependency order):")
        for name in ["flask", "ingestor", "poller", "session", "eod", "wall_poller"]:
            spec = CHILDREN[name]
            print(f"  {name:9} -> {' '.join(spec.argv)}"
                  + (" [new group]" if spec.new_group else ""))
        return 0
    if not pidfile.acquire_lock(ORCH_LOCK):
        print(f"another orchestrator is running (see {ORCH_LOCK})")
        return 1
    started: dict = {}
    sup = Supervisor(started=started)
    deps = _live_deps(started)
    deps.supervise = sup.tick
    deps.adopt = sup.adopt
    try:
        outcome = start_sequence(deps)
        print(f"start sequence: {outcome}")
        if outcome != "started":
            sup.shutdown()
            return 1
        _logger.info("supervising — Ctrl+C to stop")
        while True:
            sup.tick()
            time.sleep(5.0)
    except KeyboardInterrupt:
        print("\nshutting down...")
        sup.shutdown()
        return 0
    finally:
        pidfile.release_lock(ORCH_LOCK)


def _cmd_status() -> int:
    from scripts.ops import preflight
    print("children:")
    for name, spec in CHILDREN.items():
        print(f"  {name:9} alive={child_alive(spec)}")
    ctx = preflight.build_context()
    results = preflight.run_preflight(ctx)
    print(f"preflight verdict: {preflight.verdict(results)}")
    return 0


def _cmd_stop() -> int:
    stopped = 0
    for name in sorted(CHILDREN, key=lambda n: 0 if n == "session" else 1):
        spec = CHILDREN[name]
        if spec.pid_path is None:          # never stop natively-locked adopted daemons
            continue
        pid = pidfile.read_pid(spec.pid_path)
        if pid and pidfile.pid_alive(pid):
            stop_child(spec, _RemoteProc(pid))
            stopped += 1
    print(f"stopped {stopped} orchestrator-owned child(ren)")
    return 0


class _RemoteProc:
    """Minimal proc handle for `stop` from a second console (pid only)."""
    def __init__(self, pid: int):
        self.pid = pid

    def poll(self):
        return None if pidfile.pid_alive(self.pid) else 0

    def wait(self, timeout=None):
        end = time.time() + (timeout or 0)
        while pidfile.pid_alive(self.pid) and time.time() < end:
            time.sleep(0.2)

    def kill(self):
        if os.name == "nt":
            os.system(f"taskkill /F /PID {self.pid} >nul 2>&1")
        else:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NiftyShield ops orchestrator")
    parser.add_argument("command", nargs="?", default="start",
                        choices=["start", "status", "stop"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if args.command == "start":
        return _cmd_start(args.dry_run)
    if args.command == "status":
        return _cmd_status()
    return _cmd_stop()


if __name__ == "__main__":
    raise SystemExit(main())
