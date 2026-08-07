# DayType — Facts-Publisher Adoption Spec

**Date:** 2026-08-07
**Branch:** `research/daytype-facts-adoption`
**Status:** Spec. Defines how the bundled DayType engine is adopted as a **facts publisher**
that produces the versioned/hashed **regime fact** `nifty_shield_v1` depends on
(Decomposition Spec §6, decision D2). Role split: Claude writes this spec + the implementer
prompt + reviews; **DeepSeek V4 implements**. No code exists yet.
**Source:** `F:\nifty_research_bundle\daytype\`
**Consumers / cross-refs:** `NIFTY_SHIELD_DECOMPOSITION_SPEC.md` §6, `NIFTY_SHIELD_STAGE1_IMPLEMENTATION_PROMPT.md` §0.

> **⚠ STANDING MODEL-PROVENANCE NOTE (operator-directed, 2026-08-07).** The DayType models
> adopted here were **NOT trained on F:\nifty data.** They are the retired `D:\BOT\root`
> platform's models (`v2.0-train_thru2025`), reused **as-is** and content-hashed (DT1). Any
> regime fact they produce inherits that provenance. Retraining on F:\nifty 1m data is a
> **separate, deferred task** (needs the old-repo trainer, absent from the bundle). This note
> stands until a retrain-on-F:\nifty pass lands and is recorded here. It is embedded per-row via
> the `trained_on` fact column (§4).

---

## 1. What this is (and is not)

DayType is a **regime classifier** (BullTrend / BearTrend / Choppy at 10am/11am/13pm
checkpoints), a v2 logistic model over 41 intraday + intermarket features (incl. Block-H
`bn_nf_*` BankNifty–Nifty spreads — metadata confirms it needs **both** the Nifty and
Bank-Nifty 1m feeds). It is **infrastructure**, not a strategy: it produces facts, it never
emits `SignalEvent`s and never enters the promotion pipeline.

This adoption makes DayType a **facts publisher** conforming to Principle #2 ("indicators
pre-computed offline; runtime is read-only") — the same offline `publish_facts.py` → DuckDB →
runtime-reads shape Carry/TS-Basis use. The strategy reads the regime *fact*; it never runs the
model.

**Out of scope:** the NiftyShield SignalSource build (its own prompt); `sweep_filter`.

## 2. The two publishers

| Publisher | Produces | Needed for |
|---|---|---|
| **Offline** (historical batch) | regime fact for every past session in a bar corpus | **Stage 1 conformance corpus** (the SignalSource's replay-twice determinism reads recorded facts) — the precondition the Stage 1 prompt §0 lists |
| **Live** (intraday, at 13:00) | regime fact for *today*, from that session's bars up to 13:00 | **Stage 2 forward PAPER** (the 13:00 entry needs the regime computed live) |

The offline publisher is the first deliverable (unblocks Stage 1). The live publisher is a
Stage 2 prerequisite. Both wrap the *same* `DayTypeEngine`.

## 3. File placement (HARD path constraint)

The engine resolves models as `Path(__file__).parent.parent.parent / "models" / "daytype"`,
with **no override**. Therefore:

| File (bundle) | Destination (mandatory) |
|---|---|
| `daytype/daytype_engine.py` | `core/state/daytype_engine.py` |
| `daytype/build_intraday_features.py` | `scripts/build_intraday_features.py` (repoint its data paths to F:\nifty — see §6) |
| `daytype/models/daytype/logistic_13pm_prod/` | `models/daytype/logistic_13pm_prod/` |
| `daytype/models/daytype/logistic_10am/`, `logistic_11am/` | `models/daytype/…` (AM checkpoints load without warnings) |

`nifty_shield_v1` needs 13pm only; AM checkpoints are copied so the engine loads cleanly.

## 4. Regime-fact schema, storage, provenance

**Storage:** a DuckDB facts table (convention: `data/features/day_type/` or a `day_type_facts`
DuckDB, matching how Carry/TS-Basis publish). Keyed by `session_date`.

**Row:**
| Field | Type | Note |
|---|---|---|
| `session_date` | DATE | key (IST trading date) |
| `checkpoint` | TEXT | `13pm` (extensible to 10am/11am) |
| `regime` | TEXT | `BullTrend` \| `BearTrend` \| `Choppy` |
| `regime_confidence` | DOUBLE | model max-class probability |
| `vix_close` | DOUBLE | India VIX (the strategy's VIX input travels with the fact) |
| `regime_fact_version` | TEXT | e.g. `dt-v2.0-train_thru2025` |
| `model_hash` | TEXT | SHA-256 over `model.pkl`+`scaler.pkl`+`metadata.json` |
| `produced_by` | TEXT | `offline` \| `live`; + code commit ref |
| `trained_on` | TEXT | **standing provenance:** `D:\BOT\root vintage — NOT F:\nifty data` (until a retrain-on-F:\nifty pass lands) |

**Provenance is load-bearing (D2).** Determinism now depends on facts provenance, and this repo
has a scar exactly there (a source-of-truth store re-keyed by uncommitted code — CLAUDE.md).
Rules: the fact is produced **only** by committed, re-runnable code; `model_hash` +
`regime_fact_version` are recorded on every row; a Stage-1 replay must reproduce identical
regime facts from the recorded model + committed publisher. **The regime fact is the identity
boundary** — the DayType model is not part of `nifty_shield_v1`'s triple; its identity lives
here, in the fact's provenance columns.

## 5. Principle #2 compliance

The `DayTypeEngine.on_bar`/`on_bn_bar` runtime classification runs **inside the publisher**
(offline batch or the live 13:00 job), **not** inside the strategy runtime. The strategy's
`on_bar` does a read-only fact lookup. This resolves the §5.5 tension in the assessment:
DayType classification is a fact-production step, the strategy is a fact consumer.

## 6. Decisions (operator ratifies; recommendations given)

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| **DT1** | Reuse bundle `.pkl`s vs retrain on F:\nifty 1m data | **Reuse + content-hash now**; retraining is a later *alpha-quality* task, not a blocker | Conformance/determinism needs a *pinned* model, not a *good* one (safety ≠ alpha). Retraining needs `train_daytype_classifier.py` (**not in the bundle** — from the old repo). Reuse unblocks Stage 1; provenance = "external, bundle vintage v2.0-train_thru2025", recorded in `model_hash`. |
| **DT2** | Build order | **Offline publisher first** (unblocks Stage 1), live 13:00 publisher second (Stage 2) | Sequenced by what each gate needs. |
| **DT3** | Feature-builder data paths | Repoint `build_intraday_features.py` reads to F:\nifty's `data/market_data/nse/candles/1m/{date}.duckdb` (Nifty 50 + Bank Nifty); writes to `data/features/day_type/` | The bundle's paths are the old repo's. |
| **DT4** | Model identity in the fact | `model_hash` over the 3 model files + `regime_fact_version` on every row | Makes the regime reproducible; keeps the model out of the strategy triple (D2). |
| **DT5** | AM checkpoints (10am/11am) | Copy them (engine loads cleanly) but publish **13pm only** for now | `nifty_shield_v1` uses 13pm; AM facts are free to add later. |

**⚠ DT1 caveat to carry forward:** the bundle `.pkl`s were trained on the *old platform's* data.
If they classify F:\nifty's 1m bars poorly (feature drift, calendar/vendor differences), the
regime fact will be low-quality — which would surface as weak Stage 2 alpha, **not** a
conformance failure. A retrain-on-F:\nifty pass (needs the old-repo trainer) is the remedy, held
as a separate task. Reuse is a *safety-adequate* start, not an *alpha-adequate* one.

## 7. Deliverables (for the implementer prompt) & acceptance

1. Engine + feature builder + models placed per §3; a smoke test: `DayTypeEngine(lock_threshold=1.01)`
   loads (confirms the hard model path).
2. **Offline publisher** — batch a bar-corpus date range → regime-fact rows (§4), committed +
   re-runnable, `model_hash`/version stamped.
3. **Live 13:00 publisher** — intraday job producing today's 13pm regime fact from that session's
   Nifty + Bank-Nifty bars up to 13:00 (Stage 2; can follow the offline one).
4. Tests: determinism (same corpus + same model → identical facts); fact-schema/provenance
   assertions; a re-run reproducibility check.
- **Acceptance:** offline publisher produces reproducible, hashed regime facts over the Stage-1
  conformance corpus → satisfies the Stage 1 prompt §0 precondition. (Live publisher acceptance
  is a Stage 2 gate.)

## 8. Cross-references
- `NIFTY_SHIELD_DECOMPOSITION_SPEC.md` §6 (regime-fact interface, D2), §5.5 (Principle #2).
- `NIFTY_SHIELD_STAGE1_IMPLEMENTATION_PROMPT.md` §0 (this is the named precondition).
- Bundle: `F:\nifty_research_bundle\README.md` §2 (hard path constraint, retrain flow).
- Facts convention: `scripts/refresh_all_strategies.py`, Carry/TS-Basis `publish_facts.py`.
