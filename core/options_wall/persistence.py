"""Options-Wall scan-result persistence.

Four tables in one DuckDB file; the first three are append-only (latest-wins reads):

  scan_results   — one row per ScanResult (the persisted farm list / scan trail)
  session_regime — one row per (trade_date, underlying, ts); the regime river
  oi_baseline    — 09:15 OI per strike, captured once per session (INSERT OR IGNORE)
  trades         — one row per paper iron fly, updated in place on close

The wall snapshot store (`wall_chain_snapshots.duckdb`) holds raw chains; this
file holds derived scan output. The poller is the SOLE writer of both stores;
Flask holds only read-only connections. Writers open short-lived connections.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb

from core.analytics.chain_scanner import ScanResult

ROOT = Path(__file__).resolve().parents[2]
WALL_RESULTS_DB = ROOT / "data" / "options" / "wall_scan_results.duckdb"

_READ_RETRY_ATTEMPTS = 30
_READ_RETRY_WAIT_S = 0.5


def _connect_ro(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Read-only connection with a bounded retry on the cross-process write lock.

    The poller writes this file; a read that lands mid-append raises transiently.
    Mirrors options_wall_store._connect_ro so dashboard reads ride out a write.
    """
    last = None
    for attempt in range(_READ_RETRY_ATTEMPTS):
        try:
            return duckdb.connect(str(db_path), read_only=True)
        except (duckdb.IOException, duckdb.ConnectionException) as exc:
            last = exc
            if attempt + 1 < _READ_RETRY_ATTEMPTS:
                time.sleep(_READ_RETRY_WAIT_S)
    raise last


