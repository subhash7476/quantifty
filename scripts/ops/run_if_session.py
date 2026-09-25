"""Scheduled-task entry: run a target script only on an NSE trading session.

Usage (from Windows Task Scheduler, see register_scheduled_tasks.ps1):
  python scripts/ops/run_if_session.py orchestrator
  python scripts/ops/run_if_session.py download [-- extra args for the target]

Non-sessions (weekends, NSE holidays, special closures) are logged and skipped
with exit 0. A date outside trading_calendar coverage exits 2 and alerts: the
next year's holidays must be added before the jobs can run again. The target
runs in this process (runpy), so Ctrl+C reaches the orchestrator's own clean
shutdown and Task Scheduler tracks the real process.
"""
from __future__ import annotations

import runpy
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.trading_calendar import OutsideCoverage, is_session  # noqa: E402

TARGETS = {
    "orchestrator": ROOT / "scripts" / "ops" / "orchestrator.py",
    "download": ROOT / "scripts" / "download_all_data.py",
}
LOG_PATH = ROOT / "data" / "ops" / "scheduled_runs.log"


def _log(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")


def _run_target(script: Path, args: List[str]) -> int:
    sys.argv = [str(script), *args]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


def _telegram(text: str) -> None:
    from dotenv import load_dotenv
    from core.scheduler.eod_telegram import send_sync
    load_dotenv(ROOT / ".env")
    send_sync(text)


def main(argv: Optional[List[str]] = None, today: Optional[date] = None,
         runner: Callable[[Path, List[str]], int] = _run_target,
         alert: Callable[[str], None] = _telegram,
         log_path: Path = LOG_PATH) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in TARGETS:
        print(f"usage: run_if_session.py {{{'|'.join(TARGETS)}}} [-- args]")
        return 64
    target, extra = argv[0], argv[1:]
    if extra[:1] == ["--"]:
        extra = extra[1:]
    today = today or date.today()

    try:
        session = is_session(today)
    except OutsideCoverage as e:
        msg = (f"SCHEDULED {target} NOT RUN — {e}. Add the new year's dates to "
               f"core/market/nse_holidays.py and trading_calendar.py.")
        _log(log_path, f"ERROR {target} {today}: {e}")
        alert(msg)
        return 2
    if not session:
        _log(log_path, f"SKIP {target} {today}: not a trading session")
        return 0

    _log(log_path, f"START {target} {today} args={extra}")
    rc = runner(TARGETS[target], extra)
    _log(log_path, f"END {target} {today} exit {rc}")
    if rc != 0:
        alert(f"SCHEDULED {target} {today} finished with exit {rc} — see {log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
