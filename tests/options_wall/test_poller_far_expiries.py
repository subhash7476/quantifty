"""W3: the poller also captures Nifty's next expiries (term-structure input) into a
separate table, so no reader of option_chain_snapshot ever sees a second expiry."""
from datetime import date

import duckdb
import pytest

from core.data import options_wall_store as store
from core.data.options_provider import OptionChainRow
from core.options_wall import poller
from core.options_wall.poller import WallPoller, far_expiries

LISTED = ["2026-09-29", "2026-10-06", "2026-10-13", "2026-10-19", "2026-10-27",
          "2026-11-03", "2026-11-23", "2026-12-29", "2027-03-30"]


@pytest.mark.parametrize("today, nearest, expected", [
    # nearest has DTE >= 2: it is already stored; only the next monthly is far
    (date(2026, 9, 27), "2026-09-29", ["2026-10-27"]),
    # expiry day: first DTE>=2 weekly, then the monthly after it
    (date(2026, 9, 29), "2026-09-29", ["2026-10-06", "2026-10-27"]),
    # DTE 1 on the October monthly: next weekly, and November's monthly
    (date(2026, 10, 26), "2026-10-27", ["2026-11-03", "2026-11-23"]),
])
def test_far_expiries(today, nearest, expected):
    assert far_expiries(LISTED, today, nearest) == expected


def test_far_expiries_ignores_expired_contracts():
    assert far_expiries(["2026-09-22"] + LISTED, date(2026, 9, 27), "2026-09-29") == ["2026-10-27"]


def _rows(expiry):
    return [OptionChainRow(strike=100.0, option_type="CE", instrument_key=f"NSE_FO|{expiry}",
                           tradingsymbol="T", expiry=expiry, ltp=5.0, underlying_ltp=100.0)]


def test_far_table_append_leaves_main_table_untouched(tmp_path):
    db = tmp_path / "wall.duckdb"
    store.append_snapshot(_rows("2026-10-27"), "NSE_INDEX|Nifty 50", "2026-10-27",
                          db_path=db, table=store.FAR_TABLE)
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute(f"select count(*) from {store.FAR_TABLE}").fetchone()[0] == 1
    assert con.execute("select count(*) from option_chain_snapshot").fetchone()[0] == 0
    con.close()


def test_append_rejects_unknown_table(tmp_path):
    with pytest.raises(ValueError):
        store.append_snapshot(_rows("2026-10-27"), "NSE_INDEX|Nifty 50", "2026-10-27",
                              db_path=tmp_path / "w.duckdb", table="scan_results")


class _Provider:
    def __init__(self):
        self.chain_calls = []

    def get_weekly_expiry(self, sym):
        return "2026-09-29"

    def fetch_option_chain(self, sym, expiry):
        self.chain_calls.append((sym, expiry))
        return _rows(expiry)


class _Lister:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def __call__(self, index_name):
        self.calls += 1
        if self.fail:
            raise RuntimeError("instrument master locked")
        return LISTED


def _poller(tmp_path, monkeypatch, lister=None, **kw):
    monkeypatch.setattr("core.options_wall.poller._listed_expiries", lister or _Lister())
    monkeypatch.setattr(
        "core.options_wall.poller.UpstoxMarketData",
        lambda: type("M", (), {"fetch_quotes_batch": lambda self, keys: {"quotes": {}}})())
    monkeypatch.setattr("core.options_wall.poller._today", lambda: date(2026, 9, 29))
    for step in ("_executor_step", "_scan_persist_step", "_capture_baseline",
                 "_process_close_requests"):
        monkeypatch.setattr(WallPoller, step, lambda self, *a, **k: None)
    return WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                      snapshot_db_path=tmp_path / "wall.duckdb",
                      results_db_path=tmp_path / "res.duckdb", **kw)


def _expiries(db, table):
    con = duckdb.connect(str(db), read_only=True)
    out = sorted({e for (e,) in con.execute(f"select expiry_date from {table}").fetchall()})
    con.close()
    return out


def test_cycle_writes_far_expiries_to_far_table_only(tmp_path, monkeypatch):
    p = _poller(tmp_path, monkeypatch, far_underlyings=("NIFTY",))
    prov = _Provider()
    rows = p._poll_cycle(prov)
    db = tmp_path / "wall.duckdb"
    assert _expiries(db, "option_chain_snapshot") == ["2026-09-29"]
    assert _expiries(db, store.FAR_TABLE) == ["2026-10-06", "2026-10-27"]
    far_calls = [c for c in prov.chain_calls if c[1] != "2026-09-29"]
    assert {s for s, _ in far_calls} == {"NSE_INDEX|Nifty 50"}
    assert rows["NIFTY:far"] == 2


def test_far_capture_is_throttled(tmp_path, monkeypatch):
    lister = _Lister()
    p = _poller(tmp_path, monkeypatch, lister, far_underlyings=("NIFTY",), far_persist_interval_s=60.0)
    prov = _Provider()
    p._poll_cycle(prov)
    p._poll_cycle(prov)
    assert lister.calls == 1


def test_far_failure_never_blocks_the_main_append(tmp_path, monkeypatch):
    p = _poller(tmp_path, monkeypatch, _Lister(fail=True), far_underlyings=("NIFTY",))
    rows = p._poll_cycle(_Provider())
    assert _expiries(tmp_path / "wall.duckdb", "option_chain_snapshot") == ["2026-09-29"]
    assert rows["NIFTY:far"] == -1
    assert p._health.any_failing()


def test_far_capture_off_by_default(tmp_path, monkeypatch):
    lister = _Lister()
    p = _poller(tmp_path, monkeypatch, lister)
    p._poll_cycle(_Provider())
    assert lister.calls == 0


def test_listed_expiries_raises_without_master(tmp_path, monkeypatch):
    monkeypatch.setattr(poller.options_provider, "INSTRUMENT_DB_PATH", tmp_path / "absent.duckdb")
    with pytest.raises(FileNotFoundError):
        poller._listed_expiries("NIFTY")


def test_listed_expiries_reads_latest_snapshot_live_contracts(tmp_path, monkeypatch):
    db = tmp_path / "master.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create table instruments (name varchar, instrument_type varchar, expiry varchar, snapshot_date date)")
    con.execute("""insert into instruments values
        ('NIFTY','CE','2026-09-22','2026-09-27'), ('NIFTY','CE','2026-09-29','2026-09-27'),
        ('NIFTY','CE','2026-11-23','2026-09-27'), ('NIFTY','PE','2026-10-06','2026-09-27'),
        ('NIFTY','CE','2026-12-01','2026-09-20'), ('BANKNIFTY','CE','2026-10-27','2026-09-27')""")
    con.close()
    monkeypatch.setattr(poller.options_provider, "INSTRUMENT_DB_PATH", db)
    monkeypatch.setattr(poller, "_today", lambda: date(2026, 9, 27))
    assert poller._listed_expiries("NIFTY") == ["2026-09-29", "2026-11-23"]
