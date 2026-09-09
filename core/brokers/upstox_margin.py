"""Upstox V2 basket-margin lookup — the exchange margin for a multi-leg order.

One concrete call to `POST /v2/charges/margin`. Given the legs of a proposed
structure it returns the required margin, the final margin (after the spread
benefit a hedged book earns) and the benefit itself — the same three figures the
Upstox order pad shows. Display-only: it never sizes or routes, and never raises;
failures come back in the `error` field so the caller can degrade to "unavailable".

`NseMarginEngine` remains the platform's sizing/computation authority (ADR-011);
this is a broker-reported figure for the dashboard, not a sizing input.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

MARGIN_URL = "https://api.upstox.com/v2/charges/margin"


def fetch_basket_margin(legs: List[Dict], product: str = "D",
                        timeout: float = 6.0) -> Dict:
    """Exchange margin for a basket of F&O legs, as reported by Upstox.

    Args:
        legs: one dict per leg with keys ``instrument_key`` (str),
            ``quantity`` (int, in units — lots × lot_size) and
            ``transaction_type`` ("BUY" / "SELL").
        product: Upstox product code — "D" (carryforward/NRML) or "I" (intraday).

    Returns:
        ``{"required", "final", "benefit", "error"}``. The three figures are
        floats in rupees on success and ``None`` on failure, with ``error`` set.
    """
    if not legs:
        return {"required": None, "final": None, "benefit": None,
                "error": "no legs"}

    from core.auth.credentials import credentials
    token = credentials.get("access_token")
    if not token:
        return {"required": None, "final": None, "benefit": None,
                "error": "No access token — re-authenticate with Upstox"}

    instruments = [{
        "instrument_key": l["instrument_key"],
        "quantity": int(l["quantity"]),
        "transaction_type": l["transaction_type"],
        "product": product,
    } for l in legs]

    try:
        resp = requests.post(
            MARGIN_URL,
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/json",
                     "Content-Type": "application/json"},
            json={"instruments": instruments},
            timeout=timeout,
        )
    except requests.RequestException as e:
        return {"required": None, "final": None, "benefit": None,
                "error": f"{type(e).__name__}: {e}"}

    if resp.status_code != 200:
        return {"required": None, "final": None, "benefit": None,
                "error": f"Upstox HTTP {resp.status_code}"}

    try:
        data = resp.json().get("data", {}) or {}
    except ValueError as e:
        return {"required": None, "final": None, "benefit": None,
                "error": f"Invalid JSON response: {e}"}

    required = data.get("required_margin")
    final = data.get("final_margin")
    if required is None or final is None:
        return {"required": None, "final": None, "benefit": None,
                "error": "margin fields missing in Upstox response"}
    return {"required": float(required), "final": float(final),
            "benefit": float(required) - float(final), "error": None}
