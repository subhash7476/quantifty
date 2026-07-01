# MM11 — Architecture Review & Proposal

**Date:** 2026-07-01
**Author role:** System Architect
**Type:** Architecture review + milestone proposal (no implementation code)
**Predecessor:** MM10 (SPAN portfolio margin) closed 2026-07-01 — ADR-011, ADR-012, ADR-013.
**Related:** `docs/ARCHITECTURE_DECISIONS.md`, `docs/PROJECT_STATE.md`, CLAUDE.md.

---

## Part 1 — Architecture Review: What Should MM11 Be?

### 1.1 Method

This review evaluates the platform objectively against its own governing documents
(`docs/PLATFORM_CONSTITUTION.md`, `docs/ARCHITECTURE_DECISIONS.md`, CLAUDE.md) rather than
defaulting to the next technically obvious task. It surveys what is actually built, what is
actually missing, and what a next milestone is structurally permitted to be.

### 1.2 Current state (as of MM10 close)

- **Execution core is essentially complete.** `LoopDriver` (Phases A–H, all closed), `ExecutionHandler`
  (risk gates, idempotency, kill-switch, per-signal isolation), `RuntimeWatchdog`, the Runtime
  Event Journal, and `RuntimeTelemetryPublisher` (metrics/health/positions, §10 fully complete)
  are all built, tested, and feature-frozen or stable.
- **Margin is complete and closed.** SPAN scan-risk, contract-level RA routing, calendar spread
  credits, ELM, and the two-authorities model are done (MM9.5–MM10, ADR-007/011/012/013). No
  further margin scope exists without a fresh decision.
