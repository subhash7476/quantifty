"""TradeRecorder — universal fill-seam trade recorder.

Records every executed trade from every strategy by hooking
ExecutionHandler._handle_broker_fill — the single seam all broker fills
flow through (PAPER and LIVE). Writes round-trip rows (entry fill → exit
fill) to trade_intelligence.duckdb for post-trade learning.

This is the generic successor to TradeIntelligenceSink (which was wired to
CarryRebalancerHook and therefore only ever saw TS Basis Daily). It addresses
the M0 report §11 limitations: real exit reasons, real fill-price MTM, and
automatic coverage of every runner (no per-strategy integration).

Design rules (inherited from the frozen M1 sink spec):
  1. Write-only — never blocks or alters execution. Any failure logs and
     disables; execution continues untouched.
  2. Idempotent — INSERT OR REPLACE on natural key (entry fill_id); safe
     under replay restarts.
  3. Signal snapshot immutable after INSERT; outcome columns transition
     NULL → populated on close.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb

_logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
DEFAULT_INDEX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS executed_trades (
    -- Identity (immutable)
    trade_id           VARCHAR PRIMARY KEY,   -- entry fill_id
    symbol             VARCHAR NOT NULL,
    direction          VARCHAR NOT NULL,      -- 'LONG' | 'SHORT'
    instrument_type    VARCHAR,
    entry_timestamp    TIMESTAMP NOT NULL,
    entry_price        DOUBLE NOT NULL,
    entry_quantity     DOUBLE NOT NULL,
    order_id           VARCHAR,
    signal_id          VARCHAR,
    strategy_name      VARCHAR NOT NULL,
    strategy_version   VARCHAR,

    -- Signal snapshot (immutable — never updated after INSERT)
    signal_snapshot    VARCHAR,               -- JSON of order metadata

    -- Regime context (immutable)
    vix_at_entry       DOUBLE,
    nifty_20d_at_entry DOUBLE,

    -- Outcome (NULL until exit — populated by UPDATE)
    exit_timestamp     TIMESTAMP,
    exit_price         DOUBLE,
    realized_pnl       DOUBLE,
    total_fees         DOUBLE,
    days_held          INTEGER,
    exit_reason        VARCHAR,               -- metadata exit_reason or 'CLOSED'

    event_ts           TIMESTAMP
)
"""


def _git_commit() -> str:
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
        ).decode().strip()
    except Exception:
        return "unknown"