def _connect_rw(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Read-write connection with a bounded retry (belt-and-suspenders).

    Only the poller writes this file now, but a single cycle alternates RO and RW
    connections against it (get_oi_baseline → write_scan_results → write_regime,
    plus the executor's open_trades → open_paper_trade). The short-lived
    `finally: close()` is what normally makes that fine; the retry — on both the
    cross-process IOException and the same-process ConnectionException ("different
    configuration than existing connections") — covers when a flip overlaps.
    """
    last = None
    for attempt in range(_READ_RETRY_ATTEMPTS):
        try:
            return duckdb.connect(str(db_path))
        except (duckdb.IOException, duckdb.ConnectionException) as exc:
            last = exc
            if attempt + 1 < _READ_RETRY_ATTEMPTS:
                time.sleep(_READ_RETRY_WAIT_S)
    raise last

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
    reason          VARCHAR,
    legs            VARCHAR
);

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
    realized_vol      DOUBLE,
    underlying_ltp    DOUBLE,
    gamma_by_strike   VARCHAR,
    net_gex_cr        DOUBLE,
    hhi               DOUBLE,
    hhi_call          DOUBLE,
    hhi_put           DOUBLE,
    pin_conviction    DOUBLE,
    pin_margin        DOUBLE,
    runner_up         DOUBLE,
    gex_at_pin_cr     DOUBLE,
    gamma_ceiling     DOUBLE,
    gamma_floor       DOUBLE,
    sigma_pts         DOUBLE,
    side_coverage     DOUBLE,
    side_reliable     BOOLEAN,
    hedge_ladder      VARCHAR,
    oi_rotation       VARCHAR
);

CREATE TABLE IF NOT EXISTS oi_baseline (
    underlying  VARCHAR NOT NULL,
    trade_date  DATE NOT NULL,
    strike      DOUBLE NOT NULL,
    option_type VARCHAR NOT NULL,
    oi          BIGINT NOT NULL,
    PRIMARY KEY (underlying, trade_date, strike, option_type)
);

CREATE SEQUENCE IF NOT EXISTS wall_trade_id_seq START 1;
CREATE TABLE IF NOT EXISTS trades (
    trade_id        INTEGER DEFAULT nextval('wall_trade_id_seq'),
    underlying      VARCHAR NOT NULL,
    expiry          VARCHAR NOT NULL,
    entry_ts        TIMESTAMP NOT NULL,
    short_strike    DOUBLE, call_wing DOUBLE, put_wing DOUBLE,
    qty             INTEGER,
    net_credit      DOUBLE, entry_fees DOUBLE, max_loss DOUBLE,
    exit_ts         TIMESTAMP,
    exit_mark       DOUBLE, exit_fees DOUBLE,
    gross_pnl       DOUBLE, net_pnl DOUBLE, exit_reason VARCHAR,
    return_on_margin DOUBLE, entry_legs VARCHAR, exit_legs VARCHAR,
    PRIMARY KEY (trade_id)
);
"""

# scan_results and session_regime carry no secondary index, and none of these
# tables gains one. Every write here opens a connection and closes it (the
# cross-process lock leaves no choice), and each close checkpoints the whole
# index set: measured at 265 MB per 1,000 checkpoints indexed vs 1.3 MB
# unindexed. That is why this file reached 836 MB holding 7.9 MB of rows.
# The primary keys on oi_baseline (INSERT OR IGNORE) and trades (identity) stay
# — they are load-bearing, and both tables are written a handful of times a
# session rather than hundreds. Reads are filters over a few thousand rows.
_STALE_INDEXES = ("idx_scan_underlying", "idx_scan_ts",
                  "idx_regime_underlying", "idx_trades_underlying")


_REGIME_BASE_COLS = ["trade_date", "underlying", "ts", "regime", "net_gamma_total",
                     "zero_gamma_level", "pin_strike", "put_wall", "call_wall",
                     "atm_iv", "realized_vol", "underlying_ltp", "gamma_by_strike"]
_REGIME_WALL_COLS = {
    "net_gex_cr": "DOUBLE", "hhi": "DOUBLE", "hhi_call": "DOUBLE", "hhi_put": "DOUBLE",
    "pin_conviction": "DOUBLE", "pin_margin": "DOUBLE", "runner_up": "DOUBLE",
    "gex_at_pin_cr": "DOUBLE", "gamma_ceiling": "DOUBLE", "gamma_floor": "DOUBLE",
    "sigma_pts": "DOUBLE", "side_coverage": "DOUBLE", "side_reliable": "BOOLEAN",
    "hedge_ladder": "VARCHAR", "oi_rotation": "VARCHAR",
}
_REGIME_COLS = _REGIME_BASE_COLS + list(_REGIME_WALL_COLS)
_REGIME_JSON_COLS = ("gamma_by_strike", "hedge_ladder", "oi_rotation")
_REGIME_SELECT = ", ".join(_REGIME_COLS)


def _regime_dict(row) -> Dict:
    d = dict(zip(_REGIME_COLS, row))
    for col in _REGIME_JSON_COLS:
        if d.get(col) is not None:
            d[col] = json.loads(d[col])
    return d


def _align_trade_id_sequence(conn: duckdb.DuckDBPyConnection) -> None:
    """Push wall_trade_id_seq past MAX(trade_id) when a rebuilt store left it behind.

    A store rebuilt by the compaction script keeps its rows but recreates the
    sequence at START 1, so nextval() collides with an existing primary key and
    every open is refused. DuckDB 1.4 has no ALTER SEQUENCE ... RESTART, so the
    sequence is burned forward instead; reading duckdb_sequences() first means an
    already-aligned sequence is not consumed (no trade_id gaps).
    """
    max_id = conn.execute("SELECT COALESCE(MAX(trade_id), 0) FROM trades").fetchone()[0]
    if not max_id:
        return
    row = conn.execute(
        "SELECT start_value, last_value, increment_by FROM duckdb_sequences() "
        "WHERE sequence_name = 'wall_trade_id_seq'").fetchone()
    if row is None:
        return
    start, last, step = row
    nxt = start if last is None else last + step
    if nxt > max_id:
        return
    conn.execute("SELECT nextval('wall_trade_id_seq') FROM range(?)",
                 [max_id - nxt + 1])


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_SCHEMA)
    # drop the indexes an older store was created with (see _STALE_INDEXES)
    for stale in _STALE_INDEXES:
        conn.execute(f"DROP INDEX IF EXISTS {stale}")
    # migrate a trades table created before these columns existed
    for col in ("return_on_margin DOUBLE", "entry_legs VARCHAR", "exit_legs VARCHAR"):
        conn.execute(f"ALTER TABLE trades ADD COLUMN IF NOT EXISTS {col}")
    _align_trade_id_sequence(conn)
    # migrate a session_regime table created before spot/gamma columns existed
    for col in ("underlying_ltp DOUBLE", "gamma_by_strike VARCHAR"):
        conn.execute(f"ALTER TABLE session_regime ADD COLUMN IF NOT EXISTS {col}")
    # migrate a session_regime table created before the wall-metrics columns existed
    for col, typ in _REGIME_WALL_COLS.items():
        conn.execute(f"ALTER TABLE session_regime ADD COLUMN IF NOT EXISTS {col} {typ}")
    # migrate a scan_results table created before the iron-fly legs column existed
    conn.execute("ALTER TABLE scan_results ADD COLUMN IF NOT EXISTS legs VARCHAR")


def write_scan_results(
    results: List[ScanResult],
    underlying: str,
    ts: Optional[datetime] = None,
    db_path: Path = WALL_RESULTS_DB,
) -> int:
    ts = ts or datetime.now()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect_rw(db_path)
    try:
        init_schema(conn)
        for r in results:
            conn.execute(
                "INSERT INTO scan_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [ts, underlying, r.expiry, r.strike, r.option_type, r.screen,
                 r.structure, r.regime, r.score, r.credit, r.iv_minus_rv,
                 r.pin_conviction, r.reason,
                 json.dumps(r.legs) if r.legs is not None else None],
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
    """snapshot keys: every _REGIME_COLS name except underlying/ts (missing keys
    persist as NULL); gamma_by_strike / hedge_ladder / oi_rotation are stored as JSON."""
    ts = ts or datetime.now()
    values = dict(snapshot)
    values["underlying"] = underlying
    values["ts"] = ts
    values.setdefault("trade_date", date.today())
    for col in _REGIME_JSON_COLS:
        if values.get(col) is not None:
            values[col] = json.dumps(values[col])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect_rw(db_path)
    try:
        init_schema(conn)
        conn.execute(
            f"INSERT INTO session_regime ({_REGIME_SELECT}) VALUES "
            f"({', '.join('?' for _ in _REGIME_COLS)})",
            [values.get(c) for c in _REGIME_COLS],
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
    conn = _connect_rw(db_path)
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
    conn = _connect_ro(db_path)
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
    conn = _connect_ro(db_path)
    try:
        row = conn.execute(
            f"SELECT {_REGIME_SELECT} FROM session_regime WHERE underlying = ? AND trade_date = ? "
            "ORDER BY ts DESC LIMIT 1",
            [underlying, trade_date],
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return _regime_dict(row)


def regime_at(
    underlying: str,
    ts: datetime,
    db_path: Path = WALL_RESULTS_DB,
) -> Optional[Dict]:
    """The session_regime cycle in force at `ts` — at or nearest before it.

    Scoped to `ts`'s own trade date: a trade's entry context is the state of
    that session, never yesterday's close. Returns None when the session wrote
    no cycle before `ts`.
    """
    if not db_path.exists():
        return None
    conn = _connect_ro(db_path)
    try:
        row = conn.execute(
            f"SELECT {_REGIME_SELECT} FROM session_regime WHERE underlying = ? "
            "AND trade_date = ? AND ts <= ? ORDER BY ts DESC LIMIT 1",
            [underlying, ts.date(), ts],
        ).fetchone()
    finally:
        conn.close()
    return _regime_dict(row) if row else None


_SCAN_COLS = ["ts", "underlying", "expiry", "strike", "option_type", "screen",
              "structure", "regime", "score", "credit", "iv_minus_rv",
              "pin_conviction", "reason", "legs"]


def _scan_dict(row) -> Dict:
    d = dict(zip(_SCAN_COLS, row))
    if d.get("legs") is not None:
        d["legs"] = json.loads(d["legs"])
    return d


def latest_scan_results(
    underlying: str,
    db_path: Path = WALL_RESULTS_DB,
) -> Tuple[Optional[datetime], List[Dict]]:
    """Newest scan cycle for `underlying`: (ts, rows sorted by score desc)."""
    if not db_path.exists():
        return None, []
    conn = _connect_ro(db_path)
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
    return ts, [_scan_dict(r) for r in rows]


def signal_at(
    underlying: str,
    ts: datetime,
    db_path: Path = WALL_RESULTS_DB,
) -> List[Dict]:
    """The scan cycle the executor acted on at `ts` — at or nearest before it.

    Returns every row of that one cycle, best score first, scoped to `ts`'s own
    trade date. Empty when the session scanned nothing before `ts`.
    """
    if not db_path.exists():
        return []
    conn = _connect_ro(db_path)
    try:
        cycle = conn.execute(
            "SELECT MAX(ts) FROM scan_results WHERE underlying = ? "
            "AND ts <= ? AND CAST(ts AS DATE) = ?",
            [underlying, ts, ts.date()],
        ).fetchone()[0]
        if cycle is None:
            return []
        rows = conn.execute(
            "SELECT * FROM scan_results WHERE underlying = ? AND ts = ? "
            "ORDER BY score DESC",
            [underlying, cycle],
        ).fetchall()
    finally:
        conn.close()
    return [_scan_dict(r) for r in rows]


_TRADE_COLS = ["trade_id", "underlying", "expiry", "entry_ts", "short_strike",
               "call_wing", "put_wing", "qty", "net_credit", "entry_fees",
               "max_loss", "exit_ts", "exit_mark", "exit_fees", "gross_pnl",
               "net_pnl", "exit_reason", "return_on_margin", "entry_legs", "exit_legs"]


def _legs_json(fly) -> str:
    return json.dumps([{"side": l.side, "type": l.option_type,
                        "strike": l.strike, "mid": l.entry_mid} for l in fly.legs])


def open_paper_trade(underlying, expiry, fly, entry_ts, db_path=WALL_RESULTS_DB) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect_rw(db_path)
    try:
        init_schema(conn)
        row = conn.execute(
            "INSERT INTO trades (underlying, expiry, entry_ts, short_strike, "
            "call_wing, put_wing, qty, net_credit, entry_fees, max_loss, entry_legs) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING trade_id",
            [underlying, expiry, entry_ts, fly.short_strike, fly.call_wing,
             fly.put_wing, fly.qty, fly.net_credit, fly.entry_fees, fly.max_loss,
             _legs_json(fly)],
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return row[0]


def _trades_table_exists(db_path: Path) -> bool:
    """True if the `trades` table exists. Read-only by design: the read path must
    never create it — the poller is the results DB's sole writer, and Flask reads
    trades every ~7s, so a create-on-read here would make Flask a second writer."""
    conn = _connect_ro(db_path)
    try:
        row = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = 'trades'").fetchone()
    finally:
        conn.close()
    return bool(row and row[0])


def open_trades(underlying, db_path=WALL_RESULTS_DB) -> List[Dict]:
    if not db_path.exists() or not _trades_table_exists(db_path):
        return []
    conn = _connect_ro(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM trades WHERE underlying = ? AND exit_ts IS NULL "
            "ORDER BY entry_ts", [underlying],
        ).fetchall()
    finally:
        conn.close()
    return [dict(zip(_TRADE_COLS, r)) for r in rows]


def all_trades(underlying, db_path=WALL_RESULTS_DB) -> List[Dict]:
    """Every paper trade for `underlying` (open and closed), newest entry first."""
    if not db_path.exists() or not _trades_table_exists(db_path):
        return []
    conn = _connect_ro(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM trades WHERE underlying = ? ORDER BY entry_ts DESC",
            [underlying],
        ).fetchall()
    finally:
        conn.close()
    return [dict(zip(_TRADE_COLS, r)) for r in rows]


def close_paper_trade(trade_id, exit_ts, exit_mark, exit_fees, gross_pnl,
                      net_pnl, exit_reason, return_on_margin=None, exit_legs=None,
                      db_path=WALL_RESULTS_DB) -> None:
    conn = _connect_rw(db_path)
    try:
        init_schema(conn)
        conn.execute(
            "UPDATE trades SET exit_ts=?, exit_mark=?, exit_fees=?, gross_pnl=?, "
            "net_pnl=?, exit_reason=?, return_on_margin=?, exit_legs=? WHERE trade_id=?",
            [exit_ts, exit_mark, exit_fees, gross_pnl, net_pnl, exit_reason,
             return_on_margin, exit_legs, trade_id],
        )
        conn.commit()
    finally:
        conn.close()


def regime_river(
    underlying: str,
    limit: int = 30,
    db_path: Path = WALL_RESULTS_DB,
) -> List[Dict]:
    """Latest regime row for each of the newest `limit` sessions, ascending."""
    if not db_path.exists():
        return []
    conn = _connect_ro(db_path)
    try:
        rows = conn.execute(
            f"""
            SELECT {_REGIME_SELECT} FROM (
                SELECT *, row_number() OVER (PARTITION BY trade_date ORDER BY ts DESC) AS rn
                FROM session_regime WHERE underlying = ?
            ) WHERE rn = 1 ORDER BY trade_date DESC LIMIT ?
            """,
            [underlying, limit],
        ).fetchall()
    finally:
        conn.close()
    return [_regime_dict(r) for r in reversed(rows)]
