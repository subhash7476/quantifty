# CLAUDE.md — Trading Platform

## Project Overview
Production-grade, deterministic algorithmic trading platform.
- **Language**: Python 3.10+
- **Database**: DuckDB (single source of truth)
- **Broker**: Upstox V2 (REST + WebSocket)
- **UI**: Flask + Tailwind CSS
- **Shell**: Use Unix syntax (forward slashes, `/dev/null` not `NUL`)

---

## Feature-Frozen Components

Components certified as stable and no longer receiving feature changes:

| Component | File | Frozen Since | Notes |
|-----------|------|-------------|-------|
| ParserRegistry | `core/risk/span/span_parser.py` | MM9.5 | Parser registration infrastructure |
| ParserV400 | `core/risk/span/parser_v400.py` | MM9.5 | NSE SPAN v4.00 XML parser |
| SpanSnapshot | `core/risk/span/span_snapshot.py` | MM9.5 | Immutable DTOs |
| SpanRepository | `core/risk/span/span_repository.py` | MM9.5 | Read-only archive access |
| SpanReadiness | `core/risk/span/span_readiness.py` | MM9.5 | Startup readiness evaluation |
| SpanMarginCalculator | `core/risk/span/span_calculator.py` | MM10.2 | Contract-level SPAN margin computation |
| MarginCalculator Protocol | `core/risk/margin_calculator.py` | MM10.1 | Protocol v2 — stable interface |
| ELM Rates | `core/risk/elm_rates.py` | MM10.4 | Regulatory ELM constants — NSCCL source |
| NseMarginEngine | `core/risk/nse_margin_engine.py` | MM10.4 | Margin composition layer (SPAN + credits + ELM) |

## Margin Architecture — Two Authorities (MM10, closed)

- **Sizing/computation authority**: `NseMarginEngine` — sole margin calculator in research, backtest, paper, and LIVE (unchanged in every mode). It is a deterministic implementation of publicly available NSE Clearing margin rules, not a broker RMS clone — perfect broker parity is structurally unreachable at retail.
- **Order-acceptance authority**: the broker RMS, at the gateway only — never consulted for sizing, never overrides `NseMarginEngine`'s computed margin.
- Broker margin reconciliation (fetch/compare/log broker vs. local) is a **deferred LIVE-only capability** — no code exists today; do not build a `MarginProvider` abstraction or a validation-policy config ahead of a concrete need (no production strategy, no funded LIVE account exists yet).
- *(ADR-011, ADR-012, ADR-013 — `docs/ARCHITECTURE_DECISIONS.md`)*

## Architecture Principles (DO NOT VIOLATE)

1. **Strategies Stay Dumb** — emit `SignalEvent` only; no broker/sizing/risk logic inside strategies
2. **Analytics Produce Facts** — all indicators pre-computed offline; runtime is read-only
3. **Execution Owns Reality** — risk, sizing, and broker interaction live exclusively in `core/execution/`
4. **Runner is Neutral** — single-threaded orchestrator; live and backtest data treated identically
5. **Audit-First** — every trade must be explainable by exact analytical facts

### Layer Flow
```
CLI Scripts → DuckDB → Core Logic → Facade → Flask UI
```

---

## Key Directories

| Path | Purpose |
|------|---------|
| `core/execution/` | Risk, sizing, broker interaction |
| `core/brokers/` | Broker adapters — Upstox and PaperBroker |
| `core/brokers/mapping/` | Canonical ↔ Upstox instrument mapping |
| `core/instruments/` | Canonical instrument model, resolver, and master DB |
| `core/runtime/` | LoopDriver, telemetry, signal source contracts |
| `core/analytics/options_analytics.py` | Options structural engine (PCR, GEX, OI, Max Pain) |
| `core/data/options_provider.py` | Upstox V3 option chain fetcher + DuckDB cache |
| `core/messaging/options_publisher.py` | SSE publisher for real-time option chain updates |
| `app_facade/options_facade.py` | Options facade — bridge between Flask UI and core |
| `flask_app/blueprints/options.py` | Options dashboard Flask blueprint (`/options/`) |
| `flask_app/templates/options/index.html` | Options dashboard UI template |
| `flask_app/` | Thin Flask UI — display only, no computation |
| `scripts/fno_runner.py` | F&O live runner (Upstox, PAPER and LIVE modes) |
| `scripts/` | CLI entry points — data ingestion, instrument master, runners |
| `tests/` | Unit and integration tests by domain |
| `docs/` | Architecture docs, reports, and implementation notes |
| `docs/DRIVER_SPECIFICATION.md` | LoopDriver spec and behavior contracts |
| `docs/PLATFORM_CONSTITUTION.md` | Architectural principles and invariants |

---

## Data Layout

- **1-min candles**: `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`
  - Equities (`NSE_EQ|INE...`): 2024-10-17 to present
  - `NSE_INDEX|Nifty 50`: 2023-01-02 to present
  - `NSE_INDEX|Nifty Bank`: 2023-01-02 to present (backfilled Feb 2026, 292K bars)
- **Daily intermarket**: `data/market_data/nse/candles/1d/{date}.duckdb` (Nifty 50, Bank Nifty, India VIX)
  - 3,548 daily files spanning **2012-02-21 → present** after the CARRY G1-R re-ingest (`scripts/ingest_index_history.py`); `timestamp` is uniformly `TIMESTAMP`
  - **`NSE_INDEX|Nifty 50` resolves for all 3,548 files, 2012-02-21 → 2026-07-21.** A 59-session hole (2012-11-15 → 2013-02-07) opened by an ad-hoc deletion on 2026-07-22 was refilled the same day from the operator's niftyindices CSVs via `--fill-from-vendor` (insert-only, snapshot first). **Gate B1 measures max close difference 0.0000 across all 401 overlapping dates**, so every pre-2013 row — including the 182 written by untraceable ad-hoc SQL — is tick-verified against an independent source. A further **11 sessions** (Saturday specials + Diwali Muhurat) were fetched from the archive, and the last **4** the archive 404s (2013-10-09, 2014-03-19, 2014-12-15, 2016-06-20) came from operator single-date CSVs — **3,563 files**, beta from **2013-02-19**. Every real trading session in span now has a file. **A1's sole remaining miss is 2012-11-11 — a Sunday with 14 equity rows**, a bhavcopy artifact to drop from the calendar rather than source. Index CSVs are downloadable per-index from niftyindices.com/reports/historical-data (`CARRY_G1_R4_VERIFICATION.md` §3)
