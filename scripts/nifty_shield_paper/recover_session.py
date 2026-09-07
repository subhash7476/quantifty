"""NiftyShield — per-session evidence recovery after a crashed finalize.

Incident 2026-08-19: `finalize_session_evidence` crashed at the metrics write,
so the session package was left with only telemetry.json + audit.json (the
steps before the crash). metrics.json, session_summary.json and the recorder
package (marks.jsonl, signals.jsonl, bars.duckdb, facts.duckdb, meta.json)
were never written, and the trades ledger's exit rows were never updated
(exit_price=0.0, pnl=0.0) — because the handler passed the exit fill id to
`update_trade_exit` while the trades table is keyed by the entry fill id.

This tool reconstructs what the surviving evidence supports, mirroring the
FIXED pipeline exactly:

- repairs the trades ledger rows for one session from the canonical fills
  (`execution.db`) using the fixed handler's semantics: per-leg GROSS realized
  pnl (position-tracker formula, multiplier 1.0) and fees accumulated across
  the round trip (`fees = fees + exit_fee`),
- rewrites `metrics.json` + `session_summary.json` from the journal + ledger
  (with `metrics_json=None`: the root metrics.json has since been overwritten
  by later sessions, so max_drawdown is left 0.0 and that is disclosed),
- copies the live fact store into the package,
- writes an honest `meta.json` disclosing the irrecoverable artifacts (driver
  bars / marks / signals lived in the crashed process's memory and are gone).

It never touches journal.jsonl and never regenerates telemetry.json/audit.json
(the crashed run already wrote valid ones — preserving them is the point).

Safety: mutates the shared trade ledger, so it refuses to run while a session
is live (heartbeat fresher than --live-age) unless --force.

Usage:
    python scripts/nifty_shield_paper/recover_session.py --date 2026-08-19
    python scripts/nifty_shield_paper/recover_session.py --date 2026-08-19 --force
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.nifty_shield_paper.audit import audit_window, is_structure_entry
from scripts.nifty_shield_paper.metrics_report import risk_metrics_report
from scripts.nifty_shield_paper.session import _jsonable


def _now_naive() -> datetime:
    return datetime.now()


def _check_live(data_root: Path, live_age: int) -> None:
    heartbeat = data_root / "heartbeat.json"
    if not heartbeat.exists():
        return
    try:
        ts = json.loads(heartbeat.read_text(encoding="utf-8"))["timestamp"]
        age = _now_naive() - datetime.fromisoformat(ts)
    except (OSError, ValueError, KeyError):
        return
    if age < timedelta(minutes=live_age):
        raise SystemExit(
            f"refusing: heartbeat {age.total_seconds():.0f}s old — a session "
            f"looks live; re-run after it finalizes (or --force)")


def _open_trade_rows(db_path: Path, session: str) -> List[tuple]:
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute(
            "SELECT trade_id, symbol, side, quantity, entry_price, fees, timestamp "
            "FROM trades WHERE timestamp LIKE ? AND exit_price = 0.0 "
            "ORDER BY timestamp", [f"{session}%"]).fetchall()
    finally:
        con.close()


def _backfill_group_ids(data_root: Path, session: str) -> List[dict]:
    """Stamp group_id on execution.db orders whose entries predate the
    group_id order-stamping fix (2026-08-20 incident, part 2): the restore
    path rebuilds the OrderGroup registry from orders carrying group_id, and
    the journal's ENTRY_MARGIN events map leg symbols -> group_id. Idempotent:
    only NULL group_id rows are touched."""
    journal_path = data_root / "journal.jsonl"
    db_path = data_root / "execution.db"
    if not journal_path.exists():
        return [{"error": f"no journal at {journal_path}"}]
    entries = []
    for line in open(journal_path, encoding="utf-8"):
        if not line.strip():
            continue
        e = json.loads(line)
        if (is_structure_entry(e)
                and str(e.get("metadata", {}).get("session")) == session):
            md = e["metadata"]
            entries.append((str(md["group_id"]), list(md.get("leg_symbols", []))))
    if not entries:
        return [{"info": "no ENTRY_MARGIN events for the session"}]
    sym_to_gid: Dict[str, str] = {}
    for gid, legs in entries:
        for sym in legs:
            if sym in sym_to_gid and sym_to_gid[sym] != gid:
                return [{"error": f"ambiguous group_id for {sym}"}]
            sym_to_gid[sym] = gid
    if not db_path.exists():
        return [{"error": f"no execution.db at {db_path}"}]
    con = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(orders)")}
        if "group_id" not in cols:
            con.execute("ALTER TABLE orders ADD COLUMN group_id TEXT")
        rows = con.execute(
            "SELECT correlation_id, symbol, group_id FROM orders").fetchall()
        updated = []
        for cid, sym, gid in rows:
            if sym in sym_to_gid and not gid:
                con.execute(
                    "UPDATE orders SET group_id = ? WHERE correlation_id = ?",
                    [sym_to_gid[sym], cid])
                updated.append({"order": cid, "symbol": sym,
                                "group_id": sym_to_gid[sym]})
        con.commit()
    finally:
        con.close()
    return updated or [{"info": "no orders needed a group_id backfill"}]


def _exit_fill(fills: List[tuple], symbol: str, side: str, entry_ts: str) -> Optional[tuple]:
    """The exit fill for a leg: opposite side, later than the entry fill."""
    opposite = "BUY" if side == "SELL" else "SELL"
    matches = [f for f in fills if f[2] == symbol and f[5] == opposite
               and f[7] > entry_ts]
    if len(matches) != 1:
        return None
    return matches[0]


def _realized_pnl(side: str, entry: float, exit_: float, qty: float) -> float:
    """Gross per-leg realized pnl — the position-tracker formula with
    multiplier 1.0 (option instruments): SELL legs gain when the exit is
    below entry, BUY legs gain when the exit is above entry."""
    return (entry - exit_) * qty if side == "SELL" else (exit_ - entry) * qty


def _repair_trades(data_root: Path, session: str) -> List[dict]:
    trades_path = data_root / "trading" / "trading.db"
    fills_path = data_root / "execution.db"
    if not trades_path.exists():
        return [{"error": f"no trades ledger at {trades_path}"}]
    open_rows = _open_trade_rows(trades_path, session)
    if not open_rows:
        return [{"info": "no open (unexited) trade rows for the session"}]
    if not fills_path.exists():
        return [{"error": f"no canonical fills at {fills_path}; cannot repair"}]

    con = sqlite3.connect(str(fills_path))
    try:
        fills = con.execute(
            "SELECT fill_id, order_id, symbol, quantity, price, side, fee, timestamp "
            "FROM fills").fetchall()
    finally:
        con.close()

    from core.database.manager import DatabaseManager
    dm = DatabaseManager(data_root=data_root)
    repaired: List[dict] = []
    with dm.trading_writer() as conn:
        for trade_id, symbol, side, qty, entry, fees, ts in open_rows:
            fill = _exit_fill(fills, symbol, side, ts)
            if fill is None:
                repaired.append({
                    "trade_id": trade_id, "symbol": symbol,
                    "status": "skipped",
                    "detail": "no unique opposite-side exit fill in execution.db"})
                continue
            _fill_id, _order_id, _sym, _qty, exit_price, _side, exit_fee, _ts = fill
            pnl = _realized_pnl(side, entry, exit_price, _qty)
            conn.execute(
                "UPDATE trades SET exit_price = ?, pnl = ?, fees = fees + ? "
                "WHERE trade_id = ?",
                [exit_price, pnl, exit_fee, trade_id])
            repaired.append({
                "trade_id": trade_id, "symbol": symbol, "side": side,
                "qty": qty, "entry_price": entry, "exit_price": exit_price,
                "exit_fill": _fill_id, "pnl": round(pnl, 4),
                "fees_after": round(fees + exit_fee, 4), "status": "repaired"})
    return repaired


def _rebuild_package(data_root: Path, session: date, initial_capital: float) -> Dict[str, Any]:
    pkg = data_root / "sessions" / session.isoformat()
    pkg.mkdir(parents=True, exist_ok=True)
    journal_path = data_root / "journal.jsonl"
    trades_path = data_root / "trading" / "trading.db"

    # Preserve the evidence the crashed finalize already wrote (valid, from the
    # live process's in-memory state) — never regenerate from an empty sink.
    preserved: List[str] = []
    for name in ("telemetry.json", "audit.json"):
        if (pkg / name).exists():
            preserved.append(name)

    metrics = risk_metrics_report(
        str(journal_path), str(trades_path),
        initial_capital=initial_capital, metrics_json=None)
    (pkg / "metrics.json").write_text(
        json.dumps(_jsonable(dataclasses.asdict(metrics)), indent=2, default=str),
        encoding="utf-8")

    audit = audit_window(str(journal_path), str(trades_path))
    telemetry_clean, telemetry_violations = True, []
    telemetry_file = pkg / "telemetry.json"
    if telemetry_file.exists():
        try:
            t = json.loads(telemetry_file.read_text(encoding="utf-8"))
            telemetry_clean = t.get("clean", True)
            telemetry_violations = t.get("violations", [])
        except (OSError, ValueError):
            pass

    missing = [name for name in (
        "bars.duckdb", "marks.jsonl", "signals.jsonl", "span_snapshot.pkl")
        if not (pkg / name).exists()]

    facts_src = data_root / "facts.duckdb"
    facts_copied = False
    if facts_src.exists():
        shutil.copy2(facts_src, pkg / "facts.duckdb")
        facts_copied = True

    recorder_meta = {
        "session_date": session.isoformat(),
        "reconstructed": True,
        "platform_commit": _commit_ref(),
        "facts_copied": facts_copied,
        "missing": missing,
        "note": ("driver bars / marks / signals are irrecoverable: the recorder "
                 "package is written only at finalize, which crashed; the "
                 "in-memory capture died with the process"),
    }
    (pkg / "meta.json").write_text(
        json.dumps(recorder_meta, indent=2, default=str), encoding="utf-8")

    summary = {
        "session_date": session.isoformat(),
        "bars_processed": None,
        "signals_pulled": None,
        "telemetry_clean": telemetry_clean,
        "telemetry_violations": telemetry_violations,
        "audit_guard_events": dict(audit.guard_events),
        "audit_reverse_divergence": audit.reverse_divergence,
        "audit_one_directional_only": audit.one_directional_only,
        "audit_structures": len(audit.structures),
        "metrics_round_trips": metrics.round_trips,
        "metrics_entered": metrics.structures_entered,
        "metrics_skipped": metrics.structures_skipped,
        "replay_inputs": False,
        "reconstructed": True,
        "recorder": recorder_meta,
        "preserved": preserved,
    }
    (pkg / "session_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def _commit_ref(root: Optional[Path] = None) -> str:
    import subprocess
    root = root or Path(__file__).resolve().parents[2]
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        return out or "no-commit"
    except Exception:
        return "no-commit"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="recover one NiftyShield session package after a crashed "
                    "finalize (ledger repair + metrics/summary rebuild)")
    parser.add_argument("--date", required=True, help="session date YYYY-MM-DD")
    parser.add_argument("--data-root", default="data/nifty_shield")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--live-age", type=int, default=10,
                        help="heartbeat freshness (min) that counts as live")
    parser.add_argument("--force", action="store_true",
                        help="run even if a session looks live")
    parser.add_argument("--backfill-groups", action="store_true",
                        help="only stamp group_id on orders from the session's "
                             "ENTRY_MARGIN journal (for entries made before the "
                             "order group_id fix); no ledger or package writes")
    args = parser.parse_args()

    session = date.fromisoformat(args.date)
    data_root = Path(args.data_root).resolve()
    if not data_root.exists():
        raise SystemExit(f"no data root at {data_root}")
    if not args.force:
        _check_live(data_root, args.live_age)

    print(f"=== recovering session {session} at {data_root} ===")
    if args.backfill_groups:
        backfilled = _backfill_group_ids(data_root, session.isoformat())
        print("group_id backfill:")
        for r in backfilled:
            print(f"  {r.get('status', '?')}: {r}")
        if any("error" in r for r in backfilled):
            return 1
        return 0

    repaired = _repair_trades(data_root, session.isoformat())
    print("ledger repair:")
    for r in repaired:
        print(f"  {r.get('status', '?')}: {r}")
    if any("error" in r for r in repaired):
        raise SystemExit("ledger repair failed — see above")

    summary = _rebuild_package(data_root, session, args.capital)
    pkg = data_root / "sessions" / session.isoformat()
    print(f"package: {pkg}")
    print(f"  metrics.json       total_realized_pnl={summary['metrics_round_trips']}"
          f" RTs")
    m = json.loads((pkg / "metrics.json").read_text(encoding="utf-8"))
    print(f"  metrics.json       total_realized_pnl={m['total_realized_pnl']} "
          f"wins={m['wins']} losses={m['losses']}")
    print(f"  session_summary.json written; preserved={summary['preserved']}")
    print(f"  meta.json missing (irrecoverable): {summary['recorder']['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
