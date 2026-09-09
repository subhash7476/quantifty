# NiftyShield Model Retrain — Audit Report

**Branch:** `feat/niftyshield-model-retrain`  
**Date:** 2026-08-10  
**Status:** PHASE 1 — discovery and tooling complete; training not yet executed  
**Audience:** Operator / auditor — designed for someone who has not followed the chat

---

## 1. Background — Why This Exists

NiftyShield (`nifty_shield_v1`) is a regime-adaptive weekly Nifty options premium
seller, adopted from the retired `D:\BOT\root` platform via the MM12.5 promotion
pipeline. It is currently at **Stage 2 PAPER VALIDATED (E007 open)** — the harness
is built but zero live paper sessions have run.

The DayType regime classifier models that NiftyShield depends on were copied as `.pkl`
files from `D:\BOT\root` during the SALVAGE migration and **never trained on
`F:\Nifty` data**. Every fact row in `day_type_facts.duckdb` carries:

```
trained_on = "D:\BOT\root vintage -- NOT F:\nifty data"
```

The assessment report filed earlier in this branch
(`docs/reports/NIFTY_SHIELD_MODEL_RETRAIN_ASSESSMENT.md`) documented what exists,
what's missing, and what new data is available. This audit report covers everything
done since then and provides the current state for review.

---

## 2. Discovery — What D:\BOT\root Contains

### 2.1 The Complete Training Pipeline (3 scripts, not ported)

| Script | Lines | Purpose |
|--------|-------|---------|
| `D:\BOT\root\scripts\cluster_day_types.py` | 505 | Unsupervised KMeans clustering on EOD features → BullTrend/BearTrend/Choppy labels |
| `D:\BOT\root\scripts\train_daytype_classifier.py` | 452 | Logistic regression + LightGBM training on checkpoint intraday features |
| `D:\BOT\root\scripts\evaluate_intraday_prediction.py` | 329 | Confusion matrices, confidence calibration, year-by-year accuracy |

The pipeline flow:

```
EOD features (nifty_day_features_*.csv)
  → cluster_day_types.py (PCA + KMeans k=3)
    → cluster_labels.csv
      → train_daytype_classifier.py (LogisticRegression, Train/Val/Holdout)
        → model.pkl + scaler.pkl + metadata.json
          → evaluate_intraday_prediction.py
```

### 2.2 Verified Accuracy — Production Model (logistic_13pm_prod)

| Split | n | Overall | BearTrend | BullTrend | Choppy |
|-------|---|---------|-----------|-----------|--------|
| Train (2023-24) | 712 | 75.56% | 78.68% | 80.67% | 68.95% |
| Val (2025) | 30 | 80.00% | 72.73% | 66.67% | 92.31% |
| Holdout (2026) | — | 80.00% | — | — | — |

Source: `D:\BOT\root\models\daytype\logistic_13pm_prod\metadata.json`, reproduced
from the training script output. The Block A exclusion (gap/prev-day features)
improved holdout accuracy by +6.7% over the full-feature version.

LightGBM overfits (Train 93.33% → Val 68.83%), confirming logistic is the correct
model choice for this sample size.

### 2.3 NiftyShield Paper Trades

In `D:\BOT\root\trading.db`:
- `ns_paper_signals`: **540 rows** (one per trading day)
- `ns_paper_trades`: **513 completed trades**
- Session logs in `logs/sessions/` (Jan–Feb 2026)

Walk-forward backtest (`D:\BOT\root\scripts\nifty_shield_backtest.py`):
- 400 trades, 97.5% WR, Sharpe 9.40, Rs +26.3L net
- **Caveat: synthetic flat-IV Black-76 pricing — "optimistic & unvalidated" per the repo's own docs**

### 2.4 Other Model Directories (not relevant to NiftyShield)

D:\bot\root has 11 additional model directories for stock-level classifiers
(`stock_1000am`, `stock_930am`, `universal_stocks`) — none consumed by NiftyShield.

---

## 3. New Data Available

### 3.1 Intraday Nifty + BankNifty — 2012-01-02 to 2023-01-31

