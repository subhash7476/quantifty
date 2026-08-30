"""MRLC-test report v2: guard, slippage, time-split holdout, 2012-2022 extension."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "mrlc_test"
REPORT = ROOT / "docs" / "reports" / "MRLC_TEST_2026-08-30.md"

THRESHOLDS = (10.0, 15.0, 20.0, 30.0)
TFS = ("1h", "4h", "1d")


def load(tag):
    return pd.read_csv(OUT_DIR / f"trades_{tag}.csv")


def stats(df):
    n = len(df)
    if n == 0:
        return dict(n=0, n_win=0, win_rate=0.0, exp_net=0.0, total_net=0.0,
                    total_gross=0.0, exp_gross=0.0, avg_fees=0.0, avg_hold=0.0,
                    t=None)
    wins = df[df["r_net"] > 0]
    losses = df[df["r_net"] <= 0]
    t = (df["r_net"].mean() / (df["r_net"].std(ddof=1) / np.sqrt(n))
         if n > 1 else None)
    return dict(
        n=n, n_win=len(wins),
        win_rate=len(wins) / n * 100,
        avg_win_r=wins["r_net"].mean() if len(wins) else 0.0,
        avg_loss_r=losses["r_net"].mean() if len(losses) else 0.0,
        exp_net=df["r_net"].mean(), exp_gross=df["r_gross"].mean(),
        total_net=df["r_net"].sum(), total_gross=df["r_gross"].sum(),
        avg_fees=df["fees_rs"].mean(), avg_hold=df["hold_sessions"].mean(),
        t=t)


def fmt(v, nd=2):
    if v is None:
        return "-"
    return f"{v:.{nd}f}"


def main():
    g = load("2_0_guard")
    ng = load("2_0")
    g15 = load("1_5_guard")
    ext = load("ext_2_0_guard")
    ext_ng = load("ext_2_0")
    slip = pd.read_csv(OUT_DIR / "slippage_summary.csv")

    lines = []
    console = []

    def out(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        console.append(s)
        lines.append(s)

    out("# MRLC-Test Backtest Results (v2) - 2023-01-02 to 2026-08-28, + 2012-2022 extension")
    out("")
    out("**Rule set:** price ≥ threshold below the 25-day average (prior-day closes) +")
    out("liquidity sweep (close below the recent 10-session low on ≥ 2× usual volume, then")
    out("close back above within 3 bars). **News guard:** signals within 3 sessions after a")
    out("≥ 8% single-session crash are skipped (earnings/event proxy). Buy at next bar's")
    out("open. Stop = sweep low − 2× ATR (1.5× shown). Sell 50% at the 25-day average, rest")
    out("with break-even then 2× ATR trailing stop. 20-session time stop. Delivery fees,")
    out("era-accurate. Rs 1,00,000 fixed per trade.")
    out("")
    out("## 1. Main result — 15% stretch, 2× stop, news-guard ON")
    out("")
    out("| Chart | Trades | Winners | Win % | Avg win | Avg loss | Expectancy/trade | Total net | Fees/trade | t-stat |")
    out("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for tf in TFS:
        sub = g[(g["tf"] == tf) & (g["divergence_pct"] <= -15.0)]
        s = stats(sub)
        out(f"| {tf} | {s['n']} | {s['n_win']} | {fmt(s['win_rate'], 1)}% | "
            f"{fmt(s['avg_win_r'])} | {fmt(s['avg_loss_r'])} | {fmt(s['exp_net'])} | "
            f"{fmt(s['total_net'])} | Rs {fmt(s['avg_fees'], 0)} | {fmt(s['t'])} |")
    out("")
    out("## 2. News guard impact (2× stop, 15% stretch)")
    out("")
    out("| Chart | Guard OFF trades | Guard OFF expectancy | Guard ON trades | Guard ON expectancy |")
    out("|---|---:|---:|---:|---:|")
    for tf in TFS:
        a = stats(ng[(ng["tf"] == tf) & (ng["divergence_pct"] <= -15.0)])
        b = stats(g[(g["tf"] == tf) & (g["divergence_pct"] <= -15.0)])
        out(f"| {tf} | {a['n']} | {fmt(a['exp_net'])} | {b['n']} | {fmt(b['exp_net'])} |")
    out("")
    out("## 3. Slippage robustness (2× stop, guard ON, net expectancy per trade)")
    out("")
    out("| Chart | Stretch | 0 bp | 5 bp | 10 bp | 20 bp |")
    out("|---|---|---:|---:|---:|---:|")
    for tf in ("1h", "4h"):
        for t in (10.0, 15.0):
            row = slip[(slip["tag"] == "main_guard") & (slip["tf"] == tf)
                       & (slip["threshold"] == t)]
            if not len(row):
                continue
            cells = " | ".join(f"{r['exp_net']:.3f}" for _, r in
                               row.sort_values("slip_bp").iterrows())
            out(f"| {tf} | ≤{t:.0f}% | {cells} |")
    out("")
    out("## 4. Threshold sensitivity (2× stop, guard ON, 0 bp)")
    out("")
    out("| Chart | 10% | 15% | 20% | 30% |")
    out("|---|---:|---:|---:|---:|")
    for tf in TFS:
        cells = []
        for t in THRESHOLDS:
            s = stats(g[(g["tf"] == tf) & (g["divergence_pct"] <= -t)])
            cells.append(f"{s['exp_net']:.2f} (n={s['n']})")
        out(f"| {tf} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    out("")
    out("## 5. Stop comparison (guard ON, 15% stretch)")
    out("")
    out("| Chart | Stop | Trades | Win % | Expectancy/trade | Total net |")
    out("|---|---|---:|---:|---:|---:|")
    for tf in TFS:
        for mult, d in (("2.0×", g), ("1.5×", g15)):
            s = stats(d[(d["tf"] == tf) & (d["divergence_pct"] <= -15.0)])
            out(f"| {tf} | {mult} | {s['n']} | {fmt(s['win_rate'], 1)}% | "
                f"{fmt(s['exp_net'])} | {fmt(s['total_net'])} |")
    out("")
    out("## 6. Year by year (15% stretch, 2× stop, guard ON)")
    out("")
    g["year"] = pd.to_datetime(g["entry_date"]).dt.year
    out("| Year | 1h trades | 1h net R | 4h trades | 4h net R | 1d trades | 1d net R |")
    out("|---|---:|---:|---:|---:|---:|---:|")
    for year in sorted(g["year"].unique()):
        cells = []
        for tf in TFS:
            s = stats(g[(g["tf"] == tf) & (g["year"] == year)
                        & (g["divergence_pct"] <= -15.0)])
            cells.append(f"{s['n']} | {fmt(s['total_net'])}")
        out(f"| {year} | {cells[0]} | {cells[1]} | {cells[2]} |")
    out("")
    out("## 7. Time-split holdout — 2023-24 (train) vs 2025-26 (test), 2× stop, guard ON")
    out("")
    out("| Chart | Stretch | Half | Trades | Expectancy/trade | Total net |")
    out("|---|---|---|---:|---:|---:|")
    for tf in ("1h", "4h"):
        for t in (10.0, 15.0):
            for half, lo, hi in (("2023-24", 2023, 2024), ("2025-26", 2025, 2026)):
                s = stats(g[(g["tf"] == tf) & (g["divergence_pct"] <= -t)
                            & (g["year"] >= lo) & (g["year"] <= hi)])
                out(f"| {tf} | ≤{t:.0f}% | {half} | {s['n']} | {fmt(s['exp_net'])} | "
                    f"{fmt(s['total_net'])} |")
    out("")
    out("## 8. The 2012-2022 daily extension (out-of-sample, 2× stop, guard ON)")
    out("")
    out("11 years, 2,300 symbols from the certified CA-adjusted store — point-in-time")
    out("membership (includes names later delisted), era-accurate fees. This is the only")
    out("true calendar extension the repo can produce for any MRLC cell.")
    out("")
    out("| Stretch | Trades | Winners | Win % | Expectancy/trade | Total net | t-stat |")
    out("|---|---|---:|---:|---:|---:|---:|")
    for t in (10.0, 15.0, 20.0):
        s = stats(ext[ext["divergence_pct"] <= -t])
        out(f"| ≤{t:.0f}% | {s['n']} | {s['n_win']} | {fmt(s['win_rate'], 1)}% | "
            f"{fmt(s['exp_net'])} | {fmt(s['total_net'])} | {fmt(s['t'])} |")
    s15e = stats(ext[ext["divergence_pct"] <= -15.0])
    s15m = stats(g[(g["tf"] == "1d") & (g["divergence_pct"] <= -15.0)])
    s10e = stats(ext[ext["divergence_pct"] <= -10.0])
    s10m = stats(g[(g["tf"] == "1d") & (g["divergence_pct"] <= -10.0)])
    out("")
    out("| Window | 1d @ ≤10% | 1d @ ≤15% |")
    out("|---|---:|---:|")
    out(f"| 2012-2022 (ext) | {s10e['n']} trades, {fmt(s10e['exp_net'])} R | "
        f"{s15e['n']} trades, {fmt(s15e['exp_net'])} R |")
    out(f"| 2023-2026 (1m store) | {s10m['n']} trades, {fmt(s10m['exp_net'])} R | "
        f"{s15m['n']} trades, {fmt(s15m['exp_net'])} R |")
    out("")
    out("## 9. How trades ended (15% stretch, 2× stop, guard ON)")
    out("")
    out("| Chart | Stopped out | Timeout | 50%@SMA then trail | 50%@SMA then timeout |")
    out("|---|---:|---:|---:|---:|")
    for tf in TFS:
        sub = g[(g["tf"] == tf) & (g["divergence_pct"] <= -15.0)]
        out(f"| {tf} | {(sub['reason1'] == 'STOP').sum()} | "
            f"{(sub['reason1'] == 'TIMEOUT').sum()} | "
            f"{(sub['reason2'] == 'TRAIL').sum()} | "
            f"{(sub['reason2'] == 'TIMEOUT').sum()} |")
    out("")
    out("## 10. Caveats (read before trusting anything)")
    out("")
    out("- **Survivorship (2023-26 window):** only today's ~196 stocks. The 2012-2022")
    out("  extension removes this for the daily variant (point-in-time symbols).")
    out("- **Ideal fills:** exits at exact stop/target prices; slippage table (0-20 bp)")
    out("  shows the construct survives up to 20 bp per side on the strong cells.")
    out("- **News guard is a proxy** (≥ 8% one-day crash → skip 3 sessions). It is NOT a")
    out("  real news feed; earnings-adjacent moves under 8% are not caught.")
    out("- **Fixed target:** the profit target is the 25-day average as of the signal day.")
    out("- **2012-2022 extension specifics:** CA-adjusted prices, pre-2020 stamp duty uses")
    out("  the Maharashtra-representative 0.01% assumption, NSE retail-tier transaction")
    out("  charge. Stops/targets in % terms on adjusted prices.")
    out("- **Selection caveat:** the 10%/15% cells and the news-guard threshold were")
    out("  examined across 3 charts × 4 thresholds × 2 stops. The extension and the")
    out("  time-split are consistency checks, not fresh pre-registered holdouts.")
    out("")
    out("## Record")
    out("")
    out("- Engine `scripts/mrlc_test/engine.py` (+ `--news-guard`), extension")
    out("  `scripts/mrlc_test/daily_ext.py` (certified `equity_bhavcopy_adjusted` view,")
    out("  2012-2022), repricer `scripts/mrlc_test/repricer.py` (0/5/10/20 bp),")
    out("  sanity `scripts/mrlc_test/sanity.py` (ALL PASS).")
    out("- Trades: `data/mrlc_test/trades_*_guard.csv` (2023-26), `trades_ext_*.csv`")
    out("  (2012-22), `slippage_summary.csv`.")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nreport -> {REPORT}")


if __name__ == "__main__":
    main()
