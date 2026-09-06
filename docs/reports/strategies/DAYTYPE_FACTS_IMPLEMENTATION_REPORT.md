# DayType Facts-Publisher — Implementation Report

**Date:** 2026-08-07
**Branch:** `research/daytype-facts-adoption`
**Implementer:** DeepSeek V4. **Status:** implementer proposes; grants nothing.
**Spec:** `DAYTYPE_FACTS_ADOPTION_SPEC.md` (§2–§7, DT1–DT5). **Prompt:** `DAYTYPE_FACTS_IMPLEMENTATION_PROMPT.md`.

## 1. Scope delivered

| Deliverable | Status | Evidence |
|---|---|---|
| **A. Placement** (spec §3 hard path) | DONE | engine at `core/state/daytype_engine.py`; feature builder at `scripts/build_intraday_features.py`; models at `models/daytype/{logistic_13pm_prod,logistic_10am,logistic_11am}/` |
| **B. Offline publisher** (first — unblocks Stage 1) | DONE | `scripts/daytype/publish_facts.py` → `data/features/day_type/day_type_facts.duckdb` — **839 regime facts**, 2023-01-02 → 2026-07-03 |
| **C. Live 13:00 publisher** (Stage-2 prereq) | DONE | `scripts/daytype/publish_live_fact.py`; end-to-end verified on a past session; correctly reports NOT-READY when < MIN_BARS today |
| **D. Tests** | DONE | `tests/daytype/test_daytype_facts.py` — 9 tests, all green |

Smoke test required by the prompt: `DayTypeEngine(lock_threshold=1.01)` **loads** via the hard
path, all three checkpoints (10am/11am/13pm) resolve, models load without warnings.

## 2. Placement notes (spec §3)

| File | Destination | Notes |
|---|---|---|
| `daytype/daytype_engine.py` | `core/state/daytype_engine.py` | copied byte-identical (SHA-256 `5fc502da…`); path rule `Path(__file__).parent.parent.parent / models/daytype` holds from `core/state/` |
| `daytype/build_intraday_features.py` | `scripts/build_intraday_features.py` | paths already resolve to F:\nifty via `ROOT`; confirmed by import test |
| `daytype/models/daytype/logistic_13pm_prod/` | `models/daytype/logistic_13pm_prod/` | model.pkl + scaler.pkl + metadata.json |
| `daytype/models/daytype/logistic_10am/`, `logistic_11am/` | `models/daytype/…` | AM checkpoints copied so the engine loads cleanly (DT5); not published |
| **`core/analytics/day_features.py`** | `core/analytics/day_features.py` | **dependency not in the bundle** — the engine's `_compute_features` imports `compute_session_twap, AM_END_BAR, CLV_THRESHOLD, _range_epsilon` from it at runtime. Copied from the same vintage `D:\BOT\root\core\analytics\day_features.py` (content is source code, not a trained artifact). F:\nifty had only `resampler.py`. |

`.gitignore`: `*.pkl` is a global ignore; the model binaries (≈1.7 KB each) are now
tracked via `!models/daytype/**/model.pkl` / `!scaler.pkl`, because a Stage-1 replay must
reproduce facts from the **recorded model + committed publisher** (spec §4) — a fresh clone
without the pkls could not. `data/features/day_type/` (the facts DB) stays ignored, as with
all runtime facts stores.

## 3. Fact schema and provenance (spec §4)

Stored in DuckDB at `data/features/day_type/day_type_facts.duckdb`, table `day_type_facts`,
`PRIMARY KEY (session_date, checkpoint)`. 839 rows, 0 missing VIX.

| Field | Value (every row) |
|---|---|
| `session_date` | 2023-01-02 … 2026-07-03 |
| `checkpoint` | `13pm` (DT5 — AM checkpoints not published) |
| `regime` | Choppy 478 · BullTrend 247 · BearTrend 114 |
| `regime_confidence` | min 0.407 / mean 0.753 / max 1.0 |
| `vix_close` | per-session India VIX close from the 1d store |
| `regime_fact_version` | `dt-v2.0-train_thru2025` |
| `model_hash` | SHA-256 over the 3 model files, fixed order → `cd11e087…06b5` |
| `produced_by` | `offline@06b99e3` |
| `trained_on` | `D:\BOT\root vintage — NOT F:\nifty data` (standing provenance, per row) |

`model_hash` is content-based: tampering with any of the three model files changes the hash
(covered by `test_model_hash_is_content_based`).

