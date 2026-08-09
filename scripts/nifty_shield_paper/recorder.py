"""NiftyShield — Stage-2 PAPER session recorder + replay seams (E007 Phase B).

The forward-window (Phase B) runner records exactly what the LIVE composition
root consumed, so the replay-evidence item (deliverable G) can re-drive a
session deterministically and prove the pipeline is repeatable:

- the driver's bar stream (`RecordingMarketDataProvider`),
- every option-marks call and its result (`RecordingMarksSource`),
- the emitted signal stream (`RecordingSignalSource`),
- the session's regime-fact store + full-session NF/BN/VIX bar corpus (for the
  live fact publisher, which re-reads those bars to recompute the 13:00 fact).

Session package (written by `SessionRecorder.finalize`):

    {data_root}/nifty_shield/sessions/{YYYY-MM-DD}/
        meta.json          session date, platform commit, recorder schema version
        bars.duckdb        recorded driver bar stream (table `driver_bars`) +
                           full-session NF/BN/VIX bars (table `session_bars`)
        facts_bars/{d}.duckdb  per-day-store copy the replay fact hook reads
        marks.jsonl        recorded marks call log (call order, incl. outages)
        signals.jsonl      recorded signal stream (deterministic fields)
        facts.duckdb       day_type_facts store copy at session close

Replay seams:

- `ReplayMarksSource` serves the recorded marks log in call order, asserting the
  requested symbol set matches the recorded call (a determinism check), and
  raising `MarksSourceUnavailable` where the live call did — so the F3 loud
  outage path reproduces through replay.
- `ReplayBarProvider` serves the recorded driver bar stream in order.
- `ReplayDivergence` is raised on any non-determinism the harness must surface.

Runner/composition code only — the frozen strategy package is untouched.
"""
from __future__ import annotations

import dataclasses
import json
import pickle
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import duckdb

from core.database.providers.base import MarketDataProvider
from core.events import OHLCVBar, SignalEvent
from core.execution.options.nifty_shield_marks import (
    MarksSourceUnavailable, OptionMarksSource,
)
from core.runtime.signal_source import SignalSource

_IST = ZoneInfo("Asia/Kolkata")

# The three regime-fact inputs the live fact publisher reads (publish_live_fact).
SESSION_SYMBOLS = (
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|India VIX",
)

RECORDER_VERSION = "1.0.0"


class ReplayDivergence(RuntimeError):
    """A recorded session re-driven through the composition root diverged."""


def _now_iso() -> str:
    return datetime.now(_IST).isoformat()


def _normalize_signal(signal: SignalEvent) -> dict:
    """Deterministic JSON-safe projection of a SignalEvent (replay diff key)."""
    out = {
        "strategy_id": signal.strategy_id,
        "symbol": signal.symbol,
        "timestamp": signal.timestamp.isoformat(),
        "signal_type": signal.signal_type.value,
        "confidence": signal.confidence,
        "metadata": signal.metadata,
    }
    if signal.context is not None:
        out["context"] = dataclasses.asdict(signal.context)
    return out


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --------------------------------------------------------------------------- #
# Recording wrappers
# --------------------------------------------------------------------------- #
class RecordingMarksSource(OptionMarksSource):
    """Wraps the real marks source, recording every call (incl. outages)."""

    def __init__(self, inner: OptionMarksSource, recorder: "SessionRecorder"):
        self._inner = inner
        self._recorder = recorder

    def check_available(self) -> None:
        check = getattr(self._inner, "check_available", None)
        if check is not None:
            check()

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        try:
            result = self._inner.marks(symbols)
        except MarksSourceUnavailable as exc:
            self._recorder.record_marks(symbols, None, exc)
            raise
        self._recorder.record_marks(symbols, result, None)
        return result


class RecordingSignalSource(SignalSource):
    """Wraps a strategy source, capturing the emitted signal stream."""

    def __init__(self, inner: SignalSource, recorder: "SessionRecorder"):
        self._inner = inner
        self._recorder = recorder

    def on_start(self, context=None) -> None:
        return self._inner.on_start(context)

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        signals = self._inner.on_bar(bar)
        self._recorder.record_signals(signals)
        return signals

    def on_stop(self) -> None:
        return self._inner.on_stop()


class RecordingMarketDataProvider(MarketDataProvider):
    """Wraps the live provider, recording every bar delivered to the driver."""

    def __init__(self, inner: MarketDataProvider, recorder: "SessionRecorder"):
        super().__init__(inner.symbols)
        self._inner = inner
        self._recorder = recorder

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        bar = self._inner.get_next_bar(symbol)
        if bar is not None:
            self._recorder.record_bar(bar)
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

    def stop(self) -> None:
        stop = getattr(self._inner, "stop", None)
        if stop is not None:
            stop()

    def start(self) -> None:
        start = getattr(self._inner, "start", None)
        if start is not None:
            start()


