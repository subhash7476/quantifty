# NiftyShield Model Retrain — State Assessment

**Branch:** `feat/niftyshield-model-retrain`  
**Date:** 2026-08-10  
**Status:** ASSESSMENT — pre-execution  

---

## 1. Current State — What F:\Nifty Has

### Models (imported, not trained here)

The three `.pkl` model directories were copied from the retired `D:\BOT\root` platform
during the SALVAGE migration and frozen under Decision DT1
(`DAYTYPE_FACTS_ADOPTION_SPEC.md:99`):

| Directory | Checkpoint | Provenance |
|-----------|-----------|------------|
| `models/daytype/logistic_10am/` | 10:00 AM | D:\BOT\root vintage |
| `models/daytype/logistic_11am/` | 11:00 AM | D:\BOT\root vintage |
| `models/daytype/logistic_13pm_prod/` | 13:00 PM | **Production — used by NiftyShield** |

The 13pm_prod model (`model.pkl` + `scaler.pkl` + `metadata.json`) is the **only model
NiftyShield consumes**. The AM checkpoints are present solely so the `DayTypeEngine` loads
cleanly — they are never queried for facts (DT5).

Every fact row carries:
```
trained_on = "D:\BOT\root vintage -- NOT F:\nifty data"
```

### What IS in F:\Nifty (ported from D:\bot\root)

| File | Purpose |
|------|---------|
| `core/analytics/day_features.py` | 53 EOD features from 1m bars — input to clustering |
| `core/analytics/resampler.py` | 5m/15m bar resampling |
| `core/state/daytype_engine.py` | Live runtime: bar ingestion → feature compute → model predict |
| `scripts/build_intraday_features.py` | Offline: partial-day feature CSVs at 10am/11am/13pm |
| `scripts/daytype/publish_facts.py` | Offline facts publisher (batch over date range) |
| `scripts/daytype/publish_live_fact.py` | Live 13:00 fact publisher (wired to LoopDriver hook) |

### What is NOT in F:\Nifty (only in D:\bot\root)

| Script | Lines | Purpose |
|--------|-------|---------|
| `scripts/cluster_day_types.py` | 505 | **KMeans clustering** on EOD features → BullTrend/BearTrend/Choppy labels |
| `scripts/train_daytype_classifier.py` | 452 | **Logistic regression + LightGBM** training on checkpoint features |
| `scripts/evaluate_intraday_prediction.py` | 329 | Evaluation report + combined prediction CSV |

These three form the **training pipeline**. Without them, models cannot be retrained
from scratch.

---

## 2. What D:\BOT\root Has — The Complete Verified Pipeline

### Training data (2023–2026, 746 days)

All in `D:\BOT\root\data\features\day_type\`:

| File | Purpose |
|------|---------|
| `nifty_day_features_{2023..2026}.csv` | EOD features — input to clustering |
| `intraday_features_{10am,11am,13pm}.csv` | Checkpoint features — input to classifier |
| `cluster_labels.csv` | Output of clustering — ground truth for classifier |

### Pipeline flow

```
nifty_day_features_*.csv        intraday_features_*.csv
        │                                  │
        ▼                                  │
cluster_day_types.py                        │
  ├─ Prune degenerate cols                  │
  ├─ Winsorize (1%/99%)                    │
  ├─ StandardScaler                         │
  ├─ PCA (87% variance)                     │
  ├─ KMeans k=3 (auto-selected)             │
  │   ├─ Seed stability: ARI 0.981          │
  │   └─ Subperiod stability: 0.892         │
  └─ Output: cluster_labels.csv  ◄──────────┘
                      │
                      ▼
train_daytype_classifier.py
  ├─ Load intraday_features_{cp}.csv + cluster_labels
  ├─ Train/Val/Holdout split (2023-24 / 2025 / 2026)
  ├─ Winsorize + StandardScaler
  ├─ LogisticRegression (C=1.0, balanced)
  ├─ LightGBM (ceiling only)
  └─ Save: model.pkl + scaler.pkl + metadata.json
                      │
                      ▼
evaluate_intraday_prediction.py
  ├─ Accuracy by checkpoint, confidence tier, cluster, year
  ├─ Confusion matrices
  ├─ Flip rate between checkpoints
  └─ Combined predictions CSV
