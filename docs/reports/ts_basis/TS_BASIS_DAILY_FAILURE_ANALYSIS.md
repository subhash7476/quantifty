# TS Basis Daily — Signal Failure Analysis

**Script-generated** — `scripts/signal_engine/ts_basis_daily/run_failure_analysis.py`. Code commit `624e498`.

**Generated:** 2026-07-28

**Window:** TRAIN 2016-03-31 → 2020-12-31 (1174 formations, 117,847 signals, 117,809 enriched).

**Metric:** signed return = fwd_ret_1m × sign(z_ts). Positive = signal was directionally correct.


---
## 1. Baseline

| Metric | Value |
|---|---|
| Signals | 117,809 |
| Hit rate (signed ret > 0) | 50.9% |
| Mean signed return | +0.082% |
| SE(mean) | 0.008% |

---
## 2. Failure Predictors

*Buckets where hit rate or mean signed return drops materially below baseline.*

### ADV Tier

| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |
|---|---|--:|--:|--:|--:|--:|
| Low ADV (bottom 1/3) | 42,689 |  50.8% | +0.072% | 1.70% | -0.1pp | -0.011pp |
| Mid ADV | 39,176 |  50.8% | +0.078% | 1.75% | -0.1pp | -0.004pp |
| High ADV (top 1/3) | 35,944 |  51.2% | +0.099% | 1.72% | +0.3pp | +0.017pp |

### Overnight Nifty Gap

| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |
|---|---|--:|--:|--:|--:|--:|
| Gap < +0.04% | 39,263 |  50.8% | +0.100% | 1.84% | -0.1pp | +0.017pp |
| Gap +0.04% to +0.30% | 39,339 |  50.6% | +0.064% | 1.54% | -0.3pp | -0.018pp |
| Gap > +0.30% | 39,072 |  51.3% | +0.083% | 1.79% | +0.4pp | +0.001pp |

### Sector

| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |
|---|---|--:|--:|--:|--:|--:|
| Automobile and Auto Components | 10,474 |  51.5% | +0.065% | 1.55% | +0.5pp | -0.018pp |
| Capital Goods | 5,006 |  49.8% | +0.077% | 1.87% | -1.1pp | -0.005pp |
| Chemicals | 2,676 |  51.0% | +0.043% | 1.63% | +0.1pp | -0.039pp |
| Construction | 3,121 |  51.2% | +0.124% | 1.83% | +0.3pp | +0.042pp |
| Construction Materials | 3,476 |  51.8% | +0.071% | 1.49% | +0.8pp | -0.011pp |
| Consumer Durables | 4,173 |  52.2% | +0.121% | 1.56% | +1.3pp | +0.039pp |
| Consumer Services | 1,308 |  51.2% | +0.009% | 1.89% | +0.3pp | -0.073pp |
| Diversified | 270 |  54.4% | +0.119% | 1.26% | +3.5pp | +0.036pp |
| Fast Moving Consumer Goods | 6,930 |  50.6% | +0.054% | 1.35% | -0.3pp | -0.028pp |
| Financial Services | 31,359 |  50.5% | +0.091% | 1.90% | -0.4pp | +0.008pp |
| Healthcare | 9,445 |  51.5% | +0.062% | 1.53% | +0.5pp | -0.021pp |
| Information Technology | 6,747 |  52.1% | +0.103% | 1.39% | +1.1pp | +0.021pp |
| Media Entertainment & Publication | 2,540 |  51.5% | +0.118% | 2.08% | +0.6pp | +0.036pp |
| Metals & Mining | 7,734 |  49.9% | +0.031% | 1.94% | -1.0pp | -0.051pp |
| Oil Gas & Consumable Fuels | 8,773 |  51.5% | +0.099% | 1.54% | +0.6pp | +0.017pp |
| Power | 4,662 |  50.4% | +0.103% | 1.72% | -0.5pp | +0.021pp |
| Realty | 1,435 |  48.4% | +0.006% | 2.19% | -2.5pp | -0.077pp |
| Services | 2,666 |  51.1% | +0.161% | 1.94% | +0.1pp | +0.079pp |
| Telecommunication | 2,905 |  50.5% | +0.090% | 2.06% | -0.4pp | +0.007pp |
| Textiles | 2,109 |  50.0% | +0.113% | 1.83% | -0.9pp | +0.030pp |

### Signal Strength (thresholds=0.30, 0.70)

| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |
|---|---|--:|--:|--:|--:|--:|
| Weak signal (|z| low) | 39,270 |  50.3% | +0.040% | 1.70% | -0.7pp | -0.042pp |
| Mid signal | 39,269 |  51.3% | +0.093% | 1.67% | +0.4pp | +0.011pp |
| Strong signal (|z| high) | 39,270 |  51.2% | +0.114% | 1.80% | +0.3pp | +0.032pp |

