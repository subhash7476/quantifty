from typing import List

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource


class AlwaysRaisesSource(SignalSource):
    """A SignalSource that raises ValueError on every on_bar call.

    Used by run_fault_drill.py to prove GuardedSignalSource's
    quarantine-and-continue behavior live, through the real composition
    root, without touching the reference strategy itself (MM12.4 §8.2).
    """

    def __init__(self, message: str = "AlwaysRaisesSource: deliberate fault drill"):
        self._message = message
        self.calls = 0

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        self.calls += 1
        raise ValueError(self._message)


class BadMetadataSource(SignalSource):
    """A SignalSource that emits BUY signals with missing/invalid risk metadata.

    Used by run_fault_drill.py to prove GuardedSignalSource's
    reject-and-journal behavior live (SIGNAL_CONTRACT_REJECTED), through
    the real composition root (MM12.4 §8.2).
    """

    def __init__(self):
        self.calls = 0

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        self.calls += 1
        # Return two signals: one clean EXIT (always passes) and one
        # bad BUY (missing risk_r) to prove contract-clean siblings route.
        if self.calls == 1:
            exit_signal = SignalEvent(
                strategy_id="fault_drill",
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                signal_type=SignalType.EXIT,
                confidence=1.0,
            )
            bad_entry = SignalEvent(
                strategy_id="fault_drill",
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                signal_type=SignalType.BUY,
                confidence=1.0,
                metadata={"sl_distance": 1.5},
            )
            return [exit_signal, bad_entry]
        return []
