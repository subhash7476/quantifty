# Options-Wall Paper Pilot — Design Spec

**Branch:** `feat/options-wall`
**Date:** 2026-08-14
**Status:** Design (awaiting operator review before implementation planning).
**Depends on:** `docs/reports/OPTIONS_WALL_PROJECT_COURSE.md` (Phases 0–3 complete),
`core/analytics/chain_scanner.py`, `core/execution/options/fees.py`.

---

## 1. Purpose & framing

Run the Options-Wall premium-farm screen as a **paper-traded discovery pilot** for
one month, in parallel with continuous chain collection. At month-end we have both
the accumulated scan/chain trail and a set of paper round-trips to analyze together.

**This is a pilot, not a confirmatory read.** Its jobs are: (1) validate the
scanner → paper-executor → P&L loop end-to-end; (2) produce a clean forward record;
(3) *inform* — not authorize — a later pre-registration + RFA for a longer
confirmatory window. Month-1 results are disclosed as prior exposure to any successor.

**Non-negotiable discipline:** every threshold in §10 is **pinned before day 1 and
not tuned mid-month.** Adjusting rules while watching results turns the month into
anecdotes. This is the C2 / TS-Basis-Daily selection-contamination lesson applied.

**The pilot is not a statistical read and must never seed one.** At ≤1 fly/index over
weekly expiries, month-1 yields n≈4–8 round-trips — anecdote, not a sample. If the
premium-farm screen is ever promoted to a *confirmatory* read it enters the RFA gate
as a `per_trade_pnl` construct on ≤2 indices — the RS-MOM wall: √T ≈ 1.9 over the
~186-week sealed window ⇒ it needs an annualized Sharpe ≥ ~1.3 for power 0.80, and a
month of paper changes that arithmetic by exactly zero. Month-1 is prior exposure and
a plumbing check; its numbers must **not** be used to defend a successor's effect-size
(Sharpe/SD) band. That band must be independently defended (the C2 lesson).

---

## 2. Scope

- **Screen:** premium-farm **only**. Imperfection and laggard keep scoring and
  persisting as signals but **do not fire trades**.
- **Universe:** Nifty (Tue weekly) + BankNifty (Wed weekly) index chains, **near
  weekly expiry only**.
- **Execution:** paper only. No broker orders, no real money. Output is booked
  paper positions + P&L.

---

## 3. Entry rules

A trade is opened when **all** hold on a scan cycle, within the entry window:

1. **Regime** = `Positive GEX (Stable)` for that index.
2. **Pinning in force**: `|spot − pin| / spot ≤ pin_band_pct` (0.005), where
   `pin = argmax(gamma_by_strike)`. If spot is not near the pin, pinning is not
   real → no trade.
3. **IV−RV gate at ATM**: `ATM mid-IV − realized_vol ≥ iv_rv_min_gap` (2.0 vol pts).
   RV = `session_realized_vol_pct` (annualized 1m, percent units).
4. **Liquidity/spread**: every leg to be traded has a live bid/ask and each leg's
   `(ask − bid)/mid ≤ max_spread_pct` (0.05).
5. **DTE ≥ 1** (never open on expiry day).
6. **Entry window** 09:30–15:00 IST (skip the opening auction and the last ~20 min).
7. **Concurrency**: at most **one** open fly per index. Re-enter only after the prior
   one closes.

Entry fill = **mid of bid/ask per leg**. If any traded leg lacks a quote, no trade.

---

## 4. Structure — ATM-centered iron fly

- **Center**: the ATM strike (nearest listed strike to spot) — **not** the pin. (Pin
  is a gating condition per §3.2; when pinning is real, ATM ≈ pin and the fly is
  balanced.)
- **Short legs**: sell CE + sell PE at the ATM strike.
- **Wings**: buy CE at the nearest listed strike to `spot × (1 + 0.015)`; buy PE at
  the nearest listed strike to `spot × (1 − 0.015)`. Wing width is **±1.5% of spot,
  snapped to the nearest listed strike** — never a fixed strike count (NSE strike
  spacing is non-uniform: ~100 near ATM, sparse in the wings).
- Defined-risk, four legs. 8 orders per round-trip (4 entry + 4 exit).

---

## 5. Exit rules

Close the whole fly on the **first** of:

1. **Take profit**: position P&L ≥ **+50%** of net entry credit.
2. **Stop loss**: position P&L ≤ **−2×** net entry credit.
3. **Regime flip**: index GEX turns `Negative` → close immediately (D5 guard applies
   to holding, not just entry).
4. **Time stop**: square off at **15:15 IST on the session before expiry day**.

**TP/SL are evaluated on the marked (unrealized) position value** — current mid to
close the fly vs the net entry credit — **before exit fees**; the round-trip fees are
then booked at realization. This keeps the trigger a clean function of premium decay;
the `trades` table records the fee-inclusive net P&L.

