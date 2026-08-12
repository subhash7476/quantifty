"""Windows-safe PID/lock helpers for the ops supervisor.

Consolidates the `_pid_alive` pattern already used in `schedule_worker.py` and
`chain_poller.py`: NEVER `os.kill(pid, 0)` on Windows (CPython maps signals to
TerminateProcess). Uses OpenProcess on Windows.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        if hasattr(ctypes, "windll"):
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def read_pid(path: Path) -> Optional[int]:
    try:
        return int(Path(path).read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def write_pid(path: Path, pid: Optional[int] = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid if pid is not None else os.getpid()), encoding="utf-8")


def lock_alive(path: Path) -> bool:
    pid = read_pid(path)
    return pid is not None and pid_alive(pid)


def acquire_lock(path: Path) -> bool:
    """Single-instance guard: refuse if a live PID holds the lock, else claim it."""
    if lock_alive(path):
        return False
    write_pid(path)
    return True


def release_lock(path: Path) -> None:
    path = Path(path)
    if read_pid(path) == os.getpid():
        try:
            path.unlink()
        except OSError:
            pass
