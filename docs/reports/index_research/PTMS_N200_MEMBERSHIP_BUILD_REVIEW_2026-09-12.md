# Review — `n200_membership.duckdb` build, and does it satisfy A1?

**Date:** 2026-09-12 · **Access level:** meta only (symbol lists, dates, row counts, PDF text).
No OHLC entered a feature, signal, label or fitted parameter. No research window spent.
**Reviewed:** `data/isd/n200_membership.duckdb`, `scripts/isd/build_n200_membership.py`,
`docs/reports/N200_PIT_MEMBERSHIP_BUILD.md`, `data/reference/nse_index_pr/` (228 PDFs).

> **Verdict: the build is good work and the best membership artefact the repo has ever held —
> and it does NOT satisfy A1.** A1 is unchanged. Separately, six defects are recorded below;
> one (D1) is blocking for any use, and three concern claims the build report makes that its
> own audit table contradicts.

---

## 1. A1 — NOT SATISFIED. The measurement, not an opinion.

A1 is the circularity of `pit_membership` in `data/isd/pit_universe.duckdb`: 173,900 rows,
229 entity keys, 2023-01-02 → 2026-08-24, with **`intraday_present` TRUE on every row**
because it was derived from the candle files it is supposed to certify. The defect is that
*"not investable on date D"* cannot be separated from *"the ingest did not write it on date D"*.

An external membership source can break that circularity — but only for the names it covers.
Measured directly, exploding the panel's comma-joined entity keys and joining to the new store:

| Session | Panel names | …that are N200 members | N200 members | …absent from the panel |
|---|--:|--:|--:|--:|
| 2023-01-02 | 188 | **147** | 200 | **53** |
| 2024-06-03 | 193 | **160** | 201 | **41** |
| 2025-07-01 | 196 | **168** | 200 | **32** |
| 2026-08-24 | 197 | **169** | 200 | **31** |

**The two universes are neither nested nor congruent.** Roughly **28 panel names per session
(14–22%)** are outside Nifty 200 — the panel is F&O-shaped, as established earlier — and for
those names the circularity is untouched. Conversely **31–53 Nifty 200 members per session are
absent from the panel**, and the store cannot say whether that is correct exclusion or a
coverage gap, which is the very distinction A1 requires.

**What the store does deliver:** a genuinely non-circular, primary-sourced membership assertion
for the 147–169 names/day it does cover. That is real partial progress — it is the first
membership signal in the repo not derived from the panel it would certify. It is not a repair
of `pit_membership`, and it does not unblock Family F.

**A1's path is unchanged:** per-date F&O eligibility derived from `futures_bhavcopy`
(1,495,989 rows, 2016-02-11 → 2026-09-11), a store the 1m panel does not feed.

## 2. What the build gets right — verified, not assumed

- **Parsing fidelity is high.** Spot-checked the latest transition against the primary PDF:
  `ind_prs23022026.pdf` §12 "Nifty 200" lists 11 exclusions and 11 inclusions; the events table
  reproduces all 22, in order, symbols and companies exact. No fabrication, no drift.
- **Interval integrity is clean.** 572 intervals, 455 symbols, **0 reversed intervals, 0 NULL
  keys, 0 overlapping intervals per symbol**, exactly 200 open at the terminal date.
- **The DVR deviation is real and primary-sourced**, not a post-hoc reconstruction. `TATAMTRDVR`
  carries intervals 2016-04-01 → 2020-06-26 and 2023-09-29 → 2024-08-30, and every boundary has
  a parsed PR event (`ind_prs22022016_2`, `ind_prs10062020`, `ind_prs17082023`,
  `ind_prs23082024_1`). This checked out exactly as the report describes it.
- **Backward-chain consistency is a genuine gate and it passes.** Over 711 chain events, zero
  reverse-include-absent and zero reverse-exclude-present contradictions. This is the one
  informative gate in the battery (see D3).
