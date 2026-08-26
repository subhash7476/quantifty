"""ISD gate unit tests — synthetic fixtures only, no network, no real stores."""
import json

import duckdb
import pytest


def make_day_db(path, rows, schema="new"):
    """rows: [(symbol, 'YYYY-MM-DD HH:MM:SS', o, h, l, c, v)]"""
    con = duckdb.connect(str(path))
    if schema == "new":
        con.execute("create table candles (symbol VARCHAR, instrument_key VARCHAR,"
                    " timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE,"
                    " high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT,"
                    " is_synthetic BOOLEAN)")
        for r in rows:
            con.execute("insert into candles values (?, 'NSE_FO|x', '1m', "
                        "?, ?, ?, ?, ?, ?, false)", list(r))
    else:
        con.execute("create table candles (symbol VARCHAR, timeframe VARCHAR,"
                    " timestamp TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE,"
                    " close DOUBLE, volume BIGINT, is_synthetic BOOLEAN)")
        for r in rows:
            con.execute("insert into candles values (?, '1m', ?, ?, ?, ?, ?, ?,"
                        " false)", [r[0], r[1], *r[2:]])
    con.close()
    return path


def full_grid_rows(symbol, day, n=375):
    rows = []
    for i in range(n):
        total = 9 * 60 + 15 + i
        rows.append((symbol,
                     f"{day} {total // 60:02d}:{total % 60:02d}:00",
                     100.0, 101.0, 99.0, 100.0, 1000))
    return rows


# --------------------------------------------------------------------------- #
# reader (G3)
# --------------------------------------------------------------------------- #
def test_reader_abstracts_schema_drift(tmp_path):
    from scripts.isd.read_1m import read_day
    rows = full_grid_rows("NSE_EQ|INE000", "2026-01-05")[:3]
    old = make_day_db(tmp_path / "old.duckdb", rows, schema="old")
    new = make_day_db(tmp_path / "new.duckdb", rows, schema="new")
    a, b = read_day(old), read_day(new)
    assert list(a.columns) == list(b.columns)
    assert len(a) == len(b) == 3
    assert not a["is_synthetic"].any()


def test_reader_filters_non_equity(tmp_path):
    from scripts.isd.read_1m import read_day
    rows = [("NSE_INDEX|Nifty 50", "2026-01-05 09:15:00",
             1.0, 2.0, 0.5, 1.5, 0)] + full_grid_rows("NSE_EQ|INE001",
                                                      "2026-01-05")[:2]
    p = make_day_db(tmp_path / "d.duckdb", rows)
    assert len(read_day(p)) == 2


# --------------------------------------------------------------------------- #
# validity (G4)
# --------------------------------------------------------------------------- #
def test_validity_detects_planted_violations(tmp_path):
    from scripts.isd import gate_validity
    good = full_grid_rows("NSE_EQ|INE000", "2026-01-05")
    bad = [("NSE_EQ|INE001", "2026-01-05 09:20:00",
            100.0, 90.0, 99.0, 100.0, 10)]          # V1: high < open
    dup = ("NSE_EQ|INE002", "2026-01-05 09:25:00",
           100.0, 101.0, 99.0, 100.0, 10)
    p = make_day_db(tmp_path / "d.duckdb", good + bad + [dup, dup])
    res = gate_validity.audit_session(p, "2026-01-05", last_ex={})
    assert res["v1_ohlc_order"] == 1
    assert res["v3_duplicates"] == 1


def test_validity_clean_session_has_zero_counts(tmp_path):
    from scripts.isd import gate_validity
    p = make_day_db(tmp_path / "d.duckdb",
                    full_grid_rows("NSE_EQ|INE000", "2026-01-05"))
    res = gate_validity.audit_session(p, "2026-01-05", last_ex={})
    assert res["v1_ohlc_order"] == 0 and res["v3_duplicates"] == 0
    assert res["eq_bars"] == 375


def test_validity_first_bar_artifact_classified_explained(tmp_path):
    from scripts.isd import gate_validity
    good = full_grid_rows("NSE_EQ|INE000", "2026-01-05")
    first_bar = ("NSE_EQ|INE001", "2026-01-05 09:15:00",
                 100.0, 101.0, 100.5, 100.8, 10)     # V1: low > open at 09:15
    mid_bar = ("NSE_EQ|INE002", "2026-01-05 11:00:00",
               100.0, 99.0, 100.5, 100.8, 10)        # V1: high < open at 11:00
    p = make_day_db(tmp_path / "d.duckdb", good + [first_bar, mid_bar])
    res = gate_validity.audit_session(p, "2026-01-05", last_ex={})
    assert res["v1_ohlc_order"] == 2
    assert res["v1_first_bar_auction_artifact"] == 1


