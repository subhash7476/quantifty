"""nifty_shield_v1 — read-only regime/VIX facts reader (Decomposition §6, D2).

Loads the day-type 13pm regime facts for the sessions the source will see,
keyed by session_date. Read-only; opened in on_start and closed immediately
(the source holds no live connection). The model is NOT run here — the fact is
already published offline by the DayType facts publisher.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Optional

import duckdb


class RegimeFactsReader:
    """Read-only reader over a day_type_facts DuckDB (checkpoint='13pm')."""

    def __init__(self, db_path: str):
        self._path = Path(db_path)

    def load(self) -> Dict[date, dict]:
        if not self._path.exists():
            return {}
        con = duckdb.connect(str(self._path), read_only=True)
        try:
            rows = con.execute(
                "SELECT session_date, regime, regime_confidence, vix_close, "
                "       regime_fact_version, model_hash "
                "FROM day_type_facts "
                "WHERE checkpoint = '13pm'"
            ).fetchall()
        finally:
            con.close()
        facts = {}
        for session_date, regime, conf, vix, ver, mhash in rows:
            facts[date.fromisoformat(str(session_date))] = {
                "regime": regime,
                "regime_confidence": float(conf),
                "vix_close": float(vix) if vix is not None else None,
                "regime_fact_version": ver,
                "model_hash": mhash,
            }
        return facts
