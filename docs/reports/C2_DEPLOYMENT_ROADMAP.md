# C2 Deployment Roadmap — From Recommendation to LIVE

**Date:** 2026-07-17
**Status:** Planning document — no phase is authorized until the operator ratifies the successor pre-registration (PSB-2 §12).
**Premise:** PSB-2 closed with C2 (fortnightly delivery-% anomaly, banded 0.40) as its sole eligible candidate. This roadmap assumes each subsequent gate PASSES and maps the full build to LIVE deployment. Every phase has an explicit exit gate; a FAIL at any gate terminates the roadmap for C2 — there is no "fix and re-read" path around a sealed-window failure.

---

## Where we are

| Fact | State |
|---|---|
| C2 recommendation | PSB-2 §8: IC +0.0349, net spread +4.57%, power 0.9198, deflated p 0.024 |
| Authorization scope | Proposal rights only — no sealed read, no strategy code, no allocation |
| Known weakness | Power projection rests on a 55-observation, 2.3-year SD estimate (deliv_pct starts 2020-01-01) |
| Weakness disposition | Ingestion boundary, not source limit — MTO archive backfill scoped (`PSB2_DELIVERY_HISTORY_SCOPING.md`); probe script drafted (`scripts/probe_historical_mto.py`, untracked) |
| Strategy layer | Greenfield — `core/strategies/` intentionally empty |
| Execution stack | F&O-oriented (fno_runner, Upstox adapter, NseMarginEngine, LoopDriver); equity delivery (CNC) live path unbuilt |
| Fee model | `core/execution/equity/delivery_fees.py` exists, era-accurate |
| LIVE account | None funded |

---

## Phase 0 — Evidence strengthening (MTO delivery-history backfill)

**Goal:** Convert C2's weakest link — the 55-observation SD — into a ~9-year estimate before spending the one-shot sealed read.

- **0.1 Feasibility probe.** Run `scripts/probe_historical_mto.py` (read-only against NSE, no store writes). Confirms (a) how far back the MTO archive serves, (b) format parses, (c) symbol join survives entity/rename handling.
- **0.2 Store backfill.** Add MTO as a fourth source era in `scripts/csmp/ingest_equity_bhavcopy.py` (delivery-only backfill 2012–2019; SECFULL still wins from 2020). Copy-first discipline: backfill a copy, diff, then swap.
- **0.3 Re-certification.** Re-run the four-arm contract suite (`scripts/psb1/certify_substrate.py`) on the modified store. The substrate certification is void until this is green — `equity_bhavcopy_adjusted` feeds both PSB and CSMP.
- **0.4 C2 SD re-estimation.** Re-run C2 formation on the extended dev window (still fenced at 2022-12-30). n grows from 55 to roughly 230+ fortnightly formations.

**Exit gate G0:** Extended-window IC and SD are consistent with the PSB-2 estimate (pin the tolerance *before* running 0.4). If the longer history **falsifies** C2 — IC collapses pre-2020 or SD balloons — that is the cheap failure this phase exists to buy, and the roadmap stops here.
**Fallback:** If the probe fails (archive gone/unparseable), skip to Phase 1 with the 55-observation SD owned explicitly in the pre-registration; the operator decides if that is enough.

## Phase 1 — Successor pre-registration ("C2-VAL")

**Goal:** A frozen protocol document, ratified by the operator, before anything in the sealed window is read.

Must pin, per PSB-2 §12:
- α and selection rule for a **single** candidate (m = 1 — no battery, no shopping).
- Execution conventions: fortnightly cadence, band 0.40, quintile construction, weights, κ slippage, the fee model version.
- Sealed-read mechanics: one read of 2023-01-01→2026-07-09, script-generated report, **digest computed over the entire artifact including verdict lines, all PASS/FAIL strings computed not hardcoded** (the PSB-2 MEDIUM-1 lesson).
- Its own view on the SD estimate (Phase 0 result or the owned 55-obs limitation).
- D2 disclosure: prior CSMP momentum read as prior exposure.
- **Deployment-grade criteria pinned now, not later:** turnover tolerance band (design 0.15 vs realized 0.27 happened once already), minimum net spread on the sealed window, and the LIVE kill criteria (drawdown, IC decay band) that Phases 5–7 will inherit.

**Exit gate G1:** Operator ratifies the frozen protocol. No code, no reads before this signature.

## Phase 2 — Sealed-window validation (the one-shot read)

**Goal:** Spend the sealed window exactly once, against the frozen harness.

- Run the frozen PSB-2 harness (scoring unchanged — fidelity tests `tests/psb2/test_fidelity.py` must be green first) over 2023→2026.
- Script-generated report with sealed digest; no hand edits, no re-runs with different parameters.

**Exit gate G2:** All pre-registered criteria PASS. A FAIL is terminal for C2 — the sealed window is now consumed and cannot be reused for a tweaked variant. Partial results do not get renegotiated after the read.

## Phase 3 — Strategy engineering (backtest-grade implementation)

**Goal:** A production implementation whose backtest reproduces the harness numbers *through the real execution stack*.

C2 is a fortnightly cross-sectional rebalance, not an intraday signal loop — the build must respect the constitution without forcing C2 into the LoopDriver's bar-by-bar shape:

