# Nifty 100 — 1m coverage gap: backfill, result, and what it turned up

**Date:** 2026-09-13 · **Authority:** operator task "fix the 1m coverage gap for nifty 100".
**Baselines:** `data/_baselines/1m_pre_n100_backfill/` (copy-first, per touched file, never overwritten).
**Script:** `scripts/cas/backfill_n100_1m.py` (plan by default, `--apply` to write).

> **Result: the gap is closed. Nifty-100 constituents absent from the 1m store fall from a mean
> of 11.0 per session to 0.143, and sessions at full 100/100 coverage rise from 41 to 777 of 907.
> The sole residual is HDFC on 130 sessions — delisted at the 2023-07-13 merger and unfetchable;
> accepted at 99/100 by operator ruling 2026-09-13 (§11).**
>
> **Three defects had to be fixed to get there, two of them pre-existing and affecting other
> pipelines. A fourth finding is not a defect I introduced but a property of the substrate nobody
> had recorded: the 1m store holds corporate-action-ADJUSTED prices, not as-traded.**

---

## 1. Result

| Measure | Before | After |
|---|--:|--:|
| Sessions scanned (2023-01-02 → 2026-08-28, calendar sessions) | 918* | **907** |
| Mean N100 constituents absent per session | **11.0** | **0.143** |
| Max absent on any session | 100 | **1** |
| Sessions at full 100/100 coverage | **41** | **777** |
| Absent (session, name) cells | 10,092 | **130** |

\* the earlier figure scanned files; 907 is the count after excluding a file that is not a session (§2c).

Verified twice: once by the script's own re-check, once by an independent scan that rebuilds the
ISIN resolution from scratch and never calls the script's code.

**The sole residual is `HDFC`**, absent on all 130 sessions of 2023-01-02 → 2023-07-12. HDFC was
a Nifty-100 member until the 2023-07-13 merger into HDFCBANK; the instrument is delisted, carries
no live `instrument_master` row, and Upstox rejects the dead ISIN `INE001A01036` on every chunk.
It is **not fetchable from this source** and is reported by name rather than silently skipped.
For that window the panel is 99/100, with HDFCBANK present throughout.

Also out of reach: **10 post-CAS sessions (2026-08-31 → 2026-09-11)**, refused by design — see §3.

## 2. Three defects fixed along the way

### 2a. The fetcher dropped February, every year, for every instrument (pre-existing)

`scripts/fetch_upstox_historical.py:get_date_chunks` split minute requests into **29-day**
windows. Upstox V3 caps the 1-minute range at **one calendar month**, not 30 days. From a start
in any 31-day month a 29-day delta stays inside the month; **from a February start it overshoots**
(Feb 7 + 29d = Mar 8, while Feb 7 + 1 month = Mar 7). The API returned 400, the fetcher logged the
chunk and moved on, and the data was silently absent.

Every one of the 19 surviving failures was a February→March window, across 2023, 2025 and 2026,
across unrelated instruments — the seasonality is what gave it away. Bisecting confirmed it:
`2023-02-07 → 2023-03-08` failed while `2023-02-07 → 2023-02-14` and `2023-02-15 → 2023-03-08`
both succeeded.

Fixed to **27 days**, which is inside one calendar month from any start date. **This is not
specific to this task** — it silently truncated February for every 1m historical fetch this repo
has ever run, including the F&O backfill and the VIX ingest.

### 2b. Symbol→ISIN without the rename chain reported 354 phantom absences (mine)

The membership table is era-correct, so it carries `MCDOWELL-N` for the pre-2024 era. But the 1m
store keys a whole series under the ticker's **current** ISIN, so those bars sit under
`UNITDSPR`'s `INE854D01024` — verified present on 2023-06-01 and 2024-01-02. Looking up only
`MCDOWELL-N`'s own `INE854D01016` reported 354 sessions absent that were never missing, and then
tried to fetch a dead ISIN.

