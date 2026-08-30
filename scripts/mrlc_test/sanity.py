"""MRLC-test sanity checks: synthetic pattern, negative case, no-lookahead, invariants."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.mrlc_test.engine import run_symbol, wilder_atr  # noqa: E402

OUT_DIR = ROOT / "data" / "mrlc_test"


def make_bars(days_close, start="2023-01-02"):
    """Build 1h bars (6/day, 09:15..14:15) from a daily-close series."""
    rows = []
    d0 = pd.Timestamp(start)
    for day, c in enumerate(days_close):
        date = d0 + pd.Timedelta(days=day)
        for h in range(6):
            rows.append((date + pd.Timedelta(hours=9, minutes=15) + pd.Timedelta(hours=h),
                         1000))
    return rows


def build_frames(days_close, day71_bars):
    bars_rows = []
    d0 = pd.Timestamp("2023-01-02")
    for day, c in enumerate(days_close):
        date = d0 + pd.Timedelta(days=day)
        for h in range(6):
            ts = date + pd.Timedelta(hours=9, minutes=15) + pd.Timedelta(hours=h)
            bars_rows.append({"ts": ts, "open": c, "high": c + 0.5, "low": c - 0.5,
                              "close": c, "volume": 1000})
    for br in day71_bars:
        bars_rows.append(br)
    bars = pd.DataFrame(bars_rows).sort_values("ts").reset_index(drop=True)
    daily = bars.groupby(bars["ts"].dt.date).agg(
        ts=("ts", "min"), open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), volume=("volume", "sum"),
    ).reset_index(drop=True)
    return bars, daily


def days_close_declining():
    return [100.0 - 0.5 * d for d in range(61)] + [70.0 - 0.8 * d for d in range(1, 11)]


def main():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond

    print("== 1. Positive case: sweep + reclaim fires exactly one trade ==")
    dc = days_close_declining()
    day71 = [
        {"ts": pd.Timestamp("2023-03-14 09:15"), "open": 61.5, "high": 61.8,
         "low": 59.5, "close": 60.0, "volume": 3000},
        {"ts": pd.Timestamp("2023-03-14 10:15"), "open": 60.1, "high": 63.0,
         "low": 60.0, "close": 62.5, "volume": 800},
        {"ts": pd.Timestamp("2023-03-14 11:15"), "open": 62.8, "high": 63.2,
         "low": 62.6, "close": 63.0, "volume": 900},
    ]
    for h in range(3):
        day71.append({"ts": pd.Timestamp("2023-03-14 12:15") + pd.Timedelta(hours=h),
                      "open": 63.0, "high": 63.3, "low": 62.8, "close": 63.1,
                      "volume": 900})
    bars, daily = build_frames(dc, day71)
    trades = run_symbol(bars, daily, 2.0, "TEST", "1h")
    check("exactly 1 trade", len(trades) == 1)
    if trades:
        t = trades[0]
        atr = wilder_atr(bars)
        reclaim_idx = 71 * 6 + 1
        check("entry = open of bar after reclaim (62.8)",
              abs(t["entry"] - 62.8) < 1e-9)
        check("sl = sweep_low - 2*ATR at signal bar",
              abs(t["sl"] - (59.5 - 2.0 * atr.iloc[reclaim_idx])) < 1e-9)
        check("tp = prior-day 25-SMA (no lookahead)",
              abs(t["tp"] - daily["close"].iloc[46:71].mean()) < 1e-9)
        check("divergence <= -10%", t["divergence_pct"] <= -10.0)
        check("sweep_low == 59.5", abs(t["sweep_low"] - 59.5) < 1e-9)
        check("support == 61.5", abs(t["support"] - 61.5) < 1e-9)

    print("== 2. Negative case: no reclaim -> no trade ==")
    day71n = [
        {"ts": pd.Timestamp("2023-03-14 09:15"), "open": 70.0, "high": 70.3,
         "low": 68.0, "close": 68.5, "volume": 3000},
        {"ts": pd.Timestamp("2023-03-14 10:15"), "open": 68.6, "high": 69.0,
         "low": 67.8, "close": 68.2, "volume": 900},
        {"ts": pd.Timestamp("2023-03-14 11:15"), "open": 68.0, "high": 68.5,
         "low": 67.5, "close": 67.8, "volume": 950},
    ]
    for h in range(3):
        day71n.append({"ts": pd.Timestamp("2023-03-14 12:15") + pd.Timedelta(hours=h),
                       "open": 67.8, "high": 68.0, "low": 67.0, "close": 67.2,
                       "volume": 900})
    bars_n, daily_n = build_frames(dc, day71n)
    check("0 trades", len(run_symbol(bars_n, daily_n, 2.0, "TEST", "1h")) == 0)

    print("== 3. No-lookahead: TP excludes signal day's own close ==")
    if trades:
        t = trades[0]
        leaked = daily["close"].iloc[45:71].mean()
        check("tp != SMA including signal day", abs(t["tp"] - leaked) > 1e-6)

    print("== 4. Invariants over all real trades ==")
    bad = 0
    n = 0
    for f in (OUT_DIR / "trades_2_0.csv", OUT_DIR / "trades_1_5.csv"):
        df = pd.read_csv(f)
        n += len(df)
        bad += int((df["sl"] >= df["entry"]).sum())
        bad += int((df["tp"] <= df["entry"]).sum())
        bad += int((df["sweep_low"] > df["support"] + 1e-9).sum())
        bad += int((df["hold_sessions"] < 0).sum())
        bad += int((df["entry"] <= 0).sum())
        bad += int((df["r_gross"].isna()).sum() | (df["r_net"].isna()).sum())
    check(f"invariants hold across {n} trades (0 violations)", bad == 0)

    print()
    print("ALL PASS" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
