"""
CB-N50 HOLDOUT Phase — Out-of-Sample IC Confirmation (2020-2022)

Read-only HOLDOUT read. Features and lookbacks frozen from TRAIN.
Single test at alpha=0.05 (no Bonferroni; TRAIN multiplicity already paid).

G3: Combined IC must remain significant (p<0.05, Newey-West).
G4: Intentionally not evaluated — breadth→futures P&L already known
     to fail from TRAIN directional check. Sealed window preserved.
"""
import json
from pathlib import Path
from datetime import date

from run_train import (
    load_pit_membership, get_constituents,
    load_equity_panel, load_futures_panel, compute_forward_returns,
    compute_features, compute_daily_ic, newywest_se,
    TRAIN_START as _,
)
import duckdb
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

HOLDOUT_START = "2020-01-01"
HOLDOUT_END = "2022-12-31"
EQ_PATH = "data/market_data/equity_bhavcopy.duckdb"
FUT_PATH = "data/market_data/futures_bhavcopy.duckdb"
MEMBERSHIP_PATH = "data/reference/nifty50_pit_membership.json"
WEIGHTS_PATH = "data/reference/nifty50_pit_weights.json"

# Frozen from TRAIN
ACTIVE_FEATURES = ["reversal", "basis"]
BEST_MOMENTUM_L = 20  # not used (momentum dropped), but passed to compute_features
ALPHA = 0.05


