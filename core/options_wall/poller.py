"""Options-Wall chain poller — the sole writer of BOTH results stores.

Accumulates Nifty + BankNifty + Sensex near-weekly chains every poll cycle during
market hours. Append-only: each cycle appends one fresh snapshot per underlying via
`options_wall_store.append_snapshot` — nothing is overwritten, so the scan trail
and regime river keep their history.

Single-writer discipline: this process is the ONLY writer to both
`wall_chain_snapshots.duckdb` (raw chains) and `wall_scan_results.duckdb`
(scan_results / session_regime / oi_baseline / trades). Each cycle it appends the
snapshot, runs the paper executor, and — throttled to SCAN_PERSIST_INTERVAL_S —
scans + persists scan_results + session_regime. Flask only ever reads these files.
A PID lock prevents a second instance from opening the snapshot file read-write.

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
from datetime import date, datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb

from core.data import options_wall_store as store
from core.data import options_provider
from core.data.options_provider import OptionsProvider
from core.options_wall import persistence
from core.options_wall.engine import UNDERLYINGS
from core.options_wall.health import StepHealth
from core.brokers.upstox_market_data import UpstoxMarketData
from core.database.utils.market_hours import MarketHours
from core.logging import setup_logger

logger = setup_logger("options_wall_poller")

ROOT = Path(__file__).resolve().parents[2]
# UNDERLYINGS is imported from the engine so the poller (the results DB's sole
# writer) and Flask's read path (_sym) can never disagree on what to persist.

POLL_INTERVAL_S = 5.0
IDLE_INTERVAL_S = 30.0
TOKEN_RETRY_INTERVAL_S = 30.0
SCAN_PERSIST_INTERVAL_S = 30.0   # throttle scan_results/regime writes below the 5s cycle
# Term-structure capture (research-library plan W3): Nifty's next expiries go to
# the store's FAR_TABLE once a minute - the slope moves slowly and each far chain
# is another append holding the file lock.
FAR_UNDERLYINGS = ("NIFTY",)
FAR_PERSIST_INTERVAL_S = 60.0
FAR_MIN_DTE = 2          # a leg at <= 1 DTE says little about the term structure


def _today() -> date:
    return date.today()


def _listed_expiries(index_name: str) -> list:
    """Live expiries for `index_name` from the instrument master.

    Raises rather than calculating: `OptionsProvider.get_expiry_list` falls back
    to every-7-days dates, which miss holiday-shifted expiries (it gives
    2026-11-24 for the 2026-11-23 monthly) and so would pick the wrong monthly.
    """
    path = options_provider.INSTRUMENT_DB_PATH
    if not path.exists():
        raise FileNotFoundError(f"instrument master missing: {path}")
    conn = duckdb.connect(str(path), read_only=True)
    try:
        rows = conn.execute("""
            SELECT DISTINCT expiry FROM instruments
            WHERE name = ? AND instrument_type = 'CE' AND expiry >= ?
              AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
            ORDER BY expiry""", [index_name, _today().isoformat()]).fetchall()
    finally:
        conn.close()
    if not rows:
        raise RuntimeError(f"no live {index_name} expiries in the instrument master")
    return [r[0] for r in rows]


def far_expiries(expiries, today: date, nearest: str) -> list:
    """Expiries beyond `nearest` that a term-structure slope needs.

    The first expiry at >= FAR_MIN_DTE calendar days, and the first monthly after
    it (a month's last listed expiry; monthlies are listed months ahead, so the
    last one listed in a month is that month's monthly). `nearest` is dropped -
    the main table already holds it.
    """
    live = sorted({str(e)[:10] for e in expiries if str(e)[:10] >= today.isoformat()})
    front = next((e for e in live if (date.fromisoformat(e) - today).days >= FAR_MIN_DTE), None)
    if front is None:
        return []
    month_last = {}
    for e in live:
        month_last[e[:7]] = e
    monthly = next((e for e in sorted(month_last.values()) if e > front), None)
    return [e for e in (front, monthly) if e and e != nearest]


def _token_ok() -> bool:
    from core.auth.credentials import credentials
    return bool(credentials.has_upstox_token and not credentials.is_token_expired)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        if hasattr(ctypes, "windll"):
            # OpenProcess succeeds on an exited process whose object lingers
            # while any handle to it is held, so it read a dead poller as alive:
            # the orchestrator (pidfile.pid_alive, exit-code based) respawned it
            # and every respawn refused to start (2026-09-11). Same test as the
            # orchestrator, or the two disagree.
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = wintypes.DWORD()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(ok) and exit_code.value == STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


class WallPoller:
    """Long-running, accumulating writer of `wall_chain_snapshots.duckdb`."""

    def __init__(self, *, heartbeat_path: Path, pid_path: Path,
                 snapshot_db_path: Optional[Path] = None,
                 results_db_path: Path = persistence.WALL_RESULTS_DB,
                 poll_interval_s: float = POLL_INTERVAL_S,
                 idle_interval_s: float = IDLE_INTERVAL_S,
                 token_retry_interval_s: float = TOKEN_RETRY_INTERVAL_S,
                 scan_persist_interval_s: float = SCAN_PERSIST_INTERVAL_S,
                 far_underlyings: tuple = (),
                 far_persist_interval_s: float = FAR_PERSIST_INTERVAL_S):
        self._heartbeat_path = Path(heartbeat_path)
        self._pid_path = Path(pid_path)
        # None → the store writes to the per-day file for each cycle's date; an
        # explicit path (tests) pins a single file.
        self._snapshot_db_path = Path(snapshot_db_path) if snapshot_db_path else None
        self._results_db_path = Path(results_db_path)
        self._baseline_done: set = set()   # (sym, trade_date) captured this process
        self._scan_last: dict = {}         # sym → monotonic ts of last scan/regime write
        self._poll_interval_s = poll_interval_s
        self._idle_interval_s = idle_interval_s
        self._token_retry_interval_s = token_retry_interval_s
        self._scan_persist_interval_s = scan_persist_interval_s
        self._far_underlyings = tuple(far_underlyings)
        self._far_persist_interval_s = far_persist_interval_s
        self._far_last: dict = {}          # name → monotonic ts of last far capture
        self._stop = False
        self._health = StepHealth()

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
            "status": "DEGRADED" if self._health.any_failing() else "OK",
            "steps": self._health.snapshot(),
        }
        tmp = self._heartbeat_path.with_name(self._heartbeat_path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.replace(str(tmp), str(self._heartbeat_path))
        except OSError as exc:
            logger.error("heartbeat write failed: %s", exc)

    def _record_step(self, step: str, underlying: str, exc=None) -> None:
        # Health reporting must never take the poller down. A defect in here at
        # the fetch site would otherwise escape _poll_cycle, so the module built
        # to surface failures would be the one that stops the cycle.
        try:
            verdict = self._health.record(step, underlying, exc)
            if exc is not None:
                log = logger.error if verdict.level == "error" else logger.warning
                log("%s %s step failed (%s): %s", underlying, step, verdict.kind, exc)
            if verdict.alert:
                self._alert(step, underlying, verdict)
        except Exception as health_exc:
            logger.error("step health recording failed for %s %s: %s",
                         underlying, step, health_exc)

    def _alert(self, step: str, underlying: str, verdict) -> None:
        record = verdict.record
        text = (f"[options-wall] {underlying} {step} failing\n"
                f"{record['error_type']}: {(record['error_msg'].splitlines() or [''])[0]}\n"
                f"since {record['since']} ({record['consecutive']} cycles)")
        try:
            from core.alerts.telegram_notifier import TelegramNotifier
            TelegramNotifier().send_message(text)
        except Exception as exc:
            logger.error("health alert delivery failed: %s", exc)

    def _analytics_for(self, sym, rows, expiry):
        """Structural snapshot + realized vol, built once per underlying so the
        executor and the scan-persist step share one build (no double compute)."""
        from core.analytics.options_analytics import OptionsAnalytics
        from core.analytics.realized_vol import session_realized_vol_pct
        from core.options_wall.engine import DEALER_SIDE
        if not hasattr(self, "_analytics"):
            self._analytics = OptionsAnalytics()
        spot = rows[0].underlying_ltp or 0.0
        structural = self._analytics.build_structural_snapshot(
            rows, sym, spot, expiry, dealer_side=DEALER_SIDE)
        rv = session_realized_vol_pct(sym)
        return structural, rv

    def _executor_step(self, name, sym, rows, structural, rv):
        from core.options_wall.paper_executor import PaperExecutor
        if not hasattr(self, "_executor"):
            self._executor = PaperExecutor(db_path=self._results_db_path)
        action = self._executor.step(sym, rows, structural, rv, datetime.now())
        if action:
            logger.info("%s paper action: %s", name, action)

    def _scan_persist_step(self, name, sym, rows, structural, rv, quotes):
        """Persist scan_results + session_regime for this cycle (the poller is the
        results DB's sole writer). Throttled per underlying to
        `scan_persist_interval_s` so the 5s executor cadence never bloats the
        scan/regime tables; the executor still runs every cycle."""
        now = time.monotonic()
        if now - self._scan_last.get(sym, float("-inf")) < self._scan_persist_interval_s:
            return
        from core.options_wall.engine import persist_scan_and_regime
        n = persist_scan_and_regime(sym, rows, quotes, structural, rv,
                                    db_path=self._results_db_path)
        self._scan_last[sym] = now
        logger.info("%s: persisted %d scan_results + regime", name, n)

    def _process_close_requests(self, name, sym, rows, now) -> None:
        """Consume operator close requests for this underlying (Flask → poller).

        Flask queues a request file per trade; the poller (sole writer of the
        results DB) force-closes matching open trades at this cycle's marks.
        Stale requests (trade already closed / unknown) are cleared; a request
        for an open trade whose legs are unquoted this cycle is left for retry.
        """
        from core.options_wall import commands
        reqs = [r for r in commands.pending_closes() if r.get("index") == name]
        if not reqs:
            return
        if not hasattr(self, "_executor"):
            from core.options_wall.paper_executor import PaperExecutor
            self._executor = PaperExecutor(db_path=self._results_db_path)
        open_ids = {t["trade_id"] for t in
                    persistence.open_trades(sym, db_path=self._results_db_path)}
        for req in reqs:
            tid = req.get("trade_id")
            if tid not in open_ids:
                commands.clear_close(tid)
                continue
            if self._executor.manual_close(sym, tid, rows, now):
                commands.clear_close(tid)
                logger.info("%s manual close: trade %s", name, tid)
            else:
                logger.warning("%s manual close deferred (unquoted): trade %s",
                               name, tid)

    def _capture_baseline(self, sym, rows) -> None:
        """Session-open OI per strike: the first cycle of the day writes it
        (INSERT OR IGNORE keeps the earliest); later cycles skip the write."""
        key = (sym, datetime.now().date())
        if key in self._baseline_done:
            return
        persistence.capture_oi_baseline(rows, sym, key[1], db_path=self._results_db_path)
        self._baseline_done.add(key)

    def stop(self) -> None:
        self._stop = True

    def _far_step(self, provider, market_data, name, sym, nearest) -> Optional[int]:
        """Append this underlying's next-expiry chains to FAR_TABLE (throttled).

        Returns rows written, or None when throttled. Never touches the main table."""
        now = time.monotonic()
        if now - self._far_last.get(name, float("-inf")) < self._far_persist_interval_s:
            return None
        self._far_last[name] = now
        written = 0
        for expiry in far_expiries(_listed_expiries(name), _today(), nearest):
            rows = provider.fetch_option_chain(sym, expiry)
            if not rows:
                continue
            keys = [r.instrument_key for r in rows if r.instrument_key]
            quotes = market_data.fetch_quotes_batch(keys).get("quotes", {}) if keys else {}
            store.append_snapshot(rows, sym, expiry, db_path=self._snapshot_db_path,
                                  quotes=quotes, table=store.FAR_TABLE)
            written += len(rows)
        return written

    def _poll_cycle(self, provider) -> dict:
        """Fetch both chains, append to the store, write heartbeat.

        Returns {name: rows_written} (or -1 on fetch error, 0 on empty).
        """
        rows_by_name = {}
        market_data = UpstoxMarketData()
        for name, sym in UNDERLYINGS.items():
            try:
                expiry = provider.get_weekly_expiry(sym)
                rows = provider.fetch_option_chain(sym, expiry)
                if rows:
                    keys = [r.instrument_key for r in rows if r.instrument_key]
                    quotes = {}
                    if keys:
                        qresp = market_data.fetch_quotes_batch(keys)
                        quotes = qresp.get("quotes", {})
                        if qresp.get("error"):
                            self._record_step("quotes", name,
                                              RuntimeError(qresp["error"]))
                        else:
                            self._record_step("quotes", name)
                    # attach bid/ask to the in-memory rows so the executor's spread
                    # cap and no-quote-no-trade rule (spec §3.4) apply on the live path
                    for r in rows:
                        q = quotes.get(r.instrument_key) if r.instrument_key else None
                        r.best_bid = q.get("best_bid") if q else None
                        r.best_ask = q.get("best_ask") if q else None
                    store.append_snapshot(rows, sym, expiry,
                                          db_path=self._snapshot_db_path, quotes=quotes)
                    rows_by_name[name] = len(rows)
                    self._record_step("fetch", name)
                    logger.info("%s: appended %d rows (%d quoted) @ %s",
                                name, len(rows), len(quotes), expiry)
                    self._capture_baseline(sym, rows)
                    try:
                        structural, rv = self._analytics_for(sym, rows, expiry)
                    except Exception as exc:
                        self._record_step("analytics", name, exc)
                    else:
                        self._record_step("analytics", name)
                        try:
                            self._executor_step(name, sym, rows, structural, rv)
                        except Exception as exc:
                            self._record_step("executor", name, exc)
                        else:
                            self._record_step("executor", name)
                        try:
                            self._scan_persist_step(name, sym, rows,
                                                    structural, rv, quotes)
                        except Exception as exc:
                            self._record_step("scan_persist", name, exc)
                        else:
                            self._record_step("scan_persist", name)
                    try:
                        self._process_close_requests(name, sym, rows, datetime.now())
                    except Exception as exc:
                        self._record_step("close_request", name, exc)
                    else:
                        self._record_step("close_request", name)
                else:
                    rows_by_name[name] = 0
                    logger.warning("%s: empty chain @ %s", name, expiry)
            except Exception as exc:
                rows_by_name[name] = -1
                self._record_step("fetch", name, exc)
            if name in self._far_underlyings and rows_by_name.get(name, -1) > 0:
                try:
                    far = self._far_step(provider, market_data, name, sym, expiry)
                except Exception as exc:
                    rows_by_name[f"{name}:far"] = -1
                    self._record_step("far_fetch", name, exc)
                else:
                    if far is not None:
                        rows_by_name[f"{name}:far"] = far
                        self._record_step("far_fetch", name)
        self._write_heartbeat(rows_by_name)
        return rows_by_name

    def run(self, provider=None, max_cycles: int | None = None) -> None:
        provider = provider or OptionsProvider(read_only=True)
        while not self._stop:
            if not MarketHours.is_derivatives_open():
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
        far_underlyings=FAR_UNDERLYINGS,
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
