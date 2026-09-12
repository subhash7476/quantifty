# PTMS — A5 Re-run and C2 Reassessment (post CA refresh + rebuild)

**Date:** 2026-09-12 · **Authority:** operator instruction 2026-09-12 ("refresh the CA
downloads first, then rebuild and rerun A5").
**Run:** `scripts/psb1/certify_substrate.py`, read-only, code commit `9a02f9b`.
Raw output: `PTMS_A5_CONTRACT_SUITE_RERUN_2026-09-12.md`.
**Baseline taken before any write:** `data/_baselines/equity_bhavcopy.pre_ca_rebuild_2026-09-12.duckdb` (704 MB).

**Result: the diagnosis was correct and the remedy worked.** Every Class-2 regression is
cleared, Arm D goes from HALT to PASS, and Arm A's undocumented residue falls from 15 to 5.
**C2 remains NOT CERTIFIED** — on A1, which no rebuild can fix, and on 5 remaining Arm A items.

---

## 1. Before → after

| Check | Before | After |
|---|---|---|
| **Structural: DVL→DTIL re-key** | **FAIL** `DVL=1 DTIL=0` | **PASS** `DVL=0 DTIL=1 BONUS` |
| **Regression: DVL 2021-08-05** | **FAIL** +40.1746% | **PASS** **−6.5503%** |
| **Regression: DTIL 2021-08-05** | **FAIL** −33.4836% | **PASS** **−0.2255%** |
| **Arm D** factor evidence | **HALT** — 17 flagged, **0 dispositioned** | **PASS** — 16 flagged, **all 16 dispositioned** |
| **Arm A** intra-symbol CA-shape | **HALT** — 91 residue, **15 undocumented** | **HALT** — 83 residue, **5 undocumented** |
| Arm B / Arm C | PASS / PASS | PASS / PASS |
| Structural: membership, row count | FAIL | FAIL (Class-1 stale expectations, unchanged) |

The fabricated +40.17% / −33.48% pair is gone, replaced by the documented values.

## 2. The diagnosis, confirmed by the store

The rebuild printed the single line the diagnosis predicted:

```
Factor override : re-keyed (DVL,2021-08-05,BONUS) -> DTIL
```

and the store now carries the marker that was absent before:

| Measure | Before | After |
|---|---|---|
| Factors with `RE-KEYED` in `source` | **0** | **1** — DTIL 2021-08-05, f=0.6667, re-keyed from DVL |
| `adjustment_factors` | 1,194 · max ex_date **2026-07-10** | **1,218** · max ex_date **2026-09-11** |
| `corporate_actions` | 11,965 · max **2026-07-31** | **11,976** · max **2026-09-11** |
| `ca_evidence_exceptions` | **empty** | **16 rows** |

**The store was half-built, exactly as diagnosed.** The committed override was correct all
along; the pipeline had stopped before reaching it. No pipeline code change was required to
fix Q-1 — a clean re-run was the entire remedy.

**A correction to my own record.** The quarantine register stated that the PSB-1 disposition
register's docstring was "not true of the current store" when it said KWALITY and SAHPETRO
appear in `ca_evidence_exceptions`. **The docstring was right.** Both now appear there as
`wrong_ratio`, and both are dispositioned in Arms A and D. The table was empty only because
`record_evidence_exceptions()` — the pipeline's last step — had never run.

## 3. The quarantined entities, re-assessed

| # | Entity | Before | After | Disposition |
|---|---|---|---|---|
| **Q-1** | DVL / DTIL | Arm A + Arm D HALT; both regression guards failing | **Absent from every HALT list; all three guards PASS** | **WITHDRAWN** — the §4 withdrawal condition is met in full |
| **Q-2** | KWALITY 2010-06-15 | Arm A + Arm D undocumented HALT | Arm A + Arm D **`evidence_exception`** | **Downgraded to documented open item.** Recommend keeping the PTMS quarantine — an `evidence_exception` is a *recorded* unresolved wrong-ratio, not a resolution |
| **Q-3** | KILITCH 2012-09-24 | Arm A undocumented HALT | **Gone from Arm A entirely** — the refreshed register supplies its factor | **Recommend withdrawal** |
| **Q-4** | GULFPETRO / SAHPETRO 2013-07-09 | Arm A + Arm D undocumented HALT | Arm A + Arm D **`evidence_exception`** | Same as Q-2 — **keep quarantined**, now documented |

Q-2 and Q-4 are the honest residue: the suite knows about them and excludes them by a
committed register, but their factors are still `wrong_ratio`. Keeping them in the PTMS
quarantine costs nothing and prevents a construct silently consuming a series the substrate
owner has flagged.

## 4. The 5 remaining Arm A items — all recent, one root cause mostly identified

| Entity | Symbol | Date | Return | Class |
|---|---|---|---:|---|
| DSPGOLDETF | GOLDADD | 2026-08-28 | −90.0% | CA-shaped-orphan |
| DSPSILVETF | SILVERADD | 2026-08-28 | −89.8% | CA-shaped-orphan |
| IVZINNIFTY | IVZINNIFTY | 2026-07-31 | −89.9% | CA-shaped-orphan |
| INDIAGLYCO | INDIAGLYCO | 2026-09-02 | −78.8% | CA-shaped-orphan |
| KSE | KSE | 2026-08-17 | −62.2% | **magnitude-mismatch** |

**Every one is 2026-07-31 or later**, i.e. inside the window the stale archive had missed.

- **The three ≈ −90% moves are the ETF unit-split signature.** The disposition register has an
  `ETF_SPLITS` set for exactly this class — *"an ETF unit split is a fund scheme action; it has
  no INE\* corporate-action factor"* — but these three post-date the committed register. Per the
  register's own contract, *"if the store changes, the register must be re-enumerated and
  re-committed — a new item NOT in the register HALTs."* **They are expected new register
  entries, not data defects.** Adding them edits a closed battery's register, so it is the
  operator's call, not a PTMS change.
- **INDIAGLYCO −78.8%** and **KSE −62.2%** need individual adjudication. KSE is a different
  class — `magnitude-mismatch` means a factor exists but the move does not match it.

**A refresh gap that remains.** The rebuild summary splits sources as **BSE dividend events
10,858** vs **NSE CF-CA events 1,196**. I refreshed only the NSE CF-CA archive; the BSE side
(`bse_ca_*.json`) is still stale. If INDIAGLYCO or KSE is BSE-sourced, a BSE refresh may clear
it. That refresh has **not** been run and no BSE downloader exists.

## 5. C2 reassessment

| Arm | Status |
|---|---|
| A1 `pit_membership` circularity | **FAIL — PERMANENT.** Unchanged and unchangeable by any rebuild; Family F stays substrate-blocked |
| A2-1 DTIL interval endpoint | **Open.** The suite still reports `multi-interval symbols: 1 (DTILx2)`; the half-open correction was not part of this work |
| A2-2 226 unmapped symbols | **Open.** The CA ingest does not rebuild `symbol_entity_intervals` / `symbol_isin` — that is `build_universe.py` / `build_symbol_isin.py`, not run here |
| A3 issuer-prefix linkage | **CERTIFIED**, promoted repo-wide |
| A4 `prev_close` identity | **PASS** — Arm C again reports 0 violations |
| **A5 adjusted-series continuity** | **Arms B, C, D PASS; Arm A HALT (5 undocumented).** Substantially improved, not closed |
| A6 sector/thematic PIT | **NOT PIT — UNUSABLE** |

**C2 overall: NOT CERTIFIED.** Two independent reasons — A1 (permanent, structural) and A5's
remaining Arm A residue. Note the second is now within reach: 3 of the 5 are register entries
and 2 need adjudication, where before there were 15 undocumented items and a live regression.

## 6. What would close A5

1. **Re-enumerate and re-commit the disposition register's `ETF_SPLITS`** for DSPGOLDETF,
   DSPSILVETF and IVZINNIFTY (operator call — it edits a closed battery's register).
2. **Adjudicate INDIAGLYCO 2026-09-02 and KSE 2026-08-17.**
3. **Refresh the BSE CA archive** — no downloader exists; this is the NSE gap's twin and the
   next thing to go stale silently.
4. **Refresh `symbol_entity_intervals` / `symbol_isin`** to clear A2-2, then re-run A2.
5. **Refresh the suite's frozen Class-1 expectations** (row count 7,030,920, the missing backup
   file) so real findings are not read alongside permanent stale-expectation noise.

## 7. Process record

- Copy-first baseline taken **before** any write: 704 MB, `data/_baselines/`.
- The closed PSB-1 terminal artifact is **untouched** — md5 `9ff273418cf22329b46810d73d94677e`
  before and after both runs.
- The runner's stale `REPORT` path wrote to the old top-level location again; the output has
  been relocated to `PTMS_A5_CONTRACT_SUITE_RERUN_2026-09-12.md`. This will recur on every run
  until the constant is fixed.
