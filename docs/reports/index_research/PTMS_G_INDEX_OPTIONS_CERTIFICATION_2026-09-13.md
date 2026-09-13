# PTMS Family G — Index-options EOD substrate certification pass

> **⚠️ SUPERSEDED 2026-09-13 by
> `docs/reports/ptms/PTMS_FAMILY_G_INDEX_OPTIONS_SUBSTRATE_CERTIFICATION_2026-09-13.md`.**
>
> **This document is the PRE-REPAIR survey.** Its statements that the ingest "was *not* re-run",
> that the store ends **2026-07-17**, and that 2021-03-30 is "closable by re-running the ingest"
> were true when written and are **false now**. Phase G0 performed the repair: the store runs to
> **2026-09-11** (2,612 sessions, +66,272 rows), the `except Exception` defect is fixed, and
> 2021-03-30 was retried and is **permanently unrecoverable — the source returns 404**.
>
> Read the G0 report for the current state. Nothing below has been edited.

**Date:** 2026-09-13 · **Authority:** operator instruction — *"begin the PTMS Family G index-options
EOD substrate certification pass … P2/certification work only."*

**Access boundary, stated precisely.** Certification inspects values **structurally** — key
uniqueness, null and sign checks, OHLC ordering, grid spacing, counts by class. That is what a
substrate contract is made of, and it is the same level at which C2-A4 (`prev_close` identity) was
certified. **No option OHLC/OI/IV value entered a feature, a signal, a label or a fitted
parameter**; no candidate was run; no RFA was declared; **no market-data store was modified** — in
particular the ingest was *not* re-run, though §8 recommends it.

> **Verdict offered for signature, not taken: the surface is certifiable with four declared
> contract facts and one genuine one-session gap.** Both candidate windows survive intact —
> **TRAIN 2021-01-01 → 2022-12-31 (495 of 496 sessions)** and **HOLDOUT 2026-01-01 → 2026-07-17
> (132 of 133)**. Nothing found requires giving up either.
>
> **The one finding that would break a naive construct: 72.7% of rows are untraded, and every one
> of them carries a non-zero `close`.**

---

## 1. The surface

| | |
|---|---|
| Store | `data/market_data/options_bhavcopy.duckdb`, table `option_bhavcopy` |
| Rows | **5,490,319** |
| Span | **2016-02-11 → 2026-07-17**, 2,572 distinct `trade_date` |
| Underlying | **`NIFTY` only** — a single symbol, by rule (§7) |
| Grain | one row per `(trade_date, symbol, expiry_dt, strike, option_type)` |
| Columns | `symbol · expiry_dt · strike · option_type · open · high · low · close · settle · contracts · val_in_lakh · open_int · chg_in_oi · trade_date · ingested_at` |
| Types | CE 2,720,363 · PE 2,769,956 |

**Scope fact a Family G hypothesis must absorb first: there is no BANKNIFTY.** This store holds
Nifty index options and nothing else. Any market-state construct that wants bank-index options has
no substrate here, certified or otherwise.

---

## 2. G1 — Date and calendar semantics

`trade_date` is a **date**, not a timestamp: there is no intraday clock on this surface and none of
C1's vendor/native labelling problem applies to it.

**Coverage against `trading_calendar`, 2016-02-11 → 2026-07-17: 2,572 of 2,584 sessions; 0 options
dates absent from the calendar.** The 12 differences resolve into three classes, and only one is a
defect:

| Class | Dates | Reading |
|---|---|---|
| **Muhurat / special sessions** (7) | 2016-10-30, 2019-10-27, 2020-11-14, 2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18 | Cash traded; no F&O bhavcopy published. **Expected, not a hole** — the same class ISD's G1 calls `weekend_special` |
| **Budget Saturdays** (3) | 2020-02-01, 2025-02-01, 2026-02-01 | As above |
| **Calendar artifact** (1) | 2016-04-19 | `trading_calendar` carries the date, **`equity_bhavcopy` has no rows for it either**. The calendar is wrong, not the options store — same family as the 2012-11-11 Sunday already recorded in `CLAUDE.md` |
| **GENUINE GAP** (1) | **2021-03-30** | A real session — `equity_bhavcopy` carries 1,730 rows. The options store has none. **Quarantined (Q-G1) and it sits inside the TRAIN candidate window** |

