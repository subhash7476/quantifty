# NiftyShield E008 — PAPER report-surface identity re-pin (implementer prompt)

**Role:** DeepSeek implements; Claude reviews (standing split, `msrp-phase6-review-role`).
**Branch:** work on `main` (already carries the retrain + Phase B tooling, merge `393dbac`).
**Author:** Claude. Trigger: operator opened the E008 PAPER window 2026-08-11; the Phase B
report surface is still pinned to the pre-retrain identity.

---

## Why

The PAPER window now validates the **retrained** DayType model. E007 was consumed by the
retrained-model re-cert (Ledger E007, `code_ref fe87363`, config_hash `c5b722ff…536c`
UNCHANGED), so **PAPER VALIDATED is now E008**. But the Phase B report-generating surface was
written on 2026-08-09 against the old identity and still says **`89fcdd6` / "E007"**. Left
unfixed, `assemble_report.py` would stamp the wrong `code_ref` and the wrong ledger slot into
the permanent PAPER Validation Report at window close.

This is a **semantics-preserving identity re-pin only** — do NOT touch the counting predicate
(§3), acceptance gates (§8), evidence model, or any behavior. Only the identity strings and the
grant number change: `89fcdd6 → fe87363`, `E007 → E008`, `E006 re-cert → E007 re-cert`.

`config_hash` is unchanged and must stay `c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6`.
Do NOT touch `strategies/nifty_shield_v1/` or `models/daytype/`.

---

## Targets

### 1. `docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.skeleton.md` (FROZEN template — edit VALUES, never markers)

- Title line 1: `(Stage 2, E007)` → `(Stage 2, E008)`.
- Status para: `The E007 grant waits on Phase B's real forward window` → `The **E008** grant waits …`.
- §1 Identity table, `code_ref` row: `**`89fcdd6`** (Ledger E006 re-cert)` →
  `**`fe87363`** (Ledger E007 re-cert)`.
- **Do not add/remove/rename any `<!-- marker -->` or section header** — `assemble_report.py`
  validates markers and fails loudly on a missing/duplicated one. Only cell/prose values change.

### 2. `scripts/nifty_shield_paper/assemble_report.py` (generates the report body)

- Lines ~386 and ~390: the two `"… is not strategy-attributable (E007 acceptance #8)."` strings
  → `E008 acceptance #8` (these strings are written into the generated report).
- Docstring line 1 and the argparse `description` (~line 437): `E007 Phase B` → `E008 Phase B`.

### 3. Cosmetic docstrings (consistency; no behavior)

- `scripts/nifty_shield_paper/session.py`, `recorder.py`: `E007 Phase B` → `E008 Phase B` in
  docstrings / argparse descriptions only.

### 4. `docs/reports/NIFTY_SHIELD_STAGE2_PAPER_VALIDATION_IMPLEMENTATION_PROMPT.md` (prompt of record)

- Lines 4, 21, 71 (and any other): `code_ref 89fcdd6` → `code_ref fe87363`;
  `Ledger E006` → `Ledger E007`; the identity triple `(nifty_shield_v1, 89fcdd6, c5b722ff…)` →
  `(nifty_shield_v1, fe87363, c5b722ff…)`; the grant this earns `E007` → `E008`.

### 5. `docs/strategies/nifty_shield_v1/PAPER_WINDOW_RUNBOOK.md` (finish the sweep)

Claude already re-pinned the load-bearing header/identity lines and added a re-pin banner.
Sweep the remaining body `E007`/`89fcdd6` mentions → `E008`/`fe87363`, then **delete the banner's
last sentence** ("Every 'E007 / 89fcdd6' still appearing below is stale …") since it no longer
applies. Leave the counting/acceptance/evidence semantics untouched.

### 6. Regenerate the stale generated output (do NOT hand-edit it)

`docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.md` is generated output currently showing
`89fcdd6`. Regenerate it from the corrected skeleton so it reflects `fe87363`/E008:
```bash
python scripts/nifty_shield_paper/assemble_report.py
```
(pre-window, no evidence yet → it reproduces the skeleton-state report). Never hand-edit this file.

---

## Verification (paste output)

1. `assemble_report.py` runs clean (marker validation passes, idempotent):
   ```bash
   python scripts/nifty_shield_paper/assemble_report.py && python scripts/nifty_shield_paper/assemble_report.py
   ```
   Two consecutive runs must both succeed and produce identical output (F-B2 idempotency).
2. No stale pins remain in the report surface:
   ```bash
   grep -rn "89fcdd6" scripts/nifty_shield_paper/ docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.skeleton.md docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.md docs/strategies/nifty_shield_v1/PAPER_WINDOW_RUNBOOK.md
   # expect: no matches
   grep -rn "E007" scripts/nifty_shield_paper/*.py
   # expect: no matches (all → E008)
   ```
3. Paper package green: `python -m pytest tests/nifty_shield_paper -q`.
4. `config_hash` still reproduces `c5b722ff…536c` from `config.py`.

## Hand-back

Report the commit hash, the four verification outputs, and confirm `strategies/nifty_shield_v1/`
+ `models/daytype/` were untouched. Do NOT merge/push. Claude reviews, then this surface is
ready for report assembly at window close.

## Guardrails

- Semantics-preserving re-pin only — zero change to counting, gates, evidence, or emitted signals.
- Frozen skeleton: edit values, never markers.
- No `strategies/nifty_shield_v1/` or `models/daytype/` change; `config_hash` stays `c5b722ff…536c`.
- OSC window 2016-02-11 → 2022-12-31 untouched.
