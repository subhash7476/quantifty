"""
MM.7D.1 — Synthetic wiring proof (infrastructure validation only).

Proves the runtime executes end-to-end with a deterministic, market-data-free
SignalSource, exactly the smallest design MM7D reviewed (docs/reports/
MM7D_SYNTHETIC_SOURCE_REVIEW.md §1): a call-indexed BUY-then-EXIT source over an
equity symbol, driving the full spine

    SignalSource -> LoopDriver -> ExecutionHandler -> PaperBroker
                 -> Persistence -> Restore -> Reconciliation

through a *real* ExecutionHandler (PAPER) + PaperBroker + ExecutionStore against
an isolated tmp execution.db. NO strategy, NO alpha, NO OHLCV feed, NO option
chain, NO indicators, NO strategy-specific logic.

This is "Tier A" (equity). It exercises every box above. Canonicalization is the
deliberate equity carve-out (driver.py:439-444; canonical_restore.canonicalize_
symbol returns None for equity) — proven here as a no-op. The positive
"fires-on-derivative" half is already pinned by MM7A T4
(test_driver_canonicalization_requires_checker.py) and is NOT reproduced here, as
it would require a real derivative + instrument master and drag in Open Finding F4
(out of scope for the smallest wiring proof — MM7D §3.2).

The synthetic source is implemented test-local (below), NOT as a production
package: MM7D §0/§7 and the MM7D.1 brief both require the proof to validate wiring
WITHOUT landing a production SignalSource or entry script. Keeping it under tests/
also keeps the MM7A T1 tripwire (no scripts/ LoopDriver) green — asserted
explicitly by test_proof_harness_is_test_local_not_an_entry_script.

ZERO production code is changed by this file.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import List, Optional

import pytest
import pytz

import core.execution.handler as handler_mod
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import OHLCVBar, SignalEvent, SignalType
from core.execution.handler import ExecutionConfig, ExecutionHandler, ExecutionMode
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.position_models import PositionSide
from core.execution.order_models import OrderSide
from core.execution.rules import ExecutionRuleError
from core.runtime.config import DriverConfig, Mode
from core.runtime.driver import LoopDriver, RuntimeState
from core.runtime.event_journal import RuntimeEventJournal
from core.runtime.signal_source import SignalSource

from _doubles import FakeMarketDataProvider, bar_series

# Equity key: has_derivatives() is False (segment NSE_EQ), and canonicalize_symbol
# returns None (not a futures/option shape) -> the equity carve-out. The handler
# parses it to an Equity whose .symbol is preserved byte-for-byte
# (instrument_parser.py:46), so the position key == this string == the broker key.
EQUITY = "NSE_EQ|INE002A01018"
FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
# bar.close used as the fill price everywhere downstream — MM7C's proven-passing
# risk-clearance value (test_signalsource_consumer_contract.py).
CLOSE = 2500.0
SL_DISTANCE = 5.0
RISK_R = 1.0
QTY = 50


# --------------------------------------------------------------------------- #
# The synthetic source (MM7D §1) — test-local, the smallest possible.
# --------------------------------------------------------------------------- #
class SyntheticBuyExitSource(SignalSource):
    """
    Call-indexed BUY-then-EXIT source. State is a single emit counter; it is
    ledger-blind (holds no handler/broker/tracker — MM7C C3) and ignores the
    bar's prices entirely, emitting on call index for maximal determinism
    (MM7C C4). It carries NO market data, chain, greeks, or alpha.

        on_bar #0 -> [BUY]  (real sl_distance + risk_r + a quantity hint)
        on_bar #1 -> [EXIT] (bare — handler resolves side/qty from its ledger)
        on_bar #2+ -> []
    """

    def __init__(self, symbol: str = EQUITY):
        self._symbol = symbol
        self.calls = 0
        self.started = 0
        self.stopped = 0
        self.emitted: List[tuple] = []  # (signal_type, timestamp) for assertions

    def on_start(self, context: Optional[object] = None) -> None:
        self.started += 1

    def on_bar(self, bar: OHLCVBar) -> List[SignalEvent]:
        i = self.calls
        self.calls += 1
        if i == 0:
            self.emitted.append(("BUY", bar.timestamp))
            return [SignalEvent(
                strategy_id="synthetic", symbol=self._symbol, timestamp=bar.timestamp,
                signal_type=SignalType.BUY, confidence=1.0,
                metadata={"sl_distance": SL_DISTANCE, "risk_r": RISK_R, "quantity": QTY})]
        if i == 1:
            self.emitted.append(("EXIT", bar.timestamp))
            return [SignalEvent(
                strategy_id="synthetic", symbol=self._symbol, timestamp=bar.timestamp,
                signal_type=SignalType.EXIT, confidence=1.0, metadata={})]
        return []

    def on_stop(self) -> None:
        self.stopped += 1


def _derived_signal_id(symbol: str, ts: datetime) -> str:
    """Reproduce the handler's auto-derivation (handler.py:447-449) for assertions."""
    return sha256(f"{symbol}_synthetic_{ts.isoformat()}".encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Harness — a REAL ExecutionHandler (PAPER) over an isolated tmp execution.db.
# --------------------------------------------------------------------------- #
def _build_handler(root: Path, monkeypatch) -> ExecutionHandler:
    """Real handler whose ExecutionStore is redirected to root/execution.db (the
    G1/MM7C isolation construction). load_db_state=True so a second handler on the
    same root restores the persisted ledger (ADR-001 — recovery at construction)."""
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(root / "execution.db")))
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=root),
        clock=ReplayClock(FIXED_DT), broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(mode=ExecutionMode.PAPER, default_quantity=100.0,
                               max_position_size=1000.0),
        metrics_path=str(root / "metrics.json"),
        load_db_state=True)


