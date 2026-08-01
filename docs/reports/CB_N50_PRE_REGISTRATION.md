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
3. Compute combined score = mean of normalised feature z-scores
4. Compute **daily cross-sectional rank IC** = Spearman correlation between combined scores at t and next-day returns at t+1, across the Nifty 50 cross-section
5. Compute **breadth score** = fraction of constituents with combined score above zero, weighted by free-float market cap

### 1.4 Index Position Rule (pre-registered)

The breadth score maps to a Nifty futures position via a **fixed, pre-registered rule**:

```
if breadth_score > 0.65:  LONG  Nifty futures (1 unit)
if breadth_score < 0.35:  SHORT Nifty futures (1 unit)
else:                     FLAT
```

The thresholds (0.35, 0.65) are pre-registered before any TRAIN read. They are symmetric around 0.5 and represent the top/bottom tercile of possible breadth values (50 stocks × binary signal). These are NOT fitted to data — they are pinned by the construct design.

**Holding period**: 1 day. Re-evaluate daily. This matches the daily signal cadence and avoids overlapping-position complications.

**Position sizing**: Fixed 1 unit of Nifty futures (lot size from instrument master at execution time). No volatility scaling, no Kelly sizing — the P&L from futures is an execution check, not a second optimisation surface.

### 1.5 Universe

Nifty 50 constituents, point-in-time (PIT), from the NIFTY-200 universe in `equity_bhavcopy_adjusted`. Membership changes (additions/deletions) are applied on the effective date from `symbol_entity_intervals`.

Each day's cross-section contains exactly those stocks that were Nifty 50 members on that date. Constituents with missing data (suspended, not yet listed, data gap) are excluded from that day's cross-section; the rank IC is computed on the remaining N≥30 stocks.

### 1.6 Execution Vehicle

Nifty futures (NSE FO segment). Single-leg only — no paired BankNifty position. The breadth score aggregates 50 stock-level predictions into one index-level direction; expressing it as a Nifty future is the natural mapping.

**Cost model**: Nifty futures round-trip: brokerage + STT (0.0125% sell side) + exchange + SEBI + GST + stamp ≈ 2-3 bps. Exact schedule to be sourced from broker at execution time.

**Roll handling**: Near-month futures, rolled 2 days before expiry. Roll cost (calendar spread) is a drag, not a signal — tracked separately in execution P&L but not optimised.

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
| Key constraint | √T_sealed=1.89 fixed | n=887 (daily) scales with √n |
| sd (noise) | 1.0 (by construction) | 0.15-0.25 (IC dispersion) |
| δ/sd ratio | S=0.65 max | 0.035/0.15=0.233 |
| ncp | 0.65×1.89=1.23 | 0.233×29.8=6.95 |

The `rank_ic` metric benefits from: (a) daily cadence → large n (887 vs 186), and (b) IC dispersion (sd=0.15-0.25) is much smaller than the per_trade_pnl unit sd (1.0). The combination gives ncp≈7 at the optimistic corner vs ncp≈1.2 for RS-MOM.

---

## 3. Research Phases

### Phase 1: Substrate Certification

Before any TRAIN read:
1. **Universe gate**: Verify Nifty 50 PIT membership is correct for a random sample of dates (≥20 dates across 2016-2026). Cross-check against NSE published changes.
2. **Data gate**: Verify every Nifty 50 constituent has equity bhavcopy data on every membership date. Missing-data rate must be <1% of constituent-dates.
3. **Futures gate**: Verify Nifty futures data exists on all required dates. Verify roll dates and near-month contract identification.

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

## 4. Acceptance Criteria

### 4.1 Phase 2 (TRAIN) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G1 | Combined IC Newey-West t-test, Bonferroni p<0.05 (m=9) | No HOLDOUT read |
| G2 | At least one feature has positive mean IC after lookback selection | Drop that feature, re-test |

### 4.2 Phase 3 (HOLDOUT) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G3 | Combined IC significant at p<0.05 (single test) | No SEALED read |
| G4 | Nifty futures net P&L > 0 after costs | No SEALED read |

### 4.3 Phase 4 (SEALED) Gates

| Gate | Criterion | Consequence of Failure |
|------|-----------|----------------------|
| G5 | Combined IC significant at p<0.05 (single test) | Construct falsified |
| G6 | Nifty futures net P&L > 0 after costs | Construct falsified |

---

## 5. What This Is NOT

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

## 6. BankNifty Extension (Deferred)

The same methodology applies to BankNifty constituents but is **deferred** until the constituent panel is confirmed. NSE changed the BankNifty methodology from 12 to 14 companies (Nifty Bank methodology update, Dec 2025). The point-in-time membership must be verified before any research begins.

When authorised, the BankNifty extension:
1. Uses the same feature set and combination rule
2. Has its own RFA declaration (different n_available due to smaller cross-section)
3. Has its own TRAIN/HOLDOUT/SEALED windows
4. Does NOT pool with Nifty 50 — each index is a separate construct with separate gate progression

---

## 7. Prior Exposure Disclosure

| Read | Data | Frequency | Relevance |
|------|------|-----------|-----------|
| Nifty-BankNifty pair research | Index ratio (2 assets) | Daily | INDEX-LEVEL only; never ranked constituents |
| PSB-1 C1-C5 | NIFTY-200 equity | Monthly | Cross-sectional IC experience, but monthly + different signals |
| PSB-2 C2/C4 | NIFTY-200 equity | Monthly | Same as above |
| SFB-1/F1 | Stock futures | Monthly | Momentum difficulty finding; not a Nifty 50 constituent IC read |
| Carry sleeve | ~180 SSF names | Monthly | Basis/carry IC experience; this construct uses carry as a feature but at daily frequency on a different universe |

**No prior read exists on:** daily cross-sectional IC of Nifty 50 constituents, combined multi-feature IC, or the breadth-to-index-futures translation.

---

## 8. References

- `docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` — pair research (NO OPPORTUNITY)
- `docs/reports/RS_MOM_PRE_REGISTRATION.md` — RS-MOM ABANDON
- `governance/rfa/declarations/cb_n50.py` — frozen RFA declaration
- `docs/reports/CB_N50_RFA.md` — formal RFA gate report
- `governance/rfa/declarations/carry.py` — prior carry declaration (rank_ic template)
- Jegadeesh & Titman (1993) — "Returns to Buying Winners and Selling Losers"
- Jegadeesh (1990) — "Evidence of Predictable Behavior of Security Returns"
- Koijen, Moskowitz, Pedersen, Vrugt (2018) — "Carry"
- `docs/reports/SIGNAL_ENGINE_DESIGN.md` — engine architecture