def test_repair_zero_rows_baseline_and_delete(tmp_path):
    import scripts.isd as isd
    from scripts.isd import repair_zero_rows as rzr

    rows = full_grid_rows("NSE_EQ|INE000", "2026-01-05")
    rows.append(("NSE_EQ|INE000", "2026-01-05 19:01:00", 0.0, 0.0, 0.0, 0.0, 0))
    p = make_day_db(tmp_path / "2026-01-05.duckdb", rows)

    orig_dir, orig_baseline = rzr.NATIVE_1M_DIR, rzr.BASELINE_DIR
    rzr.NATIVE_1M_DIR = tmp_path
    rzr.BASELINE_DIR = tmp_path / "baseline"
    try:
        dry = rzr.run(apply=False)
        assert dry["rows_flagged"] == 1 and dry["rows_deleted"] == 0
        applied = rzr.run(apply=True)
        assert applied["rows_deleted"] == 1
        assert (tmp_path / "baseline" / "2026-01-05.duckdb").exists()
        again = rzr.run(apply=False)
        assert again["rows_flagged"] == 0
    finally:
        rzr.NATIVE_1M_DIR, rzr.BASELINE_DIR = orig_dir, orig_baseline


def test_currency_check_real_criterion():
    from scripts.isd.gate_contiguity import currency_check
    cal = ["2026-08-19", "2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25"]
    r = currency_check(["2026-08-19", "2026-08-20", "2026-08-21"],
                       cal, today_iso="2026-08-25")
    assert r["pass"] is False                      # 2026-08-24 missing
    r = currency_check(["2026-08-19", "2026-08-20", "2026-08-21", "2026-08-24"],
                       cal, today_iso="2026-08-25")
    assert r["pass"] is True                       # store current through Monday
    assert r["last_completed_trading_session"] == "2026-08-24"


# --------------------------------------------------------------------------- #
# contiguity (G1)
# --------------------------------------------------------------------------- #
def test_contiguity_counts_missing_and_duplicate_slots(tmp_path):
    from scripts.isd import gate_contiguity
    rows = full_grid_rows("NSE_EQ|INE000", "2026-01-05")
    rows.pop(100)                                     # one missing minute
    rows.append(rows[0][:1] + rows[0][1:])            # exact duplicate row
    p = make_day_db(tmp_path / "d.duckdb", rows)
    r = gate_contiguity.audit_session(p, "2026-01-05")
    assert r["missing_slots"] == 1
    # duplicate slot: two bars at the same (symbol, minute) -> distinct < count
    assert r["duplicate_slots"] >= 1


# --------------------------------------------------------------------------- #
# intraday fees (G6a) — hand-computed scenarios
# --------------------------------------------------------------------------- #
def test_fees_round_trip_hand_computed_post_2024():
    from datetime import date
    from core.execution.equity.intraday_fees import round_trip_fees
    d = date(2026, 8, 24)
    v = 500_000.0                                    # both legs at 5L
    fees = round_trip_fees(entry_value=v, exit_value=v, entry_date=d)
    brokerage = min(20.0, 0.0003 * v)                # 20.0 (cap binds)
    exch = v * 0.0000297                             # post-Oct-2024 rate
    sebi = v * 0.000001
    stt = v * 0.00025                                # SELL only
    stamp = v * 0.00003                              # BUY only
    gst = 0.18 * (brokerage * 2 + exch * 2 + sebi * 2)
    assert pytest.approx(fees.brokerage, 1e-9) == 2 * brokerage
    assert pytest.approx(fees.stt, 1e-9) == stt
    assert pytest.approx(fees.exchange_txn, 1e-9) == 2 * exch
    assert pytest.approx(fees.stamp_duty, 1e-9) == stamp
    assert pytest.approx(fees.gst, 1e-9) == gst
    assert pytest.approx(fees.total,
                         1e-9) == (brokerage * 2 + stt + exch * 2 + sebi * 2
                                   + stamp + gst)


def test_fees_small_ticket_flat_brokerage_binds():
    from datetime import date
    from core.execution.equity.intraday_fees import breakeven_round_trip_bps
    d = date(2026, 8, 24)
    bps_small = breakeven_round_trip_bps(price=1000.0, quantity=10,   # 10k ticket
                                         trade_date=d)
    bps_big = breakeven_round_trip_bps(price=1000.0, quantity=1000,   # 10L ticket
                                       trade_date=d)
    assert bps_small > bps_big                        # ₹20 floor hurts small
    # hand check on the big ticket — the cap STILL binds there: the flat ₹20
    # beats 0.03% for any value above Rs 66,667.
    v = 1_000_000.0
    expected = 10_000 * (20.0 * 2 + v * 0.00025 + v * 0.0000297 * 2
                         + v * 0.000001 * 2 + v * 0.00003
                         + 0.18 * (20.0 * 2 + v * 0.0000297 * 2
                                   + v * 0.000001 * 2)) / v
    assert pytest.approx(expected, rel=1e-9) == bps_big


