"""Carry net-of-fee long/short spread — precondition gate for SEALED read.

Protocol: docs/reports/CARRY_SEALED_READ_PROTOCOL.md §1
Pre-reg:  CARRY_PHASE0_PRE_REGISTRATION.md §6–§8 (construction, fees)
v2 sign:  CARRY_V2_PRE_REGISTRATION.md §1 (positive sign = long high carry)

Output:  docs/reports/CARRY_NET_SPREAD_REPORT.md
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_NET_SPREAD_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "CARRY_NET_SPREAD_SNAPSHOT.json"

# ── Windows ──
WINDOWS = {
    "TRAIN":   (date(2016, 3, 31), date(2020, 12, 31)),
    "HOLDOUT": (date(2021, 1,  1), date(2022, 12, 31)),
}

# ── Fee model (era-accurate, pre-2023-04 — no tier switching) ──
STT_RATE = 0.00010          # 0.0100% SELL side only (pre-2023-04)
EXCHANGE_TXN_RATE = 0.000021  # 0.0021% NSE derivatives txn charge (both legs)
SEBI_FEE_RATE = 0.000001      # 0.0001% Rs 10/crore (both legs)
BROKERAGE_PER_ORDER = 20.0    # Rs 20 flat per order (discount broker futures)
SLIPPAGE_BP = 5               # 5 bp per side (modeling choice, fixed)

# Stamp duty era boundaries
STAMP_POST_2020_07 = 0.00002  # 0.002% BUY side (post-2020-07-01)
STAMP_PRE_2020_07  = 0.0001   # 0.01% BUY side (pre-2020-07-01, Maharashtra proxy)

# GST era boundaries (post-2017-07-01: 18%)
GST_RATE = 0.18

# ── Portfolio ──
GROSS_EXPOSURE = 10_000_000.0  # Rs 1 Cr fixed gross
QUINTILE = 0.20
ADV_CAP_FRAC = 0.10            # max position <= 10% of 20-day ADV
BAND_SIGMA = 0.25              # no-trade band in sigma of target weights
ADV_WINDOW = 20                # trailing trading days for ADV
ADV_MIN_OBS = 10               # minimum ADV observations for a name to be eligible


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _stamp_duty_rate(trade_date: date) -> float:
    return STAMP_POST_2020_07 if trade_date >= date(2020, 7, 1) else STAMP_PRE_2020_07


def _leg_fees(*, side: str, trade_value: float, trade_date: date) -> dict:
    """Compute one-leg futures fees. Returns dict of components + total."""
    stamp = trade_value * _stamp_duty_rate(trade_date) if side == "BUY" else 0.0
    stt = trade_value * STT_RATE if side == "SELL" else 0.0
    exchange_txn = trade_value * EXCHANGE_TXN_RATE
    sebi_fee = trade_value * SEBI_FEE_RATE
    gst_base = BROKERAGE_PER_ORDER + exchange_txn + sebi_fee
    gst = GST_RATE * gst_base
    return {
        "brokerage": BROKERAGE_PER_ORDER,
        "stt": stt,
        "exchange_txn": exchange_txn,
        "sebi_fee": sebi_fee,
        "stamp_duty": stamp,
        "gst": gst,
        "total": BROKERAGE_PER_ORDER + stt + exchange_txn + sebi_fee + stamp + gst,
    }


def _load_adva(con: duckdb.DuckDBPyConnection, formation_date: date,
               underlyings: list[str]) -> dict[str, float]:
    """Trailing 20-day average daily value (Rs) per underlying."""
    result = {}
    # Batch query
    u_list = ", ".join(f"'{u}'" for u in underlyings)
    if not u_list:
        return result
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0 AS adv_rs
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM fut.futures_bhavcopy
            WHERE trade_date <= DATE '{formation_date}'
              AND trade_date > DATE '{formation_date}' - INTERVAL '{ADV_WINDOW+10} days'
              AND underlying IN ({u_list})
        )
        WHERE rn <= {ADV_WINDOW}
          AND val_in_lakh IS NOT NULL
        GROUP BY underlying
        HAVING COUNT(*) >= {ADV_MIN_OBS}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


@dataclass
class PortfolioState:
    """Running portfolio state across rebalances."""
    long_positions: dict[str, float] = field(default_factory=dict)    # name -> capital (Rs)
    short_positions: dict[str, float] = field(default_factory=dict)

    def long_total(self) -> float:
        return sum(self.long_positions.values())

    def short_total(self) -> float:
        return sum(self.short_positions.values())

    def all_held(self) -> set[str]:
        return set(self.long_positions) | set(self.short_positions)


def _compute_targets(z_weighted: bool, rows: list[tuple],
                     adva: dict[str, float], n_quintile: int) -> tuple[dict[str, float],
                                                                          dict[str, float]]:
    """Compute target long/short positions (capital Rs) from signal rows.

    rows: list of (underlying, z_carry_neut, fwd_ret_1m)
    Returns: (long_targets: {name: capital}, short_targets: {name: capital})
    """
    sorted_rows = sorted(rows, key=lambda r: r[1])  # ascending z
    long_set = {r[0] for r in sorted_rows[-n_quintile:]}   # highest z → long
    short_set = {r[0] for r in sorted_rows[:n_quintile]}    # lowest z → short

    # z-weighted: weight ∝ |z| within each leg
    if z_weighted:
        long_entries = [(r[0], r[1]) for r in sorted_rows if r[0] in long_set]
        short_entries = [(r[0], r[1]) for r in sorted_rows if r[0] in short_set]
        long_zs = np.array([abs(z) for _, z in long_entries])
        short_zs = np.array([abs(z) for _, z in short_entries])
        long_weights = long_zs / long_zs.sum() if long_zs.sum() > 0 else np.ones(len(long_zs)) / len(long_zs)
        short_weights = short_zs / short_zs.sum() if short_zs.sum() > 0 else np.ones(len(short_zs)) / len(short_zs)
    else:
        n_long = len(long_set)
        n_short = len(short_set)
        long_entries = [(u, 1.0) for u in long_set]
        short_entries = [(u, 1.0) for u in short_set]
        long_weights = np.ones(n_long) / n_long
        short_weights = np.ones(n_short) / n_short

    half_gross = GROSS_EXPOSURE / 2.0
    long_raw = {}
    for (u, _), w in zip(long_entries, long_weights):
        long_raw[u] = half_gross * w

    short_raw = {}
    for (u, _), w in zip(short_entries, short_weights):
        short_raw[u] = half_gross * w

    # ADV cap: max position <= ADV_CAP_FRAC * 20-day ADV
    for side_map in [long_raw, short_raw]:
        for u in list(side_map.keys()):
            max_pos = adva.get(u, 0.0) * ADV_CAP_FRAC
            if max_pos > 0 and side_map[u] > max_pos:
                side_map[u] = max_pos

    # Renormalize after capping
    for side_map in [long_raw, short_raw]:
        total = sum(side_map.values())
        if total > 0:
            scale = half_gross / total
            for u in side_map:
                side_map[u] *= scale

    return long_raw, short_raw


def _simulate_window(label: str, lo: date, hi: date, z_weighted: bool,
                     con) -> dict:
    """Run the portfolio simulation for one window.

    Timing: at formation date t, we rebalance into positions.
    Those positions then earn the forward return fwd_ret_1m (t -> t+1),
    measured at formation t+1. So for cycle i: return is computed at
    time i+1 using positions set at time i and fwd_ret from time i's signals.
    """
    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.fwd_ret_1m
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{lo}'
          AND s.formation_date <= DATE '{hi}'
          AND s.z_carry_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
          AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fdate, u, z, fr in sig_rows:
        by_date[fdate].append((u, float(z), float(fr)))

    formation_dates = sorted(by_date.keys())
    if not formation_dates:
        return {"error": "no formations"}

    state = PortfolioState()
    total_fees = 0.0
    total_slippage = 0.0
    gross_returns = []
    net_returns = []
    turnovers = []
    fee_breakdown = {"brokerage": 0.0, "stt": 0.0, "exchange_txn": 0.0,
                     "sebi_fee": 0.0, "stamp_duty": 0.0, "gst": 0.0}

    prev_fwd = {}  # {underlying: fwd_ret_1m} from PREVIOUS formation
    is_first = True

    for fdate in formation_dates:
        rows = by_date[fdate]
        n = len(rows)
        nq = max(1, round(QUINTILE * n))

        underlyings = [r[0] for r in rows]
        adva = _load_adva(con, fdate, underlyings)

        filt_rows = [r for r in rows if r[0] in adva]
        if len(filt_rows) < 2 * nq:
            # Save this formation's fwd for next time even if we skip
            prev_fwd = {r[0]: r[2] for r in rows}
            is_first = False
            continue

        # --- Compute gross return from positions set LAST period ---
        period_gross_long = 0.0
        period_gross_short = 0.0
        V_long = max(sum(state.long_positions.values()), 1e-6)
        V_short = max(sum(state.short_positions.values()), 1e-6)

        if not is_first and prev_fwd:
            for u, cap in state.long_positions.items():
                period_gross_long += cap * prev_fwd.get(u, 0.0)
            for u, cap in state.short_positions.items():
                period_gross_short += cap * prev_fwd.get(u, 0.0)

            gross_long_r = period_gross_long / V_long
            gross_short_r = period_gross_short / V_short
            gross_spread = gross_long_r - gross_short_r
            gross_returns.append(gross_spread)

        # --- Rebalance: compute new targets ---
        long_targets, short_targets = _compute_targets(z_weighted, filt_rows, adva, nq)

        all_target_weights = list(long_targets.values()) + list(short_targets.values())
        sigma_w = float(np.std(all_target_weights)) if len(all_target_weights) > 1 else 0.0
        band_threshold = BAND_SIGMA * sigma_w

        rebalanced_long = {}
        rebalanced_short = {}

        for u, target in long_targets.items():
            current = state.long_positions.get(u, 0.0)
            if abs(target - current) >= band_threshold or current == 0:
                rebalanced_long[u] = target
            else:
                rebalanced_long[u] = current

        for u, target in short_targets.items():
            current = state.short_positions.get(u, 0.0)
            if abs(target - current) >= band_threshold or current == 0:
                rebalanced_short[u] = target
            else:
                rebalanced_short[u] = current

        # --- Compute turnover ---
        abs_delta = 0.0
        all_held = set(state.long_positions) | set(state.short_positions)
        all_new = set(rebalanced_long) | set(rebalanced_short)
        for u in all_held | all_new:
            old_l = state.long_positions.get(u, 0.0) if u in all_held else 0.0
            new_l = rebalanced_long.get(u, 0.0) if u in all_new else 0.0
            old_s = state.short_positions.get(u, 0.0) if u in all_held else 0.0
            new_s = rebalanced_short.get(u, 0.0) if u in all_new else 0.0
            abs_delta += abs(new_l - old_l) + abs(new_s - old_s)
        gross_now = V_long + V_short
        to = abs_delta / max(gross_now, 1.0)
        turnovers.append(to)

        # --- Compute fees on trades ---
        period_fee = 0.0
        period_slippage = 0.0

        for u in set(rebalanced_long) | set(state.long_positions):
            old_cap = state.long_positions.get(u, 0.0)
            new_cap = rebalanced_long.get(u, 0.0)
            delta = new_cap - old_cap
            if abs(delta) < 1e-6:
                continue
            side = "BUY" if delta > 0 else "SELL"
            trade_val = abs(delta)
            f = _leg_fees(side=side, trade_value=trade_val, trade_date=fdate)
            period_fee += f["total"]
            period_slippage += (SLIPPAGE_BP / 10000) * trade_val
            for k in fee_breakdown:
                fee_breakdown[k] += f[k]

        for u in set(rebalanced_short) | set(state.short_positions):
            old_cap = state.short_positions.get(u, 0.0)
            new_cap = rebalanced_short.get(u, 0.0)
            delta = new_cap - old_cap
            if abs(delta) < 1e-6:
                continue
            side = "SELL" if delta > 0 else "BUY"
            trade_val = abs(delta)
            f = _leg_fees(side=side, trade_value=trade_val, trade_date=fdate)
            period_fee += f["total"]
            period_slippage += (SLIPPAGE_BP / 10000) * trade_val
            for k in fee_breakdown:
                fee_breakdown[k] += f[k]

        total_fees += period_fee
        total_slippage += period_slippage

        # Net return for this period
        if not is_first:
            net_ret = gross_spread - (period_fee + period_slippage) / GROSS_EXPOSURE
            net_returns.append(net_ret)

        # Update state
        state.long_positions = rebalanced_long
        state.short_positions = rebalanced_short

        # Save this formation's fwd_ret_1m for NEXT period
        prev_fwd = {r[0]: r[2] for r in rows}
        is_first = False

    if not gross_returns:
        return {"error": "no valid periods — portfolio never had positions to earn returns"}

    gross_arr = np.array(gross_returns)
    net_arr = np.array(net_returns)
    to_arr = np.array(turnovers[1:])  # first turnover is from empty state, skip

    months = len(gross_arr)
    ppy = 12.0
    ann_gross = float((np.prod(1 + gross_arr) ** (ppy / months) - 1)) if months > 0 else 0.0
    ann_net = float((np.prod(1 + net_arr) ** (ppy / months) - 1)) if months > 0 else 0.0
    fee_drag_bp = (ann_gross - ann_net) * 10000.0
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0

    return {
        "label": label,
        "z_weighted": z_weighted,
        "formations": len(formation_dates),
        "return_periods": months,
        "ann_gross": ann_gross,
        "ann_net": ann_net,
        "fee_drag_bp": fee_drag_bp,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        "avg_turnover": avg_to,
        "fee_breakdown": dict(fee_breakdown),
        "gross_spreads": [float(x) for x in gross_arr],
        "net_spreads": [float(x) for x in net_arr],
    }



def main():
    commit = _git_commit()
    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    results = {}
    for label, (lo, hi) in WINDOWS.items():
        for zw in [False, True]:
            key = f"{label}_{'zweighted' if zw else 'quintile'}"
            print(f"  {key}: {lo} -> {hi}  (z-weighted={zw})")
            results[key] = _simulate_window(label, lo, hi, zw, con)
            if "error" in results[key]:
                print(f"    ERROR: {results[key]['error']}")
            else:
                r = results[key]
                print(f"    formations={r['formations']}  avg_to={r['avg_turnover']:.3f}  "
                      f"gross={r['ann_gross']*100:.2f}%  net={r['ann_net']*100:.2f}%  "
                      f"drag={r['fee_drag_bp']:.1f}bp")

    con.close()

    # ── Generate report ──
    now_ts = date.today().isoformat()
    lines = []
    a = lines.append

    a("# Carry Sleeve — Net-of-Fee Long/Short Spread\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/run_net_spread.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a("**Protocol:** `CARRY_SEALED_READ_PROTOCOL.md` §1 — precondition gate for SEALED read.\n")
    a(f"**Sign:** positive (long high residual carry, short low). "
      f"Frozen per `CARRY_V2_PRE_REGISTRATION.md` §1.\n")
    a(f"**Construction:** frozen per `CARRY_PHASE0_PRE_REGISTRATION.md` §3–§8 (annualized basis, "
      f"dividend-adjusted, cross-sectionally demeaned, winsorized +/-3σ, z-scored, "
      f"beta+sector neutralized, monthly, roll T-3).\n")
    a("")
    a("---\n")
    a("")
    a("## 1. Fee Model\n")
    a(f"| Component | Rate / Rule |")
    a(f"|---|---|")
    a(f"| Futures STT | {STT_RATE*100:.4f}% SELL side only (pre-2023-04, both TRAIN and HOLDOUT) |")
    a(f"| Exchange transaction charge | {EXCHANGE_TXN_RATE*100:.4f}% both legs (NSE retail tier) |")
    a(f"| SEBI turnover fee | {SEBI_FEE_RATE*100:.4f}% both legs (Rs 10/crore) |")
    a(f"| Stamp duty | {STAMP_PRE_2020_07*100:.3f}% BUY side (pre-2020-07); "
      f"{STAMP_POST_2020_07*100:.3f}% BUY side (post-2020-07-01) |")
    a(f"| GST | {GST_RATE*100:.0f}% on (brokerage + exchange_txn + sebi_fee) |")
    a(f"| Brokerage | Rs {BROKERAGE_PER_ORDER:.0f} flat per order (discount broker futures) |")
    a(f"| Slippage | {SLIPPAGE_BP} bp per side (modeling choice, fixed) |")
    a(f"| Gross exposure | Rs {GROSS_EXPOSURE/1e7:.1f} Cr (fixed) |")
    a(f"| ADV cap | Position <= {ADV_CAP_FRAC*100:.0f}% of trailing {ADV_WINDOW}-day ADV |")
    a(f"| No-trade band | {BAND_SIGMA}σ of cross-sectional target weights |")
    a("")

    for zw_label, zw_flag in [("Quintile (equal-weight)", False), ("z-Weighted", True)]:
        a(f"## 2. {zw_label} Portfolio\n")
        a("")
        a("| Window | Net > 0? | Gross ann | Net ann | Fee drag | Slippage | Avg turnover | Formations |")
        a("|---|:--:|--:|--:|--:|--:|--:|--:|")
        for label, (lo, hi) in WINDOWS.items():
            key = f"{label}_{'zweighted' if zw_flag else 'quintile'}"
            r = results.get(key, {})
            if "error" in r:
                a(f"| {label} | ERROR | — | — | — | — | — | {r.get('error', '')} |")
                continue
            net_ok = r["ann_net"] > 0
            a(f"| **{label}** | **{'PASS' if net_ok else 'FAIL'}** | "
              f"{r['ann_gross']*100:+.2f}% | {r['ann_net']*100:+.2f}% | "
              f"{r['fee_drag_bp']:.1f} bp | {r['total_slippage']/r['formations']:.0f} Rs/mo | "
              f"{r['avg_turnover']:.3f} | {r['formations']} |")
        a("")

        # Break down fee components for one variant
        if not zw_flag:
            a(f"### Fee Component Breakdown (TRAIN)\n")
            train_key = f"TRAIN_quintile"
            tr = results.get(train_key, {})
            if "fee_breakdown" in tr:
                fb = tr["fee_breakdown"]
                total_fee = sum(fb.values())
                a("| Component | Total (Rs) | Share |")
                a("|---|---:|--:|")
                for comp in ["brokerage", "stt", "exchange_txn", "sebi_fee", "stamp_duty", "gst"]:
                    val = fb.get(comp, 0.0)
                    share = val / total_fee * 100 if total_fee > 0 else 0
                    a(f"| {comp} | {val:,.0f} | {share:.1f}% |")
                a(f"| **Total fees** | **{total_fee:,.0f}** | 100.0% |")
                a(f"| **Slippage** | **{tr['total_slippage']:,.0f}** | — |")
                a("")

    # ── Gate verdict ──
    a("---\n")
    a("## 3. Gate — Net-of-Fee Precondition\n")
    a("Both windows must show NET > 0 (annualized) on the quintile portfolio.\n")
    a("| Window | Gross ann | Net ann | Net > 0? |")
    a("|---|--:|--:|:--:|")
    all_pass = True
    for label, (lo, hi) in WINDOWS.items():
        key = f"{label}_quintile"
        r = results.get(key, {})
        if "error" in r:
            a(f"| {label} | — | — | ERROR |")
            all_pass = False
        else:
            net_ok = r["ann_net"] > 0
            a(f"| {label} | {r['ann_gross']*100:+.2f}% | {r['ann_net']*100:+.2f}% | "
              f"{'PASS' if net_ok else '**FAIL**'} |")
            if not net_ok:
                all_pass = False

    a("")
    if all_pass:
        a("**GATE VERDICT: PASS** — Net spread > 0 on both TRAIN and HOLDOUT.\n")
        a("Precondition met. SEALED read (2023-01-01 → 2026-07-20) may proceed "
          "under `CARRY_SEALED_READ_PROTOCOL.md`.\n")
    else:
        a("**GATE VERDICT: FAIL** — Net spread <= 0 on at least one window.\n")
        a("STOP. Carry is not tradeable and the SEALED read is NOT authorized. "
          "No parameter tuning (pre-registration frozen).\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    # Snapshot for reproducibility
    snapshot = {
        "commit": commit,
        "generated": now_ts,
        "fee_model": {
            "stt_rate": STT_RATE,
            "exchange_txn_rate": EXCHANGE_TXN_RATE,
            "sebi_fee_rate": SEBI_FEE_RATE,
            "brokerage_per_order": BROKERAGE_PER_ORDER,
            "slippage_bp": SLIPPAGE_BP,
            "gross_exposure": GROSS_EXPOSURE,
            "adv_cap_frac": ADV_CAP_FRAC,
            "no_trade_band_sigma": BAND_SIGMA,
        },
        "results": {k: {kk: vv for kk, vv in v.items() if kk not in ("gross_spreads", "net_spreads")}
                     for k, v in results.items()},
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"Snapshot: {SNAPSHOT}")
    print(f"Gate: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