- **Stock/index futures**: FUTSTK + FUTIDX bhavcopy, **2016-02-11 → 2026-07-20**, 363 stock + 13 index underlyings (`scripts/sfb/ingest_futures_bhavcopy_v2.py`). Pre-2016 history is not obtainable
- **Stock options**: `data/market_data/stock_options_bhavcopy.duckdb` — **98,320,092 rows, 2016-02-11 → 2026-07-20, 363 underlyings, zero index names** (`scripts/sfb/ingest_stock_options_bhavcopy.py`). The ingest is **complete**; `SIGNAL_ENGINE_DESIGN.md` §2.1's open check ("verify OPTSTK, not index-only") is **verified true**, so the Skew sleeve is data-unblocked
- **Index options**: `data/market_data/options_bhavcopy.duckdb` — 5,490,319 rows, 2016-02-11 → 2026-07-17
- **Symbol format**: `NSE_EQ|INE...` (equities), `NSE_INDEX|Nifty 50` / `NSE_INDEX|Nifty Bank` (index)
- **ALL NSE_INDEX symbols have volume=0** — never use VWAP or vol_z filters on index data
- **BankNifty ingest script**: `scripts/fetch_intermarket_data.py --include-1m` (uses 10-day chunks for 1m — 29-day chunks cause sporadic 400s)

---

## Backtesting Rules

- **Disable idempotency guard**: `execution._is_signal_already_executed = lambda sid: False`
- **90-day warmup**: data loading extends before `start_time` for indicator computation
- **Swing detection is CAUSAL**: use `result.iloc[i + period]` assignment — never centered window
- **Position stacking guard**: handler must block new entry while a position is open on same symbol
- **Position tracker must update on paper fills**: `FillEvent` → `position_tracker.update_from_fill()`
- **Fee model**: NSE equity intraday — Rs 20 brokerage + STT 0.025% + exchange/SEBI/GST/stamp

---

## Production Strategy Status

- No production strategy currently exists in this repository.
- The strategy layer (`core/strategies/`) is intentionally unimplemented — greenfield.
- Future strategy work must be designed fresh against the current infrastructure.
- Architectural decisions must not assume any specific future strategy.
- Historical strategy designs (NiftyShield, PixityAI) existed in a prior codebase and were not ported during the SALVAGE migration (2026-06-04).

---

## PSB-1 — Panel Screening Battery, Increment 1

**Status:** CLOSED 2026-07-14. Outcome: **"no winner recommended"** — the protocol worked as designed. PSB-2 authorized as the successor.

### Summary
Screened 5 candidates (C1–C5) on dev data (2012–2022) against the CSMP-certified equity store + NIFTY-200 point-in-time universe. The delivery-percentage field (NSE's unique advantage) anchored C3/C4. Every candidate ran through the frozen `PSB1_PROTOCOL.md` Rev 2: exact §5 formulas, Spearman rank IC, net top-quintile spread under gate-(d) era-accurate fees + κ=5bp/side slippage, §4.2 imputed-forward-return robustness column, §7 power projection against the 2023–2026 sealed window (≥0.80 hurdle), Bonferroni-deflated selection (m=5).

### Phase 2 Results (all numbers script-generated, no hand-edited numbers)

| Cand | n | Mean IC | t | p | Power δ | Q1-Q5 gross | Net spread | Fee drag | Outcome |
|---|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|---|
| C1 reversal (weekly) | 569 | +0.023 | 3.76 | 9e-5 | 0.68 | +1.1% | −16.8% | 1293 bp | Not eligible (net<0, power<0.80) |
| C2 residual rev (weekly) | 529 | **+0.035** | **6.63** | **4e-11** | **0.99** | **+14.9%** | −8.6% | 1422 bp | Not eligible (net<0) |
| C3 delivery z (weekly) | 143 | +0.025 | 2.93 | 0.002 | 0.95 | **+17.5%** | −2.5% | 1384 bp | Not eligible (net<0) |
| C4 C1×C3 (weekly) | 143 | −0.003 | −0.42 | 0.66 | 0.02 | −0.3% | −16.1% | 1677 bp | Not eligible |
| **C5 low-vol (monthly, banded)** | **131** | **+0.068** | **3.14** | **0.001** | 0.54 | **+16.2%** | **+4.3%** | **14 bp** | Closest — clears IC+spread, misses power |

### Fee finding — the dominant structural constraint
- Delivery-equity STT is **0.1% per leg** (vs intraday 0.025% sell-only). At weekly cadence with ~0.80 turnover, the **STT alone** imposes ~13pp/yr cost — no known Indian equity cross-sectional effect clears a 13pp hurdle. C1–C4 all confirm this: gross Q1-Q5 spreads of +1% to +17% are consumed by 12–17pp/yr fee drag.
- C5 clears fees via **monthly cadence + banded exit** (0.40 exit band). Turnover drops to ~0.04, fee drag to ~14 bp/yr.
- The STT is the binding constraint, not the signal. Any candidate that clears fees at all will almost certainly clear IC and power.

### Substrate — certified
The `equity_bhavcopy_adjusted` view (7,030,920 rows) is certified by the four-arm contract suite (`scripts/psb1/contract_arms.py`): zero structural filters, entity grain, the whole panel. Six structural defects were repaired across Prompts 2–5: entity-grain cumulative factors (rename seams), time-aware entity resolution (recycled DTIL ticker), series-crossing prev_close LAG (246 cells), the DVL→DTIL mis-key (NSE feed error), the evidence-screen blind spot (f≥0.75 no-reprice), and ISIN issuer-prefix entity fragmentation. The adjusted-series continuity invariant returns 0 view-induced fabrications.

### Key files
| File | Purpose |
|------|---------|
| `scripts/psb1/screening_harness.py` | PSB-1 harness: loader, grids (§3), C1–C5 scoring (§5), metrics (§6), power (§7), AC₁/Newey–West |
| `scripts/psb1/certify_substrate.py` | Four-arm contract suite (Arm A–D) + structural guard runner |
| `scripts/psb1/contract_arms.py` | The contract test library (intra-symbol CA-shape, cross-symbol handoff, prev_close identity, factor evidence) |
| `scripts/psb1/disposition_register.py` | Committed disposition register (ETF splits, demergers, store exceptions) |
| `scripts/psb1/repair_*.py` | Prompt-specific validate-then-apply runners (copy-first discipline) |
| `scripts/csmp/build_universe.py` | Universe membership + `symbol_entity_intervals` + ISIN issuer linkage |
| `scripts/csmp/ingest_corporate_actions.py` | `build_adjusted_view()` (entity-grain, time-aware), factor overrides (DVL→DTIL), orphan invariant, evidence screen |
| `core/execution/equity/delivery_fees.py` | Era-accurate NSE delivery-equity fee model (STT both legs, stamp, NSE/SEBI/GST, DP per sell line) |
| `docs/reports/PSB1_PROTOCOL.md` | **FROZEN Rev 2** — the pre-registered screening protocol |
| `docs/reports/PSB1_PHASE0_RESEARCH_RECORD.md` | Phase 0 brainstorm, operator decisions D1–D7 |
| `docs/reports/PSB1_C{1..5}_REPORT.md` | Script-generated candidate reports |
| `docs/reports/PSB1_SUBSTRATE_CERTIFICATION.md` | Substrate certification report (four-arm contract) |
| `tests/psb1/` | 38 tests (scoring unit tests + contract arm unit tests) |

### PSB-2 — authorized, executed, CLOSED
See the PSB-2 section below.

---

## PSB-2 — Panel Screening Battery, Increment 2

**Status:** CLOSED 2026-07-17. PSB-2 outcome: **C2 recommended** — the battery's sole eligible candidate cleared all three §8 criteria and the evidence floor. A recommendation only: no sealed read consumed, no strategy code, no allocation.

> **⚠️ C2 RETIRED 2026-07-18 — this is the terminal state.** After PSB-2's recommendation, C2 was carried into pre-sealed-read Phase 0 evidence-strengthening (0.4 delivery-backfill + SD re-estimation, 0.5 turnover-reduction mini-battery). It did not survive: on extended-history TRAIN 2011–2018, **no variant cleared power ≥ 0.80**, and net spread stayed negative under delivery-equity STT *even at reduced turnover* (V2's 0.288→0.168 lifted net only −0.43%→−0.14%). This is the PSB-1/PSB-2 fee-dominance result a third time — no turnover setting rescues a sub-gross-of-fees construct. Phase 0 killed C2 **before a single sealed read was spent**: the **2023–2026 window remains sealed and unread; HOLDOUT 2019–2022 unspent.** No successor is authorized by this outcome — any new construct starts its own pre-registration. Terminal artifacts: `docs/reports/C2_PHASE0_5_MINIBATTERY.md` + `C2_PHASE0_5_LEAD_REVIEW.md` (commit `394b2d6`).
>
> The Phase 2 / §8 record below is preserved as PSB-2's *own* finding as of 2026-07-17; read it as history, not as a live recommendation.

