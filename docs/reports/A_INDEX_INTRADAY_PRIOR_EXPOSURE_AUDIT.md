# A (Index Intraday) — Prior-Exposure Audit of the Index 1m Store

**Date:** 2026-08-27
**Branch:** `isd-program-reassessment`
**Audited asset:** `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb` rows for
`NSE_INDEX|Nifty 50` and `NSE_INDEX|Nifty Bank` (3,574 of 3,598 daily files carry
Nifty 50; first 2012-01-02, last 2026-08-21; 3,508 files with full 375-bar sessions).
**Purpose:** establish exactly what has and has not been exposed on this store
before any successor construct ("A", index intraday on Nifty futures) consumes it.
This document is input to A's Phase-0 pre-registration and RFA declaration.

---

## 1. Methodology and limits

- Enumeration: grep of every `.py` under `scripts/`, `core/`, `flask_app/`,
  `app_facade/`, `tests/` for paths into `candles/1m`; each hit traced to its
  window (code defaults and/or output artifacts) and its computation.
- Cross-checks: actual output artifacts (feature CSVs, facts DB row counts,
  pair-research JSON) used to *prove* windows where code defaults could mislead.
- **Limits, recorded honestly:** (a) the pair-research scripts were deleted after
  the work (commit `a30f1fe`, branch `research/index-pair-trading-nifty-banknifty`);
  its windows are reconstructed from the frozen report + JSON + CHANGELOG, not the
  code. (b) One-off/untracked operator probes cannot be enumerated exhaustively;
  the audit certifies every *committed* reader. (c) Git history was searched for
  surviving scripts, not for deleted ones beyond the pair research.

## 2. Provenance — two regimes, one store

| Span | Source | Path | Verified? |
|---|---|---|---|
| 2012-01-02 → 2023-01-31 | **Reference/vendor CSVs** (`NIFTY_2012-2023.csv.zip` 1,027,960 rows / 2,723 dates / avg 378 bars / 61–750 per day; `BNF_2012-2023.csv.zip`), ingested by `scripts/ingest_reference_1m.py` | `data/reference/` → store | Ingested into the store (2026-08, NiftyShield E007 retrain era); **no independent cross-source verification ever run** |
| 2023-02-01 → present | **Upstox-native 1m** (`fetch_intermarket_data.py --include-1m`, 10-day chunks; live `market_ingestor.py`) | store | Upstox-fetched; the ISD G1–G6 suite certified the *equity* rows, not the index rows |

Notes: pre-2023 rows carry `volume = 0`; July-2016 dates were sub-minute ticks
resampled to 1m by the ingestor. The reference CSVs' ultimate origin is the legacy
NiftyShield data bundle (`NIFTY_SHIELD_MODEL_RETRAIN_AUDIT.md` §3); every daytype
fact row names them in `trained_on`. **Certification implication (for step 2 of the
A program, not this audit):** the pre-2023 slice has never been checked against the
certified 1d index store (daily close-to-close consistency is the available
independent check; the 1d store is itself certified from 2012-02-21).

## 3. Exposure inventory — every committed reader of index 1m

| Reader | Window actually read | What it computed | Exposure class |
|---|---|---|---|
| `scripts/build_intraday_features.py` (daytype) | **2012-01-04 → 2025-12-31** — *proven by output CSVs*: `intraday_features_{10am,11am,13pm}.csv` hold 3,413 / 3,405 / 3,402 rows starting 2012-01-04, ending 2025-12-31 (built 2026-08-11). Code defaults (2023-01-01→2026-02-25) were overridden. | Checkpoint partial-day features per session: partial returns, TWAP, range, CLV, linreg slope, realized vol + gap/prev-day context + BankNifty intermarket (Block H). Target: day-type `cluster_id` (regime class), not returns. | **Feature-level — structural read of the full window's index OHLC (both indices)** |
| `scripts/daytype/train_daytype_classifier.py` + `evaluate_intraday_prediction.py` | Feature CSVs (2012–2025); splits train ≤2023 / val 2024 / hold ≥2025 | Logistic regime classifier (acc 69.6 / 72.0 / 72.2); prediction-quality diagnostics (accuracy, calibration) — no returns, no P&L, no entry/exit rules | downstream of the above (no additional raw read) |
| `scripts/daytype/publish_facts.py` | 2023-01-02 → 2026-07-03 (defaults; `day_type_facts.duckdb` holds 840 sessions) | 13pm regime facts via `DayTypeEngine` → NiftyShield options gating | feature-level, forward window |
| `scripts/daytype/publish_live_fact.py` | live sessions only | same, live | feature-level, live |
| Pair research (`scripts/research/nifty_banknifty_pair/`, **deleted**; report + JSON frozen) | 1m **2023-01 → ~2026-05, 844 sessions** (315K obs) | Nifty/BankNifty ratio z-scores, autocorrelation, 27 intraday mean-reversion param combos — **all net-negative**; byproduct: intraday ratio **trends** (+1.10/+1.17 slopes) | **Signal-level — trading-rule evaluation on the index pair** |
| `scripts/nifty_shield/build_conformance_corpus.py` | 6 sessions: 2023-01-02..06, 2023-01-09 | 1m bars extracted as frozen fixtures | fixture extraction, negligible but recorded |
| `core/execution/handler.py` (`DiagnosticsEngine`) | live open-trade MAE/MFE, equity symbols | live diagnostics | none for index historical |
| `flask_app/blueprints/data/routes.py` | operator-driven chart views (any date) | display only | none (no computation) |
| `scripts/isd/*` battery (F1/F4) | `NSE_EQ` rows only — **index rows untouched** | cross-sectional equity intraday | **none for index** |
| MSRP / Carry / TS-Basis / CSMP / PSB / F1 screen | 1d store, equity stores, FUTIDX daily bhavcopy | daily-frequency signals | **none for index 1m** |
| `ingest_reference_1m.py`, `fetch_intermarket_data.py`, `market_ingestor.py` | whole store | ingestion | write path, not exposure |

