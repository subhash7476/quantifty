# CAS Adaptation Register — what must change in this repo

**Date:** 2026-08-27
**Companion to:** `docs/reports/CAS_IMPACT_ASSESSMENT.md` (the rule, the market evidence, the post-15:15 question). This document is the **change register**: what in the repo encodes a pre-CAS assumption, and how bad each one is.
**Premise:** CAS is permanent. Phase 1 (F&O stocks) live since 2026-08-03; pre-open alignment 2026-09-07; Category II stocks are an announced future phase.

**Nothing was edited in this pass. This is the list.**

---

## 0. The headline finding

Post-2026-08-03, our 1m store contains **fabricated bars** for Category I (F&O) symbols. Between 15:15 and 15:27 the aggregator carries forward the last continuous price as `O=H=L=C` with `volume=0`, because no trades occur during the halt/auction. The entire auction then lands as **one bar** carrying the full auction volume.

```
NSE_EQ|INE002A01018 (RELIANCE), 2026-08-24
  15:14  1305.0 1305.1 1302.9 1304.1   vol   68,944   <- last real continuous bar
  15:15  1304.1 1304.1 1304.1 1304.1   vol        0   <- synthetic
   ...     (13 identical synthetic bars)
  15:27  1304.1 1304.1 1304.1 1304.1   vol        0
  15:29  1309.8 1309.8 1309.8 1309.8   vol  377,584   <- the entire auction, one print
```

Measured scope (`data/market_data/nse/candles/1m/`):

| Session | Equity symbols | Flat `vol=0` across 15:15–15:27 | Auction-print minute |
|---|--:|--:|---|
| 2026-07-29 (pre-CAS) | 200 | 0 (0%) | n/a — continuous throughout |
| 2026-08-03 | 200 | 184 (**92%**) | 15:29 |
| 2026-08-04 | 200 | 184 (**92%**) | **15:28** |
| 2026-08-13 | 197 | 187 (**95%**) | 15:29 |
| 2026-08-19 | 197 | 187 (**95%**) | 15:29 |
| 2026-08-24 | 197 | 188 (**95%**) | 15:29 |

The residual 5–8% that still trade continuously to 15:29 are the **Category II** (non-F&O) names — a clean natural experiment confirming the split.

**The index behaves the same way** (Nifty 50, 2026-08-04): flat at 24463.45 from 15:15 through 15:27, then a single bar to 24614.90. We hold **no** disseminated indicative-index data — the exchange publishes an indicative price and imbalance through the auction, and none of it reaches our store.

### The one piece of good news — verified, not assumed

Cross-checked the 1m auction print against the official `equity_bhavcopy` close via the ISIN→ticker map in `data/instruments/nse_fo_instruments.duckdb`:

| Session | Symbols matched | last-bar close == official | auction print == official |
|---|--:|--:|--:|
| 2026-08-04 | 200 | 185 (92%) | 185 (92%) |
| 2026-08-19 | 197 | 187 (95%) | 187 (95%) |
| 2026-08-24 | 197 | 188 (95%) | 188 (95%) |

The non-matching remainder is exactly the Category II count — those close on VWAP, which correctly differs from their last trade. **Daily close semantics are intact.** Every daily-close construct in this repo (Carry, TS Basis, TS Basis Daily, CB-N50, PSB-1/2, SFB-1/F1) is untouched by CAS. The problem is confined to **intraday** work: fillability of a 15:29 exit, feature windows containing synthetic bars, live pollers stopping too early, and a store that now holds two session structures in one table.

---

## Implementation status — 2026-08-27

All 22 items closed. 13 code tasks executed per `docs/superpowers/plans/2026-08-27-cas-adaptation.md`; Task 12 withdrawn. Commits `f82cd32`…`13ffd92` on `isd-program-reassessment`.

> **Reopened 2026-09-10 — one new item, `A9`.** The auction-window *index reference* freezes at 15:15; the original 22 items covered carry-forward **bars** and segment **end-times**, not the spot level the derivatives book is priced against. It was found only because **B6** (now closed) extended the options-wall poller to 15:40 and made the window observable. A9 is open.

