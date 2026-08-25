# Intraday-Stocks Discovery Program — Design Spec (ISD)

**Date:** 2026-08-24
**Status:** APPROVED — operator decisions frozen 2026-08-24 (§10). Plan document:
`docs/superpowers/plans/2026-08-24-isd-phase-1-substrate-certification.md`.
**Branch:** `research/intraday-stocks-program`
**Origin:** operator directive 2026-08-24 — "I want something in stocks to work
intraday", following the TS Basis de-authorization (protocol break) and a review
of the FTMO edge-discovery corpus (`F:\ftmo\docs\superpowers\
RESEARCH_REPORT_XAUUSD_USTEC100.md` + `STRUCTURAL_EDGE_MAP.md`).

---

## 1. Purpose

Establish a protocol-clean research program for **intraday strategies on NSE cash
equities**, under this repo's standing governance (RFA gate → frozen pre-registration →
TRAIN → HOLDOUT → one-shot SEALED), absorbing the process lessons that killed prior
candidates:

- **PSB-1/PSB-2/F1:** fees and demonstrability are the binding constraints, in that
  order historically; both must be addressed *by construction*, not hoped away.
- **TS Basis Daily (research-only, 2026-08-01):** iterative filter-tuning across TRAIN
  then promotion on HOLDOUT destroys every α claim (m ≫ 1). This program adopts
  FTMO's corrective: **one frozen grid, one ledger, expectancy-first discovery,
  HOLDOUT touched once, SEALED spent once.**
- **FTMO corpus:** simple single-instrument price patterns (ORB, gap-fade, VWAP
  reversion, vol-spike, drift) were a high-power null on USTEC/gold after costs —
  0/41 cells significant positive, max t +1.35. This lowers the prior on repeating
  that family here and pushes the program toward **cross-sectional breadth with an
  external anchor** — the one quadrant neither program has falsified.

## 2. Why intraday stocks is a different quadrant here

| Constraint | Delivery/EOD programs (dead) | This program |
|---|---|---|
| STT | 0.1% **per leg**, both legs | **0.025%, sell leg only** |
| Round-trip cost hurdle | ~13pp/yr at weekly turnover | ~4–8bp + slippage vs ±1–3% intraday stock moves |
| Formations (power) | ~130 monthly / ~55 fortnightly | ~190 names × ~870 sessions → **10⁴–10⁵ cross-sectional observations** (√n escape, CB-N50 lesson) |
| Signal source | EOD bhavcopy factors | Full-session 1m bars + prior-day delivery % + index/VIX regime |

The repo's own history supports the asymmetry: the fee wall was a **delivery**
phenomenon. Intraday was never the domain where costs killed a construct here —
demonstrability was, and intraday cross-sectional breadth fixes demonstrability
arithmetic rather than signal quality.

## 3. Hard guardrails (non-negotiable, inherited)

1. **RFA before any construct code.** Per-family declaration, contract v2
   (`per_trade_pnl` ⇒ annualized-Sharpe band + cadence; `rank_ic` ⇒ δ/SD bands).
   ABANDON is dispositive.
2. **No iterative tuning on any evaluation window.** Grids frozen in the Phase-0
   pre-registration; every cell logged to a trial ledger before running; BH control
   across cells; plateau rule (≥3 contiguous winning parameter cells).
3. **Discover on expectancy / rank-IC t-stat;** path metrics (pass-rate, MaxDD) are
   reported final gates, never discovery lenses (FTMO §4 correction; RFA cadence-
   invariance finding).
4. **Matched nulls per cell** — random entries through identical execution; circular-
   shift nulls for signal-series families.
5. **HOLDOUT once; SEALED once, only after HOLDOUT PASS.** A failed gate retires the
   construct; no successor inherits its windows.
6. **Copy-first substrate discipline** — baseline copies taken *before* any mutation;
   all mutations from committed, re-runnable code (the Gate-A provenance lesson).
7. **Script-generated numbers only** in every report; hand-edited figures forbidden.

## 4. Prior-exposure disclosure

- The 1m store has been consumed by **ops/paper infrastructure** (NiftyShield index
  bars, live buffer, day-type publisher) since 2023. To the operator's knowledge no
  strategy research has read **equity** 1m history; Phase-1 verification included.
