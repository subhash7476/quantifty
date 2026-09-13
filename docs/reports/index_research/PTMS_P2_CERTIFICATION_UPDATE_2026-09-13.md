# PTMS — P2 substrate certification, evidence update

**Date:** 2026-09-13 · **Authority:** operator instruction — *"do whatever you have to clear the
substrate certification, check everything and ensure all is good."*
**Access level:** meta + substrate verification. No OHLC value entered a feature, signal, label or
fitted parameter; every figure below is a count, a stamp, a class or a boolean.
**Supersedes nothing.** `PTMS_P2_CERTIFICATION_REPORT_2026-09-12.md` stands as written; this is
the evidence gathered since, and the per-surface row it adds.

> **What changed today.** C3's blocking defect is **closed** — `cas_category` was stale, not
> short, so a rebuild from the (point-in-time) futures bhavcopy covered every session and the 10
> unmarked post-CAS sessions are now marked. C1's era rule now exists **as code that refuses**
> rather than as a frozen candidate in a construct's config, with two independent arms of evidence
> for the native era and a store-wide census artifact. Three files that held another session's
> rows were repaired, and two live-infrastructure defects found on the way were fixed with tests.
>
> **What did not change: I am not writing CERTIFIED on anything.** The evidence below supports a
> scoped certification and says exactly where it stops. The stamp is the operator's.

---

## 1. The surface this is about

| | |
|---|---|
| Surface | **Equity breadth 1m** (`NSE_EQ|INE…`), per-day DuckDB files |
| Universe | **Nifty 100, point-in-time** — `data/isd/n100_membership.duckdb`, built from NSE press releases and gated monthly against 198 MCWB archives, independent of the candle store it audits |
| Window | **2023-01-02 → 2026-09-11**, 917 sessions (was 2026-08-28; C3 no longer binds it) |
| Clock | **Native era, start-labelled** — the bar stamped *t* covers *t → t+1* |

### Per-gate evidence

| Gate | Evidence | Residual inside the fence |
|---|---|---|
| **C1** timestamp semantics | Era rule as code (`core/market/bar_labeling.py`), two agreeing arms (§2), census over all 917 sessions: **917/917 native, 911 OK, 4 GAP, 0 REFUSED, 0 MISDATED** | 4 sessions with 10 missing minutes in total (§2.3) |
| **C2** PIT & entity | A1 discharged by substitution · A2-1 closed · A2-2 resolved · A3 certified · A4 PASS · A5 vacuous under this universe · **A6 scoped out by ruling** | HDFC 130 sessions, **accepted at 99/100 by ruling** |
| **C3** tradeability & synthetics | `cas_category` rebuilt to 2026-09-11 · all 30 post-CAS sessions marked · **0 index rows marked** · coverage **0 absent (session, name) cells across 917 sessions** | **548 rows on 2 sessions carry a synthetic flag that cannot be true** (§4.2) |
| **C4** VIX | Complete per the 09-12 report | 2021-02-12 quarantined |

---

## 2. C1 — the era rule, its evidence, and the artifact

### 2.1 The rule, as code that refuses

`core/market/bar_labeling.py` generalizes AP-D4's `observed_bar_labeling` store-wide, as the plan
required — verified, not rediscovered. Two things make it more than a copy of the analog-path
config:

- **It resolves against the session's own open, not a hardcoded 09:15.** First bar at the open →
  start-labelled; one minute after the open → end-labelled. That is why it holds unchanged on a
  Muhurat session opening 13:45 and on a split Saturday.
- **It raises `UnknownLabeling` on anything else.** The census below turns that into a class rather
  than a crash, but nothing silently guesses. Two files in the store exercise it (§2.4).

### 2.2 Two agreeing arms for the native era

The plan requires at least two. Both are event-anchoring arms (C1-c), independent of any second
feed's convention.

**Arm 1 — the opening print.** Under end-labelling a bar stamped 09:15 would have to cover
09:14→09:15, minutes the market was shut. The native era's first bar is stamped 09:15 on **917 of
917** sessions in the fence. The vendor era is the control and behaves exactly as end-labelling
predicts: first bar **09:16**, last bar **15:30**. The same session boundary, two eras, and the
one-minute shift visible at both ends.

**Arm 2 — the CAS 15:15 halt.** Since 2026-08-03, Category I continuous trading stops at 15:15 by
exchange schedule. Measured across all 30 post-CAS sessions, for Category I symbols only:

| Minute stamp | Sessions where it carries traded bars (volume > 0) |
|---|---|
| 15:14 | **30 of 30** (206–210 symbols each) |
| **15:15** | **0 of 30** |

Under end-labelling the bar stamped 15:15 covers the last trading minute and must carry volume; it
carries none anywhere. Under start-labelling 15:14 covers 15:14→15:15 (trading) and 15:15 covers
15:15→15:16 (halted). **The test uses `volume > 0`, never `is_synthetic`**, so it is independent of
the marker that sets that flag — otherwise the marker's own 15:15 cutoff would be doing the work.

