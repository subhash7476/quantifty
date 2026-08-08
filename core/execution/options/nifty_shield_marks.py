"""NiftyShield — option-marks feed (E007 E7-4, datasheet §11 open item).

The PAPER fill price for a struck option leg must be a REAL option-chain mark —
never the underlying's bar close and never a synthetic/flat-IV mark. The
external backtest's Sharpe 9.40 was flagged optimistic precisely for synthetic
marks; PAPER must not repeat that.

This module defines the marks-seam the execution layer prices legs against:

- `OptionMarksSource` — the seam (per-leg `marks(symbols)` -> price map).
- `StaticMarksSource` — deterministic marks (tests, smoke run).
- `ChainSnapshotMarksSource` — REAL Upstox V3 option-chain marks read from the
  latest `option_chain_snapshot` DuckDB cache (tradingsymbol -> ltp).

F3 (loud infra failures): `ChainSnapshotMarksSource` distinguishes TWO absence
classes, because the two mean different things and one of them must be LOUD:

- **Cache unavailable** (file missing, DB corrupt, query/parse failure) — raises
  `MarksSourceUnavailable`. A misconfigured live window must not silently skip
  every entry as "missing marks" (the repo's documented "bare except turns 'we
  failed' into 'the source doesn't have it'" pitfall).
- **Market closed / strikes not in the snapshot** (cache valid, query succeeds,
  no rows) — returns `{}` (a legitimate no-mark, journaled as an entry skip).

`check_available()` is the startup validation the runner calls before a live
window opens: a broken cache refuses to start, it never silently runs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

import duckdb


class MarksSourceUnavailable(RuntimeError):
    """The marks cache is absent/corrupt/unreadable — infra, not market state."""


class OptionMarksSource(ABC):
    """Per-symbol option premium marks for a set of struck legs."""

    @abstractmethod
    def marks(self, symbols: List[str]) -> Dict[str, float]:
        """Return the current premium for each symbol it can price (subset of
        `symbols`); symbols without a real mark are simply absent."""


class StaticMarksSource(OptionMarksSource):
    """A fixed mark table — deterministic, for tests and the REPLAY smoke run."""

    def __init__(self, marks: Dict[str, float]):
        self._marks = dict(marks)

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        return {s: self._marks[s] for s in symbols if s in self._marks}


class ChainSnapshotMarksSource(OptionMarksSource):
    """Real option-chain marks from the latest option_chain_snapshot snapshot.

    Reads `ltp` for each requested `tradingsymbol` from the most recent
    `snapshot_timestamp` in the cache DB. Raises `MarksSourceUnavailable` when
    the cache itself is unavailable (F3); returns {} only for a VALID cache with
    no rows for the requested symbols (market closed / strikes absent).
    """

    def __init__(self, db_path: str, table: str = "option_chain_snapshot"):
        self._db_path = db_path
        self._table = table

    def check_available(self) -> None:
        """Startup gate: raise MarksSourceUnavailable if the cache cannot open."""
        self._connect()

    def _connect(self):
        try:
            con = duckdb.connect(self._db_path, read_only=True)
        except Exception as exc:
            raise MarksSourceUnavailable(
                f"option-chain cache unavailable at {self._db_path}: {exc}"
            ) from exc
        return con

    def _latest_timestamp(self, con) -> object:
        try:
            row = con.execute(
                f"SELECT MAX(snapshot_timestamp) FROM {self._table}"
            ).fetchone()
        except Exception as exc:
            raise MarksSourceUnavailable(
                f"option-chain cache query failed (table {self._table!r}): {exc}"
            ) from exc
        return row[0] if row else None

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        if not symbols:
            return {}
        con = self._connect()
        try:
            latest = self._latest_timestamp(con)
            if latest is None:
                return {}                    # valid cache, no snapshot yet
            placeholders = ", ".join("?" for _ in symbols)
            try:
                rows = con.execute(
                    f"SELECT tradingsymbol, ltp FROM {self._table} "
                    f"WHERE snapshot_timestamp = ? "
                    f"AND tradingsymbol IN ({placeholders})",
                    [latest] + list(symbols),
                ).fetchall()
            except Exception as exc:
                raise MarksSourceUnavailable(
                    f"option-chain cache query failed: {exc}") from exc
        finally:
            con.close()
        return {sym: float(ltp) for sym, ltp in rows
                if ltp is not None and float(ltp) > 0.0}
