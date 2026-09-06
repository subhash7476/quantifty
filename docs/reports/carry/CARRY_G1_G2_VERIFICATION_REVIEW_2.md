# G1 / G2 Remediation — Verification Review, Round 2

**Reviewed:** 2026-07-21 · independent read-only verification of the corrections delivered
against `CARRY_G1_G2_VERIFICATION_REVIEW.md` (round 1).
**Method:** every claim re-measured against the stores and against NSE's live index files.
No claim accepted on report. Where round 1 named a required correction, the check is whether
the *requirement* is met — not whether an edit was made.

---

## Verdicts

| Round-1 item | Required correction | Verdict |
|---|---|---|
| **G1-1** timestamp schema split | normalize to `TIMESTAMP` across all files | **CLOSED — verified on all 2,762 files** |
| **G1-2** missing 2015 sessions | re-attempt, else document reduced warmup density | **OPEN — retry done, documentation not done, and the gap is larger than round 1 stated** |
| **G1-3** leftover CNX symbols | cosmetic, note only | **CLOSED as noted — 714 rows, 6 niche indices, Nifty 50 unaffected** |
| **G2-1** two incompatible taxonomies | pin one NSE vocabulary | **CLOSED — the fatal defect is genuinely fixed** |
| **G2-2** misclassifications from recall | source them, don't recall them | **OPEN — partially corrected, but still unsourced, and a measured 18% error rate remains** |
| **G2-3** entity-map dict collapse | resolve time-awarely | **OPEN in mechanism, nil in blast radius** |
| **G2-4** sector time-invariant | carry `valid_from`/`valid_to` | **CLOSED to the letter, not in substance** |

**Disposition.** Round 1's REJECT rested entirely on G2-1, and G2-1 is now genuinely fixed —
the redo succeeded on the thing that mattered. **P4 is no longer blocked by the taxonomy.**
What remains on G2 is bounded cleanup, not another redo.

**The freeze blocker has moved to G1.** The pre-registration's beta warmup claim is factually
wrong against the store as it now stands (§2 below). That must be resolved before freeze,
and it is a pre-reg decision, not an implementation defect.

---

## 1. G1 — what verified clean

**G1-1 — closed, exhaustively.** Not sampled: every one of the 2,762 daily files was opened
and its `candles.timestamp` column type read from `information_schema`.

```
ALL FILES type histogram: {'TIMESTAMP': 2762}
non-TIMESTAMP files: []
```

The 2023-01-01 split — which sat exactly on the TRAIN/HOLDOUT ↔ SEALED boundary — is gone.

**G1-3 — closed as noted.** Residual CNX rows measured across the full store, not the 2015
subset:

| Rows | Symbol |
|---:|---|
| 119 | `NSE_INDEX\|CNX High Beta` |
| 119 | `NSE_INDEX\|CNX Shariah25` |
| 119 | `NSE_INDEX\|CNX DEFTY` |
| 119 | `NSE_INDEX\|CNX Alpha Index` |
| 119 | `NSE_INDEX\|CNX Dividend Opportunities` |
| 119 | `NSE_INDEX\|CNX Low Volatility` |
| **714** | **total — all confined to 119 files in 2015** |

Six niche indices with no modern successor, exactly as reported. Independently confirmed:
**`NSE_INDEX|Nifty 50` appears exactly once in every one of the 2,762 files** — zero
duplicates, zero dual-identity rows for the index beta actually depends on.

---

## 2. G1-2 — OPEN, and materially worse than round 1 recorded

> **⚠️ SUPERSEDED IN PART, same day, by `CARRY_INDEX_REINGEST_SPEC.md`.** This section accepted
> the remediation report's claim that the missing 2015 sessions were unrecoverable — it checked
> the *count* but not the *conclusion*. Probing all 53 dates showed **46 are available right now**
> from the URL the ingest already uses, and the NSE archive reaches back to ~Q1 2012. **The
> recommendation below to move TRAIN to 2016-06-30 is withdrawn** — the blocker is fixed with
> data, TRAIN stays pinned at 2016-03-31, and only a factual correction to §9's wording is
> needed. The measurements in this section (53 missing, 202/248, beta computable 2016-05-26)
> remain correct as descriptions of the store *before* the re-ingest.

### The count

Measured against `trading_calendar` in `equity_bhavcopy.duckdb`, restricted to the store's
own span (on/after 2015-03-02, so the pre-ingest Jan–Feb window is not counted as a miss):

