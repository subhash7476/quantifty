# DW-1 "Dealer-Wall" — Pre-Registration Spec (v2, pending review)

**Status:** DRAFT v2 — updated for the 2026-08-12 review. **Not frozen.**
**Branch:** `feat/options-wall`
**Date:** 2026-08-12
**Review:** incorporated (2026-08-12 review — 7 defects, all accepted or refined below).

---

## 0. Review disposition summary

| # | Review defect | Disposition |
|---|---------------|-------------|
| 1 | ρ≈0 pooling indefensible → S wall ~1.3 (RS-MOM wall) | **ACCEPTED** — §2 rewritten; honest bands → expected RFA ABANDON |
| 2 | Zero BankNifty rows in options bhavcopy | **ACCEPTED** — verified in DB (`SELECT DISTINCT symbol` → only `NIFTY`) §7 |
| 3 | Weekly formations impossible pre-2019 → TRAIN ~208 NIFTY-only, not ~718 | **ACCEPTED** — verified (2016=25, 2017=27, 2018=26 monthly-era; 2019=68, 2020=73) §7 |
| 4 | 13:00 seam un-reconstructable from EOD bhavcopy — coherence defect | **ACCEPTED** — §8 resolves: EOD-overnight formation OR Tier-2-forward-only; no hybrid |
| 5 | No tail/MaxDD gate for short-premium | **ACCEPTED** — §8 adds MaxDD / R-drawdown gate (F1 lesson) |
| 6 | Prior exposure (live GEX/PCR dashboard across sealed window) under-disclosed | **ACCEPTED** — §2 disclosure added, rs_mom/cb_n50 style |
| 7 | No GEX construction-parity gate (bhavcopy-recon vs Upstox) | **ACCEPTED** — §8 adds parity gate pre-any-gate (CARRY lesson) |

---

## 1. The Edge (testable claim)

> "NSE index dealer positioning — net dealer gamma, zero-gamma flip, pin, call/put
> walls — predicts short-horizon index behavior enough to clear option fees."

| Regime | Phenomenon | Posture |
|--------|-----------|---------|
| Positive GEX (stable) | Price attracted to high-gamma **pin**, absorbed by **walls** | **Short premium** into the pin (theta collection) |
| Negative GEX (amplifying) | Price breaking the **flip / thin-gamma gap** gets chased by dealer hedging | **Long premium / directional spreads** on the break |

Regime sign = single conditioning variable.

---

## 2. Decision Registry + Statistical Reality (REWRITTEN)

| # | Decision | Value |
|---|----------|-------|
| D1 | Universe | Nifty (Tue expiry). **BankNifty REMOVED from Tier-1** — zero rows in `options_bhavcopy.duckdb`; forward-only if ever added |
| D2 | Gamma posture | Regime-adaptive (both) |
| D3 | Formation | **Must be resolved at freeze (defect 4):** (a) weekly-expiry EOD/overnight formation, or (b) Tier-2 intraday forward-paper only. A 13:00-seam trade **cannot** be validated on EOD bhavcopy |
| D4 | Substrate | Tier-1 EOD bhavcopy reconstruction — **NIFTY only** |
| D5 | Statistical framing | `per_trade_pnl` on a single index series. **Pooling bonus NOT available** (see below) |

### Prior-exposure disclosure (defect 6)
The operator has run the live options dashboard (PCR / net GEX / Max Pain, CLAUDE.md
"Options Analysis Dashboard — In Progress") across the 2023→present sealed window and
has watched live Nifty GEX/flip/wall behaviour. That is de facto exposure to the
wall-state dynamics this hypothesis targets, even though no formal regression was run.
Disclosed per the `rs_mom` / `cb_n50` declaration precedent.

### The power arithmetic (verified, load-bearing)
- Nifty/BankNifty index returns ρ ≈ 0.85 → the √2 pooling bonus collapses to `√(2/(1+0.85))`
  ≈ **1.04**. Two-leg pooling does not rescue this construct.
- More decisively: D1 now removes BankNifty from Tier-1, so there is **no second leg at all**.
  NIFTY-only, SEALED 2023→present:
  - `ncp = S·√T`, `T ≈ 3.6 yr`, need `ncp ≈ 2.4–2.7` for power 0.80
  - → requires per-trade Sharpe **S ≥ 1.31–1.44** — the RS-MOM wall (RS_MOM_RFA: S≥1.31).
- Honest Sharpe band for a 2h weekly short/momentum index-option trade: **0.2–0.6**
  → **max achievable power ≈ 0.31**.
- **Expected RFA verdict: ABANDON.** The pre-check is 0 data reads and free; this is the
  correct place for it to fire. Do not freeze a construct that cannot clear the pre-check.

---

## 3. Wall-State Features
Per index, computed at the formation seam (EOD chain state for option (a); live chain
for (b)): `S, G, F, P, CW, PW, γ(P)`, `DTE`.

---

## 4. Signal Rulebook (draft — thresholds are freeze inputs)
1. `R = +1` if `G > 0`, `−1` if `G < 0`.
2. **Short branch (R=+1):** short iron fly at `P` if `|S−P| < 0.5%·S` and `γ(P) > conv`;
   else short strangle `[PW, CW]` if inside.
