# Cross-Sectional Momentum Program (CSMP) — Phase 0 Charter

**Document type:** Program charter (Phase 0 — scoping & the decisions that gate the program)

**Status:** Phase 0 CLOSED (2026-07-08) — all §8 decisions locked as recommended; see
the "Phase 0 Decisions (LOCKED)" section below. Gates (a)–(e) unblocked.
**Implementation party: DeepSeek V4. Lead Reviewer: Claude** (prompts and reviews only —
does not implement). Implementation prompts: `docs/reports/CSMP_IMPLEMENTATION_PROMPTS.md`.

**Date:** 2026-07-08

**Predecessor:** MSRP Phase-7 research reset, operator decision LOCKED 2026-07-08
(`docs/reports/MSRP_PHASE7_RESEARCH_RESET_REVIEW.md` §Operator decision): Candidate H
adopted — Phase 7 redefined as **"First Production Knowledge Consumer"** — and
cross-sectional relative strength (momentum) on NSE equities selected as the platform's
second Knowledge program and Phase 7's deliverable path. The MSRP
`ForwardVolatilityArtifact` is shelved under its recorded revival conditions; nothing in
CSMP touches it.

---

## 1. Why this program, why now

MSRP proved the platform end-to-end and then proved something more valuable: **a
correct forecast is worthless without a transmission to P&L.** The certified vol
artifact ranked next-day RV at Spearman 0.65 and still could not beat a dumb baseline
through any instrument reachable with obtainable data (gate-c STOP; research-reset
pre-reads). The generalized lesson, now institutionalized: *choose the Knowledge
construct so that the forecast and the trade are the same object.*

Cross-sectional momentum is that construct:

> **The Knowledge is a ranking of expected relative returns across the equity
> cross-section. The strategy is holding the top of the ranking. There is no
> instrument wedge for a construct gap to open — the D1 failure mode cannot occur
> by construction.**

Supporting facts (research-reset review, F3):

