# DayType Facts-Publisher — Implementer Prompt

**For:** DeepSeek V4 (implementer). **Author/reviewer:** Claude. **Status:** hand-off artifact.
**Goal:** adopt the bundled DayType engine as a **facts publisher** producing the versioned/hashed
regime fact `nifty_shield_v1` depends on — the named precondition in
`NIFTY_SHIELD_STAGE1_IMPLEMENTATION_PROMPT.md` §0. Infrastructure only; DayType never emits
`SignalEvent`s and never enters the promotion pipeline.

> **⚠ STANDING PROVENANCE (operator-directed, 2026-08-07):** the models are **NOT trained on
> F:\nifty data** — they are the retired `D:\BOT\root` `v2.0-train_thru2025` models, reused as-is
> and content-hashed (DT1). Stamp this on every fact row (`trained_on` = `D:\BOT\root vintage —
> NOT F:\nifty data`). Do **not** silently retrain; a retrain-on-F:\nifty pass is a separate task.

## 1. Read first (authoritative)
1. `docs/reports/DAYTYPE_FACTS_ADOPTION_SPEC.md` — **the spec you implement** (§2–§7, decisions DT1–DT5).
2. `docs/reports/NIFTY_SHIELD_DECOMPOSITION_SPEC.md` §6 — the regime-fact interface + provenance rule (D2).
3. `F:\nifty_research_bundle\README.md` §2 — hard model-path constraint, retrain flow (do NOT run).
4. Facts convention: Carry/TS-Basis `publish_facts.py`, `scripts/refresh_all_strategies.py`.

## 2. Deliverables
**A. Placement (spec §3 — hard path).** Copy `daytype_engine.py` → `core/state/`;
`build_intraday_features.py` → `scripts/` (repoint reads to F:\nifty
`data/market_data/nse/candles/1m/{date}.duckdb` Nifty 50 + Bank Nifty; writes to
`data/features/day_type/`); models → `models/daytype/{logistic_13pm_prod,logistic_10am,logistic_11am}/`.
Smoke test: `DayTypeEngine(lock_threshold=1.01)` loads (confirms the hard path resolves).

**B. Offline publisher (first — unblocks Stage 1).** Batch a bar-corpus date range → regime-fact
rows per spec §4 schema (`session_date`, `checkpoint=13pm`, `regime`, `regime_confidence`,
`vix_close`, `regime_fact_version`, `model_hash` = SHA-256 over the 3 model files, `produced_by`,
`trained_on`). Committed, re-runnable code only.

**C. Live 13:00 publisher (second — Stage 2 prereq).** Intraday job producing today's 13pm regime
fact from that session's Nifty + Bank-Nifty bars up to 13:00.

**D. Tests.** Determinism (same corpus + same model → byte-identical facts); schema + provenance
assertions (`model_hash`, `trained_on` populated); a re-run reproducibility check.

## 3. Hard constraints
- **Provenance is load-bearing (D2):** facts produced **only** by committed, re-runnable code;
  `model_hash` + `regime_fact_version` + `trained_on` on every row. A Stage-1 replay must
  reproduce identical facts. (Repo scar: a source-of-truth store re-keyed by uncommitted code.)
- **Principle #2:** classification runs in the publisher, never in a strategy's runtime.
- Publish **13pm only** for now (DT5); AM checkpoints copied only so the engine loads cleanly.
- Do **not** retrain (provenance note); do **not** touch NiftyShield strategy code (separate prompt).

## 4. Acceptance
Offline publisher produces reproducible, hashed regime facts over the Stage-1 conformance corpus
→ satisfies the NiftyShield Stage 1 prompt §0 precondition. (Live-publisher acceptance is a Stage 2
gate.) Report to `docs/reports/`; the implementer proposes with evidence and grants nothing.
