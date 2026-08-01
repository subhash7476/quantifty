# RS-MOM: Nifty–BankNifty Relative-Strength Momentum — Pre-Registration

**Status:** RFA ABANDON (2026-08-01)
**Declaration:** `governance/rfa/declarations/rs_mom.py` (SHA-256: `67e3854b…`)

---

## 1. Construct

### 1.1 Core Idea

Long the relatively stronger index, short the weaker. When BankNifty outperforms Nifty over the lookback, go long BankNifty futures + short Nifty futures. When Nifty outperforms, reverse.

This is motivated by the pair-research finding that the Nifty-BankNifty ratio **trends** rather than mean-reverts:
- Intraday mean-reversion slope: +1.10 (up moves), +1.17 (down moves) — ratio continues in the same direction
- Daily ratio-change autocorrelation: +0.086 — slight continuation, not reversal
- Overnight reversal rate: 48.9% — essentially random

"Fade the move" was proven wrong. "Follow the move" is the logical alternative hypothesis.

### 1.2 Signal Definition

```
lookback_return_nifty  = close[t] / close[t - L] - 1
lookback_return_banknifty = close[t] / close[t - L] - 1
rel_strength = lookback_return_banknifty - lookback_return_nifty

if rel_strength > 0:
    long BANKNIFTY futures, short NIFTY futures
else:
    short BANKNIFTY futures, long NIFTY futures
```

- **Lookback L**: 5, 10, 20 days (to be selected on TRAIN)
- **Rebalance cadence**: Weekly (every Friday close)
- **Hedge ratio**: Beta-neutral from rolling 60-day regression, rounded to nearest lot
- **Volatility scaling**: Position size = target_vol / realized_vol_60d, capped at 2x

### 1.3 Vehicles

Two futures legs on NSE FO segment:
- Nifty futures: lot size 25 (check instrument master at execution time)
- BankNifty futures: lot size 15 (check instrument master at execution time)

### 1.4 Differentiation from Rejected Construct

| | Mean Reversion (rejected) | RS-MOM (this construct) |
|---|---|---|
| Direction | Fade the ratio extreme | Follow the ratio trend |
| Entry trigger | Z-score > threshold | Relative return sign |
| Holding thesis | Ratio reverts to mean | Ratio continues |
| Evidence against | Half-life 166d, no cointegration, bootstrap p=0.354 | None yet — no TRAIN read taken |
| Intraday behavior | Predicted to revert — contradicted by data | Predicted to trend — consistent with observed +1.10/+1.17 slopes |

---

## 2. RFA Gate — ABANDON

### 2.1 Declaration Parameters

| Parameter | Value |
|-----------|-------|
| Metric | per_trade_pnl |
| Test type | one_sided (positive expected return) |
| Cadence | Weekly (52 formations/year) |
| n_available (sealed) | 186 weeks (2023-2026) |
| Sharpe band | [0.25, 0.65] |
| Power hurdle | 0.80 |

### 2.2 Gate Result

| Verdict | ABANDON |
|---------|---------|
| Max power (optimistic corner) | **0.337** |
| n_required (optimistic) | **763 weeks** (~15 years) |
| n_required (central) | 1,589 weeks (~31 years) |
| n_required (pessimistic) | 5,146 weeks (~99 years) |
| n_available (actual) | 186 weeks (~3.6 years) |

### 2.3 Why It Fails

The gate computes power via the noncentral t-distribution:

```
ncp = Sharpe × √(T_sealed)
```

For the sealed window T_sealed ≈ 3.58 years:

| Sharpe | ncp | Power at n=186 |
|--------|-----|----------------|
| 0.65 (optimistic) | 1.23 | 0.337 |
| 0.70 | 1.32 | 0.372 |
| 0.90 | 1.70 | 0.520 |
| 1.05 | 1.99 | 0.640 |
| 1.30 | 2.46 | 0.800 ← clears |

**To clear power 0.80, the construct would need Sharpe ≥ 1.30.** No defensible literature supports a two-asset spread momentum Sharpe above 1.0. The TS-MOM literature (Moskowitz-Ooi-Pedersen 2012) reports ~0.5-0.7 for diversified portfolios; a single-pair strategy would be at the lower end of that range.

