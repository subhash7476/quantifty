# Structural Alpha Sources for Indian Index Markets — Research Dossier

**Date:** 2026-08-03
**Role:** Head of Quantitative Research
**Status:** Pre-implementation analysis — no code, no data reads

---

## Preamble: What the Platform Has Proven

Before proposing new edges, four binding constraints must be stated — discovered by
this platform, not assumed:

### Constraint 1: The Demonstrability Wall for Single-Index Strategies

```
ncp = (δ / sd) × √n = Sharpe × √T    (per_trade_pnl)
```

For a single Nifty futures strategy over the ~3.6-year sealed window:
- √T ≈ 1.89 (weekly) or ≈ 5.84 (daily) — but cadence cancels
- Power 0.80 requires **Sharpe ≥ 1.30–1.50**
- No defensible literature supports a single-index strategy at this Sharpe

**This kills all single-index and two-index timing strategies.** Not because they
can't have a genuine edge — because the sealed window is too short to prove it.
A real Sharpe of 0.5 would produce ~$1M over 10 years but cannot be distinguished
from zero at 3.6 years of data. The platform's RFA gate correctly returns ABANDON.
This is a feature, not a bug.

### Constraint 2: The Fee Wall for Delivery Equity

STT at 0.1% per leg (buy AND sell) on delivery equity imposes ~13pp/yr drag at
weekly turnover. PSB-1 and PSB-2 proved no known Indian equity cross-sectional
effect clears this. Index options escape: STT is on premium only (~0.2–0.5 bp
effective vs ~20 bp for delivery equity). Stock futures escape: STT is 0.0125%
sell-only.

### Constraint 3: The Cross-Section Escape Works But Is Narrow

Rank-IC strategies over a genuine cross-section clear the power gate by exchanging
small per-observation noise (sd_IC ≈ 0.10–0.25) for per-trade unit sd (1.0 by
construction). Carry (180-name SSF universe) proved this — OOS IC +0.029, SEALED
one-shot PASS at +20.52%.

For **index-specific** research, available cross-sections are:
- Nifty 50 constituents (CB-N50: OOS IC +0.029, usable but breadth→futures
  translation failed directionally)
- Nifty 500 constituents (~500 names, untested)
- Option strikes × expiries (OSC: N_eff ≈ 1.9 despite 283 cells/day)
- Sector indices (~15 sectors — too few)
- Option expiry tenors (~4–8 tenors — too few)

### Constraint 4: Sealed Window Status

| Window | Status |
|--------|--------|
| SEALED 2023–2026 (Carry — SSF book P&L) | SPENT (PASS) |
| SEALED 2023–2026 (TS Basis monthly — SSF book P&L) | SPENT (de-authorized, read one-shot) |
| SEALED 2023–2026 (IVOL — SSF book P&L) | SPENT (FAIL, regime flip) |
| SEALED 2023–2026 (equity dev window) | UNSPENT (PSB-1/PSB-2 never consumed) |
| SEALED 2023–2026 (TS Basis Daily, 876 formations) | PRESERVED (operator decision) |
| **2016–2022 Nifty options surface (1,701 daily formations)** | **UNREAD** (OSC abandoned at RFA) |
| BankNifty options bhavcopy | NOT INGESTED (filter exclusion, archive available) |

---

## Research Dossier

Every proposed edge must satisfy:
- **What** is the phenomenon?
- **Why** should it exist? Who creates it, who profits, who loses?
- **Why hasn't it been arbitraged away?**
- **What data** is required to investigate it?
- **Can it be tested scientifically?**
- **What is its expected half-life?**
- **How difficult is implementation?**

Rejected: any idea where the economic mechanism cannot be stated before seeing data.

---

## EDGE 1: Volatility Risk Premium — Index Short Volatility

**Category:** Risk Premia
**Research Priority:** TIER 1
**Clears RFA Gate:** NO (per_trade_pnl, single series) — but the economic case is
independent of the gate

### A. Description

Systematically sell Nifty/BankNifty options (straddles, strangles, or naked puts)
and earn the spread between implied and realized volatility. The VRP is one of the
most robust premia in all of finance, documented across every liquid options market
globally. In Indian index options specifically, the premium is likely larger than
in developed markets due to:

1. The world's highest options volume, driven by retail speculation
2. SEBI-documented 89%+ retail F&O loss rate
3. A structural imbalance: retail is overwhelmingly net long options, dealers are
   net short, and the premium compensates dealers for warehousing short-gamma risk

### B. Economic Mechanism

- **Who creates it:** Retail traders buying OTM calls and puts as lottery tickets
  (small premium, large potential payout) and institutional hedgers buying puts
  for portfolio insurance.
- **Who profits:** Option sellers — market makers, proprietary desks, and any
  systematic seller who can manage gamma risk.
- **Who loses:** Retail option buyers — consistently, year after year, by SEBI's
  own data.
- **Why it exists:** The demand for convexity (leverage for speculators, protection
  for hedgers) structurally exceeds the supply of natural option sellers. Market
  makers must be compensated. This is not a temporary mispricing — it is equilibrium
  compensation for providing a service the market demands.

### C. Persistence

- Retail speculation in Indian options shows no sign of declining. Volumes grow
  year-over-year despite SEBI warnings, mandatory risk disclosures, and higher
  margin requirements.
- Institutional hedging demand grows with AUM.
- Professional competition is limited by: (a) margin requirements for short options
  positions, (b) position limits enforced by NSE, (c) tail risk — most systematic
  funds cannot hold short-gamma through a COVID-like event and survive drawdown
  limits.
- The VRP has persisted for **decades** globally — it predates machine learning,
  HFT, and every technological innovation.

### D. Required Data

