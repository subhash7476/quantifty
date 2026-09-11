import os
import subprocess
import sys

import pytest

import scripts.market_ingestor as mi


@pytest.fixture
def lock(tmp_path, monkeypatch):
    # Never let a test touch the live data/market_ingestor.pid.
    pid_file = tmp_path / "market_ingestor.pid"
    monkeypatch.setattr(mi, "PID_FILE", pid_file)
    # os.kill(pid, 0) on Windows is GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid):
    # record instead of delivering Ctrl+C into the pytest console.
    kills = []
    if os.name == "nt":
        monkeypatch.setattr(os, "kill", lambda pid, sig: kills.append((pid, sig)))
    daemon = mi.MarketIngestorDaemon.__new__(mi.MarketIngestorDaemon)
    return daemon, pid_file, kills


def test_acquire_lock_reclaims_pid_of_exited_process(lock):
    daemon, pid_file, kills = lock
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()  # `p` stays referenced, so its handle is still open
    pid_file.write_text(str(p.pid))

    daemon._acquire_lock()

    assert pid_file.read_text() == str(os.getpid())
    if os.name == "nt":
        assert kills == []


def test_acquire_lock_exits_when_holder_pid_alive(lock):
    daemon, pid_file, _ = lock
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        pid_file.write_text(str(p.pid))

        with pytest.raises(SystemExit):
            daemon._acquire_lock()

        assert pid_file.read_text() == str(p.pid)
    finally:
        p.kill()
        p.wait()


def test_acquire_lock_reclaims_garbage_pid_file(lock):
    daemon, pid_file, _ = lock
    pid_file.write_text("not-a-pid")

    daemon._acquire_lock()

    assert pid_file.read_text() == str(os.getpid())
