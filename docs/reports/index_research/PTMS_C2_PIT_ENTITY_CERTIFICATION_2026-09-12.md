# PTMS — C2 PIT & Entity Certification

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS P2 certification review, 2026-09-12
("C2: BEGIN NOW. Do not wait for C1-a or C3").
**Access level:** meta + substrate verification. **No research-market-data read.** No window
spent, no construct code, no RFA.

**Verdict: C2 FAILS on one arm and passes four.** The failure is material for exactly the
family that was still CONDITIONAL.

| Arm | Result |
|---|---|
| **A1 — `pit_membership` universe validity** | **FAIL — the table is circular** |
| A2 — entity handoffs | **PASS with 2 defects** (1 boundary-touch, 226 unmapped symbols) |
| A3 — ISIN linkage | **PASS with a newly recorded hazard** (issuer-prefix rule must not be applied to fund ISINs) |
| A4 — `prev_close` identity | **PASS** — 5 mismatches in 6,544,193 pairs |
| A5 — adjusted-series continuity | **INCONCLUSIVE by this screen** — defer to the existing contract suite |
| A6 — sector / thematic PIT status | **NOT PIT — recorded as unusable** |

---

## A1 — `pit_membership` is circular (FAIL)

`data/isd/pit_universe.duckdb:pit_membership` — 173,900 rows, 898 sessions, 229 distinct
symbols, 2023-01-02 → 2026-08-24.

**`intraday_present` is `TRUE` on all 173,900 rows. There is not one `FALSE`.**

Per-session counts match the 1m file's `NSE_EQ` symbol count exactly:

| Session | pit rows | `intraday_present` | file `NSE_EQ` symbols | in pit but absent from file |
|---|---:|---:|---:|---:|
| 2023-06-15 | 189 | 189 | 189 | **0** |
| 2025-06-16 | 196 | 196 | 196 | **0** |

Per-session symbol count across all 898 sessions: min 188, median 194, max 200 — the same
190→198 envelope as the store itself.

**The table is therefore derived from the file's symbol set.** It answers *"which names did
the ingest write on date D"*, not *"which names were investable on date D"* — and those are
different questions. This is precisely the recorded pitfall: *a per-day 1m file's symbol set
is whichever universe its writer used, not a universe.*

**What survives.** `fno_member` (139,819 TRUE / 34,081 FALSE) is genuinely independent —
sourced from the F&O master, not from the candle files. The *eligibility* dimension is
usable; the *membership* dimension is not.

**Consequence.** The breadth-1m surface has **no non-circular PIT membership table**. A
cross-sectional construct on it cannot establish that its universe is survivorship-free: a
name investable on date D but absent from the ingest is invisible, and a name added to the
ingest later appears to "not exist" before its first written date. The alignment record's
caution — *do not upgrade ISD's certification to survivorship-free* — is now measured rather
than suspected.

**This is a substrate blocker for Family F**, independent of budget. Remedying it requires
an independent PIT universe (e.g. `fo_eligible_intervals` + a listing/delisting source),
built and certified — not a re-read of the panel.

## A2 — Entity handoffs (PASS with 2 defects)

`symbol_entity_intervals`: 4,133 intervals · 3,615 entities · 4,132 symbols · **0** null
entities · **0** inverted intervals · 450 multi-symbol entities (renames, expected) · **1**
recycled ticker.

**Defect A2-1 — one ambiguous boundary day.** The recycled ticker is **DTIL** (the known
case), and its two intervals **share an endpoint**:

```
DTIL  2010-01-04 -> 2010-07-26  entity DPL
DTIL  2010-07-26 -> 9999-12-31  entity DTIL
```

A row dated exactly **2010-07-26** matches *both* intervals. This is a closed-vs-half-open
interval convention error, not a data error: one day resolves to two entities. Fix by making
intervals half-open `[valid_from, valid_to)`, or by moving the predecessor's `valid_to` back
one session.