- **Instrument identity and broker mapping are complete.** Phase 4C (canonical instrument,
  resolver, Upstox mapping, product/segment defaults) and broker-position reconciliation (#6a/#6b)
  are both COMPLETE per `docs/PROJECT_STATE.md`.
- **The sole remaining gate before `ExecutionMode.LIVE` is operational, not architectural**: a
  first-hand authenticated non-empty `short-term-positions` capture (the account currently has no
  funding/positions). No code work unblocks this.
- **There is no strategy.** `core/strategies/` does not exist in this repository. Per CLAUDE.md
  ("Production Strategy Status") this is intentional and greenfield, and per **ADR-002**
  strategies, backtesting, ML training, and research explicitly **live outside this repository**.
  Grepping the repo confirms there is no in-repo backtest engine either — consistent with ADR-002,
  not an oversight.
- **`SignalSource` is a complete, well-specified abstract contract** (`core/runtime/signal_source.py`)
  but has **zero production implementations** — verified directly (`grep 'class \w+(SignalSource)'`
  across the repo): every subclass (`NoopSource`, `BuyExitSource`, `FakeSignalSource`,
  `SyntheticBuyExitSource`, and the `test_signal_source.py` fixtures) lives under `tests/`; none
  exist under `core/` or `scripts/`. **ADR-MM7E-1** deliberately deferred constructing a real
  `SignalSource` to "a later slice that wires the terminal root" — that slice has not happened.

### 1.3 Candidates considered and rejected

| Candidate | Verdict | Reason |
|---|---|---|
| **First production strategy / strategy framework** | **Rejected** | Directly violates ADR-002 (strategy/backtest/research live outside this repo) and CLAUDE.md's explicit instruction that architectural decisions must not assume a specific future strategy. Building strategy logic in-repo would also violate ADR-002's checkable invariant (no `Platform → Strategy` coupling, and the inverse — a strategy grown *inside* the platform — collapses the same boundary from the other direction). |
| **Broker margin reconciliation** | **Rejected for now** | Explicitly deferred by ADR-013 (this same session) pending a production strategy and a funded LIVE account; no operational need exists today. Building it now would repeat the premature-abstraction pattern already rejected once (`MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md` Q4/Q5). |
| **Live execution readiness / ops hardening, standalone** | **Rejected as a standalone milestone** | Real and worth doing (credential lifecycle, deployment, go-live checklist) but *with zero strategies and none coming in-repo, there is nothing to trade live*. `fno_runner`'s LIVE rung requires an injected `SignalSource` (ADR-MM7E-1) and none exists. Ops hardening in isolation optimizes a runtime nothing will drive — it is better framed as a **co-component** of the milestone below, not the milestone itself. |
| **Broker integration improvements (multi-broker)** | **Rejected** | Premature per the same reasoning as the rejected `MarginProvider` abstraction (ADR-013 Alternatives): exactly one broker is integrated; generalizing now guesses an interface from zero second implementations. |
| **Deployment architecture (containerization, process supervision)** | **Folded in, not standalone** | Real gap (no Dockerfile, no systemd unit, no documented process-restart policy) but it is an operational sibling of "how does a strategy actually run live," not an independent architectural chapter. |
| **Platform housekeeping / tech-debt consolidation** (Planned #2, #3, #7 — decouple strategy-analytics residue, remove dead `core/data/*` twins, unify the `core/data`↔`core/database/providers` market-data lineage) | **Genuine competing alternative — not dismissed** | This is the one candidate with an unambiguous present-day consumer: the codebase itself. It assumes no future strategy (safest possible bet), is concrete and already scoped in `PROJECT_STATE.md`, and would cleanly close the infrastructure chapter rather than open a forward-looking one. Weighed against the integration contract in §2.2; both are legitimate — the choice is presented to the Technical Lead, not pre-decided. |
| **External strategy integration contract** (the seam between "platform" and the strategies ADR-002 keeps outside it) | **Recommended, not unopposed** | The one forward-looking gap that is architectural rather than operational and does not require writing a strategy. See §2.2 for why this is not the same premature bet as the rejected rows above. |

### 1.4 The discriminating question

The platform has built a complete, audited, deterministic execution stack with **no consumer**.
`SignalSource` is the ADR-002-mandated seam through which any future strategy — built and
validated entirely outside this repository — must enter. Today that seam is a well-documented
abstract class and nothing else: no conformance test suite an external implementer can run
against, no reference/example implementation, no documented path from "I have a `SignalSource`
subclass in my own repo" to "it is running against `fno_runner` in PAPER mode" to "it is trusted
for LIVE." This is the honest next architectural chapter: it closes the loop the execution stack
has been built to serve, without writing the thing ADR-002 keeps out of this repository.

---

## Part 2 — MM11 Proposal: External Strategy Integration & Live-Readiness Contract

### 2.1 Objectives

1. Define and certify the **conformance contract** an external `SignalSource` implementation must
   satisfy before `fno_runner` will drive it — as a runnable test harness, not prose alone.
2. Provide a **reference (non-alpha) `SignalSource` implementation** — proof the seam works
   end-to-end without adding any trading logic to this repository.
3. Document the **validate → promote path**: backtest externally (ADR-002) → conform to the
   harness → run in `ExecutionMode.PAPER` → operational sign-off → `ExecutionMode.LIVE`.
4. Close the **operational gap** between "the code is LIVE-capable" and "it is safe to flip the
   switch": credential/token lifecycle, process supervision/deployment, and a formal go-live
   checklist — as the sibling that makes objectives 1–3 actually usable.

### 2.2 Architectural motivation

**Why this isn't the same premature bet as the rejected rows in §1.3.** Reconciliation and the
`MarginProvider` abstraction were rejected because they have no current consumer and no
present-day exercise path — building them now is pure speculation about a future that isn't here.
The integration contract is open to the identical objection at first glance: there is no strategy
today either. The honest distinction is not "it has a consumer now" — it doesn't — it's two
narrower claims: (1) it is exercisable **today**, in `ExecutionMode.PAPER`, with the reference
(non-alpha) implementation, with no funded account and no live strategy required — unlike
reconciliation, which cannot be exercised at all without a live broker margin call; and (2) it sits
on the critical path to the platform's stated purpose (running an externally-built strategy
through this platform, per ADR-002), whereas reconciliation is a downstream safety refinement that
only matters once live capital is actually flowing through a strategy that exists. If this
distinction does not hold up under scrutiny, the consolidation alternative in §1.3 is the correct
fallback — it requires no such argument, since its consumer (the codebase) is unambiguous today.

- **ADR-002 compliance, both directions.** The platform must stay usable with zero strategies
  (already true) *and* must not grow strategy logic inward to compensate for having none. A
  conformance harness and reference implementation are platform-owned scaffolding *about* the seam
  — they contain no alpha, satisfying both directions of the separation.
- **ADR-MM7E-1's deferred obligation.** That ADR explicitly named "the strategy slice" as the
  future owner of production `SignalSource` construction. MM11 is not that slice — it does not
  write a strategy — but it is the missing scaffolding that makes the eventual strategy slice
  tractable and reviewable instead of ad hoc.
- **Runner Is Neutral / Audit-First.** A conformance harness is how "the driver never branches on
  source type" (DRIVER_SPECIFICATION.md §5.3) and "no side effects in `on_bar`" (§5.4) become
  *checked* invariants for any future implementer, not just documented ones.
- **Closes the loop the execution stack was built for.** MM7–MM10 built (in order) the driver,
  the reconciliation gate, the instrument/broker mapping, and the margin engine — all consumed by
  a `SignalSource` that has never existed. Without this milestone, that investment has no path to
  being exercised by anything real.

### 2.3 Scope

- A `SignalSourceConformanceSuite` (design, not necessarily final name) — a test harness, runnable
  against any `SignalSource` subclass, asserting: no `on_bar` side effects on platform state, no
  held handle to ledger/broker/`ExecutionHandler`, correct `List[SignalEvent]` return shape and
  ordering, `on_start`/`on_stop` lifecycle correctness, and non-reentrancy.
- A minimal **reference `SignalSource`** (e.g., a discretionary/queue-backed or deliberately inert
  "do nothing" source) — demonstrates the contract, ships as documentation/example, not alpha.
  Candidate location: `docs/` example + a `tests/`-adjacent conformance fixture, not `core/strategies/`.
- A documented **promotion path**: what "backtested externally," "PAPER-validated," and
  "LIVE-approved" each concretely require, and who/what signs off at each gate.
- **Operational co-component**: credential/token lifecycle (Upstox OAuth expiry has no automated
  refresh today — repeatedly the reason a live capture has been blocked per `PROJECT_STATE.md`),
  a documented deployment/process-supervision approach (no Dockerfile/systemd exists today), and
  the alerting loop's completeness (the `Alerter`/Telegram path is already wired to the kill-switch
  — this scope item is verification/documentation, not new build).
