# Nifty 100 — 1m coverage gap: backfill, result, and what it turned up

**Date:** 2026-09-13 · **Authority:** operator task "fix the 1m coverage gap for nifty 100".
**Baselines:** `data/_baselines/1m_pre_n100_backfill/` (copy-first, per touched file, never overwritten).
**Script:** `scripts/cas/backfill_n100_1m.py` (plan by default, `--apply` to write).

> **Result: the gap is closed. Nifty-100 constituents absent from the 1m store fall from a mean
> of 11.0 per session to 0.143, and sessions at full 100/100 coverage rise from 41 to 777 of 907.
> The sole residual is HDFC on 130 sessions — delisted at the 2023-07-13 merger and unfetchable.**
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
| **C2** PIT & entity integrity | A1 discharged by substitution, A2-1 closed, A2-2 resolved, A3 certified, A4 PASS, **A5 vacuous** (no A5 residue was ever an N100/N200 member), coverage gap closed 11.0 → 0.143 | **A6** if the construct needs sector membership; HDFC's 130 sessions |
| **C3** tradeability & synthetics | **Satisfiable exactly to 2026-08-28** — `cas_category` covers every post-CAS session inside the fence, and those files are marked | Nothing inside the fence; everything after 2026-08-28 is blocked until the category table is extended |
| **C4** VIX certification | PASS with quarantines (operator ruling) | 2021-02-12 permanently quarantined |

**The honest summary: the substrate is close to certifiable for this scope, and the remaining work
is small, named and bounded** — not the open-ended state it was in a day ago. What stands between
here and a scoped certification:

1. **A6** — decide whether the construct needs sector membership. If it does, this is a hard
   blocker (no PIT sector table exists). If not, scope it out explicitly in the fence.
2. **HDFC, 130 sessions** (2023-01-02 → 2023-07-12) — accept 99/100 for that window, or source it
   elsewhere. Needs a stated disposition, not silence.
3. **The 4 post-close-print sessions** in §7b — same defect as the orphan, not yet dealt with.
4. **The 3 Muhurat sessions** — confirm the loader handles them rather than dropping them.
5. **Extend `cas_category`** if the fence must run past 2026-08-28, then backfill the last 10
   sessions.

**Certification remains the operator's call.** None of the above is a claim that C1–C4 are passed;
it is a statement of what is left, and the list is now short enough to work through.
