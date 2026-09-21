import json
import os
import time
import sys
from datetime import datetime, timedelta
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
    calls = {"spawned": [], "catchup": 0, "login": 0, "adopted": [], "events": []}

    def spawn(spec, **kw):
        calls["spawned"].append(spec.name)
        calls["events"].append(spec.name)
        return _FakePopen(spec.argv)

    base = dict(
        spawn=spawn,
        child_alive=lambda spec: spec.name == "eod",   # eod already up (adopt)
        token_fresh=lambda: True,
        open_login=lambda: calls.__setitem__("login", calls["login"] + 1),
        preflight=lambda: "GO",
        marks_warm=lambda: True,
        vix_warm=lambda: True,
        dispatch_catchup=lambda: calls.__setitem__("catchup", calls["catchup"] + 1),
        refresh_master=lambda: calls["events"].append("refresh_master"),
        stop_present=lambda: False,
        market_open=lambda: True,
        # The session's gate is the DERIVATIVES segment, not cash — cash closes
        # at 15:15 post-CAS while the F&O session runs to 15:40.
        derivatives_open=lambda: True,
        sleep=lambda s: None,
        now=lambda: datetime(2026, 8, 11, 9, 30),
        adopt=lambda spec: calls["adopted"].append(spec.name),
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


def test_warmup_supervises_crashed_children():
    """2026-08-21: a child that dies during warm-up (the ingestor at startup)
    must be revived by the supervise hook, or the feed it owns can never warm
    and the sequence always times out."""
    supervised = []
    deps, calls = _deps(vix_warm=lambda: False,
                        supervise=lambda: supervised.append(1))
    assert orch.start_sequence(deps, warmup_timeout_s=0.0) == "timeout:warmup"
    assert supervised, "supervise must run inside the warm-up wait"


def test_final_gate_supervises_crashed_children():
    supervised = []
    deps, calls = _deps(preflight=lambda: "NO-GO", vix_warm=lambda: False,
                        supervise=lambda: supervised.append(1))
    assert orch.start_sequence(deps, warmup_timeout_s=0.0) == "timeout:warmup"
    assert supervised, "supervise must run inside the final-gate wait"
    assert "session" not in calls["spawned"]


def test_refuses_on_stop_file_before_any_spawn():
    deps, calls = _deps(stop_present=lambda: True)
    assert orch.start_sequence(deps) == "blocked:stop"
    assert calls["spawned"] == []                 # refuse before Flask, no spawns


def test_parks_until_derivatives_open_then_starts():
    opens = iter([False, False, True])            # opens on the 3rd poll
    deps, calls = _deps(derivatives_open=lambda: next(opens))
    assert orch.start_sequence(deps) == "started"
    assert "session" in calls["spawned"]


def test_session_is_gated_on_derivatives_not_cash():
    """2026-09-08: the park read the CASH clock, which closes at 15:15 post-CAS
    while the F&O session runs to 15:40. Between those the orchestrator parked
    and silently refused to start the session — so its own 15:35 exit could
    never fire, and a restart in that window brought up every child EXCEPT the
    one the stack exists to run."""
    deps, calls = _deps(market_open=lambda: False,      # cash shut at 15:15
                        derivatives_open=lambda: True)  # F&O open until 15:40
    assert orch.start_sequence(deps) == "started"
    assert "session" in calls["spawned"]


def test_park_does_not_end_on_the_cash_close():
    """The mirror case: cash open, derivatives shut, is not a real market state
    (derivatives hours are a superset) — but the gate must follow derivatives
    even so, or it inherits the same bug in the other direction."""
    deps, calls = _deps(market_open=lambda: True,
                        derivatives_open=lambda: False)
    assert orch.start_sequence(deps) == "timeout:market_open"
    assert "session" not in calls["spawned"]


def test_adopted_children_are_registered_for_supervision():
    """`eod` is already alive, so it is adopted rather than spawned. It must
    still become supervised — an adopted child was previously invisible to the
    supervisor and could die unnoticed."""
    deps, calls = _deps()
    assert orch.start_sequence(deps) == "started"
    assert "eod" not in calls["spawned"]
    assert "eod" in calls["adopted"]


# --------------------------------------------------------------------------- #
# F2 (ops shakedown 2026-08-10): warm-up park must be symmetric — wait on VIX /
# ingestor warmth too, and the final preflight gate must retry/park on "still
# warming" rather than hard-shutting-down the stack.
# --------------------------------------------------------------------------- #
def test_warmup_waits_for_vix_too():
    warms = iter([False, False, True])            # VIX warms on the 3rd poll
    deps, calls = _deps(vix_warm=lambda: next(warms))
    assert orch.start_sequence(deps) == "started"
    assert "session" in calls["spawned"]


def test_final_gate_retries_while_warming_not_shutdown():
    # VIX is cold when the gate first runs (preflight NO-GO) but warms up; the
    # sequence must park/retry, NOT return blocked and let _cmd_start tear down.
    state = {"n": 0}

    def vix_warm():
        state["n"] += 1
        return state["n"] >= 3

    deps, calls = _deps(preflight=lambda: "GO" if vix_warm() else "NO-GO",
                        vix_warm=vix_warm)
    assert orch.start_sequence(deps) == "started"
    assert "session" in calls["spawned"]


def test_final_gate_halts_on_genuine_block():
    # Warm marks+VIX but preflight still NO-GO → the block is genuine (token/STOP),
    # so the sequence must halt, not loop forever.
    deps, calls = _deps(preflight=lambda: "NO-GO")
    assert orch.start_sequence(deps) == "blocked:preflight"
    assert "session" not in calls["spawned"]


def test_final_gate_warming_times_out():
    deps, calls = _deps(preflight=lambda: "NO-GO", vix_warm=lambda: False)
    assert orch.start_sequence(deps, warmup_timeout_s=0.0) == "timeout:warmup"
    assert "session" not in calls["spawned"]


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


# --------------------------------------------------------------------------- #
# Catch-up download: at most one dispatch per calendar day
# --------------------------------------------------------------------------- #
def test_catchup_due_when_no_stamp(tmp_path):
    assert orch._catchup_due(stamp_path=tmp_path / "absent.json",
                             now=datetime(2026, 9, 3, 9, 20)) is True


def test_catchup_not_due_after_todays_stamp(tmp_path):
    stamp = tmp_path / "last_catchup.json"
    orch._record_catchup(stamp_path=stamp, now=datetime(2026, 9, 3, 9, 20))
    assert orch._catchup_due(stamp_path=stamp,
                            now=datetime(2026, 9, 3, 14, 55)) is False


def test_catchup_due_again_the_next_day(tmp_path):
    stamp = tmp_path / "last_catchup.json"
    orch._record_catchup(stamp_path=stamp, now=datetime(2026, 9, 3, 9, 20))
    assert orch._catchup_due(stamp_path=stamp,
                            now=datetime(2026, 9, 4, 9, 20)) is True


def test_catchup_due_when_stamp_is_corrupt(tmp_path):
    stamp = tmp_path / "last_catchup.json"
    stamp.write_text("not json", encoding="utf-8")
    assert orch._catchup_due(stamp_path=stamp,
                             now=datetime(2026, 9, 3, 9, 20)) is True


def test_dispatch_catchup_spawns_once_per_day(tmp_path, monkeypatch):
    stamp = tmp_path / "last_catchup.json"
    spawned = []
    monkeypatch.setattr(orch.subprocess, "Popen",
                        lambda argv, **kw: spawned.append(argv) or _FakePopen(argv))
    orch._dispatch_catchup(stamp_path=stamp, log_dir=tmp_path)
    orch._dispatch_catchup(stamp_path=stamp, log_dir=tmp_path)
    orch._dispatch_catchup(stamp_path=stamp, log_dir=tmp_path)
    assert len(spawned) == 1
    assert "download_all_data.py" in spawned[0][-1]


def test_dispatch_catchup_captures_output_to_a_dated_log(tmp_path, monkeypatch):
    # The detached catch-up used to discard its output, so a failed refresh left no trace.
    seen = {}
    monkeypatch.setattr(orch.subprocess, "Popen",
                        lambda argv, **kw: seen.update(kw) or _FakePopen(argv))
    orch._dispatch_catchup(stamp_path=tmp_path / "last_catchup.json", log_dir=tmp_path / "logs")
    log = Path(seen["stdout"].name)
    assert log.parent == tmp_path / "logs" and log.name.startswith("catchup_")
    assert seen["stderr"] is orch.subprocess.STDOUT
    assert seen["env"]["PYTHONIOENCODING"] == "utf-8"


# --------------------------------------------------------------------------- #
# Wall poller adopted as a supervised, natively-locked child
# --------------------------------------------------------------------------- #
def test_wall_poller_is_a_native_locked_child():
    spec = orch.CHILDREN["wall_poller"]
    assert spec.native_lock is not None and spec.pid_path is None
    assert "options_wall_poller.py" in spec.argv[-1]


def test_happy_path_ensures_wall_poller():
    deps, calls = _deps()
    assert orch.start_sequence(deps) == "started"
    assert "wall_poller" in calls["spawned"]


def test_stop_skips_wall_poller(monkeypatch, tmp_path):
    # natively-locked children are never torn down by `stop` (like poller/eod)
    stops = []
    monkeypatch.setattr(orch, "stop_child", lambda spec, proc, **k: stops.append(spec.name))
    monkeypatch.setattr(orch.pidfile, "read_pid", lambda p: None)
    orch._cmd_stop()
    assert "wall_poller" not in stops


class _StoppablePopen(_FakePopen):
    def terminate(self):
        self._alive = False


def _status(path: Path, age_s: float, pid: int = None) -> Path:
    hb = datetime.now() - timedelta(seconds=age_s)
    payload = {"last_heartbeat": hb.isoformat()}
    if pid is not None:
        payload["pid"] = pid
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _dead_pid() -> int:
    import subprocess
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_stop_child_removes_the_child_pid_file(tmp_path):
    """A stopped child must not leave a pidfile the next start can adopt.

    release_lock defaulted to os.getpid(), which never equals the child's pid,
    so the file always survived (2026-09-08: adopted a recycled PID, then one
    still exiting).
    """
    pidp = tmp_path / "market_ingestor.pid"
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp)
    proc = _StoppablePopen([])
    pidfile.write_pid(pidp, proc.pid)

    orch.stop_child(spec, proc)

    assert pidp.exists() is False
    assert orch.child_alive(spec) is False


