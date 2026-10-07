from datetime import date, datetime

import duckdb
import pytest

from scripts.gex_xs_5d import ingest_board_meetings as bm


def _row(**kw):
    base = {
        "bm_symbol": "ABC", "sm_isin": "INE123A01015", "bm_date": "31-Jan-2016",
        "bm_purpose": "Results", "bm_desc": "to consider financial results",
        "bm_timestamp": "22-Jan-2016 16:03:00", "sysTime": "22-Jan-2016 16:05:01",
        "oriiginalMeetingDate": None, "proposedMeetingDate": None,
    }
    base.update(kw)
    return base


def test_parse_row_known_time_is_later_of_filing_and_dissemination():
    r = bm.parse_row(_row(bm_timestamp="22-Jan-2016 16:03:00", sysTime="22-Jan-2016 16:05:01"))
    assert r["known_ts"] == datetime(2016, 1, 22, 16, 5, 1)
    r = bm.parse_row(_row(bm_timestamp="22-Jan-2016 16:09:00", sysTime="22-Jan-2016 16:05:01"))
    assert r["known_ts"] == datetime(2016, 1, 22, 16, 9, 0)


def test_parse_row_missing_systime_falls_back_to_filing_time():
    r = bm.parse_row(_row(sysTime=None))
    assert r["known_ts"] == datetime(2016, 1, 22, 16, 3, 0)


def test_parse_row_dates_and_isin_prefix():
    r = bm.parse_row(_row())
    assert r["bm_date"] == date(2016, 1, 31)
    assert r["isin_prefix"] == "INE123A01"


@pytest.mark.parametrize("purpose,desc,expected", [
    ("Results", "", True),
    ("Financial Results/Dividend", "", True),
    ("Board Meeting Intimation", "approve the Unaudited Financial results", True),
    ("Fund Raising", "to raise capital", False),
    ("Dividend", "interim dividend", False),
])
def test_is_results_matches_result_in_purpose_or_desc(purpose, desc, expected):
    assert bm.parse_row(_row(bm_purpose=purpose, bm_desc=desc))["is_results"] is expected


def test_parse_row_keeps_revision_fields():
    r = bm.parse_row(_row(oriiginalMeetingDate="28-Jan-2016"))
    assert r["has_revision"] is True
    assert bm.parse_row(_row())["has_revision"] is False


def test_months_to_fetch_skips_cached_closed_months_and_always_refetches_open_month():
    months = bm.months_to_fetch(first=date(2026, 7, 1), end=date(2026, 10, 5),
                                cached={date(2026, 7, 1), date(2026, 8, 1), date(2026, 10, 1)},
                                today=date(2026, 10, 6))
    assert months == [date(2026, 9, 1), date(2026, 10, 1)]


def test_months_to_fetch_never_goes_past_end_month():
    months = bm.months_to_fetch(first=date(2026, 9, 1), end=date(2026, 9, 30),
                                cached=set(), today=date(2026, 12, 1))
    assert months == [date(2026, 9, 1)]


class _Resp:
    def __init__(self, status, ctype, body):
        self.status_code, self.headers, self.content = status, {"Content-Type": ctype}, body

    def json(self):
        import json
        return json.loads(self.content)


class _Sess:
    def __init__(self, resp):
        self.resp = resp

    def get(self, *a, **k):
        return self.resp


def test_fetch_month_rejects_html_shell():
    with pytest.raises(bm.FetchError):
        bm.fetch_month(_Sess(_Resp(200, "text/html", b"<html></html>")), date(2016, 1, 1))


def test_fetch_month_rejects_non_200():
    with pytest.raises(bm.FetchError):
        bm.fetch_month(_Sess(_Resp(503, "application/json", b"[]")), date(2016, 1, 1))


def test_fetch_month_accepts_list_or_data_envelope():
    rows = bm.fetch_month(_Sess(_Resp(200, "application/json", b'[{"a": 1}]')), date(2016, 1, 1))
    assert rows == [{"a": 1}]
    rows = bm.fetch_month(_Sess(_Resp(200, "application/json", b'{"data": [{"a": 2}]}')), date(2016, 1, 1))
    assert rows == [{"a": 2}]


def _cert_db(tmp_path, meeting_rows, months):
    db = tmp_path / "bm.duckdb"
    con = duckdb.connect(str(db))
    bm.ensure_schema(con)
    for m in months:
        con.execute("INSERT INTO raw_months VALUES (?, ?, ?, ?)", [m, datetime(2026, 10, 6), 1, "[]"])
    for r in meeting_rows:
        bm.insert_parsed(con, date(2016, 1, 1), [bm.parse_row(r)])
    con.close()
    return db


