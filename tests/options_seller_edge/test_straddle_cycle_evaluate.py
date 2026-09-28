"""STOCK-STRADDLE-M10 evaluator: the frozen pre-registration's sections 3, 4, 6, 7, 8 and 9."""
from datetime import date, datetime, timedelta

import duckdb
import numpy as np
import pandas as pd
import pytest

from core.execution.options.fees import option_order_fees
from core.market.trading_calendar import is_session
from scripts.research.options_seller_edge import straddle_cycle_capture as cap
from scripts.research.options_seller_edge import straddle_cycle_evaluate as ev

EXP, ENTRY, EXIT = date(2026, 10, 27), date(2026, 10, 12), date(2026, 10, 26)
T11 = date(2026, 10, 9)


def _q(key, und, typ, strike, ltp=None, bid=None, ask=None, vol=10, status="ok", lot=100):
    return dict(instrument_key=key, underlying=und, instrument_type=typ, strike=strike,
                expiry=EXP, lot_size=lot, ltp=ltp, best_bid=bid, best_ask=ask, volume=vol,
                oi=None, feed_ts=None, status=status)


def _chain(und, fut, strikes, bid=5.0, ask=5.2, lot=100):
    rows = [_q(f"F|{und}", und, "FUT", None, ltp=fut, lot=lot)]
    for k in strikes:
        for t in ("CE", "PE"):
            rows.append(_q(f"O|{und}{k}{t}", und, t, float(k), ltp=bid, bid=bid, ask=ask, lot=lot))
    return rows


class Store:
    def __init__(self, path):
        self.path = str(path)
        con = duckdb.connect(self.path)
        con.execute(cap.SCHEMA)
        con.close()

    def run(self, role, day, label, rows, late_s=0.0):
        con = duckdb.connect(self.path)
        rid = f"{role}-{day}-{label}"
        planned = datetime.combine(day, datetime.min.time()) + timedelta(hours=15, minutes=35)
        con.execute("insert into capture_runs values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [rid, role, EXP, day, label, planned, planned + timedelta(seconds=late_s),
                     planned, day, len(rows), len(rows), 0, None])
        frame = pd.DataFrame([dict(run_id=rid, **r) for r in rows],  # noqa: F841
                             columns=list(cap.QUOTE_COLS))
        con.execute("insert into quotes select * from frame")
        con.close()

    def artifact(self, kind, body, day=ENTRY):
        con = duckdb.connect(self.path)
        con.execute("insert into artifacts values (?,?,?,?,?,?,?)",
                    [day, EXP, kind, datetime.now(), body is not None, None, body])
        con.close()


def _sessions_back(last, n):
    out, d = [], last
    while len(out) < n:
        if is_session(d):
            out.append(d)
        d -= timedelta(days=1)
    return sorted(out)


def _futures(path, names_days, last=T11):
    """names_days: {underlying: number of consecutive front-future sessions ending at `last`}."""
    con = duckdb.connect(str(path))
    con.execute("create table futures_bhavcopy (underlying varchar, inst_type varchar, "
                "expiry_dt date, trade_date date, close double)")
    rng = np.random.default_rng(0)
    rows = []
    for name, n in names_days.items():
        px = 100.0
        for d in _sessions_back(last, n):
            px *= float(np.exp(rng.normal(0, 0.01)))
            rows.append((name, "FUTSTK", EXP, d, px))
    con.executemany("insert into futures_bhavcopy values (?,?,?,?,?)", rows)
    con.close()


def _opt_bhav(path, rows=()):
    con = duckdb.connect(str(path))
    con.execute("create table stock_options_bhavcopy (underlying varchar, expiry_dt date, "
                "strike double, option_type varchar, close double, settle double, "
                "contracts integer, trade_date date)")
    if rows:
        con.executemany("insert into stock_options_bhavcopy values (?,?,?,?,?,?,?,?)", list(rows))
    con.close()


BAN_OK = b"Securities in Ban For Trade Date 12-OCT-2026:\n1,BAN\n"
CA_HDR = '"SYMBOL","COMPANY NAME","SERIES","PURPOSE","FACE VALUE","EX-DATE","RECORD DATE"\n'


# ------------------------------------------------------------------ section 4

def test_atm_is_the_nearest_traded_two_sided_strike_tie_to_the_lower():
    q = pd.DataFrame(_chain("A", 102.5, [100, 105]) + _chain("B", 100, [90, 95])
                     + [_q("F|C", "C", "FUT", None, ltp=100)]
                     + [_q("O|C100CE", "C", "CE", 100.0, bid=5, ask=None),   # one-sided
                        _q("O|C100PE", "C", "PE", 100.0, bid=5, ask=5.2)])
    atm = ev.pick_atm(q)
    assert atm.loc["A"].strike == 100.0          # 2.5 each side -> lower strike
    assert "B" not in atm.index                  # nearest is 5 % away: not strictly within
    assert "C" not in atm.index                  # CE has no ask


