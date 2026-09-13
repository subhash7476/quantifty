# PTMS — P2 Substrate Certification Report

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS P2/P3 review, 2026-09-12
**Status:** **PARTIAL — C4 complete, C1 open, C2 NOT CERTIFIED (A1 permanent fail, A5 halt), C3 blocked.**
**Access level:** meta + substrate verification throughout. **No research-market-data read.**
No window spent, no construct code, no RFA.

This is the single per-surface report the ruling requires. It is **not** a certification pass
— three of four gates are open or blocked, and the per-surface rows below say so explicitly
rather than defaulting to "certified".

---

> **UPDATE 2026-09-13 — `PTMS_P2_CERTIFICATION_UPDATE_2026-09-13.md`.** Three of this report's
> statements have been overtaken by evidence, and the matrix below is not edited: **C3 is no longer
> blocked** (`cas_category` was stale, not short — rebuilt from the point-in-time futures bhavcopy
> to 2026-09-11, the 10 unmarked sessions marked, 28,660 bars); **C1's era rule now exists as code
> that refuses** (`core/market/bar_labeling.py`) with two agreeing arms for the native era and a
> store-wide census artifact; and the equity breadth 1m surface has a **scoped evidence row** for
> the Nifty-100 universe over 2023-01-02 → 2026-09-11. C1-a, A5 whole-panel and A6 whole-panel are
> unchanged and still open. **No surface is stamped CERTIFIED by that update either** — it carries
> evidence and its residuals, and the stamp remains the operator's.

## 1. Per-surface certification matrix

Columns are exactly those the ruling specified. **UNCERTIFIED means "not yet assessed",
BLOCKED means "assessed and failing", CERTIFIED means "arms passed".**

| Surface | Timestamp semantics | PIT / entity | Tradeability / synthetic | VIX status | Certified date range | Exposure-register status |
|---|---|---|---|---|---|---|
| **Index 1m — vendor era** (`NSE_INDEX\|Nifty 50`, `Nifty Bank`) | **OPEN (C1).** Observed first bar `09:16`, last `15:30`. Frozen candidate rule: **end-labelled** (bar stamped *t* covers *t−1 → t*), per AP-D4 | UNCERTIFIED (C2) | n/a pre-CAS; index rows correctly carry no synthetic marks | n/a | **NONE** — no range certified until C1 closes | **SPENT at signal level** — I-1 (feature, 2012→2025), I-4/I-5 (A), I-7/I-8 (analog path) |
| **Index 1m — native era** | **OPEN (C1).** Observed first bar `09:15`, last `15:29`. Frozen candidate rule: **start-labelled** | UNCERTIFIED (C2) | Post-CAS: index rows correctly unmarked; **the `volume = 0` predicate is `NSE_EQ`-only** | See VIX rows | **NONE** until C1 closes | **SPENT at signal level** — I-3 (pair research, 2023→2026); I-6/I-11 estimation (MSRP) |
| **Era boundary** | **Measured:** flip at **2023-01-02**; **2023-01-31 reverts to `09:16`**. Analog-path config independently brackets this (`vendor_last 2023-01-31`, `native_from 2023-03-01`), and AP-D4 resolves era by **observed first-bar stamp, not calendar date** — already handling 20 Jan-2023 sessions whose metadata disagreed with their labelling | — | — | — | — | — |
| **Equity breadth 1m** (~190→198 `NSE_EQ`) | Native era grid `09:15 → 15:29` | UNCERTIFIED (C2). `pit_membership` exists (898 sessions, 2023-01-02 → 2026-08-24) but is **not yet certified as a universe** rather than the writer's symbol set | **BLOCKED (C3)** — see §4 | n/a | **NONE** | **PARTIALLY SPENT** — E-1/E-2 (ISD TRAIN 2023-01-02 → 2024-11-30), E-3 (MRLC), E-6 |
| **1d index family** (149 latest / 200 max 2026) | Date-keyed, 00:00 naive | UNCERTIFIED (C2). **Sector/thematic membership is not PIT-tabled** | n/a | Canonical 1d VIX: 3,044 rows, 2014-05-14 → 2026-09-11 | **NONE** | D-1 (MSRP estimation), D-2 (CB-N50 TRAIN+HOLDOUT) |
| **Equity EOD** (7,158,443 rows) | Date-keyed | UNCERTIFIED (C2) | n/a | n/a | **NONE** | Q-1…Q-5 spent; **Q-6 CSMP sealed 2023-01 → 2026-06 UNREAD** |
| **Futures EOD** (1,495,989) | Date-keyed | UNCERTIFIED (C2) | n/a | n/a | **NONE** | F-1…F-6; Carry/TS-Basis/IVOL sealed windows spent; TS Basis Daily sealed **preserved** |
| **Options EOD** (index 5,490,319 → **2026-07-17**; stock 99,485,464 → present) | Date-keyed | UNCERTIFIED (C2) | n/a | n/a | **NONE** | O-1, O-2; the two stores' end dates differ — do not join naively across 2026-07-17 |
| **VIX 1m — canonical** (Upstox) | Native grid `09:15 → 15:29` | n/a (single series) | Index rows correctly unmarked | **C4 COMPLETE** — §3 | **2022-01-03 → 2026-09-11**, 1,165 sessions / 435,244 rows, **less the 88-session V2 quarantine** | **V-0b — exposure NONE (unread)** |
| **VIX 1m — vendor CSV** | Same convention as canonical (shift-0 join wins) | n/a | n/a | **C4 COMPLETE** — §3 | **2015-01-09 → 2025-03-04**, less quarantine (tail session dropped) | **V-0 — exposure NONE (unread)** |
| **VIX EOD — vendor CSV** | Date-keyed, DD-MM-YYYY, BOM | n/a | n/a | **C4 COMPLETE** — §3 | **2010-01-04 → 2025-06-05**, 5 disputed dates listed | **V-0c — exposure NONE (unread)** |

