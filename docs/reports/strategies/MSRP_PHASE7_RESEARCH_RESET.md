# MSRP Phase 7 — Research Reset: Candidate Evaluation Dossier

**Document type:** Research dossier — evaluates every realistic path forward after the D1 STOP verdict. Recommends; the operator decides.

**Date:** 2026-07-07

**Predecessor:** The D1 (Knowledge-gated ATM straddle) triage confirmed a STOP verdict (`docs/reports/MSRP_PHASE7_FEE_TRIAGE.md`). The certified Knowledge — `expected_next_day_realized_vol` with Spearman 0.651 vs. actual RV in-sample, Approved on held-out — remains valid. The failure was in the *transmission*: unhedged straddle P&L has Spearman 0.093 with next-day RV. The construct gap warned about in the D1 research doc was measured, and it dominates.

---

## The Central Diagnostic

The single binding fact driving this dossier:

| Chain step | Spearman rho | Verdict |
|---|---|---|
| E[RV] → actual RV (forecast quality) | 0.651 | **Strong** — the artifact works |
| Actual RV → straddle open→close return (transmission) | 0.093 | **Nil** — unhedged straddle is the wrong instrument |
| E[RV]/VIX → straddle open→close return (end-to-end) | −0.027 | **Broken** — the gated signal has no exploitable rank relationship |

This is not a fee problem (drag ≈ 6%). This is not a "wrong threshold" problem. This is a construct problem: an unhedged ATM straddle held open→close pays off on `|Δspot|`, not on `Σ(r²)`. These are correlated at long horizons and near-orthogonal at 1-day. Any strategy design that routes this Knowledge through an unhedged options P&L — long or short, any strike, any expiry — inherits this transmission ceiling.

**Therefore:** Candidate evaluations that depend on straddle/option P&L as the return variable inherit the same failure by construction. Candidates that use the Knowledge *directly* in risk/sizing/execution decisions bypass the transmission entirely.

---

## Candidate A — Alternative Volatility Trading

### A1 — Delta-hedged straddle
The only clean isolation of RV−IV: buy the straddle, delta-hedge intraday. P&L ≈ (RV² − IV²) × gamma — the exact construct the artifact forecasts. **Blocked by data:** delta-hedging needs intraday options prices or at minimum intraday spot for synthetic hedging. Bhavcopy is EOD only. An Upstox Plus subscription might offer expired-contract intraday candles, but history depth is ≤ 20 months per community reports. **NO-GO — data does not exist at retail scale for 2023–2026.**

### A2 — Vega-neutral option spreads
Vertical/butterfly/calendar spreads don't need intraday rebalancing. Could be priced from bhavcopy EOD. But the P&L driver is vol *structure* (smile slope, term structure), not vol *level*. The artifact forecasts vol level. A vega-neutral spread is net short skew and long/short the spread — the RV forecast says nothing about skew. **NO-GO — forecasts the wrong variable.**

### A3 — Gamma scalping
Buy gamma cheap, scalp intraday. Needs tick data. **NO-GO — data doesn't exist.**

### A4 — Variance-swap approximation (CBOE-style strip)
Buy a strip of OTM options across strikes (like VIX calculation), hold to expiry. P&L ≈ Σ(σ²_realized − K²_var). This is the *best construct match available at daily cadence* — the P&L is a function of realized variance, exactly what the artifact forecasts. Feasible with bhavcopy: for each day, compute the VIX-style strip price and compare to forecast. Daily-cadence, EOD-priced, construct-aligned. **FUTURE — best transmission but complex implementation (multi-strike options portfolio, era-accurate contract selection, non-trivial backtest). Strong Inc-2 candidate.**

### A5 — Dispersion
Long index options, short single-stock options. Needs stock options data (not in bhavcopy scope). **NO-GO — data.**

**Candidate A verdict: NO-GO for Phase 7.** A4 (variance swap) is the strongest construct match and merits Inc-2 but is too complex for the next step after a STOP.

---

## Candidate B — Options Premium Selling (Filter Variants)

