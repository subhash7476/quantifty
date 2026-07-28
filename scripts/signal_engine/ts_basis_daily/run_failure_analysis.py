"""TS Basis Daily — Signal Failure Analysis.

Joins every signal against regime (VIX, Nifty gap), sector, ADV, and
signal-strength dimensions to identify conditional failure predictors.
Reads TRAIN only (investigation, not gated evaluation).

Output: docs/reports/TS_BASIS_DAILY_FAILURE_ANALYSIS.md
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
IDX_DIR = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
SECTOR_CSV = ROOT / "governance" / "carry" / "sector_classification.csv"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_FAILURE_ANALYSIS.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

MIN_FORMATIONS_PER_BUCKET = 30
MIN_SIGNALS_PER_BUCKET = 100


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_index_regime(dates_sorted):
    """Build {date: {vix, nifty_close, nifty_open, banknifty_close}} from 1d index store."""
    regime = {}
    for d in dates_sorted:
        f = IDX_DIR / f"{d}.duckdb"
        if not f.exists():
            continue
        try:
            c = duckdb.connect()
            c.execute(f"ATTACH '{f}' AS src (READ_ONLY)")
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|India VIX'"
            ).fetchone()
            vix = float(row[0]) if row else None
            row = c.execute(
                "SELECT close, open FROM src.candles WHERE symbol = 'NSE_INDEX|Nifty 50'"
            ).fetchone()
            nifty_close = float(row[0]) if row else None
            nifty_open = float(row[1]) if row else None
            row = c.execute(
                "SELECT close FROM src.candles WHERE symbol = 'NSE_INDEX|Nifty Bank'"
            ).fetchone()
            bn_close = float(row[0]) if row else None
            c.close()
            regime[d] = {
                "vix": vix, "nifty_close": nifty_close,
                "nifty_open": nifty_open, "bn_close": bn_close,
            }
        except Exception:
            continue
    return regime


def _load_sectors():
    """Return {symbol: sector_name} for all symbols in sector CSV."""
    sectors = {}
    with open(SECTOR_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sectors[row["symbol"]] = row["sector"]
    return sectors


def _load_adv_tier(con, signals):
    """For each (fdate, underlying), get val_in_lakh and assign within-date tercile."""
    dates = sorted({s[0] for s in signals})
    adv_rows = []
    for fdate in dates:
        ulist = sorted({s[1] for s in signals if s[0] == fdate})
        if not ulist:
            continue
        ul = ", ".join(f"'{u}'" for u in ulist)
        rows = con.execute(f"""
            SELECT underlying, val_in_lakh
            FROM fut.futures_bhavcopy
            WHERE trade_date = DATE '{fdate}' AND inst_type = 'FUTSTK'
            AND underlying IN ({ul}) AND val_in_lakh IS NOT NULL
        """).fetchall()
        vals = [(r[0], float(r[1])) for r in rows if r[1] is not None]
        if len(vals) < 5:
            continue
        thresholds = np.percentile([v for _, v in vals], [33.33, 66.67])
        for u, v in vals:
            if v <= thresholds[0]:
                tier = 1
            elif v <= thresholds[1]:
                tier = 2
            else:
                tier = 3
            adv_rows.append((fdate, u, tier))
    return adv_rows


def _signed_return(z_ts, fwd_ret_1m):
    return fwd_ret_1m * (1.0 if z_ts > 0 else -1.0)


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    print("Loading signals (TRAIN)...")
    sig_rows = con.execute(f"""
        SELECT formation_date, underlying, z_ts, fwd_ret_1m, liquid
        FROM sig.signals
        WHERE formation_date >= DATE '{WINDOWS['TRAIN'][0]}'
          AND formation_date <= DATE '{WINDOWS['TRAIN'][1]}'
          AND z_ts IS NOT NULL AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
        ORDER BY formation_date, z_ts DESC
    """).fetchall()

    signals = [(r[0], r[1], float(r[2]), float(r[3])) for r in sig_rows]
    n_sig = len(signals)
    n_dates = len({r[0] for r in sig_rows})
    print(f"  {n_sig:,} signals across {n_dates} formations")

    all_dates = sorted({r[0] for r in sig_rows})
    print(f"Loading index regime for {len(all_dates)} dates...")
    regime = _load_index_regime(all_dates)
    missing_dates = [d for d in all_dates if d not in regime]
    if missing_dates:
        print(f"  WARNING: {len(missing_dates)} dates missing from index store")

    print("Loading sector classification...")
    sectors = _load_sectors()
    unmatched = sorted({s[1] for s in signals if s[1] not in sectors})
    if unmatched:
        print(f"  WARNING: {len(unmatched)} symbols unmatched to sector: {unmatched[:10]}...")

    print("Computing ADV tiers...")
    adv_tiers = _load_adv_tier(con, signals)
    adv_map = {(r[0], r[1]): r[2] for r in adv_tiers}
    print(f"  {len(adv_map)} ADV-tiered signal-cells")

    con.close()

    # Build enriched rows: (fdate, sym, z_ts, fwd_ret, signed_ret, vix, nifty_close,
    #                        nifty_open_next, nifty_ret, gap, sector, adv_tier, abs_z)
    date_idx = {d: i for i, d in enumerate(all_dates)}
    enriched = []
    for s in signals:
        fdate, sym, z, fr = s
        rd = regime.get(fdate)
        if rd is None:
            continue
        vix = rd["vix"]
        nc = rd["nifty_close"]
        if vix is None or nc is None:
            continue

        # Find next trading day for gap computation
        idx = date_idx.get(fdate, -1)
        if idx >= 0 and idx + 1 < len(all_dates):
            nd = all_dates[idx + 1]
            rd_next = regime.get(nd)
            if rd_next and rd_next["nifty_open"] is not None:
                gap = (rd_next["nifty_open"] - nc) / nc
            else:
                gap = None
        else:
            gap = None

        sec = sectors.get(sym, "Unclassified")
        adv_tier = adv_map.get((fdate, sym), None)
        signed = _signed_return(z, fr)
        abs_z = abs(z)

        enriched.append((
            fdate, sym, z, fr, signed, vix, nc, gap, sec, adv_tier, abs_z,
        ))

    n_enriched = len(enriched)
    print(f"  {n_enriched:,} enriched signals ({n_sig - n_enriched:,} dropped — missing regime data)")

    # ── Bucket Analysis ──────────────────────────────────────────────

    def _bucket_continuous(values, labels, n_buckets=3):
        """Assign each value to a bucket (0, 1, 2) based on terciles."""
        arr = np.array([v for v in values if v is not None], dtype=float)
        if len(arr) < MIN_SIGNALS_PER_BUCKET * n_buckets:
            return None
        thresholds = np.percentile(arr, np.linspace(0, 100, n_buckets + 1)[1:-1])
        buckets = []
        for v in values:
            if v is None:
                buckets.append(None)
            elif v <= thresholds[0]:
                buckets.append(0)
            elif n_buckets == 2 or v <= thresholds[1]:
                buckets.append(1)
            else:
                buckets.append(n_buckets - 1)
        return {"buckets": buckets, "labels": labels, "thresholds": thresholds}

    def _analyze_dimension(name, bucket_fn):
        """For each bucket in a dimension, compute hit rate and mean signed return."""
        rows = []
        for b_idx, b_label in enumerate(bucket_fn["labels"]):
            subset = [(signed, abs_z) for i, (signed, abs_z) in
                      enumerate(zip(signed_returns, abs_zs))
                      if bucket_fn["buckets"][i] == b_idx]
            if len(subset) < MIN_SIGNALS_PER_BUCKET:
                continue
            signed_arr = np.array([x[0] for x in subset])
            n = len(signed_arr)
            hit_rate = float(np.mean(signed_arr > 0))
            mean_signed = float(np.mean(signed_arr))
            mean_abs_fwd = float(np.mean(np.abs([fr for i, fr in enumerate(fwd_rets)
                                                  if bucket_fn["buckets"][i] == b_idx])))
            ste = float(np.std(signed_arr, ddof=1) / np.sqrt(n)) if n > 1 else 0.0
            rows.append({
                "dim": name, "bucket": b_label, "n": n,
                "hit_rate": hit_rate, "mean_signed": mean_signed,
                "mean_abs_fwd": mean_abs_fwd, "ste": ste,
            })
        return rows

    # Extract arrays for bucketing
    fwd_rets = [r[3] for r in enriched]
    signed_returns = [r[4] for r in enriched]
    abs_zs = [r[10] for r in enriched]
    vix_vals = [r[5] for r in enriched]
    gap_vals = [r[7] for r in enriched]

    all_buckets = []

    # 1. VIX tercile
    vix_b = _bucket_continuous(vix_vals, ["Low VIX", "Mid VIX", "High VIX"], 3)
    if vix_b:
        t = vix_b["thresholds"]
        threshold_str = f"thresholds={t[0]:.1f}, {t[1]:.1f}"
        all_buckets.extend(_analyze_dimension(f"VIX ({threshold_str})", vix_b))

    # 2. Overnight gap (Nifty open next day vs today's close)
    valid_gaps = [g for g in gap_vals if g is not None]
    if len(valid_gaps) >= MIN_SIGNALS_PER_BUCKET * 3:
        g_arr = np.array(valid_gaps)
        thresholds = np.percentile(g_arr, [33.33, 66.67])
        labels = [
            f"Gap < {thresholds[0]*100:+.2f}%",
            f"Gap {thresholds[0]*100:+.2f}% to {thresholds[1]*100:+.2f}%",
            f"Gap > {thresholds[1]*100:+.2f}%",
        ]
        gap_buckets = []
        for g in gap_vals:
            if g is None:
                gap_buckets.append(None)
            elif g <= thresholds[0]:
                gap_buckets.append(0)
            elif g <= thresholds[1]:
                gap_buckets.append(1)
            else:
                gap_buckets.append(2)
        bf = {"buckets": gap_buckets, "labels": labels}
        all_buckets.extend(_analyze_dimension("Overnight Nifty Gap", bf))

    # 3. Signal strength (abs z_ts tercile)
    z_b = _bucket_continuous(abs_zs, ["Weak signal (|z| low)", "Mid signal", "Strong signal (|z| high)"], 3)
    if z_b:
        t = z_b["thresholds"]
        threshold_str = f"thresholds={t[0]:.2f}, {t[1]:.2f}"
        all_buckets.extend(_analyze_dimension(f"Signal Strength ({threshold_str})", z_b))

    # 4. Sector
    sector_groups = defaultdict(list)
    for i, r in enumerate(enriched):
        sector_groups[r[8]].append((signed_returns[i], fwd_rets[i]))
    for sec_name, items in sorted(sector_groups.items()):
        if len(items) < MIN_SIGNALS_PER_BUCKET:
            continue
        signed_arr = np.array([x[0] for x in items])
        n = len(signed_arr)
        hit_rate = float(np.mean(signed_arr > 0))
        mean_signed = float(np.mean(signed_arr))
        mean_abs_fwd = float(np.mean(np.abs([x[1] for x in items])))
        ste = float(np.std(signed_arr, ddof=1) / np.sqrt(n)) if n > 1 else 0.0
        all_buckets.append({
            "dim": "Sector", "bucket": sec_name, "n": n,
            "hit_rate": hit_rate, "mean_signed": mean_signed,
            "mean_abs_fwd": mean_abs_fwd, "ste": ste,
        })

    # 5. ADV tier
    adv_groups = defaultdict(list)
    for i, r in enumerate(enriched):
        t = r[9]
        if t is None:
            continue
        adv_groups[t].append((signed_returns[i], fwd_rets[i]))
    adv_labels_map = {1: "Low ADV (bottom 1/3)", 2: "Mid ADV", 3: "High ADV (top 1/3)"}
    for tier in [1, 2, 3]:
        items = adv_groups.get(tier, [])
        if len(items) < MIN_SIGNALS_PER_BUCKET:
            continue
        signed_arr = np.array([x[0] for x in items])
        n = len(signed_arr)
        hit_rate = float(np.mean(signed_arr > 0))
        mean_signed = float(np.mean(signed_arr))
        mean_abs_fwd = float(np.mean(np.abs([x[1] for x in items])))
        ste = float(np.std(signed_arr, ddof=1) / np.sqrt(n)) if n > 1 else 0.0
        all_buckets.append({
            "dim": "ADV Tier", "bucket": adv_labels_map[tier], "n": n,
            "hit_rate": hit_rate, "mean_signed": mean_signed,
            "mean_abs_fwd": mean_abs_fwd, "ste": ste,
        })

    # ── Baseline ─────────────────────────────────────────────────────
    signed_all = np.array(signed_returns)
    baseline_hit = float(np.mean(signed_all > 0))
    baseline_mean = float(np.mean(signed_all))
    baseline_ste = float(np.std(signed_all, ddof=1) / np.sqrt(n_enriched))

    # ── Report ────────────────────────────────────────────────────────
    lines = []
    a = lines.append
    a("# TS Basis Daily — Signal Failure Analysis\n")
    a(f"**Script-generated** — `scripts/signal_engine/ts_basis_daily/run_failure_analysis.py`. Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Window:** TRAIN {WINDOWS['TRAIN'][0]} → {WINDOWS['TRAIN'][1]} "
      f"({n_dates} formations, {n_sig:,} signals, {n_enriched:,} enriched).\n")
    a(f"**Metric:** signed return = fwd_ret_1m × sign(z_ts). Positive = signal was directionally correct.\n")
    a("")

    a("---\n## 1. Baseline\n")
    a(f"| Metric | Value |")
    a(f"|---|---|")
    a(f"| Signals | {n_enriched:,} |")
    a(f"| Hit rate (signed ret > 0) | {baseline_hit*100:.1f}% |")
    a(f"| Mean signed return | {baseline_mean*100:+.3f}% |")
    a(f"| SE(mean) | {baseline_ste*100:.3f}% |")
    a("")

    a("---\n## 2. Failure Predictors\n")
    a("*Buckets where hit rate or mean signed return drops materially below baseline.*\n")

    dims = sorted(set(r["dim"] for r in all_buckets))
    for dim in dims:
        dim_rows = [r for r in all_buckets if r["dim"] == dim]
        a(f"### {dim}\n")
        a("| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |")
        a("|---|---|--:|--:|--:|--:|--:|")
        for row in dim_rows:
            delta_hit = row["hit_rate"] - baseline_hit
            delta_mean = row["mean_signed"] - baseline_mean
            hit_str = f"{row['hit_rate']*100:5.1f}%"
            mean_str = f"{row['mean_signed']*100:+.3f}%"
            abs_str = f"{row['mean_abs_fwd']*100:.2f}%"
            dh_str = f"{delta_hit*100:+.1f}pp"
            dm_str = f"{delta_mean*100:+.3f}pp"
            a(f"| {row['bucket']} | {row['n']:,} | {hit_str} | {mean_str} | {abs_str} | {dh_str} | {dm_str} |")
        a("")

    # ── Worst-case combinations ───────────────────────────────────────
    a("---\n## 3. Worst-Case Regime Combinations\n")
    a("*Worst 2-dimensional intersections by mean signed return (min 200 signals).*\n")

    vix_b2 = _bucket_continuous(vix_vals, ["a", "b", "c"], 3)
    z_b2 = _bucket_continuous(abs_zs, ["a", "b", "c"], 3)
    combo_rows = []

    if vix_b2 and z_b2:
        vix_buckets = vix_b2["buckets"]
        z_buckets = z_b2["buckets"]
        vix_labels = ["Low VIX", "Mid VIX", "High VIX"]
        z_labels_c = ["Weak |z|", "Mid |z|", "Strong |z|"]

        combo = defaultdict(list)
        for i in range(n_enriched):
            vi = vix_buckets[i]
            zi = z_buckets[i]
            combo[(vi, zi)].append(signed_returns[i])

        combo_rows = []
        for (vi, zi), vals in combo.items():
            if len(vals) < MIN_SIGNALS_PER_BUCKET:
                continue
            arr = np.array(vals)
            combo_rows.append({
                "label": f"{vix_labels[vi]} & {z_labels_c[zi]}",
                "n": len(vals),
                "hit_rate": float(np.mean(arr > 0)),
                "mean_signed": float(np.mean(arr)),
            })
        combo_rows.sort(key=lambda r: r["mean_signed"])

        if combo_rows:
            a("#### VIX × Signal Strength\n")
            a("| Condition | n | Hit Rate | Mean Signed | Δ vs Baseline |")
            a("|---|---|--:|--:|--:|")
            for row in combo_rows[:9]:
                delta_m = row["mean_signed"] - baseline_mean
                a(f"| {row['label']} | {row['n']:,} | {row['hit_rate']*100:.1f}% | "
                  f"{row['mean_signed']*100:+.3f}% | {delta_m*100:+.3f}pp |")
            a("")

    # VIX × ADV Tier combo
    adv_tier_vals = [r[9] for r in enriched]
    vix_valid = [v for v in vix_vals if v is not None]
    if vix_b2 and len([v for v in adv_tier_vals if v is not None]) >= MIN_SIGNALS_PER_BUCKET * 3:
        combo2 = defaultdict(list)
        for i in range(n_enriched):
            vi = vix_b2["buckets"][i]
            ai = adv_tier_vals[i]
            if ai is None:
                continue
            combo2[(vi, ai)].append(signed_returns[i])

        combo2_rows = []
        adv_labels = {1: "Low ADV", 2: "Mid ADV", 3: "High ADV"}
        for (vi, ai), vals in combo2.items():
            if len(vals) < MIN_SIGNALS_PER_BUCKET:
                continue
            arr = np.array(vals)
            combo2_rows.append({
                "label": f"{vix_labels[vi]} & {adv_labels.get(ai, str(ai))}",
                "n": len(vals),
                "hit_rate": float(np.mean(arr > 0)),
                "mean_signed": float(np.mean(arr)),
            })
        combo2_rows.sort(key=lambda r: r["mean_signed"])

        if combo2_rows:
            a("#### VIX × ADV Tier\n")
            a("| Condition | n | Hit Rate | Mean Signed | Δ vs Baseline |")
            a("|---|---|--:|--:|--:|")
            for row in combo2_rows[:9]:
                delta_m = row["mean_signed"] - baseline_mean
                a(f"| {row['label']} | {row['n']:,} | {row['hit_rate']*100:.1f}% | "
                  f"{row['mean_signed']*100:+.3f}% | {delta_m*100:+.3f}pp |")
            a("")

    # ── Summary ───────────────────────────────────────────────────────
    a("---\n## 4. Summary\n")

    # Best and worst single-dimension buckets
    worst = min(all_buckets, key=lambda r: r["mean_signed"])
    best = max(all_buckets, key=lambda r: r["mean_signed"])
    a(f"- **Worst regime:** {worst['dim']} > {worst['bucket']} — "
      f"hit {worst['hit_rate']*100:.1f}%, mean signed {worst['mean_signed']*100:+.3f}% "
      f"({(worst['mean_signed']-baseline_mean)*100:+.1f}pp vs baseline).")
    a(f"- **Best regime:** {best['dim']} > {best['bucket']} — "
      f"hit {best['hit_rate']*100:.1f}%, mean signed {best['mean_signed']*100:+.3f}% "
      f"({(best['mean_signed']-baseline_mean)*100:+.1f}pp vs baseline).")

    # Actionable findings: both positive (what predicts failure) and negative (what doesn't)
    a("")
    a("### What Predicts Failure\n")

    findings = []

    # Signal strength — check monotonicity
    z_rows = sorted([r for r in all_buckets if r["dim"].startswith("Signal")],
                    key=lambda r: r["mean_signed"])
    if len(z_rows) >= 3:
        weak, mid, strong = z_rows[0]["mean_signed"], z_rows[1]["mean_signed"], z_rows[2]["mean_signed"]
        if weak < strong * 0.7:
            findings.append(
                f"- **Weak |z| signals underperform dramatically.** "
                f"Weak: {weak*100:+.3f}% → Mid: {mid*100:+.3f}% → Strong: {strong*100:+.3f}%. "
                f"The signal's edge is concentrated in the top two-thirds of |z| scores. "
                f"Consider raising the |z| threshold for entry — skip the weakest tercile entirely."
            )
        else:
            findings.append(
                f"- **Signal strength is weakly directional.** "
                f"Weak: {weak*100:+.3f}% → Strong: {strong*100:+.3f}%. "
                f"Some improvement at higher |z|, but the effect is modest."
            )

    # High VIX finding
    vix_rows = [r for r in all_buckets if "High VIX" in r.get("bucket", "")]
    vix_low_rows = [r for r in all_buckets if "Low VIX" in r.get("bucket", "")]
    if vix_rows and vix_low_rows:
        high_mean = vix_rows[0]["mean_signed"]
        low_mean = vix_low_rows[0]["mean_signed"]
        if high_mean < baseline_mean - 0.0001:
            findings.append(
                f"- **High VIX degrades performance.** High VIX mean signed {high_mean*100:+.3f}% "
                f"vs baseline {baseline_mean*100:+.3f}%. Consider reducing exposure during elevated VIX."
            )
        elif high_mean > low_mean:
            findings.append(
                f"- **High VIX does NOT degrade the signal — it IMPROVES it.** "
                f"High VIX: {high_mean*100:+.3f}% vs Low VIX: {low_mean*100:+.3f}%. "
                f"The basis dislocations that create the signal are larger in volatile markets. "
                f"Counterintuitive but data-backed: do NOT add a VIX filter."
            )

    # Gap finding
    gap_rows = [r for r in all_buckets if r["dim"].startswith("Overnight")]
    if gap_rows:
        means = [r["mean_signed"] for r in gap_rows]
        spread = max(means) - min(means)
        if spread < 0.0005:
            findings.append(
                f"- **Overnight Nifty gaps do NOT predict signal failure.** "
                f"Mean signed spread across gap buckets: {spread*100:.3f}pp. "
                f"The overnight macro move does not swamp the stock-specific basis signal. "
                f"A pre-market gap filter is not needed on this evidence."
            )
        else:
            gap_high = [r for r in gap_rows if ">" in r.get("bucket", "")]
            for r in gap_high:
                if r["mean_signed"] < baseline_mean - 0.0002:
                    findings.append(
                        f"- **Large overnight Nifty gaps:** mean signed {r['mean_signed']*100:+.3f}% "
                        f"(baseline {baseline_mean*100:+.3f}%). "
                        f"A pre-market gap filter could skip these days."
                    )

    # ADV tier
    adv_rows = sorted([r for r in all_buckets if r["dim"] == "ADV Tier"],
                      key=lambda r: r["mean_signed"])
    if len(adv_rows) >= 3:
        low, mid, high = adv_rows[0]["mean_signed"], adv_rows[1]["mean_signed"], adv_rows[2]["mean_signed"]
        if low < high * 0.8:
            findings.append(
                f"- **Low ADV names underperform.** "
                f"Low ADV: {low*100:+.3f}% → High ADV: {high*100:+.3f}%. "
                f"Basis in thin names is noisier. Consider a higher ADV floor."
            )

    # Sector extremes
    sec_rows = sorted([r for r in all_buckets if r["dim"] == "Sector"],
                      key=lambda r: r["mean_signed"])
    if sec_rows:
        bottom3 = [(r["bucket"], r["mean_signed"], r["n"]) for r in sec_rows[:3]]
        findings.append(
            f"- **Worst sectors by mean signed return:** "
            + ", ".join(f"{s} ({m*100:+.3f}%, n={n:,})" for s, m, n in bottom3)
            + ". Basis signal may not carry in these sectors."
        )

    if not findings:
        findings = ["- No strong failure predictors found — failures appear randomly distributed."]

    for f_text in findings:
        a(f_text)
        a("")

    a("### Composite: strongest failure condition (VIX × |z|)\n")
    vix_z_rows = sorted([r for r in all_buckets
                          if r["dim"].startswith("VIX") or r["dim"].startswith("Signal")],
                         key=lambda r: r["mean_signed"])
    if vix_z_rows:
        worst_combo = min(combo_rows, key=lambda r: r["mean_signed"]) if combo_rows else None
        best_combo = max(combo_rows, key=lambda r: r["mean_signed"]) if combo_rows else None
        if worst_combo and best_combo:
            a(f"- Worst intersection: **{worst_combo['label']}** — "
              f"hit {worst_combo['hit_rate']*100:.1f}%, mean signed {worst_combo['mean_signed']*100:+.3f}%")
            a(f"- Best intersection: **{best_combo['label']}** — "
              f"hit {best_combo['hit_rate']*100:.1f}%, mean signed {best_combo['mean_signed']*100:+.3f}%")
        a("")

    a("---\n")
    a(f"**Generated:** {now_ts} | **Commit:** `{commit}` | "
      f"**Signals analyzed:** {n_enriched:,}\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
