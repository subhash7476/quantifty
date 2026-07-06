# MSI Engine Productionization — Scoping & Roadmap

**Document type:** Scoping proposal (pre-program — not an approved milestone plan)

**Status:** Proposed — awaiting direction

**Author:** Platform (scoping pass)

**Date:** 2026-07-04

**Question answered:** *DRA implementation is done — what should be next?*

---

## 1. Purpose

The DRA reference implementation (M0–M9) and MSI v1.0 are certified. This document scopes
what comes next, sequences the candidate tracks, and answers the one structural question
that dominates the decision:

> **Does the MSI Research pipeline need to be built?** — **Yes.** It was never in DRA scope
> (MSI-009 §6 explicitly forbids the DRA from training, optimising, validating, or researching).
> No research/validation/inference code exists today; only the frozen specs do.

This is a scoping document. It does not pre-specify harnesses, algorithms, or milestones in
detail — it frames the decision the operator needs to make before a program plan is written.

---

## 2. Where things actually stand

Three things are certified and frozen:

| Layer | Status |
|-------|--------|
| Platform Infrastructure v1.0 (execution substrate) | Certified (MM11.7) |
| MM12 — Strategy Integration Contract (`SignalSource`, conformance, `GuardedSignalSource`, heartbeat canary, promotion ledger) | Complete |
| MSI v1.0 — architecture MSI-001…009 frozen + DRA runtime (M0–M9, 283 tests) | Certified |

### The three gaps that define "next"

1. **The DRA has never produced real Knowledge.** Every milestone ran against a *test artifact*
   (the VIX-threshold classifier fixture) and a *test DuckDB fixture*. `data/msi/` does not exist;
   no `knowledge.duckdb`, no run over real history.
2. **The DRA is wired to nothing.** No script imports `core.msi`; it executes only from tests.
   There is no composition root / entry point that runs `DRAOrchestrator` in production.
3. **The "→ Strategy" arrow is unbuilt.** Nothing consumes Knowledge. `core/strategies/` is still
   intentionally empty; only the non-alpha heartbeat source exists.

The runtime pipeline stops one arrow short of usefulness:

```
Observation → Evidence → Artifact Evaluation → Knowledge → [ Strategy ]   ← nothing consumes Knowledge
```

---

## 3. Central finding — "Make the DRA real" is not one step

Producing a *real, governed* DRA run requires four things, only the last of which is small:

- **A1 — Research authoring harness.** Tooling to construct and emit a Published MSI Artifact
  (MSI-007 shape: `metadata.json` + `evidence_rules.json` + `model.py` + `provenance.json` +
  `checksum.sha256`). None exists — the sole artifact today was hand-authored as a test fixture.
- **A2 — MSI-006 validation harness.** MSI-006 defines **seven conjunctive validation domains**
  (Architectural, Scientific, Temporal, Robustness, Reproducibility, Operational, Calibration).
  A real artifact's `validation_id` must resolve to a **complete, immutable validation record**.
  The fixture's `validation_id` (`val-ref-test-001-v1`) resolves to nothing. No validation code exists.
- **A3 — Author + validate the first real artifact.** A genuine regime-classification model over
  real market data, carried through A1→A2 to an **Approved** verdict.
- **A4 — Operationalize.** A composition-root script that runs `DRAOrchestrator` on production
  data and publishes Knowledge to `data/msi/knowledge.duckdb` (plus optional schedule/telemetry/UI).

A1–A3 are a program comparable in size to the DRA runtime build itself. **This is the honest
scope of "make the DRA real."**

### The real binding constraint is not tooling — it is alpha research