**No surface is certified for research use.** C1 gates everything intraday; C2 has not run;
C3 is blocked. C4 is complete but C4 alone does not make a surface usable.

---

## 2. Gate status

| Gate | Status | Detail |
|---|---|---|
| **C1 — timestamp semantics** | **OPEN** | AP-D4's `observed_bar_labeling` is the **frozen candidate semantic rule** per the ruling — to be independently verified and generalized store-wide, never rediscovered or replaced without contradicting evidence. Three arms: (a) vendor source spec — **needs the operator**; (b) cross-source bar-level shift test; (c) event anchoring on the 2020 circuit-breaker halts. The daily-close test is retired as insufficient |
| **C2 — PIT & entity** | **NOT CERTIFIED** (ran 2026-09-12) | Contract-shaped arms per PSB-1's template, plus certifying `pit_membership` as a universe and recording sector membership as non-PIT |
| **C3 — tradeability** | **BLOCKED** | §4 |
| **C4 — VIX** | **COMPLETE** | §3 |

---

## 3. C4 — VIX certification (complete)

### 3.1 Canonical 1m VIX vs vendor 1m CSV — **PASS**

| Measure | Value |
|---|---|
| Sessions compared | 789 |
| Bars compared | **294,131** |
| Exactly equal | **0.99980** |
| Mean abs difference | 0.000002 |
| Max abs difference | 0.0500 |
| Timestamp shift test (−1 / 0 / +1) | 8,227 / **8,249** / 8,227 → **shift 0**, same convention |

Promoted from one-off to a **standing check**: re-run as canonical coverage grows.

### 3.2 Vendor EOD CSV vs canonical 1d store — **PASS at tolerance, with 5 exceptions**

The previously unrun check, now run. 2,724 overlapping dates, 2014-05-14 → 2025-06-05.

| Measure | Value |
|---|---|
| Exactly equal | 0.26211 |
| **Within 0.01** | **0.99817** (2,719 / 2,724) |
| Mean abs difference | 0.003038 |
| Max abs difference | 1.0075 |

**The low exact-match rate is a precision artifact, not a disagreement.** The vendor quotes
four decimals (e.g. `22.0425`, `17.7225`) where the canonical store holds two. Reporting
"26% match" as a failure would be wrong; **99.82% agree within 0.01**.

**Five dates genuinely disagree and are quarantined pending resolution:**

| Date | canonical | vendor | diff |
|---|---:|---:|---:|
| 2021-02-12 | 23.05 | 22.0425 | **1.0075** |
| 2021-03-30 | 20.65 | 20.4850 | 0.1650 |
| 2018-11-07 | 17.88 | 17.7225 | 0.1575 |
| 2025-06-05 | 15.08 | 15.1950 | 0.1150 |
| 2024-01-20 | 13.80 | 13.7150 | 0.0850 |

2018-11-07 is a **Muhurat** session and 2024-01-20 an **NSE Saturday special** — both are
session-definition edge cases where "the close" is genuinely ambiguous, so three of the five
have a plausible benign explanation. 2021-02-12's 1.0075 does not and must be resolved
before the EOD series is used.

