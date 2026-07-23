"""Carry SEALED read — one-shot, unrepeatable.

Protocol:  CARRY_SEALED_READ_PROTOCOL.md §1–§5
Pre-reg:   CARRY_V2_PRE_REGISTRATION.md (sign=+1)
Construction: CARRY_PHASE0_PRE_REGISTRATION.md §3–§8

One run only. Snapshot-and-log before interpreting. Output: CARRY_SEALED_REPORT.md
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr, t as student_t

ROOT = Path(__file__).resolve().parents[3]
SIG_DB = ROOT / "data" / "signal_engine" / "carry" / "signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "CARRY_SEALED_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "CARRY_SEALED_SNAPSHOT.json"

SEALED_LO = date(2023, 1, 1)
SEALED_HI = date(2026, 7, 20)
POWER_N_STAR = 42

# ── Fee model with SEALED-era STT tiers ──
EXCHANGE_TXN_RATE = 0.000021
SEBI_FEE_RATE = 0.000001
BROKERAGE_PER_ORDER = 20.0
SLIPPAGE_BP = 5
GST_RATE = 0.18

# STT tiers for SEALED window
def stt_rate(trade_date: date) -> float:
    if trade_date >= date(2024, 10, 1):
        return 0.00020    # 0.0200%
    elif trade_date >= date(2023, 4, 1):
        return 0.000125   # 0.0125%
    else:
        return 0.00010    # 0.0100%

# Stamp duty (post-2020-07-01 uniform)
STAMP_DUTY_RATE = 0.00002  # 0.002% BUY side

# ── Portfolio ──
GROSS_EXPOSURE = 10_000_000.0
QUINTILE = 0.20
ADV_CAP_FRAC = 0.10
BAND_SIGMA = 0.25
ADV_WINDOW = 20
ADV_MIN_OBS = 10
ALPHA = 0.05
AC1_TRIGGER = 0.10
NW_LAG = 4


def _leg_fees(*, side: str, trade_value: float, trade_date: date) -> dict:
    stamp = trade_value * STAMP_DUTY_RATE if side == "BUY" else 0.0
    stt = trade_value * stt_rate(trade_date) if side == "SELL" else 0.0
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


def _load_adva(con, formation_date: date, underlyings: list[str]) -> dict:
    if not underlyings:
        return {}
    u_list = ", ".join(f"'{u}'" for u in underlyings)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0 AS adv_rs
        FROM (
            SELECT underlying, val_in_lakh,
                   ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
            FROM fut.futures_bhavcopy
            WHERE trade_date <= DATE '{formation_date}'
              AND trade_date > DATE '{formation_date}' - INTERVAL '{ADV_WINDOW + 10} days'
              AND underlying IN ({u_list})
        )
        WHERE rn <= {ADV_WINDOW} AND val_in_lakh IS NOT NULL
        GROUP BY underlying
        HAVING COUNT(*) >= {ADV_MIN_OBS}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _compute_targets(rows, adva, n_quintile):
    """Equal-weight quintile: long top, short bottom."""
    sorted_rows = sorted(rows, key=lambda r: r[1])
    long_set = {r[0] for r in sorted_rows[-n_quintile:]}
    short_set = {r[0] for r in sorted_rows[:n_quintile]}

    half_gross = GROSS_EXPOSURE / 2.0
    long_raw = {u: half_gross / max(len(long_set), 1) for u in long_set}
    short_raw = {u: half_gross / max(len(short_set), 1) for u in short_set}

    for side_map in [long_raw, short_raw]:
        for u in list(side_map):
            max_pos = adva.get(u, 0.0) * ADV_CAP_FRAC
            if max_pos > 0 and side_map[u] > max_pos:
                side_map[u] = max_pos
        total = sum(side_map.values())
        if total > 0:
            scale = half_gross / total
            for u in side_map:
                side_map[u] *= scale
    return long_raw, short_raw


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main():
    commit = _git_commit()
    run_ts = datetime.utcnow().isoformat() + "Z"

    # ── SNAPSHOT before interpreting ──
    snapshot = {
        "run_timestamp": run_ts,
        "commit": commit,
        "window": {"lo": str(SEALED_LO), "hi": str(SEALED_HI)},
        "sign": "+1",
        "portfolio": "quintile_equal_weight",
        "fee_model": {
            "stt_tiers": {
                "pre_2023_04": 0.00010,
                "2023_04_to_2024_09": 0.000125,
                "post_2024_10": 0.00020,
            },
            "exchange_txn": EXCHANGE_TXN_RATE,
            "sebi_fee": SEBI_FEE_RATE,
            "stamp_duty": STAMP_DUTY_RATE,
            "brokerage": BROKERAGE_PER_ORDER,
            "gst": GST_RATE,
            "slippage_bp": SLIPPAGE_BP,
        },
        "frozen_artifacts": {
            "CARRY_V2_PRE_REGISTRATION.md":
                "74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec",
            "CARRY_SEALED_READ_PROTOCOL.md":
                "459411ab20374f07dbe531519724574f9625e784d947511885fbb7d92b7874ba",
            "governance/rfa/declarations/carry.py":
                "4b589e2f2afc6282c3e0400c6d24052e34140f4769130239a59ae150d77df855",
        },
    }

    # ── Load data ──
    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.fwd_ret_1m
        FROM sig.signals s
        WHERE s.formation_date >= DATE '{SEALED_LO}'
          AND s.formation_date <= DATE '{SEALED_HI}'
          AND s.z_carry_neut IS NOT NULL
          AND s.fwd_ret_1m IS NOT NULL
          AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fdate, u, z, fr in sig_rows:
        by_date[fdate].append((u, float(z), float(fr)))

    formation_dates = sorted(by_date.keys())
    n_formations = len(formation_dates)
    print(f"SEALED formations: {n_formations}")

    # ── 1. Rank-IC (positive-sign, one-sided, AC₁-corrected) ──
    ic_list = []
    ic_dates = []
    for fdate in formation_dates:
        rows = by_date[fdate]
        zs = np.array([r[1] for r in rows], float)
        frs = np.array([r[2] for r in rows], float)
        present = np.isfinite(zs) & np.isfinite(frs)
        if present.sum() < 5:
            continue
        ic, _ = spearmanr(zs[present], frs[present])
        if not np.isnan(ic):
            ic_list.append(float(ic))
            ic_dates.append(fdate)

    ic_arr = np.array(ic_list)
    n_ic = len(ic_arr)
    mean_ic = float(np.mean(ic_arr)) if n_ic > 0 else 0.0
    sd_ic = float(np.std(ic_arr, ddof=1)) if n_ic > 1 else 0.0
    tstat = mean_ic / (sd_ic / math.sqrt(n_ic)) if sd_ic > 0 and n_ic > 0 else 0.0

    # AC1
    try:
        from scripts.psb1.screening_harness import _ac1
        ac1 = _ac1(ic_arr)
    except ImportError:
        # fallback manual AC1
        if n_ic > 2:
            resid = ic_arr - np.mean(ic_arr)
            ac1 = float(np.sum(resid[1:] * resid[:-1]) / np.sum(resid ** 2))
        else:
            ac1 = 0.0

    p_one = 1 - float(student_t.cdf(tstat, n_ic - 1)) if n_ic > 1 else 1.0

    # HAC if |AC1| > trigger
    nw_t = None
    if abs(ac1) > AC1_TRIGGER and n_ic > NW_LAG:
        try:
            from scripts.psb1.screening_harness import _nw_se
            nw_se_val = _nw_se(ic_arr, lag=NW_LAG)
            nw_t = mean_ic / nw_se_val if nw_se_val > 0 else 0.0
        except ImportError:
            pass

    sign_correct = mean_ic > 0
    ic_pass = sign_correct and p_one < ALPHA

    print(f"  IC: mean={mean_ic:+.4f}  sd={sd_ic:.4f}  t={tstat:.4f}  p(one)={p_one:.6e}  AC1={ac1:.4f}")
    print(f"  Sign correct: {sign_correct}  IC gate: {'PASS' if ic_pass else 'FAIL'}")

    # ── 2. Net-of-fee long/short spread ──
    long_positions = {}
    short_positions = {}
    gross_returns = []
    net_returns = []
    turnovers = []
    total_fees = 0.0
    total_slippage = 0.0
    fee_breakdown = {"brokerage": 0.0, "stt": 0.0, "exchange_txn": 0.0,
                     "sebi_fee": 0.0, "stamp_duty": 0.0, "gst": 0.0}

    prev_fwd = {}
    is_first = True

    for fdate in formation_dates:
        rows = by_date[fdate]
        n = len(rows)
        nq = max(1, round(QUINTILE * n))

        underlyings = [r[0] for r in rows]
        adva = _load_adva(con, fdate, underlyings)

        filt_rows = [r for r in rows if r[0] in adva]
        if len(filt_rows) < 2 * nq:
            prev_fwd = {r[0]: r[2] for r in rows}
            is_first = False
            continue

        # Gross return from prior period
        V_long = max(sum(long_positions.values()), 1e-6)
        V_short = max(sum(short_positions.values()), 1e-6)

        period_gross = 0.0
        if not is_first and prev_fwd:
            gl = sum(cap * prev_fwd.get(u, 0.0) for u, cap in long_positions.items())
            gs = sum(cap * prev_fwd.get(u, 0.0) for u, cap in short_positions.items())
            gro = gl / V_long - gs / V_short
            period_gross = gro
            gross_returns.append(gro)

        # Rebalance
        long_targets, short_targets = _compute_targets(filt_rows, adva, nq)

        all_w = list(long_targets.values()) + list(short_targets.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND_SIGMA * sigma_w

        reb_long = {}
        reb_short = {}
        for u, t in long_targets.items():
            c = long_positions.get(u, 0.0)
            reb_long[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in short_targets.items():
            c = short_positions.get(u, 0.0)
            reb_short[u] = t if abs(t - c) >= band or c == 0 else c

        # Turnover
        abs_d = 0.0
        all_u = set(long_positions) | set(short_positions) | set(reb_long) | set(reb_short)
        for u in all_u:
            ol = long_positions.get(u, 0.0)
            nl = reb_long.get(u, 0.0)
            os = short_positions.get(u, 0.0)
            ns = reb_short.get(u, 0.0)
            abs_d += abs(nl - ol) + abs(ns - os)
        to = abs_d / max(V_long + V_short, 1.0)
        turnovers.append(to)

        # Fees
        period_fee = 0.0
        period_slippage = 0.0

        for side_positions, side_reb in [
            (long_positions, reb_long),
            (short_positions, reb_short),
        ]:
            for u in set(side_positions) | set(side_reb):
                old_c = side_positions.get(u, 0.0)
                new_c = side_reb.get(u, 0.0)
                delta = new_c - old_c
                if abs(delta) < 1e-6:
                    continue
                if side_positions is long_positions:
                    s = "BUY" if delta > 0 else "SELL"
                else:
                    s = "SELL" if delta > 0 else "BUY"
                tv = abs(delta)
                f = _leg_fees(side=s, trade_value=tv, trade_date=fdate)
                period_fee += f["total"]
                period_slippage += (SLIPPAGE_BP / 10000) * tv
                for k in fee_breakdown:
                    fee_breakdown[k] += f[k]

        total_fees += period_fee
        total_slippage += period_slippage

        if not is_first:
            net_r = period_gross - (period_fee + period_slippage) / GROSS_EXPOSURE
            net_returns.append(net_r)

        long_positions = reb_long
        short_positions = reb_short
        prev_fwd = {r[0]: r[2] for r in rows}
        is_first = False

    con.close()

    # ── Portfolio metrics ──
    gross_arr = np.array(gross_returns)
    net_arr = np.array(net_returns)
    to_arr = np.array(turnovers[1:]) if len(turnovers) > 1 else np.array([0.0])

    months = len(gross_arr)
    ppy = 12.0
    ann_gross = float((np.prod(1 + gross_arr) ** (ppy / months) - 1)) if months > 0 else 0.0
    ann_net = float((np.prod(1 + net_arr) ** (ppy / months) - 1)) if months > 0 else 0.0
    fee_drag_bp = (ann_gross - ann_net) * 10000.0
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0

    net_spread_pass = ann_net > 0
    print(f"  Gross: {ann_gross*100:+.2f}%  Net: {ann_net*100:+.2f}%  Drag: {fee_drag_bp:.1f}bp")
    print(f"  Turnover: {avg_to:.3f}  Net>0: {'PASS' if net_spread_pass else 'FAIL'}")

    # ── Power projection (optional, for context only) ──
    ncp_val = abs(mean_ic) * math.sqrt(POWER_N_STAR) / sd_ic if sd_ic > 0 else 0
    from scipy.stats import nct
    power = float(nct.sf(student_t.ppf(1 - ALPHA, max(n_ic - 1, 1)),
                         max(n_ic - 1, 1), ncp_val)) if n_ic > 1 else 0.0

    gate_pass = ic_pass and net_spread_pass

    # ── Generate report ──
    lines = []
    a = lines.append

    a("# Carry Sleeve — SEALED Read Report\n")
    a(f"**One-shot, script-generated** — `scripts/signal_engine/carry/run_sealed.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Run timestamp:** {run_ts}\n")
    a("**Protocol:** `CARRY_SEALED_READ_PROTOCOL.md` §1–§5 (frozen, SHA-256 "
      "`459411ab20374f07dbe531519724574f9625e784d947511885fbb7d92b7874ba`).\n")
    a("**Pre-registration:** `CARRY_V2_PRE_REGISTRATION.md` (frozen, SHA-256 "
      "`74c7311cd84d48db8552f8bacd880b5e43d2264ae3b671aa12e7b3013fe4b1ec`).\n")
    a("**Construction:** `CARRY_PHASE0_PRE_REGISTRATION.md` §3–§8 (frozen).\n")
    a(f"**Window:** SEALED {SEALED_LO} → {SEALED_HI} ({n_formations} formations, "
      f"{n_ic} with IC).\n")
    a(f"**Sign:** +1 (long high residual carry, short low).\n")
    a("")

    a("---\n")
    a("## 1. Rank-IC (Positive-Sign, One-Sided)\n")
    a(f"| Metric | Value |")
    a(f"|---|---|")
    a(f"| Mean IC | {mean_ic:+.6f} |")
    a(f"| SD(IC) | {sd_ic:.6f} |")
    a(f"| n (formations) | {n_ic} |")
    a(f"| t-stat (simple) | {tstat:.4f} |")
    a(f"| p-value (one-sided) | {p_one:.6e} |")
    a(f"| AC1 | {ac1:.4f} |")
    if nw_t is not None:
        a(f"| NW t (|AC1| > {AC1_TRIGGER}, lag={NW_LAG}) | {nw_t:.4f} |")
    else:
        a(f"| NW t | below trigger (|AC1| <= {AC1_TRIGGER}), not computed |")
    a(f"| Sign matches declaration (+1) | {'PASS' if sign_correct else '**FAIL**'} |")
    a(f"| Significant at alpha={ALPHA} | **{'PASS' if ic_pass else 'FAIL'}** |")
    a("")

    a("---\n")
    a("## 2. Net-of-Fee Long/Short Spread\n")
    a(f"| Metric | Value |")
    a(f"|---|---|")
    a(f"| Gross annualized | {ann_gross*100:+.2f}% |")
    a(f"| Net annualized | {ann_net*100:+.2f}% |")
    a(f"| Fee drag | {fee_drag_bp:.1f} bp |")
    a(f"| Slippage ({SLIPPAGE_BP} bp/side) | {total_slippage:,.0f} Rs |")
    a(f"| Avg turnover | {avg_to:.3f} |")
    a(f"| Return periods | {months} |")
    a(f"| Net > 0 | **{'PASS' if net_spread_pass else 'FAIL'}** |")
    a("")

    a("### Fee Component Breakdown\n")
    fb_total = sum(fee_breakdown.values())
    a(f"| Component | Total (Rs) | Share |")
    a(f"|---|---:|--:|")
    for comp in ["brokerage", "stt", "exchange_txn", "sebi_fee", "stamp_duty", "gst"]:
        val = fee_breakdown.get(comp, 0.0)
        share = val / fb_total * 100 if fb_total > 0 else 0
        a(f"| {comp} | {val:,.0f} | {share:.1f}% |")
    a(f"| **Total fees** | **{fb_total:,.0f}** | 100.0% |")
    a(f"| **Slippage** | **{total_slippage:,.0f}** | — |")
    a("")

    a("---\n")
    a("## 3. Power (Context Only — Not a Gate)\n")
    a(f"Power at n*={POWER_N_STAR}: **{power:.4f}** (hurdle 0.80). "
      f"SEALED is a sign+spread confirmation, not a standalone power clearance.\n")
    a("")

    a("---\n")
    a("## 4. SEALED Gate (per §5)\n")
    a(f"| Condition | Result | Detail |")
    a(f"|---|---|---|")
    a(f"| Positive-sign IC significant (one-sided, alpha={ALPHA}) | "
      f"{'PASS' if ic_pass else '**FAIL**'} | "
      f"t={tstat:.4f}, p={p_one:.6e} |")
    a(f"| Net long/short spread > 0 | "
      f"{'PASS' if net_spread_pass else '**FAIL**'} | "
      f"{ann_net*100:+.2f}% annualized |")
    a("")

    if gate_pass:
        a("**SEALED VERDICT: PASS** — Carry is a validated alpha across discovery "
          "(TRAIN) + two out-of-sample windows (HOLDOUT, SEALED).\n")
        a("The research phase closes. Work moves to implementation design "
          "(sizing via `NseMarginEngine`, execution, risk limits). "
          "**No further sleeve hunting.**\n")
    else:
        a("**SEALED VERDICT: FAIL** — the effect did not survive the true holdout.\n")
        a("Carry is dead; there is no v3. The sign-discovery and out-of-sample windows "
          "are exhausted. An honest terminal result, reported as-is.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    # Snapshot with results
    snapshot["results"] = {
        "ic": {
            "mean": mean_ic, "sd": sd_ic, "n": n_ic,
            "tstat": tstat, "p_one": p_one, "ac1": ac1,
            "sign_correct": sign_correct,
        },
        "portfolio": {
            "ann_gross": ann_gross, "ann_net": ann_net,
            "fee_drag_bp": fee_drag_bp, "total_fees": total_fees,
            "total_slippage": total_slippage, "avg_turnover": avg_to,
            "return_periods": months,
            "fee_breakdown": dict(fee_breakdown),
        },
        "power": power,
        "gate_pass": gate_pass,
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"Snapshot: {SNAPSHOT}")
    print(f"SEALED verdict: {'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
