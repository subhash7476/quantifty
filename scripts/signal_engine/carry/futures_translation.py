"""Carry futures translation — descriptive measurement, TRAIN + HOLDOUT only.

Re-prices the FROZEN Carry book (run_net_spread.py construction, imported, unchanged) on the
instrument it trades: the near-month single-stock future selected by the frozen T-3 roll rule.
No parameter, signal, or window is changed. Every price read is fenced at 2022-12-31.

Futures return per (formation t, name), chained daily over (t, t1] on the contract held overnight:
    F_c(d) / F_c(d-1)  =  [S(d)/S(d-1)] * [(F_c(d)/S(d)) / (F_c(d-1)/S(d-1))]
so  1 + r_fut = (1 + r_spot) * CONV,  CONV = prod of same-contract basis-ratio changes.
Raw spot S cancels inside CONV (split/bonus-robust: F and S re-base on the same ex-date), and
r_spot is the frozen fwd_ret_1m (split/bonus/special-dividend adjusted, ordinary dividends not).
CONV therefore contains (a) residual basis convergence, (b) roll yield at the T-3 roll, and
(c) +D/S on ordinary-dividend ex-dates (spot drops by D, the future does not). (c) is reported
separately.

Output: docs/reports/carry/CARRY_FUTURES_TRANSLATION_REPORT.md + _SNAPSHOT.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.environ.get("NIFTY_DATA_ROOT", ROOT)) / "data"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "signal_engine" / "carry"))
import contract_arms as A  # noqa: E402
import run_net_spread as NS  # noqa: E402

FENCE = date(2022, 12, 31)
WINDOWS = NS.WINDOWS
REPORT = ROOT / "docs" / "reports" / "carry" / "CARRY_FUTURES_TRANSLATION_REPORT.md"
SNAPSHOT = ROOT / "docs" / "reports" / "carry" / "CARRY_FUTURES_TRANSLATION_SNAPSHOT.json"
FROZEN = ROOT / "docs" / "reports" / "carry" / "CARRY_NET_SPREAD_SNAPSHOT.json"
JUMP_LO, JUMP_HI = 0.8, 1.25   # daily same-contract basis-ratio change outside this = data flag


def _connect():
    con = duckdb.connect()
    con.execute(f"ATTACH '{DATA / 'market_data' / 'futures_bhavcopy.duckdb'}' AS futraw (READ_ONLY)")
    con.execute(f"ATTACH '{DATA / 'market_data' / 'equity_bhavcopy.duckdb'}' AS eqraw (READ_ONLY)")
    con.execute(f"ATTACH '{DATA / 'signal_engine' / 'carry' / 'signals.duckdb'}' AS sigraw (READ_ONLY)")
    con.execute("ATTACH ':memory:' AS fut")
    con.execute("ATTACH ':memory:' AS eq")
    con.execute("ATTACH ':memory:' AS sig")
    con.execute(f"CREATE VIEW fut.futures_bhavcopy AS SELECT * FROM futraw.futures_bhavcopy "
                f"WHERE trade_date <= DATE '{FENCE}'")
    con.execute(f"CREATE VIEW eq.equity_bhavcopy AS SELECT * FROM eqraw.equity_bhavcopy "
                f"WHERE trade_date <= DATE '{FENCE}'")
    con.execute("CREATE VIEW eq.symbol_entity_intervals AS SELECT * FROM eqraw.symbol_entity_intervals")
    con.execute(f"CREATE VIEW eq.corporate_actions AS SELECT * FROM eqraw.corporate_actions "
                f"WHERE ex_date <= DATE '{FENCE}'")
    # Frozen signals, fenced: a row's forward return is only visible if its whole forward period
    # closes inside the fence. Membership (fwd_ret IS NOT NULL) is kept exactly as frozen.
    con.execute(f"""
        CREATE VIEW sig.signals AS
        SELECT s.formation_date, s.underlying, s.z_carry_neut, s.raw_ann_basis, s.liquid,
               CASE WHEN f.fwd_formation_date <= DATE '{FENCE}' THEN s.fwd_ret_1m END AS fwd_ret_1m,
               s.fwd_ret_1m IS NOT NULL AS has_fwd
        FROM sigraw.signals s JOIN sigraw.formations f USING (formation_date)
        WHERE s.formation_date <= DATE '{FENCE}'
    """)
    con.execute("SET threads=4")
    return con


def _daily_multipliers(con):
    """Per (underlying, day d): same-contract basis-ratio change from the previous panel day,
    on the contract selected at the previous day (the one held overnight)."""
    A.build_basis_panel(con)
    con.execute("""
        CREATE TEMP TABLE bp_seq AS
        SELECT underlying, trade_date, expiry_dt, fut_close, fut_settle, spot_close,
               LAG(trade_date) OVER w AS prev_date,
               LAG(expiry_dt)  OVER w AS prev_exp,
               LAG(fut_close)  OVER w AS prev_fc,
               LAG(fut_settle) OVER w AS prev_fs,
               LAG(spot_close) OVER w AS prev_s
        FROM basis_panel
        WHERE spot_close IS NOT NULL AND spot_close > 0 AND fut_close IS NOT NULL
        WINDOW w AS (PARTITION BY underlying ORDER BY trade_date)
    """)
    con.execute("""
        CREATE TEMP TABLE mult AS
        SELECT b.underlying, b.trade_date, b.prev_date,
               (f.close  / b.spot_close) / (b.prev_fc / b.prev_s) AS m_close,
               (f.settle / b.spot_close) / (b.prev_fs / b.prev_s) AS m_settle,
               (b.expiry_dt <> b.prev_exp) AS is_roll
        FROM bp_seq b
        JOIN fut.futures_bhavcopy f
          ON f.underlying = b.underlying AND f.trade_date = b.trade_date
         AND f.expiry_dt = b.prev_exp AND f.inst_type = 'FUTSTK'
        WHERE b.prev_date IS NOT NULL AND b.prev_fc > 0 AND b.prev_s > 0
    """)


def _period_components(con, periods):
    """periods: list of (t, t1). Returns {(t, u): dict(conv_c, conv_s, rolls, div, flags, first_roll)}."""
    con.execute("CREATE OR REPLACE TEMP TABLE per (t DATE, t1 DATE)")
    con.executemany("INSERT INTO per VALUES (?, ?)", periods)
    rows = con.execute("""
        SELECT p.t, m.underlying,
               EXP(SUM(LN(m.m_close))),
               EXP(SUM(LN(m.m_settle)) FILTER (WHERE m.m_settle > 0)),
               COUNT(*) FILTER (WHERE m.is_roll),
               COUNT(*) FILTER (WHERE m.m_close < ? OR m.m_close > ?),
               MIN(m.trade_date) FILTER (WHERE m.is_roll),
               COUNT(*)
        FROM per p JOIN mult m ON m.trade_date > p.t AND m.trade_date <= p.t1
        WHERE m.m_close > 0
        GROUP BY p.t, m.underlying
    """, [JUMP_LO, JUMP_HI]).fetchall()
    out = {(t, u): {"conv_c": cc, "conv_s": cs, "rolls": r, "flags": fl, "first_roll": fr, "days": n}
           for t, u, cc, cs, r, fl, fr, n in rows}
    divs = con.execute("""
        SELECT p.t, ca.symbol,
               SUM(CAST(json_extract_string(ca.raw_json, '$.Details') AS DOUBLE) / e.close)
        FROM per p
        JOIN eq.corporate_actions ca
          ON ca.action_type = 'DIVIDEND' AND ca.ex_date > p.t AND ca.ex_date <= p.t1
        JOIN eq.equity_bhavcopy e
          ON e.symbol = ca.symbol AND e.trade_date = p.t AND e.series = 'EQ' AND e.close > 0
        GROUP BY p.t, ca.symbol
    """).fetchall()
    for t, u, d in divs:
        if (t, u) in out and d is not None:
            out[(t, u)]["div"] = float(d)
    return out


def _simulate(label, lo, hi, z_weighted, con, comp):
    """The frozen run_net_spread._simulate_window loop, verbatim in its portfolio logic, with the
    period return evaluated under several return definitions and roll costs added alongside."""
    sig_rows = con.execute(f"""
        SELECT formation_date, underlying, z_carry_neut, fwd_ret_1m, raw_ann_basis
        FROM sig.signals
        WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
          AND z_carry_neut IS NOT NULL AND has_fwd AND liquid = TRUE
        ORDER BY formation_date, underlying
    """).fetchall()
    by_date = defaultdict(list)
    for fdate, u, z, fr, rb in sig_rows:
        by_date[fdate].append((u, float(z), fr, rb))
    fdates = sorted(by_date)

    def rets_for(fdate):
        m = {"spot": {}, "fut": {}, "fut_settle": {}, "div": {}}
        for u, _, fr, _ in by_date[fdate]:
            if fr is None:
                continue
            c = comp.get((fdate, u))
            m["spot"][u] = fr
            m["fut"][u] = (1 + fr) * (c["conv_c"] if c else 1.0) - 1
            m["fut_settle"][u] = (1 + fr) * (c["conv_s"] if c and c["conv_s"] else
                                             (c["conv_c"] if c else 1.0)) - 1
            m["div"][u] = c.get("div", 0.0) if c else 0.0
        return m

    state = NS.PortfolioState()
    prev = None
    prev_fdate = None
    is_first = True
    series = defaultdict(list)
    held_basis = defaultdict(list)
    fee_reb = slip_reb = fee_roll = slip_roll = 0.0
    turnovers = []
    missing_fut = total_held = flagged = 0

    for fdate in fdates:
        rows = [(u, z, fr) for u, z, fr, _ in by_date[fdate]]
        nq = max(1, round(NS.QUINTILE * len(rows)))
        adva = NS._load_adva(con, fdate, [r[0] for r in rows])
        filt = [r for r in rows if r[0] in adva]
        if len(filt) < 2 * nq:
            prev, prev_fdate, is_first = rets_for(fdate), fdate, False
            continue

        V_long = max(sum(state.long_positions.values()), 1e-6)
        V_short = max(sum(state.short_positions.values()), 1e-6)
        period_roll = 0.0
        if not is_first and prev:
            for key in ("spot", "fut", "fut_settle", "div"):
                gl = sum(cap * prev[key].get(u, 0.0) for u, cap in state.long_positions.items()) / V_long
                gs = sum(cap * prev[key].get(u, 0.0) for u, cap in state.short_positions.items()) / V_short
                series[f"{key}_long"].append(gl)
                series[f"{key}_short"].append(gs)
                series[key].append(gl - gs)
            for book, legs in ((state.long_positions, ("SELL", "BUY")),
                               (state.short_positions, ("BUY", "SELL"))):
                for u, cap in book.items():
                    total_held += 1
                    c = comp.get((prev_fdate, u))
                    if c is None:
                        missing_fut += 1
                        continue
                    flagged += 1 if c["flags"] else 0
                    for _ in range(c["rolls"]):
                        for side in legs:
                            f = NS._leg_fees(side=side, trade_value=cap, trade_date=c["first_roll"])
                            fee_roll += f["total"]
                            period_roll += f["total"]
                            s = (NS.SLIPPAGE_BP / 10000) * cap
                            slip_roll += s
                            period_roll += s

        long_t, short_t = NS._compute_targets(z_weighted, filt, adva, nq)
        w = list(long_t.values()) + list(short_t.values())
        band = NS.BAND_SIGMA * (float(np.std(w)) if len(w) > 1 else 0.0)
        reb_l = {u: (t if abs(t - state.long_positions.get(u, 0.0)) >= band
                     or state.long_positions.get(u, 0.0) == 0 else state.long_positions[u])
                 for u, t in long_t.items()}
        reb_s = {u: (t if abs(t - state.short_positions.get(u, 0.0)) >= band
                     or state.short_positions.get(u, 0.0) == 0 else state.short_positions[u])
                 for u, t in short_t.items()}

        abs_delta = 0.0
        for u in set(state.long_positions) | set(state.short_positions) | set(reb_l) | set(reb_s):
            abs_delta += abs(reb_l.get(u, 0.0) - state.long_positions.get(u, 0.0))
            abs_delta += abs(reb_s.get(u, 0.0) - state.short_positions.get(u, 0.0))
        turnovers.append(abs_delta / max(V_long + V_short, 1.0))

        period_reb = 0.0
        for new, old, buy_side in ((reb_l, state.long_positions, "BUY"),
                                   (reb_s, state.short_positions, "SELL")):
            for u in set(new) | set(old):
                delta = new.get(u, 0.0) - old.get(u, 0.0)
                if abs(delta) < 1e-6:
                    continue
                side = buy_side if delta > 0 else ("SELL" if buy_side == "BUY" else "BUY")
                f = NS._leg_fees(side=side, trade_value=abs(delta), trade_date=fdate)
                s = (NS.SLIPPAGE_BP / 10000) * abs(delta)
                fee_reb += f["total"]
                slip_reb += s
                period_reb += f["total"] + s

        if not is_first:
            series["cost_rebalance"].append(period_reb / NS.GROSS_EXPOSURE)
            series["cost_roll"].append(period_roll / NS.GROSS_EXPOSURE)

        rb = {u: b for u, _, _, b in by_date[fdate]}
        held_basis["long"].append(np.mean([rb[u] for u in reb_l if rb.get(u) is not None]))
        held_basis["short"].append(np.mean([rb[u] for u in reb_s if rb.get(u) is not None]))

        state.long_positions, state.short_positions = reb_l, reb_s
        prev, prev_fdate, is_first = rets_for(fdate), fdate, False

    return _summarize(label, z_weighted, series, held_basis, turnovers, fdates,
                      dict(fee_reb=fee_reb, slip_reb=slip_reb, fee_roll=fee_roll, slip_roll=slip_roll,
                           missing_fut=missing_fut, total_held=total_held, flagged=flagged))


def _ann(x):
    x = np.asarray(x)
    return float(np.prod(1 + x) ** (12.0 / len(x)) - 1) if len(x) else float("nan")


def _t(x):
    x = np.asarray(x)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 else float("nan")


def _summarize(label, zw, s, hb, turnovers, fdates, acc):
    spot, fut = np.array(s["spot"]), np.array(s["fut"])
    reb, roll = np.array(s["cost_rebalance"]), np.array(s["cost_roll"])
    net_spot = spot - reb
    net_fut = fut - reb - roll
    conv = fut - spot
    div = np.array(s["div"])
    return {
        "label": label, "z_weighted": zw, "formations": len(fdates), "periods": len(spot),
        "ann_gross_spot": _ann(spot), "ann_net_spot": _ann(net_spot),
        "ann_gross_fut": _ann(fut), "ann_gross_fut_settle": _ann(s["fut_settle"]),
        "ann_net_fut": _ann(net_fut),
        "mean_m": {k: float(np.mean(v)) for k, v in {
            "spot": spot, "fut": fut, "fut_settle": s["fut_settle"], "conv": conv, "div": div,
            "conv_ex_div": conv - div, "cost_rebalance": reb, "cost_roll": roll,
            "net_spot": net_spot, "net_fut": net_fut,
            "spot_long": s["spot_long"], "fut_long": s["fut_long"],
            "spot_short": s["spot_short"], "fut_short": s["fut_short"]}.items()},
        "t": {"spot": _t(spot), "fut": _t(fut), "conv": _t(conv), "net_fut": _t(net_fut),
              "net_spot": _t(net_spot)},
        "pos_months_net_fut": float((net_fut > 0).mean()),
        "held_raw_ann_basis": {"long": float(np.nanmean(hb["long"])), "short": float(np.nanmean(hb["short"]))},
        "avg_turnover": float(np.mean(turnovers[1:])) if len(turnovers) > 1 else float("nan"),
        "costs_rs": {k: acc[k] for k in ("fee_reb", "slip_reb", "fee_roll", "slip_roll")},
        "coverage": {"held_name_periods": acc["total_held"], "missing_fut": acc["missing_fut"],
                     "flagged_jump": acc["flagged"]},
    }


def _ic(con, comp, lo, hi):
    rows = con.execute(f"""
        SELECT formation_date, underlying, z_carry_neut, fwd_ret_1m FROM sig.signals
        WHERE formation_date >= DATE '{lo}' AND formation_date <= DATE '{hi}'
          AND z_carry_neut IS NOT NULL AND fwd_ret_1m IS NOT NULL AND liquid = TRUE
    """).fetchall()
    by = defaultdict(list)
    for f, u, z, r in rows:
        c = comp.get((f, u))
        if c:
            by[f].append((z, r, (1 + r) * c["conv_c"] - 1, c["conv_c"] - 1))
    out = {"spot": [], "fut": [], "conv": []}
    for f in sorted(by):
        a = np.array(by[f])
        if len(a) < 20:
            continue
        out["spot"].append(spearmanr(a[:, 0], a[:, 1])[0])
        out["fut"].append(spearmanr(a[:, 0], a[:, 2])[0])
        out["conv"].append(spearmanr(a[:, 0], a[:, 3])[0])
    return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)), "t": _t(v), "n": len(v)}
            for k, v in out.items()}


def main():
    con = _connect()
    print("building fenced basis panel + daily multipliers...")
    _daily_multipliers(con)
    periods = con.execute(f"""
        SELECT formation_date, fwd_formation_date FROM sigraw.formations
        WHERE fwd_formation_date <= DATE '{FENCE}' AND formation_date >= DATE '2016-03-31'
    """).fetchall()
    comp = _period_components(con, periods)
    print(f"  {len(comp):,} (formation, name) futures periods")
    maxd = con.execute("SELECT MAX(trade_date) FROM mult").fetchone()[0]

    results, ics = {}, {}
    for label, (lo, hi) in WINDOWS.items():
        ics[label] = _ic(con, comp, lo, hi)
        for zw in (False, True):
            key = f"{label}_{'zweighted' if zw else 'quintile'}"
            results[key] = _simulate(label, lo, hi, zw, con, comp)
            r = results[key]
            print(f"  {key}: spot gross {r['ann_gross_spot']:+.4%}  fut gross {r['ann_gross_fut']:+.4%}  "
                  f"net fut {r['ann_net_fut']:+.4%}")
    con.close()

    frozen = json.loads(FROZEN.read_text())["results"]
    repro = {k: (results[k]["ann_gross_spot"] - frozen[k]["ann_gross"],
                 results[k]["ann_net_spot"] - frozen[k]["ann_net"]) for k in results}
    _write(results, ics, repro, maxd)
    return 0


def _write(results, ics, repro, maxd):
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    L = []
    a = L.append
    a("# Carry — Futures Translation (TRAIN + HOLDOUT)\n")
    a(f"**Script-generated** — `scripts/signal_engine/carry/futures_translation.py`, commit `{commit}`, "
      f"run {date.today().isoformat()}. Descriptive measurement of the FROZEN book; no parameter, "
      f"signal or window changed. Price reads fenced at {FENCE}; max futures date read: **{maxd}**.\n")
    a("Portfolio logic imported from `run_net_spread.py` (targets, ADV cap, 0.25σ band, fee model). "
      "Futures return = frozen spot `fwd_ret_1m` × same-contract basis-ratio chain on the T-3-roll "
      "near-month contract (futures close). Roll cost = both legs of every T-3 roll at the fee model "
      "+ 5 bp/side slippage — a cost the frozen net spread does not charge.\n")
    a("## 0. Reproduction of the frozen spot numbers\n")
    a("| Book | Δ gross vs frozen | Δ net vs frozen |")
    a("|---|--:|--:|")
    for k, (dg, dn) in repro.items():
        a(f"| {k} | {dg*1e4:+.4f} bp | {dn*1e4:+.4f} bp |")
    a("")
    for zw in ("quintile", "zweighted"):
        a(f"## 1{'a' if zw == 'quintile' else 'b'}. Annualised spread — {zw}\n")
        a("| Window | Gross spot (t) | Gross futures (t) | Gross fut (settle) | Net spot (frozen) | Net futures | t net fut | % months net fut > 0 |")
        a("|---|--:|--:|--:|--:|--:|--:|--:|")
        for w in WINDOWS:
            r = results[f"{w}_{zw}"]
            a(f"| {w} | {r['ann_gross_spot']:+.2%} ({r['t']['spot']:+.2f}) | {r['ann_gross_fut']:+.2%} "
              f"({r['t']['fut']:+.2f}) | {r['ann_gross_fut_settle']:+.2%} | "
              f"{r['ann_net_spot']:+.2%} | **{r['ann_net_fut']:+.2%}** | {r['t']['net_fut']:+.2f} | "
              f"{r['pos_months_net_fut']:.0%} |")
        a("")
        a("Mean monthly Q5−Q1 decomposition (bp/month): futures = spot + convergence; "
          "convergence = ordinary-dividend component + residual basis/roll component.\n")
        a("| Window | Spot | Convergence (t) | of which dividend | of which residual basis + roll | Futures | Rebalance cost | Roll cost | Net futures |")
        a("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
        for w in WINDOWS:
            r = results[f"{w}_{zw}"]
            m = r["mean_m"]
            a(f"| {w} | {m['spot']*1e4:+.1f} | {m['conv']*1e4:+.1f} ({r['t']['conv']:+.2f}) | {m['div']*1e4:+.1f} | "
              f"{m['conv_ex_div']*1e4:+.1f} | {m['fut']*1e4:+.1f} | {-m['cost_rebalance']*1e4:.1f} | "
              f"{-m['cost_roll']*1e4:.1f} | {m['net_fut']*1e4:+.1f} |")
        a("")
        a("| Window | Long spot | Long futures | Short spot | Short futures | Held raw ann. basis, long / short | Turnover | Coverage (missing fut / held) | Jump-flagged periods |")
        a("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
        for w in WINDOWS:
            r = results[f"{w}_{zw}"]
            m, hb, c = r["mean_m"], r["held_raw_ann_basis"], r["coverage"]
            a(f"| {w} | {m['spot_long']*1e4:+.1f} | {m['fut_long']*1e4:+.1f} | {m['spot_short']*1e4:+.1f} | "
              f"{m['fut_short']*1e4:+.1f} | {hb['long']:+.2%} / {hb['short']:+.2%} | {r['avg_turnover']:.3f} | "
              f"{c['missing_fut']} / {c['held_name_periods']} | {c['flagged_jump']} |")
        a("")
    a("## 2. Rank IC of frozen `z_carry_neut` (all eligible names, per formation)\n")
    a("| Window | vs spot return | vs futures return | vs convergence alone | n |")
    a("|---|--:|--:|--:|--:|")
    for w, ic in ics.items():
        a(f"| {w} | {ic['spot']['mean']:+.4f} (t {ic['spot']['t']:+.2f}) | "
          f"{ic['fut']['mean']:+.4f} (t {ic['fut']['t']:+.2f}) | "
          f"{ic['conv']['mean']:+.4f} (t {ic['conv']['t']:+.2f}) | {ic['spot']['n']} |")
    a("")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    SNAPSHOT.write_text(json.dumps({"commit": commit, "fence": str(FENCE), "max_date_read": str(maxd),
                                    "reproduction_bp": {k: [v[0] * 1e4, v[1] * 1e4] for k, v in repro.items()},
                                    "results": results, "ic": ics}, indent=2, default=str), encoding="utf-8")
    print(f"report: {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
