"""NiftyShield — option-chain poller (E7-4 marks populator, implementation prompt 2026-08-09).

The NiftyShield PAPER runner prices struck option legs against REAL Upstox V3
marks read from `data/options/chain_cache.duckdb`
(`ChainSnapshotMarksSource`). Nothing else writes that file — this standalone,
long-running poller is its writer (operator decision 2026-08-09: dedicated,
self-contained, NOT coupled to the dashboard cache).

Two load-bearing, empirically-verified constraints drive the design:

1. **DuckDB cross-process write lock (§2.1).** A held read-write DuckDB
   connection blocks any other process from opening the same file even
   read-only. The runner's marks source opens a fresh read-only connection on
   every call, so the poller must NEVER hold the cache's write connection
   across its sleep. Mandated pattern: each cycle writes a FRESH single-snapshot
   DB to a temp file, closes it, then `os.replace`s it into place (atomic on
   Windows for same-directory replace), retrying on transient sharing
   violations. The reader only ever opens the target path, which the poller
   never holds open — the reader effectively never contends with a live writer.

2. **One `snapshot_timestamp` per cycle (§2.2).** The shared schema defaults
   `snapshot_timestamp` per row, which makes the reader's
   `MAX(snapshot_timestamp)` match a single row. The poller stamps ONE explicit
   timestamp for every row of a cycle; because each cycle is a fresh DB, `MAX`
   equals that cycle's timestamp and every leg is priceable.

Loudness (repo pitfalls): token absent/stale → loud + retry (never interactive);
outside market hours → idle (never spin the API); a fetch failure is a
transient logged event, never a `.404`-style permanent miss marker; a
parse/write failure surfaces (log ERROR), never "market closed"; repeated
consecutive empty cycles during market hours escalate the log level. This
poller never creates or removes a `STOP` file (the runner's kill switch is
CWD-scoped). PID file + clean SIGINT/SIGTERM shutdown.

Freshness hook (§3.5): `data/options/chain_poller_heartbeat.json`
(`{"last_snapshot", "rows", "expiry"}`) is written after each successful swap,
so a future preflight can distinguish "poller alive but market closed / empty
chain" from "poller dead".

New ops/composition-root tooling only — the frozen strategy package is untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.utils.market_hours import MarketHours
from core.logging import setup_logger

logger = setup_logger("chain_poller")

ROOT = Path(__file__).resolve().parents[2]
NF_SYMBOL = "NSE_INDEX|Nifty 50"

DEFAULT_CACHE_DIR = ROOT / "data" / "options"
DEFAULT_CACHE_PATH = DEFAULT_CACHE_DIR / "chain_cache.duckdb"
DEFAULT_TMP_PATH = DEFAULT_CACHE_DIR / "chain_cache.tmp.duckdb"
DEFAULT_HEARTBEAT_PATH = DEFAULT_CACHE_DIR / "chain_poller_heartbeat.json"
DEFAULT_PID_PATH = DEFAULT_CACHE_DIR / "chain_poller.pid"

# Poll cadence (implementation prompt §3.4).
POLL_INTERVAL_S = 5.0
IDLE_INTERVAL_S = 30.0          # outside market hours
TOKEN_RETRY_INTERVAL_S = 30.0
REPLACE_RETRIES = 5
REPLACE_RETRY_DELAY_S = 0.1
ESCALATE_AFTER_CYCLES = 6       # ~30 s of empty/failed cycles at 5 s cadence

# The exact `option_chain_snapshot` schema `OptionsProvider._init_db` creates —
# copied so the reader's SELECT (tradingsymbol, ltp by snapshot_timestamp =
# MAX) works unchanged. snapshot_id is filled by the sequence, snapshot_timestamp
# is stamped explicitly per cycle (§2.2).
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
    PRIMARY KEY (snapshot_id)
)
"""

