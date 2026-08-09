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
