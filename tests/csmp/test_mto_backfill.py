"""Backfill invariant tests — synthetic mini-store fixtures.

Exercises: (a) non-NULL cell not overwritten, (b) NULL cell filled,
(c) 2020+ row untouched, (d) arms C/D on fixture.
"""

import importlib.util
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "backfill_mto_delivery", ROOT / "scripts" / "csmp" / "backfill_mto_delivery.py")
bf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bf)


def _build_store(tmp_path, rows, meta_rows, cal_rows):
    """Build a minimal equity_bhavcopy store."""
    db = tmp_path / "store.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "CREATE TABLE equity_bhavcopy ("
        "trade_date DATE, symbol VARCHAR, series VARCHAR, "
        "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, "
        "prev_close DOUBLE, volume BIGINT, turnover DOUBLE, "
        "deliv_qty BIGINT, deliv_pct DOUBLE)"
    )
    for r in rows:
        con.execute("INSERT INTO equity_bhavcopy VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", r)
    con.execute(
        "CREATE TABLE ingest_meta (trade_date DATE PRIMARY KEY, source VARCHAR)"
    )
    for r in meta_rows:
        con.execute("INSERT INTO ingest_meta VALUES (?,?)", r)
    con.execute(
        "CREATE TABLE trading_calendar ("
        "trade_date DATE PRIMARY KEY, source VARCHAR, n_symbols INTEGER)"
    )
    for r in cal_rows:
        con.execute("INSERT INTO trading_calendar VALUES (?,?,?)", r)
    con.execute(
        "CREATE TABLE symbol_entity_intervals ("
        "symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)"
    )
    con.execute("CREATE TABLE adjustment_factors ("
               "symbol VARCHAR, ex_date DATE, factor DOUBLE, "
               "action_type VARCHAR, source VARCHAR)")
    con.close()
    return db


def _make_mto(tmp_path, date_obj, lines):
    """Write an MTO file into tmp_path."""
    ddmmyyyy = date_obj.strftime("%d%m%Y")
    header = (
        "Security Wise Delivery Position - Compulsory Rolling Settlement\n"
        f"10,MTO,{ddmmyyyy},1000000,0000001\n"
        f"Trade Date <{date_obj.strftime('%d-%b-%Y').upper()}>,"
        f"Settlement Type <N>,Settlement Date <{(date_obj + __import__('datetime').timedelta(days=2)).strftime('%d-%b-%Y').upper()}>\n"
        "Record Type,Sr No,Name of Security,Quantity Traded,"
        "Deliverable Quantity(gross across client level),"
        "% of Deliverable Quantity to Traded Quantity\n"
    )
    body = "\n".join(f"20,{i+1},{sym},{ser},{qty},{dq},{dp}"
                     for i, (sym, ser, qty, dq, dp) in enumerate(lines))
    path = tmp_path / f"MTO_{ddmmyyyy}.DAT"
    path.write_text(header + body + "\n", encoding="utf-8")
    return path


# ── (a) Non-NULL cell not overwritten ─────────────────────────────────────

def test_nonnull_not_overwritten(tmp_path):
    d = date(2015, 6, 15)
    rows = [
        (d, "SYM1", "EQ", 100.0, 101.0, 99.0, 102.0, 100.0,
         5000, 500000.0, 2500, 50.0),  # pre-existing non-null
        (d, "SYM2", "EQ", 200.0, 201.0, 199.0, 202.0, 200.0,
         10000, 2000000.0, None, None),  # NULL → should fill
    ]
    meta = [(d, "legacy")]
    cal = [(d, "equity_store", 500)]
    store = _build_store(tmp_path, rows, meta, cal)

    # Create MTO file with data that WOULD contradict if overwrite guard failed
    mto_lines = [
        ("SYM1", "EQ", 5000, 9999, 99.99),   # should NOT overwrite deliv_qty=2500
        ("SYM2", "EQ", 10000, 7500, 75.0),    # should fill NULL → 7500, 75.0
    ]
    _make_mto(tmp_path, d, mto_lines)

    # Run backfill logic
    bf.MTO_DIR = tmp_path
    con = duckdb.connect(str(store))
    cal_dates = bf.get_backfill_calendar(con)

    updated_total, parsed_total, missing, parse_errors, date_stats, mismatches = \
        bf.backfill(con, cal_dates)

    con.close()

    # Verify
    con = duckdb.connect(str(store), read_only=True)
    row1 = con.execute(
        "SELECT deliv_qty, deliv_pct FROM equity_bhavcopy "
        "WHERE symbol='SYM1' AND trade_date=?", [d]
    ).fetchone()
    assert row1 == (2500, 50.0), f"SYM1 overwritten: {row1}"

    row2 = con.execute(
        "SELECT deliv_qty, deliv_pct FROM equity_bhavcopy "
        "WHERE symbol='SYM2' AND trade_date=?", [d]
    ).fetchone()
    assert row2 == (7500, 75.0), f"SYM2 not filled: {row2}"

    assert updated_total == 2
    con.close()


