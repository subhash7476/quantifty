# Signal Engine — Design Note

**Status:** DRAFT (design, not pre-registered). Created 2026-07-21.
**Scope:** Cross-sectional long/short signal engine over the NSE single-stock-futures
(SSF) universe (~180 names). Index directional timing is explicitly out of scope for v1
(deferred to a later increment).
**Nature of this document:** architecture and build plan only. It authorizes no code and
consumes no sealed data. Each sleeve named here must clear its own RFA power pre-check and
standalone pre-registration before implementation, per `CLAUDE.md` (RFA section).

---

## 1. Thesis

A world-class signal engine is not *a signal* — it is an **architecture**: a set of
weakly-correlated alpha sleeves, each with an independent economic reason to be paid,
combined under a shared risk model and a net-of-cost acceptance gate.

That architecture is also the escape from the demonstrability wall that closed every prior
single-construct battery (PSB-1, PSB-2, SFB-1/F1). The wall is real: `ncp = S·√T`, so
**cadence** cancels and cannot buy statistical power. But **breadth** is a separate lever
the prior work never pulled:

```
IR = IC · √(breadth × N_signals)
```

Four to eight lightly-correlated sleeves across ~180 names is on the order of thousands of
near-independent bets per formation. That is how real multi-signal futures books manufacture
a demonstrable Sharpe out of a modest per-signal IC — and it is a longer/wider *sample*, not
a higher cadence, so it does not violate the `S·√T` result. Breadth is the design's alpha
source.

---

## 2. The engine (v1 composition)

A **beta- and sector-neutral cross-sectional long/short book** over the SSF universe,
combining four orthogonal sleeves under **robust fixed risk-weights** (not weight-optimized
— optimization on the available window is overfitting).

| Sleeve | What it ranks | Why it pays (economics) | Cadence | Data |
|---|---|---|---|---|
| **Carry / basis** | annualized (F−S), residual after common financing | compensation for financing leveraged longs / stock-borrow demand | monthly roll | futures + spot |
| **Trend** | vol-scaled multi-horizon time-series momentum | under-reaction + risk transfer (MOP 2012) | daily-computed, monthly-held | futures history |
| **Flow** | NSE participant-wise OI (client/FII/pro/DII long-short) | informed positioning; India-specific, published free daily | daily | NSE participant OI |
| **Skew** | per-name option risk-reversal / IV−RV | put-skew = informed pessimism; rich vol = insurance premium | daily | existing option-chain engine |

**Why these four.** Carry and Trend are the non-negotiable backbone — the two most-validated
cross-sectional futures signals in existence, decades of out-of-sample evidence across asset
classes, both economically *why*-grounded rather than mined. Flow and Skew are the
differentiated, India-specific edge a generic CTA book does not have, and both run off data
or infrastructure already available (NSE publishes participant OI free; the option surface is
already built for the options dashboard). Backbone buys robustness; overlays buy upside.
"World-class" here means disciplined diversification of *why you get paid*, not exotic signals.

### 2.1 Data feasibility (as of 2026-07-21 ingest)

Ingested substrate: adjusted equity spot (2010-01-04 → 2026-07-09, 4,132 symbols); futures
bhavcopy (2016-02-11 → 2026-07-20, 363 stock + 13 index underlyings); **full options bhavcopy
— ingest in progress** (2016-07-01 → 2024-06-30 done, ~82.5m rows and counting; will extend to
date on completion). This sets v1:

| Sleeve | Feasible now? | Blocker / note |
|---|---|---|
| **Carry** | ✅ | Futures + adjusted spot both present. |
| **Trend** | ✅ | Futures history present. |
| **Skew (per-name)** | ✅ (on ingest completion) | Full options history unblocks per-name skew / VRP. **Verify OPTSTK (stock options), not index-only, are included**; computable only on the liquid options subset (~top 50–100 names), so this sleeve has lower breadth than Carry/Trend. |
| Basis-momentum | ✅ (later) | Multi-expiry per name is in FUTSTK bhavcopy — free add. |
| **Flow** | ❌ | NSE participant-wise OI is a separate file, not in this ingest. One free ingest script unblocks it. |