# --------------------------------------------------------------------------- #
# Session recorder
# --------------------------------------------------------------------------- #
class SessionRecorder:
    """Accumulates what a live session consumed; `finalize` writes the package."""

    def __init__(self, package_dir: str):
        self._package_dir = Path(package_dir)
        self._driver_bars: List[OHLCVBar] = []
        self._marks_log: List[dict] = []
        self._signals: List[dict] = []
        self._session_date: Optional[date] = None
        self._started_at = _now_iso()

    @property
    def package_dir(self) -> Path:
        return self._package_dir

    @property
    def session_date(self) -> Optional[date]:
        return self._session_date

    @property
    def signals(self) -> List[dict]:
        """Captured signal stream (used by the replay side's own recorder)."""
        return list(self._signals)

    @property
    def driver_bars(self) -> List[OHLCVBar]:
        return list(self._driver_bars)

    def wrap_source(self, source: SignalSource) -> SignalSource:
        return RecordingSignalSource(source, self)

    def wrap_marks(self, marks: OptionMarksSource) -> OptionMarksSource:
        return RecordingMarksSource(marks, self)

    def wrap_provider(self, provider: MarketDataProvider) -> MarketDataProvider:
        return RecordingMarketDataProvider(provider, self)

    # --- record hooks ----------------------------------------------------- #
    def record_bar(self, bar: OHLCVBar) -> None:
        if self._session_date is None:
            self._session_date = bar.timestamp.date()
        self._driver_bars.append(bar)

    def record_marks(self, symbols: List[str], result: Optional[dict],
                     error: Optional[Exception]) -> None:
        rec = {"n": len(self._marks_log) + 1, "symbols": list(symbols)}
        if error is not None:
            rec["outage"] = str(error)
        else:
            rec["marks"] = dict(result or {})
        self._marks_log.append(rec)

    def record_signals(self, signals: List[SignalEvent]) -> None:
        self._signals.extend(_normalize_signal(s) for s in signals)

    # --- finalize --------------------------------------------------------- #
    def finalize(self, *, facts_db_path: str,
                 per_day_store: Optional[str] = None,
                 live_buffer: Optional[str] = None,
                 platform_commit: str = "unknown",
                 span_snapshot: Optional[object] = None) -> dict:
        """Write the session package under the recorder's package_dir.

        Facts are copied from `facts_db_path`; the full-session NF/BN/VIX bar
        corpus is taken from the per-day 1m store (canonical) or the live
        buffer (fallback) — the same sources the live fact hook read. A non-None
        `span_snapshot` (the margin engine's SPAN input the live session priced
        against) is captured so replay reproduces the exact margin figures.
        """
        if self._session_date is None:
            raise ReplayDivergence(
                "session recorder finalized with no session bar consumed")
        pkg = self._package_dir
        pkg.mkdir(parents=True, exist_ok=True)
        session = self._session_date

        _write_driver_bars(pkg / "bars.duckdb", self._driver_bars)
        session_rows = _extract_session_bars(
            session, per_day_store=per_day_store, live_buffer=live_buffer)
        if session_rows:
            _write_session_bars(pkg / "bars.duckdb", session_rows)
            _write_candles_table(pkg / "facts_bars" / f"{session.isoformat()}.duckdb",
                                 session_rows)

        _write_jsonl(pkg / "marks.jsonl", self._marks_log)
        _write_jsonl(pkg / "signals.jsonl", self._signals)

        src = Path(facts_db_path)
        if src.exists():
            shutil.copy2(src, pkg / "facts.duckdb")

        span_hash = None
        if span_snapshot is not None:
            with open(pkg / "span_snapshot.pkl", "wb") as f:
                pickle.dump(span_snapshot, f)
            span_hash = getattr(span_snapshot, "file_hash", None)

        meta = {
            "session_date": session.isoformat(),
            "platform_commit": platform_commit,
            "recorder_version": RECORDER_VERSION,
            "started_at": self._started_at,
            "ended_at": _now_iso(),
            "driver_bars": len(self._driver_bars),
            "marks_calls": len(self._marks_log),
            "signals_emitted": len(self._signals),
            "session_bars_present": bool(session_rows),
            "span_snapshot_hash": span_hash,
        }
        (pkg / "meta.json").write_text(
            json.dumps(meta, indent=2, default=str), encoding="utf-8")
        return meta


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


def _write_driver_bars(db_path: Path, bars: List[OHLCVBar]) -> None:
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE IF NOT EXISTS driver_bars ("
                "symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
                "low DOUBLE, close DOUBLE, volume BIGINT)")
    con.executemany(
        "INSERT INTO driver_bars VALUES (?,?,?,?,?,?,?)",
        [(b.symbol, b.timestamp, float(b.open), float(b.high), float(b.low),
          float(b.close), int(b.volume)) for b in bars])
    con.close()


def _write_session_bars(db_path: Path, rows: List[tuple]) -> None:
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE IF NOT EXISTS session_bars ("
                "symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
                "low DOUBLE, close DOUBLE, volume BIGINT)")
    con.executemany("INSERT INTO session_bars VALUES (?,?,?,?,?,?,?)", rows)
    con.close()


