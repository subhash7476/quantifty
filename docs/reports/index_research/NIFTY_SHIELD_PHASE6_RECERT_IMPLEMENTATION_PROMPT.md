# Implementation Prompt — Phase 6: Retrained-Model Production Swap + Re-Certification

**Branch:** `feat/niftyshield-model-retrain`
**Implementer:** DeepSeek V4
**Reviewer:** Claude (conformance PASS + config_hash-unchanged are the acceptance gates)
**Grantor of the ledger entry:** operator / Technical Lead (NOT the implementer)
**Context:** `NIFTY_SHIELD_RETRAIN_BLOCKER_FINDINGS.md`, `NIFTY_SHIELD_SEALED_ACCEPTANCE_BAR.md`,
ledger entries E005/E006 in `docs/STRATEGY_PROMOTION_LEDGER.md`.

## Objective

Put the honest, retrained DayType models (`v2.0-train_thru2023`, parity PASS) into production so
the forward-PAPER window (E007) runs on the sound model instead of the D:\BOT vintage with the
known 13%-flip train/serve skew. This is an **E006-style CONFORMANT → CONFORMANT re-certification**
of the SAME identity — same `strategy_id`, same `config_hash` (`c5b722ff…536c`), new `code_ref`,
new `model_hash`/`regime_fact_version`. It confers **NO alpha, NO PAPER VALIDATED, NO LIVE**
authority — it only swaps the model input and re-pins CONFORMANT.

This re-cert is **independent of the 2026 sealed verdict** (INCONCLUSIVE): the sealed read gates
promotion to capital, not the identity/safety re-cert. The reason to swap is soundness (honest,
correct provenance, 13-year regime breadth), not demonstrated profitability.

## Hard invariants (violating any = STOP)

- **`config_hash` UNCHANGED** — the model is a FACT input, not part of the strategy config. Verify
  it still reproduces `c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6` from
  `strategies/nifty_shield_v1/config.py`. If it moves, something is wrong — stop.
- **Do NOT regenerate the frozen conformance corpus** (`strategies/nifty_shield_v1/corpus/`).
  It is a fixed fixture; conformance tests the SignalSource *contract*, not the model output.
  The swap is a provable offline no-op for conformance precisely because the corpus is untouched
  (E006 precedent).
- **OSC index-options window 2016-02-11 → 2022-12-31 UNTOUCHED.** No P&L presented as validation.
- **No strategy/execution/driver code change.** Model + provenance + facts + tests + docs only.

## Tasks

### A — Confirm production model artifacts
The branch `models/daytype/{logistic_10am,logistic_11am,logistic_13pm_prod}` are already the
retrained v2.0 artifacts (13pm = 38 features, parity PASS). Confirm they are the ones that will
land on `main`. No re-train here.

### B — Provenance string
`scripts/daytype/publish_facts.py:49` — replace
`TRAINED_ON = r"D:\BOT\root vintage — NOT F:\nifty data"` with an honest F:\Nifty provenance
string, e.g. `TRAINED_ON = "F:\\Nifty reference 1m 2012-2023 + DuckDB store; retrained v2.0-train_thru2023"`.
Keep it a single stable literal.

### C — Fix the version-string tests (currently assert the OLD model)
`regime_fact_version()` returns `f"dt-{meta['version']}"` → now `dt-v2.0-train_thru2023`. Update
the two hardcoded expectations from `train_thru2025` → `train_thru2023`:
- `tests/daytype/test_daytype_facts.py:145`
- `tests/strategies/test_nifty_shield_v1_lazy_facts.py:59`
Do NOT weaken the assertions to "any string" — pin the exact new value.

### D — Republish the DayType facts DB
Re-run `scripts/daytype/publish_facts.py` over its production window so `day_type_facts.duckdb`
carries the new `model_hash`, `regime_fact_version = dt-v2.0-train_thru2023`, and the Task-B
`trained_on`. Report the new `model_hash` and row count. (This is live/production facts, NOT the
frozen corpus.)

### E — ACCEPTANCE GATE: conformance re-run, must PASS unchanged
Run the NiftyShield conformance + execution suites (`tests/strategies/test_nifty_shield_v1_conformance.py`,
`tests/execution/test_nifty_shield_execution.py`, plus the DS2 driver/facts tests). All must PASS
with the corpus untouched. Then run the full suite; report green/known-failures. The pre-existing
unrelated `test_g1_closure_guard` main failure noted at E006 is not caused here.

### F — Datasheet + ledger draft
- Bump `docs/strategies/nifty_shield_v1/datasheet.md` §1 `code_ref` to the new merge commit.
- Draft the ledger entry as a **CONFORMANT → CONFORMANT re-cert** (same `strategy_id`, same
  `config_hash`, new `code_ref`, new `model_hash`, `regime_fact_version = dt-v2.0-train_thru2023`).
  Per the E006 precedent a re-cert consumes the next numeric slot and PAPER VALIDATED shifts down —
  **flag the numbering for the operator, do not self-assign the grant.** The entry MUST record that
  the E005/E006 STANDING PROVENANCE CAVEAT ("models NOT trained on F:\Nifty") is now **RESOLVED** by
  this swap, and that the retrain's 2026 sealed read was INCONCLUSIVE (no promotion implied).

## Hand-back
New `code_ref`, confirmation `config_hash` unchanged, new `model_hash`/`regime_fact_version`,
facts DB row count, conformance PASS + full-suite status, updated tests, datasheet §1 diff, and the
drafted ledger entry for operator grant. Claude reviews conformance + config_hash-unchanged, then
the operator grants the ledger entry and the E007 PAPER window proceeds on the new model.
