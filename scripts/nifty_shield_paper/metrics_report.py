"""NiftyShield — risk-metrics report generator (E008 D, §7.4.2).

From the journal + the trade ledger, computes the Stage-2 risk-metrics report:
round-trip count, win rate, avg win/loss in R, profit factor, max drawdown (Rs,
%), peak gross exposure, peak margin utilization, signal->fill conversion with
per-gate rejection breakdown, and guard counters. PnL facts are included for the
owner's judgment — they are NOT pass/fail (§1.1).

R base — PINNED before the window (F2): R = structure realized PnL (Rs) ÷ the
source's declared `risk_r` (Rs), the datasheet §7 per-leg risk unit
(sl_distance × 75 × declared lots). R is therefore "Rs per declared-risk-Rs-unit",
computed at DECLARED lots, not the margin-clamped actual lots. When a structure's
`risk_r` is absent (a source/regression defect), its R is None and the R columns
are surfaced as vacuous (never silently 0.0).

Every P&L figure is NET of the ledger's fees — per-structure P&L, wins/losses,
R, profit factor, and the drawdown, which is taken from the net per-structure
equity curve (closed structures, journal order) on top of initial_capital. Gross
and fees are carried alongside (2026-09-25 audit F1: the ledger's fees were read
but never subtracted, and the drawdown came from a runtime metrics.json written
at startup, so the window printed +Rs 846 / DD 0% for a book that was -Rs 1,641
after fees with a -Rs 2,374 drawdown).

Inputs (injectable): journal JSONL, SQLite trading.db (trades = fills),
initial_capital.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.runtime.event_journal import EventType

from scripts.nifty_shield_paper.audit import GUARD_TYPES, is_structure_entry


@dataclass
class RiskMetricsReport:
    structures_attempted: int = 0
    structures_entered: int = 0
    structures_skipped: int = 0
    round_trips: int = 0                     # closed structures (1 RT = 1 structure)
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    # R columns are Optional: None when there is no computable R sample (no
    # win/loss, or every sample's risk_r was absent) — never a fabricated 0.0.
    avg_win_r: Optional[float] = None
    avg_loss_r: Optional[float] = None
    wins_with_r: int = 0
    losses_with_r: int = 0
    r_normalized_structures: int = 0          # closed structures with computable R
    profit_factor: Optional[float] = None
    max_drawdown_rs: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_gross_exposure: float = 0.0
    peak_margin_utilisation: float = 0.0
    signal_fill_conversion: float = 0.0
    rejections_by_reason: Dict[str, int] = field(default_factory=dict)
    guard_events: Dict[str, int] = field(default_factory=dict)
    total_realized_pnl: float = 0.0           # net of fees
    total_gross_pnl: float = 0.0
    total_fees: float = 0.0
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
) -> RiskMetricsReport:
    events = _read_journal(journal_path)
    report = RiskMetricsReport()

    # Plain dicts, not Counters: on Python 3.13 dataclasses.asdict() rebuilds a
    # dict subclass via `type(obj)((k, v) for k, v in obj.items())`, and the
    # Counter constructor then counts each (key, value) TUPLE as an element —
    # producing {(reason, 2): 1} and making json.dumps raise "keys must be
    # str ... not tuple" inside finalize_session_evidence (2026-08-19 incident).
    report.guard_events = dict(Counter(
        e["event_type"] for e in events if e["event_type"] in GUARD_TYPES))

    entries = [e for e in events if is_structure_entry(e)]
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

    # JSON-safe str keys only: a non-str reason (tuple, None, ...) would make
    # dataclasses.asdict -> json.dumps raise "keys must be str ... not tuple"
    # inside finalize_session_evidence and abort the whole session package.
    report.rejections_by_reason = dict(Counter(
        str(e["metadata"].get("reason")) for e in skips))

    traded = _read_trades(trades_db_path)
    total_pnl = total_gross_pnl = total_fees = 0.0
    for e in entries:
        md = e["metadata"]
        gid = md["group_id"]
        risk_r = (float(md["risk_r"]) if md.get("risk_r") is not None
                  else None)
        legs = md.get("leg_symbols", [])
        session = str(md.get("session") or "")
        # structure realized pnl + gross = sum over its legs' closed trades,
        # scoped to the structure's own session: the ledger keys by symbol,
        # and a symbol re-entered by a LATER structure must not leak its rows
        # into an earlier structure's PnL (2026-08-21: 24250PE was traded by
        # both the 08-20 orphan and the 08-21 straddle).
        gross_pnl = 0.0
        fees = 0.0
        gross = 0.0
        for sym in legs:
            for t in traded.get(sym, []):
                if session and not str(t["timestamp"]).startswith(session):
                    continue
                gross_pnl += float(t["pnl"] or 0.0)
                fees += float(t["fees"] or 0.0)
                gross += abs(float(t["price"] or 0.0)) * float(t["quantity"] or 0.0)
        pnl = gross_pnl - fees
        total_pnl += pnl
        total_gross_pnl += gross_pnl
        total_fees += fees
        closed = gid in closes
        report.per_structure.append({
            "group_id": gid,
            "session": md.get("session"),
            "structure": md.get("structure"),
            "closed": closed,
            "pnl_rs": round(pnl, 2),
            "gross_pnl_rs": round(gross_pnl, 2),
            "fees_rs": round(fees, 2),
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
    report.total_gross_pnl = total_gross_pnl
    report.total_fees = total_fees

    closed_structures = [p for p in report.per_structure if p["closed"]]
    wins = [p for p in closed_structures if p["pnl_rs"] > 0]
    losses = [p for p in closed_structures if p["pnl_rs"] < 0]
    report.wins = len(wins)
    report.losses = len(losses)
    report.win_rate = (len(wins) / len(closed_structures)
                       if closed_structures else 0.0)
    # R normalization (pinned base, F2): only structures with a declared risk_r
    # contribute; a missing risk_r is surfaced as vacuous (None), never 0.0.
    win_rs = [p["r"] for p in wins if p["r"] is not None]
    loss_rs = [p["r"] for p in losses if p["r"] is not None]
    report.wins_with_r = len(win_rs)
    report.losses_with_r = len(loss_rs)
    report.r_normalized_structures = (
        report.wins_with_r + report.losses_with_r)
    report.avg_win_r = (sum(win_rs) / len(win_rs) if win_rs else None)
    report.avg_loss_r = (sum(loss_rs) / len(loss_rs) if loss_rs else None)
    gross_win = sum(p["pnl_rs"] for p in wins)
    gross_loss = abs(sum(p["pnl_rs"] for p in losses))
    report.profit_factor = (
        gross_win / gross_loss if gross_loss > 0 else
        (float("inf") if gross_win > 0 else None))

    equity = peak = initial_capital
    for p in closed_structures:
        equity += p["pnl_rs"]
        peak = max(peak, equity)
        if peak - equity > report.max_drawdown_rs:
            report.max_drawdown_rs = peak - equity
            report.max_drawdown_pct = (peak - equity) / peak

    return report
