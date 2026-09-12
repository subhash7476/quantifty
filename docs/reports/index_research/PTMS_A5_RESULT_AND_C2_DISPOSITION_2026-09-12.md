# PTMS — A5 Contract-Suite Result and Updated C2 Disposition

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS C2 review, 2026-09-12
("A5: Run the existing PSB1 four-arm contract suite. Do not create a replacement screen.")
**Run:** `scripts/psb1/certify_substrate.py`, read-only, code commit `a41d033`.
Raw output preserved verbatim at `PTMS_A5_CONTRACT_SUITE_RUN_2026-09-12.md`.
**Access level:** substrate certification. No construct code, no RFA, no window spent.

**Result: CERTIFICATION INCOMPLETE — HALT.** Arms B and C pass; Arms A and D halt; three
structural guards and two regression guards fail.

**C2 verdict: remains NOT CERTIFIED.**

---

## 1. The suite's own summary

| Check | Result | Detail |
|---|:--:|---|
| **Arm A** intra-symbol CA-shape | **HALT** | 91 residue (76 dispositioned, **15 undocumented**); 2,739 large_genuine |
| **Arm B** cross-symbol handoff | PASS | 4 splice fabrications, all 4 dispositioned |
| **Arm C** prev_close identity | **PASS** | **0 violations** |
| **Arm D** factor evidence | **HALT** | 1,114 tested, **17 flagged, 0 dispositioned** |
| Structural: co-trading | PASS | 0 overlapping entities |
| Structural: double-apply | PASS | 0 double-apply keys |
| Structural: membership | **FAIL** | BACKUP FILE NOT FOUND |
| Structural: row count | **FAIL** | 7,154,268 (expected 7,030,920) |
| Structural: intervals | PASS | 4,133 rows; multi-interval symbols: 1 (DTIL ×2) |
| Structural: DVL→DTIL re-key | **FAIL** | DVL=1 DTIL=0 |
| Regression: PHILIPCARB 2018-04-19 | PASS | +4.9845% |
| Regression: DVL 2021-08-05 | **FAIL** | **+40.1746%** |
| Regression: DTIL 2021-08-05 | **FAIL** | **−33.4836%** |
| Regression: LITL prev_close | PASS | 57.6700 |

Store stamps: 7,154,268 rows, fenced MAX `2022-12-30`, unfenced MAX `2026-09-11`.

## 2. Reading the failures correctly — three distinct classes

Not every red cell is a substrate defect. Separating them is the whole value of this run.

### Class 1 — stale expectations, not defects (2 cells)

- **Row count "FAIL" (7,154,268 vs 7,030,920)** is the suite's *frozen PSB-1 expectation*
  meeting a store that has grown by three years. It is not a data defect.
- **Membership "FAIL — BACKUP FILE NOT FOUND"** is a missing environmental precondition, not
  a finding about the panel.

**A cross-confirmation worth recording.** The suite counts **7,154,268** rows where a direct
`count(*)` gives **7,158,443** — a difference of **exactly 4,175**, which is precisely the
C2-A2-2 unmapped-symbol row count. The suite drops rows whose symbol has no entity interval.
Two independently derived numbers reconciling to the row is strong evidence both measurements
are right.

### Class 2 — a repaired defect has REGRESSED (the serious finding)

Three cells point at one thing:

```
Structural: DVL->DTIL re-key      FAIL   DVL=1 DTIL=0
Regression:  DVL 2021-08-05 ret   FAIL   +40.1746%
Regression:  DTIL 2021-08-05 ret  FAIL   -33.4836%
Arm A:       DPL | DVL | 2021-08-05 | +40.2% | direction-mismatch | HALT
Arm D:       DVL | 2021-08-05 | 0.6667 | no_reprice+wrong_ratio  | HALT
```

PSB-1 identified and repaired the **DVL→DTIL corporate-action mis-key** — an NSE feed error
that registered a factor against the wrong symbol and fabricated a >|20%| return invisible to
a gap filter. The guard exists solely to detect its return. **It has returned.** The
fabricated +40.17% / −33.48% pair on 2021-08-05 is present in the store today, and the re-key
is absent (`DVL=1 DTIL=0`).

This is the standing lesson firing exactly as written: *a historical backfill re-introduces
every defect the backfill script was written to fix.* The repair lived in a repair script, not
in the ingest, so a later rebuild silently undid it.

**This is a live substrate defect on the equity panel, in the pre-fence era (2021), inside
windows that PSB-1, PSB-2 and CSMP all read.** It is reported, not repaired — repairing a
source-of-truth store is outside PTMS scope and requires committed, re-runnable code plus a
copy-first baseline.