| Data | Status |
|------|--------|
| Nifty options bhavcopy (all strikes, all expiries, 2016–2026) | **IN REPO** (5.5M rows) |
| Nifty 1-min futures data for delta-hedging simulation | **IN REPO** |
| India VIX | **IN REPO** (1d store, 2010–2026) |
| BankNifty options bhavcopy | **NOT INGESTED** (available from NSE archives — one ingest filter change away) |
| Tick-level options data for realistic execution | **NOT AVAILABLE** (would require paid data feed) |
| Option bid-ask spreads historically | **NOT AVAILABLE** (bhavcopy is EOD only) |

**Key unread window:** The 2016–2022 Nifty options surface (1,701 daily formations)
has **never been read** by any script. OSC probed the 2023–2025 window (already
burned for MSRP fee triage) but never touched 2016–2022. This is the single
largest clean confirmatory window remaining in the repository.

### E. Testability

**Highly testable.** The core metric is straightforward:

```
Realized variance (delta-hedged) vs implied variance at initiation
Portfolio of short straddles/strangles, daily delta-hedge
Account for: STT (0.017% sell on options, 0.0125% sell on futures),
bid-ask spread estimate, margin cost
```

The research should be done on the **2016–2022 window only** — design the strategy,
select parameters, and pin the hedge methodology. Then test ONCE on 2023–2026
(the burned SEALED, which now serves as confirmation since no prior short-vol
read exists on Nifty options). No parameter revision after sealed read.

### F. Expected Half-Life

**Decades.** The VRP is not a temporary market inefficiency — it is equilibrium
compensation for bearing variance risk. It exists in Japan (Nikkei), Europe
(EuroStoxx), US (S&P 500), Korea (KOSPI), and every market with liquid options.
It survived: the 1987 crash, the 2000 dot-com bubble, the 2008 financial crisis,
the 2010 flash crash, the 2020 COVID crash. India's retail structure makes it
particularly pronounced.

### G. Implementation Difficulty

**HIGH.** The research is straightforward. The execution is not:
- Delta hedging requires daily (or more frequent) rebalancing in Nifty futures
- Contract size mismatches (Nifty lot = 50 shares, options lot = 50)
- Margin requirements for short options are substantial
- Tail risk is real — a short-gamma portfolio will underperform catastrophically
  during crises
- An independent researcher selling >2 lots faces scaling constraints on margin

### H. Key Concern — Tail Risk Management

A naked short-vol strategy will lose 30–50%+ of accumulated profits during a
single tail event (March 2020 COVID, 2008, etc.). The IVOL sleeve in this
repository failed at SEALED due to regime flip — the exact same risk.

**The research question is not "does the VRP exist?"** — it does.
**The research question is: "can tail risk be managed (OTM put protection,
stop-loss, size management) without giving back the entire premium after costs?"**

If the answer is yes, this is the single most durable structural edge available
in Indian index markets.

---

## EDGE 2: Dealer Gamma Feedback — Expiry-Day Dynamics

**Category:** Market Microstructure
**Research Priority:** TIER 1
**Clears RFA Gate:** NO (per_trade_pnl) — but the mechanism is structural

### A. Description

On weekly expiry days (Thursday for Nifty, Wednesday for BankNifty), dealers are
structurally short gamma from the massive retail option buying during the week.
Their mechanical delta-hedging creates predictable intraday behavior:

1. **Trend amplification:** Dealers sell into weakness (hedging short puts becoming
   more short) and buy into strength (hedging short calls becoming more long) —
   effectively buying high and selling low, which amplifies price moves.

2. **Gamma concentration:** Open interest concentrates near-the-money as expiry
   approaches, increasing gamma sharply — hedging frequency accelerates in the
   final hours.

3. **Strike pinning:** Nifty often closes near a high-open-interest strike on
   expiry day because dealers adjust hedges to minimize payout — a testable
   prediction.

### B. Economic Mechanism

- **Who creates it:** Market makers/dealers who sold options to retail speculators
  during the week and must remain delta-neutral. Their hedging is mechanical —
  dictated by their risk management systems, not by market views.
- **Who profits:** Traders who understand the gamma profile and position accordingly.
  On expiry days with concentrated gamma, trading with the trend (not fading it)
  should be profitable because dealer hedging provides the fuel.
- **Who loses:** Retail option buyers who pay for gamma they don't understand, and
  reversal traders who fade trends on expiry days unaware that dealer hedging is
  providing mechanical reinforcement.
- **Why it exists:** The dealer's objective function is "stay delta-neutral," not
  "maximize P&L." They hedge mechanically regardless of whether the hedging is
  profitable — their P&L comes from the option premium, not the hedge.

### C. Persistence

This is a structural feature of any market where:
1. Options exist with regular expiry
2. Market makers provide liquidity and delta-hedge
3. End-users are systematically one-sided (retail net long)

All three conditions hold for Indian weekly index options and show no sign of
changing. As long as the conditions hold, the gamma feedback exists. It cannot
be "arbitraged away" because it IS the arbitrage mechanism — dealer hedging is
what keeps options fairly priced relative to the underlying.

### D. Required Data

| Data | Status |
|------|--------|
| Nifty options bhavcopy (OI by strike to compute gamma profile) | **IN REPO** |
| Nifty 1-min intraday data (for expiry vs non-expiry comparison) | **IN REPO** |
| BankNifty options bhavcopy | **NOT INGESTED** |
| BankNifty 1-min data | **IN REPO** |

The gamma profile is deterministic given open interest and strike distances.
No tick data required for the daily analysis. For intraday execution simulation,
1-min data is available.

### E. Testability

**Testable at two resolutions:**

**Daily resolution (lower frequency, higher confidence):**
- Compare Nifty realized volatility on expiry days vs non-expiry days
- Study open-to-close ranges on expiry Thursdays
- Measure pinning frequency: how often does Nifty close within X% of the
  highest-OI strike on expiry day vs random expectation?

**Intraday resolution (higher frequency, more challenging):**
- Compute real-time gamma profile from EOD OI + intraday spot
- Test if price moves accelerate when Nifty approaches high-gamma (high-OI)
  strike zones
- Test if reversal strategies underperform on expiry day afternoons and
  trend-following strategies outperform

### F. Expected Half-Life

