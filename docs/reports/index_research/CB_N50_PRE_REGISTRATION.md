# CB-N50: Constituent-to-Index Breadth — Pre-Registration

**Status:** RFA PROCEED (2026-08-01) — not provably infeasible, not authorised to build.
**Declaration:** `governance/rfa/declarations/cb_n50.py` (SHA-256: `e0437067…`)

---

## 1. Construct

### 1.1 Core Architecture

```
stock-level forecasts → daily cross-sectional rank IC → weighted breadth score → Nifty futures position
```

The primary hypothesis is **stock-level cross-sectional prediction**: can a pre-specified feature set rank Nifty 50 constituents by next-day return? The index futures position is a derived execution — a translation of the aggregate breadth score, not a second opportunity to optimise.

This is NOT:
- A Nifty-only timing model (the RFA would reject it — `per_trade_pnl` fails with the 3.5-year sealed window)
- A two-index spread (the RS-MOM ABANDON is dispositive for that family)
- A tweak to the rejected mean-reversion pair construct

### 1.2 Feature Set (pre-specified, frozen)

Three features, each computed per-constituent, per-day:

| Feature | Description | Literature |
|---------|-------------|-----------|
| **Relative momentum** | (close_t / close_{t-L} - 1) minus cross-sectional median, L∈{5,10,20} | Jegadeesh-Titman 1993 |
| **Futures basis** | Residual basis = (futures_price / spot_price - 1) annualised, minus cross-sectional median, winsorised ±3σ | Koijen-Moskowitz-Pedersen-Vrugt 2018 |
| **Short-term reversal** | -(close_t / close_{t-1} - 1), minus cross-sectional median | Jegadeesh 1990 |

Features are cross-sectionally normalised (z-score within the daily Nifty 50 panel, winsorised ±3σ) before combination.

**Feature combination**: Equal-weighted sum of normalised feature z-scores. The combination weight is fixed at 1/3 per feature — no optimisation on TRAIN (this prevents a multiplicity penalty on the features themselves). If a feature is later dropped (e.g., basis unavailable for non-F&O constituents), the remaining features are re-weighted equally.

### 1.3 Signal Computation

For each trading day t:

1. Compute each feature score for each Nifty 50 constituent (PIT membership)
2. Cross-sectionally normalise each feature to z-scores within the panel
3. Compute combined score = mean of normalised feature z-scores (§3.3)
4. Compute **daily cross-sectional rank IC** = Spearman correlation between combined scores at t and open-to-open returns (t+1 open → t+2 open), across the Nifty 50 cross-section
5. Compute **breadth score** = fraction of constituents with combined score above zero, weighted by free-float market cap (§3.5)

### 1.4 Index Position Rule (pre-registered)

The breadth score maps to a Nifty futures position via a **fixed, pre-registered rule** (fully specified in §3.5):

```
if breadth_score > 0.65:  LONG  Nifty futures (1 unit)
if breadth_score < 0.35:  SHORT Nifty futures (1 unit)
else:                     FLAT
```

**Hold**: enter at open t+1, exit at open t+2. Re-evaluate daily. Execution timeline specified in §3.6. Position sizing is fixed 1 unit — the futures P&L is an execution-translation check, not a second optimisation surface.

### 1.5 Universe

Nifty 50 constituents, point-in-time (PIT), from the NIFTY-200 universe in `equity_bhavcopy_adjusted`. Membership changes (additions/deletions) are applied on the effective date from `symbol_entity_intervals`.

Each day's cross-section contains exactly those stocks that were Nifty 50 members on that date. Constituents with missing data (suspended, not yet listed, data gap) are excluded from that day's cross-section; the rank IC is computed on the remaining N≥30 stocks.

### 1.6 Execution Vehicle

Nifty futures (NSE FO segment). Single-leg only. The breadth score aggregates 50 stock-level predictions into one index-level direction. Execution timeline (enter at open t+1, exit at open t+2), cost model, slippage, and roll handling are fully specified in §3.6.

---

## 2. RFA Gate — PROCEED

### 2.1 Declaration Parameters

