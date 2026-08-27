# A — Phase-1 F&O Cost-Substrate Measurements

Generated: 2026-08-27T17:16:29 · runtime 198s · valid sessions 3572 · stamp-mismatch skipped 2

**Read boundary:** raw bars + microstructure only; no construct signal, no P&L (per A_CONSTRUCT_DEFINITION.md).

## A. Slippage (bar-open vs prior-bar-close drift, bp)

| Era | Measure | p50 | p90 | p99 | max |
|---|---|---:|---:|---:|---:|
| vendor | pooled all bars | 0.25 | 0.70 | 1.70 | 406.55 |
| vendor | entry bar 31 (cell 1) | 0.29 | 0.78 | 2.19 | 7.61 |
| vendor | entry bar 46 (cell 2) | 0.26 | 0.73 | 1.62 | 12.84 |
| native | pooled all bars | 0.20 | 0.62 | 1.27 | 49.56 |
| native | entry bar 31 (cell 1) | 0.22 | 0.70 | 1.36 | 2.23 |
| native | entry bar 46 (cell 2) | 0.21 | 0.66 | 1.27 | 1.94 |

Entry slippage lane: p90 of the entry-bar drift per era per cell. Exit lane: the ISD convention — exit at the last bar close pays the same band.

## B. Basis (near-month Nifty futures vs official cash, bp)

| Statistic | Level (bp) | |Δ daily|, within-contract (bp) |
|---|---:|---:|
| n | 2555 | 2430 (roll days excluded: 125) |
| p50 | 18.22 | 7.56 |
| p90 | 45.25 | 19.24 |
| p99 | 76.55 | 38.83 |
| max | 129.79 | 100.33 |

**Basis treatment (D5 input) — mean vs dispersion.** The basis change over a hold splits into: (1) a MEAN component = the carry drift over the hold — for a ~5.7h hold at ~6% carry, ~0.4 bp/trade (direction-dependent; a long position loses the carry decay, a short gains it; for the alternating sign book it nearly nets out) — immaterial to the net-spread gate; (2) a DISPERSION component = basis noise over the hold. The measurable bound is the full-day within-contract |Δ| p90 of 19.2 bp; the intraday-hold value is unmeasurable pre-2023 (no futures 1m) and is expected to be smaller (the full-day measure includes overnight basis gaps an intraday hold avoids; futures and cash move together tick-by-tick intraday). The noise is INVISIBLE to a cash-series backtest, so it does not enter the net-spread gate as a cost — it enters the RFA as a Sharpe/power disclosure: the declared per-trade effect must be defended against a basis-noise floor of ~19 bp/day (full-day bound). A cheap forward probe (live futures LTP vs cash index over actual hold windows, ~30 sessions) can measure the intraday value on the native era. Pre-2016 spans hold the 2016+ figures as the disclosed assumption.

## C. Roll calendar (volume-dominance, NIFTY FUTIDX)

Total roll dates: 131 (2016-02-24 -> 2026-10-26); by year: 2016:11, 2017:12, 2018:12, 2019:12, 2020:12, 2021:12, 2022:12, 2023:13, 2024:12, 2025:13, 2026:10

Roll executes at entry-time instrument selection (flat overnight — 0 roll legs; the basis lane covers the discrepancy).

## D. Cadence (tradeable sessions per year)

| Year | cell 1 (entry bar 31) | cell 2 (entry bar 46) |
|---|---:|---:|
| 2012 | 250 | 250 |
| 2013 | 249 | 249 |
| 2014 | 243 | 243 |
| 2015 | 247 | 247 |
| 2016 | 246 | 246 |
| 2017 | 247 | 247 |
| 2018 | 223 | 223 |
| 2019 | 244 | 244 |
| 2020 | 251 | 251 |
| 2021 | 247 | 247 |
| 2022 | 247 | 247 |
| 2023 | 225 | 225 |
| 2024 | 249 | 249 |
| 2025 | 249 | 249 |
| 2026 | 155 | 155 |

Cadence per year = sessions passing the session-validity rule with the entry bar present. Trades/year for the RFA cadence figure: mean of the cell-1 column across 2012-2026 (238/yr).

Snapshot: `data/a_index_intraday/cost_substrate_measurements.json`
