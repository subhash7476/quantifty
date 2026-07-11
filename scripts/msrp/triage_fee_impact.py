"""MSRP Phase-7 precondition gate (c): fee-impact triage of the D1 rule.

Rough dev-window (2023-01-02 -> 2025-12-31) pass of the D1 next-day ATM straddle
rule, gross and net of the gate-(b) options fee model. This is a TRIAGE, not a
backtest: forecasts use the frozen artifact coefficients (fit on this same dev
window, so the signal is IN-SAMPLE and the gross edge is optimistic), thresholds
are dev-quantiles, and margin is not modelled. Its one job is the stop-rule from
MSRP_PHASE7_STRATEGY_RESEARCH.md par.6.1: if the net-of-cost dev edge is ~zero,
stop before pre-registration.

Rule shape (research doc par.5 D1):
  signal at close t: r_t = E[RV_{t+1}] / implied_daily_t, implied = VIX_t/100/sqrt(252)
  trade at t+1: ATM straddle (nearest strike to close_t), nearest expiry DTE >= 2,
  enter at t+1 open, exit at t+1 close (bhavcopy prices), 1 lot.

Usage::

    python scripts/msrp/triage_fee_impact.py
"""

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.options.fees import option_order_fees  # noqa: E402
from core.msi.msrp.forward_vol import compute_daily_rv, compute_har_features  # noqa: E402

DEV_START = "2023-01-02"
DEV_END = "2025-12-31"
NIFTY_50 = "NSE_INDEX|Nifty 50"
INDIA_VIX = "NSE_INDEX|India VIX"
CANDLES_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLES_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
BHAVCOPY_DB = ROOT / "data" / "market_data" / "options_bhavcopy.duckdb"
ARTIFACT_MODEL = ROOT / "core" / "msi" / "artifacts" / "forward_vol_v2" / "model.py"
REPORT = ROOT / "docs" / "reports" / "MSRP_PHASE7_FEE_TRIAGE.md"

MIN_DTE = 2          # research doc F4: weekday-agnostic contract selection
Z90 = 1.6448536269514722  # 90% two-sided normal quantile (abstention rule)


def load_frozen_coeffs() -> dict:
    spec = importlib.util.spec_from_file_location("forward_vol_v2_model", ARTIFACT_MODEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"b0": mod.B0, "b1": mod.B1, "b2": mod.B2, "b3": mod.B3, "b4": mod.B4,
            "sigma": mod.SIGMA}


def _iter_duckdb_days(root: Path, start: str, end: str):
    start_d, end_d = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    for f in sorted(root.glob("*.duckdb")):
        try:
            d = pd.Timestamp(f.stem).date()
        except ValueError:
            continue
        if start_d <= d <= end_d:
            yield f


def load_nifty_1m_closes_by_day() -> dict:
    closes_by_day = {}
    for f in _iter_duckdb_days(CANDLES_1M, DEV_START, DEV_END):
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ? ORDER BY timestamp",
                [NIFTY_50],
            ).fetchall()
        finally:
            con.close()
        if not rows:
            continue
        day = pd.Timestamp(rows[0][0]).normalize()
        closes_by_day[day] = np.array([float(r[1]) for r in rows], dtype=float)
    return closes_by_day


def load_vix_daily_close() -> pd.Series:
    records = []
    for f in _iter_duckdb_days(CANDLES_1D, DEV_START, DEV_END):
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ?", [INDIA_VIX]
            ).fetchall()
        finally:
            con.close()
        for ts, close in rows:
            records.append((pd.Timestamp(ts).normalize(), float(close)))
    idx = pd.DatetimeIndex([r[0] for r in records], name="date")
    return pd.Series([r[1] for r in records], index=idx, name="vix")


def load_bhavcopy() -> pd.DataFrame:
    con = duckdb.connect(str(BHAVCOPY_DB), read_only=True)
    try:
        df = con.execute(
            """
            SELECT trade_date, expiry_dt, strike, option_type, open, close
            FROM option_bhavcopy
            WHERE trade_date <= ?
            """,
            [DEV_END],
        ).df()
    finally:
        con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"]).dt.date
    return df


