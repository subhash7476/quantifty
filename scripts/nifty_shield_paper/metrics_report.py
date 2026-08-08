"""NiftyShield — risk-metrics report generator (E007 D, §7.4.2).

From the journal + the trade ledger, computes the Stage-2 risk-metrics report:
round-trip count, win rate, avg win/loss in R, profit factor, max drawdown (Rs,
%), peak gross exposure, peak margin utilization, signal->fill conversion with
per-gate rejection breakdown, and guard counters. PnL facts are included for the
owner's judgment — they are NOT pass/fail (§1.1).

Inputs (injectable): journal JSONL, SQLite trading.db (trades = fills),
initial_capital, and an optional execution-metrics JSON (for the max-DD %).
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.runtime.event_journal import EventType

from scripts.nifty_shield_paper.audit import GUARD_TYPES


@dataclass
class RiskMetricsReport:
    structures_attempted: int = 0
    structures_entered: int = 0
    structures_skipped: int = 0
    round_trips: int = 0                     # closed structures (1 RT = 1 structure)
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    profit_factor: Optional[float] = None
    max_drawdown_pct: float = 0.0
    peak_gross_exposure: float = 0.0
    peak_margin_utilisation: float = 0.0
    signal_fill_conversion: float = 0.0
    rejections_by_reason: Dict[str, int] = field(default_factory=dict)
    guard_events: Dict[str, int] = field(default_factory=dict)
    total_realized_pnl: float = 0.0
    per_structure: List[dict] = field(default_factory=list)


def _read_journal(path: str) -> List[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def _read_trades(db_path: str) -> Dict[str, List[dict]]:
    """symbol -> list of trade dicts (entry fills carry exit_price=0)."""
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT symbol, side, quantity, entry_price, pnl, fees, timestamp "
            "FROM trades ORDER BY timestamp").fetchall()
        con.close()
    except sqlite3.Error:
        return {}
    out: Dict[str, List[dict]] = defaultdict(list)
    for sym, side, qty, price, pnl, fees, ts in rows:
        out[sym].append({"symbol": sym, "side": side, "quantity": qty,
                         "price": price, "pnl": pnl, "fees": fees,
                         "timestamp": ts})
    return out


def risk_metrics_report(
    journal_path: str,
    trades_db_path: str,
    *,
    initial_capital: float,
    metrics_json: Optional[str] = None,
) -> RiskMetricsReport:
    events = _read_journal(journal_path)
    report = RiskMetricsReport()

    report.guard_events = Counter(
        e["event_type"] for e in events if e["event_type"] in GUARD_TYPES)

    entries = [e for e in events
               if e["event_type"] == EventType.ENTRY_MARGIN.value]
    skips = [e for e in events
             if e["event_type"] == EventType.ENTRY_SKIPPED.value]
    closes = {e["metadata"]["group_id"]
              for e in events
              if e["event_type"] == EventType.STRUCTURE_CLOSE.value}

    report.structures_attempted = len(entries) + len(skips)
    report.structures_entered = len(entries)
    report.structures_skipped = len(skips)
    report.round_trips = len([e for e in entries
                              if e["metadata"]["group_id"] in closes])
    report.signal_fill_conversion = (
        report.structures_entered / report.structures_attempted
        if report.structures_attempted else 0.0)

    report.rejections_by_reason = Counter(
        e["metadata"].get("reason") for e in skips)

    traded = _read_trades(trades_db_path)
    total_pnl = 0.0
    for e in entries:
        md = e["metadata"]
        gid = md["group_id"]
        risk_r = float(md.get("risk_r", 0.0))
        legs = md.get("leg_symbols", [])
        # structure realized pnl + gross = sum over its legs' closed trades.
        pnl = 0.0
        gross = 0.0
        for sym in legs:
            for t in traded.get(sym, []):
                pnl += float(t["pnl"] or 0.0)
                gross += abs(float(t["price"] or 0.0)) * float(t["quantity"] or 0.0)
        total_pnl += pnl
        closed = gid in closes
        report.per_structure.append({
            "group_id": gid,
            "session": md.get("session"),
            "structure": md.get("structure"),
            "closed": closed,
            "pnl_rs": round(pnl, 2),
            "risk_r": risk_r,
            "r": round(pnl / risk_r, 3) if risk_r else None,
            "gross_exposure_rs": round(gross, 2),
            "margin_rs": md.get("margin_total"),
        })
        if closed:
            report.peak_gross_exposure = max(report.peak_gross_exposure, gross)
            margin = float(md.get("margin_total") or 0.0)
            report.peak_margin_utilisation = max(
                report.peak_margin_utilisation, margin / initial_capital
                if initial_capital else 0.0)

    report.total_realized_pnl = total_pnl

    closed_structures = [p for p in report.per_structure if p["closed"]]
    wins = [p for p in closed_structures if p["pnl_rs"] > 0]
    losses = [p for p in closed_structures if p["pnl_rs"] < 0]
    report.wins = len(wins)
    report.losses = len(losses)
    report.win_rate = (len(wins) / len(closed_structures)
                       if closed_structures else 0.0)
    report.avg_win_r = (sum(p["r"] or 0.0 for p in wins) / len(wins)
                        if wins else 0.0)
    report.avg_loss_r = (sum(p["r"] or 0.0 for p in losses) / len(losses)
                         if losses else 0.0)
    gross_win = sum(p["pnl_rs"] for p in wins)
    gross_loss = abs(sum(p["pnl_rs"] for p in losses))
    report.profit_factor = (
        gross_win / gross_loss if gross_loss > 0 else
        (float("inf") if gross_win > 0 else None))

    if metrics_json:
        try:
            with open(metrics_json, encoding="utf-8") as f:
                m = json.load(f)
            report.max_drawdown_pct = float(m.get("drawdown", 0.0))
        except (OSError, ValueError):
            pass

    return report