### B1 — Sell on predicted low-vol days only
D1 gated-short already tested this: the unconditional short (+110K) outperformed every gated-short variant. Transmission ceiling (0.093) means the Knowledge cannot select *better* short days at daily horizon. **NO-GO — same failure as D1.**

### B2 — Avoid selling on predicted high-RV days
Asymmetric framing: don't try to pick winners, try to avoid losers. On the 10% of days with highest E[RV], the unconditional short lost −9,470 gross (D1 triage table, q10 row). Can the Knowledge identify *specifically dangerous* short days? The Spearman of −0.027 says no — the highest E[RV] days are not the worst short-straddle days. The days that SMASH short straddles tend to be gap events (overnight news, VIX spikes) where the artifact (issued at close) has stale information. **NO-GO — the forecast catches persistent vol, not jump risk.**

### B3 — Dynamic strike selection away from ATM
OTM short strangles collect premium on tails. But the artifact forecasts ATM RV, not tail behavior. Moving strikes introduces smile-exposure — an entirely new variable the artifact doesn't address. **NO-GO — forecasts wrong aspect of vol surface.**

### B4 — Dynamic expiry selection
Longer-DTE straddles have higher vega, making the P&L more sensitivity to implied-realized spread rather than terminal move ± vega. But the artifact is a 1-day forecast — extending to multi-day holdings requires forecasting the vol path, not just next-day RV. **NO-GO — forecasts wrong horizon.**

**Candidate B verdict: NO-GO.** Every variant faces the same 0.093 transmission ceiling, or adds variables the artifact doesn't forecast.

---

## Candidate C — Futures Overlay

This is the "prior art" failure mode documented in `DRA_TECHNICAL_DOSSIER.md`: the pre-SALVAGE codebase's HMM regime classifier was sound, but the directional strategy built on it lost money because the host strategy had no edge. The documented verdict was "repurpose as a market-timing filter for existing profitable strategies" — which stalled because no profitable host existed.

Today, that is still true. The repository has no production SignalSource beyond the MM13 proof-of-concept.

A futures overlay asks: "use Knowledge to improve an existing strategy." Since no existing strategy exists, the test becomes two hypotheses — "find a directional edge" PLUS "does Knowledge improve it" — where a null result is unattributable.

**NO-GO — wait until a profitable directional strategy exists.** This is not a Phase 7 decision; it's a future integration point for any post-Phase-7 alpha.

---

## Candidate D — Execution Optimizer

### Core idea
Use E[RV] not for *whether* to trade but for *how* to trade: adaptive stops, targets, and sizing that scale with expected volatility. No options. No construct gap. Direct, linear use of the forecast.

### Economic intuition
If you have a fixed-direction position (e.g., always long 1 Nifty) with a fixed 1% stop, you'll be stopped out more often on high-vol days — not because your direction was wrong, but because the noise floor was higher. An RV-aware stop that widens proportionally to expected vol should reduce noise-exits without changing the strategy's expected value. Conversely, a tight stop on a low-vol day captures the same risk budget with less capital at risk.

### Test design
Take a fixed daily Nifty position (entry at open, exit at close). Compare:
- **Fixed regime:** 1% stop from entry, 2% target
- **Vol-scaled regime:** Stop = E[RV] × 2, Target = E[RV] × 4
- **Abstention:** Flat when the 90% predictive interval for E[RV] is too wide (uncertainty gating — the first real use of the MM13 `uncertainty` field)
- Metric: Win rate, profit factor, Sharpe, max drawdown — all net of the existing equity fee model

### Data
- 1m Nifty bars (2023–present, available)
- Knowledge (available via the certified artifact)
- No additional data required

### Research feasibility
**EXCELLENT.** One-day implementation. No new data. No new platform components. The triage script (`triage_fee_impact.py`) provides a template — remove the options layer, add stop/target logic, keep the E[RV] → signal pipeline. Backtestable over the full dev window.

### Statistical power
~700 dev trading days for a direction-neutral test (long every day, win/loss depends on Nifty direction). The expected win rate is ~50% for the fixed regime. The test is: does vol-scaled stop/target placement improve risk-adjusted metrics? A 5% improvement in Sharpe on ~700 days needs a bootstrap to be statistically meaningful but direction is observable.

