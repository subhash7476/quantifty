"""EOD automation worker.

Standalone daemon. Flask must NOT run this in-process: it runs with
debug=True, so the Werkzeug reloader forks two processes and the job would
fire twice.

Usage:
  python scripts/schedule_worker.py
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from core.scheduler.eod_decision import MAX_ATTEMPTS  # noqa: E402
from core.scheduler.eod_job import run_attempt  # noqa: E402
from core.scheduler.eod_store import EodStore  # noqa: E402

STORE_PATH = ROOT / "data" / "_eod_automation.sqlite"
LOCK_PATH = ROOT / "data" / "_eod_worker.lock"

FIRE_HOUR = 20
STOP_HOUR = 23
STOP_MINUTE = 30
RETRY_MINUTES = 30
TICK_SECONDS = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger("eod_worker")


def is_due(now: datetime, last_finished: datetime | None, attempts: int) -> bool:
    if now.weekday() > 4:  # Mon=0 .. Fri=4
        return False
    if attempts >= MAX_ATTEMPTS:
        return False
    if now.hour < FIRE_HOUR:
        return False
    if (now.hour, now.minute) > (STOP_HOUR, STOP_MINUTE):
        return False
    if last_finished is None:
        return True
    return now >= last_finished + timedelta(minutes=RETRY_MINUTES)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        exit_code = wintypes.DWORD()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and exit_code.value == STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except Exception:
        return True
    return True


def acquire_lock(lock_path: Path) -> bool:
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
        except (ValueError, OSError):
            pid = None
        if pid and _pid_alive(pid):
            return False
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))
    return True


def main() -> int:
    if not acquire_lock(LOCK_PATH):
        logger.error(f"Another worker is already running (see {LOCK_PATH}). Exiting.")
        return 1

    store = EodStore(STORE_PATH)
    offset = datetime.now().astimezone().utcoffset()
    logger.info(f"EOD worker started (pid {os.getpid()}), local UTC offset {offset}")
    logger.info(f"Fire window {FIRE_HOUR}:00-{STOP_HOUR}:{STOP_MINUTE:02d} Mon-Fri, "
                f"retry {RETRY_MINUTES}min, max {MAX_ATTEMPTS} attempts")

    while True:
        try:
            store.heartbeat(os.getpid())
            now = datetime.now()
            today = now.date()

            if store.consume_run_now():
                logger.info("Manual run requested — running one attempt (attempt=0)")
                store.set_busy("manual run")
                try:
                    outcome = run_attempt(store, today, 0, now)
                finally:
                    store.set_busy(None)
                logger.info(f"Manual run outcome: {outcome}")

            elif store.is_enabled() and not store.is_date_terminal(today):
                attempts = store.attempts_today(today)
                if is_due(now, store.last_attempt_finished(today), len(attempts)):
                    n = len(attempts) + 1
                    logger.info(f"Attempt {n} for {today}")
                    store.set_busy(f"attempt {n}")
                    try:
                        outcome = run_attempt(store, today, n, now)
                    finally:
                        store.set_busy(None)
                    logger.info(f"Attempt {n} outcome: {outcome}")
        except Exception as e:
            logger.exception(f"Worker tick failed: {e}")

        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