**Hold horizon — multi-session, pinned (operator decision 2026-08-14).** A fly may be
held across overnight and weekend gaps, up to the §5.4 time stop (e.g. opened
Thursday, squared off Monday for a Tuesday expiry). This is deliberate: a weekly fly
does not accrue meaningful theta intraday, and an intraday-only design that re-entered
each day would pay the ~₹230 8-order round-trip fee daily (up to ~₹4,600/month — an
upper bound assuming daily re-entry, not a cost floor), eating the edge. Consequence
accepted explicitly: **the position holds a longer horizon than the IV−RV entry gate
measures** (`session_realized_vol_pct` is trailing intra-session RV and does not price
the overnight/weekend gap the fly is exposed to). The defined-risk wings cap that gap
exposure to a bounded loss; the pilot then observes empirically how often the gap
moves against the position.

Exit fill = mid of bid/ask per leg (live). During replay/audit, `ltp` is the
documented fallback when bid/ask is unavailable (see §7).

---

## 6. Sizing & margin

- **Sizing (pinned): fixed 1 lot** per fly, where `qty = 1 × the contract's live
  `lot_size`` (read per-contract from the chain, **not** a hardcoded number — the
  static 75/15 lot map is stale; the instrument master shows ~65 Nifty / ~30
  BankNifty as of 2026-08-10 and lot sizes change over time). Rationale: normalizes
  across indices via return-on-margin. The flat
  ₹20/order brokerage was checked and is **not** fee-dominant at 1 lot: on a
  representative Nifty fly (ATM straddle ~₹135/unit, wings ~₹15–18/unit, net credit
  ~₹102/unit × lot ≈ ₹7,650 at an illustrative lot), round-trip fees ≈ ₹230 — ~₹160 flat brokerage (8 orders)
  + ~₹30–35 STT (0.15% sell) + ~₹9 exchange + ~₹20 stamp/GST/SEBI — i.e. **≈3% of net
  credit, ≈6% of the +50% TP target, ≈1.1% of defined risk.** The ATM premium scale
  absorbs the flat brokerage. Verify the exact figure against live premia at freeze;
  revisit sizing only at a phase gate, never mid-month.
- **Margin denominator** = defined-risk max loss =
  `(wing_width_points × lot) − net_credit`. No SPAN snapshot needed (risk is capped
  by the wings), so **return-on-margin is well-defined** and is the primary
  cross-trade comparison metric.

---

## 7. P&L, fees, marking

- **Marking**: every open fly is marked each scan cycle off the wall trail (mid per
  leg when bid/ask present; else `ltp`, labelled). Realize P&L on exit.
- **Fees**: `core/execution/options/fees.py`, per-leg, effective-dated, BUY/SELL
  aware. 8 orders per round-trip. Verified against a current broker calculator to ±1
  paisa at qty 25 and 100; STT applies the current 0.15% sell-side rate. This is the
  **net** number we analyze.
- **Exercise STT is out of scope and must stay so**: `fees.py` omits exercise STT on
  the assumption positions exit before settlement. The §5.4 time stop enforces that
  assumption; no fly may be held into expiry day.
- **`fees.py` docstring divergence (documented, not a defect):** that module's
  docstring states its consumer's holding model as "DTE ≥ 2, same-day open→close." The
  pilot is DTE ≥ 1 and multi-session (§5 hold horizon). The **fee numbers are
  unaffected** — the divergence only concerns exercise STT, which the time stop still
  precludes. `fees.py` is a shared MSRP module and is **not** edited for this pilot;
  this note records the mismatch so a future reader does not infer the pilot's holding
  model from the fee module's docstring.

---

## 8. Persistence changes

1. **Persist bid/ask in the wall trail.** Add `best_bid` / `best_ask` columns to the
   `option_chain_snapshot` schema in `core/data/options_wall_store.py`, populated each
   cycle from `UpstoxMarketData.fetch_quotes_batch`. Without this, paper fills are not
   reconstructible or auditable after the fact (the trail currently stores `ltp`
   only). The poller (`core/options_wall/poller.py`) fetches quotes per cycle and
   passes them to `append_snapshot`. **Operational note:** this raises the poller from
   2 to 4 Upstox calls per 5s cycle (chain + quotes × 2 indices). Confirm this stays
   inside Upstox rate limits before enabling; if not, widen the poll cadence or batch
   the quote fetch across indices.
2. **New `trades` table** (in `wall_scan_results.duckdb`, beside `scan_results` /
   `session_regime`): one row per paper round-trip — index, expiry, entry_ts, exit_ts,
   the four legs (strike/type/side/entry_mid/exit_mid), net entry credit, entry fees,
   exit fees, gross P&L, net P&L, max-loss/margin, return-on-margin, exit_reason
   (tp / sl / regime_flip / time_stop). Append-only.

---

## 9. Scanner reconciliation (implementation note)

The current `_farm_screen` emits one candidate per **near-pin strike** and gates
IV−RV per that strike. Note what the current code does and does *not* do:
`_farmable_strikes` filters `|strike − pin| / spot < pin_band_pct` — that is a
**strike-near-pin** filter (the `s` in the comprehension is a strike). A
**spot-near-pin** precondition (`|spot − pin| / spot`) does **not** exist yet. This
spec demotes the pin to a gating condition and centers the structure at **ATM**.
Precise changes to `chain_scanner.py` (farm screen only):

