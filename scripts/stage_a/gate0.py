"""Stage A — Gate 0 screen. Reads NO market data.

Three free screens per STAGE_A_DISCOVERY_LAB_DESIGN.md section 6:
  0a cost floor  — era-accurate futures fees (frozen module) + measured
                   slippage/basis lanes from A_COST_SUBSTRATE_MEASUREMENTS.md
  0b prior expos — textual, carried in the report body
  0c provisional — the annualized net Sharpe required for power 0.80 at the
     RFA          FIRST alpha-bearing gate, plus the per-family cost drag

Key arithmetic: ncp = S_ann * sqrt(T), so cadence cancels. The required NET
annualized Sharpe is therefore ONE number per gate, identical for every family,
density and conditioning scheme. Families differ only in how much gross Sharpe
the fixed round-trip cost consumes.

Output: docs/reports/STAGE_A_GATE0_SCREEN.md
Usage:  python scripts/stage_a/gate0.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import breakeven_round_trip_bps
from scripts.rfa.power import power_at

# --- frozen inputs (traceable; none measured here) --------------------------
CANONICAL_PRICE, CANONICAL_QTY = 1000.0, 20_000    # Rs 2Cr, A's canonical
SLIP_BP_PER_SIDE = (0.66, 0.78)   # A_COST_SUBSTRATE_MEASUREMENTS.md p90
BASIS_MEAN_BP = 0.4               # A D5
POWER_HURDLE = 0.80
SD_FULL_BP = 100.0                # external anchor (A declaration)
H_FULL_MIN = 313                  # A's hold, 10:01 -> 15:14
BASE_CADENCE = 237                # tradeable sessions/yr (A, measured)

GATES = (("HOLDOUT 2019-2022  (first alpha gate under Stage A)", 988),
         ("TRAIN   2012-2018  (if it still carried alpha)", 1699),
         ("SEALED  2023-today", 873),
         ("SEALED  at A's power floor", 1270))

FENCES = (("DISCOVERY 2012-2018", "2012-01-02", "2018-12-31"),
          ("HOLDOUT   2019-2022", "2019-01-01", "2022-12-31"),
          ("SEALED    2023-today", "2023-01-01", "2026-08-21"),
          ("CURRENT   2024-10+", "2024-10-01", "2026-08-21"))

# Anchors — all operator-ratified or repo-measured; none invented here.
# A's band was declared on NET per-trade Sharpe, so net and gross must not be
# compared across each other. Both are carried explicitly.
A_NET_BP = 1.271397244236667       # trial_ledger.jsonl, w45 TRAIN (script-generated)
A_GROSS_BP_NARRATIVE = 4.41        # A_HOLDOUT_CLOSURE.md decomposition (see caveat)
A_BAND_NET = (0.70, 1.075, 1.45)   # ratified declaration band, NET S_ann

ANCHOR_A_NET = A_NET_BP / SD_FULL_BP * np.sqrt(BASE_CADENCE)
ANCHOR_A_GROSS_NARR = A_GROSS_BP_NARRATIVE / SD_FULL_BP * np.sqrt(BASE_CADENCE)


def mean_fee_bp(lo: str, hi: str):
    d, e, vals = date.fromisoformat(lo), date.fromisoformat(hi), []
    while d <= e:
        if d.weekday() < 5:
            vals.append(breakeven_round_trip_bps(
                price=CANONICAL_PRICE, quantity=CANONICAL_QTY, trade_date=d))
        d += timedelta(days=1)
    return float(np.mean(vals)), float(min(vals)), float(max(vals))


def cost_lane_bp(fee_bp: float):
    return (fee_bp + 2 * SLIP_BP_PER_SIDE[0] + BASIS_MEAN_BP,
            fee_bp + 2 * SLIP_BP_PER_SIDE[1] + BASIS_MEAN_BP)


def required_per_trade_sharpe(n: int) -> float:
    lo, hi = 1e-6, 3.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if power_at(mid, 1.0, n, False) < POWER_HURDLE:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sd_at(horizon_min: float) -> float:
    return SD_FULL_BP * np.sqrt(horizon_min / H_FULL_MIN)


@dataclass(frozen=True)
class Scenario:
    family: str
    label: str
    horizon_min: float
    events_per_active_session: float
    session_fraction: float
    independence: float
    note: str


SCENARIOS = (
    Scenario("F-OPEN", "A's design (EOD hold, 1/session)", 313, 1, 1.00, 1.0,
             "the construct that was actually run"),
    Scenario("F-OPEN", "short-horizon variant", 60, 1, 1.00, 1.0, "same event, 60m"),
    Scenario("F-GAP", "large-gap conditioned, EOD hold", 313, 1, 0.33, 1.0,
             "tercile conditioning"),
    Scenario("F-VOL", "vol-state conditional", 120, 2, 0.50, 0.6,
             "vol states persist"),
    Scenario("F-RANGE", "breakout", 60, 2, 0.40, 0.6, "range extremes"),
    Scenario("F-RANGE", "failed breakout", 60, 1, 0.25, 1.0, "rarer, cleaner"),
    Scenario("F-TOD", "time-of-day bucket, standalone", 60, 1, 1.00, 1.0,
             "weak standalone"),
    Scenario("F-REL", "N/BN divergence, 30-min", 30, 4, 0.60, 0.5,
             "densest defensible"),
    Scenario("F-REL", "N/BN divergence, 15-min", 15, 8, 0.70, 0.4,
             "density up, edge down"),
)

# Diagnostic only — these LEAVE the intraday quadrant (overnight risk).
MULTIDAY = (2, 3, 5, 10)


def main() -> None:
    fees = {lab: mean_fee_bp(lo, hi) for lab, lo, hi in FENCES}
    curr = cost_lane_bp(fees["CURRENT   2024-10+"][0])
    cost_mid = (curr[0] + curr[1]) / 2

    # cadence-invariant required NET annualized Sharpe, per gate
    gate_req = []
    for lab, n in GATES:
        s_pt = required_per_trade_sharpe(n)
        gate_req.append((lab, n, s_pt * np.sqrt(BASE_CADENCE)))
    req_net_ann = gate_req[0][2]          # HOLDOUT — the governing gate

    out = []
    w = out.append
    w("# Stage A — Gate 0 Screen (script-generated)\n")
    w(f"**Generated:** {date.today().isoformat()} by `scripts/stage_a/gate0.py`  ")
    w("**Data read: NONE.** Fee schedules, declared anchors, and power arithmetic only.  ")
    w("**Status:** a screen, not a result. Nothing here measures any phenomenon.\n")

    w("## 0a — Cost floor (era-accurate, frozen fee module)\n")
    w("Round-trip futures cost at the canonical Rs 2Cr notional "
      "(`core/execution/futures/futures_fees.py`), plus the measured slippage lane "
      f"({SLIP_BP_PER_SIDE[0]}-{SLIP_BP_PER_SIDE[1]} bp/side, both sides) and the D5 "
      f"basis mean ({BASIS_MEAN_BP} bp).\n")
    w("| Window | Fees mean | min | max | Round-trip cost lane |")
    w("|---|---:|---:|---:|---:|")
    for lab, _, _ in FENCES:
        m, mn, mx = fees[lab]
        c = cost_lane_bp(m)
        w(f"| {lab} | {m:.3f} | {mn:.3f} | {mx:.3f} | **{c[0]:.2f}-{c[1]:.2f} bp** |")
    w("")
    w(f"**Applied cost floor (current era, midpoint): {cost_mid:.2f} bp round trip.**\n")

    w("## 0c — The invariant: required NET annualized Sharpe per gate\n")
    w("`ncp = S_ann * sqrt(T)`, so cadence cancels. The Sharpe required for power "
      f"{POWER_HURDLE} at one-sided a=0.05 therefore depends ONLY on the gate's "
      "calendar length — **not** on horizon, event density, or conditioning. Every "
      "family in the slate faces the identical bar.\n")
    w("| Gate | n (1 trade/session) | Required NET S_ann |")
    w("|---|---:|---:|")
    for lab, n, s in gate_req:
        w(f"| {lab} | {n} | **{s:.3f}** |")
    w("")
    w(f"**The governing number is {req_net_ann:.2f}** — the net annualized Sharpe a "
      "construct must deliver to be settleable at HOLDOUT. It does not move if you "
      "trade more often, condition harder, or pick a different horizon.\n")
    w("**Judged against A's ratified NET band** (the only operator-approved effect band "
      "for this substrate) — like for like, net against net:\n")
    w(f"- pessimistic {A_BAND_NET[0]:.2f} — **below** the {req_net_ann:.2f} requirement")
    w(f"- central {A_BAND_NET[1]:.3f} — **below** the requirement (this is the "
      "section-8 defect: HOLDOUT cannot settle the central case)")
    w(f"- optimistic {A_BAND_NET[2]:.2f} — **above** the requirement (which is why the "
      "RFA returned PROCEED at the optimistic corner)\n")
    w(f"So under the section-8 amendment (**judge at the central corner**), the HOLDOUT "
      f"gate cannot settle ANY construct on this substrate whose honest central net "
      f"S_ann is below {req_net_ann:.2f}. That is family-invariant and is the first "
      "Gate-0 finding.\n")
    w(f"**The only same-substrate empirical anchor** is A's own realized TRAIN net: "
      f"{A_NET_BP:.3f} bp/trade (`trial_ledger.jsonl`, script-generated) = S_ann "
      f"**{ANCHOR_A_NET:.2f}** — **{req_net_ann/ANCHOR_A_NET:.1f}x below** the "
      f"requirement. For reference RS-MOM was abandoned for requiring S_ann >= 1.30.\n")

    w("## 0c (cont.) — Where the families differ: the cost drag\n")
    w("Cost is a **fixed** bp charge per round trip, so in Sharpe terms its bite grows "
      "as the horizon shrinks: `drag_ann = (cost_bp / SD_horizon) * sqrt(cadence)`. "
      "Required **gross** S_ann = required net + drag.\n")
    # Gross ceiling, derived (not invented): the gross Sharpe implied by A's
    # ratified optimistic NET corner at A's own cost drag.
    a_drag = (cost_mid / SD_FULL_BP) * np.sqrt(BASE_CADENCE)
    ceiling_gross = A_BAND_NET[2] + a_drag
    w(f"**Gross ceiling used below: {ceiling_gross:.2f}** — derived, not invented: A's "
      f"ratified optimistic NET corner ({A_BAND_NET[2]:.2f}) plus A's own cost drag "
      f"({a_drag:.2f}). It is the most generous GROSS reading the operator has ever "
      "approved for this substrate.\n")
    w("| Family | Scenario | Horizon | Trades/yr | SD | Cost drag | **Req. GROSS S_ann** | vs A measured | Verdict |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---|")
    n_ok = 0
    for sc in SCENARIOS:
        k_eff = 1 + (sc.events_per_active_session - 1) * sc.independence
        cadence = BASE_CADENCE * sc.session_fraction * k_eff
        sd = sd_at(sc.horizon_min)
        drag = (cost_mid / sd) * np.sqrt(cadence)
        gross = req_net_ann + drag
        ok = gross <= ceiling_gross
        n_ok += ok
        w(f"| {sc.family} | {sc.label} | {sc.horizon_min:.0f}m | {cadence:.0f} | "
          f"{sd:.0f} bp | {drag:.2f} | **{gross:.2f}** | "
          f"{gross/ANCHOR_A_GROSS_NARR:.1f}x | "
          f"{'PLAUSIBLE' if ok else 'IMPLAUSIBLE'} |")
    w("")
    w(f"**Families clearing the ratified gross ceiling ({ceiling_gross:.2f}): {n_ok} of "
      f"{len(SCENARIOS)}.** The \"vs A measured\" column is the multiple of A's TRAIN "
      f"gross S_ann ({ANCHOR_A_GROSS_NARR:.2f}) each family would have to deliver.\n")
    w("> **Caveat on A's gross figure.** `A_HOLDOUT_CLOSURE.md` decomposes TRAIN as "
      f"gross +{A_GROSS_BP_NARRATIVE} bp, fees ~1.8 bp, slippage 1.46 bp, net "
      f"+{A_NET_BP:.2f} bp. That does not reconcile: the frozen fee module A's own code "
      f"calls returns a **{fees['DISCOVERY 2012-2018'][0]:.3f} bp** mean over TRAIN, not "
      "1.8 bp, and 4.41 - 4.53 is negative where the ledger records +1.27. The ledger's "
      "**net** is script-generated and trusted; the narrative **gross** is not. Treat "
      "A's gross S_ann as a range ~0.68–0.89 and the multiples above as indicative. "
      "Flagged for the operator; not resolved here (resolving it is a DISCOVERY read).\n")

    w("### Diagnostic — where the cost drag stops binding (leaves the intraday quadrant)\n")
    w("Holding across sessions amortizes one round trip over a larger move. This is the "
      "ISD reassessment's option (b), **not** intraday, and it carries overnight risk "
      "the intraday quadrant does not.\n")
    w("| Hold | Trades/yr | SD | Cost drag | Req. GROSS S_ann |")
    w("|---|---:|---:|---:|---:|")
    for d in MULTIDAY:
        cadence = BASE_CADENCE / d
        sd = SD_FULL_BP * np.sqrt(d)
        drag = (cost_mid / sd) * np.sqrt(cadence)
        w(f"| {d} sessions | {cadence:.0f} | {sd:.0f} bp | {drag:.2f} | "
          f"**{req_net_ann + drag:.2f}** |")
    w("")
    w(f"The drag falls toward zero, but the floor never goes below the invariant "
      f"**{req_net_ann:.2f}** net. Longer holds fix the *cost* problem and leave the "
      "*demonstrability* problem untouched.\n")
    Path(ROOT / "docs" / "reports" / "STAGE_A_GATE0_SCREEN.md").write_text(
        "\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
