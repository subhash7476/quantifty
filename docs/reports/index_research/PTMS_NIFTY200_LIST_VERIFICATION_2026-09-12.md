# Verification — `ind_nifty200list.csv` vs the A1 problem

**Date:** 2026-09-12 · **Access level:** meta only. No research window spent.

**Verdict: the file is authentic and correct — and it cannot solve A1.** It is a *current
survivor snapshot*, A1 is a *point-in-time* problem, and the universe it describes is not the
universe A1 concerns. A concrete non-circular path to A1 does exist, and it is not this file (§4).

---

## 1. The file checks out as what it is

| Check | Result |
|---|---|
| Rows / distinct symbols | **200 / 200** — no duplicates |
| Series | all `EQ` |
| ISIN format | **200/200 `INE*`** — all equity, no fund or govt paper |
| Symbols absent from our equity panel | **0** — every name resolves |
| vs the pipeline's own cached `universe_raw/nifty200_current.csv` | **identical — 0 adds, 0 drops** |

It matches, symbol for symbol, the copy `build_universe.py` fetched itself during today's
rebuild (audit probe: `current_list_validation_only … 200 200 symbols`). Nothing is wrong with
the file.

## 2. Validation cross-check it *is* good for

Against the charter-locked mechanical universe (top 200 by 6-month median turnover) at the
latest rebalance, **2026-09-11**:

| Measure | Value |
|---|---|
| Overlap with the official list | **157 / 200 = 78.5%** |
| Official names the mechanical rule misses | 43 |

The misses are the expected shape — index constituents with modest turnover: `COLPAL`,
`DABUR`, `CONCOR`, `IRCTC`, `BAJAJHLDNG`, `GODFRYPHLP`, `LICHSGFIN`, `M&MFIN`, `ALKEM`,
`ASTRAL`… A turnover rule systematically under-selects low-float, low-churn names. **78.5% is
a useful, honest calibration number for the mechanical reconstruction** — and that is exactly
the role `build_universe.py` already assigns this file: *"A snapshot of today's list is fetched
for a validation cross-check ONLY … it is never a membership input."*

## 3. Why it cannot solve A1 — three independent reasons

**(a) It has no dates.** Every row is "as of today". Membership changes twice a year and names
enter and leave; a present-day list applied to 2023 states that today's survivors were members
then. `docs/DATA_STORE_MAP.md` names `nifty200_current.csv` explicitly as a **time-travel
source**, and this is the same file. Using it as history is precisely the bias the PIT
machinery exists to prevent.

**(b) It is the wrong universe.** A1 concerns `data/isd/pit_universe.duckdb:pit_membership`,
which covers the **intraday 1m panel** — ~190–197 names, keyed by *entity* (e.g.
`360ONE,IIFLWAM`, `ADANIENSOL,ADANITRANS`), an F&O-shaped set, not Nifty 200. Even a perfect
PIT Nifty-200 history would answer a different question.

**(c) It does not address the circularity.** A1's defect is that `intraday_present` is `TRUE`
on all 173,900 rows because it was derived from the candle files themselves — so we cannot
distinguish *"this name was not investable on date D"* from *"the ingest did not write it on
date D"*. A constituent list, current or historical, speaks to neither.

## 4. What *would* solve A1 — and it looks reachable

A non-circular PIT universe needs a membership signal **not derived from the 1m candle store**.
The repo has one: the **futures bhavcopy**. Which contracts existed and traded on date D is an
independent fact about F&O eligibility, recorded in `data/market_data/futures_bhavcopy.duckdb`
(1,495,989 rows, **2016-02-11 → 2026-09-11**) — a store the 1m panel does not feed.

`fo_eligible_intervals` is already a partial precomputation of exactly this: 9,092 rows, 235
underlyings — but **weekly-chunked and spanning only 2024-09-02 → 2025-07-18**, so it does not
cover the 2023→2026 intraday window and cannot be used as-is.

**The path:** derive per-date F&O eligibility directly from `futures_bhavcopy` across
2023-01-02 → present, join to the intraday panel on entity keys, and certify that the resulting
membership is independent of the candle files. That yields the missing distinction: a name
F&O-eligible on date D but absent from the 1m store is a **coverage gap**, not an absence from
the universe — which is the very thing `pit_membership` currently cannot say.

**This is a proposal, not work done, and it is outside the current A2-2 task.** It does mean
A1's "permanent blocker" status deserves re-examination: it is permanent only for as long as
membership is derived from the panel it is meant to certify.

## 5. Recommendation

1. **Keep the file** — it is a valid validation input and matches what the pipeline fetches.
2. **Do not** wire it into membership. Its only legitimate role is the 78.5% cross-check above.
3. **Do not** treat A1 as solved. Nothing in this verification changes C2's status: **C2
   remains NOT CERTIFIED**, and Family F remains substrate-blocked.
4. If A1 is worth reopening, authorize the §4 futures-derived path as its own scoped task.