**Indefinite.** Market-making gamma hedging is a permanent structural feature.
The specific magnitude may compress if more participants trade it, but the
mechanism cannot be eliminated without eliminating weekly options themselves.

### G. Implementation Difficulty

**VERY HIGH.** Implementing this in real-time requires:
- Computing gamma profiles from option OI data (doable)
- Executing Intel during high-volatility expiry moments (challenging)
- Latency advantage over other participants (retail is at a disadvantage)

Research difficulty is MEDIUM. Production difficulty is VERY HIGH. The research
may be more valuable for understanding market behavior than for direct execution
by an independent researcher.

---

## EDGE 3: VIX-Based Regime Filter and Volatility-Weighted Position Sizing

**Category:** Risk Management
**Research Priority:** TIER 1
**Clears RFA Gate:** NOT APPLICABLE (not a standalone alpha source)

### A. Description

This is NOT an alpha source. It is a risk management overlay that improves the
risk-adjusted returns of any existing strategy. The insight: volatility clusters
and regimes persist for months. During high-VIX periods, all directional signals
have lower signal-to-noise ratios. Reducing exposure during high-VIX regimes and
increasing it during low-VIX regimes improves any strategy's Sharpe ratio at
zero marginal research cost.

### B. Economic Mechanism

- VIX is mean-reverting but regimes are persistent — high VIX stays high for
  weeks/months, low VIX stays low for extended periods
- During high-VIX regimes: market is driven by macro events, black-swan fears,
  correlation → 1 (everything moves together), making any alpha signal less
  reliable because idiosyncratic variation is drowned by systematic risk
- During low-VIX regimes: dispersion increases, stock-specific signals work
  better, mean-reversion patterns are more reliable
- This is not prediction — it is bet-sizing: put less capital at risk when the
  environment is hostile

### C. Persistence

Volatility clustering is a stylized fact of financial markets — one of the
few genuinely universal properties. It exists in every asset class, every time
period, every geography. It is not a mispricing — it is an empirical description
of how markets behave.

### D. Required Data

India VIX daily data — **IN REPO** (1d store, 2010–2026)

### E. Testability

**Trivial.** Take any existing strategy's signal (Carry, TS Basis, etc.).
Multiply position sizes by `1 / VIX_t` or a function like:
```
exposure_multiplier = clip(VIX_median / VIX_current, 0.25, 2.0)
```
Apply to the TRAIN/HOLDOUT/SEALED windows. Compare Sharpe, MaxDD, and Calmar
ratio to the un-scaled baseline.

### F. Expected Half-Life

**Indefinite.** Not a tradeable edge — a property of markets.

### G. Implementation Difficulty

**LOW.** Requires only VIX data and a position-sizing rule. No new alpha
discovery, no new data, no execution complexity. Can be tested in a single
afternoon.

### H. Research Priority Rationale

This is the lowest-hanging fruit in the dossier. It is not alpha — it's better
risk management. But it costs nothing to test and can improve every strategy
the platform already runs. The Carry strategy with volatility-weighted sizing
is a direct extension of work already done.

---

## EDGE 4: Index Option Term Structure — A Genuine Cross-Section

**Category:** Cross-Market / Market Structure
**Research Priority:** TIER 2
**Clears RFA Gate:** UNCERTAIN (rank_ic, but cross-section size is unknown)

### A. Description

Nifty index options trade at multiple simultaneous expiry tenors: the current
weekly, next weekly, the current monthly, next monthly, and sometimes 2nd/3rd
monthly. Each expiry forms an implied volatility at-the-money level. The term
structure of IV across expiries is a cross-section — and unlike the strike
cross-section (which OSC proved has N_eff ≈ 1.9), the term structure dimension
is driven by fundamentally different forces:

- Near-term IV: driven by event risk, gamma hedging, expiry anticipation
- Medium-term IV: driven by macro expectations, VRP term structure
- Far-term IV: driven by long-term volatility expectations

### B. Economic Mechanism

- **The cross-section:** Not strikes (which share a common spot and gamma source),
  but expiry tenors — each driven by different market forces
- **Why it might work as a cross-section:**
  - The near-dated IV is contaminated by gamma/scalping effects and expiry
    anticipation — it may be systematically elevated
  - The VRP term structure (how rapidly IV decays as expiry approaches) is a
    risk premium itself
  - Selling the rich front-month IV and buying the cheaper back-month IV
    (a calendar spread in volatility space) could monetize term-structure
    mispricing
- **Why it might fail as a cross-section:**
  - Only 4–8 tenors are liquid simultaneously (weekly Nifty options typically
    have 2–4 weekly expiries plus 1–3 monthly expiries)
  - If N_eff is only 2–3, the cross-sectional breadth is too small for rank_ic
  - The term structure is highly autocorrelated — across tenors, IV typically
    moves directionally (all up or all down together)

### D. Required Data

Nifty options bhavcopy (all strikes, all expiries) — **IN REPO**

### E. Testability

Testable. Construct a daily panel of ATM IV by expiry tenor. Compute rank_IC
of a "richness" signal (deviation of near-term IV from term-structure-implied
fair IV) against forward returns in the underlying.

### F. Expected Half-Life

**Years.** The VRP term structure is a genuine premium. Its exploitation via
calendar spreads is standard options trading practice.

### G. Implementation Difficulty

**MEDIUM.** Research is straightforward. Execution requires trading multiple
option legs simultaneously — bid-ask spread costs multiply.

### H. Priority Rationale

TIER 2 because the cross-section size (number of simultaneously liquid tenors)
may be too small to clear the power gate, and the signal is likely subsumed by
the general VRP (Edge 1). A probe to measure N_eff across tenors is worth doing
before committing to a full construct.

---

## EDGE 5: Retail Positioning — Fading Aggregate Retail Option Flow

**Category:** Behavioral Biases / Market Structure
**Research Priority:** TIER 2
**Clears RFA Gate:** NO (single series, per_trade_pnl) — but strong economic case

### A. Description

