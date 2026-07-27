"""TS Basis Daily — Net-of-Fee Long/Short Spread.

Mirror of TS Basis run_net_spread.py for daily cadence.
Annualization factor: 252 (trading days/year) instead of 12.

Output: docs/reports/TS_BASIS_DAILY_NET_SPREAD_REPORT.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import futures_fees as _calc_fees

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_NET_SPREAD_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_NET_SPREAD_SNAPSHOT.json"

WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

GROSS_EXPOSURE = 10_000_000.0
HALF = GROSS_EXPOSURE / 2.0
QUINTILE_FRAC = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25
SLIPPAGE_BP = 5
ADV_WINDOW = 20
ADV_MIN_OBS = 10
PPY = 252.0  # trading days per year


@dataclass
class PortfolioState:
    long_positions: dict[str, float] = field(default_factory=dict)
    short_positions: dict[str, float] = field(default_factory=dict)


def _load_adva(con, fdate, underlyings):
    if not underlyings:
        return {}
    ul = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (SELECT underlying, val_in_lakh, ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
              FROM fut.futures_bhavcopy WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{ADV_WINDOW+10} days'
              AND underlying IN ({ul}) AND inst_type = 'FUTSTK')
        WHERE rn <= {ADV_WINDOW} AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= {ADV_MIN_OBS}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _compute_targets(filt, adva):
    n = len(filt)
    nq = max(1, round(QUINTILE_FRAC * n))
    sorted_by_z = sorted(filt, key=lambda r: r[1])
    long_set = {r[0] for r in sorted_by_z[-nq:]}
    short_set = {r[0] for r in sorted_by_z[:nq]}
    longs = {}
    shorts = {}
    for in_set, side_map in [(long_set, longs), (short_set, shorts)]:
        n_leg = len(in_set)
        if n_leg == 0:
            continue
        cap_each = HALF / n_leg
        for u in in_set:
            max_pos = adva.get(u, float('inf')) * ADV_CAP_FRAC
            side_map[u] = min(cap_each, max_pos if max_pos > 0 else cap_each)
        total = sum(side_map.values())
        if total > 0:
            scale = HALF / total
            side_map.update({u: v * scale for u, v in side_map.items()})
    return longs, shorts


def _simulate(label, lo, hi, con):
    sig_rows = con.execute(f"""
        SELECT formation_date, underlying, z_ts, fwd_ret_1m, liquid
        FROM sig.signals WHERE formation_date >= DATE '{lo}'
        AND formation_date <= DATE '{hi}' AND z_ts IS NOT NULL
        AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
        ORDER BY formation_date, underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fdate, u, z, fr, liq in sig_rows:
        by_date[fdate].append((u, float(z), float(fr)))

    formation_dates = sorted(by_date.keys())
    state = PortfolioState()
    gross_returns, net_returns, turnovers = [], [], []
    total_fees, total_slippage = 0.0, 0.0
    fee_breakdown = {"brokerage": 0.0, "stt": 0.0, "exchange_txn": 0.0,
                     "sebi_fee": 0.0, "stamp_duty": 0.0, "gst": 0.0}
    prev_fwd = {}
    is_first = True

    for fdate in formation_dates:
        rows = by_date[fdate]
        ulist = [r[0] for r in rows]
        adva = _load_adva(con, fdate, ulist)
        filt = [(u, z) for u, z, _ in rows if u in adva]
        if len(filt) < 5:
            prev_fwd = {r[0]: r[2] for r in rows}
            is_first = False
            continue

        V_long = max(sum(state.long_positions.values()), 1e-6)
        V_short = max(sum(state.short_positions.values()), 1e-6)
        period_gross = 0.0
        if not is_first and prev_fwd:
            gl = sum(cap * prev_fwd.get(u, 0.0) for u, cap in state.long_positions.items())
            gs = sum(cap * prev_fwd.get(u, 0.0) for u, cap in state.short_positions.items())
            period_gross = gl / V_long - gs / V_short
            gross_returns.append(period_gross)

        longs_t, shorts_t = _compute_targets(filt, adva)
        all_w = list(longs_t.values()) + list(shorts_t.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND_SIGMA * sigma_w

        reb_l, reb_s = {}, {}
        for u, t in longs_t.items():
            c = state.long_positions.get(u, 0.0)
            reb_l[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in shorts_t.items():
            c = state.short_positions.get(u, 0.0)
            reb_s[u] = t if abs(t - c) >= band or c == 0 else c

        abs_d = 0.0
        all_u = (set(state.long_positions) | set(state.short_positions) | set(reb_l) | set(reb_s))
        for u in all_u:
            ol = state.long_positions.get(u, 0.0); nl = reb_l.get(u, 0.0)
            os = state.short_positions.get(u, 0.0); ns = reb_s.get(u, 0.0)
            abs_d += abs(nl - ol) + abs(ns - os)
        turnovers.append(abs_d / max(V_long + V_short, 1.0))

        period_fee, period_slippage = 0.0, 0.0
        for side_positions, reb in [(state.long_positions, reb_l), (state.short_positions, reb_s)]:
            for u in set(side_positions) | set(reb):
                old_c = side_positions.get(u, 0.0)
                new_c = reb.get(u, 0.0)
                delta = new_c - old_c
                if abs(delta) < 1e-6:
                    continue
                if side_positions is state.long_positions:
                    side = "BUY" if delta > 0 else "SELL"
                else:
                    side = "SELL" if delta > 0 else "BUY"
                tv = abs(delta)
                f = _calc_fees(side=side, trade_value=tv, trade_date=fdate)
                period_fee += f.total
                period_slippage += (SLIPPAGE_BP / 10000) * tv
                for k in fee_breakdown:
                    fee_breakdown[k] += getattr(f, k)

        total_fees += period_fee
        total_slippage += period_slippage
        if not is_first:
            net_returns.append(period_gross - (period_fee + period_slippage) / GROSS_EXPOSURE)
        state.long_positions = reb_l
        state.short_positions = reb_s
        prev_fwd = {r[0]: r[2] for r in rows}
        is_first = False

    if not gross_returns:
        return {"error": "no valid periods"}

    g_arr = np.array(gross_returns)
    n_arr = np.array(net_returns)
    to_arr = np.array(turnovers[1:])
    periods = len(g_arr)
    ann_gross = float(np.prod(1 + g_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    ann_net = float(np.prod(1 + n_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0

    ic_vals = []
    for fdate in formation_dates:
        rows = by_date[fdate]
        zs = np.array([r[1] for r in rows if r[2] is not None], float)
        frs = np.array([r[2] for r in rows if r[2] is not None], float)
        present = np.isfinite(zs) & np.isfinite(frs)
        if present.sum() < 5:
            continue
        sr = spearmanr(zs[present], frs[present]).correlation
        if not np.isnan(sr):
            ic_vals.append(float(sr))

    ic_arr = np.array(ic_vals)
    mean_ic = float(np.mean(ic_arr)) if len(ic_arr) > 0 else 0.0
    sd_ic = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0

    return {
        "label": label, "formations": len(formation_dates), "return_periods": periods,
        "ann_gross": ann_gross, "ann_net": ann_net,
        "fee_drag_bp": (ann_gross - ann_net) * 10000.0,
        "total_fees": total_fees, "total_slippage": total_slippage,
        "avg_turnover": avg_to, "fee_breakdown": dict(fee_breakdown),
        "n_ic": len(ic_arr), "mean_ic": mean_ic, "sd_ic": sd_ic,
        "gross_spreads": [float(x) for x in g_arr],
        "net_spreads": [float(x) for x in n_arr],
    }


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    results = {}
    for label, (lo, hi) in WINDOWS.items():
        print(f"  {label}: {lo} -> {hi}")
        results[label] = _simulate(label, lo, hi, con)
        r = results[label]
        if "error" in r:
            print(f"    ERROR: {r['error']}")
        else:
            print(f"    n={r['formations']} IC={r['mean_ic']:+.4f} gross={r['ann_gross']*100:.2f}% net={r['ann_net']*100:.2f}% drag={r['fee_drag_bp']:.0f}bp to={r['avg_turnover']:.3f}")

    con.close()

    lines = []
    a = lines.append
    a("# TS Basis Daily — Net-of-Fee Long/Short Spread\n")
    a(f"**Script-generated** — `scripts/signal_engine/ts_basis_daily/run_net_spread.py`. Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Sign:** positive (long high z_ts, short low z_ts).\n")
    a(f"**Cadence:** daily ({PPY:.0f} formations/year).\n")
    a(f"**Construction:** z_ts = (basis_now - trailing_mean) / trailing_std, "
      f"lookback=504d, min_obs=12, winsorize +/-3σ, equal-weight Q5/Q1, "
      f"ADV-capped 10%, {BAND_SIGMA}σ band.\n")
    a("")

    a("---\n## 1. Rank-IC\n")
    a("| Window | n | Mean IC | SD(IC) |")
    a("|---|--:|--:|--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        r = results.get(label, {})
        if isinstance(r, dict) and "mean_ic" in r:
            a(f"| {label} | {r['n_ic']} | {r['mean_ic']:+.4f} | {r['sd_ic']:.4f} |")
    a("")

    a("---\n## 2. Net-of-Fee Spread\n")
    a("| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Periods |")
    a("|---|:--:|--:|--:|--:|--:|--:|--:|")
    all_pass = True
    for label in ["TRAIN", "HOLDOUT"]:
        r = results.get(label, {})
        if "error" in r:
            a(f"| {label} | ERROR | — | — | — | — | — | {r.get('error', '')} |")
            all_pass = False
        else:
            net_ok = r["ann_net"] > 0
            a(f"| **{label}** | **{'PASS' if net_ok else 'FAIL'}** | "
              f"{r['ann_gross']*100:+.2f}% | {r['ann_net']*100:+.2f}% | "
              f"{r['fee_drag_bp']:.0f} bp | {r['total_slippage']/max(r['formations'],1):.0f} Rs/d | "
              f"{r['avg_turnover']:.3f} | {r['formations']} |")
            if not net_ok:
                all_pass = False
    a("")

    a("---\n## 3. Fee Breakdown (TRAIN)\n")
    tr = results.get("TRAIN", {})
    if isinstance(tr, dict) and "fee_breakdown" in tr:
        fb = tr["fee_breakdown"]
        total_fee = sum(fb.values())
        a("| Component | Total (Rs) | Share |")
        a("|---|---:|--:|")
        for comp in ["brokerage", "stt", "exchange_txn", "sebi_fee", "stamp_duty", "gst"]:
            val = fb.get(comp, 0.0)
            a(f"| {comp} | {val:,.0f} | {val/total_fee*100:.1f}% |")
        a(f"| **Total fees** | **{total_fee:,.0f}** | 100.0% |")
    a("")

    a("---\n## 4. Gate\n")
    a("| Window | Gross ann | Net ann | Net > 0? |")
    a("|---|--:|--:|:--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        r = results.get(label, {})
        if "error" in r:
            a(f"| {label} | — | — | ERROR |")
        else:
            net_ok = r["ann_net"] > 0
            a(f"| {label} | {r['ann_gross']*100:+.2f}% | {r['ann_net']*100:+.2f}% | {'PASS' if net_ok else '**FAIL**'} |")
    a("")
    if all_pass:
        a("**NET-SPREAD GATE: PASS** — Net > 0 on both TRAIN and HOLDOUT.\n")
    else:
        a("**GATE VERDICT: FAIL** — Net ≤ 0 on at least one window. STOP.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    snapshot = {
        "commit": commit, "generated": now_ts,
        "fee_model": {"source": "core/execution/futures/futures_fees.py",
                       "slippage_bp": SLIPPAGE_BP, "gross_exposure": GROSS_EXPOSURE,
                       "annualization_factor": PPY},
        "results": {k: {kk: vv for kk, vv in v.items() if kk not in ("gross_spreads", "net_spreads")}
                     for k, v in results.items() if isinstance(v, dict)},
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"Gate: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
