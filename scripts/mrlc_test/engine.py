"""MRLC-test backtest engine.

Entry = 25-day SMA stretch (price far below the average of the last 25 daily closes,
prior-day anchored) + liquidity sweep (close below recent 10-session low on >=2x
volume, then close back above within 3 bars). Buy at the next bar's open.

Exit = 50% at the 25-day SMA (fixed at signal time), remaining 50% with stop moved
to break-even then trailed stop_mult x ATR(14, same TF) below the highest close;
initial stop = sweep low - stop_mult * ATR; 20-session time stop.

Output: data/mrlc_test/trades_{stop_mult}.csv
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.equity.delivery_fees import delivery_equity_fees  # noqa: E402

CANDLES_DB = ROOT / "data" / "mrlc_test" / "candles.duckdb"
UNIVERSE_CSV = ROOT / "data" / "mrlc_test" / "universe.csv"
OUT_DIR = ROOT / "data" / "mrlc_test"

NOTIONAL = 100_000.0          # Rs per trade, fixed (no compounding)
SMA_DAYS = 25
SUPPORT_SESSIONS = 10         # recent low = min low of prior 10 sessions
RECLAIM_MAX_BARS = 3
VOL_MULT = 2.0                # sweep volume >= 2x median(20)
MIN_STRETCH = 0.10            # skip trades with less than 10% stretch
TIME_STOP_SESSIONS = 20
ATR_PERIOD = 14
NEWS_CRASH = 0.08             # news-proxy: prior 3 sessions, any close-to-close <= -8% -> skip
NEWS_WINDOW = 3


def wilder_atr(df):
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / ATR_PERIOD, min_periods=ATR_PERIOD, adjust=False).mean()


def run_symbol(bars, daily, stop_mult, symbol, tf, news_guard=False,
               skipped_counter=None):
    """Scan one symbol's bars for sweep/reclaim signals and simulate trades."""
    if len(bars) < 50 or len(daily) < 30:
        return []
    bars = bars.reset_index(drop=True)
    daily = daily.reset_index(drop=True)

    daily_close = daily["close"].to_numpy()
    n_daily = len(daily_close)
    rank_to_date = {r: daily["ts"].iloc[r] for r in range(n_daily)}
    daily_ret = np.full(n_daily, np.nan)
    if news_guard:
        daily_ret[1:] = np.diff(daily_close) / daily_close[:-1]

    bars["date"] = pd.to_datetime(bars["ts"].dt.date)
    date_to_rank = {d: r for r, d in enumerate(daily["ts"].dt.normalize())}
    ranks = bars["date"].map(date_to_rank).to_numpy()

    sma_prior = [None] * n_daily
    for r in range(SMA_DAYS, n_daily):
        sma_prior[r] = float(daily_close[r - SMA_DAYS:r].mean())

    n = len(bars)
    open_, high, low, close, volume = (bars[c].to_numpy() for c in
                                       ("open", "high", "low", "close", "volume"))
    atr = wilder_atr(bars).to_numpy()
    med20 = pd.Series(volume).rolling(20, min_periods=20).median().to_numpy()

    support = np.full(n, np.nan)
    for i in range(n):
        r = ranks[i]
        if r is None or r < SUPPORT_SESSIONS:
            continue
        lo = hi = None
        for j in range(i - 1, -1, -1):
            rj = ranks[j]
            if rj is None:
                continue
            if rj < r - SUPPORT_SESSIONS:
                break
            if hi is None:
                hi = j
            lo = j
        if lo is not None and hi is not None:
            support[i] = float(low[lo:hi + 1].min())

    trades = []
    i = 0
    skip_until = -1
    while i < n:
        if i <= skip_until:
            i += 1
            continue
        r = ranks[i]
        if (r is None or r < max(SMA_DAYS, SUPPORT_SESSIONS) or i < 20
                or np.isnan(atr[i]) or np.isnan(med20[i]) or np.isnan(support[i])):
            i += 1
            continue
        sup = support[i]
        if close[i] < sup and low[i] < sup and volume[i] >= VOL_MULT * med20[i]:
            found = False
            for k in range(1, RECLAIM_MAX_BARS + 1):
                j = i + k
                if j >= n:
                    break
                if close[j] > sup:
                    found = True
                    rj = ranks[j]
                    if rj is None or rj not in rank_to_date:
                        break
                    sma = sma_prior[rj]
                    if sma is None:
                        break
                    div = (close[j] - sma) / sma
                    if div <= -MIN_STRETCH:
                        if news_guard and _crash_near(daily_ret, ranks[j]):
                            if skipped_counter is not None:
                                skipped_counter[0] += 1
                            break
                        e = j + 1
                        if e >= n:
                            break
                        entry = float(open_[e])
                        sweep_low = float(low[i:j + 1].min())
                        sl = sweep_low - stop_mult * atr[j]
                        tp = float(sma)
                        if sl < entry and tp > entry:
                            trade, end_bar = _simulate(bars, ranks, rank_to_date,
                                                       daily, entry, sl, tp, atr[j],
                                                       e, symbol, tf, div, stop_mult,
                                                       sweep_low, sup, rank_to_date[rj])
                            trades.append(trade)
                            i = end_bar
                    break
            if not found:
                skip_until = i + RECLAIM_MAX_BARS
        i += 1
    return trades


