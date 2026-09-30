"""BKV-1 worked examples (post-primary presentation; NOT frozen, computes nothing that enters a label).

Produces results/worked_examples.md: (1) one B event and one C event reconstructed from RAW as-traded bhavcopy rows with
the arithmetic written out, (2) the market benchmark for that event's date, (3) the Newey-West computation of one
headline cell, number by number, (4) the fee arithmetic.
"""
from __future__ import annotations

import math

import duckdb
import numpy as np
import pandas as pd
from scipy import stats as sst

from scripts.breakout_vol import common as C
from scripts.breakout_vol import engine as G
from scripts.breakout_vol.common import P

OUT = C.OUT_DIR / "results"


def pick(ev, sessions, con, panel, arm, kind, N, stage="VAL", H=5):
    lo, hi = G.stage_bounds(sessions, stage)
    e = ev[(ev["arm"] == arm) & (ev["kind"] == kind) & (ev["N"] == N) & (ev["t"] >= lo + 200) & ev[f"status{H}"].eq(0)]
    ents = e["entity"].unique()
    for r in e.sort_values("t").itertuples():
        syms = panel[(panel["entity"] == r.entity)]["symbol"].unique()
        if len(syms) != 1:
            continue
        sym = syms[0]
        d0 = pd.Timestamp(sessions[r.t - 83]).date()
        d1 = pd.Timestamp(sessions[r.t + 21]).date()
        if con.execute("SELECT count(*) FROM adjustment_factors WHERE symbol=? AND ex_date BETWEEN ? AND ?", [sym, d0, d1]).fetchone()[0] == 0:
            return r, sym
    raise RuntimeError("no event")


def event_block(r, sym, sessions, con, H=5) -> str:
    sess = [pd.Timestamp(x).date() for x in sessions]
    t, N = int(r.t), int(r.N)
    d0, d1 = sess[t - N], sess[t + H]
    raw = con.execute("""SELECT trade_date, open, close, volume FROM equity_bhavcopy WHERE symbol=? AND series IN ('EQ','BE')
                         AND trade_date BETWEEN ? AND ? ORDER BY trade_date""", [sym, sess[t - 20], d1]).fetchall()
    by = {a: (o, c, v) for a, o, c, v in raw}
    closes = [(sess[t - k], by[sess[t - k]][1]) for k in range(N, 0, -1)]
    vols = [(sess[t - k], by[sess[t - k]][2]) for k in range(20, 0, -1)]
    lvl = max(c for _, c in closes) if r.kind == "up" else min(c for _, c in closes)
    sv = sorted(v for _, v in vols)
    med = (sv[9] + sv[10]) / 2
    ct, vt = by[sess[t]][1], by[sess[t]][2]
    o1, cH = by[sess[t + 1]][0], by[sess[t + H]][1]
    R = cH / o1 - 1
    s = 1 if r.kind == "up" else -1
    L = []
    L.append(f"**Event:** {r.entity} ({sym}), formation session t = {sess[t]}, N = {N}, {r.kind.upper()} breakout, arm **{r.arm}**, H = {H}.")
    L.append("")
    L.append(f"1. Range: the {N} closes {closes[0][0]} … {closes[-1][0]} (raw, as traded; no corporate action in the span) have "
             f"{'max' if r.kind == 'up' else 'min'} = **{lvl:.2f}**. Close on t = **{ct:.2f}** → "
             f"{'C_t > max' if r.kind == 'up' else 'C_t < min'} ✓ (margin {abs(ct / lvl - 1) * 1e4:.1f} bp). Ledger level {r.ref_level:.4f} (adjusted; ratio close/level − 1 = {r.close / r.ref_level - 1:.6f} vs raw {ct / lvl - 1:.6f}).")
    L.append(f"2. Volume: the 20 prior volumes sorted, the 10th and 11th are {sv[9]:,.0f} and {sv[10]:,.0f} → median = **{med:,.1f}**; V_t = **{vt:,.0f}** → AV = {vt:,.0f} / {med:,.1f} = **{vt / med:.4f}** "
             f"({'≥' if vt / med >= 2 else '<'} 2.0 → {'ABN → B' if vt / med >= 2 else 'not abnormal → C'}). Ledger AV = {r.av:.4f}.")
    L.append(f"3. Entry open t+1 ({sess[t + 1]}) = **{o1:.2f}**; exit close t+{H} ({sess[t + H]}) = **{cH:.2f}** → R = {cH:.2f} / {o1:.2f} − 1 = **{R * 1e4:.2f} bp** (ledger {getattr(r, f'R{H}') * 1e4:.2f} bp).")
    rm = getattr(r, f"Rm{H}")
    L.append(f"4. Benchmark R_m(t, {H}) from the ledger = **{rm * 1e4:.2f} bp** (equal-weight mean over the PIT members with a resolved window; see block below).")
    L.append(f"5. f = sign · (R − R_m) = {s:+d} · ({R * 1e4:.2f} − {rm * 1e4:.2f}) = **{s * (R - rm) * 1e4:.2f} bp** (ledger f{H} = {getattr(r, f'f{H}'):.2f} bp).")
    return "\n".join(L)


def benchmark_block(ev_t, sessions, con, panel_tag="dev", t=None, H=5) -> str:
    pn = G.load_panel(panel_tag)
    wr = G.window_returns(pn, H)
    ok = pn.member[:, t] & np.isfinite(wr["R"][:, t]) & np.isin(wr["status"][:, t], (0, 1))
    Rs = wr["R"][ok, t]
    return (f"Benchmark for t = {pd.Timestamp(sessions[t]).date()}, H = {H}: PIT members with a resolved window = **{int(ok.sum())}**; "
            f"Σ R = {Rs.sum():.6f}; R_m = Σ R / n = {Rs.sum():.6f} / {int(ok.sum())} = **{Rs.mean() * 1e4:.4f} bp**; "
            f"check Σ (R − R_m) = {(Rs - Rs.mean()).sum():.2e} (identically 0). First 5 members: "
            + ", ".join(f"{pn.entities[i]} {wr['R'][i, t] * 1e4:.1f} bp" for i in np.nonzero(ok)[0][:5]) + ".")