- **Precedent:** Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013 —
  momentum in emerging markets); unusually strong Indian evidence (academic studies;
  NSE's NIFTY200 Momentum 30 index live since 2020; live Indian momentum funds).
- **Data:** NSE equities daily bhavcopy — free, official, decades deep; the ingestion
  pattern is proven (options bhavcopy, gate a of the prior program).
- **Statistical power:** validation is a cross-sectional rank IC over ~200–500 names
  per rebalance — a panel, an order of magnitude more effective observations than any
  single-series daily construct. No consumed held-out window: equities history allows a
  genuinely fresh sealed window.
- **Fees:** long-only cash delivery at monthly cadence is structurally lighter than the
  options program (no per-day round trips; zero brokerage on delivery at discount
  brokers).

## 2. THE decisions that gate the program (operator's call — §8)

Unlike MSRP Phase 0 (whose sizing decision was validation scope), CSMP's sizing
decisions are the **universe** and the **signal shape** — they determine data volume,
gate difficulty, and statistical power. Recommendations are in §8; nothing below §8 is
binding until locked.

## 3. Operating principle — thin vertical slice (unchanged from MSRP)

One falsifiable hypothesis carried the whole distance:

```
hypothesis → features → labels → artifact (A1) → validation (A2-style, minimal)
  → Approved → KnowledgeObjects → portfolio consumer → measured vs. free baselines
```

No multi-factor framework (value/quality/low-vol are increment 2+). No short leg
complexity before the long-only slice is proven. The deliverable of increment 1 is
bounded: **one Approved ranking artifact whose top-bucket portfolio beats the
pre-registered free baselines on a sealed window** — and, per the redefined Phase 7,
the **first production Knowledge consumer** that trades it in PAPER.

## 4. Consumer contract (free design input — this program's MM13 note)

The MM13 `KnowledgeSignalSource` selects **one** estimate by `latent_variable` name —
sufficient for a scalar forecast, **not** for a cross-section. What carries over and
what changes:

- `MarketState` already supports **N estimates** (MSI-OD-001), and each `Estimate`
  carries a `dimension` field — the artifact can emit one named estimate per universe
  symbol (e.g., `latent_variable = "xs_momentum_score"`, `dimension = <symbol>`), each
  with quantified `uncertainty`. No DTO or runtime change required.
- The **consumer is new code by design**: a portfolio-constructing SignalSource
  (select top-K by score, emit rebalance signals) in the MM13 mold — conformance-tested,
  wrapped in `GuardedSignalSource`, PaperBroker only. That is precisely the Phase-7
  deliverable under Candidate H; strategies stay dumb (ranking consumed as-is; sizing
  and risk live in execution).
- Auditability carries through unchanged: `knowledge_id` / `artifact_version` /
  provenance in every signal's metadata.

The uncertainty field must be honest, not decorative: Phase 1 defines a defensible
per-name score uncertainty (e.g., estimation variance of the formation-window return)
and where it participates (abstention/weighting), or explicitly pre-registers that
increment 1 consumes ranks only and uncertainty is reported-not-acted-on.

## 5. Preconditions — the five gates (locked by the operator decision, run in order)

Every gate produces an audited report and has a Lead-Reviewer pass before the next
begins; gate (e) carries a pre-committed stop rule. No pre-registration until all five
pass.

1. **(a) Equity daily bhavcopy ingestion + quality audit.** Full daily EOD series
   (price OHLC, volume, delivery quantity, series flag) for the chosen universe's
   history, into a dedicated DuckDB store. Audit: coverage by year, missing-day
   reconciliation against the exchange calendar, duplicate/zero-price screens, series
   handling (EQ/BE), symbol-rename mapping.
2. **(b) Corporate-action adjustment + audit.** Splits/bonuses (and rights, where
   material) corrupt raw momentum. Source adjustment factors, apply, and audit: every
   > |20%| single-day price move in the dev window must be classified (corporate action
   vs. genuine move); unexplained residue is a gate failure.
3. **(c) Survivorship / universe-membership handling + audit.** Point-in-time universe
   membership (index constituent history, or a mechanical liquidity rule computed from
   ingested data only). The dev universe on date *t* must be reconstructable using
   information available at *t*. Delisted names remain in the panel until their exit.
4. **(d) Delivery-equity fee model.** Effective-dated schedule in the gate-(b)-of-MSRP
   mold: STT on delivery (both sides), stamp duty (buy), NSE transaction charge, SEBI
   fee, GST, DP charge per sell line. Unit-tested; era-accurate rates.
5. **(e) Transmission triage (the D1 lesson, institutionalized).** Before any
   pre-registration: measured monthly cross-sectional rank IC of the candidate score vs
   forward returns on the dev window, and a rough top-bucket-minus-baseline net-of-fee
   pass. **Pre-committed stop rule** (final numbers fixed when the gate is specified,
   in the research doc that precedes it): if the dev-window mean rank IC or the
   net-of-fee top-bucket spread over the strongest free baseline is ≈ 0, stop —
   do not pre-register.

## 6. Phase map (increment 1 — the thin slice)

| Phase | Deliverable | Code? |
|-------|-------------|-------|
| **0** | This charter + §8 decisions locked | No |
| **Gates (a)–(e)** | Five audited precondition reports (§5) | Ingestion + fee scripts only |
| **1 — Research dossier (pre-registration)** | Hypothesis, features, labels, methodology, metric, decision table, threats-to-validity — frozen before the sealed window is touched | No |
| **2 — Independent model review** | Institutional-style critique; revisions folded in; dossier FROZEN | No |
| **3/4 — Latent variable + features** | `xs_momentum_score` per name with uncertainty; formation-window features, point-in-time, leak-free | No |
| **5 — Artifact authoring (A1)** | `PublishedArtifact v2`, MSI-007 shape, coefficients/parameters frozen from dev window only | Author |
| **A2 — Validation harness (cross-sectional)** | Minimal-but-conformant MSI-006 record, all seven domains; scoring adapted to the cross-sectional metric | **Yes — the one required harness build** |
| **6 — Held-out scoring** | Single scoring run on the sealed window; Approved/Rejected per the pre-registered decision rule | No (uses A2) |
| **7 — First Production Knowledge Consumer** | Portfolio SignalSource consuming the ranking in PAPER, measured against the pre-registered free baselines net of fees | Yes |

**Increment 1 is complete when:** the artifact reaches an Approved verdict on the sealed
window **and** the PAPER consumer's pre-registered metric beats the strongest free
no-Knowledge baseline (the Candidate-H completion criterion).

## 7. Scope fence (do NOT do in CSMP increment 1)

- No changes to frozen components, MSI runtime, the DRA, the execution stack, or
  anything MSRP-sealed. CSMP adds an artifact, ingestion/fee scripts, one harness
  scoring variant, and one strategy-layer consumer.
- No multi-factor framework (momentum only; value/quality/low-vol are increment 2+).
- No short leg (see §8-D4). No F&O, no leverage, no intraday equity trading.
- No LIVE work (MM14 fence unchanged). PAPER only.
- No combination with the shelved vol artifact (that is Candidate G — after this
  program produces a validated host).
- No optimization tours: one formation/holding specification pre-registered; parameter
  grids belong to the dev window and must be disclosed in the dossier if used at all.

## 8. The Phase-0 decisions the operator owns now

**D1 — Universe & liquidity filter.** The panel the ranking is computed over.
- (i) NIFTY 100 — most liquid, weakest breadth (~100 names);
- **(ii) NIFTY 200 — recommended.** Liquid enough for retail delivery execution,
  breadth of ~200 names for the cross-section, and NSE publishes a directly comparable
  public benchmark (NIFTY200 Momentum 30);
- (iii) NIFTY 500 — maximum breadth, materially harder gates (b)/(c) and worse
  execution realism in the tail.
- Gate (c) difficulty depends on this choice: point-in-time membership history must be
  obtainable for the chosen index (fallback if unobtainable: a mechanical top-N-by-
  6-month-median-turnover rule computed from ingested data only — decidable at gate c).

**D2 — Signal shape & cadence (the hypothesis).** Recommended: **classic 12-1
momentum** — formation = trailing 12 months excluding the most recent month (the
short-term reversal exclusion), **monthly rebalance**, top-quintile (~40 names at
NIFTY 200) or top-30 equal-weight holding. Well-precedented, low-turnover, deliberately
un-optimized. Alternatives (6-1 formation, weekly cadence) belong to increment 2, not
to a dev-window search.

**D3 — Pre-registered metric, baselines, and success bar.** Recommended structure
(final numbers frozen in the Phase-1 dossier, MSRP D3-style):
- **Research metric (artifact-level):** monthly cross-sectional Spearman rank IC of the
  score vs next-month total return over the point-in-time universe; primary gate on the
  sealed window: mean IC > 0 with a block-bootstrap 95% CI excluding zero.
- **Economic qualifier (consumer-level, the Candidate-H criterion):** top-bucket
  equal-weight portfolio net of the gate-(d) fee model vs **two named free baselines**:
  (1) the equal-weight universe portfolio (strongest free no-Knowledge baseline — "just
  buy everything"), and (2) the published NIFTY200 Momentum 30 total-return index (the
  strongest free *momentum* baseline — does our artifact add anything over a free
  public implementation?). Baseline (1) gates; baseline (2) is a reported reference arm.
- **Decision table pre-fixed** (Approved / Rejected / Inconclusive-extend), including
  the modal-outcome honesty the MSRP reviews demanded.

**D4 — Long-only vs long-short.** Recommended: **long-only.** Cash-equity shorting
cannot be held overnight at retail in India; a short leg forces single-stock futures
(margin, roll, borrow realism) and re-imports execution complexity that increment 1
exists to avoid. The long-only top bucket vs the universe baseline is the honest first
test; the short leg is increment 2+ if ever.

**D5 — Dev / sealed / forward windows.** Recommended: **dev = 2012-01 → 2022-12**
(11 years, ≥ 2 momentum-crash-relevant episodes incl. 2013 taper, 2018, 2020 COVID);
**sealed held-out = 2023-01 → 2026-06** (never touched by any dev choice — CSMP has no
consumed-window problem, this is a genuinely fresh seal); **forward** accumulation
continues after pre-registration for the PAPER consumer. Gate (a) ingests 2010→present
to give the 12-month formation window runway before dev starts.

On these five locks, the gates begin — gate (a) first. Nothing below Phase 0 is
committed until then.

---

## Phase 0 Decisions (LOCKED — 2026-07-08)

All five §8 decisions locked by the operator as recommended. Phase 0 is closed; the
gates begin at (a).

- **D1 — Universe: NIFTY 200** constituents, point-in-time membership (gate (c)
  determines the source; fallback if membership history is unobtainable: mechanical
  top-200-by-6-month-median-turnover computed from ingested data only).
- **D2 — Signal: classic 12-1 cross-sectional momentum**, monthly rebalance,
  equal-weight top bucket. The exact holding rule (top-quintile ≈ 40 vs top-30) is
  frozen in the Phase-1 pre-registration; gate (e)'s triage uses top-quintile
  provisionally.
- **D3 — Metric & baselines:** monthly cross-sectional Spearman rank IC (primary gate:
  mean IC > 0, block-bootstrap 95% CI excluding zero on the sealed window); economic
  qualifier: net-of-fee top-bucket portfolio vs (1) equal-weight universe (gating
  baseline) and (2) NIFTY200 Momentum 30 TRI (reported reference arm). Decision table
  pre-fixed in the Phase-1 dossier.
- **D4 — Long-only.** No short leg in increment 1.
- **D5 — Windows:** dev = 2012-01 → 2022-12; sealed held-out = 2023-01 → 2026-06
  (untouched by any dev choice); forward accumulation thereafter. Gate (a) ingests
  2010-01 → present for formation runway.

**Role split (locked):** DeepSeek V4 implements every gate deliverable from the written
prompts; Claude acts as Lead Reviewer only — writes the prompts, audits each gate
report, and issues PASS / NOT PASSED verdicts before the next gate begins. Claude does
not implement gate deliverables.

---

## Threats acknowledged at charter time (carried into the Phase-1 threat model)

- **Momentum crashes** (2009-class reversals): fat left tail at exactly the wrong time;
  the dev window must contain stress episodes, and the dossier's threat model must
  quantify drawdown expectations honestly (no crash-timing overlay in increment 1).
- **Crowding/decay:** Indian momentum premia are well-known and increasingly
  ETF-implemented; the sealed-window test is the defense — the edge must show up
  out-of-sample, not in 1990s literature.
- **Data integrity is the real work:** gates (b) and (c) — corporate actions and
  survivorship — are where equity cross-section research quietly dies. They are gated
  with Lead-Reviewer passes for exactly that reason.
- **Execution realism:** monthly rebalance of ~30–40 delivery names is retail-feasible,
  but bhavcopy close-price fills are optimistic; the fee model plus a disclosed slippage
  assumption belongs in the pre-registration.

## Symmetry, stated plainly

- **MSRP** proved the platform can produce, validate, and *refuse to deploy* Knowledge —
  the STOP was the methodology working.
- **CSMP** picks the construct where forecast and trade are the same object, and aims to
  produce the platform's **First Production Knowledge Consumer** (Phase 7, as redefined
  under Candidate H).
