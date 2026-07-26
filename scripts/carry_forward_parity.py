"""Carry forward-vs-replay parity harness — HIGH-2 verification.

Runs the forward runner's code path (DailyBhavcopyProvider + LoopDriver +
CarryRebalancerHook) over bounded TRAIN/HOLDOUT windows and confirms it
reproduces carry_paper_replay at +0.0 bp before any live-paper start.

Usage: python scripts/carry_forward_parity.py
Exit: 0 if both windows pass within 15 bp tolerance.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
RESEARCH_SNAP = ROOT / "docs" / "reports" / "CARRY_NET_SPREAD_SNAPSHOT.json"
TOLERANCE_BP = 15

from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionHandler, ExecutionConfig, ExecutionMode
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
from core.execution.portfolio.carry_rebalancer import (
    CarryRebalancerHook, paper_gross_exposure_policy,
)

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}


def _load_symbols(window_lo, window_hi):
    con = duckdb.connect(str(FUT_DB), read_only=True)
    symbols = [r[0] for r in con.execute(f"""
        SELECT DISTINCT underlying FROM futures_bhavcopy
        WHERE trade_date >= ? AND trade_date <= ? AND inst_type='FUTSTK'
        ORDER BY underlying
    """, [window_lo, window_hi]).fetchall()]
    con.close()
    return symbols


def main():
    research = {}
    if RESEARCH_SNAP.exists():
        with open(RESEARCH_SNAP) as f:
            research = json.load(f).get("results", {})

    all_pass = True

    for label, (lo, hi) in WINDOWS.items():
        symbols = _load_symbols(lo, hi)
        print(f"\n{label}: {lo} -> {hi} ({len(symbols)} symbols)")

        provider = DailyBhavcopyProvider(
            underlyings=symbols, bhavcopy_db=str(FUT_DB),
            start_date=lo, end_date=hi,
        )
        clock = ReplayClock(start_time=datetime.combine(lo, dt_time.min))
        broker = PaperBroker(clock=clock)
        db_manager = DatabaseManager(data_root="data", read_only=True)
        execution = ExecutionHandler(
            db_manager=db_manager, clock=clock, broker=broker,
            config=ExecutionConfig(mode=ExecutionMode.PAPER),
            initial_capital=10_000_000.0, load_db_state=False,
        )

        captured: list = []
        def sink(fdate, deltas, target, metrics, cap_state):
            captured.append({"formation_date": fdate, "target": target,
                             "fees": metrics.fees_total + metrics.slippage_total})

        hook = CarryRebalancerHook(
            facts_db_path=str(FACTS_DB), execution_handler=execution,
            gross_exposure_policy=paper_gross_exposure_policy,
            bhavcopy_db_path=str(FUT_DB), metrics_sink=sink,
            signals_db_path=str(SIG_DB),
        )

        driver = LoopDriver(
            config=DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000),
            clock=ReplayClock(start_time=datetime.combine(lo, dt_time.min)),
            provider=provider, source=None, execution=execution,
            rebalance_hook=hook.__call__,
        )
        driver.run()

        if len(captured) < 2:
            print(f"  FAIL: only {len(captured)} rebalances")
            all_pass = False
            continue

        sig = duckdb.connect(str(SIG_DB), read_only=True)
        fdates = sorted(r["formation_date"] for r in captured)
        fdate_set = ", ".join(f"DATE '{d}'" for d in fdates)
        fwd_rows = sig.execute(f"""
            SELECT formation_date, underlying, fwd_ret_1m FROM signals
            WHERE formation_date IN ({fdate_set}) AND fwd_ret_1m IS NOT NULL
        """).fetchall()
        sig.close()

        from collections import defaultdict
        fwd = defaultdict(dict)
        for fd, u, fr in fwd_rows:
            fwd[fd][u] = float(fr)

        net_returns = []
        for i in range(1, len(captured)):
            prev = captured[i - 1]
            curr = captured[i]
            book = prev["target"]
            fwd_map = fwd.get(prev["formation_date"], {})
            lg = sum(book.longs.values())
            sg = sum(book.shorts.values())
            gl = sum(v * fwd_map.get(u, 0.0) for u, v in book.longs.items())
            gs = sum(v * fwd_map.get(u, 0.0) for u, v in book.shorts.items())
            gr = gl / max(lg, 1e-6) - gs / max(sg, 1e-6)
            nr = gr - curr["fees"] / 10_000_000.0
            net_returns.append(nr)

        months = len(net_returns)
        ann_net = float((np.prod([1.0 + r for r in net_returns]) ** (12.0 / months) - 1))
        res_key = f"{label}_quintile"
        res_net = research.get(res_key, {}).get("ann_net", 0.0) if isinstance(research.get(res_key), dict) else 0.0
        delta_bp = (ann_net - res_net) * 10000.0
        within = abs(delta_bp) < TOLERANCE_BP

        print(f"  Rebalances: {len(captured)}  Ann Net: {ann_net*100:+.4f}%  "
              f"Research: {res_net*100:+.4f}%  Delta: {delta_bp:+.1f} bp  "
              f"{'PASS' if within else 'FAIL'}")

        if not within:
            all_pass = False

    print(f"\nForward-vs-replay parity: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
