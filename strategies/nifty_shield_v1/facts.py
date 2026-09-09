"""nifty_shield_v1 — read-only regime/VIX facts reader (Decomposition §6, D2).

Provides per-session 13pm regime/VIX fact lookups keyed by session_date. The
reader is lazy / re-queryable (DS2-1): `fact(session_date)` caches per session
and re-queries the store on a miss, so a live session whose 13:00 fact was
published intraday (DS2-2) is visible at the 13:00 bar — a start-of-run
snapshot would not see it. Read-only; each query opens and closes its own
connection (the source holds no live connection). The model is NOT run here —
the fact is already published by the DayType facts publisher (offline or live).

HORIZON (audit Finding A, resolved by disclosure): the regime label this reads is
a **full-session** (09:15-15:29) KMeans cluster, predicted at 13:00 from partial
features, and consumed over 13:00-15:15. It is a **directional prior**, not a
same-horizon forecast. What the evidence supports is a BullTrend-minus-BearTrend
forward-window separation of +0.255 pp (95% CI [+0.197, +0.312], n=1606 OOS
sessions). The trainer's 75-85% checkpoint accuracy is accuracy against the
full-session label and says nothing directly about the traded window, and
`regime_confidence` is confidence in the full-session class rather than a
probability about the afternoon. Do not derive a threshold or sizing rule as if
the label described 13:00-15:15.
See docs/reports/index_research/DAYTYPE_HORIZON_DISCLOSURE.md

DS2-3: the reader surfaces `vix_at_checkpoint` (the intraday ~13:00 India VIX
carried by live rows) alongside the legacy EOD `vix_close`. Stores created
before DS2-3 (and the frozen conformance corpus) have no such column — the
reader detects its absence and returns None, and the source falls back to
`vix_close` (a provable offline no-op).

`vix_pctile` (2026-09-08) is handled the same way: where the column exists the
reader surfaces this session's India VIX as a percentile of its own trailing
distribution, which is what the structure gates key on. Absent, it is None and
`select_structure` falls through to the calmest branch — the behaviour the
absolute gates produced in every live session, so an un-migrated store cannot
silently start trading a structure it has never traded.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Optional

import duckdb

_CHECKPOINT_COL = "vix_at_checkpoint"
_PCTILE_COL = "vix_pctile"


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
        cols = self._store_columns()
        has_cp = _CHECKPOINT_COL in cols
        has_pct = _PCTILE_COL in cols
        select = "session_date, regime, regime_confidence, vix_close"
        if has_cp:
            select += ", vix_at_checkpoint"
        if has_pct:
            select += ", vix_pctile"
        select += ", regime_fact_version, model_hash"
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
        vals = list(row)
        _, regime, conf, vix = vals[:4]
        rest = vals[4:]
        vix_cp = rest.pop(0) if has_cp else None
        vix_pct = rest.pop(0) if has_pct else None
        ver, mhash = rest[0], rest[1]
        return {
            "regime": regime,
            "regime_confidence": float(conf),
            "vix_close": float(vix) if vix is not None else None,
            "vix_at_checkpoint": float(vix_cp) if vix_cp is not None else None,
            "vix_pctile": float(vix_pct) if vix_pct is not None else None,
            "regime_fact_version": ver,
            "model_hash": mhash,
        }

    def _store_columns(self) -> set:
        con = duckdb.connect(str(self._path), read_only=True)
        try:
            return {str(r[1]) for r in
                    con.execute("PRAGMA table_info('day_type_facts')").fetchall()}
        finally:
            con.close()
