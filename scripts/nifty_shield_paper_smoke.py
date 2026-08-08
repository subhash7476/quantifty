"""NiftyShield — Stage-2 PAPER one-session smoke run (E007 Phase A).

Proves the wired pipeline end-to-end through the REAL composition root in REPLAY
over a deterministic synthetic session: publish the 13:00 live fact -> source
emits the structure -> handler assembles/fills at real (static) marks -> margin
evidence journaled -> exit driver closes at the 15:15 hard exit -> ledger +
journal + telemetry all produced. It is a harness proof, NOT a validation (E007
§3: "Do not claim Stage 2 done at the end of Phase A").

Runs offline: synthetic 1m session written to a temp per-day store, static marks,
temp ledger/journal. Deterministic and re-runnable.
"""
from __future__ import annotations

import logging
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar
from core.execution.options.nifty_shield_marks import StaticMarksSource
from core.runtime.config import Mode
from core.runtime.metrics import InMemoryTelemetrySink
from core.runtime.event_journal import RuntimeEventJournal

from scripts.nifty_shield_paper.audit import audit_window
from scripts.nifty_shield_paper.metrics_report import risk_metrics_report
from scripts.nifty_shield_paper.telemetry_archive import archive_session
from scripts.nifty_shield_paper_runner import build_nifty_shield_paper_driver

_logger = logging.getLogger("nifty_shield_smoke")

NF_SYMBOL = "NSE_INDEX|Nifty 50"
SESSION = date(2026, 6, 5)
START = datetime(2026, 6, 5, 9, 15, 0)


