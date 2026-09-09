# PSB-1 Phase 1 — Third Lead Review (Prompt 1-B)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** commit `5af42f1` (Prompt 1-B; rebuild of R1 on gate-(b)'s classifier + D5).
**Prior reviews:** `PSB1_PHASE1_LEAD_REVIEW.md`, `PSB1_PHASE1_LEAD_REVIEW_2.md`.
**Protocol:** `PSB1_PROTOCOL.md` (FROZEN Rev 2).

## Verdict

**Implementation: PASS.** Every item of Prompt 1-B is delivered and independently verified.
The classifier is a line-exact transcription of gate-(b), `is_ca_shaped` and the constants are
imported (not copied), `scripts/csmp/` is untouched, 30/30 tests pass, and the implementer
disclosed the gap in D5's reach instead of burying it.

**Phase 2: REMAINS UNAUTHORIZED.** Not because of anything in `5af42f1`. Running R1 on real
data for the first time — which is what Prompt 1-B ordered — exposed a defect in the
**substrate**, and it is a different defect from the one D5 was locked to fix.

> **`equity_bhavcopy_adjusted` fabricates a return at every symbol rename.**
> **59 entities are affected — 51 in the dev window, 8 in the sealed window.**
> It is not a corporate action. It is mechanically repairable from data already in the store.
> **D5 was locked on a misdiagnosis, and its remedy would delete recoverable data.**

§11.3 earned its keep: on its first real run the stop rule caught a genuine data-integrity
defect. That is exactly what it exists to do. The correct response is to fix the data, not to
disposition the rows.

## First — a correction to my second review

My second review asserted the CA-ratio band was **±0.02 absolute**, that the panel held **365**
moves >|20%|, and that **~18** sat on a canonical CA ratio with no spanning factor. **All three
were wrong**, and DeepSeek was right to check the source rather than take them:

- `is_ca_shaped` uses a **relative** tolerance — `abs(survived - r) / r <= 0.02` — which at
  `r = 0.01` is a band of ±0.0002, not ±0.02. That is 25× tighter than I claimed.
- The screen is asymmetric (`ret ≤ −20%` **or** `ret ≥ +25%`) and drops gaps > 5 days. The real
  count is **235** screened moves, not 365.
- The real residue is **7 rows** (6 `CA-shaped-orphan` + 1 `direction-mismatch`), not ~18.

I verified the source this time; the numbers below are reproduced from my own run of the
harness against the real store, not from the implementer's report.

## Verified against `5af42f1`

| Item | How I verified | Result |
|---|---|---|
| 1–4 R1 on gate-(b)'s classification | diffed `classify_move` line-by-line against `audit_corporate_actions.py:276–296` — interval span `ptd < ex ≤ td`, `min` by `abs(f − survived)`, ±`MAGNITUDE_TOLERANCE`, then `is_ca_shaped`, then `genuine` | **PASS** — exact. `is_ca_shaped`, `MAGNITUDE_TOLERANCE`, `MOVE_LO/HI`, `MAX_GAP_DAYS` are **imported** from gate-(b), so the ratio test cannot drift from its source |
| 3 csmp untouched | `git show --name-only 5af42f1` → 4 files, none under `scripts/csmp/` | **PASS** |
| 4 five-bucket + exemption + interval-span tests | read them; the ex-date-on-a-non-trading-day case is a real regression test for the `td == ex` bug I flagged | **PASS** |
| 5 real dev-window scan reported | ran it myself: **235** screened; `genuine` 228, `CA-shaped-orphan` 6, `direction-mismatch` 1, `magnitude-mismatch` 0, `CA-explained` 0; register **7**; undocumented **6** → would HALT | **PASS** — reproduces exactly |
| 6 reports, does not raise | `scan_data_integrity` returns `CAScanResult`; `would_halt` is a property, no exception | **PASS** |
| 6 honest disclosure | the 43-row `genuine` table is in the report, including the rows that defeat D5 | **PASS** — and it is what let me find the defect below |
| D5.1–5.8 threading | read each: register = all residue documented-or-not (D5.1); C1/C4 + C2 formation (D5.2); C2 beta week (D5.3); C2 market mean (D5.4); C5 vol day (D5.5); C3 untouched, no `reg` param at all (D5.6); forward window excluded and **not** §4.2-imputed (D5.7); three never-merged counters (D5.8) | **PASS** |
| tests | `pytest tests/psb1/` | **30/30 pass** |

