"""Tests for CarryMetricsDB — schema, writer, determinism hash.

All tests against in-memory or temp-file DuckDB. No market data dependencies.
"""
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from core.execution.portfolio.carry_metrics_db import CarryMetricsDB


@pytest.fixture
def db_mem():
    with CarryMetricsDB(":memory:") as db:
        yield db


@pytest.fixture
def db_temp():
    fd, path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    with CarryMetricsDB(path) as db:
        yield db
    Path(path).unlink(missing_ok=True)


def _sample_metadata(run_id="test-run-01"):
    return {
        "run_id": run_id,
        "git_commit": "abc1234",
        "generated_at": datetime(2026, 7, 24, 12, 0, 0),
        "window_label": "TRAIN",
        "window_lo": date(2016, 3, 31),
        "window_hi": date(2020, 12, 31),
        "gross_exposure": 10_000_000.0,
        "params_json": json.dumps({"slippage_bp": 5, "quintile": 0.20}),
        "determinism_hash": "abc_def_123",
        "source": "replay",
    }


def _sample_summary_row(run_id="test-run-01", fdate_str="2016-04-30"):
    return {
        "run_id": run_id,
        "formation_date": date.fromisoformat(fdate_str),
        "n_long": 15,
        "n_short": 14,
        "traded_value": 500_000.0,
        "turnover": 0.15,
        "fees_total": 120.0,
        "slippage_total": 250.0,
        "fee_brokerage": 40.0,
        "fee_stt": 50.0,
        "fee_exchange_txn": 5.0,
        "fee_sebi_fee": 3.0,
        "fee_stamp_duty": 2.0,
        "fee_gst": 20.0,
        "top3_conc": 0.35,
        "hhi": 0.08,
        "margin_util_pct": 18.5,
    }


class TestSchema:
    def test_create_schema_idempotent(self, db_mem):
        tables = db_mem._conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()
        names = {r[0] for r in tables}
        assert "run_metadata" in names
        assert "rebalance_summary" in names
        assert "rebalance_positions" in names
        assert "equity_curve" in names
        db_mem._create_schema()

    def test_tables_have_correct_columns(self, db_mem):
        cols = db_mem._conn.execute(
            "PRAGMA table_info('rebalance_summary')"
        ).fetchall()
        col_names = {r[1] for r in cols}
        expected = {"run_id", "formation_date", "n_long", "n_short",
                     "traded_value", "turnover", "fees_total", "slippage_total",
                     "fee_brokerage", "fee_stt", "fee_exchange_txn", "fee_sebi_fee",
                     "fee_stamp_duty", "fee_gst", "top3_conc", "hhi",
                     "margin_util_pct"}
        assert col_names >= expected