**Currency — the store is stale.** `max(ingested_at)` is **2026-07-20**, and the last `trade_date`
is 2026-07-17, while the *stock* options store runs to 2026-09-11. The index-options ingest simply
has not run for ~2 months. This is an ingest gap, not an availability gap: NSE publishes daily.

---

## 3. G2 — Contract and entity integrity

| Check | Result |
|---|---|
| Duplicate `(trade_date, symbol, expiry_dt, strike, option_type)` | **0** |
| NULL `expiry_dt` / `strike` / `settle` / `close` | **0 / 0 / 0 / 0** |
| Rows with `expiry_dt < trade_date` | **0** |
| `strike <= 0` | **0** |
| Strike range | 2,700 → 34,500 |
| Sessions with anomalously few rows | **none** — min 1,265, p5 1,367, median 2,096, max 4,950 |

**One convention change inside the store: the strike grid halved.** Modal strike spacing is **100
points through 2019 and 50 points from 2020 onward**. Any measure whose units are *strikes* rather
than *index points* (strike counts within a band, ladder width, "N strikes OTM") is **not
comparable across 2019-12-31**. Both candidate windows sit after the change, so this constrains
history, not them.

---

## 4. G3 — Expiry semantics

This is where the surface is least like an equity panel, and where an unexamined construct breaks.

**Three regimes, measured from distinct expiry counts per year:**

| Era | Shape |
|---|---|
| 2016 → 2018 | **Monthly only** — 11–12 expiries a year, Thursday |
| 2019 → mid-2025 | **Weeklies added** — 45–52 a year, Thursday, with Wednesday shifts on holidays |
| mid-2025 → 2026 | **Expiry day moved Thursday → Tuesday** — 2025 splits 34 Thursday / 17 Tuesday; 2026 is 34 Tuesday / 3 Monday / 3 Thursday |

**`expiry_dt` is the NOMINAL expiry, not necessarily the last trading day.** Five expiries fall on
dates that are not trading days at all — 2018-03-29, 2023-03-30, 2023-06-29, 2026-03-26,
2026-03-31 — so the contract's final session was earlier. **Days-to-expiry computed as
`expiry_dt − trade_date` is wrong on exactly those expiries**, and a construct keyed to the expiry
boundary must resolve the last *trading* day from the calendar.

**Not every listed expiry reaches settlement.** Three long-dated expiries — 2025-09-25, 2025-12-24,
2026-06-25 — have rows up to 2025-07-31 and then stop, with no expiry-day row. The cause is
visible in the ladder: long-dated expiries (tenor > 365d) listed **before** 2025-08-01 are 27
Thursday / 1 Wednesday / 1 Tuesday; **after**, 9 Tuesday / 1 Monday. **The Thursday → Tuesday move
re-listed the long ladder and orphaned the old Thursday-dated contracts.** That is a market event,
not a data defect — but it means *an expiry present in the store may never settle in it*.

Depth is otherwise stable: **18 expiries per session and ~1,700–1,825 days of maximum tenor right
through 2026-07**, with no collapse at the 2025 transition.

---

## 5. G4 — Corporate actions

**Index options need no corporate-action adjustment, and this is the substantive difference from
every equity surface in the repo.** Strikes are absolute index points on an index that is itself
divisor-adjusted by NSE; there is no bonus, split or face-value event that re-prices a listed Nifty
contract, and no adjustment factor exists to apply or mis-key. The CA machinery that dominates
CSMP, PSB-1 and the 1m store — entity grain, issuer-prefix ISIN linkage, adjusted-series continuity
— **does not apply here**, and importing it would be a category error.

What *does* change under the surface — index reconstitution twice a year — changes the underlying's
composition, not any contract's terms. It is a property of the index, disclosed for any construct
that reads index levels, and it is **not** a corporate action on the option.

---

## 6. G5 — Tradeability — the finding that matters

| Class | Rows | Share |
|---|--:|--:|
| `contracts = 0` (**no trade**) | **3,989,845** | **72.7%** |
| `contracts > 0` (traded) | 1,500,474 | 27.3% |
| `open_int = 0` | 3,294,361 | 60.0% |

