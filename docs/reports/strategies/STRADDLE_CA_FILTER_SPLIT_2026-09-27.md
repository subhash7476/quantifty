# W6 — Stock-Straddle `ca_in_hold` Split and Kinked Beta (generated)

Pre-analysis note: `STRADDLE_CA_FILTER_SPLIT_PREREG_2026-09-27.md`. Script: `scripts/research/options_seller_edge/ca_filter_split.py`.

- Parquet: `stock_straddles.parquet`, SHA-256 `a579b95f877c9e35e9ea41b44bd60af632a8e34e4329d47bcffe022bbfff858a`
- Construct: variant `m10`, stock names only, net at 2% spread, per-expiry mean then t across expiries

## 1. Reproduction gate (filter in place)

| window | mean | t | expiries | target mean | target t | pass |
|---|--:|--:|--:|--:|--:|---|
| discovery | +11.48% | 4.98 | 80 | +11.5% | 4.98 | PASS |
| confirmation | +8.20% | 2.90 | 43 | +8.2% | 2.90 | PASS |

(Tolerance pinned in the note: ±0.1 pp in mean, ±0.05 in t.)

Erratum to the note: it quotes discovery as "166 expiries"; 166 is the study's *names per expiry* column (§2.1). The gate tests mean and t only, as pinned, so it is unaffected.

## 2. What the filter drops

| window | clean rows | dropped | CA-verified | pure move | pure-move share of rows |
|---|--:|--:|--:|--:|--:|
| discovery | 13322 | 41 | 0 | 41 | 0.308% |
| confirmation | 8336 | 3 | 0 | 3 | 0.036% |
| post-reform | 4328 | 1 | 0 | 1 | 0.023% |

Dropped symbols absent from the CA register entirely: ['IBREALEST', 'IBULHSGFIN', 'INFRATEL', 'NIITTECH']

## 3. Result with pure moves restored (CA-verified stay dropped)

| window | filter kept: mean (t, n) | pure moves restored: mean (t, n) | change |
|---|--:|--:|--:|
| discovery | +11.48% (4.98, 80) | +10.79% (4.47, 80) | -0.69% |
| confirmation | +8.20% (2.90, 43) | +8.07% (2.85, 43) | -0.13% |
| post-reform | +6.72% (1.37, 21) | +6.59% (1.35, 21) | -0.13% |

**Pinned decision rule (confirmation, restored): mean +8.07%, t 2.85 → SURVIVES its look-ahead (still INSUFFICIENT for a construct).**

## 4. Tail disclosure

- Confirmation window: crash frequency p = 3 / 8336 = 0.036% of rows; mean net seller return on them -350.5%
- Whole sample: 44 pure-move rows, mean net seller return -234.2%

Every pure-move row (for checking by eye):

