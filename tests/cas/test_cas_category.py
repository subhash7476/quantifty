from datetime import date

import duckdb
import pytest

from scripts.cas.build_cas_category import build_intervals, is_cat1


@pytest.fixture
def futures_con(tmp_path):
    """Mirrors the real futures_bhavcopy schema: `underlying`, not `symbol`,
    and an `inst_type` that separates stock futures from index futures."""
    con = duckdb.connect(str(tmp_path / "fut.duckdb"))
    con.execute(
        "CREATE TABLE futures_bhavcopy "
        "(underlying VARCHAR, expiry_dt DATE, trade_date DATE, inst_type VARCHAR)"
    )
    con.executemany(
        "INSERT INTO futures_bhavcopy VALUES (?, ?, ?, ?)",
        [("RELIANCE", date(2026, 8, 27), date(2026, 8, 3), "FUTSTK"),
         ("RELIANCE", date(2026, 8, 27), date(2026, 8, 4), "FUTSTK"),
         ("IRCTC", date(2026, 8, 27), date(2026, 8, 3), "FUTSTK"),
         ("BANKNIFTY", date(2026, 8, 25), date(2026, 8, 4), "FUTIDX")],
    )
    return con


def test_symbol_with_a_future_on_the_date_is_cat1(futures_con):
    assert is_cat1("RELIANCE", date(2026, 8, 4), futures_con)


def test_symbol_without_a_future_on_the_date_is_cat2(futures_con):
    assert not is_cat1("IRCTC", date(2026, 8, 4), futures_con)


def test_unknown_symbol_is_cat2(futures_con):
    assert not is_cat1("NOTLISTED", date(2026, 8, 3), futures_con)


def test_build_intervals_emits_one_row_per_contiguous_run(futures_con):
    rows = build_intervals(futures_con)
    reliance = [r for r in rows if r[0] == "RELIANCE"]
    assert reliance == [("RELIANCE", date(2026, 8, 3), date(2026, 8, 4))]


def test_index_futures_underlyings_are_excluded(futures_con):
    # BANKNIFTY has FUTIDX contracts but is not a cash equity, so it can never
    # be a CAS Category I stock.
    assert not is_cat1("BANKNIFTY", date(2026, 8, 4), futures_con)
    assert not any(r[0] == "BANKNIFTY" for r in build_intervals(futures_con))
