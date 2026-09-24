"""TS Basis futures translation — descriptive measurement, TRAIN + HOLDOUT only.

Re-prices the FROZEN TS Basis book (ts_basis/run_net_spread.py portfolio logic, imported unchanged)
on the near-month single-stock future selected by the frozen T-3 roll rule. z_ts is rebuilt here
with the frozen constants of build_ts_signals.py (504 calendar days, MIN_OBS 12, clip ±3, rows
with raw_ann_basis, liquid, and fwd_ret_1m present) from the fenced Carry signal store, because
the store the original reads used is not archived. Every price read is fenced at 2022-12-31.

The futures-return identity, basis panel, fencing and roll-cost treatment are shared with
scripts/signal_engine/carry/futures_translation.py (see its docstring).

Pre-written kill rule (operator, 2026-09-24): if futures IC <= 0 OR gross futures spread <= 0,
TS Basis is closed as a futures strategy.

Output: docs/reports/ts_basis/TS_BASIS_FUTURES_TRANSLATION_REPORT.md + _SNAPSHOT.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "ts_basis"))
import importlib.util  # noqa: E402

# Same module name as this file, so load the carry helper by path (fenced connect, multipliers, components).
_spec = importlib.util.spec_from_file_location(
    "carry_futures_translation", ROOT / "scripts" / "signal_engine" / "carry" / "futures_translation.py")
FT = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = FT
_spec.loader.exec_module(FT)
import build_ts_signals as B  # noqa: E402

# The carry helper already cached carry's `run_net_spread`; load the TS one by path.
_spec = importlib.util.spec_from_file_location(
    "ts_run_net_spread", ROOT / "scripts" / "signal_engine" / "ts_basis" / "run_net_spread.py")
TS = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = TS
_spec.loader.exec_module(TS)

REPORT = ROOT / "docs" / "reports" / "ts_basis" / "TS_BASIS_FUTURES_TRANSLATION_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "ts_basis" / "TS_BASIS_FUTURES_TRANSLATION_SNAPSHOT.json"
FROZEN = ROOT / "docs" / "reports" / "ts_basis" / "TS_BASIS_NET_SPREAD_SNAPSHOT.json"


def _build_z(con):
    """Frozen build_ts_signals.py logic, on fenced rows. Returns {(fdate, u): (z_ts, fwd_or_None)}."""
    rows = con.execute("""
        SELECT formation_date, underlying, raw_ann_basis, fwd_ret_1m
        FROM sig.signals
        WHERE raw_ann_basis IS NOT NULL AND liquid = TRUE AND has_fwd
        ORDER BY underlying, formation_date
    """).fetchall()
    hist = defaultdict(list)
    for f, u, b, _ in rows:
        hist[u].append((f, float(b)))
    out = {}
    for f, u, b, fr in rows:
        h = hist[u]
        pos = next(i for i, (fd, _) in enumerate(h) if fd == f)
        prior = []
        for i2 in range(pos - 1, -1, -1):
            if (f - h[i2][0]).days > B.Z_LOOKBACK:
                break
            prior.append(h[i2][1])
        if len(prior) < B.Z_MIN_OBS:
            continue
        sd = np.std(prior, ddof=1)
        if sd < 1e-8:
            continue
        z = (float(b) - np.mean(prior)) / sd
        if np.isnan(z):
            continue
        out[(f, u)] = (float(np.clip(z, -B.WINSORIZE_SD, B.WINSORIZE_SD)), fr)
    return out


def _skip_day_returns(con, keys):
    """Diagnostic only: spot return from close(t+1) to close(t1), dropping the first session.
    If the spot IC were a close-noise artifact at t, it would vanish here."""
    con.execute("CREATE OR REPLACE TEMP TABLE sk (t DATE, u VARCHAR)")
    con.executemany("INSERT INTO sk VALUES (?, ?)", keys)
    rows = con.execute(f"""
        WITH adj AS (
            SELECT symbol, trade_date, close FROM eqraw.equity_bhavcopy_adjusted
            WHERE series = 'EQ' AND close > 0 AND trade_date <= DATE '{FT.FENCE}'),
        nxt AS (
            SELECT sk.t, sk.u, MIN(a.trade_date) AS d1
            FROM sk JOIN adj a ON a.symbol = sk.u AND a.trade_date > sk.t GROUP BY sk.t, sk.u)
        SELECT n.t, n.u, a2.close / a1.close - 1
        FROM nxt n
        JOIN sigraw.formations f ON f.formation_date = n.t AND f.fwd_formation_date <= DATE '{FT.FENCE}'
        JOIN adj a1 ON a1.symbol = n.u AND a1.trade_date = n.d1
        JOIN adj a2 ON a2.symbol = n.u AND a2.trade_date = f.fwd_formation_date
        WHERE n.d1 < f.fwd_formation_date
    """).fetchall()
    return {(t, u): r for t, u, r in rows}


def _simulate(lo, hi, zmap, comp, con):
    """The frozen ts_basis/run_net_spread._simulate loop (portfolio logic unchanged), evaluated under
    several return definitions, with T-3 roll costs added alongside."""
    by_date = defaultdict(list)
    for (f, u), (z, fr) in zmap.items():
        if lo <= f <= hi:
            by_date[f].append((u, z, fr))
    fdates = sorted(by_date)

    def rets_for(f):
        m = {"spot": {}, "fut": {}, "fut_settle": {}, "div": {}}
        for u, _, fr in by_date[f]:
            if fr is None:
                continue
            c = comp.get((f, u))
            m["spot"][u] = fr
            m["fut"][u] = (1 + fr) * (c["conv_c"] if c else 1.0) - 1
            m["fut_settle"][u] = (1 + fr) * ((c["conv_s"] or c["conv_c"]) if c else 1.0) - 1
            m["div"][u] = c.get("div", 0.0) if c else 0.0
        return m

    state = TS.PortfolioState()
    prev, prev_f, is_first = None, None, True
    s = defaultdict(list)
    held_z = defaultdict(list)
    acc = dict(missing=0, held=0, flagged=0)
    turnovers = []
    for f in fdates:
        rows = sorted(by_date[f])
        adva = TS._load_adva(con, f, [r[0] for r in rows])
        filt = [(u, z) for u, z, _ in rows if u in adva]
        if len(filt) < 5:
            prev, prev_f, is_first = rets_for(f), f, False
            continue
        V_long = max(sum(state.long_positions.values()), 1e-6)
        V_short = max(sum(state.short_positions.values()), 1e-6)
        period_roll = 0.0
        if not is_first and prev:
            for key in ("spot", "fut", "fut_settle", "div"):
                gl = sum(cap * prev[key].get(u, 0.0) for u, cap in state.long_positions.items()) / V_long
                gs = sum(cap * prev[key].get(u, 0.0) for u, cap in state.short_positions.items()) / V_short
                s[f"{key}_long"].append(gl)
                s[f"{key}_short"].append(gs)
                s[key].append(gl - gs)
            for book, legs in ((state.long_positions, ("SELL", "BUY")),
                               (state.short_positions, ("BUY", "SELL"))):
                for u, cap in book.items():
                    acc["held"] += 1
                    c = comp.get((prev_f, u))
                    if c is None:
                        acc["missing"] += 1
                        continue
                    acc["flagged"] += 1 if c["flags"] else 0
                    for _ in range(c["rolls"]):
                        for side in legs:
                            period_roll += TS._calc_fees(side=side, trade_value=cap,
                                                         trade_date=c["first_roll"]).total
                            period_roll += (TS.SLIPPAGE_BP / 10000) * cap

        longs_t, shorts_t = TS._compute_targets(filt, adva)
        all_w = list(longs_t.values()) + list(shorts_t.values())
        band = TS.BAND_SIGMA * (float(np.std(all_w)) if len(all_w) > 1 else 0.0)
        reb_l, reb_s = {}, {}
        for u, t in longs_t.items():
            c = state.long_positions.get(u, 0.0)
            reb_l[u] = t if abs(t - c) >= band or c == 0 else c
        for u, t in shorts_t.items():
            c = state.short_positions.get(u, 0.0)
            reb_s[u] = t if abs(t - c) >= band or c == 0 else c

        abs_d = 0.0
        for u in set(state.long_positions) | set(state.short_positions) | set(reb_l) | set(reb_s):
            abs_d += abs(reb_l.get(u, 0.0) - state.long_positions.get(u, 0.0))
            abs_d += abs(reb_s.get(u, 0.0) - state.short_positions.get(u, 0.0))
        turnovers.append(abs_d / max(V_long + V_short, 1.0))

        period_reb = 0.0
        for positions, reb, is_long in ((state.long_positions, reb_l, True),
                                        (state.short_positions, reb_s, False)):
            for u in set(positions) | set(reb):
                delta = reb.get(u, 0.0) - positions.get(u, 0.0)
                if abs(delta) < 1e-6:
                    continue
                side = ("BUY" if delta > 0 else "SELL") if is_long else ("SELL" if delta > 0 else "BUY")
                period_reb += TS._calc_fees(side=side, trade_value=abs(delta), trade_date=f).total
                period_reb += (TS.SLIPPAGE_BP / 10000) * abs(delta)
        if not is_first:
            s["cost_rebalance"].append(period_reb / TS.GROSS_EXPOSURE)
            s["cost_roll"].append(period_roll / TS.GROSS_EXPOSURE)

        state.long_positions, state.short_positions = reb_l, reb_s
        prev, prev_f, is_first = rets_for(f), f, False
    return s, fdates, turnovers, acc


def _ics(lo, hi, zmap, comp, skip):
    by = defaultdict(list)
    for (f, u), (z, fr) in zmap.items():
        if lo <= f <= hi and fr is not None:
            c = comp.get((f, u))
            by[f].append((z, fr, (1 + fr) * c["conv_c"] - 1 if c else np.nan,
                          c["conv_c"] - 1 if c else np.nan, fr + (c.get("div", 0.0) if c else 0.0),
                          skip.get((f, u), np.nan)))
    out = defaultdict(list)
    for f in sorted(by):
        a = np.array(by[f], float)
        if len(a) < 5:
            continue
        for j, name in enumerate(("spot", "fut", "conv", "spot_total", "spot_skip1"), start=1):
            ok = np.isfinite(a[:, j])
            if ok.sum() >= 5:
                out[name].append(spearmanr(a[ok, 0], a[ok, j]).correlation)
    return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)), "t": FT._t(v), "n": len(v)}
            for k, v in out.items()}


def main():
    con = FT._connect()
    print("building fenced basis panel + daily multipliers...")
    FT._daily_multipliers(con)
    periods = con.execute(f"""
        SELECT formation_date, fwd_formation_date FROM sigraw.formations
        WHERE fwd_formation_date <= DATE '{FT.FENCE}' AND formation_date >= DATE '2016-03-31'
    """).fetchall()
    comp = FT._period_components(con, periods)
    zmap = _build_z(con)
    maxd = con.execute("SELECT MAX(trade_date) FROM mult").fetchone()[0]
    excluded = con.execute(f"""
        SELECT COUNT(*) FROM sigraw.signals s JOIN sigraw.formations f USING (formation_date)
        WHERE s.formation_date BETWEEN DATE '2016-03-31' AND DATE '{FT.FENCE}'
          AND f.fwd_formation_date <= DATE '{FT.FENCE}'
          AND s.raw_ann_basis IS NOT NULL AND s.liquid AND s.fwd_ret_1m IS NULL
    """).fetchone()[0]
    skip = _skip_day_returns(con, [k for k, (_, fr) in zmap.items() if fr is not None])
    print(f"  z_ts cells {len(zmap):,}; futures periods {len(comp):,}; skip-day returns {len(skip):,}")

    frozen = json.loads(FROZEN.read_text())["results"]
    res = {}
    for w, (lo, hi) in TS.WINDOWS.items():
        s, fdates, tos, acc = _simulate(lo, hi, zmap, comp, con)
        spot, fut = np.array(s["spot"]), np.array(s["fut"])
        reb, roll = np.array(s["cost_rebalance"]), np.array(s["cost_roll"])
        div = np.array(s["div"])
        res[w] = {
            "formations": len(fdates), "periods": len(spot),
            "ann": {"gross_spot": FT._ann(spot), "net_spot": FT._ann(spot - reb),
                    "gross_spot_total_return": FT._ann(spot + div),
                    "gross_fut": FT._ann(fut), "gross_fut_settle": FT._ann(s["fut_settle"]),
                    "net_fut": FT._ann(fut - reb - roll)},
            "mean_bp": {k: float(np.mean(v)) * 1e4 for k, v in {
                "spot": spot, "conv": fut - spot, "div": div, "conv_ex_div": fut - spot - div,
                "fut": fut, "cost_rebalance": reb, "cost_roll": roll, "net_fut": fut - reb - roll,
                "spot_long": s["spot_long"], "fut_long": s["fut_long"],
                "spot_short": s["spot_short"], "fut_short": s["fut_short"],
                "div_long": s["div_long"], "div_short": s["div_short"]}.items()},
            "t": {"spot": FT._t(spot), "fut": FT._t(fut), "conv": FT._t(fut - spot),
                  "net_fut": FT._t(fut - reb - roll)},
            "pos_months_gross_fut": float((fut > 0).mean()),
            "avg_turnover": float(np.mean(tos[1:])),
            "coverage": acc,
            "ic": _ics(lo, hi, zmap, comp, skip),
            "repro": {"d_gross_bp": (FT._ann(spot) - frozen[w]["ann_gross"]) * 1e4,
                      "d_net_bp": (FT._ann(spot - reb) - frozen[w]["ann_net"]) * 1e4,
                      "frozen_ic": frozen[w]["mean_ic"]},
        }
        r = res[w]
        print(f"  {w}: spot {r['ann']['gross_spot']:+.2%} fut {r['ann']['gross_fut']:+.2%} "
              f"netfut {r['ann']['net_fut']:+.2%} futIC {r['ic']['fut']['mean']:+.4f}")
    con.close()
    kill = {w: bool(r["ic"]["fut"]["mean"] <= 0 or r["ann"]["gross_fut"] <= 0) for w, r in res.items()}
    _write(res, kill, maxd, excluded)
    return 0


def _write(res, kill, maxd, excluded):
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    L = []
    a = L.append
    a("# TS Basis — Futures Translation (TRAIN + HOLDOUT)\n")
    a(f"**Script-generated** — `scripts/signal_engine/ts_basis/futures_translation.py`, commit `{commit}`, "
      f"run {date.today().isoformat()}. Frozen construction, frozen portfolio logic; price reads fenced at "
      f"{FT.FENCE}; max futures date read **{maxd}**. Kill rule (pre-written): futures IC ≤ 0 OR gross "
      f"futures spread ≤ 0 → closed as a futures strategy.\n")
    a("## 0. Reproduction of the frozen spot snapshot (`TS_BASIS_NET_SPREAD_SNAPSHOT.json`, Spearman)\n")
    a("| Window | Δ gross spot | Δ net spot | IC here vs frozen |")
    a("|---|--:|--:|--:|")
    for w, r in res.items():
        a(f"| {w} | {r['repro']['d_gross_bp']:+.2f} bp | {r['repro']['d_net_bp']:+.2f} bp | "
          f"{r['ic']['spot']['mean']:+.4f} vs {r['repro']['frozen_ic']:+.4f} |")
    a("")
    a("## 1. Annualised Q5−Q1 (equal-weight quintile, frozen book)\n")
    a("| Window | Gross spot (t) | Spot incl. dividends | Gross futures (t) | Gross fut (settle) | Net spot (frozen) | Net futures (t) | Months gross fut > 0 |")
    a("|---|--:|--:|--:|--:|--:|--:|--:|")
    for w, r in res.items():
        an, t = r["ann"], r["t"]
        a(f"| {w} | {an['gross_spot']:+.2%} ({t['spot']:+.2f}) | {an['gross_spot_total_return']:+.2%} | "
          f"**{an['gross_fut']:+.2%}** ({t['fut']:+.2f}) | {an['gross_fut_settle']:+.2%} | {an['net_spot']:+.2%} | "
          f"**{an['net_fut']:+.2%}** ({t['net_fut']:+.2f}) | {r['pos_months_gross_fut']:.0%} |")
    a("")
    a("## 2. Monthly decomposition (bp/month)\n")
    a("| Window | Spot | Convergence (t) | of which dividends | of which basis + roll | Futures | Rebalance cost | Roll cost | Net futures |")
    a("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for w, r in res.items():
        m = r["mean_bp"]
        a(f"| {w} | {m['spot']:+.1f} | {m['conv']:+.1f} ({r['t']['conv']:+.2f}) | {m['div']:+.1f} | "
          f"{m['conv_ex_div']:+.1f} | {m['fut']:+.1f} | {-m['cost_rebalance']:.1f} | {-m['cost_roll']:.1f} | "
          f"{m['net_fut']:+.1f} |")
    a("")
    a("| Window | Long spot | Long fut | Long div | Short spot | Short fut | Short div | Turnover | Missing fut / held | Jump-flagged |")
    a("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for w, r in res.items():
        m, c = r["mean_bp"], r["coverage"]
        a(f"| {w} | {m['spot_long']:+.1f} | {m['fut_long']:+.1f} | {m['div_long']:+.1f} | {m['spot_short']:+.1f} | "
          f"{m['fut_short']:+.1f} | {m['div_short']:+.1f} | {r['avg_turnover']:.3f} | {c['missing']} / {c['held']} | "
          f"{c['flagged']} |")
    a("")
    a("## 3. Rank IC of frozen z_ts (all scored names, per formation)\n")
    a("| Window | vs spot | vs futures | vs convergence | vs spot + dividends | vs spot skipping day 1 (diagnostic) |")
    a("|---|--:|--:|--:|--:|--:|")
    for w, r in res.items():
        ic = r["ic"]
        a(f"| {w} | " + " | ".join(f"{ic[k]['mean']:+.4f} (t {ic[k]['t']:+.2f})"
                                   for k in ("spot", "fut", "conv", "spot_total", "spot_skip1")) + " |")
    a("")
    a("## 4. Kill rule\n")
    a("| Window | Futures IC | Gross futures | Kill fires? |")
    a("|---|--:|--:|:--:|")
    for w, r in res.items():
        a(f"| {w} | {r['ic']['fut']['mean']:+.4f} | {r['ann']['gross_fut']:+.2%} | {'**YES**' if kill[w] else 'no'} |")
    a("")
    a(f"Survivorship: {excluded} liquid (formation, name) cells in 2016-03 → 2022 have no forward "
      "return and are excluded by the frozen builder's `fwd_ret_1m IS NOT NULL` membership filter.\n")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    SNAPSHOT.write_text(json.dumps({"commit": commit, "fence": str(FT.FENCE), "max_date_read": str(maxd),
                                    "kill": kill, "survivorship_excluded": excluded, "results": res},
                                   indent=2, default=str), encoding="utf-8")
    print(f"report: {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
