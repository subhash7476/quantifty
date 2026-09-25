"""TS Basis Daily Combo — forward PAPER runner (orchestrator child).

Combo = recovery filter (basis_reverting=FALSE) + conviction (|z|>0.7),
quintile book, no TP exit, no sector cap — see
docs/reports/ts_basis/TS_BASIS_DAILY_COMBO_SPEC.md.

EOD-driven daemon, supervised by scripts/ops/orchestrator.py. It never refreshes
signals or facts itself — the EOD chain, `download_all_data.py` and the TS Basis
page's Refresh button own that pipeline. It trades each new formation once the
facts are complete (spec amendment A3):
  - the facts file has not changed for FACTS_SETTLE_S (publish replaces the
    file, then the recovery filter rewrites it — a moving mtime is mid-refresh);
  - at least one `basis_reverting = TRUE` exists (publish writes every flag
    FALSE; only the recovery filter sets TRUE, so zero means not applied yet).

Every cycle restores the hook from the store, the single source of truth, so a
cycle that fails part-way (a locked store, a failed write) leaves no half-advanced
state: the next cycle simply retries the same formations.

Deliberate deviations from ts_basis_daily_forward_runner.py:
  - signals_db_path=None: _load_fwd_names would silently drop every name at
    the live edge (fwd_ret_1m is NULL before the forward period elapses).
  - legs_by_quintile=True: legs are the stored Q5/Q1 after the combo filters
    (spec amendment A1), equal-weight per leg, instead of concentrated top-5.
  - min_abs_z=0.7, exclude_reverting=True: the combo filters.
  - State and P&L live in COMBO_DB (amendment A2), not production.duckdb.
  - No LoopDriver: the hook is date-driven and its fills are notional, so the
    runner calls it once per ready formation date instead of pumping bars.

Usage: python scripts/ts_basis_daily_combo_forward.py [--once] [--store PATH]
  --once        run a single cycle and exit (verification)
  --store PATH  state/P&L store (default COMBO_DB) — use a scratch path to verify
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import date, datetime, time as dt_time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.portfolio.carry_rebalancer import (
    CarryRebalancerHook, paper_gross_exposure_policy,
)
from core.execution.portfolio.combo_paper_store import ComboPaperStore, book_returns
from scripts.ops import pidfile

_logger = logging.getLogger("ts_basis_daily_combo_forward")

TS_FACTS_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_facts.duckdb"
TS_SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
COMBO_DIR = ROOT / "data" / "paper" / "ts_daily_combo"
COMBO_DB = COMBO_DIR / "combo_paper.duckdb"
STATUS_PATH = COMBO_DIR / "status.json"
LOCK_PATH = COMBO_DIR / "combo_runner.pid"

MIN_ABS_Z = 0.7
GROSS_EXPOSURE = 10_000_000.0
INITIAL_CAPITAL = 10_000_000.0
POLL_INTERVAL_S = 60
FACTS_SETTLE_S = 90


def facts_ready(facts_db: Path, settle_s: float = FACTS_SETTLE_S, now: float | None = None):
    """(ready, reason). Opens the store only once its mtime has settled."""
    if not facts_db.exists():
        return False, "facts store missing"
    age = (now if now is not None else time.time()) - facts_db.stat().st_mtime
    if age < settle_s:
        return False, f"facts changed {age:.0f}s ago — waiting for the refresh to settle"
    try:
        con = duckdb.connect(str(facts_db), read_only=True)
    except duckdb.IOException:
        return False, "facts store locked — refresh running"
    try:
        n_rev = con.execute(
            "SELECT COUNT(*) FROM carry_facts WHERE basis_reverting").fetchone()[0]
    finally:
        con.close()
    if n_rev == 0:
        return False, "recovery flag not applied yet"
    return True, "ready"


def pending_dates(facts_db: Path, after: date | None) -> list:
    """Formation dates to process: all after `after`; only the latest on a first start."""
    con = duckdb.connect(str(facts_db), read_only=True)
    try:
        if after is None:
            row = con.execute("SELECT MAX(formation_date) FROM carry_facts").fetchone()
            return [row[0]] if row[0] else []
        return [r[0] for r in con.execute(
            "SELECT DISTINCT formation_date FROM carry_facts WHERE formation_date > ? "
            "ORDER BY formation_date", [after]).fetchall()]
    finally:
        con.close()


class ComboRunner:
    """One store-backed forward book. `cycle()` processes every ready formation."""

    def __init__(self, store: ComboPaperStore, facts_db=TS_FACTS_DB, fut_db=FUT_DB,
                 sig_db=TS_SIG_DB, bhavcopy_db=FUT_DB, settle_s: float = FACTS_SETTLE_S):
        self.store = store
        self.facts_db = Path(facts_db)
        self.fut_db = fut_db
        self.sig_db = sig_db
        self.settle_s = settle_s
        self.last_reason = "starting"
        self._prev = {}
        self._done_mtime = None   # facts mtime of the last completed cycle
        clock = ReplayClock(start_time=datetime.combine(date.today(), dt_time.min))
        execution = ExecutionHandler(
            db_manager=DatabaseManager(data_root="data", read_only=True), clock=clock,
            broker=PaperBroker(clock=clock), config=ExecutionConfig(mode=ExecutionMode.PAPER),
            initial_capital=INITIAL_CAPITAL, load_db_state=False,
        )
        self.hook = CarryRebalancerHook(
            facts_db_path=str(self.facts_db), execution_handler=execution,
            gross_exposure_policy=paper_gross_exposure_policy,
            bhavcopy_db_path=str(bhavcopy_db) if bhavcopy_db else None,
            metrics_sink=self._sink, signals_db_path=None, max_positions_per_leg=None,
            min_abs_z=MIN_ABS_Z, exclude_reverting=True, legs_by_quintile=True,
        )

    def cycle(self) -> int:
        # An unchanged facts file needs no open: every reader competes with
        # publish_facts' os.replace, which fails on Windows while one is open.
        mtime = self.facts_db.stat().st_mtime if self.facts_db.exists() else None
        if mtime is not None and mtime == self._done_mtime:
            self.last_reason = "up to date"
            return 0
        ready, self.last_reason = facts_ready(self.facts_db, self.settle_s)
        if not ready:
            return 0
        state = self.store.last_state()
        after = state["formation_date"] if state else None
        self._prev = {"date": after,
                      "longs": state["longs"] if state else {},
                      "shorts": state["shorts"] if state else {}}
        self.hook.restore(self._prev["longs"], self._prev["shorts"], after)
        self.hook.reload_calendar()
        dates = pending_dates(self.facts_db, after)
        if state is None and dates:
            self.store.write_meta({
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "first_formation": dates[0], "git_commit": _git_commit(),
                "params": json.dumps({"min_abs_z": MIN_ABS_Z, "exclude_reverting": True,
                                      "legs_by_quintile": True, "exit": None,
                                      "gross": GROSS_EXPOSURE}),
            })
        n = 0
        for d in dates:
            if self.hook(datetime.combine(d, dt_time.min), None):
                n += 1
        self.last_reason = f"processed {n} formation(s)" if n else "up to date"
        self._done_mtime = mtime
        return n

    def _sink(self, fdate, deltas, held, metrics, cap_state):
        pnl = {"prev_date": self._prev["date"]}
        if self._prev["date"] is not None:
            pnl = book_returns(self._prev["date"], fdate, self._prev["longs"],
                               self._prev["shorts"], self.fut_db, self.sig_db)
        costs = metrics.fees_total + metrics.slippage_total
        pnl["net_pnl_fut"] = (pnl.get("fut_pnl") or 0.0) - costs
        trades = [{"underlying": d.underlying, "action": d.action,
                   "held_side": d.held_side, "held_cap": d.held_cap,
                   "target_side": d.target_side, "target_cap": d.target_cap}
                  for d in deltas if not d.suppressed]
        self.store.record(fdate, longs=held.longs, shorts=held.shorts, trades=trades,
                          costs={"traded_value": metrics.traded_value_total,
                                 "fees": metrics.fees_total,
                                 "slippage": metrics.slippage_total},
                          pnl=pnl)
        self._prev = {"date": fdate, "longs": dict(held.longs), "shorts": dict(held.shorts)}
        _logger.info("COMBO %s: %dL/%dS trades=%d fut_pnl=%s spot_pnl=%s costs=%.0f",
                     fdate, len(held.longs), len(held.shorts), len(trades),
                     _fmt(pnl.get("fut_pnl")), _fmt(pnl.get("spot_pnl")), costs)


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _fmt(x):
    return "n/a" if x is None else f"{x:.0f}"


def _write_status(state: str, reason: str, last_formation) -> None:
    payload = {"pid": os.getpid(), "last_heartbeat": datetime.now().isoformat(),
               "state": state, "reason": reason,
               "last_formation": str(last_formation) if last_formation else None}
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, STATUS_PATH)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--store", default=str(COMBO_DB))
    args = ap.parse_args(argv)
    live = Path(args.store) == COMBO_DB

    COMBO_DIR.mkdir(parents=True, exist_ok=True)
    if live and not pidfile.acquire_lock(LOCK_PATH):
        _logger.error("another combo runner holds %s", LOCK_PATH)
        return 1
    try:
        runner = ComboRunner(ComboPaperStore(args.store, capital=INITIAL_CAPITAL))
        _logger.info("TS Basis Daily COMBO forward PAPER: store=%s", args.store)
        while True:
            state, last = "ok", None
            try:
                runner.cycle()
                last = runner.store.last_state()
            except duckdb.Error as exc:
                # A locked or mid-write store; the next cycle restores from the store.
                state, runner.last_reason = "retrying", f"{type(exc).__name__}: {exc}"
                _logger.warning("cycle failed, retrying next poll: %s", exc)
            if live:
                _write_status(state, runner.last_reason, last and last["formation_date"])
            if args.once:
                _logger.info("single cycle: %s", runner.last_reason)
                return 0
            time.sleep(POLL_INTERVAL_S)
    finally:
        if live:
            pidfile.release_lock(LOCK_PATH)


if __name__ == "__main__":
    raise SystemExit(main())
