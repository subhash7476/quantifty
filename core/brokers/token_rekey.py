"""
Token-primary composition-root re-key (#6b.3).

Re-keys the broker's Dict[str, BrokerPosition] by instrument_token before
feeding to to_reconcile_positions() + reconcile(). Positions without a token
are excluded from the reconcile input and returned as
UNRECONCILABLE_UNMAPPED_POSITION alerts — a distinct alert family from
ORPHANED_BROKER_POSITION (which means "present at broker, absent internally"):
UNRECONCILABLE means "cannot be mapped into the reconcile key space at all".

Lives in core/brokers/ because:
  * BrokerPosition is a broker-layer DTO — the logic that inspects its
    instrument_token field belongs in the same layer.
  * core/execution/ must not import broker-specific DTOs (design review intent
    for the G1/4C.7 boundary, even when the mechanical instrument_key guard
    would not fire on the attribute name instrument_token).

Cause metadata in internal_value:
  "missing_token"  — BrokerPosition.instrument_token is None (equity same-day
                     delivery shape; token absent in the payload).
  "unknown_token"  — reserved for future use (token present but not resolvable).
"""
import time
from typing import Dict, List, Tuple

from core.brokers.broker_position import BrokerPosition
from core.execution.reconciliation import ReconciliationAlert


def rekey_broker_positions_by_token(
    broker_positions: Dict[str, BrokerPosition],
) -> Tuple[Dict[str, BrokerPosition], List[ReconciliationAlert]]:
    """Re-key by instrument_token; emit UNRECONCILABLE_UNMAPPED_POSITION for
    positions whose instrument_token is None.

    Returns (rekeyed, pre_alerts):
      rekeyed    — Dict keyed on instrument_token, ready for to_reconcile_positions.
      pre_alerts — UNRECONCILABLE_UNMAPPED_POSITION alerts for excluded positions.
    """
    rekeyed: Dict[str, BrokerPosition] = {}
    pre_alerts: List[ReconciliationAlert] = []
    now = time.time()

    for trading_sym, pos in broker_positions.items():
        if pos.instrument_token is None:
            pre_alerts.append(ReconciliationAlert(
                symbol=trading_sym,
                issue="UNRECONCILABLE_UNMAPPED_POSITION",
                internal_value="missing_token",
                broker_value=pos.quantity,
                timestamp=now,
            ))
        else:
            rekeyed[pos.instrument_token] = pos

    return rekeyed, pre_alerts