**Defect A2-2 — 226 panel symbols have no interval at all.** 199 `EQ` + 27 `BE`, totalling
**4,175 rows** (0.058% of 7,158,443). Confirmed clean in the other direction: for every
symbol that *does* have an interval, **zero** panel rows fall outside it. So the gap is
purely unmapped symbols, not mis-dated intervals.

## A3 — ISIN linkage (PASS, with a hazard now on record)

`symbol_isin`: 3,639 rows · 0 nulls · **0 symbols with multiple ISINs** · 294 ISINs shared
by more than one symbol.

**144 issuer prefixes carry more than one ISIN — and they are not one population:**

| ISIN class | Prefixes with >1 ISIN | What it means |
|---|---:|---|
| **INE** (equity) | **81** | Genuine issuer-level linkage cases — the PHILIPCARB/PCBL class (face-value re-issue) and renames: `INE010B01` → CADILAHC/ZYDUSLIFE, `INE619A01` → RUCHISOYA/PATANJALI |
| **INF** (mutual fund / ETF) | **52** | **Hazard — must NOT be merged** |
| **IN0** | 11 | Mixed; treat as INF until classified |

**The hazard, stated plainly.** Applying the issuer-prefix linkage rule to `INF` ISINs would
fabricate entity unions on a large scale. `INF109KC1` covers **34 distinct ISINs across 42
ICICI ETF symbols** — SILVERIETF, GOLDIETF, BANKIETF, FMCGIETF and so on. These are
genuinely different funds from one AMC, not one company re-issued. Merging them would create
a single fictitious "entity" spanning silver, gold, banking and FMCG.

Also note `INE005A11` → ICICI0202/ICICI1298/ICICI0901/ICICI0801: an `11` ISIN series
indicates **debentures**, not equity. Issuer-prefix linkage must be gated on ISIN class *and*
security-type series, not on the prefix alone.

**Certified rule for PTMS:** apply issuer-prefix linkage to `INE…01` equity ISINs only;
`INF`/`IN0` and non-`01` series are excluded and carry no entity union.

## A4 — `prev_close` identity (PASS)

Comparing `prev_close` against the previous session's `close` for the same symbol, **restricted
to genuinely consecutive trading sessions** via `trading_calendar` row numbering:

| Measure | Value |
|---|---:|
| Comparable consecutive-session pairs (`EQ`) | **6,544,193** |
| Mismatches > 0.01 | **5** |
| Mismatches > 2% | **2** |
| Of the 5, on a CA ex-date | 2 |

**A methodological note worth keeping.** The unrestricted version of this query — lagging over
stored rows without requiring calendar adjacency — reports **7,687** mismatches. Nearly all of
those are non-trading gaps, not defects. The consecutive-session control is what makes the arm
meaningful, and an uncontrolled version of this check would have produced a false alarm three
orders of magnitude too large.

## A5 — Adjusted-series continuity (INCONCLUSIVE by this screen)

A naive screen over `equity_bhavcopy_adjusted` — |return| > 20% between consecutive trading
sessions, excluding CA ex-dates — returns **3,087 observations across 866 symbols** (0.047%).

**This is a screen output, not a defect count, and must not be reported as one.** Genuine
>20% single-session moves occur routinely outside the derivatives universe, and the recorded
lesson is precisely that *fabricated* adjusted returns from CA mis-keys are **invisible to a
gap filter** — they must be caught at entity grain with zero structural filters.

**Disposition:** defer to the existing certified instrument — the four-arm contract suite
(`scripts/psb1/contract_arms.py`, driven by `scripts/psb1/certify_substrate.py`), which was
built for exactly this and caught all three defect classes. **Re-run it; do not
re-implement it.** A5 stays open until that run produces a report.

## A6 — Sector / thematic index membership (NOT PIT)

