# PTMS Family G — NIFTY index-options EOD substrate certification

**Phase G0 — zero-research-budget ingest repair and re-certification**

**Date:** 2026-09-13 · **Authority:** operator instruction, Phase G0.
**Access level:** ingest + structural certification. **No option value entered a feature, signal,
label or fitted parameter.** No candidate, no RFA, no TRAIN, no HOLDOUT, no strike selection, no
parameter fitting, no covariate (spot / VIX / futures / realized vol) was read.

> ## VERDICT: **CERTIFIED**
> The Family G NIFTY index-options EOD substrate is ready for P3 hypothesis definition /
> pre-registration, under the contract in §D–§E and the quarantines in §C.
>
> **The repair moved the HOLDOUT endpoint: 2026-07-17 → 2026-09-11** (+40 sessions).
> **2021-03-30 is NOT recovered** — the source returns 404 for it; it stays quarantined as a
> one-session hole inside TRAIN.

---

## A. Exact store state

| | Before G0 | **After G0** |
|---|---|---|
| Rows | 5,490,319 | **5,556,591** (+66,272) |
| Span | 2016-02-11 → 2026-07-17 | **2016-02-11 → 2026-09-11** |
| Sessions | 2,572 | **2,612** (+40) |
| `max(ingested_at)` | 2026-07-20 | **2026-09-13 22:20** |
| Currency vs calendar | stale by 56 days | **CURRENT** — store max = calendar max = 2026-09-11 |

Store: `data/market_data/options_bhavcopy.duckdb`, table `option_bhavcopy`.
Underlying: **`NIFTY` only** — unchanged, and enforced by the ingest's committed F2 purge.
Grain: one row per `(trade_date, symbol, expiry_dt, strike, option_type)`.
Historical start **2016-02-11** — unchanged.

**Copy-first baseline taken before any write:**
`data/_baselines/options_bhavcopy_pre_g0_repair_2026-09-13/options_bhavcopy.duckdb` (303,837,184
bytes, verified byte-size match).

---

## B. Exact date / session coverage — **G1**

**2,612 of 2,624 calendar sessions.** Zero options dates absent from the trading calendar.

| Class | Count | Dates |
|---|--:|---|
| Expected absence — cash traded, no F&O bhavcopy published (Muhurat, special sessions, Budget Saturdays) | 10 | 2016-10-30, 2019-10-27, 2020-02-01, 2020-11-14, 2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01, 2026-02-01 |
| `trading_calendar` artifact — the calendar carries it, `equity_bhavcopy` has no rows either | 1 | 2016-04-19 |
| **Genuine gap** | **1** | **2021-03-30** |

**Forward repair:** 2026-07-18 → 2026-09-12 ingested in one run — **66,272 rows, 0 dates 404, 0
skipped.** Every session in that range that exists was fetched.

---

## C. Remaining gaps and quarantines

| # | Item | Class | Status after G0 |
|---|---|---|---|
| **Q-G1** | **2021-03-30** | Genuine gap **inside TRAIN** | **NOT RECOVERED — permanent.** Retried explicitly; NSE's historical archive returns **404** for that date (legacy format; the UDiFF format does not reach back to 2021). With the §F fix in place this 404 is now *trustworthy evidence of absence at source*, not a swallowed failure. **TRAIN is 495 of 496 sessions; a construct must skip this date, never interpolate it** |
| Q-G2 | 10 Muhurat / special / Budget-Saturday sessions | Expected absence | Standing. Not a defect, never to be backfilled |
| Q-G3 | 2016-04-19 | Calendar artifact | Belongs to `trading_calendar`, not this store |
| Q-G4 | 3 orphaned long-dated expiries — 2025-09-25, 2025-12-24, 2026-06-25 | Market event | **Still present.** Listed with rows to 2025-07-31, then dropped without an expiry-day row: the Thursday→Tuesday move re-listed the long ladder (long-dated expiries before 2025-08-01 are 27 Thursday / 1 Wed / 1 Tue; after, 9 Tuesday / 1 Monday). **A listed expiry may never settle in the store** |
| ~~Q-G5~~ | Store stale since 2026-07-17 | Currency | **CLOSED** — store is current to 2026-09-11 |

---

## D. Tradeability rule — **G5**

| Class | Rows | Share |
|---|--:|--:|
| Traded — `contracts > 0` | **1,535,038** | **27.6%** |
| Untraded — `contracts = 0` | 4,021,553 | 72.4% |
| …of which carry `close > 0` | **4,021,553** | **100%** |
| `open_int = 0` | 3,319,688 | 59.7% |
| …of which **did trade** | **6,478** | — |

