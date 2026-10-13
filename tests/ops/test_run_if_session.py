from datetime import date

from scripts.ops import run_if_session as ris


def _run(target, today, tmp_path, runner_rc=0):
    calls, alerts = [], []

    def runner(script, args):
        calls.append((script.name, args))
        return runner_rc

    rc = ris.main([target], today=today, runner=runner, alert=alerts.append,
                  log_path=tmp_path / "scheduled_runs.log")
    return rc, calls, alerts, (tmp_path / "scheduled_runs.log").read_text(encoding="utf-8")


def test_skips_on_nse_holiday(tmp_path):
    rc, calls, alerts, log = _run("orchestrator", date(2026, 10, 2), tmp_path)
    assert (rc, calls, alerts) == (0, [], [])
    assert "SKIP" in log


def test_skips_on_weekend(tmp_path):
    rc, calls, _, _ = _run("download", date(2026, 9, 26), tmp_path)
    assert (rc, calls) == (0, [])


def test_runs_additional_weekend_session(tmp_path):
    rc, calls, _, _ = _run("download", date(2026, 2, 1), tmp_path)
    assert (rc, calls) == (0, [("download_all_data.py", [])])


def test_runs_target_on_trading_day_and_passes_extra_args(tmp_path):
    calls, alerts = [], []
    rc = ris.main(["orchestrator", "--", "--dry-run"], today=date(2026, 9, 25),
                  runner=lambda s, a: calls.append((s.name, a)) or 0,
                  alert=alerts.append, log_path=tmp_path / "log")
    assert rc == 0
    assert calls == [("orchestrator.py", ["--dry-run"])]
    assert alerts == []


def test_nonzero_target_exit_is_propagated_and_alerted(tmp_path):
    rc, _, alerts, log = _run("download", date(2026, 9, 25), tmp_path, runner_rc=1)
    assert rc == 1
    assert len(alerts) == 1 and "exit 1" in alerts[0]
    assert "exit 1" in log


def test_outside_calendar_coverage_fails_loudly(tmp_path):
    rc, calls, alerts, log = _run("orchestrator", date(2027, 1, 4), tmp_path)
    assert rc == 2
    assert calls == []
    assert len(alerts) == 1 and "nse_holidays" in alerts[0]
    assert "ERROR" in log


def test_straddle_capture_target_points_at_the_capture_script(tmp_path):
    assert ris.TARGETS["straddle_capture"].is_file()
    rc, calls, _, _ = _run("straddle_capture", date(2026, 10, 12), tmp_path)
    assert (rc, calls) == (0, [("straddle_cycle_capture.py", [])])


def test_run_target_turns_an_unexpected_exception_into_exit_1(monkeypatch, tmp_path):
    # An uncaught exception skipped the END line and the Telegram alert, leaving
    # only a bare LastTaskResult in Task Scheduler.
    import scripts.ops.run_if_session as rs

    def _boom(path, run_name=None):
        raise RuntimeError("respawn failed")

    monkeypatch.setattr(rs.runpy, "run_path", _boom)
    assert rs._run_target(tmp_path / "t.py", []) == 1


# --- per-run output log (the 2026-10-08 orchestrator exit-1 left no trace) ---

def _noisy_runner(script, args):
    import sys
    print("start sequence: ok")
    print("preflight failed: token", file=sys.stderr)
    return 1


def test_target_output_lands_in_a_per_target_per_day_log(tmp_path, capsys):
    alerts = []
    rc = ris.main(["orchestrator"], today=date(2026, 10, 14), runner=_noisy_runner,
                  alert=alerts.append, log_path=tmp_path / "scheduled_runs.log")
    run_log = tmp_path / "logs" / "orchestrator_2026-10-14.log"
    text = run_log.read_text(encoding="utf-8")
    assert rc == 1
    assert "start sequence: ok" in text and "preflight failed: token" in text
    # still visible to anyone watching the console (the token-approval prompt)
    out = capsys.readouterr()
    assert "start sequence: ok" in out.out and "preflight failed: token" in out.err
    # the scheduler log and the alert point at it
    sched = (tmp_path / "scheduled_runs.log").read_text(encoding="utf-8")
    assert str(run_log) in sched
    assert str(run_log) in alerts[0]


def test_an_uncaught_target_exception_traceback_is_in_the_run_log(monkeypatch, tmp_path):
    import scripts.ops.run_if_session as rs

    def _boom(path, run_name=None):
        raise RuntimeError("respawn failed")

    monkeypatch.setattr(rs.runpy, "run_path", _boom)
    rc = rs.main(["download"], today=date(2026, 10, 14), runner=rs._run_target,
                 alert=lambda m: None, log_path=tmp_path / "scheduled_runs.log")
    text = (tmp_path / "logs" / "download_2026-10-14.log").read_text(encoding="utf-8")
    assert rc == 1
    assert "RuntimeError: respawn failed" in text


def test_streams_are_restored_and_a_missing_console_still_logs(monkeypatch, tmp_path):
    import sys
    monkeypatch.setattr(sys, "stdout", None)     # pythonw / no console attached
    before = (sys.stdout, sys.stderr)
    ris.main(["download"], today=date(2026, 10, 14), runner=_noisy_runner,
             alert=lambda m: None, log_path=tmp_path / "scheduled_runs.log")
    assert (sys.stdout, sys.stderr) == before
    text = (tmp_path / "logs" / "download_2026-10-14.log").read_text(encoding="utf-8")
    assert "start sequence: ok" in text


def test_a_skipped_day_writes_no_run_log(tmp_path):
    _run("orchestrator", date(2026, 10, 2), tmp_path)
    assert not (tmp_path / "logs").exists()
