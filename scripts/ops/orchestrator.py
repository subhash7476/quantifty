"""NiftyShield ops orchestrator — foreground supervisor for the PAPER window.

Manages Flask, market_ingestor, chain_poller, the PAPER session, and the EOD
worker; starts them in dependency order behind a preflight gate; restarts crashed
children; stops them cleanly. See the design spec for the full contract.
"""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

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
