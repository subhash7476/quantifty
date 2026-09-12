# N200 membership build — D1 and D4 remediation, and the rerun

**Date:** 2026-09-12 · **Authority:** operator task "fix D1 and D4, then rerun the build".
**Scope:** D1 and D4 from `PTMS_N200_MEMBERSHIP_BUILD_REVIEW_2026-09-12.md`, plus the two
defects that had to be fixed for D4 to be implementable (§3). D2, D3, D5 and D6 are **not**
addressed here except where the rerun moves their numbers.
**Baseline before any write:** `data/_baselines/n200_membership.pre_d1_d4_2026-09-12.duckdb`.

> **Result: D1 and D4 are both closed. The union gate passes — 42 dates checked, 0 mismatches.
> The delivered membership table changed by exactly two rename-era splits and nothing else.
> A1 is unaffected and remains NOT SATISFIED; C2 remains NOT CERTIFIED.**

---

## 1. D1 — the build is reproducible now

`ind_prs23082021.pdf` is a scanned image that `pypdf` cannot read, and its OCR transcript is the
sole source of the 2021-09-30 Nifty 200 review. It was loaded from `%TEMP%\opencode\`.

- Transcript moved into the data tree at `data/reference/nse_index_pr/ind_prs23082021.ocr.txt`,
  beside the 228 PDFs it belongs with. `/data/` is gitignored repo-wide, so this is the same
  durability every other source artefact the build reads already has — the point of D1 was never
  git, it was that a load-bearing input sat in `%TEMP%` outside the source tree entirely.
- `manifest.csv` carries a provenance row: `status=ocr_transcript`,
  `url=derived-from:ind_prs23082021.pdf`, note recording **both** sha256 digests
  (txt `99fbf830…`, pdf `c9b9feef…`), so the transcript can be checked against the scan it came
  from. Manifest is now 229 rows (228 PDFs + 1 transcript).
- `OCR_FALLBACK` holds a bare filename resolved against `PR_DIR`; `ocr_pages_text()` hard-fails
  with the path if it is missing, instead of silently building without a rebalance.

**Verified:** `grep -nE "AppData|Temp|opencode|[A-Z]:\\\\"` over the builder returns nothing —
no path outside the repo remains. Two consecutive runs produce **identical contents in all three
tables** (`n200_events`, `n200_membership`, `n200_audit`: 0 rows either way in both directions).
`python scripts/isd/build_n200_membership.py` is now a true reproduction command.

## 2. D4 — both halves

### 2a. The prose super-set clause is parsed

NSE sometimes states a Nifty 200 change in prose rather than a table:

> "NIFTY 200, being a super-set of NIFTY 100 and NIFTY Midcap 100, PVR Limited will be included
> in NIFTY 200 index upon its proposed inclusion in NIFTY Midcap 100 index." — `ind_prs19032020.pdf`

`SUPERSET_PAT` now matches this shape inside an index section and emits the directive as a normal
event; the symbol resolves from the company name through the existing pass. A corpus sweep finds
this phrasing in exactly one file, so the addition is narrow by design.

**The event is now recorded — and correctly voided.** See §3a: the March-19 announcement was
declared null and void, so the row lands as `void_covid` and never reaches the chain.

```
ind_prs19032020.pdf | 2020-03-27 | include | PVR Limited | PVR | void_covid
```

**This corrects the review.** `PVR` is still absent from `n200_membership`, and that absence is
**correct** — PVR never became a Nifty 200 member. The review's D4 was right that the directive
was invisible to the build, and wrong to imply the membership table was therefore missing a
member. What the build previously could not show is that it had *seen* the clause at all; it can
now, and the audit trail records both the directive and its cancellation.

### 2b. The union reconciliation gate

NSE defines **Nifty 200 = Nifty 100 + Nifty Midcap 100**, stated in the press releases themselves.
Checked against today's three official lists first: **100 + 100, disjoint, union == the 200, zero
difference** — so the premise is not assumed, it is verified.

`union_gate()` walks the Nifty 100 and Nifty Midcap 100 event streams backward from their own
official anchor lists, replays them forward, and compares `N100(d) ∪ Midcap100(d)` against the
membership **as actually written to `n200_membership`** at every event date in the window.

This is the only check in the build that can see a **missing inclusion paired with a missing
exclusion**: the backward walk records contradictions only, so a name touched by no event is
silently carried back to launch, and the count gate bounds the net error, so a symmetric pair of
dropped events leaves it reading 200. A reconstruction from two independent streams has neither
blind spot — and unlike the terminal gate (D3), it is not the inverse of the walk it checks.

**Scope:** 2018-06-29 onward. Before that the midcap stream is spread across five renamed labels
(CNX Midcap, Nifty Free Float Midcap 100, Nifty Full Midcap 100, …) and reconstructing it is a
separate problem. The window covers exactly the era the build report claims is exact.

**Result:**

| Gate row | Value |
|---|---|
| `union_gate_start` | 2018-06-29 |
| `union_gate_dates` | **42** |
| `union_gate_mismatch_dates` | **0** |
| `union_gate_n100_breaks` | 1 |
| `union_gate_m100_breaks` | 0 |

The one residual Nifty-100 backward break is an auxiliary-stream inconsistency; it does not move
the verdict, since the union still reconciles exactly on every date.

## 3. Two defects that had to be fixed to get there

Both were surfaced by the work above, and D4 could not be implemented correctly without them.

### 3a. The COVID void was keyed to the wrong file

The May-13-2020 press release voids the reviews announced *"vide press release dated February 18,
March 12 and **March 19**, 2020"*. `VOID_COVID_FILES` named `ind_prs16032020` (March **16**)
instead of `ind_prs19032020` (March 19) — so the March-19 announcement stayed live.

That was latent while the March-19 file produced no Nifty 200 events. The moment §2a made it
produce one, the void had to be right or PVR would have been injected into the index with no
matching exit.

Fixed by keying the void on the **effective date** rather than a file list. Only four files carry
2020-03-27 rows and all four are inside the deferred tranche, so the date is the exact and
unambiguous key: nothing took effect on 2020-03-27 but the already-executed NIFTY 50 / Bank
rebalance, which keeps its existing exception. `void_covid` rows: 559 → **604**.

Note the March-16 file was never mishandled in substance — its operative rows are dated
2020-03-19 (the Yes Bank acceleration) and correctly drive `YESBANK`'s exit; only its restatement
of the deferred tranche was being voided, which remains the right outcome under the date rule.

### 3b. Footnote lines were being glued onto the row above

A table row and its footnote extract as separate lines:

```
1 Tata Power Co. Ltd.* TATAPOWER
* Excluded on account of inclusion in Nifty 100
```

The continuation state machine appended the footnote to the row and peeled its last token as the
symbol — so `… exclusion from Nifty Midcap 150` produced the **symbol `150`**, and `… w.e.f.
March 27, 2020` produced the **symbol `2020`**. Fifteen rows across Midcap 50/100, MidSmallcap
400, Smallcap 100, Nifty 500 and others carried a bogus numeric symbol.

**The Nifty 200 stream was never affected** — zero numeric symbols ever reached it — but the
corruption blinded the new gate: with `TATAPOWER`'s Midcap-100 exclusion recorded against `150`,
the union disagreed with N200 on every date. Fixed by treating a line opening with `*` or `#`
followed by a letter as a footnote, never a data row.

