"""Carry weekly-vs-monthly net-spread comparison.

Simulates a weekly-rebalance strategy (same construction: Q5 LONG, Q1 SHORT,
equal-weight, ADV-capped, 0.25σ band, futures fees + 5bp slippage) over the
TRAIN window and compares against the validated monthly result.

Answers: does the fresher weekly signal's edge survive ~4x fee drag?

Runs on weekly_signals.duckdb (211 neutralized TRAIN formations).
Output: docs/reports/CARRY_WEEKLY_VS_MONTHLY_REPORT.md
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import futures_fees as _calc_fees

SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "weekly_signals.duckdb"
MONTHLY_SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_WEEKLY_VS_MONTHLY_REPORT.md"

GROSS_EXPOSURE = 10_000_000.0
HALF = GROSS_EXPOSURE / 2.0
QUINTILE_FRAC = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25
SLIPPAGE_BP = 5
ADV_WINDOW = 20
ADV_MIN_OBS = 10

TRAIN_LO = date(2016, 3, 31)
TRAIN_HI = date(2020, 12, 31)


@dataclass
class PortfolioState:
    long_positions: dict[str, float] = field(default_factory=dict)
    short_positions: dict[str, float] = field(default_factory=dict)


def _load_adva(con, formation_date, underlyings):
    if not underlyings:
        return {}
    u_list = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM fut.futures_bhavcopy
            WHERE trade_date <= DATE '{formation_date}'
              AND trade_date > DATE '{formation_date}' - INTERVAL '{ADV_WINDOW+10} days'
              AND underlying IN ({u_list}) AND inst_type = 'FUTSTK'
        )
        WHERE rn <= {ADV_WINDOW} AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= {ADV_MIN_OBS}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _compute_targets(filt_facts, adva):
    """Equal-weight Q5 LONG, Q1 SHORT with ADV capping."""
    n = len(filt_facts)
    nq = max(1, round(QUINTILE_FRAC * n))
    sorted_by_z = sorted(filt_facts, key=lambda r: r[1])
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


def _simulate(label, formation_dates, by_date, fwd_ret_map, con, ppy=52.0):
    """Simulate rebalance over formation dates. ppy = periods per year
    (52 for weekly, 12 for monthly)."""
    state = PortfolioState()
    gross_returns = []
    net_returns = []
    turnovers = []
    total_fees = 0.0
    total_slippage = 0.0
    prev_fwd = {}  # fwd_ret from PREVIOUS formation, used for current period return
    is_first = True

    for fdate in formation_dates:
        rows = by_date[fdate]

        ulist = [r[0] for r in rows]
        adva = _load_adva(con, fdate, ulist)
        filt = [(u, zn) for u, zn in rows if u in adva]
        n = len(filt)
        if n < 5:
            prev_fwd = fwd_ret_map.get(fdate, {})
            is_first = False
            continue
        nq = max(1, round(QUINTILE_FRAC * n))

        V_long = max(sum(state.long_positions.values()), 1e-6)
        V_short = max(sum(state.short_positions.values()), 1e-6)

        # Gross return from prior period using PREVIOUS formation's fwd_ret
        period_gross = 0.0
        if not is_first and prev_fwd:
            gl = sum(cap * prev_fwd.get(u, 0.0) for u, cap in state.long_positions.items())
            gs = sum(cap * prev_fwd.get(u, 0.0) for u, cap in state.short_positions.items())
            period_gross = gl / V_long - gs / V_short
            gross_returns.append(period_gross)

        # Target book
        longs_t, shorts_t = _compute_targets(filt, adva)

        # No-trade band
        all_w = list(longs_t.values()) + list(shorts_t.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND_SIGMA * sigma_w

        reb_l = {}
        reb_s = {}
        for u, t in longs_t.items():
            c = state.long_positions.get(u, 0.0)
            reb_l[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in shorts_t.items():
            c = state.short_positions.get(u, 0.0)
            reb_s[u] = t if abs(t - c) >= band or c == 0 else c

        # Turnover
        abs_d = 0.0
        all_u = (set(state.long_positions) | set(state.short_positions)
                 | set(reb_l) | set(reb_s))
        for u in all_u:
            ol = state.long_positions.get(u, 0.0)
            nl = reb_l.get(u, 0.0)
            os = state.short_positions.get(u, 0.0)
            ns = reb_s.get(u, 0.0)
            abs_d += abs(nl - ol) + abs(ns - os)
        to = abs_d / max(V_long + V_short, 1.0)
        turnovers.append(to)

        # Fees
        period_fee = 0.0
        period_slippage = 0.0
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

        total_fees += period_fee
        total_slippage += period_slippage

        if not is_first:
            net_r = period_gross - (period_fee + period_slippage) / GROSS_EXPOSURE
            net_returns.append(net_r)

        state.long_positions = reb_l
        state.short_positions = reb_s
        prev_fwd = fwd_ret_map.get(fdate, {})
        is_first = False

    if not gross_returns:
        return {"error": "no valid periods"}

    gross_arr = np.array(gross_returns)
    net_arr = np.array(net_returns)
    to_arr = np.array(turnovers[1:])

    months_equiv = len(gross_arr)
    ann_gross = float(np.prod(1 + gross_arr) ** (ppy / months_equiv) - 1) if months_equiv > 0 else 0.0
    ann_net = float(np.prod(1 + net_arr) ** (ppy / months_equiv) - 1) if months_equiv > 0 else 0.0
    fee_drag_bp = (ann_gross - ann_net) * 10000.0
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0

    return {
        "label": label,
        "formations": len(formation_dates),
        "return_periods": months_equiv,
        "ann_gross": ann_gross,
        "ann_net": ann_net,
        "fee_drag_bp": fee_drag_bp,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        "avg_turnover": avg_to,
    }


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    # ── Load weekly signals ──
    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.fwd_ret_1m, s.liquid
        FROM sig.signals s
        WHERE s.z_carry_neut IS NOT NULL
          AND s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    fwd_ret_map = {}
    for fdate, u, zn, fr, liq in sig_rows:
        by_date[fdate].append((u, float(zn)))
        if fdate not in fwd_ret_map:
            fwd_ret_map[fdate] = {}
        if fr is not None:
            fwd_ret_map[fdate][u] = float(fr)

    formation_dates = sorted(by_date.keys())
    print(f"Weekly: {len(formation_dates)} formations, "
          f"{sum(len(v) for v in by_date.values()):,} signals")

    print("Simulating weekly...")
    weekly_result = _simulate("Weekly", formation_dates, by_date,
                               fwd_ret_map, con, ppy=52.0)

    # ── Simulate monthly (on original monthly signals DB, same window) ──
    print("Simulating monthly...")
    con.execute(f"ATTACH '{MONTHLY_SIG_DB}' AS sig_m (READ_ONLY)")
    m_sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.fwd_ret_1m, s.liquid
        FROM sig_m.signals s
        WHERE s.z_carry_neut IS NOT NULL
          AND s.formation_date >= DATE '{TRAIN_LO}'
          AND s.formation_date <= DATE '{TRAIN_HI}'
          AND s.fwd_ret_1m IS NOT NULL AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    m_by_date = defaultdict(list)
    m_fwd_ret = {}
    for fdate, u, zn, fr, liq in m_sig_rows:
        m_by_date[fdate].append((u, float(zn)))
        if fdate not in m_fwd_ret:
            m_fwd_ret[fdate] = {}
        m_fwd_ret[fdate][u] = float(fr)

    m_dates = sorted(m_by_date.keys())
    print(f"Monthly: {len(m_dates)} formations, "
          f"{sum(len(v) for v in m_by_date.values()):,} signals")

    monthly_result = _simulate("Monthly", m_dates, m_by_date,
                                m_fwd_ret, con, ppy=12.0)

    con.close()

    # ── Report ──
    lines = []
    a = lines.append

    a("# Carry — Weekly vs Monthly Net Spread\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/weekly_vs_monthly.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a(f"**Data:** {len(formation_dates)} weekly formations with z_carry_neut "
      f"(TRAIN {TRAIN_LO} → {TRAIN_HI}).\n")
    a(f"**Construction:** Q5 LONG, Q1 SHORT, equal-weight, ADV-capped "
      f"({ADV_CAP_FRAC*100:.0f}%), {BAND_SIGMA}σ no-trade band, "
      f"futures fees (canonical tiered STT) + {SLIPPAGE_BP}bp/side slippage.\n")
    a("")

    a("---\n")
    a("## 1. Results\n")
    a("")
    a("| Cadence | Formations | Periods | Gross ann | Net ann | Fee drag | Avg turnover |")
    a("|---|--:|--:|--:|--:|--:|--:|")
    for r in [weekly_result, monthly_result]:
        if "error" in r:
            a(f"| {r['label']} | — | — | — | — | — | {r['error']} |")
        else:
            a(f"| **{r['label']}** | {r['formations']} | {r['return_periods']} | "
              f"{r['ann_gross']*100:+.1f}% | {r['ann_net']*100:+.1f}% | "
              f"{r['fee_drag_bp']:.0f} bp | {r['avg_turnover']:.3f} |")
    a("")

    a("---\n")
    a("## 2. Fee Breakdown\n")
    a("")
    a("| Cadence | Total Fees (Rs) | Total Slippage (Rs) | Fee/period (Rs) |")
    a("|---|--:|--:|--:|")
    for r in [weekly_result, monthly_result]:
        if "error" in r:
            continue
        a(f"| {r['label']} | {r['total_fees']:,.0f} | {r['total_slippage']:,.0f} | "
          f"{r['total_fees']/r['formations']:,.0f} |")
    a("")

    # ── Comparison ──
    a("---\n")
    a("## 3. Head-to-Head\n")
    a("")
    if "error" in weekly_result or "error" in monthly_result:
        a("Insufficient data for comparison.\n")
    else:
        net_delta = (weekly_result["ann_net"] - monthly_result["ann_net"]) * 10000
        gross_delta = (weekly_result["ann_gross"] - monthly_result["ann_gross"]) * 10000
        to_ratio = weekly_result["avg_turnover"] / max(monthly_result["avg_turnover"], 0.001)
        fee_ratio = weekly_result["total_fees"] / max(monthly_result["total_fees"], 1.0)

        a(f"| Metric | Weekly | Monthly | Delta |")
        a(f"|---|--:|--:|--:|")
        a(f"| Net ann | {weekly_result['ann_net']*100:+.1f}% | "
          f"{monthly_result['ann_net']*100:+.1f}% | {net_delta:+.0f} bp |")
        a(f"| Gross ann | {weekly_result['ann_gross']*100:+.1f}% | "
          f"{monthly_result['ann_gross']*100:+.1f}% | {gross_delta:+.0f} bp |")
        a(f"| Turnover | {weekly_result['avg_turnover']:.3f} | "
          f"{monthly_result['avg_turnover']:.3f} | {to_ratio:.1f}x |")
        a(f"| Total fees | Rs {weekly_result['total_fees']:,.0f} | "
          f"Rs {monthly_result['total_fees']:,.0f} | {fee_ratio:.1f}x |")
        a("")

        a("---\n")
        a("## 4. Verdict\n")
        a("")

        w_net = weekly_result["ann_net"]
        m_net = monthly_result["ann_net"]

        if w_net > m_net:
            a(f"**Weekly BEATS monthly** by {net_delta:+.0f}bp net. "
              f"The fresher signal ({gross_delta:+.0f}bp gross edge) more than "
              f"compensates for the {fee_ratio:.1f}x higher fee drag.\n")
            a("Weekly rebalancing is recommended over monthly.\n")
        else:
            a(f"**Monthly BEATS weekly** by {abs(net_delta):.0f}bp net. "
              f"The {fee_ratio:.1f}x higher fee drag ({weekly_result['fee_drag_bp']:.0f}bp vs "
              f"{monthly_result['fee_drag_bp']:.0f}bp) consumes the fresher signal's "
              f"gross edge ({gross_delta:+.0f}bp).\n")
            a("Monthly rebalancing remains the correct cadence.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    print(f"\nReport: {REPORT}")
    if "error" not in weekly_result:
        print(f"Weekly: gross={weekly_result['ann_gross']*100:+.1f}% net={weekly_result['ann_net']*100:+.1f}% turnover={weekly_result['avg_turnover']:.3f}")
    if "error" not in monthly_result:
        print(f"Monthly: gross={monthly_result['ann_gross']*100:+.1f}% net={monthly_result['ann_net']*100:+.1f}% turnover={monthly_result['avg_turnover']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
