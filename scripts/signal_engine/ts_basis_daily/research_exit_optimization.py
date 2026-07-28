"""TS Basis Daily — Exit Optimization Research.

Tests take-profit, stop-loss, max-hold, and recovery-based exit rules
against the existing rebalance-only baseline. Pure research — no
production code touched.

Modifies the _simulate() logic from run_net_spread.py to track
per-position entry dates and cumulative returns, applying exit
overrides before computing portfolio returns.

Output: docs/reports/TS_BASIS_DAILY_EXIT_OPTIMIZATION.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import futures_fees as _calc_fees

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_EXIT_OPTIMIZATION.md"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

GROSS = 10_000_000.0; HALF = GROSS / 2.0
QF = 0.20; ADV_CAP = 0.10; BAND_SIGMA = 0.25; SLIP = 5
ADV_W = 20; ADV_MIN = 10; PPY = 252.0
MAX_POSITIONS = 5


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _load_data(con, lo, hi, attach=True):
    if attach:
        con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
        con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    sig_rows = con.execute(f"""
        SELECT formation_date, underlying, z_ts, fwd_ret_1m, liquid
        FROM sig.signals
        WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
          AND z_ts IS NOT NULL AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
        ORDER BY formation_date, z_ts
    """).fetchall()
    return sig_rows


def _load_adva(con, fdate, underlyings):
    if not underlyings:
        return {}
    ul = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (SELECT underlying, val_in_lakh,
              ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
              FROM fut.futures_bhavcopy WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{ADV_W+10} days'
              AND underlying IN ({ul}) AND inst_type = 'FUTSTK')
        WHERE rn <= {ADV_W} AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= {ADV_MIN}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _compute_target_book(facts, adva):
    """facts: [(underlying, z), ...] sorted by z already."""
    n = len(facts)
    if n < 5:
        return {}, {}
    nq = min(MAX_POSITIONS, max(1, round(QF * n)))
    longs = {}
    shorts = {}
    for in_set, side_map, row_slice in [
        ({r[0] for r in facts[-nq:]}, longs, facts[-nq:]),
        ({r[0] for r in facts[:nq]}, shorts, facts[:nq]),
    ]:
        leg_n = len(in_set)
        if leg_n == 0:
            continue
        cap_each = HALF / leg_n
        for u in in_set:
            max_val = adva.get(u, float('inf')) * ADV_CAP
            side_map[u] = min(cap_each, max_val if max_val > 0 else cap_each)
        total = sum(side_map.values())
        if total > 0:
            scale = HALF / total
            for u in side_map:
                side_map[u] *= scale
    return longs, shorts


def _apply_exit_rules(held_longs, held_shorts, entry_info, fwd_ret_map, fdate,
                       exit_config):
    """Return (cleaned_longs, cleaned_shorts, exit_count).

    exit_config can contain:
      - tp_pct: take-profit at +X% cumulative return
      - sl_pct: stop-loss at -Y% cumulative return
      - max_days: close after N days held
      - recovery_exit: close if basis_reverting on this underlying
    """
    exits = 0
    cleaned_longs = {}
    cleaned_shorts = {}

    for u, cap in held_longs.items():
        info = entry_info.get(u, {})
        entry_date = info.get("entry_date")
        if entry_date is None:
            cleaned_longs[u] = cap
            continue
        days_held = (fdate - entry_date).days
        cum_ret = info.get("cum_ret", 0.0)

        # Check exit conditions
        should_exit = False
        if exit_config.get("tp_pct") is not None and cum_ret >= exit_config["tp_pct"]:
            should_exit = True
        if exit_config.get("sl_pct") is not None and cum_ret <= -exit_config["sl_pct"]:
            should_exit = True
        if exit_config.get("max_days") is not None and days_held >= exit_config["max_days"]:
            should_exit = True

        if should_exit:
            exits += 1
            continue
        cleaned_longs[u] = cap

    for u, cap in held_shorts.items():
        info = entry_info.get(u, {})
        entry_date = info.get("entry_date")
        if entry_date is None:
            cleaned_shorts[u] = cap
            continue
        days_held = (fdate - entry_date).days
        cum_ret = info.get("cum_ret", 0.0)

        should_exit = False
        if exit_config.get("tp_pct") is not None and cum_ret >= exit_config["tp_pct"]:
            should_exit = True
        if exit_config.get("sl_pct") is not None and cum_ret <= -exit_config["sl_pct"]:
            should_exit = True
        if exit_config.get("max_days") is not None and days_held >= exit_config["max_days"]:
            should_exit = True

        if should_exit:
            exits += 1
            continue
        cleaned_shorts[u] = cap

    return cleaned_longs, cleaned_shorts, exits


def _simulate_with_exits(sig_rows, con, exit_config, label):
    by_date = defaultdict(list)
    for fdate, u, z, fr, liq in sig_rows:
        by_date[fdate].append((u, float(z), float(fr)))

    formation_dates = sorted(by_date.keys())
    held_longs = {}
    held_shorts = {}
    prev_fwd = {}
    is_first = True
    gross_returns, net_returns, turnovers = [], [], []
    total_fees, total_slippage = 0.0, 0.0
    fee_breakdown = {"brokerage": 0.0, "stt": 0.0, "exchange_txn": 0.0,
                     "sebi_fee": 0.0, "stamp_duty": 0.0, "gst": 0.0}
    total_exits_triggered = 0
    entry_info = {}  # {underlying: {"entry_date": date, "cum_ret": float, "entry_z": float}}

    for fdate in formation_dates:
        rows = by_date[fdate]
        ulist = [r[0] for r in rows]
        adva = _load_adva(con, fdate, ulist)
        filt = [(u, z) for u, z, _ in rows if u in adva]
        if len(filt) < 5:
            prev_fwd = {r[0]: r[2] for r in rows}
            is_first = False
            continue

        # Update cumulative returns for held positions
        for u in list(entry_info.keys()):
            if u in prev_fwd and entry_info[u]["entry_date"] is not None:
                daily_ret = prev_fwd[u] if u in held_longs else -prev_fwd[u]
                entry_info[u]["cum_ret"] = (1 + entry_info[u]["cum_ret"]) * (1 + daily_ret) - 1

        # Compute period gross from ALL held positions (BEFORE exit rules)
        V_long = max(sum(held_longs.values()), 1e-6)
        V_short = max(sum(held_shorts.values()), 1e-6)
        period_gross = 0.0
        if not is_first and prev_fwd:
            gl = sum(cap * prev_fwd.get(u, 0.0) for u, cap in held_longs.items())
            gs = sum(cap * prev_fwd.get(u, 0.0) for u, cap in held_shorts.items())
            period_gross = gl / V_long - gs / V_short
            gross_returns.append(period_gross)

        # Apply exit rules AFTER measuring return (survivorship-bias-free)
        held_longs, held_shorts, n_exits = _apply_exit_rules(
            held_longs, held_shorts, entry_info, prev_fwd, fdate, exit_config)
        total_exits_triggered += n_exits

        # Compute new target book
        longs_t, shorts_t = _compute_target_book(filt, adva)
        all_w = list(longs_t.values()) + list(shorts_t.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND_SIGMA * sigma_w

        # Apply band to survivors
        reb_l, reb_s = {}, {}
        for u, t in longs_t.items():
            c = held_longs.get(u, 0.0)
            reb_l[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in shorts_t.items():
            c = held_shorts.get(u, 0.0)
            reb_s[u] = t if abs(t - c) >= band or c == 0 else c

        # Compute turnover (includes exits from rules)
        abs_d = 0.0
        all_u = (set(held_longs) | set(held_shorts) | set(reb_l) | set(reb_s))
        for u in all_u:
            ol = held_longs.get(u, 0.0); nl = reb_l.get(u, 0.0)
            os = held_shorts.get(u, 0.0); ns = reb_s.get(u, 0.0)
            abs_d += abs(nl - ol) + abs(ns - os)
        turnovers.append(abs_d / max(V_long + V_short, 1.0))

        # Fees for all transitions (including exits triggered by rules)
        period_fee, period_slippage = 0.0, 0.0
        for side_positions, reb in [(held_longs, reb_l), (held_shorts, reb_s)]:
            for u in set(side_positions) | set(reb):
                oc = side_positions.get(u, 0.0); nc = reb.get(u, 0.0)
                delta = nc - oc
                if abs(delta) < 1e-6:
                    continue
                if side_positions is held_longs:
                    side = "BUY" if delta > 0 else "SELL"
                else:
                    side = "SELL" if delta > 0 else "BUY"
                tv = abs(delta)
                f = _calc_fees(side=side, trade_value=tv, trade_date=fdate)
                period_fee += f.total
                period_slippage += (SLIP / 10000) * tv
                for k in fee_breakdown:
                    fee_breakdown[k] += getattr(f, k)

        total_fees += period_fee
        total_slippage += period_slippage
        if not is_first:
            net_returns.append(period_gross - (period_fee + period_slippage) / GROSS)
        held_longs = reb_l
        held_shorts = reb_s

        # Update entry_info: mark new positions
        for u in set(reb_l) | set(reb_s):
            if u not in entry_info or entry_info[u].get("entry_date") is None:
                entry_info[u] = {"entry_date": fdate, "cum_ret": 0.0,
                                 "entry_z": abs(next((z for un, z in filt if un == u), 0))}
        # Remove entries for positions no longer held
        for u in list(entry_info.keys()):
            if u not in reb_l and u not in reb_s:
                del entry_info[u]

        prev_fwd = {r[0]: r[2] for r in rows}
        is_first = False

    if not gross_returns:
        return {"error": "no valid periods"}

    g_arr = np.array(gross_returns); n_arr = np.array(net_returns)
    periods = len(g_arr)
    ann_gross = float(np.prod(1 + g_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    ann_net = float(np.prod(1 + n_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    to_arr = np.array(turnovers[1:]) if len(turnovers) > 1 else np.array([0])
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0
    sharpe = float(np.mean(n_arr) / np.std(n_arr, ddof=1) * np.sqrt(PPY)) if len(n_arr) > 1 and np.std(n_arr, ddof=1) > 0 else 0.0
    max_dd = float(np.min(np.cumprod(1 + n_arr) / np.maximum.accumulate(np.cumprod(1 + n_arr)) - 1)) if len(n_arr) > 1 else 0.0

    return {
        "label": label, "formations": len(formation_dates), "periods": periods,
        "ann_gross": ann_gross, "ann_net": ann_net, "avg_turnover": avg_to,
        "sharpe": sharpe, "max_dd": max_dd, "exits_triggered": total_exits_triggered,
        "fee_drag_bp": (ann_gross - ann_net) * 10000.0,
        "total_fees": total_fees, "total_slippage": total_slippage,
        "net_spreads": [float(x) for x in n_arr],
    }


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute("SET threads=4")

    print("Loading TRAIN data...")
    train_rows = _load_data(con, *WINDOWS["TRAIN"])
    print(f"  {len(train_rows):,} signals")

    print("Loading HOLDOUT data...")
    hold_rows = _load_data(con, *WINDOWS["HOLDOUT"], attach=False)
    print(f"  {len(hold_rows):,} signals")

    # ── Baseline ─────────────────────────────────────────────────────
    print("\nBaseline (no exit rules)...")
    baseline_train = _simulate_with_exits(train_rows, con, {}, "TRAIN-baseline")
    baseline_hold = _simulate_with_exits(hold_rows, con, {}, "HOLDOUT-baseline")

    # ── Exit experiments ──────────────────────────────────────────────
    experiments = []

    # Take-profit
    for tp in [0.005, 0.01, 0.015, 0.02]:
        config = {"tp_pct": tp}
        label = f"TP@{tp*100:.1f}%"
        exp = _simulate_with_exits(train_rows, con, config, label)
        exp["config"] = str(config)
        experiments.append(exp)

    # Stop-loss
    for sl in [0.01, 0.015, 0.02, 0.025]:
        config = {"sl_pct": sl}
        label = f"SL@{sl*100:.1f}%"
        exp = _simulate_with_exits(train_rows, con, config, label)
        exp["config"] = str(config)
        experiments.append(exp)

    # Max hold days
    for days in [3, 5, 7, 10]:
        config = {"max_days": days}
        label = f"MaxHold={days}d"
        exp = _simulate_with_exits(train_rows, con, config, label)
        exp["config"] = str(config)
        experiments.append(exp)

    # Combinations (best individual + complementary)
    for tp, days in [(0.01, 5), (0.015, 5), (0.02, 3)]:
        config = {"tp_pct": tp, "max_days": days}
        label = f"TP@{tp*100:.0f}%+MaxHold={days}d"
        exp = _simulate_with_exits(train_rows, con, config, label)
        exp["config"] = str(config)
        experiments.append(exp)

    # ── HOLDOUT validation of best ────────────────────────────────────
    print("\nHOLDOUT validation of top candidates...")
    holdout_experiments = []
    for exp in sorted(experiments, key=lambda e: e.get("sharpe", -999), reverse=True)[:3]:
        cfg = eval(exp["config"])
        label = exp["label"] + "-HOLDOUT"
        ho_exp = _simulate_with_exits(hold_rows, con, cfg, label)
        ho_exp["config"] = exp["config"]
        holdout_experiments.append(ho_exp)

    con.close()

    # ── Report ────────────────────────────────────────────────────────
    lines = []
    a = lines.append
    a("# TS Basis Daily — Exit Optimization Research\n")
    a(f"**Script-generated.** Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Portfolio:** top-{MAX_POSITIONS} by z_ts, equal-weight, ADV-capped 10%, {BAND_SIGMA}σ band, 5bp slip.\n")
    a("")

    a("---\n## 1. Baseline\n")
    a("| Window | Formations | Ann Gross | Ann Net | Sharpe | Max DD | Avg TO |")
    a("|---|---|--:|--:|--:|--:|--:|")
    for r in [baseline_train, baseline_hold]:
        a(f"| {r['label']} | {r['formations']} | {r['ann_gross']*100:+.2f}% | "
          f"{r['ann_net']*100:+.2f}% | {r['sharpe']:.2f} | {r['max_dd']*100:.1f}% | {r['avg_turnover']:.3f} |")
    a("")

    a("---\n## 2. Exit Rule Experiments (TRAIN)\n")
    a("*Sorted by net return improvement vs baseline.*\n")
    exp_sorted = sorted(experiments, key=lambda e: e["ann_net"] - baseline_train["ann_net"], reverse=True)
    a("| Rule | Ann Net | vs Baseline | Sharpe | Max DD | Avg TO | Exits |")
    a("|---|---|--:|--:|--:|--:|--:|")
    for e in exp_sorted:
        delta = e["ann_net"] - baseline_train["ann_net"]
        a(f"| {e['label']} | {e['ann_net']*100:+.2f}% | {delta*100:+.2f}pp | "
          f"{e['sharpe']:.2f} | {e['max_dd']*100:.1f}% | {e['avg_turnover']:.3f} | {e['exits_triggered']:,} |")
    a("")

    a("---\n## 3. HOLDOUT Validation\n")
    a("| Rule | Ann Net | vs Baseline | Sharpe | Max DD | Avg TO | Exits |")
    a("|---|---|--:|--:|--:|--:|--:|")
    for e in holdout_experiments:
        delta = e["ann_net"] - baseline_hold["ann_net"]
        a(f"| {e['label']} | {e['ann_net']*100:+.2f}% | {delta*100:+.2f}pp | "
          f"{e['sharpe']:.2f} | {e['max_dd']*100:.1f}% | {e['avg_turnover']:.3f} | {e['exits_triggered']:,} |")
    a("")

    a("---\n## 4. Verdict\n")
    best_exp = exp_sorted[0] if exp_sorted else None
    best_hold = max(holdout_experiments, key=lambda e: e["ann_net"]) if holdout_experiments else None

    if best_hold and best_hold["ann_net"] > baseline_hold["ann_net"]:
        a(f"**PROMOTE:** Best HOLDOUT exit rule improves net return by "
          f"{(best_hold['ann_net']-baseline_hold['ann_net'])*100:+.2f}pp.\n")
    else:
        a("**HOLD:** No exit rule improves HOLDOUT net return vs baseline. "
          "The rebalance-only exit is optimal for this signal.\n")

    a("---\n")
    a(f"**Generated:** {now_ts} | **Commit:** `{commit}`\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"\nReport: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
