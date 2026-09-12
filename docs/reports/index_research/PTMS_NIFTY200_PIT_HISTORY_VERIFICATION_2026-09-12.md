# Verification — `nifty200_2012-01-01_to_2026-09-12.csv` (PIT membership history)

**Date:** 2026-09-12 · **Access level:** meta only. No store write, no research window spent.
**Supersedes** the earlier verification of `ind_nifty200list.csv`, which was the current
survivor snapshot.

**Verdict: this is a genuine point-in-time membership history and a real substrate upgrade —
with three caveats that must be honoured before use. It still does not solve A1** (§5).

---

## 1. What it is

`effective_date, index_type, inclusions, exclusions, symbols` — **50 rows, 2012-04-27 →
2026-03-31**, `index_type` uniformly `Nifty200`.

| Check | Result |
|---|---|
| Symbols per row | **exactly 200 on every one of the 50 rows** |
| Duplicate symbols within a row | **0** |
| Cadence | 2–6 changes/year, settling at 2/year recently — consistent with semi-annual rebalances plus ad-hoc changes |

This is the artefact `build_universe.py`'s docstring records as *not freely obtainable* ("NSE
publishes no freely-obtainable point-in-time index-constituent change history"). If it holds
up, that finding is superseded for the EOD equity panel.

## 2. Caveat 1 — symbols are back-mapped to present-day tickers (verified, not suspected)

**Contemporaneity test** — for each `effective_date`, how many of its 200 symbols actually
traded in our panel within ±30 days:

| Effective date | Traded within ±30d | Absent |
|---|---:|---:|
| 2012-04-27 | 164 / 200 | **36** |
| 2014-03-28 | 171 / 200 | 29 |
| 2017-09-29 | 181 / 200 | 19 |
| 2021-09-30 | 184 / 200 | 16 |
| 2026-03-31 | 194 / 200 | 6 |

The absence rate **declines monotonically as dates approach the present** — the signature of
back-mapping. Confirmed by tracing the absent names' first-ever appearance in our panel:

```
LINDEINDIA 2013-04-10 · IIFL 2014-03-13 · CASTROLIND 2014-03-14 · INTELLECT 2014-12-18
VEDL 2015-05-07 · BHARATFIN 2016-07-01 · 63MOONS 2017-01-19 · CGPOWER 2017-03-08
```

These are renames — LINDEINDIA was BOC India, VEDL was Sesa Goa/Sterlite, 63MOONS was
Financial Technologies, GMRAIRPORT was GMRINFRA, IDFCFIRSTB did not exist in 2012, and
CYIENTDLM listed in 2023. The file lists **who was a member, on the right date, under today's
ticker**.

**This is not the survivorship bias the PIT machinery guards against.** That bias is applying
today's *constituent set* to a past date; here the sets genuinely change over time. Back-mapping
is a naming transformation, membership-neutral.

**But it means the file cannot be joined to the panel on `symbol` for historical dates.** It
must be joined on **entity**, through `symbol_entity_intervals` — which was rebuilt today to
4,344 intervals / 3,825 entities covering all 4,343 panel symbols. That machinery exists
precisely for this, and the standing rule applies: *an entity is not one symbol for all time*.

**Six names never appear in our panel at all** and need entity resolution before any join:
`AMARAJA`, `BHUSHANSTL`, `OBC`, `PIRAMAL`, `PIRAMAN`, `SDREAMS`.

## 3. Caveat 2 — the `inclusions`/`exclusions` columns are lossy; `symbols` is authoritative

Self-consistency test — does `symbols[i] == symbols[i−1] + inclusions[i] − exclusions[i]`?

**It fails on 24 of 49 transitions**, each time by exactly one name. Since every row still
carries exactly 200 symbols with no duplicates, the `symbols` column is internally coherent and
the delta columns are the unreliable ones (a rename recorded on one side only would produce
precisely this).

**Use `symbols` as the membership source. Do not reconstruct membership from the delta columns**
— doing so would drift by up to 24 names across the span.

## 4. Caveat 3 — coverage is narrower than the filename claims

| Boundary | Filename claims | File actually holds |
|---|---|---|
| Start | 2012-01-01 | **2012-04-27** |
| End | 2026-09-12 | **2026-03-31** |

The equity panel starts **2010-01-04**, so **2010-01-04 → 2012-04-26** has no membership, and
**2026-04-01 → present** (the last ~5.5 months) is uncovered. Any construct using this file
must fence to its actual span, not the filename's.

## 5. It still does not solve A1

A1 is the circularity of `pit_membership` in `data/isd/pit_universe.duckdb`, which covers the
**intraday 1m panel** — ~190–197 entity-keyed, F&O-shaped names. **Nifty 200 is a different
universe.** Knowing index membership on date D does not tell you whether a name was investable
*and present in the 1m store* on date D, which is what A1 needs.

What it **does** do is materially stronger than the previous file: it is a credible replacement
for — or at minimum an independent validation of — the charter-locked mechanical
top-200-by-turnover reconstruction in `universe_membership`, for **EOD** cross-sectional work.
Recall the mechanical rule recovers only **78.5%** of the official current list; a true PIT
history removes that approximation entirely over its span.

A1's actual path remains the one named previously: derive per-date F&O eligibility from
`futures_bhavcopy` (independent of the candle store, 2016-02-11 → 2026-09-11).

## 6. Recommendation

1. **Keep it — it is the best membership artefact in the repo**, subject to §2–§4.
2. **Do not ingest it yet.** Before it can be used it needs: entity-grain resolution of the
   back-mapped tickers via `symbol_entity_intervals`, disposition of the 6 unresolvable names,
   an explicit fence to 2012-04-27 → 2026-03-31, and a recorded provenance statement (the
   operator has not yet said where it came from).
3. **Do not treat A1 as solved, and do not treat C2 as certified.** Neither status changes.
4. Ingesting it is a scoped substrate task of its own — it would modify `universe_membership`,
   which currently feeds the CSMP/PSB lineage, so it needs its own authorization and baseline.