- A formal **go-live checklist** document that separates the *architectural* deliverables above
  from the *operational, non-code* prerequisite that has nothing to do with this milestone: a
  funded account and a first authenticated position capture.

### 2.4 Out of scope

- Any actual trading strategy, indicator, or alpha logic (ADR-002).
- Broker margin reconciliation build-out (ADR-013 — deferred pending a production strategy and a
  funded LIVE account).
- A `MarginProvider` or multi-broker abstraction (ADR-013, `MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md`
  Q5 — premature with one broker integrated).
- Any change to `LoopDriver`, `ExecutionHandler`, margin, or instrument/broker mapping — all are
  complete or feature-frozen; MM11 is additive scaffolding only.

### 2.5 Dependencies

- ADR-002 (Platform/Strategy Separation) — defines what MM11 may and may not contain.
- ADR-006 / ADR-MM7E-1 (sole orchestrator; composition root injects, does not construct, a source)
  — defines the seam MM11 certifies.
- ADR-013 (Two Margin Authorities) — confirms margin work is closed and out of MM11's scope.
- `docs/DRIVER_SPECIFICATION.md` §5 — the existing prose contract MM11's harness makes executable.

### 2.6 Risks

- **Scope creep toward writing a strategy.** The reference implementation must stay deliberately
  inert/non-alpha; any temptation to make it "a little useful" is the same trap ADR-MM7E-1's
  Design-A alternative already rejected once.
- **Premature generalization.** Do not build a plugin registry or multi-strategy loader speculatively
  (mirrors the rejected `MarginProvider` reasoning) — one reference implementation is enough until
  a second, real external strategy exists.
- **Conflating "ready" with "funded."** The go-live checklist must explicitly name the funded-account
  precondition as external to this milestone, so MM11 is not perceived as blocked on money.
- **Credential-lifecycle scope underestimation.** Upstox token refresh has caused live-capture
  delays before; if the automated-refresh design proves nontrivial, it should be scoped as its own
  slice rather than stretching MM11's timeline.