- **Signal builder (offline, "Analytics Produce Facts"):** formation-date script computing delivery z-scores and target quintile portfolio from the certified store. Deterministic: same date → byte-identical target list.
- **Rebalance engine:** diffs target vs. held portfolio under the 0.40 exit band, emits `SignalEvent`s only (strategies stay dumb).
- **Execution handler (`core/execution/equity/`):** sizing, order generation, delivery fee application, position tracking across multi-day holds. `FillEvent` → `position_tracker.update_from_fill()` (known pitfall).
- **Corporate-action handling on live positions:** splits/bonuses/demergers must adjust *held quantities*, not just the research view — this is new surface; the CA machinery so far only serves the adjusted view.
- **Parity backtest — the acceptance test:** run the full stack over the dev window and reconcile against the harness net spread within a pinned tolerance. This is TDD at the system level: state the tolerance before the run.

**Exit gate G3:** Parity within tolerance + full walk-forward on dev data + test suite green.

## Phase 4 — Data operations hardening

**Goal:** The research-time pipeline becomes a daily production pipeline.

- Automated daily SECFULL ingest (bhavcopy + delivery) with freshness checks; a formation date with stale delivery data must **refuse to trade** (readiness-gate pattern already proven in `SpanReadiness`).
- Ongoing CA ingest cadence + universe point-in-time maintenance (`symbol_entity_intervals`, `symbol_changes`).
- Fortnightly formation calendar with NSE holiday handling.
- Ingest-failure alerting; a missed day must be loud, not silent (silent-failure discipline).

**Exit gate G4:** N consecutive unattended daily cycles (pin N; suggest 10) with zero manual intervention.

## Phase 5 — Paper trading (shadow deployment)

**Goal:** The full live path, end-to-end, with PaperBroker under CNC delivery semantics.

- Run ≥ 6 rebalance cycles (~3 months minimum; 6 preferred to span at least one CA event and one expiry-adjacent volatility window).
- Every order explainable from analytical facts (audit-first).
- Track: realized turnover vs. the pinned band, fill prices vs. the κ = 5bp/side assumption, tracking error vs. a concurrent backtest of the same window.

**Exit gate G5:** Tracking error and turnover inside pre-registered bands; zero unexplained orders; zero manual interventions.

## Phase 6 — LIVE readiness and pilot

**Goal:** First real capital, small, with the safety rails built *before* funding.

- **Broker build-out:** Upstox equity delivery (CNC) order path in the adapter — the current adapter surface is F&O-oriented and the delivery path must be verified against real API behavior. Order-rejection and partial-fill handling for delivery orders.
- **Broker reconciliation:** the deferred LIVE-only capability (ADR-013) now has its concrete need — daily fetch/compare/log of broker positions & funds vs. local state. Still never consulted for sizing (two-authorities architecture stands).
- **Ops:** monitoring dashboard (Flask, display-only), run-book, kill switch that flattens to cash and halts formation.
- **Pilot:** small fixed capital, per-name cap, portfolio cap, the Phase-1 kill criteria armed.

**Exit gate G6 (go-LIVE):** funded account + reconciliation green for a full paper cycle + operator sign-off.
**Exit gate G7 (pilot review):** ≥ 6 LIVE cycles reconciled against paper/backtest expectations before any capital increase.

## Phase 7 — Steady state and governance

- Capital ramp rules (stepwise, gated on rolling tracking error).
- **IC decay monitor:** rolling realized IC against the pinned band from Phase 1 — crossing it triggers review, not silent hope.
- Annual substrate re-certification; slippage model recalibration from realized fills.
- **Retirement criteria are part of the strategy**, pre-registered — a strategy without a death condition is a future unbounded loss.

---

## Decision-gate summary

| Gate | Question | On FAIL |
|---|---|---|
| G0 | Does 9-year history confirm the SD/IC? | C2 falsified cheaply — stop |
| G1 | Operator ratifies frozen C2-VAL protocol? | No read occurs |
| G2 | Sealed window PASS? | **Terminal** — window consumed |
| G3 | Stack reproduces harness numbers? | Fix implementation, not the numbers |
| G4 | Pipeline runs unattended? | Not deployable, regardless of alpha |
| G5 | Paper matches backtest? | Diagnose divergence before any funding |
| G6/G7 | LIVE pilot reconciles? | Kill switch, post-mortem, no ramp |

## Explicitly out of scope

- No second strategy is stacked into this roadmap; promotion never happens inside a screening battery, and additions get their own pre-registration.
- No broker-RMS margin cloning; NseMarginEngine remains the sole sizing authority.
- No timeline promises tied to calendar dates — each gate is evidence-gated, not schedule-gated. Rough shape if everything passes first try: Phase 0 ≈ 1–2 weeks, Phases 1–3 ≈ 3–5 weeks, Phase 4 ≈ 2 weeks, Phase 5 ≈ 3 months of wall-clock shadow, Phase 6 pilot ≈ 3 months. **LIVE at scale is realistically ~7–9 months out**, dominated by shadow/pilot wall-clock time that cannot be compressed without destroying the evidence.
