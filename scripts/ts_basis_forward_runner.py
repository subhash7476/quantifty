"""TS Basis shadow sleeve — forward PAPER runner.

Runs LoopDriver + DailyBhavcopyProvider forward from today, polling
for new bhavcopy data and executing rebalances on formation dates.
Reuses CarryRebalancerHook unchanged — ts_facts.duckdb stores z_ts
in the z_carry_neut column.

Shadow/observational only. Separate run_id in production.duckdb.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_logger = logging.getLogger("ts_basis_forward")

TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_facts.duckdb"
TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis" / "ts_signals.duckdb"
CARRY_SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
CARRY_FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
PROD_DB = ROOT / "data" / "signal_engine" / "carry" / "production.duckdb"

GROSS_EXPOSURE = 10_000_000.0
INITIAL_CAPITAL = 10_000_000.0
POLL_INTERVAL_S = 60

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


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_symbols():
    if not CARRY_FACTS_DB.exists():
        return []
    con = duckdb.connect(str(CARRY_FACTS_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT underlying FROM carry_facts ORDER BY underlying"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _refresh_ts_signals():
    """Re-run build_ts_signals.py to add new z_ts rows forward."""
    import subprocess
    build_script = ROOT / "scripts" / "signal_engine" / "ts_basis" / "build_ts_signals.py"
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0:
        _logger.error("build_ts_signals FAILED: %s", result.stderr)
        return False
    return True


def _refresh_ts_facts():
    """Re-run ts_basis/publish_facts.py to append new formations."""
    import subprocess
    pub_script = ROOT / "scripts" / "signal_engine" / "ts_basis" / "publish_facts.py"
    result = subprocess.run(
        [sys.executable, str(pub_script)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        _logger.error("publish_facts FAILED: %s", result.stderr)
        return False
    return True


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    dry_run = "--dry-run" in sys.argv
    today = date.today()
    commit = _git_commit()
    now_ts = datetime.utcnow().isoformat() + "Z"
    run_id = f"ts-basis-forward-{now_ts[:10]}"

    symbols = _load_symbols()
    if not symbols:
        _logger.error("No symbols in carry facts DB")
        return 1

    fac_con = duckdb.connect(str(TS_FACTS_DB), read_only=True)
    facts_max = fac_con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
    fac_con.close()
    start_date = min(today, facts_max or today)

    _logger.info("TS Basis forward: %d symbols, run=%s, start=%s", len(symbols), run_id, start_date)

    provider = DailyBhavcopyProvider(
        underlyings=symbols, bhavcopy_db=str(FUT_DB),
        start_date=start_date, end_date=None,
    )

    clock = ReplayClock(start_time=datetime.combine(today, dt_time.min))
    broker = PaperBroker(clock=clock)
    db_manager = DatabaseManager(data_root="data", read_only=True)
    execution = ExecutionHandler(
        db_manager=db_manager, clock=clock, broker=broker,
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        initial_capital=INITIAL_CAPITAL, load_db_state=False,
    )

    db = CarryMetricsDB(str(PROD_DB))
    db.write_run_metadata(
        run_id=run_id, git_commit=commit,
        generated_at=datetime.utcnow(),
        window_label="TS_FORWARD",
        window_lo=today, window_hi=date(2099, 12, 31),
        gross_exposure=GROSS_EXPOSURE,
        params_json=json.dumps({"sleeve": "ts_basis", "quintile_frac": 0.20}),
        determinism_hash=None, source="forward",
    )

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
        margin_util = ((lg + sg) * 0.20 / max(cap_state.current_equity, 1.0)) * 100

        db.write_rebalance_summary(
            run_id=run_id, formation_date=fdate,
            n_long=len(target.longs), n_short=len(target.shorts),
            traded_value=metrics.traded_value_total, turnover=to,
            fees_total=metrics.fees_total, slippage_total=metrics.slippage_total,
            fee_brokerage=metrics.fee_breakdown.get("brokerage", 0.0),
            fee_stt=metrics.fee_breakdown.get("stt", 0.0),
            fee_exchange_txn=metrics.fee_breakdown.get("exchange_txn", 0.0),
            fee_sebi_fee=metrics.fee_breakdown.get("sebi_fee", 0.0),
            fee_stamp_duty=metrics.fee_breakdown.get("stamp_duty", 0.0),
            fee_gst=metrics.fee_breakdown.get("gst", 0.0),
            top3_conc=top3, hhi=hhi, margin_util_pct=margin_util,
        )
        _logger.info("TS Basis rebalance: %s %dL/%dS fees=%.0f slip=%.0f",
                      fdate, len(target.longs), len(target.shorts),
                      metrics.fees_total, metrics.slippage_total)

    hook = CarryRebalancerHook(
        facts_db_path=str(TS_FACTS_DB), execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB), metrics_sink=sink,
        signals_db_path=str(TS_SIG_DB),
    )

    config = DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000)

    _logger.info("TS Basis forward PAPER started. Run ID: %s", run_id)

    # Initial signal/facts refresh to catch any data past the last build
    _logger.info("Refreshing TS Basis signals...")
    _refresh_ts_signals()
    _logger.info("Refreshing TS Basis facts...")
    _refresh_ts_facts()

    while True:
        driver = LoopDriver(
            config=config,
            clock=ReplayClock(start_time=datetime.combine(today, dt_time.min)),
            provider=provider, source=None, execution=execution,
            rebalance_hook=hook.__call__,
        )
        driver.run()

        if provider.refresh_if_exhausted():
            _logger.info("New bhavcopy data loaded. Refreshing TS signals + facts...")
            _refresh_ts_signals()
            _refresh_ts_facts()
            continue

        if dry_run:
            break
        time.sleep(POLL_INTERVAL_S)

    dhash = db.compute_determinism_hash(run_id)
    db._conn.execute(
        "UPDATE run_metadata SET determinism_hash=? WHERE run_id=?",
        [dhash, run_id],
    )
    db.close()
    _logger.info("TS Basis forward PAPER stopped. Hash: %s", dhash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