class TestMetadata:
    def test_write_and_read(self, db_mem):
        meta = _sample_metadata()
        db_mem.write_run_metadata(**meta)
        rows = db_mem._conn.execute(
            "SELECT * FROM run_metadata WHERE run_id=?", [meta["run_id"]]
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "abc1234"

    def test_write_updates_existing(self, db_mem):
        meta = _sample_metadata()
        db_mem.write_run_metadata(**meta)
        meta2 = {**meta, "git_commit": "def5678"}
        db_mem.write_run_metadata(**meta2)
        row = db_mem._conn.execute(
            "SELECT git_commit FROM run_metadata WHERE run_id=?", [meta["run_id"]]
        ).fetchone()
        assert row[0] == "def5678"


class TestRebalanceSummary:
    def test_write_single_row(self, db_mem):
        db_mem.write_run_metadata(**_sample_metadata())
        row = _sample_summary_row()
        db_mem.write_rebalance_summary(**row)
        rows = db_mem._conn.execute(
            "SELECT fees_total, slippage_total FROM rebalance_summary"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == pytest.approx(120.0)
        assert rows[0][1] == pytest.approx(250.0)

    def test_fee_fields_not_conflated(self, db_mem):
        db_mem.write_run_metadata(**_sample_metadata())
        row = _sample_summary_row()
        db_mem.write_rebalance_summary(**row)
        r = db_mem._conn.execute(
            "SELECT fees_total, slippage_total, fee_stt, fee_brokerage "
            "FROM rebalance_summary"
        ).fetchone()
        assert r[0] == pytest.approx(120.0)
        assert r[1] == pytest.approx(250.0)
        assert r[0] != pytest.approx(r[1])

    def test_write_multiple_formations(self, db_mem):
        db_mem.write_run_metadata(**_sample_metadata())
        for i in range(3):
            row = _sample_summary_row(fdate_str=f"2016-{4+i:02d}-30")
            db_mem.write_rebalance_summary(**row)
        count = db_mem._conn.execute(
            "SELECT COUNT(*) FROM rebalance_summary"
        ).fetchone()[0]
        assert count == 3


class TestRebalancePositions:
    def test_write_positions(self, db_mem):
        db_mem.write_run_metadata(**_sample_metadata())
        rows = [
            {"underlying": "ACC", "target_side": "LONG", "target_cap": 300_000.0,
             "z_carry_neut": 1.8, "quintile": 5, "action": "OPEN", "suppressed": False},
            {"underlying": "ADANIENT", "target_side": "SHORT", "target_cap": 280_000.0,
             "z_carry_neut": -2.1, "quintile": 1, "action": "OPEN", "suppressed": False},
        ]
        db_mem.write_rebalance_positions("test-run-01", date(2016, 4, 30), rows)
        result = db_mem._conn.execute(
            "SELECT underlying, target_side, quintile FROM rebalance_positions "
            "ORDER BY underlying"
        ).fetchall()
        assert len(result) == 2
        assert result[0] == ("ACC", "LONG", 5)
        assert result[1] == ("ADANIENT", "SHORT", 1)


class TestEquityCurve:
    def test_write_equity(self, db_mem):
        db_mem.write_run_metadata(**_sample_metadata())
        rows = [
            {"formation_date": date(2016, 4, 30), "cum_net_ret": 0.005,
             "drawdown_pct": 0.0},
            {"formation_date": date(2016, 5, 31), "cum_net_ret": 0.012,
             "drawdown_pct": 0.0},
            {"formation_date": date(2016, 6, 30), "cum_net_ret": 0.008,
             "drawdown_pct": -0.004},
        ]
        db_mem.write_equity_curve("test-run-01", rows)
        result = db_mem._conn.execute(
            "SELECT cum_net_ret, drawdown_pct FROM equity_curve ORDER BY formation_date"
        ).fetchall()
        assert len(result) == 3
        assert result[0][0] == pytest.approx(0.005)
        assert result[2][1] == pytest.approx(-0.004)


class TestDeterminismHash:
    def test_identical_runs_same_hash(self, db_temp):
        for run_id in ["run-a", "run-b"]:
            db_temp.write_run_metadata(**_sample_metadata(run_id=run_id))
            for i in range(2):
                row = _sample_summary_row(run_id=run_id, fdate_str=f"2016-{4+i:02d}-30")
                db_temp.write_rebalance_summary(**row)
            h = db_temp.compute_determinism_hash(run_id)
            db_temp._conn.execute(
                "UPDATE run_metadata SET determinism_hash=? WHERE run_id=?", [h, run_id]
            )
        assert db_temp.compute_determinism_hash("run-a") == db_temp.compute_determinism_hash("run-b")

    def test_different_data_different_hash(self, db_temp):
        db_temp.write_run_metadata(**_sample_metadata(run_id="run-1"))
        row = _sample_summary_row(run_id="run-1", fdate_str="2016-04-30")
        db_temp.write_rebalance_summary(**row)
        h1 = db_temp.compute_determinism_hash("run-1")

        db_temp.write_run_metadata(**_sample_metadata(run_id="run-2"))
        row2 = _sample_summary_row(run_id="run-2", fdate_str="2016-04-30")
        row2["fees_total"] = 999.0
        db_temp.write_rebalance_summary(**row2)
        h2 = db_temp.compute_determinism_hash("run-2")

        assert h1 != h2


class TestContextManager:
    def test_enter_exit(self):
        db = CarryMetricsDB(":memory:")
        assert db._conn is not None
        db.close()
        db = CarryMetricsDB(":memory:")  # re-open

    def test_with_statement(self, db_mem):
        assert db_mem._conn is not None
