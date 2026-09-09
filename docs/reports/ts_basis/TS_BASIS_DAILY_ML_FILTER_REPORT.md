# TS Basis Daily — ML Signal Rejection Filter

**Script-generated** — `scripts/signal_engine/ts_basis_daily/ml_filter.py`. Code commit `80f5e86`.

**Generated:** 2026-07-28

**Model:** LightGBM binary classifier. Target: signed_return > 0.

**Windows:** TRAIN 2016-03-31→2019-12-31 (95,087) | VAL 2020-01-01→2020-12-31 (22,722) | HOLDOUT 2021-01-01→2022-12-31 (72,319).


---
## 1. Baseline

| Window | n | Hit Rate |
|---|---:|--:|
| TRAIN | 95,087 | 50.7% |
| VAL | 22,722 | 51.8% |
| HOLDOUT | 72,319 | 50.8% |

---
## 2. Model Performance

| Metric | TRAIN | VAL | HOLDOUT |
|---|---:|---:|---:|
| ROC-AUC | 0.5475 | 0.4943 | 0.5112 |
| Brier | 0.2499 | 0.2498 | 0.2499 |
| Trees | 1 | — | — |

---
## 3. Feature Importance

| Feature | Importance |
|---|---:|
| nifty_ret_20d | 7.0000 |
| n_signals_today | 6.0000 |
| nifty_ret_1d | 4.0000 |
| vix | 3.0000 |
| z_rank | 2.0000 |
| raw_ann_basis | 2.0000 |
| abs_z | 1.0000 |
| nifty_ret_5d | 1.0000 |
| z_ts | 0.0000 |
| z_delta | 0.0000 |
| adv_tier | 0.0000 |
| day_of_week | 0.0000 |

---
## 4. Rejection Analysis (HOLDOUT)

*Can the model identify a subset of signals to reject with meaningfully worse hit rate?*

| Threshold | Rejected | Kept | Rejected Hit | Kept Hit | Lift |
|---|--:|--:|--:|--:|--:|
| 0.505 | 450 | 71,869 | 53.6% | 50.8% | -0.0pp |
| 0.506 | 13,829 | 58,490 | 50.7% | 50.9% | +0.0pp |
| 0.507 | 16,505 | 55,814 | 50.2% | 51.1% | +0.2pp |
| 0.507 | 22,756 | 49,563 | 50.2% | 51.1% | +0.3pp |
| 0.507 | 34,620 | 37,699 | 50.0% | 51.7% | +0.8pp |
| 0.507 | 34,620 | 37,699 | 50.0% | 51.7% | +0.8pp |
| 0.507 | 43,960 | 28,359 | 50.4% | 51.6% | +0.8pp |
| 0.507 | 43,960 | 28,359 | 50.4% | 51.6% | +0.8pp |
| 0.508 | 65,073 | 7,246 | 50.5% | 54.3% | +3.4pp |

---
## 5. Verdict

**VERDICT: DISCARD** — Early-stopped at 1 tree (VAL AUC 0.4943, worse than random). HOLDOUT AUC 0.5112 is noise-level. The +3.4pp apparent lift at the 0.508 threshold keeps only 7,246 signals (10% of HOLDOUT) — a sample-size artifact, not a real finding. The model learned nothing. Delete `ml_filter.py` and `ml_reject_model.pkl` — no impact on pipeline.


---

**Generated:** 2026-07-28 | **Commit:** `80f5e86`

