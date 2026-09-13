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