- **Add (new):** a spot-near-pin precondition `|spot − pin| / spot ≤ pin_band_pct`
  (§3.2) as a gate on whether to emit any farm row at all. This is not the existing
  strike-near-pin filter.
- **Switch:** measure the IV−RV gate at the **ATM** strike (§3.3) — replace the
  current per-near-pin-strike `_strike_mid_iv` gate.
- **Replace:** the per-near-pin-strike loop with emission of a **single ATM-centered
  fly** candidate per index per cycle (§4), carrying the four chosen leg strikes, not
  a per-strike list.
- **Keep:** rank on IV−RV gap (HIGH-1 fix preserved); with one candidate per index the
  rank is trivially the gap value.

The imperfection/laggard screens are unchanged.

---

## 10. Frozen parameters (pinned before day 1)

| Parameter | Value |
|---|---|
| Screen | premium-farm only |
| Regime required | Positive GEX (Stable) |
| Pin-proximity gate | `|spot − pin|/spot ≤ 0.005` |
| IV−RV gate (at ATM) | ≥ 2.0 vol pts |
| Max leg spread | ≤ 5% of mid |
| Wing width | ±1.5% of spot, snapped to nearest strike |
| Fly center | ATM (nearest strike to spot) |
| DTE to open | ≥ 1 |
| Entry window | 09:30–15:00 IST |
| Concurrency | ≤ 1 open fly per index |
| Take profit | +50% of net credit |
| Stop loss | −2× net credit |
| Regime-flip exit | on flip to Negative GEX |
| Time stop | 15:15 IST, session before expiry day |
| Sizing | 1 lot = 1 × live per-contract `lot_size` (pinned; ≈3% fee drag est.) |
| Fee model | `core/execution/options/fees.py` |

---

## 11. Non-goals & month-end analysis

**Non-goals:** no auto-sizing beyond the fixed lot, no real orders, no mid-month
parameter changes, no NiftyShield strategy integration (execution *primitives* may be
reused; the strategy logic is clean-room), no confirmatory statistical claim.

**Month-end analysis is strictly plumbing/mechanics** (n≈4–8 cannot support a signal
claim — see §1): trade count, fee drag as a fraction of gross credit, exit-reason mix,
mark-vs-fill slippage, regime-flip-exit frequency, and any reconstruction/audit
failures (missing quotes, un-markable legs, store gaps). These are **descriptive**,
not evidence. Explicitly **out of scope:** IV−RV-realized attribution ("did the gap
predict the outcome?") and any win-rate/edge claim — those are statistical reads the
sample structurally cannot answer, and attempting them is the retired post-hoc
in-sample read. Output is a report on whether the *loop* works and the *fees* are
real, plus a decision on whether the screen merits a formal pre-registration — never a
go-live and never an effect-size estimate.

---

## 12. Build implications (for the plan)

1. `chain_scanner.py` — farm-screen reconciliation (§9).
2. `options_wall_store.py` — bid/ask columns (§8.1).
3. `poller.py` — fetch + persist quotes each cycle (§8.1).
4. New paper executor — construct fly from a farm candidate, mark off the trail,
   apply §5 exits, book to the `trades` table (§8.2). Reuse `paper_broker` /
   `group_tracker` / `group_pnl` primitives; wire only to the wall store (clean-room).
5. Ops — poller on a durable schedule so the trail + paper book accumulate unattended.
6. Tests — fly construction (wing snapping, ATM centering), exit-rule triggers, fee
   round-trip, store round-trip with bid/ask.

**As-built note (§12.4 deviation, accepted):** the executor is self-contained — it
computes fly P&L directly (`core/options_wall/fly.py` + `fees.py`) and does **not**
reuse `group_tracker` / `group_pnl` / `paper_broker`. A 4-leg fly's P&L is arithmetic;
the group primitives added no value (repo rule: no over-engineering). Clean-room intent
holds — the executor touches only the wall store + the shared fee model.

---

## 13. Known limitations (as-built, documented — not defects)

- **Time-stop on holiday-shortened weeks.** The exit fires at `DTE ≤ 1` and
  `≥ 15:15`. On the normal Tue/Wed-weekly calendar this lands the session before
  expiry. If the session before expiry is a market holiday (last open session at
  DTE ≥ 2), the intended pre-expiry close does not fire and the fly is instead closed
  on expiry day (DTE = 0) at 15:15 — a **safety net that still precludes settlement
  and exercise STT**, but at worse (expiry-day) marks than intended. A
  trading-calendar-aware "last open session before expiry" rule was judged
  over-engineering for the pilot; the DTE = 0 close is the accepted fallback.
- **Quote keying dependency.** Entry requires a live bid/ask per leg. This relies on
  `UpstoxMarketData.fetch_quotes_batch` keying its response by the full instrument
  key; verify against a live response before day 1 (runbook pre-flight). If keying
  differs, the trail's bid/ask is all-NULL and no farm trade can open.
