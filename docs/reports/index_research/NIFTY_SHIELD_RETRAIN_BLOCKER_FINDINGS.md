# NiftyShield Retrain — Blocker Findings (pre-bundle)

**Branch:** `feat/niftyshield-model-retrain`
**Date:** 2026-08-11
**Status:** Task 1 done (holdout guard). **Task 2 (sealed bundle) HALTED** pending operator decision on Finding 1.

While preparing the sealed validation bundle, a parity check surfaced a train/serve
skew in the retrained `logistic_13pm_prod` model. Building the bundle on top of it
would forward-test a model whose deployed regime stream differs from the validated one.
Details, quantified severity, and remediation options below.

---

## Finding 1 (BLOCKER) — 13pm model trains on 3 features the engine serves as 0.0

`logistic_13pm_prod` (`block_a_excluded: true`) lists these in `feature_names` and was
fit on their real values, but `DayTypeEngine` never provides them at inference:

| Feature | In model? | Training values | Engine at inference |
|---|---|---|---|
| `prev_day_vol_pct` | yes | nonzero 93.1% of rows, mean 0.484 | **0.0 always** |
| `partial_vol_pct20` | yes | nonzero 92.7%, mean 0.482 | **0.0 always** |
| `partial_range_pct20` | yes | nonzero 93.7%, mean 0.493 | **0.0 always** |

### Root cause — two definitions of "Block A" drifted apart

- **Training** `BLOCK_A_FEATURES` (`train_daytype_classifier.py:62`), the set `--no-block-a`
  drops, is **7 columns** and does **not** include `prev_day_vol_pct`; it never touches
  `partial_vol_pct20` / `partial_range_pct20`. So the 13pm model is trained **with** all three.
- **Engine** `BLOCK_A_COLS` (`daytype_engine.py:109`) is those 7 **plus `prev_day_vol_pct`**,
  and the engine gates the whole `_inject_block_a()` method on `block_a_excluded`. That method
  is *also* where `partial_vol_pct20` / `partial_range_pct20` (rolling percentiles) are computed.
  So for 13pm all three are skipped and fall through `feats.get(f, 0.0)` → 0.0.

### Quantified severity (model + scaler, 2024/2025 rows, real vs zeroed-3)

| Split | Trained acc (real) | Engine acc (zeroed) | Δ | Predictions flipped |
|---|---|---|---|---|
| 2024 val | 71.95% | 70.33% | −1.63pp | 9.3% |
| 2025 holdout | 72.18% | **71.37%** | −0.81pp | **13.3%** |

