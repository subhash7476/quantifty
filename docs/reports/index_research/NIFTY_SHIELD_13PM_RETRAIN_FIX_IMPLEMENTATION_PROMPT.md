# Implementation Prompt — 13pm Train/Serve Skew Fix + EOD Loader Fix

**Branch:** `feat/niftyshield-model-retrain`
**Implementer:** DeepSeek V4
**Reviewer:** Claude (parity gate is the acceptance criterion)
**Context:** `docs/reports/NIFTY_SHIELD_RETRAIN_BLOCKER_FINDINGS.md`

The retrained `logistic_13pm_prod` model is trained on 3 features the engine serves as
0.0 at inference, so the deployed regime stream differs from the validated one on ~13% of
days. This prompt fixes that (Option A: retrain without the orphan features so trained ==
served) and the related EOD-loader crash. **Do not edit the certified `DayTypeEngine`** —
fixes are on the training/data side only.

---

## Task 1 — DONE (do not redo)

`split_data` holdout already pinned to `year == train_thru + 2`
(`scripts/daytype/train_daytype_classifier.py`). The retrain below runs with this in place.

## Task 2 — Fix EOD-context loader crash (Finding 2)

`core/analytics`/`build_eod_features.py` writes `nifty_day_features_{yr}.csv` with an
**unnamed index**, but `DayTypeEngine._load_eod_context()` reads `index_col='date'` →
`ValueError: 'date' is not in list` on engine construction.

- Fix on the **writer side** (no certified-code edit): set the index name to `date` before
  `to_csv` (or pass `index_label='date'`) in `scripts/daytype/build_eod_features.py`.
- Regenerate all `nifty_day_features_{2012..2026}.csv`.
- **Verify:** `DayTypeEngine(model_name="logistic")` constructs without error with those CSVs
  present, and `engine._eod_df is not None` with a `DatetimeIndex`.

This also fixes 10am/11am, which depend on this context for real Block A values.

## Task 3 — Retrain 13pm without the 3 orphan features (Finding 1, Option A)

The engine never provides these to the 13pm model (it skips `_inject_block_a` when
`block_a_excluded=True`): `prev_day_vol_pct`, `partial_vol_pct20`, `partial_range_pct20`.

- Add these three to the drop path for the `--no-block-a` 13pm training so they are **absent
  from the model's `feature_names`**. (Simplest: extend `BLOCK_A_FEATURES` handling, or add a
  dedicated `ENGINE_UNAVAILABLE_WHEN_BLOCK_A_EXCLUDED` drop set applied when `no_block_a`.)
- Retrain: `--checkpoint 13pm --train-thru 2023 --no-block-a --model-name logistic_13pm_prod`.
- Splits must be Train 2012–2023, Val 2024, Holdout 2025 (verify n ≈ 2907 / 246 / 248).
- Report the new Train/Val/Holdout accuracy. Expect ≈ 69–72% (the 3 features were weak;
  aggregate accuracy should be within ~1pp of the prior CSV numbers).

## Task 4 — ACCEPTANCE GATE: full engine↔CSV feature parity (mandatory)

This is the gate. The retrain is not accepted until it passes.

- For a sample of **≥ 20 sessions across 2024–2025**, compare, feature-by-feature, the
  13pm feature vector produced by `DayTypeEngine._compute_features('13pm')` (fed the 1m
  DuckDB bars, session-filtered 09:15–15:29) against the corresponding row of
  `data/features/day_type/intraday_features_13pm.csv`, restricted to the model's final
  `feature_names`.
- **PASS = every feature in `feature_names` matches within 1e-6 on every sampled session**
  (no feature served as 0.0 that the CSV has nonzero, no residual skew).
- Also report the **deployed** holdout accuracy: run the engine over all 2025 sessions,
  take the acted-on regime (the locked/last state as the harness does), and score against
  the 2025 `cluster_id` labels. This is the honest headline number for the datasheet.
- Write results to `docs/reports/NIFTY_SHIELD_DAYTYPE_PARITY_REPORT.md`.

## Out of scope

- No `DayTypeEngine` edits (certified). No sealed-window data access. No facts republish /
  re-cert yet (that is Phase 6, after the sealed run). 10am/11am models are not retrained —
  Task 2 alone makes them consistent; confirm parity for them opportunistically but they are
  not gating (NiftyShield consumes the 13pm regime).

## Hand-back

Report: new 13pm metadata (feature_names without the 3), Train/Val/Holdout accuracy, the
parity report path with PASS/FAIL, and the deployed 2025 accuracy. On PASS, Claude assembles
the sealed bundle against the corrected model.
