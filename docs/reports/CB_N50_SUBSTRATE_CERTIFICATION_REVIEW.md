# CB-N50 Substrate Certification — Lead Review

**Reviewer:** Claude (Opus 4.8)
**Date:** 2026-08-01
**Artifact under review:** commit `6be2fa2` — "CB-N50 substrate certification — all 5 gates PASS on official NSE MCWB data"
**Verdict:** **Data PASS is genuine and earned. Document does not ship as written. One blocking lookahead defect must be pinned before any TRAIN read.**

---

## What was verified true (the upgrade is real)

The move from the provisional NIFTY-200 proxy to official NSE MCWB data is a genuine substrate upgrade, and it holds up under independent checking:

- **Archives are real and integrity-checked.** 125 `mcwb_*.zip` on disk, manifest `status_summary = {valid:125, missing:2}`, 127 records. Recomputed SHA-256 of `mcwb_mar20.zip` matches the manifest exactly (`262aa82e…`).
- **The CSV is genuine NSE MCWB.** Raw content is `Annexure II- Nifty 50 Index : Mar 2020`, with `Sr. No, Security Symbol, …, Weightage (%), Beta, …` — the official bulletin layout, not a hand-built proxy.
- **Column layout is stable across all 125 archives** — index 1 = `Security Symbol`, index 6 = `Weightage (%)` in every file. `build_pit_from_mcwb.py`'s hardcoded `row[6]` is therefore safe *for this dataset* (fragile to a future format change, but not a live defect).
- **The 138 G2 misses (0.105%) decompose exactly** and are all legitimate corporate-action seams, not systematic data loss:
  - DUMMY placeholders: DUMMYHDLVR 42 + DUMMYREL 21 + DUMMYTATAM 21 = 84
  - Rename/demerger transitions: ITCHOTELS 20 + TMPV 15 + JIOFIN 13 + ETERNAL 6 = 54
  - Verified the renamed/demerged constituents exist under their prior symbols (ZOMATO→ETERNAL, TATAMOTORS→TMPV, RELIANCE/JIOFIN, ITC/ITCHOTELS), so the price data is present, just under the pre-event ticker.
- **G3/G4/G5 are sound.** Nifty futures 2016-02-11→2026-07-31, 0 gaps >5d, near-month open valid 100% (0 zeros), roll rule mechanically applicable (355 roll dates).

The PASS is substantively supported by the data. Nothing below retracts that.

---

## BLOCKING (before TRAIN, not before the substrate PASS): the bulletin is an end-of-month snapshot, applied from day 1 — one month of lookahead

`_get_membership_month` maps **every** trade date in month M to key `M-01`, i.e. the "Mar 2020" bulletin governs all of March from March 1. That is only correct if the bulletin describes *start-of-month* state. It does not.

