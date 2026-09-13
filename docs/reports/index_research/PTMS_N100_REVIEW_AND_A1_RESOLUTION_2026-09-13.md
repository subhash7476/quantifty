# Review — `n100_membership.duckdb`, and A1 under a Nifty-100 scope

**Date:** 2026-09-13 · **Access level:** meta only (symbol lists, dates, distinct-symbol counts,
file presence). No OHLC entered a feature, signal, label or fitted parameter.
**Reviewed:** `data/isd/n100_membership.duckdb`, `scripts/isd/build_n100_membership.py`,
`scripts/download_mcwb_archives.py`, `data/reference/mcwb_*.zip` (198 archives) + manifest.

> **Verdict: the build is sound — the strongest-evidenced membership artefact in the repo — and
> under a Nifty-100 scope it DOES satisfy A1.**
>
> **And satisfying A1 immediately exposes what the circularity was hiding: the 1m store does not
> contain the Nifty 100.** A mean of **11.0 constituents per session are absent** across 918
> sessions; only **41 of 918** sessions carry all 100. That is a blocking defect for the test,
> and it is the first time it has been measurable.

---

## 1. The build verifies — independently, not by re-running their code

**MCWB is the real find.** `data/reference/mcwb_*.zip` — 198 monthly NSE "Market Capitalisation,
Weightage & Beta" archives, 2010-01 → 2026-07, each carrying the full `nifty50_mcwb.csv` and
`niftynext50_mcwb.csv` constituent lists with per-file sha256 in the manifest. Unlike the press
releases, this is an **absolute-state source published monthly**, so it is self-correcting: an
error at one month cannot propagate. This is the artefact the N200 build never had.

**G3 reproduced from the delivered artefact.** I parsed the archives with my own reader and
recomputed month-end membership directly from `n100_membership`'s intervals — not from the
builder's internals:

```
INDEPENDENT G3 on the DELIVERED UNION: 184 months, 0 mismatched
union size at month-ends: 100 on 162 months, 101 on 20, 99 on 2
```

Every 101 and 99 month agrees with MCWB exactly, so the deviations are attested, not errors.

| Check | Result |
|---|---|
| Intervals / distinct symbols | 263 / 216 |
| Overlapping intervals per symbol | **0** |
| Reversed intervals | **0** |
| Open at terminal | **100** |
| Span | 2011-03-25 → 2026-03-30 |
| Determinism (two consecutive runs) | **content-identical, both tables** |
| Pre-listing intervals | **0** |
| N50 anchor vs independent `nifty50_constituents_current.csv` | **exact** |
| `n200_events` mutated | **no** — N200 store still 587 intervals |

One thing I got wrong on first pass and corrected: my naive MCWB parser showed several months at
51 or 54 members. The builder is right and I was wrong — those are NSE's own `DUMMY*` placeholder
rows (DUMMYSIEMS for the Siemens demerger, four Dummy Vedanta entities in Apr/May-2026), which
`parse_leg()` correctly excludes from membership and tallies separately.

## 2. The 23 overrides are load-bearing, and the gate genuinely constrains them

The obvious worry is circularity: the overrides were seeded from MCWB mismatches, then the build
reports passing an MCWB gate. I tested it by rebuilding with `OVERRIDES = []`:

```
G3 mcwb months compared: 368, mismatched: 260
G5 union-count mismatches: 43
NIFTY NEXT 50 terminal EXTRA: ['ASIANPAINT', 'ULTRACEMCO', 'WIPRO']
```

**260 of 368 month-legs fail without them; 0 with them.** So the press-release corpus alone
cannot produce a correct Nifty-100 history — the overrides are not cosmetic.

And the circularity is weaker than it looks: each override is a *point* edit whose effect
propagates across every later month, and all 368 month-legs are checked. Twenty-three edits
satisfying 368 simultaneous set equalities over 50-name sets is not something fitting can buy — a
wrong override breaks months downstream. The evidence key (R1–R8) cites the specific PR file and
MCWB months for each.

**The real residual: G3 is a *monthly* gate, so it cannot constrain a date within its month.**
Any day in May-2017 satisfies G3 identically for the GRASIM→VEDL swap; likewise the ACC re-entry
(Nov-2020), JIOFIN's exit (Sep-2023) and ITCHOTELS' exit (Mar-2025). The build discloses this as
"±30d" and that disclosure is accurate. **Immaterial for monthly formations; material for a daily
one**, where up to ~4 weeks of one name's membership is unpinned at each of those four boundaries.

