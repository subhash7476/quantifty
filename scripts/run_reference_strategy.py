#!/usr/bin/env python3
"""
MM12.4 — Reference Strategy Happy-Path Runner

Runs HeartbeatSignalSource through the real composition root
(fno_runner.build_runner) in PAPER mode over a recorded bar corpus.

Usage:
    python scripts/run_reference_strategy.py [--symbol SYM] [--bars N]
        [--entry-period N] [--holding-period N] [--sl-pct P] [--risk-r R]
        [--data-dir PATH] [--max-bars N]

Evidence outputs (under data-dir or cwd):
    logs/runtime_events.jsonl   — journal
    logs/telemetry.json          — telemetry snapshot

This script is a platform validation tool, not a trading strategy.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import pytz

from core.brokers.paper_broker import PaperBroker
from core.clock import Clock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar
from core.execution.handler import ExecutionMode
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.signal_source import SignalSource
from reference_strategies.heartbeat import build_signal_source
from scripts.fno_runner import build_runner


def _build_synthetic_provider(symbol: str, total_bars: int,
                              start: datetime, close: float = 100.0,
                              step_minutes: int = 1) -> MarketDataProvider:
    """Build a FakeMarketDataProvider with a scripted bar corpus."""
    from tests.runtime._doubles import FakeMarketDataProvider, make_bar

    bars = [make_bar(symbol, start + timedelta(minutes=i * step_minutes), close)
            for i in range(total_bars)]
    return FakeMarketDataProvider({symbol: bars})


def main():
    parser = argparse.ArgumentParser(
        description="MM12.4 Reference Strategy Happy-Path Runner")
    parser.add_argument("--symbol", default="NSE_EQ|INE000A01012",
                        help="Traded symbol (default a placeholder equity)")
    parser.add_argument("--bars", type=int, default=200,
                        help="Number of bars to run (default 200)")
    parser.add_argument("--entry-period", type=int, default=60,
                        help="Entry cadence in bars (default 60)")
    parser.add_argument("--holding-period", type=int, default=15,
                        help="Holding period in bars (default 15)")
    parser.add_argument("--sl-pct", type=float, default=0.01,
                        help="SL distance as fraction of close (default 0.01)")
    parser.add_argument("--risk-r", type=float, default=500.0,
                        help="Risk R units (default 500.0)")
    parser.add_argument("--max-bars", type=int, default=None,
                        help="Max bars to process (default = same as --bars)")
    parser.add_argument("--data-dir", default=os.getcwd(),
                        help="Output directory for logs")
    args = parser.parse_args()

    output_dir = args.data_dir
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)

    # Shared telemetry sink for observability
    telemetry = InMemoryTelemetrySink()

    # Journal
    journal = RuntimeEventJournal(
        path=os.path.join(output_dir, "logs/runtime_events.jsonl"),
        source_component="run_reference_strategy",
    )

    # Build the source via the external-style factory
    source = build_signal_source({
        "entry_period_bars": args.entry_period,
        "holding_period_bars": args.holding_period,
        "sl_distance_pct": args.sl_pct,
        "risk_r": args.risk_r,
    })

    # Build a synthetic provider with recorded bar corpus
    start = datetime(2026, 6, 5, 9, 15, 0, tzinfo=pytz.UTC)
    max_bars = args.max_bars or args.bars
    provider = _build_synthetic_provider(args.symbol, args.bars, start)

    from core.clock import ReplayClock
    clock = ReplayClock()

    runner = build_runner(
        source=source,
        symbols=[args.symbol],
        execution_mode=ExecutionMode.PAPER,
        clock=clock,
        provider=provider,
        journal=journal,
        telemetry=telemetry,
        max_bars=max_bars,
    )

    runner.run()

    # Report
    print(f"=== MM12.4 Reference Strategy Report ===")
    print(f"Strategy: reference_heartbeat_v1")
    print(f"Total bars processed: {runner.bars_processed}")
    print(f"Total signals pulled: {runner.signals_pulled}")
    print(f"Journal: {os.path.join(output_dir, 'logs/runtime_events.jsonl')}")

    snapshot = telemetry.snapshot()
    print(f"\nTelemetry snapshot:")
    for metric, count in sorted(snapshot.items(), key=lambda x: x[0].value):
        print(f"  {metric.value}: {count}")

    # Save telemetry snapshot
    telemetry_path = os.path.join(output_dir, "logs/telemetry.json")
    with open(telemetry_path, "w") as f:
        json.dump({k.value: v for k, v in snapshot.items()}, f, indent=2)
    print(f"\nTelemetry snapshot saved to: {telemetry_path}")

    # Acceptance check: must have zero guard events
    guard_events = [
        RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS,
        RuntimeMetric.STRATEGY_ERRORS,
        RuntimeMetric.STRATEGY_QUARANTINE_EVENTS,
    ]
    violations = []
    for m in guard_events:
        count = snapshot.get(m, 0)
        if count > 0:
            violations.append(f"{m.value}={count}")
    if violations:
        print(f"\n!!! GUARD EVENT VIOLATION: {', '.join(violations)}")
        sys.exit(1)
    else:
        print(f"\nOK: zero guard events (SIGNAL_CONTRACT_REJECTIONS, "
              f"STRATEGY_ERRORS, STRATEGY_QUARANTINE_EVENTS)")

    # Check at least one full round trip
    if runner.bars_processed >= args.entry_period + args.holding_period:
        print(f"OK: >=1 full round trip possible "
              f"({runner.bars_processed} >= {args.entry_period + args.holding_period})")
    else:
        print(f"WARNING: fewer bars processed than a full round trip needs")

    if runner.signals_pulled > 0:
        print(f"OK: {runner.signals_pulled} signal(s) emitted")
    else:
        print(f"WARNING: no signals emitted")


if __name__ == "__main__":
    main()