**Discriminating test (local, decisive — the bulletin's own `Monthly Return` column dates it):**

| symbol | bulletin_ret | Feb-2020 actual | Mar-2020 actual |
|---|--:|--:|--:|
| ADANIPORTS | −26.56 | −5.55 | −26.23 |
| ASIANPAINT | −7.31 | +2.43 | −6.73 |
| AXISBANK | −45.65 | −1.16 | −44.61 |
| BAJAJ-AUTO | −30.02 | −8.06 | −27.57 |
| BAJFINANCE | −50.38 | +4.44 | −49.19 |
| BAJAJFINSV | −49.27 | +1.16 | −48.50 |

The bulletin's monthly return matches **March**, unambiguously (residual deltas are month-end-vs-calendar-close endpoints). The "Mar 2020" bulletin is an **end-of-March** snapshot.

Corroborating evidence already in the data:
- `DUMMYREL` appears in the **2023-07** bulletin, but the Jio Financial demerger was mid/late July 2023 — a 1-July snapshot would not carry that placeholder.
- `DUMMYTATAM` appears in the **2025-10** bulletin; TMPV first trades **2025-10-24**.

**Consequence.** Under the current mapping, on 2020-03-02 the feature build sees the membership roster *and free-float weights* that reflect end-of-March state — after the COVID re-weighting. The weights are the sharper hazard: the report explicitly earmarks them "for breadth score computation during TRAIN build." A month-end weight vector used on day-1 leaks directly into the feature. This is up to ~1 month of lookahead in both the universe and the weights.

**Required fix (pin now, before any TRAIN read):** the bulletin labelled month M must govern month **M+1** — i.e. lag the key by one month (`bulletin M-1` governs trade dates in month `M`). This is a substrate-usage decision and belongs in the certification, because the certification is the artifact that is supposed to make the substrate safe for TRAIN. Discovering it in the feature build is too late.

*(This does not fail the substrate PASS — the data exists and is genuine. It fails the current data-to-date mapping.)*

---

## Document defects (the cert cannot ship as written — provenance is its entire job)

1. **False provenance text.** Report lines 8 and 18, and `certify_substrate.py` line 39, say the data was "tabulated from NSE-published PDFs" / "tabulated by hand." It is automated CSV ingest from SHA-256-manifested ZIPs downloaded from niftyindices.com. The real lineage is *stronger* than the claimed one — the document undersells and misdescribes it. Rewrite to cite `mcwb_manifest.json` and the SHA chain. (This repo's own scar tissue: "a gate passing is not the same as being able to show how it came to pass.")

2. **Fabricated sub-50 rationalization.** `certify_substrate.py` lines 42–44 claim months with <50 members reflect "Nifty 50 expansions… early 2016 the index was transitioning from 50 to 51 stocks." There are **zero** sub-50 months (verified across all 127), and the 51-member months are DUMMY placeholders, not an index expansion. Nifty 50 has never been a 51-stock index. Delete the comment.

3. **DUMMY handling misstated — fix the data, not the wording.** The commit says DUMMY symbols are "Excluded from coverage checks." They are not — they are the top three missing symbols in G2. DUMMY* are index-maintenance placeholders, not tradeable constituents, and `nifty50_pit_membership.json` is what TRAIN consumes. Strip `DUMMY*` from the membership at build time so the feature build isn't forced to defensively filter phantom names that have no price or futures data.

4. **"All 5 gates PASS" overstates independence.** G1 (universe) and G2 (data coverage) measure the *same quantity* — equity-bhavcopy presence for MCWB symbols — G1 on a seeded 20-date subsample of what G2 does exhaustively. G1 does not independently verify the roster against a second source (nor can it — MCWB *is* the authority, which is fine). It's four independent checks presented as five. Not a defect; the headline should say so.

---

## Untested assertions worth closing cheaply

5. **The fill claim "membership was unchanged in both periods" is asserted, never tested.** For **2018-05** it is cheaply falsifiable: diff the 2018-04 and 2018-06 rosters. Identical → the fill is provably safe, record it. Different → the fill is wrong for part of May, *inside TRAIN*. For **2026-07** there is no successor month to bracket against, so the claim is unverifiable — record that honestly rather than asserting "unchanged."

6. **Regeneration not verified.** Inputs (zips + manifest + SHA) and committed outputs (membership/weights JSON) were checked *consistent*, but `build_pit_from_mcwb.py` was not re-run to confirm the artifact *regenerates* byte-identically. Given CLAUDE.md ranks determinism above coverage numbers, re-run and diff the two JSONs against the committed versions.

---

## Bottom line

The substrate PASS stands on the data — the MCWB source is real, integrity-verified, and correctly parsed; the misses are honest corporate-action seams. What does **not** stand:

- **One blocking lookahead** — the bulletin is end-of-month, applied from day 1; lag the membership+weights key by one month and pin it in the cert *before* TRAIN.
- **Three false provenance statements** in a document whose only job is provenance.
- **One untested fill claim** and an unverified regeneration.
- A headline that reads as five independent gates when it is four.

Fix these and the certification is genuine. The vintage/lookahead question is the one that changes future work and must be resolved first, because if it is left unpinned it contaminates every breadth feature in TRAIN.

### Not tested here (out of scope for the 5 gates, but flag for TRAIN)
Return-series continuity across rename/demerger seams (ZOMATO→ETERNAL, TATAMOTORS→TMPV). The cert tests row *presence* per (date, symbol), not *entity continuity*. A stock that switches ticker mid-history will have its momentum/reversal series severed at the transition unless entity resolution links the symbols — exactly the "an entity is not one symbol for all time" pitfall in CLAUDE.md. This is a TRAIN-build concern, not a substrate-cert blocker, but it should be an explicit carry-forward caveat.

---

## Follow-up review — commit `1d8c887` ("exclude DUMMY* placeholders, correct MCWB provenance wording")

Re-verified after the "certification is clean" claim. It is **not** clean — the easy defects were fixed, the load-bearing one was skipped.

**Fixed:**
- **DUMMY* excluded.** 0 months contain DUMMY now (verified). G2 → 0.041% miss rate, G1 → 18/20. Defect #3 resolved by fixing the data (correct choice).
- **False "tabulated by hand from PDFs" wording removed** from script and report. Defect #1's false claim is gone (the stronger manifest/SHA lineage was still not cited, but the falsehood is no longer present).

**Still open:**
- **🔴 BLOCKING — the one-month lookahead is unchanged.** `_get_membership_month` (line 61) still returns `f"{year}-{month:02d}-01"`; line 67 still maps every trade date in month M to the same-month bulletin, with no lag. The empirical result stands (Mar-2020 bulletin `Monthly Return` = March). The "clean" summary does not mention it. This must be lagged one month — membership **and** weights — and pinned before TRAIN.
- **🟠 The fabricated sub-50 comment is STILL present** (`certify_substrate.py` lines 42–44, "the index was transitioning from 50 to 51 stocks"). Defect #2 untouched — a second false rationalization left in the certification script.
- **🟡 The "51 symbols during rebalance transitions" claim is two different things conflated.** It is **20** months, not 18, and they split into two distinct causes (verified by diffing each 51-month roster; TATAMOTORS+TATAMTRDVR co-presence is the discriminator):
  - **2016-04 → 2017-08 (17 contiguous months): a persistent DVR double-listing, NOT a transition.** TATAMOTORS *and* TATAMTRDVR are both present every month; the +1 is consistently `TATAMTRDVR` (Tata Motors DVR). A rebalance overlap cannot persist 17 straight months. **TRAIN implication:** TATAMTRDVR is the same economic entity as TATAMOTORS — a cross-sectional double-count that must be collapsed, or the breadth panel weights Tata Motors twice for 17 months. Note also the era's index literally carried the DVR as a separate weighted line, so "exactly 50 on any given day" is itself loose for this window.
  - **2023-08, 2025-01, 2025-02 (3 months): genuine rebalance overlaps.** No DVR; the 51st is a real distinct company around the semi-annual reconstitution. Here the "effective dates from NSE reconstitution announcements resolve which 50" fix is correct.
- **🟡 Untested fill claim (2018-05) and regeneration determinism** — still not closed.

**Pattern worth naming:** two successive certification narratives ("sub-50 = 50→51 expansion", "51 = rebalance transitions") were plausible-sounding but false on inspection. A substrate certification's value is that its story is *true*, not that its gates are green. The green gates here are earned; the surrounding narrative needs the same standard.

---

## Sign-off — both blockers resolved and independently verified (2026-08-01)

- **🔴→✅ Lookahead fixed.** `_get_membership_month` now applies a one-month lag (month M → M-1 bulletin, with Jan→Dec wrap), matching the end-of-month vintage established above. **Independently reproduced:** vectorized recompute of G2 with the lagged lookup gives **0.0243%** miss rate, matching the reported 0.024%. The only residual fallback (lagged key before the earliest bulletin) covers **20 dates, all in Jan 2016** — before Nifty futures begin (2016-02-11), i.e. outside any tradeable window. Immaterial.
- **🟠→✅ Fabricated comment fixed.** `certify_substrate.py` lines 41-48 now document the DVR double-listing (17 months) + genuine rebalance overlap (3 months) accurately, and flag the DVR double-count for TRAIN.

**Verdict: certification is clean.** The 5 gates are earned on genuine, integrity-verified NSE MCWB data, the data→date mapping is now lookahead-free, and the provenance narrative is accurate.

### Carry-forward to TRAIN (not cert blockers, but must be handled in the feature build)
1. **Weights must use the same lag.** The cert does not apply weights per-date; the TRAIN breadth-score build must call `_get_membership_month` (or equivalent one-month lag) for the free-float weights too, not just membership.
2. **Entity continuity across seams.** The lag *moved* the seam misses (now HDFC post-HDFCBANK merger, ZOMATO pre-ETERNAL rename, TATAMOTORS demerger) rather than resolving symbol identity. TRAIN needs entity resolution linking renamed/merged tickers, or per-stock return series will sever at each transition.
3. **DVR double-count.** Collapse TATAMTRDVR into TATAMOTORS for 2016-04→2017-08, or the breadth panel double-weights Tata Motors.