**A5 (ISD SEALED straddle) — MOOT.** The ISD battery closed at TRAIN (`05f5ed2`: both families FAIL, F1 sign negative and F4 net-spread gate). No sealed read will be taken, so the 55%-post-CAS straddle is history rather than a live risk. The declaration is left frozen as-is; moving a SHA on a closed program is the error this repo already recorded against PSB-2's selection report.

**A6 (A-construct exit) — RESOLVED at 15:14.** Operator decision D6 (`d33e762`) pinned the exit at the 15:14 bar close: last continuous print in all eras, auction window untraded. The construct was then retired at HOLDOUT (`c72fa63`: TRAIN net +1.27 bp p 0.003; HOLDOUT net −0.22 bp p 0.15), SEALED untouched at 873 sessions. D6 stands as the settled convention for any index intraday exit.

**Backfill applied.** 40,430 carry-forward bars flagged across the original 16 post-CAS sessions, plus 2,429 (2026-08-25) and 2,402 (2026-08-26) after the B11 lag fill — 45,261 total across 18 sessions. Copy-first snapshots (`.pre_cas_mark`) taken before each mutation and never overwritten. Verified after every pass: **0 index bars flagged, 0 auction prints flagged**, Nifty 50's closes intact.

**B11 closed.** 1m store was two sessions behind (through 2026-08-24) while bhavcopy was current to 2026-08-26. The live buffer purges daily, so the gap was refilled from the Upstox V3 historical API (150,000 rows, 200 symbols × 375 bars × 2 sessions) and then marked.

---

## Class A — Backtest-contaminating
*Changes a number in a committed or pending research artifact. Fix before any affected read is spent.*

### A1 · Synthetic carry-forward bars are indistinguishable from real ones
13 fabricated slots per Cat-I symbol per session since 2026-08-03. Nothing in the schema marks them. Any feature computed over the last 15 minutes — realized vol, true range, CLV, close-location, PM statistics — is silently deflated for post-CAS sessions, because 13 of the window's bars have zero range by construction.
**Where:** the store itself; consumed by `core/analytics/day_features.py`, `scripts/build_intraday_features.py`, `scripts/isd/battery_features.py`.
**Fix:** flag or exclude. A `vol=0 AND O==H==L==C AND minute>=15:15 AND date>=2026-08-03` predicate identifies them for equities.

### A2 · The auction bar is not reliably "the last bar" — and for indices there is no tell

> **Consequence made explicit 2026-08-27:** any marking predicate that leans on `volume = 0` is **`NSE_EQ`-only by rule**. Applied to `NSE_INDEX` it marks the index's real close as fabricated — Nifty 50's 24614.90 on 2026-08-04 sits at 15:29 as a flat, zero-volume bar and would be destroyed. The implementation plan carries a guard and a regression test on both marking paths.

The random close (15:28–15:30) put the print at **15:28 on 2026-08-04** and 15:29 on every other session measured. For equities the print is identifiable by `volume>0`. **Indices carry `volume=0` always** (existing pitfall in CLAUDE.md), so for Nifty/BankNifty the auction bar **cannot be detected from the data**. Index remediation must be era-rule-based, never data-detected.

### A3 · The store is now heterogeneous within a single table
Cat-I symbols have **361** tradeable minutes; Cat-II have **375**. Nothing distinguishes them, and membership moves — 16 continuous-trading symbols on Aug 3/4, 10 from Aug 13 onward. CAS category is therefore a **point-in-time symbol attribute**, not an era flag.
**Fix:** derive PIT CAS-category from the F&O instrument master, using the machinery already built at `scripts/isd/build_pit_universe.py`.

### A4 · ISD Phase-1 substrate certification covers 16 post-CAS sessions
`ISD_PHASE1_SUBSTRATE_CERTIFICATION.md` certifies **903 sessions, 2023-01-02 → 2026-08-24** — all gates PASS. The window includes 2026-08-03 → 2026-08-24. `scripts/isd/gate_contiguity.py` requires exactly one bar per slot 09:15..15:29 and got it — **the gate counted correctly**. What it cannot do is certify that a bar is a *tradeable observation*. This is the exact mirror of the pitfall already recorded in CLAUDE.md ("a gate that tests file existence cannot certify row existence"), one level down.
**Fix:** amend the certification with a post-CAS scope note; add a tradeability arm to the contiguity gate.