Aggregate accuracy loss is ~1pp, but **~1 in 8 daily regime predictions differ** between
the validated model and what deploys. For a one-structure-per-day premium seller that is a
different structure on ~13% of days. The headline retrain numbers (69.6/72.0/**72.2**) are
CSV-measured; the **deployed** 2025 accuracy is **71.4%**.

### Remediation options (operator call — do not silently patch certified code)

- **A — Retrain 13pm without the 3 features (recommended, lowest risk).** Add the three to
  the training drop path so trained == served (both without them). No engine change, no
  re-cert of the engine. Costs ~1pp vs the (unattainable) CSV number, but the number becomes
  honest. Folds in the Task-1 guard fix.
- **B — Fix the engine to serve the 3 for 13pm.** Keeps the ~1pp of signal, but edits the
  certified `DayTypeEngine` (re-certification) **and** requires fixing Finding 2 first (the
  EOD-context loader currently crashes), since `prev_day_vol_pct` needs EOD context.
- **C — Accept as disclosed caveat.** The sealed harness uses the engine, so it already
  forward-tests deployed (zeroed) behavior; only the *classifier* headline is overstated by
  ~1pp. Weakest option — leaves a model with coefficients fit to signal it never sees.

---

## Finding 2 (secondary) — EOD-context loader crashes on the branch's feature CSVs

`daytype_engine._load_eod_context()` reads `nifty_day_features_{yr}.csv` with
`index_col='date'`, but `build_eod_features.py` writes the date as an **unnamed index**
(header starts with a bare comma). `pd.read_csv(index_col='date')` raises
`ValueError: 'date' is not in list`, so constructing `DayTypeEngine()` with those CSVs
present crashes on init.

Impact: 10am/11am models (`block_a_excluded: false`) depend on this context for Block A;
without it they would zero-fill (or, as written, crash). 13pm does not use it. Fix is a
one-liner on either side (name the index column `date` on write, or read `index_col=0`),
but it must be settled before the bundle includes EOD CSVs.

---

## Finding 3 — old-vs-new is not a valid decision rule on this sealed window

The old `D:\BOT` model's splits were train 2023-24, **val 2025, holdout 2026**. The sealed
window is 2025-01 → 2026-07, so the old model saw **both** years — it has no clean
out-of-sample window anywhere in range. Plan step 4 ("new ≥ old on 2026 P&L → proceed") and
D8 ("keep old if worse") **cannot be executed as written**. Restate the criterion as an
**absolute bar on the new model's 2026 P&L**; report the old number, if at all, as
non-comparable context.

Correction to an earlier claim: the old model dir **does** contain `logistic_10am` and
`logistic_11am` (verified in `d:/BOT/root/models/daytype/`); an earlier statement that it
lacked them was wrong.

---

## Task 1 — DONE

`split_data` holdout pinned from `year >= train_thru+2` to `year == train_thru+2`
(`train_daytype_classifier.py:107`). Forward-looking only: current artifacts stay valid
because the feature build already stopped at 2025-12-31, so no retrain is implied *by this
change*. (A retrain may be required by Finding 1, independently.)

---

## Finding 4 (bundle-time) — options `TIMESTAMPTZ` breaks the harness's manual +5:30 shift

The sealed options data is now per-date DuckDB (`{YYYY-MM-DD}.duckdb`, one table, 15 cols)
with `timestamp` typed **`TIMESTAMP WITH TIME ZONE`**, not the UTC-naive CSV the harness was
written for.

On a machine whose DuckDB session tz is `Asia/Calcutta` (verified default here), `.df()`
returns the UTC instant for 13:00 IST already converted to `13:00:00+05:30` (`.hour=13`).
The harness (`get_timestamps_for_date`) then adds `+5:30` → `18:30` (`.hour=18`), so
`entry_ist=(13,0)` is never found and **every session silently skips as `no_13:00_bar`
(zero trades, no error).** Environment-dependent: a UTC-session machine would behave
differently, which is itself the hazard.

Fix (bundle assembly): normalize options `timestamp` to **naive IST wall-clock** on load
(`pd.to_datetime(col, utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)`) and key
entry/exit directly on the IST `(hour, minute)` — drop the `+5:30`. Requires one
disambiguating fact from the sealed files: the min/max `timestamp` of any single day (time
component only) to confirm the stored instants render as 09:15–15:30 IST (already IST) vs
03:45–10:00 (UTC-in-IST-clothing). Also harden the per-date reader: discover the table name
instead of hardcoding `options`, and add `sessions_attempted` + a `load_failed` bucket to
`summary.json` so silent skips are visible (the summary is the only artifact the reviewer sees).

Schema confirmed present (required cols): `timestamp`, `expiry_code` (BIGINT),
`strike_relative`, `option_type`, `close`, `iv`, `strike_price`, `spot_price`.

**RESOLVED (operator, 2026-08-11):** table name is **`options`**; a day's `timestamp` spans
`09:15 → 15:30 +05:30 (Asia/Calcutta)` — i.e. the stored instants **already render as correct
IST wall-clock**. Bundle fix is therefore: on load, `dt.tz_localize(None)` (or
`tz_convert('Asia/Kolkata').tz_localize(None)`) to get naive IST, then key entry/exit on the
IST `(hour, minute)` directly and **delete the `+5:30` shift** in `get_timestamps_for_date`.
No offset is added. Table-name discovery + `load_failed`/`sessions_attempted` still added for
robustness/observability.

## Finding 5 (INVALIDATES first sealed run) — bull_put_spread wing sign bug

First sealed run (`reference/summary.json`, 393 sessions) returned +₹25,237 / Sharpe 1.19 /
WR 64% — **but zero BullTrend trades.** The engine predicts BullTrend **153/393** times
(verified from bars alone, no options), the most common regime, so all 153 were silently
dropped as `no_credit`. Cause: `select_structure`'s `bull_put_spread` buys the protective PE
wing at `+DIRECTIONAL_WING_PTS` (above ATM = ITM PE, dearer) instead of `-DIRECTIONAL_WING_PTS`
(below ATM = OTM PE, cheaper). Real PE prices rise with strike → sell-ATM-PE minus
buy-higher-PE = a debit → `no_credit` every bull day. `bear_call_spread`, `iron_fly`, strangles
use correct signs — only `bull_put` was wrong. The +₹25K reflects only Bear (+27,776) and
Choppy (−2,539); every bullish day (likely profitable put-selling in a rising market) was
discarded, so the number is not usable.

Fixed in `sealed_harness.py` (wing → `-DIRECTIONAL_WING_PTS`); validated on a BullTrend date
with monotonic pricing (now trades, previously `no_credit`). Also added a `load_failed` skip
bucket (the reconciliation was 3 short — 3 sessions with <100 bars). Bundle rebuilt. This is
MM12.5 forward paper, not a one-shot RFA read, so re-running the corrected harness over
2025–2026 is legitimate — the sealed window is not burned.

## Recommended next step

Operator picks A / B / C for Finding 1. If **A**, the retrain re-runs with the guard fix and
the 3 features dropped, holdout is remeasured, and only then is the sealed bundle assembled
against a model whose deployed behavior matches its validation. Findings 2 and 3 are settled
in passing (2 = one-line CSV/loader fix; 3 = restate the decision criterion).
