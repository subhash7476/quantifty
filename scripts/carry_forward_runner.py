"""Carry forward PAPER runner — Piece 2 of forward-PAPER plan.

Runs LoopDriver + DailyBhavcopyProvider forward from today, polling for
new bhavcopy data and executing rebalances on formation dates. Same code
path as carry_paper_replay.py (parity-verified at +0.0 bp).

Usage:
  Forward-run:    python scripts/carry_forward_runner.py
  Dry-run (exit): python scripts/carry_forward_runner.py --dry-run

Architecture: Runner is Neutral. Same LoopDriver + hook + provider.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_logger = logging.getLogger("carry_forward")

FACTS_DB = ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
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


def _git_commit() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_symbols() -> list[str]:
    if not FACTS_DB.exists():
        return []
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT underlying FROM carry_facts ORDER BY underlying"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    dry_run = "--dry-run" in sys.argv
    today = date.today()
    commit = _git_commit()
    now_ts = datetime.utcnow().isoformat() + "Z"
    run_id = f"forward-{now_ts[:10]}"

    symbols = _load_symbols()
    if not symbols:
        _logger.error("No symbols in facts DB")
        return 1

    _logger.info("Carry forward: %d symbols, run=%s", len(symbols), run_id)

    provider = DailyBhavcopyProvider(
        underlyings=symbols,
        bhavcopy_db=str(FUT_DB),
        start_date=today,
        end_date=None,
    )

    clock = ReplayClock(start_time=datetime.combine(today, dt_time.min))
    broker = PaperBroker(clock=clock)
    db_manager = DatabaseManager(data_root="data", read_only=True)
    execution = ExecutionHandler(
        db_manager=db_manager, clock=clock, broker=broker,
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        initial_capital=INITIAL_CAPITAL,
        load_db_state=False,
    )

    db = CarryMetricsDB(str(PROD_DB))
    db.write_run_metadata(
        run_id=run_id, git_commit=commit,
        generated_at=datetime.utcnow(),
        window_label="FORWARD",
        window_lo=today, window_hi=date(2099, 12, 31),
        gross_exposure=GROSS_EXPOSURE,
        params_json=json.dumps({"quintile_frac": 0.20, "slippage_bp": 5}),
        determinism_hash=None, source="forward",
    )

    def sink(fdate, deltas, target, metrics, cap_state):
        executions = [d for d in deltas if not d.suppressed]
        all_caps = list(target.longs.values()) + list(target.shorts.values())
        total_cap = sum(all_caps)
        shares = sorted([c / total_cap for c in all_caps], reverse=True) if total_cap > 0 else []
        top3 = sum(shares[:3]) if len(shares) >= 3 else sum(shares)
        hhi = sum(s ** 2 for s in shares)
        long_gross = sum(target.longs.values())
        short_gross = sum(target.shorts.values())
        total_gross = long_gross + short_gross
        turnover = metrics.traded_value_total / max(total_gross, 1.0)
        margin_util = (total_gross * 0.20 / max(cap_state.current_equity, 1.0)) * 100

        alu = {d.underlying for d in executions}
        z_lookup = {}
        if alu:
            zc = duckdb.connect(str(FACTS_DB), read_only=True)
            ul = ", ".join(f"'{u}'" for u in alu)
            zc_rows = zc.execute(f"""
                SELECT underlying, z_carry_neut, quintile
                FROM carry_facts WHERE formation_date=? AND underlying IN ({ul})
            """, [fdate]).fetchall()
            zc.close()
            z_lookup = {r[0]: (r[1], r[2]) for r in zc_rows}

        positions = []
        for d in executions:
            z, q = z_lookup.get(d.underlying, (None, None))
            if q is None:
                q = 5 if d.target_side == "LONG" else (1 if d.target_side == "SHORT" else None)
            positions.append({
                "underlying": d.underlying, "target_side": d.target_side,
                "target_cap": d.target_cap,
                "z_carry_neut": float(z) if z is not None else None,
                "quintile": q, "action": d.action, "suppressed": d.suppressed,
            })

        db.write_rebalance_summary(
            run_id=run_id, formation_date=fdate,
            n_long=len(target.longs), n_short=len(target.shorts),
            traded_value=metrics.traded_value_total, turnover=turnover,
            fees_total=metrics.fees_total, slippage_total=metrics.slippage_total,
            fee_brokerage=metrics.fee_breakdown.get("brokerage", 0.0),
            fee_stt=metrics.fee_breakdown.get("stt", 0.0),
            fee_exchange_txn=metrics.fee_breakdown.get("exchange_txn", 0.0),
            fee_sebi_fee=metrics.fee_breakdown.get("sebi_fee", 0.0),
            fee_stamp_duty=metrics.fee_breakdown.get("stamp_duty", 0.0),
            fee_gst=metrics.fee_breakdown.get("gst", 0.0),
            top3_conc=top3, hhi=hhi, margin_util_pct=margin_util,
        )
        if positions:
            db.write_rebalance_positions(run_id, fdate, positions)

        _logger.info("Carry rebalance: %s %dL/%dS fees=%.0f slip=%.0f",
                      fdate, len(target.longs), len(target.shorts),
                      metrics.fees_total, metrics.slippage_total)

    hook = CarryRebalancerHook(
        facts_db_path=str(FACTS_DB),
        execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB),
        metrics_sink=sink,
        signals_db_path=str(SIG_DB),
    )

    config = DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000)

    _logger.info("Forward PAPER started. Run ID: %s", run_id)

    while True:
        driver = LoopDriver(
            config=config,
            clock=ReplayClock(start_time=datetime.combine(today, dt_time.min)),
            provider=provider,
            source=None,
            execution=execution,
            rebalance_hook=hook.__call__,
        )
        driver.run()

        if provider.refresh_if_exhausted():
            _logger.info("New bhavcopy data loaded.")
            continue

        _logger.debug("No new data. Sleeping %ds.", POLL_INTERVAL_S)
        if dry_run:
            break
        time.sleep(POLL_INTERVAL_S)

    dhash = db.compute_determinism_hash(run_id)
    db._conn.execute(
        "UPDATE run_metadata SET determinism_hash=? WHERE run_id=?",
        [dhash, run_id],
    )
    db.close()
    _logger.info("Forward PAPER stopped. Hash: %s", dhash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