def _build_driver(root: Path, handler: ExecutionHandler, source, *,
                  broker_positions, max_bars: int = 2, mode: Mode = Mode.REPLAY,
                  journal_name: str = "runtime_events.jsonl"):
    cfg = DriverConfig(mode=mode, symbols=[EQUITY], max_bars=max_bars,
                       poll_interval_s=0.25)
    provider = FakeMarketDataProvider(
        {EQUITY: bar_series(EQUITY, max_bars, close=CLOSE)}, live=cfg.is_live)
    return LoopDriver(
        cfg, clock=handler.clock, provider=provider,
        journal=RuntimeEventJournal(path=str(root / journal_name)),
        source=source, execution=handler,
        broker_positions=broker_positions, master_readiness=None)


def _events(root: Path, name: str = "runtime_events.jsonl") -> List[str]:
    p = root / name
    if not p.exists():
        return []
    import json
    return [json.loads(l)["event_type"] for l in p.read_text().splitlines()]


@pytest.fixture
def alerts(monkeypatch):
    """Silence + capture the driver's alerter — no Telegram I/O."""
    class _Rec:
        def __init__(self):
            self.levels = []

        def info(self, m):
            self.levels.append("info")

        def warning(self, m):
            self.levels.append("warning")

        def critical(self, m):
            self.levels.append("critical")

    rec = _Rec()
    monkeypatch.setattr("core.runtime.driver.alerter", rec)
    return rec