> **53 sessions missing**, essentially all contiguous between **2015-03-12 and 2015-06-10**.

Round 1 said 58; the remediation report says 65 gross / 55 net of holidays. The differences
are calendar-definition artifacts and are not worth reconciling — the number that matters is
that a **~3-month contiguous block of index history is absent**, and the remediation
correctly established that NSE's archive does not serve it.

### The finding round 1 missed — beta is not computable as pre-registered

`CARRY_PHASE0_PRE_REGISTRATION.md` §4 specifies a **trailing 252-day beta to Nifty**, and
§9 line 179 asserts:

> "beta warms up off 2010+ adjusted spot, so it does not consume futures formations"

**That is true of the stock leg and false of the market leg.** Verified:

- `equity_bhavcopy_adjusted` — MIN `2010-01-04`. The stock leg is fine.
- The only Nifty index series in the repo is the 1d store, which begins **2015-03-02**.
  The equity panel contains Nifty *ETFs* (`NIFTYBEES`, `AXISNIFTY`, …) but not the index.
- Index sessions available as of TRAIN's first formation **2016-03-31: 215**. A 252-session
  lookback is **not satisfiable at all** — the window would have to run past the store's start.
- Restricting to the nominal trailing year 2015-03-31 → 2016-03-31: **202 of 248 sessions
  present (81.5%)**, because the missing block sits inside it.
- **The earliest date at which a full 252-session beta exists is 2016-05-26.**

So the first ~2 monthly formations of the pinned TRAIN window (2016-03-31, 2016-04-29) cannot
carry a spec-compliant beta, and the third is marginal. The neutralization would either
silently shorten the window or silently stretch it across a 13-month calendar span — and
either way §4's stated method is not what runs. `neutralize.py` does not exist yet
(pre-reg §12 lists it as to-be-created), so the pre-reg text is currently the only authority,
and the text is wrong.

**This is a freeze blocker, and it is an operator decision, not an implementation bug.**
Three exits, all legitimate, none selectable after seeing results:

1. **Move TRAIN start to 2016-06-30** — costs ~2 of ~58 formations, keeps §4 exactly as
   written. Cleanest, and the cost is trivial.
2. **Pin a shorter beta window** (e.g. 126 sessions) for the whole sleeve — changes §4 for
   every formation, not just the early ones. Acceptable, but it is a methodology change and
   must be justified on grounds other than convenience.
3. **Pin an explicit ramp** — "beta uses min(252, available) sessions, floor 120" — and state
   in §9 which formations run degraded. Most honest about the data, most moving parts.

Recommendation: **(1)**. It is the only one that costs nothing but two formations and leaves
the pre-registered method untouched. Whichever is chosen, §9's "does not consume futures
formations" sentence must be corrected — as written it is a false statement about the substrate.

---

## 3. G2-1 — CLOSED. The fatal defect is genuinely fixed

This was the blocking defect and it is properly resolved. Measured on the produced
`governance/carry/sector_classification.csv` (363 names):

- **20 labels total**, all of them NSE macro-sector labels.
- **Every label used by Tier 2 and Tier 3 also appears in Tier 1.** There is no parallel
  vocabulary and no tier-only label.
- The round-1 splits are gone: IT names are `Information Technology` in all three tiers,
  pharma is `Healthcare`, auto is `Automobile and Auto Components`, oil is
  `Oil Gas & Consumable Fuels` — regardless of tier.

Tier membership therefore no longer encodes size/survivorship into the sector dummies, which
was the actual mechanism by which §4 neutralization would have been contaminated.

Tier counts: **Tier 1 = 285 sourced · Tier 2 = 18 inherited · Tier 3 = 60 manual ·
UNCLASSIFIED = 0.**

Sourcing was also independently re-derived: re-downloading `ind_nifty500list.csv` and parsing
it with a proper CSV reader reproduces the script's naive `split(",")` result **exactly**
(500 names, 0 label differences), so Tier 1 is genuinely NSE-sourced and the parse is not
silently corrupting rows today. *(Note: `line.split(",")` remains latently fragile — a company
name containing a comma would shift the fields and silently drop the name. It does not bite on
the current file. LOW.)*

---

## 4. G2-2 — OPEN. The register was corrected, not sourced — and the error rate is measurable

Round 1 required: *"shrink the manual register to genuinely dead names only, recording per
name the evidence used."* Neither half was done.

