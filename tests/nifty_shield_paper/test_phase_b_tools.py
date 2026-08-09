"""
NiftyShield — Stage-2 PAPER Phase B tooling tests (E007 Phase B).

End-to-end over a deterministic synthetic session: build a session package
through the real composition root with the recorder, then exercise the Phase B
tools against it:

- recorder: session package contents (bars/marks/signals/facts/span), replay
  seam (call order, outage re-raise, divergence).
- session.py finalize: per-session audit/telemetry/metrics + package.
- replay.py: signal stream byte-identical, ledger deterministic fields match,
  fact identity match.
- drill.py: STOP injection -> kill switch journaled once, entry blocked, loop
  completed, recovery clean, and the STOP file never leaks (F-B3).
- assemble_report.py: the frozen skeleton's markers get filled; the headline
  counts only counting sessions (F-B1); assembly is idempotent against the
  default path (F-B2).
- LIVE-only seams: real RuntimeWatchdog heartbeat (F-B4) and the
  span_snapshot.pkl round-trip (F-B4).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.daytype.publish_live_fact as live
import scripts.nifty_shield_paper_runner as runner_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.database.providers.base import MarketDataProvider
from core.database.schema import TRADING_TRADES_SCHEMA
from core.events import OHLCVBar
from core.execution.options.nifty_shield_marks import (
    MarksSourceUnavailable, StaticMarksSource,
)
from core.runtime.config import Mode
from core.runtime.event_journal import EventType, RuntimeEventJournal
from core.runtime.metrics import InMemoryTelemetrySink

from scripts.daytype.publish_facts import compute_13pm_state
from scripts.nifty_shield_paper.recorder import (
    ReplayDivergence, ReplayMarksSource, SessionRecorder, read_jsonl,
)
from scripts.nifty_shield_paper.session import finalize_session_evidence
from scripts.nifty_shield_paper.replay import run_session_replay
from scripts.nifty_shield_paper.drill import run_drill
from scripts.nifty_shield_paper.assemble_report import assemble

NF_SYMBOL = "NSE_INDEX|Nifty 50"
SESSION = date(2026, 6, 5)
START = datetime(2026, 6, 5, 9, 15, 0)
DEFAULT_CFG = None


class _StubSnapshot:
    """Picklable stand-in for a SpanSnapshot (module-level: pickling a local
    class from a test function fails)."""

    def __init__(self):
        self.file_hash = "testhash123"

    def __eq__(self, other):
        return (isinstance(other, _StubSnapshot)
                and other.file_hash == self.file_hash)


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


def _write_candle_db(path: Path, rows) -> None:
    import duckdb
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE candles (
            symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?)", rows)
    con.close()


class _SessionBarProvider(MarketDataProvider):
    def __init__(self, bars):
        super().__init__([b.symbol for b in bars])
        self._bars = list(bars)

    def get_next_bar(self, symbol):
        return self._bars.pop(0) if self._bars else None

    def is_data_available(self, symbol):
        return bool(self._bars)

    def get_latest_bar(self, symbol):
        return self._bars[-1] if self._bars else None

    def reset(self, symbol):
        return None

    def get_progress(self, symbol):
        return (0, len(self._bars))


@pytest.fixture()
def synthetic_session(tmp_path, monkeypatch):
    """Run the LIVE-shaped composition root (REPLAY driver) with the recorder
    over a deterministic synthetic session; finalize the session package.
    Returns (data_root, package_dir)."""
    monkeypatch.setattr(runner_mod, "_load_span_snapshot", lambda: None)

    work = tmp_path / "window"
    work.mkdir()
    candle_dir = work / "candles_1m"
    candle_dir.mkdir()

    bars_n = 361
    nf = _session_frame(seed=1, base=24000.0, bars=bars_n)
    bn = _session_frame(seed=2, base=52000.0, bars=bars_n)
    vix = _stable_vix(bars_n)
    _write_candle_db(candle_dir / f"{SESSION.isoformat()}.duckdb", [
        (NF_SYMBOL, ts, float(o), float(h), float(l), float(c), int(v))
        for ts, o, h, l, c, v in zip(nf["timestamp"], nf["open"], nf["high"],
                                     nf["low"], nf["close"], nf["volume"])] + [
        ("NSE_INDEX|Nifty Bank", ts, float(o), float(h), float(l), float(c), int(v))
        for ts, o, h, l, c, v in zip(bn["timestamp"], bn["open"], bn["high"],
                                     bn["low"], bn["close"], bn["volume"])] + [
        ("NSE_INDEX|India VIX", ts, float(o), float(h), float(l), float(c), int(v))
        for ts, o, h, l, c, v in zip(vix["timestamp"], vix["open"], vix["high"],
                                     vix["low"], vix["close"], vix["volume"])],
    )

    # Point the live fact publisher at the synthetic session store.
    live.CANDLE_DIR_1M = candle_dir
    live.LIVE_BUFFER = work / "no_live_buffer.duckdb"
    # Point the session-evidence finalizer's session-bars extraction at the
    # same synthetic store (the recorder's per-day-store source).
    import scripts.nifty_shield_paper.session as session_mod
    monkeypatch.setattr(session_mod, "PER_DAY_STORE", candle_dir)
    monkeypatch.setattr(session_mod, "LIVE_BUFFER", work / "no_live_buffer.duckdb")

    facts_db = work / "facts.duckdb"
    from strategies.nifty_shield_v1 import structures
    from strategies.nifty_shield_v1.config import DEFAULT_CONFIG
    st = compute_13pm_state(SESSION, nf, bn)
    assert st is not None and st.get("predicted_state") != "Unknown"
    close_at_13 = float(nf.iloc[225]["close"])
    structure = structures.select_structure(st["predicted_state"], 14.5,
                                            DEFAULT_CONFIG)
    legs = structures.compute_legs(structure, close_at_13, DEFAULT_CONFIG,
                                   SESSION)
    marks = StaticMarksSource({
        leg["symbol"]: (100.0 if leg["signal_type"] == "SELL" else 20.0)
        for leg in legs
    })

    journal = RuntimeEventJournal(str(work / "journal.jsonl"))
    telemetry = InMemoryTelemetrySink()
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=work)
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)

    recorder = SessionRecorder(str(work / "sessions" / SESSION.isoformat()))
    bars = [
        OHLCVBar(symbol=NF_SYMBOL, timestamp=ts.to_pydatetime(),
                 open=float(o), high=float(h), low=float(l),
                 close=float(c), volume=float(v))
        for ts, o, h, l, c, v in zip(nf["timestamp"], nf["open"], nf["high"],
                                     nf["low"], nf["close"], nf["volume"])
    ]
    driver = runner_mod.build_nifty_shield_paper_driver(
        mode=Mode.REPLAY,
        clock=ReplayClock(START),
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
        recorder=recorder,
        provider=_SessionBarProvider(bars),
    )
    driver.run()

    summary = finalize_session_evidence(
        session_date=SESSION, data_root=work, telemetry=telemetry,
        driver=driver, recorder=recorder, facts_db_path=facts_db,
        initial_capital=1_000_000.0)
    return work, work / "sessions" / SESSION.isoformat(), summary


# --------------------------------------------------------------------------- #
# Recorder + session package
# --------------------------------------------------------------------------- #
def test_session_package_contents(synthetic_session):
    work, pkg, summary = synthetic_session
    assert summary["replay_inputs"] is True
    assert summary["audit_structures"] == 1
    assert summary["audit_guard_events"] == {}
    assert summary["metrics_entered"] == 1

    assert (pkg / "meta.json").exists()
    assert (pkg / "bars.duckdb").exists()
    assert (pkg / "facts_bars" / f"{SESSION.isoformat()}.duckdb").exists()
    assert (pkg / "marks.jsonl").exists()
    assert (pkg / "signals.jsonl").exists()
    assert (pkg / "facts.duckdb").exists()
    assert (pkg / "audit.json").exists()
    assert (pkg / "telemetry.json").exists()
    assert (pkg / "metrics.json").exists()
    assert (pkg / "session_summary.json").exists()

    signals = read_jsonl(pkg / "signals.jsonl")
    assert len(signals) >= 2                      # one structure's leg set
    assert {s["signal_type"] for s in signals} == {"SELL", "BUY"}
    marks_log = read_jsonl(pkg / "marks.jsonl")
    assert marks_log and all("n" in m for m in marks_log)


def test_replay_marks_divergence_on_symbol_mismatch(tmp_path):
    log = tmp_path / "marks.jsonl"
    log.write_text(json.dumps({"n": 1, "symbols": ["A"], "marks": {"A": 1.0}})
                   + "\n", encoding="utf-8")
    src = ReplayMarksSource(str(log))
    with pytest.raises(ReplayDivergence):
        src.marks(["B"])


def test_replay_marks_exhausts_loudly(tmp_path):
    log = tmp_path / "marks.jsonl"
    log.write_text(json.dumps({"n": 1, "symbols": ["A"], "marks": {"A": 1.0}})
                   + "\n", encoding="utf-8")
    src = ReplayMarksSource(str(log))
    assert src.marks(["A"]) == {"A": 1.0}
    with pytest.raises(ReplayDivergence):
        src.marks(["A"])


def test_replay_marks_re_raises_outage(tmp_path):
    log = tmp_path / "marks.jsonl"
    log.write_text(json.dumps({"n": 1, "symbols": ["A"],
                               "outage": "chain cache corrupt"}) + "\n",
                   encoding="utf-8")
    src = ReplayMarksSource(str(log))
    with pytest.raises(MarksSourceUnavailable):
        src.marks(["A"])


# --------------------------------------------------------------------------- #
# Replay evidence (deliverable G)
# --------------------------------------------------------------------------- #
def test_replay_evidence_passes(synthetic_session):
    work, pkg, summary = synthetic_session
    result = run_session_replay(session_dir=str(pkg), data_root=str(work))
    assert result.signals_match, result.signals_mismatches
    assert result.fact_identity_match, result.fact_diff
    assert result.ledger_match, result.ledger_mismatches
    assert result.live_signals >= 2 and result.replay_signals == result.live_signals
    assert result.replay_guard_events == {}
    assert not result.replay_reverse_divergence
    assert result.pass_
    assert (pkg / "replay_result.json").exists()


# --------------------------------------------------------------------------- #
# Kill-switch drill (deliverable H)
# --------------------------------------------------------------------------- #
def test_kill_switch_drill_passes(synthetic_session):
    work, pkg, summary = synthetic_session
    try:
        result = run_drill(session_dir=str(pkg), data_root=str(work))
        assert result.kill_switch_journaled
        assert result.kill_switch_count == 1
        assert result.entry_block_journaled
        assert result.fills_after_stop == 0
        assert result.loop_completed
        assert result.recovery_fills > 0
        assert result.recovery_clean
        assert result.pass_
        assert (pkg / "drill" / "drill_result.json").exists()
    finally:
        stop = Path.cwd() / "STOP"
        if stop.exists():
            stop.unlink()


# --------------------------------------------------------------------------- #
# Report assembly (deliverable I)
# --------------------------------------------------------------------------- #
_G1 = "11111111-2222-3333-4444-555555555555"
_G2 = "aaaaaaaa-0000-0000-0000-000000000000"


def _margin_event(gid=_G1, session="2026-08-11", structure="SPREAD",
                  legs=("NIFTY11AUG2623950CE", "NIFTY11AUG2624100CE")):
    return {
        "timestamp": f"{session} 13:00:00+05:30",
        "event_type": EventType.ENTRY_MARGIN.value, "severity": "INFO",
        "source_component": "NiftyShieldExecutionHandler",
        "message": "structure margin",
        "metadata": {"group_id": gid, "session": session, "structure": structure,
                     "lots": 2, "lot_size": 75, "margin_total": 18000.0,
                     "span": 15000.0, "elm": 3000.0, "engine": "NseMarginEngine",
                     "leg_symbols": list(legs), "risk_r": 15000.0},
    }


def _close_event(gid=_G1, session="2026-08-11", reason="time_exit"):
    return {
        "timestamp": f"{session} 15:16:00+05:30",
        "event_type": EventType.STRUCTURE_CLOSE.value, "severity": "INFO",
        "source_component": "NiftyShieldExecutionHandler",
        "message": "structure closed",
        "metadata": {"group_id": gid, "session": session, "reason": reason},
    }


def _window_fixture(tmp_path) -> Path:
    """3-session window: (a) clean+closed+recorded [counts], (b) telemetry-gap,
    (c) --no-record. Closed structures on both (a) and (b) so the RT count must
    drop from raw 2 to counting 1."""
    data_root = tmp_path / "window"
    data_root.mkdir()
    journal = data_root / "journal.jsonl"
    with open(journal, "w", encoding="utf-8") as f:
        f.write(json.dumps(_margin_event(gid=_G1, session="2026-08-11")) + "\n")
        f.write(json.dumps(_close_event(gid=_G1, session="2026-08-11")) + "\n")
        # closed structure inside the telemetry-gapped session (b) — must NOT
        # count toward the ≥30 round-trips headline.
        f.write(json.dumps(_margin_event(gid=_G2, session="2026-08-12")) + "\n")
        f.write(json.dumps(_close_event(gid=_G2, session="2026-08-12")) + "\n")
    trading_dir = data_root / "trading"
    trading_dir.mkdir(parents=True)
    con = sqlite3.connect(str(trading_dir / "trading.db"))
    con.execute("""
        CREATE TABLE trades (
            trade_id TEXT, signal_id TEXT, timestamp TEXT, symbol TEXT,
            side TEXT, quantity REAL, entry_price REAL, exit_price REAL,
            pnl REAL, fees REAL, metadata TEXT
        )
    """)
    con.executemany("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
        ("t1", "s1", "2026-08-11", "NIFTY11AUG2623950CE", "SELL", 150, 100.0, 0, 0, 0, "{}"),
        ("t2", "s2", "2026-08-11", "NIFTY11AUG2624100CE", "BUY", 150, 20.0, 0, 0, 0, "{}"),
        ("t3", "s3", "2026-08-12", "NIFTY12AUG2623950CE", "SELL", 150, 100.0, 0, 0, 0, "{}"),
        ("t4", "s4", "2026-08-12", "NIFTY12AUG2624100CE", "BUY", 150, 20.0, 0, 0, 0, "{}"),
    ])
    con.commit()
    con.close()

    def _session(d, replay_inputs, clean):
        pkg = data_root / "sessions" / d
        pkg.mkdir(parents=True)
        (pkg / "session_summary.json").write_text(json.dumps({
            "session_date": d, "replay_inputs": replay_inputs,
        }), encoding="utf-8")
        (pkg / "telemetry.json").write_text(json.dumps({
            "session": d, "clean": clean,
            "violations": [] if clean
            else ["bars_processed(100) > loop_iterations(90)"],
            "snapshot": {"bars_processed": 361},
        }), encoding="utf-8")

    _session("2026-08-11", True, True)     # counts toward the window
    _session("2026-08-12", True, False)    # telemetry-gap -> excluded
    _session("2026-08-13", False, True)    # --no-record -> excluded
    return data_root


def _report_skeleton_path() -> Path:
    return (Path(__file__).resolve().parents[2] / "docs" / "strategies"
            / "nifty_shield_v1" / "PAPER_VALIDATION_REPORT.skeleton.md")


def test_counting_predicate_window_fixture(tmp_path, monkeypatch):
    """F-B1: the ≥20/≥30 headline counts only sessions that count — telemetry
    clean AND recorded AND ≥1 closed structure — and the exclusion is auditable
    (raw + counting surfaced, excluded sessions with reasons)."""
    from scripts.nifty_shield_paper.assemble_report import (
        assemble, load_window_evidence,
    )
    data_root = _window_fixture(tmp_path)
    evidence = load_window_evidence(data_root)
    counting = evidence["counting"]
    assert counting["sessions_total"] == 3
    assert counting["sessions_counting"] == 1
    excluded = {d["session"]: d["exclusion_reasons"]
                for d in counting["sessions_excluded"]}
    assert excluded["2026-08-12"] == ["telemetry-gap"]
    assert excluded["2026-08-13"] == ["not-recorded (--no-record)",
                                      "no-closed-structure"]
    assert counting["round_trips_total"] == 2      # includes the gapped session
    assert counting["round_trips_counting"] == 1   # only the counting session

    report = tmp_path / "PAPER_VALIDATION_REPORT.md"
    skeleton = tmp_path / "PAPER_VALIDATION_REPORT.skeleton.md"
    skeleton.write_text(_report_skeleton_path().read_text(encoding="utf-8"),
                        encoding="utf-8")
    monkeypatch.setattr("scripts.nifty_shield_paper.assemble_report._commit_ref",
                        lambda: "testcommit")
    assemble(data_root=data_root, report_path=report, skeleton_path=skeleton)
    text = report.read_text(encoding="utf-8")
    assert "**1 / ≥20 required**" in text          # counting N, not 3
    assert "**1 / ≥30 required**" in text          # counting RT, not 2
    assert "raw 3" in text
    assert "raw 2" in text
    assert "telemetry-gap" in text
    assert "not-recorded (--no-record)" in text


def test_assemble_report_fills_skeleton(synthetic_session, tmp_path, monkeypatch):
    work, pkg, summary = synthetic_session
    report = tmp_path / "PAPER_VALIDATION_REPORT.md"
    skeleton = tmp_path / "PAPER_VALIDATION_REPORT.skeleton.md"
    skeleton.write_text(_report_skeleton_path().read_text(encoding="utf-8"),
                        encoding="utf-8")
    monkeypatch.setattr("scripts.nifty_shield_paper.assemble_report._commit_ref",
                        lambda: "testcommit")
    result = assemble(data_root=work, report_path=report, skeleton_path=skeleton)
    text = report.read_text(encoding="utf-8")
    assert "**[FILL AT CLOSE]**" not in text
    assert "**[count] / ≥20 required**" not in text
    assert "**1 / ≥20 required**" in text
    assert "**1 / ≥30 required**" in text
    assert "[FILLED:" in text
    assert (work / "window_evidence.json").exists()


def test_assemble_idempotent_default_path(tmp_path, monkeypatch):
    """F-B2: assembling twice against the default path must both succeed and
    produce identical output — the skeleton template is never overwritten."""
    import scripts.nifty_shield_paper.assemble_report as ar
    data_root = _window_fixture(tmp_path)
    tmp_skeleton = tmp_path / "PAPER_VALIDATION_REPORT.skeleton.md"
    tmp_report = tmp_path / "PAPER_VALIDATION_REPORT.md"
    tmp_skeleton.write_text(_report_skeleton_path().read_text(encoding="utf-8"),
                            encoding="utf-8")
    # Point the module defaults at a temp mirror (running against the tracked
    # path in CI would dirty the tree); assemble() uses its default resolution.
    monkeypatch.setattr(ar, "SKELETON_PATH", tmp_skeleton)
    monkeypatch.setattr(ar, "REPORT_PATH", tmp_report)
    monkeypatch.setattr(ar, "_commit_ref", lambda: "testcommit")
    ar.assemble(data_root=data_root)
    first = tmp_report.read_bytes()
    ar.assemble(data_root=data_root)          # second run must not raise
    second = tmp_report.read_bytes()
    assert first == second
    # the skeleton (template) still carries the markers after both runs
    assert "**[FILL AT CLOSE]**" in tmp_skeleton.read_text(encoding="utf-8")


def test_skeleton_is_immutable_template_and_report_is_generated(tmp_path):
    """F-B2 structural guard: the tracked skeleton holds the markers; the
    tracked report is generated output with the banner."""
    root = Path(__file__).resolve().parents[2]
    skel = root / "docs" / "strategies" / "nifty_shield_v1" \
        / "PAPER_VALIDATION_REPORT.skeleton.md"
    report = root / "docs" / "strategies" / "nifty_shield_v1" \
        / "PAPER_VALIDATION_REPORT.md"
    assert skel.exists()
    assert "**[FILL AT CLOSE]**" in skel.read_text(encoding="utf-8")
    assert ("GENERATED by scripts/nifty_shield_paper"
            in report.read_text(encoding="utf-8"))


def test_assemble_report_fails_on_changed_skeleton(tmp_path):
    skeleton = tmp_path / "skeleton.md"
    report = tmp_path / "report.md"
    skeleton.write_text(
        "## 2. Window\n"
        "| Window dates | **[FILL AT CLOSE]** |\n"
        "| Sessions | **[count] / ≥20 required** |\n"
        "| Sessions | **[count] / ≥20 required** |\n",
        encoding="utf-8")
    from scripts.nifty_shield_paper.assemble_report import assemble
    with pytest.raises(RuntimeError):
        assemble(data_root=tmp_path, report_path=report, skeleton_path=skeleton)


# --------------------------------------------------------------------------- #
# Telemetry + audit per-session evidence
# --------------------------------------------------------------------------- #
def test_session_telemetry_archived(synthetic_session):
    work, pkg, summary = synthetic_session
    telemetry = json.loads((pkg / "telemetry.json").read_text(encoding="utf-8"))
    assert telemetry["clean"] is True
    assert telemetry["snapshot"]["bars_processed"] == 361


# --------------------------------------------------------------------------- #
# New composition-root seams
# --------------------------------------------------------------------------- #
def test_build_runner_wires_watchdog_factory(tmp_path, monkeypatch):
    """The Phase-B watchdog_factory seam wires a watchdog on the driver."""
    import core.execution.handler as handler_mod
    from core.clock import ReplayClock
    from core.database.manager import DatabaseManager
    from core.execution.persistence.execution_store import ExecutionStore
    from core.execution.handler import ExecutionMode
    from core.runtime.config import Mode
    from core.runtime.signal_source import SignalSource
    from core.events import OHLCVBar
    from scripts.fno_runner import build_runner

    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()

    class _Src(SignalSource):
        def on_bar(self, bar: OHLCVBar):
            return []

    calls = []

    def wf(execution):
        calls.append(execution)
        return "watchdog-stub"

    driver = build_runner(
        source=_Src(), symbols=["NSE_EQ|INE001A01036"],
        execution_mode=ExecutionMode.PAPER,
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=ReplayClock(datetime(2026, 6, 5, 9, 15, 0)),
        journal=None, max_bars=1, watchdog_factory=wf, mode=Mode.LIVE,
    )
    assert calls
    assert driver._watchdog == "watchdog-stub"


def test_recorder_wraps_provider_and_captures_bars(tmp_path):
    """The recorder's provider seam captures every bar delivered."""
    from scripts.nifty_shield_paper.recorder import SessionRecorder
    rec = SessionRecorder(str(tmp_path / "pkg"))
    bars = [
        OHLCVBar(symbol="S", timestamp=datetime(2026, 6, 5, 9, 15),
                 open=1.0, high=2.0, low=1.0, close=2.0, volume=100.0),
        OHLCVBar(symbol="S", timestamp=datetime(2026, 6, 5, 9, 16),
                 open=2.0, high=3.0, low=2.0, close=3.0, volume=200.0),
    ]
    wrapped = rec.wrap_provider(_SessionBarProvider(bars))
    assert wrapped.get_next_bar("S") == bars[0]
    assert wrapped.get_next_bar("S") == bars[1]
    assert rec.driver_bars == bars
    assert rec.session_date == date(2026, 6, 5)


