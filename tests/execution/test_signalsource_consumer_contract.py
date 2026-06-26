"""
MM.7C — C1: the SignalEvent consumer contract a production SignalSource must emit.

A SignalSource returns List[SignalEvent]; the driver routes each to the sole live
order path, ExecutionHandler.process_signal(signal, current_price) (handler.py:432).
This pins what that path REQUIRES of an emitted signal, so MM7D builds a strategy
against pinned behavior — not a guess.

Findings pinned (handler.py:457-482, 558-615, 819-824):
- non-EXIT: sl_distance + risk_r are mandatory downstream; when absent the handler
  back-fills conservative defaults into signal.metadata (a real source must supply
  real values, not rely on the warn-default).
- signal_id auto-derives as sha256(symbol_strategy_timestamp) when the source omits
  it — so idempotency works without the source setting one.
- SIZING is a hint+authority split (refines MM7B): the source MAY pass
  metadata['quantity'], but the handler CAPS it at config.max_position_size and
  falls back to default_quantity·(0.5+confidence·0.5) when no hint is given. Sizing
  authority stays with the handler (ADR-005).

Real ExecutionHandler over an isolated tmp PaperBroker + ExecutionStore (the
G1-characterization construction). ZERO production code changed.
"""
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytz

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.execution.order_models import OrderSide
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
EQUITY = "RELIANCE"


def _build_handler(tmp_path, monkeypatch, config=None):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")))
    clock = ReplayClock(FIXED_DT)
    handler = ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock, broker=PaperBroker(clock),
        config=config or ExecutionConfig(),
        initial_capital=1_000_000_000.0,  # MM9.1: ample capital — characterization tests don't exercise the margin gate
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )
    return handler


def _signal(signal_type=SignalType.BUY, metadata=None):
    return SignalEvent(strategy_id="mm7c", symbol=EQUITY, timestamp=FIXED_DT,
                       signal_type=signal_type, confidence=1.0,
                       metadata=dict(metadata or {}))


# --- non-EXIT risk-field requirement -------------------------------------- #

def test_non_exit_with_risk_fields_produces_order(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    order = h.process_signal(
        _signal(metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0,
                          "signal_id": "s1"}),
        current_price=2500.0)
    assert order is not None and order.side == OrderSide.BUY


def test_non_exit_backfills_default_risk_fields_when_absent(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    sig = _signal(metadata={"quantity": 50, "signal_id": "s2"})  # no sl_distance/risk_r
    h.process_signal(sig, current_price=2500.0)
    # The handler insists on these downstream — it back-fills when the source omits
    # them. A real source MUST provide real values rather than rely on this default.
    assert "sl_distance" in sig.metadata
    assert "risk_r" in sig.metadata


# --- signal_id derivation -------------------------------------------------- #

def test_signal_id_auto_derives_when_absent(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    sig = _signal(metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0})  # no signal_id
    h.process_signal(sig, current_price=2500.0)
    expected = sha256(f"{EQUITY}_mm7c_{FIXED_DT.isoformat()}".encode()).hexdigest()
    assert expected in h._seen_signals


# --- sizing: source hint vs handler authority (ADR-005) -------------------- #

def test_source_quantity_hint_is_honored(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch)
    order = h.process_signal(
        _signal(metadata={"quantity": 50, "sl_distance": 5.0, "risk_r": 1.0,
                          "signal_id": "s3"}),
        current_price=2500.0)
    assert order.quantity == 50


def test_handler_caps_quantity_at_max_position_size(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch,
                       config=ExecutionConfig(max_position_size=1000.0))
    order = h.process_signal(
        _signal(metadata={"quantity": 5000, "sl_distance": 5.0, "risk_r": 1.0,
                          "signal_id": "s4"}),
        current_price=2500.0)
    # The handler owns the bound even when the source over-hints.
    assert order.quantity == 1000


def test_handler_defaults_size_when_no_hint(tmp_path, monkeypatch):
    h = _build_handler(tmp_path, monkeypatch,
                       config=ExecutionConfig(default_quantity=100.0))
    order = h.process_signal(
        _signal(metadata={"sl_distance": 5.0, "risk_r": 1.0, "signal_id": "s5"}),
        current_price=2500.0)
    # default_quantity·(0.5 + confidence·0.5) = 100·(0.5+0.5) at confidence 1.0.
    assert order.quantity == 100


# --- isolation guard ------------------------------------------------------- #

def test_real_execution_db_untouched(tmp_path, monkeypatch):
    real = Path("data/execution.db")
    before = (real.exists(), real.stat().st_mtime_ns if real.exists() else None)
    h = _build_handler(tmp_path, monkeypatch)
    h.process_signal(
        _signal(metadata={"quantity": 10, "sl_distance": 5.0, "risk_r": 1.0,
                          "signal_id": "s6"}),
        current_price=2500.0)
    after = (real.exists(), real.stat().st_mtime_ns if real.exists() else None)
    assert before == after
