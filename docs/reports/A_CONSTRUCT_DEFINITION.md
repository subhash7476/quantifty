# A — Construct Definition: Index Intraday Opening-Drive Continuation (Nifty Futures)

**Date:** 2026-08-27 · **Status:** DRAFT (not frozen — inputs are the prior-exposure
audit; the freeze lands with the pre-registration after substrate certification +
RFA) · **Branch:** `isd-program-reassessment`
**Inputs:** `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` ·
`ISD_PROGRAM_REASSESSMENT.md` (§4.A) · `NIFTY_BANKNIFTY_PAIR_RESEARCH.md` ·
`ISD_PHASE0_PRE_REGISTRATION.md` (F1/F4 machinery, reused with changes noted).

**Research question, stated exactly:** does NSE index intraday opening-flow
persist (time-series continuation) on a per-trade basis — or is the FTMO null
(0/41 intraday time-series patterns) reproduced on NSE? The in-repo prior that
says "this quadrant differs": the index-pair work measured intraday ratio
trending (+1.10/+1.17 slopes). The equity-level opening drive **faded** (ISD F1,
negative sign, family closed without sign-flip). The index-level answer is
unmeasured. A exists to measure it.

---

## 1. Signal window(s) — grid dimension 1

- **Feature:** opening-period return = (window-end bar close − **opening
  print**) / **opening print**, on `NSE_INDEX|Nifty 50` 1m bars.
- **Opening print (D3, decided 2026-08-27):** the first bar open of the
  session — era-consistent semantics. The vendor era (2012-01-02 →
  2023-01-31) has **no 09:15 auction bar** (its first bar is labeled 09:16
  and approximates the auction: median 3.2 bp / p99 25 bp / max 74 bp off the
  official open — `A_INDEX_SLICE_CERTIFICATION.md` §C5). The native era
  (2023-03-01 → present) carries the exact auction print as its 09:15 bar.
  The mechanism (the opening print concentrates the overnight information
  set) is era-invariant; the price source is the first bar open in both eras.
- **Window cells (frozen, 2) — bar-count semantics from the opening print**
  (era-invariant; certified 2026-08-27 — the vendor era's bars are labeled one
  minute later than the native era, so clock labels are not era-consistent):
  - Cell 1: window = bars 0..30 (opening print + 30 bars); entry bar 31.
    Native-era labels: 09:15–09:45 window, 09:46 entry — identical to ISD F1.
    Vendor-era labels: 09:16–09:46 window, 09:47 entry.
  - Cell 2: window = bars 0..45 (opening print + 45 bars); entry bar 46.
    Native-era labels: 09:15–10:00 window, 10:01 entry. Vendor-era labels:
    09:16–10:01 window, 10:02 entry.
  - The real-time window length differs by the vendor label offset (~1
    minute, sized by the C5 alignment distribution) — a disclosed era
    property, not a tunable.
- The feature is intraday-only by construction (opening-print base) — the
  overnight gap is a *different* information set (ISD F4) and is deliberately
  absent here; A and the retired F4 do not share a signal.
- **Mechanism anchor for continuation:** the opening call auction
  concentrates opening information into one print; the index-pair trending
  slopes are the empirical hint that index-level intraday flow persists.
  (D1 — sign pinned +1, ratified 2026-08-27.)

## 2. Entry timestamp

- **Entry:** the bar OPEN at bar index 31 (cell 1) / 46 (cell 2) — the bar
  immediately after the window-end bar. Signal fully known at entry
  (window-end close prints before the next bar opens; no look-ahead). Same
  convention as ISD F1, kept verbatim, generalized to bar counts.
- **Session validity rule (C6 defect class):** a session is skipped unless
  its first bar is stamped with the session's own date and the entry bar
  exists. This mechanically excludes the three certified first-bar defects
  (2025-02-01, 2026-02-25, 2026-03-02) and all partial sessions lacking the
  entry bar — skipped, counted, reported; never filled. Sessions whose
  first bar is missing entirely (e.g., 2013-07-29 first at 09:21, 2014-11-05
  first at 09:35) are skipped by this rule when the signal window is
  incomplete.

## 3. Exit timestamp

- **Exit (D4, decided 2026-08-27):** the **last bar close** of the session
  — the vendor era's 15:30-labeled bar, the native era's 15:29 bar. EOD-flat
  by construction — the position never survives overnight. Overnight is B's
  question, not A's.
