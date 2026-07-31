"""TS Basis Daily — SEALED read (one-shot, unrepeatable). DISABLED.

The operator declared TS Basis Daily RESEARCH-ONLY on 2026-08-01, which
preserves the 876-formation SEALED window (2023-01-01 -> 2026-07-24) unspent.
Running this script would consume it, and the window cannot be regenerated:
NSE F&O history cannot predate 2016.

This guard exists because the decision is otherwise unenforced. The repo's own
lesson from the 2026-07-31 stale-feed incident applies — a constraint that is
documented but never asserted is documentation, not a control.

To re-enable: an operator decision reversing research-only status, recorded in
docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md, plus a frozen
pre-registration with a pinned acceptance rule and horizon. Deleting this guard
is not by itself authorization.

Mirror of TS Basis run_sealed.py for daily cadence.
Annualization factor: 252 (trading days/year) instead of 12.

Output: docs/reports/TS_BASIS_DAILY_SEALED_REPORT.md
"""
from __future__ import annotations

import json, math, sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr, t as student_t, nct

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import futures_fees as _calc_fees

SIG_DB = ROOT / "data" / "signal_engine" / "ts_basis_daily" / "ts_signals.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_SEALED_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "TS_BASIS_DAILY_SEALED_SNAPSHOT.json"

SEALED_LO = date(2023, 1, 1)
SEALED_HI = date(2026, 7, 20)
POWER_N_STAR = 504  # ~2 years of daily formations

GROSS = 10_000_000.0; HALF = GROSS / 2.0
QF = 0.20; ADV_CAP_FRAC = 0.10; BAND = 0.25; SLIP = 5
ADV_W = 20; ADV_MIN = 10; ALPHA = 0.05; AC1_TRIGGER = 0.10; NW_LAG = 4
PPY = 252.0