### A5 · ISD's SEALED window straddles the CAS boundary — **MOOT as of 2026-08-27**

> **Closed without action.** The ISD battery **closed at TRAIN** (commit `05f5ed2`: both families FAIL — F1 sign negative, F4 net-spread gate). No sealed read will ever be taken, so the straddle below is history, not a live risk. The declaration stays frozen as written; moving a SHA on a closed program is the error this repo already recorded against PSB-2's selection report. The analysis is retained because the *pattern* — a one-shot window accumulating regime contamination while a decision stays open — will recur for the next construct whose window spans 2026-08-03.

The original finding, preserved:
`governance/rfa/declarations/isd_opening_drive.py` pins TRAIN 2023-01-02 → 2024-11-30 (474 formations) and HOLDOUT 2024-12-01 → 2025-12-31 (270) — both entirely pre-CAS and clean. But **SEALED is 2026-01-01 → spend date with a floor of n ≥ 317 sessions.** Counted from the store: 2026-01-01 → 2026-07-31 supplies **144 pre-CAS sessions**, so **173 of the 317 — 55% of the eventual sealed sample — must come from post-CAS sessions.** At the observed 2026 pace (20.7 sessions/month) the floor is reached around **April 2027**. That majority-post-CAS sample would be evaluated against a construct pre-registered on pre-CAS microstructure, with `M_EXIT = 15*60+29` (`scripts/isd/battery_features.py:32`) landing on an auction print.
This is a one-shot window. It needs an explicit decision **before** it is spent: re-pin the exit, split the window at 2026-08-03, or disclose and price the regime break.

### A6 · A-index-intraday construct — **RESOLVED 2026-08-27: exit pinned at 15:14**

> **Closed.** Operator decision **D6** (commit `d33e762`) pinned the exit at the **15:14 bar close** — "last continuous print all eras, auction window untraded." That is the era-based rule this item asked for, and it is now the repo's settled convention for any index intraday exit. The A construct itself was subsequently **retired at HOLDOUT** (commit `c72fa63`: TRAIN net +1.27 bp, p 0.003; HOLDOUT net −0.22 bp, p 0.15), with SEALED untouched at 873 sessions. Only the `era_for()` certifier boundary (item A7) remains to implement.

The original finding, preserved:
`docs/reports/A_CONSTRUCT_DEFINITION.md` §3 pins the exit at the **15:29 bar close, EOD-flat**. `A_INDEX_SLICE_CERTIFICATION.md` reasons explicitly that "the native era… last bar is 15:29 — the residual ~4 bp median vs the official 15:30 close is the expected last-minute move." **That reasoning is void from 2026-08-03**: the residual is no longer last-minute drift, it is a discrete auction gap (+151 pts on 2026-08-04). Per A2 there is no volume tell on the index.
**Fix:** pin the exit at the 15:14 close (last continuous-regime print), or accept the official close with a priced auction-gap cost lane. Either way the pre-registration must state it before freeze.

### A7 · Era logic in the index-slice certifier is now two-era where three are needed
`scripts/a_index_intraday/certify_index_slice.py:179-181` hardcodes vendor era (`09:16`/`15:30`) vs native era (`09:15`/`15:29`) with the split at 2023-03-01. A third era begins 2026-08-03. The check will keep passing — bars still exist at 15:29 — while the semantics underneath it changed.

### A8 · PM feature window now contains synthetic bars
`core/analytics/day_features.py:38` sets `PM_START_BAR = 255` (13:30); the PM window runs 13:30–15:29, of which 13–14 bars are now fabricated for Cat-I names. `EXPECTED_BARS = 375` (line 40) still holds numerically but no longer means 375 tradeable minutes. These features feed the DayType facts store, which feeds **NiftyShield regime classification**.
**Verify:** NiftyShield's live entry reads the 13:00 fact, which precedes the PM window's close — so the live path is probably clean. The historical facts store used for classification is not. Confirm before relying on either.


### A9 · The index reference freezes during the auction — `underlying_ltp` stops updating at 15:15
*Added 2026-09-10.*

From **15:15** the index print stops moving: the cash auction halts continuous trading, so the index is no longer computed from live trades while options keep quoting against it. Measured on the option-chain snapshot store, distinct `underlying_ltp` values per bucket:

