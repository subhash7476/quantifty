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
from datetime import datetime, time
from pathlib import Path
from typing import Optional, Sequence

from core.clock import Clock, ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionMode
from core.execution.options.nifty_shield_handler import (
    NiftyShieldExecutionHandler, NiftyShieldExitDriver,
)
from core.execution.options.nifty_shield_marks import (
    ChainSnapshotMarksSource, OptionMarksSource,
)
from core.runtime.config import Mode
from core.runtime.metrics import InMemoryTelemetrySink, TelemetrySink
from core.runtime.event_journal import RuntimeEventJournal
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_repository import SpanRepository
from strategies.nifty_shield_v1 import build_signal_source
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

from scripts.fno_runner import build_runner
from scripts.nifty_shield_paper.journal_hook import journaled_publish_hook_factory

ROOT = Path(__file__).resolve().parents[1]

NF_SYMBOL = "NSE_INDEX|Nifty 50"
CHECKPOINT = time(13, 0)          # 13:00 IST — the DS2-2 pre-signal seam
FACTS_DB = ROOT / "data" / "features" / "day_type" / "day_type_facts.duckdb"
CHAIN_DB = ROOT / "data" / "options" / "chain_cache.duckdb"
# Arbitrary replay anchor: the driver's clock is data-driven (advanced from each
# bar), so the start time only matters before the first bar arrives.
_REPLAY_DEFAULT_START = datetime(2026, 6, 5, 9, 15, 0)

_logger = logging.getLogger("nifty_shield_paper")


def _load_span_snapshot():
    """Best-effort SPAN snapshot for NseMarginEngine (SPAN+ELM margin evidence).
    Absent -> flat-rate MarginTracker fallback (journaled as such, §7.7)."""
    try:
        repo = SpanRepository()
        return repo.load(expected_span_date())
    except Exception as exc:
        _logger.warning("SPAN snapshot unavailable (%s) — flat-rate margin", exc)
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
):
    """Compose the full NiftyShield PAPER pipeline (LIVE or REPLAY)."""
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
    span_snapshot = _load_span_snapshot()
    strategy_config = dict(DEFAULT_CONFIG)

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

    if mode is Mode.REPLAY and clock is None:
        clock = ReplayClock(_REPLAY_DEFAULT_START)

    return build_runner(
        source=build_signal_source({"facts_db_path": facts_db_path}),
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
        mode=mode,
        clock=clock,
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
