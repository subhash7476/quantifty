"""STOCK-STRADDLE-M10 quote capture: calendar role, chunk failures, entry band, exit re-quote."""
from datetime import date, datetime

import duckdb
import pytest

from scripts.research.options_seller_edge import straddle_cycle_capture as cap

EXP = date(2026, 10, 27)


def _master(path):
    con = duckdb.connect(str(path))
    con.execute("""create table instruments (instrument_key varchar, tradingsymbol varchar,
        name varchar, expiry varchar, strike double, instrument_type varchar, lot_size integer,
        snapshot_date varchar)""")
    rows = []
    for i in range(cap.MIN_MONTHLY_NAMES):        # filler names make 10-27 a monthly expiry
        rows.append((f"F|{i}", "", f"S{i}", str(EXP), None, "FUT", 100))
    rows += [("F|ABC", "", "ABC", str(EXP), None, "FUT", 500),
             ("F|NIFTY", "", "NIFTY", str(EXP), None, "FUT", 75),
             ("F|ABCW", "", "ABC", "2026-10-20", None, "FUT", 500)]
    for k in (80, 95, 100, 105, 130):
        for t in ("CE", "PE"):
            rows.append((f"O|ABC{k}{t}", "", "ABC", str(EXP), float(k), t, 500))
    rows.append(("O|NIFTY25000CE", "", "NIFTY", str(EXP), 25000.0, "CE", 75))
    con.executemany("insert into instruments values (?,?,?,?,?,?,?,'2026-09-25')", rows)
    con.close()


class _FakeMD:
    """Quotes ABC's future at 100 and every option two-sided; can fail the first N calls."""

    def __init__(self, fail_calls=0):
        self.fail_calls, self.calls = fail_calls, []

    def fetch_quotes_batch(self, keys):
        self.calls.append(list(keys))
        if self.fail_calls:
            self.fail_calls -= 1
            return {"quotes": {}, "error": "Upstox HTTP 429"}
        q = {}
        for k in keys:
            if k == "F|ABC":
                q[k] = {"ltp": 100.0, "best_bid": 99.9, "best_ask": 100.1, "volume": 10}
            elif k.startswith("O|ABC"):
                q[k] = {"ltp": 3.0, "best_bid": 2.9, "best_ask": 0, "volume": 5} if k == "O|ABC95PE" \
                    else {"ltp": 3.0, "best_bid": 2.9, "best_ask": 3.1, "volume": 5}
        return {"quotes": q, "error": None}


def _no_sleep(_):
    pass


def test_role_is_entry_on_t10_and_exit_on_t1_of_the_oct_27_expiry():
    assert cap.cycle_role(date(2026, 10, 12), [EXP]) == ("entry", EXP)
    assert cap.cycle_role(date(2026, 10, 26), [EXP]) == ("exit", EXP)
    assert cap.cycle_role(date(2026, 10, 13), [EXP]) is None


def test_nov_expiry_counts_back_over_the_holidays():
    assert cap.sessions_before(date(2026, 11, 23), 10) == date(2026, 11, 6)
    assert cap.sessions_before(date(2026, 11, 23), 1) == date(2026, 11, 20)


def test_a_chunk_that_keeps_failing_is_api_fail_not_missing():
    md = _FakeMD(fail_calls=cap.RETRIES)
    quotes, failed, errors = cap.quote_all(md, ["F|ABC"], sleep=_no_sleep)
    assert quotes == {} and failed == {"F|ABC"} and len(errors) == cap.RETRIES


def test_a_transient_failure_is_retried():
    quotes, failed, _ = cap.quote_all(_FakeMD(fail_calls=1), ["F|ABC"], sleep=_no_sleep)
    assert "F|ABC" in quotes and not failed


def _db(tmp_path):
    con = duckdb.connect(str(tmp_path / "cap.duckdb"))
    con.execute(cap.SCHEMA)
    return con