## 3. One defect — the headline gates are not in the audit table

`n100_audit` records the count violations, terminals, the 23 overrides and the pre-listing
screen. It does **not** record `backward_breaks`, `forward_breaks`, the **G3 result**, or G5 —
they are printed to stdout and lost. G3 is the load-bearing gate of the entire build; a reader
opening the store cannot see that it ran, let alone that it passed.

This is the same class of defect as N200's D2, which was just fixed in the other direction: the
N200 audit now carries `backward_breaks`, `forward_breaks`, `union_gate_*` and
`pre_listing_intervals`. **Fix: write G1/G3/G5 results to `n100_audit`.** Low effort, and until
it is done the store's own register understates what was verified.

## 4. A1 — SATISFIED under a Nifty-100 scope

A1 was the circularity of `pit_membership`: `intraday_present` TRUE on all 173,900 rows because
membership was derived from the candle files it was meant to certify, so *"not investable on date
D"* could not be separated from *"the ingest did not write it on date D"*.

Three conditions had to hold for an external source to break that, and all three now do:

1. **The membership is externally sourced** — NSE press releases, gated monthly against NSE's own
   MCWB reports. Nothing is derived from the candle store.
2. **It covers the research universe exactly** — 100 names per session, by construction.
3. **Every member resolves to a store key** — 100/100 mapped via `instrument_master`, **0
   unmapped**, on every session tested. This was the practical blocker for the N200 attempt and
   it is simply absent here.

So for a Nifty-100 study the question A1 posed is now answerable on any date: the eligible set is
known independently, and any member without bars is a **coverage gap**, provably.

**Note what did not change.** `pit_membership` in `data/isd/pit_universe.duckdb` is still
circular and still wrong; nothing here repairs it. What changed is that a Nifty-100-scoped study
**does not need it** — this table replaces it for that universe. A1 is satisfied by substitution,
not by repair, and only within this scope.

## 5. What A1 being answerable immediately reveals — the blocking finding

With the universe finally defined independently, the coverage question can be asked. I scanned
**all 918 sessions** of the 1m store from 2023-01-01, mapping each session's N100 members through
`instrument_master` and checking presence:

| Year | Sessions | Mean N100 names absent | Max | Sessions with full coverage |
|---|--:|--:|--:|--:|
| 2023 | 246 | **14.0** | 15 | 0 |
| 2024 | 249 | **10.7** | 13 | 0 |
| 2025 | 249 | **10.2** | 11 | 0 |
| 2026 | 174 | **8.4** | 100 | 41 |
| **All** | **918** | **11.0** | 100 | **41** |

**Absent on 868 of 918 sessions each: `DLF`, `BRITANNIA`, `KOTAKBANK`, `BAJAJFINSV`.** Then `ABB`
(807), `CHOLAFIN` (801), `MOTHERSON` (801), `ADANIPOWER` (561), `ATGL` (556), `BERGEPAINT` (432).

**This is not a mapping artefact — I checked.** For each of the four worst names I looked up
*every* ISIN known to the repo, from both `instrument_master` and `symbol_isin` (including the
superseded pre-split ISINs), and searched the session file for any matching key. None is present.
They are genuinely not in the store.

Also found: **2026-02-01 holds 750 rows across 2 index symbols and zero equities** — a session
where the equity ingest did not run at all. It is the `max = 100` row above.

### What this means for the test

A Nifty-100 cross-sectional intraday study over 2023–2026 would currently run on **~89 of 100
names**, and the missing ~11 are **not random** — they are large caps, absent on ~95% of sessions.
That is a systematic, survivorship-shaped hole in the cross-section, and it would bias any
breadth, dispersion or L/S construct built on it while every existing gate reported success.

This is the repo's own recorded pitfall, now measured against the universe that matters: *"A
per-day 1m file's symbol set is whichever universe its writer used, not a universe."* The existing
tooling (`scripts/cas/fo_1m_coverage.py`, `scripts/cas/backfill_fo_1m.py --apply`) checks and
fills against the **F&O** universe, not the Nifty 100, so it has never been asked this question.

**The honest reading: A1 did not clear the path — it made the obstruction visible.** That is what
a certification gate is for. The substrate gap is now a bounded, named, fixable list rather than
an unanswerable question.

## 6. Disposition

- **The N100 build: accept.** Strongest evidence base in the repo; verified independently.
- **A1: SATISFIED for the Nifty-100 universe**, by substitution. `pit_membership` remains
  circular and should not be used; this table replaces it for this scope.