- **Fidelity, disclosed, not costed:** the vendor-era last-bar close deviates
  from the official 15:30 close print by median 5.4 bp / p99 32 bp / max
  108 bp (native era: median 4 bp — the expected last-minute move;
  `A_INDEX_SLICE_CERTIFICATION.md` §C5). The backtest exit price IS the last
  bar close — the same convention in both eras — and execution realism is
  carried by the measured slippage lane, so no separate exit-fidelity lane is
  added (a lane would double-count what slippage covers). The distribution is
  recorded here and cited by the pre-registration as a modeling property of
  the vendor-era substrate.
- The ISD convention (exit at the last bar close, slippage applied) is kept
  for comparability.

## 4. Position rule

- One position per session, single-name time-series: **long if feature > 0,
  short if feature < 0, flat if feature == 0** (index prints make zero
  measure-zero; every tradeable session produces exactly one trade).
- **Sizing:** constant canonical notional ₹20,000,000 (the ISD canonical
  capital, `CANONICAL_CAPITAL`), executed as Nifty futures at market. No sizing
  grid, no risk-bucketing, no scaling. Per-trade returns are expressed in bp of
  notional, so sizing is not a free parameter.
- **No thresholds, no bands, no VIX filters, no exit variants** — every session
  trades. Any of these would be a new construct, not A.

## 5. Futures contract and roll methodology

- **Traded instrument:** near-month Nifty futures (FUTIDX, `NIFTY`).
- **Roll rule (causal, mechanical):** the traded contract on session t is
  determined at session open from the previous session's bhavcopy: roll from
  near to next when the next-month contract's volume exceeds the near-month's
  volume on t−1 (volume-dominance). Contract known at entry; no intra-session
  roll decision.
- **Execution substrate:** the backtest executes on the **cash index 1m series
  as the price proxy** — no futures intraday history exists (F1 determination:
  Upstox cannot backfill; the FUTIDX bhavcopy is daily). The basis is a
  disclosed proxy assumption with a cost lane (below), measured in
  certification.
- **Era boundary (certified):** vendor era 2012-01-02 → 2023-01-31
  (vendor CSVs, no auction bar, evening-session filter), native era
  2023-03-01 → present (Upstox). **2023-02-01 → 2023-02-28 (20 sessions)
  has no index 1m at all** — a permanent transition hole
  (`A_INDEX_SLICE_CERTIFICATION.md` §defects).
- **Roll cost:** because the book is flat overnight, a roll requires no
  transaction — the entry simply executes on the new contract. Roll cost = 0
  legs; the basis lane covers the discrepancy.
- The FUTIDX bhavcopy store (2016-02-11 → 2026-07-20) drives the roll calendar
  for 2016+; for 2012–2015 no futures data exists and the near-month is
  unverifiable — the roll calendar for that span is **cash-proxy with a
  disclosed assumption** (see §7 basis lane; flagged for the certification to
  size).

## 6. Per-trade return definition

- One observation per session:
  `r_t = sign · (exit_close_t − entry_open_t) / entry_open_t − costs_t`
  in **bp of notional**, where `costs_t` = fees_t + slippage_t + basis_lane_t
  (+ roll adjustment where a roll day is involved: 0 legs, see §5).
- Return series: `{r_t}`, one per tradeable session, net of all costs.
- **No compounding, no margin accounting** — returns are per-trade, on
  notional; leverage is an operator decision outside the construct.

## 7. Cost model (era-accurate; applied per session)

1. **F&O futures fees** — **BUILT 2026-08-27**
   (`core/execution/futures/futures_fees.py`, 13 tests green, gate-(a)/(b)
   schedules with [VERIFY] flags): brokerage min(₹20, 0.03% × notional) per
   order both legs; STT futures sell-side 0.01% (pre-2019-10-01) →
   0.0125% (2019-10-01 → 2024-09-30) → 0.02% (2024-10-01+); NSE F&O txn
   0.0021% → 0.00173% (2024-10-01+, [VERIFY]); SEBI ₹10/crore both legs;
   stamp buy-side 0.002% ([VERIFY]); GST/service tax schedule identical to
   the equity models. **Measured: 3.81 bp round trip at the canonical ₹2Cr
   notional (16 lots @ 50, post-2024 era).**
2. **Slippage** — **MEASURED 2026-08-27** (entry-bar drift p90 on the index
   1m, era-split): cell-1 entry 0.78 bp (vendor) / 0.70 bp (native); cell-2
   0.73 / 0.66 bp. Exit pays the same band (ISD convention). Round trip
   ≈ 1.4–1.6 bp at p90.
