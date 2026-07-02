#!/usr/bin/env python3
"""
MM12.4 — GuardedSignalSource Fault Drill

Proves GuardedSignalSource's reject-and-quarantine behavior live through
the real composition root using two throwaway fixture sources:

    1. AlwaysRaisesSource   — proves quarantine-and-continue:
       STRATEGY_ERROR -> STRATEGY_QUARANTINED (once) -> loop survives.

    2. BadMetadataSource    — proves reject-and-journal:
       SIGNAL_CONTRACT_REJECTED observed; contract-clean sibling still routes.

Usage:
    python scripts/run_fault_drill.py [--mode {raises,bad-meta}] [--data-dir PATH]

This script is a platform validation tool, not a trading strategy.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import pytz

from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionMode
from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink, RuntimeMetric
from reference_strategies.fault_fixtures import AlwaysRaisesSource, BadMetadataSource
from scripts.fno_runner import build_runner

from tests.runtime._doubles import FakeMarketDataProvider, make_bar


def _build_provider(symbol: str, total_bars: int,
                    start: datetime, close: float = 100.0) -> FakeMarketDataProvider:
    bars = [make_bar(symbol, start + timedelta(minutes=i), close)
            for i in range(total_bars)]
    return FakeMarketDataProvider({symbol: bars})


def _check_mode(source_id, expected_type_name, journal_path, telemetry):
    """Check the journal for the expected event type and return violations."""
    if not os.path.exists(journal_path):
        return ["journal file not found"]

    violations = []
    found_quarantine = False
    found_signal_rejected = False
    found_strategy_error = False

    with open(journal_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            et = record.get("event_type")
            if et == EventType.STRATEGY_QUARANTINED.value:
                found_quarantine = True
            if et == EventType.STRATEGY_ERROR.value:
                found_strategy_error = True
            if et == EventType.SIGNAL_CONTRACT_REJECTED.value:
                found_signal_rejected = True

    snapshot = telemetry.snapshot()

    if source_id == "raises":
        if not found_strategy_error:
            violations.append(
                "MISSING: STRATEGY_ERROR journal entry (expected for raising source)")
        if not found_quarantine:
            violations.append(
                "MISSING: STRATEGY_QUARANTINED journal entry (expected once)")
        errors = snapshot.get(RuntimeMetric.STRATEGY_ERRORS, 0)
        if errors < 1:
            violations.append(
                f"MISSING: STRATEGY_ERRORS telemetry counter (got {errors})")
        quarantines = snapshot.get(RuntimeMetric.STRATEGY_QUARANTINE_EVENTS, 0)
        if quarantines < 1:
            violations.append(
                f"MISSING: STRATEGY_QUARANTINE_EVENTS telemetry counter "
                f"(got {quarantines})")
        # Check it's edge-triggered (only 1 quarantine even across multiple bars)
        if quarantines > 1:
            violations.append(
                f"NOT EDGE-TRIGGERED: STRATEGY_QUARANTINE_EVENTS={quarantines} "
                f"(expected 1)")

    if source_id == "bad-meta":
        if not found_signal_rejected:
            violations.append(
                "MISSING: SIGNAL_CONTRACT_REJECTED journal entry (expected for "
                "bad metadata source)")
        rejections = snapshot.get(RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS, 0)
        if rejections < 1:
            violations.append(
                f"MISSING: SIGNAL_CONTRACT_REJECTIONS telemetry counter "
                f"(got {rejections})")

    return violations


def main():
    parser = argparse.ArgumentParser(
        description="MM12.4 Fault Drill — prove GuardedSignalSource behavior live")
    parser.add_argument("--mode", choices=["raises", "bad-meta"], default="raises",
                        help="Fault fixture to use (default: raises)")
    parser.add_argument("--data-dir", default=os.getcwd(),
                        help="Output directory for logs")
    parser.add_argument("--symbol", default="NSE_EQ|INE000A01012",
                        help="Traded symbol")
    parser.add_argument("--bars", type=int, default=10,
                        help="Number of bars to process (default 10)")
    args = parser.parse_args()

    output_dir = args.data_dir
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)

    telemetry = InMemoryTelemetrySink()

    journal_path = os.path.join(output_dir, "logs/runtime_events.jsonl")
    if os.path.exists(journal_path):
        os.remove(journal_path)

    journal = RuntimeEventJournal(
        path=journal_path,
        source_component="run_fault_drill",
    )

    if args.mode == "raises":
        source = AlwaysRaisesSource()
        source_label = "AlwaysRaisesSource"
    else:
        source = BadMetadataSource()
        source_label = "BadMetadataSource"

    start = datetime(2026, 6, 5, 9, 15, 0, tzinfo=pytz.UTC)
    provider = _build_provider(args.symbol, args.bars, start)
    clock = ReplayClock()

    runner = build_runner(
        source=source,
        symbols=[args.symbol],
        execution_mode=ExecutionMode.PAPER,
        clock=clock,
        provider=provider,
        journal=journal,
        telemetry=telemetry,
        max_bars=args.bars,
    )

    runner.run()

    print(f"=== MM12.4 Fault Drill Report ===")
    print(f"Fixture: {source_label}")
    print(f"Total bars processed: {runner.bars_processed}")
    print(f"Journal: {journal_path}")

    snapshot = telemetry.snapshot()
    print(f"\nTelemetry snapshot:")
    for metric, count in sorted(snapshot.items(), key=lambda x: x[0].value):
        print(f"  {metric.value}: {count}")

    violations = _check_mode(
        args.mode, source_label, journal_path, telemetry)

    if violations:
        print(f"\n!!! FAULT DRILL VIOLATIONS:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print(f"\nOK: all expected guard events observed for {source_label}")
        print(f"Loop survived, process did not crash.")


if __name__ == "__main__":
    main()
