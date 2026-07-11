# Market State Research Program (MSRP) — Phase 0 Charter

**Document type:** Program charter (Phase 0 — scoping & the decisions that gate the program)

**Status:** Phase 0 CLOSED (2026-07-06) — all §8 decisions locked; see the
"Phase 0 Decisions (LOCKED)" section below. Phase 1 (Research Dossier) unblocked.

**Date:** 2026-07-06

**Predecessor:** MM13 certified & merged to `main` (`c122443`) — the
`Knowledge → [Strategy]` arrow is proven end-to-end in PAPER. Engineering is no
longer the binding constraint. See
`docs/reports/MSI_ENGINE_PRODUCTIONIZATION_SCOPING.md` (Axis 2).

---

## 1. Why this program, why now

Every layer from real market data to a PaperBroker fill is built, certified, and
integration-proven:

```
Real data → ObservationReader → EvidenceBuilder → ArtifactEvaluator
  → KnowledgeBuilder → KnowledgePublisher → KnowledgeObject
  → KnowledgeSignalSource → GuardedSignalSource → ExecutionHandler → PaperBroker
```

The one thing this pipeline has never carried is *real Knowledge*. The sole
artifact today is the experimental VIX-threshold fixture. The open question is no
longer an engineering question — it is a **quantitative research** question:

> **What Knowledge should MSI produce?**

MSRP is the program that answers it. Its deliverable is **not code** — it is a
**research-backed, validated `PublishedArtifact` whose KnowledgeObjects
measurably beat the reference fixture**, plus the minimal validation
infrastructure required to certify it.

This is the Axis-2 / "MSI-010-class" program named in the scoping doc. It sits
**before** MM14 (LIVE readiness) and is distinct from "more MSI engines"
(Intraday / Options / Macro) — those are premature until *one* engine is proven
to deliver decision-driving Knowledge.

## 2. THE decision that gates the program (operator's call — make this first)

Scoping doc §5. For the **first** real artifact, the validation path is either:

- **(i) Full 7-domain MSI-006 up front** — build the complete conjunctive
  validation framework (Architectural, Scientific, Temporal, Robustness,
  Reproducibility, Operational, Calibration) before the first Approved verdict.
- **(ii) Minimal-but-conformant** — satisfy each of the seven mandatory domains
  with the **lightest defensible method**, producing a real, immutable
  validation record, and defer the heavier robustness/calibration *tooling* to a
  later artifact.

MSI-006 is conjunctive — (ii) is **not** "skip domains," it is "cover every
mandatory domain minimally, enrich later." This choice sizes the entire program
more than anything else.

**Recommendation: (ii) minimal-but-conformant.** It matches the thin-slice
strategy in §3 and lets the first increment finish in a bounded time. Build (i)'s
richer tooling only once one artifact has proven the pipeline. **Everything below
assumes (ii) unless the operator chooses (i).**

## 3. Operating principle — a thin vertical slice, not a grand framework

The temptation is to design a rich market-state framework — Trend, Volatility,
Participation, Liquidity, Momentum, Gap Risk, Market Health — *before* validating
anything. That is big-design-up-front, the exact trap that doing Axis-1 (MM13)
first was meant to avoid.

Invert it. **Pick one — at most two — falsifiable latent variables** and carry
them the whole distance:

```
hypothesis → features → labels → model → author (A1) → validate (A2, minimal)
  → Approved → publish → KnowledgeObjects → measured against the fixture
```

The `MarketState` DTO already supports N estimates, so choosing one now forecloses
nothing architecturally. Prove the **research → artifact → Knowledge pipeline**
end-to-end on a small hypothesis; grow the framework from a working spine. The
first increment's deliverable is bounded and provable: **one Approved artifact
that beats the fixture on a pre-registered metric.**

## 4. What MM13 already told us (free design input — do not re-derive)

MM13's `KnowledgeSignalSource` is the first real consumer of Knowledge. What it
actually needs from a `KnowledgeObject` is the empirical contract for
`PublishedArtifact v2`:

- It selects **one `Estimate` by `latent_variable` name** from
  `market_state.estimates` (`value` + `uncertainty`).