def _simulate(bars, ranks, rank_to_date, daily, entry, sl, tp, atr_sig, e,
              symbol, tf, div, stop_mult, sweep_low, support, signal_date):
    open_, high, low, close = (bars[c].to_numpy() for c in
                               ("open", "high", "low", "close"))
    n = len(bars)
    r_entry = ranks[e]

    one_r = entry - sl
    half1_rank = None
    sl_current = sl
    trail_ref = None
    trail_stop = None
    exit1 = exit2 = None
    reason1 = reason2 = ""
    exit_date1 = exit_date2 = None

    for b in range(e, n):
        r = ranks[b]
        if r is None:
            continue
        if low[b] <= sl_current:
            if half1_rank is not None:
                exit2 = float(sl_current)
                exit_date2 = rank_to_date.get(r)
                reason2 = "TRAIL" if trail_stop is not None else "BREAKEVEN"
            else:
                exit1 = float(sl_current)
                exit_date1 = rank_to_date.get(r)
                reason1 = "STOP"
            break
        if half1_rank is None and close[b] >= tp:
            half1_rank = r
            exit1 = float(tp)
            exit_date1 = rank_to_date.get(r)
            reason1 = "TP1"
            sl_current = entry
            trail_ref = float(high[b])
            trail_stop = trail_ref - stop_mult * atr_sig
        elif half1_rank is not None:
            if float(high[b]) > trail_ref:
                trail_ref = float(high[b])
                trail_stop = trail_ref - stop_mult * atr_sig
            if low[b] <= trail_stop:
                exit2 = float(trail_stop)
                exit_date2 = rank_to_date.get(r)
                reason2 = "TRAIL"
                break
        if r - r_entry >= TIME_STOP_SESSIONS:
            if half1_rank is not None:
                exit2 = float(close[b])
                exit_date2 = rank_to_date.get(r)
                reason2 = "TIMEOUT"
            else:
                exit1 = float(close[b])
                exit_date1 = rank_to_date.get(r)
                reason1 = "TIMEOUT"
            break
    else:
        if half1_rank is not None:
            exit2 = float(close[-1])
            exit_date2 = rank_to_date.get(ranks[-1])
            reason2 = "OPEN_END"
        else:
            exit1 = float(close[-1])
            exit_date1 = rank_to_date.get(ranks[-1])
            reason1 = "OPEN_END"

    shares = NOTIONAL / entry
    exit_rank = ranks[b]
    if half1_rank is None:
        r_trade = (exit1 - entry) / one_r
        gross_rs = (exit1 - entry) * shares
        fees = (_leg_fees("BUY", entry * shares, r_entry, daily)
                + _leg_fees("SELL", exit1 * shares, exit_rank, daily))
    else:
        r1 = (tp - entry) / one_r
        r2 = (exit2 - entry) / one_r
        r_trade = 0.5 * r1 + 0.5 * r2
        gross_rs = (0.5 * shares * (tp - entry)
                    + 0.5 * shares * (exit2 - entry))
        fees = (_leg_fees("BUY", entry * shares, r_entry, daily)
                + _leg_fees("SELL", tp * 0.5 * shares, half1_rank, daily)
                + _leg_fees("SELL", exit2 * 0.5 * shares, exit_rank, daily))
    net_rs = gross_rs - fees
    r_net = net_rs / (one_r * shares)

    return ({
        "tf": tf, "symbol": symbol, "signal_date": signal_date,
        "entry_date": rank_to_date.get(r_entry), "entry": entry, "sl": sl,
        "tp": tp, "sweep_low": sweep_low, "support": support,
        "divergence_pct": div * 100, "stop_mult": stop_mult,
        "atr_sig": atr_sig,
        "exit1_date": exit_date1, "exit1_price": exit1, "reason1": reason1,
        "exit2_date": exit_date2, "exit2_price": exit2, "reason2": reason2,
        "hold_sessions": int(exit_rank) - int(r_entry),
        "r_gross": r_trade, "r_net": r_net, "fees_rs": fees,
        "gross_rs": gross_rs, "net_rs": net_rs,
    }, b)


