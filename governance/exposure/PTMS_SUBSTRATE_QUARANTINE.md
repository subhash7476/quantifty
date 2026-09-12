# PTMS — Substrate Quarantine Register

**Opened:** 2026-09-12 · **Updated:** 2026-09-12 (§6 — defective names dropped from the PTMS substrate) · **Authority:** operator instruction 2026-09-12 ("Quarantine DVL,
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


---

## 5. Update — 2026-09-12, after the CA refresh, rebuild and A5 re-run

Append-only, per §Contract. Full evidence:
`docs/reports/index_research/PTMS_A5_RERUN_AND_C2_REASSESSMENT_2026-09-12.md`.

| # | Entity | New status |
|---|---|---|
| **Q-1** | DVL / DTIL | **WITHDRAWN.** The §4 withdrawal condition is met in full: the `RE-KEYED` marker exists, the structural guard reads `DVL=0 DTIL=1 BONUS`, and both regression guards pass (DVL **−6.5503%**, DTIL **−0.2255%**). The entity is absent from every HALT list. Its data is sound and it is released from quarantine |
| **Q-2** | KWALITY 2010-06-15 | **RETAINED**, downgraded to *documented open item* — now dispositioned `evidence_exception` in Arms A and D. An evidence exception is a **recorded** unresolved `wrong_ratio`, not a resolution |
| **Q-3** | KILITCH 2012-09-24 | **WITHDRAWN.** Gone from Arm A entirely — the refreshed CA register supplies its factor |
| **Q-4** | GULFPETRO / SAHPETRO 2013-07-09 | **RETAINED**, same basis as Q-2 — now `evidence_exception` in Arms A and D |

**Correction to §1 of this register.** The claim that the PSB-1 disposition register's
docstring was "not true of the current store" regarding KWALITY and SAHPETRO in
`ca_evidence_exceptions` is **retracted — the docstring was right.** Both names now appear
there. The table was empty only because `record_evidence_exceptions()`, the CA pipeline's last
step, had never run. That is the same half-built-store cause as Q-1, seen from a third angle.

**§3's proposed atomicity fix stands and is still not implemented.** Nothing in the store
announced that it was half-built; three separate symptoms (a missing re-key, empty evidence
tables, and 15 undocumented Arm A items) each had to be traced back to it independently.


---

## 6. Update — 2026-09-12: defective names DROPPED from the PTMS research substrate

**Operator decision.** BSE CA refresh is deferred (BSE is not traded). The remaining defective
names are **dropped from the PTMS research substrate** on the stated rationale that they
mostly no longer trade on NSE and, where they do, sit outside the Nifty-200 universe.

**This is an exclusion, not a deletion.** No row is removed from the canonical store. PTMS
constructs must exclude these entities; every other consumer is unaffected.

### Dropped

| Entity / symbol | Defect | Last NSE session | In PIT universe? |
|---|---|---|---|
| DSPGOLDETF → **GOLDADD** | Arm A −90.0% 2026-08-28 (ETF unit split) | 2024-02-14 → 2026-09-11 | **never** |
| DSPSILVETF → **SILVERADD** | Arm A −89.8% 2026-08-28 (ETF unit split) | 2024-02-14 → 2026-09-11 | **never** |
| **IVZINNIFTY** | Arm A −89.9% 2026-07-31 (ETF unit split) | 2026-09-11 | **never** |
| **INDIAGLYCO** | Arm A −78.8% 2026-09-02 | 2026-09-11 | **never** |
| **KSE** | Arm A −62.2% 2026-08-17, magnitude-mismatch | 2026-09-11 | **never** |
| **GULFPETRO / SAHPETRO** (Q-4) | Arm A/D `evidence_exception`, wrong_ratio 2013-07-09 | 2026-09-11 / 2015-05-05 | **never** |
| **KWALITY** (Q-2) | Arm A/D `evidence_exception`, wrong_ratio 2010-06-15 | 2021-02-23 (delisted) | **YES — see below** |

### Verification of the rationale — it holds on the operative test, with one exception

The operative test is **PIT universe membership**, not existence. Checked against
`universe_membership` (35,000 rows, 634 symbols, 2012-01-31 → 2026-07-09):

- **12 of the 13 names checked have ZERO rebalances — never in the universe.** The rationale
  holds for every dropped name except one.
- **KWALITY is the exception: 8 rebalances, 2012-01-31 → 2016-06-30.** It *was* in the
  Nifty-200-style universe for four and a half years, so "outside the Nifty200 universe" is
  **not true of KWALITY**. Recorded rather than glossed.
  **Why dropping it is still defensible:** its defect date is **2010-06-15**, *before* its
  membership window opens. A `wrong_ratio` factor mis-scales the cumulative adjusted **level**
  from that date onward, but within 2012–2016 the mis-scaling is constant and therefore
  cancels in returns — the only return it distorts is the 2010-06-15 ex-date itself, outside
  every membership window. The drop is sound; the stated reason was not the operative one.

**The "no longer exists on NSE" half of the rationale does not hold**, and is recorded as such:
**9 of the 13 still traded on 2026-09-11** (GOLDADD, SILVERADD, IVZINNIFTY, INDIAGLYCO, KSE,
GULFPETRO, KILITCH, DVL, DTIL). Only DSPGOLDETF and DSPSILVETF (both renamed, not delisted),
KWALITY (2021-02-23) and SAHPETRO (2015-05-05) have stopped trading. Universe membership — not
existence — is what makes the drop safe.

### A fourth sighting of the same staleness

`universe_membership` runs to **2026-07-09** — the same boundary as the CA archive, the mapping
tables and the Arm A cluster. Four independent artefacts stop at one date. Refreshing the
universe and mapping tables (`build_universe.py`, `build_symbol_isin.py`) remains open work,
and is what A2-2 needs.

### Consequence for A5

Dropping these does **not** close A5: the contract suite reports on the whole store and will
keep HALTing on the 5 Arm A items until they are dispositioned in the PSB-1 register or the
store changes. What the drop settles is narrower and sufficient for PTMS — **no PTMS construct
may consume these entities**, so their defects cannot reach a PTMS result.