### Fatal weaknesses
- No edge in the underlying direction (long Nifty every day = beta, not alpha). If the entire strategy is beta, the execution optimizer is optimizing beta exposure, not alpha generation.
- This is a better test than D1 was (no construct gap), but the economic value is in risk-management improvement, not standalone P&L.

### Verdict
**GO — secondary priority.** Low-risk, fast to implement, uses the Knowledge directly. Should be built alongside a primary candidate (E) rather than as the standalone deliverable.

---

## Candidate E — Risk Management / Vol-Targeted Position Sizing

### Core idea
Use E[RV] to *size* positions: scale position size inversely with expected volatility to maintain constant risk exposure. This is the most institutionally natural use of a vol forecast — risk targeting, not alpha generation.

### Economic intuition
Professional allocators target risk (vol). A portfolio manager who wants 10% annualized vol on Nifty needs to know tomorrow's RV to set tomorrow's position size. If E[RV] says tomorrow will be 2× normal vol, halve the position. If E[RV] says tomorrow will be 0.5× normal, double it. The resulting portfolio has more stable realized volatility — the primary objective of risk management.

### Why this bypasses the construct gap
Risk management doesn't need E[RV] → P&L transmission. It needs E[RV] → position_size → realized_portfolio_vol. The metric is *vol stability*, not P&L. The 0.651 Spearman between E[RV] and actual RV is directly the relevant quality measure — no options, no straddles, no transmission step between forecast and use.

### Test design
**PAPER (forward):** Take a fixed-bias position (e.g., always long 1 unit × sizing_factor Nifty). Compare:
- **Fixed-size:** Always 1 lot; realized portfolio vol = whatever the market gives
- **Vol-targeted:** Position = capital × target_vol / E[RV_t+1]; realized portfolio vol should be closer to target
- **Uncertainty-gated:** Reduce size further when the predictive interval is wide (the uncertainty field earns its keep)

Primary metric: standard deviation of daily P&L. Secondary: Sharpe (mean unchanged, denominator shrinks → Sharpe improves by construction if sizing works). Benchmark: the unconditional fixed-size portfolio.

**DEV backtest:** Same design, 2023–2025, to calibrate the sizing function. This is a sizing calibration, not a strategy backtest — the P&L is still driven by Nifty beta.

### Data
- 1m Nifty bars (available)
- Knowledge (available)
- No additional data required

### Research feasibility
**EXCELLENT.** Partially pre-built: the `ForwardVolatilityArtifact` already emits the named estimate. The `position_tracker` in execution already supports sizing. The missing piece is a SignalSource that reads the Knowledge and emits signals with vol-scaled position metadata — a thin extension of the MM13 `KnowledgeSignalSource` pattern.

### Statistical power
The metric is vol stability, not P&L. On ~700 days, the variance of realized vol is estimable. The test tracks *whether* the vol-targeted portfolio has lower realized vol dispersion, not *whether* it makes money — a simpler statistical question.

### Platform impact
- New `core/strategies/vol_targeted_signal_source.py` — selects named estimate, emits signals with vol-scaled sizing
- Existing execution stack unchanged (size flows through to margin → PaperBroker)
- Existing MM13 consumer contract unchanged
- Zero frozen-component changes

### Implementation complexity
**LOW.** One new SignalSource file. One calibration script. PAPER verification on forward data.

### Fatal weaknesses
- The strategy is beta, not alpha. Long Nifty every day = Nifty returns. Vol-targeting changes the risk profile, not the expected return.
- But that is exactly the charter's Phase 7: "a core/strategies/ source that consumes v2 Knowledge and genuinely attempts P&L." A risk-managed beta position consumes the Knowledge and genuinely manages the risk of P&L. Whether "genuinely attempts P&L" requires a positive expected return beyond beta is an operator interpretation question — a vol-targeted beta portfolio doesn't generate alpha, but it generates a more *controlled* beta exposure, which is P&L-relevant for any leveraged or drawdown-constrained investor.

### Verdict
**GO — PRIMARY recommendation.** Direct construct match (no transmission gap), uses the Knowledge exactly as it was designed, testable in one day, platform-ready, and architecturally the most natural consumer of a daily vol forecast. Risk management is the first use-case a real institution would deploy this Knowledge for — alpha comes after risk.

