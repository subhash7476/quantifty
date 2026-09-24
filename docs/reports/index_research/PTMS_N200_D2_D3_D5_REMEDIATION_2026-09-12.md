# N200 membership build — D2, D3 and D5 remediation

**Date:** 2026-09-12 · **Authority:** operator task "now fix D2, D3 and D5".
**Follows:** `PTMS_N200_MEMBERSHIP_BUILD_REVIEW_2026-09-12.md` (the defects) and
`PTMS_N200_D1_D4_REMEDIATION_2026-09-12.md` (D1/D4, closed earlier today).
**Baseline before any write:** `data/_baselines/n200_membership.pre_d2_d3_d5_2026-09-12.duckdb`.

> **Result: D2, D3 and D5 are closed as far as the sources allow. Intervals asserting membership
> before the security listed drop 14 → 2, and the two survivors are now reported by name rather
> than left implicit. A1 is unaffected and remains NOT SATISFIED; C2 remains NOT CERTIFIED.**

---

## 1. D5 — era-correct symbols, 18 → 31 rename pairs

The claim "symbols are as-printed at the time" held for 18 pairs; every other rename projected
today's ticker back to 2011, so the store was back-mapped in exactly the way the vendor CSV was
faulted for. **All twelve missing predecessors turned out to be in NSE's own `symbol_changes`
table** — none had to be inferred:

| | | | |
|---|---|---|---|
| HEROHONDA → HEROMOTOCO | ISPATIND → JSWISPAT | COREPROTEC → COREEDUTEC | PIPAVAVYD → PIPAVAVDOC |
| MUNDRAPORT → ADANIPORTS | DEWANHOUS → DHFL | PIRHEALTH → PEL | PANTALOONR → FRL |
| UNIPHOS → UPL | TATAGLOBAL → TATACONSUM | TATAMOTORS → TMPV | SESAGOA → SSLT → VEDL |

`era_chain()` already handled multi-step chains, so **SESAGOA → SSLT → VEDL** splits into all
three segments automatically. Twelve back-projected intervals became twenty-five era-correct ones;
`intervals` 574 → **587**.

