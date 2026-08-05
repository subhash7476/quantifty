# Structural Alpha Dossier — Round 2 (independent pass)

**Date:** 2026-08-04
**Status:** Research dossier. **No construct is authorized. No pre-registration exists. No gate has been run. No market data was read for this document.**
**Relationship to Round 1:** `STRUCTURAL_ALPHA_DOSSIER.md` (2026-08-03, commit `5d5ded1`) is a separate, independent pass on the same mandate. This document does **not** supersede it. It agrees with its framing, **disagrees with three of its top five recommendations**, identifies one concrete defect in its flagship research plan, and adds four candidates and one regulatory regime break it does not contain.
**Method:** external primary-source verification (NSE / SEBI circulars, peer-reviewed journals) scored against this repository's own accumulated failure record.

---

> ## ⚠️ REVISION 2026-08-05 — SE-1 is ABANDONED at the RFA gate. Its ranking is RESOLVED, not suspended.
>
> **The question this banner left open on 2026-08-04 has been answered, and the answer is no.** The literature check it demanded was performed, a Sharpe band was defended, frozen, and gated: **SE-1 returns ABANDON at max achievable power 0.7674 < 0.80** (`SE-1_RFA.md`; declaration `governance/rfa/declarations/se1.py`, SHA-256 `5fbf35ac…`, commit `7dd46fc`). n_required is **24** announcement clusters at the optimistic corner against **22** available; the required annualized Sharpe is **0.8375** against a defended ceiling of 0.80.
>
> **SE-1 is not ranked. It is closed.** Treat every SE-1 recommendation below as superseded by this line.
>
> Two corrections the gate made to this document's own reasoning, both worth keeping:
> - The hurdle was hand-derived as 0.810. It is **0.8375**.
> - This banner implied the calendar could not rescue SE-1. It can move it: n_required at the band ceiling is **two** more clusters (~Sept 2026), not twelve. But moving is not rescuing — reaching 0.80 at n=24 still requires the truth to sit at the very top of a band whose centre projects power ~0.50. **The revisit condition is a conjunction:** n ≥ 24 **AND** a defensible ceiling ≥ 0.8375, the latter requiring new evidence on effect size or within-cluster correlation — not a re-read of the same literature, and not a band widened because the first one abandoned.
>
> **Cost of the whole SE-1 sequence: zero market data.** No price, return, or futures data has ever been consumed for SE-1. The counting pass read MCWB membership only. The gate killed it on arithmetic, before a window was opened — the gate working exactly as designed, for the third time (after FLOW and RS-MOM).
>
> ---
>
> *The 2026-08-04 finding that produced this closure, retained as the record:*
>
> This dossier claimed SE-1 was *"the only candidate whose demonstrability arithmetic is comfortable rather than marginal"* and ranked it **#1** on that basis. **The claim is false.** Measured by `scripts/se1/count_index_events.py` (`SE1_EVENT_COUNTING_REPORT.md`, 2026-08-04):
>
> - Nifty 50 index changes 2016–2026: **66 genuine name-events** (a floor), collapsing into **22 announcement clusters**, ratio **3.0**.
> - Required `δ/sd` for two-sided power 0.80: **0.3501** at name level, **0.6264** at the honest cluster level — **≈4.7× the 0.13 claimed below**.
> - The §B.6 decision rule, pinned before the run, **triggers**.
>
> **The events are not independent** — every name added in one review shares one market environment. This is the same effective-breadth failure that gave OSC `N_eff = 1.9` against 283 nominal cells. The dossier applied that test hard to SE-3 and not hard enough to SE-1.
>
> **SE-1's rank is suspended, not reassigned.** Whether it survives turns on whether published Indian inclusion-premium effect sizes support a cluster-level `δ/sd` above 0.63 — decided **against the literature**, before any window opens. Promoting SE-2 to #1 by default would be exactly the post-hoc selection this document warns against: re-ranking after an unfavourable number, with no new positive evidence for the alternative.
>
> **The honest state of the ledger: no candidate in this dossier now has comfortable arithmetic.** Recorded as-is. Full reasoning: `SE1_AND_SPAN_LEAD_REVIEW.md`.
>
> *Corrected in the same pass:* SE-5's data verdict below said historical SPAN is unobtainable. **Partly wrong** — `archive.nseclearing.in` serves a rolling ~14-month window, and **275 settlement sessions (2025-06-19 → 2026-08-03) are now archived**. This does not make SE-5 testable; it makes its observation structure *probeable* now rather than in 2028.

---

## 0. Prior-exposure disclosure — read before using either dossier

Anyone building from this document has now read the outcomes of **ten failed or closed constructs** (O1, RS-MOM, N50-LS, FLOW, OSC, Trend, Skew, LAG, IVOL, CB-N50) plus two that reached production or de-authorization (Carry, TS Basis). **Every subsequent RFA declaration must disclose both dossiers as prior exposure.** This is exactly the contamination class that cost TS Basis Daily its windows.

Neither dossier names a parameter, threshold, lookback, or cutoff. Parameter choice belongs inside a pre-registration made *before* the relevant window is opened.

---

## 1. Where Round 1 is right

Round 1's Constraints 1–4 are correct and this pass adopts them without modification:

- `ncp = (δ/sd)·√n = S·√T`; cadence cancels; a single index P&L series needs Sharpe ≈1.30–1.50 over the 3.5-year window. Single-index and two-index timing is structurally dead.
- Delivery-equity STT (0.1% per leg, both legs) is a ~13pp/yr wall; index options (STT on premium, sell-side only) and stock futures escape it.
- The `rank_ic` cross-section escape works and is narrow.
- Its sealed-window table is accurate.

Its governing insight — *"the wall is about sample size, not signal quality"* — is the correct diagnosis and the most valuable sentence in either document.

---

## 2. Where Round 1 is wrong

Five findings. The first is the serious one.

### R1-A (CRITICAL) — the flagship VRP plan proposes confirming in a window that is mostly already burned

Round 1's top research recommendation is:

> *"Use the unread 2016–2022 Nifty options window for design… Then read 2016–2022 for design, test ONCE on 2023–2026 for confirmation."*

**Roughly six-sevenths of that proposed confirmation window has already been read, and the prior read measured the same quantity the flagship construct would measure.**

Verified at source this session (`scripts/msrp/triage_fee_impact.py`):

- Lines 36–37 pin `DEV_START = "2023-01-02"`, `DEV_END = "2025-12-31"`.
- Line 42 targets `data/market_data/options_bhavcopy.duckdb`; line 109 queries `option_bhavcopy`.
- Lines 132–274 select a nearest-strike ATM straddle on the nearest expiry and compute **long and short arms net of fees**.
- The recorded result: the **unconditional short ATM straddle netted +Rs 110K with fee drag ≈6%** (`INDEX_CONSTRUCT_DIAGNOSIS.md` §8).
- OSC's SD/breadth probe also ran on 2023–2025 by design, precisely because it was already burned and therefore cost no purity.

**Precision matters here and the span is not identical:** the triage read ends **2025-12-31**, while the options store runs to 2026-07-17. So of Round 1's proposed ~3.5-year confirmation window, **2023-01-02 → 2025-12-31 is burned and only ~2026-01 → 2026-07 is unread** — about seven months, far too short to confirm anything.

So the proposed sequence is inverted: it designs on the *clean* window and confirms on the *substantially contaminated* one — and the contaminating read is a short-straddle P&L result, i.e. the exact quantity the flagship construct would measure. A short-vol construct confirmed there is confirming on data whose short-vol outcome is already known.

The correct ordering, if VRP is pursued at all, is design on the burned 2023–2025 window and confirm once on the unread 2016-02-11 → 2022-12-31 window (1,701 dates), stating in the pre-registration that this is **backward confirmation** — defensible and standard in the literature, but weaker than forward confirmation, and it must be said in those words.

### R1-B — VRP is ranked #1 while simultaneously scored "Gate-clear? NO"

Round 1's own ranking table marks Edge 1 as failing the `per_trade_pnl` gate and then makes it the flagship program. That is internally inconsistent. It is also already adjudicated: **O1 (Nifty VRP) is WITHDRAWN** at the RFA gate — Sharpe 0.59 against 0.92 needed, via a crossed-corner artifact (`RFA_GATE_O1_REVIEW.md`). Re-proposing index short-vol requires stating what is *structurally* different, not what is differently parameterized.

There is one genuinely structural difference available, and Round 1 does not use it — see SE-7 below (the premium is **overnight**, not 24-hour; O1 tested the wrong object).

### R1-C — the VIX regime filter at #2 is contradicted by this repo's most recent experiment

Round 1 recommends volatility-weighted position sizing as a near-zero-cost win, testable "in a single afternoon."

