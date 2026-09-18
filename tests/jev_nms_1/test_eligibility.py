from datetime import date, datetime, timedelta

import duckdb
import pytest

from scripts.jev_nms_1.eligibility import (
    ContractStop, evaluate_session, load_seal, longest_flat_run, populations,
)

SYMBOL = "NSE_INDEX|Nifty 50"


def _write(store, d, bars):
    con = duckdb.connect(str(store / f"{d.isoformat()}.duckdb"))
    con.execute("CREATE TABLE candles (symbol VARCHAR, timeframe VARCHAR, timestamp TIMESTAMP, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, "
                "is_synthetic BOOLEAN DEFAULT FALSE)")
    if bars:
        con.executemany("INSERT INTO candles VALUES (?, '1m', ?, ?, ?, ?, ?, 0, ?)",
                        [(SYMBOL, ts, o, h, l, c, syn) for ts, o, h, l, c, syn in bars])
    con.close()


def _session(d, flat_from=None, flat_len=0, drop=None, last="15:29"):
    bars, start = [], datetime.combine(d, datetime.strptime("09:15", "%H:%M").time())
    end = datetime.combine(d, datetime.strptime(last, "%H:%M").time())
    ts, px, i = start, 100.0, 0
    while ts <= end:
        if drop != ts.strftime("%H:%M"):
            if flat_from is not None and flat_from <= i < flat_from + flat_len:
                bars.append((ts, 150.0, 150.0, 150.0, 150.0, False))
            else:
                px += 0.5
                bars.append((ts, px - 0.2, px + 0.3, px - 0.4, px, False))
        ts += timedelta(minutes=1)
        i += 1
    return bars


def test_a_clean_session_with_a_clean_predecessor_is_eligible(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4)))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["eligible"] and rec["previous_session"] == "2024-06-03"
    assert rec["prev_1529_close"] > 0


def test_predecessor_without_a_1529_bar_fails_item_8_only(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3), last="12:29"))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4)))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["items"]["8"] is False and rec["reasons"]["8"] == "prev_no_1529_bar"
    assert rec["otherwise_eligible"] is False
    assert all(v for k, v in rec["items"].items() if k != "8")


def test_predecessor_with_no_nifty_bars_fails_item_8(tmp_path):
    _write(tmp_path, date(2024, 6, 3), [])
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4)))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["reasons"]["8"] == "prev_no_nifty_bars"


def test_physical_row_order_is_not_part_of_item_5(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), list(reversed(_session(date(2024, 6, 4)))))
    assert evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)["eligible"]


def test_a_missing_window_minute_fails_item_5(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4), drop="11:00"))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["items"]["5"] is False


def test_an_eleven_bar_freeze_fails_item_7_but_stays_otherwise_eligible(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4), flat_from=60, flat_len=11))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["items"]["7"] is False and rec["otherwise_eligible"] and not rec["eligible"]
    assert rec["item7_longest_run"] == {"start": "2024-06-04T10:15:00", "length": 11}


def test_a_nine_bar_freeze_passes_item_7(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4), flat_from=60, flat_len=9))
    assert evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)["eligible"]


def test_flat_run_variants():
    bars = _session(date(2024, 6, 4), flat_from=60, flat_len=10)
    assert longest_flat_run(bars, "identical_close")[1] == 10
    assert longest_flat_run(bars, "minute_adjacent")[1] == 10
    assert longest_flat_run(bars, "vs_previous_bar")[1] == 9


def test_a_run_on_which_the_readings_disagree_stops_rather_than_choosing(tmp_path):
    # Exactly 10 flat bars: two readings say 10 (fail), vs_previous_bar says 9 (pass).
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    _write(tmp_path, date(2024, 6, 4), _session(date(2024, 6, 4), flat_from=60, flat_len=10))
    with pytest.raises(ContractStop):
        evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)


def test_defect_register_and_special_sessions_exclude(tmp_path):
    _write(tmp_path, date(2024, 3, 1), _session(date(2024, 3, 1)))
    _write(tmp_path, date(2024, 3, 2), _session(date(2024, 3, 2)))
    rec = evaluate_session(date(2024, 3, 2), tmp_path, {date(2024, 3, 2)}, 10)
    assert rec["items"]["4"] is False and rec["items"]["9"] is False
    assert rec["items"]["1"] is False and rec["reasons"]["1"] == "weekend"


def test_absent_file_fails_item_1(tmp_path):
    _write(tmp_path, date(2024, 6, 3), _session(date(2024, 6, 3)))
    rec = evaluate_session(date(2024, 6, 4), tmp_path, set(), 10)
    assert rec["reasons"]["1"] == "file_absent" and not rec["eligible"]


def test_populations_follow_the_sealed_sets():
    config, addendum = load_seal()
    pops = populations(config, addendum)
    assert pops["d_fit"][0] == date(2023, 3, 1) and pops["d_fit"][-1] == date(2024, 12, 31)
    assert pops["d_eval"][0] == date(2025, 1, 1) and pops["d_eval"][-1] == date(2025, 12, 31)
    assert pops["h_exposed"][0] == date(2026, 1, 1) and pops["h_exposed"][-1] == date(2026, 9, 18)
    assert date(2024, 1, 20) in pops["d_fit"] and date(2024, 1, 22) not in pops["d_fit"]