**Verified:** a symbol-by-symbol comparison against first-trade dates in `equity_bhavcopy` now
returns **2** intervals that begin before the security traded, down from 14 (and 16 before any of
today's work).

### The irreducible residue, now reported instead of silent

`MGL` and `PNBHOUSING` are not renames — they listed in 2016 with no predecessor, and their index
*entries* appear in no press release in the 228-file archive while their exits (2022-03-31 /
2020-09-25) are genuine parsed events. Nothing in the corpus can date their entries.

A name that no event ever touches is carried silently back to `LAUNCH_DATE`: no break fires,
because the backward walk records contradictions only. So a new **`pre_listing_gate()`** flags
every interval beginning before the symbol's first trade and writes each one to `n200_audit`:

```
pre_listing_intervals  2
pre_listing            PNBHOUSING|2011-07-19|2016-11-07
pre_listing            MGL|2011-07-19|2016-07-01
```

That is the correct disposition for a defect the sources cannot resolve: make it visible and
bounded rather than fix it by invention. **The error is in the interval start, not the
membership** — from their true entries (bounded to 2017-03 and 2017-09 by listing date plus the
3-month IPO rule) both names are correct, which is why the union gate reconciles exactly from
2018-06-29 on.

## 2. D3 — the terminal gate is labelled as the identity it is

Given `backward_breaks == 0`, the forward replay is the exact inverse composition of the backward
walk over the same ordered event list, so it *must* return the anchor. Deleting an entire press
release does not break it; the launch state absorbs the change.

- The code now says so at the check, and `n200_audit` carries a row that says so in the store:
  `terminal_is_identity = "yes - inverse of the backward walk when backward_breaks=0; carries no
  information about source completeness, see union_gate_*"`.
- The gate is **kept**, because it is still a real self-consistency assertion on the two walks —
  it would fire if the replay were ever implemented as something other than the inverse.
- The build report's residual 3, which rested the "exact from ~2018" claim on this gate, is
  replaced by the claim the evidence actually supports: parse fidelity against the primary PDFs,
  counts of exactly 200 from 2020-06-26 outside the documented DVR episode, and the union gate.

## 3. D2 — the gate table now matches the audit, and two real gaps closed

### 3a. `backward_breaks` conflated two different checks

The audit value was read *after* the forward pass had appended to the same `breaks` list, so one
number covered both walks. Split into `backward_breaks` and `forward_breaks` (both **0**).

### 3b. The launch state was never evaluated

`counts` began at the first *event* date, so `LAUNCH_DATE → 2011-11-21` — the one span with no
preceding event — was the only span the count gate never looked at, while `launch_count = 201` sat
in the audit unremarked. The launch state is now the first count entry. `forward_violations`
41 → **42**; the new one is `2011-07-19|201`, which was always true and never counted.

### 3c. The report claimed "all green" over 42 recorded violations

Rewritten. The gate table now states the 42 deviations, adds the union gate, the pre-listing gate,
the interval-integrity checks, and the terminal-gate caveat. The five **202**-dates
(2016-04-01, 2016-09-30, 2016-11-15, 2017-01-23, 2017-03-31), previously undocumented anywhere,
are now in the composition table.

### 3d. The count decomposition, derived rather than asserted

Computed from the chain, not restated:

| Span | Count | Composition |
|---|--:|---|
| 2011-07-19 (launch) → 2015-10-19 | **201** | 200 + 2 phantoms − 1 unsourced genuine entry |
| 2016-04-01 → 2017-03-31 | **202** | 201 (NSE-stated DVR era) + 2 − 1 |
| 2017-07-05 → 2020-03-19 | **201** | 201 (DVR era); ABIRLANUVO's unmatched exit removes the earlier surplus |
| 2023-09-29, 2024-03-28 | **201** | 201 (second DVR episode) |

Measured directly: at 2013-06-28 and at 2015-01-01 the walk holds **201 members, of which exactly
2 had not yet listed** — so the span carries two members too early and one member missing, netting
+1. The phantoms are provable and the count is measured; **the identity of the missing entry is not
derivable from the corpus, and the report no longer implies otherwise.**

**One correction to my own review.** The review said the report's MGL/PNBHOUSING diagnosis "does
not match the dates in the table", on the ground that the surplus vanishes at ABIRLANUVO's
2017-07-05 exit rather than at the phantoms' exits. The arithmetic above shows the prior report's
shape — two phantoms less one absentee — was **right**; what it omitted was ABIRLANUVO's unmatched
exit as a separate term, the five 202-dates, and the launch state. The criticism of the "all
green" framing stands; the charge that the diagnosis was wrong does not.

## 4. State after the rerun

| Check | Before today | After D1/D4 | **After D2/D3/D5** |
|---|---|---|---|
| Rename pairs | 16 | 18 | **31** |
| Intervals / distinct symbols | 572 / 455 | 574 / 457 | **587 / 470** |
| Intervals starting before first trade | 16 | 14 | **2** (both reported by name) |
| `backward_breaks` / `forward_breaks` | 0 (conflated) | 0 (conflated) | **0 / 0** (split) |
| `forward_violations` | 41 | 41 | **42** (launch state now counted) |
| Union gate | — | 42 dates, 0 mismatches | **44 dates, 0 mismatches** |
| Overlapping intervals / open at terminal | 0 / 200 | 0 / 200 | **0 / 200** |
| N200 events with no symbol / no effective date | 0 / 0 | 0 / 0 | **0 / 0** |
| Terminal check | claimed as evidence | unchanged | **labelled an identity in code and store** |

Membership diff against the pre-D2/D3/D5 baseline: **12 intervals replaced by 25**, all era
splits, every one dated from `symbol_changes`. No membership *span* changed — only the labels
carried within it. Two consecutive runs remain content-identical across all three tables.

## 5. What is still open

- **MGL and PNBHOUSING entry dates** — unresolvable from this corpus. Reported, bounded, not fixed.
- **The one unsourced genuine entry** implied by the pre-2016 arithmetic is unidentified.
- **No independent check covers 2011 → mid-2018.** Extending the union gate through the renamed
  midcap-label era (CNX Midcap → Nifty Free Float Midcap 100 → Nifty Full Midcap 100 → Nifty
  Midcap 100) is the one remaining piece of work that would bound the early era the way 2018+ is
  bounded now.
- **One residual NIFTY 100 backward break** in the auxiliary stream (`union_gate_n100_breaks = 1`).
  It does not move the gate's verdict — the union still reconciles exactly on all 44 dates.
- **D6** — the builder and reports are committed; the store and the PR corpus cannot be, since
  `/data/` is gitignored repo-wide.
- **A1 is unchanged.** The panel/N200 overlap measurement stands: the two universes are neither
  nested nor congruent, so `pit_membership`'s circularity is unrepaired by any of this work.