- It needs the estimate to be **present and named stably** (it emits nothing when
  the named estimate is absent).
- It carries `knowledge_id` / `artifact_version` / `provenance_reference` through
  to the signal's metadata for auditability.
- It does **not** need a scalar "confidence," a regime *label*, or any other
  field. The multidimensional-`MarketState`, per-estimate-uncertainty contract
  (MSI-OD-001 / MSI-5D-03) is sufficient and correct.

Implication: `PublishedArtifact v2` must emit **named latent-variable estimates
with quantified uncertainty**, stably named across versions. That is the whole
consumer contract. Design the artifact to that, not to a richer imagined API.

## 5. Preconditions (clear before Phase 1 research begins)

1. **Data freshness & breadth.** The candle store ends **2026-05-11 (1m) /
   2026-02-27 (1d)**; today is 2026-07-06. Top up with
   `scripts/fetch_upstox_historical.py` (chunked pull). Confirm the chosen
   hypothesis's required coverage — symbols, cadence, and history depth (a daily
   regime artifact wants a multi-year daily series; an intraday one wants clean
   1m breadth). This is a precondition, not a research phase.
2. **Point-in-time discipline.** Any feature/label the research uses must be
   reconstructable as-of a past date with no look-ahead. The
   `DuckDBObservationReader` reads a single date's file today; a real lookback
   needs either a spanning read path (Axis-2 engineering, scoped when the
   hypothesis demands it) or a hypothesis that is genuinely point-in-time.
3. **Reproducibility substrate.** Fix the RNG seeds, library versions, and data
   snapshot hash that the eventual validation record will cite (MSI-006
   Reproducibility domain), even under path (ii).

## 6. Phase map (increment 1 — the thin slice)

| Phase | Deliverable | Code? |
|-------|-------------|-------|
| **0** | This charter + the §2 decision + one pre-registered hypothesis & success metric | No |
| **1 — Research baseline** | DRA Research Dossier: objectives, model, features, labels, methodology, validation, failures, assumptions, sources. The falsifiable baseline. | No |
| **2 — Independent model review** | Institutional-style critique of the existing DRA/fixture model: hidden assumptions, leaking features, unstable labels, causal vs. merely-predictive variables, unmodelled uncertainty. | No |
| **3 — Latent-variable(s) definition** | **One (≤2)** latent variable(s) with an economic rationale, each estimated with uncertainty. NOT a 7-state framework. | No |
| **4 — Candidate feature library** | Features admitted only by answering "which latent variable does this estimate?" — point-in-time, measurable, leak-free. | No |
| **5 — `PublishedArtifact v2` spec** | Artifact conforming to §4's consumer contract: named estimates + uncertainty. MSI-007 shape (`metadata` + `evidence_rules` + `model` + `provenance` + `checksum`). | Author (A1) |
| **A2 — Minimal MSI-006 harness** | Real, immutable validation record covering all seven mandatory domains with the lightest defensible method; a resolvable `validation_id`. Built alongside Phase 5. | **Yes — the one required build** |
| **6 — Knowledge validation** | Generate KnowledgeObjects over a held-out window; test stability, economic usefulness, reproducibility, and whether they improve the downstream decision **vs. the fixture** on the pre-registered metric. | No (uses A2) |
| **7 — First alpha strategy** | Only now: a `core/strategies/` source that consumes v2 Knowledge and genuinely attempts P&L. Downstream of a proven artifact. | Yes |

**Increment 1 is complete when:** one `PublishedArtifact v2` reaches an **Approved**
verdict through the minimal MSI-006 harness, and its KnowledgeObjects beat the
reference fixture on the Phase-0 pre-registered metric over a held-out period.
The richer framework and additional latent variables are increment 2+.

## 7. Scope fence (do NOT do in MSRP increment 1)

- No runtime/engine changes — MSI, the DRA, and the execution stack are frozen and
  sufficient. MSRP changes the **artifact**, not the platform.
- No 7-latent-variable framework up front (§3).
- No full-fat MSI-006 tooling unless the operator picks path (i) in §2.
- No LIVE / MM14 work — downstream of a proven artifact.
- No additional MSI engines (Intraday / Options / Macro).
- No persistent `data/msi/knowledge.duckdb` beyond what Phase-6 evaluation needs
  (durable publication is an operationalization step, not a research one).