No PIT membership table exists for sector or thematic index constituents. `universe_membership`
covers the NIFTY-200-style liquidity universe (`rebalance_date, symbol, rank, turnover_median,
method`), not sector indices. **Recorded status: sector/thematic membership is NOT
point-in-time and is certified UNUSABLE for cross-sectional work** until such a table exists.
Treating current membership as historical injects survivorship bias directly.

---

## Summary and what C2 changes

1. **A1's failure is the headline.** The breadth-1m surface's only PIT membership table is
   circular. Family F — the strongest CONDITIONAL candidate in the P3 catalogue — is now
   **substrate-blocked**, not merely budget-constrained. This is a determination about the
   substrate, not an availability inference from physical coverage.
2. **A3 adds a rule the repo did not have**: issuer-prefix linkage is an *equity-ISIN* rule.
   Generalizing it to fund ISINs would fabricate entity unions across 42 unrelated ICICI ETFs.
3. **A2's two defects are small, bounded and fixable** — one interval-convention day, 226
   unmapped symbols (0.058% of rows).
4. **A4 passes cleanly**, and records why the uncontrolled version of the check is misleading.
5. **A5 requires the existing contract suite to be run**, not a new screen.

**C2 verdict: NOT CERTIFIED.** A1 fails; A5 is open pending the contract-suite run.

---

## Dispositions (operator ruling, C2 review 2026-09-12)

### A1 — PERMANENT BLOCKER

`pit_membership` is circular **and may not be repaired by deriving another universe from the
same candle panel** — any such derivation reproduces the circularity. **Family F is
SUBSTRATE-BLOCKED, permanently, unless an independent PIT universe is separately sourced and
certified.** Family F is removed from the list of potentially executable PTMS families; it is
not to be rescued without that independent universe.

### A2-1 — DTIL endpoint convention

Deterministic correction required: make `symbol_entity_intervals` **half-open**
`[valid_from, valid_to)`, or move the predecessor's `valid_to` back one trading session.
Either removes the two-entity ambiguity on 2010-07-26. **Not to be left silently passing.**

### A2-2 — the 226 unmapped symbols: enumerated and dispositioned

Full list: `PTMS_C2_A2_UNMAPPED_SYMBOLS.json`. The enumeration settles the class cleanly:

| Property | Value |
|---|---|
| Symbols | 226 (199 `EQ` + 27 `BE`), 4,175 rows |
| **First seen** | **all 226 in 2026**, earliest **2026-07-10** |
| Last seen | all 226 in 2026 (still trading) |
| Rows per symbol | min 1, median 20, max 46 |
| Carry a `symbol_isin` row | **1** of 226 |

**This is not corruption — it is a stale mapping table.** Every unmapped symbol is a listing
that began on or after 2026-07-10; `symbol_entity_intervals` and `symbol_isin` have not been
rebuilt since roughly 2026-07-09.

**Disposition (two acceptable routes):** (i) rebuild the mapping tables
(`scripts/csmp/build_universe.py`, `scripts/csmp/build_symbol_isin.py`) and re-run A2; or
(ii) set the certified equity window to end at the last mapping rebuild and exclude later
listings explicitly. **Consequence either way: the certified equity panel currently ends
around 2026-07-09, not at the store's 2026-09-11 max** — a fact no other gate surfaces.

### A3 — certified rule, promoted globally

**Issuer-prefix linkage applies only to `INE…01` equity ISINs.** `INF`, `IN0`, and non-`01`
series receive **no** issuer-prefix union unless separately classified. Recorded in
`DATA_STORE_MAP.md` so it binds outside PTMS.

### A4 — certification contract

The consecutive-trading-session methodology **is** the contract for `prev_close` identity.
Unrestricted row lagging is not admissible evidence for this arm.

### A6 — no substitution

Sector/thematic membership is NOT point-in-time and is UNUSABLE for cross-sectional work.
**Current membership may not be substituted for historical membership.**