**Consequence.** **Carry + Trend + Skew** are buildable once the options ingest completes
(Carry + Trend today). The engine's demonstrability comes from combining weakly-correlated
sleeves (`composite IR ≈ √(N_signals) × per-sleeve IR`). Futures history cannot extend before
2016 (SFB-1/F1 lockdown), so the calendar lever is exhausted at n*=42 and demonstrability must
come from breadth of sleeves:
- **2 sleeves** (Carry+Trend) → composite power ≈ **0.6** at n*=42 (central) — short.
- **3 sleeves** (+Skew) → ≈ **0.75** — near the hurdle.
- **4 sleeves** (+Flow, via the free participant-OI ingest) → ≈ **0.86** — clears.

So the path to a demonstrable engine is concrete and mostly free: full options (in progress)
buys Skew and gets close; the **participant-OI ingest** (free → Flow) gets it over 0.80. The
index-options subset (NIFTY) remains the basis for the **later index increment** (VRP, GEX,
term-structure). *(All power figures are central-assumption projections; upper-band realized
IRs clear with fewer sleeves.)*

---

## 3. Build order (each sleeve validated standalone first)

Each sleeve is pre-registered and validated **standalone** before it enters the combination.
A dud sleeve is then a $0 kill, not a contaminated engine, and each step slots into the
existing train / holdout / sealed walk-forward discipline.

1. **Carry** — build first. Cleanest to compute the moment futures data lands (basis =
   annualized F−S; strip the common financing component; the residual cross-sectional
   dispersion is the tradeable borrow-demand / sentiment signal). Lowest overfitting surface
   (~one number per name), so it is the most honest first read and the natural anchor.
2. **Trend** — vol-scaled, multi-horizon, standard construction. Confirms the backbone before
   effort is spent on the novel sleeves.
3. **Flow** — parse NSE participant-wise OI; the free informed-positioning edge. More plumbing.
   **Blocked until the participant-OI ingest is run** (§2.1).
4. **Skew** — wire the option surface into name selection. Highest novelty, validated last.
   **Unblocked once the full options ingest completes** (§2.1); computable on the liquid
   options subset (~top 50–100 names), so lower breadth than Carry/Trend.

---

## 4. Design decisions locked now

These are the three places cross-sectional books quietly die, so they are fixed at design
time rather than discovered later:

1. **Neutralize to beta *and* sector before ranking.** Otherwise "carry" is a covert
   short-financials or short-high-beta bet, and the sleeves are not actually orthogonal.
2. **Combine by equal *risk* contribution, not equal notional.** A sleeve's weight is set by
   its risk contribution, not its dollar exposure.
3. **Gate every acceptance on net-of-cost, with an ADV / liquidity cap per name.** The SSF
   universe has a long tail of thin contracts that backtest beautifully and cannot be traded;
   the cap is enforced before a name can enter the book.

---

## 5. Engine layers

```
Signal layer     each sleeve → cross-sectional z-score per name per day, sign-aligned
Neutralization   residualize each z-score against beta and sector
Combination      robust fixed risk-weights across sleeves (no optimized weights)
Risk model       shrunk covariance (Ledoit–Wolf or factor-based) for construction
Construction     beta-neutral long/short; ADV/liquidity caps; turnover penalty
Cost model       futures fees + impact; net-of-cost is the acceptance gate
Validation       train / holdout / sealed walk-forward; breadth-based power projection
```

---

## 6. Out of scope for v1 (recorded, not dropped)

- **Index directional timing** (Nifty/BankNifty futures) — deferred to a later increment;
  smaller sample, different validation, does not benefit from cross-sectional breadth.
- **Additional sleeves** considered and parked: basis-momentum (Boons–Prado 2019),
  short-term reversal, betting-against-beta / low-vol, dealer-gamma (GEX) intraday regime.
  Each is a candidate for a later increment once the v1 four are validated.

---

## 7. Next step

Draft the **Carry sleeve pre-registration**: the RFA declaration (Sharpe + breadth bands,
independently defended and frozen), the exact basis construction and financing-component
removal, the beta/sector neutralization, and the net-of-cost acceptance gate — ready to run
the moment the futures data finishes downloading.