Files placed at `F:\Nifty\data\reference\`:

| File | Rows | Trading days | Avg bars/day | Range |
|------|------|-------------|-------------|-------|
| `NIFTY_2012-2023.csv.zip` (11 MB) | 1,027,960 | 2,723 | 378 | 61–750 |
| `BNF_2012-2023.csv.zip` (12 MB) | 1,035,565 | 2,723 | 380 | 61–756 |

- **Date overlap: 2,723/2,723 — perfect.** Every date has both Nifty and BankNifty.
- **Format:** 1-minute OHLC, no volume. `Stock,Date,Time,Open,High,Low,Close`
- **Gap:** Data ends 2023-01-31, existing `F:\Nifty` DuckDB 1m data starts 2023-01-02 — one month of overlap for vendor-bridge validation.
- **Quality flag:** ~10 dates in July 2016 have 750 bars (double the expected ~375) — likely tick-level data that needs resampling to 1m before use.
- **Volume:** Not provided — irrelevant for index data (volume is always 0 on NSE feeds).

### 3.2 Existing F:\Nifty 1m DuckDB Store

`data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`:
- **893 files**, 2023-01-02 to 2026-08-07
- Nifty 50 + Bank Nifty + India VIX
- Same calendar window the old models were trained on, from a different data vendor (Upstox)

### 3.3 Nifty Options Chain — 2025 to July 2026 (1-minute)

Kept in a **separate location outside `F:\Nifty`** — the sealed forward-validation surface.

Verified format from sample data provided by operator:

| Column | Description |
|--------|------------|
| `timestamp` | UTC+0, 1-minute resolution |
| `expiry_code` | 1–3 (3 nearest weekly expiries) |
| `strike_relative` | ATM, ATM±1 through ATM±10 |
| `option_type` | CE / PE |
| `open, high, low, close` | OHLC per bar |
| `iv` | Implied volatility |
| `volume` | Contract volume |
| `strike_price` | Absolute strike in rupees |
| `oi` | Open interest |
| `spot_price` | Nifty spot at each timestamp |
| `from_date, to_date` | Expiry window |

21 strike buckets at 50-pt Nifty intervals (±10 strikes = ±500 pts), covering all
structure legs: directional wings (150 pts), iron fly wings (100 pts), strangle OTM
(50 pts).

---

## 4. What Was Built in This Branch

### 4.1 Assessment Report

`docs/reports/NIFTY_SHIELD_MODEL_RETRAIN_ASSESSMENT.md` (334 lines, committed)

Covers:
- Current state of models in F:\Nifty (what's ported, what's missing)
- Full D:\bot\root pipeline documentation
- Training window comparison (old 712 days vs new ~2,800 days)
- 6-phase training plan with data ingestion, script port, clustering, classifier
  training, validation, and model replacement
- Risk register

### 4.2 EOD Feature Builder

`scripts/daytype/build_eod_features.py` (~90 lines, uncommitted)

Computes per-session EOD features from the existing 1m DuckDB store using
`core/analytics/day_features.py`. Built and executed — output verified:

| File | Rows | Size |
|------|------|------|
| `data/features/day_type/nifty_day_features_2023.csv` | 223 | 182 KB |
| `data/features/day_type/nifty_day_features_2024.csv` | 248 | 202 KB |
| `data/features/day_type/nifty_day_features_2025.csv` | 249 | 203 KB |
| `data/features/day_type/nifty_day_features_2026.csv` | 147 | 120 KB |

867 sessions processed, 26 skipped (missing/incomplete bar data). Each row has 59
columns (53 engineered features + 6 internal columns dropped during finalization).
These CSVs are the input to `cluster_day_types.py` for regime label generation.

**Block A gap features** are computed post-hoc using `block_a_gap_context()` —
gap is derived from previous session's close vs current session's open, from the
same OHLC data. Rolling percentile features (`gap_size_pct60`, `prev_day_vol_pct`,
`partial_vol_pct20`) are computed by `finalize_dataframe()` across the full panel.

### 4.3 Sealed Validation Harness

`scripts/nifty_shield_paper/sealed_harness.py` (~580 lines, uncommitted)

A self-contained Python script designed to run **outside F:\Nifty** in a sealed
folder. It reads raw 1m bars + options chain CSVs and produces a trade log +
summary — no live feeds, no API calls, no DuckDB outside the bar store.

**Architecture:**

```
sealed_validation/
├── run.py                         # The harness (copy of sealed_harness.py)
├── core/                          # Bundled engine — copied from F:\Nifty
│   ├── state/daytype_engine.py    # Auto-resolves ROOT to sealed folder root
│   └── analytics/{day_features,resampler}.py
├── models/logistic_13pm_prod/     # model.pkl + scaler.pkl + metadata.json
├── bars/{YYYY-MM-DD}.duckdb       # 1m Nifty + BankNifty (read-only)
├── options/*.csv                  # Options chain CSVs (read-only)
└── output/                        # Generated: trade_list.csv + summary.json
```

**Simulation flow per session:**
1. Load 1m Nifty + BNF bars from DuckDB, run `DayTypeEngine.on_bar()` / `on_bn_bar()`
2. Engine processes bars up to 15:30, triggers checkpoints (10am/11am/13pm)
3. At session end, read final locked state → regime + confidence
4. Load options chain CSV, slice at 13:00 IST (= 07:30 UTC in the timestamp column)
5. Find ATM strike → nearest to `spot_price` at 13:00
6. Use ATM CE IV as VIX gate proxy
7. Select structure: regime + VIX → bull_put_spread / bear_call_spread / short_strangle / iron_fly / short_straddle
8. Resolve leg strikes at 50-pt intervals from `strike_price` column
9. Record entry prices at 13:00 `close`
10. Walk 13:01→15:15 minute-by-minute, marking each leg to `close` price
11. Exit triggers: TP ≥ 50% credit, SL ≤ −2× credit, or 15:15 hard exit
12. Write trade row to `trade_list.csv`

**Output files:**
- `trade_list.csv` — date, regime, confidence, vix, structure, ATM, net_credit,
  entry/exit time, exit_reason, pnl_pts, pnl_rs, leg details
- `summary.json` — total trades, total P&L, mean P&L, Sharpe (from daily PnL × √252),
  max drawdown, win rate, breakdowns by regime/structure/exit_reason, skipped
  session counts

**Known limitations (disclosed in script comments):**
- No delta flattening exit (Greeks not included in options CSVs)
- ATM CE IV used as VIX proxy (not actual India VIX index)
- Expiry code 1 assumed to be nearest weekly expiry
- No bid/ask spread or slippage — `close` price used for both entry and exit
- Lot sizing is cosmetic (strategy-level per-contract P&L, not portfolio-level)
- Block A EOD features not needed (13pm_prod has `block_a_excluded: true`)

---

## 5. Training Plan — What Has NOT Been Done Yet

### Phase 1: Data ingestion (not started)
- Parse `NIFTY_2012-2023.csv` and `BNF_2012-2023.csv` into per-date DuckDB files
  matching the existing `{YYYY-MM-DD}.duckdb` schema
- Resample July 2016 sub-minute ticks to 1m
- Validate continuity at the 2023-01-31 ↛ 2023-01-02 bridge

### Phase 2: Port training scripts (not started)
Copy `cluster_day_types.py`, `train_daytype_classifier.py`, `evaluate_intraday_prediction.py`
from `D:\BOT\root\scripts\` to `F:\Nifty\scripts\daytype\` with path adjustments.

### Phase 3: Build intraday features (not started)
Run `scripts/build_intraday_features.py` over the extended 2012-2025 date range
to produce `intraday_features_{10am,11am,13pm}.csv`.

### Phase 4: Cluster + Train + Evaluate (not started)

| Step | Script | Key parameters |
|------|--------|---------------|
| Clustering | `cluster_day_types.py` | EOD features 2012-2023 or 2012-2025 (TBD) |
| Training | `train_daytype_classifier.py` | `--checkpoint 13pm --train-thru 2023 --no-block-a --model-name logistic_13pm_prod` |
| Evaluation | `evaluate_intraday_prediction.py` | `--split all` |

**Training splits:**

| Split | Years | ~Days | Purpose |
|-------|-------|-------|---------|
| Train | 2012–2023 | ~2,800 | Logistic regression |
| Val | 2024 | ~250 | Hyperparameter selection |
| Holdout | 2025 | ~250 | Accuracy check — same year as forward P&L validation |

### Phase 5: Validate against old model (not started)
- Compare regime assignments old vs new on 2023-2026 data
- Run NiftyShield conformance suite with new model
- Run sealed harness with both models over options chain data, compare net P&L

### Phase 6: Replace and re-certify (not started)
- Replace `models/daytype/logistic_13pm_prod/` artifacts
- Update `TRAINED_ON` provenance string
- Re-publish historical facts
- Re-run conformance suite → `code_ref` bump, `strategy_id` + `config_hash` unchanged

---

## 6. Key Decisions — Auditor Should Verify

| # | Decision | Where |
|---|----------|-------|
| D1 | Training split: 2012-2023 train, 2024 val, 2025 holdout | Assessment §4 |
| D2 | Clustering window: 2012-2023 (purist, zero label leakage) OR 2012-2025 (old-pipeline style, more stable clusters). Not yet decided. | Assessment §5 Phase 3 |
| D3 | Sealed harness uses ATM CE IV as VIX proxy for the >20 skip gate. Actual India VIX is not in the options chain CSV. | Sealed harness (disclosed in script comments) |
| D4 | Sealed harness assumes expiry_code=1 is nearest weekly. Unverified against NSE expiry calendar. | Sealed harness |
| D5 | Sealed harness uses `close` price for both entry and exit. No bid/ask spread, no slippage. Real execution will differ. | Sealed harness |
| D6 | Block A exclusion (`--no-block-a`) on 13pm model — same ablation as the production model from D:\bot\root. Retrain uses identical flag. | Training script design |
| D7 | Options chain forward-validation data must remain in its separate location. No training script may read it. 2026 portion is truly unread. | Assessment §3.2, §7 |
| D8 | If new model performs worse than old on forward validation, keep old model. Provenance cleanup is not worth a worse strategy. | Assessment §7 |

---

## 7. Files in This Branch

### Committed

| File | Purpose |
|------|---------|
| `docs/reports/NIFTY_SHIELD_MODEL_RETRAIN_ASSESSMENT.md` | Phase 1 assessment: models, data, training plan |

### Uncommitted (work in progress)

| File | Purpose | Status |
|------|---------|--------|
| `scripts/daytype/build_eod_features.py` | Builds EOD feature CSVs from 1m DuckDB | **Built and executed** — CSVs in `data/features/day_type/` |
| `scripts/nifty_shield_paper/sealed_harness.py` | Self-contained sealed validation harness | **Written, not yet tested** — needs options chain CSV for dry run |

### Generated (not tracked)

| File | Purpose |
|------|---------|
| `data/features/day_type/nifty_day_features_2023.csv` | 223 rows, EOD features |
| `data/features/day_type/nifty_day_features_2024.csv` | 248 rows, EOD features |
| `data/features/day_type/nifty_day_features_2025.csv` | 249 rows, EOD features |
| `data/features/day_type/nifty_day_features_2026.csv` | 147 rows, EOD features |

### Not in F:\Nifty (external reference only)

| Location | Content |
|----------|---------|
| `D:\BOT\root\scripts\cluster_day_types.py` | Clustering pipeline |
| `D:\BOT\root\scripts\train_daytype_classifier.py` | Classifier trainer |
| `D:\BOT\root\scripts\evaluate_intraday_prediction.py` | Evaluation script |
| `D:\BOT\root\trading.db` | NiftyShield paper trades (540 signals / 513 trades) |
| `F:\Nifty\data\reference\NIFTY_2012-2023.csv.zip` | 1m Nifty 2012-2023 |
| `F:\Nifty\data\reference\BNF_2012-2023.csv.zip` | 1m BankNifty 2012-2023 |
| Separate location (operator-managed) | Nifty options chain 1m 2025–Jul 2026 |