| session | index | 15:05–15:10 | 15:15–15:20 | 15:20–15:30 | 15:30–15:33 |
|---|---|--:|--:|--:|--:|
| 2026-09-04 | all three | 13 | 1 | 1–2 | 1 |
| 2026-09-07 | all three | 16–17 | 1–2 | 1–2 | 1 |
| 2026-09-09 | all three | 21–22 | 1–2 | 2 | 1 |
| 2026-09-10 | all three | 17–19 | 1–2 | 2 | 1 |

NIFTY, BANKNIFTY and SENSEX, four sessions, no exceptions — from 15:15 onward the reference is effectively one frozen number for the rest of the session.

**This is A1's defect in a different field.** A1 is carry-forward *bars* from a stale LTP; this is the carry-forward *index level* the derivatives book is priced against. The tell is different and there is no `is_synthetic` flag to filter on — the value simply stops changing, which is indistinguishable from a quiet tape unless you count distinct values.

**Why it is Class A and not Class B:** it has already changed a number in an analysis. `OPTIONS_WALL_CAS_AUCTION_WINDOW_ANALYSIS_2026-09-10.md` Addendum 1 concluded expiry-day decay was negative (−₹388) from a synthetic fly centred on the 15:15 print of 74,629.50. SENSEX settled near 74,900, so the fly was built ~300 points off *because the frozen reference put it there*. Addendum 2 withdrew the finding. Any study that selects a strike, computes a moneyness, or measures a "spot move" inside 15:15–15:40 is exposed the same way.

**Confirmed not affected:** option **quotes** are healthy throughout — two-sided 100.0% at every minute 15:00→15:40, median ATM relative spread 0.24% pre-auction vs 0.25–0.30% through it. Marks are trustworthy; only the underlying reference is stale. So mark-to-market, TP/SL and any clock-driven exit are clean, and `core/options_wall/paper_executor.py` is unaffected (it marks from chain mids and its time stop reads only the clock).

**Where:** anything keyed on spot after 15:15 —
- `core/options_wall/fly.py::build_iron_fly` — centres ATM and both wings on `structural.underlying_ltp`. Safe today only because `entry_end = 15:00`; **this is the blocker on any late-entry proposal** (`OPTIONS_WALL_CAS_AUCTION_WINDOW_ANALYSIS_2026-09-10.md` Addendum 3).
- `core/analytics/chain_scanner.py::_farm_screen` — the pin-proximity band `|spot − pin| / spot`.
- `core/analytics/options_analytics.py::calculate_gex` — `cr_scale = underlying_ltp²·…`, so net GEX in ₹cr and the regime classification derived from it.
- `core/options_wall/persistence.py` → `session_regime` — **rows written 15:15–15:40 carry a stale `underlying_ltp` and everything computed from it.** Treat that tail as non-market-state, not as a quiet regime.
- The `/options/wall/` dashboard, which renders those rows live.

**Fix direction:** source the reference from something that keeps trading through the auction — the option chain's own synthetic forward (put-call parity at the ATM strike), or the front-month index future, which trades to 15:40. Until then, **no consumer may treat a post-15:15 `underlying_ltp` as a live level**, and studies over that window must state which side of the freeze their spot came from.

**Verify:** the freeze boundary is the *cash* segment's, so it should track `session_schedule`'s `cash_cat1` end rather than a constant — check the pre-CAS era, where continuous cash ran to 15:30 and no such window existed.

---

## Class B — Forward-only
*Live and paper behavior from here on. No committed artifact moves.*

### B1 · `MarketHours.MARKET_CLOSE = time(15, 30)` — `core/database/utils/market_hours.py:45`
One global constant now wrong for all three segments simultaneously: cash Cat-I continuous ends **15:15** (auction to ~15:35), cash Cat-II **15:30**, derivatives **15:40**.

> **Do not simply flip this to 15:40.** `market_ingestor` gates equity aggregation on the same predicate (B4), so a 15:40 close would fabricate **ten more minutes** of carry-forward equity bars — making A1 worse. A bare flip also retroactively changes `is_market_open(historical_ts)`, which `tests/runtime/test_driver_telemetry_publish.py:104` asserts against.