## 4. Determinism / reproducibility (the load-bearing contract)

- **Byte-identical across independent runs.** The full corpus was published twice to separate
  DuckDB files; all 839 fact rows compared equal across all 9 columns (`BYTE-IDENTICAL: True`).
- **Re-run idempotency.** Re-running the offline publisher over the same range appended **0** new
  rows (`INSERT OR REPLACE` on the PK; existing dates skipped).
- **Live ≡ offline for the same session.** `publish_live_fact.py --date 2023-01-02` produced
  `Choppy 0.6573`, identical to the offline fact for that session (asserted in
  `test_live_publisher_matches_offline_for_same_session`).
- Determinism is *structural*: the same bars + same model files produce the same classification
  because the publisher is committed code fed from a fixed path, and the model is pinned by hash.

## 5. Classification boundary (Principle #2 / spec §5)

`DayTypeEngine.on_bar` / `on_bn_bar` run **inside the publishers** (offline batch or the live
13:00 job). No strategy runtime runs the model; `nifty_shield_v1` reads the fact from DuckDB.
The strategy never receives the Bank-Nifty feed the Block-H features need.

## 6. Skipped sessions (transparency)

| Bucket | Count | Meaning |
|---|---|---|
| published | 839 | full 13pm fact produced |
| skipped_no_data | 27 | 1m file absent or < 100 bars up to 13:00 |
| skipped_no_state | 2 | bars present but no 13pm checkpoint emitted |
| skipped_no_vix | 0 | every published session has a VIX close |

**Cleanup applied (2026-08-07, review F2/F3):** VIX-less sessions are now **skipped**, never
published with a NULL `vix_close` (`skipped_no_vix` increments and the row is dropped); the live
publisher applies the same guard. Two vacuous test asserts were replaced with real before/after
checks, and a synthetic VIX-less-session test was added. Suite now **10/10 green**.

## 7. Acceptance check (prompt §4)

> Offline publisher produces reproducible, hashed regime facts over the Stage-1 conformance
> corpus → satisfies the NiftyShield Stage 1 prompt §0 precondition.

**Met.** The offline publisher is committed and re-runnable; facts are reproducible and
provenance-stamped; the NiftyShield Stage 1 `§0` precondition (regime/VIX fact interface exists)
is satisfied by the schema + populated store above. Live-publisher acceptance remains a Stage 2
gate — the code path exists and is tested, but no live 13:00 bar feed is wired to it in this
repo today (it correctly reports NOT-READY when the session has < MIN_BARS).

## 8. Prohibitions honored

- **No retrain.** The `.pkl`s are the retired `D:\BOT\root` `v2.0-train_thru2025` models, reused
  as-is and content-hashed. `trained_on` stamps this on every fact row.
- **No NiftyShield code touched.** This task touches only DayType infra.
- **No strategy `SignalEvent`s, no promotion-pipeline entry.** DayType stays infrastructure.

## 9. Files

| File | Purpose |
|---|---|
| `core/state/daytype_engine.py` | adopted DayType engine (byte-identical to bundle) |
| `core/state/__init__.py` | package marker |
| `core/analytics/day_features.py` | engine feature-library dependency (from `D:\BOT\root` vintage) |
| `scripts/build_intraday_features.py` | offline feature builder (paths repointed to F:\nifty) |
| `scripts/daytype/publish_facts.py` | **offline publisher** — batch date range → hashed 13pm facts |
| `scripts/daytype/publish_live_fact.py` | **live 13:00 publisher** (Stage-2 prereq) |
| `scripts/daytype/__init__.py` | package marker |
| `models/daytype/…` | 3 checkpoint model dirs (13pm + AM) |
| `tests/daytype/test_daytype_facts.py` | 9 tests: determinism, schema/provenance, re-run, live≡offline, model-hash content identity |
| `data/features/day_type/day_type_facts.duckdb` | 839-row facts store (runtime artifact, gitignored) |

## 10. Implementation notes for the reviewer

- **The bundle README §2's "imports only stdlib + numpy/pandas — no core.*" is imprecise**: the
  engine's `_compute_features` does function-local `core.analytics.resampler` /
  `core.analytics.day_features` imports. Both now exist in F:\nifty (`resampler.py` was already
  present; `day_features.py` was brought over). This is the one non-obvious dependency the
  spec's §3 table did not list.
- **Proposed, not self-granted:** nothing is granted here — the reviewer/operator decides on the
  Stage-1 conformance hand-off.