def test_ticket_size_table_monotone():
    from datetime import date
    from core.execution.equity.intraday_fees import ticket_size_table
    rows = ticket_size_table(trade_date=date(2026, 8, 24))
    bps = [r["round_trip_cost_bps"] for r in rows]
    # wider book -> smaller per-name ticket -> the flat-brokerage floor takes a
    # LARGER relative bite. Cost share must rise with width, never fall.
    assert all(bps[i] <= bps[i + 1] for i in range(len(bps) - 1))
    assert bps[0] < 10.0                              # sanity at ₹20L tickets


# --------------------------------------------------------------------------- #
# PIT universe helpers (G5) — interval resolution on a hand-built index
# --------------------------------------------------------------------------- #
def test_entity_interval_resolution():
    import datetime as dt
    from scripts.isd.build_pit_universe import _resolve
    d = dt.date
    idx = {"ABC": ([d(2020, 1, 1), d(2023, 5, 1)],
                   [(d(2020, 1, 1), d(2023, 5, 1), "OLD_ENT"),
                    (d(2023, 5, 1), d(9999, 12, 31), "NEW_ENT")])}
    assert _resolve(idx, "ABC", "2022-01-01") == "OLD_ENT"
    assert _resolve(idx, "ABC", "2023-05-01") == "NEW_ENT"   # half-open seam
    assert _resolve(idx, "ABC", "2019-01-01") is None        # before listing
    assert _resolve(idx, "ZZZ", "2024-01-01") is None        # unknown symbol


# --------------------------------------------------------------------------- #
# vendor ingest (G7a-d) — tail policy + resolution on a tiny zip
# --------------------------------------------------------------------------- #
def test_vendor_tail_policy_and_resolution(tmp_path):
    import zipfile
    from scripts.isd import ingest_vendor_archive as iva

    sym_map = {"ABB": "INE117A01022"}
    lines = ["date,open,high,low,close,volume",
             "2026-01-05 09:15:00,100,101,99,100,1000",
             "2026-01-05 15:29:00,100,101,99,100.5,900",
             # junk tails: off-grid + zero volume -> dropped
             "2026-01-05 17:57:00,100,100,100,100,0",
             "2026-01-05 20:28:00,100,100,100,100,0",
             # off-grid WITH volume -> kept loudly
             "2026-01-05 09:00:00,100,101,99,100,50"]
    zp = tmp_path / "archive.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("NIFTY50/ABB.csv", "\n".join(lines))

    # redirect the staging tree into tmp_path
    orig_dir = iva.VENDOR_DIR
    staged = tmp_path / "vendor" / "ABB.duckdb"
    iva.VENDOR_DIR = tmp_path / "vendor"
    try:
        rec = iva.stage_member(zipfile.ZipFile(zp), "NIFTY50/ABB.csv", sym_map)
    finally:
        iva.VENDOR_DIR = orig_dir

    assert rec["resolved"] is True and rec["isin"] == "INE117A01022"
    assert rec["rows_raw"] == 5
    assert rec["rows_kept"] == 3                      # 2 junk dropped
    assert rec["tail_dropped"] == 2
    assert rec["modal_first_minute"] == 9 * 60        # 09:00 kept off-grid bar
    con = duckdb.connect(str(staged), read_only=True)
    try:
        n = con.execute("select count(*) from vendor_1m").fetchone()[0]
    finally:
        con.close()
    assert n == 3


def test_vendor_manifest_roundtrip(tmp_path):
    import zipfile
    from scripts.isd import ingest_vendor_archive as iva

    sym_map = {}
    lines = ["date,open,high,low,close,volume",
             "2026-01-05 09:15:00,1,1,1,1,0"]
    zp = tmp_path / "a.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("NIFTY50/UNKNOWN.csv", "\n".join(lines))
    orig_dir = iva.VENDOR_DIR
    orig_manifest = iva.MANIFEST_PATH
    iva.VENDOR_DIR = tmp_path / "v2"
    iva.MANIFEST_PATH = iva.VENDOR_DIR / "manifest.jsonl"
    try:
        res = iva.run(zp)
    finally:
        iva.VENDOR_DIR = orig_dir
        iva.MANIFEST_PATH = orig_manifest
    assert res["unresolved_tickers"] == ["UNKNOWN"]
    assert res["resolution_rate"] == 0.0
    rec = json.loads(open(res["manifest"], encoding="utf-8").read().strip())
    assert rec["ticker"] == "UNKNOWN"


