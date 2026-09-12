# PTMS — Substrate Quarantine Register

**Opened:** 2026-09-12 · **Authority:** operator instruction 2026-09-12 ("Quarantine DVL,
DTIL, KWALITY, KILITCH, GULFPETRO and SAHPETRO from the research substrate").
**Scope:** PTMS research constructs only. This register does **not** modify
`scripts/psb1/disposition_register.py` — PSB-1 is a closed battery and its register is a
committed terminal artifact; a PTMS exclusion belongs in a PTMS register, so a later reader
can tell which one is load-bearing.

**Contract.** Exclusions are **data, not code**. No PTMS construct may reintroduce a
quarantined entity through a query-level filter, and none may rely on a quarantined entity's
adjusted series. Entries are append-only; a withdrawal is a new dated entry, never a deletion.

---

## Quarantined entities

| # | Entity / symbols | Date(s) | Class | Basis | Status |
|---|---|---|---|---|---|
| **Q-1** | **DVL** / **DTIL** (Dhunseri) | 2021-08-05 | Active substrate defect — CA mis-key | Arm A direction-mismatch +40.2%; Arm D `no_reprice+wrong_ratio` f=0.6667; regression guards DVL +40.1746% / DTIL −33.4836%; structural guard `DVL=1 DTIL=0` | **PROVISIONAL** — see §2. A committed fix exists and has simply not been applied; if the CA ingest is re-run successfully this entry should be **withdrawn**, not left standing |
| **Q-2** | **KWALITY** | 2010-06-15 | Unresolved historical | Arm A CA-shaped +45.9%; Arm D `wrong_ratio` f=0.5833 | Standing |
| **Q-3** | **KILITCH** | 2012-09-24 | Unresolved historical | Arm A CA-shaped-orphan −39.9% | Standing |
| **Q-4** | **GULFPETRO / SAHPETRO** | 2013-07-09 | Unresolved historical | Arm A direction-mismatch +81.6%; Arm D `wrong_ratio` f=0.4524 | Standing |

Quarantine is **entity-wide**, not date-scoped: a mis-keyed or unexplained factor corrupts the
cumulative adjusted series on **both sides** of its ex-date, so excluding only the event date
leaves fabricated levels in place. This follows the PSB-1 finding that such returns are
invisible to a gap filter.

**Registry check performed.** Neither `ca_evidence_exceptions` nor `ca_scope_exclusions` in the
live store contains **any** of these six names — both return zero rows. The PSB-1 disposition
register's docstring states KWALITY and SAHPETRO appear in `ca_evidence_exceptions`; that is
**not true of the current store**, and the reason is §2: the pipeline step that populates those
tables never ran. So these are new entries, not duplicates — but they *may* become duplicates
once the pipeline completes, at which point this register must be re-enumerated.

---

## 2. Why Q-1 is provisional — the diagnosis

Two earlier explanations were tested and **both are false**:

- **"The repair lived in a repair script, not the ingest."** Wrong. `FACTOR_OVERRIDES` is a
  committed constant in the canonical ingest (`scripts/csmp/ingest_corporate_actions.py:51`),
  applied by `apply_factor_overrides()` at line 867 of `main()`, and its own comment states it
  is *"applied after ingest, before the view is built, so it survives every rebuild."*
- **"`historical_backtest.py` left the store dirty."** Wrong. That harness copies the store
  (`_copy_store`) and its docstring states the real store is never mutated.

**The evidence that settles it:**

| Check | Result | Meaning |
|---|---|---|
| Factors whose `source` contains `RE-KEYED` | **0** | `apply_factor_overrides()` has **never run** against the current `adjustment_factors` table. It is the only writer of that marker |
| Raw feed `(DVL, 2021-08-05, 'Bonus 1:2')` rows | **exactly 1** | The override's guard ("expected exactly 1 row to re-key") would be **satisfied** — it did not fail, it did not execute |
| `ca_evidence_exceptions` / `ca_scope_exclusions` | **empty for all 6 names** | `record_evidence_exceptions()` — the **last** step of `main()` — also did not run |
| `adjustment_factors` | 1,194 rows, max ex_date 2026-07-10 | `purge_and_rebuild()` **did** run |

**One explanation covers every observation: the CA ingest ran `purge_and_rebuild()` and stopped
before `apply_factor_overrides()`.** Everything downstream of that call —
`apply_factor_overrides`, `register_relisting_factors`, `assert_no_orphan_factors`,
`build_adjusted_view`, `record_evidence_exceptions` — did not execute. The store is **half-built**,
not corrupted by a bad rebuild.

**Consequence for the operator's instruction.** "Fix the canonical CA/mapping pipeline" was
premised on the pipeline being wrong. On this evidence **the pipeline code is correct** and was
not run to completion. A clean re-run of `scripts/csmp/ingest_corporate_actions.py` is likely
the entire remedy for Q-1.

A collateral observation, recorded and not acted on: `corporate_actions` now carries the
**correct** BSE record `('DTIL', 2021-08-05, 'Bonus issue 1:2', BSE_538902)` alongside the
mis-keyed NSE row. The override may be partially redundant against the current feed — but that
is a design question for whoever owns the ingest, not a PTMS change.

## 3. The real pipeline defect worth fixing

Not the override — the **atomicity**. A pipeline that can leave `adjustment_factors` rebuilt
while the override, the orphan assertion, the adjusted view and the evidence tables are all
missing will silently present a half-built store as a finished one. Nothing in the store says
"incomplete"; it took a four-arm contract suite to notice.

Proposed fix (**not implemented**): run `main()`'s steps in a transaction, or write a
completion stamp as the final step and have readers assert it. This is the same class as the
recorded lessons that a gate over a time series needs an explicit contiguity check, and that a
freshness value printed but never asserted is documentation rather than a control.

## 4. Withdrawal condition for Q-1

Q-1 is withdrawn when **all** hold: `apply_factor_overrides` has run (a `RE-KEYED` source
marker exists); the regression guards report DVL −6.550% and DTIL at its documented value;
and the A5 re-run shows Arm A/Arm D clear of the 2021-08-05 items. Q-2 … Q-4 are **not**
withdrawn by a re-run — they are unresolved historical items needing individual adjudication.