Fixed by walking `symbol_changes` to the terminal ticker: every ISIN on the chain counts for the
presence test, and the fetch uses the terminal ticker's current ISIN. This is the repo's own
standing lesson — *an entity is not one symbol for all time* — applied to the checker rather than
to the data.

### 2c. A per-day file that is not a session (pre-existing)

`2026-03-03` is **not in `trading_calendar`** and has zero bhavcopy rows; its neighbours 03-02 and
03-04 are sessions. Its 1m file holds **197 rows, every one stamped 2026-03-02 15:29–15:59** —
misfiled tail rows from the previous close, including bars after the market had shut.

Scanning files rather than the calendar reported its 9 members absent forever with nothing to
fetch. The script now derives sessions from `trading_calendar ∩ files` and names any orphan.
**The file itself is still there and should be disposed of** — it is not this task's to delete.

## 3. What the backfill did NOT do — post-CAS safety

`data/cas/cas_category.duckdb` ends **2026-08-28**, and `mark_file()` returns 0 for an empty
Category I list, so an unmarked session is indistinguishable from a marked one. A backfill into
2026-08-31 → 2026-09-11 would land carry-forward bars flagged `is_synthetic = FALSE` — real-looking
rows with no trades behind them, the exact defect the marker exists to prevent.

Those **10 sessions are refused**, not silently written. They are reachable once C3 is resolved.

On the 9 post-CAS sessions that *were* touched, the copy-first baselines prove no harm: on
2026-08-14 the count of unmarked zero-volume bars at/after 15:15 is **190 before and 190 after**.
The pre-existing 190 (189 Category I names with one bar each) and CHOLAFIN's 14 on 2026-08-28 are
**not from this work** — neither file was touched by it.

The marker reported 0 new flags for a good reason: the historical API returns **only real traded
bars**, so backfilled names have no carry-forward bars at all. They carry the 15:29 auction print
and nothing fabricated between 15:15 and 15:28. Since the standing rule is to filter on
`is_synthetic`, the panel is consistent after that filter — the backfilled rows are simply already
clean.

## 4. The finding that outranks the backfill: the 1m store is CA-ADJUSTED

Comparing each N100 name's last traded 1m close to the official bhavcopy close, **56 names deviate
by more than 2% on at least one session**, and the deviations are exact corporate-action ratios:

| Name | Sessions deviating | Ratio | Cause |
|---|--:|--:|---|
| KOTAKBANK | 753 of 907 | 5.00 | 1:5 split (ISIN serial 01028 → 01036) |
| PIDILITIND | 676 of 907 | — | CA |
| **HDFCBANK** | **657 of 907** | — | CA |
| NESTLEIND | 646 of 907 | — | CA |
| MOTHERSON | 633 of 907 | 1.50 | 1:2 bonus |
| **RELIANCE** | **451 of 907** | 2.00 | 1:1 bonus |
| ADANIPOWER | 368 of 600 | 5.00 | 1:5 split |

**This is pre-existing and has nothing to do with the backfill.** HDFCBANK, PIDILITIND,
NESTLEIND, RELIANCE, BAJFINANCE, WIPRO, DRREDDY and most of the other 56 were **never absent and
never touched** — every one of their bars predates this work. The store was itself built from
Upstox historical fetches, and Upstox serves history adjusted to today's basis.

So the backfilled bars are **the same kind of data as what was already there**: consistency is
preserved, not broken. Within a name the basis is uniform — KOTAKBANK's 2023 is 246 backfilled
sessions all at ratio 5.00, not a mixture.

**But it is undocumented, and it matters.** `CLAUDE.md` records the 1m store's symbol format,
span and synthetic-bar rules and says nothing about price basis; the repo keeps a separate
`equity_bhavcopy_adjusted` view precisely because the daily store is as-traded, which invites the
assumption that the 1m store is too. Any construct that joins 1m prices to bhavcopy prices, or
computes a return across a corporate action using the daily store, is wrong by the CA ratio —
a factor of 5 for KOTAKBANK, 2 for RELIANCE.

