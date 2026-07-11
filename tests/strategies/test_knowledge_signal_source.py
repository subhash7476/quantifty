from datetime import date, datetime
from typing import Optional

from core.events import OHLCVBar, SignalType
from core.msi.contracts.estimate import Estimate
from core.msi.contracts.knowledge import KnowledgeObject
from core.msi.contracts.market_state import MarketState
from core.strategies.knowledge_signal_source import KnowledgeSignalSource

_TS = datetime(2026, 2, 27, 9, 15)
TRADED = "NSE_EQ|INE139A01034"


def _knowledge(regime_value: Optional[float], latent: str = "market_regime") -> KnowledgeObject:
    estimates = ()
    if regime_value is not None:
        estimates = (Estimate(latent_variable=latent, value=regime_value,
                              uncertainty=0.15, dimension="regime_class"),)
    ms = MarketState(evaluation_timestamp=_TS, estimates=estimates)
    return KnowledgeObject(
        knowledge_id="k-1", evaluation_timestamp=_TS, artifact_version="v1.0.0",
        runtime_version="msi-v1.0", market_state=ms, provenance_reference="prov-1")


class _StubOrch:
    def __init__(self, knowledge: KnowledgeObject):
        self._knowledge = knowledge
        self.calls = 0

    def run(self, evaluation_date, artifact_ref):
        self.calls += 1
        return self._knowledge


def _bar(ts=_TS, close=357.4) -> OHLCVBar:
    return OHLCVBar(symbol=TRADED, timestamp=ts, open=close, high=close,
                    low=close, close=close, volume=1000)


def _source(regime_value=0.0):
    orch = _StubOrch(_knowledge(regime_value))
    src = KnowledgeSignalSource(orch, date(2026, 2, 27), "artifact/ref",
                                traded_symbol=TRADED)
    return src, orch


def test_on_start_runs_dra_once_and_caches_regime():
    src, orch = _source(regime_value=2.0)
    src.on_start()
    assert orch.calls == 1


def test_no_signal_before_on_start():
    src, _ = _source()
    assert src.on_bar(_bar()) == []


def test_emits_one_contract_valid_buy_on_first_bar():
    src, _ = _source(regime_value=0.0)
    src.on_start()
    out = src.on_bar(_bar())
    assert len(out) == 1
    sig = out[0]
    assert sig.signal_type is SignalType.BUY
    assert sig.symbol == TRADED
    assert sig.timestamp == _TS
    assert float(sig.metadata["sl_distance"]) > 0
    assert float(sig.metadata["risk_r"]) > 0
    assert sig.metadata["knowledge_id"] == "k-1"
    assert sig.metadata["regime_value"] == 0.0


def test_single_emit_then_silent():
    src, _ = _source()
    src.on_start()
    assert len(src.on_bar(_bar())) == 1
    assert src.on_bar(_bar(ts=datetime(2026, 2, 27, 9, 16))) == []


def test_no_emit_when_selected_estimate_absent():
    orch = _StubOrch(_knowledge(regime_value=None))
    src = KnowledgeSignalSource(orch, date(2026, 2, 27), "ref", traded_symbol=TRADED)
    src.on_start()
    assert src.on_bar(_bar()) == []
