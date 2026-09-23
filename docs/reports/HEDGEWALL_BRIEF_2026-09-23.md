# HedgeWall → GEX Fly — Brief

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios` · **Status:** parked

## 1. What HedgeWall says

HedgeWall (@Hedgeewall) sells an intraday "dealer positioning" read of NIFTY/SENSEX options. The idea: option
writers (they call them dealers) hedge their gamma, and that hedging shapes how the index moves.

- **Net GEX:** total gamma exposure in the chain. If it's positive, dealers are long gamma: they sell rallies and buy
  dips, which **dampens** moves. If it's negative, they chase moves, which **amplifies** them.
- **Gamma flip:** the spot level where net GEX changes sign. Above the flip, moves get absorbed; below it, they run.
- **Walls / pin / HHI:** strikes where gamma concentrates. These act as magnets or barriers, and the pin is where
  expiry tends to settle.
- **Dealer side:** inferred from change in OI × change in price per strike, and applied only to today's flow.

Their evidence is anecdotal: winning days get posted, and there is no published hit rate. Their numbers also
contradicted each other within a single day (gamma sign flipped between reads).

## 2. What we thought could work

**The idea:** open an iron fly (short ATM straddle, long wings). If it goes well, lock in the profit. If the market
moves, use HedgeWall-style reads to decide how to adjust or reposition.

**The catch:** adjustment and exit rules only reshape P&L; they can't create an edge the base trade lacks. The
repo's own data had already shown iron flies and NIFTY premium selling to be flat or worse. So we tested in this
order: **first does the signal exist, then does a trade built on it make money.**

## 3. What we found

| Step | Question | Result |
|---|---|---|
| Claim 1 | Does strike concentration (HHI) stay dispersed into expiry since CAS? | **Not demonstrated.** No pre-CAS intraday data to compare, and the late spike is a gamma artefact |
| **Stage A** | Does end-of-day net GEX predict whether the next day is calmer than options priced? | **Yes.** High GEX → next-day realized vol ≈ 20 % below implied, after controlling for VIX. Held in 2016–19 (t −3.2) and again in 2020–22 (t −2.7) |
| **Stage B** | Does a GEX-gated iron fly make money? | **No.** 2019–22: Sharpe −0.75 after costs. **+0.22 even with zero costs** |

## 4. What it means

- **The HedgeWall signal is real, but small.** GEX does tell you something true about tomorrow's volatility. Using it
  to decide when to hold a fly clearly helps (−0.35 → +0.22 before costs). It just isn't big enough to trade profitably.
- **Costs aren't the problem; size is.** At a Sharpe of 0.22, proving the edge would take about 128 years of data. We
  have about 4, and cheaper execution doesn't change that.
- **The dealer story isn't proven either.** The same pattern would appear if traders simply pile into calls after
  rallies. We validated the number, not HedgeWall's explanation.
- **What's kept:** GEX as a known fact. It's a possible *filter* for some future trade rather than a trade by
  itself. The 2023–26 data was never touched, so it's still available to confirm a stronger idea.
- **Caveat (operator's rule):** this is a finding about 2016–22 history, not a verdict on today's market.

*Detail:* `HEDGEWALL_POSITIONING_REVIEW_2026-09-23.md` → `GEX_REGIME_STAGE_A_{TRAIN,HOLDOUT}.md` +
`_TRAIN_REVIEW.md` → `GEX_FLY_B1_DEV.md` + `GEX_FLY_B1_REVIEW.md`.