- **Completeness sweep, run independently, is near-clean.** All 228 PDFs parse. Of every file
  carrying a real Nifty-200 / CNX-200 reference near an action phrase but producing no N200
  event, there is exactly **one** — `ind_prs19032020.pdf` — and its cause is D4 below, not a
  dropped rebalance. No missing semi-annual review was found.
- Provenance per PDF is recorded in `manifest.csv`; manifest and directory agree exactly
  (228 = 228, no orphans either way).

---

## 3. Defects

> **Status update, same day — `PTMS_N200_D1_D4_REMEDIATION_2026-09-12.md`.**
> **D1 and D4 are CLOSED.** The OCR transcript is committed with both sha256s and the build is
> reproducible from the repo alone (content-identical across consecutive runs). The prose
> super-set clause is parsed, and the union reconciliation gate is built and **passes: 42 dates,
> 0 mismatches, 2018-06-29 → 2026-09-11**.
> **One correction to D4 below:** the PVR directive was subsequently declared null and void by
> the May-13-2020 press release, so `PVR`'s absence from `n200_membership` is **correct** and the
> table was never missing a member. The blind spot was real — the build could not show it had
> seen the clause — but it had not produced a wrong membership. Fixing it required correcting the
> COVID void, which was keyed to `ind_prs16032020` where the source names March **19**.
> **D5 is partly reduced:** 18 rename pairs now, and intervals starting before first trade drop
> **16 → 14**. D2, D3 and D6 are unchanged.
>
> **Second update — `PTMS_N200_D2_D3_D5_REMEDIATION_2026-09-12.md`. D2, D3 and D5 are now closed
> as far as the sources allow.** 31 rename pairs; pre-listing intervals **16 → 2**, and the two
> survivors (MGL, PNBHOUSING) are reported by name by a new `pre_listing_intervals` gate. The
> terminal check is labelled an identity in both code and store. `backward_breaks` and
> `forward_breaks` are split, the launch state is counted (violations 41 → **42**), and the build
> report's gate table and residuals are rewritten against the audit.
> **One correction to D2 below:** the charge that the MGL/PNBHOUSING diagnosis "does not match the
> dates" was wrong — the prior report's arithmetic (two phantoms less one absentee) is confirmed
> by direct measurement (201 members at 2015-01-01, exactly 2 not yet listed). What it omitted was
> ABIRLANUVO's unmatched exit, the five 202-dates and the launch state. The "all green" criticism
> stands. **D6 is the only defect still open**, and it cannot close: `/data/` is gitignored.

### D1 — BLOCKING: a whole rebalance is sourced from a file in a temp directory

`scripts/isd/build_n200_membership.py:30`

```python
OCR_FALLBACK = {
    'ind_prs23082021.pdf': r'C:\Users\devou\AppData\Local\Temp\opencode\ocr_23082021.txt',
}
```

`ind_prs23082021.pdf` is a scanned image. Its OCR transcript is the **sole source of the entire
2021-09-30 Nifty 200 review** — 6 exclusions (ABBOTINDIA, BBTC, CESC, GODREJAGRO, IBULHSGFIN,
VGUARD) and 6 inclusions (ASTRAL, HINDCOPPER, INDIANB, IRFC, NATIONALUM, TATACOMM). That file
is **not in the repo, not committed, not in the manifest, and has no provenance record**. It
lives in the user temp directory.

The report states *"Reproduce: `python scripts/isd/build_n200_membership.py`"*. **That is false
on any other machine, and false on this one after a temp clean.** The build would then lose a
balanced 6/6 rebalance — and because it is balanced, the count gate would still read 200 and
report no problem (see D4).

This is the pitfall CLAUDE.md already records: *"Mutate a source-of-truth store only from
committed, re-runnable code."* Fix: commit the OCR transcript to `data/reference/nse_index_pr/`
with a manifest row recording that it is OCR-derived and from which PDF, and point the builder
at the committed path.

Related: the builder does `os.remove(OUT_DB)` on every run with no copy-first baseline. Harmless
while the store is new; it violates the standing discipline the moment anything depends on it.

