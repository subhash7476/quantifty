# N200 Per-Stock Regime Classifier — Closure

**Date:** 2026-09-09
**Branch:** `feat/n200-regime-hmm` (unmerged)
**Status:** **CLOSED.** Two pre-registered constructs, both gates failed. The volatility-regime family is closed by the pre-commitment written into the Variant B spec before its numbers existed. **No successor is authorized by this outcome.**

This is the terminal artifact. It consolidates what would otherwise have to be reconstructed from six reports, two specs and a commit log.

---

## 1. What was asked and what was built

A per-stock regime classifier over the point-in-time N200 cross-section: for every stock on every day, a filtered probability distribution over three latent states, a canonical label, and an entropy measure. Treated strictly as statistical estimation — no strategy expression, no P&L, no trading rule.

Pooled panel Gaussian HMM, K=3, one transition matrix shared across ~200 names, diagonal covariance, hand-rolled Baum-Welch in log space, canonical variance ordering after each fit, forward-only Hamilton filtering, expanding annual folds 2017–2026 with the parameter barrier at 31 December T−1.

## 2. Outcome

| | Variant A | Variant B | gate needs |
|---|---:|---:|---|
| Features | vol, vol-ratio, KER, drift | vol, vol-ratio-short, vol-ratio-med | — |
| S0→S2 volatility separation | 0.26σ | **1.03σ** | — |
| Brier, P(S₂) | 0.35664 | 0.29895 | — |
| Skill vs base rate | −0.6304 | −0.3667 | > 0 |
| Skill vs persistence | −0.4119 | −0.1835 | > 0 |
| Folds positive vs persistence | 0/10 | 3/10 | ≥ 7/10 |
| ECE | 0.3526 | 0.2940 | < 0.05 |
| Reliability monotone | no | no | yes |
| **Primary gate** | **FAIL** | **FAIL** | — |
| Sanity A (likelihood) | PASS 10/10 | PASS 10/10 | ≥ 8/10 |
| Sanity C (dwell, coherence) | PASS | PASS | — |

Variant A failed because EM separated on **direction** (2.4σ drift between S1 and S2, 0.26σ volatility): `P(S₂)` was a down-trend probability scored against an unoriented volatility target. Variant B removed every directional and trend-shape axis. Every number improved. None improved enough.

## 3. The finding worth keeping — the target was self-normalizing

Variant B's reliability table:

```
[0.0,0.1)   317,917 obs   predicted 0.004   observed 0.233
[0.9,1.0)   117,728 obs   predicted 0.993   observed 0.512
```

Where the model is 99.3% certain a stock sits in its high-volatility state, forward 5-day realized volatility clears that stock's **own trailing 67th percentile** 51% of the time. Above the 33% base rate, so there is real information — nowhere near a forecast.

**The mechanism: the tercile threshold is itself trailing and adaptive.** A stock that stays in a high-volatility regime for 28 sessions drags its own trailing distribution up with it, so the bar rises to meet the state. A persistent regime gets priced into the definition of the event it is supposed to predict. This is also why the persistence baseline is so hard to beat — it encodes the same adaptation directly, with no latent state required.

**Consequence for any future work:** the barrier here was the *target*, not the model. A regime construct evaluated against a **non-self-normalizing** target — an absolute volatility threshold, or a cross-sectional one — is a different and untested question. It is a new pre-registration, not a variant, and nothing in this closure authorizes it.

## 4. Why the failures were cheap

- **Zero data spend.** Everything ran on stores already in the repo.
- **The 2023–2026 sealed return window is untouched.** Both variants scored against forward *volatility*, never a return, so neither required an RFA declaration nor consumed the confirmatory budget.
- **No strategy code was written against a signal that had not cleared its gate.**
- **Variant B's failure could not be argued into a Variant C**, because the spec pre-committed in writing — before any number existed — that a failure at that point was a family-level result. That clause did the work it was written for.

## 5. Retained vs retired

**Retained — substrate and capability:**

| Asset | Why it survives |
|---|---|
| `data/features/n200_regime/panel.duckdb` | 1.8M rows, 590 entities, CA-adjusted OHLC + GK + PIT membership + entity resolution + sequence cuts. Built variant-independent on purpose; it is substrate, not output, and outlives the construct. |
| `core/analytics/regime/panel_hmm.py` | Tested panel HMM: batched log-space Baum-Welch, canonical ordering, causal filter. |
| `core/analytics/regime/features.py` | GK, efficiency ratio, drift, normalization, forward-vol target, trailing tercile cuts. |
| `tests/regime/` | 21 tests. Both causality guarantees are **mutation-verified**, not assumed. |
| Engineering patterns | Plain-array artifacts with no library-version coupling; fit-window barrier covering normalization as well as parameters; truncation test for filtered-vs-smoothed. |

**Retired — do not build on:**

| Asset | Status |
|---|---|
| `regime_panel.duckdb`, `regime_panel_b.duckdb` | Kept only so the reports reproduce. Outputs of failed constructs. |
| `params/`, `params_b/` | Same. |
| `P(S₂)` as an input to sizing, filtering or risk | **Not authorized.** Feeding it into any return-affecting decision reopens the gate question through a side door, needs its own pre-registration, and would touch forward returns. |

**Sanity A passing is not a licence.** It says the HMM compresses the feature panel better than an i.i.d. mixture or a single Gaussian, in every fold. That is a statement about description, not prediction. It is not a business case and must not be cited as one.

## 6. Boundary against the DayType repair

The DayType intraday classifier's three audited defects remain open and are the next work. **No part of this build may be substituted for DayType's model.** They are different objects over different horizons — an intraday nowcast of a session archetype versus a daily persistent regime process — and that distinction is the first section of `REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md`.

What *may* carry across is engineering practice, and it is exactly what the audit found missing there: persist fitted objects, hash plain arrays rather than pickles, and test that truncation cannot move a filtered output.

## 7. Artifact index

| File | Contents |
|---|---|
| `docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` | Variant A pre-registration |
| `docs/superpowers/specs/2026-09-09-n200-regime-hmm-variant-b-design.md` | Variant B pre-registration (delta form) |
| `docs/reports/index_research/N200_REGIME_SUBSTRATE_PREFLIGHT.md` | Substrate check, and the two facts the design absorbed |
| `docs/reports/index_research/N200_REGIME_EVALUATION.md` | Variant A gate — FAIL |
| `docs/reports/index_research/N200_REGIME_VARIANT_B_EVALUATION.md` | Variant B gate — FAIL, failure mode 1 |
| `docs/reports/index_research/REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md` | The audit that started this work |
| `docs/reports/index_research/REGIME_TRANSITION_DIAGNOSTIC.md` | DayType label persistence — no persistence found |
| `scripts/n200_regime/` | preflight, panel build, fold runner, evaluation |

Commits: `e0d67cf` preflight · `81175b0` Variant A spec · `99be3dd` engine and tests · `8971235` panel · `99153c8` folds and batched EM · `97f9c03` Variant A evaluation · `ad6ffec` Variant B spec · `5cce669` Variant B implementation and evaluation.

## 8. Caveats a reader should not lose

- The universe is `method = turnover_top200` — a constructed top-200 by turnover, **not official NSE Nifty 200 membership**. Never describe these results as "Nifty 200".
- Both variants share one panel, one target and one gate. Prior exposure is m = 2 and is disclosed in the Variant B spec; a third construct against this target would make the multiplicity problem real rather than notional.
- The pinned separation prediction for Variant B (≥ 1.0σ) was met at **1.03σ** — it cleared, and it should not be read as a comfortable margin.
