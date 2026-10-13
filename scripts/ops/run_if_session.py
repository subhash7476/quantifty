"""Scheduled-task entry: run a target script only on an NSE trading session.

Usage (from Windows Task Scheduler, see register_scheduled_tasks.ps1):
  python scripts/ops/run_if_session.py orchestrator
  python scripts/ops/run_if_session.py download [-- extra args for the target]
  python scripts/ops/run_if_session.py straddle_capture

Non-sessions (weekends, NSE holidays, special closures) are logged and skipped
with exit 0. A date outside trading_calendar coverage exits 2 and alerts: the
next year's holidays must be added before the jobs can run again. The target
runs in this process (runpy), so Ctrl+C reaches the orchestrator's own clean
shutdown and Task Scheduler tracks the real process.

Each run's stdout/stderr is also teed into
`data/ops/logs/<target>_<date>.log` (the START line names it), so a non-zero
exit leaves its traceback on disk. Scheduler-level outcomes stay in
`scheduled_runs.log`.
"""
from __future__ import annotations

import runpy
import sys
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.market.trading_calendar import OutsideCoverage, is_session  # noqa: E402

TARGETS = {
    "orchestrator": ROOT / "scripts" / "ops" / "orchestrator.py",
    "download": ROOT / "scripts" / "download_all_data.py",
    "straddle_capture": ROOT / "scripts" / "research" / "options_seller_edge" / "straddle_cycle_capture.py",
}
LOG_PATH = ROOT / "data" / "ops" / "scheduled_runs.log"


def _log(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")


class _Tee:
    """Mirrors a text stream into the run log, flushing every write.

    The console copy is best-effort: Task Scheduler may give the process no
    console at all, and a console error must never cost the log line.
    """

    def __init__(self, stream, sink) -> None:
        self._stream = stream
        self._sink = sink

    def write(self, text: str) -> int:
        if not self._sink.closed:    # logging handlers outlive the run
            self._sink.write(text)
            self._sink.flush()
        if self._stream is not None:
            try:
                self._stream.write(text)
            except (OSError, ValueError):
                pass
        return len(text)

    def flush(self) -> None:
        if self._stream is not None:
            try:
                self._stream.flush()
            except (OSError, ValueError):
                pass

    def __getattr__(self, name: str):     # encoding, isatty, fileno, ...
        return getattr(self._stream, name)


def _run_logged(runner: Callable[[Path, List[str]], int], script: Path,
                args: List[str], run_log: Path) -> int:
    """Run the target with its stdout/stderr teed into `run_log`.

    Python-level only: children the target spawns inherit the process handles
    and keep writing to their own logs, not into this file.
    """
    run_log.parent.mkdir(parents=True, exist_ok=True)
    with run_log.open("a", encoding="utf-8", errors="replace") as sink:
        sink.write(f"--- {datetime.now().isoformat(timespec='seconds')} "
                   f"{script.name} {args}\n")
        out, err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = _Tee(out, sink), _Tee(err, sink)
        try:
            return runner(script, args)
        finally:
            sys.stdout, sys.stderr = out, err


def _run_target(script: Path, args: List[str]) -> int:
    sys.argv = [str(script), *args]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:  # noqa: BLE001 — so the END line and the alert still fire
        traceback.print_exc()
        return 1
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

    run_log = log_path.parent / "logs" / f"{target}_{today.isoformat()}.log"
    _log(log_path, f"START {target} {today} args={extra} log={run_log}")
    rc = _run_logged(runner, TARGETS[target], extra, run_log)
    _log(log_path, f"END {target} {today} exit {rc}")
    if rc != 0:
        alert(f"SCHEDULED {target} {today} finished with exit {rc} — "
              f"see {log_path} and {run_log}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