**THE RULE — `contracts > 0` is the tradeability predicate.**

- **Every untraded row carries a non-zero `close`.** The bhavcopy publishes a closing price for
  contracts nobody traded, on 72.4% of rows. Reading `close` without asserting `contracts > 0` is
  reading a number the market never printed. This is the CAS carry-forward lesson on a different
  surface: *a row is a quote, not a trade.*
- **`open_int > 0` MUST NOT be used as the tradeability predicate.** 6,478 rows traded with zero
  open interest — opened and closed inside the session. An OI filter silently discards real trades.
- `settle = 0` has two meanings: worthless settlement on the contract's own expiry day, and a
  legacy-era convention for deep-OTM untraded strikes, concentrated in 2016–2019 and near-vanished
  by 2026.

---

## E. Expiry-regime facts — **G3**

**Three regimes, unchanged by the repair:**

| Era | Shape |
|---|---|
| 2016 → 2018 | Monthly only, 11–12 expiries a year, Thursday |
| 2019 → mid-2025 | Weeklies added, 45–52 a year, Thursday, Wednesday on holiday shifts |
| mid-2025 → 2026 | **Expiry day moved Thursday → Tuesday.** 2025: 34 Thu / 17 Tue / 3 Wed / 1 Mon. **2026 after the repair: 41 Tue / 4 Mon / 3 Thu** |

- **`expiry_dt` is NOMINAL and must not be treated as the final trading date.** Five expiries fall
  on non-trading days — 2018-03-29, 2023-03-30, 2023-06-29, 2026-03-26, 2026-03-31 — so
  `expiry_dt − trade_date` is wrong for them. Resolve the last *trading* day from the calendar.
- Eight expiries have no row on their own expiry date: the five above, plus the three orphaned
  long-dated contracts (Q-G4).
- **Strike grid: 100 points through 2019, 50 points from 2020 onward.** Any measure whose unit is
  *strikes* rather than index points is not comparable across 2019-12-31. Both candidate windows
  sit after the change.
- Depth is stable: 18 expiries per session, ~1,700–1,825 days maximum tenor, through 2026-09.

### Corporate actions — **G4**

**None apply, and this remains the structural difference from every equity surface in the repo.**
Strikes are absolute index points on a divisor-adjusted index; no bonus, split or face-value event
re-prices a listed NIFTY contract, and no adjustment factor exists to apply or mis-key. Index
reconstitution changes the underlying's composition, not any contract's terms.

---

## F. Ingest provenance and repair — **G6**

**Script:** `scripts/msrp/ingest_option_bhavcopy.py` — committed, idempotent (skips any date that
already has rows), insert-only per date. Behaviour preserved; no architectural change.

**The defect, fixed.** The run loop caught bare `Exception` and counted every failure into the
404 tally, printing it as "no data" — the pitfall `CLAUDE.md` names: *a bare except turns "we
failed" into "the source doesn't have it."* Now:

| Outcome | Handling |
|---|---|
| HTTP 404 from both formats | Counted as **confirmed absent at source** |
| `requests.RequestException` (connection, timeout, non-200 via `raise_for_status`) | Counted separately as **"we failed to fetch — retry these"**, listed by date, and **does not advance the legacy fast-skip counter** |
| Anything else (parse, schema, programming error) | **Raised — fails loudly** |

This is what makes §C's Q-G1 disposition evidence rather than assumption: 2021-03-30's 404 was
produced by the corrected classifier.

**Structural certification is now a committed re-runnable script**, not ad-hoc SQL:
`scripts/msrp/certify_index_options.py` — runs G1–G6 and exits non-zero on a hard structural
failure. Current run: **exit 0, no hard failure.**

**Disclosed side effect:** the ingest script's own tail writes
`docs/reports/MSRP_PHASE7_BHAVCOPY_AUDIT.md` (a new, previously untracked file). Its content is
structural — coverage percentages, average open interest, zero-volume day counts by expiry. No
outcome statistic, no return, no P&L.

**G2 integrity, re-run after the repair — all clean:**

| Check | Result |
|---|---|
| Duplicate `(trade_date, symbol, expiry_dt, strike, option_type)` | **0** |
| NULL `expiry_dt` / `strike` / `close` / `settle` | **0 / 0 / 0 / 0** |
| `expiry_dt < trade_date` | **0** |
| `strike <= 0`, `low < 0`, `settle < 0` | **0** |
| OHLC ordering violations **among traded rows** | **0** |
| Sessions with < 400 rows (partial ingest) | **0** |

---

## G. Exact candidate TRAIN / HOLDOUT windows

Structural session accounting only. No return, P&L, selection outcome, IC, t-stat or Sharpe was
computed.