```

### Verified accuracy — logistic_13pm_prod (Block A excluded)

| Split | n | Overall | BearTrend | BullTrend | Choppy |
|-------|---|---------|-----------|-----------|--------|
| Train (2023-24) | 712 | 75.56% | 78.68% | 80.67% | 68.95% |
| Val (2025) | 30 | 80.00% | 72.73% | 66.67% | 92.31% |
| Holdout (2026) | — | 80.00% | — | — | — |

LightGBM overfits severely: Train 93.33% → Val 68.83%, confirming that the low-n regime
is better served by the simpler model.

### NiftyShield paper trades (D:\bot\root only)

- `trading.db` → `ns_paper_signals`: **540 rows**
- `trading.db` → `ns_paper_trades`: **513 completed trades**
- Session logs in `logs/sessions/` (Jan–Feb 2026)
- Backtest: 400 trades across 4 walk-forward windows, 97.5% WR, Sharpe 9.40 — but
  **synthetic flat-IV pricing**, explicitly not platform evidence

### Other models (not relevant to NiftyShield)

D:\bot\root has 11 additional model directories for stock-level 10am classifiers,
stock 9:30am classifiers, and universal stock clustering — none used by NiftyShield.

---

## 3. New Data Available

### 3.1 Intraday Nifty + BankNifty — 2012-01-02 → 2023-01-31

| File | Rows (excl header) | Trading days | Avg bars/day | Min/Max bars |
|------|--------------------|-------------|-------------|-------------|
| `data/reference/NIFTY_2012-2023.csv.zip` | 1,027,960 | 2,723 | 378 | 61 / 750 |
| `data/reference/BNF_2012-2023.csv.zip` | 1,035,565 | 2,723 | 380 | 61 / 756 |

- **Date overlap: 2,723/2,723 — perfect.** Zero dates with Nifty-only or BNF-only.
- **Format:** 1-minute OHLC, no volume. Columns: `Stock,Date,Time,Open,High,Low,Close`
- **Timespan:** 2012-01-02 to 2023-01-31 — bridges perfectly with F:\Nifty's existing
  DuckDB 1m data which starts 2023-01-02.
- **Quality:** ~10 dates in July 2016 have 750 bars (double the expected ~375) —
  these are likely sub-minute ticks and need resampling to 1m. The minimum of 61 bars
  suggests some half-day/muhurat sessions. Both are straightforward to handle.
- **Volume:** Not provided, but irrelevant — index volume is always 0 on NSE feeds
  and the production 13pm model excludes the volume block entirely.

### 3.2 Nifty Options Chain — 2025 → July 2026 (1-minute)

Kept in a **separate location outside F:\Nifty** deliberately — this is the sealed
forward-validation data. It must NOT be touched during training. It serves as the
out-of-sample P&L validation surface for the strategy after the model is retrained.

**Sealed-window discipline:** This data must never be read during any step of the
clustering, feature building, or classifier training pipeline. It is the forward
test — the 2023→present window that the RFA/PSB protocols protect.

### 3.3 Existing F:\Nifty 1m Data — 2023-01-02 → present

The DuckDB 1m store in `data/market_data/nse/candles/1m/` covers Nifty 50 and
Bank Nifty from 2023-01-02 onward. This is the same calendar window D:\bot\root's
models were trained on, from a different data vendor.

---

## 4. Training Window — Before vs After

| | D:\bot\root (old) | F:\Nifty (new, with reference data) |
|---|---|---|
| **EOD feature window** | 2023–2026 (~4 years) | **2012–2026 (~14 years)** |
| **Intraday feature window** | 2023–2026 (~4 years) | **2012–2026 (~14 years)** |
| **Classifier train split** | 712 days (2023-24) | **~2,500+ days (e.g., 2012-22)** |
| **Classifier val split** | 30 days (2025) | **~250 days (2023)** |
| **Classifier holdout split** | ~30 days (2026) | **~220+ days (2024)** |
| **Regime coverage** | Post-COVID only | **Full cycle: 2013 taper, 2014-15 bull, 2016 demo, 2018 IL&FS, 2020 COVID, 2021-22 recovery** |
| **Cluster stability test** | 2023-24 vs 2025-26 | **Multiple subperiods across 14 years** |

### Why this matters

The old model was trained on a single volatility regime (post-COVID 2023-24). A
classifier that has never seen a 10% gap-down or a 2018-style slow bleed cannot be
expected to classify those days correctly. The 11-year reference data contains every
meaningful Indian market regime.

The Choppy class is the weak link in the current model (68.95% train accuracy vs
78-80% for directional classes). More diverse training data should improve
discrimination between genuine chop and weak trends.

---

## 5. What Needs to Happen — Training Plan

### Phase 1: Data ingestion

1. **Convert reference CSVs to DuckDB** — parse `NIFTY_2012-2023.csv` and
   `BNF_2012-2023.csv` into the existing per-date DuckDB 1m format
   (`data/market_data/nse/candles/1m/{date}.duckdb`).
   - Resample sub-minute ticks (2016-07 dates) to 1m
   - Handle half-day sessions (min 61 bars) — flag or pad to expected bar range
   - Validate continuity at the 2023-01-31 → 2023-01-02 bridge with existing data

2. **Build EOD features** for the full 2012–2026 span using
   `core/analytics/day_features.py` → output to `data/features/day_type/`.

3. **Build intraday checkpoint features** using `scripts/build_intraday_features.py`
   for the full span → output to `data/features/day_type/intraday_features_*.csv`.

### Phase 2: Port training scripts from D:\bot\root

Copy and adapt from `D:\BOT\root\scripts\` to `F:\Nifty\scripts\daytype\`:

| Source | Destination | Changes needed |
|--------|-------------|----------------|
| `cluster_day_types.py` | `scripts/daytype/cluster_day_types.py` | Paths, year list → `.duckdb` reader instead of CSV |
| `train_daytype_classifier.py` | `scripts/daytype/train_daytype_classifier.py` | Paths, split years, `--no-block-a` flag |
| `evaluate_intraday_prediction.py` | `scripts/daytype/evaluate_intraday_prediction.py` | Paths |

### Phase 3: Cluster on extended window

Run `cluster_day_types.py` on 2012–2026 EOD features:
- Verify the auto-selected k=3 still holds on the wider window
- Verify seed stability and subperiod stability
- Inspect centroid profiles for semantic consistency with the old labels
- Auto-map clusters to BullTrend/BearTrend/Choppy by centroid z-scores

### Phase 4: Train classifier

Train logistic regression (and LightGBM ceiling) on the extended intraday features:
- Train: 2012–2022 (~2,500 days)
- Val: 2023 (~250 days)  
- Holdout: 2024 (~250 days)
- Compare accuracy against the old model's baseline (75.56% train / 80% val)
- Produce `logistic_13pm_prod` model with `--no-block-a`

**Expected range from the old docs:** 13pm logistic should land 75–85%. With ~3.5x
more training data spanning multiple regimes, the Choppy class should improve and
holdout stability should be stronger. But the ceiling is structural — a 3-class
classifier on partial-day features cannot reach much above ~85%.

### Phase 5: Validate against old model

Before replacing the production model:
1. Run both models (old + new) over the same 2023–2026 period
2. Compare regime assignments — how often do they disagree?
3. If disagreement >20%, investigate which one is right by checking
   the actual full-day outcomes
4. Run the NiftyShield conformance suite with the new model — the 16-signal
   stream will differ (expected), but the guard wrap conformance must still PASS
5. Re-run the strategy over the **options chain forward-validation data**
   (kept in a separate location) with both models and compare net P&L

### Phase 6: Replace and re-certify

If the new model passes validation:
1. Replace `models/daytype/logistic_13pm_prod/` artifacts
2. Update `trained_on` in `scripts/daytype/publish_facts.py` from
   `"D:\BOT\root vintage -- NOT F:\nifty data"` to the new provenance string
3. Re-publish facts for the full historical window
4. Re-run the NiftyShield conformance suite — the `code_ref` changes but
   `strategy_id` + `config_hash` are unchanged → E006-style re-certification
5. Bump `model_hash` and `regime_fact_version` in the facts schema

---

## 6. What Does NOT Change

- **Strategy identity** — `nifty_shield_v1`, `config_hash` unchanged
- **Strategy logic** — same structures, same VIX gates, same sizing
- **DayType engine** — same `DayTypeEngine`, same feature computation, same
  checkpoint timing
- **Conformance contract** — the 16-signal stream will differ (different model →
  different regime → different structures) but the guard-wrapped conformance
  tests the *contract*, not the model's output

---

## 7. Risks

| Risk | Mitigation |
|------|-----------|
| Reference data quality differs from Upstox feed | Compare overlapping period (2023-01) between reference CSV and existing DuckDB — if OHLC differs systematically, note the vendor as a caveat |
| k=3 doesn't hold on 14-year window | The old pipeline is designed to auto-select k — if k=4 or k=5 emerges as more stable, that changes the classification scheme NiftyShield depends on. Requires operator sign-off before proceeding |
| New model is worse than old on the forward-validation window | This is the point of the validation — if it loses, keep the old model and document why. The provenance cleanup is not worth a worse model |
| Sealed window leakage | The options chain data must stay in its separate location. No analysis script may read it until Phase 5 validation |

---

## 8. Files Referenced

| File | Location |
|------|----------|
| DayType adoption spec (DT1 decision) | `docs/reports/DAYTYPE_FACTS_ADOPTION_SPEC.md` |
| Strategy promotion ledger (E005 caveat) | `docs/STRATEGY_PROMOTION_LEDGER.md` |
| NiftyShield datasheet | `docs/strategies/nifty_shield_v1/datasheet.md` |
| Reference Nifty 1m data | `data/reference/NIFTY_2012-2023.csv.zip` |
| Reference BankNifty 1m data | `data/reference/BNF_2012-2023.csv.zip` |
| Options chain forward-validation data | **Separate location — not in F:\Nifty** |
| Existing 1m DuckDB store | `data/market_data/nse/candles/1m/` |
| Existing model artifacts | `models/daytype/logistic_13pm_prod/` |
| DayType engine | `core/state/daytype_engine.py` |
| EOD feature library | `core/analytics/day_features.py` |
| Intraday feature builder (ported) | `scripts/build_intraday_features.py` |
| Clustering script (D:\bot\root) | `D:\BOT\root\scripts\cluster_day_types.py` |
| Classifier training (D:\bot\root) | `D:\BOT\root\scripts\train_daytype_classifier.py` |
| Evaluation script (D:\bot\root) | `D:\BOT\root\scripts\evaluate_intraday_prediction.py` |
| NiftyShield paper trades (D:\bot\root) | `D:\BOT\root\trading.db` → `ns_paper_signals` / `ns_paper_trades` |
| NiftyShield backtest (D:\bot\root) | `D:\BOT\root\scripts\nifty_shield_backtest.py` |