**Recommend recording this in `CLAUDE.md` and `DATA_STORE_MAP.md` as a substrate property**, and
treating "which price basis does this store hold" as a question the C-gate certification must
answer explicitly. One residual I did not chase: MOTHERSON shows 23 sessions attributed to
live ingest at the pre-bonus ratio, which does not fit the uniform-adjustment picture and is worth
a look before the store is relied on across its 2024 bonus.

## 5. Disposition

- **The Nifty-100 coverage blocker on C2 (scoped) is cleared**, except HDFC's 130 sessions and the
  10 C3-blocked sessions, both named and bounded.
- **Not yet done:** dispose of the `2026-03-03` orphan file; extend `cas_category` past 2026-08-28
  (C3) and then backfill the last 10 sessions; record the CA-adjusted price basis in the docs;
  resolve the MOTHERSON 23-session anomaly.
- **Re-run `python scripts/cas/backfill_n100_1m.py`** (plan mode, no writes) to re-verify coverage
  at any time; it exits non-zero if anything is absent or unmappable.

---

## 6. The MOTHERSON 23-session anomaly — resolved, and it was mine

**There is no anomaly. The store is uniformly adjusted for MOTHERSON, and my source attribution
was the thing at fault.**

The relevant corporate action is a **Bonus 1:2, ex-date 2025-07-18** (`corporate_actions`, NSE
CF-CA feed). A 1:2 bonus multiplies shares by 1.5, so an adjusted price is the as-traded price
× 2/3 and `bhav_close / 1m_close` should read **1.5 before the ex-date and 1.0 from it onward**.

Tested across all 907 sessions:

| | Sessions | Ratio |
|---|--:|--:|
| Pre-ex (2023-01-02 → 2025-07-17) | **631** | 1.5 |
| Post-ex (2025-07-18 → 2026-08-28) | **276** | 1.0 |
| **Off-step (mixed basis)** | **1** | see below |

**A clean step function at the ex-date, with zero pre-ex sessions at the unadjusted basis and zero
post-ex sessions at the adjusted one.** There is no mixing.

**What I had mislabelled.** My `live` flag meant "this bar predates my backfill", *not* "written by
the live intraday ingest". The 23 sessions sit in 2024-02-29 → 2024-12-31 — all pre-ex — and were
written by an earlier Upstox *historical* fetch, which serves the same adjusted basis as the bars
the backfill added. `live @ratio 1.5` was therefore exactly what a correctly adjusted store should
show, and reading it as a contradiction was an error in the label, not a defect in the data.

### The one off-step session is not a defect either

`2026-05-29` reads ratio 0.965 against an expected 1.0. The day's OHLC matches the bhavcopy
**exactly** — open 144.46, high 151.77, low 140.08 — and the file holds a complete 375 traded
bars. Only the close differs: last trade **151.01** at 15:29 against an official close of
**145.74**, on a session with 84.7M shares (roughly double its neighbours) and a sharp run from
~148 to ~151 in the final five minutes.

That is the expected divergence between *last traded price* and NSE's official close, which is
the **volume-weighted average of the last 30 minutes** — exaggerated by a violent late move.

**Corollary, and a correction to §4.** The ratio test in §4 uses last-traded-close as a proxy for
the official close, so it conflates two effects. The large, many-session entries (KOTAKBANK 753,
RELIANCE 451, MOTHERSON 633 …) are genuine corporate-action ratios. **The long tail of that table
— ASIANPAINT, SBILIFE, ULTRACEMCO, SHREECEM, INDIGO and the others showing exactly 1 session — is
this benign VWAP-versus-last-trade effect, not a corporate action.** §4's headline finding (the
1m store is CA-adjusted, pre-existing and undocumented) is unaffected; only the tail of its table
needed this reading.

---

## 7. Orphan disposed, and a native-era label census

### 7a. `2026-03-03` quarantined

Moved to `data/_baselines/1m_orphans/2026-03-03.duckdb` (sha256 verified identical before
removal), not deleted. A README there records the contents. It held **197 rows, all stamped
2026-03-02**:

- **13 rows at 15:29** — already present in the real `2026-03-02.duckdb` with identical
  (symbol, timestamp, close). Pure duplicates.
- **184 rows at 15:40–15:59** — after the equity session ends (the real file's last bar is 15:29,
  and 2026-03-02 predates CAS). Post-close prints that belong in no 1m file on any date.

**Disposal loses no row that belongs in the store.** A full sweep confirms it was the **sole
orphan in 3,613 files**, and the arithmetic now closes exactly: 4,146 calendar sessions − 534 with
no file = **3,612 files**, which is what `DATA_STORE_MAP.md` already claimed.

### 7b. C1's missing artifact, for the native era

Gate C1's third deliverable is "a contiguity + label census over all files recording the observed
stamp per file". Produced here for 2023-01-02 → present (`NSE_EQ` rows), 917 sessions:

| First bar | Last bar | Distinct minutes | Sessions | Reading |
|---|---|--:|--:|---|
| 09:15 | 15:29 | 375 | **904** | textbook native era, start-labelled |
| 09:15 | 15:29 | 370–374 | 3 | minor contiguity gaps |
| 09:15 | 12:29 | 105 | 2 | truncated/special session |
| 09:15 | 15:44 / 15:53 / 15:59 | 377–393 | 4 | **post-close prints — same defect class as §7a** |
| 18:15 / 18:00 / 13:45 | +59 min | 60 | 3 | Muhurat / special sessions, legitimate |

**The native era is uniformly start-labelled 09:15 on 904 of 917 sessions, and all 13 exceptions
fall into three named classes.** That is a certifiable state for a 2023+ fence — the era rule does
not need rediscovering, only a loader that handles the three classes and refuses an unrecognised
stamp rather than guessing.

Note the 3 Muhurat sessions: any loader that assumes a 09:15 start silently drops them, and any
gate that asserts 375 bars fails them. They are real trading sessions.

## 8. Are we near substrate certification?

**For a Nifty-100 intraday study fenced 2023-01-02 → 2026-08-28: yes, materially.** That fence is
not arbitrary — three independent constraints land on it.

| Gate | State for that fence | Residual |
|---|---|---|
| **C1** timestamp semantics | **Out of the cross-era seam entirely** — a 2023+ study never spans the vendor/native boundary, and §7b certifies the native era's labelling | Loader must handle the 13 enumerated exceptions; C1-a (vendor spec) matters only if pre-2023 is ever in scope |
| **C2** PIT & entity integrity | A1 discharged by substitution, A2-1 closed, A2-2 resolved, A3 certified, A4 PASS, **A5 vacuous** (no A5 residue was ever an N100/N200 member), coverage gap closed 11.0 → 0.143 | **None inside the fence** — A6 scoped out (§10), HDFC accepted at 99/100 for 130 sessions (§11) |
| **C3** tradeability & synthetics | **Satisfiable exactly to 2026-08-28** — `cas_category` covers every post-CAS session inside the fence, and those files are marked | Nothing inside the fence; everything after 2026-08-28 is blocked until the category table is extended |
| **C4** VIX certification | PASS with quarantines (operator ruling) | 2021-02-12 permanently quarantined |

**The honest summary: the substrate is close to certifiable for this scope, and the remaining work
is small, named and bounded** — not the open-ended state it was in a day ago. What stands between
here and a scoped certification:

1. ~~**A6** — does the construct need sector membership?~~ — **CLOSED 2026-09-13.** Operator
   ruling: it does not. Scoped out of the fence explicitly; clause and cost in §10.
2. ~~**HDFC, 130 sessions** (2023-01-02 → 2023-07-12)~~ — **CLOSED 2026-09-13.** Operator ruling:
   accept 99/100 for that window. Disposition and the obligations it carries: §11.
3. ~~**The 4 post-close-print sessions** in §7b~~ — **CLOSED 2026-09-13**, §9: 466 rows pruned,
   the class is gone from the census.
