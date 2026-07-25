"""Carry PAPER replay — full LoopDriver path over TRAIN + HOLDOUT.

Drives the REAL production path (DailyBhavcopyProvider → LoopDriver →
CarryRebalancerHook → ExecutionHandler → PaperBroker) over the training
and holdout windows, capturing per-formation structural metrics through
the metrics_sink seam. Equity curve computed analytically post-run from
the captured book × signals.fwd_ret_1m (C3: never read from tracker).

Phase A.3 of CARRY_PRODUCTION_METRICS_IMPLEMENTATION_PROMPT.md.
Does NOT run SEALED (C1: one-shot protocol).
"""
from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("F:/Nifty")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))

_logger = logging.getLogger("carry_replay")

FACTS_DB = DATA_ROOT / "data" / "signal_engine" / "carry" / "facts.duckdb"
SIG_DB = DATA_ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = DATA_ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
PROD_DB = DATA_ROOT / "data" / "signal_engine" / "carry" / "production.duckdb"
SEALED_SNAPSHOT = DATA_ROOT / "docs" / "reports" / "CARRY_SEALED_SNAPSHOT.json"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

GROSS_EXPOSURE = 10_000_000.0
INITIAL_CAPITAL = 10_000_000.0
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25

from core.database.manager import DatabaseManager
from core.execution.handler import ExecutionHandler, ExecutionConfig, ExecutionMode
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver
from core.database.providers.daily_bhavcopy import DailyBhavcopyProvider
from core.execution.futures.futures_fees import futures_fees as _calc_fees
from core.execution.portfolio.carry_rebalancer import (
    CarryRebalancerHook, TargetBook, Delta, RebalanceMetrics,
    CapitalState, paper_gross_exposure_policy,
    SLIPPAGE_BP,
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


def _load_z_lookup(fdate: date, underlyings: list[str]) -> dict:
    """Load z_carry_neut + quintile per underlying from facts DB."""
    con = duckdb.connect(str(FACTS_DB), read_only=True)
    u_list = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, z_carry_neut, quintile
        FROM carry_facts
        WHERE formation_date = ? AND underlying IN ({u_list})
    """, [fdate]).fetchall()
    con.close()
    return {r[0]: (r[1], r[2]) for r in rows}


def _compute_concentration(target: TargetBook) -> dict:
    """Compute top-3 concentration and HHI from target book weights."""
    all_caps = list(target.longs.values()) + list(target.shorts.values())
    if not all_caps:
        return {"top3_conc": 0.0, "hhi": 0.0}
    total = sum(all_caps)
    if total == 0:
        return {"top3_conc": 0.0, "hhi": 0.0}
    shares = sorted([c / total for c in all_caps], reverse=True)
    top3 = sum(shares[:3]) if len(shares) >= 3 else sum(shares)
    hhi = sum(s ** 2 for s in shares)
    return {"top3_conc": top3, "hhi": hhi}


def _make_metrics_sink(captured: list, facts_db_path: str):
    def sink(fdate, deltas, target, metrics, cap_state):
        executions = [d for d in deltas if not d.suppressed]
        all_underlyings = {d.underlying for d in executions}
        z_lookup = _load_z_lookup(fdate, list(all_underlyings))

        positions = []
        for d in executions:
            z, quintile = z_lookup.get(d.underlying, (None, None))
            if quintile is None:
                quintile = 5 if d.target_side == "LONG" else (1 if d.target_side == "SHORT" else None)
            positions.append({
                "underlying": d.underlying,
                "target_side": d.target_side,
                "target_cap": d.target_cap,
                "z_carry_neut": float(z) if z is not None else None,
                "quintile": quintile,
                "action": d.action,
                "suppressed": d.suppressed,
            })

        conc = _compute_concentration(target)
        long_gross = sum(target.longs.values())
        short_gross = sum(target.shorts.values())
        total_gross = long_gross + short_gross
        turnover = metrics.traded_value_total / max(total_gross, 1.0)
        margin_util = (total_gross * 0.20 / max(cap_state.current_equity, 1.0)) * 100

        captured.append({
            "formation_date": fdate,
            "n_long": len(target.longs),
            "n_short": len(target.shorts),
            "traded_value": metrics.traded_value_total,
            "turnover": turnover,
            "fees_total": metrics.fees_total,
            "slippage_total": metrics.slippage_total,
            "fee_brokerage": metrics.fee_breakdown.get("brokerage", 0.0),
            "fee_stt": metrics.fee_breakdown.get("stt", 0.0),
            "fee_exchange_txn": metrics.fee_breakdown.get("exchange_txn", 0.0),
            "fee_sebi_fee": metrics.fee_breakdown.get("sebi_fee", 0.0),
            "fee_stamp_duty": metrics.fee_breakdown.get("stamp_duty", 0.0),
            "fee_gst": metrics.fee_breakdown.get("gst", 0.0),
            "top3_conc": conc["top3_conc"],
            "hhi": conc["hhi"],
            "margin_util_pct": margin_util,
            "target": target,
            "positions": positions,
        })
    return sink


def _run_window(label: str, lo: date, hi: date) -> list[dict]:
    _logger.info("Replay %s: %s → %s", label, lo, hi)

    con = duckdb.connect(str(FUT_DB), read_only=True)
    symbols = [r[0] for r in con.execute(f"""
        SELECT DISTINCT underlying
        FROM futures_bhavcopy
        WHERE trade_date >= ? AND trade_date <= ? AND inst_type = 'FUTSTK'
        ORDER BY underlying
    """, [lo, hi]).fetchall()]
    con.close()

    if not symbols:
        _logger.error("No symbols for %s", label)
        return []

    provider = DailyBhavcopyProvider(
        underlyings=symbols,
        bhavcopy_db=str(FUT_DB),
        start_date=lo,
        end_date=hi,
    )

    broker = PaperBroker(clock=ReplayClock(start_time=datetime.combine(lo, time.min)))
    db_manager = DatabaseManager(data_root="data", read_only=True)
    execution = ExecutionHandler(
        db_manager=db_manager,
        clock=ReplayClock(start_time=datetime.combine(lo, time.min)),
        broker=broker,
        config=ExecutionConfig(mode=ExecutionMode.PAPER),
        initial_capital=INITIAL_CAPITAL,
        load_db_state=False,
    )

    captured: list[dict] = []
    sink_fn = _make_metrics_sink(captured, str(FACTS_DB))

    hook = CarryRebalancerHook(
        facts_db_path=str(FACTS_DB),
        execution_handler=execution,
        gross_exposure_policy=paper_gross_exposure_policy,
        bhavcopy_db_path=str(FUT_DB),
        metrics_sink=sink_fn,
        signals_db_path=str(SIG_DB),
    )

    driver = LoopDriver(
        config=DriverConfig(mode=Mode.REPLAY, symbols=symbols, max_bars=500_000),
        clock=ReplayClock(start_time=datetime.combine(lo, time.min)),
        provider=provider,
        source=None,
        execution=execution,
        rebalance_hook=hook.__call__,
    )

    driver.run()
    _logger.info("Replay done: %d rebalances captured", len(captured))
    return captured


def _compute_equity_curve(captured: list[dict]) -> list[dict]:
    """Compute cumulative net return and drawdown analytically.

    Uses signals.fwd_ret_1m to apply returns to each captured target book,
    then subtracts fees+slippage. C3: never reads from position tracker.
    """
    if len(captured) < 2:
        return []

    con = duckdb.connect(str(SIG_DB), read_only=True)

    fdates = sorted(r["formation_date"] for r in captured)
    fdate_set = set(fdates)

    rows = con.execute("""
        SELECT formation_date, underlying, fwd_ret_1m
        FROM signals
        WHERE formation_date IN ({dates})
          AND fwd_ret_1m IS NOT NULL
          AND liquid = TRUE
    """.format(dates=", ".join(f"DATE '{d}'" for d in fdate_set))).fetchall()
    con.close()

    fwd_by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for fdate, u, fr in rows:
        fwd_by_date[fdate][u] = float(fr)

    equity = []
    cum_net = 0.0
    peak = 0.0
    prev_captured = None

    for i, cap in enumerate(captured):
        fdate = cap["formation_date"]
        if i == 0:
            equity.append({
                "formation_date": fdate,
                "cum_net_ret": 0.0,
                "drawdown_pct": 0.0,
            })
            peak = 1.0
            cum_net = 1.0
            prev_target = cap["target"]
            continue

        prev_fwd = fwd_by_date.get(captured[i - 1]["formation_date"], {})
        curr_fees = cap["fees_total"] + cap["slippage_total"]

        long_gross = sum(prev_target.longs.values())
        short_gross = sum(prev_target.shorts.values())

        gl = sum(c * prev_fwd.get(u, 0.0) for u, c in prev_target.longs.items())
        gs = sum(c * prev_fwd.get(u, 0.0) for u, c in prev_target.shorts.items())
        gross_ret = (gl / max(long_gross, 1e-6) - gs / max(short_gross, 1e-6))
        net_ret = gross_ret - curr_fees / GROSS_EXPOSURE

        cum_net *= (1.0 + net_ret)
        peak = max(peak, cum_net)
        dd_pct = (cum_net - peak) / peak if peak > 0 else 0.0

        equity.append({
            "formation_date": fdate,
            "cum_net_ret": float(cum_net - 1.0),
            "drawdown_pct": float(dd_pct),
        })
        prev_target = cap["target"]

    return equity


def _derive_net_series(captured: list[dict]) -> Tuple[list[float], float]:
    """Derive monthly net returns from captured books × fwd_ret_1m."""
    con = duckdb.connect(str(SIG_DB), read_only=True)
    fdate_set = {r["formation_date"] for r in captured}
    rows = con.execute("""
        SELECT formation_date, underlying, fwd_ret_1m
        FROM signals
        WHERE formation_date IN ({dates})
          AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
    """.format(dates=", ".join(f"DATE '{d}'" for d in fdate_set))).fetchall()
    con.close()

    fwd_by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for fdate, u, fr in rows:
        fwd_by_date[fdate][u] = float(fr)

    net_returns = []
    for i in range(1, len(captured)):
        prev = captured[i - 1]
        curr = captured[i]
        target = prev["target"]
        fees = curr["fees_total"] + curr["slippage_total"]
        fwd = fwd_by_date.get(prev["formation_date"], {})

        lg = sum(target.longs.values())
        sg = sum(target.shorts.values())
        gl = sum(v * fwd.get(u, 0.0) for u, v in target.longs.items())
        gs = sum(v * fwd.get(u, 0.0) for u, v in target.shorts.items())
        gr = gl / max(lg, 1e-6) - gs / max(sg, 1e-6)
        nr = gr - fees / GROSS_EXPOSURE
        net_returns.append(nr)

    gross_arr = [r + (captured[i]["fees_total"] + captured[i]["slippage_total"]) / GROSS_EXPOSURE
                 for i, r in enumerate(net_returns, 1)]
    net_arr = net_returns

    months = len(net_arr)
    ann_net = float((np.prod([1.0 + r for r in net_arr]) ** (12.0 / months) - 1)) if months > 0 else 0.0

    return net_arr, ann_net


def _ingest_sealed_snapshot(db: CarryMetricsDB, commit: str, now_ts: str):
    if not SEALED_SNAPSHOT.exists():
        _logger.warning("SEALED snapshot not found: %s", SEALED_SNAPSHOT)
        return

    with open(SEALED_SNAPSHOT) as f:
        snap = json.load(f)

    window = snap.get("window", {})
    results = snap.get("results", {})

    run_id = f"sealed-snapshot-{now_ts[:10]}"
    db.write_run_metadata(
        run_id=run_id,
        git_commit=snap.get("commit", commit),
        generated_at=datetime.utcnow(),
        window_label="SEALED",
        window_lo=date.fromisoformat(window.get("lo", "2023-01-01")),
        window_hi=date.fromisoformat(window.get("hi", "2026-07-20")),
        gross_exposure=10_000_000.0,
        params_json=json.dumps(snap.get("fee_model", {})),
        determinism_hash=None,
        source="snapshot",
    )

    portfolio = results.get("portfolio", {})
    ic_data = results.get("ic", {})
    db.write_rebalance_summary(
        run_id=run_id,
        formation_date=date.fromisoformat(window.get("lo", "2023-01-01")),
        n_long=0,
        n_short=0,
        traded_value=0.0,
        turnover=portfolio.get("avg_turnover", 0.0),
        fees_total=portfolio.get("total_fees", 0.0),
        slippage_total=portfolio.get("total_slippage", 0.0),
        fee_brokerage=portfolio.get("fee_breakdown", {}).get("brokerage", 0.0),
        fee_stt=portfolio.get("fee_breakdown", {}).get("stt", 0.0),
        fee_exchange_txn=portfolio.get("fee_breakdown", {}).get("exchange_txn", 0.0),
        fee_sebi_fee=portfolio.get("fee_breakdown", {}).get("sebi_fee", 0.0),
        fee_stamp_duty=portfolio.get("fee_breakdown", {}).get("stamp_duty", 0.0),
        fee_gst=portfolio.get("fee_breakdown", {}).get("gst", 0.0),
        top3_conc=0.0,
        hhi=0.0,
        margin_util_pct=0.0,
    )

    ann_net = portfolio.get("ann_net", 0.0)
    months = portfolio.get("return_periods", 42)
    equity_rows = [{
        "formation_date": date.fromisoformat(window.get("lo", "2023-01-01")),
        "cum_net_ret": 0.0,
        "drawdown_pct": 0.0,
    }, {
        "formation_date": date.fromisoformat(window.get("hi", "2026-07-20")),
        "cum_net_ret": ann_net,
        "drawdown_pct": 0.0,
    }]
    db.write_equity_curve(run_id, equity_rows)

    _logger.info("SEALED ingested: ann_net=%+.2f%%, IC=%.4f, gate=%s",
                 ann_net * 100, ic_data.get("mean", 0),
                 "PASS" if results.get("gate_pass") else "FAIL")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    commit = _git_commit()
    now_ts = datetime.utcnow().isoformat() + "Z"

    PROD_DB.parent.mkdir(parents=True, exist_ok=True)

    with CarryMetricsDB(str(PROD_DB)) as db:
        all_captured = {}

        for label, (lo, hi) in WINDOWS.items():
            captured = _run_window(label, lo, hi)
            all_captured[label] = captured

            if not captured:
                _logger.warning("No rebalances captured for %s", label)
                continue

            run_id = f"replay-{label.lower()}-{now_ts[:10]}"
            db.write_run_metadata(
                run_id=run_id,
                git_commit=commit,
                generated_at=datetime.utcnow(),
                window_label=label,
                window_lo=lo,
                window_hi=hi,
                gross_exposure=GROSS_EXPOSURE,
                params_json=json.dumps({
                    "quintile_frac": 0.20,
                    "adv_cap_frac": ADV_CAP_FRAC,
                    "band_sigma": BAND_SIGMA,
                    "slippage_bp": SLIPPAGE_BP,
                    "gross_exposure": GROSS_EXPOSURE,
                }),
                determinism_hash=None,
                source="replay",
            )

            for cap in captured:
                db.write_rebalance_summary(
                    run_id=run_id,
                    formation_date=cap["formation_date"],
                    n_long=cap["n_long"],
                    n_short=cap["n_short"],
                    traded_value=cap["traded_value"],
                    turnover=cap["turnover"],
                    fees_total=cap["fees_total"],
                    slippage_total=cap["slippage_total"],
                    fee_brokerage=cap["fee_brokerage"],
                    fee_stt=cap["fee_stt"],
                    fee_exchange_txn=cap["fee_exchange_txn"],
                    fee_sebi_fee=cap["fee_sebi_fee"],
                    fee_stamp_duty=cap["fee_stamp_duty"],
                    fee_gst=cap["fee_gst"],
                    top3_conc=cap["top3_conc"],
                    hhi=cap["hhi"],
                    margin_util_pct=cap["margin_util_pct"],
                )
                if cap["positions"]:
                    db.write_rebalance_positions(
                        run_id, cap["formation_date"], cap["positions"]
                    )

            equity = _compute_equity_curve(captured)
            if equity:
                db.write_equity_curve(run_id, equity)

            dhash = db.compute_determinism_hash(run_id)
            db._conn.execute(
                "UPDATE run_metadata SET determinism_hash=? WHERE run_id=?",
                [dhash, run_id],
            )
            _logger.info("%s determinism_hash: %s", label, dhash)

            net_series, ann_net = _derive_net_series(captured)
            _logger.info("%s ann_net: %+.4f%% (%d periods)", label, ann_net * 100, len(net_series))

        _ingest_sealed_snapshot(db, commit, now_ts)

    _logger.info("Production DB: %s", PROD_DB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