## 8. The Phase-0 decision the operator owns now

1. **§2 — validation scope:** minimal-but-conformant (recommended) or full 7-domain.
2. **The first hypothesis:** name the one latent variable, its economic rationale,
   its features' point-in-time availability, and the **pre-registered metric**
   that decides whether its Knowledge beats the fixture.
3. **Data top-up scope:** which symbols / cadence / history depth the hypothesis
   needs.

On those three answers, Phase 1 (the Research Dossier) begins and MSRP gets a full
program plan + a PROJECT_STATE entry. Nothing below Phase 0 is committed until then.

---

## Phase 0 Decisions (LOCKED — 2026-07-06)

All three §8 decisions are made. Phase 0 is closed; Phase 1 is unblocked.

### D1 — §2 validation scope: **(ii) minimal-but-conformant**

Cover all seven mandatory MSI-006 domains with the lightest defensible method,
producing one real immutable validation record. Heavier robustness/calibration
*tooling* deferred to a later artifact. Conjunctive — every domain covered, none
skipped.

### D2 — First hypothesis: **Forward volatility regime**

- **Latent variable:** `expected_next_day_realized_vol` — a single named estimate
  with quantified `uncertainty` (conforms to the §4 consumer contract).
- **Economic rationale:** volatility clusters and mean-reverts; next-day realized
  vol is partially predictable from trailing realized vol, India VIX, overnight
  gap, and prior-day range. It competes with the reference fixture on the
  fixture's own turf (the fixture is a VIX-threshold vol classifier).
- **Availability:** daily, point-in-time clean (§5.2 satisfied by construction —
  single-date as-of reads; no spanning-reader engineering).

### D3 — Pre-registered metric (the decision rule that gates "Approved")

- **Common binary target `Y`:** `Y = 1` if the next-trading-day realized
  volatility of `NSE_INDEX|Nifty 50` — computed from that day's 1m log-returns
  (index has volume=0; realized vol, never VWAP) — exceeds its **trailing
  20-trading-day median**, else `Y = 0`. One label per date, fully point-in-time.
- **Fixture → target mapping:** the reference fixture's discrete `market_regime`
  value (0/1/2) is used directly as its discriminant **score** for `Y`; the
  candidate's continuous `E[next-day RV]` is its score. Both are rankings of
  "how high-vol is tomorrow."
- **Primary metric: ROC-AUC** of each score against `Y`. Rank-based — compares a
  3-level discrete score and a continuous estimate without requiring probability
  calibration (which the discrete fixture cannot honestly provide). **Brier is
  secondary** (needs a calibration map; recorded, not decisive).
- **Held-out window:** `2026-01-01 → 2026-07-03`, pre-registered. The artifact's
  features and thresholds may touch **none** of it — development uses 2023–2025
  only. No feature/threshold selection may see the held-out window.
- **Success bar (Approved iff both hold):** `AUC_candidate − AUC_fixture ≥ 0.03`
  on the held-out window **AND** the 95% paired-bootstrap CI of the difference
  excludes zero. Rejects lucky point wins; exercises the required uncertainty.

### Precondition status

- **§5.1 data freshness — DONE.** Candle store (1m + 1d) tops up through
  `2026-07-03`. Data scope (§8.3) confirmed: the daily hypothesis is served by the
  existing 1m equity/index + 1d intermarket (Nifty 50, India VIX) coverage.
- **§5.2 point-in-time — SATISFIED** by choosing a daily, as-of-clean hypothesis.
- **§5.3 reproducibility substrate — OPEN (the one remaining precondition).** RNG
  seed, library versions, and the data-snapshot hash of the candle store
  @ 2026-07-03 are pinned when the Phase-1 dossier is built, cited against the
  held-out window above.

---

## Symmetry, stated plainly

- **MSI** solved the engineering problem: *deterministically transform
  observations into consumable Knowledge.*
- **MM13** proved that Knowledge flows through the execution platform.
- **MSRP** solves the scientific problem: *what Knowledge is actually worth
  producing* — and produces the first artifact that proves an answer.