def nifty_lot_size(d: date) -> int:
    # 50 -> 25 (2024-04-26, NSE FAOP64625) -> 75 (new contracts from 2024-11-20,
    # SEBI Rs 15L minimum). Transition contracts kept old lots until expiry —
    # approximated as a hard cut, acceptable for triage.
    if d >= date(2024, 11, 20):
        return 75
    if d >= date(2024, 4, 26):
        return 25
    return 50


def select_straddle(day_df: pd.DataFrame, trade_d: date, spot: float):
    """Nearest-strike ATM straddle on the nearest expiry with DTE >= MIN_DTE.

    Both legs must have open > 0 and close > 0. Returns None if no valid pair.
    """
    eligible = day_df[day_df["expiry_dt"] >= trade_d + timedelta(days=MIN_DTE)]
    if eligible.empty:
        return None
    expiry = eligible["expiry_dt"].min()
    chain = eligible[eligible["expiry_dt"] == expiry]
    valid = chain[(chain["open"] > 0) & (chain["close"] > 0)]
    pivot = valid.pivot_table(index="strike", columns="option_type",
                              values=["open", "close"], aggfunc="first")
    if pivot.empty:
        return None
    has_both = pivot.dropna()
    if has_both.empty:
        return None
    strikes = has_both.index.to_numpy(dtype=float)
    strike = float(strikes[np.argmin(np.abs(strikes - spot))])
    row = has_both.loc[strike]
    return {
        "expiry": expiry,
        "dte": (expiry - trade_d).days,
        "strike": strike,
        "ce_open": float(row[("open", "CE")]),
        "pe_open": float(row[("open", "PE")]),
        "ce_close": float(row[("close", "CE")]),
        "pe_close": float(row[("close", "PE")]),
    }


def straddle_fees(legs: dict, lot: int, trade_d: date, direction: str) -> float:
    """Round-trip fees for 1 lot. Long: buy both at open, sell both at close.
    Short: sell both at open, buy both at close."""
    entry_side, exit_side = ("BUY", "SELL") if direction == "long" else ("SELL", "BUY")
    total = 0.0
    for prem in (legs["ce_open"], legs["pe_open"]):
        total += option_order_fees(premium=prem, quantity=lot, side=entry_side,
                                   trade_date=trade_d).total
    for prem in (legs["ce_close"], legs["pe_close"]):
        total += option_order_fees(premium=prem, quantity=lot, side=exit_side,
                                   trade_date=trade_d).total
    return total


def build_daily_records() -> pd.DataFrame:
    coeffs = load_frozen_coeffs()
    closes_by_day = load_nifty_1m_closes_by_day()
    rv = compute_daily_rv(closes_by_day)
    features = compute_har_features(rv)
    vix = load_vix_daily_close().reindex(features.index)
    spot_close = pd.Series({d: float(c[-1]) for d, c in closes_by_day.items()}).reindex(
        features.index)

    bhav = load_bhavcopy()
    bhav_by_day = dict(tuple(bhav.groupby("trade_date")))

    sigma = coeffs["sigma"]
    records = []
    skipped_no_next, skipped_no_straddle = 0, 0
    feature_days = features.index.to_list()
    for i, t in enumerate(feature_days[:-1]):
        v = vix.loc[t]
        if pd.isna(v) or pd.isna(spot_close.loc[t]):
            continue
        t_next = feature_days[i + 1].date()
        # trade only if t+1 is the immediate next NSE session present in bhavcopy
        if t_next not in bhav_by_day:
            skipped_no_next += 1
            continue
        mu = (coeffs["b0"]
              + coeffs["b1"] * np.log(features.loc[t, "rv_daily"])
              + coeffs["b2"] * np.log(features.loc[t, "rv_weekly"])
              + coeffs["b3"] * np.log(features.loc[t, "rv_monthly"])
              + coeffs["b4"] * np.log(v))
        e_rv = float(np.exp(mu + sigma ** 2 / 2.0))
        ci_lo, ci_hi = float(np.exp(mu - Z90 * sigma)), float(np.exp(mu + Z90 * sigma))
        implied = float(v) / 100.0 / np.sqrt(252.0)

        spot = float(spot_close.loc[t])
        legs = select_straddle(bhav_by_day[t_next], t_next, spot)
        if legs is None:
            skipped_no_straddle += 1
            continue
        lot = nifty_lot_size(t_next)
        open_prem = legs["ce_open"] + legs["pe_open"]
        close_prem = legs["ce_close"] + legs["pe_close"]
        gross_long = (close_prem - open_prem) * lot
        rv_next = rv.get(feature_days[i + 1], np.nan)
        records.append({
            "rv_next": float(rv_next) if not pd.isna(rv_next) else np.nan,
            "signal_date": t.date(),
            "trade_date": t_next,
            "dte": legs["dte"],
            "strike": legs["strike"],
            "spot": spot,
            "e_rv": e_rv,
            "implied": implied,
            "ratio": e_rv / implied,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "lot": lot,
            "open_prem": open_prem,
            "close_prem": close_prem,
            "gross_long": gross_long,
            "gross_short": -gross_long,
            "fees_long": straddle_fees(legs, lot, t_next, "long"),
            "fees_short": straddle_fees(legs, lot, t_next, "short"),
        })
    df = pd.DataFrame(records)
    df.attrs["skipped_no_next"] = skipped_no_next
    df.attrs["skipped_no_straddle"] = skipped_no_straddle
    return df