| symbol | entry | exit | max \|daily move\| | net seller return | P&L % notional | symbol in CA register |
|---|---|---|--:|--:|--:|---|
| PNB | 2017-10-11 | 2017-10-25 | 36.1% | -764.5% | -45.97% | True |
| DHFL | 2018-09-11 | 2018-09-26 | 55.6% | -709.3% | -44.62% | True |
| DIVISLAB | 2016-12-15 | 2016-12-28 | 25.2% | -666.0% | -26.67% | True |
| IBREALEST | 2017-04-12 | 2017-04-26 | 32.7% | -646.5% | -51.87% | False |
| CANBK | 2017-10-11 | 2017-10-25 | 32.2% | -638.9% | -36.82% | True |
| IEX | 2025-07-17 | 2025-07-30 | 34.1% | -579.4% | -29.99% | True |
| BANKINDIA | 2017-10-11 | 2017-10-25 | 29.1% | -570.2% | -33.68% | True |
| BANKBARODA | 2017-10-11 | 2017-10-25 | 26.9% | -522.2% | -28.72% | True |
| UNIONBANK | 2017-10-11 | 2017-10-25 | 29.1% | -516.8% | -34.03% | True |
| DISHTV | 2019-01-17 | 2019-01-30 | 39.7% | -420.8% | -25.36% | True |
| TATAMTRDVR | 2019-10-15 | 2019-10-30 | 31.9% | -359.6% | -32.10% | True |
| ADANIENT | 2024-11-12 | 2024-11-27 | 25.8% | -311.6% | -14.03% | True |
| TATAMOTORS | 2019-10-15 | 2019-10-30 | 30.3% | -287.4% | -26.99% | True |
| INDUSINDBK | 2020-03-12 | 2020-03-25 | 27.4% | -274.6% | -46.35% | True |
| M&MFIN | 2020-03-12 | 2020-03-25 | 33.1% | -274.3% | -33.22% | True |
| AXISBANK | 2020-03-12 | 2020-03-25 | 32.9% | -254.0% | -31.22% | True |
| YESBANK | 2018-09-11 | 2018-09-26 | 34.2% | -246.9% | -21.55% | True |
| IDEA | 2019-11-14 | 2019-11-27 | 30.4% | -227.1% | -67.80% | True |
| ASHOKLEY | 2020-03-12 | 2020-03-25 | 25.8% | -214.4% | -28.55% | True |
| CHOLAFIN | 2020-03-12 | 2020-03-25 | 35.3% | -212.9% | -25.73% | True |
| BAJAJFINSV | 2020-03-12 | 2020-03-25 | 29.7% | -198.0% | -23.79% | True |
| EQUITAS | 2020-03-12 | 2020-03-25 | 29.3% | -173.9% | -31.58% | True |
| ZEEL | 2024-01-10 | 2024-01-24 | 39.6% | -160.5% | -21.85% | True |
| BAJFINANCE | 2020-03-12 | 2020-03-25 | 26.7% | -156.9% | -17.96% | True |
| FEDERALBNK | 2020-03-12 | 2020-03-25 | 28.1% | -147.4% | -19.68% | True |
| ZEEL | 2021-09-16 | 2021-09-29 | 27.1% | -137.7% | -14.02% | True |
| ZEEL | 2019-01-17 | 2019-01-30 | 30.9% | -135.6% | -6.71% | True |
| IDEA | 2019-10-15 | 2019-10-30 | 28.2% | -130.1% | -19.35% | True |
| INFRATEL | 2020-03-12 | 2020-03-25 | 26.1% | -124.5% | -18.90% | False |
| STAR | 2018-05-17 | 2018-05-30 | 26.7% | -122.0% | -9.30% | True |
| IBULHSGFIN | 2020-06-11 | 2020-06-24 | 26.3% | -105.8% | -19.39% | False |
| JISLJALEQS | 2019-06-13 | 2019-06-26 | 33.4% | -97.5% | -10.06% | True |
| INFIBEAM | 2018-10-10 | 2018-10-24 | 29.3% | -56.4% | -13.00% | True |
| NIITTECH | 2020-03-12 | 2020-03-25 | 27.0% | -45.0% | -4.12% | False |
| MFSL | 2020-03-12 | 2020-03-25 | 34.4% | -30.5% | -4.20% | True |
| PCJEWELLER | 2018-07-12 | 2018-07-25 | 30.0% | -27.5% | -5.25% | True |
| DHFL | 2019-07-11 | 2019-07-24 | 45.6% | +0.7% | +0.67% | True |
| RELCAPITAL | 2019-06-13 | 2019-06-26 | 36.0% | +4.3% | +0.88% | True |
| RBLBANK | 2020-03-12 | 2020-03-25 | 25.1% | +17.4% | +4.58% | True |
| MOTHERSUMI | 2020-03-12 | 2020-03-25 | 26.2% | +30.7% | +6.54% | True |
| INFIBEAM | 2018-09-11 | 2018-09-26 | 25.4% | +31.6% | +3.46% | True |
| JETAIRWAYS | 2019-06-13 | 2019-06-26 | 65.1% | +47.6% | +15.79% | True |
| RELINFRA | 2019-06-13 | 2019-06-26 | 29.5% | +53.0% | +8.75% | True |
| IDEA | 2020-01-16 | 2020-01-29 | 28.5% | +54.5% | +18.18% | True |

CA-verified rows (kept dropped):

| symbol | entry | exit | events |
|---|---|---|---|

## 5. Kinked market beta (descriptive)

y = equal-weight mean P&L (% of futures notional) per expiry; x = Nifty 50 entry→exit return; kink k = -3%; HC1 standard errors.

| sample | n | cycles x < k | β (se) | β_down (se) | x² coef (t) |
|---|--:|--:|--:|--:|--:|
| filter kept | 123 | 12 | +0.076 (0.098) | +0.373 (0.103) | -1.99 (-1.70) |
| pure moves restored | 123 | 12 | +0.060 (0.098) | +0.550 (0.081) | -2.75 (-2.80) |

All windows pooled (2016 → 2026-08). Few cycles fall below the kink, so β_down is imprecise; it is reported, not used to choose anything.

## 6. Supplementary check (added after the run; not pinned in the note)

No dropped row was CA-verified, which means corporate actions leave the sample earlier, through the missing-exit filter. Is that filter a second outcome filter?

- Rows (m10, stock, other clean filters) with a missing exit leg or future: **59 of 21717** (0.27%); CA-verified 35, unmatched 24
- Unmatched rows: median max |daily move| 5.0%; 6 with a move ≥ 15%

| symbol | entry | exit | max \|daily move\| |
|---|---|---|--:|
| ABFRL | 2025-05-15 | 2025-05-28 | 109.2% |
| ARVIND | 2018-11-14 | 2018-11-28 | 104.8% |
| KPIT | 2019-01-17 | 2019-01-30 | 51.9% |
| TATAMOTORS | 2025-10-13 | 2025-10-27 | 51.2% |
| M&MFIN | 2020-07-16 | 2020-07-29 | 36.1% |
| MOTHERSUMI | 2022-01-12 | 2022-01-25 | 23.4% |
| TORNTPOWER | 2023-02-09 | 2023-02-22 | 10.4% |
| L&TFH | 2021-01-13 | 2021-01-27 | 9.4% |
| VEDL | 2020-10-15 | 2020-10-28 | 7.8% |
| RECLTD | 2023-07-13 | 2023-07-26 | 6.9% |

The large-move unmatched rows are corporate events absent from the repo's demerger register (e.g. ABFRL 2025, ARVIND 2018, KPIT 2019, TATAMOTORS 2025, MOTHERSUMI 2022 demergers). A missing exit leaves no seller P&L to restore, and the set is too small to move the per-expiry mean, so the pinned verdict stands.
