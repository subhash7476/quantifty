"""NiftyShield ops orchestrator — foreground supervisor for the PAPER window.

Manages Flask, market_ingestor, chain_poller, the PAPER session, and the EOD
worker; starts them in dependency order behind a preflight gate; restarts crashed
children; stops them cleanly. See the design spec for the full contract.
"""
from __future__ import annotations

import argparse
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


def child_alive(spec: ChildSpec) -> bool:
    lock = spec.native_lock or spec.pid_path
    return bool(lock) and pidfile.lock_alive(lock)


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
        pid_path=OPS_DIR / "market_ingestor.pid"),
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
}


@dataclass
class Deps:
    spawn: Callable
    child_alive: Callable
    token_fresh: Callable[[], bool]
    open_login: Callable[[], None]
    preflight: Callable[[], str]
    marks_warm: Callable[[], bool]
    dispatch_catchup: Callable[[], None]
    stop_present: Callable[[], bool]
    market_open: Callable[[], bool]
    sleep: Callable[[float], None]
    now: Callable[[], datetime]


def _ensure(deps: Deps, name: str) -> None:
    """Adopt a living child; else spawn it."""
    spec = CHILDREN[name]
    if not deps.child_alive(spec):
        deps.spawn(spec)


def start_sequence(deps: Deps, *, token_timeout_s: float = 600.0,
                   warmup_timeout_s: float = 120.0, park_timeout_s: float = 21600.0,
                   poll_s: float = 2.0, park_poll_s: float = 30.0) -> str:
    # 1. STOP-file refusal BEFORE any spawn (design §5.1 step 1 / §6) — never
    #    silently clear an operator kill switch.
    if deps.stop_present():
        return "blocked:stop"

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

    # 5a. Park until market open — pre-open the poller idles, so marks CANNOT be
    #     warm (design §5.1 step 5: PARK until market-open + warm-up). This wait
    #     can be long (command run pre-open); the safety cap only guards a broken
    #     clock, it is not a normal exit.
    waited = 0.0
    while not deps.market_open():
        if waited >= park_timeout_s:
            return "timeout:market_open"
        deps.sleep(park_poll_s)
        waited += park_poll_s

    # 5b. Warm-up — once open, wait bounded for marks to flow before the runner
    #     constructs (a valid-but-empty cache prices nothing).
    waited = 0.0
    while not deps.marks_warm():
        if waited >= warmup_timeout_s:
            return "timeout:warmup"
        deps.sleep(poll_s)
        waited += poll_s

    # 6. Background catch-up (non-blocking; never gates the session).
    deps.dispatch_catchup()

    # 7. Final preflight gate.
    if deps.preflight() != "GO":
        return "blocked:preflight"

    # 8. Start the session (recording ON via CHILDREN["session"]).
    _ensure(deps, "session")

    # 9. Ensure the EOD worker.
    _ensure(deps, "eod")
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
        try:
            killer(proc.pid, sig)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("signalling %s failed: %s", spec.name, exc)
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
        pidfile.release_lock(spec.pid_path)


class Supervisor:
    def __init__(self, *, started: dict, spawn=spawn, child_alive=child_alive,
                 stopper=stop_child, backoff_cap_s: float = 30.0):
        self._started = started
        self._spawn = spawn
        self._child_alive = child_alive
        self._stopper = stopper
        self._backoff_cap = backoff_cap_s
        self._fails: dict = {}

    def tick(self) -> None:
        for name, proc in list(self._started.items()):
            spec = CHILDREN[name]
            proc_dead = proc is not None and proc.poll() is not None
            if proc_dead and not self._child_alive(spec):
                self._fails[name] = self._fails.get(name, 0) + 1
                _logger.error("child %s died — restart #%d", name, self._fails[name])
                self._started[name] = self._spawn(spec)

    def shutdown(self) -> None:
        # Session first (longest finalize), then the rest — only what we started.
        for name in sorted(self._started, key=lambda n: 0 if n == "session" else 1):
            self._stopper(CHILDREN[name], self._started[name])


def _dispatch_catchup() -> None:
    """Fire download_all_data as a detached background one-shot; never blocks."""
    argv = [PY, str(ROOT / "scripts" / "download_all_data.py")]
    flags = _CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    kw = {"cwd": str(ROOT)}
    if os.name == "nt":
        kw["creationflags"] = flags
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(argv, **kw)
        _logger.info("background catch-up download dispatched")
    except Exception as exc:  # noqa: BLE001
        _logger.warning("catch-up dispatch failed (non-blocking): %s", exc)


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

    return Deps(
        spawn=_spawn, child_alive=child_alive, token_fresh=_token_fresh,
        open_login=_open_login,
        preflight=lambda: preflight.verdict(preflight.run_preflight(preflight.build_context())),
        marks_warm=_marks_warm, dispatch_catchup=_dispatch_catchup,
        stop_present=lambda: (ROOT / "STOP").exists(),
        market_open=lambda: MarketHours.is_market_open(),
        sleep=time.sleep, now=datetime.now,
    )


def _cmd_start(dry_run: bool) -> int:
    if dry_run:
        print("DRY-RUN start plan (dependency order):")
        for name in ["flask", "ingestor", "poller", "session", "eod"]:
            spec = CHILDREN[name]
            print(f"  {name:9} -> {' '.join(spec.argv)}"
                  + (" [new group]" if spec.new_group else ""))
        return 0
    if not pidfile.acquire_lock(ORCH_LOCK):
        print(f"another orchestrator is running (see {ORCH_LOCK})")
        return 1
    started: dict = {}
    sup = Supervisor(started=started)
    try:
        outcome = start_sequence(_live_deps(started))
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