def _crash_near(daily_ret, r):
    """True if any of the NEWS_WINDOW sessions before rank r crashed >= NEWS_CRASH."""
    if r is None:
        return False
    for k in range(1, NEWS_WINDOW + 1):
        i = r - k
        if i < 0:
            break
        v = daily_ret[i]
        if not np.isnan(v) and v <= -NEWS_CRASH:
            return True
    return False


def _leg_fees(side, value, rank, daily):
    if rank is None:
        return 0.0
    d = daily["ts"].iloc[rank].date()
    return delivery_equity_fees(side=side, trade_value=value, trade_date=d).total


def main(stop_mult, news_guard=False):
    con = duckdb.connect(str(CANDLES_DB), read_only=True)
    universe = pd.read_csv(UNIVERSE_CSV)["symbol"].tolist()
    all_trades = []
    skipped = [0]
    for tf, table in (("1h", "c1h"), ("4h", "c4h"), ("1d", "c1d")):
        for sym in universe:
            bars = con.execute(
                f"SELECT ts, open, high, low, close, volume FROM {table} "
                "WHERE symbol = ? ORDER BY ts", [sym]).fetchdf()
            if bars.empty:
                continue
            daily = con.execute(
                "SELECT ts, open, high, low, close, volume FROM c1d "
                "WHERE symbol = ? ORDER BY ts", [sym]).fetchdf()
            all_trades.extend(run_symbol(bars, daily, stop_mult, sym, tf,
                                         news_guard=news_guard,
                                         skipped_counter=skipped))
    df = pd.DataFrame(all_trades)
    tag = "guard" if news_guard else ""
    out = OUT_DIR / f"trades_{str(stop_mult).replace('.', '_')}{'_' if tag else ''}{tag}.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} trades (news-guard skipped {skipped[0]}) -> {out}")
    for tf in ("1h", "4h", "1d"):
        sub = df[df["tf"] == tf]
        wins = int((sub["r_net"] > 0).sum()) if len(sub) else 0
        avg = sub["r_net"].mean() if len(sub) else 0.0
        print(f"  {tf}: {len(sub)} trades, {wins} net winners, avg net R {avg:.2f}")
    con.close()


if __name__ == "__main__":
    guard = len(sys.argv) > 2 and sys.argv[2] == "--news-guard"
    main(float(sys.argv[1]), news_guard=guard)
