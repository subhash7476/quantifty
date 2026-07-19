"""Tests for SFB certification arms — fed from real builder output, not
hand-built continuous tables. Each test inserts raw futures_bhavcopy data,
runs build_continuous(), then runs the arm on that output."""

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "sfb"))

import build_continuous_futures as B
import certify_futures_substrate as C


def _build_raw_store():
    """Create an in-memory DuckDB with the futures_bhavcopy schema and
    synthetic data for one underlying (TESTSTK) with 2 expiries, a
    contango roll, and a backwardation roll."""
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE futures_bhavcopy (
            underlying   VARCHAR,
            expiry_dt    DATE,
            trade_date   DATE,
            inst_type    VARCHAR,
            open         DOUBLE,
            high         DOUBLE,
            low          DOUBLE,
            close        DOUBLE,
            settle       DOUBLE,
            contracts    BIGINT,
            val_in_lakh  DOUBLE,
            open_int     BIGINT,
            chg_in_oi    BIGINT
        )
    """)
    con.execute("""
        CREATE TABLE fo_eligible_intervals (
            underlying  VARCHAR,
            valid_from  DATE,
            valid_to    DATE
        )
    """)

    base = date(2020, 1, 1)
    exp1 = date(2020, 1, 30)
    exp2 = date(2020, 2, 27)
    exp3 = date(2020, 3, 26)

    # Build 40 trading days (8 weeks, skip weekends)
    tds = []
    d = base
    while len(tds) < 40:
        if d.weekday() < 5:
            tds.append(d)
        d += timedelta(days=1)

    # Expiry 1 (near) — contango, rising prices from 100
    # Expiry 2 (next) — 2% above expiry 1
    # Expiry 3 (far) — also 2% above expiry 2
    for i, td in enumerate(tds):
        c1 = 100.0 + i * 0.5
        c2 = c1 * 1.02
        c3 = c1 * 1.04
        v1 = max(1000 - i * 10, 100)
        v2 = max(200 + i * 20, 100)

        con.execute("""
            INSERT INTO futures_bhavcopy VALUES
            ('TESTSTK', ?, ?, 'FUTSTK', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [exp1, td, c1, c1 + 0.5, c1 - 0.5, c1, c1, v1,
              c1 * 1000, 50000, 0])
        con.execute("""
            INSERT INTO futures_bhavcopy VALUES
            ('TESTSTK', ?, ?, 'FUTSTK', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [exp2, td, c2, c2 + 0.5, c2 - 0.5, c2, c2, v2,
              c2 * 500, 30000, 0])
        con.execute("""
            INSERT INTO futures_bhavcopy VALUES
            ('TESTSTK', ?, ?, 'FUTSTK', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [exp3, td, c3, c3 + 0.5, c3 - 0.5, c3, c3,
              max(v2 // 2, 50), c3 * 300, 15000, 0])

    return con, tds, exp1, exp2, exp3


class TestArmFA:
    def test_clean_splice_passes(self):
        """Run arm_fa against real builder output. With a clean synthetic
        contango series, every roll splice should satisfy the invariant:
        adj_return ≈ economic_return within tolerance."""
        con, _, _, _, _ = _build_raw_store()
        B.build_continuous(con)

        res = C.arm_fa(con)
        assert len(res.violations) == 0, (
            f"Expected 0 violations on clean data, got {len(res.violations)}: "
            f"{res.violations}")


class TestArmFB:
    def test_no_duplicates(self):
        con, _, _, _, _ = _build_raw_store()
        B.build_continuous(con)
        res = C.arm_fb(con)
        dupes = [v for v in res.violations if v[0] == "duplicate_raw"]
        assert len(dupes) == 0, f"Expected no duplicate violations"

    def test_detect_duplicate(self):
        con, _, _, _, _ = _build_raw_store()
        B.build_continuous(con)
        con.execute("""
            INSERT INTO futures_bhavcopy VALUES
            ('TESTSTK', '2020-01-30', '2020-01-01', 'FUTSTK',
             100, 101, 99, 100, 100, 1000, 100000, 50000, 10)
        """)
        res = C.arm_fb(con)
        dupes = [v for v in res.violations if v[0] == "duplicate_raw"]
        assert len(dupes) > 0, "Expected duplicate violation"


class TestArmFC:
    def test_no_lookahead(self):
        """Run arm_fc against builder output — every roll decision must match
        the independently computed roll date."""
        con, _, _, _, _ = _build_raw_store()
        B.build_continuous(con)
        res = C.arm_fc(con)
        assert len(res.violations) == 0, (
            f"Expected 0 lookahead violations, got {res.violations}")


class TestArmFD:
    def test_passes_on_clean_data(self):
        """Run arm_fd on a minimal fo_eligible_intervals."""
        con, _, _, _, _ = _build_raw_store()
        # Build a minimal eligible interval
        con.execute("""
            INSERT INTO fo_eligible_intervals VALUES
            ('TESTSTK', '2020-01-01', '2020-03-01')
        """)
        B.build_continuous(con)
        res = C.arm_fd(con)
        assert len(res.violations) == 0, (
            f"Expected 0 FD violations, got {res.violations}")


class TestArmFE:
    def test_all_boundaries_pass(self):
        res = C.arm_fe()
        assert len(res.violations) == 0, (
            f"Expected 0 fee violations, got {res.violations}")
