# Carry — Full-Path Replay Parity Report

**Script-generated** — `scripts/signal_engine/carry/replay_parity_check.py`. Code commit `06aa49d`.

**Generated:** 2026-07-24

**Protocol:** `CARRY_IMPLEMENTATION_BRIDGE.md` §5 — production path must reproduce research net spread within tolerance.

**SEALED:** NOT re-run — parity guaranteed by construction (identical code = identical output).


---

## 1. Setup and Constants


**Gross exposure:** Rs 1.0 Cr (research-identical)

**Slippage:** 5 bp/side

**Tolerance:** ±15 bp (float ordering + fill timing)

**Windows:**

- TRAIN: 2016-03-31 → 2020-12-31

- HOLDOUT: 2021-01-01 → 2022-12-31


---

## 2. Predictions (stated before results, per §5)


**Date set match:** WILL match

**Book identity:** WILL match

**Parity within tolerance:** WILL fall within

**Rationale:** Construction is identical; replay path now feeds coherent cross-sections.


---

## 3. Pre-Check 4.1 — Rebalance-Date Set Identity


| Window | Direct Count | Replay Count | Match? | Missing | Extra |
|---|--:|--:|:--:|---|---|
| TRAIN | 58 | 26 | ❌ | 32 | 0 |

| HOLDOUT | 24 | 24 | ✅ | 0 | 0 |


---

## 4. Pre-Check 4.2 — Per-Date Book Identity


| Window | Total Dates | Matching | Differing | Match? | Example Diff |
|---|--:|--:|--:|:--:|---|
| TRAIN | 58 | 23 | 35 | ❌ | (datetime.date(2016, 6, 30), 'long_symbols', {'IFCI', 'CROMPGREAV', 'LICHSGFIN', 'ABIRLANUVO', 'HCLTECH', 'IBULHSGFIN', 'RECLTD', 'SOUTHBANK', 'ICICIBANK', 'BANKBARODA', 'NMDC', 'RPOWER', 'HDFCBANK', 'BEML', 'NTPC', 'IDBI', 'JINDALSTEL', 'ORIENTBANK', 'INFY', 'PFC', 'ICIL', 'KPIT', 'L&TFH', 'SYNDIBANK', 'ADANIENT', 'INDUSINDBK', 'HINDALCO', 'HEXAWARE', 'IDFC', 'UNITECH', 'UNIONBANK', 'NHPC', 'BHEL', 'POWERGRID'}, {'IFCI', 'CROMPGREAV', 'LICHSGFIN', 'ABIRLANUVO', 'HCLTECH', 'IBULHSGFIN', 'RECLTD', 'SOUTHBANK', 'ICICIBANK', 'BANKBARODA', 'NMDC', 'RPOWER', 'HDFCBANK', 'BEML', 'NTPC', 'IDBI', 'JINDALSTEL', 'ORIENTBANK', 'INFY', 'PFC', 'ICIL', 'KPIT', 'L&TFH', 'SYNDIBANK', 'ADANIENT', 'INDUSINDBK', 'HINDALCO', 'HEXAWARE', 'IDFC', 'UNITECH', 'UNIONBANK', 'NHPC', 'BHEL'}) |

| HOLDOUT | 24 | 21 | 3 | ❌ | (datetime.date(2022, 2, 28), 'short_symbols', {'ONGC', 'BEL', 'IOC', 'MFSL', 'INDIAMART', 'AMBUJACEM', 'NAVINFLUOR', 'IPCALAB', 'RAIN', 'TECHM', 'INDUSTOWER', 'SRTRANSFIN', 'CHOLAFIN', 'VOLTAS', 'BOSCHLTD', 'APOLLOHOSP', 'GNFC', 'MINDTREE', 'LT', 'NTPC', 'MUTHOOTFIN', 'BHARATFORG', 'GAIL', 'COLPAL', 'CHAMBLFERT', 'BPCL', 'ESCORTS', 'NAM-INDIA', 'ITC', 'FSL', 'LUPIN', 'CADILAHC', 'COFORGE', 'VEDL', 'IDFC', 'BSOFT', 'SUNTV', 'MRF', 'BHEL', 'POWERGRID'}, {'ONGC', 'BEL', 'IOC', 'MFSL', 'INDIAMART', 'AMBUJACEM', 'NAVINFLUOR', 'IPCALAB', 'RAIN', 'TECHM', 'INDUSTOWER', 'SRTRANSFIN', 'CHOLAFIN', 'VOLTAS', 'BOSCHLTD', 'APOLLOHOSP', 'GNFC', 'MINDTREE', 'LT', 'NTPC', 'MUTHOOTFIN', 'BHARATFORG', 'GAIL', 'COLPAL', 'CHAMBLFERT', 'BPCL', 'ESCORTS', 'NAM-INDIA', 'ITC', 'FSL', 'DIXON', 'LUPIN', 'COFORGE', 'VEDL', 'IDFC', 'BSOFT', 'SUNTV', 'MRF', 'BHEL', 'POWERGRID'}) |


---

## 5. Parity — Replay vs Research


| Window | Rebalances | Research Net | Replay Net | Delta (bp) | Verdict |
|---|--:|--:|--:|--:|:--:|
| TRAIN | 26 | +12.84% | -1.87% | -1471.5 bp | ❌ **FAIL** |

| HOLDOUT | 24 | +6.96% | +3.22% | -373.5 bp | ❌ **FAIL** |


---

## 6. Determinism


**Output hash:** 101717258224

(Rerun the script twice — hashes must match for determinism)


---

## 7. Gate Verdict


**GATE D VERDICT: ❌ FAIL**


FAIL: Rebalance-date set mismatch — replay missed or added dates.

FAIL: Per-date book identity mismatch — construction divergence.

FAIL: Net-spread delta outside tolerance — path divergence.


STOP. Trace the divergence before proceeding to WS-E.