**Coverage over the overlap span:** vendor 2,734 dates, canonical 2,728; **10 vendor-only**,
**4 canonical-only**. The vendor CSV extends daily VIX back to **2010-01-04**, five years
before the canonical store's 2014-05-14 start — that prefix has **no independent check
available** and must be labelled single-sourced.

### 3.3 Quarantine lists — enumerated

Machine-readable: `PTMS_C4_QUARANTINE_LISTS.json`.

| Item | Extent | Disposition |
|---|---|---|
| **Vendor 1m invalid OHLC** | **2,547 rows across 28 sessions — a single contiguous run, 2018-12-10 → 2019-01-22** | Quarantine the run. The contiguity is itself evidence: one vendor feed incident, not scattered corruption |
| **Vendor 1m short sessions** | 29 sessions below 375 bars (excluding the special sessions below) | Ineligible; never pad |
| **Vendor 1m sub-minute stamps** | 100 sessions carry seconds ≠ 0 | Floor to the minute before any join, or the key breaks |
| **Vendor 1m truncated tail** | Final session **2025-03-05** ends 11:30 | Drop the partial session; certified range ends **2025-03-04** |
| **V2 — canonical VIX bars past 15:30** | **88 defect sessions**, 2022-03-24 → 2026-03-04 — 26 × 376 bars, 41 × 377, 21 × 378, running to 15:31/15:32 while the index pair stops at 15:30. Concentrated in 2022 (**83 of 88**); stragglers 2023 ×1, 2024 ×1, 2025 ×5, 2026 ×1 | Trim the trailing bars or quarantine the sessions; full list in the JSON. *(The >15:30 filter also catches 3 Muhurat evening sessions — correct data, separated in the JSON as `v2_muhurat_captured_by_filter_not_defects`.)* |
| **PRESERVE — Muhurat** | 2015-11-11, 2016-10-30, 2017-10-19, 2018-11-07, 2019-10-27, 2020-11-14, 2021-11-04, 2022-10-24, 2023-11-12, 2024-11-01 | **Correct data.** 60-bar evening sessions. Do not filter as anomalies |
| **PRESERVE — NSE Saturday specials** | 2024-03-02, 2024-05-18 | **Correct data.** 105 bars across two windows |

### 3.4 Provenance

Operator-stated: both CSVs are external-vendor downloads; the canonical 1m VIX rows were
fetched from **Upstox** via `scripts/fetch_upstox_historical.py` (yearly runs + split
retries, `is_synthetic = FALSE` upserts). `is_synthetic = FALSE` on index rows is **correct
by rule**. Neither CSV has a committed ingest script; both are gitignored. **C4 certifies the
data's internal consistency and its agreement with an independent source — it does not
certify the vendor.**

---

## 4. C3 — BLOCKED (operator ruling: no silent workaround)

The 10 post-CAS sessions **2026-08-31 → 2026-09-11** carry **zero** equity synthetic marks.
`cas_category.duckdb` ends **2026-08-28**, and `mark_file()` returns 0 when a session has no
Category I list — so an unmarked session is indistinguishable from a marked one.

Per the ruling, C3 clears only by **(i)** obtaining or fixing upstream Category-I coverage,
or **(ii)** an explicit operator-approved quarantine boundary. PTMS may not work around it.

Certification must additionally require that the marker **assert the Category I list is
non-empty** before marking, and be **re-run after any ingest touching post-CAS sessions** —
a historical backfill re-introduces exactly the defect the marker exists to fix.

**Consequence while blocked:** no post-2026-08-28 equity intraday data can be certified
tradeable, so any family needing recent breadth intraday is blocked at the substrate, not
at the budget.

---

## 5. What P2 still needs

| # | Item | Owner |
|---|---|---|
| 1 | **C1-a** — the vendor's own specification for the reference 1m bundle. The cheapest resolution of V1 and the only arm needing no inference | **Operator** |
| 2 | **C3** — fix upstream Category-I coverage, or approve an explicit quarantine boundary | **Operator** |
| 3 | 2021-02-12 VIX EOD discrepancy (1.0075) — resolve or permanently quarantine | Operator / P2 |
| 4 | C1-b and C1-c arms | P2 |
| 5 | C2 in full | P2 |
| 6 | L0 access layer implementing the certified rules, refusing unrecognized eras rather than guessing | P2 |

## 6. After P2 — the reconciliation the ruling requires

Certified surfaces must then be reconciled against the exposure register and **an eligible
window derived separately for each of the seven families**. Availability is never inferred
from physical coverage. Until that reconciliation exists, the P3 catalogue's availability
column is a register-derived expectation, not a determination — and **no RFA is authorized**.
