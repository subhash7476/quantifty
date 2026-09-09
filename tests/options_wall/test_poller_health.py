"""A failing step must be visible in the heartbeat within one cycle."""
import json

import duckdb
import pytest

from core.options_wall.poller import WallPoller


def _poller(tmp_path):
    return WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                      snapshot_db_path=tmp_path / "s.duckdb",
                      results_db_path=tmp_path / "r.duckdb")


@pytest.fixture(autouse=True)
def _no_telegram(monkeypatch):
    """No test may reach the real notifier — a structural failure alerts by design."""
    class Silent:
        def send_message(self, text):
            pass
    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Silent())


def test_structural_failure_lands_in_the_heartbeat(tmp_path):
    p = _poller(tmp_path)
    p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))
    p._write_heartbeat({"NIFTY": 74})
    hb = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert hb["status"] == "DEGRADED"
    assert hb["steps"]["NIFTY"]["executor"]["ok"] is False
    assert hb["steps"]["NIFTY"]["executor"]["error_type"] == "ConstraintException"
    assert hb["rows"] == {"NIFTY": 74}
    assert "last_snapshot" in hb


def test_healthy_cycle_reports_ok(tmp_path):
    p = _poller(tmp_path)
    p._record_step("executor", "NIFTY")
    p._write_heartbeat({"NIFTY": 74})
    hb = json.loads((tmp_path / "hb.json").read_text(encoding="utf-8"))
    assert hb["status"] == "OK"
    assert hb["steps"]["NIFTY"]["executor"]["ok"] is True


def test_alert_delivery_failure_does_not_propagate(tmp_path, monkeypatch):
    p = _poller(tmp_path)

    class Boom:
        def send_message(self, text):
            raise RuntimeError("telegram down")

    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Boom())
    p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))


def test_alert_is_sent_once_for_a_persistent_fault(tmp_path, monkeypatch):
    p = _poller(tmp_path)
    sent = []

    class Spy:
        def send_message(self, text):
            sent.append(text)

    monkeypatch.setattr("core.alerts.telegram_notifier.TelegramNotifier", lambda: Spy())
    for _ in range(50):
        p._record_step("executor", "NIFTY", duckdb.ConstraintException("Duplicate key"))
    assert len(sent) == 1
    assert "NIFTY" in sent[0] and "executor" in sent[0]


def test_an_exception_with_an_empty_message_does_not_crash(tmp_path):
    """`AssertionError()` stringifies to "", and "".splitlines() is []."""
    p = _poller(tmp_path)
    p._record_step("executor", "NIFTY", AssertionError())