4. ~~**The 3 Muhurat sessions** — confirm the loader handles them.~~ **ANSWERED 2026-09-13,
   §12: no single loader does, and `session_schedule.py` — the stated authority — mis-answers
   all three.** The requirement this places on the study loader is stated there; whether it
   blocks the scoped certification is an operator call.
5. **Extend `cas_category`** if the fence must run past 2026-08-28, then backfill the last 10
   sessions.

**Four of the five are now closed or answered; `cas_category` remains** — plus whatever the
operator decides to do with §12's finding.

**Certification remains the operator's call.** None of the above is a claim that C1–C4 are passed;
it is a statement of what is left, and the list is now short enough to work through.

---

## 9. Post-close prints pruned — and two classes of data that nearly went with them

**466 rows removed across 4 sessions; the native-era census is now clean of post-close prints.**
Script: `scripts/cas/prune_post_close_bars.py` (plan by default, `--apply` to write), baselines in
`data/_baselines/1m_pre_post_close_prune/`.

| Session | Rows pruned | Symbols | Last stamp before | After |
|---|--:|--:|---|---|
| 2026-02-18 | 2 | 2 | 15:59 | 15:29 |
| 2026-02-23 | 130 | 40 | 15:44 | 15:29 |
| 2026-02-26 | 151 | 43 | 15:53 | 15:29 |
| 2026-03-04 | 183 | 183 | 15:59 | 15:29 |

All four are genuine sessions with a complete 09:15→15:29 book (206–207 symbols) plus a tail of
one-row-per-symbol prints swelling toward 15:59 — the same shape as the 197 rows in the 2026-03-03
orphan file, so one mechanism. Every cash window in `session_schedule.py` closes by 15:30 (15:35
post-CAS), so no equity bar can legitimately carry a later stamp. **Symbol counts are unchanged
(207→207, 206→206)** — no name was removed, so the coverage result in §1 is untouched.

### Two classes the first pass would have destroyed

The rule was initially written against the cash schedule for *all* symbols. Plan mode listed **19**
sessions, not 4, and inspecting them before deleting is what caught it:

- **`MCX_FO|451669`** — an MCX commodity future. MCX opens **09:00** and runs to **23:55**, so its
  505 bars to 23:54 on 2026-02-16 are entirely real. The NSE *cash* schedule does not bound it.
- **`NSE_INDEX|Nifty 50` at 15:30 on 2023-01-31** — the vendor-era end-labelled bar. `CLAUDE.md`
  and the C1 plan both record 2023-01-31 as the one native-era date still on the 09:16→15:30
  vendor convention. **That single bar is gate C1's own evidence**; pruning it would have erased
  the artifact the gate exists to explain.

The rule is now scoped to `NSE_EQ|`, which excludes both without special-casing either. A file
whose bars are *entirely* outside the window is reported as a **special session and never touched**
— this is what protects the Muhurat sessions (2023-11-12, 2024-11-01), each holding 12,180 real
bars.

### Native-era census after the prune

| First | Last | Minutes | Sessions | Reading |
|---|---|--:|--:|---|
| 09:15 | 15:29 | 375 | **908** | canonical |
| 09:15 | 15:29 | 370–374 | 4 | contiguity gaps |
| 09:15 | 12:29 | 105 | 2 | truncated sessions |
| 18:15 / 18:00 / 13:45 | +59 min | 60 | 3 | Muhurat / special, legitimate |

**Exceptions fall from 13 to 9, and the post-close class is gone entirely.** What remains for the
loader: 4 contiguity gaps, 2 truncated sessions, and 3 special sessions that any 09:15-start
assumption silently drops.


---

## 10. A6 scoped out — operator ruling 2026-09-13

**Ruling: "sector membership is not needed for this construct."** A6 therefore does not block this
fence. It is **waived in scope, not repaired** — no PIT sector table was built, and none exists.

### The clause, written so it can be checked

A6 covers two distinct artefacts, and "not needed" has to close both or it closes neither:

| Artefact | What it is | Status under this fence |
|---|---|---|
| Sector / thematic **index constituents** (who was in NIFTY IT on date X) | A PIT membership question, the same class as N100 membership. **No table exists** | Out of scope |
| Sector **classification** — `governance/carry/sector_classification.csv` | A flat, undated label per name, current state only; used by Carry's neutralizer | Out of scope |

The second is the one that can walk back in unnoticed: that CSV is present, readable and
uncontrolled, so a construct could neutralize on sector under this fence and believe itself
compliant. Hence the clause names the file rather than the concept.

> **Fence clause.** No construct certified under the Nifty-100 / 2023-01-02 → 2026-08-28 fence may
> read `governance/carry/sector_classification.csv`, any sector or thematic index constituent
> list, or any other sector label — not as a feature, not as a neutralization axis, and not as a
> post-hoc diagnostic. A design that needs one **reopens A6 as a hard blocker** and must build a
> PIT sector table before certification.

The post-hoc route is closed deliberately. A "descriptive only" sector breakdown carries exactly
the same static-membership bias, and once such numbers are printed they shape what gets claimed.

### What the ruling costs

Stated plainly, because a waiver with no stated cost reads as a free pass:

1. **Sector-neutral and sector-conditioned designs are excluded from this fence.** Family F's
   normalization row in `PTMS_P3_FAMILY_CATALOGUE_2026-09-12.md` offers "beta and sector
   neutralization if the claim is idiosyncratic"; the sector half of that option is foreclosed
   here. That catalogue is a dated design record under a 2026-09-12 operator ruling and is left
   unedited — this note is the amendment.
2. **A finding can be neither attributed to nor ruled out as a sector effect.** If the construct's
   spread is in truth a bank trade or an IT trade, this substrate cannot say so. That is a real
   limit on what any result may claim, and it belongs in the construct's own disclosure, not only
   here.

### Present-state check

`scripts/isd/`, `scripts/cas/` and `A_CONSTRUCT_DEFINITION.md` return **zero** matches for
`sector`, so the ruling is consistent with the code that exists today. **That establishes present
state, not future compliance** — nothing in the repo enforces the clause, and a prose scope-out is
documentation, not a control. Naming the CSV at least makes it greppable.

**Globally, A6 is unchanged: sector/thematic membership is NOT point-in-time and remains UNUSABLE
for cross-sectional work** (`PTMS_C2_PIT_ENTITY_CERTIFICATION_2026-09-12.md`). What changed is
scope, not status.


---

## 11. HDFC accepted at 99/100 — operator ruling 2026-09-13

**Ruling: accept 99/100 for HDFC's 130 sessions.** Measured directly today, not inherited from
§1:

| Fact | Value |
|---|---|
| HDFC's Nifty-100 interval | 2011-03-25 → 2023-07-13 (half-open — last member session 2023-07-12) |
| Member sessions inside the fence | **130**, 2023-01-02 → 2023-07-12 — 14.3% of the fence's 907 |
| Session files present for those dates | 130 of 130 |
| Sessions carrying an HDFC 1m bar | **0** |
| `equity_bhavcopy` rows for the window | **130 of 130** — the daily record is complete |
| Every other N100 absence in the fence | **0 cells across 907 sessions** (plan re-run today) |

HDFC delisted into HDFCBANK at the 2023-07-13 merger. It has no `instrument_master` row, only a
legacy `symbol_isin` row (`INE001A01036`), and Upstox rejects the dead ISIN on every chunk — so
`backfill_n100_1m.py` now reports it through the *no ISIN anywhere (cannot fetch)* channel rather
than as an absent cell. **Read the plan output carefully: "0 absent cells" is not "no gap"** — the
gap is real and is carried on the line below it.

**What is being accepted, precisely:** the **1m** panel is 99 names for 130 sessions. HDFC is not
missing from the study — its daily record is intact, so any EOD-level control or sanity check can
include it. Only the intraday leg is short, and only for that window.

