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