- The register still holds **60 names — 19 dead plus 41 under the comment "Live names outside
  Nifty 500"**. It was not shrunk to dead names.
- **No evidence column exists** in the register or in the output CSV. The labels are better
  recall, but they are still recall.

### The 18% error rate is not a hypothetical — it is measured

Tier 1 sources only from Nifty 500 (the 13 sectoral files add 5 names; the union is 505).
**NSE publishes `ind_niftytotalmarket_list.csv` — 750 names, same `Industry` column, same
taxonomy.** It was not used. Downloading it sources **17 of the 60 hand-register names**, and
against NSE as the pinned authority, **3 of those 17 hand labels are wrong**:

| Symbol | Hand label | NSE label | Business |
|---|---|---|---|
| `JUSTDIAL` | Services | **Consumer Services** | local search |
| `PTC` | Services | **Power** | PTC India — power trading |
| `KSCL` | Chemicals | **Fast Moving Consumer Goods** | Kaveri Seed — agri |

That is a **17.6% error rate on the checkable subset**, and there is no reason the 43
uncheckable names carry a lower one.

### The errors cluster in catch-all buckets — the G2-1 mechanism in miniature

The two `Services` errors are not incidental. The hand register assigns `Services` to exactly
**4 names — `JETAIRWAYS`, `RNAVAL`, `JUSTDIAL`, `PTC`** — an airline, a shipbuilder, a local
search portal and a power trader. Both of the two that NSE can adjudicate are **wrong**, and
both belong in different sectors. `Chemicals` shows the same shape: 5 hand-assigned names, the
only checkable one (`KSCL`) wrong. Round 1 flagged `IT` and `Chemicals` as recall catch-alls;
the catch-all has simply moved to `Services`.

This is the G2-1 contamination mechanism at reduced scale: unrelated businesses collapsed into
one dummy, and the collapse correlates with *"we could not source this name"* — which again
correlates with size and survivorship. It is much smaller than round 1's defect (a handful of
names, not 156) but it is the same failure, so it should be fixed by sourcing rather than by
re-typing.

**Severity: MEDIUM.** It does not re-block P4 the way G2-1 did — but it is cheap to fix and
the fix is mechanical.

---

## 5. G2-3 — mechanism still collapses; blast radius nil on this universe

`get_entity_map_time_aware()` genuinely loads intervals ordered by `valid_from`, so the
round-1 "whichever row arrives last, arbitrarily" defect is gone. But the consumer then does:

```python
entity = intervals[-1][2]      # g2_ingest_sector_classification.py:212
```

— it takes the **most recent** entity and discards the intervals. The load is time-aware; the
use is not. For a recycled ticker this assigns the successor business's sector to the
predecessor's entire history, which is exactly the documented `DTIL` failure mode.

**Measured impact on this universe: zero.** All 18 Tier-2 names (`MOTHERSUMI`, `LTI`, `LTIM`,
`TATAGLOBAL`, `NIITTECH`, `CADILAHC`, `SRTRANSFIN`, …) are renames or mergers where inheriting
from the successor is the *correct* answer, and none is a recycled ticker. So this is not
blocking — but the mechanism must not be carried into the certified path, where the universe
is not hand-checkable.

---

## 6. G2-4 — closed to the letter, not in substance

The output now carries `valid_from`/`valid_to`, so a later fix is not a re-key — which is
literally what round 1 asked for. But **every one of the 363 rows carries the identical pair
`2016-02-11` → `9999-12-31`**. Sector remains time-invariant in content; only the schema moved.

Two consequences to note rather than fix:

- `PEL` (pharma → NBFC) and the demerged Tata Motors entities are still single-sector for all
  time. `PEL` is now labelled `Financial Services` across a window in which it was pharma.
- `valid_from = 2016-02-11` means an interval join yields **no sector before 2016-02-11**.
  Harmless given TRAIN's first formation is 2016-03-31 — but it is an unstated coupling
  between the sector master and the window pin. If the beta fix moves TRAIN (§2), re-check it.

---

## 7. Reproducibility gap

`governance/carry/nse_industry_sourced.csv` (363 rows, 285 populated + 78 blank) exists in the
governance directory but **no committed script produces it** —
`g2_ingest_sector_classification.py` writes only `sector_classification.csv`. It is a useful
provenance record; it should either be emitted by the script or deleted. An unreproducible
artifact in `governance/` is precisely what the certification discipline exists to prevent.

---

## 8. Required corrections — round 2

