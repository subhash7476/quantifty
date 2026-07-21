# Options Strategy Research — Index & Stock Options, Indian Market

**Date:** 2026-07-17
**Status:** Research survey — no candidate is authorized for implementation. Any pursuit goes through a pre-registered screening battery (proposed: PSB-O1), same discipline as PSB-1/PSB-2.
**Scope:** NSE index options (Nifty, BankNifty) and single-stock options, evaluated against this platform's cost-first research doctrine and existing infrastructure.

---

## 1. Why options — the structural argument from our own findings

PSB-1 and PSB-2 established, three times over, that **the binding constraint on Indian cash-equity strategies is not signal quality — it is delivery STT** (0.1% per leg, both sides). Gross Q1–Q5 spreads of +17%/yr were consumed whole by 12–17pp/yr fee drag. Only monthly+banded constructs survive.

Options invert this cost structure:

| Cost element | Delivery equity | Index options |
|---|---|---|
| STT | 0.1% of **full notional**, both legs | 0.15% of **premium**, sell side (per the effective-dated schedule in `core/execution/options/fees.py`: 0.05% → 0.0625% (2023-04) → 0.1% (2024-10) → 0.15% (2026-04); 0.125% of intrinsic if exercised ITM) |
| Effective cost per unit of market exposure | ~20bp round trip on notional | ~0.2–0.5bp on equivalent notional (premium ≈ 0.5–2% of notional) |
| Cadence ceiling imposed by fees | Monthly at best | Weekly, even intraday, remains viable |

**The same fee wall that killed C1–C4 simply does not exist in index options.** That is the structural reason this venue deserves a battery, independent of any specific signal.

A second, less obvious argument: this platform already owns the three hardest pieces of options infrastructure — a frozen SPAN margin engine (`NseMarginEngine`, MM10) for exact sizing, live option-chain analytics (PCR, **net GEX**, OI, max pain in `core/analytics/options_analytics.py`), and a day-type classifier at **80% validation accuracy** (`logistic_13pm_prod`). Most retail operations have none of these.

## 2. Market-structure constraints (the lens every candidate must pass)

1. **Single-stock options settle physically.** ITM at expiry → delivery obligation with full delivery STT on notional. Stock-option candidates must exit before expiry week by construction, or the fee wall re-enters through the back door.
2. **Liquidity is a cliff, not a slope.** Nifty weeklies are among the most liquid option markets in the world; BankNifty is a tier below; stock options are tradeable in perhaps the top 25–40 F&O names and near-untradeable beyond (spreads of 1–5% of premium replace STT as the binding cost).
3. **Expiry cadence** (per our instrument master): Nifty weekly Tuesday, BankNifty weekly Wednesday — `get_weekly_expiry()` against `data/instruments/nse_fo_instruments.duckdb` is authoritative.
4. **Margin regime:** SPAN + exposure, with expiry-day add-ons. Short premium consumes ~1.5–2.5L margin per lot-pair; margin expands *during* stress — exactly when positions hurt. Sizing must be computed against `NseMarginEngine` with stress headroom, never at rest-state margin.
5. **The counterparty evidence:** SEBI's own studies find ~90% of individual F&O traders lose money, dominated by naked long-option buying and undisciplined selling. The persistent transfer is *from* impatient directional buyers *to* disciplined, defined-risk premium sellers. An edge here is structural (a risk premium), not an anomaly that decays on discovery.

## 3. Candidate slate

Ranked by expected robustness × fit to existing infrastructure. Each entry states the mechanism, why it should persist, and its kill risks.

### O1 — Nifty variance risk premium (VRP), regime-filtered, defined-risk ★ primary candidate

**Mechanism:** Implied volatility on Nifty weeklies persistently exceeds subsequently-realized volatility. Selling that gap — as **iron condors or broken-wing structures, never naked** — collects an insurance premium. This is the most documented effect in Indian derivatives: the India VIX vs realized-vol gap is positive in the large majority of months, and the effect survives publication because it is *payment for bearing tail risk*, not mispricing.

**Construction sketch (to be pinned in a protocol, not here):**
- Sell weekly Nifty iron condor at entry-day IV-percentile above a threshold; skip when India VIX term structure is inverted (backwardation = stress).
- Regime filters from assets we already run: **net GEX sign** (positive GEX → dealers dampen moves → range regime → sell premium; negative GEX → do not sell), and the **DayTypeEngine** classification.
- Defined risk caps the tail; exit at a pinned profit fraction or stop, never hold short gamma into the final hours of expiry.

