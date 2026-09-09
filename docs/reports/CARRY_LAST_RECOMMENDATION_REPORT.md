# Carry — Last Recommendation & Performance-to-Date

**Script-generated** — `scripts/carry_last_recommendation_report.py`. Code commit `f051fd3`.

**Generated:** 2026-09-08

**Formation (recommendation):** 2026-07-31  ·  **Marked through:** 2026-09-07 (latest bhavcopy)

**Sources:** `data/signal_engine/carry/facts.duckdb`, `data/market_data/futures_bhavcopy.duckdb` (near-month close, same price source as the forward PAPER runner).


---

## 1. The Last Recommendation


Monthly carry formation **2026-07-31**: long the Q5 names (high residual carry), short the Q1 names (lowest carry), equal-weight, ADV-capped, 0.25σ no-trade band — **41 longs / 41 shorts**. Executed as the FORWARD paper book (`forward-2026-08-04` / `forward-2026-08-07` runs, ₹10M gross per side). The next formation is due 2026-08-31 (month-end); `facts.duckdb` contains nothing newer.


---

## 2. Performance to Date (formation → latest close)


Window: **2026-07-31 → 2026-09-07** (17 trading days). Equal-weight near-month futures returns, gross of fees.


| Book | n | Coverage | Mean return |
|---|--:|:--:|--:|
| **Long (Q5)** | 41 | 40/41 | -2.2906%
| **Short (Q1)** | 41 | 41/41 | -1.5951%
| **Spread (L−S)** | — | — | **-0.6955%**

Benchmark: **Nifty 50 -2.48%** over the same window — the carry spread outperformed the benchmark by **+1.7834%** (relative to a flat index the spread was -0.6955%).

Fees: entry recorded by the paper run = ₹3,270 fees + ₹5,000 slippage (~4.1 bp on ₹20M gross); a symmetric exit makes ~8.3 bp round-trip → net spread ≈ **-0.7785%**.


---

## 3. Big Movers (17-day, stock-specific)


| Side | Helped | Hurt |
|---|---|---|
| Long | ETERNAL +6.1%, MOTHERSON +7.5%, MOTILALOFS +23.3% | LUPIN -13.1%, CROMPTON -11.5%, IEX -11.5% |
| Short | GODREJCP -19.3%, RECLTD -14.9%, PIIND -12.4% | RBLBANK +11.0%, SAIL +11.2%, BOSCHLTD +18.1% |

---

## 4. Caveats


- **One formation, 17 trading days — statistically meaningless on its own.** Monthly carry's validated edge is ~+20% ann net (SEALED); a single month's spread of −0.26% is within noise.

- The FORWARD paper runs wrote entry positions only — no equity curve is tracked for FORWARD runs in `production.duckdb`, so this mark is the only point-in-time performance source. It prices the book at near-month close rather than simulating fills.

- August was idiosyncratic: Nifty 50 −0.68% while single names swung ±10–17% (GODREJCP −13.2%, RECLTD −12.1%, BOSCHLTD +17.5%, MOTILALOFS +16.4%). Neither book showed directional edge (20/41 up in each).

- No dividend adjustment applied to futures marks; a dividend paid in the window lowers the futures price and reads as a long-book loss / short-book gain mechanically (the signal itself is div-adjusted).