def test_untraded_strikes_are_not_candidates():
    q = pd.DataFrame(_chain("A", 100, [100]) + _chain("A2", 100, [95]))
    q.loc[q.instrument_key == "O|A100CE", "volume"] = 0
    assert "A" not in ev.pick_atm(q).index


# ------------------------------------------------------------------ sections 3, 6, 7

def _cycle(tmp_path, entry_rows_by_pass, exit_rows_by_pass, names_days=None, ban=BAN_OK, ca=None,
           bhav=()):
    s = Store(tmp_path / "cap.duckdb")
    for lb, rows in entry_rows_by_pass.items():
        s.run("entry", ENTRY, lb, rows)
    for lb, rows in exit_rows_by_pass.items():
        s.run("exit", EXIT, lb, rows)
    s.artifact("fo_secban", ban)
    s.artifact("ca_forward", (CA_HDR + (ca or "")).encode())
    _futures(tmp_path / "f.duckdb", names_days or {"A": 70, "B": 70, "BAN": 70})
    _opt_bhav(tmp_path / "o.duckdb", bhav)
    return dict(capture_db=s.path, futures_db=str(tmp_path / "f.duckdb"),
                options_bhav_db=str(tmp_path / "o.duckdb"))


def test_a_full_cycle_scores_the_equal_weight_net_on_premium(tmp_path):
    entry = _chain("A", 100, [100], bid=5.0) + _chain("B", 200, [200], bid=10.0) + _chain("BAN", 50, [50])
    exit_ = [_q("O|A100CE", "A", "CE", 100.0, ask=2.0), _q("O|A100PE", "A", "PE", 100.0, ask=1.0),
             _q("O|B200CE", "B", "CE", 200.0, ask=12.0), _q("O|B200PE", "B", "PE", 200.0, ask=1.0)]
    kw = _cycle(tmp_path, {"c-5": entry}, {"c-5": exit_})
    names, info = ev.score_cycle(EXP, **kw)
    got = names.set_index("underlying")
    assert got.loc["BAN"].status == "U4"
    fees_a = sum(option_order_fees(premium=p, quantity=100, side=sd, trade_date=d).total
                 for p, sd, d in ((5, "SELL", ENTRY), (5, "SELL", ENTRY), (2, "BUY", EXIT), (1, "BUY", EXIT)))
    net_a = (10 - 3 - fees_a / 100) / 10
    assert got.loc["A"].net == pytest.approx(net_a)
    assert got.loc["A"].gross == pytest.approx(0.7)
    assert got.loc["B"].gross == pytest.approx((20 - 13) / 20)
    assert info["cycle_net"] == pytest.approx((net_a + got.loc["B"].net) / 2)
    assert info["fallback_legs"] == 0 and not info["void"]


def test_a_name_whose_primary_pass_failed_is_taken_whole_from_the_next_pass(tmp_path):
    bad = [_q("F|A", "A", "FUT", None, status="api_fail")] + _chain("A", 100, [100])[1:]
    kw = _cycle(tmp_path, {"c-5": bad + _chain("B", 200, [200]), "c-2": _chain("A", 104, [105], bid=7.0)},
                {}, names_days={"A": 70, "B": 70})
    names, _ = ev.score_cycle(EXP, entry_only=True, **kw)
    a = names.set_index("underlying").loc["A"]
    assert (a.entry_pass, a.strike, a.ce_bid) == ("c-2", 105.0, 7.0)


def test_a_late_pass_is_unusable(tmp_path):
    s = Store(tmp_path / "cap.duckdb")
    s.run("entry", ENTRY, "c-5", _chain("A", 100, [100]), late_s=61)
    s.run("entry", ENTRY, "c-2", _chain("A", 100, [100]), late_s=5)
    con = duckdb.connect(s.path, read_only=True)
    assert set(ev.usable_passes(con, "entry", EXP, ENTRY)) == {"c-2"}


def test_history_filter_and_its_t11_guard(tmp_path):
    _futures(tmp_path / "f.duckdb", {"OLD": 70, "NEW": 30})
    assert ev.history_pass(str(tmp_path / "f.duckdb"), ENTRY, T11) == {"OLD"}
    _futures(tmp_path / "g.duckdb", {"OLD": 70}, last=date(2026, 10, 8))
    with pytest.raises(RuntimeError, match="T-11"):
        ev.history_pass(str(tmp_path / "g.duckdb"), ENTRY, T11)


def test_ban_file_counts_only_for_the_entry_date():
    assert ev.ban_set(BAN_OK, ENTRY)[0] == {"BAN"}
    other = b"Securities in Ban For Trade Date 13-OCT-2026:\n1,BAN\n"
    names, src = ev.ban_set(other, ENTRY)
    assert names == set() and src.startswith("none")


