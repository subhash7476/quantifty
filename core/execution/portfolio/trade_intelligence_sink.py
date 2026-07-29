"""Trade Intelligence Sink — write-only trade recorder (M1).

Receives portfolio deltas from CarryRebalancerHook, persists them
to trade_intelligence.duckdb. Never influences execution — if the
DB is unavailable, logs the error and continues.

Design rules (frozen M1 spec):
  1. Write-only — never blocks or alters execution.
  2. Consume deltas — not portfolio state. OPEN→INSERT, CLOSE→UPDATE.
  3. Idempotent — INSERT OR REPLACE semantics per natural trade_id.
  4. Timestamps recorded — event_ts + formation_date.
"""
from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import duckdb

_logger = logging.getLogger(__name__)


def _git_commit():
    import subprocess
    from pathlib import Path as _Path
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_Path(__file__).resolve().parents[3]),
        ).decode().strip()
    except Exception:
        return "unknown"


class TradeIntelligenceSink:
    """Append-only trade recorder. Idempotent — safe for replay restarts."""

    def __init__(self, db_path: str, strategy_name: str = "ts_basis_daily",
                 strategy_version: Optional[str] = None,
                 sector_csv: Optional[str] = None,
                 index_dir: Optional[str] = None):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._strategy_name = strategy_name
        self._strategy_version = strategy_version or _git_commit()
        self._sectors = self._load_sectors(sector_csv) if sector_csv else {}
        self._index_dir = Path(index_dir) if index_dir else None
        self._errors: int = 0
        self._inserts: int = 0
        self._updates: int = 0
        self._init_db()

    @staticmethod
    def _load_sectors(path):
        sectors = {}
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    sectors[row["symbol"]] = row["sector"]
        except Exception:
            pass
        return sectors

    @staticmethod
    def _load_regime(date_val, index_dir):
        f = index_dir / f"{date_val}.duckdb"
        if not f.exists():
            return {}
        try:
            c = duckdb.connect()
            c.execute(f"ATTACH '{f}' AS src (READ_ONLY)")
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|India VIX'"
            ).fetchone()
            vix = float(row[0]) if row else None
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|Nifty 50'"
            ).fetchone()
            nifty = float(row[0]) if row else None
            c.close()
            if vix is None or nifty is None:
                return {}
            # Approximate 20d lookback — use 20 calendar days
            from datetime import timedelta
            lookback = date_val - timedelta(days=30)
            lookback_f = index_dir / f"{date_val}.duckdb"
            n20 = None
            try:
                # Scan backward for nearest trading day with index data
                for offset in range(17, 30):
                    d = date_val - timedelta(days=offset)
                    f20 = index_dir / f"{d}.duckdb"
                    if f20.exists():
                        c2 = duckdb.connect()
                        c2.execute(f"ATTACH '{f20}' AS src (READ_ONLY)")
                        row = c2.execute(
                            "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|Nifty 50'"
                        ).fetchone()
                        c2.close()
                        if row and row[0] and nifty > 0:
                            n20 = (nifty - float(row[0])) / float(row[0])
                        break
            except Exception:
                pass
            return {"vix": vix, "nifty_20d": n20}
        except Exception:
            return {}

    def _init_db(self):
        try:
            con = duckdb.connect(str(self._db_path))
            con.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id           VARCHAR PRIMARY KEY,
                    underlying         VARCHAR NOT NULL,
                    side               VARCHAR NOT NULL,
                    entry_date         DATE NOT NULL,
                    strategy_name      VARCHAR NOT NULL,
                    strategy_version   VARCHAR NOT NULL,
                    z_ts               DOUBLE,
                    raw_z              DOUBLE,
                    quintile           TINYINT,
                    rank_in_date       INTEGER,
                    basis_reverting    BOOLEAN,
                    sector             VARCHAR,
                    vix_at_entry       DOUBLE,
                    nifty_20d_at_entry DOUBLE,
                    exit_date          DATE,
                    days_held          INTEGER,
                    exit_reason        VARCHAR,
                    stock_return       DOUBLE,
                    event_ts           TIMESTAMP
                )
            """)
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_entry ON trades (entry_date)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_trades_exit ON trades (exit_date)"
            )
            con.close()
        except Exception as e:
            _logger.error("TradeIntelligenceSink: schema init failed: %s", e)
            self._errors += 1

    @property
    def stats(self):
        return {"inserts": self._inserts, "updates": self._updates,
                "errors": self._errors}

    def __call__(self, fdate: date, deltas: list, position_entries: dict,
                 facts: list):
        """Process portfolio deltas. Never raises — errors are logged + counted.

        Args:
            fdate: formation date being processed
            deltas: List[Delta] — executed (non-suppressed) deltas
            position_entries: {underlying: {entry_date, cum_ret, trade_id, side}}
            facts: [(underlying, z, raw_z, quintile, basis_reverting), ...]
        """
        try:
            regime = {}
            if self._index_dir is not None:
                regime = self._load_regime(fdate, self._index_dir)
            self._process(fdate, deltas, position_entries, facts, regime)
        except Exception as e:
            _logger.error("TradeIntelligenceSink: %s — %s", fdate, e)
            self._errors += 1

    def _process(self, fdate, deltas, position_entries, facts, regime):
        now = datetime.now(timezone.utc)

        z_map = {}; rz_map = {}; q_map = {}; br_map = {}
        for f in facts:
            u = f[0]
            z_map[u] = float(f[1]) if len(f) > 1 and f[1] is not None else 0.0
            rz_map[u] = float(f[2]) if len(f) > 2 and f[2] is not None else z_map.get(u, 0.0)
            q_map[u] = int(f[3]) if len(f) > 3 and f[3] is not None else 3
            br_map[u] = bool(f[4]) if len(f) > 4 and f[4] is not None else False

        # Compute rank in date
        z_abs = [(u, abs(z_map[u])) for u in z_map]
        z_abs.sort(key=lambda r: r[1], reverse=True)
        rank_map = {u: i + 1 for i, (u, _) in enumerate(z_abs)}

        inserts = []
        updates = []

        for d in deltas:
            u = d.underlying
            if d.action == 'OPEN':
                # New entry
                trade_id = f"{u}_{fdate}_{d.target_side}"
                inserts.append((
                    trade_id, u, d.target_side, fdate,
                    self._strategy_name, self._strategy_version,
                    z_map.get(u), rz_map.get(u), q_map.get(u),
                    rank_map.get(u), br_map.get(u),
                    self._sectors.get(u, "Unclassified"),
                    regime.get('vix'), regime.get('nifty_20d'),
                    now,
                ))

            elif d.action == 'CLOSE':
                entry = position_entries.get(u, {})
                entry_date = entry.get("entry_date")
                cum_ret = entry.get("cum_ret", 0.0)
                days = (fdate - entry_date).days if entry_date else 0
                exit_reason = getattr(d, 'exit_reason', None) or 'EXIT_SIGNAL'
                updates.append((
                    fdate, days, exit_reason, cum_ret, now,
                    f"{u}_{entry_date}_{d.held_side}" if entry_date else None,
                ))

            elif d.action == 'FLIP':
                # Close old side
                entry = position_entries.get(u, {})
                entry_date = entry.get("entry_date")
                cum_ret = entry.get("cum_ret", 0.0)
                days = (fdate - entry_date).days if entry_date else 0
                exit_reason = getattr(d, 'exit_reason', None) or 'EXIT_SIGNAL'
                updates.append((
                    fdate, days, exit_reason, cum_ret, now,
                    f"{u}_{entry_date}_{d.held_side}" if entry_date else None,
                ))
                # Open new side
                trade_id = f"{u}_{fdate}_{d.target_side}"
                inserts.append((
                    trade_id, u, d.target_side, fdate,
                    self._strategy_name, self._strategy_version,
                    z_map.get(u), rz_map.get(u), q_map.get(u),
                    rank_map.get(u), br_map.get(u),
                    self._sectors.get(u, "Unclassified"),
                    regime.get('vix'), regime.get('nifty_20d'),
                    now,
                ))

        if inserts or updates:
            con = duckdb.connect(str(self._db_path))
            try:
                if inserts:
                    con.executemany("""
                        INSERT OR REPLACE INTO trades
                        (trade_id, underlying, side, entry_date,
                         strategy_name, strategy_version,
                         z_ts, raw_z, quintile, rank_in_date,
                         basis_reverting, sector,
                         vix_at_entry, nifty_20d_at_entry, event_ts)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, inserts)
                    self._inserts += len(inserts)
                if updates:
                    for row in updates:
                        trade_id = row[5]
                        if trade_id is None:
                            continue
                        con.execute("""
                            UPDATE trades
                            SET exit_date=?, days_held=?, exit_reason=?,
                                stock_return=?, event_ts=?
                            WHERE trade_id=?
                        """, (row[0], row[1], row[2], row[3], row[4], trade_id))
                    self._updates += len(updates)
            finally:
                con.close()