**Prior in-repo evidence (MSRP Phase 7 fee triage, 2026-07-07 — must be disclosed as prior exposure in any protocol):** the unconditional short ATM straddle over the 695-day dev window was **net positive (+Rs 110K)** with fees at only ~6% of mean daily gross — direct confirmation that (a) a VRP exists on Nifty weeklies and (b) fees do not bind in this venue. The same triage recorded the caveats that define O1's job: 2023 was negative (regime clustering) and tail risk was unmodelled. O1 is precisely the disciplined version of that observation — defined-risk, regime-filtered, pre-registered.

**Why it can be "reliably strong":** it is a risk premium (structural payer on the other side), fee-cheap (premium-based STT), capacity-deep (Nifty weeklies), and testable with EOD data. **Kill risks:** gap-through-strikes tail events (Covid Mar-2020, election Jun-2024 class moves — defined risk caps but does not eliminate), volatility-regime clustering (losses bunch), margin expansion forcing exits at the worst time.

### O2 — DayTypeEngine × structure selection (intraday, 13:00 decision) ★ the differentiated edge

> **⚠️ Caveat — the classifier does not exist in this repository.** O2's core asset — the 80%-validation-accuracy day-type classifier described below — was not ported during the SALVAGE migration. No `DayTypeEngine` class, `build_intraday_features.py`, `train_daytype_classifier.py`, or model artifact (`logistic_13pm_prod`) is present in the codebase (verified 2026-07-21). O2 **cannot be pre-registered** until the classifier is rebuilt and independently validated on a fresh train/holdout/sealed split. A rebuilt classifier's accuracy would be a fresh read, not the inherited 80%.

**Mechanism:** (If rebuilt) The platform's classifier would call afternoon day-type at 13:00 with targeted validation accuracy. Map classification → option structure for the 13:00→15:25 session: trend-day call → directional debit vertical (defined risk, cheap afternoon theta); range-day call → short iron fly harvesting the steepest part of weekly theta decay. Flat by close: **zero overnight risk, zero delivery risk, minimal STT** (intraday, premium-based).

**Why it's attractive:** converts an already-validated 80% classifier into P&L through the one venue where 2.5-hour holding periods are fee-viable. The classifier's edge was proven on 2023–2025 data; the options overlay is *expression*, not new signal discovery. **Kill risks:** the 80% is validation accuracy on classification, not P&L — payoff asymmetry between right/wrong must be measured; afternoon option spreads and slippage at 13:00 entry; classifier decay.

### O3 — GEX-regime filter (overlay, not standalone)

