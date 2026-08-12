"""NiftyShield — Stage-2 PAPER per-session ops runner (E007 Phase B).

The daily Phase B operation. Composes the LIVE composition root (frozen
identity) with the Phase B recorder + heartbeat watchdog, runs the session,
then finalizes the session evidence on shutdown:

- telemetry snapshot + archive (evidence item 5),
- cumulative journal audit (item 3; the load-bearing F4 1-structure/session
  verification MUST run every session),
- risk-metrics snapshot (item 4),
- recorder.finalize -> the session package (replay-evidence input, item G).

Everything lands under an isolated `--data-root` (default `data/nifty_shield`)
so the window's evidence is self-contained and replayable:

    {root}/journal.jsonl            accumulated runtime journal
    {root}/trading/trading.db       accumulated PAPER trade ledger
    {root}/metrics.json             execution metrics
    {root}/heartbeat.json           watchdog heartbeat (live only)
    {root}/facts.duckdb             live 13:00 fact store
    {root}/sessions/{YYYY-MM-DD}/   per-session package (audit/telemetry/
                                    replay inputs, meta)

Exit code is non-zero when a session's evidence violates a stage rule
(guard event fired, reverse divergence, telemetry violation) — the daily op
must fail loudly, never pass a broken session quietly.

Usage:
    python scripts/nifty_shield_paper/session.py --date 2026-08-11
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import signal
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.manager import DatabaseManager
from core.database.utils.market_hours import MarketHours
from core.runtime.config import Mode
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink

from scripts.nifty_shield_paper.audit import audit_window
from scripts.nifty_shield_paper.metrics_report import risk_metrics_report
from scripts.nifty_shield_paper.recorder import SessionRecorder, _commit_ref
from scripts.nifty_shield_paper.telemetry_archive import archive_session
from scripts.nifty_shield_paper_runner import (
    _load_span_snapshot, build_nifty_shield_paper_driver,
)

_logger = logging.getLogger("nifty_shield_session")

CHAIN_DB = Path(__file__).resolve().parents[2] / "data" / "options" / "chain_cache.duckdb"
PER_DAY_STORE = (Path(__file__).resolve().parents[2] / "data" / "market_data"
                 / "nse" / "candles" / "1m")
LIVE_BUFFER = (Path(__file__).resolve().parents[2] / "data" / "live_buffer"
               / "candles_today.duckdb")


def _as_dict(obj: Any) -> Dict[str, Any]:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = dataclasses.asdict(obj)
        d.pop("guard_events", None)
        return d
    return dict(obj)


def finalize_session_evidence(
    *,
    session_date: date,
    data_root: Path,
    telemetry: InMemoryTelemetrySink,
    driver: Any,
    recorder: Optional[SessionRecorder],
    facts_db_path: Path,
    initial_capital: float = 1_000_000.0,
    span_snapshot: Optional[object] = None,
) -> Dict[str, Any]:
    """Run the per-session evidence capture; write it into the session package.

    Shared by the LIVE daily op (`session.py`) and the REPLAY harness
    (`replay.py`). Returns the session summary dict.
    """
    pkg = data_root / "sessions" / session_date.isoformat()
    pkg.mkdir(parents=True, exist_ok=True)
    journal_path = data_root / "journal.jsonl"
    trades_path = data_root / "trading" / "trading.db"
    metrics_path = data_root / "metrics.json"
    heartbeat_path = data_root / "heartbeat.json"

    raw_snapshot = telemetry.snapshot()
    snapshot = {k.value if hasattr(k, "value") else k: v
                for k, v in raw_snapshot.items()}
    telemetry_arch = archive_session(
        session_date.isoformat(), raw_snapshot,
        heartbeat_path=str(heartbeat_path) if heartbeat_path.exists() else None)
    (pkg / "telemetry.json").write_text(
        json.dumps({
            "session": session_date.isoformat(),
            "snapshot": snapshot,
            "clean": telemetry_arch.clean,
            "violations": telemetry_arch.violations,
        }, indent=2), encoding="utf-8")

    audit = audit_window(str(journal_path), str(trades_path))
    audit_json = {
        "structures": [_as_dict(a) for a in audit.structures],
        "guard_events": dict(audit.guard_events),
        "skipped_sessions": audit.skipped_sessions,
        "reverse_divergence": audit.reverse_divergence,
        "one_directional_only": audit.one_directional_only,
    }
    (pkg / "audit.json").write_text(
        json.dumps(audit_json, indent=2, default=str), encoding="utf-8")

    metrics = risk_metrics_report(
        str(journal_path), str(trades_path),
        initial_capital=initial_capital,
        metrics_json=str(metrics_path) if metrics_path.exists() else None)
    (pkg / "metrics.json").write_text(
        json.dumps(dataclasses.asdict(metrics), indent=2, default=str),
        encoding="utf-8")

    summary = {
        "session_date": session_date.isoformat(),
        "bars_processed": getattr(driver, "bars_processed", None),
        "signals_pulled": getattr(driver, "signals_pulled", None),
        "telemetry_clean": telemetry_arch.clean,
        "telemetry_violations": telemetry_arch.violations,
        "audit_guard_events": dict(audit.guard_events),
        "audit_reverse_divergence": audit.reverse_divergence,
        "audit_one_directional_only": audit.one_directional_only,
        "audit_structures": len(audit.structures),
        "metrics_round_trips": metrics.round_trips,
        "metrics_entered": metrics.structures_entered,
        "metrics_skipped": metrics.structures_skipped,
    }
    if recorder is not None:
        recorder_meta = recorder.finalize(
            facts_db_path=str(facts_db_path),
            per_day_store=str(PER_DAY_STORE / f"{session_date.isoformat()}.duckdb"),
            live_buffer=str(LIVE_BUFFER),
            platform_commit=_commit_ref(),
            span_snapshot=span_snapshot,
        )
        summary["recorder"] = recorder_meta
        summary["replay_inputs"] = True
    else:
        summary["replay_inputs"] = False

    (pkg / "session_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def _bootstrap_trading_schema(dm: DatabaseManager) -> None:
    from core.database.schema import (
        TRADING_TRADES_SCHEMA, TRADING_TRADE_CONTEXT_SCHEMA,
    )
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)


def _make_stop_handler(driver):
    """Return a signal handler that requests a clean driver stop (loop drains to
    STOPPED, the run_session `finally` finalizes the session package). Errors are
    swallowed so a second signal can never abort finalization."""
    def _handler(signum, frame):
        _logger.info("stop signal %s received; requesting clean driver stop",
                     signum)
        try:
            driver.stop()
        except Exception as exc:  # noqa: BLE001 — shutdown must not raise
            _logger.warning("driver.stop() during shutdown raised: %s", exc)
    return _handler


def run_session(*, session_date: date, data_root: Path, chain_db_path: str,
                initial_capital: float, max_bars: Optional[int],
                record: bool = True) -> int:
    """Run one LIVE PAPER session; return the process exit code."""
    data_root.mkdir(parents=True, exist_ok=True)
    journal = RuntimeEventJournal(str(data_root / "journal.jsonl"))
    telemetry = InMemoryTelemetrySink()
    dm = DatabaseManager(data_root=data_root)
    _bootstrap_trading_schema(dm)

    recorder = SessionRecorder(str(data_root / "sessions" / session_date.isoformat())) \
        if record else None
    facts_db = data_root / "facts.duckdb"
    span_snapshot = _load_span_snapshot()
    driver = build_nifty_shield_paper_driver(
        mode=Mode.LIVE,
        db_manager=dm,
        journal=journal,
        telemetry=telemetry,
        facts_db_path=str(facts_db),
        chain_db_path=chain_db_path,
        metrics_path=str(data_root / "metrics.json"),
        heartbeat_path=str(data_root / "heartbeat.json"),
        execution_store_path=str(data_root / "execution.db"),
        initial_capital=initial_capital,
        max_bars=max_bars,
        recorder=recorder,
        span_snapshot=span_snapshot,
    )

    # Cooperative external stop (ops orchestrator): SIGTERM (POSIX) / SIGBREAK
    # (Windows CTRL_BREAK_EVENT) drain the loop via driver.stop() so the
    # `finally` below finalizes the session package. Ctrl+C in a foreground
    # console still works through the KeyboardInterrupt path.
    handler = _make_stop_handler(driver)
    signal.signal(signal.SIGTERM, handler)
    if hasattr(signal, "SIGBREAK"):           # Windows CTRL_BREAK_EVENT
        signal.signal(signal.SIGBREAK, handler)

    interrupted = False
    try:
        driver.run()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        summary = finalize_session_evidence(
            session_date=session_date, data_root=data_root,
            telemetry=telemetry, driver=driver, recorder=recorder,
            facts_db_path=facts_db, initial_capital=initial_capital,
            span_snapshot=span_snapshot)

    print(f"\n=== NiftyShield PAPER session {session_date} ===")
    print(f"interrupted_by_operator: {interrupted}")
    print(f"bars_processed: {summary['bars_processed']} "
          f"signals_pulled: {summary['signals_pulled']}")
    print(f"telemetry clean: {summary['telemetry_clean']}")
    print(f"audit structures: {summary['audit_structures']} "
          f"guard_events: {summary['audit_guard_events']} "
          f"reverse_divergence: {summary['audit_reverse_divergence']}")
    print(f"metrics RT: {summary['metrics_round_trips']} "
          f"entered: {summary['metrics_entered']} "
          f"skipped: {summary['metrics_skipped']}")
    print(f"session package: {data_root / 'sessions' / session_date.isoformat()}")

    if summary["audit_guard_events"]:
        _logger.error("guard events on session %s: %s",
                      session_date, summary["audit_guard_events"])
        return 1
    if summary["audit_reverse_divergence"]:
        _logger.error("reverse divergence on session %s: %s",
                      session_date, summary["audit_reverse_divergence"])
        return 1
    if not summary["telemetry_clean"]:
        _logger.error("telemetry violations on session %s: %s",
                      session_date, summary["telemetry_violations"])
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NiftyShield Stage-2 PAPER session runner (E007 Phase B)")
    parser.add_argument("--date", default=None,
                        help="session date YYYY-MM-DD (default: today IST)")
    parser.add_argument("--data-root", default="data/nifty_shield",
                        help="isolated evidence root (default data/nifty_shield)")
    parser.add_argument("--chain-db", default=str(CHAIN_DB),
                        help="option-chain snapshot cache for real marks (E7-4)")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--no-record", action="store_true",
                        help="run without session recording (no replay evidence)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    session_date = (date.fromisoformat(args.date) if args.date
                    else MarketHours.get_ist_now().date())
    return run_session(
        session_date=session_date,
        data_root=Path(args.data_root).resolve(),
        chain_db_path=args.chain_db,
        initial_capital=args.capital,
        max_bars=args.max_bars,
        record=not args.no_record,
    )


if __name__ == "__main__":
    raise SystemExit(main())
