"""
MM9.2-S3-S1 — PriceSnapshot Infrastructure.

Architecture B (spec §3/§4): the handler's signal-driven ``_latest_prices``
dict is replaced by ``_price_cache: Dict[str, PriceSnapshot]`` where each
entry bundles its recording timestamp. A single public writer
``update_market_price(symbol, price)`` timestamps with the deterministic
clock. ``MarginTracker.get_used_margin`` keeps its ``Dict[str, float]``
signature — ``_check_margin_budget`` projects the snapshot cache to a plain
float dict immediately before the call.

This slice is infrastructure-only: zero behavioural change. Coverage mirrors
MM9_2_S3_IMPLEMENTATION_SPEC_V2.md §9 (S3-S1 acceptance criteria):

  * pricesnapshot_stores_price
  * pricesnapshot_stores_timestamp_from_mockclock
  * update_market_price_overwrites_existing_snapshot
  * exit_signal_still_updates_cache
  * check_margin_budget_projects_price_snapshot_to_dict
  * latest_prices_no_longer_exists
"""

import pytz
import pytest
from datetime import datetime, timedelta

import core.execution.handler as handler_mod
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType
from core.brokers.paper_broker import PaperBroker
from core.execution.handler import (
    ExecutionConfig,
    ExecutionHandler,
    PriceSnapshot,
)
from core.execution.order_lifecycle import FillEvent
from core.execution.persistence.execution_store import ExecutionStore

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)


# =========================================================================== #
# Shared construction helpers — mirror tests/execution/test_mm9_2_s1_price_cache.py
# =========================================================================== #

def _build_handler(tmp_path, monkeypatch, initial_capital=100_000.0,
                   max_utilisation=0.80):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore",
        lambda *a, **k: ExecutionStore(str(tmp_path / "execution.db")),
    )
    DatabaseManager.reset_instance()
    clock = ReplayClock(FIXED_DT)
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=clock,
        broker=PaperBroker(clock),
        config=ExecutionConfig(max_capital_utilisation=max_utilisation),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
        initial_capital=initial_capital,
    )


def _make_signal(symbol="NSE_EQ|INE001A01036", sig_type=SignalType.BUY,
                 suffix="S3S1", quantity=None):
    metadata = {
        "signal_id": f"SIG-MM9.2-S3-S1-{suffix}",
        "sl_distance": 1.0,
        "risk_r": 1.0,
    }
    if quantity is not None:
        metadata["quantity"] = quantity
    return SignalEvent(
        strategy_id="test_mm9_2_s3_s1",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=sig_type,
        confidence=0.9,
        metadata=metadata,
    )


def _inject_position(handler, symbol, qty, price, side="BUY"):
    """Pushes a FillEvent straight into position_tracker without going through
    process_signal — so the cache is NOT warmed (mirrors _replay_state)."""
    fill = FillEvent(
        fill_id=f"fill-{symbol}-{side}",
        order_id=f"ord-{symbol}-{side}",
        symbol=symbol,
        quantity=qty,
        price=price,
        timestamp=FIXED_DT,
        side=side,
    )
    handler.position_tracker.update_from_fill(fill)


def _spy_used_margin(handler, monkeypatch):
    """Wraps margin_tracker.get_used_margin to capture the prices argument."""
    captured = {"prices": None, "used": None, "n": 0}
    real = handler.margin_tracker.get_used_margin

    def spy(prices):
        captured["n"] += 1
        captured["prices"] = dict(prices)
        captured["used"] = real(prices)
        return captured["used"]

    monkeypatch.setattr(handler.margin_tracker, "get_used_margin", spy)
    return captured


# =========================================================================== #
# 1. PriceSnapshot stores price correctly
# =========================================================================== #

def test_pricesnapshot_stores_price():
    snap = PriceSnapshot(price=123.45, timestamp=FIXED_DT)
    assert snap.price == 123.45


# =========================================================================== #
# 2. PriceSnapshot stores timestamp from the injected (mock) clock
# =========================================================================== #

