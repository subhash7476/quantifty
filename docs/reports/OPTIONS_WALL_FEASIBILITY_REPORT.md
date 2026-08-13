# Options Wall Analytics — Feasibility & Implementation Report

**Branch:** `feat/options-wall`  
**Date:** 2026-08-12  
**Source:** [Hedgewall](https://hedgewall.in/) — Dealer-positioning terminal for NIFTY/SENSEX/BANKNIFTY

> **⚠️ CORRECTION BANNER (2026-08-12).** This document is a **feature-inventory / roadmap
> report, not a feasibility assessment**, despite the title — the one thing that decides
> feasibility (power arithmetic at the RFA pre-check) is not computed here. The "~50% of
> Hedgewall's core" line (repeated in §7) is **overstated**: Hedgewall's headline product is
> BANKNIFTY/SENSEX dealer positioning, and this repo has **zero** BankNifty index-option
> history (verified: `options_bhavcopy.duckdb` → symbols = {NIFTY} only). §6's roadmap
> implies a 4-week Vanna/Charm/UI build before any power question is settled — the wrong
> order. For the actual feasibility analysis, corrected substrate facts and the real power
> arithmetic, read **`DW1_DEALER_WALL_PRE_REGISTRATION.md` (v2)**. The strategy construct
> derived from this report (DW-1) does **not** clear the RFA power pre-check at an honest
> Sharpe band, and is parked pending operator decision.

---

## 1. Hedgewall Feature Inventory (What They Sell)

| Layer | Features | Data Source |
|-------|----------|-------------|
| **Gamma Explorer** | Net GEX per strike, absolute GEX, zero-gamma flip level, call wall, put wall, gamma regime (positive/negative) | Full option chain (OI, gamma, spot) |
| **Vanna & Charm** | Vanna (dDelta/dVol), Charm (dDelta/dTime), decay clock to expiry | Requires 2nd-order Greeks + TTE |
| **IV Term Structure** | ATM IV by expiry (weekly → monthly), term slope, skew (25Δ put vs call) | Multi-expiry chain fetch |
| **OI Rotation** | Since-open OI delta (added/unwound), call/put legs per strike | 5-sec snapshots from 09:15 |
| **Pin Magnet** | Pin conviction score, session funnel (time-decay cone), distance to pin | Gamma mass distribution + time model |
| **Gamma Orbit** | Visual: strikes as orbiting bodies sized by gamma, pin at center | Frontend visualization |
| **Regime History** | 30-session net dealer gamma river (gold=stable, rust=amplifying) | Daily persistence |
| **Session Replay** | Full historical replay of any session | Snapshot store |

**Pricing:** ₹133–166/day (by request, no public API).

---

## 2. Current Repo Coverage (What We Have)

### Implemented in `core/analytics/options_analytics.py`

| Metric | Function | Status |
|--------|----------|--------|
| **PCR** (overall + by-strike + change) | `calculate_pcr()` | ✅ Complete |
| **Net GEX** (CE/PE separated, lot-size adjusted) | `calculate_gex()` | ✅ Complete |
| **Zero-Gamma Flip Level** (linear interpolation) | `_find_zero_gamma_level()` | ✅ Complete |
| **Call Wall / Put Wall** (max CE/PE OI strikes) | `analyze_oi_changes()` → `resistance_strike` / `support_strike` | ✅ Complete |
| **Gamma Distribution per Strike** | `GEXResult.gamma_distribution` | ✅ Complete |
| **GEX Regime** (Positive/Negative/Neutral) | `GEXResult.regime` | ✅ Complete |
| **OI Buildup Patterns** (Long/Short buildup, unwinding, covering) | `analyze_oi_changes()` | ✅ Complete |
| **Max Pain** | `calculate_max_pain()` | ✅ Complete |
| **Full Structural Snapshot** | `build_structural_snapshot()` | ✅ Complete |

### Data Pipeline (Working)
- `OptionsProvider` fetches Upstox V2 option chain (5-sec cycle)
- Caches to DuckDB (`data/market_data/options_poller.duckdb`)
- Provides: `ltp, oi, oi_change, iv, delta, gamma, theta, vega` per strike
- Expiry resolution via instrument master (`nse_fo_instruments.duckdb`)

### Execution Infrastructure (Ready)
- `NiftyShieldExecutionHandler` — groups legs, sizes via `NseMarginEngine`, routes through standard gates
- `NiftyShieldExitDriver` — TP/SL/time/delta-flatten exits
- `LoopDriver` — single-threaded orchestrator (LIVE + REPLAY)
- Paper runner + session recorder + audit + metrics

---

## 3. Gap Analysis (What's Missing)

| Feature | Gap | Effort | Files to Create/Modify |
|---------|-----|--------|------------------------|
| **Vanna** (dDelta/dVol) | Upstox provides only 1st-order Greeks | Medium | `core/analytics/greeks.py` (new BS engine) |
| **Charm** (dDelta/dTime) | Same — needs TTE + IV surface | Medium | `greeks.py` + `options_analytics.py` |
| **IV Term Structure** | Need multi-expiry fetch + ATM IV per expiry | Medium | `options_provider.py` (multi-expiry) + `options_analytics.py` |
| **Pin Conviction Score** | Statistical model: gamma mass at pin vs runner-ups | Medium | `options_analytics.py` (new method) |
| **Expiry Magnet / Session Funnel** | Time-decay simulation of pin probability | Medium | `options_analytics.py` (new class) |
| **OI Rotation Since Open** | Current `oi_change` is vs prev close, not 09:15 | Low | `options_provider.py` (store 09:15 baseline) |
| **Gamma Orbit Visualization** | Frontend charting (Flask/SSE + JS) | Medium | `flask_app/blueprints/options.py` + templates |
| **30-Session Regime History** | Daily persistence + regime classification | Low | New schema + `options_analytics.py` |
| **Session Replay** | Full snapshot store + replay engine | Medium | New persistence + REPLAY provider |

---

## 4. How Metrics Map to Trade Decisions

### Decision Framework

```
Option Chain (5s) → OptionsAnalytics → Structural Snapshot
                                                      ↓
                              Strategy (SignalSource) → SignalEvent (legs, strikes, expiry)
                                                      ↓
                              ExecutionHandler → Sizing (NseMarginEngine) + Fills
                                                      ↓
                              ExitDriver → TP/SL/Time/Delta-Flatten
```

### Concrete Rules (Examples)

| Market Condition | Analytics Signal | Trade Structure | Rationale |
|------------------|------------------|-----------------|-----------|
| Spot ∈ [Put Wall, Call Wall], **Positive GEX** | Rangebound, dealers stabilize | **Iron Fly at Pin** / **Iron Condor Put Wall → Call Wall** | Sell premium where dealers pin price |
| Spot > **Flip**, **Negative GEX** | Trend up, dealers amplify | **Buy Call Spread** (Flip → Call Wall) / **Long Straddle** | Ride dealer-chasing flow |
| Spot < **Flip**, **Negative GEX** | Trend down, dealers amplify | **Buy Put Spread** (Put Wall → Flip) / **Long Straddle** | Ride dealer-chasing flow |
| \|Spot - Pin\| < 50 pts, **High Gamma** | Pin risk, max pinning force | **0DTE Fly at Pin**, exit by 14:30 | Gamma scalping near expiry |
| **Vanna > 0** (IV rising + spot rising) | Dealers buying futures | **Long OTM Calls** / **Call Backspread** | Vanna flow reinforces move |
| **Charm Decay Accelerating** (1-2 days to expiry) | Delta bleed forces rebalance | **Directional trade with charm** (e.g., sell ITM, buy OTM) | Expiry-day charm cascade |
| **IV Term Steep** (Front > Back) | Near-term fear | **Calendar Spread**: sell near, buy far | Theta + vol mean-reversion |

### Exit Triggers from Analytics

| Trigger | Action |
|---------|--------|
| Spot crosses **Flip** | Close directional spreads (hedging regime flipped) |
| Spot hits **Call Wall / Put Wall** | Take profit on short premium (wall held) |
| **IV drops > 2 pts** (Vanna/Charm decay) | Close long vol positions |
| **15:15 Hard Exit** | Close all (no overnight gamma risk) |
| **Pin Conviction < 60%** | Reduce size / exit pin trades |

---

## 5. Implementation Roadmap

### Phase 1: Core Greeks Engine (Week 1)
- [ ] `core/analytics/greeks.py` — Black-Scholes 2nd-order: Vanna, Charm, Vomma, Veta
- [ ] Integrate into `OptionChainRow` (compute if API missing)
- [ ] Add `calculate_vanna_charm()` to `OptionsAnalytics`

### Phase 2: IV Term Structure (Week 1-2)
- [ ] Extend `OptionsProvider.fetch_option_chain()` to accept multiple expiries
- [ ] Add `calculate_iv_term_structure()` → ATM IV per expiry, term slope, skew
- [ ] Store multi-expiry snapshots in DuckDB

### Phase 3: Pin & Magnet Analytics (Week 2)
- [ ] `calculate_pin_conviction(gamma_by_strike, spot)` → 0-100 score
- [ ] `SessionFunnel` class: time-decay cone, pin probability vs time
- [ ] `calculate_oi_rotation_since_open()` — baseline at 09:15

### Phase 4: Regime History & Replay (Week 2-3)
- [ ] Daily regime persistence table: `session_regime(date, regime, net_gex, flip, pin, walls)`
- [ ] 30-session regime river query
- [ ] REPLAY provider reading full snapshots

### Phase 5: Strategy & UI (Week 3-4)
- [ ] `GammaStrategySignalSource` — implements decision framework above
- [ ] Flask blueprint `/options/wall` — gamma orbit, regime history, pin funnel
- [ ] SSE push for real-time updates (reuse `options_publisher.py`)

### Phase 6: Paper Validation (Week 4+)
- [ ] `gamma_paper_runner.py` — composition root for Gamma strategy
- [ ] REPLAY over 30-session history
- [ ] Audit: guard events, reverse divergence, telemetry

---

## 6. Risk & Constraints

| Risk | Mitigation |
|------|------------|
| **Upstox API rate limits** (5-sec chain fetch) | Single poller → cache → consumers read cache (already implemented) |
| **Missing 2nd-order Greeks** | Compute locally via BS; validate against known prices |
| **Pin conviction model overfit** | ~~Backtest on 30-session history; require >60% conviction for trade~~ — **STRUCK (2026-08-12): in-sample threshold selection on ~30 observations reproduces the C2 post-hoc bolt-on sin. Correct rule: the conviction threshold must be a pre-registered freeze input; validation happens on TRAIN/HOLDOUT splits, never on ~30 sessions.** |
| **Execution slippage on 0DTE** | Paper trade first; measure fill conversion vs marks |
| **Regime classification noise** | Use 3-session smoothing; don't flip on single session |

---

## 7. Conclusion

**We have ~50% of Hedgewall's analytical core** (GEX, Flip, Walls, Pin, PCR, Max Pain, OI patterns).  
**Missing:** Vanna/Charm, IV term structure, Pin conviction, OI rotation since open, Regime history, Visualization.

**The execution infrastructure is production-ready** — the gap is purely analytics + strategy layer.

**Recommended next step:** Implement `greeks.py` (Vanna/Charm) and multi-expiry fetch, then build `GammaStrategySignalSource` to paper-trade the decision framework in Section 4.

---

## Appendix: Key File References

| File | Purpose |
|------|---------|
| `core/analytics/options_analytics.py` | All current metrics (GEX, PCR, Walls, Pin, Max Pain) |
| `core/data/options_provider.py` | Upstox V2 fetcher + DuckDB cache |
| `core/execution/options/nifty_shield_handler.py` | Execution handler + exit driver |
| `scripts/nifty_shield_paper_runner.py` | Paper runner composition root |
| `flask_app/blueprints/options.py` | Options dashboard (extend for Wall) |
| `docs/archive/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md` | Original dashboard plan |