def _session_frame(seed: int, base: float, bars: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = base + np.cumsum(rng.normal(0, 3, bars))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    times = pd.date_range(START, periods=bars, freq="1min")
    return pd.DataFrame({
        "timestamp": times, "open": opens,
        "high": np.maximum(opens, closes) + 1.0,
        "low": np.minimum(opens, closes) - 1.0,
        "close": closes, "volume": np.full(bars, 1000.0),
    })


def _stable_vix(bars: int) -> pd.DataFrame:
    times = pd.date_range(START, periods=bars, freq="1min")
    return pd.DataFrame({
        "timestamp": times, "open": 14.5, "high": 14.5, "low": 14.5,
        "close": 14.5, "volume": np.full(bars, 1000.0),
    })


def _write_candle_db(path: Path, rows: Dict[str, pd.DataFrame]) -> None:
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE candles (
            symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    for symbol, df in rows.items():
        con.executemany(
            "INSERT INTO candles VALUES (?,?,?,?,?,?,?)",
            [(symbol, ts.to_pydatetime(), float(o), float(h), float(l),
              float(c), int(v))
             for ts, o, h, l, c, v in zip(
                 df["timestamp"], df["open"], df["high"], df["low"],
                 df["close"], df["volume"])],
        )
    con.close()


class SessionBarProvider(MarketDataProvider):
    """Replays a fixed bar list once (a minimal REPLAY provider for the smoke)."""

    def __init__(self, bars: List[OHLCVBar]):
        super().__init__([b.symbol for b in bars])
        self._bars = list(bars)

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        return self._bars.pop(0) if self._bars else None

    def is_data_available(self, symbol: str) -> bool:
        return bool(self._bars)

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        return self._bars[-1] if self._bars else None

    def reset(self, symbol: str) -> None:
        return None

    def get_progress(self, symbol: str):
        return (0, len(self._bars))


def main() -> int:
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    work = Path(tempfile.mkdtemp(prefix="nifty_shield_smoke_"))
    candle_dir = work / "candles_1m"
    candle_dir.mkdir()

    # Full session 09:15 -> 15:15 (361 bars) so the 15:15 hard exit fires.
    bars_n = 361
    nf = _session_frame(seed=1, base=24000.0, bars=bars_n)
    bn = _session_frame(seed=2, base=52000.0, bars=bars_n)
    vix = _stable_vix(bars_n)
    _write_candle_db(candle_dir / f"{SESSION.isoformat()}.duckdb", {
        NF_SYMBOL: nf, "NSE_INDEX|Nifty Bank": bn, "NSE_INDEX|India VIX": vix,
    })

    # Point the live fact publisher at the synthetic session store.
    import scripts.daytype.publish_live_fact as live
    live.CANDLE_DIR_1M = candle_dir
    live.LIVE_BUFFER = work / "no_live_buffer.duckdb"

    facts_db = work / "facts.duckdb"
    # Compute the EXACT struck legs the source will emit at 13:00 (regime from
    # the synthetic bars, strikes from the 13:00 close), then price those legs
    # deterministically: shorts at 100, wings at 20 (net credit > 0).
    from scripts.daytype.publish_facts import compute_13pm_state
    from strategies.nifty_shield_v1 import structures
    from strategies.nifty_shield_v1.config import DEFAULT_CONFIG as _CFG
    st = compute_13pm_state(SESSION, nf, bn)
    assert st is not None and st.get("predicted_state") != "Unknown", \
        "synthetic session produced no 13pm state"
    close_at_13 = float(nf.iloc[225]["close"])
    structure = structures.select_structure(st["predicted_state"], 14.5, _CFG)
    legs = structures.compute_legs(structure, close_at_13, _CFG, SESSION)
    marks = StaticMarksSource({
        leg["symbol"]: (100.0 if leg["signal_type"] == "SELL" else 20.0)
        for leg in legs
    })
    print(f"session regime={st['predicted_state']} structure={structure} "
          f"legs={[l['symbol'] for l in legs]}")
    journal = RuntimeEventJournal(str(work / "journal.jsonl"))
    telemetry = InMemoryTelemetrySink()
    dm = DatabaseManager(data_root=work)
    clock = ReplayClock(START)

    bars = [
        OHLCVBar(symbol=NF_SYMBOL, timestamp=ts.to_pydatetime(),
                 open=float(o), high=float(h), low=float(l),
                 close=float(c), volume=float(v))
        for ts, o, h, l, c, v in zip(nf["timestamp"], nf["open"], nf["high"],
                                     nf["low"], nf["close"], nf["volume"])
    ]
    provider = SessionBarProvider(bars)

    driver = build_nifty_shield_paper_driver(
        mode=Mode.REPLAY,
        clock=clock,
        db_manager=dm,
        journal=journal,
        telemetry=telemetry,
        marks_source=marks,
        facts_db_path=str(facts_db),
        metrics_path=str(work / "metrics.json"),
        heartbeat_path=str(work / "heartbeat.json"),
        execution_store_path=str(work / "execution.db"),
        initial_capital=1_000_000.0,
        max_bars=len(bars),
    )
    # The composition root builds its own provider; swap in the session replay.
    driver._provider = provider
    driver.run()

    print(f"\n=== NiftyShield Stage-2 PAPER smoke run @ {SESSION} ===")
    print(f"bars_processed: {driver.bars_processed} "
          f"signals_pulled: {driver.signals_pulled}")
    print(f"telemetry: {dict(telemetry.snapshot())}")

    audit = audit_window(str(work / "journal.jsonl"), str(work / "trading.db"))
    print(f"journal audit: structures={len(audit.structures)} "
          f"guard_events={dict(audit.guard_events)} "
          f"reverse_divergence={audit.reverse_divergence}")
    for a in audit.structures:
        print(f"  {a.status:8s} {a.group_id[:8]} {a.structure:20s} "
              f"closed={a.closed} {a.exit_reason or ''}")

    metrics = risk_metrics_report(str(work / "journal.jsonl"),
                                  str(work / "trading.db"),
                                  initial_capital=1_000_000.0,
                                  metrics_json=str(work / "metrics.json"))
    print(f"risk metrics: RT={metrics.round_trips} win_rate={metrics.win_rate:.2f} "
          f"conv={metrics.signal_fill_conversion:.2f} "
          f"peak_margin_util={metrics.peak_margin_utilisation:.2%}")

    tel = archive_session(SESSION.isoformat(), telemetry.snapshot())
    print(f"telemetry: clean={tel.clean} violations={tel.violations}")

    ok = (driver.signals_pulled >= 2 and audit.structures
          and any(a.closed for a in audit.structures)
          and not audit.reverse_divergence
          and not audit.guard_events
          and tel.clean)
    print(f"\nSMOKE {'PASS' if ok else 'FAIL'}")
    print(f"artifacts: {work}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
