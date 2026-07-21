# Carry — Index & Spot Re-Ingest: Acquisition Spec + Implementation Prompt

**Written:** 2026-07-21 · supersedes the G1-2 conclusion in
`CARRY_G1_G2_VERIFICATION_REVIEW_2.md` §2 and the remediation report's "55 genuine NSE archive
gaps, no alternate source found."
**Purpose:** fix the beta-warmup blocker with **data** rather than by moving TRAIN, and replace
the three throwaway G1 patch scripts with one clean ingest.

---

## 0. The finding that changes the plan

**"No alternate source found" was wrong. The data was there the whole time.**

Every one of the 53 missing 2015 sessions was probed against the *exact URL the existing
ingest already uses* (`nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv`):

| Result | Count |
|---|---:|
| **HTTP 200 with a valid index CSV — available right now** | **46** |
| Genuine 404 on this pattern | 7 |

The 7 real misses: `2015-03-12`, `2015-03-13`, `2015-05-19`, `2015-07-08`, `2015-09-04`,
`2015-10-16`, `2015-12-01`.

### Why 46 available dates were recorded as archive gaps

`scripts/g1_retry_2015.py:91-101`:

```python
try:
    resp = sess.get(url, timeout=30)
    if resp.status_code == 200 and len(resp.content) > 100:
        from g1_ingest_index_history import parse_index_csv, store_candles   # inside the loop
        df = parse_index_csv(resp.text, d)
        n = store_candles(df, d)
        ...
except:            # bare except
    pass           # every failure mode collapses to "still missing"
```

A bare `except: pass` wrapping a download **and** an in-loop import **and** a parse **and** a
DuckDB write.

**What can and cannot be concluded.** The import was tested and *succeeds* in this environment,
so that mechanism is ruled out. Two remain and they are not distinguishable after the fact:

- the fetch returned 200 and a **downstream parse or write threw**, swallowed by the bare
  except; or
- NSE **throttled** the run (the script uses a plain session with no retry adapter and a 0.5 s
  delay), the status was not 200, and the date fell through as missing.

Either way the script **could not tell absence from failure**, and reported both as absence.
That is the defect: not one specific exception, but a control flow in which "NSE does not have
this" and "something went wrong on our side" are the same output. The conclusion was then
written into a governance report as a fact about NSE.