### D2 — "Gates (all green)" is contradicted by the build's own audit table

The report's gate table says *"Member counts: **200 every session** except documented deviations"*.
`n200_audit` says:

- **`forward_violations` = 41** — a gate result that appears nowhere in the report's gate table.
- **41 dates with count ≠ 200**, spanning 2011-11-22 → 2024-03-28.
- Five of those dates read **202, not 201**: 2016-04-01, 2016-09-30, 2016-11-15, 2017-01-23,
  2017-03-31. **The report documents no 202 state anywhere.** (It is arithmetically consistent
  with DVR + the pre-2017 surplus coinciding, but it is undocumented as delivered.)
- **`launch_count` = 201**, and the launch state is **never evaluated by the count gate at all** —
  `counts` begins at the first *event* date, so 2011-07-19 → 2011-11-21 sits outside the 41.

Also a label bug: `backward_breaks` is written to the audit *after* the forward pass has appended
to the same `breaks` list, so the value conflates backward and forward breaks. It reads 0 either
way, so nothing is concealed — but the name is wrong.

The residual section further attributes the pre-2016 surplus to MGL and PNBHOUSING. The surplus
in fact vanishes exactly at **2017-07-05**, the ABIRLANUVO manual exit — not at MGL's 2022-03-31
or PNBHOUSING's 2020-09-25 exits. The stated diagnosis does not match the dates in the table.

### D3 — the terminal gate is a tautology and proves nothing

`build_chain()` derives the launch state by walking **backward** from today's official 200,
inverting each event (`include → discard`, `exclude → add`). It then replays the **same event
list forward** (`include → add`, `exclude → discard`) from that state.

Given `backward_breaks == 0`, the forward pass is the exact inverse composition of the backward
pass over the identical ordered event list. **It must return the anchor. Always.** Delete a whole
press release and the terminal gate still passes — the launch state simply shifts to absorb it.

So `(0 breaks, terminal exact)` carries **one** bit of information, not two. Residual 3's claim —
*"the terminal gate proves the full 2012→present walk reproduces today's list"* — therefore
supports nothing, and the conclusion resting on it ("from ~2018 on the table is exact") is
unsupported **as argued**.

The honest version of that claim, which the evidence does support: post-2018 quality rests on
(a) primary-source parsing fidelity, spot-verified, and (b) counts == 200 from 2020-06-26 onward
with the single documented DVR episode. Say that instead.

### D4 — the gate battery is blind to a missed inclusion paired with a missed exclusion

This is the methodological finding, and it is demonstrated, not hypothesised.

The backward walk only records a *contradiction*. A name that appears in **no event at all**
is silently carried back to `LAUNCH_DATE` — and **201 of 572 intervals start at 2011-07-19**.
For a continuous member that is correct; for a name whose entry event was missed, mis-parsed, or
printed under a pre-rename ticker, it is a false assertion no gate can see. The count gate bounds
only the **net** imbalance: two missed events of opposite sign cancel and read 200.

**Demonstration — PVR.** `ind_prs19032020.pdf` states the Nifty 200 change in **prose, not a
table**:

> "NIFTY 200, being a super-set of NIFTY 100 and NIFTY Midcap 100, PVR Limited will be included
> in NIFTY 200 index upon its proposed inclusion in NIFTY Midcap 100 index."

The parser handles tables; it produces **zero** N200 events from this clause. The builder's own
output records PVR entering **Nifty Midcap 100** w.e.f. 2020-03-27, and NSE's stated rule —
quoted in the PR itself — is that Nifty 200 is the union of Nifty 100 and Nifty Midcap 100.
**`PVR` and `PVRINOX` appear nowhere in `n200_membership`.** Neither boundary is present, so
every count reads 200 and nothing fires.

**Corroboration — 16 intervals assert membership before the security first traded:**

