# F1 Cash-Synthesized Feasibility Screen — Pre-Analysis Spec

**Status:** DRAFT spec for implementer. Not a battery, not a pre-registration, not a certification.
**Date:** 2026-07-19
**Decision it exists to make:** *Is it worth spending money on real GDFL/TrueData single-stock-futures history (2012–2022) to run a proper fresh pre-registered F1?* — **GO / NO-GO, nothing else.**
**Origin:** NSE has locked down historical F&O bhavcopy and Upstox cannot backfill expired contracts (`F1_UPSTOX_INGESTION_DETERMINATION.md`). Rather than buy vendor data blind, screen the construct cheaply on data we already own.

---

## 0. Why this is a screen and not a battery (read first)

Two facts cap what this analysis is allowed to conclude:

1. **The signal is prior-exposed.** 12-1 momentum on the 2012–2022 cash panel is among the
   most-mined signals in this project: PSB-2 **C4** = "momentum, long-only, staggered 6-mo hold"
   ran on this exact panel (net +2.87%, mean IC +0.0466, **dropped on power 0.4110**, fee drag
   35.2 bp/yr), and CLAUDE.md's successor rule requires disclosing the prior CSMP momentum read
   as exposure (D2). TRAIN 2012–2018 is therefore **not a clean fold** for this signal family.
2. **The cost side is assumed, not measured.** Synthesizing futures returns from cash means roll
   cost, bid-ask, and impact-in-a-≤10-name book are all modeled. Turnover-drag is one of F1's four
   metrics. This project has been humbled by fees three times, always in the same direction —
   **realized cost worse than modeled.**

**Therefore the screen's only valid output is a spend decision.** It may NOT recommend a strategy,
consume a sealed read of signal/returns, or feed a promotion path. C4 died on *power*
(demonstrability), not fees — so a favorable assumed fee model cannot by itself resurrect the
construct, and any positive result here must be read with that in mind.

## 1. Substrate (already owned — no acquisition)

- **Signal/return substrate:** `equity_bhavcopy_adjusted` (7.03M rows, PSB-1 certified, entity-grain,
  CA-adjusted). Windows echo F1: TRAIN 2012–2018, HOLDOUT 2019–2022. **No sealed read of
  2023+ signal/returns.**
- **Cost-calibration substrate:** the 2023+ real futures panel (`futures_candles`, UDiFF, ~158K
  rows). Used **only** to bound cost params (turnover/roll frequency, fee stack, a slippage prior) —
  never for signal or returns. Reading cost microstructure from the sealed window is a **disclosed
  operator decision** (defensible: cost params, not returns). See §4 conservatism requirement.

## 2. Universe — PIT F&O-eligibility proxy

Real F&O-eligibility is time-varying and we lack the PIT list for 2012–2022. **Proxy, disclosed as
a proxy:** restrict each formation to names clearing a causal cash-liquidity floor (e.g. trailing
63-session median traded value ≥ a fixed threshold), reusing the PSB-2 D3 liquidity-floor pattern.
This *over-includes* some names never F&O-eligible and *under-includes* none that were liquid — an
optimistic bias on tradability, which is acceptable **only** because the screen's job is to kill weak
constructs, not bless strong ones (a NO-GO under an optimistic universe is a robust NO-GO).

## 3. Construct (F1 as designed, run on synthesized daily series)

- **Signal:** 12-1 cross-sectional momentum (skip most-recent month), long-only, concentrated to
  **≤10 names** per formation.
- **Synthesized futures series:** rank on cash total-return (adjusted) 12-1 momentum; realize P&L on
  the cash **price** path as the near-month futures proxy. Basis/carry drift **ignored** and disclosed
  (over a ~monthly hold the basis-convergence term is small vs. the momentum dispersion; note it adds
  unmodeled noise, not a directional edge).
- **Bracket ladder:** F1's conservative daily-OHLC ladder (open-gap → worst-case whiplash →
  High/Low intercept → period-close fallback), computed on cash daily OHLC as the intraday proxy.
  ATR-scaled, **TRAIN-fold-selected** — but note (§0) TRAIN is not fresh, so bracket params are a
  screening choice, not an out-of-sample-honest selection.
- **Cadence:** monthly formation (matches C4; the only fee-survivable cadence in prior batteries).

## 4. Cost model — conservatively calibrated (the load-bearing part)

Impact/bid-ask cannot be precisely measured from daily data (UDiFF has OHLC+vol+OI, no quote). So:

- **Known futures fee stack:** use the existing era-accurate model (`core/execution/futures/futures_fees.py`;
  STT 0.0125%→0.02% at 2024-10-01, exchange/SEBI/GST/stamp). This part is measured.
- **Roll/turnover:** bound roll frequency and per-roll round-trips from the **real 2023+ panel's**
  observed roll structure; apply that turnover to every formation.
- **Slippage/impact:** a **swept band**, not a point estimate. Lean the early era (2012–2018) to the
  **pessimistic** end — 2023+ spreads understate 2012-era illiquidity. Require the verdict to be
  **robust across the whole band**, not just the optimistic end.
- **Conservatism invariant:** if the construct only survives at the optimistic end of the slippage
  sweep, that is a **NO-GO**, because real early-era cost will be worse.

## 5. Evaluation — F1's portfolio metrics (rank-IC retired, invalid on ≤10 names)

Report, per fold (TRAIN, HOLDOUT), net of the §4 cost model, across the slippage sweep:
Expectancy per formation · Max Drawdown · Days-Held · **Turnover-Drag** · block-bootstrap CI on
expectancy. No noncentral-t / Bonferroni (those belong to the real battery, not a screen).

## 6. Decision rule (the whole point)

- **NO-GO (do not buy vendor data):** net expectancy ≤ 0 anywhere in the conservative slippage band
  on TRAIN, OR HOLDOUT sign-flips, OR turnover-drag consumes the gross edge (the recurring pattern).
  → F1 dies for ~$0.
- **GO (worth buying real futures data):** net expectancy robustly positive across the *full* band on
  **both** TRAIN and HOLDOUT, with a MaxDD-scaled return that a real, power-deflated battery could
  plausibly clear. → trigger vendor purchase (GDFL/TrueData) and run the **real** pre-registered F1 on
  fresh futures data — this screen does **not** substitute for it.
- **Explicit non-outcome:** "promising signal, promote toward live." Not available from this artifact
  under any result. Prior exposure + assumed cost forbid it.

## 7. Deliverables (implementer)

1. `scripts/sfb/f1_feasibility_screen.py` — universe proxy, synth series, bracket ladder, §4 cost
   sweep, §5 metrics. Reuses PSB harness where clean.
2. `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md` — script-generated, all numbers computed (no
   hardcoded PASS strings), carrying §0 caveats and the §6 GO/NO-GO verdict inline.
3. Tests: synth-return identity vs cash, cost-sweep monotonicity, decision-rule unit tests.

**Role split unchanged:** DeepSeek implements from this spec; Claude reviews. No freeze, no sealed
read of signal/returns, no scoring beyond the GO/NO-GO screen.