Indian retail traders are systematically net buyers of out-of-the-money options.
SEBI data shows >89% of retail F&O participants lose money. The systematic other
side — selling OTM options to retail — should be the structural winner. This is
related to Edge 1 (VRP) but distinct in targeting specific retail-favored strikes
rather than selling ATM straddles.

### B. Economic Mechanism

- **Who creates it:** Retail traders on mobile apps (Zerodha, Groww, Upstox)
  buying OTM calls and puts with a lottery-ticket mentality — small premium,
  potentially large payout. Overwhelmingly net buyers.
- **Who profits:** The other side of every trade — market makers, proprietary
  desks, algorithmic liquidity providers.
- **Who loses:** Retail traders — systematically, year after year, by SEBI's
  own rigorous study.
- **Why it persists:** Gambling behavior is one of the most persistent human
  behaviors observed. SEBI has tried warnings, mandatory risk disclosures,
  higher margins for OTM options, reduced expiry days — volumes keep growing.
  Education does not cure the lottery-ticket preference.

### C. Persistence

This is one of the few edges where the losing side has been documented by the
regulator itself. SEBI publishes annual studies of retail F&O profitability.
Every single study finds >85% of retail traders lose money. The behavior persists
because:

1. Low barrier to entry (₹500 can buy an options contract)
2. Social media/Signal groups promoting "easy money" in options
3. Lottery-ticket preference — humans overweight small probabilities of large
   gains
4. Survivorship bias — the few who win are highly visible; the 89% who lose
   are silent

### D. Required Data

| Data | Status |
|------|--------|
| Nifty options bhavcopy (OI by strike) | **IN REPO** |
| Retail vs institutional OI split | **NOT AVAILABLE** (SEBI publishes aggregate stats, not strike-level) |
| Broker-level options flow data | **NOT AVAILABLE** (proprietary data, not purchasable) |

