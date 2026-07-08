# MSRP Phase 7 — Research Reset: Independent Evidence Review

**Document type:** Independent review of `MSRP_PHASE7_RESEARCH_RESET.md` (commit
`9821932`, authored by Codex, 2026-07-08), with **new measured evidence**. Same standing
as the gate-(a) Lead-Reviewer audit and the gates-(b)/(c) independent review: the
dossier under review recommends; this review confirms or challenges with data; the
operator decides.

**Date:** 2026-07-08

**Reviewer / evidence author:** Claude. The two scoping pre-reads cited throughout were
run for this review (`scripts/msrp/scoping_transmission_preread.py`, in-sample,
non-decisive by design — same caveat class as the gate-(c) triage: frozen coefficients
are in-sample-optimistic, bhavcopy marks, no slippage, 1m index stands in for futures).

**Scope:** the dossier's candidate-by-candidate verdicts (A–H), its final ranking
(E primary, D secondary, A4/F future, B/C/G NO-GO, H adopted), and the Phase-7
recommendation. The frozen artifact, sealed Phase ≤ 6 records, and the gate-(c) STOP are
out of scope (all confirmed final).

---

## 1. New evidence — two scoping pre-reads (695 dev days, 2023-01-02 → 2025-12-31)

The D1 post-mortem lesson is that transmission must be *measured during scoping*, not
discovered after gates. Both pre-reads apply it to the two rescue routes most likely to
be chosen next.

### 1.1 Pre-read A — synthetic delta-hedged straddle (candidate A transmission)

Long ATM straddle at t+1 bhavcopy open, exit t+1 close; Black–Scholes straddle delta
(entry IV via Brenner–Subrahmanyam) re-hedged every 15 minutes on the 1m Nifty path;
gate-(b) straddle fees plus a crude hedge-fee overlay (0.012% one-way + Rs 20/trade).

| Measurement | Value |
|---|---|
| Spearman(RV_next, unhedged straddle return) | 0.093 (matches gate c) |
| **Spearman(RV_next, delta-hedged straddle return)** | **0.198** |
| Spearman(E[RV]/implied, hedged return) | **−0.012** |
| Mean hedge turnover / hedge trades per day | Rs 1.60M / 25.9 |
| Unconditional short hedged, net (Sharpe) | −331,761 (−3.11) |
| Gated short q20 / gated long q80, net | −73,148 / −180,754 |

Delta-hedging with the only obtainable historical marks (EOD bhavcopy + constant-IV
deltas on an index hedge path) lifts transmission only 0.09 → 0.20, leaves the signal
with zero rank relationship to hedged P&L, and the hedge friction stack buries every
arm. The theory (Bakshi–Kapadia 2003: delta-hedged gains isolate realized-minus-implied)
is not in question — **the data to backtest it does not exist at any obtainable
quality.** This converts the dossier's A1 assumption into a measurement, and it defines
the revival condition (§3, F5).

### 1.2 Pre-read E — does the intraday-RV forecast carry to the risk-relevant quantity?

The certified construct excludes the overnight gap. Any position held overnight is
exposed to *total* close-to-close volatility. Measured:

