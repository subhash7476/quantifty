from typing import List, Optional

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource


_STRATEGY_ID = "reference_heartbeat_v1"


class HeartbeatSignalSource(SignalSource):
    """Fixed-cadence heartbeat strategy: a pure function of bar count.

    Effectively:
        FLAT  -> after entry_period_bars -> BUY  -> LONG
        LONG  -> after holding_period_bars -> EXIT -> FLAT
        Repeat forever, for each symbol independently.

    No market awareness, no indicator, no randomness. Determinism is
    inductively provable from the single rule (MM12.4 §6).
    """

    def __init__(self,
                 entry_period_bars: int = 60,
                 holding_period_bars: int = 15,
                 sl_distance_pct: float = 0.01,
                 risk_r: float = 500.0):
        self._entry_period_bars = entry_period_bars
        self._holding_period_bars = holding_period_bars
        self._sl_distance_pct = sl_distance_pct
        self._risk_r = risk_r
        self._state: dict = {}

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        sym = bar.symbol
        if sym not in self._state:
            self._state[sym] = {
                "position": "FLAT",
                "bars_since_signal": 0,
                "total_bars_seen": 0,
            }
        st = self._state[sym]
        st["total_bars_seen"] += 1
        st["bars_since_signal"] += 1

        if st["position"] == "FLAT":
            if st["bars_since_signal"] >= self._entry_period_bars:
                st["position"] = "LONG"
                st["bars_since_signal"] = 0
                return [self._make_buy(bar)]
            return []
        else:
            if st["bars_since_signal"] >= self._holding_period_bars:
                st["position"] = "FLAT"
                st["bars_since_signal"] = 0
                return [self._make_exit(bar)]
            return []

    def _make_buy(self, bar: OHLCVBar) -> SignalEvent:
        return SignalEvent(
            strategy_id=_STRATEGY_ID,
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            signal_type=SignalType.BUY,
            confidence=1.0,
            metadata={
                "sl_distance": round(bar.close * self._sl_distance_pct, 2),
                "risk_r": self._risk_r,
                "reference_bar_index": self._state[bar.symbol]["total_bars_seen"],
                "reference_rule": "fixed_cadence_entry",
            },
        )

    def _make_exit(self, bar: OHLCVBar) -> SignalEvent:
        return SignalEvent(
            strategy_id=_STRATEGY_ID,
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            signal_type=SignalType.EXIT,
            confidence=1.0,
            metadata={
                "reference_bar_index": self._state[bar.symbol]["total_bars_seen"],
                "reference_rule": "fixed_cadence_exit",
            },
        )
