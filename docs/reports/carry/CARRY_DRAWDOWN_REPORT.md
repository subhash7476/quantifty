# Carry — Drawdown / Regime Profile

**Script-generated** — `scripts/signal_engine/carry/drawdown_analysis.py`. Code commit `da3e3ba`.

**Generated:** 2026-07-23

**Protocol:** `CARRY_IMPLEMENTATION_BRIDGE.md` §6.3 — characterize risk before sizing. Size on the conservative net, not the SEALED +20.5%.

**SEALED:** NOT read — TRAIN and HOLDOUT only. SEALED (2023–26) is likely a carry-favorable regime; sizing on that headline number would understate risk.


---

## 1. Risk Summary


| Metric | TRAIN | HOLDOUT | Conservative |
|---|--:|--:|--:|
| Annualized net | 12.84% | 6.96% | 6.96% |
| Worst month | -2.85% | -4.59% | -4.59% |
| Max drawdown | -6.44% | -5.16% | -6.44% |
| Monthly std dev | 2.23% | 2.38% | 2.38% |

---

## 2. Risk-Adjusted Metrics


| Metric | TRAIN | HOLDOUT |
|---|--:|--:|
| Sharpe (ann) | 1.61 | 0.86 |
| Sortino (ann) | 3.81 | 1.28 |
| Calmar (ret/|DD|) | 1.99 | 1.35 |
| Ulcer Index | 0.03 | 0.02 |
| % positive months | 64.9% | 65.2% |
| Return skew | 0.11 | -0.42 |

---

## 3. Return Concentration

What fraction of total return comes from the top N months? High concentration → returns are lumpy, not steady.


| Window | Top 3 months | Top 5 months |
|---|--:|--:|
| TRAIN | 27% | 42% |
| HOLDOUT | 87% | 129% |

---

## 4. Rolling 12-Month Returns (Annualized)

Shows the range of annual returns an investor would have experienced at any entry point.


| Window | Worst 12m | Mean 12m | Best 12m |
|---|--:|--:|--:|
| TRAIN | -0.7% | +13.0% | +32.1% |
| HOLDOUT | +2.1% | +7.9% | +10.3% |

---

## 5. Monthly Return Distribution


### TRAIN (57 months)

| Percentile | Return |
|---|--:|
| p10 | -2.17% |
| p25 | -0.57% |
| p50 | +0.99% |
| p75 | +2.75% |
| p90 | +3.75% |

- Mean: +1.04% · Std: 2.23% · Skew: +0.11

- Positive: 65% · Best: +6.91% · Worst: -2.85%


### HOLDOUT (23 months)

| Percentile | Return |
|---|--:|
| p10 | -2.06% |
| p25 | -0.87% |
| p50 | +0.65% |
| p75 | +2.47% |
| p90 | +3.11% |

- Mean: +0.59% · Std: 2.38% · Skew: -0.42

- Positive: 65% · Best: +4.71% · Worst: -4.59%


---

## 6. Sizing Guidance


- **Worst drawdown (TRAIN + HOLDOUT): -6.4%** — size so this is tolerable at the chosen risk budget.

- **Conservative Sharpe:** 0.86 (the lower of the two windows).

- **Monthly std dev (conservative): 2.4%** — the expected monthly swing.

- **SEALED is NOT used for sizing.** The +20.52% SEALED return is likely carry-favorable regime performance. Size on the conservative HOLDOUT-class net and worst-case drawdown, not the headline.


---

## 7. Trend Overlay (Optional — Not Evaluated)

The Trend sleeve's −0.246 correlation with Carry was identified in the pre-registration as a potential drawdown-reduction overlay. If evaluated, it would run on the same TRAIN/HOLDOUT data (no SEALED spend). This analysis is deferred — the report above provides the standalone Carry risk profile for sizing decisions.