**C1-a is untouched and still needs the operator.** The vendor bundle's own specification remains
the one arm nobody can run for you. It does not block this fence: a 2023+ study never crosses the
seam.

### 2.3 The census artifact

`scripts/isd/census_1m_labeling.py` → `data/isd/c1_labeling_census_eq.jsonl` (fence) and
`c1_labeling_census.jsonl` (store-wide). Per file: observed first/last stamp, resolved labelling,
every missing and every extra minute, rows stamped for another date, and rows whose synthetic flag
contradicts its definition. Expected minutes come from `session_windows`, so a 60-minute Muhurat
and a split Saturday are measured against their own shape instead of failing a 375 constant.

**Fence result, 2026-09-13:**

```
917 files 2023-01-02 -> 2026-09-11
  labelling: {'native': 917}
  classes:   {'OK': 911, 'GAP': 4, 'SYNTHETIC_LIES': 2}
```

The four GAP sessions, in full — whole-market minute outages, every symbol absent:

| Session | Missing minutes | Count |
|---|---|--:|
| 2023-07-12 | 14:57 | 1 |
| 2023-07-24 | 12:49, 12:50, 12:51 | 3 |
| 2023-08-07 | 15:23 | 1 |
| 2024-04-23 | 10:52, 10:53, **10:55**, 10:56, 10:57 | 5 |

**Ten missing minutes in 343,875 session-minutes.** They are *not* repaired, deliberately: the
store was itself built from the Upstox historical API, so the absence is almost certainly upstream,
and the only way to test that is a re-fetch that **rewrites existing bars on today's CA basis**.
The store is corporate-action adjusted; re-fetching part of a symbol's 2023 could leave that symbol
on a mixed basis. A ten-minute hole is a smaller defect than that cure. Enumerated here so a loader
can declare them rather than trip on them.

### 2.4 What the store-wide census adds (outside this fence)

The same script over all **3,612 files, 2012-01-02 → 2026-09-11**:

```
labelling: {'vendor': 2438, 'native': 1162, unresolved: 12}
classes:   {'OK': 3302, 'EXTRA': 261, 'GAP': 34, 'REFUSED': 12, 'SYNTHETIC_LIES': 3}
```

**The pre-2023 store is materially messier than the fence, and that is the argument for scoping
the certification rather than a footnote to it.**

- **The vendor-era seam is per symbol, not per date.** 247 of the 261 EXTRA files are 2022
  sessions that resolve *native* — `Nifty Bank` and `India VIX` open 09:15 — while
  `NSE_INDEX|Nifty 50` carries a 15:30 bar; 166 EXTRA files have exactly one extra minute, and it
  is 15:30. The same split appears on 2023-01-31. So the repo's "2023-01-31 is on the vendor
  convention" is true **only of Nifty 50**, and the boundary is a per-series property.
- **12 REFUSED — the rule declining to guess, which is what it is for.** Six Saturday special
  sessions (first bar ~11:08, ~93 minutes), three late-start index sessions (09:19, 09:21, 09:35),
  one pre-2023 Muhurat (2022-10-24, 18:15→19:14), and the two `MCX_FO` days that open 09:00 and run
  to 23:54. **Ten of those twelve are the maintenance obligation made concrete:** `SPECIAL_SESSIONS`
  holds only the five special sessions inside the 2023+ window I measured, so every earlier one
  still falls through to the era schedule.
- **34 GAP files outside the fence**, 18 of them in 2012.
- **11 index sessions in Apr–May 2025 carry post-close prints** at 15:39/15:59 — the same class as
  the equity tails pruned on 2026-09-13, in the index series, and **not** repaired: the equity
  pruner is `NSE_EQ`-scoped by design, and that scoping is what protects the MCX contracts and the
  2023-01-31 seam bar gate C1 exists to explain.
- **A third SYNTHETIC_LIES file**, 2026-02-18, is `MCX_FO` rows carrying the flag. Same class as
  §4.2 and outside the equity universe.

---

## 3. C2 — under this universe

Nothing in C2 changed today; this records the state the dispositions left it in.

| Arm | State |
|---|---|
| A1 `pit_membership` circularity | **Discharged by substitution** — the study uses `n100_membership`, built from press releases + MCWB, not from the candle store. `pit_membership` itself remains circular and unused |
| A2-1 interval endpoint | CLOSED (retraction + one real consumer fix) |
| A2-2 stale mapping | RESOLVED — 211 unmapped symbols → 0 |
| A3 ISIN issuer-prefix linkage | CERTIFIED |
| A4 `prev_close` identity | PASS — 5 mismatches in 6,544,193 calendar-adjacent pairs |
| A5 adjusted-series continuity | **Vacuous under this universe** — none of the 5 Arm-A items or 6 quarantined entities was ever an N100 or N200 constituent. Still a whole-panel blocker |
| A6 sector / thematic PIT | **Scoped out** by operator ruling 2026-09-13; clause and cost in `PTMS_N100_1M_COVERAGE_BACKFILL_2026-09-13.md` §10 |

