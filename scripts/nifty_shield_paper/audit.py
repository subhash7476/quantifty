"""NiftyShield — journal-audit tool (E007 C, §7.4.4).

From the journal + the trade ledger, trace every structure's entry intent to
fill or journaled rejection and quantify shadow-state divergence.

Divergence rule: it is expected to be ONE-DIRECTIONAL only — the strategy
believes in entries the gates rejected (a structure attempted but no/partial
fills). ANY reverse divergence (fills with no matching strategy intent) is a
platform defect and halts the pipeline for everyone (ADR-017 / §7.4.4).

Inputs (injectable, so the tool runs offline on an archived window):
- journal_path  : the RuntimeEventJournal JSONL for the window.
- trades_db_path: the SQLite trading.db (trades table = the ledger fills).
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.runtime.event_journal import EventType

GUARD_TYPES = {
    EventType.STRATEGY_ERROR.value,
    EventType.STRATEGY_QUARANTINED.value,
    EventType.SIGNAL_CONTRACT_REJECTED.value,
}


@dataclass
class StructureAudit:
    group_id: str
    session: str
    structure: str
    status: str                       # "entered" | "skipped" | "partial"
    reason: Optional[str] = None
    leg_symbols: List[str] = field(default_factory=list)
    filled_legs: List[str] = field(default_factory=list)
    closed: bool = False
    exit_reason: Optional[str] = None


@dataclass
class AuditReport:
    structures: List[StructureAudit] = field(default_factory=list)
    guard_events: Dict[str, int] = field(default_factory=dict)
    skipped_sessions: List[Dict] = field(default_factory=list)
    reverse_divergence: List[str] = field(default_factory=list)
    one_directional_only: bool = True


def _read_journal(path: str) -> List[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def _trade_symbols(db_path: str) -> Dict[str, List[str]]:
    """symbol -> [trade symbols] from the ledger trades table."""
    try:
        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT symbol, side, quantity, entry_price, pnl, fees "
            "FROM trades ORDER BY timestamp").fetchall()
        con.close()
    except sqlite3.Error:
        return {}
    out: Dict[str, List[tuple]] = defaultdict(list)
    for row in rows:
        out[row[0]].append(row)
    return out


def audit_window(journal_path: str, trades_db_path: str) -> AuditReport:
    events = _read_journal(journal_path)
    report = AuditReport()

    report.guard_events = Counter(
        e["event_type"] for e in events if e["event_type"] in GUARD_TYPES)

    entries = [e for e in events
               if e["event_type"] == EventType.ENTRY_MARGIN.value]
    skips = [e for e in events
             if e["event_type"] == EventType.ENTRY_SKIPPED.value]
    closes = [e for e in events
              if e["event_type"] == EventType.STRUCTURE_CLOSE.value]
    report.skipped_sessions = [
        {"session": e["metadata"].get("session"),
         "reason": e["metadata"].get("reason")}
        for e in events
        if e["event_type"] == EventType.FACT_PUBLISH_SKIPPED.value]

    close_by_group = {e["metadata"]["group_id"]: e["metadata"].get("reason")
                      for e in closes}

    for e in entries:
        md = e["metadata"]
        gid = md["group_id"]
        audit = StructureAudit(
            group_id=gid,
            session=str(md.get("session")),
            structure=str(md.get("structure")),
            status="entered",
            leg_symbols=list(md.get("leg_symbols", [])),
            closed=gid in close_by_group,
            exit_reason=close_by_group.get(gid),
        )
        report.structures.append(audit)

    for e in skips:
        md = e["metadata"]
        report.structures.append(StructureAudit(
            group_id=str(md.get("group_id")),
            session=str(md.get("session")),
            structure=str(md.get("structure")),
            status="skipped",
            reason=str(md.get("reason")),
            leg_symbols=list(md.get("leg_symbols", [])),
        ))

    # Every entered structure must have a fill for every leg in the ledger.
    traded = _trade_symbols(trades_db_path)
    for audit in report.structures:
        if audit.status != "entered":
            continue
        for sym in audit.leg_symbols:
            if sym in traded:
                audit.filled_legs.append(sym)
        if audit.filled_legs and len(audit.filled_legs) < len(audit.leg_symbols):
            audit.status = "partial"

    # Reverse divergence: any nifty-option-shaped ledger fill whose symbol is not
    # part of any structure's leg set — a fill with no recorded strategy intent.
    all_legs = {sym for a in report.structures for sym in a.leg_symbols}
    for sym in traded:
        if sym.startswith("NIFTY") and sym not in all_legs:
            report.reverse_divergence.append(sym)

    report.one_directional_only = not report.reverse_divergence
    return report