| Parameter | Value |
|-----------|-------|
| Metric | rank_ic |
| Test type | two_sided |
| Cadence | daily |
| n_available (sealed) | 887 (2023-2026) |
| delta band | [0.010, 0.035] |
| sd band | [0.15, 0.25] |
| Power hurdle | 0.80 |

### 2.2 Gate Result

| Verdict | **PROCEED** |
|---------|-------------|
| Max power (optimistic) | 1.000 |
| n_required (optimistic) | 147 |
| n_required (central) | 623 |
| n_required (pessimistic) | 4,908 |
| n_available | **887** |

The optimistic corner clears by a wide margin (ncp=6.95). The central case clears (n_required=623 < 887). The pessimistic case fails (n_required=4,908) — as designed, since low-delta/high-sd combinations are the "the signal barely exists" scenario.

### 2.3 Why This Clears When RS-MOM Failed

| | RS-MOM (ABANDON) | CB-N50 (PROCEED) |
|---|---|---|
| Metric | per_trade_pnl | rank_ic |
| ncp formula | S × √T | (δ/sd) × √n |
| Sealed window | Same 2023-2026 | Same 2023-2026 |
| n (observations) | 186 (weekly trades) | 887 (daily ICs) |
| sd (noise) | 1.0 (by construction) | 0.15-0.25 (IC dispersion) |
| δ/sd ratio | S=0.65 max | 0.035/0.15=0.233 |
| ncp | 0.65×1.89=1.23 | 0.233×29.8=6.95 |

Both constructs use the same 3.6-year sealed window. The difference is **measurement density**: `rank_ic` produces one observation per trading day (a cross-sectional rank correlation over 50 constituents), while `per_trade_pnl` produces one observation per completed trade cycle. The daily cross-section gives 887 IC observations from the same window that yields only 186 weekly trades. IC dispersion (sd=0.15-0.25) is also much smaller than the per_trade_pnl unit standard deviation (1.0). Together: ncp ≈ 7 at the optimistic corner vs ncp ≈ 1.2 for RS-MOM.

---

## 3. Pre-TRAIN Requirements (must be pinned before any data read)

These are frozen specifications — none may be revised in response to TRAIN results.

### 3.1 Universe

- **Point-in-time Nifty 50 membership** determines eligibility. The NIFTY-200 universe dataset (`symbol_entity_intervals`) is the **data source** — it must not become a proxy universe. Every constituent included in the cross-section on a given date must be independently verified as a Nifty 50 member on that date, not merely a NIFTY-200 member.
- **Survivorship bias**: membership is PIT — a stock that enters Nifty 50 mid-window is included from its effective date; a stock that leaves is excluded from its removal date. No look-ahead. The cross-section on a date contains only those stocks that WERE Nifty 50 members on that date.
- **Free-float market-cap weights** from the same source, used for the weighted breadth score only (not for IC computation, which is equal-weighted rank correlation).
- **Missing-data rule**: constituents with missing data on a given day (suspended, not yet listed, data gap) are excluded from that day's cross-section. The rank IC must be computed on the remaining N ≥ 30 stocks. Days with N < 30 are excluded entirely from the IC series.
- **Verification gate**: before any TRAIN read, verify Nifty 50 PIT membership against NSE published changes for ≥20 randomly sampled dates across 2016-2026. Cross-check that no NIFTY-200-but-not-Nifty-50 stocks appear in the cross-section.

### 3.2 Target and Metric

- **Target return**: open-to-open. Specifically, the return from the open auction price on day t+1 to the open auction price on day t+2. This avoids the look-ahead bias of close-to-close: a signal computed from day t closing data cannot be executed at day t's close.
- **Signal computation timing**: features are computed from closing data available at the end of trading day t. The combined score for day t is finalised after the day t close.
- **Metric**: daily cross-sectional **Spearman** rank correlation between the combined signal score (computed after day t close) and the open-to-open return (t+1 open → t+2 open), across the Nifty 50 constituents present on day t.
- **Observation unit**: one IC value per trading day. **Not** 50 × 887 pseudo-independent stock-days. The statistical test operates on the time series of 887 daily IC values, each computed from a cross-section of ~50 stocks.

### 3.3 Feature Set (closed, frozen)