**The key limitation:** The platform cannot distinguish retail option buying from
institutional option buying in the OI data. A proxy would be needed: e.g., OTM
puts with small notional value (retail's preferred instrument) vs ATM options
with large notional value (institutional hedging).

### E. Testability

Partially testable with proxies:
- OI concentration at OTM strikes (retail-dominant) vs ATM (institutional)
- Option premium as % of underlying — retail buys cheaper OTM, institutions
  trade ATM or near-ATM
- Small-lot activity proxy: contracts with high OI but low average trade size

These are proxies, not direct measurements. A definitive test requires
broker-level data that the platform does not possess.

### F. Expected Half-Life

**Decades.** Retail gambling in financial markets is a permanent feature of
human psychology.

### G. Implementation Difficulty

**HIGH.** Same tail risk concern as Edge 1 (short options). Plus the added
complexity of identifying retail flow without position-level data.

### H. Priority Rationale

TIER 2 because the mechanism is strong but (a) may be indistinguishable from
Edge 1 (VRP) without retail flow data, (b) the data limitation is binding,
and (c) tail risk management is the same unsolved problem.

---

## EDGE 6: Institutional Positioning — Futures Open Interest Dynamics

**Category:** Information Advantage
**Research Priority:** TIER 2
**Clears RFA Gate:** NO (single series, per_trade_pnl) — index timing faces wall

### A. Description

Nifty futures open interest changes, combined with price direction, reveal
institutional positioning:
- Rising OI + rising price = new long positions (bullish)
- Rising OI + falling price = new short positions (bearish)
- Falling OI + rising price = long unwinding (bearish reversal)
- Falling OI + falling price = short covering (bullish reversal)

These signals reflect genuine capital commitment, not speculative noise.

### B. Economic Mechanism

- **Who creates it:** Institutional participants (FIIs, mutual funds, proprietary
  desks) establishing or unwinding directional positions in Nifty futures.
- **Why it carries information:** A price rise driven by position building
  (rising OI) is fundamentally different from a price rise driven by position
  unwinding (falling OI). The former reflects conviction; the latter reflects
  exit. Standard price-based indicators cannot distinguish these.
- **Who profits:** Traders who monitor OI changes and position with institutional
  flow rather than against it.

### C. Persistence

- Futures OI data is published daily by NSE — permanent
- Institutional positioning via futures is structural
- The signal is well-known in commodity futures but less systematically studied
  for Indian equity index futures specifically

### D. Required Data

Nifty futures bhavcopy (OI, OHLC, volume) — **IN REPO** (FUTIDX from 2016-02-11)

### E. Testability

Easily testable. Construct daily OI-price signals. Test predictive power for
next-day, next-week Nifty returns.

### F. Expected Half-Life

**Years.** Known in commodities but less applied to equity indices. The mechanism
is simple enough that it could be eroded by systematic adoption, but the
OI-price relationship is mechanical (OI = capital committed) and not purely
a market inefficiency.

### G. Implementation Difficulty

**LOW.** Daily data, simple signal construction, single futures position.

### H. Priority Rationale

TIER 2. Likely too weak as a standalone signal (IC probably ~0.01–0.03,
Sharpe ~0.2–0.4 — well below RFA gate threshold). But useful as a factor in
a composite index timing model. Should be tested quickly and cheaply, not
pursued as a major research program.

---

## EDGE 7: Sector Rotation — Nifty/BankNifty Drivers from Cross-Asset Inputs

**Category:** Cross-Market Relationships
**Research Priority:** TIER 3
**Clears RFA Gate:** NO (two-index, per_trade_pnl) — killed by demonstrability wall

### A. Description

Nifty and BankNifty have permanently different sector compositions. Systematic
differences in their relative performance reflect genuine economic transmission
— not random noise and not the mean-reversion pair trade that failed. Banks
outperform when rates are stable and credit growth is strong. IT outperforms
when INR is weak and US tech spending is strong. These are multi-month sustained
regimes driven by macro factors.

### B. Economic Mechanism

- BankNifty drivers: RBI policy rates, yield curve steepness, credit growth,
  NPA cycle, GDP growth
- Nifty-IT drivers: USD/INR (weak INR = higher IT export revenue in INR terms),
  US corporate IT spending, global tech cycle
- Nifty-Energy drivers: Crude oil prices, refining margins, government fuel
  pricing policy
- The relative performance of Nifty vs BankNifty is NOT random — it is the
  market's aggregation of these macro transmission channels

### C. Persistence

Sector composition differences are permanent. The economic forces that drive
bank vs IT vs energy performance are permanent. This is not a market anomaly
— it is how sector rotation works in every multi-sector equity market.

### D. Required Data

| Data | Status |
|------|--------|
| Nifty, BankNifty daily data | **IN REPO** |
| Nifty IT, Nifty Bank, Nifty Auto, etc. sector indices | **IN REPO** (140+ NSE indices) |
| USD/INR | **NOT IN REPO** (MCX FUT configured but never fetched) |
| 10-year G-Sec yield | **NOT IN REPO** |
| Crude oil | **NOT IN REPO** |
| RBI policy rates | **NOT IN REPO** (publicly available, not ingested) |

### E. Testability

Testable. The honest Sharpe of a Nifty/BankNifty relative-strength strategy
driven by macro inputs is likely ~0.3–0.5 — well below the RFA gate threshold.
This doesn't mean the mechanism is false — it means the sealed window is too
short to prove it at this effect size.

### F. Expected Half-Life

**Indefinite.** Economic drivers of sector performance are permanent.

### G. Implementation Difficulty

**LOW.** Two futures contracts, monthly rebalancing.

### H. Priority Rationale

TIER 3. The economic mechanism is sound but the platform's gate will kill it as
a standalone P&L strategy. More useful as a macro overlay on the existing Carry
strategy — tilt the 180-name SSF book toward bank-heavy names during rate-cut
cycles and toward IT names during weak-INR periods. This is sector-informed
portfolio construction, not standalone alpha.

---

## EDGE 8: Nifty Index Rebalancing — Passive Flow Capture

**Category:** Institutional Constraints
**Research Priority:** TIER 2
**Clears RFA Gate:** UNCERTAIN (event study, not time-series prediction)

### A. Description

Nifty 50 is rebalanced semi-annually (March and September). Stocks added to the
index see predictable buying from ~₹2–3 lakh crore of passive AUM tracking Nifty
50. Stocks deleted face predictable selling. The announcement-to-effective-date
window creates a structural trade: buy additions, sell deletions, hold through
the effective date.

### B. Economic Mechanism

- **Who creates it:** Index funds and ETFs that mechanically replicate Nifty 50
  — they MUST buy additions and sell deletions at the rebalance effective date.
- **Who profits:** Arbitrageurs who accumulate additions before the passive
  flows hit and unwind after.
- **Who loses:** Passive investors who pay a higher price for additions (this
  is the well-known "index front-running" concern).
- **Why it exists:** The passive AUM is enormous and growing. Index funds have no
  discretion — they must trade. This creates predictable demand/supply at a
  known future date.

### C. Persistence

Passive AUM in India is growing structurally — EPFO (Employees' Provident Fund
Organization), NPS (National Pension System), and retail index fund/ETF flows
are all secular trends. As passive AUM grows, the rebalancing effect should
increase, not decrease.

Competition from other arbitrageurs may compress the effect but cannot eliminate
it entirely because: (a) there is a limit to how much you can front-run without
moving the price yourself, and (b) the announcement-to-effective period is only
4–6 weeks — too short for very large positions.

### D. Required Data

- Nifty 50 historical index composition (additions/deletions) — publicly
  available from NSE Indices
- Equity data for additions/deletions — **IN REPO** (7M-row equity bhavcopy)

### E. Testability

Easily testable as an event study. For each historical rebalance, measure the
return of additions minus deletions from announcement date to effective date + X
days. Account for the fact that the names are pre-announced — test if the effect
persists after the announcement (which would indicate it's not fully arbed).

### F. Expected Half-Life

**Years to decades.** Passive AUM growth is secular. Index fund mechanics are
permanent. The effect has been documented globally for 30+ years and persists.

### G. Implementation Difficulty

**LOW to MEDIUM.** Research is straightforward event study. Execution requires
buying a handful of stocks and holding for 1–6 weeks — no leverage, no options,
low complexity. But it's a delivery-equity trade → STT 0.1% both sides. The fee
wall applies.

### H. Priority Rationale

TIER 2 — downgraded from TIER 1 because this is a delivery-equity strategy and
the fee wall may consume the gains. At ~12% expected return on a ~6-week hold,
STT alone is 0.2% (both sides) ≈ ~1.7% annualized from STT alone (from holding
6-week positions all year), plus other transaction costs. The edge is real but
the net-of-fees outcome depends on the pre-announcement drift being large enough.
A 2016–2026 event study to measure the net-of-STT effect is cheap and worth doing.

Note: This edge is NOT index-level — it operates on individual stocks entering
or leaving Nifty 50. It's included because it's a structural source of returns
related to the index ecosystem.

---

## EDGE 9: Cross-Asset Contagion — Overnight S&P 500 → Nifty Intraday Drift

**Category:** Cross-Market Relationships
**Research Priority:** TIER 3
**Clears RFA Gate:** NO (single series, per_trade_pnl)

### A. Description

Major S&P 500 moves during Indian closed hours are transmitted into Nifty's open
gap. The question is whether there is a predictable intraday drift beyond the
initial gap — i.e., after a -2% S&P overnight move, Nifty gaps down -1.5% at open
but drifts a further -0.5% during the day as FII positioning adjusts.

### B. Economic Mechanism

India is a recipient of global risk appetite. FIIs allocate capital to India
based on global conditions. When S&P 500 falls overnight, FIIs reduce India
exposure, but the adjustment may not be instantaneous because:
- Some FII trading desks operate only during Indian hours
- Domestic participants absorb the initial gap but may not fully price the move
- Algorithmic traders spread large orders over time

### C. Persistence

The FII capital allocation mechanism is structural but the residual intraday
drift is likely tiny (a few basis points) and competed away by algorithmic
traders operating at sub-second speeds.

### D. Required Data

- S&P 500 daily data — publicly available (not yet in repo)
- Nifty 1-min data — **IN REPO**

### E. Testability

Testable. Regress Nifty open-to-close return on overnight S&P return.

### F. Expected Half-Life

**Months.** This is the most liquid, most watched, most systematically traded
relationship in Indian markets. Any residual drift is tiny and actively arbed.

### G. Implementation Difficulty

**LOW** for research. **HIGH** for execution (competing against HFT firms).

### H. Priority Rationale

TIER 3. Well-known, widely traded, likely arbed to zero. Do not prioritize.

---

## EDGE 10: The Meta-Edge — Composite Index Strategy from Weak but Independent Signals

**Category:** Research Design
**Research Priority:** TIER 2
**Clears RFA Gate:** POSSIBLY (composite Sharpe from multiple signals)

### A. Description

The Carry strategy proved the breadth thesis for SSF: combine weakly-correlated
sleeves and the composite Sharpe exceeds individual Sharpes. The same principle
applies to index strategies: even if no single index timing signal clears the
RFA gate alone, a composite of multiple weakly-correlated signals might.

```
Composite Sharpe ≈ √(Σ Sharpe²_i)    (under zero correlation)
```

If 10 independent signals each have Sharpe 0.25, the composite Sharpe is
~0.79 — borderline for the gate. If any signal reaches 0.3–0.4, the composite
clears.

### B. Candidate Index Signals (all weak individually)

| Signal | Expected Sharpe | Independence from others | Status |
|--------|----------------|-------------------------|--------|
| VIX regime (Edge 3) | ~0.1–0.2 (as filter) | Low (colinear with most) | Untested |
| FII flows (Edge 6 reduced) | ~0.2–0.3 | Moderate | Untested |
| Futures OI dynamics (Edge 6) | ~0.2–0.3 | Moderate | Untested |
| Options PCR change | ~0.1–0.2 | Moderate | Untested |
| Overnight S&P 500 gap fade | ~0.1–0.2 | High (by construction) | Untested |
| Expiry-day bias (Edge 2) | ~0.1–0.2 | Low (event-specific) | Untested |
| Month-end effect | ~0.1 | Low | Untested |
| RBI policy event | ~0.3–0.4 (but only 6/year) | Low | Untested |

### C. Key Insight

The RFA gate is per-construct, not per-signal. A pre-registered composite
strategy declaring "we will combine signals A, B, C, D, E with equal weights,
tested once on HOLDOUT and once on SEALED" has a different power profile than
any individual signal. The composite n increases (more independent bets) while
the composite sd decreases (diversification).

### D. The Caveat

This is exactly what the signal engine attempted (4 sleeves: Carry + Trend +
Flow + Skew → power ~0.86). Three of four sleeves failed at TRAIN. The meta-edge
works in theory but finding genuinely independent index-level signals that
survive TRAIN has proven difficult. This is not a criticism of the approach —
it's a statement about how hard it is.

### E. Priority Rationale

TIER 2. Worth pursuing only after Edges 1–6 are individually evaluated. A
composite of untested signals is a research program, not a single experiment.
The individual signals should be cheaply tested first.

---

## Ideas Explicitly Rejected

The following were considered and rejected. The rejection reason is stated so
that the rejection is itself a finding.

| Idea | Rejection Reason |
|------|-----------------|
| **Any indicator-based strategy** (RSI, MACD, moving averages, ATR, Bollinger, chart patterns) | No economic mechanism. These are data transformations, not explanations for why alpha should exist. |
| **Generic machine learning / deep learning** | No economic mechanism. ML is a function approximator — it cannot create alpha ex nihilo. If there is no structural edge to learn, ML will learn noise. |
| **Nifty-BankNifty mean reversion** | Exhaustively researched. Not cointegrated. Half-life 166 days. Bootstrap p=0.354. All 27 intraday combos negative. This is settled. |
| **Nifty trend-following (TSMOM)** | Tested as Trend sleeve. IC +0.022, t=1.13, p=0.131 — insignificant. TRAIN FAIL. |
| **Index-level skew/risk-reversal** | Tested as Skew sleeve. IC −0.018, t=−1.15, p=0.255 — insignificant. TRAIN FAIL. |
| **Sector lead-lag** | Tested as LAG sleeve. Wrong sign, 58% subsumed by momentum. TRAIN FAIL. |
| **OI flow dynamics (Flow sleeve)** | Killed at RFA. Max power 0.6053 < 0.80. Gate's first live kill. |
| **Relative-strength momentum (Nifty-BankNifty)** | Killed at RFA. Max power 0.337. Need Sharpe ≥1.30+. |
| **Option surface cross-section (strike × expiry)** | OSC probed: honest δ +0.0167, sd 0.2502, N_eff≈1.9. Fails power by ~2% before any OOS shrinkage. |
| **Breadth→futures directional translation** | CB-N50: constituent IC +0.029 (valid), but 0.35/0.65 breadth thresholds → wrong directional sign on Nifty futures. |
| **Options Max Pain** | Popular retail theory. The mechanism is dealer pinning, which is real (Edge 2). But Max Pain as a prediction rule ("Nifty will close at max pain strike") is untestable — it must be computed after the fact using the spot close, which is circular. |
| **GIFT Nifty / offshore lead** | The spread is closed in milliseconds by HFT firms. An independent researcher cannot compete on latency. Not researchable with EOD data. |
| **RBI policy surprise trading** | Only 6 meetings/year × 10 years = 60 observations. Insufficient for statistical inference. |
| **Any per_trade_pnl strategy on <10 index underlyings** | RFA gate demonstrates this is structurally dead. Single-index Sharpe ≥1.30+ and two-index Sharpe ≥1.30+ are both indefensible. |

---

## Data Gaps — What the Platform Does NOT Have

| Data | Importance | Availability | Action |
|------|-----------|-------------|--------|
| **BankNifty options bhavcopy** | HIGH | Available from NSE archives (free) | One-line ingest filter change. Archival data from 2016. Adds a second index's option surface. |
| **Crude oil (Brent/WTI) daily** | MEDIUM | Public/free | Download historical from FRED/Yahoo. Sector rotation research. |
| **USD/INR daily** | MEDIUM | MCX configured but not fetched | Run the configured `fetch_intermarket_data.py` with appropriate flags. Alternatively, RBI reference rate is free. |
| **10-year G-Sec yield** | MEDIUM | Public/free (RBI/CCIL) | Download historical. Bond-equity interaction research. |
| **RBI policy rate history** | LOW | Public/free | Download. Only 6/year — too few observations for systematic strategy. |
| **S&P 500, VIX (US) daily** | LOW | Public/free (Yahoo/FRED) | Overnight drift research. |
| **Nifty 50 historical index composition** | MEDIUM | Available from NSE Indices | Index rebalancing event study. |
| **Retail vs institutional options flow split** | HIGH | NOT AVAILABLE to retail | SEBI publishes aggregate statistics. Strike-level or broker-level retail flow data is proprietary and not purchasable. This is a binding constraint for Edge 5. |
| **Option tick data (bid-ask, trade-level)** | HIGH for execution simulation | NOT AVAILABLE (paid data, expensive) | Bhavcopy is EOD only. Realistic execution cost estimates need bid-ask. This is a binding constraint for Edge 1's backtest to be accurate. |
| **GIFT Nifty / SGX Nifty intraday** | LOW | Available via Bloomberg/Reuters (paid) | Not relevant — HFT-competitive space. |

---

## Recommendations

### Top 10 Most Plausible Structural Edges (Ranked)

| Rank | Edge | Tier | Gate-clear? | Economic Mechanism Strength | Research Cost | Data Available |
|------|------|------|------------|---------------------------|--------------|---------------|
| 1 | **Volatility Risk Premium — Index Short Volatility** | 1 | NO (per_trade_pnl gate) | Very Strong | Medium | Yes |
| 2 | **VIX-Based Regime Filter / Position Sizing** | 1 | N/A (risk management) | Very Strong | Very Low | Yes |
| 3 | **Dealer Gamma Feedback — Expiry-Day Dynamics** | 1 | NO (per_trade_pnl gate) | Strong | Medium | Yes |
| 4 | **Index Rebalancing — Passive Flow Capture** | 2 | N/A (event study) | Strong | Low | Partly (need composition history) |
| 5 | **Index Option Term Structure Cross-Section** | 2 | Uncertain | Moderate | Low | Yes |
| 6 | **Retail Option Fading** | 2 | NO (per_trade_pnl gate) | Strong | High | No (need retail flow split) |
| 7 | **Institutional Positioning — Futures OI Dynamics** | 2 | NO (per_trade_pnl gate) | Moderate | Low | Yes |
| 8 | **Composite Index Strategy (Meta-Edge)** | 2 | Possible | Strong (by construction) | High | Yes (for candidate signals) |
| 9 | **Sector Rotation from Cross-Asset Inputs** | 3 | NO (per_trade_pnl gate) | Strong but gate-killed | Medium | Partly |
| 10 | **Cross-Asset Contagion — Overnight Drift** | 3 | NO (per_trade_pnl gate) | Weak (arbed away) | Low | Partly |

### Which Deserve Immediate Research

**This week:**

1. **VIX-Based Regime Filter (Edge 3)** — Test in a single afternoon. Apply
   volatility-weighted position sizing to the Carry strategy's TRAIN/HOLDOUT/
   SEALED windows. Compare Sharpe and MaxDD to the un-scaled baseline. This
   costs nothing and could improve the platform's one production strategy.

2. **Index Rebalancing Event Study (Edge 8)** — Quick event study: for each
   Nifty 50 rebalance since 2016, measure the return of additions minus
   deletions from announcement to effective date + N days. Account for STT.
   If the net-of-fee return is negative or near-zero, reject the edge
   permanently.

**This month:**

3. **Volatility Risk Premium on Nifty Options (Edge 1)** — The flagship research
   program. Use the unread 2016–2022 Nifty options window for design. Test:
   sell ATM straddle, delta-hedge daily, account for STT and estimated bid-ask.
   Measure tail risk events. Determine if tail risk management (OTM put
   protection, stop-loss) preserves positive net returns net of costs.

   **Pre-registration required before any data read.** Pin: instrument
   (straddle/strangle/put), delta-hedge frequency, tail risk management rule,
   Universe (Nifty, BankNifty, both), parameter selection method. Freeze. Then
   read 2016–2022 for design, test ONCE on 2023–2026 for confirmation.

**This quarter:**

4. **BankNifty Options Ingest** — One-line filter change in the ingest script.
   Adds a second index's option surface (doubles the cross-asset dimension).
   Required for: any VRP strategy that diversifies across indices, gamma
   dynamics on Wednesday expiries, and term structure comparison across
   different underlying indices.

5. **Expiry-Day Gamma Dynamics (Edge 2)** — Research at daily resolution first
   (expiry vs non-expiry day volatility comparison). Intraday gamma profiling
   as a second phase.

### Which Should Be Abandoned Immediately

| Edge | Reason |
|------|--------|
| Any single-index timing strategy | RFA gate proves this is structurally dead. The sealed window is too short to distinguish genuine Sharpe ~0.5 from zero. |
| Any two-index pair strategy | Same arithmetic — need Sharpe ≥1.30+. Both RS-MOM and Nifty-BankNifty mean reversion are exhausted. |
| Any delivery-equity cross-sectional strategy | Fee wall — STT 0.1% both sides. PSB-1 and PSB-2 proved this beyond reasonable doubt. Escape to futures or options. |
| Nifty-BankNifty mean reversion | Exhaustively researched. Seven fatal findings. Do not reopen. |
| Max Pain / strike pinning as a standalone prediction rule | Circular — Max Pain requires the spot close to compute. Do not pursue without a causal mechanism (Edge 2's dealer gamma framework is the correct framing). |
| GIFT Nifty / offshore arbitrage | HFT-competitive. Not researchable with EOD data. |

### Which Require Data We Do Not Possess

| Edge | Missing Data | Obtainable? |
|------|-------------|------------|
| Retail Option Fading (Edge 5) | Strike-level retail vs institutional OI split | **No.** Broker-level data is proprietary. SEBI publishes aggregate only. |
| VRP — accurate execution simulation (Edge 1) | Option tick data with bid-ask spreads | **Expensive.** Paid data feed required. Bhavcopy proxies may suffice for research phase. |
| Sector Rotation (Edge 7) | G-Sec yield, crude oil, USD/INR | **Yes.** All free and public. Just not yet ingested. |
| Cross-Asset Contagion (Edge 9) | S&P 500 daily | **Yes.** Free (Yahoo/FRED). |
| Index Rebalancing (Edge 8) | Nifty 50 historical composition changes | **Yes.** NSE Indices publishes this. |

### Highest Probability of Durable Alpha

1. **Volatility Risk Premium** — Decades-old premium, every liquid options market
   globally, India-specific amplification from retail behavior. The tail risk
   problem is real but manageable. Highest probability of genuine structural
   alpha.

2. **Dealer Gamma Feedback** — Mechanical, not behavioral. Exists as long as
   (a) weekly options exist, (b) retail net-buys options, (c) dealers delta-hedge.
   All three are near-certain to persist indefinitely.

3. **VIX-Based Regime Filter** — Not alpha but a risk management overlay that
   improves risk-adjusted returns at near-zero cost. Highest probability of
   being correct at the lowest research cost.

### Realistically Achievable by an Independent Researcher

| Edge | Achievable? | Constraint |
|------|------------|------------|
| VIX-Based Regime Filter | **YES** — today | No constraints |
| Index Rebalancing Event Study | **YES** — this week | Needs composition history (free) |
| VRP Research | **YES** — research phase | Research is straightforward. Live execution is the bottleneck (margin, hedging frequency, tail risk). |
| VRP Live Execution | **PARTIALLY** | Margin for >2 Nifty option lots is substantial. Scaling is limited. But 1–2 lots of a systematic VRP strategy as part of a diversified portfolio is achievable. |
| Dealer Gamma (research) | **YES** | Data exists |
| Dealer Gamma (live) | **VERY DIFFICULT** | Intraday execution, latency competition, gamma computation in real-time |
| Composite Index Strategy | **YES** — over time | Each candidate signal must be individually tested. No shortcut. |
| Retail Option Fading | **NO** — without broker data | Cannot distinguish retail flow from institutional in OI data alone |
| GIFT Nifty Arbitrage | **NO** | HFT domain. Not researchable with EOD data. |

---

## The Governing Insight

The platform has already converged on the correct architecture for Indian markets:

- **Stock futures with rank_ic over a ~180-name cross-section** — Carry's home,
  the platform's one production-ready strategy
- **Index derivatives for structural premia** — VRP and gamma dynamics, which
  are harvested, not predicted
- **VIX-based regime management** — the bet-sizing lever that costs nothing

The history of failures teaches something load-bearing: **index timing (predicting
Nifty's direction) faces an arithmetic wall that cannot be overcome with better
signals, better feature engineering, or better models.** The wall is about sample
size, not signal quality. Cross-sectional strategies escape this wall; single-series
strategies do not.

The most productive path forward is:

1. **Harvest structural premia via index derivatives** (Edge 1, Edge 2) — these
   do not require predicting direction, they earn a premium for bearing a risk
   others want to shed.

2. **Improve existing strategies with risk management** (Edge 3) — zero marginal
   research cost, improves every strategy's Sharpe.

3. **Add missing data assets** — BankNifty options, cross-asset macro data
   (crude, USD/INR, yields) — to widen the research surface when future
   questions arise.

4. **Do not reopen index timing.** The wall is arithmetic. Accept it and move on.

---

## Appendix: Platform-Specific Implementation Notes

### For the VRP Research Program (Edge 1)

The 2016–2022 Nifty options bhavcopy window (1,701 daily formations) is the
single largest clean confirmatory window remaining. It must be protected:

- **Phase 1:** Research on 2016–2022. Design the strategy, select parameters,
  pin the hedge methodology. Pre-register everything.
- **Phase 2:** Read the 2023–2026 surface ONCE for confirmation. No parameter
  revision. This window is already burned for MSRP/OSC purposes — using it as
  confirmation preserves the principle even though the window is not pristine.
- **Phase 3 (later):** Ingest BankNifty options from 2016 onwards — this creates
  a second surface that is completely pristine and could serve as a true
  independent confirmation.

### For the VIX Regime Filter (Edge 3)

The simplest possible implementation:

```python
# Not code — just specification
vix_median = rolling_median(india_vix, window=252)
exposure_multiplier = clip(vix_median / india_vix_current, 0.25, 2.0)
adjusted_position_size = base_position_size * exposure_multiplier
```

Apply to the Carry strategy's signal. Compare Sharpe, MaxDD, Calmar ratio on
all three windows (TRAIN/HOLDOUT/SEALED). The multiplier clips prevent extreme
positions — at VIX = 100 (March 2020), exposure drops to 0.25×; at VIX = 8
(calm periods), exposure rises to 2.0× (subject to margin constraints).

### For the Index Rebalancing Event Study (Edge 8)

Quick event study spec:
- Universe: All Nifty 50 additions and deletions since 2016
- Signal: Buy additions on announcement date, sell deletions on announcement date
- Hold: Through effective date + 5 days (for passive flow to complete)
- Costs: STT 0.1% both sides (delivery), brokerage, stamp duty
- Null hypothesis: Net return ≤ 0 after costs
- If net return is near-zero or negative → permanently reject, move on
- If net return is positive and economically meaningful → design a full construct