This is the failure mode `.claude/rules/common/coding-style.md` names explicitly ("never
silently swallow an error") and it is the single most important thing the re-ingest must not
reproduce. **In deterministic research code, a crash with a traceback beats a wrong number in
a report.**

### Two more gaps that are also not gaps

- **Archive depth.** `ind_close_all` does **not** stop at 2015-03-02. Probed: `2012-01-02` 404,
  `2012-04-02` OK, and every quarter from there to present OK. The archive serves from
  **somewhere in Q1–Q2 2012**. Backfilling to the archive floor puts **~750 index sessions**
  before TRAIN's first formation — the 252-day beta becomes computable with three years to
  spare, **and TRAIN does not move.**
- **G3 / the spot tail is not an NSE gap either.** All 7 equity sessions missing from
  `equity_bhavcopy` (`2026-07-10` → `2026-07-20`) return **HTTP 200** from the UDiFF bhavcopy
  endpoint the ingest already implements (`ingest_equity_bhavcopy.py:181`). Round 2 §3 flagged
  this as suspicious; it is confirmed — a re-run closes it, no acquisition needed.

---

## 1. What you need to download manually

**Short answer: probably nothing. Read this section before spending any effort.**

The blocker you want gone — beta uncomputable at TRAIN's first formations — is closed by the
**automated** path alone:

- The NSE archive serves from ~Q1 2012. Backfilling it makes a 252-session beta computable
  from **~April 2013** — nearly three years before TRAIN's first formation (2016-03-31).
- Plus the 46 recovered sessions, 2015 is complete but for 7 scattered days.

So the manual download is **not on the critical path.** It buys exactly two things: literal
2010 parity with the equity panel, and the last 7 holes. Both are optional — see §1.2 for why
the cheaper resolution is a one-sentence pre-reg correction, not a data acquisition.

### 1.1 Optional — NIFTY 50 daily OHLC, 2010-01-01 → 2015-12-31

- **Source:** <https://www.niftyindices.com/reports/historical-data> → *Equity* → Index
  **NIFTY 50** → set the date range → Download CSV.
  This is NSE's own index authority and serves back to inception, so it covers both the
  pre-2012 span and the 7 stubborn 2015 dates in one pull.
- **Range caps:** the site limits how much it will return per request. Pull **one calendar year
  at a time** (2010, 2011, …, 2015) rather than fighting the cap — six downloads, same result.
- **Columns needed:** `Index Name`, `Date`, `Open`, `High`, `Low`, `Close`. Extra columns
  (Shares Traded, Turnover) are harmless — leave them in, the ingest ignores them.
- **Do not** hand-edit, re-sort, re-date, or convert the files. Save exactly as downloaded.
- **Drop them here:** `data/market_data/vendor/niftyindices/nifty50_<YYYY>.csv`

**A caveat before you go:** the site's data endpoint was probed programmatically and returned
HTML rather than data, so the export was **not** verified end-to-end here — only the manual UI
route is assumed to work. If it wants a login, throttles, or exports a different shape than
above, **stop and say so rather than working around it.** Nothing downstream depends on it.

### 1.2 The cheaper resolution — and why it is not "moving the train"

`CARRY_PHASE0_PRE_REGISTRATION.md` §9 says beta "warms up off 2010+ adjusted spot." The stock
leg does reach 2010-01-04 (`equity_bhavcopy_adjusted` MIN, verified); the market leg is what
does not. But read what the sentence is *for*: it is a claim that **warmup does not consume
TRAIN formations** — and that is equally true with the market leg starting ~2012, since the
first formation is 2016-03-31.

So there are two ways to make §9 honest:

| | Cost | Effect on the test |
|---|---|---|
| **(i) Correct the sentence** — "market leg from ~2012, well before first formation" | zero | **none** — no formation lost, no window moved, no data read |
| (ii) Download 2010–2012 | six manual pulls, unverified route | none |

**(i) is not the thing you rejected.** Moving TRAIN meant *losing formations and altering the
test*. Fixing a factual description of the substrate costs nothing and changes no number. The
pre-reg is still a DRAFT (§13 freeze not executed), so this is an ordinary pre-freeze edit, not
a post-hoc revision.

Recommendation: **take (i), skip the download.** Take (ii) only if you want 2010 parity for
reasons beyond this sleeve.

### 1.3 If you do supply the file — the overlap is free validation

Where your file and the NSE archive both have a date, they must agree. That turns the manual
file from "trust the operator's download" into a cross-checked source, and it is the only way
to earn confidence in the 2010–2012 span where no second source exists. Gate B in §3.

### 1.4 The 7 stubborn dates — document, don't chase

`2015-03-12`, `03-13`, `05-19`, `07-08`, `09-04`, `10-16`, `12-01` were re-probed against two
alternate NSE hosts as well as the primary — **none serves them.** They are scattered
singletons, not a block, and they are **7 sessions out of the ~250 in any beta window.** Their
effect on a 252-day beta is immaterial. Record them as known absences in the pre-reg; do not
make an acquisition depend on them.

### Optional — only if you want the intermarket store complete on the same span

`NIFTY BANK` (same site, same procedure) and India VIX (NSE publishes separately, history is
shorter). **The carry sleeve needs neither** — §4 beta is to Nifty 50 alone. Skip unless you
want it for other work; it is not on the critical path and should not delay the re-ingest.

### What NOT to buy

Nothing. No vendor spend is warranted here — this is free NSE data. If a vendor quote comes up
for Nifty index history, the answer is no.

---

## 2. What is automated — no manual work

| Item | Method | Expected |
|---|---|---|
| 46 recoverable 2015 sessions | re-fetch, same URL | all 46 land |
| Backfill to archive floor (~Q1–Q2 2012) | walk the calendar backwards until sustained 404 | ~700+ new sessions |
| **Beta computable well before TRAIN** | consequence of the backfill | **~2013, vs 2016-05-26 now** |
| CNX dual-identity symbols | canonicalize at write time, hard-fail unmapped | 0 residual `CNX` |
| Schema split (`VARCHAR`/`TIMESTAMP`) | declare schema once, up front | uniform `TIMESTAMP` |
| G3 spot tail (7 equity days) | re-run existing equity ingest | panel reaches 2026-07-20 |
| *7 stubborn 2015 dates* | *only from an operator file — else documented* | *optional* |
| *2010-01-04 → archive floor* | *only from an operator file* | *optional* |

---

## 3. Implementation prompt — G1-R (issue as-is)

> **Task: G1-R — clean re-ingest of the NSE daily index store.**
>
> **Deliverable:** one script, `scripts/ingest_index_history.py`. On completion **delete**
> `scripts/g1_ingest_index_history.py`, `scripts/g1_fix_timestamp.py`, and
> `scripts/g1_retry_2015.py` — they are superseded, and the repo does not keep shims.
>
> **Target:** `data/market_data/nse/candles/1d/{YYYY-MM-DD}.duckdb`, table `candles`,
> one row per (symbol, date), covering **2010-01-04 → present** for `NSE_INDEX|Nifty 50`.
>
> ### Non-negotiables — these are the defects being repaired, not style preferences
>
> 1. **No bare `except`. No `except Exception: pass`. Anywhere.** The previous script recorded
>    46 downloadable dates as permanent archive gaps because a bare except swallowed a
>    post-download failure. Catch **only** the specific exception you intend to handle
>    (`requests.RequestException` around the fetch, nothing wider), and let everything else
>    crash with a traceback. A date may be classified `MISSING` **only** on an HTTP status that
>    is not 200 — never on a parse or write failure.
> 2. **Declare the schema once, explicitly.** `CREATE TABLE IF NOT EXISTS candles (symbol
>    VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume
>    BIGINT)` — `timestamp` is `TIMESTAMP`, and a real timestamp is inserted, never
>    `date.isoformat()`. If an existing file's `candles.timestamp` is not `TIMESTAMP`, **raise**
>    — do not silently write into a divergent schema. That collision is exactly what split the
>    store at the 2023 sealed-window boundary.
> 3. **Canonicalize symbols at write time, and hard-fail on unmapped names.** Keep the
>    `CNX_TO_CURRENT` map. Any index name not in the map and not already `NSE_INDEX|`-canonical
>    must be **skipped and counted**, never written through as
>    `f"NSE_INDEX|{raw_name}"`. The fall-through is what created six pre-2016 CNX indices living
>    as separate identities from their post-2016 selves. Print the skipped-name tally.
> 4. **Idempotent.** Re-running must not duplicate rows. Delete-then-insert per (file, symbol),
>    and assert exactly one `NSE_INDEX|Nifty 50` row per file afterward.
>
> ### Sources, in precedence order
>
> **(a) NSE archive** — `https://nsearchives.nseindia.com/content/indices/ind_close_all_{DDMMYYYY}.csv`.
> Authoritative where served. Discover the archive floor empirically: walk backwards from
> 2015-01-01 and stop after 15 consecutive trading-day 404s; print the discovered floor. Do not
> hardcode it — probing showed 2012-01-02 is 404 and 2012-04-02 is 200, so the true floor is
> inside Q1 2012 and must be measured, not assumed. Rate-limit ~0.3–0.5 s between requests.
>
> **(b) Operator-supplied niftyindices files** — `data/market_data/vendor/niftyindices/nifty50_<YYYY>.csv`,
> columns `Index Name, Date, Open, High, Low, Close` (dates in the site's `DD-MMM-YYYY` form;
> parse explicitly, never with a bare `pd.to_datetime` guess). Used **only** where (a) does not
> serve. Record `source` per row so provenance is queryable.
>
> ### Gate set A — archive-only. **Must pass with no operator file present.**
>
> Source (b) is optional and may never arrive. Run and pass these on source (a) alone; they
> are what closes the blocker.
>
> - **Calendar completeness, archive era.** For the discovered floor → 2026-07-21, compare
>   against `trading_calendar` in `equity_bhavcopy.duckdb`. Print every missing date.
>   **Allowed misses: exactly the 7 known absences** (`2015-03-12`, `03-13`, `05-19`, `07-08`,
>   `09-04`, `10-16`, `12-01`). Any other miss is a FAIL.
> - **Beta computability — the blocker gate.** Print the earliest date at which 252 prior index
>   sessions exist. **Must be ≤ 2013-06-30**, i.e. comfortably before TRAIN's first formation
>   2016-03-31. (It is currently 2016-05-26 — that is the number being removed.)
> - **Schema uniformity.** Every file's `candles.timestamp` is `TIMESTAMP`. Print the histogram.
> - **Symbol hygiene.** `SELECT COUNT(*) ... WHERE symbol LIKE '%CNX%'` → **0**.
> - **No duplicates.** No file has more than one `NSE_INDEX|Nifty 50` row.
> - **Continuity.** Print every day-over-day Nifty 50 move exceeding 8%, with dates. Expect only
>   real events (2020-03-12 −8.3%, 2020-03-23 −13.0%, 2020-04-07 +8.8%, plus 2012–2014 dates to
>   be eyeballed). Any 8%+ move at a source seam is a splice artifact and a FAIL.
>
> ### Gate set B — only if the operator file is present. Skip cleanly if absent.
>
> If `data/market_data/vendor/niftyindices/` is empty or missing, **print "source (b) not
> supplied — skipping gate set B" and exit 0.** Absence is not an error.
>
> - **Cross-source agreement.** On every date served by *both* (a) and (b), compare Nifty 50
>   close. **Require max absolute difference < 0.05 index points.** If they disagree beyond
>   that, the file is not trustworthy for 2010–2012 where it is the only source — **stop and
>   report, do not ingest it.**
> - **Extended floor.** 252-session beta computable from ≤ 2011-01-31, and the 7 known absences
>   are filled.
>
> ### Falsifiable predictions — state PASS/FAIL on each *before* reporting anything else
>
> **Archive-only (must hold regardless):**
> 1. 46 of the 53 currently-missing 2015 sessions are recovered from source (a) alone.
> 2. The discovered archive floor falls between 2012-01-02 and 2012-04-02.
> 3. Exactly 7 calendar misses remain, and they are the 7 named above — no others.
> 4. Final store: zero `CNX` symbols, uniform `TIMESTAMP`, 252-session beta computable no later
>    than 2013-06-30.
>
> **Only if source (b) supplied:**
> 5. Cross-source close agreement on the overlap is < 0.05 index points at the maximum.
> 6. The 7 known absences are filled, and beta is computable from January 2011.
>
> ### Second task — G3, same session
>
> Re-run `scripts/csmp/ingest_equity_bhavcopy.py` for `2026-07-10` → `2026-07-20`. All 7
> sessions were verified to return HTTP 200 from the UDiFF endpoint. Afterwards
> `MAX(trade_date)` in both `equity_bhavcopy` and `equity_bhavcopy_adjusted` must be
> **2026-07-20**, closing OPEN-3 without a window pin.
>
> `equity_bhavcopy_adjusted` was checked and is a **VIEW**, not a materialized table
> (`information_schema.tables.table_type = 'VIEW'`), so the new rows propagate automatically —
> no rebuild needed. But **verify it rather than assume it**: if `MAX(trade_date)` on the view
> does not move with the base table, stop and report. Also report the adjusted row count before
> and after, and confirm no corporate action falls in the 7-day tail that would need a factor
> pass.

---

## 4. What this does and does not resolve

**Resolves, on the automated path alone:**
- The §2 beta blocker — **without moving TRAIN.** TRAIN stays pinned at 2016-03-31, and a
  252-session beta becomes computable from ~2013, three years before the first formation.
- G1-2 (46 of 53 missing sessions; 7 documented absences), G1-3 (CNX identities), G1-1
  permanently (schema declared once, divergence raises).
- OPEN-3 / G3 spot tail.

**Requires one pre-reg edit either way:** §9's "beta warms up off 2010+ adjusted spot" must
become an accurate description of the market leg (§1.2). Free, loses no formation, and must be
made **before freeze** — not after any TRAIN read.

**Does not resolve — still open after this:**
- **G2 cleanup** (§8 of round 2): widen Tier 1 with `ind_niftytotalmarket_list`, adopt NSE's
  label over the hand register where they disagree (`JUSTDIAL`, `PTC`, `KSCL` confirmed),
  add the `evidence` column, fix Tier-2 interval handling, emit or delete
  `nse_industry_sourced.csv`. Prompt G2-R is ready in round 2 §9 and is unaffected by this work.
- **The carry substrate certification** (P2) remains unrun.

**Windows untouched:** SEALED 2023-01-01 → 2026-07-20 unread; HOLDOUT 2021–2022 unspent; no
TRAIN read taken. Nothing in this spec looks at futures or at any return series.

---

## 5. Correction to the record

`CARRY_G1_G2_VERIFICATION_REVIEW_2.md` §2 accepted, on the remediation report's word, that the
2015 sessions were unrecoverable — it verified the *count* but not the *conclusion*. That was
an error in round 2, corrected here by probing all 53. The lesson generalizes: **"we tried and
the source doesn't have it" is a claim about the world and has to be probed like any other.**
A report of absence produced by code that cannot distinguish absence from failure is not
evidence of absence.

The same standard was then applied to this document's own claims. The 7 remaining dates were
re-probed against alternate NSE hosts before being called absent (§1.4); the in-loop import was
executed before the failure mechanism was attributed (§0); `equity_bhavcopy_adjusted` was
checked to be a VIEW before the G3 gate assumed propagation (§3). Where a check could not
settle the question — which of two mechanisms broke the retry run — the document says so
instead of picking one.
