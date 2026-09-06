# MSRP Phase 7 — Strategy Research: What the First Alpha Strategy Should Be

**Document type:** Research / scoping input for the Phase-7 decision (analogous to the
Phase-0 charter's §8 — this document recommends; the operator decides). Nothing here
is pre-registered yet.

**Date:** 2026-07-07

**Predecessor:** MSRP Phase 6 CERTIFIED — Approved verdict on the
`ForwardVolatilityArtifact` (`docs/implementation/msrp/reports/MSRP_PHASE6_REPORT.md`,
validation_id `47fe3272…`). Charter §6 row 7 defines Phase 7: "First alpha strategy —
a `core/strategies/` source that consumes v2 Knowledge and genuinely attempts P&L.
Downstream of a proven artifact."

**Revision provenance:** revised once (2026-07-07, same day) after an independent
model review (GLM), which accepted the D1 recommendation but identified five
under-weighted issues — construct gap (unhedged straddle ≠ RV−IV), statistical power,
long-arm selection, fee-triage sequencing, and uncertainty-rule calibration. All five
are folded in below; the arm-selection amendment to the §7 locked decisions was
approved by the operator.

---

## 1. What the certified Knowledge actually provides

Phase 7 must be designed around what the artifact *is*, not what a strategy might wish for:

| Property | Fact | Source |
|---|---|---|
| Estimate | `expected_next_day_realized_vol` — a **level** forecast of next-day *intraday* Nifty 50 RV (overnight gap excluded) | Dossier §5, §7 |
| Uncertainty | State-dependent predictive spread, **calibration-validated** (94.12% empirical coverage of nominal 90%) | Phase-6 report §3 |
| Cadence | Daily; issued as-of close of day `t`, about day `t+1` | Dossier §8 |
| Edge size | AUC 0.585 vs base rate 0.538 — statistically significant, **economically modest** | Phase-6 report §5 |
| Edge trend | ΔAUC_gate = 0.065 (H1-2026) → 0.0125 (second sub-period) — **fading** | Phase-6 report §5 |
| Vs. implied vol | ΔAUC_vix = 0.066 > 0 — adds information **over and above India VIX** | Phase-6 report §4 |
| Consumer contract | `KnowledgeSignalSource` selects one named estimate (`value` + `uncertainty`); strategy stays dumb; sizing/risk in execution | MM13 §4 |

Two design-controlling implications:

1. **This is a volatility forecast, not a directional signal.** It says nothing about
   whether Nifty goes up or down tomorrow — only how much it will move intraday. Any
   Phase-7 design that monetizes it through directional index/futures entries is
   re-importing the exact failure mode of the prior codebase (§3).
2. **The differentiated content is `E[RV]` relative to what the market already prices.**
   The ΔAUC_vix > 0 result is the artifact's economic substance: the HAR structure knows
   something VIX doesn't. The natural monetization of "my vol forecast differs from the
   implied vol forecast" is **options** — buy convexity when the model says implied is too
   low, sell premium when it says implied is too high. Everything else is an indirect use.

## 2. The three monetization archetypes

| Archetype | Mechanism | Construct match | Blocker |
|---|---|---|---|
| **A. Options vol trading** | Trade next-day straddle/premium against the model-vs-implied spread | **Approximate** — unhedged straddle P&L is terminal-move/vega-mediated, not RV−IV itself (§5, D1); still the closest match of the three | No historical options data in the repo (§4) |
| **B. Regime gate on a host strategy** | Trade an intraday strategy only on predicted high-vol (or low-vol) days | Indirect — Knowledge selects days, host provides the entry edge | **No host strategy exists** (greenfield); conflates two untested hypotheses in one experiment |
| **C. Vol-targeted sizing overlay** | Scale position size ∝ 1/E[RV] | Indirect | Same — an overlay needs something to overlay on |

B and C both presuppose a profitable base strategy. The repository has none (production
strategy layer is intentionally greenfield), so choosing B or C means Phase 7 secretly
becomes *two* research programs — "find an intraday edge" plus "does the Knowledge improve
it" — where a null result is unattributable: was the gate useless, or was there no edge to
gate? That is a badly-posed experiment. Archetype A is the only design where the Knowledge
itself is the tested edge.

## 3. Prior-art lessons (paid for once already — do not re-purchase)

From `docs/reports/DRA_TECHNICAL_DOSSIER.md` (the pre-SALVAGE daily-regime post-mortem):

- **"Classifier works, strategy not profitable."** The HMM regime classifier was sound;
  the directional strategy built on it lost money on the Nifty cash index (−Rs 1,647 over
  200 trades, 44.7% win rate at 1:2 R:R). Root cause was the *execution* layer: index
  volume=0 silently disabled two of three confirmation filters, and EMA-only entries had
  no edge. A good state estimate did not rescue a bad entry mechanism.
- **The documented verdict was "repurpose as a market-timing filter for existing
  profitable strategies"** — which is archetype B, and it stalled precisely because no
  profitable host existed. That is still true today.
- **The prior codebase's own resolution was the pivot to options premium harvesting**
  (NiftyShield, Mar 2026) "after 5 months of directional prediction attempts."

The lesson compresses to: *don't route a volatility forecast through a directional trade
on an instrument with no microstructure edge.* Trade volatility as volatility.

## 4. Data feasibility — the binding constraint

| Data | Status | Consequence |
|---|---|---|
| Nifty 50 1m index | 2023-01 → present | RV / features fully covered (already used by the artifact) |
| India VIX 1d | 2023-01 → present | Implied-vol reference covered |
| **Options price history** | **None.** `data/market_data/options.duckdb` does not exist; the 5-sec snapshot cache only accumulates from whenever the dashboard runs | An options backtest needs an external historical source |
| Futures history | None in the candle store | A futures strategy would backtest on the index as proxy (basis/rollover unmodelled) |
| F&O instrument metadata | `data/instruments/nse_fo_instruments.duckdb` (strikes, expiries, lot sizes) | Contract selection logic is already supported |

External options-history options (to be verified as a Phase-7 precondition, the same way
the Phase-0 data top-up was a precondition):

1. **Upstox Expired Instruments API** (Upstox Plus plan): expiries, expired option
   contracts, and expired-contract candles at 1minute→day intervals. **History is
   shallow** — community threads indicate availability from ~Oct 2024, with a standing
   feature request because the expiries endpoint returns only ~6 months. Best case this
   yields ~Oct-2024→present: a ~14-month dev window + a 2026 held-out window at daily
   cadence (~300 + ~120 obs). Marginal but usable; depth must be verified empirically
   before pre-registration.
2. **NSE F&O bhavcopy** (official, free, full history): per-contract daily OHLC + settle
   + OI for every option contract, covering the entire 2023→2026 span. Sufficient for a
   **daily-cadence, EOD-priced** strategy — which is exactly the cadence of the Knowledge.
   Liquidity caveat: bhavcopy open prices on illiquid strikes can be stale; ATM weekly
   Nifty strikes are among the most liquid contracts in the world, mitigating this.

A daily-cadence options design is therefore backtestable today with a bounded ingestion
task; an intraday options design is not (data exists ≤ ~20 months at best, behind a paid
plan). This strongly favors keeping Phase 7 at daily cadence — which also matches the
artifact's native cadence.

## 5. Candidate designs evaluated

### D1 — Direction-neutral next-day ATM straddle, Knowledge-gated (RECOMMENDED)

At close of day `t` the artifact emits `E[RV_{t+1}]` with uncertainty. Compare it to the
market-implied next-day move (from the ATM weekly straddle price, or VIX scaled to one
day). Pre-registered rule of the form:

- `E[RV]` **well below** implied (by a dev-window-fitted margin) → **short** the next-day
  ATM straddle (harvest premium the model says is too rich);
- `E[RV]` **well above** implied → **long** the straddle;
- otherwise → **flat**. The natural abstention form: stand aside when the implied move
  lies **inside** the model's 90% predictive interval (the model cannot distinguish its
  forecast from the market's). Caveat (review finding 5): the 94.12% coverage certified
  in Phase 6 calibrates the interval for `E[RV]`, a *different decision problem* than
  the `(E[RV] − implied)` spread — the abstention rule's economic value must be
  demonstrated on the dev window, not assumed from the coverage number, before it is
  frozen into the pre-registration.

Execution shape that matches the construct: enter at day-`t+1` **open**, exit at day-`t+1`
**close** — intraday-only exposure, mirroring the artifact's overnight-excluded RV
definition. Computable from bhavcopy OHLC.

**The construct gap, stated structurally (review finding 1).** An *unhedged* straddle
held open→close pays off on the **terminal move** `|Δspot|` plus a vega term
(ΔIV over the day), minus theta — it does **not** equal `RV − IV`. The artifact
forecasts *path variance* (Σ of squared 1m returns); a day that travels violently but
closes flat is high-RV and a losing long straddle. The only clean isolation of
realized-vs-implied is a *delta-hedged* straddle, which needs the intraday options data
§4 rules out. So D1 tests "does the forecast improve next-day straddle trading," not
"RV−IV capture" — an attenuated but real transmission (`|Δspot|` and `√RV` are strongly
positively related). Mitigation: prefer short-DTE weeklies, where vega is small and
gamma/theta dominate, keeping the P&L predominantly a vol bet. This gap is structural,
accepted with eyes open; every other archetype is worse on construct match.

**Expiry selection is load-bearing (review finding 5).** Nifty weeklies expire
**Tuesday**: a Monday-close signal traded "t+1 open→close" on the *nearest* expiry is a
**0DTE** trade — pure pin/gamma, a different instrument from the same rule on other
weekdays. The pre-registration must fix contract selection (e.g., always ≥ 2 DTE, ATM
by nearest strike or 50-delta) or weekday heterogeneity contaminates the whole series.

- **Why it's best:** closest construct match available at daily cadence (see gap note
  above); daily cadence = artifact cadence; direction-neutral (immune to the prior
  directional failure mode); backtestable over the full dev window from official free
  data; both long-vol and short-vol arms are exercised **in development**, so the dev
  backtest tests *forecast quality*, not just the structural variance risk premium.