**Every one of the 3,989,845 untraded rows carries `close > 0`, and 3,988,249 of them carry
`open = high = low = 0`.** The bhavcopy publishes a closing price for a contract nobody traded.
`close = settle` on only 3,577 of them, so the two fields disagree about what that price even is.

**This is the CAS carry-forward lesson on a different surface: a row is not a trade.** A construct
that reads `close` without asserting `contracts > 0` is reading a number the market never printed —
for nearly three rows in four. The apparent "3,988,249 OHLC violations" in a naive scan are exactly
this class (`high = 0 < close`), not corrupt data: **among traded rows there are 0 OHLC ordering
violations.**

Two further contract facts:

- **`settle = 0` has two meanings.** 15,050 of the 187,775 zero-settle rows fall on the contract's
  own expiry day — a worthless settlement, correct and informative. The other 172,725 are
  off-expiry, 89% of them in **2016–2019** (2016: 23,337 · 2017: 51,430 · 2018: 37,772 · 2019:
  41,997, collapsing to 419 in 2026) — a legacy-era convention of publishing zero settle for
  deep-OTM untraded strikes. Inside the candidate windows it is small but non-zero (2021: 4,018 ·
  2022: 6,651 · 2026: 419).
- **6,426 traded rows carry `open_int = 0`** — opened and closed within the session. Real, and a
  tradeability filter keyed on OI would discard them.

---

## 7. G6 — Provenance

| | |
|---|---|
| Ingest | `scripts/msrp/ingest_option_bhavcopy.py` — **committed and re-runnable** |
| Idempotence | Skips any date that already has rows; insert-only per date |
| Miss handling | **No permanent miss markers are written.** A missed date is retried on the next run — this store does **not** carry the `.404`-cache defect that bit the equity ingest |
| Fast-skip | After 30 consecutive misses, and **only in the legacy era** — explicitly disabled for the forward backfill |
| Recorded repair | A committed **F2 purge** removes non-`NIFTY` rows (NIFTYNXT50 contamination). The single-underlying property in §1 is enforced, not incidental |

**One defect, MEDIUM.** The ingest loop wraps `_ingest_single_day` in `except Exception` and counts
the failure into `total_404`, printing it as "no data". That is the pitfall `CLAUDE.md` names — *a
bare except turns "we failed" into "the source doesn't have it"*. The damage is bounded here
because nothing is cached, so a re-run recovers; but **`total_404` is not evidence of absence** and
must not be quoted as such. Recommended fix: catch only `requests.RequestException` around the
fetch and classify a date as missing solely on a non-200 status.

---

## 8. Quarantine register for this surface

| # | Item | Class | Disposition |
|---|---|---|---|
| **Q-G1** | **2021-03-30** — real session, zero options rows | Genuine gap | **Quarantine the session.** It is inside the TRAIN candidate window; a construct must skip it rather than interpolate. Closable by re-running the ingest for that single date |
| **Q-G2** | 10 Muhurat / special / Budget-Saturday sessions | Expected absence | Not a defect. Declare, never backfill |
| **Q-G3** | 2016-04-19 | `trading_calendar` artifact | Belongs to the calendar, not this store. Same class as 2012-11-11 |
| **Q-G4** | 3 orphaned long-dated Thursday expiries (2025-09-25, 2025-12-24, 2026-06-25) | Market event | Declare: a listed expiry may never settle in the store |
| **Q-G5** | Store stale since 2026-07-17 (`ingested_at` max 2026-07-20) | Currency | **Re-run the ingest** — an ingest-level action that spends no research budget and would extend the HOLDOUT candidate to the present. Not done here: the instruction forbids modifying market data |

---

## 9. The certified surface — offered for signature