The platform tested the **same family of overlay on a sibling construct yesterday**. The TS Basis directional-strength filter probe (commit `83b3726`, 8 configs on burned 2016–2022, fence-guarded, N_eff 10.1) included a **G1 VIX regime gate** scaling book-level exposure by `clip(vix_med/vix, …)`. Result, per the commit record: **all three gates REMOVE-or-flat at the margin and NOT stability-clear.**

That is not proof a VIX overlay fails on Carry, and this pass did not read the probe report itself — the claim rests on the commit record and the gate's stated construction. But it is direct, recent, in-repo evidence against the prior. Round 1's "costs nothing and could improve the platform's one production strategy" should be downgraded to "the same family of overlay has just been tried on a sibling construct and did not survive."

Separately: the mandate asked for **sources of alpha**. Round 1's own table marks this entry "N/A (risk management)." A non-alpha overlay ranked #2 dilutes the list.

### R1-D (minor) — Max Pain's rejection is right; the word "circular" is imprecise

Both dossiers reject max pain, so nothing turns on this. One refinement for the register: Round 1 calls it *"circular."* The max-pain **strike** is computable from the strike-level OI distribution alone, at any time before the close — it is evaluating the *prediction rule* ("spot will close there") that needs the close. The standard critique is **co-movement, not circularity**: OI clusters near spot, so the apparent predictive relation is partly reverse causality.

The rejection this pass would write: academic support for pinning is strongest for **single stocks with concentrated OI and weak for liquid indices**; much of the apparent effect is OI having clustered where price already was; and at one observation per expiry, n ≈ 500 maximum.

### R1-E — two structural changes are missing, and both invalidate parts of Round 1

Round 1's Edge 2 is entirely about **expiry-day** dynamics and its Edge 4 about term structure. Neither mentions that:

1. **The expiry day itself moved.** SEBI's May 2025 circular requires all NSE equity derivatives — weekly, monthly and long-tenor — to expire on **Tuesday**, effective **1 September 2025** (BSE moved to Thursday). Every expiry-conditioned series has a hard break there.
2. **Settlement price formation changed last week.** See §4. Any study of expiry-day or closing-price behaviour built on pre-2026 data describes a mechanism that no longer exists.

---

## 3. The scoring rubric used in this pass

Every candidate is scored on five axes, not one. Economic plausibility is necessary and **not sufficient** — this platform has killed five constructs that all had defensible economic stories.

1. **Mechanism** — who is *forced* to trade, why, who is paid, who pays.
2. **Observation structure** — which escape is claimed:
   - **Escape A — a genuine cross-section.** `rank_ic` over N simultaneous units; sd_IC 0.15–0.25 rather than a P&L series' unit sd. CB-N50 reached ncp 6.95 / power 1.00 at n = 887 this way.
   - **Escape B — a genuinely high Sharpe.** Rare and dangerous: **the noncentral-t framework does not penalize negative skew.** A short-tail construct can pass the gate on a Sharpe that is payment for a tail it has not yet paid. Flagged wherever it applies.
   - Anything reducing to one-number-per-period without Escape B is **demonstrability-blocked**, regardless of story quality.
3. **Effective breadth, not nominal.** OSC had 283 nominal cells/day and **N_eff = 1.9** (PC1 = 61%). Nominal unit count is not evidence of breadth.
4. **Does an unread confirmatory window exist?** The scarcest resource, and the mandate cannot know its state. §5 inventories it.
5. **Independent-researcher accessibility.** This **inverts** the usual ranking. Latency, queue, colocation and order-book edges are structurally unavailable. Slow, capacity-constrained, data-assembly-heavy, event-driven edges are *more* available precisely because a large fund cannot deploy into them.

---

## 4. The regime break neither dossier had priced — CAS

Not a candidate. A correction to the premise of every expiry- and close-conditioned study on this platform, and it is one week old.