### VIX (thresholds=13.9, 16.8)

| Bucket | n | Hit Rate | Mean Signed | |Fwd Ret| | Δ Hit | Δ Mean |
|---|---|--:|--:|--:|--:|--:|
| Low VIX | 39,483 |  51.1% | +0.062% | 1.48% | +0.2pp | -0.020pp |
| Mid VIX | 39,087 |  50.8% | +0.084% | 1.64% | -0.1pp | +0.001pp |
| High VIX | 39,239 |  50.9% | +0.101% | 2.05% | -0.1pp | +0.019pp |

---
## 3. Worst-Case Regime Combinations

*Worst 2-dimensional intersections by mean signed return (min 200 signals).*

#### VIX × Signal Strength

| Condition | n | Hit Rate | Mean Signed | Δ vs Baseline |
|---|---|--:|--:|--:|
| High VIX & Weak |z| | 13,202 | 50.0% | +0.024% | -0.058pp |
| Low VIX & Weak |z| | 13,522 | 50.7% | +0.041% | -0.041pp |
| Mid VIX & Weak |z| | 12,546 | 50.0% | +0.055% | -0.027pp |
| Low VIX & Mid |z| | 13,224 | 51.1% | +0.068% | -0.015pp |
| Low VIX & Strong |z| | 12,737 | 51.4% | +0.077% | -0.005pp |
| Mid VIX & Strong |z| | 13,637 | 51.0% | +0.083% | +0.000pp |
| High VIX & Mid |z| | 13,141 | 51.4% | +0.099% | +0.017pp |
| Mid VIX & Mid |z| | 12,904 | 51.4% | +0.112% | +0.030pp |
| High VIX & Strong |z| | 12,896 | 51.2% | +0.183% | +0.101pp |

#### VIX × ADV Tier

| Condition | n | Hit Rate | Mean Signed | Δ vs Baseline |
|---|---|--:|--:|--:|
| Low VIX & Mid ADV | 13,013 | 51.0% | +0.053% | -0.029pp |
| Mid VIX & Low ADV | 13,970 | 50.1% | +0.054% | -0.028pp |
| Low VIX & Low ADV | 14,428 | 51.4% | +0.057% | -0.025pp |
| High VIX & Mid ADV | 12,939 | 50.3% | +0.072% | -0.010pp |
| Low VIX & High ADV | 12,042 | 50.8% | +0.076% | -0.006pp |
| Mid VIX & High ADV | 11,893 | 51.4% | +0.091% | +0.008pp |
| High VIX & Low ADV | 14,291 | 50.9% | +0.103% | +0.021pp |
| Mid VIX & Mid ADV | 13,224 | 51.0% | +0.108% | +0.026pp |
| High VIX & High ADV | 12,009 | 51.4% | +0.131% | +0.048pp |

---
## 4. Summary

- **Worst regime:** Sector > Realty — hit 48.4%, mean signed +0.006% (-0.1pp vs baseline).
- **Best regime:** Sector > Services — hit 51.1%, mean signed +0.161% (+0.1pp vs baseline).

### What Predicts Failure

- **Weak |z| signals underperform dramatically.** Weak: +0.040% → Mid: +0.093% → Strong: +0.114%. The signal's edge is concentrated in the top two-thirds of |z| scores. Consider raising the |z| threshold for entry — skip the weakest tercile entirely.

- **High VIX does NOT degrade the signal — it IMPROVES it.** High VIX: +0.101% vs Low VIX: +0.062%. The basis dislocations that create the signal are larger in volatile markets. Counterintuitive but data-backed: do NOT add a VIX filter.

- **Overnight Nifty gaps do NOT predict signal failure.** Mean signed spread across gap buckets: 0.035pp. The overnight macro move does not swamp the stock-specific basis signal. A pre-market gap filter is not needed on this evidence.

- **Low ADV names underperform.** Low ADV: +0.072% → High ADV: +0.099%. Basis in thin names is noisier. Consider a higher ADV floor.

- **Worst sectors by mean signed return:** Realty (+0.006%, n=1,435), Consumer Services (+0.009%, n=1,308), Metals & Mining (+0.031%, n=7,734). Basis signal may not carry in these sectors.

### Composite: strongest failure condition (VIX × |z|)

- Worst intersection: **High VIX & Weak |z|** — hit 50.0%, mean signed +0.024%
- Best intersection: **High VIX & Strong |z|** — hit 51.2%, mean signed +0.183%

---

**Generated:** 2026-07-28 | **Commit:** `624e498` | **Signals analyzed:** 117,809