## 4. Findings — what the audit settles for A

1. **"2012–2022 index 1m is unread" is FALSE.** The daytype feature builder
   consumed Nifty and BankNifty 1m OHLC over **2012-01-04 → 2025-12-31** (proven
   by its output artifacts, which outlive the run). The series has been read,
   transformed into checkpoint features, and used to train a production regime
   classifier (NiftyShield DayType). A's RFA cannot claim a virgin store.
2. **But no trading evaluation exists on the pre-2023 window.** Every daytype
   computation targeted regime classification (labels = `cluster_id`); no returns,
   no P&L, no entry/exit rules were ever computed on index 1m data anywhere in
   the repo except the pair research. **Exposure is structural (the price series
   was read), not evaluative (no rule was scored).**
3. **The 2023–2026 window carries the only signal-level read:** the pair research
   — 27 mean-reversion combos, all net-negative (the *pair* does not revert), with
   the byproduct trending-slope evidence (+1.10/+1.17) that A's continuation
   hypothesis leans on. That read is prior evidence, direction-favorable, and must
   be disclosed as such.
4. **Feature-space overlap is real and must be disclosed.** A's natural features
   (opening-window return, gap, checkpoint slope) are linear functions of the same
   prices the daytype pipeline already featurized. Overlap does not invalidate A —
   the daytype target (regime) is not A's target (per-trade return) — but it moves
   the prior from "unread quadrant" to "read for a different target, same inputs."
5. **No unread deep reserve exists for indices.** The ISD vendor archive
   (`candles/1m_vendor/`) is **equity-only** (101 ticker files, all NSE_EQ; no
   index ticker). The reference CSVs are the *same* data already in the store.
   There is no second copy of index 1m to buy a clean window from.

## 5. Consequences for the A program

- **Prior-exposure statement for A's RFA** (to be cited verbatim, SHA-locked with
  the declaration): (a) index 1m 2012–2025 read structurally by the daytype
  regime pipeline (inputs consumed, different target); (b) index 1m 2023–2026 read
  by pair-ratio analysis — mean-reversion falsified on the pair, intraday trending
  slopes +1.10/+1.17 measured; (c) no trading-rule evaluation of index 1m exists
  on any window; (d) the FTMO 0/41 corpus is the standing out-of-repo falsification
  prior.
- **Window fences remain usable but their meaning changes:** TRAIN/HOLDOUT
  (2012–2022) are *structurally exposed* (price series consumed) but *evaluatively
  clean* (no rule scored); SEALED (2023-01-01 → present) is evaluatively exposed by
  the pair research for the ratio-mean-reversion hypothesis only. The RFA's band
  defense and the TRAIN gate must not rely on "freshness" of the series — only on
  the absence of return-evaluation, which is what a pre-registration actually needs.
- **Certification (program step 2) gains one gate:** cross-check the pre-2023 index
  1m rows against the certified 1d index store (daily close identity, per-session
  completeness) — the only independent verification available for the vendor CSV
  regime.

## 6. Audit trail

- Store census: 3,598 files; Nifty 50 in 3,574; 3,508 full 375-bar sessions;
  partials 374 (17), 373 (6), 377 (6), 93 (5), 371 (4), 370 (3), 60 (3), others.
- Daytype feature CSVs: built 2026-08-11 14:27–14:28; spans as in §3.
- Facts DB: 840 sessions, `regime_fact_version` dt-v2.0-train_thru2023, model_hash
  `bd0d6826…54be7` (E007 recert, commit `fe87363`).
- Pair research: `docs/reports/NIFTY_BANKNIFTY_PAIR_RESEARCH.json` (intraday
  `n_days=844`, `intraday_mean_reverting=False`, slopes 1.0983 / 1.1710); commit
  `a30f1fe`; scripts deleted post-merge.
- Reference CSVs: `NIFTY_SHIELD_MODEL_RETRAIN_AUDIT.md` §3 tables (1,027,960 rows /
  2,723 dates / 378 avg / 61–750 min-max).