| Measurement | Value |
|---|---|
| Overnight share of close-to-close variance | **31.8%** |
| Spearman(E[RV], next-day intraday RV) | 0.651 |
| Spearman(RV_t persistence, next-day intraday RV) | 0.590 |
| Spearman(E[RV], next-day &#124;c2c return&#124;) | 0.145 |
| **Spearman(RV_t persistence, next-day &#124;c2c return&#124;)** | **0.154** |
| Vol-targeted long Nifty, ann. Sharpe (2x-cap, mean-normalized) | E[RV]: 1.17; RV_t: 1.05; buy-and-hold: **1.28** |
| Vol-targeted ann. vol | 10.8% (both scalers) vs 11.7% unconditional |

Three facts with direct consequences for the dossier's primary recommendation:

1. On next-day **total** volatility — the quantity an overnight-held position's risk
   system actually manages — the certified artifact is statistically indistinguishable
   from yesterday's RV (0.145 vs 0.154), a quantity available for free with no Knowledge
   infrastructure. The artifact's genuine 0.06 edge over persistence lives entirely
   inside the intraday-RV construct and is diluted away by the 31.8% overnight
   component it deliberately does not forecast.
2. Vol targeting did stabilize vol (11.7% → 10.8%) — but *both* scalers achieved it
   equally. Vol stability alone cannot demonstrate the Knowledge's value.
3. The dossier's claim that "Sharpe improves by construction if sizing works" is
   contradicted by measurement: in this dev window vol targeting **reduced** Sharpe
   (1.17 vs 1.28). The Moreira–Muir Sharpe benefit is real but concentrates in crisis
   regimes absent from 2023–2025; detecting it needs decades or a crash in-window.

---

## 2. Findings on the dossier under review

Findings follow the gate-(a) convention: F*n*, severity, then the evidence.

### F1 — MAJOR — Candidate E (the PRIMARY recommendation) tests the wrong baseline

The dossier's E design compares vol-targeted sizing against a **fixed-size** baseline.
That repeats, in mirror image, the flaw class that killed D1: the gate-(c) verdict
turned on the Knowledge failing to beat the *strongest free no-Knowledge baseline*
(unconditional short), not a strawman. For a vol consumer the strongest free baseline is
**persistence sizing** (size ∝ 1/RV_t). Pre-read E measures the artifact at parity with
that baseline on total next-day vol (0.145 vs 0.154) and shows vol stability is achieved
equally by both. An E experiment as designed could "succeed" while demonstrating nothing
the platform couldn't have for free — an uninterpretable success.

There is one measured glimmer: the in-sample vol-target sim gives E[RV] Sharpe 1.17 vs
persistence 1.05. That difference is unverified noise until a block-bootstrap CI says
otherwise, but it is the *correct* comparison, and it is cheap to test.

**Required change if E proceeds:** the pre-registered gate must be
"Knowledge-scaled sizing beats persistence-scaled sizing" (primary), with fixed-size
reported as context only — and a gate-(c)-style triage with a pre-committed stop rule
should run **before** any pre-registration. If E[RV] cannot beat RV_t sizing, E fails
the same dumb-baseline test as D1 and must not be Phase 7's deliverable.
Additionally, the intraday-only variant (where the construct matches: 0.651 vs 0.590)
has near-zero expected return to stabilize — open→close index exposure excludes the
overnight component where most of the equity premium accrues — so it cannot rescue the
design either. This finding does not kill E; it removes its claimed exemption from the
transmission problem ("bypasses the construct gap" — §Candidate E) and makes its success
probability an open empirical question rather than a presumption.

### F2 — MAJOR — Candidate A4's construct claim is incorrect

The dossier rates the variance-swap strip "EXCELLENT — best construct match at daily
cadence… P&L ≈ Σ(σ²_realized − K²_var)… hold to expiry… feasible with bhavcopy." A
**static** strip of options held to expiry does not pay realized variance. The
log-contract replication (the basis of VIX) equals realized variance only when the strip
is **dynamically delta-hedged** in the underlying through expiry; unhedged, the strip's
payoff is a terminal-value bet — the same construct-gap family that produced the D1
STOP, spread across more strikes with more fees. Three additional defects: (i) the
hedge leg re-imports the intraday data problem that made the dossier reject A1 — A4 is
not an escape from it; (ii) horizon mismatch — a weekly strip prices multi-day variance
against a 1-day forecast; (iii) bhavcopy OTM wing quotes are stale/zero (the gate-(a)
audit's liquidity findings concentrate exactly there).

**Required change:** A4 moves from "FUTURE — strong Inc-2 candidate" into the same
bucket as A1/A3: blocked pending intraday data. It must not be queued as a
ready-to-research increment.

### F3 — MAJOR — Candidate F dismisses cross-sectional ranking on a data error

The dossier's F table rejects cross-sectional ranking with "Data: Stock 1m (not
available) → NO-GO (data: only Nifty index)." Cross-sectional momentum does not need 1m
data. It needs **daily EOD equity data**, and NSE equities daily bhavcopy is free,
official, and decades deep — the same source family as the options bhavcopy the platform
already ingests with a proven pipeline (gate a). With the data premise corrected,
cross-sectional relative strength becomes the strongest new-Knowledge candidate
available, on four grounds:

1. **Structural transmission.** The Knowledge (an expected-relative-return ranking) *is*
   the trade (hold the top of the ranking). There is no instrument wedge for a
   construct gap to open — the failure mode of D1, and re-measured in pre-reads A and E,
   cannot occur by construction.
2. **Precedent.** Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013 —
   momentum in emerging markets); unusually strong Indian evidence (academic studies;
   NSE's own NIFTY200 Momentum 30 index, live since 2020, with long back-history
   outperformance; live Indian momentum funds).
3. **Statistical power.** Validation is a cross-sectional rank IC over a panel of
   ~200–500 names per rebalance — an order of magnitude more effective observations than
   any single-series daily construct. It also needs no consumed held-out window: decades
   of history allow a genuinely fresh sealed window.
4. **Retail feasibility and fees.** Long-only cash delivery; STT 0.1% both sides, zero
   brokerage at discount brokers, low turnover at monthly rebalance — structurally
   lighter fees than the options program.

Honest liabilities, each gate-able exactly like gate (a): corporate-action adjustment
(splits/bonuses corrupt raw momentum), survivorship (historical universe membership
required), momentum-crash tail risk (2009-style reversals belong in the threat model),
and execution slippage on smaller names (mitigate with a liquid-universe filter, e.g.
NIFTY 200). By contrast the dossier's preferred Inc-2 (market regime) re-raises the
transmission question unanswered — the prior codebase's own post-mortem of a regime
classifier was "classifier works, strategy not profitable."

**Required change:** F's verdict table corrects cross-sectional ranking from
"NO-GO (data)" to the leading Inc-2 candidate, ahead of market regime, with the five
precondition gates named (ingestion + quality audit; corporate actions; survivorship;
delivery-equity fee model; **transmission triage before pre-registration**).

### F4 — MINOR — Candidate D's expected increment over trailing vol is now measured ≈ 0

Vol-scaled stops/targets are standard practice — implemented essentially everywhere with
*trailing* vol (ATR), not forecasts. Pre-read E quantifies the marginal content of
E[RV] over RV_t on the quantity execution cares about: nil on total vol (0.145 vs
0.154), +0.06 rank on intraday RV. The dossier's D test design (always-long beta host,
stops/targets in E[RV] units) would therefore most likely measure noise, and its host
has no positive expectation to protect. D as "GO (secondary)" overstates it: the correct
disposition is to implement vol-scaled execution with RV_t as the default whenever a
real host exists, and let E[RV] earn an upgrade through an A/B on real executions.