# --------------------------------------------------------------------------- #
# vendor adjustment seams (G7f) — synthetic series with a planted ex-date
# --------------------------------------------------------------------------- #
def test_vendor_adjustment_seam_detector(tmp_path):
    import datetime as dt
    import duckdb
    from scripts.isd import verify_adjustments as va

    def store(ticker, rows):
        con = duckdb.connect(str(tmp_path / f"{ticker}.duckdb"))
        con.execute("create table vendor_1m (ts TIMESTAMP, open DOUBLE, "
                    "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
        for ts, o, c in rows:
            con.execute("insert into vendor_1m values (?, ?, ?, ?, ?, 100)",
                        [ts, o, o, c, c])
        con.close()

    ex = dt.date(2026, 5, 11)                    # 1:1 bonus ex-date
    # GOOD: vendor series back-adjusted (d1 halved) -> seam gap ~ +100 bps
    store("GOOD", [("2026-05-08 09:15:00", 50.0, 50.0),
                   ("2026-05-11 09:15:00", 50.5, 51.0),
                   ("2026-05-12 09:15:00", 51.2, 51.5)])
    # BAD: seam into 2026-05-12 opens -30% off d2 close -> fabricated
    store("BAD", [("2026-05-08 09:15:00", 100.0, 100.0),
                  ("2026-05-11 09:15:00", 100.0, 100.0),
                  ("2026-05-12 09:15:00", 70.0, 71.0)])
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps({"ticker": "GOOD", "isin": "INE000GOOD00", "resolved": True,
                    "first_date": "2026-05-08", "last_date": "2026-05-12"}) + "\n"
        + json.dumps({"ticker": "BAD", "isin": "INE000BAD00", "resolved": True,
                      "first_date": "2026-05-08", "last_date": "2026-05-12"}) + "\n",
        encoding="utf-8")

    orig_dir, orig_ca = va.VENDOR_DIR, va._ca_ex_dates
    va.VENDOR_DIR = tmp_path
    va._ca_ex_dates = lambda isins: {
        "INE000GOOD00": [(ex, "1:1 bonus")],
        "INE000BAD00": [(ex, "1:1 bonus")],
    }
    try:
        res = va.run(manifest_path=manifest)
    finally:
        va.VENDOR_DIR, va._ca_ex_dates = orig_dir, orig_ca

    assert res["seams_checked"] == 2
    assert res["fabricated_seams"] == 1
    assert res["violations"][0]["ticker"] == "BAD"
    assert res["violations"][0]["session"] == "2026-05-12"


# --------------------------------------------------------------------------- #
# vendor consolidate (G7e support) — native bulk flatten of staging DBs
# --------------------------------------------------------------------------- #
def test_vendor_consolidate_native_bulk(tmp_path):
    import duckdb
    from scripts.isd import cross_validate_vendor as cvv

    def store(ticker, rows):
        con = duckdb.connect(str(tmp_path / f"{ticker}.duckdb"))
        con.execute("create table vendor_1m (ts TIMESTAMP, open DOUBLE, "
                    "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
        for ts, c in rows:
            con.execute("insert into vendor_1m values (?, 1, 1, 1, ?, 1)",
                        [ts, c])
        con.close()

    store("A", [("2026-01-05 09:15:00", 100.0),
                ("2026-01-05 09:16:00", 101.0)])
    store("B", [("2026-01-05 09:15:00", 200.0)])
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps({"ticker": "A", "isin": "INE000AAAAA", "resolved": True}) + "\n"
        + json.dumps({"ticker": "B", "isin": "INE000BBBBB", "resolved": True}) + "\n"
        + json.dumps({"ticker": "C", "isin": None, "resolved": False}) + "\n",
        encoding="utf-8")

    orig_dir = __import__("scripts.isd", fromlist=["VENDOR_DIR"]).VENDOR_DIR
    isd = __import__("scripts.isd", fromlist=["VENDOR_DIR"])
    isd.VENDOR_DIR = tmp_path
    try:
        n = cvv.consolidate(manifest_path=manifest)
    finally:
        isd.VENDOR_DIR = orig_dir

    assert n == 3
    con = duckdb.connect(str(tmp_path / "vendor_flat.duckdb"), read_only=True)
    try:
        rows = con.execute(
            "select ticker, isin, close from vendor_closes order by ticker"
        ).fetchall()
    finally:
        con.close()
    assert rows == [("A", "INE000AAAAA", 100.0), ("A", "INE000AAAAA", 101.0),
                    ("B", "INE000BBBBB", 200.0)]