def _write_candles_table(db_path: Path, rows: List[tuple]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE IF NOT EXISTS candles ("
                "symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, "
                "low DOUBLE, close DOUBLE, volume BIGINT)")
    con.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?)", rows)
    con.close()


def _write_jsonl(path: Path, records: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")


def _extract_session_bars(session: date, *, per_day_store: Optional[str],
                          live_buffer: Optional[str]) -> List[tuple]:
    """Full-session NF/BN/VIX 1m bars: per-day store first, then live buffer.

    The live buffer candles table carries extra columns (timeframe,
    instrument_key, is_synthetic); the per-day store is the plain 7-column
    shape. Both are normalized to (symbol, timestamp, open, high, low, close,
    volume).
    """
    if per_day_store and Path(per_day_store).exists():
        rows = _read_candle_db(Path(per_day_store))
        if rows:
            return rows
    if live_buffer and Path(live_buffer).exists():
        return _read_candle_db(Path(live_buffer))
    return []


def _read_candle_db(path: Path) -> List[tuple]:
    try:
        con = duckdb.connect(str(path), read_only=True)
        try:
            cols = {r[1] for r in con.execute(
                "PRAGMA table_info('candles')").fetchall()}
            if "timeframe" in cols:
                rows = con.execute(
                    "SELECT symbol, timestamp, open, high, low, close, volume "
                    "FROM candles WHERE timeframe = '1m' "
                    "ORDER BY symbol, timestamp").fetchall()
            else:
                rows = con.execute(
                    "SELECT symbol, timestamp, open, high, low, close, volume "
                    "FROM candles ORDER BY symbol, timestamp").fetchall()
        finally:
            con.close()
    except Exception:
        return []
    out = []
    for sym, ts, o, h, l, c, v in rows:
        if sym not in SESSION_SYMBOLS:
            continue
        out.append((sym, ts, float(o), float(h), float(l), float(c),
                    int(v if v is not None else 0)))
    return out


# --------------------------------------------------------------------------- #
# Replay seams
# --------------------------------------------------------------------------- #
class ReplayMarksSource(OptionMarksSource):
    """Serves the recorded marks log in call order; loud on divergence."""

    def __init__(self, marks_log_path: str):
        self._log = read_jsonl(Path(marks_log_path))
        self._idx = 0

    @property
    def calls_served(self) -> int:
        return self._idx

    def check_available(self) -> None:
        return None                       # a package log is always "available"

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        if self._idx >= len(self._log):
            raise ReplayDivergence(
                f"marks call {self._idx + 1} exceeds recorded log "
                f"({len(self._log)} calls)")
        rec = self._log[self._idx]
        self._idx += 1
        if sorted(rec["symbols"]) != sorted(symbols):
            raise ReplayDivergence(
                f"marks call {rec['n']}: requested {sorted(symbols)} != "
                f"recorded {sorted(rec['symbols'])} (non-deterministic call "
                f"sequence)")
        if "outage" in rec:
            raise MarksSourceUnavailable(rec["outage"])
        return dict(rec["marks"])


class ReplayBarProvider(MarketDataProvider):
    """Serves a recorded driver bar stream in order (a minimal REPLAY provider)."""

    def __init__(self, bars: List[OHLCVBar]):
        super().__init__([b.symbol for b in bars] or ["NSE_INDEX|Nifty 50"])
        self._bars = list(bars)

    def get_next_bar(self, symbol: str) -> Optional[OHLCVBar]:
        return self._bars.pop(0) if self._bars else None

    def get_latest_bar(self, symbol: str) -> Optional[OHLCVBar]:
        return self._bars[-1] if self._bars else None

    def is_data_available(self, symbol: str) -> bool:
        return bool(self._bars)

    def reset(self, symbol: str) -> None:
        return None

    def get_progress(self, symbol: str):
        return (0, len(self._bars))


def load_driver_bars(package_dir: str) -> List[OHLCVBar]:
    """Load the recorded driver bar stream from a session package."""
    db_path = Path(package_dir) / "bars.duckdb"
    if not db_path.exists():
        raise ReplayDivergence(f"session package has no bars.duckdb: {db_path}")
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = con.execute(
            "SELECT symbol, timestamp, open, high, low, close, volume "
            "FROM driver_bars ORDER BY rowid").fetchall()
    finally:
        con.close()
    return [
        OHLCVBar(symbol=sym, timestamp=ts, open=float(o), high=float(h),
                 low=float(l), close=float(c), volume=float(v))
        for sym, ts, o, h, l, c, v in rows
    ]


def load_span_snapshot(package_dir: str):
    """Load the captured SPAN snapshot from a session package (or None)."""
    pkl = Path(package_dir) / "span_snapshot.pkl"
    if not pkl.exists():
        return None
    try:
        with open(pkl, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None
