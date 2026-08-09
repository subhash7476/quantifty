"""NiftyShield ops orchestrator — foreground supervisor for the PAPER window.

Manages Flask, market_ingestor, chain_poller, the PAPER session, and the EOD
worker; starts them in dependency order behind a preflight gate; restarts crashed
children; stops them cleanly. See the design spec for the full contract.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
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