**Shape of the fix:** segment-named (`cash_continuous` / `cash_auction` / `derivatives`) **and date-keyed**, following the era-schedule pattern already proven in `core/execution/equity/intraday_fees.py::_STT_INTRADAY_SCHEDULE` and the era-accurate delivery fee model. Callers then ask for the segment they mean.

### B2 · `MarketSession.SESSION_END = time(15, 30)` — `core/database/utils/market_session.py:42`
Session boundaries, `contains()`, `get_progress()`, and VWAP windows all inherit the wrong end. Same date-keyed segment treatment.

### B3 · `scripts/ingest_reference_1m.py:47-48` — `SESSION_END = time(15, 30)`, `EXPECTED_BARS = 375`
Reference-ingest session filter and bar-count expectation.

### B4 · `scripts/market_ingestor.py:285` — root cause of A1, and the F&O blind spot
Live aggregation runs only while `MarketHours.is_market_open(now)`. Two consequences: it **manufactures** the synthetic bars (it keeps aggregating through 15:15–15:30 when no ticks arrive), and it **stops at 15:30**, so the extended derivatives session 15:30–15:40 is never captured for any instrument, ever. Both halves need fixing together — extend for derivatives, stop carrying forward for halted cash.

### B5 · `scripts/nifty_shield_paper/chain_poller.py:375` — options chain stops at 15:30
Misses the 15:30–15:40 F&O window entirely, including the post-settlement window on expiry days. This is the single cheapest change that starts accumulating the only dataset any post-15:15 construct could ever be gated on.

### B6 · `core/options_wall/poller.py:182` — same gate, same gap.

> **Closed 2026-09-10.** The poller now gates on `MarketHours.is_derivatives_open()` (`poller.py:313`) and reached **15:40:02** on 2026-09-09. It is what makes the 15:15–15:40 option window observable at all — and, in doing so, exposed **A9**: the repo now collects a window whose spot reference is frozen.

### B7 · `core/runtime/driver.py:883` — telemetry `market_open` flag
Publishes `MarketHours.is_market_open(now)`; will read `False` during 15:30–15:40 while F&O is live. Coupled to the test at `tests/runtime/test_driver_telemetry_publish.py:104` — see the warning in B1.

### B8 · Order-type restrictions during CAS are not encoded anywhere
Stop-loss, IOC, iceberg, and disclosed-quantity orders are **rejected** during CAS; market orders are barred after 15:25; orders beyond ±3% of reference are not carried forward. No cash LIVE path exists today, but ISD targets exactly intraday cash equity — this must be in the order layer before any equity LIVE promotion.

### B9 · Broker MIS auto-square-off now precedes ISD's own exit
Auto-square-off for Cat-I cash moved to **~15:12** (from 15:20). ISD's battery exits at the **15:29 close**. Under a real intraday (MIS) account the broker would have force-closed the position ~17 minutes earlier. `core/execution/equity/intraday_fees.py` models the intraday fee structure but encodes no square-off timing, so nothing catches this. It is an execution-feasibility break, not just a cost error.

### B10 · `data/options/chain_cache.duckdb` is a rolling cache, not an archive
Holds only the latest snapshot (verified: 374 rows, all `2026-08-27 15:29:55`). Auction-window option behavior cannot be reconstructed retrospectively — only accumulated forward. Reinforces B5's urgency.

### B11 · 1m ingest is lagging
No `2026-08-25.duckdb` or `2026-08-26.duckdb` as of 2026-08-27; files stop at 2026-08-24. Unrelated to CAS but it is a live hole in the same store, and the EOD chain reports success regardless (the known "gating a multi-feed pipeline on one feed" pitfall).

---

## Class C — Cosmetic, labels, and documentation

