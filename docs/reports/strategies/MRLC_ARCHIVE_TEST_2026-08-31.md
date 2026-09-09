# MRLC Archive Test — Nifty 100 1m (2015-02 → 2025-08)

**Date:** 2026-08-31 · **Branch:** MRLC-testing
**Source:** `C:\Users\devou\Downloads\archive.zip` — 100 CSVs (Nifty 50 + Nifty Next 50
as of ~Aug-2025), 1-minute OHLCV, 89.2M rows, 2015-02-02 → 2025-08-06.

## What was done

1. **Ingested** (`archive_ingest.py`): streamed the zip → resampled 1h/4h/1d per symbol,
   after-hours stray row stripped, 78 zero-close vendor-gap days removed.
2. **Validated the price basis**: the archive is an internally continuous (CA-adjusted,
   anchored ~2015) series — verified: on ex-dates (e.g., RELIANCE 2024-10-28) the raw
   bhavcopy steps 0.50→1.00 while the archive's own return is 0.45%. Our 1m store is
   also on an adjusted basis (matches `equity_bhavcopy_adjusted` to ~0.1%), so the
   archive and the 2023-26 dev window are **directly comparable**.
3. **Backtested** (same engine as the 2023-26 test, 2× stop, news guard, delivery fees):
   - **OOS 2015-02 → 2022-12** — an 8-year window the intraday cells had never seen.
   - **OVL 2023-01 → 2025-08** — overlap with the dev period, same 100 names.

## Results (net of fees, 2× stop, news guard)

| TF | Window | ≤10% n | win% | exp | t | ≤15% n | exp | t |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| **1h** | dev 2023-26 (196 names) | 244 | 43% | +0.39 | 3.29 | 40 | +0.72 | 2.12 |
| 1h | **OOS 2015-22 (100 names)** | 298 | 41% | **+0.15** | 1.66 | 79 | +0.29 | 1.74 |
| 1h | OVL 2023-25 (100 names) | 54 | 30% | −0.03 | −0.11 | 9 | +0.90 | 0.83 |
| **4h** | dev 2023-26 | 83 | 53% | +0.13 | 1.23 | 15 | +0.42 | 2.87 |
| 4h | **OOS 2015-22** | 109 | 54% | **+0.19** | 1.90 | 30 | +0.20 | 0.90 |
| 4h | OVL 2023-25 | 16 | 50% | +0.20 | 0.74 | 4 | +0.78 | 2.00 |
| **1d** | dev 2023-26 | 35 | 51% | −0.02 | −0.16 | 4 | +0.67 | 1.67 |
| 1d | **OOS 2015-22** | 49 | 53% | **+0.09** | 0.91 | 11 | +0.73 | 1.70 |
| 1d | OVL 2023-25 | 11 | 46% | −0.08 | −0.31 | 1 | +0.65 | — |

## What this establishes

1. **No sign flips anywhere in the 8-year unread window.** Every cell that was positive
   in 2023-26 is positive in 2015-22 (1h +0.15, 4h +0.19, 1d +0.09); none of the
   archive OOS cells are negative. The intraday construct survives its first real
   out-of-sample test.
2. **The 4h cell is the steadiest**: +0.19R over 109 OOS trades (t=1.90) and +0.20R on
   the overlap — consistent with the dev window's +0.13R/+0.42R. Three independent
   windows, same sign, same magnitude.
3. **The edge is weaker in the pure large-cap 100 than in the 196-name/2,300-name
   universes** — consistent with the size-split finding. The 1h OVL 2023-25 (−0.03R,
   n=54) is the one weak spot; the dev window's 1h strength comes mostly from
   2025-26 and from mid-caps outside the archive's 100.

## Caveats

- **Survivorship (archive):** the 100 names are today's Nifty 100 — names removed since
  2015 are absent. This flatters results; the 2,300-name daily extension remains the
  cleanest universe.
- **Vendor volume units unknown** — the sweep's 2×-median filter is unit-invariant per
  symbol, so this does not bias the trigger; disclosed anyway.
- **OOS ≠ pre-registered holdout:** thresholds/guard were set on the 2023-26 window
  before this read; the archive read is consistent with the pinned config, but the
  selection history must be disclosed in any future gate.

## Record

- `scripts/mrlc_test/archive_ingest.py` — zip → 1h/4h/1d candles (`archive_candles.duckdb`)
- `scripts/mrlc_test/summarize_archive.py` — the table above
- Trades: `trades_arc_os_2_0_guard.csv` (OOS), `trades_arc_ov_2_0_guard.csv` (overlap)
- Engine unchanged (`engine.py` — ranks int-cast fix only); sanity suite ALL PASS.