_INSERT_SQL = """
INSERT INTO option_chain_snapshot (
    snapshot_timestamp, underlying_symbol, expiry_date, strike_price,
    option_type, instrument_key, tradingsymbol, ltp, open, high, low, close,
    oi, oi_change, oi_change_pct, volume, iv, delta, gamma, theta, vega, rho,
    lot_size, underlying_ltp
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _init_snapshot_table(conn) -> None:
    """Mirror OptionsProvider._init_db: sequence + table + indexes."""
    conn.execute("CREATE SEQUENCE IF NOT EXISTS snapshot_id_seq START 1")
    conn.execute(_SNAPSHOT_TABLE_SQL)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_underlying "
                 "ON option_chain_snapshot(underlying_symbol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_expiry "
                 "ON option_chain_snapshot(expiry_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_strike "
                 "ON option_chain_snapshot(strike_price)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_timestamp "
                 "ON option_chain_snapshot(snapshot_timestamp)")


def _token_ok() -> bool:
    from core.auth.credentials import credentials
    return bool(credentials.has_upstox_token and not credentials.is_token_expired)


def _pid_alive(pid: int) -> bool:
    """Windows-safe process liveness check — never os.kill(pid, 0) on Windows
    (CPython maps it to TerminateProcess, which would kill the other process)."""
    if os.name == "nt":
        import ctypes
        if hasattr(ctypes, "windll"):
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _acquire_lock(pid_path: Path) -> bool:
    """Single-instance PID lock; a stale PID file is overwritten, an alive
    instance refuses to start."""
    pid_path = Path(pid_path)
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pid = None
        if pid is not None and _pid_alive(pid):
            logger.error("another ChainPoller instance is already running "
                         "(PID %s); refusing to start", pid)
            return False
        logger.warning("stale chain-poller PID file %s — overwriting", pid_path)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    return True


def _release_lock(pid_path: Path) -> None:
    try:
        if pid_path.exists() and int(pid_path.read_text(encoding="utf-8").strip()) \
                == os.getpid():
            pid_path.unlink()
    except (ValueError, OSError):
        pass


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


class ChainPoller:
    """Long-running writer of `data/options/chain_cache.duckdb`.

    Paths are injectable so tests run against a temp dir; the fetch seam is a
    callable `() -> (rows, expiry)` so tests can stub the chain without network.
    """

    def __init__(
        self,
        *,
        cache_path: str,
        tmp_path: Optional[str] = None,
        heartbeat_path: Optional[str] = None,
        pid_path: Optional[str] = None,
        poll_interval_s: float = POLL_INTERVAL_S,
        idle_interval_s: float = IDLE_INTERVAL_S,
        token_retry_interval_s: float = TOKEN_RETRY_INTERVAL_S,
        replace_retries: int = REPLACE_RETRIES,
        replace_retry_delay_s: float = REPLACE_RETRY_DELAY_S,
        escalate_after_cycles: int = ESCALATE_AFTER_CYCLES,
    ):
        self._cache_path = Path(cache_path)
        self._tmp_path = (Path(tmp_path) if tmp_path
                          else self._cache_path.with_name("chain_cache.tmp.duckdb"))
        self._heartbeat_path = (Path(heartbeat_path) if heartbeat_path
                                else self._cache_path.with_name(
                                    "chain_poller_heartbeat.json"))
        self._pid_path = (Path(pid_path) if pid_path
                          else self._cache_path.with_name("chain_poller.pid"))
        self._poll_interval_s = poll_interval_s
        self._idle_interval_s = idle_interval_s
        self._token_retry_interval_s = token_retry_interval_s
        self._replace_retries = replace_retries
        self._replace_retry_delay_s = replace_retry_delay_s
        self._escalate_after_cycles = escalate_after_cycles
        self._stop = threading.Event()
        self._consecutive_failures = 0

    # ------------------------------------------------------------------ #
    # Public surface
    # ------------------------------------------------------------------ #
    @property
    def cache_path(self) -> Path:
        return self._cache_path

    @property
    def heartbeat_path(self) -> Path:
        return self._heartbeat_path

    def stop(self) -> None:
        self._stop.set()

    def bootstrap(self) -> None:
        """Ensure the target cache exists as a valid (possibly empty) cache.

        An existing readable cache is kept (it may hold the last good snapshot);
        a missing/corrupt target is rebuilt as a fresh empty single-snapshot DB
        so `ChainSnapshotMarksSource.check_available()` passes even before the
        first successful fetch (F3: valid-but-empty -> `{}`, not an error).
        """
        if self._cache_path.exists():
            try:
                import duckdb
                con = duckdb.connect(str(self._cache_path), read_only=True)
                try:
                    con.execute(
                        "SELECT 1 FROM option_chain_snapshot LIMIT 1").fetchall()
                finally:
                    con.close()
                logger.info("existing chain cache valid at %s — keeping it",
                            self._cache_path)
                return
            except Exception:
                logger.error("chain cache %s is unreadable — rebuilding",
                             self._cache_path)
        _remove_if_exists(self._tmp_path)
        con = self._open_fresh_tmp()
        try:
            _init_snapshot_table(con)
            con.commit()
        finally:
            con.close()
        if not self._swap():
            raise RuntimeError(
                f"bootstrap: could not place an initial chain cache at "
                f"{self._cache_path} after {self._replace_retries} attempts")

    def write_cycle(self, rows: List[object], expiry: Optional[str],
                    underlying: str = NF_SYMBOL) -> datetime:
        """Write ONE fresh single-snapshot cache and atomically swap it in.

        `now` is computed once and stamped on every row (§2.2). The write
        connection is closed before the swap (§2.1) and is never held across
        the sleep. Returns the stamped snapshot timestamp.
        """
        now = datetime.now()
        _remove_if_exists(self._tmp_path)
        con = self._open_fresh_tmp()
        try:
            _init_snapshot_table(con)
            for row in rows:
                con.execute(_INSERT_SQL, [
                    now, underlying,
                    row.expiry, row.strike, row.option_type,
                    row.instrument_key, row.tradingsymbol, row.ltp,
                    row.open, row.high, row.low, row.close,
                    row.oi if row.oi else 0,
                    row.oi_change if row.oi_change else 0,
                    row.oi_change_pct if row.oi_change_pct else 0.0,
                    row.volume if row.volume else 0,
                    row.iv, row.delta, row.gamma, row.theta, row.vega, row.rho,
                    row.lot_size, row.underlying_ltp,
                ])
            con.commit()
        finally:
            con.close()
        if not self._swap():
            # N1: a chronically unwritable target escalates like a fetch outage,
            # not just per-cycle ERROR lines. The previous good snapshot stays.
            self._consecutive_failures += 1
            level = logger.error if (self._consecutive_failures
                                     >= self._escalate_after_cycles) \
                else logger.warning
            level("swap into %s failed (%d consecutive) — previous snapshot "
                  "kept; retrying next cycle", self._cache_path,
                  self._consecutive_failures)
            return now
        self._consecutive_failures = 0
        self._write_heartbeat(now, len(rows), expiry)
        return now

    def run(self, fetch: Callable[[], Tuple[List[object], str]],
            *, symbol: str = NF_SYMBOL,
            max_cycles: Optional[int] = None) -> None:
        """Long-running loop: fetch the near-weekly chain and write it.

        Outside market hours the loop idles (never spins the API). A missing or
        expired Upstox token is logged loudly and retried; an empty/failed fetch
        is a transient event (never a permanent miss marker) that escalates the
        log level on repeated consecutive cycles during market hours.
        """
        while not self._stop.is_set():
            if not MarketHours.is_market_open():
                time.sleep(self._idle_interval_s)
                continue
            if not _token_ok():
                logger.error("Upstox token absent or expired — refresh via the "
                             "Dashboard; retrying every %ss",
                             self._token_retry_interval_s)
                time.sleep(self._token_retry_interval_s)
                continue
            try:
                rows, expiry = fetch()
            except Exception as exc:
                self._consecutive_failures += 1
                self._log_failure(exc)
            else:
                if rows:
                    self._consecutive_failures = 0
                    self.write_cycle(rows, expiry, underlying=symbol)
                    logger.info("chain polled: %d rows @ %s", len(rows), expiry)
                else:
                    self._consecutive_failures += 1
                    self._log_empty()
            if max_cycles is not None:
                max_cycles -= 1
                if max_cycles <= 0:
                    break
            time.sleep(self._poll_interval_s)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _open_fresh_tmp(self):
        import duckdb
        self._tmp_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self._tmp_path))

    def _swap(self) -> bool:
        """os.replace(tmp -> cache), retrying on transient sharing violations.

        The target is NEVER deleted on failure — the previous good snapshot
        stays in place (§2.1). Returns True only if the swap landed.
        """
        for attempt in range(self._replace_retries):
            try:
                os.replace(str(self._tmp_path), str(self._cache_path))
                return True
            except (PermissionError, OSError) as exc:
                if attempt == self._replace_retries - 1:
                    logger.error("os.replace %s -> %s failed after %d attempts "
                                 "(%s); keeping the previous snapshot",
                                 self._tmp_path, self._cache_path,
                                 self._replace_retries, exc)
                    return False
                time.sleep(self._replace_retry_delay_s)
        return False

    def _write_heartbeat(self, last_snapshot: datetime, rows: int,
                         expiry: Optional[str]) -> None:
        payload = {
            "last_snapshot": last_snapshot.isoformat(),
            "rows": rows,
            "expiry": expiry,
        }
        tmp = self._heartbeat_path.with_name(self._heartbeat_path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.replace(str(tmp), str(self._heartbeat_path))
        except OSError as exc:
            logger.error("heartbeat write failed: %s", exc)

    def _log_failure(self, exc: Exception) -> None:
        level = logger.error if (self._consecutive_failures
                                 >= self._escalate_after_cycles) else logger.warning
        level("chain fetch raised (%d consecutive): %s",
              self._consecutive_failures, exc)

    def _log_empty(self) -> None:
        level = logger.error if (self._consecutive_failures
                                 >= self._escalate_after_cycles) else logger.warning
        level("%d consecutive empty/failed chain cycles during market hours — "
              "the marks feed may be down", self._consecutive_failures)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NiftyShield option-chain poller (E7-4 marks populator)")
    parser.add_argument("--index", default=NF_SYMBOL,
                        help=f"underlying index (default {NF_SYMBOL})")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR),
                        help="directory for chain_cache.duckdb + heartbeat + PID")
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL_S)
    parser.add_argument("--idle-interval", type=float, default=IDLE_INTERVAL_S)
    parser.add_argument("--token-retry-interval", type=float,
                        default=TOKEN_RETRY_INTERVAL_S)
    parser.add_argument("--max-cycles", type=int, default=None,
                        help="run at most N cycles then exit (testing/preflight)")
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    poller = ChainPoller(
        cache_path=str(cache_dir / "chain_cache.duckdb"),
        tmp_path=str(cache_dir / "chain_cache.tmp.duckdb"),
        heartbeat_path=str(cache_dir / "chain_poller_heartbeat.json"),
        pid_path=str(cache_dir / "chain_poller.pid"),
        poll_interval_s=args.poll_interval,
        idle_interval_s=args.idle_interval,
        token_retry_interval_s=args.token_retry_interval,
    )

    if not _acquire_lock(poller._pid_path):
        return 1

    def _shutdown(sig, frame):
        logger.info("shutdown signal received (%s); stopping poller", sig)
        poller.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        poller.bootstrap()
        from core.data.options_provider import OptionsProvider

        provider = OptionsProvider(read_only=True)   # fetch-only; we own persistence

        def _fetch() -> Tuple[List[object], str]:
            expiry = provider.get_weekly_expiry(args.index)
            rows, _underlying = provider._fetch_from_upstox(args.index, expiry)
            return rows, expiry

        logger.info("chain poller starting: %s -> %s (poll %ss, idle %ss)",
                    args.index, poller.cache_path,
                    args.poll_interval, args.idle_interval)
        poller.run(_fetch, symbol=args.index, max_cycles=args.max_cycles)
    finally:
        _release_lock(poller._pid_path)
    logger.info("chain poller stopped cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
