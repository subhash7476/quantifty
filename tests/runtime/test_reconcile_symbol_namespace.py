"""
MM.7G — Broker-position symbol-NAMESPACE characterization (G5).

The MM7F adapter review (F1-note / risk 1) established that the shape mismatch
(Dict[str, Position] -> List[Dict], enum -> string) is trivial, but the
SYMBOL-NAMESPACE mismatch is the substantive hazard. This file pins it.

The two namespaces:

  * Internal ledger key — `PositionTracker._positions` is keyed by `fill.symbol`
    (handler.py:326 `update_from_fill(fill)`), i.e. the driver's instrument key /
    order `instrument_token` (e.g. `NSE_FO|53001`, what UpstoxAdapter.place_order
    sends as `instrument_token`, upstox_adapter.py:86). reconcile() iterates these
    raw keys (reconciliation.py:57).
  * Upstox position symbol — `UpstoxAdapter.get_positions()` keys on
    `pos_data['trading_symbol']` (upstox_adapter.py:131-132), the broker's
    human display symbol (e.g. `NIFTY26JAN2623500CE`), NOT the instrument_token.

reconcile() matches these by RAW STRING (reconciliation.py:54,57,77). The existing
net (test_reconciliation_broker.py, test_broker_positions_adapter.py) masks the
hazard by using `"RELIANCE"` on BOTH sides — an accidental namespace alignment.

These tests CHARACTERIZE current behavior — they do not fix it. They prove that
a real live broker book keyed on `trading_symbol`, reconciled today against an
internal ledger keyed on the driver instrument key, produces a FALSE divergence
for EVERY position (one QUANTITY_MISMATCH for the internal leg + one
ORPHANED_BROKER_POSITION for the broker leg), even when the economic position is
identical on both sides. The aligned-namespace cases pin the contrast: when the
keys agree, reconcile() is correct and flags only genuine divergence.

NO adapter. NO reconciliation change. NO broker change. Characterization only.
"""

from datetime import datetime

from core.brokers.upstox_adapter import UpstoxAdapter
from core.clock import ReplayClock
from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.position_models import Position, PositionSide
from core.execution.position_tracker import PositionTracker
from core.execution.reconciliation import ReconciliationEngine
from core.instruments.equity import Equity


# --------------------------------------------------------------------------- #
# Helpers — reuse the existing net's adapter stub + bridge glue, so these tests
# run through the REAL broker shape (UpstoxAdapter.get_positions) and the
# documented shape bridge, isolating the namespace variable.
# --------------------------------------------------------------------------- #
def _adapter(rows):
    a = UpstoxAdapter("key", "secret", "token",
                      ReplayClock(datetime(2026, 1, 1, 9, 15)))
    a._make_request = lambda *args, **kwargs: {"status": "success", "data": rows}
    return a


def _bridge(adapter):
    """MM7H #6b.1: the production shape transform `to_reconcile_positions`. The
    broker dict's KEY (`trading_symbol`) becomes the reconcile `symbol` — the shape
    adapter carries the broker namespace through UNCHANGED. Key-mapping is NOT part
    of the shape bridge (that is the open #6b.2 / 4C.8 question this file motivates)."""
    return to_reconcile_positions(adapter.get_positions())


# --------------------------------------------------------------------------- #
# (1) NAMESPACE MATCH — keys agree on both sides, position identical -> clean.
# This is the (accidental) alignment the existing net relies on; pin it as the
# baseline the namespace mismatch is measured against.
# --------------------------------------------------------------------------- #
def test_aligned_namespace_consistent_position_no_alert():
    internal = PositionTracker()
    internal._positions["RELIANCE"] = Position(
        instrument=Equity("RELIANCE"), side=PositionSide.LONG,
        quantity=10, avg_price=2500.0)
    engine = ReconciliationEngine(internal)

    adapter = _adapter([
        {"trading_symbol": "RELIANCE", "quantity": "10", "average_price": "2500.5"},
    ])

    # Keys agree ("RELIANCE" == "RELIANCE"): reconcile sees one matched position.
    assert engine.reconcile(_bridge(adapter)) == []