3. **Long branch (R=−1):** call spread `[F→CW]` if `S>F`; put spread `[PW→F]` if `S<F`;
   entry only within `n_bars` of a flip cross.
4. **No-trade:** `γ(P)` below threshold, VIX skip, audit guards (reverse-divergence /
   one-directional-only). **`DTE=0` clause deleted** — contradicts entering on expiry-day
   seam (review defect 4); replaced by an explicit exit-time rule at freeze.
5. **Exit:** TP at `pct` credit, SL `mult` × risk, time hard-exit at freeze.

---

## 5. Sizing & Risk
Max 2 lots / structure; 25% margin budget; portfolio delta cap 500; R pinned.

---

## 6. Fee Model (index options, era-accurate)
Flat ₹20/order; **STT on premium** (sell leg); exchange charges; SEBI; GST 18%; stamp on
sell. Rates pinned to NSE/NSE-IT at freeze. `delivery_fees.py` is equity — not reusable;
new module required.

---

## 7. Tier-1 Substrate — VERIFIED REALITY (defect 2/3 corrected)
Sources:
- `data/market_data/options_bhavcopy.duckdb` (5,490,319 rows; 2016-02-11 → 2026-07-17;
  **symbols = {NIFTY} only**, verified 2026-08-12)
- index EOD candles (Nifty 2012+)
- Black-Scholes IV solver → per-contract gamma → GEX/strike → aggregate flip/pin/walls

**Formation capacity (verified):**
| Year | Distinct Nifty expiries |
|------|-------------------------|
| 2016 | 25 (monthly era) |
| 2017 | 27 |
| 2018 | 26 |
| 2019 | 68 (weeklies begin ~Feb) |
| 2020 | 73 |
| 2021 | 73 |
| 2022 | 72 |

- **No weekly seam before 2019.** TRAIN 2019–2022 NIFTY-only ≈ **~208** weekly formations,
  not the earlier ~718 pooled.
- SEALED NIFTY-only ≈ **~187** weekly formations (2023→2026-08), not 374.
- Every n in §8 is revised to these verified counts.
- BankNifty: **not obtainable for Tier-1** (no rows). Would be forward-only (Tier-2) if ever
  added — which also forfeits any pooling (per §2).

---

## 8. Validation Protocol (mirrors repo governance; tail + parity gates added)

| Stage | Window | n (NIFTY weekly) | Gate |
|-------|--------|------------------|------|
| RFA pre-check | — | 0 data reads | power ≥ 0.80 at honest band + ρ haircut. **Expected: ABANDON** |
| Parity gate (new) | overlapping dates | — | reconstructed-GEX vs Upstox GEX parity before any gate fires (CARRY precedent) |
| TRAIN | 2019–2022 | ~208 | sign discovery on regime gate; sensitivity across banded thresholds |
| HOLDOUT | 2023 | ~54 | IC/spread + AC₁ |
| SEALED | 2023-08→present | ~120 | one-shot, frozen thresholds, never re-run |

**Tail / drawdown gates (defect 5, F1 lesson):**
- MaxDD gate on TRAIN net P&L (return/MaxDD ≥ pinned floor) — short-premium admits
  survivable-looking but tail-fragile SEALED "passes".
- R-normalized MaxDD across structures; log the top-loss event per regime.
- `per_trade_pnl` Sharpe is not gateable alone on this P&L; MaxDD is load-bearing.

**Seam coherence (defect 4) — pick exactly one at freeze:**
- **(a) EOD/overnight formation:** 15:30 wall state, hold to expiry-day close / next-day
  09:15 exit. Contradicts "no overnight gamma"; only frame validable on bhavcopy.
- **(b) Tier-2 forward-paper only:** real 13:00→15:15 seam on live snapshots, validated
  forward, ~1 formation/week. No TRAIN/HOLDOUT/SEALED structure; evidence accumulates by
  session count, power grows by √t — months to any gate.

---

## 9. Feature Gap vs Repo (what is available / needed)
Unchanged items stand (GEX/flip/walls/PCR/MaxPain in `OptionsAnalytics`; execution infra
reusable). Remaining gaps: pin + conviction score, Vanna/Charm engine, IV term structure,
OI-rotation store, Tier-1 wall-surface reconstructor (NIFTY), index-option fee module,
`DealerWallSignalSource`.

---

## 10. Decision Point (operator)

DW-1 as spec'd (weekly per-index option trade) **cannot clear the RFA power pre-check** —
the arithmetic is closed at S ≥ 1.31 with an honest band of 0.2–0.6. That is the gate
working. The constructive options, in recommended order:

1. **Park DW-1** as a record (this document) — do not spend a sealed read on a construct
   the free pre-check already kills.
2. **Re-frame as a regime overlay** on an existing density-rich construct that already
   clears its own power — this is a *new pre-registered candidate* per the C2 guard, not
   a DW-1 reopen, and it would need its own RFA with the C2-retirement discipline applied.
3. **Tier-2 forward-paper only** (option (b) above), with eyes fully open that a 2h weekly
   option P&L accrues ~1 formation/week: ~3 years to approach power 0.80 even at a Sharpe
   nobody can defend today.

No freeze actions are authorized at this disposition. Next step is operator decision on §10.