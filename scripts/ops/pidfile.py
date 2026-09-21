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
        from ctypes import wintypes
        if hasattr(ctypes, "windll"):
            # OpenProcess(SYNCHRONIZE) returns a non-null handle for a *zombie*
            # process (a PID whose process object still lingers after exit), so a
            # bare "did OpenProcess succeed" check wrongly reports dead children as
            # alive and the supervisor never respawns them. GetExitCodeProcess ==
            # STILL_ACTIVE is the reliable liveness test (mirrors schedule_worker).
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = wintypes.DWORD()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(ok) and exit_code.value == STILL_ACTIVE
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


# FILETIME resolution and filesystem mtime granularity; a recycled PID would have
# to be reused within this window of the lock being written.
_START_TOLERANCE_S = 2.0
_EPOCH_AS_FILETIME = 116444736000000000


def process_started_at(pid: int) -> Optional[float]:
    """Creation time of `pid` as epoch seconds, or None where unavailable."""
    if os.name != "nt" or pid <= 0:
        return None
    import ctypes
    from ctypes import wintypes
    if not hasattr(ctypes, "windll"):
        return None
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    ok = ctypes.windll.kernel32.GetProcessTimes(
        handle, ctypes.byref(created), ctypes.byref(exited),
        ctypes.byref(kernel), ctypes.byref(user))
    ctypes.windll.kernel32.CloseHandle(handle)
    if not ok:
        return None
    ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
    return (ticks - _EPOCH_AS_FILETIME) / 1e7


def lock_alive(path: Path) -> bool:
    """The PID in `path` is alive AND is the process that wrote the lock.

    A bare live PID is not a live holder: a lock left by a killed process names
    a PID Windows later hands to anything. The chain poller's Friday lock named
    21948; Monday 05:03 msedge got it, and the orchestrator adopted Edge as the
    poller and never spawned one (2026-09-21). Every holder writes its lock after
    it starts, so a process created after the lock's mtime is a recycled PID.
    """
    pid = read_pid(path)
    if pid is None or not pid_alive(pid):
        return False
    started = process_started_at(pid)
    if started is None:
        return True
    try:
        written = Path(path).stat().st_mtime
    except OSError:
        return False
    return started <= written + _START_TOLERANCE_S


def acquire_lock(path: Path) -> bool:
    """Single-instance guard: refuse if a live PID holds the lock, else claim it."""
    if lock_alive(path):
        return False
    write_pid(path)
    return True


def release_lock(path: Path, pid: Optional[int] = None) -> None:
    """Drop the lock when it belongs to `pid` (default: this process).

    Child pidfiles hold the CHILD's pid, so the os.getpid() default never
    matched and every stopped child left its pidfile behind. A surviving file
    lets the next start adopt a phantom: a recycled PID (2026-09-08 09:26) or
    one still exiting from the previous run (2026-09-08 10:03).
    """
    path = Path(path)
    if read_pid(path) == (os.getpid() if pid is None else pid):
        try:
            path.unlink()
        except OSError:
            pass