# --------------------------------------------------------------------------- #
# 1. The synthetic source emits BUY then EXIT then nothing; lifecycle fires.
# --------------------------------------------------------------------------- #
def test_synthetic_source_emits_buy_then_exit(tmp_path, alerts, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    source = SyntheticBuyExitSource()
    driver = _build_driver(tmp_path, handler, source, broker_positions=lambda: [],
                           max_bars=3)
    driver.run()

    assert [t for t, _ in source.emitted] == ["BUY", "EXIT"]
    assert source.started == 1            # on_start once, before the loop
    assert source.stopped == 1            # on_stop once, on shutdown
    assert driver.signals_pulled == 2     # BUY + EXIT, nothing on bar #2
    assert driver.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# 2. The BUY carries real risk fields -> the clean path, not the warn-default.
# --------------------------------------------------------------------------- #
def test_buy_carries_valid_risk_fields_clean_path(tmp_path, alerts, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    warned = []
    monkeypatch.setattr(handler.logger, "warning", lambda m, *a: warned.append(m))
    driver = _build_driver(tmp_path, handler, SyntheticBuyExitSource(),
                           broker_positions=lambda: [])
    driver.run()

    # No "missing risk definition" warning means the source supplied real values
    # and process_signal took the clean path (handler.py:482).
    assert not any("missing risk definition" in str(m) for m in warned)


# --------------------------------------------------------------------------- #
# 3. Equity round-trip persists orders + fills; position opens then flattens.
# --------------------------------------------------------------------------- #
def test_equity_roundtrip_persists_orders_and_fills(tmp_path, alerts, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    driver = _build_driver(tmp_path, handler, SyntheticBuyExitSource(),
                           broker_positions=lambda: [])
    driver.run()

    orders = handler.order_repo.get_all()
    fills = handler.fill_repo.get_all()
    assert len(orders) == 2
    assert len(fills) == 2
    assert {o.side for o in orders} == {OrderSide.BUY, OrderSide.SELL}
    # BUY opened qty 50, EXIT closed the full 50 (handler-resolved).
    assert sorted(int(o.quantity) for o in orders) == [QTY, QTY]
    assert all(f.price == CLOSE for f in fills)
    # Round-trip closed: net FLAT.
    assert handler.position_tracker.get_position(EQUITY).side is PositionSide.FLAT


# --------------------------------------------------------------------------- #
# 4. Restart restores the ledger + idempotency registry; re-emit is rejected.
# --------------------------------------------------------------------------- #
def test_restart_restores_ledger_and_idempotency(tmp_path, alerts, monkeypatch):
    handler1 = _build_handler(tmp_path, monkeypatch)
    _build_driver(tmp_path, handler1, SyntheticBuyExitSource(),
                  broker_positions=lambda: []).run()

    # A fresh handler on the SAME execution.db restores at construction (ADR-001).
    handler2 = _build_handler(tmp_path, monkeypatch)
    assert len(handler2.order_repo.get_all()) == 2          # orders restored
    assert len(handler2.fill_repo.get_all()) == 2           # fills restored

    bar0_ts = bar_series(EQUITY, 1)[0].timestamp
    buy_id = _derived_signal_id(EQUITY, bar0_ts)
    assert buy_id in handler2._seen_signals                 # idempotency registry restored

    # Re-emitting the recorded BUY signal is rejected (idempotency, rules.py:17).
    replay = SignalEvent(strategy_id="synthetic", symbol=EQUITY, timestamp=bar0_ts,
                         signal_type=SignalType.BUY, confidence=1.0,
                         metadata={"sl_distance": SL_DISTANCE, "risk_r": RISK_R})
    with pytest.raises(ExecutionRuleError):
        handler2.process_signal(replay, CLOSE)


# --------------------------------------------------------------------------- #
# 5. Reconciliation PASS (book matches) and FAIL (book diverges) at the gate.
# --------------------------------------------------------------------------- #
def _establish_open_long(root: Path, monkeypatch):
    """Run only the BUY bar (max_bars=1) so an open long persists for the restart
    reconciliation tests."""
    handler = _build_handler(root, monkeypatch)
    _build_driver(root, handler, SyntheticBuyExitSource(),
                  broker_positions=lambda: [], max_bars=1).run()


def test_reconciliation_pass_when_book_matches(tmp_path, alerts, monkeypatch):
    _establish_open_long(tmp_path, monkeypatch)
    handler = _build_handler(tmp_path, monkeypatch)
    matching = [{"symbol": EQUITY, "quantity": QTY, "side": "LONG"}]
    # source=None: isolate the startup gate outcome from any loop trading. A
    # dedicated journal so we read THIS run's gate outcome, not the establish run.
    driver = _build_driver(tmp_path, handler, None, broker_positions=lambda: matching,
                           journal_name="gate.jsonl")
    driver.run()

    ev = _events(tmp_path, "gate.jsonl")
    assert "RECONCILIATION_PASS" in ev
    assert "RUNNING" in ev
    assert driver.state is RuntimeState.STOPPED


def test_reconciliation_fail_when_book_diverges(tmp_path, alerts, monkeypatch):
    _establish_open_long(tmp_path, monkeypatch)
    handler = _build_handler(tmp_path, monkeypatch)
    divergent = [{"symbol": EQUITY, "quantity": 30, "side": "LONG"}]  # qty mismatch
    driver = _build_driver(tmp_path, handler, None, broker_positions=lambda: divergent,
                           journal_name="gate.jsonl")
    driver.run()

    ev = _events(tmp_path, "gate.jsonl")
    assert "RECONCILIATION_FAIL" in ev
    assert "RUNNING" not in ev            # refused to start
    assert "RECONCILIATION_PASS" not in ev
    assert driver.state is RuntimeState.STOPPED
    assert driver.bars_processed == 0     # loop never ran
    assert "critical" in alerts.levels    # divergence is loud (unlike W3)


# --------------------------------------------------------------------------- #
# 6. Canonicalization is a no-op on the equity path (Tier A carve-out).
#    The fires-on-derivative half is pinned by MM7A T4 (not reproduced — F4).
# --------------------------------------------------------------------------- #
def test_canonicalization_noop_on_equity(tmp_path, alerts, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    calls = {"pos": 0, "ord": 0}
    monkeypatch.setattr(handler, "canonicalize_restored_positions",
                        lambda: calls.__setitem__("pos", calls["pos"] + 1))
    monkeypatch.setattr(handler, "canonicalize_restored_orders",
                        lambda: calls.__setitem__("ord", calls["ord"] + 1))
    driver = _build_driver(tmp_path, handler, SyntheticBuyExitSource(),
                           broker_positions=lambda: [])
    driver.run()

    # Gate is LIVE and has_derivatives and master_readiness (driver.py:439-444);
    # equity REPLAY fails it -> the driver never triggers either half.
    assert calls == {"pos": 0, "ord": 0}
    assert driver.state is RuntimeState.STOPPED


# --------------------------------------------------------------------------- #
# 7. Determinism: two independent runs produce identical deterministic artifacts.
# --------------------------------------------------------------------------- #
def _projection(handler: ExecutionHandler):
    """The deterministic slice of the persisted ledger (UUIDs excluded)."""
    orders = sorted((o.symbol, o.side.value, int(o.quantity), str(o.signal_id))
                    for o in handler.order_repo.get_all())
    fills = sorted((f.symbol, f.side, int(f.quantity), float(f.price))
                   for f in handler.fill_repo.get_all())
    return orders, fills


def test_determinism_two_runs_identical_artifacts(tmp_path, alerts, monkeypatch):
    a = tmp_path / "a"
    handler_a = _build_handler(a, monkeypatch)
    source_a = SyntheticBuyExitSource()
    _build_driver(a, handler_a, source_a, broker_positions=lambda: []).run()

    b = tmp_path / "b"
    handler_b = _build_handler(b, monkeypatch)
    source_b = SyntheticBuyExitSource()
    _build_driver(b, handler_b, source_b, broker_positions=lambda: []).run()

    assert source_a.emitted == source_b.emitted        # identical routed stream
    assert _projection(handler_a) == _projection(handler_b)  # identical ledger


# --------------------------------------------------------------------------- #
# 8. The proof is test-local — it lives under tests/ and defines its own
#    synthetic source rather than importing the production entry script.
#    (The "no scripts/ LoopDriver" tripwire was MM7A T1's; MM7E consciously
#    flipped it — scripts/fno_runner.py now exists — so this proof no longer
#    asserts that absence; it only asserts its own test-locality.)
# --------------------------------------------------------------------------- #
def test_proof_harness_is_test_local_not_an_entry_script():
    here = Path(__file__).resolve()
    assert "tests" in here.parts and "scripts" not in here.parts
    # The proof's source is defined in THIS module, not imported from scripts/.
    assert SyntheticBuyExitSource.__module__ == __name__