# --------------------------------------------------------------------------- #
# (4) QUANTITY MISMATCH with MATCHING namespace — keys agree, quantities differ
# -> exactly one genuine QUANTITY_MISMATCH (no spurious orphan). Proves reconcile
# is correct WHEN the namespaces align.
# --------------------------------------------------------------------------- #
def test_aligned_namespace_quantity_mismatch_single_alert():
    internal = PositionTracker()
    internal._positions["RELIANCE"] = Position(
        instrument=Equity("RELIANCE"), side=PositionSide.LONG,
        quantity=10, avg_price=2500.0)
    engine = ReconciliationEngine(internal)

    adapter = _adapter([
        {"trading_symbol": "RELIANCE", "quantity": "5", "average_price": "2500.5"},
    ])

    alerts = engine.reconcile(_bridge(adapter))
    assert len(alerts) == 1
    assert alerts[0].issue == "QUANTITY_MISMATCH"
    assert alerts[0].symbol == "RELIANCE"
    assert alerts[0].internal_value == 10.0
    assert alerts[0].broker_value == 5.0


# --------------------------------------------------------------------------- #
# (3) ORPHANED BROKER POSITION — internal book empty, broker holds a position
# keyed on its trading_symbol -> ORPHANED_BROKER_POSITION. Pin the orphan path
# in isolation (no internal leg to also mismatch).
# --------------------------------------------------------------------------- #
def test_orphaned_broker_position_when_internal_empty():
    engine = ReconciliationEngine(PositionTracker())   # empty internal book

    adapter = _adapter([
        {"trading_symbol": "NIFTY26JAN2623500CE", "quantity": "50",
         "average_price": "120.0"},
    ])

    alerts = engine.reconcile(_bridge(adapter))
    assert len(alerts) == 1
    assert alerts[0].issue == "ORPHANED_BROKER_POSITION"
    assert alerts[0].symbol == "NIFTY26JAN2623500CE"
    assert alerts[0].broker_value == 50.0


# --------------------------------------------------------------------------- #
# (2) NAMESPACE MISMATCH — THE HAZARD. The SAME economic position (LONG 50) is
# held internally under the driver instrument key (`NSE_FO|53001`) and reported
# by the broker under its trading_symbol (`NIFTY26JAN2623500CE`). reconcile()'s
# raw-string match treats the two keys as two unrelated symbols, producing a
# DOUBLE false divergence: a QUANTITY_MISMATCH on the internal leg (internal 50
# vs broker 0) AND an ORPHANED_BROKER_POSITION on the broker leg. A shape-only
# adapter (no key mapping) reconciled live would refuse to start on every run.
# --------------------------------------------------------------------------- #
def test_mismatched_namespace_same_position_double_false_divergence():
    internal = PositionTracker()
    # Internal ledger keyed on the driver instrument key (the order instrument_token).
    internal._positions["NSE_FO|53001"] = Position(
        instrument=Equity("NSE_FO|53001"), side=PositionSide.LONG,
        quantity=50, avg_price=120.0)
    engine = ReconciliationEngine(internal)

    # Broker reports the identical position under its trading_symbol namespace.
    adapter = _adapter([
        {"trading_symbol": "NIFTY26JAN2623500CE", "quantity": "50",
         "average_price": "120.0"},
    ])

    alerts = engine.reconcile(_bridge(adapter))

    # Current behavior: the economically-matched position is flagged TWICE.
    issues = {(a.symbol, a.issue) for a in alerts}
    assert issues == {
        ("NSE_FO|53001", "QUANTITY_MISMATCH"),       # internal leg vs broker 0
        ("NIFTY26JAN2623500CE", "ORPHANED_BROKER_POSITION"),  # broker leg vs internal 0
    }
    assert len(alerts) == 2
