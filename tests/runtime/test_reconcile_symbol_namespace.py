"""
MM.7G — Broker-position symbol-NAMESPACE characterization (G5) + #6b.3 acceptance.

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

The first four tests pin the shape-adapter path (no re-key):
  - aligned namespace → 0 alerts (correct)
  - matching namespace qty mismatch → 1 QUANTITY_MISMATCH (correct)
  - orphaned broker position (no internal counterpart) → 1 ORPHANED_BROKER_POSITION
  - NAMESPACE MISMATCH (shape-adapter path only) → 2 false alerts — the smoking gun

#6b.3 (token-primary wiring) accepts this: `rekey_broker_positions_by_token`
re-keys the broker book on instrument_token before the shape adapter runs, so both
sides of reconcile() share the same `NSE_FO|<token>` key space, eliminating the
false divergence. Positions whose instrument_token is None are excluded and returned
as UNRECONCILABLE_UNMAPPED_POSITION alerts (distinct from ORPHANED — they cannot be
mapped into the key space at all).

instrument_token observed present for live NSE_EQ positions (6B.ENDPOINT capture);
treated as present-for-live-NSE_EQ, not guaranteed for all position types.
Implementation tolerates instrument_token is None per MM7J.2 design.
"""

from datetime import datetime

from core.brokers.upstox_adapter import UpstoxAdapter
from core.clock import ReplayClock
from core.execution.broker_positions_adapter import to_reconcile_positions
from core.execution.position_models import Position, PositionSide
from core.execution.position_tracker import PositionTracker
from core.execution.reconciliation import ReconciliationEngine
from core.brokers.token_rekey import rekey_broker_positions_by_token
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
# (2) NAMESPACE MISMATCH — THE HAZARD (shape-adapter path only, for reference).
# The SAME economic position (LONG 50) is held internally under the driver
# instrument key (`NSE_FO|53001`) and reported by the broker under its
# trading_symbol (`NIFTY26JAN2623500CE`). A shape-only adapter produces a
# DOUBLE false divergence: a QUANTITY_MISMATCH on the internal leg (internal 50
# vs broker 0) AND an ORPHANED_BROKER_POSITION on the broker leg.
#
# #6b.3 ACCEPTANCE: with token-primary wiring (rekey_broker_positions_by_token)
# before the shape adapter, both sides key on `NSE_FO|53001` → 0 alerts.
# The broker payload must carry instrument_token for the re-key to succeed.
# --------------------------------------------------------------------------- #
def test_mismatched_namespace_same_position_double_false_divergence():
    internal = PositionTracker()
    # Internal ledger keyed on the driver instrument key (the order instrument_token).
    internal._positions["NSE_FO|53001"] = Position(
        instrument=Equity("NSE_FO|53001"), side=PositionSide.LONG,
        quantity=50, avg_price=120.0)
    engine = ReconciliationEngine(internal)

    # Broker reports the same position under its trading_symbol namespace BUT
    # carries instrument_token = the ledger key.  The token-primary re-key
    # converts the dict from {trading_symbol: pos} to {instrument_token: pos}
    # before the shape adapter runs, so reconcile() sees matching keys.
    adapter = _adapter([
        {"instrument_token": "NSE_FO|53001",
         "trading_symbol": "NIFTY26JAN2623500CE", "quantity": "50",
         "average_price": "120.0"},
    ])

    raw = adapter.get_positions()
    rekeyed, pre_alerts = rekey_broker_positions_by_token(raw)
    alerts = pre_alerts + engine.reconcile(to_reconcile_positions(rekeyed))

    # #6b.3 acceptance: the economically-matched position produces 0 alerts.
    assert alerts == []


# --------------------------------------------------------------------------- #
# #6b.3 — None-token BrokerPosition path.
# A position whose instrument_token is None (e.g. equity same-day delivery shape
# where the token field was absent in the payload) cannot be mapped into the
# `NSE_FO|<token>` key space. It is excluded from the reconcile input and
# returned as an UNRECONCILABLE_UNMAPPED_POSITION alert with cause metadata.
# --------------------------------------------------------------------------- #
def test_none_token_broker_position_is_excluded_and_emits_unreconcilable():
    adapter = _adapter([
        {"trading_symbol": "RELIANCE", "quantity": "10", "average_price": "2500.5"},
    ])
    raw = adapter.get_positions()  # instrument_token is None — no token in payload

    rekeyed, pre_alerts = rekey_broker_positions_by_token(raw)

    assert rekeyed == {}
    assert len(pre_alerts) == 1
    assert pre_alerts[0].issue == "UNRECONCILABLE_UNMAPPED_POSITION"
    assert pre_alerts[0].symbol == "RELIANCE"
    assert pre_alerts[0].internal_value == "missing_token"


def test_none_token_position_excluded_from_reconcile_engine():
    """The UNRECONCILABLE position does not reach reconcile() — the engine
    never sees it, so it cannot generate a spurious ORPHANED_BROKER_POSITION."""
    engine = ReconciliationEngine(PositionTracker())  # empty internal book

    adapter = _adapter([
        {"trading_symbol": "RELIANCE", "quantity": "10", "average_price": "2500.5"},
    ])
    raw = adapter.get_positions()
    rekeyed, pre_alerts = rekey_broker_positions_by_token(raw)

    engine_alerts = engine.reconcile(to_reconcile_positions(rekeyed))

    # engine sees nothing (rekeyed is empty) → no engine alerts
    assert engine_alerts == []
    # The only alert is the UNRECONCILABLE pre-alert
    assert len(pre_alerts) == 1
    assert pre_alerts[0].issue == "UNRECONCILABLE_UNMAPPED_POSITION"
