"""
CB-N50 TRAIN Phase — Signal Construction & Validation (2016-2019)

Read-only TRAIN read on the Nifty 50 constituent cross-section.
Consumes: equity bhavcopy, futures bhavcopy, PIT MCWB membership.
Does NOT touch: HOLDOUT (2020-2022) or SEALED (2023-2026).

Per the frozen pre-registration:
- Features: relative momentum (L∈{5,10,20}), futures basis, short-term reversal
- Target: open-to-open return (t+1 open → t+2 open)
- Metric: daily cross-sectional Spearman rank IC
- Observation unit: one IC value per trading day (NOT 50×N stock-days)
- Inference: Newey-West SE, Bonferroni-adjusted for m=9 multiplicity
"""
import json
import sys
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict
import warnings

import duckdb
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore")


# Window constants
TRAIN_START = "2016-01-01"
TRAIN_END = "2019-12-31"
LOOKBACKS = [5, 10, 20]
EQ_PATH = "data/market_data/equity_bhavcopy.duckdb"
FUT_PATH = "data/market_data/futures_bhavcopy.duckdb"
MEMBERSHIP_PATH = "data/reference/nifty50_pit_membership.json"
WEIGHTS_PATH = "data/reference/nifty50_pit_weights.json"
ALPHA = 0.05
M_MULTIPLICITY = 9  # 3 features × 3 lookbacks


def load_pit_membership():
    with open(MEMBERSHIP_PATH) as f:
        membership = json.load(f)
    with open(WEIGHTS_PATH) as f:
        weights = json.load(f)
    return membership, weights


def get_membership_month(trade_date):
    if isinstance(trade_date, str):
        parts = trade_date.split("-")
        y, m = int(parts[0]), int(parts[1])
    else:
        y, m = trade_date.year, trade_date.month
    # One-month lag
    if m == 1:
        return f"{y-1:04d}-12-01"
    return f"{y:04d}-{m-1:02d}-01"


def get_constituents(trade_date, membership):
    key = get_membership_month(trade_date)
    if key in membership:
        return set(membership[key])
    months = sorted(membership.keys())
    if key < months[0]:
        return set(membership[months[0]])
    for m in reversed(months):
        if m < key:
            return set(membership[m])
    return set()


def load_equity_panel(dates, membership):
    """Load OHLC data for Nifty 50 constituents over the date range."""
    conn = duckdb.connect(EQ_PATH, read_only=True)

    # Get all symbols that were ever in Nifty 50 during the period
    all_symbols = set()
    for d in dates:
        constituents = get_constituents(d, membership)
        all_symbols |= constituents

    print(f"  Loading equity data for {len(all_symbols)} symbols over {len(dates)} dates...")

    # Batch-load into a pivot DataFrame
    syms_str = "','".join(all_symbols)
    date_strs = "','".join(d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in dates)

    df = conn.execute(f"""
        SELECT trade_date, symbol, open, high, low, close, volume
        FROM equity_bhavcopy
        WHERE symbol IN ('{syms_str}')
          AND trade_date IN ('{date_strs}')
        ORDER BY trade_date, symbol
    """).fetchdf()

    conn.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_futures_panel(dates):
    """Load stock futures close prices for basis computation."""
    conn = duckdb.connect(FUT_PATH, read_only=True)

    date_strs = "','".join(d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in dates)

    df = conn.execute(f"""
        SELECT trade_date, underlying, close, expiry_dt
        FROM futures_bhavcopy
        WHERE inst_type = 'FUTSTK'
          AND trade_date IN ('{date_strs}')
        ORDER BY trade_date, underlying, expiry_dt
    """).fetchdf()

    conn.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    # Keep near-month only
    df = df.sort_values(["trade_date", "underlying", "expiry_dt"])
    df = df.groupby(["trade_date", "underlying"]).first().reset_index()
    return df