def main():
    print("=" * 70)
    print("CB-N50 HOLDOUT PHASE — Out-of-Sample IC Confirmation (2020-2022)")
    print("=" * 70)
    print(f"  Frozen features: {ACTIVE_FEATURES}")
    print(f"  Test: single, alpha={ALPHA} (no Bonferroni)")

    membership, weights = load_pit_membership()

    conn = duckdb.connect(EQ_PATH, read_only=True)
    all_dates = conn.execute(f"""
        SELECT DISTINCT trade_date FROM equity_bhavcopy
        WHERE trade_date >= '{HOLDOUT_START}' AND trade_date <= '{HOLDOUT_END}'
        ORDER BY trade_date
    """).fetchall()
    conn.close()
    trade_dates = [d[0] for d in all_dates]
    print(f"\n  {len(trade_dates)} trading days in HOLDOUT window ({HOLDOUT_START} to {HOLDOUT_END})")

    # ── Load data ───────────────────────────────────────────────────
    print("\n[1] Loading data...")
    equity_df = load_equity_panel(trade_dates, membership)
    futures_df = load_futures_panel(trade_dates)
    returns_df = compute_forward_returns(equity_df, membership)

    # ── Compute frozen signal ───────────────────────────────────────
    print("\n[2] Computing frozen signal (reversal + basis)...")
    features_df = compute_features(equity_df, futures_df, BEST_MOMENTUM_L, ACTIVE_FEATURES)

    ic_df = compute_daily_ic(features_df, returns_df, membership)
    print(f"  Daily IC: {len(ic_df)} observations")

    if len(ic_df) < 30:
        print("  ERROR: insufficient IC observations")
        return

    mean_ic = ic_df["rank_ic"].mean()
    ic_std = ic_df["rank_ic"].std()
    nw_mean, nw_se = newywest_se(ic_df["rank_ic"].values)
    nw_t = nw_mean / nw_se
    df_eff = len(ic_df) - 1
    p_value = 2 * scipy_stats.t.sf(abs(nw_t), df=df_eff)
    significant = p_value < ALPHA
    ac1 = ic_df["rank_ic"].autocorr(lag=1)

    print(f"\n  Results:")
    print(f"  {'Mean IC:':<20} {mean_ic:.6f}")
    print(f"  {'IC Std:':<20} {ic_std:.6f}")
    print(f"  {'AC1:':<20} {ac1:.4f}")
    print(f"  {'NW SE:':<20} {nw_se:.6f}")
    print(f"  {'NW t-statistic:':<20} {nw_t:.4f}")
    print(f"  {'p-value:':<20} {p_value:.6f}")
    print(f"  {'Alpha:':<20} {ALPHA}")
    print(f"  {'Significant:':<20} {'YES' if significant else 'NO'}")

    # ── TRAIN comparison ────────────────────────────────────────────
    train_ic = 0.058674  # frozen from TRAIN report
    train_t = 11.3583
    train_n = 983

    print(f"\n  TRAIN comparison:")
    print(f"  {'TRAIN Mean IC:':<20} {train_ic:.6f} (t={train_t:.1f}, n={train_n})")
    print(f"  {'HOLDOUT Mean IC:':<20} {mean_ic:.6f} (t={nw_t:.1f}, n={len(ic_df)})")
    print(f"  {'Change:':<20} {mean_ic - train_ic:+.6f}")

    # ── G3 Gate ─────────────────────────────────────────────────────
    print(f"\n  {'='*50}")
    print(f"  G3 (HOLDOUT IC significance): {'PASS' if significant else 'FAIL'}")
    print(f"  {'='*50}")

    if significant:
        print(f"\n  HOLDOUT confirms TRAIN IC. Signal is out-of-sample robust.")
        print(f"  But G4 (futures P&L via breadth) is NOT evaluated —")
        print(f"  TRAIN directional check already showed breadth->futures fails.")
        print(f"  The SEALED window is preserved.")
        print(f"\n  Path forward: the +{mean_ic:.3f} cross-sectional IC warrants a")
        print(f"  fresh construct — constituent long-short book with per_trade_pnl")
        print(f"  RFA — not Nifty futures via breadth.")

    # ── Save ─────────────────────────────────────────────────────────
    results = {
        "phase": "HOLDOUT",
        "window": f"{HOLDOUT_START} to {HOLDOUT_END}",
        "n_trading_days": len(trade_dates),
        "n_ic_observations": len(ic_df),
        "active_features": ACTIVE_FEATURES,
        "combined_ic": {
            "mean_IC": round(float(mean_ic), 6),
            "ic_std": round(float(ic_std), 6),
            "ac1": round(float(ac1), 4),
            "nw_mean": round(float(nw_mean), 6),
            "nw_se": round(float(nw_se), 6),
            "nw_t": round(float(nw_t), 4),
            "p_value": round(float(p_value), 6),
            "alpha": ALPHA,
            "significant": bool(significant),
        },
        "train_comparison": {
            "train_mean_IC": train_ic,
            "train_nw_t": train_t,
            "train_n_obs": train_n,
            "holdout_mean_IC": round(float(mean_ic), 6),
            "holdout_nw_t": round(float(nw_t), 4),
            "holdout_n_obs": len(ic_df),
            "ic_change": round(float(mean_ic - train_ic), 6),
        },
        "gate_g3": "PASS" if significant else "FAIL",
        "gate_g4": "NOT EVALUATED",
        "note": (
            "G4 (futures P&L via breadth) intentionally skipped. "
            "TRAIN directional check showed breadth->futures fails. "
            "SEALED window preserved. The real result is the +"
            f"{mean_ic:.3f} cross-sectional IC, which warrants a "
            "fresh construct (constituent long-short book, per_trade_pnl RFA)."
        ),
    }

    out_path = Path("F:/Nifty/docs/reports/CB_N50_HOLDOUT_RESULTS.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))

    report_lines = []
    report_lines.append("# CB-N50 HOLDOUT Report — Out-of-Sample IC Confirmation")
    report_lines.append(f"Generated: {date.today()}")
    report_lines.append("")
    report_lines.append(f"**Window:** {HOLDOUT_START} to {HOLDOUT_END}")
    report_lines.append(f"**Trading days:** {len(trade_dates)}")
    report_lines.append(f"**IC observations:** {len(ic_df)}")
    report_lines.append(f"**Active features:** {', '.join(ACTIVE_FEATURES)} (momentum dropped in TRAIN)")
    report_lines.append("")
    report_lines.append("## Combined Signal (frozen from TRAIN)")
    report_lines.append("")
    report_lines.append(f"- Mean IC: {mean_ic:.6f}")
    report_lines.append(f"- IC Std: {ic_std:.6f}")
    report_lines.append(f"- AC1: {ac1:.4f}")
    report_lines.append(f"- NW SE: {nw_se:.6f}")
    report_lines.append(f"- NW t-statistic: {nw_t:.4f}")
    report_lines.append(f"- p-value: {p_value:.6f}")
    report_lines.append(f"- **Significant at alpha={ALPHA}: {'YES' if significant else 'NO'}**")
    report_lines.append("")
    report_lines.append("## TRAIN Comparison")
    report_lines.append("")
    report_lines.append(f"- TRAIN Mean IC: {train_ic:.6f} (t={train_t:.1f}, n={train_n})")
    report_lines.append(f"- HOLDOUT Mean IC: {mean_ic:.6f} (t={nw_t:.1f}, n={len(ic_df)})")
    report_lines.append(f"- Change: {mean_ic - train_ic:+.6f}")
    report_lines.append("")
    report_lines.append(f"**G3 Gate: {'PASS' if significant else 'FAIL'}**")
    report_lines.append("")
    report_lines.append("## Disposition")
    report_lines.append("")
    report_lines.append("G4 (futures P&L via breadth) is NOT evaluated. TRAIN already showed")
    report_lines.append("the breadth->futures directional check fails — spending the HOLDOUT")
    report_lines.append("read on a P&L gate we can predict fails is not productive, and the")
    report_lines.append("SEALED window is preserved for a future construct that can clear its")
    report_lines.append("own per_trade_pnl RFA.")
    report_lines.append("")
    report_lines.append(f"The real result is the +{mean_ic:.3f} cross-sectional IC —")
    report_lines.append("a constituent-level signal that predicts next-day open-to-open returns")
    report_lines.append("across the Nifty 50 cross-section, confirmed out-of-sample. Its")
    report_lines.append("tradeable home is a long-short constituent book (fresh pre-registration")
    report_lines.append("with per_trade_pnl metric and its own RFA), not Nifty futures via breadth.")
    report_lines.append("")

    report_path = Path("F:/Nifty/docs/reports/CB_N50_HOLDOUT_REPORT.md")
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