### F5 — OBSERVATION — A1's NO-GO is confirmed, and it implies an action the dossier omits

Pre-read A converts A1's data-blocked assumption into a measurement (0.198 transmission,
−0.012 signal rank, fee-fatal hedging) — CONFIRMED. But the correct response to "the
only economically clean monetization is blocked on data that doesn't exist" is to
**start the data existing**: the repo's `OptionsProvider` already snapshots full option
chains every 5 seconds into `data/market_data/options.duckdb` whenever the dashboard
runs. A supervised, always-on capture job (with a monthly quality audit) makes the
delta-hedged construct researchable in ~12–18 months at near-zero cost. This belongs in
the Phase-7 decision as a standing background action regardless of which candidate is
chosen.

### F6 — OBSERVATION — Candidate H: CONFIRMED, with one amendment

Both analyses independently converge on redefining Phase 7 as **"First Production
Knowledge Consumer."** Confirmed — with the completion criterion tightened per F1: the
pre-registered metric must demonstrate improvement over the **strongest free
no-Knowledge baseline** (named explicitly in the pre-registration; for vol consumers,
persistence-RV), not merely over "no Knowledge." Two shelving provisions should be
recorded at the same time: (i) quarterly forward scoring of the certified artifact
(observational, zero cost, monitors the Phase-6 fading-edge caveat and builds the
out-of-sample track record); (ii) named revival conditions — Revival-1: ≥ 12 months of
captured intraday chains → A1/A4 research unblocks; Revival-2: a validated host
portfolio exists → risk-consumer A/B vs persistence (E/C/D).

### Confirmations without findings

- **B (premium-selling filter): NO-GO confirmed.** Measured dead in the gate-(c) arms
  table; the dossier's B1–B4 reasoning is sound (the forecast catches persistent vol,
  not the jump/gap risk that kills sellers).
- **C (futures overlay): confirmed** — untestable without a validated host; a null is
  unattributable (archetype-B objection). Sequence after F produces a host.
- **G (multi-Knowledge framework): confirmed** — deferred; MSI v1.0 already supports
  multiple artifacts, so there is no framework to pre-build (over-engineering fence).
  The natural first instance is F's ranking sized/gated by a vol artifact — G is where
  E and F eventually meet.