### Summary
The fee-survivable successor to PSB-1. Three constructs (C2–C4), each designed to clear the cost structure *by construction* rather than hoping a signal outruns it. Substrate (`equity_bhavcopy_adjusted`, 7,030,920 rows) and harness reused from PSB-1. Dev data fenced at 2022-12-30 (fence proven each run: fenced MAX ≠ unfenced MAX 2026-07-09); the 2023–2026 window remains **sealed and unread**. Ran against frozen `PSB2_PROTOCOL.md`: §7 power projection vs. the sealed window (≥0.80 hurdle), Bonferroni-deflated selection at **m = 3** (pinned pre-results; C1/C5 dropped for data-independent reasons and so cannot inflate the penalty).

### Phase 2 / §8 Results

| Cand | Construct | Cadence | n | Mean IC | Net spread | Power | Fee drag | Outcome |
|---|---|---|--:|--:|--:|--:|--:|---|
| **C2** | Delivery-% anomaly (delivery z), banded 0.40 | fortnightly | 55 | **+0.0349** | **+4.57%** | **0.9198** | 270.3 bp | **ELIGIBLE — recommended** |
| C3 | Delivery-conditioned reversal | fortnightly | 55 | +0.0083 | −1.10% | 0.1816 | 444.7 bp | Not eligible (net<0, power) |
| C4 | Momentum, long-only, staggered 6-mo hold | monthly | 131 | +0.0466 | +2.87% | 0.4110 | **35.2 bp** | Not eligible (power) |

n* = 84 fortnightly / 42 monthly. C2 deflated p = min(1, 3 × 7.994592e-03) = **0.023984 < 0.05** → evidence floor PASS.

### What the battery found
- **The fee constraint held a third time.** C3 (fortnightly delivery-conditioned reversal) died exactly as PSB-1's weekly C3 did — turnover 0.4683 → 444.7 bp/yr drag → net −1.10%. Across two batteries, sub-monthly delivery signals do not survive STT.
- **C4 is PSB-1's C5 story repeating.** Best mean IC (+0.0466) and best fee structure (35.2 bp/yr) in the battery, dropped **by rule** at power 0.4110 — SD_IC 0.208949 over 131 formations is too noisy to project 0.80 at n* = 42. A good construct is not the same as a demonstrable one.
- **C2 cleared fees despite missing its own design estimate.** Turnover came in 0.2701 vs. ~0.15 designed (drag 270.3 vs. ~78 bp/yr) and the net spread survived anyway. Disclosed, not buried; no parameter was tuned toward the estimate.
- **The AC₁ threat did not materialize.** All three AC₁ negative (C2 −0.1818). The largest disclosed threat to a fortnightly candidate — inflated simple-t from overlapping formations — is absent in this data, so C2's power is not flattered by autocorrelation.

### Carry-forward caveats (do not lose these)
- **C2's recommendation is a power projection resting on a 55-observation, 2.3-year SD estimate.** `deliv_pct` begins 2020-01-01 and the 252-day baseline pushes the earliest feasible formation to 2020-09-04, so this is the *entire* available span — nothing held in reserve. Power is a function of SD. *(This caveat was borne out: when Phase 0.5 re-estimated on extended-history TRAIN 2011–2018, the mean IC weakened to +0.023 and no variant projected power ≥ 0.80 — the retirement above. The projection did not survive a wider SD estimate.)*
- **Known limitation in the selection artifact (documented, frozen — not repaired).** `PSB2_SELECTION_REPORT.md`'s §10 digest (`fad88aac14decee3`) covers only the report body through §7; the "Predictions verified" section is appended after the hash and sits outside the seal, and predictions 1/2/4/7 are hardcoded PASS strings rather than computed. **The claims were independently verified true** in lead review — the report's stated mechanism is overstated, its numbers are not wrong. Left frozen rather than re-run, since a fix moves the digest on a terminal artifact. Full detail: `PSB2_PROMPT3_LEAD_REVIEW.md`.

### Key files
| File | Purpose |
|------|---------|
| `scripts/psb2/harness.py` | PSB-2 harness: grids, C2–C4 scoring, §6 metrics, §7 power, selection constants |
| `scripts/psb2/run_phase2.py` | Candidate battery runner → `PSB2_C{2,3,4}_REPORT.md` |
| `scripts/psb2/run_phase3.py` | §8 selection runner → `PSB2_SELECTION_REPORT.md` |
| `docs/reports/PSB2_PROTOCOL.md` | **FROZEN** — the pre-registered protocol (§8 selection rule, m=3 rationale) |
| `docs/reports/PSB2_PHASE0_RESEARCH_RECORD.md` | Phase 0 slate + operator decisions (incl. D2 prior-exposure, D11/D12) |
| `docs/reports/PSB2_C{2,3,4}_REPORT.md` | Script-generated candidate reports |
| `docs/reports/PSB2_SELECTION_REPORT.md` | Script-generated §8 selection report — **C2 recommended** |
| `docs/reports/PSB2_PROMPT3_LEAD_REVIEW.md` | Lead review of the selection report (ACCEPT; MEDIUM-1 digest finding) |
| `scripts/c2_phase0_5_minibattery.py` | Phase 0.5 turnover-reduction mini-battery runner (S4 slate: V1–V3) |
| `docs/reports/C2_PHASE0_5_MINIBATTERY.md` | Phase 0.5 report — **NO WINNER** (no variant power ≥ 0.80 on TRAIN) |
| `docs/reports/C2_PHASE0_5_LEAD_REVIEW.md` | Phase 0.5 lead review — **retire C2 CONFIRMED**, sealed window preserved |
| `tests/csmp/test_phase0_5.py` + `tests/psb2/test_fidelity.py` | Phase 0.5 + fidelity tests — 15/15 green at close |