- **C2: still NOT CERTIFIED.** §5 is a new, material substrate finding, and the other open gates
  (C1 timestamp semantics, C3 `cas_category` ending 2026-08-28) are untouched.
- **Blocking before any Nifty-100 intraday test:** backfill the missing constituents, re-scoped
  from the F&O universe to N100 membership, then re-run this coverage scan to zero.
- **Next, cheap:** write G1/G3/G5 into `n100_audit` (§3), and dispose of 2026-02-01.
- For a **daily-cadence** construct, the four inferred boundaries in §2 need an explicit
  disposition; for a monthly one they can be accepted as disclosed.

---

## 7. What is actually blocking C2 — measured, 2026-09-13

C2's six arms, current state:

| Arm | Status |
|---|---|
| A1 `pit_membership` circularity | **Discharged for the Nifty-100 scope by substitution** (§4). `pit_membership` itself remains circular and unused |
| A2-1 DTIL interval endpoint | **CLOSED** — retracted as a data defect (the check used closed `<=` against an already half-open table); the one real consumer fixed (`scripts/n200_regime/build_panel.py:113`, commit `9c444c2`) |
| A2-2 stale universe / mapping | **RESOLVED** — 211 unmapped symbols → 0 |
| A3 ISIN issuer-prefix linkage | **CERTIFIED** |
| A4 `prev_close` identity | **PASS** — 5 mismatches in 6,544,193 calendar-adjacent pairs |
| A5 adjusted-series continuity | **HALT** — Arms B, C, D PASS; Arm A carries 5 undocumented items |
| A6 sector / thematic PIT | **SCOPED OUT 2026-09-13** by operator ruling — this construct needs no sector membership. Globally unchanged: **NOT PIT — UNUSABLE**, no PIT sector-constituent table exists |

### A5's residue is entirely outside the study universe

The 5 Arm A items and all 6 quarantined entities were checked against both PIT membership tables:

| Symbol | Ever in Nifty 100 | Ever in Nifty 200 |
|---|--:|--:|
| DSPGOLDETF · GOLDADD · DSPSILVETF · SILVERADD · IVZINNIFTY | 0 | 0 |
| INDIAGLYCO · KSE | 0 | 0 |
| KWALITY · GULFPETRO · SAHPETRO · DVL · DTIL · KILITCH | 0 | 0 |

**Not one has ever been a Nifty-100 or Nifty-200 constituent.** Three are ETFs, the rest small
caps. So A5's HALT is a **whole-panel** blocker that is *vacuous under a Nifty-100 scope* — the
adjudications (3 PSB-1 `ETF_SPLITS` register entries, plus INDIAGLYCO 2026-09-02 and KSE
2026-08-17) remain necessary to certify the full 4,343-symbol panel and are irrelevant to this
test.

### So the blocker list depends on scope

**Globally — C2 stays NOT CERTIFIED** on A5 (5 items, operator adjudication, one edits a closed
battery's register) and A6 (no PIT sector table exists at all).

**Scoped to Nifty 100, A1/A2/A3/A4 are satisfied and A5 is vacuous. What remains:**

1. **The 1m coverage hole (§5)** — mean 11.0 of 100 constituents absent per session, four large
   caps absent on 868 of 918 sessions. The universe is certified; the panel does not contain it.
   **This is the binding blocker**, and it is new — it was unmeasurable while A1 was circular.
2. ~~**A6**, only if the construct needs sector membership.~~ **CLOSED 2026-09-13 by operator
   ruling** — it does not, so A6 is scoped out of the fence. The consequence binds: sector-neutral
   and sector-conditioned designs are excluded, and no sector diagnostic is available, post-hoc
   included. Clause and cost: `PTMS_N100_1M_COVERAGE_BACKFILL_2026-09-13.md` §10.

### Two non-C2 gates block the same test

- **C1 — timestamp semantics OPEN.** Unresolved bar-labelling convention for the 1m store
  (AP-D4 `observed_bar_labeling` is a frozen candidate, not a certification). Directly load-bearing
  for any intraday construct.
- **C3 — blocked.** `data/cas/cas_category.duckdb` still ends **2026-08-28** (366 rows, verified
  today), so post-CAS carry-forward bars after that date remain unmarked `is_synthetic = FALSE`.
  Any intraday window extending past 2026-08-28 reads fabricated bars as real.

**Certifying C2 is the operator's call.** The evidence above supports a *scoped* certification —
Nifty-100 universe, stated fence — once the coverage gap is closed; it does not support a
whole-panel certification, and nothing here touches C1 or C3.