The root cause is the `per_trade_pnl` metric: with sd=1.0 by construction, ncp = Sharpe × √T, and √T is fixed at ~1.89 by the sealed window length. The only lever is Sharpe, and no realistic Sharpe can compensate.

### 2.4 Why This Is Not a Remedy Opportunity

- **Can't widen the Sharpe band**: A band of [0.25, 1.30] would be "the crossed-corner defect" — smuggling in an effect size nobody defended.
- **Can't switch to rank_ic**: The construct has exactly 2 assets (Nifty, BankNifty). Rank IC is degenerate — it's either +1 or -1 per formation.
- **Can't lengthen the sealed window**: NSE F&O history before 2016 is unobtainable (SFB-1/F1 lockdown finding). The total available calendar is fixed at ~10.5 years.
- **Cadence cancels**: ncp = S × √T regardless of cadence. Trading daily instead of weekly multiplies n and divides per-formation Sharpe by the same factor.

**This is the per_trade_pnl limitation documented in the RFA design.** The gate correctly identifies that the sealed window is too short to discriminate a realistic effect from zero.

---

## 3. What Was Learned

### 3.1 Methodological

The RFA gate worked exactly as designed: it killed an infeasible construct before any code was written, any TRAIN data consumed, or any Sealed window spent. The cost was one declaration file. This is the same protocol that correctly killed FLOW (max power 0.6053) and saved the project months of dead-end research.

### 3.2 Pair Research: The Binding Constraint

The pair research produced one positive signal (ratio trends intraday) and one structural negative (per_trade_pnl can't clear RFA power 0.80 with only 3.5 years of sealed data). The structural negative is the binding one — it doesn't matter how good the signal is if you can't demonstrate it.

### 3.3 Implication for Other Index Constructs

Any construct trading a single index pair (Nifty–BankNifty, or any two-indices-one) with `per_trade_pnl` metric will face the same wall: √T_sealed ≈ 1.89, requiring Sharpe ≥ ~1.3. This effectively rules out:

- Two-index relative-strength momentum (this construct)
- Two-index calendar spread / carry
- Two-index volatility spread
- Two-index dispersion

**Unless** the construct can be formulated with `rank_ic` (requiring a genuine cross-section of ≥10 assets) or can justify a much longer sealed window (not available).

### 3.4 What Survives

Single-index time-series momentum (Nifty futures only) avoids the per_trade_pnl limitation? No — it still uses per_trade_pnl. The same math applies.

Actually, the carry construct cleared RFA because it used `rank_ic` with a ~180-name cross-section. The IC dispersion (sd=0.10-0.18) is small relative to IC mean (delta=0.02-0.045), giving ncp = (0.045/0.10) × √42 = 2.92 — easily clearing power 0.80.

**The lesson**: constructs with per_trade_pnl need ~15+ years of sealed data, which doesn't exist for Indian futures. Constructs with rank_ic can clear with ~42 formations because the IC noise (sd) is much smaller than the Sharpe noise (sd=1.0).

---

## 4. Disposition

**No successor is authorized by this ABANDON.** The gate is dispositive — it is not conditional on better data or a revised argument. Any new index-pair construct must either:

1. Use `rank_ic` with a genuine cross-section of ≥10 assets (not a two-index pair)
2. Solve the sealed-window-length problem (not currently possible with Indian futures data)

**The Sealed window 2023-2026 remains untouched.** No data was read. No strategy code exists.

---

## 5. References

- `docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.md` — mean-reversion pair research (NO OPPORTUNITY)
- `governance/rfa/declarations/rs_mom.py` — this construct's RFA declaration
- `governance/rfa/declarations/flow.py` — prior ABANDON (max power 0.6053)
- `docs/reports/RFA_RETROSPECTIVE.md` — RFA design record
- Moskowitz, Ooi, Pedersen (2012) — "Time Series Momentum", JFE
- Asness, Moskowitz, Pedersen (2013) — "Value and Momentum Everywhere", JF