### Successor — none authorized (C2 retired)
PSB-2 §12 gave C2's win the right to *propose* a successor pre-registration — but C2 was retired in Phase 0 before that path was taken (see the retirement banner above), so **no successor is authorized by PSB-2's outcome.** Any future construct starts its own pre-registration from scratch: pin its own α, execution conventions, and sealed-read mechanics; state its own view on the SD estimate; disclose the prior CSMP momentum read as prior exposure (D2); and **not** inherit C2's substrate assumptions as settled. **Promotion never happens inside a screening battery, and a retired candidate hands nothing forward.**

> Recurring temptation to guard against: reopening C2 with post-hoc, in-sample-tuned execution overlays (e.g. intraday TP/SL brackets fitted to observed 2012–2022 MFE/MAE excursions). This was raised and declined 2026-07-18 — brackets can only *add* delivery round-trips (turnover floor is set by formation cadence), so they worsen the exact STT constraint that retired C2. If path-dependent exits are worth testing, they are a **new pre-registered candidate** with train/holdout/sealed structure and an exit rule pinned *before* seeing path data — never a C2 reopen or bolt-on.

---

## SFB-1 / F1 — Stock-Futures Battery, Increment 1

**Status:** CLOSED 2026-07-20. Outcome: **NO-GO on the vendor-data spend.** No futures history was purchased, no battery was pre-registered, no strategy code exists. **The 2023→present sealed window remains untouched; HOLDOUT 2019–2022 was spent only inside the cash-synthesized screen, never on a real futures panel.**

> **⚠️ Verdict override — read before citing the report.** `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md` (run 2026-07-20T16:09:08) prints **GO**. **That verdict is superseded and must not be acted on.** The screen's `decide()` implements only two of spec §6's three GO conditions — it never evaluates the "MaxDD-scaled return a power-deflated battery could plausibly clear" clause, which this run fails outright (TRAIN return/MaxDD ≈ 0.23 on a −45.7% drawdown). Full reasoning: `docs/reports/F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md`. The report was left as-generated rather than re-run, because re-deriving a threshold *after* seeing the results table is the same post-hoc sin the review faulted elsewhere.

### Why F1 closed

Four findings, in decreasing order of weight (`F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md`):

