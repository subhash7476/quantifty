# Carry — Production Metrics Report

**Script-generated** — `scripts/carry_production_report.py`. Code commit `2ed44fa`.

**Generated:** 2026-07-25

**Source:** `data/signal_engine/carry/production.duckdb`

**SEALED:** snapshot-ingested only — strategy NEVER run over SEALED (`CARRY_SEALED_READ_PROTOCOL.md` §2).


---

## 1. Runs


| Window | Source | Rebalances | Determinism Hash |
|---|:---:|--:|:---:|
| TRAIN | replay | 58 | `5dcfbf6ee1981763` |
| HOLDOUT | replay | 24 | `6cee5eb8b577e6ac` |
| SEALED | snapshot | 1 | `(snapshot)` |

---

## 2. Returns


| Window | Source | Ann Gross | Ann Net | Fee Drag | Avg Turnover |
|---|:--:|--:|--:|--:|--:|
| **TRAIN** | replay |  +14.22% | **+12.84%** | 138.2 bp | 1.433 |
| **HOLDOUT** | replay |   +8.36% | **+6.96%** | 140.6 bp | 1.464 |
| **SEALED** | snapshot | +22.23% | **+20.52%** | 170.6 bp | 1.466 |

---

## 3. Parity Reconciliation (A5 Gate)


Tolerance: 15 bp (same as GATE D).


| Window | Research Net | Replay Net | Delta | Verdict |
|---|--:|--:|--:|:--:|
| **TRAIN** | +12.84% | +12.84% | +0.0 bp | PASS |
| **HOLDOUT** | +6.96% | +6.96% | +0.0 bp | PASS |

Note: parity check tests construction-level identity at +0.0 bp (`parity_check.py`). The LoopDriver replay path reproduces research returns exactly — the hook's `signals_db_path` parameter filters the book to `signals.fwd_ret_1m IS NOT NULL`, matching the pre-registered filter. Both windows converge to 0.0 bp delta.


---

## 4. Fee Decomposition


### TRAIN

| Component | Total (Rs) | Share |
|---|--:|--:|
| Brokerage | 119,240 | 49.5% |
| STT | 41,547 | 17.3% |
| Exchange Txn | 17,450 | 7.2% |
| SEBI Fee | 831 | 0.3% |
| Stamp Duty | 38,079 | 15.8% |
| GST | 23,610 | 9.8% |
| **Subtotal fees** | **240,757** | 100.0% |
| **Slippage (5 bp/side)** | **415,469** | — |

### HOLDOUT

| Component | Total (Rs) | Share |
|---|--:|--:|
| Brokerage | 53,940 | 57.5% |
| STT | 17,565 | 18.7% |
| Exchange Txn | 7,377 | 7.9% |
| SEBI Fee | 351 | 0.4% |
| Stamp Duty | 3,513 | 3.7% |
| GST | 11,100 | 11.8% |
| **Subtotal fees** | **93,847** | 100.0% |
| **Slippage (5 bp/side)** | **175,648** | — |

---

## 5. Position Concentration


| Window | Avg Top-3 | Avg HHI | Max Top-3 |
|---|--:|--:|--:|
| TRAIN | 0.049 | 0.016 | 0.107 |
| HOLDOUT | 0.044 | 0.015 | 0.065 |

---

## 6. Drawdown / Risk


| Window | Max DD | Worst Month | Best Month | Sharpe |
|---|--:|--:|--:|--:|
| TRAIN | -6.44% | -2.85% | +6.91% | 1.61 |
| HOLDOUT | -5.16% | -4.59% | +4.71% | 0.86 |

---

## 7. Margin Utilisation


| Window | Avg % | Max % |
|---|--:|--:|
| TRAIN | 20.0% | 20.0% |
| HOLDOUT | 20.0% | 20.0% |

---

## 8. Determinism


- **HOLDOUT:** `6cee5eb8b577e6ac`

- **TRAIN:** `5dcfbf6ee1981763`


Re-run `scripts/carry_paper_replay.py` — the TRAIN and HOLDOUT hashes must match. Any divergence indicates non-deterministic replay behaviour.


---

## 9. SEALED (Snapshot-Ingested Only)


- **Window:** 2023-01-01 → 2026-07-20

- **Mean IC:** +0.061043

- **Ann Gross:** +22.23%

- **Ann Net:** +20.52%

- **Fee Drag:** 170.6 bp

- **Avg Turnover:** 1.466

- **Gate:** PASS


**Strategy was NEVER run over SEALED.** Metrics above are ingested from the frozen one-shot `CARRY_SEALED_SNAPSHOT.json` per `CARRY_SEALED_READ_PROTOCOL.md` §2.

