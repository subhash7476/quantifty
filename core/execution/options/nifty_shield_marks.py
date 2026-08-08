"""NiftyShield — option-marks feed (E007 E7-4, datasheet §11 open item).

The PAPER fill price for a struck option leg must be a REAL option-chain mark —
never the underlying's bar close and never a synthetic/flat-IV mark. The
external backtest's Sharpe 9.40 was flagged optimistic precisely for synthetic
marks; PAPER must not repeat that.

This module defines the marks-seam the execution layer prices legs against:

- `OptionMarksSource` — the seam (per-leg `marks(symbols)` -> price map).
- `StaticMarksSource` — deterministic marks (tests, smoke run).
- `ChainSnapshotMarksSource` — REAL Upstox V3 option-chain marks read from the
  latest `option_chain_snapshot` DuckDB cache (tradingsymbol -> ltp). Phase B
  wires the live chain feed into that cache; the seam is already real.

A struck leg with no available mark is a journaled gate outcome to audit — the
handler never fabricates a mark (E7-4: no synthetic fallback).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import duckdb


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
    `snapshot_timestamp` in the cache DB. Absent rows -> absent from the result
    (the handler journals the missing-mark gate outcome; no synthetic fallback).
    """

    def __init__(self, db_path: str,
                 table: str = "option_chain_snapshot"):
        self._db_path = db_path
        self._table = table

    def marks(self, symbols: List[str]) -> Dict[str, float]:
        if not symbols:
            return {}
        try:
            con = duckdb.connect(self._db_path, read_only=True)
        except Exception:
            return {}
        try:
            placeholders = ", ".join("?" for _ in symbols)
            rows = con.execute(
                f"SELECT tradingsymbol, ltp FROM {self._table} "
                f"WHERE snapshot_timestamp = (SELECT MAX(snapshot_timestamp) "
                f"FROM {self._table}) AND tradingsymbol IN ({placeholders})",
                list(symbols),
            ).fetchall()
        except Exception:
            rows = []
        finally:
            con.close()
        return {sym: float(ltp) for sym, ltp in rows
                if ltp is not None and float(ltp) > 0.0}