Three features. No additions, no removals after this specification is frozen.

| Feature | Formula | Sign | Missing-data rule |
|---------|---------|------|-------------------|
| **Relative momentum** | (close_t / close_{t-L} - 1) − cross-sectional median | Positive | Exclude if fewer than L days of prior close available |
| **Futures basis** | Residual basis = (futures_close / spot_close − 1) annualised, winsorised ±3σ, minus cross-sectional median | Positive | Exclude if no futures data exists for that underlying |
| **Short-term reversal** | −(close_t / close_{t-1} − 1) − cross-sectional median | Positive | Exclude if prior close missing |

- **Winsorisation**: cross-sectional z-scores clipped to ±3.0 before combination, applied within each day independently.
- **Normalisation**: each feature is cross-sectionally z-scored within the daily Nifty 50 panel (subtract cross-sectional mean, divide by cross-sectional std) before combination.
- **Combination**: equal-weighted sum of z-scored features (weight = 1/3 per feature). If a feature is unavailable for a given stock (e.g., basis for non-F&O constituent), the stock is still scored on the remaining features with equal weights among available features.

### 3.4 Autocorrelation-Aware Inference

Daily IC is serially correlated — a signal that persists across adjacent days produces correlated IC values. The statistical inference must account for this:

- **Effective sample size**: the noncentral-t power computation assumes independent observations. The RFA gate does not apply an AC haircut, so the PROCEED verdict depends on the declared bands being defensible even at a reduced effective n. At AC₁=0.3, effective n ≈ 887 × (1−0.3)/(1+0.3) ≈ 477 — the optimistic corner still clears (ncp ≈ 5.1, power ≈ 1.00).
- **TRAIN/HOLDOUT/SEALED inference**: all IC hypothesis tests must use **Newey-West standard errors** with a lag length chosen by automatic bandwidth selection (Andrews 1991). The t-statistic is computed as mean(IC) / Newey-West SE(mean). This replaces the naive t-test that assumes independent IC observations.
- **Pre-committed AC₁ disclosure**: the AC₁ of the daily IC series must be reported alongside every gate result. If AC₁ > 0.5, the observation density is mostly redundant and the construct should be reconsidered.

### 3.5 Index Position Rule (frozen)

The breadth score maps to a Nifty futures position via a **fixed rule with no parameter to optimise**:

```
For constituents i = 1..N on day t, where N = number with usable inputs:
  S_i = combined_score_i           # mean of normalised feature z-scores (§3.3)
  w_i = free_float_mcap_i          # from PIT Nifty 50 membership data
  eligible_i = S_i is not NaN      # constituent has usable features

Let M = count of eligible constituents on day t.
If M = 0: day is unscorable — no position, no IC observation.

breadth_score = sum(w_i for i where S_i > 0 and eligible_i) /
                sum(w_i for i where eligible_i)

if breadth_score > 0.65:  LONG  Nifty futures (1 unit)
if breadth_score < 0.35:  SHORT Nifty futures (1 unit)
else:                     FLAT
```

- **Thresholds (0.35, 0.65)** are symmetric around 0.5 and represent the top/bottom tercile of possible breadth values. They are pinned by the construct design, not fitted to data.
- **Neutral region [0.35, 0.65]** represents days where the aggregate signal is too ambiguous to act. A FLAT position on these days is the correct behaviour — forcing a position when half the index is scored positive and half negative is noise-trading, not conviction.
- **Low-N treatment**: if M < 30 eligible constituents, the day is unscorable — no breadth score computed, no IC observation generated, no position taken. This is consistent with the IC minimum-N rule in §3.1.
- **No later threshold optimisation** is permitted. If the TRAIN data suggests different thresholds would have performed better, that finding is recorded as a caveat but the thresholds remain unchanged.
- **Position sizing**: fixed 1 unit of Nifty futures. No volatility scaling, no Kelly sizing, no regime-dependent gearing. The futures P&L is an execution-translation check, not a second optimisation surface.

### 3.6 Tradability Timing (execution alignment)

A signal computed from day t closing data cannot be executed at that same close. The following timeline is pinned:

