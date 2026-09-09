"""NiftyShield — close any open structures at current chain marks (ops action).

Closes every open NiftyShield structure at the latest chain-cache marks,
through the real composition path: per-leg EXIT signals -> PaperBroker fills ->
entry-keyed ledger exit update -> STRUCTURE_CLOSE journaled (the same seam the
15:35 exit driver uses, minus the trigger).

Why this exists: the 2026-08-20 structure was orphaned by a restart (the exit
manager was blind to it) and carried into a new session — violating the F4
one-structure-per-session invariant and pricing the book every bar. Closing it
before the next session's entry window opens restores a clean flat book.

Run ONLY with no live session — an external close while the session runs would
diverge from its in-memory trackers:

    python scripts/ops/orchestrator.py stop
    python scripts/nifty_shield_paper/close_open_structures.py
    python scripts/ops/orchestrator.py start

Usage:
    python scripts/nifty_shield_paper/close_open_structures.py
    python scripts/nifty_shield_paper/close_open_structures.py --data-root data/nifty_shield --force
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.execution.options.nifty_shield_gates import nifty_shield_execution_config
from core.execution.options.nifty_shield_handler import NiftyShieldExecutionHandler
from core.execution.options.nifty_shield_marks import ChainSnapshotMarksSource
from core.execution.persistence.execution_store import ExecutionStore
from core.runtime.event_journal import RuntimeEventJournal

from scripts.nifty_shield_paper.recover_session import _check_live
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG

_IST = ZoneInfo("Asia/Kolkata")
CHAIN_DB = Path(__file__).resolve().parents[2] / "data" / "options" / "chain_cache.duckdb"


def close_open_structures(*, data_root: Path, chain_db: Path,
                          reason: str = "manual_close") -> List[dict]:
    """Close every open NiftyShield structure at current chain marks."""
    handler_mod.ExecutionStore = lambda *a, **k: ExecutionStore(
        str(data_root / "execution.db"))
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=data_root)
    now = datetime.now(_IST).replace(tzinfo=None)
    clock = ReplayClock(now)
    handler = NiftyShieldExecutionHandler(
        db_manager=dm,
        clock=clock,
        broker=PaperBroker(clock),
        config=nifty_shield_execution_config(initial_capital=1_000_000.0),
        metrics_path=str(data_root / "metrics.json"),
        load_db_state=True,
        initial_capital=1_000_000.0,
        journal=RuntimeEventJournal(str(data_root / "journal.jsonl")),
        marks_source=ChainSnapshotMarksSource(str(chain_db)),
        strategy_config=dict(DEFAULT_CONFIG),
    )

    groups = handler.open_nifty_shield_groups()
    if not groups:
        return [{"info": "no open structures to close"}]

    outcomes: List[dict] = []
    for gid in groups:
        group = handler.group_tracker.get_group(gid)
        if group is None:
            continue
        symbols = [leg.symbol for leg in group.legs]
        marks = handler.marks(symbols)
        missing = [s for s in symbols if s not in marks]
        if missing:
            outcomes.append({
                "group_id": str(gid), "status": "skipped",
                "detail": f"no marks for {missing} — cannot price the close"})
            continue
        before = {leg.symbol: handler.position_tracker.get_position(
            leg.symbol).side.value for leg in group.legs}
        handler.close_group(gid, reason, now, marks)
        after = {leg.symbol: handler.position_tracker.get_position(
            leg.symbol).side.value for leg in group.legs}
        outcomes.append({
            "group_id": str(gid), "status": "closed",
            "reason": reason, "bar_time": now.isoformat(),
            "marks": {s: round(m, 2) for s, m in marks.items()},
            "before": before, "after": after,
        })
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="close open NiftyShield structures at current chain marks")
    parser.add_argument("--data-root", default="data/nifty_shield")
    parser.add_argument("--chain-db", default=str(CHAIN_DB))
    parser.add_argument("--reason", default="manual_close")
    parser.add_argument("--live-age", type=int, default=10,
                        help="heartbeat freshness (min) that counts as live")
    parser.add_argument("--force", action="store_true",
                        help="run even if a session looks live")
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    if not data_root.exists():
        raise SystemExit(f"no data root at {data_root}")
    if not args.force:
        _check_live(data_root, args.live_age)

    outcomes = close_open_structures(data_root=Path(args.data_root).resolve(),
                                     chain_db=Path(args.chain_db).resolve(),
                                     reason=args.reason)
    print("close outcomes:")
    for o in outcomes:
        print(f"  {o}")
    if any(o.get("status") == "skipped" for o in outcomes):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