def test_update_market_price_timestamps_from_mockclock(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # ReplayClock.now() is FIXED_DT until advanced.
    assert handler.clock.now() == FIXED_DT
    handler.update_market_price("NSE_EQ|AAA", 100.0)
    snap = handler._price_cache["NSE_EQ|AAA"]
    assert snap.price == 100.0
    assert snap.timestamp == FIXED_DT  # sourced from self.clock.now()


# =========================================================================== #
# 3. update_market_price overwrites an existing snapshot
# =========================================================================== #

def test_update_market_price_overwrites_existing_snapshot(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    handler.update_market_price("NSE_EQ|AAA", 100.0)
    first = handler._price_cache["NSE_EQ|AAA"]
    assert first.price == 100.0

    # Advance the deterministic clock; second write must replace, not append.
    handler.clock.advance(timedelta(seconds=120))
    handler.update_market_price("NSE_EQ|AAA", 150.0)

    assert len(handler._price_cache) == 1  # no duplicate key
    second = handler._price_cache["NSE_EQ|AAA"]
    assert second.price == 150.0
    assert second.timestamp == handler.clock.now()
    assert second.timestamp != first.timestamp


# =========================================================================== #
# 4. EXIT signals still update the cache (unconditional warm)
# =========================================================================== #

def test_exit_signal_still_updates_cache(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    # Open a LONG on AAA so a later EXIT has something to close.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|AAA", suffix="EXIT-IN", quantity=100), 100.0)
    entry_snap = handler._price_cache["NSE_EQ|AAA"]
    assert entry_snap.price == 100.0

    # Advance clock so the EXIT's snapshot timestamp is distinguishable.
    handler.clock.advance(timedelta(seconds=60))
    exit_sig = _make_signal(symbol="NSE_EQ|AAA", sig_type=SignalType.EXIT,
                            suffix="EXIT-OUT")
    result = handler.process_signal(exit_sig, 110.0)
    assert result is not None  # EXIT executed

    exit_snap = handler._price_cache["NSE_EQ|AAA"]
    assert exit_snap.price == 110.0  # cache warmed even for EXIT
    assert exit_snap.timestamp == handler.clock.now()
    assert exit_snap.timestamp != entry_snap.timestamp


# =========================================================================== #
# 5. _check_margin_budget projects Dict[str, PriceSnapshot] -> Dict[str, float]
#    immediately before MarginTracker.get_used_margin (signature unchanged)
# =========================================================================== #

def test_check_margin_budget_projects_price_snapshot_to_dict(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch, initial_capital=1_000_000.0)
    # Hold AAA via the replay seam; warm both AAA and BBB through the public
    # writer so the cache holds PriceSnapshot values, not raw floats.
    _inject_position(handler, "NSE_EQ|AAA", 100, 100.0)
    handler.update_market_price("NSE_EQ|AAA", 100.0)

    captured = _spy_used_margin(handler, monkeypatch)
    # process_signal warms BBB (signal symbol) and then runs the gate, which
    # must project the snapshot cache to a plain float dict before the call.
    handler.process_signal(
        _make_signal(symbol="NSE_EQ|BBB", suffix="PROJ"), 50.0)

    assert captured["n"] >= 1
    prices = captured["prices"]
    # MarginTracker received a Dict[str, float], not PriceSnapshot objects.
    assert all(isinstance(v, float) for v in prices.values())
    assert prices["NSE_EQ|AAA"] == 100.0
    assert prices["NSE_EQ|BBB"] == 50.0
    # Held AAA contributes its cached mark to used_current.
    assert captured["used"] >= 100 * 100 * 1.0 * 0.2 - 1e-9


# =========================================================================== #
# 6. _latest_prices no longer exists; _price_cache replaces it
# =========================================================================== #

def test_latest_prices_no_longer_exists(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert not hasattr(handler, "_latest_prices")
    assert not hasattr(handler, "_price_timestamps")
    assert hasattr(handler, "_price_cache")
    assert isinstance(handler._price_cache, dict)


def test_price_cache_initializes_empty(tmp_path, monkeypatch):
    handler = _build_handler(tmp_path, monkeypatch)
    assert handler._price_cache == {}
