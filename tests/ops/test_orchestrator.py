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


# --------------------------------------------------------------------------- #
# Task 6 — start state machine (injected Deps; no processes/network/clock)
# --------------------------------------------------------------------------- #
from datetime import datetime


def _deps(**over):
    calls = {"spawned": [], "catchup": 0, "login": 0}

    def spawn(spec, **kw):
        calls["spawned"].append(spec.name)
        return _FakePopen(spec.argv)

    base = dict(
        spawn=spawn,
        child_alive=lambda spec: spec.name == "eod",   # eod already up (adopt)
        token_fresh=lambda: True,
        open_login=lambda: calls.__setitem__("login", calls["login"] + 1),
        preflight=lambda: "GO",
        marks_warm=lambda: True,
        dispatch_catchup=lambda: calls.__setitem__("catchup", calls["catchup"] + 1),
        stop_present=lambda: False,
        market_open=lambda: True,
        sleep=lambda s: None,
        now=lambda: datetime(2026, 8, 11, 9, 30),
    )
    base.update(over)
    d = orch.Deps(**base)
    return d, calls


def test_happy_path_starts_in_dependency_order():
    deps, calls = _deps()
    assert orch.start_sequence(deps) == "started"
    # flask before ingestor/poller before session; eod adopted, not re-spawned.
    order = calls["spawned"]
    assert order.index("flask") < order.index("ingestor") < order.index("session")
    assert "poller" in order and order.index("poller") < order.index("session")
    assert "eod" not in order                     # already alive → adopted
    assert calls["catchup"] == 1                  # background catch-up dispatched


def test_blocks_when_preflight_no_go():
    deps, calls = _deps(preflight=lambda: "NO-GO")
    assert orch.start_sequence(deps).startswith("blocked:")
    assert "session" not in calls["spawned"]      # never start the session on NO-GO


def test_token_gate_opens_login_then_waits():
    seq = iter([False, False, True])              # fresh on 3rd poll
    deps, calls = _deps(token_fresh=lambda: next(seq))
    assert orch.start_sequence(deps) == "started"
    assert calls["login"] == 1                    # login opened exactly once


def test_warmup_timeout_when_marks_never_warm():
    deps, calls = _deps(marks_warm=lambda: False)
    assert orch.start_sequence(deps, warmup_timeout_s=0.0) == "timeout:warmup"
    assert "session" not in calls["spawned"]


def test_refuses_on_stop_file_before_any_spawn():
    deps, calls = _deps(stop_present=lambda: True)
    assert orch.start_sequence(deps) == "blocked:stop"
    assert calls["spawned"] == []                 # refuse before Flask, no spawns


def test_parks_until_market_open_then_starts():
    opens = iter([False, False, True])            # opens on the 3rd poll
    deps, calls = _deps(market_open=lambda: next(opens))
    assert orch.start_sequence(deps) == "started"
    assert "session" in calls["spawned"]


# --------------------------------------------------------------------------- #
# Task 7 — supervise loop, cooperative stop, CLI
# --------------------------------------------------------------------------- #
import signal


def test_stop_child_session_signals_group_and_waits():
    spec = orch.CHILDREN["session"]
    proc = _FakePopen(spec.argv)
    proc.pid = 777
    sent = {}

    def killer(pid, sig):
        sent["pid"], sent["sig"] = pid, sig
        proc._alive = False

    waited = {"n": 0}
    proc.wait = lambda timeout=None: waited.__setitem__("n", waited["n"] + 1)
    orch.stop_child(spec, proc, killer=killer)
    assert sent["pid"] == 777
    # Windows → CTRL_BREAK, POSIX → SIGTERM; both are cooperative, never kill.
    expected = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM
    assert sent["sig"] == expected
    assert waited["n"] >= 1


def test_supervisor_restarts_crashed_owned_child():
    started = {"ingestor": _FakePopen([])}
    started["ingestor"]._alive = False            # crashed
    respawns = []
    sup = orch.Supervisor(
        started=started,
        spawn=lambda spec: respawns.append(spec.name) or _FakePopen([]),
        child_alive=lambda spec: False,           # pid file also dead
    )
    sup.tick()
    assert "ingestor" in respawns


def test_supervisor_shutdown_leaves_adopted_children():
    # only started children are torn down; eod (adopted, not in `started`) is left.
    stops = []
    sup = orch.Supervisor(
        started={"session": _FakePopen([])},
        spawn=lambda spec: _FakePopen([]),
        child_alive=lambda spec: True,
        stopper=lambda spec, proc: stops.append(spec.name),
    )
    sup.shutdown()
    assert stops == ["session"]                   # session only; eod untouched
