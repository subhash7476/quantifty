from datetime import date
from typing import Any, List, Optional

from core.events import OHLCVBar, SignalEvent, SignalType
from core.runtime.signal_source import SignalSource


class KnowledgeSignalSource(SignalSource):

    def __init__(self, orchestrator, evaluation_date: date, artifact_ref: str,
                 traded_symbol: str, latent_variable: str = "market_regime",
                 strategy_id: str = "mm13_knowledge_reader",
                 sl_frac: float = 0.01, risk_r: float = 1.0):
        self._orchestrator = orchestrator
        self._evaluation_date = evaluation_date
        self._artifact_ref = artifact_ref
        self._traded_symbol = traded_symbol
        self._latent_variable = latent_variable
        self._strategy_id = strategy_id
        self._sl_frac = sl_frac
        self._risk_r = risk_r
        self._knowledge = None
        self._regime_value: Optional[float] = None
        self._emitted = False

    def on_start(self, context: Optional[Any] = None) -> None:
        self._knowledge = self._orchestrator.run(
            self._evaluation_date, self._artifact_ref)
        self._regime_value = self._select_estimate_value(self._knowledge)

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        if self._knowledge is None or self._regime_value is None or self._emitted:
            return []
        self._emitted = True
        return [SignalEvent(
            strategy_id=self._strategy_id,
            symbol=self._traded_symbol,
            timestamp=bar.timestamp,
            signal_type=SignalType.BUY,
            confidence=0.9,
            metadata={
                "signal_id": f"MM13-{bar.timestamp.isoformat()}",
                "entry_price": bar.close,
                "sl_distance": round(bar.close * self._sl_frac, 2),
                "risk_r": self._risk_r,
                "knowledge_id": self._knowledge.knowledge_id,
                "latent_variable": self._latent_variable,
                "regime_value": self._regime_value,
            },
        )]

    def _select_estimate_value(self, knowledge) -> Optional[float]:
        for estimate in knowledge.market_state.estimates:
            if estimate.latent_variable == self._latent_variable:
                return estimate.value
        return None