# --------------------------------------------------------------------------- #
# F-B3 — the drill must never leak a STOP file
# --------------------------------------------------------------------------- #
def test_drill_never_leaks_stop_on_failure(synthetic_session, monkeypatch):
    """F-B3: a crash between the STOP write and Phase 2 must never leave a STOP
    file in the operator's CWD (a leaked STOP silently kill-switches the next
    live session)."""
    import scripts.nifty_shield_paper.drill as drill_mod
    work, pkg, summary = synthetic_session
    real_build = drill_mod.build_replay_driver
    calls = {"n": 0}

    def failing_recovery(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 2:              # Phase 2 (recovery) build raises
            raise RuntimeError("recovery build failed mid-drill")
        return real_build(*a, **k)

    monkeypatch.setattr(drill_mod, "build_replay_driver", failing_recovery)
    with pytest.raises(RuntimeError):
        run_drill(session_dir=str(pkg), data_root=str(work))
    assert not (Path.cwd() / "STOP").exists(), \
        "STOP file leaked into CWD after a failed drill"


# --------------------------------------------------------------------------- #
# F-B4 — LIVE-only evidence paths get real coverage
# --------------------------------------------------------------------------- #
def test_span_snapshot_roundtrip(tmp_path):
    """F-B4: a non-None span_snapshot is captured to span_snapshot.pkl with a
    non-null hash in meta.json and loads back as an equal object."""
    from scripts.nifty_shield_paper.recorder import (
        SessionRecorder, load_span_snapshot,
    )

    rec = SessionRecorder(str(tmp_path / "pkg"))
    rec.record_bar(OHLCVBar(symbol="S", timestamp=datetime(2026, 6, 5, 9, 15),
                            open=1.0, high=2.0, low=1.0, close=2.0,
                            volume=100.0))
    rec.finalize(facts_db_path=str(tmp_path / "none.duckdb"),
                 span_snapshot=_StubSnapshot())
    pkg = tmp_path / "pkg"
    assert (pkg / "span_snapshot.pkl").exists()
    meta = json.loads((pkg / "meta.json").read_text(encoding="utf-8"))
    assert meta["span_snapshot_hash"] == "testhash123"
    loaded = load_span_snapshot(str(pkg))
    assert isinstance(loaded, _StubSnapshot)
    assert loaded.file_hash == "testhash123"


def test_live_watchdog_writes_real_heartbeat(tmp_path, monkeypatch):
    """F-B4: the LIVE composition root constructs a REAL RuntimeWatchdog and a
    driven tick writes heartbeat.json (not a stub)."""
    from core.execution.watchdog import RuntimeWatchdog
    monkeypatch.setattr(runner_mod, "_load_span_snapshot", lambda: None)
    work = tmp_path / "live"
    work.mkdir()
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=work)
    with dm.trading_writer() as conn:
        conn.execute(TRADING_TRADES_SCHEMA)
    journal = RuntimeEventJournal(str(work / "journal.jsonl"))
    telemetry = InMemoryTelemetrySink()
    bars = [
        OHLCVBar(symbol=NF_SYMBOL, timestamp=datetime(2026, 6, 5, 9, 15),
                 open=1.0, high=2.0, low=1.0, close=2.0, volume=1000.0),
    ]
    driver = runner_mod.build_nifty_shield_paper_driver(
        mode=Mode.LIVE, db_manager=dm, journal=journal, telemetry=telemetry,
        marks_source=StaticMarksSource({}),
        facts_db_path=str(work / "facts.duckdb"),
        chain_db_path=str(work / "chain.duckdb"),
        metrics_path=str(work / "metrics.json"),
        heartbeat_path=str(work / "heartbeat.json"),
        execution_store_path=str(work / "execution.db"),
        initial_capital=1_000_000.0, max_bars=1,
        provider=_SessionBarProvider(bars))
    driver.run()
    assert isinstance(driver._watchdog, RuntimeWatchdog)
    hb = work / "heartbeat.json"
    assert hb.exists(), "LIVE heartbeat was not written"
    data = json.loads(hb.read_text(encoding="utf-8"))
    assert "timestamp" in data and "bars_processed" in data
    assert data["bars_processed"] >= 1
