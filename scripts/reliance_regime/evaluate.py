"""Long/Flat evaluation for the RELIANCE regime research.

Position decided at close(t) from the signal at t; the strategy return for
day t is position(t) * ret[t->t+1] where ret[t->t+1] = close(t+1)/close(t)-1.
Fees are era-accurate delivery-equity costs (core/execution/equity/
delivery_fees.py) charged on every entry and exit at a fixed notional
(1,00,000) — STT 0.1% per leg dominates, exactly as the PSB line found.

Metrics: in-market fraction, round trips/year, gross and net daily means
(over all days and in-market days), annualized net return, annualized
strategy vol, Sharpe-like ratio, max drawdown of the net equity curve, hit
rate, IC (corr(signal_t, ret_{t+1})) with Newey-West t, and a block
bootstrap 95% CI for the net daily mean.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from core.execution.equity.delivery_fees import delivery_equity_fees
from scripts.reliance_regime.stats import block_bootstrap_ci, nw_t

NOTIONAL = 100_000.0


def _fees_buy(d: date) -> float:
    return delivery_equity_fees(side="BUY", trade_value=NOTIONAL,
                                trade_date=d).total / NOTIONAL


def _fees_sell(d: date) -> float:
    return delivery_equity_fees(side="SELL", trade_value=NOTIONAL,
                                trade_date=d).total / NOTIONAL


def backtest(panel: pd.DataFrame, signal: pd.Series) -> dict:
    ret = panel["ret"]
    sig = signal.reindex(panel.index).ffill().fillna(0.0)
    # position for day t is the signal at t (decided at close t, held over
    # the t -> t+1 return): align signal(t) with ret[t->t+1]
    pos = sig.shift(1)
    strat_ret = pos * ret
    valid = ret.notna() & pos.notna()
    strat_ret = strat_ret[valid]
    pos = pos[valid]
    ret = ret[valid]
    dates = panel.index[valid]

    in_mkt = pos > 0.5
    n = len(strat_ret)
    n_in = int(in_mkt.sum())
    days_in = pd.Series(in_mkt.values, index=dates)
    # round trips: buy toggles
    buys = days_in.astype(int).diff().fillna(days_in.astype(int)).clip(lower=0)
    sells = (-days_in.astype(int).diff()).fillna(0.0).clip(lower=0)
    trades = int(buys.sum() + sells.sum())

    fee_series = pd.Series(0.0, index=dates)
    buy_dates = dates[buys.values.astype(bool)]
    sell_dates = dates[sells.values.astype(bool)]
    fee_series.loc[buy_dates] += [_fees_buy(d) for d in buy_dates]
    fee_series.loc[sell_dates] += [_fees_sell(d) for d in sell_dates]

    net = strat_ret - fee_series
    net_in = net[in_mkt]
    eq = (1.0 + net).cumprod()
    gross_mean_in = float(strat_ret[in_mkt].mean())
    ann_net = float(net.mean()) * 252.0
    ann_vol = float(net.std()) * np.sqrt(252.0)
    always = ret.mean() * 252.0
    always_fee = float(np.mean([_fees_buy(d) for d in buy_dates]) * trades / max(n, 1)
                       * 252.0) if trades else 0.0
    run_max = eq.cummax()
    dd = (eq / run_max - 1.0).min()

    ic = np.corrcoef(sig[valid], ret)[0, 1]
    lo, hi = block_bootstrap_ci(net.values)
    out = {
        "n_days": n,
        "n_in_market": n_in,
        "in_market_fraction": n_in / n,
        "round_trips": trades,
        "trades_per_year": trades / n * 252.0,
        "gross_mean_in_market_daily": gross_mean_in,
        "net_mean_daily": float(net.mean()),
        "net_mean_in_market_daily": float(net_in.mean()),
        "ann_net_return": ann_net,
        "ann_strategy_vol": ann_vol,
        "sharpe_like": ann_net / ann_vol if ann_vol > 0 else None,
        "always_long_ann_gross": always,
        "max_drawdown": float(dd),
        "hit_rate": float((net_in > 0).mean()),
        "ic": float(ic) if np.isfinite(ic) else None,
        "ic_nw_t": float(nw_t((sig[valid] - sig[valid].mean())
                              * (ret - ret.mean())
                              / (sig[valid].std() * ret.std()))),
        "ci95_lo": lo,
        "ci95_hi": hi,
        "fees_paid_fraction": float(fee_series.sum() / n),
    }
    return out


def regime_buckets(panel: pd.DataFrame, signal: pd.Series,
                   n_buckets: int = 3) -> dict:
    """Descriptive: net strategy return by trailing-volatility regime."""
    ret = panel["ret"]
    sig = signal.reindex(panel.index).ffill().fillna(0.0)
    pos = sig.shift(1)
    rv = ret.rolling(20).std()
    rv_pct = rv.rolling(252).apply(lambda w: (w[:-1] < w[-1]).mean(),
                                   raw=True)
    valid = ret.notna() & pos.notna()
    strat = (pos * ret)[valid]
    pct = rv_pct[valid]
    out = {}
    for b in range(n_buckets):
        mask = (pct > b / n_buckets) & (pct <= (b + 1) / n_buckets)
        out[f"vol_bucket_{b}"] = {
            "n": int(mask.sum()),
            "net_mean_daily": float(strat[mask].mean()) if mask.sum() else None,
        }
    return out