```
Day t:
  - Market closes. Closing prices for all Nifty 50 constituents are final.
  - Feature scores computed after close t using day t closing data.
  - Combined score, breadth_score, and position decision finalised before
    day t+1 open.

Day t+1:
  - ENTER position at the OPEN auction price of Nifty futures on day t+1.
  - No intraday entry timing — the open price is the first executable price
    after the signal is known.

Day t+2:
  - EXIT position at the OPEN auction price of Nifty futures on day t+2.
  - The target return for IC validation is the constituent stock's
    open(t+1)-to-open(t+2) return, consistent with the holding period.

Rollover: if day t+2 is a roll date (2 days before futures expiry), the exit
occurs on the expiring contract's open and the next entry (if any) occurs on
the new near-month contract's open on day t+2.
```

- **Cost model**: Nifty futures round-trip: brokerage + STT (0.0125% sell side) + exchange transaction charge (0.0019%) + SEBI turnover fee (0.0001%) + stamp duty (0.002% buy side) + GST (18% on brokerage + exchange). Estimated total ~2-3 bps per round-trip. Exact schedule from broker at execution time; era-accurate statutory changes applied.
- **Slippage**: κ = 2 bps/side added to the open auction price for entry and exit. This covers the bid-ask spread on Nifty futures at market open (typically 1-2 ticks = ~1-2 bps) plus a conservative buffer.
- **No intraday execution**: entry and exit both at the open auction. This eliminates intraday timing as a free parameter and makes the backtest reproducible from daily OHLC data.
- **Operational validity**: NSE runs a 9:00-9:15 call-auction pre-open session for current-month index futures, with the equilibrium price treated as the day's open. This price is directly executable — the open-auction convention is not a modelling convenience, it is the exchange mechanism.

---

## 4. Research Phases

### Phase 1: Substrate Certification

Before any TRAIN read:
1. **Universe gate**: Verify Nifty 50 PIT membership is correct for a random sample of dates (≥20 dates across 2016-2026). Cross-check against NSE published changes.
2. **Data gate**: Verify every Nifty 50 constituent has equity bhavcopy data on every membership date. Missing-data rate must be <1% of constituent-dates.
3. **Futures gate**: Verify Nifty futures data exists on all required dates. Verify roll dates and near-month contract identification.
4. **Execution-price gate**: Confirm that entry and exit prices in the backtest use the **actual Nifty futures open auction price** (not the cash-index open, not a synthetic open derived from spot). The futures pre-open call-auction equilibrium price is the executable price.
5. **Roll-rule gate**: Confirm the pinned roll rule (2 days before expiry, near-month → next-near-month) is applied **before** computing returns. A position opened on the expiring contract and held through roll must exit on the expiring open and the next entry (if any) on the new contract open.

### Phase 2: TRAIN (2016-2019, ~1,008 daily formations)

Burned for:
1. Feature lookback selection: for each feature, test L∈{5,10,20} and select the best-performing lookback by mean IC (not by net spread). This is a **multiplicity cost** of m=3 per feature × 3 features = 9 comparisons. Bonferroni-corrected α = 0.05/9 ≈ 0.0056 per test.
2. Signal validation: measure daily rank IC of the combined signal. IC must be statistically significant (Newey-West t-test, Bonferroni-adjusted for m=9).
3. Breadth-threshold verification: confirm the pre-registered thresholds (0.35, 0.65) produce signed index positions that are directionally consistent with subsequent Nifty returns. **Thresholds are NOT optimised** — this is a confirmation check, not a selection step.

**Gate**: Combined IC must have Newey-West t-statistic with Bonferroni-adjusted p < 0.05. If it fails, no HOLDOUT read is authorised.

### Phase 3: HOLDOUT (2020-2022, ~748 daily formations)

1. Confirm combined IC with Newey-West t-test (single test, α=0.05, no Bonferroni since TRAIN multiplicity was already paid).
2. Measure Nifty futures P&L from the breadth-threshold rule with era-accurate costs.
3. Compute net spread, Sharpe, MaxDD, and compare to buy-and-hold Nifty.

**Gate**: IC must remain significant (p<0.05). Futures P&L must be positive net of costs. If both pass, SEALED read is authorised.

