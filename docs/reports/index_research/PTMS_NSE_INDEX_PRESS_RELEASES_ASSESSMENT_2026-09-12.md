# Assessment — `data/reference/nse_index_pr/` (NSE index press releases)

**Date:** 2026-09-12 · **Access level:** meta only. No store write, no research window spent.

**Verdict: this is the strongest membership artefact in the repo — the *primary source*, with
contemporaneous tickers. It does not solve A1. It does, combined with the CSV, make a credible
PIT universe for the EOD panel reachable.**

---

## 1. What it is

**215 readable PDFs + a manifest**, `ind_prsDDMMYYYY.pdf`, fetched from
`niftyindices.com/Press_Release/`. Spread 2011 → 2026 (7–24 per year, rising with time).
Every one parses cleanly with `pypdf` — **0 unreadable**.

Manifest: 216 rows, **215 `ok`, 1 `MISSING`** — `ind_prs02032012.pdf`, noted as *"live URL
serves 404 page; single Wayback"*. Provenance is recorded per file (filename, URL, title,
status), which is more than any other reference artefact here carries.

Each release contains exactly what membership reconstruction needs:

```
The Index Maintenance Sub-Committee has decided to make the following changes in CNX 500
Index ... which will become effective from August 07, 2013.
The following companies are being excluded:   1  Sujana Tower Limited   SUJANATOW
The following companies are being included:   1  Wipro Limited          WIPRO
```

Index name · effective date (with "close of" convention stated in later releases) · excluded
and included companies, **name and symbol**.

## 2. Why this is better than the CSV — contemporaneous symbols

The 2013 release names **`SUJANATOW`**, the ticker in force *at the time*. The CSV
(`nifty200_2012-01-01_to_2026-09-12.csv`) back-maps every historical constituent to its
**present-day** ticker — verified earlier: only 164 of its 200 names for 2012-04-27 traded
within ±30 days of that date.

**The press releases are therefore the authority that can undo the CSV's one structural
weakness**, and they are a genuine primary source rather than a vendor derivation.

## 3. Why it does not replace the CSV — a change-log is not self-correcting

**90 of the 215 releases mention Nifty 200 / CNX 200.** The rest concern other indices
(Nifty 500, Nifty India FPI 150, sectoral, thematic) — the corpus is all-index, not Nifty-200.

The deeper limitation: a press release announces a **change**. Reconstructing membership from
changes requires a correct starting list **plus every subsequent change**, and a single missed
release corrupts every date after it. Completeness here is **not provable** — and one file is
already known missing (`ind_prs02032012.pdf`, live URL 404, Wayback only).

By contrast the CSV carries the **full 200-symbol list on every effective date**. That is
*self-correcting*: an error at one date does not propagate.

**So the two are complementary, not competing:**

| Artefact | Gives | Weakness |
|---|---|---|
| CSV | Absolute 200-name state per date, self-correcting | Back-mapped tickers; `inclusions`/`exclusions` disagree with `symbols` on 24 of 49 transitions; spans only 2012-04-27 → 2026-03-31 |
| Press releases | Primary authority; **contemporaneous symbols**; per-file provenance; spans 2011 → 2026 | Change-log (error-propagating); completeness unprovable, 1 known missing; all-index corpus needing filtering; two distinct document layouts (IISL pre-2017, NSE Indices after) |

The reconciliation that uses both — CSV as state, press releases to verify each transition and
recover the contemporaneous ticker — is what a certified PIT universe would rest on.

## 4. It still does not solve A1

Third time, same reason, stated plainly: **A1 is the circularity of `pit_membership` over the
intraday 1m panel** — ~190–197 entity-keyed, F&O-shaped names. These releases describe **index
constituent** changes. Knowing that Wipro entered CNX 500 in August 2013 does not tell you
whether a name was investable *and written into the 1m store* on a given 2023–2026 session.

A1's path remains what it was: derive per-date F&O eligibility from `futures_bhavcopy`, which
is independent of the candle store and spans 2016-02-11 → 2026-09-11.

## 5. What this *does* unlock

For the **EOD equity panel**, `universe_membership` is currently a *mechanical reconstruction*
— top 200 by 6-month median turnover — which recovers only **78.5%** of the official current
list. `build_universe.py`'s docstring justifies that fallback on the ground that *"NSE publishes
no freely-obtainable point-in-time index-constituent change history."*

**That justification no longer holds.** Between the CSV and these 90 Nifty-200 releases, the
change history is obtainable. Replacing the mechanical rule with a reconciled, primary-sourced
PIT universe is now a real option — a material substrate upgrade for any EOD cross-sectional
work, and it would retire a documented approximation.

## 6. Recommendation

1. **Keep both artefacts.** Together they are the best membership evidence the repo has held.
2. **Do not ingest either yet.** A reconciled ingest needs: filtering to Nifty-200 releases,
   a parser tolerant of both document layouts, transition-by-transition agreement with the
   CSV's `symbols` column, contemporaneous-ticker recovery via `symbol_entity_intervals`,
   disposition of the 6 names absent from the panel, recovery or disposition of the missing
   2012-03-02 release, and an explicit fence.
3. **A1 is unchanged**, and so is **C2 — NOT CERTIFIED**.
4. This is a scoped substrate task of its own. It would replace `universe_membership`, which
   feeds the CSMP/PSB lineage, so it needs its own authorization and copy-first baseline.