3. **Basis — MEASURED 2026-08-27, treatment per D5** (see below): mean
   component ≈ 0.4 bp/trade (carry drift over the hold; alternating book
   nets it out) — **not subtracted** from the net-spread gate; dispersion
   component (full-day within-contract |Δ| p90 = 19.2 bp, level p50 18 bp /
   p90 45 bp) is a **Sharpe/power disclosure** — the cash-series backtest
   cannot see it, so the RFA band must defend against it. Pre-2016 spans
   hold the 2016+ figures as the disclosed assumption.
4. **Tick/impact:** the measured drift bands contain the index spread
   component; no separate tick lane needed (certification decided this with
   data).

**The economics gate that matters (updated with measurements):** fees 3.81 +
slippage ≈ 1.5 = **~5.3 bp/session** hard costs; basis mean ≈ 0.4 bp. The
net-spread gate (mean net bp > 0) runs on these. The basis DISPERSION (19.2
bp full-day bound) is the power question, not the cost question — the RFA
must defend the declared effect size against it.

## 8. Sharpe definition

- Per-trade Sharpe: `S = mean({r_t}) / sd({r_t})` on the **net** bp series.
- Annualized: `S_ann = S · √cadence`, cadence = trades/year ≈ 250 (1/session;
  exact cadence measured in certification, reported in the RFA).
- **RFA declaration form (contract v2, per_trade_pnl):** annualized Sharpe band
  + cadence_per_year. Candidate band (declared and frozen only at RFA):
  `S_ann ∈ [0.95, 1.90]` (≈ per-trade S 0.06–0.12), cadence 250.
- **Power arithmetic (one-sided α = 0.05, hurdle 0.80, ncp = 2.486):**
  - SEALED n ≈ 900 (2023-01-01 → 2026-08, ~3.6 yr): optimistic corner
    S_ann 1.90 → power ≈ 0.97; central 1.42 (S=0.09) → ≈ 0.85;
    pessimistic 0.95 → ≈ 0.55 (disclosed: the pessimistic corner does not
    clear the hurdle — the read is calibrated to the central effect).
  - TRAIN (2012–2018, ~1,700 sessions) and HOLDOUT (2019–2022, ~1,000)
    produce thousands of trades before the sealed spend — existence is
    established (or falsified) cheaply, and the FTMO null is either
    reproduced on NSE or not, at TRAIN.

## 9. Minimal frozen grid

| Dimension | Frozen values | Notes |
|---|---|---|
| Signal window | {09:15–09:45, 09:15–10:00} | 2 cells |
| Sign | +1 continuation (D1) | pinned by mechanism; negative TRAIN closes the family |
| Entry | next-bar open after window end | 09:46 / 10:01 |
| Exit | 15:29 close, EOD-flat | no exit grid |
| Sizing | constant ₹2Cr notional | no sizing grid |
| Filters | none | every session trades |

- **Multiplicity:** 2 cells → per-cell α = 0.05/2 = 0.025 (BH). Family gate:
  ≥1 qualifying cell (empirical null, circular-shift + random-entry per ISD §7)
  AND family-level one-sided test on the mean of qualifying cells (α = 0.05,
  NW t) AND **net-spread > 0 at measured cost** (the gate that killed F4 —
  carried verbatim).
- Cell selection and family book = equal-weighted mean of qualifying cells;
  trial-ledger discipline per ISD §5 (append-only, written before results
  visible).

## 9a. Windows and availability (as certified, 2026-08-27)

| Window | Span | Sessions with bars | Permanent in-scope holes |
|---|---|---|---|
| TRAIN | 2012-01-02 → 2018-12-31 | ~1,700 | 2018-05-02..31 (22, absent from source) |
| HOLDOUT | 2019-01-01 → 2022-12-31 | ~1,000 | none in-scope (4 Diwali specials are out-of-shape) |
| SEALED | 2023-01-01 → present | ~860 (excl. 2023-02, 20) | 2023-02-01..28 (20, transition hole) + C6-defect sessions (skipped by rule) |

Out-of-shape specials (12 Muhurat/evening sessions, skipped by construction)
and the session-validity skip rule are detailed in
`A_INDEX_SLICE_CERTIFICATION.md` §defects. Fences are unchanged by any of
this; only the count of tradeable sessions is affected, and the counts above
are re-measured, never assumed, at pre-registration.

## D5 — basis treatment (DECISION PENDING: 2026-08-27)