| Symbol | valid_from | first trade | lead (days) |
|---|---|---|--:|
| TMPV | 2011-07-19 | 2025-10-24 | 5,211 |
| SHRIRAMFIN | 2011-07-19 | 2022-12-20 | 4,172 |
| ZYDUSLIFE | 2011-07-19 | 2022-03-07 | 3,884 |
| TATACONSUM | 2011-07-19 | 2020-02-27 | 3,145 |
| PNBHOUSING | 2011-07-19 | 2016-11-07 | 1,938 |
| MGL | 2011-07-19 | 2016-07-01 | 1,809 |
| VEDL | 2011-07-19 | 2015-05-07 | 1,388 |
| UPL, FRL, PEL, DHFL, ADANIPORTS, PIPAVAVDOC, COREEDUTEC, JSWISPAT, HEROMOTOCO | 2011-07-19 | 2011–2013 | 20–827 |

Most are rename/demerger label defects (D5); MGL and PNBHOUSING are true phantoms. Either way
these are **rows in the delivered table asserting index membership on dates when the security
did not exist**, and they are the visible tail of an error class whose size no gate bounds.

**Consequence for the report's residual 3:** "≤2 names out of ~200" bounds the *net* error. The
*gross* error is unbounded by anything in the build. The claim should be restated.

**The fix is available and cheap.** `n200_events` already parses the Nifty 100 and Nifty Midcap
100 streams. Since NSE defines **N200 ≡ N100 ∪ Midcap100**, reconstructing N200 from those two
streams and reconciling against the direct N200 chain is a genuinely independent check that
catches exactly this missed-pair class. That, not the terminal gate, is the gate this build needs.

### D5 — "era-correct symbols" covers 16 rename pairs, not the corpus

The report's headline advantage over the CSV is contemporaneous tickers: *"Symbols are
as-printed at the time (era-correct across renames)."* `load_rename_dates()` asserts **16**
pairs from `symbol_changes`. Everything else is projected backward under its modern ticker.

Absent from `n200_membership` entirely: `HEROHONDA`, `SESAGOA`, `SSLT`, `TATAGLOBAL`,
`CADILAHC`, `SRTRANSFIN`, `MUNDRAPORT`, `UNIPHOS`. Present instead, spanning back to launch:
`HEROMOTOCO`, `VEDL`, `TATACONSUM`, `ZYDUSLIFE`, `SHRIRAMFIN`, `ADANIPORTS`, `UPL`.

So for these names **the new store is back-mapped in exactly the way the CSV was faulted for**,
and a naive symbol join over 2012–2020 silently loses them. The advantage is real for the 16
handled pairs (GMRINFRA, ADANITRANS, LTI/MINDTREE, ZEEL are correctly split) — it is not general,
and the report should scope the claim.

### D6 — the deliverable is not in git

`scripts/isd/build_n200_membership.py` and `docs/reports/N200_PIT_MEMBERSHIP_BUILD.md` are both
**untracked**. The store is therefore not attributable, not durable, and not reviewable by diff.

---

## 4. Disposition

**A1: NOT SATISFIED. C2: NOT CERTIFIED.** Neither status changes.

The store is nonetheless the strongest membership artefact in the repo and is worth keeping and
finishing. Ordered next actions:

1. **D1 first** — commit the OCR transcript with provenance; the build is not reproducible until
   then, and nothing should depend on the store while that holds.
2. **D4's reconciliation gate** — rebuild N200 from the already-parsed N100 ∪ Midcap100 streams
   and diff against the direct chain. This is the only proposed check that can bound gross error.
3. **Correct the report** — D2 (41 violations, five 202-dates, launch state uncounted, the
   MGL/PNBHOUSING diagnosis), D3 (drop the terminal-gate claim, substitute the supported one),
   D5 (scope era-correctness to the 16 pairs).
4. **Handle the prose superset clause** in the parser, then re-run and re-check PVR.
5. Commit the script, report and store together (D6).

None of this is authorized here, and none of it should touch `universe_membership` — which feeds
the CSMP/PSB lineage — without its own scoped authorization and copy-first baseline.