def load_nifty_index(dates):
    """Load Nifty 50 index data (for Nifty futures execution reference)."""
    conn = duckdb.connect(EQ_PATH, read_only=True)
    date_strs = "','".join(d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in dates)

    df = conn.execute(f"""
        SELECT trade_date, symbol, open, close
        FROM equity_bhavcopy
        WHERE symbol = 'NIFTY 50'
          AND trade_date IN ('{date_strs}')
        ORDER BY trade_date
    """).fetchdf()

    conn.close()
    # Also try nifty 50 from the index store if not in bhavcopy
    if len(df) == 0:
        # Nifty 50 might not be in equity_bhavcopy; load from 1d candles instead
        index_dates = sorted(set(d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d) for d in dates))
        rows = []
        for d in index_dates:
            try:
                c = duckdb.connect(f"data/market_data/nse/candles/1d/{d}.duckdb", read_only=True)
                r = c.execute("SELECT timestamp, close FROM candles WHERE symbol='NSE_INDEX|Nifty 50' LIMIT 1").fetchone()
                if r:
                    rows.append({"trade_date": d, "close": r[1]})
                c.close()
            except:
                pass
        if rows:
            df = pd.DataFrame(rows)
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df["open"] = np.nan

    return df


def compute_features(equity_df, futures_df, lookback, active_features=None):
    """
    Compute the three features for each constituent on each date.

    active_features: list of feature names to include. None = all three.
    Returns DataFrame with columns: trade_date, symbol, feat_momentum, feat_basis, feat_reversal, combined_score
    """
    if active_features is None:
        active_features = ["momentum", "reversal", "basis"]

    df = equity_df.copy()
    df = df.sort_values(["symbol", "trade_date"])

    if "momentum" in active_features:
        df["close_lag"] = df.groupby("symbol")["close"].shift(lookback)
        df["feat_momentum_raw"] = df["close"] / df["close_lag"] - 1

    if "reversal" in active_features:
        df["close_lag1"] = df.groupby("symbol")["close"].shift(1)
        df["feat_reversal_raw"] = -(df["close"] / df["close_lag1"] - 1)

    if "basis" in active_features and futures_df is not None and len(futures_df) > 0:
        basis = futures_df[["trade_date", "underlying", "close"]].rename(
            columns={"underlying": "symbol", "close": "futures_close"}
        )
        df = df.merge(basis, on=["trade_date", "symbol"], how="left")
        df["feat_basis_raw"] = (df["futures_close"] / df["close"] - 1) * (365 / 30)

    # Cross-sectional normalisation for active features only
    feature_map = {
        "momentum": "feat_momentum_raw",
        "reversal": "feat_reversal_raw",
        "basis": "feat_basis_raw",
    }

    scores = []
    for feat_name in active_features:
        raw_col = feature_map[feat_name]
        if raw_col not in df.columns:
            continue
        day_mean = df.groupby("trade_date")[raw_col].transform("mean")
        day_std = df.groupby("trade_date")[raw_col].transform("std").replace(0, np.nan)
        z = (df[raw_col] - day_mean) / day_std
        z = z.clip(-3, 3)
        norm_col = raw_col.replace("_raw", "")
        df[norm_col] = z
        scores.append(norm_col)

    # Equal-weighted combination of active features
    df["combined_score"] = df[scores].mean(axis=1, skipna=True)

    return df


def compute_forward_returns(equity_df, membership):
    """Compute open-to-open forward returns: open(t+1) -> open(t+2)."""
    df = equity_df[["trade_date", "symbol", "open"]].copy()
    df = df.sort_values(["symbol", "trade_date"])

    # Forward open at t+1 and t+2
    df["open_t1"] = df.groupby("symbol")["open"].shift(-1)
    df["open_t2"] = df.groupby("symbol")["open"].shift(-2)
    df["forward_return"] = df["open_t2"] / df["open_t1"] - 1

    return df.dropna(subset=["forward_return"])


def compute_daily_ic(features_df, returns_df, membership):
    """
    Compute daily cross-sectional Spearman rank IC.
    One IC value per trading day.

    Returns DataFrame with columns: trade_date, n_stocks, rank_ic
    """
    df = features_df[["trade_date", "symbol", "combined_score"]].merge(
        returns_df[["trade_date", "symbol", "forward_return"]],
        on=["trade_date", "symbol"], how="inner"
    )

    ics = []
    for td, group in df.groupby("trade_date"):
        valid = group.dropna(subset=["combined_score", "forward_return"])

        # Check N >= 30
        if len(valid) < 30:
            continue

        # PIT membership: only Nifty 50 members on this date
        constituents = get_constituents(td, membership)
        valid = valid[valid["symbol"].isin(constituents)]

        if len(valid) < 30:
            continue

        # Spearman rank IC
        ic, _ = scipy_stats.spearmanr(valid["combined_score"], valid["forward_return"])

        ics.append({
            "trade_date": td,
            "n_stocks": len(valid),
            "rank_ic": ic,
        })

    return pd.DataFrame(ics)


