"""nifty_shield_v1 — read-only regime/VIX facts reader (Decomposition §6, D2).

Provides per-session 13pm regime/VIX fact lookups keyed by session_date. The
reader is lazy / re-queryable (DS2-1): `fact(session_date)` caches per session
and re-queries the store on a miss, so a live session whose 13:00 fact was
published intraday (DS2-2) is visible at the 13:00 bar — a start-of-run
snapshot would not see it. Read-only; each query opens and closes its own
connection (the source holds no live connection). The model is NOT run here —
the fact is already published by the DayType facts publisher (offline or live).

DS2-3: the reader surfaces `vix_at_checkpoint` (the intraday ~13:00 India VIX
carried by live rows) alongside the legacy EOD `vix_close`. Stores created
before DS2-3 (and the frozen conformance corpus) have no such column — the
reader detects its absence and returns None, and the source falls back to
`vix_close` (a provable offline no-op).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Optional

import duckdb

_CHECKPOINT_COL = "vix_at_checkpoint"


class RegimeFactsReader:
    """Read-only, lazy reader over a day_type_facts DuckDB (checkpoint='13pm')."""

    def __init__(self, db_path: str):
        self._path = Path(db_path)
        self._cache: Dict[date, Optional[dict]] = {}

    def fact(self, session_date: date) -> Optional[dict]:
        """Return the 13pm fact for `session_date`, or None if absent.

        Per-session cached; a miss re-queries the store so a fact published
        after the first lookup becomes visible on a later call. The column
        shape is re-detected per query so a store migrated mid-run (DS2-3)
        is read correctly.
        """
        if session_date in self._cache:
            return self._cache[session_date]
        fact = self._query(session_date)
        if fact is not None:
            self._cache[session_date] = fact
        return fact

    def _query(self, session_date: date) -> Optional[dict]:
        if not self._path.exists():
            return None
        has_cp = self._store_has_checkpoint_col()
        if has_cp:
            select = ("session_date, regime, regime_confidence, vix_close, "
                      "vix_at_checkpoint, regime_fact_version, model_hash")
        else:
            select = ("session_date, regime, regime_confidence, vix_close, "
                      "regime_fact_version, model_hash")
        con = duckdb.connect(str(self._path), read_only=True)
        try:
            row = con.execute(
                f"SELECT {select} FROM day_type_facts "
                "WHERE checkpoint = '13pm' AND session_date = ?",
                [session_date],
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        if has_cp:
            _, regime, conf, vix, vix_cp, ver, mhash = row
        else:
            _, regime, conf, vix, ver, mhash = row
            vix_cp = None
        return {
            "regime": regime,
            "regime_confidence": float(conf),
            "vix_close": float(vix) if vix is not None else None,
            "vix_at_checkpoint": float(vix_cp) if vix_cp is not None else None,
            "regime_fact_version": ver,
            "model_hash": mhash,
        }

    def _store_has_checkpoint_col(self) -> bool:
        con = duckdb.connect(str(self._path), read_only=True)
        try:
            cols = {str(r[1]) for r in
                    con.execute("PRAGMA table_info('day_type_facts')").fetchall()}
        finally:
            con.close()
        return _CHECKPOINT_COL in cols