MSI-006 Domain 2 (Scientific) requires a **hypothesis with empirical and out-of-sample support**.
The gate on a *trustworthy* first artifact is therefore *"does a regime hypothesis worth
productionizing exist yet?"* — greenfield quant research, different in kind from the deterministic
infrastructure work done so far. (Note: the research side is **not** bound by the runtime's
determinism discipline, so the A1 harness is lighter than the DRA build; the weight is in A3's science,
not A1's code.)

---

## 4. The decomposition that changes the recommendation

The naive sequence is A ("make DRA real") → B ("first strategy"). But B bundles two independent axes,
and bundling them makes the **first end-to-end proof wait on the entire research program**. Split them:

### Axis 1 — Integration / plumbing (cheap, front-runnable)

`KnowledgeObject → Strategy → GuardedSignalSource → execution → PAPER`.

This needs *a* Knowledge object **of the right shape** — not a *validated* one. It can be proven
**now**, against the existing (experimental / clearly-labeled) artifact, via `DRAOrchestrator` +
a thin regime-reading `SignalSource` run through `fno_runner`. This de-risks the "→ Strategy" arrow
and is most of MM13's integration surface. Precedent exists: the heartbeat canary proved
data→execution plumbing separately from alpha.

Governance is compatible: MSI-009 §13 requires *Active Published (validated)* artifacts only for
**production** runs; an **experimental PAPER integration proof** does not need Axis 2.

### Axis 2 — Real content (heavy, research-gated)

A1 research harness + A2 validation harness + A3 first *trustworthy* artifact. Gated on actual
quant research, and on data availability (§6).

### Why this ordering wins

Axis 1 first surfaces **which Knowledge fields a strategy actually needs** — which is the design
input to Axis 2's artifact. It turns the "B-informs-A design spike" into a concrete, shippable
milestone instead of a paper exercise, and delivers the first end-to-end proof (real stack, real
composition root) that the roadmap has deferred since MM11 — without waiting on research.

---

## 5. The one decision that dominates cost

For the **first** real artifact (A3), do we:

- **(i)** build the **full 7-domain MSI-006** validation framework up front, or
- **(ii)** define a **minimal-but-conformant** validation path — a real, immutable validation record
  that genuinely covers the mandatory domains for a first artifact — and defer the heavier
  robustness/calibration tooling to a later artifact?

MSI-006 is conjunctive (no domain can be skipped for an *Approved* verdict), so (ii) is not
"skip domains" — it is "satisfy each mandatory domain with the lightest defensible method, and
build richer tooling later." This choice sets the size of Axis 2 more than anything else. **It is
the operator's call and should be made before an Axis-2 program plan is written.**

---

## 6. Preconditions / open items

- **DATA (blocking for Axis 2).** `data/` is gitignored; the candle store CLAUDE.md describes
  (`data/market_data/nse/candles/`) is **absent from this working tree**. A separate
  `historical/index/1m/` store exists (2024-01→), plus the instrument master. **Nifty 50 + India VIX
  coverage at the cadence a daily regime artifact needs (90-day lookback, daily close) is
  unconfirmed here.** Verify coverage and cadence before committing to Axis 2. (Axis 1 can proceed
  on the existing fixture data.)
- **CLAUDE.md data-layout drift.** The documented `1d/` intermarket path does not exist in this tree —
  reconcile the doc with reality as part of any data-prep step.

---

## 7. Governance reconciliation (avoid an orphan track)

Slot this into existing numbering rather than inventing a parallel sequence:

- **Axis 1 ≈ MM13** ("First External Strategy Validation — PAPER", already named in PROJECT_STATE
  Planned). The first Knowledge-consuming `SignalSource` run through `fno_runner` in PAPER *is* the
  MM13 integration surface.
- **Axis 2 = a new MSI-engine-productionization program** (an MSI-010-class effort: Research authoring +
  Validation harness + first Approved artifact). This is distinct from the MSI "Future Specifications"
  list (Intraday / Options / Macro / … engines), which are *additional* engines and are premature until
  one real engine is proven end-to-end.
- **MM14** (LIVE readiness + broker margin reconciliation) is unchanged and downstream of both.

More MSI engines and a daily scheduler/dashboard are downstream of proving *one* engine delivers real,
decision-driving Knowledge — they are not the next step.

---

## 8. Recommendation

1. **Front-run Axis 1 (≈ MM13 integration):** build a thin regime-reading `SignalSource` that consumes
   `DRAOrchestrator` Knowledge (experimental artifact) and prove it through `fno_runner` in PAPER.
   Cheapest path to the first real end-to-end proof; surfaces the Knowledge contract a strategy needs.
2. **Use that contract to design the real artifact**, then decide §5 (full vs minimal-conformant MSI-006).
3. **Then execute Axis 2** (Research harness → validation → first Approved artifact → governed DRA run
   into `data/msi/`), after the §6 data precondition is cleared.

---

## 9. Next action for the operator

Pick the entry point:

- **Start Axis 1 now** (build the integration milestone / MM13 spec), or
- **Plan Axis 2 first** (write the MSI-010-class program plan, incl. the §5 validation-scope decision), or
- **Resolve §6 data first** (confirm Nifty/VIX coverage before anything else).

Nothing here is approved yet — this document only frames the choice. On approval, the chosen track
gets a full program plan and a PROJECT_STATE entry.