def test_entry_pass_quotes_stock_futures_and_the_strike_band_only(tmp_path):
    _master(tmp_path / "m.duckdb")
    m = duckdb.connect(str(tmp_path / "m.duckdb"), read_only=True)
    futs, opts = cap.load_universe(m, date(2026, 9, 25), EXP)
    assert "NIFTY" not in set(futs.underlying) and "O|NIFTY25000CE" not in set(opts.instrument_key)
    con = _db(tmp_path)
    run = cap.run_pass(con, _FakeMD(), "entry", EXP, date(2026, 9, 25), futs, opts, "c-5",
                       datetime(2026, 10, 12, 15, 35), sleep=_no_sleep)
    got = {k for (k,) in con.execute(
        "select instrument_key from quotes where run_id=? and instrument_type<>'FUT'", [run]).fetchall()}
    assert got == {f"O|ABC{k}{t}" for k in (95, 100, 105) for t in ("CE", "PE")}  # 80, 130 outside 10%
    # zero ask is stored as missing, never as a price of 0
    assert con.execute("select best_ask from quotes where instrument_key='O|ABC95PE'").fetchone()[0] is None
    cov = cap.coverage(con, run)
    assert cov["names_two_sided"] == 1 and cov["one_sided"] == 1 and cov["api_fail"] == 0
    # filler futures have no quote -> missing, not api_fail
    assert cov["missing"] == cap.MIN_MONTHLY_NAMES


def test_exit_pass_requotes_the_entry_keys_not_a_new_band(tmp_path):
    _master(tmp_path / "m.duckdb")
    m = duckdb.connect(str(tmp_path / "m.duckdb"), read_only=True)
    futs, opts = cap.load_universe(m, date(2026, 9, 25), EXP)
    con = _db(tmp_path)
    cap.run_pass(con, _FakeMD(), "entry", EXP, date(2026, 9, 25), futs, opts, "c-5",
                 datetime(2026, 10, 12, 15, 35), sleep=_no_sleep)

    class _Moved(_FakeMD):  # the future has run to 130: a fresh band would pick other strikes
        def fetch_quotes_batch(self, keys):
            res = super().fetch_quotes_batch(keys)
            if "F|ABC" in res["quotes"]:
                res["quotes"]["F|ABC"]["ltp"] = 130.0
            return res

    run = cap.run_pass(con, _Moved(), "exit", EXP, date(2026, 9, 25), futs, opts, "c-5",
                       datetime(2026, 10, 26, 15, 35), sleep=_no_sleep)
    got = {k for (k,) in con.execute(
        "select instrument_key from quotes where run_id=? and instrument_type<>'FUT'", [run]).fetchall()}
    assert got == {f"O|ABC{k}{t}" for k in (95, 100, 105) for t in ("CE", "PE")}


def _run_main(tmp_path, md, today, extra=()):
    _master(tmp_path / "m.duckdb")
    sent = []
    rc = cap.main(["--db", str(tmp_path / "cap.duckdb"), "--master", str(tmp_path / "m.duckdb"),
                   "--immediate", *extra], md=md, today=today, sleep=_no_sleep, notify=sent.append,
                  artifacts_kw={"http_get": lambda url: (_ for _ in ()).throw(OSError("offline")),
                                "ca_fetch": lambda frm, to: b'"SYMBOL"\n'})
    return rc, sent


def test_main_is_a_noop_off_the_capture_sessions(tmp_path):
    md = _FakeMD()
    rc, sent = _run_main(tmp_path, md, date(2026, 10, 13))
    assert rc == 0 and md.calls == [] and sent == []


def test_main_on_entry_day_archives_artifacts_and_fails_loud_on_poor_coverage(tmp_path):
    rc, sent = _run_main(tmp_path, _FakeMD(), date(2026, 10, 12))
    con = duckdb.connect(str(tmp_path / "cap.duckdb"), read_only=True)
    arts = dict(con.execute("select kind, ok from artifacts").fetchall())
    assert arts == {"fo_secban": False, "ca_forward": True}
    assert con.execute("select count(distinct pass_label) from capture_runs").fetchone()[0] == 4
    # only 1 of 101 stock futures is quoted in the fake -> below MIN_FUT_COVERAGE -> alert exit
    assert rc == 1 and "FAILED" in sent[0]


def test_main_exits_nonzero_when_every_chunk_fails(tmp_path):
    rc, _ = _run_main(tmp_path, _FakeMD(fail_calls=10 ** 6), date(2026, 10, 12))
    assert rc == 1


def test_dry_run_sends_nothing_and_is_tagged(tmp_path):
    rc, sent = _run_main(tmp_path, _FakeMD(), date(2026, 9, 28),
                         ["--dry-run", "--role", "entry", "--expiry", str(EXP)])
    con = duckdb.connect(str(tmp_path / "cap.duckdb"), read_only=True)
    assert sent == [] and {r for (r,) in con.execute("select distinct role from capture_runs").fetchall()} == {"dry-entry"}
