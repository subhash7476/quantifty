"""TS Basis Daily — concentrated backtest (top-5 longs, top-5 shorts).

Mirror of ts_basis_concentrated_backtest.py for daily cadence.
Reuses CarryRebalancerHook with max_positions_per_leg=5.

Usage: python scripts/ts_basis_daily_concentrated_backtest.py
"""
from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_logger = logging.getLogger("ts_basis_daily_b5")

TS_FACTS = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
TS_SIG = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"

MAX_POSITIONS = 5
GROSS_EXPOSURE = 10_000_000.0
PPY = 252.0

WINDOWS = {
    "TRAIN":   (date(2016, 4, 29), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1, 29), date(2022, 12, 31)),
}

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
from core.execution.portfolio.exit_policy import TakeProfitExitPolicy
from core.execution.position_models import PositionSide


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _max_dd(daily):
    eq = np.cumprod(1.0 + np.array(daily))
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(np.min(dd))


def _sharpe(daily):
    arr = np.array(daily)
    if len(arr) < 2 or np.std(arr, ddof=1) == 0:
        return 0.0
    return float(np.mean(arr) / np.std(arr, ddof=1) * np.sqrt(PPY))


def _run_window(label, lo, hi):
    con = duckdb.connect(str(FUT_DB), read_only=True)
    symbols = [r[0] for r in con.execute("""
        SELECT DISTINCT underlying FROM futures_bhavcopy
        WHERE trade_date >= ? AND trade_date <= ? AND inst_type='FUTSTK'
        ORDER BY underlying
    """, [lo, hi]).fetchall()]
    con.close()

    provider = DailyBhavcopyProvider(
        underlyings=symbols, bhavcopy_db=str(FUT_DB),
        start_date=lo, end_date=hi,
    )
    broker = PaperBroker(clock=ReplayClock(start_time=datetime.combine(lo, dt_time.min)))
    db_manager = DatabaseManager(data_root="data", read_only=True)
    execution = ExecutionHandler(
        db_manager=db_manager,
        clock=ReplayClock(start_time=datetime.combine(lo, dt_time.min)),
        broker=broker,
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        initial_capital=GROSS_EXPOSURE, load_db_state=False,
    )

    captured = []

    def sink(fdate, deltas, target, metrics, cap_state):
        executions = [d for d in deltas if not d.suppressed]
        captured.append({
            "formation_date": fdate,
            "target": target,
            "fees": metrics.fees_total + metrics.slippage_total,
            "n_long": len(target.longs),
            "n_short": len(target.shorts),
            "turnover": metrics.traded_value_total / max(
                sum(target.longs.values()) + sum(target.shorts.values()), 1.0,
            ),
        })

    hook = CarryRebalancerHook(
        facts_db_path=str(TS_FACTS), execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB), metrics_sink=sink,
        signals_db_path=str(TS_SIG), max_positions_per_leg=MAX_POSITIONS,
        exit_policy=TakeProfitExitPolicy(threshold=0.005),
        sector_csv_path=str(ROOT / "governance" / "carry" / "sector_classification.csv"),
        max_per_sector=2,
    )

    driver = LoopDriver(
        config=DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000),
        clock=ReplayClock(start_time=datetime.combine(lo, dt_time.min)),
        provider=provider, source=None, execution=execution,
        rebalance_hook=hook.__call__,
    )
    driver.run()
    return captured


def _compute_returns(captured):
    if len(captured) < 2:
        return [], 0.0, 0.0

    con = duckdb.connect(str(TS_SIG), read_only=True)
    fd_set = ", ".join(f"DATE '{r['formation_date']}'" for r in captured)
    rows = con.execute(f"""
        SELECT formation_date, underlying, fwd_ret_1m FROM signals
        WHERE formation_date IN ({fd_set}) AND fwd_ret_1m IS NOT NULL
    """).fetchall()
    con.close()
    fwd = defaultdict(dict)
    for fd, u, fr in rows:
        fwd[fd][u] = float(fr)

    net = []
    gross_list = []
    for i in range(1, len(captured)):
        prev = captured[i - 1]
        curr = captured[i]
        book = prev["target"]
        fd_map = fwd.get(prev["formation_date"], {})
        lg = sum(book.longs.values())
        sg = sum(book.shorts.values())
        gl = sum(v * fd_map.get(u, 0.0) for u, v in book.longs.items())
        gs = sum(v * fd_map.get(u, 0.0) for u, v in book.shorts.items())
        gr = gl / max(lg, 1e-6) - gs / max(sg, 1e-6)
        gross_list.append(gr)
        net.append(gr - curr["fees"] / GROSS_EXPOSURE)

    periods = len(net)
    ann_net = float((np.prod([1.0 + r for r in net]) ** (PPY / periods) - 1)) if periods > 0 else 0.0
    ann_gross = float((np.prod([1.0 + r for r in gross_list]) ** (PPY / periods) - 1)) if periods > 0 else 0.0
    return net, ann_net, ann_gross, ann_gross - ann_net


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print(f"TS Basis Daily Concentrated (top-{MAX_POSITIONS}/bottom-{MAX_POSITIONS})")
    print(f"Gross: Rs {GROSS_EXPOSURE/1e7:.1f} Cr, Slippage: 5 bp/side, Daily\n")
    print(f"{'Window':<10} {'Rebals':>6} {'Ann Gross':>10} {'Ann Net':>10} {'Fee Drag':>10} {'Max DD':>10} {'Sharpe':>7} {'Avg TO':>7}")
    print("-" * 70)

    for label, (lo, hi) in WINDOWS.items():
        captured = _run_window(label, lo, hi)
        net_series, ann_net, ann_gross, fee_drag = _compute_returns(captured)
        dd = _max_dd(net_series)
        sh = _sharpe(net_series)
        avg_to = np.mean([r["turnover"] for r in captured[1:]]) if len(captured) > 1 else 0.0

        print(f"{label:<10} {len(captured):>6} {ann_gross*100:>10.1f}% {ann_net*100:>10.1f}% "
              f"{fee_drag*10000:>10.0f} bp {dd*100:>9.1f}% {sh:>7.2f} {avg_to:>7.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
