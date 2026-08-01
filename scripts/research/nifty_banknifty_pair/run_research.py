"""
Deep Research: Nifty-BankNifty Index Pair Trading

Run comprehensive analysis on index pair trading opportunities using:
- 1d EOD data (2016-2026): cointegration, ratio mean reversion, strategy backtests
- 1m intraday data (2023-2026): intraday spread behavior, high-frequency z-score

Output: docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.research.nifty_banknifty_pair.data_loader import load_1d_data, load_1m_data
from scripts.research.nifty_banknifty_pair.analysis import run_full_analysis, generate_report


def main():
    print("=" * 70)
    print("NIFTY-BANKNIFTY INDEX PAIR TRADING — DEEP RESEARCH")
    print("=" * 70)

    # ── Load EOD data (2016 onwards) ──────────────────────────────────
    print("\n[1/4] Loading 1d EOD data (2016 onwards)...")
    df_1d = load_1d_data(start="2016-01-01")
    print(f"  Loaded {len(df_1d):,} daily observations")
    print(f"  Date range: {df_1d.index[0]} to {df_1d.index[-1]}")
    print(f"  Nifty range: {df_1d['nifty_close'].min():.0f} – {df_1d['nifty_close'].max():.0f}")
    print(f"  BankNifty range: {df_1d['banknifty_close'].min():.0f} – {df_1d['banknifty_close'].max():.0f}")

    # ── Load 1m data ──────────────────────────────────────────────────
    print("\n[2/4] Loading 1m intraday data (2023 onwards)...")
    df_1m = load_1m_data()
    print(f"  Loaded {len(df_1m):,} 1-minute observations")
    if len(df_1m) > 0:
        df_1m["ratio"] = df_1m["banknifty_close"] / df_1m["nifty_close"]
        print(f"  Date range: {df_1m.index[0]} to {df_1m.index[-1]}")

    # ── Run analysis ──────────────────────────────────────────────────
    print("\n[3/4] Running full analysis suite...")
    results = run_full_analysis(df_1d, df_1m)

    print(f"\n  Correlation: {results['correlation']['return_correlation']}")
    print(f"  Cointegrated: {results['cointegration'].get('cointegrated', 'N/A')}")
    print(f"  Half-life: {results['half_life'].get('half_life_days', 'N/A')} days")

    eod_strats = [s for s in results.get("eod_strategies", []) if "error" not in s]
    if eod_strats:
        best = sorted(eod_strats, key=lambda x: x["net_pnl_bps"], reverse=True)[0]
        print(f"  Best EOD strategy: net={best['net_pnl_bps']} bps, {best['n_trades']} trades, win_rate={best['win_rate']}%")

    intra_strats = [s for s in results.get("intraday_strategies", []) if "error" not in s]
    if intra_strats:
        best_1m = sorted(intra_strats, key=lambda x: x["net_pnl_bps"], reverse=True)[0]
        print(f"  Best intraday strategy: net={best_1m['net_pnl_bps']} bps, {best_1m['n_trades']} trades")

    bs = results.get("bootstrap", {})
    if bs:
        print(f"  Bootstrap p-value: {bs.get('p_value')} (significant: {bs.get('significant_at_5pct')})")

    # ── Generate report ───────────────────────────────────────────────
    print("\n[4/4] Generating research report...")
    output_path = Path("F:/Nifty/docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, output_path)
    print(f"  Report written to: {output_path}")

    # ── JSON snapshot ─────────────────────────────────────────────────
    snapshot_path = Path("F:/Nifty/docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.json")
    serializable = {}
    for k, v in results.items():
        if k in ("eod_strategies", "intraday_strategies"):
            serializable[k] = [{kk: vv for kk, vv in item.items() if kk != "trades"} for item in v if "error" not in v]
        else:
            serializable[k] = v
    snapshot_path.write_text(json.dumps(serializable, indent=2, default=str))
    print(f"  JSON snapshot: {snapshot_path}")

    print("\n" + "=" * 70)
    print("RESEARCH COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