### 2.7 Implementation roadmap (design-level; no code authored under this proposal)

1. **MM11.1** — Design the `SignalSource` conformance suite: enumerate every DRIVER_SPECIFICATION.md
   §5.4 invariant as a checkable assertion; decide harness shape (pytest fixtures vs. standalone
   script an external repo can import).
2. **MM11.2** — Design the reference `SignalSource` and its promotion-path documentation (backtest
   externally → conform → PAPER → sign-off → LIVE).
3. **MM11.3** — Design credential/token lifecycle handling and the deployment/process-supervision
   approach (co-component; may be scoped as its own sub-milestone if nontrivial).
4. **MM11.4** — Draft the formal go-live checklist, explicitly separating architectural completion
   from the funded-account operational prerequisite.

Each of the above is a design/spec deliverable, consistent with "architecture proposal only, no
implementation code," per this document's scope.

---

## Part 3 — Reassessment (2026-07-01, second pass): Consolidation vs. Integration Contract

**Trigger:** the Technical Lead challenged the Part 2 recommendation directly, naming Platform
Consolidation / Infrastructure Freeze as a competing Candidate B and asking for an objective
re-evaluation, not a defense of the original call.

### 3.1 Verification performed before re-deciding

Two facts were checked directly rather than assumed, because the whole reassessment turns on them:

- **`core/runtime/signal_source.py` has exactly one commit in its entire history** (`git log
  --follow`) — the file that defines the `SignalSource` ABC has never been modified since it was
  introduced. The integration contract is not "about to be published as new" — it has been public
  and completely stable since ADR-002/ADR-006 (predates MM7). No consolidation work has touched it,
  needed to touch it, or is likely to.