- **Delivery-% is a READ factor** (PSB-2's C2, retired). Using prior-day delivery as a
  *conditioning covariate* inside a new construct is permitted only with a
  pre-committed sign and mechanism, disclosed as prior exposure.
- Index-pair findings (Nifty/BankNifty intraday ratio trends, doesn't revert) are
  prior art any index-conditioning feature must acknowledge.

## 5. Data substrate — measured 2026-08-24

### 5.1 Inventory

| Store | Range (measured) | Grain | Notes |
|---|---|---|---|
| Equity 1m per-day files | **2023-01-02 → 2026-08-21**, ~880 sessions | ~188→200 `NSE_EQ\|ISIN` symbols/day, union ≈229 | median 375 bars/symbol/session (full 09:15–15:29), 0% synthetic flags |
| **Vendor archive.zip** (`~/Downloads`, probed 2026-08-24) | **2015-02-02 → 2025-08-06** | 100 tickers (`NIFTY50/*.csv`), `date,open,high,low,close,volume`, ~970k rows/file | UNVERIFIED: naive IST stamps, ticker keys (not ISIN), volume=0 tail bars at post-close times (17:57/20:28), prices appear **back-adjusted** (RELIANCE ≈216 on 2015-02-02 ⇒ retroactive CA adjustment), provenance unknown |
| Index/VIX 1m | 2023-01-02 → present (live via buffer) | Nifty 50, Bank Nifty, India VIX | same era as equities |
| Equity daily candles | 2012-02 → present, certified (G3 closed) | adjusted view available | overnight-gap features; CA ground truth for G7 |
| Delivery % | 2020-01-01 → present (EOD bhavcopy store) | per symbol/day | prior-day conditioning |
| Stock futures/options bhavcopy | 2016-02-11 → 2026-07-20/17 (EOD) | FUTSTK/OPTSTK | expiry calendar, EOD OI only |

The two intraday stores **overlap 2023-01 → 2025-08 on ~100 large caps** — an
independent-source cross-validation opportunity (the Gate-B1 pattern): agreement
there certifies both; disagreement localizes defects.

### 5.2 Known defects (measured 2026-08-24, updated after operator repairs)

| # | Defect | Evidence | Severity |
|---|---|---|---|
| ~~D1~~ | ~~Dec-2024 hole~~ **RESOLVED** — operator refilled 2024-12-02…12-11 (+ 2024-02-29, 2024-11-29). All 53 residual weekday gaps are genuine NSE holidays, **including 2024-11-20** (special NSE closure, Maharashtra Assembly Elections) — zero data-holes remain | gap scan re-run + operator identification 2026-08-24 | closed |
| ~~D2~~ | ~~Post-Aug-7 gap~~ **RESOLVED** — per-day store verified current through 2026-08-21 (200 syms, full sessions) | re-scan | closed |
| D3 | **Schema drift**: `instrument_key` column added from 2026-03-05 (105 files differ) | column-signature scan | normalization required |
| D4 | Store uncertified: no contiguity check ever run on 1m grain; no OHLC validity audit; no duplicate-key audit | CLAUDE.md P2 certification unrun | BLOCKING (DTIL-class fabrication risk) |
| D5 | Vol=0 minutes present (tail-heavy on some sessions) | sampled counts | monitor; illiquid minutes/halts/vendor tails |
| **D6** | Vendor archive unverified: unknown provenance, unknown CA-adjustment basis, post-close junk bars, ticker→ISIN mapping needed | probe 2026-08-24 | BLOCKING for any use before G7 passes |

## 6. Phase 1 — Substrate certification (blocking, precedes everything)

Exit criteria, each scripted into `scripts/isd/`, report generated, **baseline copy
of any mutated store taken first**:

- **G1 Contiguity:** for every eq session, exactly one row per (symbol, minute) over
  the full 09:15–15:29 grid, or an explicit missing-bar ledger with counts; trading
  calendar reconciled against the NSE holiday list **including special closures**
  (2024-11-20 Maharashtra Assembly Elections). Zero unexplained weekday gaps is the
  PASS bar.
- **G2 Currency:** D2 repaired — per-day ingest extended to present (source decision:
  open question Q2) — so the SEALED window is well-defined.
- **G3 Normalization:** single reader abstracting the schema drift (D3); `is_synthetic`
  asserted 0 everywhere or synthetic rows excluded loudly.
- **G4 Validity:** zero OHLC violations, zero duplicate (symbol, timestamp) keys,
  non-negative volumes, price sanity vs prior close (session-gap bounds).
- **G5 Entity/PIT mapping:** ISIN-level identity across the window; PIT F&O-universe
  membership via CSMP `symbol_entity_intervals`; corporate-action cross-check so
  intraday returns spanning ex-dates are flagged, never silently compounded.
- **G6 Cost + slippage model:** era-accurate intraday fee function as code (STT
  0.025% sell; brokerage min(₹20, 0.03%)/order; exchange/SEBI/GST/stamp per current
  NSE schedule), evaluated against the **canonical paper capital of ₹2,00,00,000**
  (operator decision Q4 — ticket sizes, and therefore the fee hurdle every construct
  must clear, derive from this basis) plus *measured* slippage
  bands from the data itself (next-bar-open vs signal-close; minute high–low
  distributions by liquidity decile) — the FTMO "row 11 measurement" lesson.
- **G7 Vendor-archive certification (new, blocking for the deep window):** ingest the
  100-ticker archive only after (a) ticker→ISIN resolution via instrument master with
  PIT awareness (tickers recycle — the DTIL lesson), (b) session fingerprinting
  (open=09:15/close=15:29 mass, holiday alignment, FTMO timezone-resolution lesson),
  (c) OHLC/duplicate audits at vendor grain, (d) junk-bar policy (post-close volume-0
  tails dropped by rule), (e) **cross-validation against the Upstox store on the
  2023-01→2025-08 overlap** (per-bar close agreement bands; disagreement census before
  any reconciliation), and (f) CA-adjustment verification against the certified daily
  adjusted view (split/bonus seams must show zero fabricated overnight returns — the
  four-arm contract pattern). The archive earns the TRAIN window only if G7 passes;
  otherwise it is a measurement artifact and the program runs on the native store.

## 6b. What G7 changes if it passes

Native-store windows (§7) assume ~3 years of equity intraday history. A G7-PASSed
vendor archive extends the cross-section to **2015 → present (~11.5y)** for ~100 large
caps, transforming the power arithmetic: e.g. a daily cross-sectional rank-IC family
moves from ~1.7×10⁵ name-sessions to ~8×10⁵. Phase 0 then chooses between two
declared substrates — **deep-narrow (100 names × 11.5y)** vs **wide-short (~200 names
× 3.5y)** — or pre-registers a pooled design with explicit entity handling; the choice
is frozen in the pre-registration, never revisited after first results.

Certification verdict: PASS per gate or the program stops at the failing gate.

## 7. Phase 0 — Pre-registration (after Phase-1 PASS, separate review)

One document freezing: window fences, universe definition (PIT), the chosen
family/families from §8, exact feature/sign/parameter grids, cell ledger format,
null constructions, BH policy, power probe (MDE stated before sweep), fee/slippage
application points, and the RFA declarations for each family. Proposed fences
(post-repair): **TRAIN 2023-01→2024-11 · HOLDOUT 2024-12→2025-12 · SEALED
2026-01→present** — final fences pinned in Phase 0, never moved after.

## 8. Candidate families (under consideration — NOT commitments)

| # | Family | External anchor | Why not already falsified |
|---|---|---|---|
| A | **Intraday cross-sectional drive/reversal**: rank ~190 names on 09:15–10:00 behavior, banded long-short book, EOD flat | index open drive, prior-day delivery %, VIX regime | PSB tested EOD delivery factors; FTMO tested time-series intraday on indexes; nobody tested intraday cross-sectional price action on stocks |
| B | **Overnight-gap cross-sectional** fade/continuation | gap = accumulated global news while NSE closed (no overnight session) | FTMO H1/H2 analogs were time-series on indexes; cross-sectional stock version untested both repos |
| C | **Expiry-calendar conditioning** on constituents (weekly index expiry days, monthly stock-expiry week) | public clock, forced dealer hedging shadow | FTMO B2 analog never executed (calendar-only reachable); nothing here tests it |
| D | Volume/OI-shock continuation | forced-flow shadow | **weakest data**: OI is EOD-only → flag now, likely dropped at Phase 0 unless a proxy survives G6 slippage realism |

Family selection and grids freeze in Phase 0. Each family carries its own RFA.

## 9. Termination rules

- Any Phase-1 gate FAIL → stop, repair or abandon; no strategy work proceeds.
- RFA ABANDON per family → family dead, declaration retained, successor starts fresh.
- TRAIN fail → family closed (sign/effect dead), no re-grid fishing.
- HOLDOUT fail → construct retired; SEALED untouched.
- SEALED fail → construct dead; the window is spent **for this construct only**.
- Program-level: two consecutive family closures on substrate grounds (not signal
  grounds) triggers a written reassessment before any new family is declared.

## 10. Operator decisions — frozen 2026-08-24

| # | Question | Decision |
|---|---|---|
| Q1 | Window fences | **Deferred to Phase 0** as proposed; once pinned, fences never move. Deep-narrow vs wide-short substrate choice per §6b happens there. |
| Q2 | Missing session 2024-11-20 | **Fenced by calendar, not by data loss** — it was the special NSE closure for the Maharashtra Assembly Elections; no data is missing. Era has zero unexplained gaps. |
| Q3 | Universe | **(a) PIT membership** via CSMP machinery (`symbol_entity_intervals`, ISIN issuer-prefix linkage); a static symbol list is rejected as survivorship-biased. |
| Q4 | Canonical paper capital | **₹2,00,00,000 (₹2 Cr)** — all fee/ticket-size arithmetic in G6 and every Phase-0 cost model derives from this basis. |
| Q5 | Path to SEALED | **(b) A mandatory forward PAPER interval between HOLDOUT PASS and SEALED spend**, length pinned in the Phase-0 pre-registration before any gate runs. |

No open questions remain. The plan document operationalizes Phase 1 only.
