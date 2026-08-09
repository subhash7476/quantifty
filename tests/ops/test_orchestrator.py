import os
from pathlib import Path

from scripts.ops import orchestrator as orch
from scripts.ops import pidfile


class _FakePopen:
    def __init__(self, argv, **kw):
        self.argv = argv
        self.kw = kw
        self.pid = 4321
        self._alive = True

    def poll(self):
        return None if self._alive else 0


def test_spawn_owned_writes_pid_file(tmp_path):
    pidp = tmp_path / "flask.pid"
    spec = orch.ChildSpec(name="flask", argv=["python", "x"], pid_path=pidp)
    captured = {}

    def fake_popen(argv, **kw):
        captured["argv"], captured["kw"] = argv, kw
        return _FakePopen(argv, **kw)

    proc = orch.spawn(spec, popen=fake_popen)
    assert captured["argv"] == ["python", "x"]
    assert pidfile.read_pid(pidp) == proc.pid


def test_child_alive_owned_reads_pid_file(tmp_path):
    pidp = tmp_path / "flask.pid"
    spec = orch.ChildSpec(name="flask", argv=[], pid_path=pidp)
    assert orch.child_alive(spec) is False
    pidfile.write_pid(pidp, os.getpid())
    assert orch.child_alive(spec) is True


def test_child_alive_native_lock_reads_lock_file(tmp_path):
    lock = tmp_path / "chain_poller.pid"
    spec = orch.ChildSpec(name="poller", argv=[], native_lock=lock)
    pidfile.write_pid(lock, os.getpid())
    assert orch.child_alive(spec) is True


def test_session_child_spawns_in_new_group():
    spec = orch.CHILDREN["session"]
    assert spec.new_group is True
    assert "session.py" in " ".join(spec.argv)
    assert "--no-record" not in spec.argv        # recording must stay ON (F-B1)
