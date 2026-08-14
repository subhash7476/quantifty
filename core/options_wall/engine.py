"""Options-Wall scan engine — ties provider + store + analytics + scanner.

One call site for "produce today's ranked farm list for Nifty and BankNifty":

    load-or-fetch the near-weekly chain (fresh from the wall store if recent,
    live fetch otherwise) -> structural metrics -> realized vol -> bid/ask
    enrichment -> ChainScanner -> ranked ScanResult list.

Read-only with respect to the store unless it has to fetch a stale/missing chain.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.data.options_provider import OptionsProvider
from core.data import options_wall_store as store
from core.analytics.options_analytics import OptionsAnalytics, OptionsStructuralData
from core.analytics.chain_scanner import ChainScanner, ScanConfig, ScanResult
from core.analytics.realized_vol import session_realized_vol_pct
from core.brokers.upstox_market_data import UpstoxMarketData

UNDERLYINGS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

STALE_AFTER_S = 60.0


def _load_or_fetch(sym: str, expiry: str, provider: OptionsProvider):
    """Latest snapshot from the store if fresh, else live fetch (and append)."""
    rows = store.latest_snapshot(sym, expiry)
    ts_list = store.snapshot_timestamps(sym)
    if rows and ts_list:
        age = (datetime.now() - ts_list[-1]).total_seconds()
        if age < STALE_AFTER_S:
            return rows

    fetched, _ = provider._fetch_from_upstox(sym, expiry)
    if fetched:
        store.append_snapshot(fetched, sym, expiry)
    return fetched if fetched else rows


def scan_underlying(
    name: str,
    provider: Optional[OptionsProvider] = None,
    config: Optional[ScanConfig] = None,
) -> Tuple[List[ScanResult], Optional[OptionsStructuralData], Optional[float]]:
    """Scan one index (NIFTY / BANKNIFTY) and return (results, structural, rv)."""
    sym = UNDERLYINGS[name]
    provider = provider or OptionsProvider(read_only=True)
    expiry = provider.get_weekly_expiry(sym)

    chain = _load_or_fetch(sym, expiry, provider)
    if not chain:
        return [], None, None

    underlying_ltp = chain[0].underlying_ltp or 0.0
    structural = OptionsAnalytics().build_structural_snapshot(
        chain, sym, underlying_ltp, expiry)

    rv = session_realized_vol_pct(sym)

    keys = [r.instrument_key for r in chain if r.instrument_key]
    quotes: Dict[str, dict] = {}
    if keys:
        quotes = UpstoxMarketData().fetch_quotes_batch(keys).get("quotes", {})

    results = ChainScanner(config).scan_chain(chain, structural, rv, quotes)
    return results, structural, rv


def scan_indices(
    names: Tuple[str, ...] = ("NIFTY", "BANKNIFTY"),
    config: Optional[ScanConfig] = None,
) -> Dict[str, dict]:
    """Scan the given indices; returns {name: {results, structural, rv}}."""
    provider = OptionsProvider(read_only=True)
    out: Dict[str, dict] = {}
    for name in names:
        results, structural, rv = scan_underlying(name, provider, config)
        out[name] = {"results": results, "structural": structural, "rv": rv}
    return out