The implementer did what was asked, and the honest disclosure in item 6 is what made the real
defect findable. That deserves to be said plainly.

## The defect: adjustment factors are keyed to the symbol, the price history spans two

`adjustment_factors` is keyed by **symbol**. An entity that renames its ticker has a history
spanning two symbols. Backward adjustment scales a print at date *d* by the product of the
factors of *its own symbol* with `ex_date > d` — so a factor attached to the **post-rename**
symbol is applied to post-rename prints and **not** to the pre-rename prints of the *same
entity*. The entity's adjusted series therefore steps by exactly that factor on the rename date.

The prints, from the store — **the raw series is continuous in every case; only the adjusted
series breaks**:

```
entity COFORGE            raw_close   adj_close
2020-08-19  NIITTECH        2017.45     2017.45     <- no factor row: unadjusted
2020-08-20  COFORGE         2002.50      400.50     <- raw x 0.2      => adj move -80.15%

entity BAJAUTOFIN         raw_close   adj_close
2010-09-28  BAJAUTOFIN       793.60      793.60     <- unadjusted
2010-09-29  BAJFINANCE       774.60        7.75     <- raw x 0.01     => adj move -99.02%

entity INFOSYSTCH         raw_close   adj_close
2011-06-28  INFOSYSTCH      2865.30     2865.30     <- unadjusted
2011-06-29  INFY            2881.75      360.22     <- raw x 0.125    => adj move -87.43%
```

COFORGE: `400.50 = 2002.50 × 0.2`, and the only COFORGE factor is `(COFORGE, 2025-06-04, 0.2)` —
a 1:5 split whose ex-date is **in the sealed window**. Raw move −0.7%; adjusted **−80.15%**.

BAJAUTOFIN: raw move **−2.4%**; adjusted **−99.02%** — Bajaj Finance's 2016 and 2025 splits
(composing to 0.01) applied to `BAJFINANCE`'s prints and not to `BAJAUTOFIN`'s.

INFOSYSTCH: raw move **+0.6%**; adjusted **−87.43%**. `0.125 = 0.5³` — **Infosys' three 1:1
bonuses**, applied to `INFY` and not to `INFOSYSTCH`.

Identical mechanism for `SRTRANSFIN→SHRIRAMFIN` (×0.2, −79.8%) and `ANGELBRKG→ANGELONE` (×0.1,
−90.1%).

**This is why the surviving ratios look like corporate-action ratios: the fabricated jump *is*
the split factor.** `CA-shaped-orphan` fires on 0.1985, 0.2025, 0.0988 not by coincidence but
because the number *is* 0.2, 0.2, 0.1. The classifier is correctly reporting a missing factor —
the factor is missing from the **old symbol**, not from the market.

### Scope of the defect vs. contamination of the panel — two different numbers

**Defect scope** — every `symbol_changes` row whose post-rename symbol carries a later factor,
cross-checked against the factor table (of 1,050 renames, 991 adjust correctly):

| | count |
|---|--:|
| entities with a fabricated jump at the rename | **59** |
| …landing in the **dev** window (≤ 2022-12-31) | **51** |
| …landing in the **sealed** window (≥ 2023-01-01) | **8** |
| …caused **only** by sealed-window (≥ 2023) ex-dates | 25 |

**Panel contamination** — of the **235** moves R1 actually screens, **15 span a symbol rename**:
**5 of the 7 residue rows**, **9 of the 43 large `genuine` moves**, and 1 other. That 15 — not 51
— is the number a substrate rebuild should be sized against, and the number to quote for
"fabricated returns in the scored panel."