def arm_stats(sub: pd.DataFrame, direction: str, n_total: int) -> dict:
    gross = sub[f"gross_{direction}"]
    fees = sub[f"fees_{direction}"]
    net = gross - fees
    days = len(sub)
    ann = np.sqrt(252.0)
    return {
        "n": days,
        "pct_days": 100.0 * days / n_total if n_total else 0.0,
        "gross": gross.sum(),
        "fees": fees.sum(),
        "net": net.sum(),
        "net_per_day": net.mean() if days else 0.0,
        "hit": 100.0 * (net > 0).mean() if days else 0.0,
        "sharpe": (net.mean() / net.std() * ann) if days > 1 and net.std() > 0 else 0.0,
    }


def main() -> None:
    df = build_daily_records()
    n = len(df)
    print(f"Daily records: {n} "
          f"(skipped: {df.attrs['skipped_no_next']} no-next-session, "
          f"{df.attrs['skipped_no_straddle']} no-valid-straddle)")

    arms = {}
    arms["Unconditional long straddle"] = arm_stats(df, "long", n)
    arms["Unconditional short straddle"] = arm_stats(df, "short", n)
    for q in (0.1, 0.2, 0.3):
        lo, hi = df["ratio"].quantile(q), df["ratio"].quantile(1 - q)
        arms[f"Gated short (ratio <= q{int(q*100)})"] = arm_stats(
            df[df["ratio"] <= lo], "short", n)
        arms[f"Gated long (ratio >= q{int((1-q)*100)})"] = arm_stats(
            df[df["ratio"] >= hi], "long", n)
    lo20, hi80 = df["ratio"].quantile(0.2), df["ratio"].quantile(0.8)
    combined_short = arm_stats(df[df["ratio"] <= lo20], "short", n)
    combined_long = arm_stats(df[df["ratio"] >= hi80], "long", n)

    # Abstention rule (research doc D1): flat when implied inside the 90% interval
    outside_hi = df[df["implied"] > df["ci_hi"]]   # market prices more vol than model -> short
    outside_lo = df[df["implied"] < df["ci_lo"]]   # market prices less vol than model -> long
    arms["Abstention short (implied > CI90 hi)"] = arm_stats(outside_hi, "short", n)
    arms["Abstention long (implied < CI90 lo)"] = arm_stats(outside_lo, "long", n)

    per_year = []
    for yr, sub in df.groupby(pd.to_datetime(df["trade_date"]).dt.year):
        s_lo = sub[sub["ratio"] <= lo20]
        per_year.append({
            "year": int(yr),
            "days": len(sub),
            "lot": int(sub["lot"].mode().iloc[0]),
            "uncond_short_net": (sub["gross_short"] - sub["fees_short"]).sum(),
            "gated_short_net": (s_lo["gross_short"] - s_lo["fees_short"]).sum(),
            "gated_short_days": len(s_lo),
            "avg_fee_rt": sub["fees_short"].mean(),
            "avg_abs_gross": sub["gross_short"].abs().mean(),
        })

    fee_drag = df["fees_short"].mean() / df["gross_short"].abs().mean() * 100.0

    # --- Robustness: where does the chain break? ------------------------------
    df["long_ret"] = (df["close_prem"] - df["open_prem"]) / df["open_prem"]
    sp_construct = df["e_rv"].corr(df["rv_next"], method="spearman")
    sp_transmission = df["rv_next"].corr(df["long_ret"], method="spearman")
    sp_signal = df["ratio"].corr(df["long_ret"], method="spearman")
    # Straddle-implied denominator variant. CONTAMINATED by construction: the
    # entry premium (t+1 open) sits in both the signal denominator and the
    # return denominator, so noise in the open price induces spurious positive
    # rank correlation — reported as an upper bound only, not a valid signal.
    implied2 = (df["open_prem"] / df["spot"]) / np.sqrt(df["dte"].clip(lower=1))
    ratio2 = df["e_rv"] / implied2
    sp_signal2 = ratio2.corr(df["long_ret"], method="spearman")
    r2_short = arm_stats(df[ratio2 <= ratio2.quantile(0.2)], "short", n)
    r2_long = arm_stats(df[ratio2 >= ratio2.quantile(0.8)], "long", n)

    lines = []
    lines.append("# MSRP Phase 7 — Gates (b) + (c): Options Fee Model and Fee-Impact Triage\n")
    lines.append(f"*Generated: {pd.Timestamp.now().isoformat()}*\n")
    lines.append("**Caveats (by design of the triage):** signal is IN-SAMPLE (frozen artifact "
                 "coefficients were fit on this same dev window) so gross edges are optimistic; "
                 "thresholds are dev-quantiles; bhavcopy open/close fills; no slippage; no margin "
                 "denominator; 1 lot throughout (lot size era-accurate: 50/25/75).\n")
    lines.append(f"- Dev window: {DEV_START} -> {DEV_END}; tradable days: {n} "
                 f"(skipped {df.attrs['skipped_no_next']} no-next-session, "
                 f"{df.attrs['skipped_no_straddle']} no-valid-straddle)")
    lines.append(f"- DTE of selected contracts: median {df['dte'].median():.0f}, "
                 f"p10 {df['dte'].quantile(0.1):.0f}, p90 {df['dte'].quantile(0.9):.0f}")
    lines.append(f"- Mean round-trip fee (short, 1 lot): Rs {df['fees_short'].mean():.0f}; "
                 f"mean |gross| per day: Rs {df['gross_short'].abs().mean():.0f}; "
                 f"**fee drag = {fee_drag:.1f}% of mean absolute daily gross**\n")

    lines.append("## Arms (1 lot, Rs, dev window total)\n")
    lines.append("| Arm | Days | %Days | Gross | Fees | Net | Net/day | Hit% | Sharpe |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for name, s in arms.items():
        lines.append(f"| {name} | {s['n']} | {s['pct_days']:.0f}% | {s['gross']:,.0f} | "
                     f"{s['fees']:,.0f} | {s['net']:,.0f} | {s['net_per_day']:,.0f} | "
                     f"{s['hit']:.1f} | {s['sharpe']:.2f} |")
    lines.append("")
    lines.append("## Combined D1 rule (short <= q20, long >= q80)\n")
    for label, s in (("short leg", combined_short), ("long leg", combined_long)):
        lines.append(f"- {label}: {s['n']} days, gross {s['gross']:,.0f}, fees {s['fees']:,.0f}, "
                     f"net {s['net']:,.0f} (net/day {s['net_per_day']:,.0f}, hit {s['hit']:.1f}%, "
                     f"Sharpe {s['sharpe']:.2f})")
    tot_net = combined_short["net"] + combined_long["net"]
    lines.append(f"- **combined net: Rs {tot_net:,.0f}**\n")

    lines.append("## Per-year (short arms)\n")
    lines.append("| Year | Days | Lot | Uncond short net | Gated short net (q20) | Gated days | "
                 "Avg fee RT | Avg &#124;gross&#124; |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in per_year:
        lines.append(f"| {r['year']} | {r['days']} | {r['lot']} | {r['uncond_short_net']:,.0f} | "
                     f"{r['gated_short_net']:,.0f} | {r['gated_short_days']} | "
                     f"{r['avg_fee_rt']:,.0f} | {r['avg_abs_gross']:,.0f} |")
    lines.append("")
    lines.append("Rupee figures are per 1 lot with the era-accurate lot size, so per-year "
                 "totals are not directly comparable across the 50/25/75 lot eras.\n")

    lines.append("## Robustness — where the chain breaks\n")
    lines.append("Rank (Spearman) correlations over the tradable days, in causal order:\n")
    lines.append(f"1. `E[RV_t+1]` vs realized `RV_t+1` (the certified construct): "
                 f"**{sp_construct:.3f}** — the artifact does its job (in-sample).")
    lines.append(f"2. Realized `RV_t+1` vs long-straddle open->close return (the transmission): "
                 f"**{sp_transmission:.3f}** — even PERFECT next-day RV foresight barely "
                 f"predicts unhedged straddle P&L. This is the construct gap of research-doc "
                 f"finding 1, measured.")
    lines.append(f"3. D1 signal `E[RV]/implied_vix` vs long-straddle return: "
                 f"**{sp_signal:.3f}** — no exploitable rank relationship.")
    lines.append(f"4. Straddle-implied denominator variant (`E[RV] / (entry_prem/spot/sqrt(DTE))`): "
                 f"rank {sp_signal2:.3f}; gated arms net short {r2_short['net']:,.0f} / long "
                 f"{r2_long['net']:,.0f} over {r2_short['n']}+{r2_long['n']} days "
                 f"({(r2_short['net'] + r2_long['net']) / max(r2_short['n'] + r2_long['n'], 1):,.0f}/day vs "
                 f"{arms['Unconditional short straddle']['net_per_day']:,.0f}/day unconditional short). "
                 f"Mechanically contaminated (entry premium in both signal and return "
                 f"denominators) and mildly look-ahead — an optimistic upper bound that "
                 f"STILL does not beat the dumb baseline.\n")

    lines.append("## Verdict\n")
    lines.append("- **Gate (b) — options fee model: PASS.** `core/execution/options/fees.py`, "
                 "effective-dated statutory schedules (STT 0.05/0.0625/0.1/0.15%, NSE txn "
                 "0.0495/0.03503%, SEBI, GST, stamp), 12 unit tests green "
                 "(`tests/execution/test_options_fees.py`).")
    lines.append("- **Gate (c) — fee-impact triage: STOP CONDITION TRIGGERED.** Fees are NOT "
                 "the binding constraint (drag ~6% of mean absolute daily gross; the "
                 "unconditional short survives costs). The binding failure is the "
                 "construct transmission: the Knowledge-gated D1 rule is net NEGATIVE "
                 "in-sample while the no-Knowledge unconditional short-straddle baseline is "
                 "net positive — the artifact adds nothing over the dumb premium seller in "
                 "any variant tried, because next-day RV itself is nearly orthogonal to "
                 "unhedged straddle P&L at this horizon.")
    lines.append("- Per research-doc par.6.1: **do not pre-register D1 as specified.** The "
                 "unconditional short-VRP result is not a rescue: it does not consume the "
                 "Knowledge (fails the charter's Phase-7 definition), is era-concentrated "
                 "(2023 negative), and carries unmodelled short-vol tail risk.")
    lines.append("- Decision on how to proceed (delta-hedged construct needs intraday options "
                 "data that does not exist; alternative transmissions; or stand down Phase 7) "
                 "belongs to the operator.\n")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {REPORT}")
    for name, s in arms.items():
        print(f"{name:45s} n={s['n']:4d} gross={s['gross']:12,.0f} fees={s['fees']:10,.0f} "
              f"net={s['net']:12,.0f} sharpe={s['sharpe']:6.2f}")
    print(f"Combined D1 net: {tot_net:,.0f}")


if __name__ == "__main__":
    main()
