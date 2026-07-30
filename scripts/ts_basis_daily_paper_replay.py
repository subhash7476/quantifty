"""TS Basis Daily — historical PAPER replay.

Mirror of ts_basis_paper_replay.py for daily cadence.
Reuses CarryRebalancerHook — ts_facts.duckdb stores z_ts
in the z_carry_neut column.

Usage: python scripts/ts_basis_daily_paper_replay.py
"""
from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_logger = logging.getLogger("ts_basis_daily_replay")

TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
PROD_DB = ROOT / "data" / "signal_engine" / "carry" / "production.duckdb"
TI_DB = ROOT / "data" / "signal_engine" / "trade_intelligence" / "trade_intelligence.duckdb"
IDX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"

WINDOWS = {
    "TRAIN":   (date(2016, 4, 29), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1, 29), date(2022, 12, 31)),
}

GROSS_EXPOSURE = 10_000_000.0
INITIAL_CAPITAL = 10_000_000.0
PPY = 252.0

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
from core.execution.portfolio.carry_metrics_db import CarryMetricsDB
from core.execution.portfolio.exit_policy import TakeProfitExitPolicy
from core.execution.portfolio.trade_intelligence_sink import TradeIntelligenceSink


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


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
        initial_capital=INITIAL_CAPITAL, load_db_state=False,
    )

    captured: list = []

    def sink(fdate, deltas, target, metrics, cap_state):
        executions = [d for d in deltas if not d.suppressed]
        all_caps = list(target.longs.values()) + list(target.shorts.values())
        total_cap = sum(all_caps) or 1.0
        shares = sorted([c / total_cap for c in all_caps], reverse=True)
        top3 = sum(shares[:3]) if len(shares) >= 3 else sum(shares)
        hhi = sum(s ** 2 for s in shares)
        lg = sum(target.longs.values())
        sg = sum(target.shorts.values())
        to = metrics.traded_value_total / max(lg + sg, 1.0)

        captured.append({
            "formation_date": fdate, "target": target,
            "fees": metrics.fees_total + metrics.slippage_total,
            "n_long": len(target.longs), "n_short": len(target.shorts),
            "traded_value": metrics.traded_value_total, "turnover": to,
            "fees_total": metrics.fees_total, "slippage_total": metrics.slippage_total,
            "top3_conc": top3, "hhi": hhi,
        })
        _logger.info("TS Basis Daily rebalance: %s %dL/%dS fees=%.0f slip=%.0f",
                      fdate, len(target.longs), len(target.shorts),
                      metrics.fees_total, metrics.slippage_total)

    # Trade intelligence sink — write-only, never blocks execution
    ti_sink = TradeIntelligenceSink(
        db_path=str(TI_DB), sector_csv=str(SECTOR_CSV),
    )

    hook = CarryRebalancerHook(
        facts_db_path=str(TS_FACTS_DB), execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB), metrics_sink=sink,
        signals_db_path=str(TS_SIG_DB),
        exit_policy=TakeProfitExitPolicy(threshold=0.005),
        trade_sink=ti_sink.__call__,
        max_positions_per_leg=5,
        sector_csv_path=str(SECTOR_CSV),
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
        return []
    con = duckdb.connect(str(TS_SIG_DB), read_only=True)
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
        net.append(gr - curr["fees"] / GROSS_EXPOSURE)

    periods = len(net)
    ann = float((np.prod([1.0 + r for r in net]) ** (PPY / periods) - 1)) if periods > 0 else 0.0
    return net, ann


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if not TS_FACTS_DB.exists():
        _logger.error("TS Basis Daily facts not found: %s", TS_FACTS_DB)
        _logger.error("Run scripts/signal_engine/ts_basis_daily/publish_facts.py first.")
        return 1

    commit = _git_commit()
    now_ts = datetime.utcnow().isoformat() + "Z"

    # Clean TI DB for fresh replay
    if TI_DB.exists():
        TI_DB.unlink()

    with CarryMetricsDB(str(PROD_DB)) as db:
        for label, (lo, hi) in WINDOWS.items():
            _logger.info("Replay %s: %s -> %s", label, lo, hi)
            captured = _run_window(label, lo, hi)
            if not captured:
                _logger.warning("No rebalances for %s", label)
                continue

            run_id = f"ts-basis-daily-replay-{label.lower()}-{now_ts[:10]}"
            db.write_run_metadata(
                run_id=run_id, git_commit=commit,
                generated_at=datetime.utcnow(),
                window_label=f"TS_DAILY_{label}",
                window_lo=lo, window_hi=hi,
                gross_exposure=GROSS_EXPOSURE,
                params_json=json.dumps({"sleeve": "ts_basis_daily", "quintile_frac": 0.20, "cadence": "daily"}),
                determinism_hash=None, source="replay",
            )

            for cap in captured:
                db.write_rebalance_summary(
                    run_id=run_id, formation_date=cap["formation_date"],
                    n_long=cap["n_long"], n_short=cap["n_short"],
                    traded_value=cap["traded_value"], turnover=cap["turnover"],
                    fees_total=cap["fees_total"], slippage_total=cap["slippage_total"],
                    fee_brokerage=0.0, fee_stt=0.0, fee_exchange_txn=0.0,
                    fee_sebi_fee=0.0, fee_stamp_duty=0.0, fee_gst=0.0,
                    top3_conc=cap["top3_conc"], hhi=cap["hhi"],
                    margin_util_pct=0.0,
                )

            net_series, ann_net = _compute_returns(captured)
            _logger.info("%s: %d rebalances, ann_net=%+.4f%% (%d periods)",
                         label, len(captured), ann_net * 100, len(net_series))

            dhash = db.compute_determinism_hash(run_id)
            db._conn.execute(
                "UPDATE run_metadata SET determinism_hash=? WHERE run_id=?",
                [dhash, run_id],
            )

    _logger.info("Production DB: %s", PROD_DB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
