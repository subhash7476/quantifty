"""Carry strategy — WS-C dumb emitter.

Bridge §3: on each monthly formation date, read the carry fact table and emit
SignalEvent intents. Between formation dates: emit nothing. No sizing, no
neutralization, no margin, no broker — intent and rank only.

Loads formation calendar from the facts DB on startup. On every bar, checks
if formation_date matches and emits batch intents.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import List, Optional, Set

import duckdb

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource

_logger = logging.getLogger(__name__)


class CarryStrategy(SignalSource):
    """Dumb formation-date emitter for the Carry sleeve.

    On each formation date: emits a single "batch" SignalEvent carrying the
    formation_date and fact_path in metadata — the rebalancer consumes this.
    On non-formation bars: returns empty list.
    """

    def __init__(self, facts_db_path: str):
        self._facts_db = Path(facts_db_path)
        self._formation_dates: Set[date] = set()
        self._last_emitted: Optional[date] = None

    def on_start(self, context=None) -> None:
        con = duckdb.connect(str(self._facts_db), read_only=True)
        rows = con.execute(
            "SELECT DISTINCT formation_date FROM carry_facts ORDER BY formation_date"
        ).fetchall()
        con.close()
        self._formation_dates = {r[0] for r in rows}
        _logger.info("CarryStrategy: loaded %d formation dates", len(self._formation_dates))

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        bar_date = bar.timestamp.date() if hasattr(bar.timestamp, 'date') else bar.timestamp
        if bar_date not in self._formation_dates:
            return []
        if self._last_emitted == bar_date:
            return []
        self._last_emitted = bar_date

        _logger.info("CarryStrategy: formation date %s", bar_date)
        return [
            SignalEvent(
                strategy_id="carry",
                symbol="__CARRY_BATCH__",
                timestamp=bar.timestamp,
                signal_type=SignalType.NEUTRAL,
                confidence=0.0,
                metadata={
                    "rebalance": True,
                    "formation_date": bar_date.isoformat(),
                }
            )
        ]

    def on_stop(self) -> None:
        pass