- **Comparison arms (MSRP method carried forward):** (i) the same rule driven by the
  reference fixture's `market_regime` instead of the Knowledge; (ii) an unconditional
  short-straddle baseline (pure variance-risk-premium harvest — the "dumb premium seller"
  every gated variant must beat to justify the artifact's existence).
- **Risks / costs to model honestly:** options transaction costs (the repo's fee model is
  equity-intraday only — an options fee model incl. STT-on-premium, exchange charges, and
  Rs 20/leg brokerage is a Phase-7 deliverable); slippage at the open; SPAN+ELM margin for
  the short side (`NseMarginEngine` already exists for exactly this); expiry-day gamma on
  Tuesdays; a construct gap between straddle P&L (path-dependent, IV-change-exposed) and
  RV (the pre-registration must state this, not discover it).

### D2 — Expiry-day (0DTE) premium selling, Knowledge-gated

Same idea concentrated on the weekly Tuesday expiry. Rejected for increment 1: pin/path
risk dominates the daily RV construct, one observation per week (~26 per held-out —
hopeless power), and intraday management would be needed, dragging in the intraday-data
problem.

### D3 — Vol-gated intraday futures strategy (e.g., ORB on predicted high-vol days)

Backtestable today on the 1m index as proxy, but this is archetype B: it requires
inventing an intraday entry edge that the DRA post-mortem says the index does not offer
at retail, and a null P&L result would not tell us whether the Knowledge or the host
failed. Keep as a *fallback* only if the options-data precondition fails outright.

### D4 — Forward-PAPER-only options strategy (no backtest)

Deploy D1 live-paper and evaluate on accumulating forward data only. Rejected as the
primary path: with an edge this modest, ~120 forward days cannot separate skill from
noise (Phase 6 barely cleared a rank-based gate with that sample; P&L is far noisier).
Forward PAPER is the *confirmation* stage after a backtested pre-registration, not the
experiment itself.

## 6. Recommendation

**Phase 7 = D1**, run with the full MSRP discipline, sized as follows:

1. **Precondition (before any pre-registration):** three gates, in order —
   (a) ingest NSE F&O bhavcopy for Nifty weekly options 2023→present and audit
   liquidity/quality; (b) build the options fee model (STT on premium, exchange
   charges, Rs 20/leg, GST, stamp — the repo's fee model is equity-intraday only);
   (c) **fee-impact triage** (review finding 4): a rough dev-window pass of the D1 rule
   net of costs. **If the net-of-cost dev edge is ~zero, stop here and reconsider — do
   not pre-register an uneconomic design.** No strategy design decisions until all
   three gates pass.
2. **Phase-7 pre-registration (a new dossier — the Phase-1 dossier is frozen and must not
   be edited):** entry/exit rule, the model-vs-implied threshold fitted on dev only, the
   uncertainty abstention rule, the fee model, the comparison arms, the metric, and the
   decision rule — all fixed before the held-out window is scored.
   - **Fresh held-out window required.** The 2026-01→2026-07 window is consumed (Phase 6
     touched it once, as designed). The natural choice: dev = 2023→2025 (options data
     permitting), 2026-01→07 reported as a *transition slice, not decisive*, and the true
     held-out being **forward data from 2026-07 onward** — which also directly tests the
     §11 fading-edge concern on genuinely unseen data.
   - **Metric — rank gate + economic qualifier (review finding 2):** straddle returns
     are fat-tailed and (short side) negatively skewed, so a mean-P&L bootstrap on ~120
     forward days will almost certainly span zero even if a real edge exists. Mirror the
     Phase-6 structure: the **primary gate is a rank/discrimination statistic on paired
     daily P&L** (Knowledge-gated arm vs. fixture-gated arm, and vs. the unconditional
     short baseline) with a moving-block bootstrap CI — the Phase-6 machinery reused
     as-is — and **net-of-cost P&L per unit of margin is the reported economic
     qualifier** (the charter's "genuinely attempts P&L" requirement lives here; it
     qualifies the verdict, it does not gate it). The §10-style decision table must
     name **"inconclusive → extend the window" as the modal expected outcome**: the
     realistic timeline to a decisive verdict under forward-only accumulation is
     **250–500+ sessions (1–2+ years)**, an expectation the operator accepts by
     choosing forward-only. Pre-register a non-decisive interim reporting cadence
     (e.g., quarterly) so the wait is observable without being decision-contaminating.
3. **Architecture:** a new `core/strategies/` SignalSource in the MM13 mold (select the
   named estimate, emit signals with `sl_distance`/`risk_r` metadata, pass conformance,
   run under `GuardedSignalSource` on PaperBroker). Strategies stay dumb; option-leg
   sizing and margin live in execution. No platform changes — the scope fence holds.
4. **Kill criterion (new, motivated by the fading-edge caveat):** pre-register a
   monitoring rule on the forward window (e.g., trailing gate discrimination below a
   floor for N consecutive sessions → strategy stands down). The Phase-6 sub-period drift
   is the single biggest threat to Phase 7 and deserves a first-class, pre-committed
   response rather than a discretionary one.

**What Phase 7 must not be:** a directional index/futures strategy dressed up with a vol
gate (D3 as primary); a multi-signal framework; an intraday options system requiring data
that doesn't exist; LIVE deployment (still fenced behind MM14); or an edit to anything
frozen (Phase-1 dossier, Phase-5 artifact, A2 harness, Phase-6 sealed record).

## 7. Operator decisions (LOCKED — 2026-07-07)

All three open questions were put to the operator and decided the same day:

1. **Risk framing: both sides — AMENDED same day (review finding 3, operator-approved).**
   Both long- and short-straddle arms (plus abstention) are authorized **for the
   dev-window backtest**; the **held-out arm set is selected from dev evidence and then
   frozen in the pre-registration**. Rationale: the unconditional long straddle loses on
   average (variance risk premium), and locking a possibly fee-negative long arm by fiat
   costs statistical power — but whether the *gated* long arm (which trades only when
   the model says E[RV] ≫ implied, exactly where the VRP compresses) earns its place is
   an empirical dev question, not one to decide by assertion in either direction.
   Dev-window selection is consistent with pre-registration discipline. PAPER only;
   SPAN+ELM margin for the short side computed by `NseMarginEngine`.
2. **Data source: NSE bhavcopy only.** Free official EOD per-contract OHLC/settle/OI,
   full 2023→2026 coverage. No Upstox Plus subscription for increment 1; the Expired
   Instruments API remains a possible later enrichment.
3. **Held-out: forward-only.** Dev = 2023→2025 (options data permitting); 2026-01→07 is
   reported as a non-decisive transition slice; the decisive held-out accumulates
   forward from 2026-07 under a pre-registered decision rule. This directly tests the
   Phase-6 fading-edge caveat on genuinely unseen data.

With these locked, Phase 7 is scoped: **precondition (bhavcopy ingestion + quality
audit) → Phase-7 pre-registration dossier → independent review → implementation →
forward evaluation.**

---

## Sources

- `docs/reports/MSRP_PHASE0_CHARTER.md` — Phase-7 definition, scope fence, thin-slice principle
- `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` (FROZEN) — construct definitions, §10 decision table, §11 threats
- `docs/implementation/msrp/reports/MSRP_PHASE6_REPORT.md` — Approved verdict, caveats (modest edge, sub-period drift), Phase-7 authorization
- `docs/reports/DRA_TECHNICAL_DOSSIER.md` — prior-art failure analysis (classifier vs. strategy)
- `core/strategies/knowledge_signal_source.py`, `core/runtime/guarded_signal_source.py` — consumer contract
- [Upstox Expired Instruments API launch](https://upstox.com/developer/api-documentation/announcements/expired-instruments-api/), [Expired Historical Candle Data API](https://upstox.com/developer/api-documentation/get-expired-historical-candle-data/), [community: history depth limited](https://community.upstox.com/t/feature-request-extend-expired-instruments-api-history-beyond-6-months/16583), [community: no option data before Oct 2024](https://community.upstox.com/t/historical-option-data-before-october-2024/16402)

*End of research. This document recommends; the Phase-7 pre-registration decides.*