def test_results_coverage_counts_distinct_meeting_dates_per_name():
    rows = [_row(bm_date=d) for d in ("31-Jan-2016", "31-Jan-2016", "30-Apr-2016", "31-Jul-2016")]
    rows += [_row(bm_symbol="XYZ", sm_isin="INE999Z01011", bm_date=d) for d in ("31-Jan-2016", "30-Apr-2016")]
    names = {"ABC": "INE123A01", "XYZ": "INE999Z01"}
    cov = bm.results_coverage(rows=[bm.parse_row(r) for r in rows], names=names, year=2016)
    assert cov == {"n_names": 2, "n_covered": 1, "share": 0.5}


def test_missing_months_reports_months_without_rows(tmp_path):
    db = _cert_db(tmp_path, [_row()], months=[date(2016, 1, 1)])
    con = duckdb.connect(str(db))
    con.execute("UPDATE raw_months SET n_rows = 0 WHERE month = DATE '2016-01-01'")
    assert bm.missing_months(con, date(2016, 1, 1), date(2016, 2, 15)) == [date(2016, 1, 1), date(2016, 2, 1)]


def test_lead_share_counts_known_date_on_or_before_meeting_date():
    rows = [bm.parse_row(_row(bm_date="31-Jan-2016", bm_timestamp="22-Jan-2016 16:03:00", sysTime=None)),
            bm.parse_row(_row(bm_date="31-Jan-2016", bm_timestamp="31-Jan-2016 18:00:00", sysTime=None)),
            bm.parse_row(_row(bm_date="31-Jan-2016", bm_timestamp="02-Feb-2016 10:00:00", sysTime=None))]
    assert bm.known_before_meeting_share(rows) == pytest.approx(2 / 3)


def test_reschedule_pairs_counts_close_dated_meetings_and_later_filing():
    rows = [bm.parse_row(_row(bm_date="11-Feb-2019", bm_timestamp="01-Feb-2019 17:00:00", sysTime=None)),
            bm.parse_row(_row(bm_date="14-Feb-2019", bm_timestamp="06-Feb-2019 15:00:00", sysTime=None)),
            bm.parse_row(_row(bm_date="24-May-2019", bm_timestamp="15-May-2019 19:00:00", sysTime=None)),
            bm.parse_row(_row(bm_date="27-May-2019", bm_timestamp="15-May-2019 17:00:00", sysTime=None)),
            bm.parse_row(_row(bm_date="13-Aug-2019", bm_timestamp="01-Aug-2019 17:00:00", sysTime=None))]
    assert bm.reschedule_pairs(rows) == {"pairs": 2, "later_filed": 1}


def test_calendar_digest_is_order_independent_and_sensitive_to_content(tmp_path):
    a, b = _row(bm_date="31-Jan-2016"), _row(bm_symbol="XYZ", bm_date="30-Apr-2016")
    db1 = tmp_path / "1.duckdb"; db2 = tmp_path / "2.duckdb"; db3 = tmp_path / "3.duckdb"
    for db, rows in ((db1, [a, b]), (db2, [b, a]), (db3, [a, _row(bm_symbol="XYZ", bm_date="01-May-2016")])):
        con = duckdb.connect(str(db)); bm.ensure_schema(con)
        bm.insert_parsed(con, date(2016, 1, 1), [bm.parse_row(r) for r in rows]); con.close()
    d = [bm.calendar_digest(duckdb.connect(str(db), read_only=True), date(2016, 12, 31)) for db in (db1, db2, db3)]
    assert d[0] == d[1] and d[0] != d[2]


def test_calendar_digest_ignores_rows_after_end(tmp_path):
    db1 = tmp_path / "1.duckdb"; db2 = tmp_path / "2.duckdb"
    for db, rows in ((db1, [_row()]), (db2, [_row(), _row(bm_date="15-Jan-2017")])):
        con = duckdb.connect(str(db)); bm.ensure_schema(con)
        bm.insert_parsed(con, date(2016, 1, 1), [bm.parse_row(r) for r in rows]); con.close()
    d = [bm.calendar_digest(duckdb.connect(str(db), read_only=True), date(2016, 12, 31)) for db in (db1, db2)]
    assert d[0] == d[1]