### Three obligations this acceptance creates

1. **The absence is systematic, not random.** It is one specific name — at the time one of the
   largest-weight constituents — absent across a *contiguous* block at the **start** of the fence,
   terminating at a merger. If a result's strength concentrates in H1-2023, that must be examined
   against the 99-name composition before it is claimed. This belongs in the construct's own
   disclosure, not only here.
2. **Fixed-count buckets shift; fractional quantiles do not.** A top-quintile rule ranks 99 instead
   of 100 and is unaffected in kind. A fixed top-*k* rule draws its *k* from a 99-name pool on
   those sessions. The construct must state which it uses.
3. **Pin the exception — do not loosen the gate.** The eligibility check must never be relaxed to
   "≥ 99 names": that tolerance would silently absorb the *next* absence, which is exactly how the
   coverage hole went unmeasured for as long as it did. The assertion is **100 names, or exactly
   99 where the missing name is HDFC and the date is before 2023-07-13 — anything else hard-fails.**
   The repo's pattern for this is a committed disposition register
   (`scripts/psb1/disposition_register.py` is the shape; PSB-1's own register is closed and is not
   to be edited). No such gate exists yet because the study's eligibility code does not exist yet
   — this is the requirement on it when it is written, not a claim that it is in place.


---

## 12. The 3 Muhurat sessions — checked against every reader in the fence's path

**Asked: does the loader handle them? Answer: there is no single loader, and the component that
claims to be the authority on session hours gets all three wrong.** One construct loader handles
them properly; the canonical reader passes them through; the ISD completeness gate produces an
internally incoherent row.

**Access note:** every figure below is structural — bar counts, slot counts, defect labels, boolean
window answers. No price was printed, and nothing computed here entered a feature, signal, label or
parameter.

### The three sessions, measured

| Date | Weekday | Window | Bars | `NSE_EQ` symbols |
|---|---|---|--:|--:|
| 2023-11-12 | Sunday | **18:15 → 19:14** | 12,180 | 203 |
| 2024-11-01 | Friday | **18:00 → 18:59** | 12,180 | 203 |
| 2025-10-21 | Tuesday | **13:45 → 14:44** | 12,420 | 207 |

All three are in `trading_calendar`; each carries 60 distinct minutes per symbol and zero synthetic
bars. They are real trading sessions with complete capture — nothing is missing from them.

### What each reader does with them

| Component | Behaviour | Reading |
|---|---|---|
| `core/market/session_schedule.py` | Returns the ordinary 09:15–15:30 window on all three dates | **WRONG on all three** — Finding 1 |
| `scripts/isd/read_1m.py` | Returns all 12,180 / 12,180 / 12,420 rows with correct stamps | **Handles** — time-agnostic by construction |
| `scripts/isd/gate_contiguity.py` (L2) | Ledger row, no block | **Incoherent** — Finding 2 |
| `scripts/analog_path/data_layer.py` + `eligibility.py` | `valid=False`; defects `first_bar_stamp_18:15` / `short_session_60` / `morning_incomplete_0` plus 5 horizon codes; excluded from the eligible list and written to the defect register with date and codes | **Handles correctly** — refuses, names, publishes |
| `core/analytics/day_features.py` | `EXPECTED_BARS = 375`, `PM_START_BAR = 255` positional | **Would break silently** — `iloc[255:]` on a 60-row frame is empty; no execution needed to see it |
| `scripts/cas/*` (coverage, backfill, prune) | Coverage and backfill are time-agnostic; the pruner classifies an all-out-of-window file as a SPECIAL SESSION and never touches it (§9) | Handles |

### Finding 1 — the stated authority mis-answers, and the afternoon case is the dangerous one

`session_schedule.py`'s docstring calls it *the single authority for when segment X is open on date
D*. It is keyed by **era** only and has no concept of a special session. Measured:

| Date | `session_window("cash_cat1")` | `any_open()` during real trading | `any_open()` outside it |
|---|---|---|---|
| 2023-11-12 | 09:15–15:30 | **False** at 18:30 | — |
| 2024-11-01 | 09:15–15:30 | **False** at 18:30 | — |
| 2025-10-21 | 09:15–15:30 | True at 14:00 — **for the wrong reason** | **True at 09:30 and 15:00, when the market was shut** |

The two evening sessions **fail closed**: 12,180 real bars each read as out-of-hours. The 2025
afternoon session **fails open**, which is worse — the authority reports the market open across
6h15m of which 60 minutes were real, and it is accidentally right at 14:00 only because 13:45–14:44
falls inside the ordinary window.

Live tick capture is not affected, for a reason worth recording: `live_buffer_writer` guards by
session **date**, explicitly *not* by `session_window`, because index dissemination legitimately
runs outside the widest defined segment. That deliberate choice is why these bars are in the store
at all. Anything that instead calls `MarketHours.is_any_open()` — a thin wrapper over `any_open` —
inherits the table above.

### Finding 2 — the detection signal disappeared when Muhurat moved to the afternoon

ISD's L2 audit grids each file against minutes 555–929 (09:15–15:29):

| Date | `expected_slots` | `missing_slots` | `bars_outside_grid` |
|---|--:|--:|--:|
| 2023-11-12 | 76,125 | 63,945 | **12,180** |
| 2024-11-01 | 76,125 | 63,945 | **12,180** |
| 2025-10-21 | 77,625 | 65,205 | **0** |

Two things fall out.

**The arithmetic is incoherent on these files.** `missing_slots = expected - distinct_slots`, but
`distinct_slots` counts distinct `(symbol, minute)` pairs across **all** bars while `expected` is
defined over the 375-minute grid. So an 18:30 bar is credited against a missing 09:15 slot: the
2023 row reports 63,945 missing rather than the 76,125 actually absent from the grid. The two
quantities are on different domains. That is harmless while `bars_outside_grid = 0` — true of every
ordinary session — and wrong exactly here.

**The marker that made 2023 and 2024 visible is gone in 2025.** 13:45–14:44 sits *inside* the grid,
so `bars_outside_grid` is 0 and the row reads as an ordinary session 84% incomplete —
indistinguishable from a feed that died at the open. Whatever detected the evening sessions does not
detect the afternoon one, and 2025 is the most recent precedent.

### The requirement this places on the study loader

None of this blocks a construct that never reads these sessions — a 60-bar session fails any
sensible eligibility rule, and `analog_path` already excludes them by name. The exposure is a loader
that iterates `trading_calendar` and trusts either `any_open` or a 375-bar assumption. So, when the
Nifty-100 study's eligibility code is written:

1. **Resolve the session window from the observed bars or an explicit special-session table — never
   from `session_schedule` alone**, which is era-keyed and does not know these dates exist.
2. **Refuse and name; do not assert 375 and do not guess.** `analog_path`'s `first_bar_stamp_HH:MM`
   and `short_session_N` codes, written to a register with the date, are the pattern to copy: an
   excluded session that is *published* is handled; one silently dropped is not.
3. **Never treat a 60-bar special session as an incomplete 375-bar one.** They are different
   objects, and the 2025 row above is what conflating them looks like.

### The `session_schedule` defect — shape and blast radius, not repaired

The fix is a date-keyed special-session override consulted ahead of the era schedule. **Not applied,
because it is not a documentation change:** `session_schedule` has a test file
(`tests/market/test_session_schedule.py`) and live consumers — `market_hours`, `market_session`,
`db_tick_aggregator`, `live_buffer_writer`, `daily_bhavcopy`, `cas_rules`, `paper_executor`,
`nifty_shield_v1/config`, `ingest_reference_1m`, `certify_index_slice`, `build_ts_basis_daily` — so
correcting it changes live behaviour on Muhurat dates. It is platform infrastructure rather than
PTMS construct code, so nothing forbids the change; it is simply not a repair to make inside a
substrate-certification pass without being asked.