**Operator, before freeze (blocking):**

1. **Resolve the beta warmup (§2).** Pick exit (1), (2) or (3) and write it into the pre-reg.
   Correct the false sentence at §9 line 179. This must be pinned before any TRAIN read.

**Implementation (issue to DeepSeek — see prompt below; none of this re-blocks P4):**

2. Add `ind_niftytotalmarket_list` to Tier 1 sourcing; re-run; the hand register should shrink
   by ~17 names automatically.
3. Adopt NSE's label wherever it disagrees with the hand register — `JUSTDIAL`, `PTC`, `KSCL`
   are confirmed corrections, and any further disagreement surfaced by the wider source is
   resolved the same way. NSE is the pinned authority; these are not judgment calls.
4. Add an `evidence` column recording, per name, where its label came from
   (`nse_index:<file>`, `entity_inherit:<sibling>`, or `manual:<reason>`).
5. Resolve Tier 2 per-interval rather than `intervals[-1]`, and emit real `valid_from`/
   `valid_to` per interval instead of the hardcoded pair.
6. Emit `nse_industry_sourced.csv` from the script, or delete it.

**Not required:** another G2 redo. The taxonomy is single-sourced and consistent; that was the
blocking defect and it is closed.

---

## 9. Implementation prompt — G2-R (cleanup, issue as-is)

> **Task: G2-R — sector classification cleanup.** Edit
> `scripts/g2_ingest_sector_classification.py` only. Do not touch the pre-registration.
>
> 1. **Widen Tier 1.** Add `ind_niftytotalmarket_list` to `NSE_INDEX_FILES`. Replace the
>    `line.split(",")` parse with `csv.DictReader`, reading the `Symbol` and `Industry`
>    columns by name. Verified: this reproduces the current 500-name result exactly, and the
>    total-market file adds 750 names on the same taxonomy.
> 2. **Shrink the register mechanically.** After the widened Tier 1 runs, any name still in
>    `MANUAL_SECTORS` that is now sourced must be **deleted from the dict**, not left to be
>    shadowed by the `if k in remaining` filter. Expect ~17 deletions, including `JUSTDIAL`,
>    `PTC`, `KSCL`, `ARVIND`, `GNFC`, `GSFC`, `DCBBANK`, `KTKBANK`, `SOUTHBANK`, `RAIN`,
>    `VGUARD`, `METROPOLIS`, `HCC`, `ICIL`, `STAR`, `APLLTD`, `PCJEWELLER`.
> 3. **Add an `evidence` column** to the output CSV, populated per name:
>    `nse_index:<filename>` for Tier 1, `entity_inherit:<sibling_symbol>` for Tier 2,
>    `manual:delisted` / `manual:unsourced` for Tier 3. A Tier-3 row that cannot state why it
>    is manual is a defect, not a row.
> 4. **Fix Tier 2 to be time-aware in use, not only in load.** Emit one row per
>    `(symbol, entity-interval)` with that interval's real `valid_from`/`valid_to`, inheriting
>    the industry of that interval's entity. Do not use `intervals[-1]`.
> 5. **Emit `nse_industry_sourced.csv`** from the script (symbol, sector, source), so the
>    provenance artifact is reproducible.
> 6. **Report per tier after the re-run**: names, cells, % cells, and the count of remaining
>    manual names split `delisted` vs `unsourced`.
>
> **Falsifiable predictions — state pass/fail on each before reporting anything else:**
> - Tier 1 rises from 285 to ≈302; Tier 3 falls from 60 to ≈43.
> - The label set stays at ≤20 labels and every Tier-2/Tier-3 label remains a subset of Tier 1.
> - `UNCLASSIFIED` remains 0.
> - `JUSTDIAL` becomes `Consumer Services`, `PTC` becomes `Power`, `KSCL` becomes
>   `Fast Moving Consumer Goods` — all three from the NSE file, none hand-typed.
> - No name changes sector for any reason other than a sourced NSE label replacing a hand label.

---

## 10. What round 2 does not certify

This review verifies the **G1/G2 remediation against round 1's requirements**. It is not a
substrate certification. The carry substrate suite (P2, `CARRY_SUBSTRATE_CERTIFICATION_SPEC.md`)
is unrun, and nothing here substitutes for it. Windows are untouched: **SEALED 2023-01-01 →
2026-07-20 remains unread; HOLDOUT 2021–2022 unspent; no TRAIN read has been taken.**
