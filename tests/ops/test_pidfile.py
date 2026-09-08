import os
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
