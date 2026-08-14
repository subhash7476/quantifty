"""Options-Wall chain poller — the sole writer of `wall_chain_snapshots.duckdb`.

Accumulates Nifty + BankNifty near-weekly chains every poll cycle during market
hours. Append-only: each cycle appends one fresh snapshot per underlying via
`options_wall_store.append_snapshot` — nothing is overwritten, so the scan trail
and regime river keep their history.

Single-writer discipline (review LOW-3): this process is the ONLY writer to the
snapshot store. The scan engine reads it; it does not append. A PID lock prevents
a second instance from opening the same file read-write.

Loudness mirrors the repo pitfalls: token absent/stale → loud + retry; outside
market hours → idle; a fetch failure is a transient log event, never a permanent
miss marker. PID file + heartbeat + clean SIGINT/SIGTERM.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.data import options_wall_store as store
from core.data.options_provider import OptionsProvider
from core.database.utils.market_hours import MarketHours
from core.logging import setup_logger

logger = setup_logger("options_wall_poller")

ROOT = Path(__file__).resolve().parents[2]
UNDERLYINGS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

POLL_INTERVAL_S = 5.0
IDLE_INTERVAL_S = 30.0
TOKEN_RETRY_INTERVAL_S = 30.0


def _token_ok() -> bool:
    from core.auth.credentials import credentials
    return bool(credentials.has_upstox_token and not credentials.is_token_expired)


def _pid_alive(pid: int) -> bool:
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


class WallPoller:
    """Long-running, accumulating writer of `wall_chain_snapshots.duckdb`."""

    def __init__(self, *, heartbeat_path: Path, pid_path: Path,
                 snapshot_db_path: Path = store.WALL_SNAPSHOT_DB,
                 poll_interval_s: float = POLL_INTERVAL_S,
                 idle_interval_s: float = IDLE_INTERVAL_S,
                 token_retry_interval_s: float = TOKEN_RETRY_INTERVAL_S):
        self._heartbeat_path = Path(heartbeat_path)
        self._pid_path = Path(pid_path)
        self._snapshot_db_path = Path(snapshot_db_path)
        self._poll_interval_s = poll_interval_s
        self._idle_interval_s = idle_interval_s
        self._token_retry_interval_s = token_retry_interval_s
        self._stop = False

    def _acquire_lock(self) -> bool:
        if self._pid_path.exists():
            try:
                pid = int(self._pid_path.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pid = None
            if pid is not None and _pid_alive(pid):
                logger.error("another WallPoller is already running (PID %s); "
                             "refusing to start", pid)
                return False
        self._pid_path.parent.mkdir(parents=True, exist_ok=True)
        self._pid_path.write_text(str(os.getpid()), encoding="utf-8")
        return True

    def _release_lock(self) -> None:
        try:
            if self._pid_path.exists() and \
                    int(self._pid_path.read_text(encoding="utf-8").strip()) == os.getpid():
                self._pid_path.unlink()
        except (ValueError, OSError):
            pass

    def _write_heartbeat(self, rows_by_name: dict) -> None:
        payload = {
            "last_snapshot": datetime.now().isoformat(),
            "rows": rows_by_name,
        }
        tmp = self._heartbeat_path.with_name(self._heartbeat_path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.replace(str(tmp), str(self._heartbeat_path))
        except OSError as exc:
            logger.error("heartbeat write failed: %s", exc)

    def stop(self) -> None:
        self._stop = True

    def _poll_cycle(self, provider) -> dict:
        """Fetch both chains, append to the store, write heartbeat.

        Returns {name: rows_written} (or -1 on fetch error, 0 on empty).
        """
        rows_by_name = {}
        for name, sym in UNDERLYINGS.items():
            try:
                expiry = provider.get_weekly_expiry(sym)
                rows = provider.fetch_option_chain(sym, expiry)
                if rows:
                    store.append_snapshot(rows, sym, expiry, db_path=self._snapshot_db_path)
                    rows_by_name[name] = len(rows)
                    logger.info("%s: appended %d rows @ %s", name, len(rows), expiry)
                else:
                    rows_by_name[name] = 0
                    logger.warning("%s: empty chain @ %s", name, expiry)
            except Exception as exc:
                rows_by_name[name] = -1
                logger.warning("%s fetch failed: %s", name, exc)
        self._write_heartbeat(rows_by_name)
        return rows_by_name

    def run(self, provider=None, max_cycles: int | None = None) -> None:
        provider = provider or OptionsProvider(read_only=True)
        while not self._stop:
            if not MarketHours.is_market_open():
                time.sleep(self._idle_interval_s)
                continue
            if not _token_ok():
                logger.error("Upstox token absent or expired — refresh via the "
                             "Dashboard; retrying every %ss",
                             self._token_retry_interval_s)
                time.sleep(self._token_retry_interval_s)
                continue

            self._poll_cycle(provider)

            if max_cycles is not None:
                max_cycles -= 1
                if max_cycles <= 0:
                    break
            time.sleep(self._poll_interval_s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Options-Wall chain poller")
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL_S)
    parser.add_argument("--idle-interval", type=float, default=IDLE_INTERVAL_S)
    parser.add_argument("--token-retry-interval", type=float, default=TOKEN_RETRY_INTERVAL_S)
    parser.add_argument("--max-cycles", type=int, default=None,
                        help="run at most N cycles then exit (testing/preflight)")
    args = parser.parse_args()

    state_dir = ROOT / "data" / "options"
    state_dir.mkdir(parents=True, exist_ok=True)
    poller = WallPoller(
        heartbeat_path=state_dir / "wall_poller_heartbeat.json",
        pid_path=state_dir / "wall_poller.pid",
        poll_interval_s=args.poll_interval,
        idle_interval_s=args.idle_interval,
        token_retry_interval_s=args.token_retry_interval,
    )

    if not poller._acquire_lock():
        return 1

    def _shutdown(sig, frame):
        logger.info("shutdown signal received (%s); stopping poller", sig)
        poller.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        poller.run(max_cycles=args.max_cycles)
    finally:
        poller._release_lock()
    logger.info("wall poller stopped cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