- **C1** `core/database/utils/market_hours.py:6-9` docstring still states "Market open: 9:15 AM - 3:30 PM".
- **C2** `MarketHours.POST_MARKET_CLOSE = time(16, 0)` (line 47) — the cash post-close session is now 15:50–16:00, executed at the closing price. Label only.
- **C3** UI status strings will render "CLOSED" during 15:30–15:40 while derivatives trade: `flask_app/blueprints/ops/routes.py:69-76,215`, `flask_app/blueprints/nifty_shield.py:362`, `app_facade/ops_facade.py:77`.
- **C4** `core/database/providers/daily_bhavcopy.py:105,235` stamps daily bars at `time(15, 30)`; the Cat-I official close is now struck 15:30–15:35. The *value* is correct (verified above) — only the timestamp label is off.
- **C5** `core/analytics/day_features.py:33-36` carries a confused self-correcting comment block about `PM_START_BAR` (a stale value, then a correction in prose). Pre-existing; worth cleaning while A8 is being addressed.
- **C6** `CLAUDE.md` — the Data Layout section needs a CAS note so future sessions don't re-derive §0 from scratch, and `docs/reports/CAS_IMPACT_ASSESSMENT.md` should be cross-linked.
- **C7** Add a Known Pitfall: *"A bar is not a trade. Post-CAS, 13 minutes per session per F&O symbol are aggregator carry-forward (`O=H=L=C`, `volume=0`); a contiguity gate counting one bar per slot passes on fabricated data. Bar-count completeness is not tradeability."*

---

## Explicitly NOT affected — verified, so nobody re-audits them

- **All daily-close constructs**: Carry (production), TS Basis, TS Basis Daily, CB-N50, PSB-1/PSB-2, SFB-1/F1. The auction print **is** the official close (92–95% match; the remainder are Cat-II VWAP closes, which is correct pre- and post-CAS alike). No committed number moves.
- **NiftyShield v1**: structurally insulated. Its 15:15 exit now coincides exactly with the end of continuous cash, it trades **index options** which stay liquid to 15:40, and `expiry_days_min = 2` means it never holds a same-day-expiring contract — zero exposure to CAS-derived settlement. Only caveat: when the paper record is evaluated, split it at 2026-08-03, since afternoon flow character may drift as closing volume migrates into the auction.
  > **Two corrections, 2026-09-10.** The exit is **15:35**, not 15:15 — `core/execution/options/nifty_shield_exit.py:51-52` defaults to hour 15 / minute 35 — so the structure is held *through* the auction, not flattened at its start. That places it inside **A9**'s window. It appears to be handled: `nifty_shield_marks.py:233` and `nifty_shield_handler.py:657` describe a deliberate 15:29→15:35 bridge for exactly the moment the underlying stops printing. **Not re-verified here** — the exemption above should be re-confirmed against A9 rather than inherited.
- **Fee models**: CAS changed no statutory rate. STT, stamp, exchange, SEBI, and GST schedules are unaffected in both `intraday_fees.py` and `delivery_fees.py`.

---

## Suggested order of work

1. **A5** — decide the ISD SEALED window question *before* anything else. It is one-shot, it is straddling, and every day that passes adds post-CAS sessions to it.
2. **B5 / B4** — extend the pollers and ingestor to 15:40 and stop the carry-forward. Cheap, forward-only, and it starts the dataset clock. Every day not captured is gone permanently (B10).
3. **A1 / A3** — mark synthetic bars and derive PIT CAS category; this unblocks a truthful A4 amendment.
4. **A6 / A7** — settle the A-construct exit before its pre-registration freezes.
5. **B1 / B2 / B3** — the date-keyed segment schedule, done properly rather than as a constant flip.
6. **A4, A8, B8, B9** — certification amendment, feature-window repair, order-type and square-off encoding.
7. **C** — labels and docs.

---

## Amendment to `CAS_IMPACT_ASSESSMENT.md`

That memo's §3 stated the post-CAS 15:15–15:29 bars "reflect the disseminated indicative/auction values, not continuous trade." **The mechanism half of that sentence is wrong** and should be corrected: we hold no indicative data at all; those bars are aggregator carry-forward, and the move materializes as one discrete auction print.

**The §3 table itself stands.** Pre-CAS the 15:29 close sat ~4 bp from the official close (measured in `A_INDEX_SLICE_CERTIFICATION.md`); post-CAS the 15:29 close *is* the auction close. So "15:14 close → session close" measures the same statistic across the boundary and the comparison remains valid. What changed is the decomposition: fifteen minutes of continuous drift became a single gap. §4.3's poller note should likewise be sharpened — the gap is not merely that we stop at 15:30, but that what we record from 15:15 onward is manufactured.
