"""NiftyShield — Stage-2 PAPER runner entry point (E007 A).

Composes the FULL pipeline for a PAPER window at the frozen identity:
nifty_shield_v1 source -> GuardedSignalSource -> LoopDriver(publish_hook @ 13:00,
exit-driver rebalance hook) -> NiftyShieldExecutionHandler(PAPER) -> PaperBroker
-> ledger + journal + telemetry.

This is runner / composition-root code only — NO edit to the frozen strategy
package (identity: nifty_shield_v1 @ 89fcdd6 / c5b722ff…536c).

Mode:
- LIVE (default): forward window on the live feed (Mode.LIVE + ExecutionMode.PAPER).
- REPLAY: re-drives a recorded session through the same root (the §4.2/§4.G
  replay-evidence artifact and the Phase-A smoke run).

The marks feed (E7-4) is `ChainSnapshotMarksSource` by default (real Upstox V3
chain cache); a deterministic `StaticMarksSource` is injected for the smoke run.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional, Sequence

from core.clock import Clock, ReplayClock
from core.database.manager import DatabaseManager
from core.database.providers.live_market import LiveDuckDBMarketDataProvider
from core.execution.handler import ExecutionMode
from core.execution.options.nifty_shield_handler import (
    NiftyShieldExecutionHandler, NiftyShieldExitDriver,
)
from core.execution.options.nifty_shield_marks import (
    ChainSnapshotMarksSource, OptionMarksSource,
)
from core.execution.watchdog import RuntimeWatchdog
from core.runtime.config import Mode
from core.runtime.metrics import InMemoryTelemetrySink, TelemetrySink
from core.runtime.event_journal import EventType, RuntimeEventJournal, Severity
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_repository import SpanRepository
from strategies.nifty_shield_v1 import build_signal_source
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

from scripts.fno_runner import build_runner
from scripts.nifty_shield_paper.journal_hook import journaled_publish_hook_factory
from scripts.nifty_shield_paper.recorder import SessionRecorder

ROOT = Path(__file__).resolve().parents[1]

NF_SYMBOL = "NSE_INDEX|Nifty 50"
CHECKPOINT = time(13, 0)          # 13:00 IST — the DS2-2 pre-signal seam
# The publisher may retry from 13:00 through this deadline (inclusive) so a live
# fact that needs a few minutes to gather 13:00 bars still publishes. Matches the
# strategy's `entry_window_minutes` (the source waits the same window).
CHECKPOINT_DEADLINE = (datetime.combine(datetime.min, CHECKPOINT)
                       + timedelta(
                           minutes=DEFAULT_CONFIG["entry_window_minutes"])).time()
FACTS_DB = ROOT / "data" / "features" / "day_type" / "day_type_facts.duckdb"
CHAIN_DB = ROOT / "data" / "options" / "chain_cache.duckdb"
# Arbitrary replay anchor: the driver's clock is data-driven (advanced from each
# bar), so the start time only matters before the first bar arrives.
_REPLAY_DEFAULT_START = datetime(2026, 6, 5, 9, 15, 0)

_logger = logging.getLogger("nifty_shield_paper")


def _load_span_snapshot(journal=None):
    """SPAN snapshot for NseMarginEngine (SPAN+ELM margin evidence).

    Absent -> flat-rate MarginTracker fallback. ADR-011/012/013 make
    NseMarginEngine the sole margin authority in every mode, so this downgrade
    is a departure from the certified margin architecture and not a detail: the
    flat rate prices 20% of premium notional, which on the 2026-09-07 spread
    read Rs 4,619 against the broker's Rs 79,902. A logger warning is not an
    audit record, so journal it at CRITICAL and leave the evidence trail able
    to say which engine priced each entry.
    """
    try:
        repo = SpanRepository()
        return repo.load(expected_span_date())
    except Exception as exc:
        _logger.warning("SPAN snapshot unavailable (%s) — flat-rate margin", exc)
        if journal is not None:
            try:
                # STARTUP, not ENTRY_MARGIN: this is a session-level
                # composition fact with no structure behind it, and every
                # ENTRY_MARGIN consumer indexes metadata["group_id"].
                journal.record(
                    EventType.STARTUP,
                    "SPAN snapshot unavailable — margin downgraded to the "
                    "flat-rate MarginTracker (NOT NseMarginEngine); SPAN/ELM "
                    "evidence will be absent and the margin figure is not the "
                    "certified SPAN+ELM number",
                    severity=Severity.CRITICAL,
                    source_component="nifty_shield_paper_runner",
                    metadata={"expected_span_date": str(expected_span_date()),
                              "error": str(exc),
                              "engine": "MarginTracker"},
                )
            except Exception:
                _logger.exception("journal write failed for SPAN downgrade")
        return None


def _patch_execution_store(db_path: str) -> None:
    """Isolate the handler's ExecutionStore (default `data/execution.db`) so a
    PAPER window never reads stale repo state and runs are repeatable. The
    handler hardcodes `ExecutionStore()` at construction, so the dedicated
    PAPER process patches the module seam (the same pattern the platform's own
    handler tests use)."""
    import core.execution.handler as handler_mod
    from core.execution.persistence.execution_store import ExecutionStore
    handler_mod.ExecutionStore = lambda *a, **k: ExecutionStore(db_path)


def build_nifty_shield_paper_driver(
    *,
    mode: Mode = Mode.LIVE,
    clock: Optional[Clock] = None,
    db_manager: Optional[DatabaseManager] = None,
    journal: Optional[RuntimeEventJournal] = None,
    telemetry: Optional[TelemetrySink] = None,
    marks_source: Optional[OptionMarksSource] = None,
    facts_db_path: str = str(FACTS_DB),
    chain_db_path: str = str(CHAIN_DB),
    metrics_path: str = "logs/nifty_shield_metrics.json",
    heartbeat_path: str = "logs/heartbeat.json",
    execution_store_path: Optional[str] = None,
    initial_capital: float = 1_000_000.0,
    symbols: Sequence[str] = (NF_SYMBOL,),
    max_bars: Optional[int] = None,
    recorder: Optional[SessionRecorder] = None,
    provider: Optional[object] = None,
    span_snapshot: Optional[object] = None,
):
    """Compose the full NiftyShield PAPER pipeline (LIVE or REPLAY).

    When `recorder` is set (Phase B forward window), the source, marks source
    and market-data provider are wrapped in the recorder's seams so the session
    package captures exactly what the composition root consumed (replay-evidence
    input, deliverable G). `provider` overrides the market-data provider (the
    REPLAY-evidence harness injects a recorded-bar provider).
    """
    db_manager = db_manager or DatabaseManager()
    journal = journal or RuntimeEventJournal(
        "logs/nifty_shield_runtime_events.jsonl")
    telemetry = telemetry or InMemoryTelemetrySink()
    _patch_execution_store(execution_store_path or
                           "data/nifty_shield/execution.db")

    # Bootstrap the SQLite trade ledger so save_trade persists fills (the audit
    # and metrics-report tools read it).
    from core.database.schema import (
        TRADING_TRADES_SCHEMA, TRADING_TRADE_CONTEXT_SCHEMA,
    )
    with db_manager.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)

    marks = marks_source or ChainSnapshotMarksSource(chain_db_path)
    # F3: a broken marks cache must refuse to start, never silently skip every
    # entry as "missing marks". StaticMarksSource (tests/smoke) has no cache.
    check = getattr(marks, "check_available", None)
    if check is not None:
        check()
    if span_snapshot is None:
        span_snapshot = _load_span_snapshot(journal)
    strategy_config = dict(DEFAULT_CONFIG)

    source = build_signal_source({"facts_db_path": facts_db_path})
    if provider is None:
        DatabaseManager.reset_instance()
        market_db = DatabaseManager(data_root="data")
        provider = LiveDuckDBMarketDataProvider(list(symbols), db_manager=market_db)
        # Restore the evidence-scoped singleton for downstream callers
        DatabaseManager.reset_instance()
        DatabaseManager(data_root=str(db_manager.data_root))

    if recorder is not None:
        # Phase B: wrap every input seam so the session package captures exactly
        # what the composition root consumed. The wrapped objects are still the
        # same interface — no pipeline behaviour change.
        source = recorder.wrap_source(source)
        marks = recorder.wrap_marks(marks)
        provider = recorder.wrap_provider(provider)

    def handler_factory(**kwargs):
        kwargs.setdefault("journal", journal)
        kwargs.setdefault("span_snapshot", span_snapshot)
        return NiftyShieldExecutionHandler(
            marks_source=marks,
            strategy_config=strategy_config,
            **kwargs,
        )

    def exit_hook_factory(execution):
        return NiftyShieldExitDriver(execution, marks)

    def publish_hook_factory(execution):
        return journaled_publish_hook_factory(journal, facts_db_path)(execution)

    def watchdog_factory(execution):
        # LIVE-only: heartbeat + staleness evidence for the PAPER window. The
        # driver drives it per tick (live-gated internally, §9.5).
        return RuntimeWatchdog(execution, heartbeat_path=heartbeat_path)

    if mode is Mode.REPLAY and clock is None:
        clock = ReplayClock(_REPLAY_DEFAULT_START)

    return build_runner(
        source=source,
        symbols=symbols,
        execution_mode=ExecutionMode.PAPER,
        db_manager=db_manager,
        journal=journal,
        telemetry=telemetry,
        metrics_path=metrics_path,
        initial_capital=initial_capital,
        handler_factory=handler_factory,
        rebalance_hook_factory=exit_hook_factory,
        publish_hook_factory=publish_hook_factory,
        publish_checkpoint_time=CHECKPOINT,
        publish_checkpoint_deadline=CHECKPOINT_DEADLINE,
        watchdog_factory=watchdog_factory if mode is Mode.LIVE else None,
        mode=mode,
        clock=clock,
        provider=provider,
        max_bars=max_bars,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NiftyShield Stage-2 PAPER runner (E007 Phase A wiring)")
    parser.add_argument("--facts-db", default=str(FACTS_DB))
    parser.add_argument("--chain-db", default=str(CHAIN_DB))
    parser.add_argument("--journal", default="logs/nifty_shield_runtime_events.jsonl")
    parser.add_argument("--metrics", default="logs/nifty_shield_metrics.json")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--max-bars", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    driver = build_nifty_shield_paper_driver(
        mode=Mode.LIVE,
        facts_db_path=args.facts_db,
        chain_db_path=args.chain_db,
        metrics_path=args.metrics,
        initial_capital=args.capital,
        max_bars=args.max_bars,
    )
    driver.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