---

## Candidate F — New Knowledge Sources

### Premise
Return to the Phase-0 charter and select a different latent variable for MSRP Increment 2, rather than forcing the vol Knowledge into a role it was not designed for.

### Candidates evaluated

| Latent variable | Data | Difficulty | Platform value | Verdict |
|---|---|---|---|---|
| Expected return (direction) | 1m Nifty | HIGH — directional forecasting is the hardest problem; prior art failed | Highest if solved | FUTURE — needs a fundamentally different model class |
| Market regime (HMM / classifier) | 1m Nifty + VIX | MEDIUM — prior art had a working classifier (DRA technical dossier) | HIGH — regime-context for any strategy | GO — strongest Inc-2 candidate; the classifier worked before |
| Trend probability | 1m Nifty | MEDIUM | MEDIUM — technical overlay, not standalone | FUTURE |
| Mean-reversion probability | 1m Nifty | MEDIUM | MEDIUM — pairs with vol for vol-mean-reversion strategies | FUTURE |
| Cross-sectional ranking | Stock 1m (not available) | HIGH | HIGH — pairs trading, factor models | NO-GO (data: only Nifty index) |
| Liquidity | Order book (not available) | BLOCKED | HIGH — execution quality | NO-GO (data) |

### Assessment
The infrastructure exists (DRA, M0–M9, A1–A2 harness, MSI-006 validation). Building a second artifact is an engineering exercise, not an architecture exercise. But:

1. **Exhaust the existing artifact first.** The vol Knowledge is validated and frozen. Candidates D and E use it directly with no construct gap. Deploy those before searching for new Knowledge.
2. **Market regime is the strongest Inc-2 candidate.** It pairs naturally with vol (vol-regime → sizing; direction-regime → entry). It has a working prior implementation (the HMM classifier from the pre-SALVAGE DRA). It addresses the "both sides" gap: vol tells you *how much* to trade; regime tells you *when*.
3. **Do not start Inc-2 until Inc-1 has a functioning consumer.** The platform's gap is not "too few Knowledge artifacts" — it's "zero consumers of the one we have."

**Verdict: FUTURE — gate on Inc-1 closure.** Market regime is the recommended Inc-2 artifact. Do not start until Candidates D/E are PAPER-verified.

---

## Candidate G — Hybrid Multi-Knowledge Framework

### Assessment
This is long-term platform architecture, not a Phase 7 decision. The MSRP thin-slice principle explicitly warns against big-design-up-front: "prove one hypothesis end-to-end before growing the framework." A multi-Knowledge architecture before any single Knowledge has a production consumer is exactly that trap.

The correct sequence is:
1. Vol Knowledge → risk management consumer (Candidate E) → PAPER-verified
2. Later: regime Knowledge → direction consumer → the two combine

The architecture for combining Knowledge is already partially specified (MM13 `KnowledgeSignalSource` selects one named estimate; a multi-Knowledge source would select multiple and combine them). The engineering surface is minimal — the delay is in *having the Knowledge*, not the architecture to combine it.

**Verdict: FUTURE — deferred. Correct direction, wrong timing.**

---

## Candidate H — Phase 7 Redefinition

### Core question
Is "First Alpha Strategy" still the correct milestone, or should Phase 7 be redefined based on what was learned?

### Assessment

The charter's Phase 7 definition: "a core/strategies/ source that consumes v2 Knowledge and genuinely attempts P&L." The D1 experiment attempted exactly this — it consumed the Knowledge through an options strategy and failed on construct, not on forecast quality. The experiment was well-posed and produced a definitive answer.

**Should Phase 7 continue as "First Alpha Strategy"?**
An alpha strategy requires positive expected return beyond the risk-free rate on a risk-adjusted basis. Candidate E (vol-targeted sizing) is a *risk management* strategy — it controls risk, not generates return. Candidate D (execution optimization) improves risk-adjusted metrics but doesn't create standalone alpha. Neither meets the strictest reading of "alpha."