# ── (b) NULL cell filled ───────────────────────────────────────────────────

def test_null_cells_filled(tmp_path):
    d = date(2015, 6, 15)
    rows = [
        (d, "SYM1", "EQ", 100.0, 101.0, 99.0, 102.0, 100.0,
         5000, 500000.0, None, None),
        (d, "SYM2", "EQ", 200.0, 201.0, 199.0, 201.0, 200.0,
         10000, 2000000.0, None, None),
    ]
    meta = [(d, "legacy")]
    cal = [(d, "equity_store", 500)]
    store = _build_store(tmp_path, rows, meta, cal)

    mto_lines = [
        ("SYM1", "EQ", 5000, 2500, 50.0),
        ("SYM2", "EQ", 10000, 8000, 80.0),
    ]
    _make_mto(tmp_path, d, mto_lines)

    bf.MTO_DIR = tmp_path
    con = duckdb.connect(str(store))
    cal_dates = bf.get_backfill_calendar(con)
    bf.backfill(con, cal_dates)
    con.close()

    con = duckdb.connect(str(store), read_only=True)
    for sym, exp_qty, exp_pct in [("SYM1", 2500, 50.0), ("SYM2", 8000, 80.0)]:
        row = con.execute(
            "SELECT deliv_qty, deliv_pct FROM equity_bhavcopy "
            "WHERE symbol=? AND trade_date=?", [sym, d]
        ).fetchone()
        assert row == (exp_qty, exp_pct), f"{sym}: expected ({exp_qty}, {exp_pct}) got {row}"
    con.close()


# ── (c) 2020+ row untouched ────────────────────────────────────────────────

def test_2020_plus_untouched(tmp_path):
    d_pre = date(2015, 6, 15)
    d_post = date(2020, 6, 15)
    rows = [
        (d_pre, "SYM1", "EQ", 100.0, 101.0, 99.0, 102.0, 100.0,
         5000, 500000.0, None, None),
        (d_post, "SYM1", "EQ", 200.0, 201.0, 199.0, 202.0, 200.0,
         10000, 2000000.0, None, None),
    ]
    meta = [(d_pre, "legacy"), (d_post, "secfull")]
    cal = [(d_pre, "equity_store", 500), (d_post, "equity_store", 500)]
    store = _build_store(tmp_path, rows, meta, cal)

    mto_lines = [
        ("SYM1", "EQ", 5000, 2500, 50.0),
    ]
    _make_mto(tmp_path, d_pre, mto_lines)

    bf.MTO_DIR = tmp_path
    con = duckdb.connect(str(store))
    cal_dates = bf.get_backfill_calendar(con)
    bf.backfill(con, cal_dates)
    con.close()

    con = duckdb.connect(str(store), read_only=True)
    pre = con.execute(
        "SELECT deliv_qty, deliv_pct FROM equity_bhavcopy "
        "WHERE symbol='SYM1' AND trade_date=?", [d_pre]
    ).fetchone()
    assert pre == (2500, 50.0), f"Pre-2020 row not filled: {pre}"
    post = con.execute(
        "SELECT deliv_qty, deliv_pct FROM equity_bhavcopy "
        "WHERE symbol='SYM1' AND trade_date=?", [d_post]
    ).fetchone()
    assert post == (None, None), f"2020+ row modified: {post}"
    con.close()


# ── (d) Arms C/D on fixture ───────────────────────────────────────────────

