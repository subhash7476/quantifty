# NiftyShield E007 — Completion Commit + Facts-DB Republish (implementer prompt)

**Role:** DeepSeek implements; Claude reviews green and re-pins the grant afterward
(standing split, `msrp-phase6-review-role`).
**Branch:** `feat/niftyshield-model-retrain` (current; do **not** merge or push).
**Author of this prompt:** Claude (review side). Operator granted E007 on 2026-08-11.

---

## Why this exists (the defect)

E007 (`nifty_shield_v1` retrained-model re-cert, CONFORMANT → CONFORMANT) was **granted by
the operator**, but the `code_ref` the grant was drafted against — **`d2410be`** — is an
**incomplete, test-red commit**:

- `d2410be` commits the retrained model artifacts (`models/daytype/logistic_13pm_prod/*`,
  `metadata.json` version `v2.0-train_thru2023`, 38 features) — the substantive retrain is
  in the commit.
- **But it left three trailing files stale**, so a clean checkout of `d2410be`:
  1. **fails a test** — `tests/daytype/test_daytype_facts.py::test_regime_fact_version_reflects_metadata`
     asserts `dt-v2.0-train_thru2025` while the committed model reports `dt-v2.0-train_thru2023`
     (observed: `1 failed, 6 passed`).
  2. **carries a stale provenance string** — `scripts/daytype/publish_facts.py:TRAINED_ON`
     still reads `D:\BOT\root vintage — NOT F:\nifty data`, directly contradicting the E007
     ledger text ("`TRAINED_ON = F:\Nifty … rides every fact row`").

A CONFORMANT `code_ref` cannot be a commit whose tests are red and whose provenance string
disproves the ledger entry. The fixes for all three are **already made and sitting uncommitted
in the working tree** — this task is only to **commit them into one green, self-consistent
commit** and **republish the facts DB from that committed code** (operator decisions,
2026-08-11).

The three uncommitted completion files (verify with `git status --short`):

```
 M scripts/daytype/publish_facts.py                    (TRAINED_ON → F:\Nifty string)
 M tests/daytype/test_daytype_facts.py                 (pin → dt-v2.0-train_thru2023)
 M tests/strategies/test_nifty_shield_v1_lazy_facts.py (fixture → dt-v2.0-train_thru2023)
```

**Do NOT touch these two files — they are Claude's re-pin step, already finalized (pinned to
the soon-to-be-superseded `d2410be`) and left uncommitted on purpose:**

```
 M docs/STRATEGY_PROMOTION_LEDGER.md
 M docs/strategies/nifty_shield_v1/datasheet.md
```

---

## Task 1 — the completion commit (green, self-consistent)

1. **Pre-commit gate — prove green first.** Run and paste output:
   ```bash
   python -m pytest tests/daytype/test_daytype_facts.py tests/strategies/test_nifty_shield_v1_lazy_facts.py tests/strategies/test_nifty_shield_v1_conformance.py -q
   ```
   All must pass (the two version-pin tests are the ones that were red at `d2410be`).

2. **Stage ONLY the three completion files** — never `git add -A` / `git commit -a`
   (that would sweep in the ledger/datasheet Claude owns):
   ```bash
   git add scripts/daytype/publish_facts.py tests/daytype/test_daytype_facts.py tests/strategies/test_nifty_shield_v1_lazy_facts.py
   git status --short   # confirm ONLY these 3 are staged; the 2 docs remain unstaged
   ```

3. **Commit** (message body verbatim; keep the Co-Authored-By line):
   ```
   fix: complete 13pm retrain provenance — TRAINED_ON + version test pins

   d2410be swapped logistic_13pm_prod to v2.0-train_thru2023 but left three
   trailing files stale, making the commit test-red and its provenance string
   self-contradictory:
     - publish_facts.py TRAINED_ON still named the D:\BOT vintage
     - test_daytype_facts + lazy_facts still pinned dt-v2.0-train_thru2025

   This commit makes the retrain self-consistent and green so it can serve as
   the E007 CONFORMANT code_ref. Model artifacts unchanged (model_hash
   bd0d6826…54be7 reproduces); only the provenance string and version pins move.

   Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
   ```