Net GEX from `options_analytics.py` as a *conditioning variable*: positive GEX days → mean-reversion/premium-selling regimes; negative GEX → momentum/long-gamma regimes. Academic and practitioner evidence (SPX; mechanism is dealer hedging, which transfers to Nifty's dealer-dominated weekly book). **Recommendation: build as a filter for O1/O2 first; standalone GEX strategies are noisier than GEX-conditioned ones.**

### O4 — Expiry-day (0DTE) theta harvest — deferred

Tuesday Nifty expiry premium decay is violent and pin/max-pain effects are real (we already compute max pain). But 0DTE short gamma is the highest-tail-risk construct in the slate, expiry-day margin add-ons apply, and intraday granular option data (which we only have from the dashboard's recent 5-second snapshots) is required to backtest honestly. **Park until O1/O2 have run and the snapshot archive is deep enough.**

### O5 — Stock options: earnings IV crush — research-grade only

Front-expiry IV in liquid single names inflates before earnings and collapses after. Short pre-earnings straddle/strangle in the top-liquidity tier (Reliance, HDFC Bank, ICICI, Infosys, TCS class), exit immediately post-event, always before expiry week (physical settlement). **Constraints:** ~25–40 tradeable names → small cross-section, event-driven cadence, spread costs 1–3% of premium, and Indian earnings dates need a clean point-in-time calendar we do not yet have. Genuine but operationally expensive edge.

### O6 — C2 synergy: delivery-z conviction via stock options — future extension

Where C2's top-quintile names intersect the F&O list, express the position as a bull call spread instead of (or alongside) cash delivery — leverage without delivery STT on entry. **Honest assessment:** the intersection of NIFTY-200 top-quintile with liquid-options names is partial and fluctuating; option spreads may eat what STT saved; and it contaminates C2's clean validation story. Do not touch until C2 itself is deployed and measured.

### O7 — Dispersion (index vol vs component vol) — parked

An archived implementation plan exists (`docs/archive/DISPERSION_RESEARCH_IMPLEMENTATION_PLAN.md`). Correlation risk premium is real but the construct needs simultaneous multi-leg execution across index + N stock options — operationally the hardest thing in this document. Parked indefinitely.

## 4. The find — stated plainly

> **The reliably strong opportunity is not a new signal; it is a venue arbitrage against our own cost findings.** Two batteries proved that Indian cash-equity alpha drowns in delivery STT at any cadence faster than monthly. Index options are the one NSE venue where transaction cost per unit of exposure falls by roughly two orders of magnitude — and they are also the venue where the platform already holds an unfair infrastructure position in **two of three** claimed assets: a certified SPAN engine for exact margin-aware sizing (`core/risk/nse_margin_engine.py`) and live GEX/PCR/max-pain analytics (`core/analytics/options_analytics.py`). The third — a validated 80% day-type classifier — does not exist in this repository (see O2 caveat). **O1 (regime-filtered Nifty VRP) harvests a structural risk premium that cannot be arbitraged away because it is compensation for tail risk; O2 would monetize proprietary IP if rebuilt and re-validated.** O1 with O3 as a shared filter is the recommended core slate; O2's inclusion is contingent on classifier rebuild and independent validation, not inherited.

## 5. Prerequisites before any battery (PSB-O0 — data substrate)

More exists than a fresh survey would assume, but gaps remain:

1. **Options EOD substrate — partially built.** MSRP Phase 7 already delivered `scripts/msrp/ingest_option_bhavcopy.py`: 1,351,214 rows, 862 trade dates, **2023-01-02 → 2026-07-06**, ATM straddle legs complete on 100% of eligible days (Lead-Review PASS). Required: extend backward (NSE F&O bhavcopy archives go back years) so a dev/sealed split leaves a real dev window — 2023→2026 alone is too short to fence.
2. **Fee model — done.** `core/execution/options/fees.py` (MM-certified, 12 tests) with effective-dated statutory schedules. No new build.
3. **India VIX daily history** — partially present via the intermarket store; verify span and gaps.
4. **Substrate certification** — a contract suite in the PSB-1 style (contract-grain continuity across expiry rolls, strike grids, lot-size changes — lot sizes change and will corrupt notional calculations exactly the way corporate actions corrupted equity returns). The MSRP ingest passed its audit but was never put through a four-arm-style contract certification.
5. **Intraday substrate for O2/O4 — the real gap.** The 5-second snapshot store starts at the dashboard's recent go-live; MSRP's Revival-1 threshold (≥12 months of captured intraday chains) applies here too. Keep the capture job running — O2 cannot be honestly backtested on EOD data.

## 6. Proposed path (PSB discipline, unchanged)

| Step | Content |
|---|---|
| PSB-O0 | F&O EOD substrate build + certification (prerequisite, no signal work) |
| PSB-O1 Phase 0 | Frozen protocol: candidates O1, O2 (m = 2 Bonferroni), dev/sealed fence dates pinned, fee model (premium STT + exchange + GST + stamp + SEBI), slippage model per liquidity tier, margin-aware return denominator (return on SPAN margin, not notional — this is the honest denominator for short premium) |
| PSB-O1 Phase 2 | Scripted screening on dev window; script-generated reports; digest over the full artifact (PSB-2 MEDIUM-1 lesson) |
| PSB-O1 §8 | Selection under deflated α; power projection vs sealed window |

**Non-negotiables carried over:** defined-risk structures only (a naked-short-premium candidate is not eligible for screening at all); no sealed read before ratified pre-registration; kill criteria pre-registered; the C2 roadmap (`C2_DEPLOYMENT_ROADMAP.md`) is not displaced — this is a parallel research track, sequenced behind C2's Phase 0–2 evidence work in operator attention.

## 7. Risk register (what makes short-vol operations die)

- **Tail clustering:** VRP losses arrive bunched in vol regimes; a strategy Sharpe measured across calm years overstates. Walk-forward must span 2020 and 2024 stress windows.
- **Margin procyclicality:** SPAN expands in stress; forced deleveraging at the low is the classic retail short-vol death. Size at stressed margin (scan-range shocked), keep pinned headroom.
- **Regulatory drift:** SEBI has repeatedly tightened F&O (lot sizes, expiry-day margins, weekly-expiry structure). Any candidate must state which regulatory parameters it is sensitive to, and re-validate on change.
- **The 90%-lose statistic cuts both ways:** the counterparties funding the premium are also the reason SEBI keeps intervening. Capacity of the edge is policy-dependent.
- **Backtest optimism in options is worse than in equities:** EOD mid-quotes overstate fills; spreads and STT on premium must be modelled per liquidity tier from day one — this repo's fee-first doctrine applies with more force here, not less.