**Proposed certification text** (the stamp is the operator's, exactly as with the N100 substrate):

> **Surface:** `option_bhavcopy`, underlying `NIFTY`, EOD grain.
> **Window:** 2016-02-11 → 2026-07-17, 2,572 sessions, less Q-G1 (2021-03-30).
> **Contract:** one row per `(trade_date, symbol, expiry_dt, strike, option_type)`, unique and
> non-null; no CA adjustment applies; `expiry_dt` is nominal; a row is a quote, **not** a trade —
> `contracts > 0` is the tradeability predicate; strike grid is 100 points to 2019 and 50 from
> 2020; expiry regime is monthly → weekly (2019) → Tuesday (mid-2025).

**Four declared contract facts ride with it** — untraded rows carry prices (§6), `expiry_dt` is
nominal (§4), the strike grid changed in 2020 (§3), and the expiry day changed in 2025 (§4).

---

## 10. Eligible unread windows, with prior-exposure reconciliation

Exposure traced component-wise and transitively, against
`governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` and the consumers' own artifacts.

| Window | Sessions | Prior exposure | Status |
|---|--:|---|---|
| 2016-02-11 → 2016-06-30 | ~95 | none recorded | Fresh but pre-dates both convention changes; 100-point grid, monthly-only expiries |
| 2016-07-01 → 2020-12-31 | ~1,100 | **Skew sleeve TRAIN**, `SKEW_TRAIN_REPORT.md` — signal level, FAILED at TRAIN | **SPENT** |
| **2021-01-01 → 2022-12-31** | **495** of 496 | Skew's HOLDOUT was **specified as 2021-01 → 2022-12 and never read** — TRAIN failed first | **FRESH — the TRAIN candidate** |
| 2023-01-02 → 2025-12-31 | ~740 | **MSRP D1 straddle triage**, `scripts/msrp/triage_fee_impact.py` — a next-day ATM straddle rule evaluated gross and net of fees | **SPENT at signal level** |
| **2026-01-01 → 2026-07-17** | **132** of 133 | none recorded | **FRESH — the HOLDOUT candidate** |

**Both candidate windows are preserved and materially complete.** TRAIN misses one session
(Q-G1, 2021-03-30); HOLDOUT misses one (2026-02-01, a Budget Saturday with no F&O publication).

**Three comparability facts that any Family G pre-registration must declare — they are not
blockers, they are disclosures:**

1. **The expiry day changes between TRAIN and HOLDOUT.** TRAIN is entirely Thursday-expiry;
   HOLDOUT is Tuesday. A construct expressed in *days to expiry* survives this; one expressed in
   weekday effects, or in "the weekly", does not.
2. **The traded-row share differs sharply** — 34.1% in TRAIN (1,072,606 rows) versus 60.6% in
   HOLDOUT (238,556 rows). The ladder is quoted differently in the two eras, so any statistic
   computed per *listed* contract is on different denominators. Compute per *traded* contract.
3. **HOLDOUT is short and capped by staleness** — 132 sessions, ending 2026-07-17 only because the
   ingest stopped. Closing Q-G5 would extend it by ~40 sessions at zero budget cost.

**Level note.** The register records the Skew consumer at signal level against index options and
the MSRP triage under the same row without a pinned window; §10 pins both. That pinning is the
correction the P3 reconciliation flagged — a row for the operator to append, not for me to edit.

---

## 11. What this pass does NOT cover

- **Stock options** (`stock_options_bhavcopy`, 99,485,464 rows to 2026-09-11) — a different store,
  different CA semantics, and already signal-consumed 2016-02-26 → 2026-08-20 by the seller-edge
  study. Not examined here.
- **Futures EOD** — a market-state construct will likely want the futures leg; that surface is
  uncertified and its budget is largely spent (F-1…F-6).
- **The index level itself.** A Nifty-options construct that conditions on spot or on realized
  volatility reads the 1d/1m index surfaces, which are **uncertified** and, at signal level,
  **spent**. *This is the most likely way a Family G construct accidentally becomes ineligible —
  the options surface being clean does not make its covariates clean.*
- **Any hypothesis.** No construct was defined, no feature computed, no RFA declared.

---

## 12. Recommendation

1. **Sign or refuse §9.** The four contract facts are the substance; the verdict is yours.
2. **Close Q-G5 first** — re-run `scripts/msrp/ingest_option_bhavcopy.py` to the present. It spends
   no research budget, extends the HOLDOUT candidate by roughly 40 sessions, and is the single
   cheapest improvement available to Family G.
3. **Close Q-G1 in the same run** — one date, 2021-03-30, inside the TRAIN window.
4. **Fix the `except Exception` in the ingest** (§7) before relying on any future "no data" report.
5. **Before a G pre-registration, settle the covariate question** (§11): if the construct needs
   spot or realized vol, its substrate is not this surface alone, and that part is neither
   certified nor unspent.
