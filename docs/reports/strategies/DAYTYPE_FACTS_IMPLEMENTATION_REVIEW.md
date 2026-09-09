# DayType Facts-Publisher — Lead Review

**Date:** 2026-08-07
**Reviewer:** Claude (role split — Claude reviews; DeepSeek implemented). **Verdict: ACCEPT** (non-blocking cleanups below).
**Reviews:** `DAYTYPE_FACTS_IMPLEMENTATION_REPORT.md`, the code, and the empirical checks run for this review.
**Spec:** `DAYTYPE_FACTS_ADOPTION_SPEC.md` · **Prompt:** `DAYTYPE_FACTS_IMPLEMENTATION_PROMPT.md`.

## 1. Verified empirically (not taken on trust)

| Claim | Check | Result |
|---|---|---|
| 9/9 tests green | `python -m pytest tests/daytype/` | **9 passed** |
| Model `.pkl` committable (reproducibility) | `git check-ignore models/daytype/logistic_13pm_prod/model.pkl` | **NOT ignored** — the `!models/daytype/**` negation holds |
| Facts DB not tracked (runtime artifact) | `git status` | `data/features/day_type/` absent from status → correctly ignored |
| Placement (hard path) | report + `git status` | engine at `core/state/`, models at `models/daytype/`, builder at `scripts/` |
| Provenance per row (D2) | `publish_facts.py` `_schema` + tests | `model_hash` (SHA over 3 files), `regime_fact_version`, `produced_by`, `trained_on` all NOT NULL, asserted |
| `day_features.py` correctness | full read | clean, **causal**, epsilon-guarded; engine uses only 4 benign helpers |

## 2. Load-bearing contracts — all met

- **Provenance/determinism (D2, spec §4):** every fact carries the content-hash of the exact model + version + `trained_on` standing note; the publisher is committed, re-runnable, fed from a fixed path; determinism proven byte-identical on the full 839-session corpus. A Stage-1 replay is reproducible. **This is the requirement the whole adoption existed to satisfy, and it is satisfied.**
- **DT1 (reuse + hash), DT5 (13pm only), Principle #2 (model runs in the publisher, not the strategy):** honored.
- **Prohibitions:** no retrain, no NiftyShield code touched, no `SignalEvent`/pipeline entry. Honored.
- **Acceptance (prompt §4):** the NiftyShield Stage 1 `§0` precondition (a reproducible, provenance-stamped regime/VIX fact interface) **is satisfied.**

**Positive diligence noted:** the implementer caught the `.gitignore` `*.pkl` trap (load-bearing — a fresh clone would otherwise fail reproducibility) and surfaced that the bundle README's "engine imports only stdlib + numpy/pandas — no core.*" claim is false.

## 3. Findings (all non-blocking)

**F1 — `day_features.py` provenance (LOW).** A clean causal feature library, brought from `D:\BOT\root` vintage; not previously in F:\nifty and not flagged in spec §3. The engine imports only `compute_session_twap`, `AM_END_BAR`, `CLV_THRESHOLD`, `_range_epsilon` from it — all benign. **No correctness risk.** But it participates in fact production, so its provenance should be recorded like the model's (`D:\BOT\root` vintage, not validated on F:\nifty), and it should be listed in the spec §3 dependency table. Cosmetic: leftover scratch comments at lines 33–38.

**F2 — `skipped_no_vix` counts-but-publishes (LOW).** In `publish_facts.py`, a session with no VIX increments `skipped_no_vix` **but still publishes** the fact with `vix_close = NULL` (lines 203–210). 0 occurrences on the current corpus, so no live impact. But NiftyShield needs VIX (structure selection **and** the `VIX > 20` skip filter), so a NULL-VIX fact is unusable by the consumer. Recommend: either genuinely skip (do not publish) VIX-less sessions, or rename the counter and document that consumers must treat NULL VIX as "skip session".

**F3 — two vacuous test assertions (LOW).** `test_rerun_reproducibility_idempotent` (line 87) `assert _facts(db) == _facts(db)` compares a value to itself; `test_live_publisher_not_ready_without_data` (line 173) `assert not (...).exists() or True` is always true. Each has a real assertion alongside (`new_rows == 0`, `ready is False`), so the behaviors *are* tested — but the dead asserts should be removed so they can't mask a future regression.

## 4. Recommendation

**ACCEPT for the Stage-1 hand-off.** The precondition is met and the reproducibility contract is intact and verified. F1–F3 are cleanups, not blockers — best folded in before the commit (F2 and F3 are ~10-minute fixes; F1 is a doc/provenance note). None require re-running the 839-session publish. The Stage-1 conformance hand-off remains the operator's grant.