- **The consolidation candidates (Planned #2, #3, #7) share no file surface with the integration
  contract's deliverables.** #2 touches `core/analytics/capture.py` / `metrics_service` / DB
  schema; #3 removes dead, zero-importer `core/data/*` modules; #7 unifies the
  `core/data`↔`core/database/providers` market-data lineage. None of these touch
  `core/runtime/signal_source.py`, `core/runtime/driver.py`, or `scripts/fno_runner.py` — the
  surface a `SignalSource` conformance harness and reference implementation would be built against.

**This settles Q1 as false, not merely debatable.** "Consolidate first to stabilize the contract
and avoid future breaking changes to it" cannot be true when the contract has never changed and
the planned consolidation work doesn't touch it. Candidate B is not a technical *prerequisite* for
Candidate A. Anyone tempted to justify Candidate B on churn-avoidance grounds is using a premise
this repository's own history disproves.

### 3.2 Answers to the five questions

1. **Is publishing the contract creating a long-term public API, and does that require
   consolidating first?** The API already exists and is already long-term-stable (§3.1) — nothing
   new is being "published" by building a harness around it. No, consolidation is not required
   first on churn-avoidance grounds.
2. **Who is the present consumer of the integration contract? Immediate need, or a future
   problem?** Honestly, no present consumer — this is the same weakness the Part 2 proposal always
   had, and it should not be understated. It is future-facing, on the platform's stated purpose
   (ADR-002: serving an external strategy), but "future-facing" all the same.
3. **Does Consolidation have a stronger present-day justification because its consumer is the
   codebase itself?** Yes, unambiguously. This is the strongest, most objective point in favor of
   Candidate B, and it should not be minimized: it is the only candidate with a consumer that
   exists *today*, needing no future event to materialize.
4. **Would an "Infrastructure v1.0 Complete" milestone give a cleaner boundary before exposing
   extension points?** Mostly ceremony — but one sub-point is substantive, not ceremonial:
   `README.md` currently describes this repository as a "Market Data Repository" (not the trading
   platform CLAUDE.md describes) and `PROJECT_REVIEW_SUMMARY.md` is dated 2026-03-04 and describes
   a prior, different multi-strategy monolith (its top finding — committed credentials in
   `config/credentials.json` — is already resolved; the file is `.gitignore`d and untracked today,
   confirming the document is simply stale, not that the finding is still live). Publishing an
   external-facing contract on top of docs that describe a different platform is a genuine
   sequencing problem. The doc-audit slice of consolidation should precede anything external-facing;
   the code-residue slices (#2/#3/#7) do not need to, per §3.1.
5. **Is the proposed MM11→MM14 roadmap architecturally superior?** It is a defensible, reasonable
   sequence, but not for the reason its own framing implies. It is **not** superior because
   Candidate B is a dependency of Candidate A — §3.1 shows it is not. It is superior (or at least
   equally valid) on **prioritization** grounds: deferred technical debt (#2/#3/#7 have sat in
   `docs/PROJECT_STATE.md` "Planned" since MM7–MM8, repeatedly deprioritized) tends to compound,
   while deferring the integration contract loses nothing — the `SignalSource` ABC stays frozen and
   PAPER validation is exactly as achievable at MM12 as at MM11.

### 3.3 The cost of choosing Consolidation, named explicitly

Choosing Candidate B for MM11 defers the **first end-to-end proof** that the MM7–MM10 execution
stack actually drives a `SignalSource` through the real composition root (`fno_runner.py`) in a
running process, rather than through unit/integration test doubles only. That is Candidate A's one
genuinely strong argument — real risk reduction that consolidation work does not provide — and it
is not addressed by any of the five questions above. It does not change the verdict below (the
stack is already heavily unit- and integration-tested; a thin, non-alpha reference source running
in PAPER is marginal incremental de-risking, not a large unknown), but it is named here so the
choice is made with eyes open, not by omission.

### 3.4 Final decision

**Candidate B — Platform Consolidation / Infrastructure Freeze — is MM11.** Candidate A — External
Strategy Integration Contract — becomes **MM12**, unchanged in content from Part 2 of this
document (conformance harness, reference implementation, promotion-path documentation, operational
co-component), simply resequenced one milestone later.

This is decided on **prioritization**, not dependency: §3.1 shows Candidate B is not a technical
prerequisite for Candidate A, and any reasoning that treats it as one is factually wrong for this
repository. It is decided because (a) Candidate B's consumer (the codebase and its documentation)
is real and present today, unlike Candidate A's; (b) technical debt deferred since MM7–MM8 has a
demonstrated tendency to keep being deprioritized in favor of the next forward-looking milestone,
and this reassessment declines to repeat that pattern a third time; (c) the external-facing-docs
problem (§3.2 Q4) is a genuine, if narrow, reason not to publish an integration contract on top of
a README that describes a different platform; and (d) Candidate A loses nothing by waiting one
milestone — the contract it depends on has never changed and shows no sign of needing to.

**Revised roadmap:**

```
MM10  Risk & Margin — COMPLETE (ADR-011/012/013)
  |
MM11  Platform Consolidation
        - decouple strategy-analytics residue (Planned #2)
        - remove dead core/data/* twins (Planned #3)
        - unify core/data <-> core/database/providers (Planned #7)
        - stale top-level docs rewrite (README.md, PROJECT_REVIEW_SUMMARY.md)
  |
      Platform v1.0 Complete
  |
MM12  External Strategy Integration Contract
        - SignalSource conformance harness
        - reference (non-alpha) implementation
        - backtest -> PAPER -> LIVE promotion path documentation
  |
MM13  First External Strategy Validation (PAPER)
  |
MM14  LIVE Readiness
        - credential/token lifecycle automation
        - deployment / process-supervision architecture
        - broker margin reconciliation (ADR-013's deferred item)
        - operational validation / go-live checklist
```

MM12–MM14 remain proposals at this point, sequenced but not detailed beyond what Part 2 of this
document already specifies for the (former) MM11 content; MM14 additionally folds in the
broker-reconciliation item ADR-013 deferred, since by MM14 a production strategy and LIVE
readiness are both in scope for the first time.

---

*Ref: docs/ARCHITECTURE_DECISIONS.md (ADR-002, ADR-006, ADR-MM7E-1, ADR-013, ADR-014);
docs/PROJECT_STATE.md; docs/DRIVER_SPECIFICATION.md §5; core/runtime/signal_source.py;
CLAUDE.md (Production Strategy Status); README.md; PROJECT_REVIEW_SUMMARY.md.*