def newywest_se(series, max_lag=None):
    """Newey-West standard error of the mean."""
    n = len(series)
    if n < 2:
        return np.nan, np.nan
    if max_lag is None:
        max_lag = int(4 * (n / 100) ** (2 / 9))  # Newey-West automatic bandwidth
        max_lag = min(max_lag, n // 4)

    mean = np.mean(series)
    demeaned = series - mean

    # Compute autocovariances
    var = np.sum(demeaned ** 2) / n
    for lag in range(1, max_lag + 1):
        weight = 1 - lag / (max_lag + 1)
        autocov = np.sum(demeaned[lag:] * demeaned[:-lag]) / n
        var += 2 * weight * autocov

    se = np.sqrt(var / n)
    return mean, se


def feature_lookback_selection(equity_df, futures_df, returns_df, membership):
    """
    Grid search over lookback periods for the momentum feature.
    Basis and reversal have fixed lookbacks.

    Returns best lookback per feature and their individual ICs.
    """
    print("\n  Feature lookback selection (Bonferroni m=9):")
    print(f"  {'Feature':<20} {'L':>4} {'Mean IC':>10} {'NW t':>8} {'p_raw':>10} {'Significant?'}")
    print(f"  {'-'*60}")

    results = []
    bonferroni_alpha = ALPHA / M_MULTIPLICITY

    for feat_name, feat_col, lookbacks in [
        ("momentum", "feat_momentum_raw", LOOKBACKS),
        ("reversal", "feat_reversal_raw", [1]),  # fixed lookback=1
        ("basis", "feat_basis_raw", [1]),         # fixed lookback=1
    ]:
        for L in lookbacks:
            # Recompute features for this lookback if needed
            if feat_name == "momentum":
                temp_features = compute_features(equity_df, futures_df, L)
            else:
                temp_features = compute_features(equity_df, futures_df, LOOKBACKS[0])  # any L works for non-momentum

            # Use individual feature as score
            temp_features["combined_score"] = temp_features[feat_col.replace("_raw", "")]

            ic_df = compute_daily_ic(temp_features, returns_df, membership)

            if len(ic_df) < 30:
                continue

            mean_ic, nw_se = newywest_se(ic_df["rank_ic"].values)
            if np.isnan(nw_se) or nw_se == 0:
                continue

            nw_t = mean_ic / nw_se
            df_eff = len(ic_df) - 1
            p_raw = 2 * scipy_stats.t.sf(abs(nw_t), df=df_eff)
            sig = p_raw < bonferroni_alpha

            results.append({
                "feature": feat_name,
                "L": L,
                "mean_IC": round(mean_ic, 6),
                "NW_SE": round(nw_se, 6),
                "NW_t": round(nw_t, 4),
                "p_raw": round(p_raw, 6),
                "n_obs": len(ic_df),
                "significant": sig,
            })

            sig_str = "YES" if sig else "no"
            print(f"  {feat_name:<20} {L:>4} {mean_ic:>10.6f} {nw_t:>8.2f} {p_raw:>10.6f} {sig_str}")

    # Select best lookback for momentum
    momentum_results = [r for r in results if r["feature"] == "momentum"]
    if momentum_results:
        best_m = max(momentum_results, key=lambda r: r["mean_IC"])
        best_L = best_m["L"]
        print(f"\n  Best momentum lookback: L={best_L} (mean IC={best_m['mean_IC']:.6f})")
    else:
        best_L = LOOKBACKS[0]

    return results, best_L


def run_train():
    print("=" * 70)
    print("CB-N50 TRAIN PHASE — Signal Construction & Validation (2016-2019)")
    print("=" * 70)

    # ── Load membership ─────────────────────────────────────────────
    print("\n[1] Loading PIT membership...")
    membership, weights = load_pit_membership()
    months = sorted(membership.keys())
    print(f"  {len(months)} months, {months[0]} to {months[-1]}")

    # ── Determine trade dates ───────────────────────────────────────
    conn = duckdb.connect(EQ_PATH, read_only=True)
    all_dates = conn.execute(f"""
        SELECT DISTINCT trade_date FROM equity_bhavcopy
        WHERE trade_date >= '{TRAIN_START}' AND trade_date <= '{TRAIN_END}'
        ORDER BY trade_date
    """).fetchall()
    conn.close()
    trade_dates = [d[0] for d in all_dates]
    print(f"  {len(trade_dates)} trading days in TRAIN window")

    # ── Load data ───────────────────────────────────────────────────
    print("\n[2] Loading equity panel...")
    equity_df = load_equity_panel(trade_dates, membership)

    print("  Loading futures panel...")
    futures_df = load_futures_panel(trade_dates)

    print("  Computing forward returns (open-to-open)...")
    returns_df = compute_forward_returns(equity_df, membership)

    # ── Feature lookback selection ──────────────────────────────────
    print("\n[3] Feature lookback selection...")
    lookback_results, best_L = feature_lookback_selection(equity_df, futures_df, returns_df, membership)

    # ── Check feature signs ─────────────────────────────────────────
    print("\n[4] Feature sign check...")
    # Per pre-registration: all features pinned with POSITIVE sign.
    # If a feature has negative mean IC, it cannot be flipped post-hoc.
    # The feature must be dropped (G2: 'at least one feature has positive mean IC').

    active_features = ["momentum", "reversal", "basis"]
    features_to_drop = []
    feature_signs = {}

    # Re-check each feature individually with the selected lookback
    for feat_name, feat_col, L in [
        ("momentum", "feat_momentum", best_L),
        ("reversal", "feat_reversal", 1),
        ("basis", "feat_basis", 1),
    ]:
        temp_df = compute_features(equity_df, futures_df, best_L, [feat_name])
        temp_df["combined_score"] = temp_df[feat_col]
        ic_temp = compute_daily_ic(temp_df, returns_df, membership)
        mean_ic_temp = ic_temp["rank_ic"].mean()
        feature_signs[feat_name] = round(float(mean_ic_temp), 6)

        sign_ok = mean_ic_temp > 0
        status = "OK" if sign_ok else "WRONG SIGN — drop"
        if not sign_ok:
            features_to_drop.append(feat_name)
        print(f"  {feat_name}: IC={mean_ic_temp:.6f} ({status})")

    if features_to_drop:
        print(f"\n  Dropping features with wrong sign: {features_to_drop}")
        active_features = [f for f in active_features if f not in features_to_drop]
        print(f"  Retained features: {active_features}")
    else:
        print(f"  All features have correct sign — no features dropped")

    # ── Combined signal with retained features ──────────────────────
    print(f"\n[5] Combined signal ({', '.join(active_features)})...")
    features_df = compute_features(equity_df, futures_df, best_L, active_features)

    ic_df = compute_daily_ic(features_df, returns_df, membership)
    print(f"  Daily IC: {len(ic_df)} observations")

    mean_ic = ic_df["rank_ic"].mean()
    ic_std = ic_df["rank_ic"].std()
    nw_mean, nw_se = newywest_se(ic_df["rank_ic"].values)
    nw_t = nw_mean / nw_se
    df_eff = len(ic_df) - 1
    p_value = 2 * scipy_stats.t.sf(abs(nw_t), df=df_eff)
    bonferroni_alpha = ALPHA / M_MULTIPLICITY
    significant = p_value < bonferroni_alpha

    ac1 = ic_df["rank_ic"].autocorr(lag=1)

    print(f"  Mean IC:           {mean_ic:.6f}")
    print(f"  IC Std:            {ic_std:.6f}")
    print(f"  AC1:               {ac1:.4f}")
    print(f"  NW Mean:           {nw_mean:.6f}")
    print(f"  NW SE:             {nw_se:.6f}")
    print(f"  NW t-statistic:    {nw_t:.4f}")
    print(f"  p-value (raw):     {p_value:.6f}")
    print(f"  Bonferroni alpha:  {bonferroni_alpha:.6f} (m={M_MULTIPLICITY})")
    print(f"  Significant:       {'YES' if significant else 'NO'}")

    # ── G1/G2 Gate Checks ──────────────────────────────────────────
    g1 = significant
    g2 = len(active_features) >= 2  # at least two features with positive IC
    print(f"\n  G1 (Combined IC significance): {'PASS' if g1 else 'FAIL'}")
    print(f"  G2 (Active features > 1): {'PASS' if g2 else 'FAIL'}")

    # ── Breadth threshold verification ──────────────────────────────
    print("\n[6] Breadth threshold verification...")

    # Compute breadth score per day
    features_df["score_positive"] = features_df["combined_score"] > 0

    # Group by date
    breadth_scores = []
    for td, group in features_df.groupby("trade_date"):
        valid = group.dropna(subset=["combined_score"])
        if len(valid) < 30:
            continue

        constituents = get_constituents(td, membership)
        valid = valid[valid["symbol"].isin(constituents)]

        if len(valid) < 30:
            continue

        # Equal-weighted breadth (weights available but not used for this check)
        n_pos = valid["score_positive"].sum()
        breadth = n_pos / len(valid)

        breadth_scores.append({
            "trade_date": td,
            "breadth": breadth,
            "n_stocks": len(valid),
            "n_positive": int(n_pos),
        })

    breadth_df = pd.DataFrame(breadth_scores)
    print(f"  Breadth observations: {len(breadth_df)}")
    print(f"  Breadth mean: {breadth_df['breadth'].mean():.4f}")
    print(f"  Breadth std:  {breadth_df['breadth'].std():.4f}")

    # Classify days by breadth signal
    breadth_df["signal"] = "FLAT"
    breadth_df.loc[breadth_df["breadth"] > 0.65, "signal"] = "LONG"
    breadth_df.loc[breadth_df["breadth"] < 0.35, "signal"] = "SHORT"

    # Merge with Nifty index returns for directional check
    nifty_df = load_nifty_index(trade_dates)
    if len(nifty_df) > 0:
        # Compute forward Nifty return (next day close-to-close, approximate for open-to-open check)
        nifty_df = nifty_df.sort_values("trade_date")
        nifty_df["nifty_return"] = nifty_df["close"].pct_change().shift(-1)

        merged = breadth_df.merge(nifty_df[["trade_date", "nifty_return"]], on="trade_date", how="inner")

        long_days = merged[merged["signal"] == "LONG"]
        short_days = merged[merged["signal"] == "SHORT"]
        flat_days = merged[merged["signal"] == "FLAT"]

        print(f"\n  Directional consistency check:")
        print(f"  LONG days:  {len(long_days):>4} ({len(long_days)/len(merged)*100:.1f}%), mean Nifty return: {long_days['nifty_return'].mean()*10000:.1f} bps")
        print(f"  SHORT days: {len(short_days):>4} ({len(short_days)/len(merged)*100:.1f}%), mean Nifty return: {short_days['nifty_return'].mean()*10000:.1f} bps")
        print(f"  FLAT days:  {len(flat_days):>4} ({len(flat_days)/len(merged)*100:.1f}%), mean Nifty return: {flat_days['nifty_return'].mean()*10000:.1f} bps")

        long_mean = long_days["nifty_return"].mean() if len(long_days) > 0 else 0
        short_mean = short_days["nifty_return"].mean() if len(short_days) > 0 else 0
        directional = long_mean > short_mean
        print(f"\n  Directional: {'PASS' if directional else 'FAIL'} (LONG return {long_mean*10000:.1f} bps > SHORT return {short_mean*10000:.1f} bps)")

    # ── Save results ───────────────────────────────────────────────
    results = {
        "phase": "TRAIN",
        "window": f"{TRAIN_START} to {TRAIN_END}",
        "n_trading_days": len(trade_dates),
        "n_ic_observations": len(ic_df),
        "lookback_selection": lookback_results,
        "best_momentum_L": best_L,
        "feature_signs": feature_signs,
        "features_dropped": features_to_drop,
        "active_features": active_features,
        "combined_ic": {
            "mean_IC": round(float(mean_ic), 6),
            "ic_std": round(float(ic_std), 6),
            "ac1": round(float(ac1), 4),
            "nw_mean": round(float(nw_mean), 6),
            "nw_se": round(float(nw_se), 6),
            "nw_t": round(float(nw_t), 4),
            "p_value": round(float(p_value), 6),
            "bonferroni_alpha": round(float(bonferroni_alpha), 6),
            "m_multiplicity": M_MULTIPLICITY,
            "significant": bool(significant),
        },
        "breadth": {
            "n_observations": len(breadth_df),
            "breadth_mean": round(float(breadth_df["breadth"].mean()), 4),
            "n_long": int((breadth_df["signal"] == "LONG").sum()),
            "n_short": int((breadth_df["signal"] == "SHORT").sum()),
            "n_flat": int((breadth_df["signal"] == "FLAT").sum()),
        },
        "gate_g1": "PASS" if g1 else "FAIL",
        "gate_g2": "PASS" if g2 else "FAIL",
    }

    out_path = Path("F:/Nifty/docs/reports/CB_N50_TRAIN_RESULTS.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to: {out_path}")

    # ── Report ──────────────────────────────────────────────────────
    report_lines = []
    report_lines.append("# CB-N50 TRAIN Report — Signal Construction & Validation")
    report_lines.append(f"Generated: {date.today()}")
    report_lines.append("")
    report_lines.append(f"**Window:** {TRAIN_START} to {TRAIN_END}")
    report_lines.append(f"**Trading days:** {len(trade_dates)}")
    report_lines.append(f"**IC observations:** {len(ic_df)}")
    report_lines.append("")
    report_lines.append("## Feature Lookback Selection (Bonferroni m=9)")
    report_lines.append("")
    report_lines.append("| Feature | L | Mean IC | NW t | p_raw | Significant? |")
    report_lines.append("|---------|---|---------|------|-------|-------------|")
    for r in lookback_results:
        report_lines.append(
            f"| {r['feature']} | {r['L']} | {r['mean_IC']:.6f} | {r['NW_t']:.2f} | {r['p_raw']:.6f} | {'YES' if r['significant'] else 'no'} |"
        )
    report_lines.append("")
    report_lines.append(f"**Best momentum lookback: L={best_L}**")
    report_lines.append("")
    report_lines.append("## Feature Sign Check")
    report_lines.append("")
    for feat, ic in feature_signs.items():
        sign = "OK" if ic > 0 else "WRONG SIGN — dropped"
        report_lines.append(f"- {feat}: IC={ic:.6f} ({sign})")
    if features_to_drop:
        report_lines.append(f"\nDropped: {', '.join(features_to_drop)}")
    report_lines.append(f"Active: {', '.join(active_features)}")
    report_lines.append("")
    report_lines.append("## Combined Signal (retained features)")
    report_lines.append("")
    report_lines.append(f"- Mean IC: {mean_ic:.6f}")
    report_lines.append(f"- IC Std: {ic_std:.6f}")
    report_lines.append(f"- AC1: {ac1:.4f}")
    report_lines.append(f"- NW Mean: {nw_mean:.6f}")
    report_lines.append(f"- NW SE: {nw_se:.6f}")
    report_lines.append(f"- NW t-statistic: {nw_t:.4f}")
    report_lines.append(f"- p-value (raw): {p_value:.6f}")
    report_lines.append(f"- Bonferroni alpha: {bonferroni_alpha:.6f} (m={M_MULTIPLICITY})")
    report_lines.append(f"- **Significant: {'YES' if significant else 'NO'}**")
    report_lines.append("")
    report_lines.append(f"**G1 Gate (IC significance): {'PASS' if g1 else 'FAIL'}**")
    report_lines.append(f"**G2 Gate (features with correct sign): {'PASS' if g2 else 'FAIL'}**")
    report_lines.append("")
    report_lines.append("## Breadth Threshold Verification")
    report_lines.append("")
    report_lines.append(f"- Breadth mean: {breadth_df['breadth'].mean():.4f}")
    if len(nifty_df) > 0:
        report_lines.append(f"- LONG days: {len(long_days)} ({len(long_days)/len(merged)*100:.1f}%), mean Nifty next-day return: {long_days['nifty_return'].mean()*10000:.1f} bps")
        report_lines.append(f"- SHORT days: {len(short_days)} ({len(short_days)/len(merged)*100:.1f}%), mean Nifty return: {short_days['nifty_return'].mean()*10000:.1f} bps")
        report_lines.append(f"- FLAT days: {len(flat_days)} ({len(flat_days)/len(merged)*100:.1f}%), mean Nifty return: {flat_days['nifty_return'].mean()*10000:.1f} bps")
        report_lines.append(f"- Directional: {'PASS' if directional else 'FAIL'} (LONG > SHORT: {long_mean*10000:.1f} > {short_mean*10000:.1f} bps)")
    report_lines.append("")

    report_text = "\n".join(report_lines)
    report_path = Path("F:/Nifty/docs/reports/CB_N50_TRAIN_REPORT.md")
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Report saved to: {report_path}")

    return g1 and g2


if __name__ == "__main__":
    ok = run_train()
    print(f"\n{'='*70}")
    print(f"TRAIN: {'PASS' if ok else 'FAIL'} — {'HOLDOUT authorised' if ok else 'No HOLDOUT read'}")
    print(f"{'='*70}")