def _load_adva(con, fdate, ulist):
    if not ulist: return {}
    ul = ", ".join(f"'{u}'" for u in ulist)
    rows = con.execute(f"""
        SELECT underlying, AVG(val_in_lakh) * 100000.0
        FROM (SELECT underlying, val_in_lakh, ROW_NUMBER() OVER (PARTITION BY underlying ORDER BY trade_date DESC) AS rn
              FROM fut.futures_bhavcopy WHERE trade_date <= DATE '{fdate}'
              AND trade_date > DATE '{fdate}' - INTERVAL '{ADV_W+10} days'
              AND underlying IN ({ul}) AND inst_type = 'FUTSTK')
        WHERE rn <= {ADV_W} AND val_in_lakh IS NOT NULL
        GROUP BY underlying HAVING COUNT(*) >= {ADV_MIN}
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def _compute_targets(filt, adva):
    n = len(filt); nq = max(1, round(QF * n))
    srt = sorted(filt, key=lambda r: r[1])
    ls = {r[0] for r in srt[-nq:]}; ss = {r[0] for r in srt[:nq]}
    longs, shorts = {}, {}
    for in_set, side_map in [(ls, longs), (ss, shorts)]:
        n_leg = len(in_set)
        if n_leg == 0: continue
        cap_each = HALF / n_leg
        for u in in_set:
            max_pos = adva.get(u, float('inf')) * ADV_CAP_FRAC
            side_map[u] = min(cap_each, max_pos if max_pos > 0 else cap_each)
        total = sum(side_map.values())
        if total > 0:
            scale = HALF / total
            side_map.update({u: v * scale for u, v in side_map.items()})
    return longs, shorts


def _ac1(arr):
    n = len(arr)
    if n < 3: return 0.0
    r = arr - np.mean(arr)
    return float(np.sum(r[1:] * r[:-1]) / np.sum(r ** 2))


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main():
    raise SystemExit(
        "REFUSED: TS Basis Daily is RESEARCH-ONLY (operator decision 2026-08-01).\n"
        "The SEALED window 2023-01-01 -> 2026-07-24 (876 formations) is preserved "
        "unspent and cannot be regenerated — NSE F&O history cannot predate 2016.\n"
        "Running this read would consume it permanently.\n"
        "See docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md §B.4."
    )

    commit = _git_commit()
    run_ts = datetime.utcnow().isoformat() + "Z"

    snapshot = {
        "run_timestamp": run_ts, "commit": commit,
        "window": {"lo": str(SEALED_LO), "hi": str(SEALED_HI)},
        "sign": "+1", "portfolio": "quintile_equal_weight",
        "cadence": "daily", "ppy": PPY,
        "fee_model": {"source": "core/execution/futures/futures_fees.py", "slippage_bp": SLIP, "gross": GROSS},
    }

    con = duckdb.connect()
    con.execute(f"ATTACH '{SIG_DB}' AS sig (READ_ONLY)")
    con.execute(f"ATTACH '{FUT_DB}' AS fut (READ_ONLY)")
    con.execute("SET threads=4")

    print("Loading SEALED data...")
    sig_rows = con.execute(f"""
        SELECT s.formation_date, s.underlying, s.z_ts, s.fwd_ret_1m
        FROM sig.signals s WHERE s.formation_date >= DATE '{SEALED_LO}'
        AND s.formation_date <= DATE '{SEALED_HI}'
        AND s.z_ts IS NOT NULL AND s.fwd_ret_1m IS NOT NULL AND s.liquid = TRUE
        ORDER BY s.formation_date, s.underlying
    """).fetchall()

    by_date = defaultdict(list)
    for fd, u, z, fr in sig_rows:
        by_date[fd].append((u, float(z), float(fr)))
    formation_dates = sorted(by_date.keys())
    n_form = len(formation_dates)
    print(f"  SEALED formations: {n_form}")

    ic_list = []
    for fd in formation_dates:
        rows = by_date[fd]
        zs = np.array([r[1] for r in rows], float)
        frs = np.array([r[2] for r in rows], float)
        present = np.isfinite(zs) & np.isfinite(frs)
        if present.sum() < 5: continue
        ic, _ = spearmanr(zs[present], frs[present])
        if not np.isnan(ic): ic_list.append(float(ic))

    ic_arr = np.array(ic_list)
    n_ic = len(ic_arr)
    mean_ic = float(np.mean(ic_arr)) if n_ic > 0 else 0.0
    sd_ic = float(np.std(ic_arr, ddof=1)) if n_ic > 1 else 0.0
    tstat = mean_ic / (sd_ic / math.sqrt(n_ic)) if sd_ic > 0 and n_ic > 0 else 0.0
    ac1 = _ac1(ic_arr)
    p_one = 1 - float(student_t.cdf(tstat, n_ic - 1)) if n_ic > 1 else 1.0
    sign_correct = mean_ic > 0
    ic_pass = sign_correct and p_one < ALPHA
    print(f"  IC: mean={mean_ic:+.4f} sd={sd_ic:.4f} t={tstat:.2f} p={p_one:.6e} ac1={ac1:.4f} {'PASS' if ic_pass else 'FAIL'}")

    long_positions, short_positions = {}, {}
    gross_returns, net_returns, turnovers = [], [], []
    total_fees, total_slippage = 0.0, 0.0
    fb = {"brokerage": 0.0, "stt": 0.0, "exchange_txn": 0.0, "sebi_fee": 0.0, "stamp_duty": 0.0, "gst": 0.0}
    prev_fwd, is_first = {}, True

    for fd in formation_dates:
        rows = by_date[fd]
        ulist = [r[0] for r in rows]
        adva = _load_adva(con, fd, ulist)
        filt = [(r[0], r[1]) for r in rows if r[0] in adva]
        if len(filt) < 5:
            prev_fwd = {r[0]: r[2] for r in rows}; is_first = False; continue

        VL = max(sum(long_positions.values()), 1e-6)
        VS = max(sum(short_positions.values()), 1e-6)
        pg = 0.0
        if not is_first and prev_fwd:
            gl = sum(cap * prev_fwd.get(u, 0.0) for u, cap in long_positions.items())
            gs = sum(cap * prev_fwd.get(u, 0.0) for u, cap in short_positions.items())
            pg = gl / VL - gs / VS; gross_returns.append(pg)

        longs_t, shorts_t = _compute_targets(filt, adva)
        all_w = list(longs_t.values()) + list(shorts_t.values())
        sigma_w = float(np.std(all_w)) if len(all_w) > 1 else 0.0
        band = BAND * sigma_w

        rl = {u: t if abs(t - long_positions.get(u, 0)) >= band or long_positions.get(u, 0) == 0 else long_positions.get(u, 0) for u, t in longs_t.items()}
        rs = {u: t if abs(t - short_positions.get(u, 0)) >= band or short_positions.get(u, 0) == 0 else short_positions.get(u, 0) for u, t in shorts_t.items()}

        abs_d = 0.0
        all_u = set(long_positions) | set(short_positions) | set(rl) | set(rs)
        for u in all_u:
            abs_d += abs(rl.get(u, 0) - long_positions.get(u, 0)) + abs(rs.get(u, 0) - short_positions.get(u, 0))
        turnovers.append(abs_d / max(VL + VS, 1.0))

        pf, ps = 0.0, 0.0
        for side_positions, reb in [(long_positions, rl), (short_positions, rs)]:
            for u in set(side_positions) | set(reb):
                oc = side_positions.get(u, 0); nc = reb.get(u, 0)
                delta = nc - oc
                if abs(delta) < 1e-6: continue
                if side_positions is long_positions: side = "BUY" if delta > 0 else "SELL"
                else: side = "SELL" if delta > 0 else "BUY"
                tv = abs(delta)
                f = _calc_fees(side=side, trade_value=tv, trade_date=fd)
                pf += f.total; ps += (SLIP / 10000) * tv
                for k in fb: fb[k] += getattr(f, k)

        total_fees += pf; total_slippage += ps
        if not is_first: net_returns.append(pg - (pf + ps) / GROSS)
        long_positions = rl; short_positions = rs
        prev_fwd = {r[0]: r[2] for r in rows}; is_first = False

    con.close()

    g_arr = np.array(gross_returns); n_arr = np.array(net_returns)
    to_arr = np.array(turnovers[1:])
    periods = len(g_arr)
    ann_gross = float(np.prod(1 + g_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    ann_net = float(np.prod(1 + n_arr) ** (PPY / periods) - 1) if periods > 0 else 0.0
    drag = (ann_gross - ann_net) * 10000.0
    avg_to = float(np.mean(to_arr)) if len(to_arr) > 0 else 0.0
    net_pass = ann_net > 0
    print(f"  Gross={ann_gross*100:+.2f}% Net={ann_net*100:+.2f}% drag={drag:.0f}bp to={avg_to:.3f} {'PASS' if net_pass else 'FAIL'}")

    ncp = abs(mean_ic) * math.sqrt(POWER_N_STAR) / sd_ic if sd_ic > 0 else 0
    power = float(nct.sf(student_t.ppf(1 - ALPHA, max(n_ic - 1, 1)), max(n_ic - 1, 1), ncp)) if n_ic > 1 else 0.0

    gate = ic_pass and net_pass

    lines = []
    a = lines.append
    a("# TS Basis Daily — SEALED Read Report\n")
    a(f"**One-shot, script-generated** — `scripts/signal_engine/ts_basis_daily/run_sealed.py`. Code commit `{commit}`.\n")
    a(f"**Run timestamp:** {run_ts}\n")
    a(f"**Window:** SEALED {SEALED_LO} -> {SEALED_HI} ({n_form} formations, {n_ic} with IC).\n")
    a(f"**Cadence:** daily ({PPY:.0f} formations/year).\n")
    a(f"**Sign:** +1 (long high z_ts, short low z_ts).\n\n")

    a("---\n## 1. Rank-IC\n")
    a("| Metric | Value |\n|---|---|")
    a(f"| Mean IC | {mean_ic:+.6f} |"); a(f"| SD(IC) | {sd_ic:.6f} |")
    a(f"| n | {n_ic} |"); a(f"| t-stat | {tstat:.4f} |"); a(f"| p (one) | {p_one:.6e} |")
    a(f"| AC1 | {ac1:.4f} |"); a(f"| Sign correct | {'PASS' if sign_correct else 'FAIL'} |")
    a(f"| IC gate (α={ALPHA}) | {'**PASS**' if ic_pass else '**FAIL**'} |\n")

    a("---\n## 2. Net-of-Fee Spread\n")
    a("| Metric | Value |\n|---|---|")
    a(f"| Gross ann | {ann_gross*100:+.2f}% |"); a(f"| Net ann | {ann_net*100:+.2f}% |")
    a(f"| Fee drag | {drag:.0f} bp |"); a(f"| Turnover | {avg_to:.3f} |")
    a(f"| Return periods | {periods} |"); a(f"| Net > 0 | {'**PASS**' if net_pass else '**FAIL**'} |\n")

    fb_total = sum(fb.values())
    a("### Fee Breakdown\n")
    a("| Component | Total (Rs) | Share |\n|---|---:|--:|")
    for comp in ["brokerage", "stt", "exchange_txn", "sebi_fee", "stamp_duty", "gst"]:
        a(f"| {comp} | {fb[comp]:,.0f} | {fb[comp]/fb_total*100:.1f}% |")
    a(f"| **Total** | **{fb_total:,.0f}** | 100.0% |\n")

    a("---\n## 3. Power (context only)\n")
    a(f"Power at n*={POWER_N_STAR}: **{power:.4f}** (hurdle 0.80). SEALED is sign+spread confirmation.\n")

    a("---\n## 4. SEALED Gate\n")
    a("| Condition | Result | Detail |\n|---|---|---|")
    a(f"| IC sig (α={ALPHA}, one-sided) | {'PASS' if ic_pass else '**FAIL**'} | t={tstat:.2f}, p={p_one:.6e} |")
    a(f"| Net > 0 | {'PASS' if net_pass else '**FAIL**'} | {ann_net*100:+.2f}% |\n")

    if gate:
        a("**SEALED VERDICT: PASS** — TS Basis Daily is validated.\n")
    else:
        a("**SEALED VERDICT: FAIL** — the effect did not survive the holdout.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    snapshot["results"] = {
        "ic": {"mean": mean_ic, "sd": sd_ic, "n": n_ic, "tstat": tstat, "p_one": p_one, "ac1": ac1, "sign_correct": sign_correct},
        "portfolio": {"ann_gross": ann_gross, "ann_net": ann_net, "fee_drag_bp": drag, "total_fees": total_fees, "total_slippage": total_slippage, "avg_turnover": avg_to, "return_periods": periods, "fee_breakdown": dict(fb)},
        "power": power, "gate_pass": gate,
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    print(f"\nReport: {REPORT}")
    print(f"SEALED: {'PASS' if gate else 'FAIL'}")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
