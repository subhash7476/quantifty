"""Options-Wall snapshot store — the accumulating, multi-symbol chain cache.

Decoupled from NiftyShield: `scripts/nifty_shield_paper/chain_poller.py` writes a
single-snapshot overwrite cache (`data/options/chain_cache.duckdb`, Nifty-only,
latest cycle only) for its marks source. The wall scanner needs the *trail* —
accumulated snapshots across Nifty AND BankNifty — so it owns this separate
append-only store.

Conventions:
  - Append-only: every cycle inserts rows stamped with ONE explicit
    `snapshot_timestamp`; nothing deletes or overwrites.
  - `latest_snapshot()` reads the newest cycle per (underlying, expiry) via
    MAX(snapshot_timestamp).
  - Schema mirrors `option_chain_snapshot` (sequence + indexes) so the row shape
    is identical to `OptionsProvider._init_db`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import duckdb

from core.data.options_provider import OptionChainRow

ROOT = Path(__file__).resolve().parents[2]
WALL_SNAPSHOT_DB = ROOT / "data" / "options" / "wall_chain_snapshots.duckdb"

_SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS option_chain_snapshot (
    snapshot_id       INTEGER DEFAULT nextval('snapshot_id_seq'),
    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    underlying_symbol  VARCHAR NOT NULL,
    expiry_date        VARCHAR NOT NULL,
    strike_price       DOUBLE NOT NULL,
    option_type        VARCHAR NOT NULL,
    instrument_key     VARCHAR NOT NULL,
    tradingsymbol      VARCHAR NOT NULL,
    ltp                DOUBLE,
    open               DOUBLE,
    high               DOUBLE,
    low                DOUBLE,
    close              DOUBLE,
    oi                 BIGINT DEFAULT 0,
    oi_change          BIGINT DEFAULT 0,
    oi_change_pct      DOUBLE DEFAULT 0.0,
    volume             BIGINT DEFAULT 0,
    iv                 DOUBLE,
    delta              DOUBLE,
    gamma              DOUBLE,
    theta              DOUBLE,
    vega               DOUBLE,
    rho                DOUBLE,
    lot_size           INTEGER DEFAULT 75,
    underlying_ltp     DOUBLE,
    best_bid           DOUBLE,
    best_ask           DOUBLE,
    PRIMARY KEY (snapshot_id)
)
"""

_INSERT_SQL = """
INSERT INTO option_chain_snapshot (
    snapshot_timestamp, underlying_symbol, expiry_date, strike_price,
    option_type, instrument_key, tradingsymbol, ltp, open, high, low, close,
    oi, oi_change, oi_change_pct, volume, iv, delta, gamma, theta, vega, rho,
    lot_size, underlying_ltp, best_bid, best_ask
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SEQUENCE IF NOT EXISTS snapshot_id_seq START 1")
    conn.execute(_SNAPSHOT_TABLE_SQL)
    # migrate an existing store created before best_bid/best_ask were added
    conn.execute("ALTER TABLE option_chain_snapshot ADD COLUMN IF NOT EXISTS best_bid DOUBLE")
    conn.execute("ALTER TABLE option_chain_snapshot ADD COLUMN IF NOT EXISTS best_ask DOUBLE")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wall_underlying "
                 "ON option_chain_snapshot(underlying_symbol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wall_expiry "
                 "ON option_chain_snapshot(expiry_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wall_strike "
                 "ON option_chain_snapshot(strike_price)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wall_timestamp "
                 "ON option_chain_snapshot(snapshot_timestamp)")


def append_snapshot(
    rows: List[OptionChainRow],
    underlying: str,
    expiry: str,
    ts: Optional[datetime] = None,
    db_path: Path = WALL_SNAPSHOT_DB,
    quotes: Optional[dict] = None,
) -> datetime:
    """Append one full chain snapshot for (underlying, expiry) under a single ts.

    `quotes` (optional, keyed by instrument_key with best_bid/best_ask) is the
    bid/ask enrichment from `UpstoxMarketData.fetch_quotes_batch`; when absent the
    two columns are stored NULL.
    """
    ts = ts or datetime.now()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        init_schema(conn)
        for row in rows:
            q = (quotes or {}).get(row.instrument_key) or {}
            conn.execute(_INSERT_SQL, [
                ts, underlying, expiry, row.strike, row.option_type,
                row.instrument_key, row.tradingsymbol, row.ltp,
                row.open, row.high, row.low, row.close,
                row.oi if row.oi else 0,
                row.oi_change if row.oi_change else 0,
                row.oi_change_pct if row.oi_change_pct else 0.0,
                row.volume if row.volume else 0,
                row.iv, row.delta, row.gamma, row.theta, row.vega, row.rho,
                row.lot_size, row.underlying_ltp,
                q.get("best_bid"), q.get("best_ask"),
            ])
        conn.commit()
    finally:
        conn.close()
    return ts


def _migrate_columns(db_path: Path) -> None:
    """Add best_bid/best_ask to a store created before they existed (idempotent)."""
    conn = duckdb.connect(str(db_path))
    try:
        init_schema(conn)
    finally:
        conn.close()


def latest_snapshot(
    underlying: str,
    expiry: str,
    db_path: Path = WALL_SNAPSHOT_DB,
) -> List[OptionChainRow]:
    """Newest cycle for (underlying, expiry), or [] if none recorded."""
    if not db_path.exists():
        return []
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        cols = [r[0] for r in conn.execute(
            "PRAGMA table_info('option_chain_snapshot')").fetchall()]
    finally:
        conn.close()
    if "best_bid" not in cols:
        _migrate_columns(db_path)
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        result = conn.execute(
            """
            SELECT strike_price, option_type, instrument_key, tradingsymbol,
                   expiry_date, ltp, open, high, low, close,
                   oi, oi_change, oi_change_pct, volume,
                   iv, delta, gamma, theta, vega, rho,
                   lot_size, underlying_ltp, best_bid, best_ask
            FROM option_chain_snapshot
            WHERE underlying_symbol = ? AND expiry_date = ?
              AND snapshot_timestamp = (
                  SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot
                  WHERE underlying_symbol = ? AND expiry_date = ?
              )
            ORDER BY strike_price, option_type
            """,
            [underlying, expiry, underlying, expiry],
        ).fetchall()
    finally:
        conn.close()

    chain = []
    for row in result:
        row_obj = OptionChainRow(
            strike=row[0], option_type=row[1], instrument_key=row[2],
            tradingsymbol=row[3], expiry=row[4], ltp=row[5], open=row[6],
            high=row[7], low=row[8], close=row[9], oi=row[10],
            oi_change=row[11], oi_change_pct=row[12], volume=row[13],
            iv=row[14], delta=row[15], gamma=row[16], theta=row[17],
            vega=row[18], rho=row[19], lot_size=row[20],
            underlying_ltp=row[21],
        )
        row_obj.best_bid = row[22]
        row_obj.best_ask = row[23]
        chain.append(row_obj)
    return chain


def snapshot_timestamps(
    underlying: str,
    db_path: Path = WALL_SNAPSHOT_DB,
) -> List[datetime]:
    if not db_path.exists():
        return []
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            "SELECT DISTINCT snapshot_timestamp FROM option_chain_snapshot "
            "WHERE underlying_symbol = ? ORDER BY snapshot_timestamp",
            [underlying],
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]