def test_corporate_action_rule():
    ca = (CA_HDR
          + '"SPL","x","EQ","Face Value Split (Sub-Division)","10","20-Oct-2026","20-Oct-2026"\n'
          + '"DIV1","x","EQ","Dividend - Rs 1 Per Share","10","20-Oct-2026","20-Oct-2026"\n'
          + '"DIV3","x","EQ","Interim Dividend - Rs 3 Per Share","10","20-Oct-2026","20-Oct-2026"\n'
          + '"DIVX","x","EQ","Special Dividend","10","20-Oct-2026","20-Oct-2026"\n'
          + '"LATE","x","EQ","Bonus 1:1","10","28-Oct-2026","28-Oct-2026"\n'
          + '"ONENTRY","x","EQ","Bonus 1:1","10","12-Oct-2026","12-Oct-2026"\n').encode()
    fut = {k: 100.0 for k in ("SPL", "DIV1", "DIV3", "DIVX", "LATE", "ONENTRY")}
    out, _ = ev.ca_excluded(ca, ENTRY, EXIT, fut)
    assert out == {"SPL", "DIV3", "DIVX"}      # 1 % dividend kept; ex-dates outside (entry, exit] ignored
    assert ev.ca_excluded(b"", ENTRY, EXIT, fut)[0] == set()


def test_exit_ask_falls_back_through_passes_then_to_the_marked_up_reference(tmp_path):
    entry = _chain("A", 100, [100], bid=5.0)
    exit_c5 = [_q("O|A100CE", "A", "CE", 100.0, ltp=2.0, ask=None), _q("O|A100PE", "A", "PE", 100.0, ask=1.0)]
    exit_c2 = [_q("O|A100CE", "A", "CE", 100.0, ltp=2.4, ask=None)]
    bhav = [("A", EXP, 100.0, "CE", 2.2, 2.1, 0, EXIT)]         # untraded -> settle 2.1
    kw = _cycle(tmp_path, {"c-5": entry}, {"c-5": exit_c5, "c-2": exit_c2},
                names_days={"A": 70}, bhav=bhav)
    names, info = ev.score_cycle(EXP, **kw)
    a = names.set_index("underlying").loc["A"]
    assert a.ce_exit_src == "fallback" and a.ce_ask == pytest.approx(1.10 * 2.4)
    assert a.pe_exit_src == "c-5" and a.pe_ask == 1.0
    assert info["fallback_legs"] == 1


def test_a_missing_exit_mark_refuses_to_score_rather_than_guess(tmp_path):
    kw = _cycle(tmp_path, {"c-5": _chain("A", 100, [100])}, {}, names_days={"A": 70})
    with pytest.raises(RuntimeError, match="no exit ask"):
        ev.score_cycle(EXP, **kw)


# ------------------------------------------------------------------ section 8

def test_entry_capture_below_coverage_voids_the_cycle(tmp_path):
    rows = _chain("A", 100, [100]) + [_q(f"F|Z{i}", f"Z{i}", "FUT", None, status="missing") for i in range(5)]
    kw = _cycle(tmp_path, {"c-5": rows}, {}, names_days={"A": 70})
    names, info = ev.score_cycle(EXP, **kw)
    assert info["void"] and "coverage" in info["void_reason"]


def test_void_and_rescoring_replace_rows(tmp_path):
    names = pd.DataFrame([dict(expiry=EXP, role="live", underlying="A", lot_size=1, status="U2")])
    info = dict(void=True, void_reason="x", ban_source="b", ca_source="c",
                excl={"U2": 1, "U3": 0, "U4": 0, "U5": 0})
    for _ in range(2):
        ev.write_cycle(str(tmp_path / "cy.duckdb"), EXP, "live", names, info, ENTRY, EXIT)
    con = duckdb.connect(str(tmp_path / "cy.duckdb"), read_only=True)
    assert con.execute("select count(*) from cycles").fetchone()[0] == 1
    assert con.execute("select count(*) from cycle_names").fetchone()[0] == 1


# ------------------------------------------------------------------ sections 1 and 9

def test_summary_in_progress_confirmed_and_not_confirmed():
    assert ev.summary([0.05] * 5 + [0.06])["verdict"].startswith("IN PROGRESS")
    rng = np.random.default_rng(1)
    strong = list(0.10 + 0.05 * rng.standard_normal(36))
    assert ev.summary(strong)["verdict"] == "CONFIRMED"
    weak = list(0.00 + 0.20 * rng.standard_normal(36))
    assert ev.summary(weak)["verdict"] in ("NOT CONFIRMED", "FALSIFIED")
    assert ev.summary(strong + [-5.0])["n"] == 36     # only the first 36 counted cycles


def test_falsification_f1_and_f2_only_from_cycle_six():
    s = ev.summary([-0.10, -0.12, -0.09, -0.11, -0.10, -0.11])
    assert s["verdict"] == "FALSIFIED" and s["falsified"].startswith("F1 at cycle 6")
    crash = [0.05, -0.60, 0.05, -0.60, 0.05, 0.02, 0.03]
    s = ev.summary(crash)
    assert s["falsified"].startswith("F2 at cycle 6")
    assert ev.summary([-0.6, -0.6, 0.1, 0.1, 0.1])["falsified"] is None   # before cycle 6