4. **Record the new hash:** `git rev-parse HEAD` (full) and `git rev-parse --short HEAD`.
   Call this **X** — it becomes the E007 `code_ref`.

---

## Task 2 — republish `day_type_facts.duckdb` from committed code

The certified facts DB (840 rows) was produced from the **uncommitted** publisher, so every
row carries `produced_by = offline@d2410be` (the red commit). Republish from committed code so
provenance is reproducible from **X**. The DB is **untracked** (regenerable; no git diff).

The publisher **skips already-existing dates** (`publish_facts.py:198`) and bakes the HEAD
short-SHA into `produced_by` (line 258) — so an incremental re-run writes nothing and leaves
`produced_by` stale. You must **clear the DB and rebuild the full range**.

1. **Copy-first backup** (baseline before any mutation):
   ```bash
   cp "data/features/day_type/day_type_facts.duckdb" "$TEMP/day_type_facts.pre-X.duckdb"
   ```
2. **Clear** so all rows rewrite at HEAD=X:
   ```bash
   rm "data/features/day_type/day_type_facts.duckdb"
   ```
3. **Republish** at HEAD=X (defaults are the certified range 2023-01-02 → 2026-07-03):
   ```bash
   python scripts/daytype/publish_facts.py
   ```
4. **Verify — all must hold** (paste the output):
   ```bash
   python -c "
   import duckdb
   con=duckdb.connect('data/features/day_type/day_type_facts.duckdb', read_only=True)
   print('rows      :', con.execute('SELECT COUNT(*) FROM day_type_facts').fetchone()[0])
   print('range     :', con.execute('SELECT MIN(session_date), MAX(session_date) FROM day_type_facts').fetchone())
   for c in ('regime_fact_version','model_hash','trained_on','produced_by'):
       print(f'{c:20}:', [r[0] for r in con.execute(f'SELECT DISTINCT {c} FROM day_type_facts').fetchall()])
   con.close()"
   ```
   Expected (only `produced_by` changes vs. the current DB):

   | field | expected |
   |---|---|
   | `rows` | **840** |
   | `range` | 2023-01-02 → 2026-07-03 |
   | `regime_fact_version` | `dt-v2.0-train_thru2023` (single value) |
   | `model_hash` | `bd0d6826a155f4b13a6aed03d76f8ab97401dcae3e5c9bf04bbcad2f56b54be7` (single value) |
   | `trained_on` | `F:\Nifty reference 1m 2012-2023 + DuckDB store; retrained v2.0-train_thru2023` |
   | `produced_by` | `offline@<X-short>` (single value — the NEW commit, **not** `d2410be`) |

   **If `rows` ≠ 840, STOP and report** — do not proceed. A short count means a source
   candle/VIX file changed availability; that is a substrate change, not a provenance fix,
   and must be surfaced, not papered over.

---

## Hand-back (report, do not self-grant)

Report back to Claude:

- **X** — full + short hash of the completion commit.
- Task-1 pytest output (the three suites green).
- `git status --short` proving only the 3 files were committed and the 2 docs remain
  unstaged/modified.
- Task-2 republish summary + the verification table above (confirm `produced_by = offline@<X-short>`
  and `rows = 840`).

**Do NOT edit** `docs/STRATEGY_PROMOTION_LEDGER.md` or
`docs/strategies/nifty_shield_v1/datasheet.md`, and **do NOT merge or push.** Claude reviews
X green, re-pins the E007 `code_ref` (ledger + datasheet §1) from `d2410be` → **X**, and files
the grant-record commit (the E006 code-then-ledger two-commit pattern). Only after that does the
operator decide on merge/push and the E008 PAPER window.

---

## Guardrails

- OSC index-options window **2016-02-11 → 2022-12-31 stays UNTOUCHED** — no backtest, no read.
- No frozen conformance corpus regeneration; no `config.py` change (`config_hash`
  `c5b722ff…536c` must stay reproducible — it is unchanged by this task).
- No `models/daytype/**` change (model_hash must stay `bd0d6826…54be7`).
- Commit specific paths only; the two grant docs are off-limits.