---

## 3. Revised ranking (dossier ranking, amended per findings)

| Rank | Candidate | Dossier verdict | Review verdict | Basis |
|---|---|---|---|---|
| 1 | H — redefine Phase 7 | ADOPT | **ADOPT (confirmed, F6 amendment)** | both analyses converge; baseline criterion tightened |
| 2 | F — new Knowledge: **cross-sectional momentum** | FUTURE (regime preferred; cross-sectional "NO-GO data") | **GO — open as the second Knowledge program** | F3: data premise was wrong; structural transmission; panel power; best precedent |
| 3 | E — vol-targeted sizing | GO (PRIMARY) | **CONDITIONAL — triage first, persistence baseline** | F1: parity with free baseline on total vol (0.145 vs 0.154); overnight 31.8% outside construct; in-sample Sharpe glimmer (1.17 vs 1.05) is the one thing worth a cheap gate-(c)-style test |
| 4 | A — vol trading (A1–A5) | A4 FUTURE-best, rest NO-GO | **all data-blocked (F2, F5); snapshot capture job starts now** | measured 0.198 / −0.012 / fee-fatal; A4's construct claim incorrect |
| 5 | C — futures overlay | NO-GO until host | confirmed (FUTURE, after F) | no host exists |
| 6 | D — execution optimizer | GO (secondary) | **downgrade: FUTURE, RV_t default, E[RV] via A/B** | F4: increment over trailing vol measured ≈ 0 |
| 7 | G — multi-Knowledge | FUTURE | confirmed | needs ≥ 2 artifacts; nothing to pre-build |
| 8 | B — premium-selling filter | NO-GO | confirmed | measured dead (gate c) |

## 4. Recommendation to the operator

1. **Adopt H** (both parties agree): Phase 7 = "First Production Knowledge Consumer,"
   completion gated on beating the strongest free no-Knowledge baseline, named in the
   pre-registration. Record the MSRP shelving provisions (quarterly forward scoring;
   Revival-1/Revival-2).
2. **Run the E triage before committing Phase 7 to E** (days, not weeks; the pre-read
   script is 80% of it): pre-committed stop rule, primary comparison
   E[RV]-sizing vs RV_t-sizing, block-bootstrap CI on the Sharpe/vol-stability
   difference, overnight-inclusive returns. If it fails — the measured prior says it
   likely does — E is not Phase 7.
3. **Open the second Knowledge program: cross-sectional relative strength on NSE
   equities** (corrected F), under its own Phase-0-style charter with five precondition
   gates: (a) equity daily bhavcopy ingestion + quality audit; (b) corporate-action
   adjustment + audit; (c) survivorship/universe-membership handling + audit;
   (d) delivery-equity fee model; (e) transmission triage (measured rank IC with a
   pre-committed stop rule) **before** any pre-registration. If the E triage fails,
   this program is Phase 7's deliverable; if E passes, they proceed in sequence.
4. **Start the intraday options snapshot capture job now** (F5) — supervised,
   always-on, audited monthly. It is the cheapest action available that changes what is
   researchable a year from now.

The disagreement between this review and the dossier is narrow and empirical: the
dossier believes the vol Knowledge can demonstrate production value through sizing
today; the measurements say that is unlikely but cheaply testable, and that the
platform's first strategy with *structural* transmission is the equity cross-section.
Both paths run through the same next physical step — adopt H, then let the E triage's
pre-committed stop rule make the choice mechanically, exactly as gate (c) did for D1.

---

## Sources

- `docs/reports/MSRP_PHASE7_RESEARCH_RESET.md` (commit `9821932`) — dossier under review
- `scripts/msrp/scoping_transmission_preread.py` — pre-reads A and E (run 2026-07-08)
- `docs/reports/MSRP_PHASE7_FEE_TRIAGE.md`; `MSRP_PHASE7_GATES_BC_REVIEW_REQUEST.md` — STOP evidence and review discipline
- `docs/reports/MSRP_PHASE7_STRATEGY_RESEARCH.md`; `docs/reports/DRA_TECHNICAL_DOSSIER.md` — archetypes and prior-art post-mortem
- Bakshi & Kapadia (2003); Carr & Wu (2009); Moreira & Muir (2017); Fleming, Kirby & Ostdiek (2001, 2003); Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013)

*End of review. The operator decides.*