class TradeRecorder:
    """Write-only round-trip recorder over the broker-fill seam. Never raises."""

    def __init__(self,
                 db_path: Optional[str] = None,
                 index_dir: Optional[str] = None,
                 enabled: bool = True):
        self._enabled = enabled
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._index_dir = Path(index_dir) if index_dir else DEFAULT_INDEX_DIR
        self._strategy_version = _git_commit()
        self._open: Dict[str, str] = {}          # symbol -> open trade_id
        self._regime_cache: Dict[date, Dict[str, Any]] = {}
        self._errors = 0
        self._inserts = 0
        self._updates = 0
        if self._enabled:
            self._init_db()

    @property
    def stats(self) -> Dict[str, int]:
        return {"inserts": self._inserts, "updates": self._updates,
                "errors": self._errors}

    def _init_db(self):
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            con = duckdb.connect(str(self._db_path))
            try:
                con.execute(_SCHEMA)
                con.execute(
                    "CREATE INDEX IF NOT EXISTS idx_exec_trades_symbol "
                    "ON executed_trades (symbol)")
                con.execute(
                    "CREATE INDEX IF NOT EXISTS idx_exec_trades_entry "
                    "ON executed_trades (entry_timestamp)")
            finally:
                con.close()
        except Exception as e:
            _logger.error("TradeRecorder: schema init failed — disabled: %s", e)
            self._enabled = False
            self._errors += 1

    def on_fill(self, fill, order, signed_qty_before: float,
                realized_pnl: float):
        """Record a fill's effect on the round-trip row. Never raises.

        Args:
            fill: FillEvent just processed by the position tracker.
            order: NormalizedOrder that produced the fill (None if unknown).
            signed_qty_before: net signed position quantity BEFORE the fill
                (+long / -short / 0 flat), as captured by the handler.
            realized_pnl: realized PnL this fill generated (position tracker).
        """
        if not self._enabled:
            return
        try:
            self._process(fill, order, signed_qty_before, realized_pnl)
        except Exception as e:
            _logger.error("TradeRecorder: %s — %s", fill.fill_id, e)
            self._errors += 1

    def _process(self, fill, order, signed_before, realized_pnl):
        fs = fill.quantity if fill.side == "BUY" else -fill.quantity
        signed_after = signed_before + fs

        if signed_before == 0 and signed_after != 0:
            self._insert_entry(fill, order, signed_after)
        elif signed_before != 0 and (signed_before > 0) != (fs > 0):
            # Reducing or flipping — closes min(|before|, |fill|) units.
            self._apply_close_fill(fill, order, signed_before, signed_after,
                                   realized_pnl)
            if (signed_after > 0) != (signed_before > 0) and signed_after != 0:
                # Flip: remainder opens the opposite side at the same fill.
                self._insert_entry(fill, order, signed_after)
        else:
            # Increasing an existing position (or zero-qty degenerate fill).
            if signed_before != 0:
                self._apply_add_fill(fill, signed_before)

    # --- entry ----------------------------------------------------------

    def _insert_entry(self, fill, order, signed_after):
        strategy = getattr(order, "strategy_id", None) or "unknown"
        signal_id = getattr(order, "signal_id", None)
        snapshot = None
        if order is not None:
            meta = getattr(getattr(order, "metadata", None),
                           "strategy_metadata", None)
            if meta:
                try:
                    snapshot = json.dumps(meta, default=str)
                except Exception:
                    snapshot = None

        regime = self._regime(fill.timestamp.date())
        trade_id = fill.fill_id
        con = duckdb.connect(str(self._db_path))
        try:
            con.execute("""
                INSERT OR REPLACE INTO executed_trades
                (trade_id, symbol, direction, instrument_type,
                 entry_timestamp, entry_price, entry_quantity,
                 order_id, signal_id, strategy_name, strategy_version,
                 signal_snapshot, vix_at_entry, nifty_20d_at_entry,
                 total_fees, event_ts)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                trade_id, fill.symbol,
                "LONG" if signed_after > 0 else "SHORT",
                str(getattr(getattr(order, "instrument_type", None),
                            "value", "") or "") or None,
                fill.timestamp, float(fill.price), abs(signed_after),
                str(getattr(order, "correlation_id", "")) or None,
                signal_id, strategy, self._strategy_version,
                snapshot, regime.get("vix"), regime.get("nifty_20d"),
                float(fill.fee or 0.0), datetime.now(timezone.utc),
            ))
        finally:
            con.close()
        self._open[fill.symbol] = trade_id
        self._inserts += 1

    def _apply_add_fill(self, fill, signed_before):
        trade_id = self._resolve_open(fill.symbol)
        if trade_id is None:
            _logger.warning(
                "TradeRecorder: add-fill %s on %s has no open row; skipped",
                fill.fill_id, fill.symbol)
            return
        con = duckdb.connect(str(self._db_path))
        try:
            row = con.execute(
                "SELECT entry_quantity, entry_price FROM executed_trades "
                "WHERE trade_id = ?", [trade_id]).fetchone()
            if not row:
                return
            old_qty, old_px = float(row[0]), float(row[1])
            new_qty = old_qty + abs(fill.quantity)
            vwap = ((old_qty * old_px + abs(fill.quantity) * fill.price)
                    / new_qty) if new_qty > 0 else old_px
            con.execute("""
                UPDATE executed_trades
                SET entry_quantity=?, entry_price=?,
                    total_fees=total_fees+?, event_ts=?
                WHERE trade_id=?
            """, (new_qty, vwap, float(fill.fee or 0.0),
                  datetime.now(timezone.utc), trade_id))
        finally:
            con.close()
        self._updates += 1

    # --- exit -----------------------------------------------------------

    def _apply_close_fill(self, fill, order, signed_before, signed_after,
                          realized_pnl):
        trade_id = self._resolve_open(fill.symbol)
        if trade_id is None:
            _logger.warning(
                "TradeRecorder: closing fill %s on %s has no open row",
                fill.fill_id, fill.symbol)
            return
        fs = fill.quantity if fill.side == "BUY" else -fill.quantity

        exit_reason = None
        if order is not None:
            meta = getattr(getattr(order, "metadata", None),
                           "strategy_metadata", None) or {}
            exit_reason = meta.get("exit_reason")
        # The held trade is fully closed once the fill covers its whole size —
        # true both for flatten-to-zero and for flips (residual reopens new).
        fully_closed = abs(fs) >= abs(signed_before)

        con = duckdb.connect(str(self._db_path))
        try:
            if fully_closed:
                row = con.execute(
                    "SELECT entry_timestamp FROM executed_trades "
                    "WHERE trade_id=?", [trade_id]).fetchone()
                days_held = None
                if row and row[0]:
                    days_held = max(
                        0, (fill.timestamp - row[0]).days)
                con.execute("""
                    UPDATE executed_trades
                    SET exit_timestamp=?, exit_price=?,
                        realized_pnl=COALESCE(realized_pnl,0)+?,
                        total_fees=total_fees+?,
                        days_held=?, exit_reason=COALESCE(?, ?), event_ts=?
                    WHERE trade_id=?
                """, (
                    fill.timestamp, float(fill.price), float(realized_pnl),
                    float(fill.fee or 0.0), days_held,
                    exit_reason, "CLOSED", datetime.now(timezone.utc),
                    trade_id))
                self._open.pop(fill.symbol, None)
            else:
                # Partial reduce — keep row open, accumulate pnl + fees.
                con.execute("""
                    UPDATE executed_trades
                    SET realized_pnl=COALESCE(realized_pnl,0)+?,
                        total_fees=total_fees+?, event_ts=?
                    WHERE trade_id=?
                """, (float(realized_pnl), float(fill.fee or 0.0),
                      datetime.now(timezone.utc), trade_id))
        finally:
            con.close()
        self._updates += 1

    def _resolve_open(self, symbol: str) -> Optional[str]:
        """Open trade_id for symbol — memory cache first, DB on miss/restart."""
        if symbol in self._open:
            return self._open[symbol]
        con = duckdb.connect(str(self._db_path))
        try:
            row = con.execute(
                "SELECT trade_id FROM executed_trades "
                "WHERE symbol=? AND exit_timestamp IS NULL "
                "ORDER BY entry_timestamp DESC LIMIT 1",
                [symbol]).fetchone()
            return row[0] if row else None
        except Exception:
            return None
        finally:
            con.close()

    # --- regime context ---------------------------------------------------

    def _regime(self, d: date) -> Dict[str, Any]:
        """India VIX close + Nifty trailing-20-session return at entry.

        Uses latest available 1d index file <= entry date (today's file does
        not exist yet during intraday fills). Returns {} on any gap — regime
        columns stay NULL rather than blocking the record."""
        cached = self._regime_cache.get(d)
        if cached is not None:
            return cached
        result: Dict[str, Any] = {}

        def f_for(dd: date) -> Optional[Path]:
            for back in range(8):
                f = self._index_dir / f"{dd - timedelta(days=back)}.duckdb"
                if f.exists():
                    return f
            return None

        try:
            base = f_for(d)
            if base is not None:
                c = duckdb.connect()
                c.execute(f"ATTACH '{base}' AS src (READ_ONLY)")
                row = c.execute(
                    "SELECT close FROM src.candles "
                    "WHERE symbol='NSE_INDEX|India VIX'").fetchone()
                if row and row[0]:
                    result["vix"] = float(row[0])
                row = c.execute(
                    "SELECT close FROM src.candles "
                    "WHERE symbol='NSE_INDEX|Nifty 50'").fetchone()
                c.close()
                if row and row[0]:
                    c0 = float(row[0])
                    closes = []
                    day = d - timedelta(days=1)
                    while len(closes) < 20 and day > d - timedelta(days=60):
                        f = self._index_dir / f"{day}.duckdb"
                        if f.exists():
                            c2 = duckdb.connect()
                            c2.execute(f"ATTACH '{f}' AS s (READ_ONLY)")
                            r = c2.execute(
                                "SELECT close FROM s.candles "
                                "WHERE symbol='NSE_INDEX|Nifty 50'"
                            ).fetchone()
                            c2.close()
                            if r and r[0]:
                                closes.append(float(r[0]))
                        day -= timedelta(days=1)
                    if len(closes) == 20 and closes[-1]:
                        result["nifty_20d"] = (c0 - closes[-1]) / closes[-1]
        except Exception as e:
            _logger.debug("TradeRecorder: regime lookup failed for %s: %s",
                          d, e)
            result = {}
        self._regime_cache[d] = result
        return result
