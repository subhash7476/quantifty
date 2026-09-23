"""EOD NIFTY gamma-exposure regime from options bhavcopy.

Implements §4 of docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md.
Sign convention (an assumption): dealers long calls, short puts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from core.execution.options.nifty_shield_pricing import bs_price

RATE = 0.065
MAX_DTE = 45
MIN_PRICE = 0.5
MONEYNESS_BAND = 0.10
IV_MIN, IV_MAX = 0.01, 3.0
MAX_FWD_DEV = 0.02
MIN_STRIKES = 10
FLIP_EDGE = 0.05
FLIP_GRID = np.round(np.arange(-FLIP_EDGE, FLIP_EDGE + 1e-9, 0.001), 6)


def bs_gamma(spot, strike, t_years, rate, iv):
    vol_t = iv * np.sqrt(t_years)
    d1 = (np.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / vol_t
    return np.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (spot * vol_t)


def implied_vol(price, spot, strike, t_years, rate, option_type):
    def err(v):
        return bs_price(spot, strike, t_years, rate, v, option_type) - price
    if err(IV_MIN) > 0 or err(IV_MAX) < 0:
        return None
    return brentq(err, IV_MIN, IV_MAX, xtol=1e-7)


def parity_forward(chain: pd.DataFrame, t_years: float, rate: float = RATE):
    traded = chain[chain["contracts"] > 0]
    wide = traded.pivot_table(index="strike", columns="option_type", values="close", aggfunc="first")
    if "CE" not in wide.columns or "PE" not in wide.columns:
        return None
    wide = wide.dropna(subset=["CE", "PE"])
    if wide.empty:
        return None
    diff = wide["CE"] - wide["PE"]
    k = diff.abs().idxmin()
    return float(k + diff[k] * math.exp(rate * t_years))


@dataclass(frozen=True)
class ExpiryStrikes:
    forward: float
    t_years: float
    strikes: np.ndarray
    iv: np.ndarray
    oi_ce: np.ndarray
    oi_pe: np.ndarray


def select_strikes(chain: pd.DataFrame, forward: float, t_years: float, rate: float = RATE) -> ExpiryStrikes:
    oi = (chain.pivot_table(index="strike", columns="option_type", values="open_int",
                            aggfunc="sum", fill_value=0)
          .reindex(columns=["CE", "PE"], fill_value=0))
    spot_star = forward * math.exp(-rate * t_years)
    kept = []
    for r in chain.sort_values("strike").itertuples(index=False):
        otm = "PE" if r.strike < forward else "CE"
        if r.option_type != otm or r.contracts <= 0 or r.close < MIN_PRICE:
            continue
        if abs(math.log(r.strike / forward)) > MONEYNESS_BAND:
            continue
        iv = implied_vol(r.close, spot_star, r.strike, t_years, rate, otm)
        if iv is None:
            continue
        kept.append((r.strike, iv, oi.at[r.strike, "CE"], oi.at[r.strike, "PE"]))
    arr = np.array(kept, float).reshape(-1, 4)
    return ExpiryStrikes(forward, t_years, arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3])


@dataclass(frozen=True)
class DayRegime:
    n_strikes: int
    net_norm: float
    sign: int
    flip_x: float
    censored: bool


def _exposure(e: ExpiryStrikes, x: float):
    spot = e.forward * math.exp(-RATE * e.t_years) * (1 + x)
    fwd = e.forward * (1 + x)
    g = bs_gamma(spot, e.strikes, e.t_years, RATE, e.iv) * fwd * fwd * 0.01
    return g * (e.oi_ce - e.oi_pe), g * (e.oi_ce + e.oi_pe)


def _flip(expiries):
    net = np.array([sum(_exposure(e, x)[0].sum() for e in expiries) for x in FLIP_GRID])
    idx = np.where(np.sign(net[:-1]) * np.sign(net[1:]) < 0)[0]
    if idx.size == 0:
        at_spot = net[len(net) // 2]
        return (-FLIP_EDGE if at_spot > 0 else FLIP_EDGE), True
    i = idx[np.argmin(np.abs(FLIP_GRID[idx] + FLIP_GRID[idx + 1]))]
    x0, x1, g0, g1 = FLIP_GRID[i], FLIP_GRID[i + 1], net[i], net[i + 1]
    return float(x0 - g0 * (x1 - x0) / (g1 - g0)), False


def day_regime(expiries: list[ExpiryStrikes]) -> DayRegime:
    signed = sum(_exposure(e, 0.0)[0].sum() for e in expiries)
    gross = sum(_exposure(e, 0.0)[1].sum() for e in expiries)
    flip_x, censored = _flip(expiries)
    return DayRegime(
        n_strikes=int(sum(len(e.strikes) for e in expiries)),
        net_norm=float(signed / gross),
        sign=int(np.sign(signed)),
        flip_x=flip_x,
        censored=censored,
    )