def test_stop_child_leaves_a_pid_file_owned_by_someone_else(tmp_path):
    """Only the stopped child's own lock is dropped — never another holder's."""
    pidp = tmp_path / "market_ingestor.pid"
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp)
    pidfile.write_pid(pidp, os.getpid())          # a different, live holder

    orch.stop_child(spec, _StoppablePopen([]))    # pid 4321

    assert pidp.exists() is True


def test_child_alive_false_when_published_heartbeat_is_stale(tmp_path):
    """A live PID is not a live child: 19336 was recycled by conhost while the
    ingestor's own status file sat 17 h stale."""
    pidp = tmp_path / "market_ingestor.pid"
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp,
                          status_path=_status(tmp_path / "s.json", 17 * 3600))
    pidfile.write_pid(pidp, os.getpid())          # PID genuinely alive
    assert orch.child_alive(spec) is False


def test_child_alive_true_when_published_heartbeat_is_fresh(tmp_path):
    pidp = tmp_path / "market_ingestor.pid"
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp,
                          status_path=_status(tmp_path / "s.json", 5.0))
    pidfile.write_pid(pidp, os.getpid())
    assert orch.child_alive(spec) is True


def test_child_alive_falls_back_to_pid_when_status_file_absent(tmp_path):
    """Never spawn a second single-writer because a status file is missing."""
    pidp = tmp_path / "market_ingestor.pid"
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp,
                          status_path=tmp_path / "absent.json")
    pidfile.write_pid(pidp, os.getpid())
    assert orch.child_alive(spec) is True