- **1 Sept 2025** — SEBI's May 2025 circular takes effect: all NSE equity derivatives expire **Tuesday**; BSE Thursday. ([circular coverage](https://www.5paisa.com/news/sebi-reshuffles-equity-derivatives-expiry-days-to-streamline-trading))
- **2026** — NSE launches the **Closing Auction Session**, **15:15–15:35**, for eligible cash-market securities. The close is now an **equilibrium price** — the price maximising executable volume, market orders ahead of limit orders — with reference price from the **15:00–15:15 VWAP** and a **±3% band**. Only limit and market orders; no stop-loss, no iceberg. ([NSE CAS](https://www.nseindia.com/static/products-services/closing-auction-session), [NSE circular CMTR73362](https://nsearchives.nseindia.com/content/circulars/CMTR73362.pdf))
- **3 Aug 2026** — NSE extends the F&O close from 15:30 to **15:40** to align with CAS; the derivatives VWAP window moves from 15:00–15:30 to **15:10–15:40**. ([Groww](https://groww.in/blog/nse-extends-f-and-o-trading-hours-by-10-minutes-new-timings-effective-from-august-3-2026), [Anand Rathi](https://anandrathi.com/blog/nse-extends-trading-hours))
- **Already visible:** because constituents now close via a separate auction order book while index futures keep trading, index close and futures close are formed by different mechanisms. NSE has had to publicly explain a Nifty / Bank Nifty spot-futures divergence caused by exactly this ([Business Today, 4 Aug 2026](https://www.businesstoday.in/markets/stocks/story/why-are-nifty-and-sensex-moving-opposite-nse-explains-closing-auction-session-547012-2026-08-04)).

**Three load-bearing implications:**

1. **Index derivative settlement is now downstream of a call auction.** Final settlement references the index close → constituent closes → auction prints. Historical expiry-settlement studies describe a dead mechanism.
2. **Every closing-price-referenced basis, carry and index-arb series breaks in 2026.** Carry is production-ready and its entire research record is pre-CAS. This does not invalidate it — but the parity gate that showed **+0.0 bp** reproduction was measured against a settlement convention that has since changed, and that should be said out loud before capital is committed.
3. **SE-1's execution point moved.** Index-reconstitution trades print at the effective-date close, which is now a volume-maximising auction with a ±3% band. Same trade, different execution model.

**Verdict on CAS itself: untestable now (no history), mandatory to monitor.** Revisit in 2028.

---

## 5. Confirmatory-window inventory

| Window | Universe | State |
|---|---|---|
| 2023-01 → 2026-07 | ~180-name SSF cross-section (monthly) | **SPENT** — Carry PASS, TS Basis de-authorized, IVOL FAIL |
| 2023-01 → 2026-07 | **Nifty 50 constituent daily cross-section** | **PRESERVED, UNREAD** (CB-N50 declined G4) |
| 2016-02-11 → 2022-12-31 | **NIFTY index options, 1,701 dates, ~4.12M rows** | **UNREAD** — OSC abandoned without spending it |
| **2023-01-02 → 2025-12-31** | **NIFTY index options** | **BURNED** — MSRP triage; short-ATM-straddle P&L known (see R1-A) |
| 2016–2019 / 2020–2022 | Nifty 50 constituent daily | BURNED (CB-N50 TRAIN + HOLDOUT) |
| 2016–2022 | SSF cross-section | BURNED (Carry, TS Basis, IVOL, Trend, Skew, LAG) |
| **Event-time (index reviews, expiry rolls, margin changes)** | — | **NEVER CONSTRUCTED — nothing burned** |
| BANKNIFTY options 2016–2026 | — | **Not ingested** — one filter change in `scripts/msrp/ingest_option_bhavcopy.py` |

The last two rows are this inventory's real finding. **Every construct this platform has attempted is a calendar-time panel over the same two universes.** Event-time is an unexplored axis and does not consume calendar-window purity the same way.

---

# Part I — Surviving structural edges

Seven survived rejection. The mandate asked for a Top 10 and simultaneously said *"if there are only five, produce five — reject weak ideas."* Padding to ten would be the failure mode it warned against. Twelve rejections are on the record in Part II.

---

## SE-1 — Forced passive rebalancing flow (index reconstitution) — **✗ CLOSED, ABANDON at the RFA gate 2026-08-05**

> **Read this section as history.** SE-1 was gated on 2026-08-05 and returned **ABANDON** — max achievable power **0.7674** < 0.80, n_required **24** announcement clusters against **22** available (`SE-1_RFA.md`; declaration SHA-256 `5fbf35ac…`). Everything below describes the mechanism accurately and none of it is retracted; the construct died on **demonstrability at n=22**, not on the mechanism, the data, or the accessibility. Note in particular that §E below judged the observation structure the best in the dossier — **that judgement was wrong**, and the counting pass is what proved it.

*Overlaps Round 1's Edge 8, which ranked it #4. This pass ranked it #1 and disagreed on what the hard part is — and was wrong about the hard part. The hard part was n.*

### A. Description
Index providers publish constituent changes on a **pre-announced schedule with a pre-announced effective date**. NSE Indices reviews the Nifty 50 semi-annually on data through 31 January / 31 July, effective the last trading day of March / September, with **four weeks' prior notice** ([NSE methodology](https://archives.nseindia.com/content/indices/ind_nifty50.pdf), [Bajaj AMC](https://www.bajajamc.com/knowledge-centre/nifty-50-rebalancing)). MSCI reviews quarterly (Feb/May/Aug/Nov), effective roughly 10–21 days after announcement ([Marketcalls](https://www.marketcalls.in/investment/msci-rebalancing-explained-a-comprehensive-guide-for-indian-investors-and-traders.html)). Every benchmarked fund must transact the change, at the effective-date close, in the size the index dictates, irrespective of price.

### B. Economic mechanism
- **Who is forced:** index funds and ETFs. Passive AUM in India was **₹9.8 lakh crore at Feb 2025 with 73% tracking Nifty indices** ([NSE Nifty Passive Insights Q1 2025](https://www.niftyindices.com/Nifty_Passive_Insights/Nifty%20Passive%20Insights%20Quarterly%20update%20-%20January%20to%20March%202025.pdf)), crossing **₹15 lakh crore by Feb 2026** ([Finnovate](https://www.finnovate.in/learn/blog/how-to-select-and-build-a-strategy-around-passive-funds)). Their mandate is tracking error, not return. A fund buying the addition at a bad price *at the index price* has zero tracking error; buying it cheaply three weeks early creates tracking error. **The incentive is explicitly anti-alpha.**
- **Who profits:** whoever warehouses inventory between announcement and effective date, and supplies liquidity into the effective-date auction.
- **Who loses:** end holders of passive funds, via implementation shortfall — the "hidden costs of passive investing" ([arXiv 2506.21775](https://arxiv.org/pdf/2506.21775)).
- **Documented in India:** event studies report positive abnormal returns and volume spikes on Nifty additions, negative on deletions, **fading within ~60 days** — a temporary price-pressure effect, exactly what a liquidity-provision story predicts and not a permanent revaluation. FIIs react faster than domestic mutual funds ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1042444X20300049)).

### C. Persistence
Partly arbitraged — US inclusion premia have compressed since the 1990s and Indian effect sizes should be assumed decaying. But the mechanism can be *priced*, not removed, because the forced side is structurally price-indifferent and its size compounds with passive AUM (~32% CAGR). **What limits it is capacity, not competition** — which is exactly why it is available to a small researcher and unattractive to a large fund.

### D. Required data
| Item | Source | Availability | Cost |
|---|---|---|---|
| NSE index-change **announcements** (date, index, adds, drops) | NSE Indices press releases / circular archive | Public; requires **hand-assembly into an event calendar** | ₹0 + labour |
| MSCI / FTSE India review announcements | Provider announcements | Public; historical depth is the weak link | ₹0–low |
| Daily OHLCV for affected names | **On hand** — `equity_bhavcopy_adjusted`, 7,052,381 rows | On hand | ₹0 |
| Single-stock futures (execution leg) | **On hand** — FUTSTK 2016-02-11 → present, 363 underlyings | On hand | ₹0 |
| PIT index membership | **On hand** — `scripts/csmp/build_universe.py`, `symbol_entity_intervals`, NSE MCWB PIT (CB-N50) | On hand | ₹0 |

**Where this pass disagrees with Round 1.** Round 1 lists the missing item as *"Nifty 50 historical composition — available from NSE Indices."* Composition is the easy half. The hard half is the **announcement date**, and it is the half that determines whether the study is look-ahead-free. The effective date is not admissible as the information timestamp; neither is the review data cut-off. Only the contemporaneous announcement is, and it must be sourced from the announcement itself rather than a later summary that has been revised.

**Survivorship (severe, specific):** the construct is an event study on *changes* in membership. Reconstructing history from today's list is fatal look-ahead.

**Corporate-action interaction:** additions and deletions cluster around exactly the events (demergers, ISIN re-issues, ticker recycling) that CLAUDE.md records as having produced fabricated adjusted returns three separate ways. The four-arm contract suite exists for this and must be run on the event panel.

### E. Testability
> **SUPERSEDED 2026-08-04 — measured, and the original claim was wrong. Retained below as the record of the error.**
>
> **Measured:** 66 genuine Nifty-50 name-events (a floor) in **22 announcement clusters**. Because names inside one review share a single market environment, the honest unit is the **cluster**: `√n = 4.69`, required **`δ/sd` = 0.6264** — not 0.13. At name level it is 0.3501. Nifty Next 50 is worse on ratio (278 events / 33 clusters = 8.4).
>
> **Testability verdict now:** testable, **marginal, not comfortable**. It survives only if published Indian inclusion-premium effect sizes support a cluster-level `δ/sd` above 0.63. That must be argued against the literature *before* a window opens, and the observation unit must not be re-derived after seeing the number.
>
> **Do not pool Nifty 50 with Next 50 to raise `n`.** A name dropped from the 50 is typically added to the Next 50 in the same review — one event, two rows, opposite-signed and partially offsetting flow. If both are used the unit is the *entity-review*, not the index-membership row.
>
> **Announcement-date sourcing:** coverage is 13.6% (9/66) programmatically, but at cluster resolution only **~22 dates** are needed, and 58 of 66 events are scheduled reviews with a published four-week notice convention. This is a day of work, not a wall.

*Original claim, falsified:* **Testable, and the arithmetic is comfortable rather than marginal — the only candidate here of which that is true.** Each review is a set of name-events: ~20 NSE semi-annual reviews and ~40 MSCI reviews over 2016–2026, at a handful of names each → on the order of **several hundred name-events**. As `per_trade_pnl` with n in the hundreds and an event effect measured in whole percent against a per-event sd of a few percent, `δ/sd` need only be ≈0.13 at n = 450 to reach ncp 2.80. Published event studies routinely exceed that ratio.

The declaration must use `per_trade_pnl` (Sharpe band + cadence, per RFA contract v2) and anchor the Sharpe band on **published Indian event-study effect sizes**, not on a read of this platform's data.

### F. Expected half-life
**Years to decades for the mechanism; years for any given effect magnitude.** Expect the per-event premium to shrink while the number and size of events grows.

### G. Implementation difficulty
**Medium.** A few name-level positions held for weeks, expressed in single-stock futures to avoid the delivery-STT wall. Execution risk concentrates at the effective-date close — now the **Closing Auction Session** (§4), a mechanism that did not exist before 2026.

### H. Research priority
**SUSPENDED (was 1).** The mechanism, the untouched event-time axis, the absence of any data purchase, and the capacity limit all still hold. **The demonstrability claim does not** — required `δ/sd` is 0.6264 at the honest cluster unit, not 0.13. Rank is restored, lowered, or withdrawn only after the literature check on cluster-level effect size.

---

## SE-2 — Compensated liquidity provision in the Nifty 50 constituent cross-section

*Not in Round 1. This is the CB-N50 signal, separated from the execution vehicle that killed it.*

### A. Description
Price-insensitive demand arriving in a constituent — SIP-funded DII buying, FII risk-appetite reallocation, index-fund flow — moves that name away from its peers, and the move partially reverts as inventory redistributes. The compensation for absorbing it is a short-horizon cross-sectional reversal in the constituent panel.

**This platform has already measured it.** CB-N50 recorded a daily cross-sectional rank IC of **+0.029 out-of-sample** on 2020–2022 HOLDOUT (NW t = 4.4, p < 0.00002), from reversal and basis features, on official NSE MCWB point-in-time membership. Its TRAIN finding was that daily "momentum" **is** reversal (IC −0.02) — the sign of a liquidity-provision effect, not continuation.

### B. Economic mechanism
- **Who is forced:** SIP-funded mutual funds deploy on a fixed calendar with no view on entry price; FIIs reallocate on global risk appetite, not Indian relative value; index funds buy the index, not the name. All three are price-insensitive demand shocks distributed unevenly across constituents.
- **Who profits:** whoever takes the other side and warehouses inventory for days. **Who loses:** the flow originator, in implementation shortfall.
- This is the canonical "evaporating liquidity" mechanism. Reversal here is the *observable consequence* of an inventory cycle — not an indicator. The mechanism predicts both its sign and that it strengthens when flow is larger and liquidity thinner, which is a falsifiable conditional, not a fitted parameter.

### C. Persistence
**Weakest persistence case in the dossier, stated plainly:** short-horizon reversal is the most competed-for effect in systematic equity. It survives only because inventory risk is real — the liquidity provider genuinely can lose, which is why the payment exists. It would **not** survive unlimited institutional participation; capital allocated to it is bounded by the risk it must warehouse. In India it is additionally protected by SIP flow growth.

### D. Required data
Everything is **already in the repository**: `equity_bhavcopy_adjusted` (certified, four-arm contract suite), FUTSTK 2016–2026 for the execution leg, official NSE MCWB PIT membership (CB-N50 substrate cert, 0.024% miss rate), and the CB-N50 harness. **No acquisition, no cost, no unrepaired survivorship gap.**

### E. Testability — and the metric question that decides it
- N50-LS was gated as `per_trade_pnl` → **ABANDON at max power 0.7466**.
- CB-N50 was gated as `rank_ic` → **power 1.00**.

Same book. The difference is whether the primary hypothesis is *stock-level cross-sectional prediction* (rank_ic legitimate) or *index timing under a stock-level veneer* (rank_ic illegitimate — CB-N50's own binding constraint #3). For a book that is genuinely long and short 50 names and never expresses an index view, **rank_ic is the honest primary hypothesis**. CB-N50 died because it chose an index-futures execution vehicle whose directional check was known to fail — not because the signal failed.

The rebuttal that must be answered *in the pre-registration, before the read*: if the P&L series is what the researcher will live on, `per_trade_pnl` is what must clear — and it did not (0.7466). **A rank_ic PASS with a per_trade_pnl FAIL is a real possible outcome and means "the cross-sectional prediction is demonstrable but the resulting P&L is not."** Declare what that outcome triggers before opening the window.

**Effective-breadth risk: low.** Unlike OSC, the units are 50 separate companies, not 50 strikes on one underlying. The platform's own evidence supports this: Carry↔IVOL signal ρ = **−0.04**. Name-level cross-sections in this universe genuinely decorrelate.

**Confirmatory window:** the Nifty 50 constituent daily **2023–2026 sealed window is PRESERVED and UNREAD** — the only clean confirmatory window a constituent-level construct has.

**Effect-size anchor (load-bearing):** the honest δ is HOLDOUT **+0.029**, not TRAIN +0.059. The IC halved out of sample. This is the "SD must be independently defended, not inherited from a short in-sample read" lesson that retired C2.

### F. Expected half-life
**Years, decaying.** Assume continuous erosion.

### G. Implementation difficulty
**High.** Daily-rebalanced 50-name L/S at retail scale is operationally demanding and fee-constrained. Delivery equity is out. Single-stock futures are the only viable venue and only ~40 of the Nifty 50 are reliably liquid there. Banded rebalancing and turnover control are mandatory.

### H. Research priority
**2.** Highest probability that a real effect exists (already measured OOS), against the worst persistence and hardest implementation.

---

## SE-3 — Index-versus-constituent implied correlation (dispersion premium)

*Not in Round 1. Round 1's Edge 4 (term structure across ~4–8 tenors of one underlying) is a different and much narrower object — and it inherits OSC's breadth problem, since all tenors share one underlying's vol level.*

### A. Description
Index option implied volatility embeds an implied correlation among constituents. When index-option demand systematically exceeds single-stock-option demand, index implied vol is bid relative to the vol of its parts, and implied correlation trades above subsequently realized correlation. Harvested by selling index vol against constituent vol — or, cross-sectionally, by ranking constituents on how rich their own options are relative to what index-implied correlation says they should be.

### B. Economic mechanism
- **Who creates it:** concentrated one-directional demand for *index* optionality — unusually extreme in India. Retail trading is **concentrated in and dominates index options**, specifically NIFTY 50 and BANKNIFTY ([Agarwal, Ghosh, Prabhala & Zhao 2025](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5430635)). NSE data put roughly **one-third of index-option turnover with retail and about one-half with proprietary desks acting as market makers**. There is no comparable retail demand for single-stock options.
- **Who profits:** the dealer short index vol and long constituent vol, who therefore bears **correlation risk** — the risk that in a crash everything moves together and the hedge fails exactly when needed.
- **Who loses:** index-option buyers, paying for a correlation assumption that is usually too high.
- This is a risk premium in the strict sense — compensation for a genuinely undesirable risk — not a mispricing.

### C. Persistence
**Strong.** It persists in every major market studied, decades after documentation, because the risk is real and the demand imbalance structural. It survives institutional participation — institutions *are* the sellers. Additionally protected here by a demand source regulators have actively tried and failed to suppress (SE-6).

### D. Required data
| Item | State |
|---|---|
| NIFTY index options, 2016-02-11 → 2026-07, 5,490,319 rows | **On hand** |
| Stock options (OPTSTK) bhavcopy, **98,320,092 rows, 2016-02-11 → 2026-07-20, 363 underlyings** | **On hand, ingest verified complete** |
| PIT Nifty 50 membership + weights | On hand (MCWB) |
| BANKNIFTY options | **Absent by ingest filter, not by source** — recoverable |

Resolution is **daily EOD only, and that is sufficient**: Bakshi & Kapadia (RFS 2003) and Goyal & Saretto (JFE 2009) both compute delta-hedged option returns on daily EOD rebalancing. `INDEX_CONSTRUCT_DIAGNOSIS.md` §6 already records that this platform's earlier "delta-hedging needs intraday data" NO-GO was **stricter than the literature requires**. (Round 1's data-gap table repeats a softer version of that same over-strictness for Edge 1.)

**Survivorship:** F&O eligibility changes over time; the constituent option panel must be built on point-in-time eligibility.

### E. Testability
**Testable, with one unknown that decides everything.**

The index-level dispersion trade (index vol vs a basket) is **one number per day → blocked.** Reject in that form.

The cross-sectional form claims Escape A. **Effective breadth is the open question**, and the honest prior is *better than OSC, worse than nominal*: OSC collapsed to N_eff 1.9 because 283 cells shared one underlying's vol level; here the units are 50 different companies with idiosyncratic vol, and ρ = −0.04 says name-level signals decorrelate in this universe. But a market-wide vol shock still moves all 50 constituents' options together. **Breadth collapse is a live risk that must be measured before any declaration** — an N_eff / sd_IC probe on the burned window, exactly as `OSC_SD_PROBE_PROMPT.md` prescribed. Carry forward the **dispersion only**; the measured IC mean must not become the δ anchor.

**Prior exposure:** the Skew sleeve (risk-reversal) already read TRAIN and FAILED (IC −0.018, t = −1.15). The stock-options TRAIN surface is partly burned for option-cross-section work. Dispersion is a different quantity from skew; the exposure is still real and must be disclosed.

### F. Expected half-life
**Decades.** Of everything here, the mechanism most likely to be intact in 2040.

### G. Implementation difficulty
**Very High.** Simultaneous index and single-stock option positions, delta hedging, and continuous management of a short-tailed correlation exposure. **Escape-B's warning bites hardest here: a dispersion book reports an attractive Sharpe until correlation goes to one, and the noncentral-t gate will not see that.**

### H. Research priority
**3.** Best mechanism, worst implementation, one unmeasured breadth number standing between it and a declaration. The probe is cheap — run it before anything else on this candidate.

---

## SE-4 — Expiry mechanics: physical delivery and the forced roll in single-stock derivatives

*Not in Round 1. Distinct from Round 1's Edge 2, which is about index dealer gamma; this is about single-stock delivery obligation.*

### A. Description
Indian single-stock derivatives are **physically settled**. A holder of an ITM stock option or stock futures position into expiry must take or make delivery of the underlying at full notional, with delivery margins levied progressively across the expiry week. Anyone unable or unwilling to fund delivery must close or roll before the deadline. The deadline is known, the position size is observable (open interest), and the constraint binds hardest on those least able to fund it.

Since **1 September 2025** the clock has moved to **Tuesday** for all NSE equity derivatives — a hard regime boundary in every expiry-conditioned series.

### B. Economic mechanism
- **Who is forced:** holders of ITM stock options and stock futures who cannot fund delivery — disproportionately leveraged retail and small proprietary books. The forcing is a **funding constraint**, entirely unrelated to expected return.
- **Who profits:** whoever supplies liquidity into the roll and can fund delivery, or source stock via Securities Lending and Borrowing (live since 2008; **253 eligible securities as of Sept 2023**, tenures 1–12 months — [NSE SLB](https://www.nseindia.com/market-data/securities-lending-and-borrowing)).
- **Who loses:** the constrained holder, transacting on a deadline rather than a price.
- Pressure should scale with **open interest relative to deliverable float** — names where the derivative position is large against the shares actually available are where squeeze mechanics bind. That is a falsifiable cross-sectional prediction, stated before any data read.

### C. Persistence
**Durable.** The forcing is regulatory (mandatory physical settlement, phased from October 2019) and the funding constraint is a real balance-sheet limit, not an error. Institutional participation compresses the premium but cannot remove the constraint, because the constrained party is *defined* by not having the balance sheet.

### D. Required data
| Item | State |
|---|---|
| FUTSTK bhavcopy incl. OI, 2016-02-11 → 2026-07-20, 363 underlyings | **On hand** |
| OPTSTK bhavcopy incl. strike-level OI, 98.3M rows | **On hand** |
| Spot / adjusted equity panel | **On hand** |
| Deliverable quantity / delivery percentage | Partial — `deliv_pct` begins 2020-01-01 (the constraint that limited C2) |
| Free float | Derivable from MCWB PIT weights |
| SLB borrow rates / availability history | **Not on hand.** NSE publishes daily; historical depth **unverified** |
| Expiry calendar with the Sept-2025 Tuesday break | Constructible; **the break must be modelled, not smoothed** |

### E. Testability
**Testable, second-best observation structure in the dossier.** The natural unit is a **name-expiry event**: ~180 F&O names × 12 monthly expiries × 10 years ≈ **2,000+ events** for `per_trade_pnl` (√n ≈ 46, requiring δ/sd ≈ 0.06 — modest); or ~120 expiry formations for `rank_ic` across names (√n ≈ 11, requiring δ ≈ 0.038 at sd 0.15 — demanding). **The event framing is materially stronger; the pre-registration should choose `per_trade_pnl` on name-events.**

Two hard regime boundaries must be **pre-declared, not discovered**: October 2019 (physical settlement phase-in) and September 2025 (Tuesday expiry).

Prior exposure: the SSF 2016–2022 panel is burned for basis-family work. This construct uses OI, delivery obligation and the expiry clock — different quantities on the same substrate. Disclose; do not pretend it is clean.

### F. Expected half-life
**Decades for the mechanism** (written into settlement rules); **years for any magnitude**, because the regulator keeps changing the clock. Every rule change resets the estimate.

### G. Implementation difficulty
**Medium.** Single-stock futures/options held days. The real difficulty is that the trade concentrates at exactly the moment liquidity is worst.

### H. Research priority
**4.** Genuine forced-trade mechanism, genuine event cross-section, data mostly on hand. Ranked below SE-1 mainly because the effect size has no published Indian anchor and the regime breaks are severe. **Revised 2026-08-05:** SE-1 is now closed at the gate, and the comparison inverts on the axis that decided it — SE-4's ~2,000 name-expiry events against SE-1's 22 clusters. The missing Indian effect-size anchor and the two regime breaks are still real and still unaddressed, so this is **not** an automatic promotion; it is a note that the reason SE-4 sat below SE-1 no longer holds.

---

## SE-5 — Margin-regime shocks as exogenous forced deleveraging

*Not in Round 1. Included partly because the mandate explicitly asks which ideas need data we do not possess, and this is the cleanest example.*

### A. Description
NSE Clearing publishes SPAN risk parameter files setting margin per contract. When scanning ranges or volatility scans rise — mechanically after volatility spikes, discretionarily around events — every leveraged holder of that contract faces an immediate funding demand and must post or reduce. The margin change is **dated, exogenous to the individual holder, and observable at contract level**.

### B. Economic mechanism
- **Who is forced:** leveraged holders, at a moment chosen by the clearing corporation rather than by them.
- **Who profits:** unlevered capital absorbing the forced reduction. **Who loses:** the levered holder, deleveraging into a market that has read the same margin file.
- The mechanism is unusually clean because the trigger is a **published rule applied to a published input**, not a participant's judgement — one of very few genuinely exogenous forced-trade instruments in this market.

### C. Persistence
**Durable.** SEBI's peak-margin and upfront-collection regime has tightened the constraint over five years. Unlikely to be arbitraged away, because the forced party is defined by insufficient capital.

### D. Required data — **archive now exists (forward collection started 2026-08-04)**
| Item | State |
|---|---|
| Historical daily NSE SPAN risk parameter files | **On hand for a ~14-month rolling window** — archive activated 2026-08-04 (`SPAN_INGEST_ACTIVATION_REPORT.md`). 275 settlement snapshots, **2025-06-19 → 2026-08-03**, backfilled from the NSCCL archive endpoint the same day. Not a research panel yet — see §E. |
| Contract-level OI panel to measure who was affected | On hand |
| Margin-rule change circulars | Public; hand-assembly |

**Correction recorded (lead review CRITICAL-1):** the earlier claim here — *"NSE Clearing publishes SPAN files for the current day; historical daily archives are not distributed at retail scale"* — was falsified by probing. The market-reports SPA *lists* current + previous day, but the date-path URL *serves* a rolling ~14-month window. ~280 sessions were retrievable at activation and have been preserved; the trailing edge decays ~1 session/day. The discipline that applies to any absence claim applies here too: **probe before recording absence.**

### E. Testability
**Testable in principle; 14 months of panel now exist and are not enough.** The construct is well-specified — margin-change events × contracts is a large event cross-section — and remains short of a research panel. The SE-1 lesson applies with more force here: a volatility spike moves scanning ranges across every contract simultaneously, so nominal contract-events will vastly exceed effective ones; the effective-breadth probe is the first thing the backfilled window buys, not a margin-change detector. Proxying margin changes from realized volatility reintroduces exactly the indicator-fitting the mandate rejects: the point of SPAN is that it *is* the rule, not a reconstruction of it.

### F. Expected half-life
**Decades** — the panel is growing from 2026-08-04 onward.

### G. Implementation difficulty
**High**, and not assessable in detail without data.

### H. Research priority
**5.** **DONE (2026-08-04): the daily SPAN archive is live and the ~14-month retrievable window is backfilled.** The job runs in the daily chain with an asserted freshness condition. The next SE-5 step — and the only one the panel supports — is the effective-breadth probe on the ~275 backfilled snapshots, to learn the observation structure now instead of in 2028. No SE-5 construct is authorized.

---

## SE-6 — Retail lottery demand in index options (mechanism strongest, measurement blocked)

*Overlaps Round 1's Edge 5, which ranked it #6 and blocked it on missing broker data. This pass agrees it is blocked and disagrees about why — the blockage is structural, not a data-purchase problem.*

### A. Description
Indian retail traders buy short-dated, far-OTM index options in extraordinary volume and lose money doing it, systematically and at scale. This is the largest, best-documented, most economically legible wealth transfer in any equity market in the world today.

### B. Economic mechanism
The numbers come from the regulator and are not in dispute:

- **91% of individual traders lost money** in equity derivatives in FY2024-25; aggregate net losses **₹1,05,603 crore**, up **41% YoY** from ₹74,812 crore; ~**9.6 million** individual investors studied; average loss **₹1.1 lakh** ([SEBI study, July 2025](https://www.business-standard.com/markets/news/net-losses-of-traders-in-fo-widens-in-fy25-sebi-study-125070701221_1.html), [ICICI Direct](https://www.icicidirect.com/share-market-today/news/sebi-sees-dip-in-derivatives-turnover,-91percentage-of-retail-traders-lose-money-in-fy25/1615620)).
- India accounts for roughly **78% of equity options contracts traded worldwide** ([FIA](https://www.fia.org/marketvoice/articles/premium-turnover-indian-options-hits-150-billion)).
- Roughly **one-third of NSE index-option turnover is retail; about one-half proprietary market makers; under one-tenth foreign.**
- The academic record names the counterparty explicitly: retail concentrates in and dominates index options, day-trades heavily, takes short-duration directional bets into 0DTE, and **"the aggregate losses borne by retail investors are the aggregate profits of the institutions"** ([Agarwal, Ghosh, Prabhala & Zhao 2025](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5430635)).

**Who creates it:** lottery preference plus financial constraint — cheap far-OTM weeklies are the only instrument offering a life-changing payoff on a small account. **Who profits:** proprietary market makers. **Who loses:** retail, permanently and measurably.

### C. Persistence
**Strongest persistence case in the dossier, and it is empirical rather than theoretical.** SEBI has attempted suppression: lot-size increases, upfront premium collection, intraday position monitoring, mandatory loss disclosure at broker login, expiry-day rationalisation. The academic finding is that these were **offset by migration to smaller-ticket, riskier options** — the behaviour re-routed rather than stopped, and losses *rose 41%* in the year the measures landed. A behaviour that survives a determined regulator will not be arbitraged away by competition; competition is the thing collecting it.

### D. Required data
| Item | State |
|---|---|
| Participant-wise OI (FII / DII / Pro / Client, long & short, across index fut, index call, index put, stock fut, stock call, stock put) | Published **daily and free** by NSE, ~5–6 pm, later on expiry days ([NSE All Reports – Derivatives](https://www.nseindia.com/all-reports-derivatives)). **Not currently ingested.** |
| Strike-level index option OI and volume | **On hand** |
| Client-level trade panel | **Fundamentally unobtainable** — the academic result rests on a regulator-provided market-wide panel |

### E. Testability — why it does not rank first
The mechanism is beyond doubt. **The observation structure is fatal**, and the failure is worth stating precisely because it is counterintuitive:

- Participant-wise OI is **four categories × six instrument buckets, aggregated across all underlyings** — not per-name, not per-strike. Applied to Nifty it is **one number per day** → `per_trade_pnl` on a single series → the Sharpe-1.50 wall. The platform has already killed a construct in this family: **FLOW, ABANDON, max power 0.6053.**
- The price-side expression — "sell the overpriced lottery corner of the surface" — is a *spread*, also one number per day. Ranking richness across surface cells to manufacture a cross-section **is OSC**, which died at N_eff 1.9, δ +0.0167, sd_IC 0.2502.
- The client-level panel that makes the academic result possible is available to a regulator and to nobody else.

**So the largest identified wealth transfer in world equity markets is, for this platform, not demonstrable.** That is not a claim it cannot be captured — market makers capture it daily. It is a claim that capturing it requires *being* a market maker: queue position, latency, quoting obligations, capital. That is the capability an independent researcher does not have, and it is a stronger and more permanent blockage than Round 1's "broker data is proprietary."

The one non-blocked use is as a **conditioning variable** on an already-validated cross-sectional sleeve — and note the platform tested a structurally similar idea *yesterday* (TS Basis gate-stability probe, commit `83b3726`) and found all three gates REMOVE-or-flat at the margin and not stability-clear. Conditioning gates have a poor record here.

### F. Expected half-life
**Decades for the phenomenon.** Indefinite for the blockage.

### G. Implementation difficulty
**Very High / structurally unavailable.**

### H. Research priority
**6 as a research target; 1 as context.** It is here to be *understood*, not pursued — it explains who is on the other side of every index-option trade in India, and that should inform the sign and sizing of everything else.

**One cheap action it justifies:** ingest the free daily participant-wise OI file starting now. It is not a signal; it is the only observable proxy for the largest flow in the market.

---

## SE-7 — The overnight-segmented volatility risk premium, and the GIFT Nifty change

*This is the structural difference Round 1's Edge 1 needed and did not have. O1 tested VRP as a single 24-hour object; the literature says that is the wrong object.*

### A. Description
The volatility risk premium in Indian index options is **not evenly distributed across the day**. Bhat et al. (2024), *Journal of Futures Markets* 44:1320–1337, ["The asymmetry in day and night option returns: Evidence from an emerging market"](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512), find **positive and significant overnight** option returns accompanied by **negative intraday** returns on Nifty options, and conclude the variance risk premium earned by option sellers is **mainly a reward for overnight risk**. Put risk premia are significantly negative overnight, when the exchange is closed and continuous delta-hedging is impossible, and align with the risk-free rate intraday when hedging is feasible.

Separately, the hedging instrument for that exact risk arrived: **GIFT Nifty replaced SGX Nifty on 3 July 2023**, trading ~21 hours a day across two sessions on NSE International Exchange, USD-settled, accessible to FPIs, NRIs and eligible foreign investors ([transition detail](https://www.bajajamc.com/knowledge-centre/sgx-nifty)).

### B. Economic mechanism
- **The risk is genuine and un-hedgeable in the domestic session.** The Indian cash market is closed ~17.75 hours a day; an option seller cannot rebalance a delta through the gap. Gap risk is undesirable, un-diversifiable at index level, and therefore compensated. A risk premium in the strict sense.
- **Who profits:** whoever can bear or offset overnight gap risk. **Who loses:** participants mandated or constrained to be flat overnight.
- **The structural change:** the premium was established when the risk could not be hedged during the Indian night. GIFT Nifty now trades through it — **but only FPIs, NRIs and EFIs can access it.** A domestic researcher cannot. That access asymmetry is the segmentation keeping the premium alive, and the reason this is *not* an edge available to the researcher who most wants it.

### C. Persistence
**Decades for the premium.** The access asymmetry is a policy variable that could change at any time; if domestic participants gain routine access to a 21-hour Nifty future, the overnight premium should compress. A regulatory event to watch, not a modelling assumption.

### D. Required data
| Item | State |
|---|---|
| NIFTY index options daily EOD | **On hand**, 2016–2026 |
| **Intraday option prices** (to separate day from night returns) | **NOT ON HAND — the binding gap.** The entire construct is a within-day decomposition. |
| GIFT Nifty (and pre-2023 SGX Nifty) history | **Not on hand.** Separate venue, separate feed, likely paid. |
| Regime split at 3 July 2023 | Mandatory — different venues, participant sets and hours |

### E. Testability
**Not testable on current data.** The claim is an intraday-versus-overnight decomposition; EOD bhavcopy carries close-to-close only. Approximating the split from daily open/close works for the *underlying* but not for option premia, which is where the effect lives.

Even with the data, the observation structure is the familiar wall: an overnight-only short-vol book is **one P&L series** → Sharpe ~1.50 on 3.5 years. O1 already died here (WITHDRAWN, 0.59 against 0.92).

**Escape-B warning at full strength.** A pure overnight short-volatility book is exactly the construct most likely to *report* Sharpe above 1.5 and *be* a short tail. **The RFA's noncentral-t machinery scores mean over standard deviation and is blind to skew.** If any construct passes the gate on Escape B, treat the pass as suspicious until a separate tail analysis is run. **This is a gap in the platform's gate, not in the construct — and it is worth fixing regardless of whether SE-7 is ever pursued.** It bears directly on Round 1's flagship recommendation, which is a short-volatility program.

### F. Expected half-life
**Decades.** The gap risk is not going away while the exchange is closed 17 hours a day.

### G. Implementation difficulty
**Very High.** Intraday data the platform lacks, cross-venue access the researcher lacks, and a tail framework the gate does not implement.

### H. Research priority
**7.** Not actionable now. Included because the day/night decomposition is a real correction to how this platform has thought about VRP.

---

# Part II — Rejected

| Idea | Why rejected |
|---|---|
| **Dealer gamma / GEX positioning** *(Round 1 Edge 2, ranked #3)* | The mechanism is real, but **dealer inventory is not observable**. NSE publishes strike-level OI without holder identity, and participant-wise OI without strike. Any GEX series is an *allocation assumption* dressed as data. Compounding this, GEX-conditioned index volatility is one number per period → wall. |
| **VIX regime filter / vol-weighted sizing** *(Round 1 Edge 3, ranked #2)* | Not an alpha source (Round 1's own table says "N/A"), and a sibling test ran yesterday: TS Basis probe G1 VIX gate — **REMOVE-or-flat at the margin, not stability-clear** (commit `83b3726`). |
| **Participant-wise OI as a directional signal** *(Round 1 Edge 6)* | Single time series, aggregated across underlyings. FLOW already died in this family (max power 0.6053). Ingest as context; do not gate on it. |
| **FII/DII daily cash flows** | Single time series → wall. Also the most heavily mined public dataset in Indian retail trading. |
| **Cross-asset / overnight S&P → Nifty drift** *(Round 1 Edge 9, which also rated it "weak — arbed away")* | Agreed, and for a more fundamental reason than latency: the residual is **one number per day → wall**, and the pre-open call auction (9:00–9:15, randomised close) exists to impound it. |
| **GIFT Nifty offshore lead** | Reject — but Round 1's stated reason (HFT latency) understates it. The binding barrier is **FPI-only access**: a domestic researcher cannot trade the instrument at all. |
| **Max Pain / expiry pinning** | Reject, agreeing with Round 1. Preferred wording (see R1-D): the mechanism is **co-movement, not circularity** — OI clusters near spot. Grounds: weak index-level evidence, and n ≈ 500 max at one observation per expiry. |
| **SIP / month-end / calendar flow at index level** | Real forced flow, but AMFI data is monthly, the index expression is one number per month, and it is indistinguishable from the calendar seasonality the mandate rejects. |
| **Order-book imbalance, queue dynamics, auction microstructure, latency** | Genuine and profitable — for participants with colocation, quoting obligations and tick data. Structurally unavailable; no tick data on this platform. |
| **Sector-index cross-section** | Sector index futures (NIFTYIT, NIFTYINFRA, NIFTYPSE, NIFTYCPSE, NIFTYMID50) all ceased 2018–2020. Trading a sector index means constituent baskets → back into the delivery-STT wall. |
| **The Closing Auction Session as a research target today** | The most important structural change in this market in a decade, with **no history**. A warning (§4), not a project. Revisit 2028. |
| **Composite "meta-edge" from weak signals** *(Round 1 Edge 10)* | Not rejected on mechanism — it has none, by construction. A composite is an *aggregation method*, not a structural source of alpha, and the mandate asked for sources. It also inherits the multiplicity problem: combining k signals each individually short of the gate does not produce a gate-clearing composite unless their independence is itself demonstrated, which requires its own reads. |

---

# Part III — Final output (the six questions)

## 1. Ranked list

**Seven survived rejection; twelve were rejected on the record.** The mandate asked for a Top 10 and also said "reject weak ideas / I would rather have five institutional-quality directions than fifty retail ones." Padding to ten would be the failure mode it named.

| # | Edge | Escape claimed | Breadth risk | Confirmatory window | Mechanism | Independent-researcher accessible? |
|---|---|---|---|---|---|---|
| **✗ CLOSED** | **SE-1 Forced passive rebalancing flow** — **ABANDON at the RFA gate 2026-08-05**, max power 0.7674 | A (event cross-section) | **Measured: 66 events → 22 clusters, ratio 3.0. n_required 24 > 22 available** | Event-time — **unburned, and stays that way** | Strong | Yes — but demonstrability, not access, is what killed it |
| 2 | **SE-2 Constituent liquidity provision (SSF-executed)** | A (`rank_ic`, contested) | Low (ρ = −0.04) | **Nifty-50 daily 2023–26 PRESERVED** | Strong | Yes, with effort |
| 3 | **SE-3 Implied-correlation / dispersion premium** | A (**breadth unmeasured**) | **Unknown — probe first** | Partly burned (Skew) | **Strongest** | Marginal |
| 4 | **SE-4 Physical-delivery expiry forced roll** | A (name-expiry events) | Low | Event-time; substrate partly burned | Strong | **Yes** |
| 5 | **SE-5 Margin-regime shocks (SPAN)** | A (event cross-section) | Low | N/A | Strong | Yes — **in 2028** |
| 6 | **SE-6 Retail lottery wealth transfer** | **None — blocked** | N/A | N/A | **Overwhelming** | **No** |
| 7 | **SE-7 Overnight-segmented VRP + GIFT Nifty** | B (Sharpe, skew-suspect) | N/A | None | Strong | **No** |

## 2. Which deserve immediate research

~~**SE-1, then SE-3's breadth probe, then SE-2**~~ → **SE-3's breadth probe, then SE-2 — and only with SE-2's metric question settled in advance.** *(Revised 2026-08-05: SE-1 ran first, as this section directed, and closed at the gate. The remaining order is unchanged.)*

- ~~**SE-1 first**~~ — **DONE, and SE-1 is CLOSED.** The counting pass ran 2026-08-04 (66 events → 22 clusters, required cluster-level `δ/sd` 0.6264, falsifying the "comfortable arithmetic" premise). The literature check this section demanded ran 2026-08-05 and produced a defended annualized Sharpe band [0.35, 0.80], which the gate then rejected: **max power 0.7674 < 0.80, n_required 24 > 22 available.** No further SE-1 step exists. Sourcing the ~22 cluster announcement dates is no longer on the critical path — it was never the binding constraint, and the gate is decided on n and the band alone.
- **SE-3's N_eff / sd_IC probe second**, on the already-burned window. Cheap, costs no purity, and it is the single number deciding whether the best mechanism here is reachable. Carry forward the **dispersion only**.
- **SE-2 third.** rank_ic PASS with per_trade_pnl FAIL is a real possible outcome and must be pre-declared. The 2023–2026 constituent window is the last clean one; do not open it on an unsettled question.

**Explicitly not recommended this week:** Round 1's #1 (VRP) and #2 (VIX filter), for the reasons in §2.

## 3. Which should be abandoned immediately

Dealer gamma / GEX; participant-wise OI as a signal; FII/DII cash flows; overnight S&P → Nifty drift; GIFT Nifty offshore lead; max-pain / pinning; calendar-SIP effects at index level; order-book / queue / latency; sector-index cross-section; composite meta-edge as a *source*; and **any re-parameterization of Carry, TS Basis, OSC, O1, FLOW, RS-MOM, or breadth→futures**.

## 4. Which require data we do not possess

| Edge | Missing | Obtainable? |
|---|---|---|
| **SE-5 SPAN margin shocks** | Historical daily SPAN risk-parameter files. **~14-month rolling window now on hand** (275 snapshots, 2025-06-19 → 2026-08-03, backfilled 2026-08-04). Not a research panel — still requires **forward collection to 2028**. | Forward collection **started 2026-08-04** (daily job, asserted freshness); older history not purchasable at retail scale. |
| **SE-7 Overnight VRP** | Intraday option prices; GIFT/SGX Nifty history | Intraday: paid vendor. GIFT: separate venue, FPI-gated. |
| **SE-6 Retail transfer** | Client-level trade panel | **No — regulator-only.** |
| ~~**SE-1 (partial)**~~ **— MOOT, SE-1 closed** | Contemporaneous index-change **announcement dates** | Yes, by hand assembly — but **no longer worth doing for SE-1.** It was never the binding constraint (the gate is decided on n and the Sharpe band alone), and the construct is abandoned. Retained only because the same calendar would serve any future event-time construct on index membership. Note this is *not* the same as composition history, which Round 1 lists. |
| **SE-4 (partial)** | SLB borrow rates/availability history; pre-2020 delivery percentage | Partially — NSE publishes daily; depth unverified. |
| **SE-3 (optional)** | BANKNIFTY options | **Yes — one filter change plus re-ingest.** Decide before measuring; it changes the breadth arithmetic. |

**Three zero-cost data actions worth starting this week, none touching a sealed window:**
1. ~~Archive the daily NSE SPAN files (enables SE-5 in ~2028)~~ — **DONE 2026-08-04** (`fetch_span_params.py`, daily chain, backfill to retention edge).
2. Archive the daily participant-wise OI file (context for everything).
3. ~~Begin the point-in-time index-change **announcement** calendar (unblocks SE-1).~~ — **dropped 2026-08-05.** SE-1 is abandoned at the gate, and the calendar never unblocked it in the first place: announcement-date coverage does not enter the power arithmetic.

## 5. Highest probability of durable alpha

~~**SE-3 on mechanism; SE-1 on realizability.**~~ → **SE-3 on mechanism. The realizability slot is now vacant.** *(Revised 2026-08-05 — SE-1 held it and is closed; SE-4 is the natural claimant on its ~2,000 name-expiry events, but it has never been gated, so promoting it here would be the post-hoc re-ranking this document warns against. Left vacant deliberately.)* The two axes still differ on *which* probability.

- **SE-3**'s mechanism — compensation for correlation risk — is the most likely of anything here to be intact in 2040, protected by an Indian demand imbalance a determined regulator has failed to suppress. But it is Very High difficulty, its breadth is unmeasured, and it is short a tail.
- ~~**SE-1**'s mechanism decays but cannot vanish, because the forced side's mandate is explicitly anti-alpha and its AUM compounds at ~32%. It is the candidate most likely to survive contact with this platform's own gate.~~ **FALSIFIED 2026-08-05 — and instructively.** The first clause stands: the mechanism is real and its forced side is mandated to be price-insensitive. The second is exactly backwards — SE-1 was the *first* of these candidates to meet the gate and it did not survive, at max power 0.7674. **A mechanism being real, durable, and forced says nothing about whether 22 observations can demonstrate it.** That is the dossier's own governing insight applied to its own #1 pick, and this document failed to apply it until the arithmetic was run.
- **SE-2** has the highest probability that a *real effect exists* — already measured OOS at IC +0.029 — and the lowest probability of *durability*.

## 6. Realistically achievable by an independent researcher

**Achievable: SE-4 and SE-2 (with effort)** — and SE-1 *was* achievable in this sense too, which is precisely the point. All three share the profile that makes an edge available to a small researcher and unattractive to a large one: **capacity-limited, low-frequency, data-assembly-heavy, requiring patience rather than infrastructure.** A multi-billion-dollar fund cannot deploy meaningfully into a few hundred crore of index-rebalancing flow or a single-stock expiry roll. You can.

**But SE-1 is closed anyway, and the reason is worth carrying into SE-4 and SE-2.** Accessibility and demonstrability are independent axes. SE-1 scored top marks on the first — capacity-limited in your favour, event-time window unburned, no infrastructure required — and still died on the second, because a low-frequency edge available to a small researcher generates *few observations by the same property that makes it available*. **The profile praised in this paragraph is partly a description of a small-n problem.** SE-4's ~2,000 name-expiry events are the reason it survives that tension where SE-1 did not; SE-2 must answer it before its metric question is settled.

**Not achievable: SE-6, SE-7, and every rejected microstructure idea.** They need market-making infrastructure, cross-venue FPI access, or a regulator's data. The correct response is not to approximate them — approximation is where OSC's N_eff = 1.9 came from — but to decline them.

**SE-3 is the genuine borderline.** The mechanism is available to anyone with EOD option data on both legs, which this platform has. Managing a delta-hedged, correlation-exposed, tail-short book is institutional work.

---

## 7. The uncomfortable conclusion

Durable alpha is structurally possible in this market. The mechanisms are real, several are documented by the regulator itself, and one — the retail options wealth transfer — is the largest in the world by absolute size.

But the honest answer to *"where is it most likely to originate?"* is **not where the money is.** The biggest, cleanest, most persistent transfer in Indian markets is captured by *having a market-making business*, and no amount of research skill substitutes for that.

What is left for a researcher with excellent engineering, sixteen years of EOD data, and no exchange membership is narrower and less glamorous: **be the patient counterparty to someone who is forced to trade on a published schedule.** Index funds at reconstitution. Leveraged holders at physical-delivery expiry. Price-insensitive flow in the constituent cross-section.

> **CORRECTED 2026-08-05 — this paragraph's closing claim was false for the first of its three examples, and the error is the whole lesson.** The original text asserted that all three *"produce **many independent observations from a single calendar year**, which is the only thing this platform's arithmetic has ever rewarded."* The second clause is right. The first was **asserted, not counted** — and when it was counted, index reconstitution produced **2.335 announcement clusters per year**, the opposite of many. SE-1 died on exactly that.
>
> The corrected claim: **being forced-schedule is not the same as being observation-rich, and this document conflated them.** Expiry rolls (~2,000 name-events) and the constituent cross-section (daily × ~50 names) genuinely are observation-rich. Reconstitution is not, because the same schedule that makes the flow predictable also makes it *rare*. **A published schedule tells you the trade is real; only counting tells you whether it is demonstrable.** The dossier's own governing insight was available the entire time and was applied to SE-3 and not to SE-1 — which is why the counting pass, not the mechanism review, is what settled it.

The pattern across ten dead constructs is not that the edges were absent. It is that they were expressed as **one number per period**. Every survivor here is an attempt to fix that, and the fix is always the same: **find the units, not the signal.**

---

## Sources

**Regulatory and exchange primary sources**
1. [NSE — Closing Auction Session](https://www.nseindia.com/static/products-services/closing-auction-session)
2. [NSE circular CMTR73362](https://nsearchives.nseindia.com/content/circulars/CMTR73362.pdf) — CAS operational circular
3. [NSE — All Reports, Derivatives](https://www.nseindia.com/all-reports-derivatives) — participant-wise OI, FII derivatives statistics
4. [NSE — Securities Lending and Borrowing](https://www.nseindia.com/market-data/securities-lending-and-borrowing)
5. [NSE Indices — Nifty 50 methodology](https://archives.nseindia.com/content/indices/ind_nifty50.pdf) — review schedule, notice period
6. [NSE Nifty Passive Insights, Q1 2025](https://www.niftyindices.com/Nifty_Passive_Insights/Nifty%20Passive%20Insights%20Quarterly%20update%20-%20January%20to%20March%202025.pdf) — passive AUM tracking Nifty
7. [NSE Clearing — SLB scheme FAQ](https://www.nseclearing.in/sites/default/files/2025-07/FAQ%20for%20SLB%20Scheme.pdf)

**Regulatory findings on retail derivatives**
8. [Business Standard — SEBI study, F&O net losses widen in FY25](https://www.business-standard.com/markets/news/net-losses-of-traders-in-fo-widens-in-fy25-sebi-study-125070701221_1.html) — ₹1,05,603 cr, +41% YoY
9. [ICICI Direct — 91% of retail traders lose money, FY25](https://www.icicidirect.com/share-market-today/news/sebi-sees-dip-in-derivatives-turnover,-91percentage-of-retail-traders-lose-money-in-fy25/1615620)
10. [CFA Institute — India's derivatives market and retail investors](https://blogs.cfainstitute.org/marketintegrity/2025/11/05/indias-derivatives-market-and-retail-investors/)
11. [5paisa — SEBI expiry-day reshuffle: NSE Tuesday, BSE Thursday](https://www.5paisa.com/news/sebi-reshuffles-equity-derivatives-expiry-days-to-streamline-trading)

**Academic**
12. [Agarwal, Ghosh, Prabhala & Zhao (2025) — *Animal Spirits on Steroids: Evidence from Retail Options Trading in India*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5430635)
13. [Bhat et al. (2024) — *The asymmetry in day and night option returns*, JFM 44:1320–1337](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512)
14. [Institutional ownership, investor recognition and stock performance around index rebalancing: evidence from India](https://www.sciencedirect.com/science/article/abs/pii/S1042444X20300049)
15. [*On the hidden costs of passive investing* (arXiv 2506.21775)](https://arxiv.org/pdf/2506.21775)
16. [Jain et al. (2019) — *Indian equity options: smile, risk premiums, and efficiency*, JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.21971)

**Market structure and flows**
17. [Groww — NSE extends F&O hours to 15:40, effective 3 Aug 2026](https://groww.in/blog/nse-extends-f-and-o-trading-hours-by-10-minutes-new-timings-effective-from-august-3-2026)
18. [Anand Rathi — NSE extended F&O timings, VWAP window shift](https://anandrathi.com/blog/nse-extends-trading-hours)
19. [Business Today — NSE explains Nifty/Sensex spot-futures divergence under CAS](https://www.businesstoday.in/markets/stocks/story/why-are-nifty-and-sensex-moving-opposite-nse-explains-closing-auction-session-547012-2026-08-04)
20. [FIA — Premium turnover in Indian options hits $150 billion](https://www.fia.org/marketvoice/articles/premium-turnover-indian-options-hits-150-billion)
21. [Bajaj AMC — Nifty 50 rebalancing mechanics](https://www.bajajamc.com/knowledge-centre/nifty-50-rebalancing)
22. [Marketcalls — MSCI rebalancing for Indian investors](https://www.marketcalls.in/investment/msci-rebalancing-explained-a-comprehensive-guide-for-indian-investors-and-traders.html)
23. [Bajaj AMC — GIFT Nifty / SGX Nifty transition](https://www.bajajamc.com/knowledge-centre/sgx-nifty)
24. [Finnovate — passive AUM growth in India](https://www.finnovate.in/learn/blog/how-to-select-and-build-a-strategy-around-passive-funds)
25. [Sahi — Closing Auction Session 2026 guide](https://www.sahi.com/blogs/closing-auction-session-cas-explained-nse-bse-closing-price-rules-2026)

**Internal (this repository)**
26. `docs/reports/STRUCTURAL_ALPHA_DOSSIER.md` — Round 1 (commit `5d5ded1`)
27. `docs/reports/INDEX_CONSTRUCT_DIAGNOSIS.md` — the `ncp = S·√T` wall; §8 the burned 2023–2025 options window
28. `docs/reports/OSC_RFA_ABANDON.md` — N_eff 1.9, sd_IC 0.2502
29. `docs/reports/CB_N50_HOLDOUT_REPORT.md` — OOS IC +0.029, preserved sealed window
30. `docs/reports/RFA_GATE_O1_REVIEW.md` — O1 withdrawal
31. `docs/reports/TS_BASIS_FILTER_SD_PROBE_REPORT.md` (commit `83b3726`) — VIX/OI/expiry gates REMOVE-or-flat, not stability-clear
32. `scripts/rfa/power.py`, `docs/reports/RFA_RETROSPECTIVE.md` — the gate and its arithmetic
33. `CLAUDE.md` — substrate inventory, fee models, pitfall register

---

## Methodology

Sixteen targeted web searches plus one primary-source fetch, prioritising NSE and SEBI primary documents and peer-reviewed journals over secondary summaries. `firecrawl` and `exa` MCP tools are **not configured** in this environment; `WebSearch` and `WebFetch` were used instead.

Claims that could not be verified to a primary source, flagged in-text rather than asserted: SLB historical data depth; MSCI announcement-to-effective lag (secondary sources only — a range is given, not a point figure); the Agarwal et al. numbers are taken from the abstract and working-paper listings, as the PDF could not be parsed in this environment.

Two repository claims were verified directly at source rather than inherited from another report:
- **No SPAN archive exists under `data/`** — checked by glob and directory listing. This is why SE-5 is classified as data-not-possessed.
- **`scripts/msrp/triage_fee_impact.py` reads `option_bhavcopy` over 2023-01-02 → 2025-12-31 and computes long/short ATM straddle arms net of fees** — lines 36–37, 42, 109, 132–274. This is the evidence for R1-A.

**Scope limit on the Round 1 critique.** This pass read Round 1's preamble (§Constraints 1–4) and its closing sections (Rejected / Data Gaps / Recommendations / Governing Insight) in full, plus its section headings. **It did not read the bodies of Edges 1–10.** Findings R1-A through R1-E are therefore scoped to what those sections state; a disagreement recorded here may already be qualified inside an edge body this pass did not open.

**No market data was read. No window was opened. No gate was run.**