## 4. What the rerun changed in the delivered table

Exactly four rows added, two removed — two rename-era splits, nothing else:

| | symbol | valid_from | valid_to |
|---|---|---|---|
| removed | ZYDUSLIFE | 2011-07-19 | — |
| added | CADILAHC | 2011-07-19 | 2022-03-07 |
| added | ZYDUSLIFE | 2022-03-07 | — |
| removed | SHRIRAMFIN | 2011-07-19 | — |
| added | SRTRANSFIN | 2011-07-19 | 2022-12-20 |
| added | SHRIRAMFIN | 2022-12-20 | — |

`CADILAHC→ZYDUSLIFE` and `SRTRANSFIN→SHRIRAMFIN` were added to `RENAME_PAIRS` (both dated from
NSE's own `symbol_changes`) because the union gate saw the Nifty 100 / Midcap 100 streams carrying
the old labels while the N200 chain carried only the modern one. A third divergence, `MCDOWELL`,
is **not** a rename — `symbol_changes` has no such record; the 2014 release simply prints
`MCDOWELL` for United Spirits, whose ticker was `MCDOWELL-N` throughout — so it is handled by a
new one-entry `SYMBOL_ALIASES` map rather than by inventing a rename.

Both splits are **corrections**: they retire two of the intervals that asserted membership before
the ticker existed. That count drops **16 → 14** (D5's remaining 14 are untouched here).

## 5. Full state after the rerun

| Check | Before | After |
|---|---|---|
| Backward-chain breaks | 0 | **0** |
| Terminal open set vs official 200 | exact | **exact** |
| Intervals / distinct symbols | 572 / 455 | **574 / 457** |
| Overlapping intervals per symbol | 0 | **0** |
| Open intervals at terminal | 200 | **200** |
| N200 events with no symbol / no effective date | 0 / 0 | **0 / 0** |
| Bogus numeric symbols, all indices | 15 | **0** |
| Intervals starting before first trade | 16 | **14** |
| `void_covid` rows | 559 | **604** |
| **Union gate (2018-06-29 → 2026-09-11)** | — | **42 dates, 0 mismatches** |
| Reproducible from the repo alone | **no** | **yes, content-identical across runs** |
| `forward_violations` (count ≠ 200) | 41 | 41 — **unchanged, D2 not addressed** |
| `launch_count` | 201 | 201 — **unchanged** |

## 6. What is still open

- **D2** — the build report's "Gates (all green)" still contradicts `forward_violations = 41`,
  the five undocumented 202-dates, and the uncounted launch state. Not touched.
- **D3** — the terminal gate remains a tautology. It is now joined by a gate that is not one, so
  the honest claim for the post-2018 era is available; the report text still needs correcting.
- **D5** — era-correctness now covers 18 rename pairs, not 16. Fourteen intervals still back-project
  a modern ticker to 2011 (`TMPV`, `TATACONSUM`, `VEDL`, `UPL`, `ADANIPORTS`, `HEROMOTOCO`, …),
  and `MGL` / `PNBHOUSING` remain true phantoms.
- **D6** — the builder and the reports are now committed. The **store and the PR corpus cannot
  be**: `/data/` is gitignored repo-wide. Their durability rests on the manifest, the sha256s and
  the fact that the builder reproduces the store content-identically from them.
- The pre-2018 union gate (the renamed midcap-label era) is not built.
- **A1 is unchanged.** The panel/N200 overlap measurement in the review stands: the two universes
  are neither nested nor congruent, so `pit_membership`'s circularity is unrepaired.