**Should Phase 7 be redefined?**
The recommended redefinition: **"First Production Knowledge Consumer"** — a `core/strategies/` source that consumes the Knowledge and produces a measurable improvement in either:
- Risk-adjusted returns (Sharpe, drawdown)
- Risk stability (vol targeting)
- Execution quality (sizing, stops)
- Any pre-registered metric that demonstrates the Knowledge's platform value

This is broader than "alpha" but narrower than "anything goes." It demands a pre-registered metric and a measurable improvement over a no-Knowledge baseline — the same discipline that the alpha framework enforced.

**What changes?**
- Charter Amendment: MSRP Phase 7 redefined to "First Production Knowledge Consumer"
- Deliverable: a PAPER-verified SignalSource + pre-registered metric + baseline comparison
- Phase 7 completes when: the consumer is PAPER-verified, and its pre-registered metric demonstrates improvement over the no-Knowledge baseline
- Inc-2 opened after Phase 7 closure

**Verdict: Adopt the redefinition.** The charter was written before we knew the construct gap. The disciplined response is to update the milestone to match what was learned, not to force-fit "alpha" onto a risk-management forecast.

---

## Final Comparison Table

| Cand | Description | Construct match | Data ready | Platform ready | Research difficulty | GO/NO-GO |
|------|-------------|-----------------|------------|----------------|---------------------|----------|
| A | Alternative vol trading | **A4: EXCELLENT** (variance swap); rest: NO-GO | A4: Yes (bhavcopy, complex) | A4: Needs multi-strike portfolio | A4: HIGH | **A4: FUTURE (Inc-2)**; rest: NO-GO |
| B | Premium selling filter | ALL: NO-GO (0.093 ceiling) | Yes | Yes | LOW (already tested by D1) | **NO-GO** |
| C | Futures overlay | INDIRECT | Yes | Yes | Needs host strategy | **NO-GO — until host exists** |
| D | Execution optimizer | **EXCELLENT** — no transmission | Yes | One new SignalSource | **LOW** | **GO (secondary)** |
| E | Risk management (vol-targeted sizing) | **DIRECT** — forecast → sizing, no P&L transmission | Yes | One new SignalSource + calibration | **LOW** | **GO (PRIMARY)** |
| F | New Knowledge sources | N/A (different latent variable) | Varies | Infrastructure exists | HIGH (new research cycle) | **FUTURE (Inc-2, after E/D verified)** |
| G | Multi-Knowledge framework | N/A (architecture) | N/A | Partially specified (MM13) | MEDIUM (architecture) | **FUTURE — deferred** |
| H | Redefine Phase 7 | N/A (governance) | N/A | Charter amendment only | LOW | **ADOPT** |

---

## Recommendation

1. **Amend the charter:** Redefine Phase 7 as "First Production Knowledge Consumer" (Candidate H). The D1 experiment proved the forecast works; it also proved the specific transmission failed. The milestone should capture what was learned.

2. **Primary Phase 7 deliverable: Vol-Targeted Position Sizing (Candidate E).** The Knowledge is an intraday vol forecast. The natural consumer is a sizing engine that adjusts position size to maintain constant risk exposure. This is the direct, gap-free use. Pre-register: target vol, sizing function, metric (realized portfolio vol dispersion vs. fixed-size baseline), decision rule. PAPER-verify on forward data.

3. **Secondary (built alongside): Execution Optimizer (Candidate D).** Vol-adaptive stops and targets. Same Knowledge, complementary use. Pre-register: stop/target scaling function, metric (Sharpe improvement, win-rate change), baseline comparison.

4. **Inc-2 roadmap (FUTURE, after E/D verified):**
   - A4 (variance-swap approximation) — best construct match for vol trading, merits deeper research
   - F (Market Regime artifact) — strongest new latent variable, pairs naturally with vol Knowledge

5. **Do not:** Build another options strategy (A1–A3, B), wait for a directional host (C), or start multi-Knowledge architecture (G) before the first Knowledge has a PAPER-verified consumer.

---

*End of research dossier. This document recommends; the operator decides. A charter amendment for Phase 7 redefinition requires the same governance process as the Phase-0 charter decisions (§8).*
