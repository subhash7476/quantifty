"""MSRP Phase-7 research reset: scoping transmission pre-reads.

Two IN-SAMPLE, NON-DECISIVE measurements to rank candidate directions after the
D1 STOP (docs/reports/MSRP_PHASE7_FEE_TRIAGE.md). Nothing here is a backtest or
a gate; the numbers inform the research-reset dossier only.

Pre-read A (candidate A — delta-hedged straddle / gamma scalping):
  Reconstruct a synthetic delta-hedged long straddle over each dev day: enter
  ATM straddle at t+1 bhavcopy open, exit at t+1 bhavcopy close, hedge the
  Black-Scholes straddle delta on the 1m Nifty index path (futures proxy).
  Measure Spearman(RV_{t+1}, hedged return) — the transmission the unhedged
  construct lacked (0.09) — and Spearman(E[RV]/implied, hedged return), plus
  hedge turnover for fee realism.

Pre-read E (candidate E — vol-targeted exposure / risk consumer):
  Measure whether E[RV_{t+1}] (an intraday-RV forecast) carries to NEXT-DAY
  TOTAL volatility (overnight gap included), and whether it adds anything over
  the naive persistence baseline RV_t. Quick vol-targeting Sharpe comparison.

Usage::

    python scripts/msrp/scoping_transmission_preread.py
"""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TRIAGE = ROOT / "scripts" / "msrp" / "triage_fee_impact.py"
spec = importlib.util.spec_from_file_location("triage_fee_impact", TRIAGE)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)

SQRT_2PI_FACTOR = math.sqrt(2.0 / math.pi)  # Brenner-Subrahmanyam straddle approx


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def straddle_delta(s: float, k: float, sigma: float, t_years: float) -> float:
    if sigma <= 0 or t_years <= 0:
        return 0.0
    d1 = (math.log(s / k) + 0.5 * sigma * sigma * t_years) / (sigma * math.sqrt(t_years))
    return 2.0 * norm_cdf(d1) - 1.0


def hedged_day(prices: np.ndarray, k: float, open_prem: float, close_prem: float,
               dte: int, lot: int, rebalance_every: int):
    """Long straddle entered at first 1m close, hedged on the index path.

    Returns (hedged_pnl_rs, unhedged_pnl_rs, hedge_turnover_rs, n_hedge_trades).
    Hedge position is continuous (research-grade); turnover reported so fee
    scenarios can be layered on top.
    """
    s0 = float(prices[0])
    t_years = max(dte, 1) / 365.0
    sigma = open_prem / (s0 * SQRT_2PI_FACTOR * math.sqrt(t_years))
    unhedged = (close_prem - open_prem) * lot

    hedge_pnl = 0.0
    turnover = 0.0
    n_trades = 0
    pos = 0.0  # index units held as hedge
    idx = list(range(0, len(prices), rebalance_every))
    if idx[-1] != len(prices) - 1:
        idx.append(len(prices) - 1)
    for j in range(len(idx) - 1):
        s = float(prices[idx[j]])
        target = -straddle_delta(s, k, sigma, t_years) * lot
        if target != pos:
            turnover += abs(target - pos) * s
            n_trades += 1
            pos = target
        s_next = float(prices[idx[j + 1]])
        hedge_pnl += pos * (s_next - s)
    # unwind at close
    s_last = float(prices[-1])
    if pos != 0.0:
        turnover += abs(pos) * s_last
        n_trades += 1
    return unhedged + hedge_pnl, unhedged, turnover, n_trades