def test_child_alive_trusts_the_published_pid_over_a_clobbered_pidfile(tmp_path):
    """2026-09-09 and 2026-09-15: one false negative made the supervisor spawn a
    duplicate ingestor, spawn() overwrote the pidfile with its PID, the duplicate
    died on the port-5555 bind, and the pidfile named a dead process forever —
    a respawn every ~20 s beside a healthy incumbent. The status file is written
    by the child about itself and never by the supervisor."""
    pidp = tmp_path / "market_ingestor.pid"
    pidfile.write_pid(pidp, _dead_pid())          # clobbered by a doomed duplicate
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp,
                          status_path=_status(tmp_path / "s.json", 1.0, pid=os.getpid()))
    assert orch.child_alive(spec) is True


def test_child_alive_false_when_the_published_pid_is_dead(tmp_path):
    """The mirror: a fresh heartbeat from a child that has since exited is dead,
    even if the pidfile's PID was recycled by another live process."""
    pidp = tmp_path / "market_ingestor.pid"
    pidfile.write_pid(pidp, os.getpid())
    spec = orch.ChildSpec(name="ingestor", argv=[], pid_path=pidp,
                          status_path=_status(tmp_path / "s.json", 1.0, pid=_dead_pid()))
    assert orch.child_alive(spec) is False


