# DayType Facts-Publisher — Cleanup Prompt (F2 + F3)

**For:** DeepSeek V4. **Author/reviewer:** Claude. **Context:** the DayType implementation was
reviewed **ACCEPT** (`DAYTYPE_FACTS_IMPLEMENTATION_REVIEW.md`) with 3 LOW, non-blocking findings.
F1 (doc/provenance) is done. This prompt clears **F2 + F3**. Do not touch provenance, the fact
schema, the model files, or the classification logic. Keep all 9 tests green (add/adjust as noted).

## F2 — VIX-less sessions must SKIP, not publish a NULL-VIX fact
In `scripts/daytype/publish_facts.py`, the `vix is None` branch (~lines 203–210) increments
`skipped_no_vix` **but still appends the row** with `vix_close = NULL`. NiftyShield needs VIX
(structure selection **and** the `VIX > 20` skip filter), so a NULL-VIX fact is unusable.

- **Fix:** when `vix is None`, `skipped_no_vix += 1` and **`continue`** — do not append the row.
- Leave the `vix_close` column nullable in the schema (no schema change), but the publisher now
  never emits a NULL-VIX row.
- **No re-publish required:** the current 839-row store had 0 such sessions (the facts DB is
  gitignored and regenerable regardless), so this is a code-correctness fix, not a data fix.
- Add/adjust a test asserting a synthetic VIX-less session is counted in `skipped_no_vix` and
  produces **no** fact row.

## F3 — remove two vacuous test assertions in `tests/daytype/test_daytype_facts.py`
- `test_rerun_reproducibility_idempotent` (line ~87): `assert _facts(db) == _facts(db)` compares a
  value to itself. Replace with a real before/after check: snapshot `rows_before = _facts(db)`
  after the first publish, re-publish, then `assert _facts(db) == rows_before`.
- `test_live_publisher_not_ready_without_data` (line ~173): `assert not (...).exists() or True` is
  always true — delete that line; keep `assert res["ready"] is False`.

## Constraints & acceptance
- No change to provenance columns, schema, model files, or engine/feature code.
- `python -m pytest tests/daytype/` green (still 9+ tests; F2 may add one).
- Report back briefly (what changed, test count); the operator/Claude decide the commit. Grant nothing.
