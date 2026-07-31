import sqlite3
from datetime import date, datetime, timedelta

import pytest

from app_facade.data_facade import DataFacade
from core.scheduler.eod_store import EodStore


@pytest.fixture
def facade(tmp_path):
    f = DataFacade(data_root=tmp_path)
    f._eod_store_path = tmp_path / "eod.sqlite"
    return f


def test_status_reports_disabled_and_no_worker(facade):
    st = facade.get_eod_status()
    assert st["enabled"] is False
    assert st["worker_alive"] is False


def test_toggle_enables_and_persists(facade):
    facade.set_eod_enabled(True)
    assert facade.get_eod_status()["enabled"] is True
    facade.set_eod_enabled(False)
    assert facade.get_eod_status()["enabled"] is False


def test_worker_alive_true_on_fresh_heartbeat(facade):
    EodStore(facade._eod_store_path).heartbeat(999)
    assert facade.get_eod_status()["worker_alive"] is True


def test_worker_alive_false_on_stale_heartbeat(facade):
    EodStore(facade._eod_store_path).heartbeat(999)
    stale = (datetime.now() - timedelta(minutes=10)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET worker_heartbeat=? WHERE id=1", [stale])
    con.commit()
    con.close()
    assert facade.get_eod_status()["worker_alive"] is False


def test_run_now_sets_the_trigger(facade):
    facade.trigger_eod_run_now()
    assert EodStore(facade._eod_store_path).consume_run_now() is True


def test_status_reports_attempts_today(facade):
    EodStore(facade._eod_store_path).record(date.today(), 1, "download", "retry", "")
    assert facade.get_eod_status()["attempts_today"] == 1


def test_busy_worker_counts_as_alive_despite_stale_heartbeat(facade):
    store = EodStore(facade._eod_store_path)
    store.heartbeat(999)
    store.set_busy("attempt 1")
    stale = (datetime.now() - timedelta(minutes=10)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET worker_heartbeat=? WHERE id=1", [stale])
    con.commit()
    con.close()
    st = facade.get_eod_status()
    assert st["worker_alive"] is True
    assert st["worker_busy"] is True
    assert st["busy_phase"] == "attempt 1"


def test_stale_busy_marker_ages_out(facade):
    store = EodStore(facade._eod_store_path)
    store.set_busy("attempt 1")
    ancient = (datetime.now() - timedelta(hours=3)).isoformat()
    con = sqlite3.connect(str(facade._eod_store_path))
    con.execute("UPDATE eod_automation SET busy_since=? WHERE id=1", [ancient])
    con.commit()
    con.close()
    assert facade.get_eod_status()["worker_alive"] is False
