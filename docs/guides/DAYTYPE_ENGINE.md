# DayType engine — the regime NiftyShield trades on

The DayType engine (`core/state/daytype_engine.py`) labels a Nifty 50 session
**BullTrend**, **BearTrend** or **Choppy** from that session's own intraday bars.
NiftyShield reads the label at 13:00 to choose its structure. The engine is
deterministic: the same bars, models and library versions produce the same fact.

## How a label is made

**Offline, once (already done; the result ships in the repo):**

1. `scripts/daytype/build_eod_features.py`: whole-session shape features for every
   Nifty session 2012 → 2025 (return, range, close location, trend and TWAP
   statistics, flip counts and similar).
2. `scripts/daytype/cluster_day_types.py`: PCA + **KMeans (k = 3)** over those
   features. The clusters are named Choppy (0), BullTrend (1) and BearTrend (2). These are the **labels**. They describe the full 09:15–15:29 session.
3. `scripts/daytype/train_daytype_classifier.py`: a classifier per checkpoint
   (10am / 11am / 13pm) learns to predict the full-session label from the **partial**
   session up to that checkpoint. Trained through 2023, validated 2024, held out 2025.

**Live, every session at 13:00** (`scripts/daytype/publish_live_fact.py`):

1. Read today's Nifty 50, Bank Nifty and India VIX 1m bars up to 13:00, from the
   per-day 1m store if it exists, else the ingestor's live buffer
   (`data/live_buffer/candles_today.duckdb`). At least **100** bars are required, or
   the fact is "not ready" and NiftyShield skips the session.
2. Compute the **38 production features**: 32 Nifty partial-session features (opening
   5/15/30-minute returns and range, TWAP crosses and lean, linear-trend slope and r²,
   higher-high/lower-low counts, partial realized vol and ATR, and similar) plus 6
   Bank Nifty-vs-Nifty intermarket features (spreads, 5-minute correlation, which leads).
3. Score with `models/daytype/logistic_13pm_prod/` (scaler + logistic regression).
4. Take India VIX at 13:00 and its **percentile in the trailing 756 sessions**
   (`scripts/daytype/vix_percentile.py`).
5. Upsert one row into `data/features/day_type/day_type_facts.duckdb`
   (`day_type_facts`): regime, confidence, `vix_at_checkpoint`, `vix_pctile`, model
   hash, fact version, commit.

## Back data it needs

| Data | Needed for | Shipped? | How a fresh clone gets it |
|---|---|---|---|
| Trained models (`models/daytype/*`) | scoring | **yes, committed** | nothing to do |
| Today's Nifty / Bank Nifty / India VIX 1m bars (09:15–13:00) | features + VIX at 13:00 | no (live) | market ingestor, started by the orchestrator |
| India VIX **daily closes**, ≥ 189 sessions (756 ideal, ~3 years) | VIX percentile → NiftyShield's Choppy-branch structure | no | `python scripts/bootstrap.py seed` (Upstox daily candles → `data/market_data/nse/candles/1d/` → `data/nifty_shield/vix_history.duckdb`); the trading-profile orchestrator re-runs it each morning |
| EOD feature CSVs (`data/features/day_type/nifty_day_features_*.csv`) | "Block A" previous-day/gap features | no | **not needed.** The 13pm production model excludes Block A (`block_a_excluded: true`). The 10am/11am models are not used by NiftyShield |
| 2012 → present Nifty 1m history | **retraining only** | no | not in this repo, and Upstox's 1m history does not reach back that far. Use the committed models |

**The silent failure to avoid.** With fewer than 189 VIX closes the percentile is
`None`. Nothing errors: NiftyShield takes its calmest Choppy branch and trades a
**short straddle** every Choppy day, never the iron fly or strangle. Run
`bootstrap.py seed` before the first session and check:

```bash
python -c "import duckdb; print(duckdb.connect('data/nifty_shield/vix_history.duckdb', read_only=True).sql('select count(*), min(session_date), max(session_date) from vix_history'))"
```

## What the label is, and is not

- Out-of-sample accuracy of the 13pm production model against the full-session
  label: **70.7 %** (2024 validation, n = 246) and **70.6 %** (2025 holdout, n = 248).
  The KMeans labels were fitted on 2012–2025, which includes those years. That is an
  optimism channel, disclosed in the model metadata.
- It is a **full-session directional prior**. It is not a forecast of the
  13:00–15:35 window NiftyShield holds. What the evidence supports is a
  Bull-minus-Bear forward-window return separation of **+0.255 pp**
  (95 % CI +0.197…+0.312, n = 1,606 out-of-sample sessions).
- `regime_confidence` is confidence in the full-session class, not a probability
  about the afternoon. Do not build thresholds or sizing on it as if it were.

Details: `docs/reports/index_research/DAYTYPE_HORIZON_DISCLOSURE.md`,
`docs/reports/strategies/DAYTYPE_FACTS_ADOPTION_SPEC.md`,
`docs/lessons_learned/daytype_and_microstructure.md`.

## Version coupling

The models are pickles. `scikit-learn==1.8.0`, `lightgbm==4.7.0` and `scipy` are
pinned in `requirements.txt` because a different library version can change the
fact without changing any hash. The engine logs `MODEL VERSION SKEW` when it can
detect a mismatch.
