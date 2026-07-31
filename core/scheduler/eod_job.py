"""One EOD attempt: download -> probe -> decide -> act -> record.

Dependencies are injected via Deps so the whole decision path is testable
without subprocesses, DuckDB stores, or network calls.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from core.scheduler import eod_telegram as tg
from core.scheduler.eod_chain import StepResult, run_chain, run_step
from core.scheduler.eod_decision import decide, probe_feeds
from core.scheduler.eod_store import EodStore

ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_SCRIPT = ROOT / "scripts" / "download_all_data.py"


def run_download(timeout: int = 3600) -> StepResult:
    return run_step("download_all_data.py", DOWNLOAD_SCRIPT, timeout=timeout)


def _default_book():
    sys.path.insert(0, str(ROOT / "scripts"))
    from ts_basis_daily_options import get_book
    from core.analytics.options_selection import DEFAULT_MIN_DTE, select_book_options
    target, book = get_book(None, 5)
    return target, select_book_options(book, min_dte=DEFAULT_MIN_DTE)


@dataclass
class Deps:
    download: Callable[[], StepResult] = run_download
    probe: Callable[[], dict] = probe_feeds
    chain: Callable[[], list] = run_chain
    send: Callable[[str], bool] = tg.send_sync
    book: Callable[[], tuple] = _default_book


def run_attempt(store: EodStore, run_date: date, attempt: int,
                now: datetime, deps: Deps | None = None) -> str:
    deps = deps or Deps()

    deps.download()  # exit code is not authoritative — the feed probe is
    feeds = deps.probe()
    decision = decide(feeds, run_date, now, attempt)

    if decision.action in ("holiday", "exhausted"):
        deps.send(tg.format_stopped(decision.action, decision.reason, attempt))
        store.record(run_date, attempt, "download", decision.action, decision.reason)
        return decision.action

    if decision.action == "retry":
        store.record(run_date, attempt, "download", "retry", decision.reason)
        return "retry"

    # decision.action == "chain"
    deps.send(tg.format_download_success(feeds, run_date, attempt))

    results = deps.chain()
    failed = next((r for r in results if not r.ok), None)
    if failed:
        deps.send(tg.format_chain_failure(failed.label, failed.stderr_tail))
        store.record(run_date, attempt, "chain", "chain_failed",
                     f"{failed.label}: {failed.stderr_tail[:300]}")
        return "chain_failed"

    target, contracts = deps.book()
    deps.send(tg.format_options_book(target, contracts))
    store.record(run_date, attempt, "done", "success", f"{len(results)} chain steps ok")
    return "success"