# --------------------------------------------------------------------------- #
# Supervision gap (2026-09-08): the session stopped mid-window and was never
# revived, while the supervise loop ran on reporting nothing wrong.
# --------------------------------------------------------------------------- #

class _DeadProc:
    """A child that exited cleanly — poll() is 0, not None."""
    pid = 4321

    def poll(self):
        return 0


def _supervisor(alive, **kw):
    spawned = []

    def spawn(spec):
        spawned.append(spec.name)
        return _FakePopen(spec.argv)

    started = kw.pop("started")
    sup = orch.Supervisor(started=started, spawn=spawn,
                          child_alive=lambda spec: alive.get(spec.name, False),
                          stopper=lambda spec, proc: None, **kw)
    return sup, spawned


def test_adopted_child_that_dies_is_restarted():
    """The 2026-09-08 hole: tick() iterated only children this process SPAWNED,
    so an adopted session could exit and never be revived."""
    started = {}
    sup, spawned = _supervisor({"session": True}, started=started,
                               spawn_grace_s=0.0)
    sup.adopt(orch.CHILDREN["session"])          # adopted: registered, no handle
    assert "session" in started

    sup.tick()
    assert spawned == []                          # alive -> untouched

    sup2, spawned2 = _supervisor({"session": False}, started=started,
                                 spawn_grace_s=0.0)
    sup2.tick()
    assert spawned2 == ["session"]                # gone -> revived


def test_cleanly_exited_child_is_restarted():
    """A clean exit leaves poll() == 0. The old test was
    `proc_dead and not child_alive`, which needed a proc handle to notice —
    liveness now comes from the child's own lock, which covers both."""
    started = {"session": _DeadProc()}
    sup, spawned = _supervisor({"session": False}, started=started,
                               spawn_grace_s=0.0)
    sup.tick()
    assert spawned == ["session"]


def test_spawn_grace_prevents_a_respawn_storm():
    """Liveness is read from a lock the child writes at startup, so a freshly
    spawned child reads as dead until it does. Without a grace window the
    supervisor would respawn it every tick."""
    started = {}
    sup, spawned = _supervisor({"session": False}, started=started,
                               spawn_grace_s=300.0)
    sup.adopt(orch.CHILDREN["session"])
    sup.tick()
    assert spawned == ["session"]                 # first revival
    sup.tick()
    sup.tick()
    assert spawned == ["session"]                 # still inside the grace window


def test_shutdown_skips_an_adopted_child_with_no_handle():
    """An adopted, natively-locked child has no pidfile and so no handle;
    shutdown must skip it rather than raise on None."""
    stopped = []
    started = {"poller": None, "session": _DeadProc()}
    sup = orch.Supervisor(started=started, spawn=lambda spec: None,
                          child_alive=lambda spec: True,
                          stopper=lambda spec, proc: stopped.append(spec.name))
    sup.shutdown()
    assert stopped == ["session"]


