import os
import time
from pathlib import Path

from scripts.ops import pidfile


def test_pid_alive_true_for_current_process():
    assert pidfile.pid_alive(os.getpid()) is True


def test_pid_alive_false_for_absent_pid():
    assert pidfile.pid_alive(2_000_000_000) is False
    assert pidfile.pid_alive(0) is False


def test_acquire_write_read_release_cycle(tmp_path):
    lock = tmp_path / "x.pid"
    assert pidfile.acquire_lock(lock) is True
    assert pidfile.read_pid(lock) == os.getpid()
    assert pidfile.lock_alive(lock) is True
    pidfile.release_lock(lock)
    assert lock.exists() is False


def test_acquire_refuses_when_live_pid_present(tmp_path):
    lock = tmp_path / "x.pid"
    pidfile.write_pid(lock, os.getpid())          # a "live" holder
    assert pidfile.acquire_lock(lock) is False


def test_acquire_overwrites_stale_pid(tmp_path):
    lock = tmp_path / "x.pid"
    pidfile.write_pid(lock, 2_000_000_000)        # dead pid
    assert pidfile.acquire_lock(lock) is True
    assert pidfile.read_pid(lock) == os.getpid()


def test_release_lock_drops_a_lock_held_by_another_pid(tmp_path):
    """Child pidfiles hold the child's pid, not ours — the caller names it."""
    lock = tmp_path / "child.pid"
    pidfile.write_pid(lock, 4321)
    pidfile.release_lock(lock, 4321)
    assert lock.exists() is False


def test_release_lock_keeps_a_lock_held_by_a_different_pid(tmp_path):
    lock = tmp_path / "child.pid"
    pidfile.write_pid(lock, 4321)
    pidfile.release_lock(lock, 9999)
    assert lock.exists() is True


def _backdate(path: Path, seconds: float) -> None:
    t = time.time() - seconds
    os.utime(path, (t, t))


def test_lock_alive_false_when_pid_was_recycled_after_the_lock_was_written(tmp_path):
    """2026-09-21: the poller's lock named 21948 from Friday; Monday 05:03 msedge
    got that PID, the orchestrator adopted Edge as the poller and never spawned
    one. A holder that started AFTER its lock was written is not the holder."""
    lock = tmp_path / "chain_poller.pid"
    pidfile.write_pid(lock, os.getpid())
    _backdate(lock, 30 * 86400)                   # written long before we started
    assert pidfile.pid_alive(os.getpid()) is True
    assert pidfile.lock_alive(lock) is False


def test_acquire_reclaims_a_lock_whose_pid_was_recycled(tmp_path):
    lock = tmp_path / "x.pid"
    pidfile.write_pid(lock, os.getpid())
    _backdate(lock, 30 * 86400)
    assert pidfile.acquire_lock(lock) is True


def test_process_started_at_is_before_now_for_current_process():
    started = pidfile.process_started_at(os.getpid())
    if started is None:
        return                                    # platform without a start-time source
    assert started <= time.time()
