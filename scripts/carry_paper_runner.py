"""Carry sleeve — PAPER mode entry point.

Wires CarryRebalancerHook into a running PAPER-mode LoopDriver via
fno_runner.build_runner()'s rebalance_hook_factory seam.

§6.4 of the go-live gate: run live-paper to validate fill pipeline,
position tracking, and rebalancer wiring end-to-end without real capital.
Slippage measurement is deferred to LIVE (real broker fills).

Bridge: CARRY_IMPLEMENTATION_BRIDGE.md §4.1, §6.4.
Prompt: docs/reports/CARRY_PAPER_INTEGRATION_PROMPT.md
"""
from __future__ import annotations

import duckdb
import logging
from pathlib import Path
from typing import List, Optional

from core.events import OHLCVBar, SignalEvent
from core.execution.handler import ExecutionMode
from core.runtime.signal_source import SignalSource
from scripts.fno_runner import build_runner

ROOT = Path(__file__).resolve().parents[2]
FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
BHAVCOPY_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

_logger = logging.getLogger("carry_paper")


class NoOpSignalSource(SignalSource):
    """Trivial source that emits nothing — the rebalance hook drives everything."""

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        return []

    def on_start(self, context=None) -> None:
        pass

    def on_stop(self) -> None:
        pass


def _load_symbols() -> list[str]:
    """Derive the traded universe from facts DB — no separate universe source."""
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT underlying FROM carry_facts ORDER BY underlying"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _rebalance_hook_factory(execution_handler):
    from core.execution.portfolio.carry_rebalancer import (
        CarryRebalancerHook, paper_gross_exposure_policy,
    )
    return CarryRebalancerHook(
        facts_db_path=str(FACTS_DB),
        execution_handler=execution_handler,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(BHAVCOPY_DB),
    )


def main():
    symbols = _load_symbols()
    _logger.info("Carry PAPER: %d symbols from facts DB", len(symbols))

    driver = build_runner(
        source=NoOpSignalSource(),
        symbols=symbols,
        underlyings=symbols,
        execution_mode=ExecutionMode.PAPER,
        rebalance_hook_factory=_rebalance_hook_factory,
        initial_capital=10_000_000.0,  # Rs 1 Cr — 1:1 with paper gross
    )
    driver.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    raise SystemExit(main())