### Phase 4: SEALED (2023-2026, ~887 daily formations)

One-shot read. Never re-run.
1. Daily rank IC of combined signal (Newey-West, single test, α=0.05).
2. Nifty futures P&L from breadth rule, era-accurate costs.
3. All metrics frozen in `CB_N50_SEALED_SNAPSHOT.json`.

---

## 5. Acceptance Criteria

### 5.1 Phase 2 (TRAIN) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G1 | Combined IC Newey-West t-test, Bonferroni p<0.05 (m=9) | No HOLDOUT read |
| G2 | At least one feature has positive mean IC after lookback selection | Drop that feature, re-test |

### 5.2 Phase 3 (HOLDOUT) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G3 | Combined IC significant at p<0.05 (single test) | No SEALED read |
| G4 | Nifty futures net P&L > 0 after costs | No SEALED read |

### 5.3 Phase 4 (SEALED) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G5 | Combined IC significant at p<0.05 (single test) | Construct falsified |
| G6 | Nifty futures net P&L > 0 after costs | Construct falsified |

---

## 6. What This Is NOT

Explicitly rejected formulations:

| Rejected | Reason |
|----------|--------|
| Nifty-only TS-MOM | per_trade_pnl fails RFA (√T_sealed too small) |
| Nifty/BankNifty calendar carry | per_trade_pnl fails RFA |
| Expiry-day premium selling | per_trade_pnl fails RFA |
| Cross-section across strikes/expiries | Contracts are correlated, not independent assets |
| Ranking 5 NSE derivative indices | Too few assets for rank_ic |
| "Hidden" index timing under a stock-level veneer | The primary hypothesis MUST be stock-level predictability; if a post-hoc analysis shows 50-stock IC is noise and the result is just index-level timing, the construct is invalid |

---

## 7. BankNifty Extension (Deferred)

The same methodology applies to BankNifty constituents but is **deferred** until the constituent panel is confirmed. NSE changed the BankNifty methodology from 12 to 14 companies (Nifty Bank methodology update, Dec 2025). The point-in-time membership must be verified before any research begins.

When authorised, the BankNifty extension:
1. Uses the same feature set and combination rule
2. Has its own RFA declaration (different n_available due to smaller cross-section)
3. Has its own TRAIN/HOLDOUT/SEALED windows
4. Does NOT pool with Nifty 50 — each index is a separate construct with separate gate progression

---

## 8. Prior Exposure Disclosure

| Read | Data | Frequency | Relevance |
|------|------|-----------|-----------|
| Nifty-BankNifty pair research | Index ratio (2 assets) | Daily | INDEX-LEVEL only; never ranked constituents |
| PSB-1 C1-C5 | NIFTY-200 equity | Monthly | Cross-sectional IC experience, but monthly + different signals |
| PSB-2 C2/C4 | NIFTY-200 equity | Monthly | Same as above |
| SFB-1/F1 | Stock futures | Monthly | Momentum difficulty finding; not a Nifty 50 constituent IC read |
| Carry sleeve | ~180 SSF names | Monthly | Basis/carry IC experience; this construct uses carry as a feature but at daily frequency on a different universe |

**No prior read exists on:** daily cross-sectional IC of Nifty 50 constituents, combined multi-feature IC, or the breadth-to-index-futures translation.

---

## 9. References

- `docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` — pair research (NO OPPORTUNITY)
- `docs/reports/RS_MOM_PRE_REGISTRATION.md` — RS-MOM ABANDON
- `governance/rfa/declarations/cb_n50.py` — frozen RFA declaration
- `docs/reports/CB_N50_RFA.md` — formal RFA gate report
- `governance/rfa/declarations/carry.py` — prior carry declaration (rank_ic template)
- Jegadeesh & Titman (1993) — "Returns to Buying Winners and Selling Losers"
- Jegadeesh (1990) — "Evidence of Predictable Behavior of Security Returns"
- Koijen, Moskowitz, Pedersen, Vrugt (2018) — "Carry"
- `docs/reports/SIGNAL_ENGINE_DESIGN.md` — engine architecture