def test_arms_c_d_on_fixture(tmp_path):
    d_pre = date(2015, 6, 15)

    def _row(td, sym, ser, vol, dq, dp):
        return (td, sym, ser, 100.0, 101.0, 99.0, 102.0, 100.0,
                vol, vol * 100.0, dq, dp)

    rows = [
        _row(d_pre, "SYM1", "EQ", 5000, None, None),
        _row(d_pre, "SYM2", "EQ", 10000, None, None),
    ]
    meta = [(d_pre, "legacy")]
    cal = [(d_pre, "equity_store", 500)]
    store = _build_store(tmp_path, rows, meta, cal)

    mto_lines = [
        ("SYM1", "EQ", 5000, 2500, 50.0),
        ("SYM2", "EQ", 10000, 8000, 80.0),
    ]
    _make_mto(tmp_path, d_pre, mto_lines)

    import shutil
    orig_store = tmp_path / "orig.duckdb"
    work_store = tmp_path / "work.duckdb"
    shutil.copy2(store, orig_store)
    shutil.copy2(store, work_store)

    bf.MTO_DIR = tmp_path
    bf.STORE = orig_store
    con = duckdb.connect(str(work_store))
    cal_dates = bf.get_backfill_calendar(con)
    updated, parsed, missing, parse_errors, date_stats, mismatches = \
        bf.backfill(con, cal_dates)

    arms = bf.run_audit(con, mismatches)
    con.close()

    assert arms["C"]["pass"], f"Arm C failed: {arms['C']}"
    assert arms["D"]["pass"], f"Arm D failed: {arms['D']}"
    con.close()


# ── Determinism: generate_report twice → identical output ──────────────

def test_report_deterministic():
    arms = {
        "A": {"prediction": "test", "pass": True, "calendar_dates": 100, "backfilled_dates": 100, "missing": 0, "coverage_pct": 100.0, "missing_dates": []},
        "B": {"prediction": "test", "pass": True, "total_backfilled_rows": 1000, "qty_mismatches": 5, "mismatch_pct": 0.5, "mismatch_detail": [("2020-01-01", "A", 100, 100), ("2020-01-02", "B", 200, 200), ("2020-01-03", "C", 300, 300), ("2020-01-04", "D", 400, 400), ("2020-01-05", "E", 500, 500)]},
        "C": {"prediction": "test", "pass": True, "non_delivery_diffs_copy_vs_orig": 0, "non_delivery_diffs_orig_vs_copy": 0, "row_count_copy": 1000, "row_count_orig": 1000, "differences_2020_plus": 0},
        "D": {"prediction": "test", "pass": True, "total_backfilled": 1000, "bad_deliv_pct_range": 0, "bad_deliv_qty_gt_volume": 0, "bad_deliv_qty_gt_mto_qtytraded": 0, "bad_recalc_vs_published": 0, "pct_out_of_range": 0.0, "pct_recalc_mismatch": 0.0},
        "E": {"prediction": "test", "pass": True, "overwrite_count_vs_original": 0},
        "F": {"prediction": "test", "pass": True, "store_rows_still_null": 5},
        "G": {"prediction": "test", "pass": True, "error": None, "arm_results": {"Arm_A": True, "Arm_B": True, "Arm_C": True, "Arm_D": True}},
    }
    stats = {
        "mto_files_on_disk": 100, "mto_files_used": 95, "weekend_fetched": 0, "weekend_absent": 0,
        "calendar_count": 100, "dates_with_data": 95, "dates_missing": 0,
        "rows_backfilled": 10000, "distinct_symbols": 500, "total_parse_rejects": 0,
        "non_null_start": "2010-01-04", "non_null_end": "2020-01-01",
        "yearly": {"2010": {"total": 1000, "filled": 1000}, "2011": {"total": 1000, "filled": 999}},
    }

    report1, digest1 = bf.generate_report(arms, stats)
    report2, digest2 = bf.generate_report(arms, stats)

    assert report1 == report2, "Two runs produced different report text"
    assert digest1 == digest2, f"Two runs produced different digest: {digest1} vs {digest2}"
    assert len(digest1) == 64, f"Digest not 64 hex chars: {digest1}"