# --------------------------------------------------------------------------- #
# Instrument-master refresh (2026-09-15): run_refresh had no caller, and the
# OAuth-callback backstop is skipped by a surviving token or a CLI login, so
# snapshots stopped at 2026-09-08 while four sessions ran.
# --------------------------------------------------------------------------- #
def test_master_refreshed_before_any_child_spawns():
    """The chain poller resolves expiries from the master, and Flask's OAuth
    callback writes it — refresh before either exists."""
    deps, calls = _deps()
    assert orch.start_sequence(deps) == "started"
    events = calls["events"]
    assert events[0] == "refresh_master"
    assert events.count("refresh_master") == 1
    assert events.index("refresh_master") < events.index("flask") < events.index("poller")


def test_stop_file_refuses_before_master_refresh():
    deps, calls = _deps(stop_present=lambda: True)
    assert orch.start_sequence(deps) == "blocked:stop"
    assert calls["events"] == []


def _master(tmp_path, mtime: datetime) -> Path:
    db = tmp_path / "nse_fo_instruments.duckdb"
    db.write_bytes(b"")
    os.utime(db, (mtime.timestamp(), mtime.timestamp()))
    return db


def test_refresh_master_runs_when_master_is_from_a_previous_day(tmp_path):
    db = _master(tmp_path, datetime(2026, 9, 8, 9, 27))
    seen = []
    orch._refresh_master(db_path=db, run=lambda db_path: seen.append(db_path) or 0,
                         now=datetime(2026, 9, 15, 9, 10))
    assert seen == [db]


def test_refresh_master_runs_when_master_is_absent(tmp_path):
    seen = []
    orch._refresh_master(db_path=tmp_path / "absent.duckdb",
                         run=lambda db_path: seen.append(db_path) or 0,
                         now=datetime(2026, 9, 15, 9, 10))
    assert len(seen) == 1


def test_refresh_master_skips_when_already_refreshed_today(tmp_path):
    """A mid-session restart must not rewrite the store under live readers."""
    db = _master(tmp_path, datetime(2026, 9, 15, 9, 5))
    seen = []
    orch._refresh_master(db_path=db, run=lambda db_path: seen.append(db_path) or 0,
                         now=datetime(2026, 9, 15, 11, 40))
    assert seen == []


def test_refresh_master_failure_is_non_blocking(tmp_path, caplog):
    db = _master(tmp_path, datetime(2026, 9, 8, 9, 27))

    def boom(db_path):
        raise OSError("database is locked")

    orch._refresh_master(db_path=db, run=boom, now=datetime(2026, 9, 15, 9, 10))
    orch._refresh_master(db_path=db, run=lambda db_path: 3, now=datetime(2026, 9, 15, 9, 10))
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("database is locked" in w for w in warnings)
    assert any("exit 3" in w for w in warnings)


def test_refresh_master_survives_a_broken_import(tmp_path, monkeypatch, caplog):
    """The refresh module pulls in duckdb/pyarrow; a broken install must cost one
    refresh, not raise out of start_sequence before Flask exists."""
    import scripts
    # `from scripts import x` reads the package attribute first, which an earlier
    # test's import leaves behind — clear both so the import really fails.
    monkeypatch.setitem(sys.modules, "scripts.fetch_instrument_master", None)
    monkeypatch.delattr(scripts, "fetch_instrument_master", raising=False)
    orch._refresh_master(db_path=tmp_path / "absent.duckdb", now=datetime(2026, 9, 15, 9, 10))
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_child_alive_false_when_native_lock_pid_was_recycled(tmp_path):
    """A stale poller lock whose PID now belongs to another process (msedge,
    2026-09-21) must read dead so the poller is spawned, not adopted."""
    lock = tmp_path / "chain_poller.pid"
    spec = orch.ChildSpec(name="poller", argv=[], native_lock=lock)
    pidfile.write_pid(lock, os.getpid())
    t = time.time() - 30 * 86400
    os.utime(lock, (t, t))
    assert orch.child_alive(spec) is False