**Coverage, re-measured today after the C3 rebuild: 917 sessions, 0 absent (session, name) cells.**
The sole residual is HDFC on 130 sessions (2023-01-02 → 2023-07-12), delisted at the merger,
accepted at 99/100 by operator ruling, with its three obligations recorded in §11 of that report.

**One documentation residual:** `n100_membership.duckdb`'s `n100_audit` table carries interval
counts, terminal checks and the 23 overrides, but **no G1/G3/G5 rows** — the delivered report's
"368/368 MCWB months agree" is not in the artifact. G3 was reproduced independently (184 months
from the delivered intervals, 0 mismatches), so this is a provenance gap in the audit table, not a
data defect. Recorded rather than patched: adding rows without re-running that build would fake
provenance.

---

## 4. C3 — the blocker is closed, and one new finding

### 4.1 V3 closed — the table was stale, not short

`data/cas/cas_category.duckdb` ended 2026-08-28 and 10 post-CAS sessions carried **zero** synthetic
marks, so their carry-forward bars read as real trades. The plan listed this as an operator
dependency ("authority to fix or escalate V3").

**The fix needed no new data and no ingest.** `cas_category` is derived from `futures_bhavcopy`,
which is genuinely point-in-time (a contract traded on a date, or it did not) — and that store
**already ran to 2026-09-11**. The table had simply not been rebuilt.

| Step | Evidence |
|---|---|
| Baseline first | `data/_baselines/cas_category_pre_rebuild_2026-09-13/` + `intervals_before.json` |
| Rebuild (`scripts/cas/build_cas_category.py`) | 366 intervals in, **366 out**; **0 new runs, 0 vanished runs, 0 end-dates changed for any reason other than extension**; 210 runs extended past 2026-08-28; new max `effective_to` **2026-09-11** |
| Mark (`mark_synthetic_bars.py --apply --since 2026-08-31`) | **10 sessions, 28,660 bars flagged**, 2,736–2,926 per session — in line with the 2,703–2,912 of the 20 already-marked sessions |
| Index safety | **0 non-equity rows marked** on any of the 10 |
| Coverage | the 10 sessions are no longer REFUSED by the N100 backfill; **0 absent cells** across the full 917 |

**The fence end moves from 2026-08-28 to 2026-09-11** as a result — C3 no longer binds it.

**Standing obligation, now in `CLAUDE.md`: rebuild `cas_category` whenever the futures store
advances.** Nothing couples them, so the same silent gap reopens on its own.

### 4.2 New finding — 548 rows carry a synthetic flag that cannot be true

`is_synthetic` has exactly one documented meaning: a CAS auction carry-forward bar, defined by
`is_carry_forward()` — equities only, post-CAS only, `volume == 0`, inside the auction window. The
census now asserts that definition instead of counting marks, and two sessions violate it:

| Session | Symbol | Rows marked | Volume > 0 | Stamps |
|---|---|--:|--:|---|
| 2026-03-02 | MOTHERSON · CHOLAFIN | 205 | **205** | 09:15 → 11:38 |
| 2026-03-04 | MOTHERSON · CHOLAFIN | 343 | **343** | 09:15 → 15:00 |

Both dates are **pre-CAS**, every row **carries volume**, and both names are Nifty-100
constituents. `is_carry_forward()` returns False on both counts, so the live aggregator cannot have
written these; the historical fetcher writes FALSE; the marker refuses pre-CAS sessions. The one
path that could carry them is `migrate_monolith_to_isolated.py`, which copies `is_synthetic`
through from the pre-migration store — **i.e. the provenance is not recoverable.**

**Not repaired, and that is the argued position, not an omission.** Clearing the flag would assert
these are ordinary tick-aggregated bars, and I cannot support that: the flag may be recording
something true about them (reconstructed rather than aggregated), and the writer is unknown.
Deleting an unexplained warning is worse than keeping it. The cost of keeping it is bounded and
stated: a construct obeying the mandated `is_synthetic = FALSE` filter loses **2 constituents on 2
sessions, partial days**. If the operator wants them cleared, it is a one-rule committed script
with copy-first — but it needs a decision, not an inference.

---

## 5. C4 — unchanged

Complete as of the 09-12 report: canonical 1m VIX 2022-01-03 → 2026-09-11 less the 88-session V2
quarantine; vendor 1m and EOD CSVs certified with their quarantines; 2021-02-12 permanently
quarantined by operator ruling. Nothing today touched it.

