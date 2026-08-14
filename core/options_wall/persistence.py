"""Options-Wall scan-result persistence.

Three tables in one DuckDB file, all append-only (latest-wins reads):

  scan_results   — one row per ScanResult (the persisted farm list / scan trail)
  session_regime — one row per (trade_date, underlying, ts); the regime river
  oi_baseline    — 09:15 OI per strike, captured once per session (INSERT OR IGNORE)

The wall snapshot store (`wall_chain_snapshots.duckdb`) holds raw chains; this
file holds derived scan output. Writers open short-lived connections — the same
single-writer discipline as the snapshot store.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb

from core.analytics.chain_scanner import ScanResult

ROOT = Path(__file__).resolve().parents[2]
WALL_RESULTS_DB = ROOT / "data" / "options" / "wall_scan_results.duckdb"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_results (
    ts              TIMESTAMP NOT NULL,
    underlying      VARCHAR NOT NULL,
    expiry          VARCHAR NOT NULL,
    strike          DOUBLE,
    option_type     VARCHAR,
    screen          VARCHAR NOT NULL,
    structure       VARCHAR NOT NULL,
    regime          VARCHAR,
    score           DOUBLE,
    credit          DOUBLE,
    iv_minus_rv      DOUBLE,
    pin_conviction  DOUBLE,
    reason          VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_scan_underlying ON scan_results(underlying);
CREATE INDEX IF NOT EXISTS idx_scan_ts ON scan_results(ts);

CREATE TABLE IF NOT EXISTS session_regime (
    trade_date        DATE NOT NULL,
    underlying        VARCHAR NOT NULL,
    ts                TIMESTAMP NOT NULL,
    regime            VARCHAR,
    net_gamma_total   DOUBLE,
    zero_gamma_level  DOUBLE,
    pin_strike        DOUBLE,
    put_wall          DOUBLE,
    call_wall         DOUBLE,
    atm_iv            DOUBLE,
    realized_vol      DOUBLE
);
CREATE INDEX IF NOT EXISTS idx_regime_underlying ON session_regime(underlying, trade_date, ts);

CREATE TABLE IF NOT EXISTS oi_baseline (
    underlying  VARCHAR NOT NULL,
    trade_date  DATE NOT NULL,
    strike      DOUBLE NOT NULL,
    option_type VARCHAR NOT NULL,
    oi          BIGINT NOT NULL,
    PRIMARY KEY (underlying, trade_date, strike, option_type)
);
"""


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_SCHEMA)


def write_scan_results(
    results: List[ScanResult],
    underlying: str,
    ts: Optional[datetime] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> int:
    ts = ts or datetime.now()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        init_schema(conn)
        for r in results:
            conn.execute(
                "INSERT INTO scan_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [ts, underlying, r.expiry, r.strike, r.option_type, r.screen,
                 r.structure, r.regime, r.score, r.credit, r.iv_minus_rv,
                 r.pin_conviction, r.reason],
            )
        conn.commit()
    finally:
        conn.close()
    return len(results)


def write_regime(
    underlying: str,
    snapshot: Dict,
    ts: Optional[datetime] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> None:
    """snapshot keys: trade_date, regime, net_gamma_total, zero_gamma_level,
    pin_strike, put_wall, call_wall, atm_iv, realized_vol."""
    ts = ts or datetime.now()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        init_schema(conn)
        conn.execute(
            "INSERT INTO session_regime VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                snapshot.get("trade_date", date.today()),
                underlying, ts,
                snapshot.get("regime"),
                snapshot.get("net_gamma_total"),
                snapshot.get("zero_gamma_level"),
                snapshot.get("pin_strike"),
                snapshot.get("put_wall"),
                snapshot.get("call_wall"),
                snapshot.get("atm_iv"),
                snapshot.get("realized_vol"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def capture_oi_baseline(
    chain: List,
    underlying: str,
    trade_date: Optional[date] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> int:
    """Record 09:15 OI per strike once per session (idempotent via PK)."""
    trade_date = trade_date or date.today()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    n = 0
    try:
        init_schema(conn)
        for r in chain:
            conn.execute(
                "INSERT OR IGNORE INTO oi_baseline VALUES (?,?,?,?,?)",
                [underlying, trade_date, r.strike, r.option_type, r.oi or 0],
            )
            n += 1
        conn.commit()
    finally:
        conn.close()
    return n


def get_oi_baseline(
    underlying: str,
    trade_date: Optional[date] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> Dict[Tuple[float, str], int]:
    trade_date = trade_date or date.today()
    if not db_path.exists():
        return {}
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            "SELECT strike, option_type, oi FROM oi_baseline "
            "WHERE underlying = ? AND trade_date = ?",
            [underlying, trade_date],
        ).fetchall()
    finally:
        conn.close()
    return {(r[0], r[1]): r[2] for r in rows}


def latest_regime(
    underlying: str,
    trade_date: Optional[date] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> Optional[Dict]:
    trade_date = trade_date or date.today()
    if not db_path.exists():
        return None
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        row = conn.execute(
            "SELECT * FROM session_regime WHERE underlying = ? AND trade_date = ? "
            "ORDER BY ts DESC LIMIT 1",
            [underlying, trade_date],
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    cols = ["trade_date", "underlying", "ts", "regime", "net_gamma_total",
            "zero_gamma_level", "pin_strike", "put_wall", "call_wall",
            "atm_iv", "realized_vol"]
    return dict(zip(cols, row))


_SCAN_COLS = ["ts", "underlying", "expiry", "strike", "option_type", "screen",
              "structure", "regime", "score", "credit", "iv_minus_rv",
              "pin_conviction", "reason"]


def latest_scan_results(
    underlying: str,
    db_path: Path = WALL_RESULTS_DB,
) -> Tuple[Optional[datetime], List[Dict]]:
    """Newest scan cycle for `underlying`: (ts, rows sorted by score desc)."""
    if not db_path.exists():
        return None, []
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        ts = conn.execute(
            "SELECT MAX(ts) FROM scan_results WHERE underlying = ?", [underlying],
        ).fetchone()[0]
        if ts is None:
            return None, []
        rows = conn.execute(
            "SELECT * FROM scan_results WHERE underlying = ? AND ts = ? "
            "ORDER BY score DESC",
            [underlying, ts],
        ).fetchall()
    finally:
        conn.close()
    return ts, [dict(zip(_SCAN_COLS, r)) for r in rows]


def regime_river(
    underlying: str,
    limit: int = 30,
    db_path: Path = WALL_RESULTS_DB,
) -> List[Dict]:
    """Latest regime per trade_date, ascending, capped at `limit`."""
    if not db_path.exists():
        return []
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT * FROM (
                SELECT *, row_number() OVER (PARTITION BY trade_date ORDER BY ts DESC) AS rn
                FROM session_regime WHERE underlying = ?
            ) WHERE rn = 1 ORDER BY trade_date ASC LIMIT ?
            """,
            [underlying, limit],
        ).fetchall()
    finally:
        conn.close()
    cols = ["trade_date", "underlying", "ts", "regime", "net_gamma_total",
            "zero_gamma_level", "pin_strike", "put_wall", "call_wall",
            "atm_iv", "realized_vol"]
    return [dict(zip(cols, r)) for r in rows]