The two differ because a rename artifact is only *visible to R1* if it clears the >|20%| screen.
The rest are **sub-threshold and therefore invisible to every classifier keyed on that screen** —
DUCON's rename fabricates a −9.09% one-day return that R1 will never see, and which still enters
C1's 5-day formation return and C5's 252-day σ. **You cannot screen your way to a clean panel;
only an entity-grain repair removes these.**

Magnitudes run from −9% to **−99%**, and the list is a roll-call of the moves this battery has
been arguing about for two reviews:

| Entity | Rename | Date | Fabricated jump | Causing ex-dates |
|---|---|---|--:|---|
| BAJAUTOFIN | → BAJFINANCE | 2010-09-29 | **−99.00%** | 2016-09-08, 2025-06-16 |
| PAISALO | SEINV → | 2018-01-24 | −95.00% | 2024-03-20, 2022-06-30 |
| ABSHEKINDS | → TRIDENT | 2011-05-03 | −90.00% | 2019-12-13 |
| ANGELBRKG | → ANGELONE | 2021-11-11 | −90.00% | 2026-02-26 |
| **INFOSYSTCH** | **→ INFY** | 2011-06-29 | **−87.50%** | 2015-06-15, 2014-12-02, 2018-09-04 |
| CHOLADBS | → CHOLAFIN | 2010-06-22 | −80.00% | 2019-06-14 |
| ANDHRAPAP | ANDPAPER → | 2020-03-05 | −80.00% | 2024-09-11 |
| COFORGE | NIITTECH → | 2020-08-20 | −80.00% | 2025-06-04 |
| SHRIRAMFIN | SRTRANSFIN → | 2022-12-20 | −80.00% | 2025-01-10 |
| MOTHERSON | MOTHERSUMI → | 2022-06-09 | −55.56% | 2022-10-03, 2025-07-18 |
| DEWANHOUS | → DHFL | 2012-05-22 | −50.00% | 2015-09-09 |
| VAKRANGEE | VAKRANSOFT → | 2013-11-27 | −50.00% | 2017-12-21 |

(+47 more.) **`BAJAUTOFIN −99%` is the move D5 was written about.** It is not a demerger. It is
Bajaj Finance's 2016 and 2025 splits applied to half its own history. **`INFOSYSTCH −87.5%` is
Infosys.**

### Five of the six rows that would HALT the battery are this bug

R1's undocumented residue: ANGELBRKG, COFORGE, SHRIRAMFIN, VAKRANGEE, DEWANHOUS-2012 — **all five
are rename artifacts**. Only KWALITY (+45.9%, `direction-mismatch`, 2010-06-15) is not.

The detail that should settle any doubt: **DEWANHOUS appears twice.** Its −49.3% on 2012-05-22 is
the rename artifact — and it **HALTS the battery**. Its −42.6% on 2018-09-21 — the real DHFL
collapse — is classed `genuine` and **stays in the scored panel**. The stop rule is currently
halting on the fabrication and keeping the crash.

### Why gate-(b) could never have seen it

Gate-(b) partitions by **symbol** (`LAG(close) OVER (PARTITION BY symbol ...)`) over **raw**
prices. It never compares NIITTECH's close to COFORGE's, and in the raw series there is no
discontinuity to find. The defect is **invisible to gate-(b) by construction** and only appears
once an entity-level dedup stitches the two symbol series together. Gate-(b)'s certification of
the factor table is not impeached — it certified the right thing at the wrong grain for this
consumer.

### It reaches CSMP

`scripts/csmp/run_a2_validation.py:67–82` builds its panel with the **identical** entity-level
`rn=1` dedup over `equity_bhavcopy_adjusted`. **CSMP's A2 panel is therefore built from the same
contaminated series.** I have not re-run CSMP and make no claim about how much its banked numbers
move; that is for the operator and the CSMP owner. But it should be checked, and it is the reason
this cannot be handled as a PSB-1-local patch.

## What D5 gets wrong, and what it should govern

D5's premise is that an unadjusted corporate action is an **unrepairable** missing input, so the
name is simply not scorable across that window. For the dominant class that premise is **false**:

- The rename artifacts are **exactly repairable** from data already in the store — compose the
  cumulative factor across the entity's symbol chain (`symbol_changes` + `adjustment_factors` +
  `universe_eligibility`) instead of the symbol. **No new ingestion (D4-safe), no adjudication,
  no new parameter, no judgment call.**
- Applying D5 as pinned would instead **delete** the affected scoring windows — Infosys' among
  them — as "missing inputs," when the input is not missing, merely misapplied.
- It reaches **only what clears the >|20%| screen** (15 of the 235). The sub-threshold artifacts
  stay in the panel under D5, because D5's register is built from R1's screened moves.
- And it would leave the **sealed window contaminated** (8 renames land there; 25 of the 59 jumps
  are caused only by ≥2023 ex-dates). D5 cleans the dev panel; it does nothing for the
  out-of-sample test. A dev-window-only disposition cannot fix a defect that is also in the
  sealed window.

**Two notes for whoever implements the repair.** Renames can be **multi-hop** (A→B→C), so the
composition must be transitive across the whole chain, not a single hop. And **991 of the 1,050
renames already adjust correctly** — the fix must repair the 59 without disturbing them. Because
the defect is in the shared substrate and reaches CSMP, this is a **store rebuild**, not a
PSB-1 loader patch — which means changing a gate-(b)-certified artifact, and that is the
operator's call to authorize.

**After the repair, a real D5 population remains** — genuine corporate actions the factor table
never covered, by charter. **34 of the 43 large `genuine` moves are *not* renames**: ADANIENT
−82.8% (2015 demerger), IDFC −57.2%, MASTEK −66.0%, ARVIND −65.1%, JSL −60.9%, TATACHEM −56.5%,
ABREL −55.4%, and the six that the store *does* carry evidence for:

- **five with `purpose_raw = 'Spin Off'`** — SUVEN, GFLLIMITED, FEL, CGPOWER, ABIRLANUVO;
- **AURUM −98.8%**, a `DIVIDEND` row with **`ratio_or_fv = 974.00`** — a Rs 974 special dividend
  on a Rs 985.65 close, which *is* the −98.76% move, arithmetically.

Two **direct-evidence** channels exist in the store and D5's register consults neither:
`purpose_raw` matching spin-off / scheme-of-arrangement / capital-reduction (85 / 47 / 51 rows),
and `DIVIDEND` rows whose `ratio_or_fv` implies a drop past the move screen. These are evidence,
not heuristics, and should be wired in regardless of what else is decided.

For the residue no store evidence covers, the panel cannot currently distinguish an unadjusted
demerger from a genuine crash — **63MOONS −64.50%** (the 2013 NSEL collapse, apparently genuine)
and **ARVIND −65.09%** (a demerger) are 0.6pp apart and both classed `genuine`; **YESBANK −56.11%**
(2020 RBI moratorium) is *larger* than MOTHERSON's demerger. **No magnitude threshold separates
them** — I nearly recommended one, and the data refuted it. That residue needs operator
adjudication, and I am not going to pin its scope here.
*(Named events above are memory-identified, not adjudicated — they corroborate the point; they
are not the evidence for it. The evidence is the interleaving in the store's own ordered table.)*

## Required before Phase 2

**Blocking, in order:**

1. **Repair the adjustment defect at the entity grain** (59 entities). This is a substrate fix,
   not a PSB-1 fix, and it must cover the **sealed** window too.
2. **Re-run R1.** The residue and the 43-row `genuine` list will both shrink to their true
   population. Everything downstream of this decision should be re-derived from that run, not
   from the current one.
3. **Re-scope D5** on what actually remains, with the two direct-evidence channels wired in.
   D5 as locked was ruled against a misdiagnosis and, on the evidence, should be re-opened —
   still **pre-result**, which is the only moment it is free to change (§9).
4. **Check CSMP A2** for the same contamination.

**Not blocking, and unchanged:** the fee-dominance finding stands (planted gross +9.8%/yr nets
−3.1%/yr; §8 eligibility (ii) imposes a ~13pp/yr gross hurdle on C1–C4, ~0.4pp/yr on C5).

Nothing in Prompt 1-B needs to be redone. The harness is not the problem; it is the instrument
that found the problem.
