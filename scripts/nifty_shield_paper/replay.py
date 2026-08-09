"""NiftyShield — Stage-2 PAPER replay-evidence harness (E007 Phase B, deliverable G).

Re-drives a RECORDED session package through the real composition root in REPLAY
and diffs determinism:

1. **Signal stream** — the recorded live signal capture (`signals.jsonl`) vs the
   replay's own capture (byte-identical on the deterministic fields).
2. **Fact identity** — the recorded 13:00 fact row vs the row the live fact
   publisher recomputes from the recorded session bars (regime / confidence /
   intraday VIX / model provenance). `produced_by` is a standing exclusion (it
   embeds the platform commit the replay runs at).
3. **Ledger deterministic fields** — the live session's ledger rows (from the
   window root `trading.db`, filtered to the session) vs the replay's ledger:
   symbol, side, quantity, fill price, signal_id. Standing exclusions only:
   `trade_id`/`broker_id` UUIDs and journal wall-clock.

Marks come from the package's recorded call log (`ReplayMarksSource`, call
order), the driver bars from the recorded stream, and the margin engine from the
captured SPAN snapshot — so every input the live session consumed is exactly
reproduced, and any divergence is a REAL platform finding, surfaced loudly.

Output: `replay_result.json` in the session package + a printed report. Exit 0
only when every check passes.

Usage:
    python scripts/nifty_shield_paper/replay.py --session 2026-08-11
    python scripts/nifty_shield_paper/replay.py --session 2026-08-11 --data-root data/nifty_shield
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.database.utils.market_hours import MarketHours
from core.runtime.config import Mode
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink

from scripts.nifty_shield_paper.recorder import (
    ReplayBarProvider, ReplayDivergence, ReplayMarksSource, SessionRecorder,
    load_driver_bars, load_span_snapshot, read_jsonl,
)
from scripts.nifty_shield_paper_runner import build_nifty_shield_paper_driver

_logger = logging.getLogger("nifty_shield_replay")

# Standing exclusions for the fact-identity check (the produced_by field embeds
# the platform commit the replay runs at, which legitimately differs).
_FACT_EXCLUDED = {"produced_by"}

# Ledger deterministic fields (§4.2 replay row): symbol, side, quantity, fill
# price, signal_id. trade_id/broker_id UUIDs and journal wall-clock excluded.
_LEDGER_FIELDS = ("symbol", "side", "quantity", "entry_price", "signal_id")


@dataclasses.dataclass
class ReplayResult:
    session: str
    platform_commit: str
    driver_bars: int
    live_signals: int
    replay_signals: int
    signals_match: bool
    signals_mismatches: List[dict]
    fact_identity_match: bool
    fact_diff: Optional[dict]
    live_ledger_rows: int
    replay_ledger_rows: int
    ledger_match: bool
    ledger_mismatches: List[dict]
    replay_guard_events: Dict[str, int]
    replay_reverse_divergence: List[str]
    pass_: bool

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def _read_fact_row(db_path: Path) -> Optional[dict]:
    if not db_path.exists():
        return None
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row = con.execute(
            "SELECT session_date, checkpoint, regime, regime_confidence, "
            "vix_close, vix_at_checkpoint, regime_fact_version, model_hash, "
            "produced_by FROM day_type_facts WHERE checkpoint = '13pm' "
            "ORDER BY session_date DESC LIMIT 1").fetchone()
    finally:
        con.close()
    if row is None:
        return None
    (d, cp, regime, conf, vix, vix_cp, ver, mhash, produced) = row
    return {
        "session_date": str(d), "checkpoint": cp, "regime": regime,
        "regime_confidence": float(conf),
        "vix_close": float(vix) if vix is not None else None,
        "vix_at_checkpoint": float(vix_cp) if vix_cp is not None else None,
        "regime_fact_version": ver, "model_hash": mhash, "produced_by": produced,
    }


def _ledger_rows(db_path: Path, session: str) -> List[tuple]:
    """Deterministic ledger fields for one session (entry-keyed rows)."""
    if not db_path.exists():
        return []
    try:
        con = sqlite3.connect(str(db_path))
        rows = con.execute(
            f"SELECT symbol, side, quantity, entry_price, signal_id FROM trades "
            f"WHERE timestamp LIKE ? ORDER BY timestamp, symbol",
            [f"{session}%"],
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [tuple(r) for r in rows]


def _normalize_signals(signals: List[dict]) -> List[dict]:
    """JSON-stable projection of a signal capture for byte comparison."""
    out = []
    for s in signals:
        o = {
            "strategy_id": s["strategy_id"], "symbol": s["symbol"],
            "timestamp": s["timestamp"], "signal_type": s["signal_type"],
            "confidence": float(s["confidence"]),
        }
        o["metadata"] = json.loads(json.dumps(s.get("metadata", {}), sort_keys=True))
        if s.get("context") is not None:
            o["context"] = json.loads(json.dumps(s["context"], sort_keys=True))
        out.append(o)
    return out


def _bootstrap_trading_schema(dm: DatabaseManager) -> None:
    from core.database.schema import (
        TRADING_TRADES_SCHEMA, TRADING_TRADE_CONTEXT_SCHEMA,
    )
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
        conn.execute(TRADING_TRADE_CONTEXT_SCHEMA)


def build_replay_driver(*, session_dir: str, replay_root: str,
                        initial_capital: float = 1_000_000.0):
    """Build the REPLAY composition root over a recorded session package.

    Returns a tuple (driver, journal, telemetry, recorder, bars) so callers can
    drive the run and then read the replay-side evidence (shared by the
    replay-evidence harness and the kill-switch drill).
    """
    pkg = Path(session_dir)
    meta_path = pkg / "meta.json"
    if not meta_path.exists():
        raise ReplayDivergence(f"no session package at {pkg} (missing meta.json)")
    bars = load_driver_bars(str(pkg))
    if not bars:
        raise ReplayDivergence(f"session package {pkg} has no recorded driver bars")

    replay_root = Path(replay_root)
    replay_root.mkdir(parents=True, exist_ok=True)
    journal = RuntimeEventJournal(str(replay_root / "journal.jsonl"))
    telemetry = InMemoryTelemetrySink()
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=replay_root)
    _bootstrap_trading_schema(dm)

    # Isolate the live fact publisher to the package's recorded session bars —
    # the same data the live hook read (per-day store first, then live buffer).
    import scripts.daytype.publish_live_fact as live
    live.CANDLE_DIR_1M = pkg / "facts_bars"
    live.LIVE_BUFFER = replay_root / "no_live_buffer.duckdb"

    marks = ReplayMarksSource(str(pkg / "marks.jsonl"))
    recorder = SessionRecorder(str(replay_root / "capture"))
    clock = ReplayClock(bars[0].timestamp)
    span_snapshot = load_span_snapshot(str(pkg))

    driver = build_nifty_shield_paper_driver(
        mode=Mode.REPLAY,
        clock=clock,
        db_manager=dm,
        journal=journal,
        telemetry=telemetry,
        marks_source=marks,
        facts_db_path=str(pkg / "facts.duckdb"),
        metrics_path=str(replay_root / "metrics.json"),
        heartbeat_path=str(replay_root / "heartbeat.json"),
        execution_store_path=str(replay_root / "execution.db"),
        initial_capital=initial_capital,
        max_bars=len(bars),
        recorder=recorder,
        provider=ReplayBarProvider(bars),
        span_snapshot=span_snapshot,
    )
    return driver, journal, telemetry, recorder, bars


def run_session_replay(*, session_dir: str, data_root: str,
                       initial_capital: float = 1_000_000.0) -> ReplayResult:
    pkg = Path(session_dir)
    meta_path = pkg / "meta.json"
    if not meta_path.exists():
        raise ReplayDivergence(f"no session package at {pkg} (missing meta.json)")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    session = meta["session_date"]
    platform_commit = meta.get("platform_commit", "unknown")

    bars = load_driver_bars(str(pkg))
    if not bars:
        raise ReplayDivergence(f"session package {pkg} has no recorded driver bars")

    # Live-side ledger for the session (the window's accumulated evidence).
    live_trades_path = Path(data_root) / "trading" / "trading.db"
    live_ledger = _ledger_rows(live_trades_path, session)
    # Live-side signal capture.
    live_signals = _normalize_signals(read_jsonl(pkg / "signals.jsonl"))
    # Live-side fact row (read BEFORE the replay overwrites the copy).
    recorded_fact = _read_fact_row(pkg / "facts.duckdb")

    driver, journal, telemetry, recorder, bars = build_replay_driver(
        session_dir=session_dir,
        replay_root=str(pkg / "replay"),
        initial_capital=initial_capital,
    )
    driver.run()

    replay_signals = _normalize_signals(recorder.signals)
    recomputed_fact = _read_fact_row(pkg / "facts.duckdb")
    replay_ledger = _ledger_rows(pkg / "replay" / "trading" / "trading.db", session)

    # --- diffs ------------------------------------------------------------ #
    sig_mismatch: List[dict] = []
    n = max(len(live_signals), len(replay_signals))
    for i in range(n):
        a = live_signals[i] if i < len(live_signals) else None
        b = replay_signals[i] if i < len(replay_signals) else None
        if a != b:
            sig_mismatch.append({"index": i, "live": a, "replay": b})
    signals_match = not sig_mismatch and len(live_signals) == len(replay_signals)

    fact_diff: Optional[dict] = None
    if recorded_fact is None and recomputed_fact is None:
        fact_identity_match = True
    else:
        a = {k: v for k, v in (recorded_fact or {}).items()
             if k not in _FACT_EXCLUDED}
        b = {k: v for k, v in (recomputed_fact or {}).items()
             if k not in _FACT_EXCLUDED}
        if a == b:
            fact_identity_match = True
        else:
            fact_identity_match = False
            fact_diff = {"recorded": recorded_fact, "recomputed": recomputed_fact}

    ledger_mismatch: List[dict] = []
    n_ledger = max(len(live_ledger), len(replay_ledger))
    for i in range(n_ledger):
        a = live_ledger[i] if i < len(live_ledger) else None
        b = replay_ledger[i] if i < len(replay_ledger) else None
        if a != b:
            ledger_mismatch.append({"index": i, "live": a, "replay": b})
    ledger_match = (not ledger_mismatch
                    and len(live_ledger) == len(replay_ledger))

    from scripts.nifty_shield_paper.audit import audit_window
    replay_audit = audit_window(str(pkg / "replay" / "journal.jsonl"),
                                str(pkg / "replay" / "trading" / "trading.db"))

    ok = (signals_match and fact_identity_match and ledger_match
          and not replay_audit.guard_events
          and not replay_audit.reverse_divergence)

    result = ReplayResult(
        session=session, platform_commit=platform_commit,
        driver_bars=len(bars),
        live_signals=len(live_signals), replay_signals=len(replay_signals),
        signals_match=signals_match, signals_mismatches=sig_mismatch,
        fact_identity_match=fact_identity_match, fact_diff=fact_diff,
        live_ledger_rows=len(live_ledger), replay_ledger_rows=len(replay_ledger),
        ledger_match=ledger_match, ledger_mismatches=ledger_mismatch,
        replay_guard_events=dict(replay_audit.guard_events),
        replay_reverse_divergence=replay_audit.reverse_divergence,
        pass_=ok,
    )
    (pkg / "replay_result.json").write_text(
        json.dumps(result.as_dict(), indent=2, default=str), encoding="utf-8")
    return result


def _fmt_result(r: ReplayResult) -> str:
    lines = [
        f"\n=== NiftyShield session replay — {r.session} ===",
        f"platform_commit: {r.platform_commit}   driver_bars: {r.driver_bars}",
        f"signal stream  : live {r.live_signals} vs replay {r.replay_signals} "
        f"-> {'PASS' if r.signals_match else 'FAIL'}",
        f"fact identity  : {'PASS' if r.fact_identity_match else 'FAIL'}",
        f"ledger (det)   : live {r.live_ledger_rows} vs replay "
        f"{r.replay_ledger_rows} -> {'PASS' if r.ledger_match else 'FAIL'}",
        f"replay guards  : {r.replay_guard_events}  reverse_divergence: "
        f"{r.replay_reverse_divergence}",
        f"REPLAY {'PASS' if r.pass_ else 'FAIL'}",
    ]
    if r.signals_mismatches:
        lines.append(f"  signal mismatches: {len(r.signals_mismatches)}")
        for m in r.signals_mismatches[:3]:
            lines.append(f"    [{m['index']}] live={m['live']} replay={m['replay']}")
    if r.ledger_mismatches:
        lines.append(f"  ledger mismatches: {len(r.ledger_mismatches)}")
        for m in r.ledger_mismatches[:3]:
            lines.append(f"    [{m['index']}] live={m['live']} replay={m['replay']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NiftyShield Stage-2 PAPER replay evidence (E007 Phase B)")
    parser.add_argument("--session", required=True,
                        help="session date YYYY-MM-DD of the recorded package")
    parser.add_argument("--data-root", default="data/nifty_shield",
                        help="window evidence root holding trading.db")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    session_dir = Path(args.data_root) / "sessions" / args.session
    result = run_session_replay(session_dir=str(session_dir),
                                data_root=args.data_root,
                                initial_capital=args.capital)
    print(_fmt_result(result))
    return 0 if result.pass_ else 1


if __name__ == "__main__":
    raise SystemExit(main())
