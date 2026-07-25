"""Carry production-metrics database — DuckDB schema + writer.

Bridge: CARRY_PRODUCTION_METRICS_IMPLEMENTATION_PROMPT.md, Phase A.1.
Stores per-formation structural metrics (fees, slippage, turnover,
concentration, margin) and analytically-derived equity curves for
deterministic replay verification.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb

_logger = logging.getLogger(__name__)

TABLE_RUN_META = """
CREATE TABLE IF NOT EXISTS run_metadata (
    run_id TEXT PRIMARY KEY,
    git_commit TEXT,
    generated_at TIMESTAMP,
    window_label TEXT,
    window_lo DATE,
    window_hi DATE,
    gross_exposure DOUBLE,
    params_json TEXT,
    determinism_hash TEXT,
    source TEXT
)
"""

TABLE_REBALANCE_SUMMARY = """
CREATE TABLE IF NOT EXISTS rebalance_summary (
    run_id TEXT,
    formation_date DATE,
    n_long INTEGER,
    n_short INTEGER,
    traded_value DOUBLE,
    turnover DOUBLE,
    fees_total DOUBLE,
    slippage_total DOUBLE,
    fee_brokerage DOUBLE,
    fee_stt DOUBLE,
    fee_exchange_txn DOUBLE,
    fee_sebi_fee DOUBLE,
    fee_stamp_duty DOUBLE,
    fee_gst DOUBLE,
    top3_conc DOUBLE,
    hhi DOUBLE,
    margin_util_pct DOUBLE,
    PRIMARY KEY (run_id, formation_date)
)
"""

TABLE_REBALANCE_POSITIONS = """
CREATE TABLE IF NOT EXISTS rebalance_positions (
    run_id TEXT,
    formation_date DATE,
    underlying TEXT,
    target_side TEXT,
    target_cap DOUBLE,
    z_carry_neut DOUBLE,
    quintile INTEGER,
    action TEXT,
    suppressed BOOLEAN
)
"""

TABLE_EQUITY_CURVE = """
CREATE TABLE IF NOT EXISTS equity_curve (
    run_id TEXT,
    formation_date DATE,
    cum_net_ret DOUBLE,
    drawdown_pct DOUBLE,
    PRIMARY KEY (run_id, formation_date)
)
"""


class CarryMetricsDB:
    """DuckDB writer for Carry production metrics.

    Context-managed: `with CarryMetricsDB(path) as db: ...`
    Schema created idempotently on open. All writes are immediate
    (no transactions across calls).
    """

    def __init__(self, db_path: str):
        self._path = Path(db_path)
        self._conn = duckdb.connect(str(self._path))
        self._create_schema()

    def _create_schema(self):
        for ddl in [TABLE_RUN_META, TABLE_REBALANCE_SUMMARY,
                     TABLE_REBALANCE_POSITIONS, TABLE_EQUITY_CURVE]:
            self._conn.execute(ddl)

        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_rebalance_summary_run "
            "ON rebalance_summary(run_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_rebalance_positions_run_date "
            "ON rebalance_positions(run_id, formation_date)"
        )

    def write_run_metadata(
        self,
        *,
        run_id: str,
        git_commit: str,
        generated_at: datetime,
        window_label: str,
        window_lo: date,
        window_hi: date,
        gross_exposure: float,
        params_json: str,
        determinism_hash: Optional[str] = None,
        source: str,
    ):
        self._conn.execute(
            """INSERT OR REPLACE INTO run_metadata
               (run_id, git_commit, generated_at, window_label,
                window_lo, window_hi, gross_exposure, params_json,
                determinism_hash, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [run_id, git_commit, generated_at, window_label,
             window_lo, window_hi, gross_exposure, params_json,
             determinism_hash, source],
        )

    def write_rebalance_summary(
        self,
        *,
        run_id: str,
        formation_date: date,
        n_long: int,
        n_short: int,
        traded_value: float,
        turnover: float,
        fees_total: float,
        slippage_total: float,
        fee_brokerage: float,
        fee_stt: float,
        fee_exchange_txn: float,
        fee_sebi_fee: float,
        fee_stamp_duty: float,
        fee_gst: float,
        top3_conc: float,
        hhi: float,
        margin_util_pct: float,
    ):
        self._conn.execute(
            """INSERT OR REPLACE INTO rebalance_summary
               (run_id, formation_date, n_long, n_short, traded_value,
                turnover, fees_total, slippage_total, fee_brokerage, fee_stt,
                fee_exchange_txn, fee_sebi_fee, fee_stamp_duty, fee_gst,
                top3_conc, hhi, margin_util_pct)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [run_id, formation_date, n_long, n_short, traded_value,
             turnover, fees_total, slippage_total, fee_brokerage, fee_stt,
             fee_exchange_txn, fee_sebi_fee, fee_stamp_duty, fee_gst,
             top3_conc, hhi, margin_util_pct],
        )

    def write_rebalance_positions(
        self,
        run_id: str,
        formation_date: date,
        positions: List[Dict],
    ):
        for p in positions:
            self._conn.execute(
                """INSERT INTO rebalance_positions
                   (run_id, formation_date, underlying, target_side,
                    target_cap, z_carry_neut, quintile, action, suppressed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [run_id, formation_date, p["underlying"], p.get("target_side"),
                 p.get("target_cap"), p.get("z_carry_neut"), p.get("quintile"),
                 p.get("action"), p.get("suppressed")],
            )

    def write_equity_curve(self, run_id: str, rows: List[Dict]):
        for r in rows:
            self._conn.execute(
                """INSERT OR REPLACE INTO equity_curve
                   (run_id, formation_date, cum_net_ret, drawdown_pct)
                   VALUES (?, ?, ?, ?)""",
                [run_id, r["formation_date"], r["cum_net_ret"],
                 r["drawdown_pct"]],
            )

    def compute_determinism_hash(self, run_id: str) -> str:
        rows = self._conn.execute(
            """SELECT formation_date, fees_total, slippage_total,
                      traded_value, turnover, fee_brokerage, fee_stt,
                      fee_exchange_txn, fee_sebi_fee, fee_stamp_duty,
                      fee_gst, top3_conc, hhi, margin_util_pct
               FROM rebalance_summary
               WHERE run_id = ?
               ORDER BY formation_date""",
            [run_id],
        ).fetchall()

        if not rows:
            return ""

        serialized = json.dumps(
            [[str(r[0])] + list(r[1:]) for r in rows],
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False