def nw_block(cell, coh) -> str:
    g = coh[(coh["N"] == cell.N) & (coh["H"] == cell.H) & (coh["side"] == cell.side)].sort_values("t")
    x, pos, H = g["d"].to_numpy(), g["t"].to_numpy(), int(cell.H)
    n = len(x)
    mean = x.mean()
    z = x - mean
    dense = np.zeros(pos[-1] - pos[0] + 1)
    dense[pos - pos[0]] = z
    g0 = z @ z / n
    rows, lrv = [], g0
    for k in range(1, H + 1):
        gk = dense[:-k] @ dense[k:] / n
        w = 1 - k / (H + 1)
        lrv += 2 * w * gk
        rows.append((k, gk, w, 2 * w * gk))
    se = math.sqrt(lrv / n)
    t = mean / se
    p = sst.t.sf(t, n - 1)
    L = [f"**Cell VAL, N={cell.N}, H={cell.H}, side={cell.side}** — paired formation dates n = **{n}**.", "",
         f"* d̄ = Σ d(t) / n = {x.sum():.4f} / {n} = **{mean:.4f} bp**",
         f"* g₀ = Σ (d−d̄)² / n = {z @ z:.2f} / {n} = {g0:.4f}", ""]
    L.append("| k | g_k = Σ(pairs k sessions apart) z_i z_j / n | weight 1−k/(H+1) | contribution 2·w·g_k |")
    L.append("|---|---|---|---|")
    for k, gk, w, c in rows:
        L.append(f"| {k} | {gk:.4f} | {w:.4f} | {c:.4f} |")
    L += ["", f"* LRV = g₀ + Σ contributions = **{lrv:.4f}**; SE = √(LRV / n) = √({lrv:.4f} / {n}) = **{se:.4f} bp**",
          f"* t = d̄ / SE = {mean:.4f} / {se:.4f} = **{t:.4f}**; one-sided p = P(T₍{n - 1}₎ > t) = **{p:.4f}**",
          f"* Table values: d̄ = {cell.d_mean:.4f}, SE = {cell.d_se:.4f}, t = {cell.d_t:.4f}, p = {cell.d_p_one:.4f}."]
    L += ["", "First five and last three cohort observations (date, n_B, n_C, m_B, m_C, d = m_B − m_C):", "",
          "| date | n_B | n_C | m_B (bp) | m_C (bp) | d (bp) |", "|---|---|---|---|---|---|"]
    for r in list(g.head(5).itertuples()) + list(g.tail(3).itertuples()):
        L.append(f"| {str(r.date)[:10]} | {int(r.n_B)} | {int(r.n_C)} | {r.m_B:.2f} | {r.m_C:.2f} | {r.d:.2f} |")
    return "\n".join(L)


def main() -> None:
    pn = G.load_panel("dev")
    ev = pd.read_parquet(OUT / "events_VAL.parquet")
    panel = pd.read_parquet(C.OUT_DIR / "panel_dev.parquet", columns=["entity", "symbol"]).drop_duplicates()
    con = duckdb.connect(str(C.EQUITY_DB), read_only=True)
    parts = ["# BKV-1 worked examples (generated by `worked_examples.py`)", ""]
    for arm, kind, N in (("B", "up", 20), ("C", "up", 20)):
        r, sym = pick(ev, pn.sessions, con, panel, arm, kind, N)
        parts += [f"## Event example — arm {arm}, {kind}, N={N}", "", event_block(r, sym, pn.sessions, con), "", benchmark_block(ev, pn.sessions, con, "dev", int(r.t)), ""]
    cells = pd.read_csv(OUT / "cells_VAL.csv")
    coh = pd.read_csv(OUT / "cohort_VAL.csv")
    c = cells[(cells.N == 20) & (cells.H == 5) & (cells.side == "up")].iloc[0]
    parts += ["## Headline-cell aggregation and Newey–West arithmetic", "", nw_block(c, coh), ""]
    v = con.execute("SELECT 1").fetchone()
    from scripts.breakout_vol.verify_independent import vp6_fee_by_hand
    f = vp6_fee_by_hand()
    parts += ["## Fee arithmetic (one BUY 2019-06-03, one SELL 2019-06-12, ₹5,00,000 each)", "",
              f"BUY: STT {f['components_buy_rs']['stt']:.2f} + exchange {f['components_buy_rs']['exchange']:.4f} + SEBI {f['components_buy_rs']['sebi']:.2f} + stamp {f['components_buy_rs']['stamp']:.2f} + GST {f['components_buy_rs']['gst']:.4f} = ₹{f['hand_buy_rs']:.4f} (library ₹{f['lib_buy_rs']:.4f}).",
              f"SELL: STT 500.00 + exchange 17.25 + SEBI 0.50 + GST 3.195 + DP 13.5×1.18 = ₹{f['hand_sell_rs']:.4f} (library ₹{f['lib_sell_rs']:.4f}).",
              f"Round trip = ₹{f['hand_buy_rs'] + f['hand_sell_rs']:.2f} / ₹5,00,000 = **{f['round_trip_bp']:.2f} bp** of notional, before slippage.", ""]
    (OUT / "worked_examples.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts)[:6000])


if __name__ == "__main__":
    main()