def main() -> None:
    df = triage.build_daily_records()
    closes_by_day = triage.load_nifty_1m_closes_by_day()
    print(f"records: {len(df)}")

    # ---------------- Pre-read A: delta-hedged straddle --------------------
    rows = []
    for r in df.itertuples():
        day = pd.Timestamp(r.trade_date)
        prices = closes_by_day.get(day)
        if prices is None or len(prices) < 30:
            continue
        hedged, unhedged, turnover, n_tr = hedged_day(
            prices, r.strike, r.open_prem, r.close_prem, r.dte, r.lot,
            rebalance_every=15)  # 15-minute rebalance grid
        rows.append({
            "trade_date": r.trade_date, "rv_next": r.rv_next, "e_rv": r.e_rv,
            "implied": r.implied, "ratio": r.ratio, "lot": r.lot,
            "hedged": hedged, "unhedged": unhedged,
            "hedged_ret": hedged / (r.open_prem * r.lot),
            "unhedged_ret": unhedged / (r.open_prem * r.lot),
            "turnover": turnover, "n_hedge_trades": n_tr,
            "straddle_fees": r.fees_long,
        })
    h = pd.DataFrame(rows)
    n = len(h)

    sp_unhedged = h["rv_next"].corr(h["unhedged_ret"], method="spearman")
    sp_hedged = h["rv_next"].corr(h["hedged_ret"], method="spearman")
    sp_signal_hedged = h["ratio"].corr(h["hedged_ret"], method="spearman")

    print("\n=== Pre-read A: synthetic delta-hedged straddle (15m rebalance, index hedge) ===")
    print(f"days: {n}")
    print(f"Spearman(RV_next, UNhedged straddle ret): {sp_unhedged:.3f}  (triage: 0.093)")
    print(f"Spearman(RV_next, hedged straddle ret):   {sp_hedged:.3f}")
    print(f"Spearman(E[RV]/implied, hedged ret):      {sp_signal_hedged:.3f}")
    print(f"mean hedge turnover/day: Rs {h['turnover'].mean():,.0f}; "
          f"mean hedge trades/day: {h['n_hedge_trades'].mean():.1f}")

    # gated arms on the hedged construct, gross and with a crude fee overlay:
    # straddle fees (gate-b model) + hedge cost ~0.012% one-way of turnover + Rs 20/trade
    h["hedge_fees"] = h["turnover"] * 0.00012 + h["n_hedge_trades"] * 20.0
    h["net_long_hedged"] = h["hedged"] - h["straddle_fees"] - h["hedge_fees"]
    h["net_short_hedged"] = -h["hedged"] - h["straddle_fees"] - h["hedge_fees"]
    lo20, hi80 = h["ratio"].quantile(0.2), h["ratio"].quantile(0.8)
    for name, sub, col in (
        ("uncond short hedged", h, "net_short_hedged"),
        ("uncond long hedged", h, "net_long_hedged"),
        ("gated short hedged (ratio<=q20)", h[h["ratio"] <= lo20], "net_short_hedged"),
        ("gated long hedged (ratio>=q80)", h[h["ratio"] >= hi80], "net_long_hedged"),
    ):
        net = sub[col]
        gross = net + sub["straddle_fees"] + sub["hedge_fees"]
        sharpe = net.mean() / net.std() * math.sqrt(252) if len(net) > 1 and net.std() > 0 else 0.0
        print(f"{name:34s} n={len(sub):4d} gross={gross.sum():12,.0f} "
              f"net={net.sum():12,.0f} net/day={net.mean():8,.0f} sharpe={sharpe:6.2f}")

    # ---------------- Pre-read E: total-vol transmission --------------------
    daily = []
    for day in sorted(closes_by_day):
        p = closes_by_day[day]
        daily.append({"date": day, "open": float(p[0]), "close": float(p[-1])})
    dd = pd.DataFrame(daily).set_index("date")
    dd["prev_close"] = dd["close"].shift(1)
    dd["c2c_ret"] = dd["close"] / dd["prev_close"] - 1.0
    dd["overnight_ret"] = dd["open"] / dd["prev_close"] - 1.0
    dd["intraday_ret"] = dd["close"] / dd["open"] - 1.0

    sig = df.set_index(pd.to_datetime(df["signal_date"]))
    sig["trade_ts"] = pd.to_datetime(sig["trade_date"])
    sig["abs_c2c_next"] = sig["trade_ts"].map(dd["c2c_ret"].abs())
    rv_series = pd.Series(triage.compute_daily_rv(closes_by_day))
    sig["rv_t"] = sig.index.map(rv_series)

    e = sig.dropna(subset=["abs_c2c_next", "rv_t", "rv_next"])
    print("\n=== Pre-read E: does the intraday-RV forecast carry to total next-day vol? ===")
    print(f"days: {len(e)}")
    print(f"overnight variance share of c2c: "
          f"{dd['overnight_ret'].var() / dd['c2c_ret'].var() * 100:.1f}%")
    print(f"Spearman(E[RV], RV_next intraday):        {e['e_rv'].corr(e['rv_next'], method='spearman'):.3f}")
    print(f"Spearman(RV_t persistence, RV_next):      {e['rv_t'].corr(e['rv_next'], method='spearman'):.3f}")
    print(f"Spearman(E[RV], |c2c ret| next):          {e['e_rv'].corr(e['abs_c2c_next'], method='spearman'):.3f}")
    print(f"Spearman(RV_t persistence, |c2c| next):   {e['rv_t'].corr(e['abs_c2c_next'], method='spearman'):.3f}")

    # quick vol-target sim on c2c returns (in-sample, indicative only)
    ret_next = e["trade_ts"].map(dd["c2c_ret"])
    print(f"buy-hold ann.Sharpe={ret_next.mean() / ret_next.std() * math.sqrt(252):.2f}, "
          f"ann.vol={ret_next.std() * math.sqrt(252) * 100:.1f}%")
    for label, scaler in (("E[RV] forecast", e["e_rv"]), ("RV_t persistence", e["rv_t"])):
        lev = 1.0 / scaler
        lev = (lev / lev.mean()).clip(upper=2.0)  # mean-normalized, 2x cap
        scaled = ret_next * lev
        print(f"vol-target [{label:16s}]: ann.Sharpe={scaled.mean() / scaled.std() * math.sqrt(252):.2f}, "
              f"ann.vol={scaled.std() * math.sqrt(252) * 100:.1f}%")


if __name__ == "__main__":
    main()