- **§6's MaxDD condition was never evaluated.** TRAIN: ~+10.3%/yr net against a **−45.7%** MaxDD on a ≤10-name book (return/MaxDD 0.23). HOLDOUT clears (1.06); TRAIN does not.
- **The bracket was selected into near-inactivity — so F1 reduced to the thing it was meant to differ from.** TRAIN grid search picked `n=5` (window minimum) with `k_sl=2.5`/`k_tp=5.0` (both maxima). Since only the month-end fallback can produce a hold beyond 5 bars, the reported `DaysH` of **18.8** means the large majority of trades never triggered the bracket. Strip it and F1 is plain monthly-rebalanced 12-1 cross-sectional momentum. Note the grid-boundary result is **not** "the optimum lies outside the grid" — with levels wide enough never to be touched the objective is *flat* in that dimension, so the argmax is noise.
- **TRAIN expectancy is not statistically distinguishable from zero at any slippage setting** — bootstrap CI includes zero at optimistic, mid, and pessimistic alike. (This is *not* a §4 conservatism-invariant violation: point estimates are positive across the full band, so §4 is satisfied. It is the reason §6's undefined "robustly" must be pinned before any real battery.)
- **The GO rested on one favorable regime.** HOLDOUT 2019–2022 (n=47) spans the COVID crash and the 2020–21 momentum rally. "Genuinely fine, TRAIN noisy" and "caught one hospitable regime" are not separable at that sample size, and the screen retired power analysis by design (§5).

### The load-bearing lesson — the binding constraint migrated

**PSB-1 C1–C4 died on fees.** Once constructs were engineered to clear fees *by construction* — C5 (monthly+banded, 14 bp/yr), C4 (35 bp/yr), C2 (reduced turnover) — every one of them died on **demonstrability** instead: power 0.54, power 0.4110, and for C2 a compound fees-and-power failure. F1 fails the same way in its own framework (CI includes zero), though "demonstrability" is the correct umbrella rather than "power" — F1 retired the rank-IC/noncentral-t machinery, so its CI failure is not a power result.

**The consequence: demonstrability is sample-size × effect-size, and for monthly cross-sectional equity both are roughly fixed.** At IC ~0.03 with SD ~0.2, clearing power 0.80 needs on the order of 350 monthly formations (~29 years); the dev window holds ~130. That is arithmetic, not signal quality — **it will not yield to a better monthly cross-sectional signal.** Treat this as strongly indicated rather than proven: the effect-size inputs are themselves the prior-exposed reads.

**This also corrects the SFB rationale.** The screen accidentally tested "does momentum survive futures fees" — but fees were never this signal family's binding constraint. If futures are ever revisited, the honest case is that their **fee structure** permits strategies cash equity cannot support — *never* because of cadence. Higher cadence buys no statistical power: `ncp = (delta/sd)·√n = S·√T` — cadence `c` cancels because multiplying formations by `c` divides per-formation Sharpe by `√c` (see the RFA section). The only escapes from the demonstrability wall are a longer calendar window or a genuinely higher Sharpe.

### Substrate gate — resolved after the fact, and not by a purchase

> **⚠️ SUPERSEDED 2026-07-21 by the CARRY track's ingest.** The paragraph below was true when F1 closed and is false now: **stock-futures history exists in the repo** — FUTSTK/FUTIDX bhavcopy 2016-02-11 → 2026-07-20, 363 stock + 13 index underlyings, ingested free from NSE (`scripts/sfb/ingest_futures_bhavcopy_v2.py`). What remains true is the part that mattered: **history before 2016 is still not obtainable**, so the calendar lever is exhausted at n*≈42 monthly formations, and **no vendor purchase was ever authorized or made.** F1's NO-GO stands on its own reasoning (§6 MaxDD, CI includes zero) — it is not rehabilitated by the data arriving.

At F1's close the repo had **no stock-futures price history** (only the instrument master `nse_fo_instruments.duckdb`). NSE has locked down historical F&O bhavcopy and Upstox cannot backfill expired contracts (`F1_UPSTOX_INGESTION_DETERMINATION.md`). The feasibility screen existed precisely to decide whether to buy GDFL/TrueData history rather than buy blind — **it returned NO-GO, so no purchase is authorized.** The screen cost ~$0 and killed the spend; that is the protocol working as designed.

### Successor — none authorized

**Do not treat F1's closure as licence to re-run F1 with a widened bracket grid, a MaxDD threshold chosen now, or a longer futures panel.** Any future construct starts its own pre-registration and must clear a **power-feasibility pre-check before any construct code is written**: given a plausible effect-size range and the formations actually available, compute maximum achievable power and abandon anything that cannot clear 0.80 even under optimistic assumptions. That gate is free, touches no data, and would have saved the back half of C5, C4, and F1 — tested, not assumed; see `docs/reports/RFA_RETROSPECTIVE.md`. C2 is the exception: as PSB-2 recorded it, C2 clears the hurdle and the gate would have said PROCEED.

### Key files
| File | Purpose |
|------|---------|
| `docs/reports/F1_FEASIBILITY_SCREEN_SPEC.md` | The screen's pre-analysis spec (§0 caveats, §6 decision rule) |
| `scripts/sfb/f1_feasibility_screen.py` | Cash-synthesized screen harness |
| `docs/reports/F1_FEASIBILITY_SCREEN_REPORT.md` | Script-generated run — **prints GO; superseded, see override banner** |
| `docs/reports/F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md` | **Terminal artifact** — NO-GO reasoning (V1–V5) |
| `docs/reports/F1_FEASIBILITY_SCREEN_REPORT_REVIEW{,_2}.md` | Corrective-pass reviews (R1–R12, B1–N2, A1) |
| `docs/reports/F1_UPSTOX_INGESTION_DETERMINATION.md` | Why futures history cannot be self-sourced |
| `tests/sfb/test_f1_feasibility_screen.py` | Screen tests |

<details>
<summary>Original Phase 0 design (historical — read as history, not as a live plan)</summary>

The successor research path after the cash-equity `C#` sequence (C1–C5) closed. **F1** (Futures-1) was the first candidate of a new **SFB** lineage — a deliberate namespace break from the retired `PSB`/`C#` cash-equity constructs. Core shift: **cash/delivery equity → liquid single-stock futures**, intended to dissolve the delivery-STT fee wall that killed every prior sub-monthly construct (the new binding cost assumed to be **slippage/impact in a concentrated ≤10-name book**, not STT).

- **Construct:** intraday-bracketed (conservative daily-OHLC: open-gap → worst-case whiplash → High/Low intercept → Friday-close fallback), concentrated (≤10 names) 12-1 cross-sectional momentum. Brackets are **ATR-scaled and TRAIN-fold-selected — never read off observed excursions** (the concrete "not a C2 reopen" discharge; permitted exactly by the C2 guard note above).
- **Evaluation departs from PSB:** rank-IC / noncentral-t is retired (invalid on ≤10 names); F1 uses portfolio-level Expectancy / Max DD / Days-Held / Turnover-Drag with a **block-bootstrap** power projection.
- **BLOCKING GATE:** the repo has **no stock-futures price history** — only the instrument master `nse_fo_instruments.duckdb`. F1 cannot run until a **Phase −1** operator-authorized NSE F&O-bhavcopy ingestion + contract-shaped certification (roll-adjusted continuous series, PIT F&O-eligible universe, era futures fee model) is complete. This precedes freeze because roll-trigger feasibility is data-structure-dependent.
- **Windows:** TRAIN 2012–2018 / HOLDOUT 2019–2022 / **SEALED 2023→present (untouched).**
- **Key files:** `docs/reports/F1_PHASE_0_PRE_REGISTRATION.md` (DRAFT stub), `docs/reports/F1_PHASE_MINUS1_INGESTION_PROMPT.md` (implementer prompt for the substrate). Freeze artifact `F1_PROTOCOL.md` was never written — certification never passed.

</details>

---

## RFA — Research Feasibility Assessment (power pre-check)

**Status:** Active gate. Every new research construct must clear it **before any construct
code is written.**

The RFA answers one question: given the formations actually available and an independently
defended effect-size band, can this construct reach power 0.80 even under assumptions more
generous than anyone believes? It reads no market data, so it is free.

- **ABANDON is dispositive.** **PROCEED means "not provably infeasible"** — a floor, never
  authorization, and never a statement about fees or MaxDD.
- **Contract v2 / `METHODOLOGY_VERSION` 2.0.0** (2026-07-21). For
  `metric="per_trade_pnl"` the declared quantity is an **annualized Sharpe band plus
  `cadence_per_year`** — *not* separate delta and SD bands (supplying both is rejected).
  For `metric="rank_ic"` the original delta/SD bands remain, because IC mean and IC
  dispersion are separately estimable and independence is defensible.
- **Why Sharpe for PnL:** mean and SD of per-trade P&L are estimated off the same series,
  so "high mean **and** low SD" is itself a Sharpe claim. Declaring them separately is
   over-parameterised and lets a crossed corner smuggle in an effect size nobody defended.
   Since `ncp = (delta/sd)·√n = S·√T`, cadence cancels and only Sharpe matters.
- **Cadence invariance:** because `ncp = S·√T`, trading weekly instead of monthly
  multiplies formation count by ~4 but divides per-formation Sharpe by √4 — the two
  exactly offset. **Higher cadence buys no statistical power.** The only escape from
  the demonstrability wall is a longer calendar window or a genuinely higher Sharpe
  (see SFB-1/F1 section for this finding applied to futures).
- **O1 is WITHDRAWN** (2026-07-21) — the sole real declaration (Nifty VRP, `o1_vrp.py`)
  returned PROCEED via a crossed-corner artifact (see `RFA_GATE_O1_REVIEW.md` §1).
  Withdrawal preserves the declaration file and its digest; no successor is authorized.
- **FLOW: ABANDON** (2026-07-22, `flow.py`, SHA-256 `d7a54cfb…`) — **the gate's first real
  kill, and it worked exactly as designed.** Max achievable power **0.6053** at n*=42; even
  the optimistic corner (δ=0.030 / SD=0.10) needs **71** monthly formations, central 241,
  pessimistic 892. Futures history cannot predate 2016, so n* cannot be raised. **Verified
  independently — all four figures reproduce exactly from `scripts/rfa/power.py`.** Flow
  receives **no TRAIN read**. Cost: one declaration file, zero data reads.
  *Consequence:* the engine is the **3-sleeve case** (Carry+Trend+Skew, central ≈ 0.75), and
  0.80 is now faced empirically by the composite after ≥2 TRAIN reads. A 3-sleeve engine
  settled on realized ICs is a valid outcome; the 4th sleeve was correctly **not** forced in.
- Bands are **frozen at approval** (SHA-256 over the whole declaration file) and cannot be
  revised in response to results.

| File | Purpose |
|---|---|
| `governance/rfa/declaration.py` | Frozen input contract + validation |
| `governance/rfa/declarations/` | One declaration module per candidate |
| `scripts/rfa/power.py` | Noncentral-t power + formation-count inversion |
| `scripts/rfa/gate.py` | Optimistic-corner verdict; `METHODOLOGY_VERSION` |
| `scripts/rfa/report.py`, `run_rfa.py` | Report generation |
| `scripts/rfa/retrospective.py` | Non-binding retrospective |
| `docs/reports/RFA_RETROSPECTIVE.md` | Retrospective output |
| `docs/reports/RFA_GATE_O1_REVIEW.md` | O1 review — withdrawal finding (§1) |
| `governance/rfa/declarations/flow.py` | **FLOW declaration — frozen, ABANDON** (SHA-256 `d7a54cfb…`) |
| `docs/reports/FLOW_RFA.md` | FLOW gate report — max power 0.6053, verified reproducible |
| `docs/reports/RFA_V2_REMEDIATION_PROMPT.md` | V2 remediation plan (Tasks 1–5) |
| `docs/superpowers/specs/2026-07-20-rfa-power-feasibility-gate-design.md` | Design |

**Retrospective correction.** This repo previously implied the pre-check would have saved C5,
C4, C2, and F1. Tested: it fires on C5, C4, and F1, but **not** on C2 as PSB-2 recorded it
(power 0.9198 — the gate would have said PROCEED). C2 fails only on the extended-history SD
re-estimate. The gate's verdict is only as good as the declared SD, which is why SD must be
independently defended rather than inherited from a short in-sample read.

---

## Signal Engine / CARRY — Implementation complete, production-metrics built

**Status:** Research validated, production path built and parity-verified. **Carry is the platform's
first production-ready strategy — validated on TRAIN (burned for sign), HOLDOUT (confirmed), and
SEALED (one-shot PASS at +20.52%).** The strategy was NEVER run over SEALED; metrics are
snapshot-ingested per `CARRY_SEALED_READ_PROTOCOL.md` §2.

| Gate | Status | Detail |
|---|---|---|
| RFA | PROCEED | `governance/rfa/declarations/carry.py` (SHA `4b589e2f…`) |
| TRAIN | Burned | v1 sign discovery (IC +0.041, wrong sign); v2 registered positive sign |
| HOLDOUT | PASS | IC +0.046, t=2.60, p=0.016, net +6.96% |
| SEALED | PASS | One-shot, IC +0.061, net +20.52% (`CARRY_SEALED_SNAPSHOT.json`) |
| Parity gate | PASS | LoopDriver REPLAY reproduces research at +0.0 bp both windows |
| Production metrics | Built | `CarryMetricsDB`, full replay harness, A5-gated report generator |
| Tests | 44 passing | `tests/portfolio/test_carry_rebalancer.py` (28) + `test_carry_metrics.py` (3) + `test_carry_metrics_db.py` (13) |

### Sleeves
Breadth thesis: composite power from weakly-correlated sleeves over ~180-name SSF universe. Seven constructs attempted: one production-validated (Carry), one sealed-but-de-authorized (TS Basis), one sealed-failed (IVOL), four dead at TRAIN/RFA.

| Sleeve | Status | Gate progression | Notes |
|---|---|---|---|
| **Carry** (residual basis, +sign) | **Production-ready** | TRAIN→HOLDOUT→SEALED all PASS | HOLDOUT IC +0.046; SEALED IC +0.061, net +20.52% (`CARRY_SEALED_SNAPSHOT.json`); full rebalancer/metrics/paper infra built. Beta+sector neutralized, monthly, ADV-capped, banded |
| **TS Basis** (basis *level*, +sign) | **SEALED de-authorized** (selection defect; signal NOT falsified) | TRAIN net +18.4%, HOLDOUT INCONCLUSIVE, SEALED read taken 2026-07-24 | HOLDOUT IC gate used Pearson not the pre-registered Spearman → recomputed p=0.0313 > α=0.025, so the sealed window was opened on a gate that didn't hold. The SEALED itself is strong (IC +0.077, t=5.89, p=3.1e-07, net +22.57%, pre-reg SHA `07265b50…`) but reached via the broken gate — a multiplicity/selection concern, not a signal-quality concern. PAPER-candidate; only forward paper months can resolve the de-authorization |
| **IVOL** (idiosyncratic vol, −sign) | **SEALED FAIL** (regime flip) | TRAIN PASS, HOLDOUT PASS, gate-4 composite PASS (0.9854), SEALED FAIL | TRAIN IC −0.055 net +5.96%; HOLDOUT IC −0.0295 net +2.16%; SEALED sign-flipped (IC +0.018, net −13.78%). Sealed window spent for this construct. Carry↔IVOL signal ρ=−0.04 (genuinely decorrelated). Construct: 60-day realized vol, beta+sector neutralized (`IVOL_*` reports, declaration SHA `d7ebcbcc…`) |
| **Trend** (vol-scaled TSMOM) | TRAIN FAIL | §9 gate 2 FAIL | IC +0.022, t=1.13, p=0.131 — insignificant; second-half IC decayed to −0.010 |
| **Skew** (risk-reversal, ±sign) | TRAIN FAIL | §9 gate 2 FAIL | IC −0.018, t=−1.15, p=0.255 — insignificant |
| **LAG** (sector lead-lag diffusion) | TRAIN FAIL | §9 gate 2 FAIL | IC −0.031 wrong sign, t=−1.43; 58% subsumed by Trend (momentum-in-disguise guard fired). Pre-reg SHA `82ed96f9…` |
| **Flow** (OI dynamics) | RFA ABANDON | RFA gate killed | Max power 0.6053 < 0.80; the gate's first live kill |
| **TS Basis Daily** (basis *level*, +sign, **daily**) | **RESEARCH-ONLY — no promotion path** (operator decision 2026-08-01) | TRAIN net +60.23%, HOLDOUT net +41.44% (quintile); top-5: TRAIN +85.42%, HOLDOUT +94.43% — **all in-sample or selection-contaminated; none is out-of-sample evidence** | Daily mirror of TS Basis monthly; `LOOKBACK_ROWS = 252` **row** window (NOT the monthly's 504 calendar days), MIN_OBS 12, winsorized ±3. **TRAIN (1,202 formations) and HOLDOUT (495) are both burned as SELECTION surfaces** — the `basis_reverting` filter was chosen on TRAIN and promoted on a HOLDOUT accept/reject check (`48f83bb`), TP@0.5% set on both (`4521b86`), an ML filter trained across all three (`80f5e86`), a sector cap tried and reverted (`9c97c98`→`e113f6b`). So m ≫ 1 and no α is justified. **SEALED 2023-01-01 → 2026-07-24 (876 formations) is PRESERVED UNSPENT** — `run_sealed.py` refuses to run. Never frozen, never gated; the declaration is retained as a record of error, not as a live candidate. Full detail: `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §B. Scripts: `scripts/signal_engine/ts_basis_daily/` + `scripts/ts_basis_daily_*.py` |

**Composite status:** the only standalone-validated sleeve is **Carry**. TS Basis's SEALED is de-authorized (gate defect, not signal defect) and stands as a PAPER candidate; its resolution requires forward paper time, not more in-sample reads. **TS Basis Daily** is **research-only by operator decision (2026-08-01)** — no promotion path, never frozen, never gated; its TRAIN and HOLDOUT are selection surfaces and its 876-formation sealed window is deliberately preserved unspent. The 2023→2026 out-of-sample budget is spent (Carry PASS, TS Basis de-authorized, IVOL FAIL), and futures history cannot predate 2016 — so no unread confirmatory window remains for a new basis-family construct. A Carry+TS-Basis 50/50 blend shows diversification benefit on TRAIN+HOLDOUT (advisor's decision-support estimate: Sharpe ~2.09 vs Carry-alone ~1.72, L/S return ρ=0.46; *not a gated read* — TRAIN is burned for Carry sign-discovery, so this is a ranking estimate, not forward evidence). Basis-momentum (the basis *change*, distinct from TS Basis the basis *level*) is analytically available but has no unread window to confirm in.

### Production infrastructure
| File | Purpose |
|---|---|
| `core/strategies/carry_strategy.py` | Dumb formation-date `SignalEvent` emitter |
| `core/execution/portfolio/carry_rebalancer.py` | `CarryRebalancerHook` — LoopDriver rebalance seam, `compute_target_book`, `summarize_rebalance`, `RebalanceMetrics` |
| `core/execution/portfolio/carry_metrics_db.py` | DuckDB schema + writer (4 tables: run_metadata, rebalance_summary, rebalance_positions, equity_curve) |
| `scripts/carry_paper_replay.py` | LoopDriver REPLAY over TRAIN+HOLDOUT; SEALED snapshot ingest; writes `production.duckdb` |
| `scripts/carry_production_report.py` | Auto-generated report from `production.duckdb` (gated on A5 parity PASS) |
| `scripts/carry_paper_runner.py` | PAPER mode entry point (live `LiveDuckDBMarketDataProvider`, not REPLAY) |
| `tests/portfolio/` | 44 tests across rebalancer (28), metrics (3), metrics DB (13) |

### Substrate status (data-quality baseline)
| Gap | State |
|---|---|
| Futures↔spot join | **100.00% — 0 misses across all 477,577 FUTSTK cells** |
| G1 index history | Gap **closed** (vendor fill + archive + operator CSVs); Gate A + B ALL PASS; 16 sessions still absent (Saturday specials, Diwali Muhurat) |
| G2 sector classification | **G2-R done** — 0 unclassified |
| G3 equity tail | **Closed** — 7,052,381 rows, 0 duplicate keys |
| G5 ISIN linkage | **Closed** — all 11 sealed-window F&O underlyings mapped |
| P2 substrate certification | **Unrun** |

### Before freeze (blocking, operator — not blockers for PAPER mode)
1. Drop **2012-11-11** (Sunday, 14 equity rows — bhavcopy artifact) from the trading calendar, then re-scope B2.
2. Correct pre-reg §9's wording about beta warmup (stock leg vs market leg).
3. Run **G2-R** cleanup (widen Tier 1, adopt NSE labels, fix Tier-2 interval handling).
4. Run the P2 substrate certification.

### Key files
| File | Purpose |
|---|---|
| `docs/reports/SIGNAL_ENGINE_DESIGN.md` | Engine architecture, four sleeves, breadth thesis (DRAFT) |
| `docs/reports/CARRY_PHASE0_PRE_REGISTRATION.md` | Carry pre-registration — **FROZEN** (v1, superseded sign) |
| `docs/reports/CARRY_V2_PRE_REGISTRATION.md` | Carry v2 re-registration — **FROZEN** (positive sign) |
| `docs/reports/CARRY_TRAIN_REPORT.md` | v1 TRAIN report |
| `docs/reports/CARRY_NET_SPREAD_REPORT.md` | Net-spread report (v2 sign) |
| `docs/reports/CARRY_NET_SPREAD_SNAPSHOT.json` | Frozen TRAIN+HOLDOUT numbers |
| `docs/reports/CARRY_SEALED_REPORT.md` | One-shot SEALED read |
| `docs/reports/CARRY_SEALED_SNAPSHOT.json` | Frozen SEALED snapshot |
| `docs/reports/CARRY_RFA.md` | RFA gate report (PROCEED) |
| `docs/reports/CARRY_PARITY_REPORT.md` | Construction parity (+0.0 bp) |
| `docs/reports/CARRY_DRAWDOWN_REPORT.md` | Drawdown/regime profile |
| `docs/reports/CARRY_CAPACITY_REPORT.md` | ADV capacity analysis |
| `docs/reports/CARRY_INTEGRATION_SMOKE_REPORT.md` | End-to-end integration verification |
| `docs/reports/CARRY_PRODUCTION_METRICS_REPORT.md` | Script-generated production metrics |
| `docs/reports/CARRY_PRODUCTION_METRICS_IMPLEMENTATION_PROMPT.md` | Build spec (Phase A/B) |
| `docs/reports/CARRY_PRODUCTION_METRICS_PLAN_REVIEW.md` | Original plan audit (NO-GO) |
| `docs/reports/CARRY_PRODUCTION_METRICS_REPORT_REVIEW.md` | Round-2 audit (NOT complete → traced + fixed) |
| `governance/rfa/declarations/carry.py` | **FROZEN** RFA declaration (SHA `4b589e2f…`) |
| `scripts/signal_engine/carry/build_carry.py` | Frozen signal construction |
| `scripts/signal_engine/carry/neutralize.py` | Beta + sector neutralization |
| `scripts/signal_engine/carry/publish_facts.py` | Production fact publisher |
| `scripts/signal_engine/carry/run_train.py` | TRAIN read |
| `scripts/signal_engine/carry/run_sealed.py` | **FROZEN** — one-shot SEALED read, never re-run |
| `scripts/signal_engine/carry/run_net_spread.py` | Net-spread computation |
| `scripts/signal_engine/carry/parity_check.py` | Production-vs-research parity harness |
| `scripts/signal_engine/carry/drawdown_analysis.py` | Drawdown analysis |
| `scripts/signal_engine/carry/capacity_analysis.py` | ADV capacity analysis |
| `scripts/ingest_index_history.py` | 1d index store ingest + Gate A/B |
| `scripts/sfb/ingest_futures_bhavcopy_v2.py` | FUTSTK/FUTIDX bhavcopy ingest |
| `docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` | **Terminal artifact** — can TS Basis / TS Basis Daily be re-authorized? Monthly: no (sealed spent), but the read is estimator-clean and the defect is priceable. Daily: research-only, window preserved |
| `docs/reports/TS_BASIS_DAILY_NET_SPREAD_REPORT.md` | TS Basis Daily net-spread report |
| `docs/reports/TS_BASIS_DAILY_HOLDOUT_REPORT.md` | TS Basis Daily HOLDOUT report |
| `scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py` | TS Basis Daily signal construction (DuckDB-optimised, incremental) |
| `scripts/signal_engine/ts_basis_daily/publish_facts.py` | TS Basis Daily facts publisher |
| `scripts/signal_engine/ts_basis_daily/run_net_spread.py` | TS Basis Daily net-spread analysis |
| `scripts/signal_engine/ts_basis_daily/run_holdout.py` | TS Basis Daily HOLDOUT gate |
| `scripts/signal_engine/ts_basis_daily/run_sealed.py` | TS Basis Daily SEALED read — **DISABLED, refuses to run** (research-only; window preserved) |
| `scripts/signal_engine/ts_basis_daily/run_drawdown.py` | TS Basis Daily drawdown analysis |
| `scripts/signal_engine/ts_basis_daily/run_capacity.py` | TS Basis Daily capacity analysis |
| `scripts/ts_basis_daily_signals.py` | TS Basis Daily signal report (latest date, top-N) |
| `scripts/ts_basis_daily_paper_replay.py` | TS Basis Daily LoopDriver PAPER replay |
| `scripts/ts_basis_daily_forward_runner.py` | TS Basis Daily forward PAPER runner |
| `scripts/ts_basis_daily_concentrated_backtest.py` | TS Basis Daily top-5 concentrated backtest |
| `scripts/refresh_all_strategies.py` | Checkpointed pipeline: carry + ts_basis + ts_basis_daily build + facts |
| `scripts/download_all_data.py` | Unified NSE bhavcopy download → build → refresh pipeline |
| `governance/rfa/declarations/ts_basis_daily.py` | **FROZEN** TS Basis Daily RFA declaration |

TS Basis Daily options selection is live-anchored: ATM struck on the live near-month futures LTP with a live bid/ask-spread + OI + volume tradeability screen (`MAX_SPREAD_PCT=5%`, `STRIKE_BAND=±3`, `MIN_OI=100`, volume ≥ 1 lot), falling back to EOD bhavcopy (`anchor_source`/`screen` labelled per contract) when the market is closed or the token is missing. Shared by `scripts/ts_basis_daily_options.py` and the `/ts-basis-daily/` panel via `core/analytics/options_selection.py`.

---

## Options Analysis Dashboard — In Progress

Real-time options structural analysis (PCR, Net GEX, OI buildup, Max Pain, IV smile) for Nifty 50 and BankNifty, from the Upstox V3 option chain at 5-second snapshots.

- **Flow**: `options_provider.py` → `options_analytics.py` → `options_facade.py` → `/options/` blueprint; SSE push via `options_publisher.py` (paths in Key Directories above)
- **Expiry**: Nifty=Tuesday, BankNifty=Wednesday weekly — `get_weekly_expiry()` / `get_expiry_list()` against `data/instruments/nse_fo_instruments.duckdb`
- **Tests**: `tests/analytics/test_options.py` — 17 tests, passing
- **Full detail**: `docs/archive/OPTIONS_ANALYSIS_DASHBOARD_PLAN.md`

---

## Known Pitfalls

- Trailing stops on intraday equity **hurt** — cut winners on normal pullbacks
- Directional filters (daily EMA trend) **removed winning counter-trend trades**
- Fee impact is massive at Rs 500 risk — STT alone is 0.025% of turnover per leg
- Single-period validation is misleading — always run full walk-forward
- Index data (Nifty) has volume=0 — kills vol_z and VWAP filters silently
- Position tracker not updated → equity=cash only, DD wrong, TP/SL/time stops never fire
- **DELIVERY-EQUITY FEES DOMINATE WEEKLY STRATEGIES** — STT is 0.1% **per leg** (both buy and sell) for delivery equity vs 0.025% sell-only for intraday. At weekly turnover ~0.80, STT alone imposes ~13pp/yr. No known Indian equity cross-sectional effect clears a 13pp fee hurdle. Monthly+banded constructs are the only fee-survivable path. Confirmed by PSB-1 Phase 2: C1 gross +1.1% → net −16.8%; C5 gross +16.2% → net +4.3% (14 bp/yr drag).
- **Fabricated adjusted returns from CA mis-keys survive both screens** — a factor registered to the wrong symbol (DVL→DTIL), dropped by the events CTE (PHILIPCARB/PCBL ISIN fragmentation), or spanning a recycling ticker (DTIL/DVL entity union) produces a false >|20%| return invisible to R1's gap filter. The four-arm contract suite catches all three classes at entity grain with zero structural filters.
- **An entity is not one symbol for all time** — NSE recycles vacated tickers (DTIL→tea business). Time-aware entity resolution via `symbol_entity_intervals` is required; union-find alone is not sufficient.
- **An ISIN is not one entity for all time** — face-value changes re-issue the security with a new ISIN serial (PHILIPCARB/PCBL, INE602A01015→INE602A01031). ISIN issuer-prefix linkage is required; full-ISIN matching severs a company at exactly the corporate action it must adjust for.
- **An index is not one name for all time either** — Nifty 50 was `S&P CNX Nifty`, then `CNX Nifty`, then `Nifty 50`. A canonicalization guard anchored on `startswith("CNX ")` misses `"S&P CNX Nifty"` and writes a year of real index history through as a separate identity, silently. Match legacy names by *containment*, not prefix, and hard-fail unmapped rather than falling through to `f"NSE_INDEX|{raw_name}"`.
- **A gate that tests file existence cannot certify row existence.** Deleting `NSE_INDEX|Nifty 50` from 59 dates left every file in place at 25/28 rows, and **all six Gate-A checks still passed**: A1 compares file stems to the calendar, A2 reads only the 252nd session's *date* (it slipped 59 sessions and stayed inside the bound), A5 tests `>1` not `==0`, and A6 measures % change between *consecutive available* rows — a three-month hole read as +4.17%, a quiet day. Any gate over a time series needs an explicit **contiguity** check (every calendar date in span carries exactly one row); completeness checks on the container are not checks on the contents.
- **A gate passing is not the same as being able to show how it came to pass.** On 2026-07-21 the 1d index store's 241 pre-2013 sessions were re-keyed by code that exists in no commit, no working-tree diff, and no untracked file — flipping Gate A2 from FAIL to PASS on data that measures sound. The store is now not rebuildable from the repo, and the "no OHLC change" prediction is permanently unverifiable because the mandated copy-first baseline was never taken. **Mutate a source-of-truth store only from committed, re-runnable code, and take the baseline copy *before* the write** — a substrate certification certifies provenance, and provenance cannot be reconstructed after the fact.
- **A bare `except: pass` around a download turns "we failed" into "the source doesn't have it"** — and that claim then gets written into a governance report as a fact about the world. 46 downloadable NSE sessions were recorded as permanent archive gaps this way. Catch only the specific exception intended (`requests.RequestException` around the fetch); classify a date MISSING **only** on a non-200 status, never on a parse or write failure.
- **A 404 is only evidence of absence for a date that has already closed — never cache it permanently for one that hasn't.** A run on 2026-07-09 probed five months of forward dates, 404'd on every one (they had not happened yet), and wrote 289 permanent `.404` markers covering 2026-08-01 → 2026-12-31. Those markers short-circuit the fetch, so equity ingestion would have been silently skipped for the rest of the year while the EOD chain reported `success` nightly. Guarded by `_may_cache_miss()` in `ingest_equity_bhavcopy.py`; the futures/options ingests are **unaudited** for the same pattern. Full detail: `docs/reports/EQUITY_MISS_CACHE_DEFECT.md`.
- **Gating a multi-feed pipeline on one feed makes every other feed optional.** `eod_decision.decide()` fires the EOD chain when *futures* publishes and never checks equity, so a totally failed equity ingest still yields `success`. The stale feed was named in every Telegram message (`old equity: 2026-07-29`) and no code consumed that field — **a freshness value that is printed but never asserted is documentation, not a control.** The only detector that worked was the operator recognising yesterday's names in an options book.

---

## Development Conventions

- **No over-engineering** — don't add error handling, helpers, or abstractions for one-time use
- **No docstrings/comments** on code you didn't change
- **No backwards-compatibility shims** — delete unused code completely
- **Validate with train/test split** — in-sample results are meaningless
- Before modifying any file, **read it first** — understand existing patterns
- Prefer editing existing files over creating new ones