| | TRAIN | HOLDOUT |
|---|---|---|
| Window | **2021-01-01 → 2022-12-31** | **2026-01-01 → 2026-09-11** |
| Calendar sessions | 496 | 173 |
| **Sessions with options data** | **495** | **172** |
| Missing | **2021-03-30** (Q-G1, source 404) | 2026-02-01 (Budget Saturday, Q-G2) |
| Rows | 1,072,606 | 304,828 |
| Traded rows (`contracts > 0`) | 365,590 (**34.1%**) | 179,122 (**58.8%**) |

**HOLDOUT endpoint is 2026-09-11, not 2026-07-17** — the repair added 40 sessions and the store is
now current to the calendar.

**Three comparability facts the pre-registration must declare** — disclosures, not defects:

1. **The expiry day differs between the windows.** TRAIN is entirely Thursday-expiry; HOLDOUT is
   Tuesday. A construct expressed in *days to expiry* survives this; one expressed in weekday
   effects or "the weekly" does not.
2. **Traded-row share differs sharply** — 34.1% vs 58.8%. The ladder is quoted differently in the
   two eras, so any statistic per *listed* contract is on different denominators. Compute per
   *traded* contract.
3. **HOLDOUT is roughly one third of TRAIN's length** (172 vs 495 sessions) and will keep growing
   with calendar time; the endpoint must be **frozen in the pre-registration**, not left as "the
   present".

---

## H. Prior-exposure reconciliation

Only the structural read required for this certification was performed. **No additional historical
window was opened.**

| Window | Prior exposure | Status |
|---|---|---|
| 2016-02-11 → 2016-06-30 | none recorded | Fresh; pre-dates both convention changes |
| 2016-07-01 → 2020-12-31 | **Skew sleeve TRAIN** (`SKEW_TRAIN_REPORT.md`) — signal level, FAILED at TRAIN | **SPENT** |
| **2021-01-01 → 2022-12-31** | Skew's HOLDOUT was *specified* as this window and **never read** — TRAIN failed first | **FRESH — TRAIN candidate** |
| 2023-01-02 → 2025-12-31 | **MSRP D1 straddle triage** (`scripts/msrp/triage_fee_impact.py`) — a next-day ATM straddle rule evaluated gross and net of fees | **SPENT at signal level** |
| **2026-01-01 → 2026-09-11** | none recorded | **FRESH — HOLDOUT candidate** |

**This pass's own exposure, for the register:** ingest-level (write path) over 2021-03-30 and
2026-07-18 → 2026-09-12, plus **structural certification** reads across the full store. Per the
register's own key, ingest and meta/structural levels **do not spend budget**. The rows above are
for the operator to append; the register is append-only.

**Pinning correction carried forward:** the register records the Skew and MSRP consumers under row
O-2 without windows. §H pins both. That correction remains the operator's to append.

---

## I. Remaining blockers

**For this surface: none.** G1–G6 return no hard structural failure; the certification script exits
0.

Two boundaries that are **not** blockers to certifying this substrate, but which bound what may be
built on it:

1. **Covariates are not certified.** Spot, VIX, realized vol, futures — a construct that conditions
   on any of them reaches surfaces that are uncertified and, at signal level, largely spent. Per
   the instruction, those require a later, explicit certification stage.
2. **Q-G1 is permanent.** 2021-03-30 cannot be recovered from this ingest path. TRAIN is 495
   sessions, not 496, and the pre-registration must say so.

---

## J. Certification verdict

**CERTIFIED — the Family G NIFTY index-options EOD substrate is ready for P3 hypothesis definition
and pre-registration.**

Certified surface:

> `option_bhavcopy`, underlying **NIFTY**, EOD grain, **2016-02-11 → 2026-09-11**, 2,612 sessions,
> less the quarantines in §C. One row per `(trade_date, symbol, expiry_dt, strike, option_type)`,
> unique and non-null. **No corporate-action adjustment applies.** `expiry_dt` is **nominal**.
> **`contracts > 0` is the tradeability predicate; `open_int > 0` is not.** Strike grid 100 points
> to 2019, 50 from 2020. Expiry regime monthly → weekly (2019) → Tuesday (mid-2025).

Candidate windows, frozen by this report:
**TRAIN 2021-01-01 → 2022-12-31 (495 sessions)** · **HOLDOUT 2026-01-01 → 2026-09-11 (172
sessions)**.

**Stop point.** No hypothesis has been defined, no construct proposed, no strike selected, no
parameter fitted, no RFA run. The next step is yours: define the Family G hypothesis, declare
multiplicity and prior exposure, and only then run the RFA.
