"""Intraday option-chain scanner — the Options-Wall "farm list".

Reads one chain snapshot (List[OptionChainRow]) plus its structural metrics and
scores three screens:

  (a) Premium Farm  — short premium where GEX is positive and IV is rich vs realized.
  (b) Imperfections — call-put-IV asymmetry and single-strike vol outliers.
  (c) Laggards      — a fresh flip cross or near-expiry charm cascade.

Each screen returns its own ranked list; `scan_chain` concatenates them in screen
priority (farm first — that is the actionable deliverable). Within the farm screen
rows are ranked by per-strike IV−RV gap (the "actual edge"), descending. There is
no SPAN margin here yet, so ranking is on the vol premium, not on credit/margin.

This is a discovery instrument: it returns a ranked list of ScanResult rows. It does
not size, route, or place orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional

from core.data.options_provider import OptionChainRow
from core.analytics.options_analytics import OptionsStructuralData


@dataclass
class ScanConfig:
    """Thresholds for the three screens. Display parameters, not tuned fits.

    All vol quantities (iv, realized_vol, gaps, outliers) are in PERCENTAGE
    POINTS, matching `OptionChainRow.iv` from Upstox.
    """

    iv_rv_min_gap: float = 2.0            # per-strike (IV - RV) floor to farm premium
    pin_band_pct: float = 0.005           # |S - pin| / S to count as "near pin"
    vol_outlier_sigma: float = 2.0        # strike IV deviation vs neighbours (vol pts)
    lag_spot_move_pct: float = 0.3        # flip-cross window, % of spot
    charm_dte_max: int = 2                # DTE bound for the charm-cascade flag
    max_spread_pct: float = 0.05          # skip farm legs whose bid/ask spread exceeds this
    vol_scan_band_pct: float = 0.05       # vol-outlier scan window (|S - strike|/S)


@dataclass
class ScanResult:
    """One row of the farm list."""

    underlying: str
    expiry: str
    strike: Optional[float]
    option_type: Optional[str]
    screen: str
    structure: str
    regime: str
    score: float = 0.0
    credit: Optional[float] = None
    iv_minus_rv: Optional[float] = None
    pin_conviction: Optional[float] = None
    reason: str = ""
    ts: datetime = field(default_factory=datetime.now)


class ChainScanner:
    """Scores a chain snapshot into a ranked farm list."""

    def __init__(self, config: Optional[ScanConfig] = None):
        self.config = config or ScanConfig()

    def scan_chain(
        self,
        chain: List[OptionChainRow],
        structural: OptionsStructuralData,
        realized_vol: Optional[float] = None,
        quotes: Optional[dict] = None,
    ) -> List[ScanResult]:
        """Run all three screens; farm first, each screen internally ranked desc.

        `realized_vol` and every `iv` are in percentage points. `quotes` is the
        optional bid/ask enrichment from `UpstoxMarketData.fetch_quotes_batch`,
        keyed by `instrument_key`; when absent the farm screen skips its
        spread/liquidity guard.
        """
        if not chain or structural.gex is None:
            return []

        results: List[ScanResult] = []
        results.extend(self._farm_screen(chain, structural, realized_vol, quotes))
        results.extend(self._imperfection_screen(chain, structural))
        results.extend(self._laggard_screen(chain, structural))
        return results

    # ------------------------------------------------------------------ (a) farm

    def _farm_screen(self, chain, structural, realized_vol, quotes=None):
        cfg = self.config
        if realized_vol is None:
            return []
        if "Positive" not in (structural.gex.regime or ""):
            return []

        pin = self._pin_strike(structural)
        conviction = self._pin_conviction(structural, pin)

        out: List[ScanResult] = []
        for strike in self._farmable_strikes(chain, structural, pin):
            if quotes is not None and not self._spread_ok(strike, chain, quotes):
                continue
            credit = self._credit_at_strike(chain, strike)
            if credit is None or credit <= 0:
                continue
            strike_iv = self._strike_mid_iv(chain, strike)
            gap = (strike_iv - realized_vol) if strike_iv is not None else None
            if gap is None or gap < cfg.iv_rv_min_gap:
                continue

            out.append(
                ScanResult(
                    underlying=structural.underlying,
                    expiry=structural.expiry,
                    strike=strike,
                    option_type=None,
                    screen="premium_farm",
                    structure="iron_fly",
                    regime=structural.gex.regime,
                    score=gap,
                    credit=credit,
                    iv_minus_rv=gap,
                    pin_conviction=conviction,
                    reason=f"IV-RV {gap:.1f}pt @pin",
                )
            )
        return sorted(out, key=lambda r: r.score, reverse=True)

    # -------------------------------------------------------- (b) imperfections

    def _imperfection_screen(self, chain, structural):
        cfg = self.config
        spot = structural.underlying_ltp
        out: List[ScanResult] = []

        ce_iv, pe_iv = self._atm_ce_pe_iv(chain, spot)
        if ce_iv is not None and pe_iv is not None:
            asym = ce_iv - pe_iv
            if abs(asym) > cfg.vol_outlier_sigma:
                side = "CE" if asym > 0 else "PE"
                out.append(
                    ScanResult(
                        underlying=structural.underlying,
                        expiry=structural.expiry,
                        strike=self._atm_strike(chain, spot),
                        option_type=side,
                        screen="imperfection",
                        structure="iv_asymmetry",
                        regime=structural.gex.regime,
                        score=abs(asym),
                        reason=f"CE-PE IV {asym:+.1f}pt",
                    )
                )

        for strike, outlier_iv, dev in self._vol_outliers(chain, spot):
            out.append(
                ScanResult(
                    underlying=structural.underlying,
                    expiry=structural.expiry,
                    strike=strike,
                    option_type=None,
                    screen="imperfection",
                    structure="vol_outlier",
                    regime=structural.gex.regime,
                    score=dev,
                    reason=f"strike IV {outlier_iv:.1f} off neighbours",
                )
            )
        return sorted(out, key=lambda r: r.score, reverse=True)

    # ----------------------------------------------------------- (c) laggards

    def _laggard_screen(self, chain, structural):
        cfg = self.config
        spot = structural.underlying_ltp
        flip = structural.gex.zero_gamma_level
        out: List[ScanResult] = []

        if flip is not None:
            dist_pct = abs(spot - flip) / spot * 100.0
            if dist_pct < cfg.lag_spot_move_pct:
                out.append(
                    ScanResult(
                        underlying=structural.underlying,
                        expiry=structural.expiry,
                        strike=flip,
                        option_type=None,
                        screen="laggard",
                        structure="flip_cross",
                        regime=structural.gex.regime,
                        score=1.0 - dist_pct / cfg.lag_spot_move_pct,
                        reason=f"spot {spot:.0f} vs flip {flip:.0f}",
                    )
                )

        dte = self._dte(structural.expiry)
        if dte is not None and 0 < dte <= cfg.charm_dte_max:
            theta_rows = sorted(
                (r for r in chain if r.theta),
                key=lambda r: abs(r.theta),
                reverse=True,
            )[:5]
            for row in theta_rows:
                out.append(
                    ScanResult(
                        underlying=structural.underlying,
                        expiry=row.expiry,
                        strike=row.strike,
                        option_type=row.option_type,
                        screen="laggard",
                        structure="charm_cascade",
                        regime=structural.gex.regime,
                        score=abs(row.theta),
                        reason=f"DTE {dte} theta {row.theta:.1f}",
                    )
                )
        return sorted(out, key=lambda r: r.score, reverse=True)

    # -------------------------------------------------------------- helpers

    def _farmable_strikes(self, chain, structural, pin):
        if pin is None:
            return []
        strikes = sorted({r.strike for r in chain})
        return [s for s in strikes if abs(s - pin) / structural.underlying_ltp < self.config.pin_band_pct]

    def _credit_at_strike(self, chain, strike):
        ce = next((r.ltp for r in chain if r.strike == strike and r.option_type == "CE" and r.ltp), None)
        pe = next((r.ltp for r in chain if r.strike == strike and r.option_type == "PE" and r.ltp), None)
        if ce is None or pe is None:
            return None
        return ce + pe

    def _spread_ok(self, strike, chain, quotes):
        """Both legs have a quote and their mid spread is inside max_spread_pct."""
        cfg = self.config
        for r in chain:
            if r.strike != strike:
                continue
            q = quotes.get(r.instrument_key) if r.instrument_key else None
            if not q:
                return False
            bid, ask = q.get("best_bid"), q.get("best_ask")
            if not bid or not ask or bid <= 0 or ask <= 0:
                return False
            mid = (bid + ask) / 2.0
            if (ask - bid) / mid > cfg.max_spread_pct:
                return False
        return True

    def _pin_strike(self, structural):
        dist = structural.gex.gamma_by_strike
        if not dist:
            return None
        return max(dist, key=lambda s: dist[s])

    def _pin_conviction(self, structural, pin):
        dist = structural.gex.gamma_by_strike
        if not dist or pin is None:
            return None
        total = sum(abs(v) for v in dist.values())
        if total == 0:
            return None
        return abs(dist[pin]) / total

    def _atm_strike(self, chain, spot):
        return min({r.strike for r in chain}, key=lambda s: abs(s - spot))

    def _atm_ce_pe_iv(self, chain, spot):
        strike = self._atm_strike(chain, spot)
        ce = next((r.iv for r in chain if r.strike == strike and r.option_type == "CE" and r.iv), None)
        pe = next((r.iv for r in chain if r.strike == strike and r.option_type == "PE" and r.iv), None)
        return ce, pe

    def _strike_mid_iv(self, chain, strike):
        ce = next((r.iv for r in chain if r.strike == strike and r.option_type == "CE" and r.iv), None)
        pe = next((r.iv for r in chain if r.strike == strike and r.option_type == "PE" and r.iv), None)
        if ce is None or pe is None:
            return None
        return (ce + pe) / 2.0

    def _vol_outliers(self, chain, spot):
        strikes = sorted({r.strike for r in chain})
        strikes = [s for s in strikes if abs(s - spot) / spot < self.config.vol_scan_band_pct]
        mid_iv = {s: self._strike_mid_iv(chain, s) for s in strikes}
        mid_iv = {s: v for s, v in mid_iv.items() if v is not None}
        if len(mid_iv) < 3:
            return []
        ordered = sorted(mid_iv)
        deviations = []
        for i, s in enumerate(ordered):
            neighbours = [ordered[j] for j in (i - 1, i + 1) if 0 <= j < len(ordered)]
            if not neighbours:
                continue
            base = sum(mid_iv[n] for n in neighbours) / len(neighbours)
            dev = abs(mid_iv[s] - base)
            if dev > self.config.vol_outlier_sigma:
                deviations.append((s, mid_iv[s], dev))
        deviations.sort(key=lambda t: t[2], reverse=True)
        return deviations[:10]

    def _dte(self, expiry: str):
        try:
            return (date.fromisoformat(expiry) - date.today()).days
        except (TypeError, ValueError):
            return None