Measured (2016–2026, within-contract, roll days excluded): basis level p50
18 bp / p90 45 bp / max 130 bp over cash; full-day |Δ| p90 **19.2 bp**.
The treatment question: the basis change over a ~5.7h hold has a MEAN
component ≈ 0.4 bp (carry drift; the alternating book nets it out) and a
DISPERSION component whose intraday value is unmeasurable pre-2023 (no
futures 1m; the 19.2 bp full-day bound includes overnight basis gaps an
intraday hold avoids). Options:

- **(a) Mean-only + dispersion disclosure (recommended):** the net-spread
  gate subtracts the mean (~0.4 bp, direction-consistent); the RFA defends
  the declared effect size against the dispersion floor; optionally a cheap
  live forward probe (~30 sessions, live futures LTP vs cash index over the
  actual hold window) measures the intraday value on the native era.
- **(b) Conservative full-day lane (19.2 bp/trade):** honest but almost
  certainly kills the construct at the cost filter before TRAIN — the lane
  exceeds any defensible gross edge.
- **(c) Scaled lane (~13 bp, √(5.7/24) variance scaling):** statistically
  arguable, but the scaling assumption (random-walk basis) is itself
  unverified — invented precision, declined.

The certified measurements:
`docs/reports/A_COST_SUBSTRATE_MEASUREMENTS.md` +
`data/a_index_intraday/cost_substrate_measurements.json`.

## D1 — operator decision (DECIDED 2026-08-27: continuation pinned)

**DECISION: pin continuation (+1) by mechanism. Ratified by the operator on
2026-08-27.** A negative TRAIN read closes the family — no sign-flip fishing
(F1 discipline, carried verbatim). Rationale: (a) it is the construct's
stated research question — reproduce the NSE trend-slope evidence or
reproduce the FTMO null; (b) one-sided TRAIN = maximum power at fixed α;
(c) F1's precedent shows the discipline holds; (d) a significant *negative*
TRAIN would itself be a falsification, and the fade hypothesis is a different
construct, not an A variant. The F4-style sign-burn alternative was
considered and declined — direction discovery on the same read that
establishes existence would double-count the TRAIN spend.

Consequences of the pin: TRAIN family-level test is **one-sided positive**
(α = 0.05); per-cell empirical nulls are one-sided positive; m = 1 (no sign
discovery) for the direction, plus 2 cells (BH α = 0.025) — multiplicity
declared at pre-registration: m = 2 (cells), not 3.

## 10. Certification checklist (next step — Phase-1 for A)

1. **Index slice (2012-01-02 → 2026-08-21):** **DONE 2026-08-27 — overall
   FAIL with a full defect register** (`A_INDEX_SLICE_CERTIFICATION.md`):
   contiguity (2018-05 + 2023-02 permanent holes, 12 out-of-shape specials),
   completeness (66 partials), validity (45 era-bound issues; zero OHLC/dup/
   monotonic violations), schema PASS, alignment REPORT (vendor boundary
   fidelity as recorded in §1/§3), C6 native first-bar defects (2026-02-25,
   2026-03-02 — wrong-date first bars; excluded by the §2 skip rule). The
   construct amendments (D3 opening print, D4 last-bar-close exit, skip
   rule) are incorporated above.
2. **F&O execution/cost substrate:** **DONE 2026-08-27** —
   `core/execution/futures/futures_fees.py` (13 tests green; 3.81 bp round
   trip at canonical notional); slippage measured era-split (entry p90
   0.66–0.78 bp/side); basis measured 2016–2026 (level + within-contract
   |Δ|, roll days excluded — D5 pending); volume-dominance roll calendar
   built (131 roll dates, 2016-02-24 → 2026-10-26); cadence measured
   (238/yr mean, cell 1). Report:
   `A_COST_SUBSTRATE_MEASUREMENTS.md`.
3. All gates report to a Phase-1 certification report, script-generated, with
   the same audit trail discipline as `ISD_PHASE1_SUBSTRATE_CERTIFICATION.md`.

## 11. What this document does not decide

- The RFA bands (declared and frozen at the RFA step, per gate.py convention —
  candidate band above is arithmetic, not a freeze).
- The sealed-read protocol and spend floor (pre-registration step).
- Whether A is PAPER-then-LIVE (out of scope until research validates).

**Chain:** prior-exposure audit → this definition → substrate certification →
RFA → pre-registration (freeze) → TRAIN. Nothing below this line has been read
at signal level; the audit (dated today) certifies the exposure boundary.
