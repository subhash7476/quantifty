"""Options-Wall scan engine — ties provider + store + analytics + scanner.

Two entry points:

  scan_underlying / scan_indices — read-only: produce the ranked farm list from
      the newest wall-store snapshot (live fetch into memory only if the store is
      stale/missing; the poller is the store's sole writer).

  scan_and_persist — read the newest snapshot, scan, and write scan_results +
      session_regime (and capture the 09:15 OI baseline) into the results DB.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from core.analytics.chain_scanner import ChainScanner, ScanConfig, ScanResult
from core.analytics.options_analytics import OptionsAnalytics, OptionsStructuralData
from core.analytics.realized_vol import session_realized_vol_pct
from core.analytics import wall_metrics as wm
from core.brokers.upstox_market_data import UpstoxMarketData
from core.data import options_wall_store as store
from core.data.options_provider import OptionsProvider
from core.options_wall import persistence

UNDERLYINGS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}

DEALER_SIDE = "inferred"   # per-contract sign from the OI×price grid (wall_metrics doc)

STALE_AFTER_S = 60.0


def _load_chain(sym: str, provider: OptionsProvider):
    """Newest snapshot from the store if fresh, else a live fetch (memory only)."""
    expiry = provider.get_weekly_expiry(sym)
    rows = store.latest_snapshot(sym, expiry)
    ts_list = store.snapshot_timestamps(sym)
    if rows and ts_list:
        age = (datetime.now() - ts_list[-1]).total_seconds()
        if age < STALE_AFTER_S:
            return rows, expiry
    return provider.fetch_option_chain(sym, expiry), expiry


def _run_scan(chain, sym, expiry, config):
    underlying_ltp = chain[0].underlying_ltp or 0.0
    structural = OptionsAnalytics().build_structural_snapshot(
        chain, sym, underlying_ltp, expiry, dealer_side=DEALER_SIDE)
    rv = session_realized_vol_pct(sym)

    keys = [r.instrument_key for r in chain if r.instrument_key]
    quotes: Dict[str, dict] = {}
    if keys:
        quotes = UpstoxMarketData().fetch_quotes_batch(keys).get("quotes", {})

    results = ChainScanner(config).scan_chain(chain, structural, rv, quotes)
    return results, structural, rv


def _atm_iv(chain, spot):
    strike = min({r.strike for r in chain}, key=lambda s: abs(s - spot))
    ivs = [r.iv for r in chain if r.strike == strike and r.iv]
    return sum(ivs) / len(ivs) if ivs else None


def _regime_snapshot(structural, chain, rv, oi_baseline=None, now=None) -> Dict:
    gex = structural.gex
    dist = gex.gamma_by_strike
    spot = structural.underlying_ltp
    now = now or datetime.now()

    pins = wm.pin_candidates(gex.gamma_ce_by_strike, gex.gamma_pe_by_strike)
    pin = pins["pin"]
    if pin is None and dist:
        pin = max(dist, key=lambda s: dist[s])
    ceiling, floor = wm.gamma_walls(gex.gamma_ce_by_strike, gex.gamma_pe_by_strike)
    atm_iv = _atm_iv(chain, spot)
    tte = wm.time_to_expiry_years(structural.expiry, now)
    return {
        "trade_date": now.date(),
        "regime": gex.regime,
        "net_gamma_total": gex.net_gamma_total,
        "zero_gamma_level": gex.zero_gamma_level,
        "pin_strike": pin,
        "put_wall": structural.oi_analysis.support_strike,
        "call_wall": structural.oi_analysis.resistance_strike,
        "atm_iv": atm_iv,
        "realized_vol": rv,
        "underlying_ltp": spot,
        "gamma_by_strike": dist,
        "net_gex_cr": gex.net_gex_cr,
        "hhi": wm.hhi(dist),
        "hhi_call": wm.hhi(gex.gamma_ce_by_strike),
        "hhi_put": wm.hhi(gex.gamma_pe_by_strike),
        "pin_conviction": pins["conviction"],
        "pin_margin": pins["margin"],
        "runner_up": pins["runner_up"],
        "gex_at_pin_cr": gex.gex_cr_by_strike.get(pin) if pin is not None else None,
        "gamma_ceiling": ceiling,
        "gamma_floor": floor,
        "sigma_pts": wm.sigma_points(spot, atm_iv, tte),
        "side_coverage": gex.side_coverage,
        "side_reliable": gex.side_reliable,
        "hedge_ladder": wm.hedge_ladder(dist, spot),
        "oi_rotation": wm.oi_since_open(chain, oi_baseline or {}),
    }


def scan_underlying(
    name: str,
    provider: Optional[OptionsProvider] = None,
    config: Optional[ScanConfig] = None,
) -> Tuple[List[ScanResult], Optional[OptionsStructuralData], Optional[float]]:
    """Scan one index (NIFTY / BANKNIFTY); return (results, structural, rv)."""
    sym = UNDERLYINGS[name]
    provider = provider or OptionsProvider(read_only=True)
    chain, expiry = _load_chain(sym, provider)
    if not chain:
        return [], None, None
    return _run_scan(chain, sym, expiry, config)


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


def scan_and_persist(
    names: Tuple[str, ...] = ("NIFTY", "BANKNIFTY"),
    config: Optional[ScanConfig] = None,
) -> Dict[str, int]:
    """Scan each index and persist scan_results + session_regime + OI baseline.

    Returns {name: number of scan_results rows written} for indices whose chain
    resolved; a name with no chain is omitted.
    """
    provider = OptionsProvider(read_only=True)
    written: Dict[str, int] = {}
    for name in names:
        sym = UNDERLYINGS[name]
        chain, expiry = _load_chain(sym, provider)
        if not chain:
            continue
        results, structural, rv = _run_scan(chain, sym, expiry, config)
        persistence.write_scan_results(results, sym)
        persistence.capture_oi_baseline(chain, sym)
        baseline = persistence.get_oi_baseline(sym)
        persistence.write_regime(sym, _regime_snapshot(structural, chain, rv, baseline))
        written[name] = len(results)
    return written
