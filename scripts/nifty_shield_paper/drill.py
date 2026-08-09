"""NiftyShield — Stage-2 PAPER kill-switch drill (E007 Phase B, deliverable H).

The mid-window operator drill (E7-5): exercise the manual kill switch against the
real composition root and capture the evidence the PAPER report needs:

1. **Activate** — the `STOP` file is placed in the runner's CWD (the handler's
   gate 0 checks `os.path.exists("STOP")` on every signal).
2. **Blocked + journaled** — the drill re-drives a recorded session and, at a
   deterministic point *before* the 13:00 entry, injects the STOP file. The
   13:00 leg set is then blocked by the kill switch: `KILL_SWITCH_ACTIVATED`
   journaled exactly once (IN-001), the entry journals an `ENTRY_SKIPPED`
   "every leg rejected by a handler gate", and zero fills land in the ledger.
3. **Kill-switched-but-running** — the loop keeps running to the end of the
   corpus (bars_processed == corpus size; heartbeat/telemetry counters alive).
4. **Restart per the runbook** — the STOP file is removed and the SAME session
   is re-driven clean through a fresh composition root (the operator's restart);
   the entry now fires (fills present, guards 0), proving the kill switch is not
   sticky across a restart.

Output: `{session}/drill/drill_result.json` + the drill journal and telemetry
snapshot. Exit 0 only when every assertion holds.

The `STOP` file's lifetime is strictly scoped (F-B3): `run_drill` writes it only
inside a `try` whose `finally` always removes it, so a crash mid-drill can never
leak a `STOP` into the operator's CWD (a leaked `STOP` would silently
kill-switch the next live `session.py` — handler gate 0 checks
`os.path.exists("STOP")` relative to CWD).

Usage:
    python scripts/nifty_shield_paper/drill.py --session 2026-08-11
    python scripts/nifty_shield_paper/drill.py --session 2026-08-11 --data-root data/nifty_shield
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar
from core.runtime.event_journal import EventType
from core.runtime.metrics import RuntimeMetric

from scripts.nifty_shield_paper.recorder import (
    ReplayDivergence, read_jsonl,
)
from scripts.nifty_shield_paper.replay import build_replay_driver

_logger = logging.getLogger("nifty_shield_drill")

STOP_FILE = "STOP"


@dataclasses.dataclass
class DrillResult:
    session: str
    stop_file: str
    stop_injected_before_bars: int
    kill_switch_journaled: bool
    kill_switch_count: int
    entry_block_journaled: bool
    fills_after_stop: int
    bars_processed: int
    corpus_bars: int
    loop_completed: bool
    telemetry: Dict[str, int]
    recovery_fills: int
    recovery_guard_events: Dict[str, int]
    recovery_clean: bool
    pass_: bool

    def as_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d.pop("telemetry", None)
        d["telemetry"] = self.telemetry
        return d


class _GateBarProvider(MarketDataProvider):
    """Wraps a replay bar provider; blocks one call at `gate_at` bars so the
    drill can inject the STOP file mid-run at a deterministic point."""

    def __init__(self, inner: MarketDataProvider, gate_at: int,
                 gate: threading.Event):
        super().__init__(inner.symbols)
        self._inner = inner
        self._gate_at = gate_at
        self._gate = gate
        self._delivered = 0

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        if self._delivered >= self._gate_at:
            if not self._gate.wait(timeout=60):
                raise ReplayDivergence(
                    "drill gate timed out waiting for STOP injection")
        bar = self._inner.get_next_bar(symbol)
        if bar is not None:
            self._delivered += 1
        return bar

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        return self._inner.get_latest_bar(symbol)

    def is_data_available(self, symbol: str) -> bool:
        return self._inner.is_data_available(symbol)

    def reset(self, symbol: str) -> None:
        return self._inner.reset(symbol)

    def get_progress(self, symbol: str):
        return self._inner.get_progress(symbol)

    def advance_tick(self) -> bool:
        advance = getattr(self._inner, "advance_tick", None)
        return advance() if advance is not None else True


def _count_events(journal_path: Path, event_type: EventType) -> int:
    return sum(1 for e in read_jsonl(journal_path)
               if e["event_type"] == event_type.value)


def _guard_events(journal_path: Path) -> Dict[str, int]:
    from scripts.nifty_shield_paper.audit import GUARD_TYPES
    out: Dict[str, int] = {}
    for e in read_jsonl(journal_path):
        if e["event_type"] in GUARD_TYPES:
            out[e["event_type"]] = out.get(e["event_type"], 0) + 1
    return out


def _ledger_fills(trades_db: Path) -> int:
    if not trades_db.exists():
        return 0
    import sqlite3
    try:
        con = sqlite3.connect(str(trades_db))
        n = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        con.close()
        return int(n)
    except sqlite3.Error:
        return 0


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def run_drill(*, session_dir: str, data_root: str,
              initial_capital: float = 1_000_000.0,
              stop_before_bars: int = 100) -> DrillResult:
    """Run the kill-switch drill over a recorded session package."""
    pkg = Path(session_dir)
    meta_path = pkg / "meta.json"
    if not meta_path.exists():
        raise ReplayDivergence(f"no session package at {pkg} (missing meta.json)")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    session = meta["session_date"]

    stop_path = Path.cwd() / STOP_FILE
    drill_root = pkg / "drill"
    recovery_root = pkg / "drill_recovery"

    # --- Phase 1: STOP-injection run -------------------------------------- #
    gate = threading.Event()
    driver, journal, telemetry, recorder, bars = build_replay_driver(
        session_dir=session_dir, replay_root=str(drill_root),
        initial_capital=initial_capital)
    gated = _GateBarProvider(driver._provider, stop_before_bars, gate)
    driver._provider = gated

    def _drive() -> None:
        try:
            driver.run()
        except Exception as exc:
            _logger.error("drill run failed: %s", exc)

    thread = threading.Thread(target=_drive, name="nifty-shield-drill")
    thread.start()

    recovery_guard: Dict[str, int] = {}
    recovery_fills = 0
    recovery_clean = False
    telemetry_snapshot: Dict[str, int] = {}
    kill_count = 0
    entry_blocks: List[dict] = []
    fills = 0
    loop_completed = False
    try:
        # F-B3: the STOP file's lifetime is strictly scoped to this try. The
        # finally ALWAYS removes it, so a crash between write and unlink can
        # never leak a STOP into the operator's CWD — a leaked STOP would
        # silently kill-switch the next live session (handler gate 0 checks
        # `os.path.exists("STOP")` relative to CWD).
        deadline = time.time() + 60
        while driver.bars_processed < stop_before_bars:
            if not thread.is_alive():
                break
            if time.time() > deadline:
                raise ReplayDivergence("drill: driver never reached the STOP gate")
            time.sleep(0.005)
        stop_path.write_text(
            "NiftyShield E007 Phase B kill-switch drill (E7-5)", encoding="utf-8")
        gate.set()
        thread.join(timeout=120)

        telemetry_snapshot = {k.value if hasattr(k, "value") else k: v
                              for k, v in telemetry.snapshot().items()}
        drill_journal = drill_root / "journal.jsonl"
        drill_trades = drill_root / "trading" / "trading.db"

        kill_count = _count_events(drill_journal, EventType.KILL_SWITCH_ACTIVATED)
        entry_blocks = [e for e in read_jsonl(drill_journal)
                        if e["event_type"] == EventType.ENTRY_SKIPPED.value
                        and "every leg rejected by a handler gate"
                        in e.get("metadata", {}).get("reason", "")]
        fills = _ledger_fills(drill_trades)
        loop_completed = driver.bars_processed >= len(bars)

        # --- Phase 2: recovery run (restart per the runbook) ---------------- #
        _safe_unlink(stop_path)                 # remove STOP before restart
        r_driver, r_journal, r_telemetry, r_recorder, r_bars = build_replay_driver(
            session_dir=session_dir, replay_root=str(recovery_root),
            initial_capital=initial_capital)
        r_driver.run()
        recovery_fills = _ledger_fills(recovery_root / "trading" / "trading.db")
        recovery_guard = _guard_events(recovery_root / "journal.jsonl")
        recovery_clean = (recovery_fills > 0 and not recovery_guard
                          and not r_telemetry.snapshot().get(
                              RuntimeMetric.STRATEGY_ERRORS.value, 0))
    finally:
        _safe_unlink(stop_path)

    ok = (kill_count == 1 and bool(entry_blocks) and fills == 0
          and loop_completed and recovery_clean)

    result = DrillResult(
        session=session, stop_file=str(stop_path),
        stop_injected_before_bars=stop_before_bars,
        kill_switch_journaled=kill_count == 1, kill_switch_count=kill_count,
        entry_block_journaled=bool(entry_blocks),
        fills_after_stop=fills,
        bars_processed=driver.bars_processed, corpus_bars=len(bars),
        loop_completed=loop_completed, telemetry=telemetry_snapshot,
        recovery_fills=recovery_fills, recovery_guard_events=recovery_guard,
        recovery_clean=recovery_clean, pass_=ok,
    )
    (drill_root / "drill_result.json").write_text(
        json.dumps(result.as_dict(), indent=2, default=str), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NiftyShield Stage-2 PAPER kill-switch drill (E007 Phase B)")
    parser.add_argument("--session", required=True,
                        help="session date YYYY-MM-DD of the recorded package")
    parser.add_argument("--data-root", default="data/nifty_shield",
                        help="window evidence root")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--stop-before-bars", type=int, default=100,
                        help="inject STOP after this many bars (before 13:00)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    session_dir = Path(args.data_root) / "sessions" / args.session
    r = run_drill(session_dir=str(session_dir), data_root=args.data_root,
                  initial_capital=args.capital,
                  stop_before_bars=args.stop_before_bars)
    print(f"\n=== NiftyShield kill-switch drill — {r.session} ===")
    print(f"STOP injected before bar {r.stop_injected_before_bars}")
    print(f"KILL_SWITCH_ACTIVATED journaled: {r.kill_switch_journaled} "
          f"(count {r.kill_switch_count})")
    print(f"entry blocked + journaled: {r.entry_block_journaled}   "
          f"fills after STOP: {r.fills_after_stop}")
    print(f"loop completed: {r.loop_completed} "
          f"({r.bars_processed}/{r.corpus_bars} bars)")
    print(f"recovery run: fills {r.recovery_fills} guards {r.recovery_guard_events} "
          f"clean {r.recovery_clean}")
    print(f"DRILL {'PASS' if r.pass_ else 'FAIL'}")
    print(f"evidence: {Path(session_dir) / 'drill' / 'drill_result.json'}")
    return 0 if r.pass_ else 1


if __name__ == "__main__":
    raise SystemExit(main())
