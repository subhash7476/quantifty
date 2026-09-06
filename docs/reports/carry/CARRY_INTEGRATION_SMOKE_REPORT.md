# Carry — Integration Smoke Test Report

**Script-generated** — `scripts/carry_integration_check.py`. Code commit `438c45f`.

**Generated:** 2026-07-23

**Purpose:** verify that `CarryRebalancerHook.__call__()` drives the full production chain end-to-end — margin check, target-book construction, delta execution, fill placement — against real `facts.duckdb` data.


---

## 1. Setup

- **Facts DB:** `F:\Nifty\data\signal_engine\carry\facts.duckdb`

- **Bhavcopy DB:** `F:\Nifty\data\market_data\futures_bhavcopy.duckdb`

- **Handler mode:** `ExecutionMode.PAPER`, `PaperBroker`

- **Initial capital:** Rs 1 Cr (`initial_capital=10_000_000.0`)

- **Gross-exposure policy:** `paper_gross_exposure_policy` → Rs 1 Cr fixed

- **ADV capping:** enabled (`bhavcopy_db_path` provided)

- **Margin check:** active (flat-rate 20%, 80% utilisation cap)

- **Slippage:** 5bp/side injected via `_build_fill`


---

## 2. Per-Date Results


| Formation Date | Fired | Longs | Shorts | Gross (Rs Cr) | Target | Dedup |
|---|:--:|--:|--:|--:|--:|:--:|
| 2016-05-31 | PASS | 32 | 32 | 1.00 | 1.00 | PASS |
| 2021-05-31 | PASS | 31 | 31 | 1.00 | 1.00 | PASS |
| 2026-07-20 | PASS | 39 | 39 | 1.00 | 1.00 | PASS |

---

## 3. Detail (per-formation samples)


### 2016-05-31

- **Fired:** True

- **Positions:** 32 long + 32 short = 64 total (from 0 initially)

- **Gross exposure:** Rs 10,000,000 (target: Rs 10,000,000)

- **Dedup:** second call returned `False` (positions unchanged)

- **Longs (sample):** ALBKFUT, AMARAJABATFUT, ANDHRABANKFUT

- **Shorts (sample):** AMBUJACEMFUT, BAJFINANCEFUT, BIOCONFUT


### 2021-05-31

- **Fired:** True

- **Positions:** 31 long + 31 short = 62 total (from 0 initially)

- **Gross exposure:** Rs 10,000,000 (target: Rs 10,000,000)

- **Dedup:** second call returned `False` (positions unchanged)

- **Longs (sample):** AMARAJABATFUT, APOLLOTYREFUT, BANDHANBNKFUT

- **Shorts (sample):** ASIANPAINTFUT, BHARTIARTLFUT, DIVISLABFUT


### 2026-07-20

- **Fired:** True

- **Positions:** 39 long + 39 short = 78 total (from 0 initially)

- **Gross exposure:** Rs 10,000,000 (target: Rs 10,000,000)

- **Dedup:** second call returned `False` (positions unchanged)

- **Longs (sample):** ABBFUT, ASIANPAINTFUT, AUROPHARMAFUT

- **Shorts (sample):** ADANIPOWERFUT, ASTRALFUT, BAJAJFINSVFUT


---

## 4. Verdict

**PASS** — `CarryRebalancerHook` fires on formation dates, margin check clears, target book constructed, fills placed in `position_tracker`, gross exposure matches target. Dedup prevents double-execution on same date. Full production chain verified end-to-end.