---

## 6. Repairs applied today

Every one through committed, re-runnable code, with the baseline taken **before** the write.

| Repair | Scale | Script | Baseline |
|---|---|---|---|
| `cas_category` rebuilt to 2026-09-11 | 210 intervals extended, 0 other changes | `scripts/cas/build_cas_category.py` | `data/_baselines/cas_category_pre_rebuild_2026-09-13/` |
| 10 post-CAS sessions marked | 28,660 bars | `scripts/cas/mark_synthetic_bars.py --apply --since` | `*.duckdb.pre_cas_mark` per file |
| Misfiled rows removed from 3 files | **23,670 rows**, 0 refused, 0 remaining | `scripts/cas/prune_misdated_bars.py --apply` | `data/_baselines/1m_pre_misdated_prune/` |

The misfiled rows are worth a line of their own. 2026-02-25 held 12,221 rows stamped 2026-02-24,
2026-03-02 held 11,436 stamped 2026-02-27, 2026-03-04 held 13 stamped 2026-03-02 — so any reader
that trusts the filename (and every reader does) mixed two sessions. **The script proves losslessness
per row before deleting**: a row goes only if the correct file already carries that
`(symbol, timestamp)`, or if its stamp falls outside the owning session's own window. All 23,670
qualified; of the duplicated ones only 12,541 agreed with the good copy on close and volume, the
rest being partial aggregates — i.e. they were strictly poorer copies in the wrong place.

### Two live-infrastructure defects fixed on the way

- **`session_schedule` had no concept of a special session** and answered 09:15–15:30 on all five —
  three Muhurat sessions and two NSE special Saturdays. The Saturdays trade in **two blocks**
  (09:15–10:00 and 11:30–12:30, measured from the bars), so `SPECIAL_SESSIONS` now holds a tuple of
  windows per segment, `session_window` returns outer bounds, and `is_open` checks each window —
  the 90-minute recess reads shut. Before the fix `any_open` was True across it.
- **`mark_synthetic_bars` overwrote its own copy-first snapshot on a re-run**, which is precisely
  the hazard `CLAUDE.md` warns about: the snapshot's value is that it predates the *first* mark. It
  now never overwrites an existing one, and `--since` lets a newly-ingested tail be marked without
  re-entering already-marked files.

---

## 7. What is **not** certified

**Globally — unchanged and not addressed today:**

- **C1-a**, the vendor bundle's own timestamp specification. Operator dependency.
- **The vendor-era index slice.** Two arms cover the native era; the pre-2023 slice keeps its frozen
  candidate rule and now a measured complication (§2.4: the seam is per symbol).
- **C2-A5**, whole-panel: 5 Arm-A items still need adjudication, one of which would edit a closed
  battery's register. Vacuous under this universe, not resolved.
- **C2-A6**, whole-panel: no PIT sector table exists. Scoped out here, not built.
- Every non-equity surface in the 09-12 matrix (1d family, equity/futures/options EOD) — those rows
  still read UNCERTIFIED and nothing today changed them.

**Inside the fence — three enumerated residuals, all small and all named:**

1. **10 missing minutes** across 4 sessions (§2.3) — unrepaired by argument, not oversight.
2. **548 rows with a false synthetic flag** on 2 sessions (§4.2) — needs an operator decision.
3. **HDFC, 130 sessions** — accepted at 99/100, with obligations recorded.

---

## 8. Verification — commands and timestamps

Every claim above reproduces from these, run 2026-09-13:

```bash
python scripts/isd/census_1m_labeling.py --from 2023-01-02 --symbols eq
python scripts/cas/backfill_n100_1m.py                 # plan only: 917 sessions, 0 absent cells
python scripts/cas/prune_misdated_bars.py              # plan only: 0 files
python scripts/cas/prune_post_close_bars.py            # plan only: 0 sessions
python -m pytest tests/market tests/cas -q             # 51 passed
```

Test state at the time of writing: **582 passed, 4 skipped** across `tests/market`,
`tests/database`, `tests/execution`, `tests/options_wall`, `tests/cas`. The full suite carries **2
pre-existing failures** (`tests/g1/test_g1_closure_guard.py`, offending files
`core/execution/options/nifty_shield_groups.py` and `nifty_shield_sizing.py`) and **12 errors** in
`tests/trade_intelligence/test_builder.py` — both in code untouched by this work, verified by
reading what the guard names.

---

## 9. The decision that is not mine

The evidence supports certifying **one surface over one window for one universe**: equity breadth
1m, Nifty-100 PIT, 2023-01-02 → 2026-09-11, native start-labelled clock, with the three residuals in
§7 declared rather than hidden. It does not support a whole-panel or whole-store certification, and
§7 says why in each case.

**Certifying is the operator's act.** What is done is the work that was blocking it.