### Class 3 — genuine open items (Arms A and D)

**Arm A — 15 undocumented.** Splitting them by date is decisive:

| Group | Count | Items |
|---|---:|---|
| **On or after 2026-07-21** | **11** | POCL 07-21, JLHL 07-24, IVZINNIFTY 07-31, TDPOWERSYS 08-24, CORDELIA 08-25, KIRLPNU 08-18, DSPGOLDETF 08-28, DSPSILVETF 08-28, INDIAGLYCO 09-02, TCC 09-04, HOPFL 09-11 |
| **Historical** | **4** | KWALITY 2010-06-15 (+45.9%), KILITCH 2012-09-24 (−39.9%), GULFPETRO/SAHPETRO 2013-07-09 (+81.6%), **DVL 2021-08-05 (+40.2%)** |

**The 11 recent ones share the root cause already established in C2-A2-2.** Every one falls
after ~2026-07-09, the point at which the mapping and corporate-action registers stopped being
rebuilt. They are CA events that happened and were never registered — the same staleness, seen
through a different arm. Their shapes (−90.0%, −89.8%: ETF unit splits; −50%, −60%, −79%:
splits/bonuses) are consistent with ordinary unregistered corporate actions, not corruption.

**The 4 historical ones are real open items**, and one of them is the DVL regression above.

**Arm D — 17 flagged, 0 dispositioned.** Three (DVL 2021-08-05, KWALITY 2010-06-15,
SAHPETRO 2013-07-09) overlap Arm A. The remaining 14 are `no_reprice` — a factor is registered
but the adjacent session shows no corresponding reprice. This is the evidence-screen class
PSB-1 built Arm D to catch, and none has a disposition-register entry.

## 3. Updated C2 disposition

| Arm | Status |
|---|---|
| A1 `pit_membership` circularity | **FAIL — PERMANENT BLOCKER.** Family F removed from executable families |
| A2-1 DTIL interval endpoint | Open — deterministic half-open correction specified. Note the suite independently reports the same single multi-interval symbol |
| A2-2 226 unmapped symbols | Dispositioned as **stale mapping tables** (all first-seen ≥ 2026-07-10). Independently corroborated by the suite's row-count delta of exactly 4,175 |
| A3 issuer-prefix linkage | **CERTIFIED and promoted repo-wide** (`DATA_STORE_MAP.md` §9b) |
| A4 `prev_close` identity | **PASS — now doubly confirmed.** My consecutive-session arm found 5 mismatches in 6,544,193 pairs; the suite's Arm C reports **0 violations** at entity grain |
| **A5 adjusted-series continuity** | **HALT.** Arms A and D do not clear; the DVL→DTIL repair has regressed |
| A6 sector/thematic PIT | **NOT PIT — UNUSABLE**, no current-membership substitution |

**C2 overall: NOT CERTIFIED**, and the ruling's two closing conditions now stand as:

1. **A1 has its explicit permanent disposition** — recorded, Family F removed. ✔
2. **A5 is resolved** — **not met.** The contract produced its report and the report halts.

## 4. What A5 requires to close (none of it authorized here)

1. **Repair the DVL→DTIL regression in the ingest, not in a repair script** — otherwise the
   next rebuild undoes it again, exactly as happened here. Copy-first baseline before any write.
2. **Rebuild the corporate-action and mapping registers past 2026-07-09**, then re-run. This
   should clear 11 of the 15 Arm A items and is the same remediation A2-2 already needs.
3. **Disposition or repair the 4 historical Arm A items and the 17 Arm D items.** Arm D's 14
   `no_reprice` factors are the evidence-screen class and need individual adjudication.
4. **Refresh the suite's frozen expectations** (row count, backup-file precondition) or run it
   against the fenced dev store it was written for — otherwise Class-1 noise recurs on every run.

## 5. Two process notes

**The closed PSB-1 artifact was not touched.** `docs/reports/psb/PSB1_SUBSTRATE_CERTIFICATION.md`
md5 `9ff273418cf22329b46810d73d94677e` before and after the run. The runner's `REPORT`
constant still points at the pre-reorganisation top-level path, so it wrote a *new* file; that
output has been relocated to `PTMS_A5_CONTRACT_SUITE_RUN_2026-09-12.md` so no misleading
duplicate of a closed battery's terminal artifact sits at the old location.

**The stale `REPORT` path is a latent hazard worth fixing outside PTMS.** Had the reports not
been reorganised into `docs/reports/psb/`, re-running this suite would have silently
overwritten a frozen terminal artifact. That is provenance loss by accident, not design.
