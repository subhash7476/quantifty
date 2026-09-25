"""TS Basis Daily Combo — forward PAPER runner.

Combo = recovery filter (basis_reverting=FALSE) + conviction (|z|>0.7),
quintile book, no TP exit, no sector cap — see
docs/reports/ts_basis/TS_BASIS_DAILY_COMBO_SPEC.md.

Deliberate deviations from ts_basis_daily_forward_runner.py:
  - signals_db_path=None: _load_fwd_names would silently drop every name at
    the live edge (fwd_ret_1m is NULL before the forward period elapses).
  - legs_by_quintile=True: legs are the stored Q5/Q1 after the combo filters
    (spec amendment A1), equal-weight per leg, instead of concentrated top-5.
  - min_abs_z=0.7, exclude_reverting=True: the combo filters.
  - State and P&L live in their own store (COMBO_DB, spec amendment A2), not
    production.duckdb: the run resumes from its last persisted book, so a
    restart continues one forward record, and the Flask page can read it.
  - A failed signals/facts refresh blocks trading for that cycle.

Usage: python scripts/ts_basis_daily_combo_forward.py [--dry-run] [--no-refresh] [--store PATH]
  --no-refresh  trade the facts already published (no signal/facts rebuild)
  --store PATH  state/P&L store (default COMBO_DB) — use a scratch path to verify
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_logger = logging.getLogger("ts_basis_daily_combo_forward")

TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
COMBO_DB = ROOT / "data" / "paper" / "ts_daily_combo" / "combo_paper.duckdb"

MIN_ABS_Z = 0.7

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
from core.execution.portfolio.combo_paper_store import ComboPaperStore, book_returns


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_symbols():
    if not TS_FACTS_DB.exists():
        return []
    con = duckdb.connect(str(TS_FACTS_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT underlying FROM carry_facts ORDER BY underlying"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _refresh_signals():
    import subprocess
    build_script = ROOT / "scripts" / "signal_engine" / "ts_basis_daily" / "build_ts_basis_daily.py"
    result = subprocess.run(
        [sys.executable, str(build_script), "--incremental"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0:
        _logger.error("build_ts_basis_daily FAILED: %s", result.stderr)
        return False
    return True


def _refresh_facts():
    import subprocess
    daily = ROOT / "scripts" / "signal_engine" / "ts_basis_daily"
    for script in (daily / "publish_facts.py", daily / "apply_recovery_filter.py"):
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        _logger.info("%s: %s", script.name, result.stdout.strip())
        if result.returncode != 0:
            _logger.error("%s FAILED: %s", script.name, result.stderr)
            return False
    return True


def _refresh(hook, enabled=True) -> bool:
    ok = not enabled or (_refresh_signals() and _refresh_facts())
    if ok:
        hook.reload_calendar()
    else:
        _logger.error("Refresh failed — not trading this cycle; retrying next poll")
    return ok


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--store", default=str(COMBO_DB))
    args = ap.parse_args()
    dry_run, do_refresh = args.dry_run, not args.no_refresh
    today = date.today()

    symbols = _load_symbols()
    if not symbols:
        _logger.error("No symbols in TS facts DB")
        return 1

    store = ComboPaperStore(args.store, capital=INITIAL_CAPITAL)
    state = store.last_state()
    if state is None:
        fac_con = duckdb.connect(str(TS_FACTS_DB), read_only=True)
        facts_max = fac_con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()[0]
        fac_con.close()
        start_date = min(today, facts_max or today)
        store.write_meta({
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "first_formation": start_date, "git_commit": _git_commit(),
            "params": json.dumps({"min_abs_z": MIN_ABS_Z, "exclude_reverting": True,
                                  "legs_by_quintile": True, "exit": None,
                                  "gross": GROSS_EXPOSURE}),
        })
    else:
        start_date = state["formation_date"]
    _logger.info("TS Basis Daily COMBO forward: %d symbols, %s from %s",
                 len(symbols), "resuming" if state else "starting", start_date)

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

    prev = {"date": state["formation_date"] if state else None,
            "longs": state["longs"] if state else {},
            "shorts": state["shorts"] if state else {},
            "cum": state["cum_net_pnl_fut"] if state else 0.0}

    def sink(fdate, deltas, held, metrics, cap_state):
        pnl = {"prev_date": prev["date"]}
        if prev["date"] is not None:
            pnl = book_returns(prev["date"], fdate, prev["longs"], prev["shorts"],
                               FUT_DB, TS_SIG_DB)
        costs = metrics.fees_total + metrics.slippage_total
        pnl["net_pnl_fut"] = (pnl.get("fut_pnl") or 0.0) - costs
        trades = [{"underlying": d.underlying, "action": d.action,
                   "held_side": d.held_side, "held_cap": d.held_cap,
                   "target_side": d.target_side, "target_cap": d.target_cap}
                  for d in deltas if not d.suppressed]
        store.record(fdate, longs=held.longs, shorts=held.shorts, trades=trades,
                     costs={"traded_value": metrics.traded_value_total,
                            "fees": metrics.fees_total,
                            "slippage": metrics.slippage_total},
                     pnl=pnl)
        prev.update(date=fdate, longs=dict(held.longs), shorts=dict(held.shorts),
                    cum=prev["cum"] + pnl["net_pnl_fut"])
        _logger.info("COMBO %s: %dL/%dS trades=%d fut_pnl=%s spot_pnl=%s costs=%.0f cum_net=%.0f",
                     fdate, len(held.longs), len(held.shorts), len(trades),
                     _fmt(pnl.get("fut_pnl")), _fmt(pnl.get("spot_pnl")), costs, prev["cum"])

    hook = CarryRebalancerHook(
        facts_db_path=str(TS_FACTS_DB), execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB), metrics_sink=sink,
        signals_db_path=None, max_positions_per_leg=None,
        min_abs_z=MIN_ABS_Z, exclude_reverting=True,
        legs_by_quintile=True,
    )
    if state is not None:
        hook.restore(state["longs"], state["shorts"], state["formation_date"])

    config = DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000)
    ready = _refresh(hook, do_refresh)

    while True:
        if ready:
            LoopDriver(
                config=config,
                clock=ReplayClock(start_time=datetime.combine(today, dt_time.min)),
                provider=provider, source=None, execution=execution,
                rebalance_hook=hook.__call__,
            ).run()
            if provider.refresh_if_exhausted():
                _logger.info("New bhavcopy data loaded. Refreshing TS signals + facts...")
                ready = _refresh(hook, do_refresh)
                continue
        if dry_run:
            break
        time.sleep(POLL_INTERVAL_S)
        if not ready:
            ready = _refresh(hook, do_refresh)

    _logger.info("TS Basis Daily COMBO forward PAPER stopped.")
    return 0


def _fmt(x):
    return "n/a" if x is None else f"{x:.0f}"


if __name__ == "__main__":
    raise SystemExit(main())
