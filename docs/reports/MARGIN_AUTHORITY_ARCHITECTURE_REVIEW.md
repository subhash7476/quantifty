# Margin Authority Model — Architecture Decision Review

**Date:** 2026-07-01
**Type:** Architecture review (no code, no implementation spec)
**Trigger:** Upstox `/charges/margin` order-margin API evidence + a proposed revised product
objective and validation-policy model for the margin subsystem.
**Predecessor:** `docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md` (MM10.5-scoped — Risk 1
component-count question only). This document is broader: it addresses the platform-level
question of what role the broker margin API should play, which the predecessor doc touched but
did not fully resolve.
**Related:** ADR-011 (`docs/architecture_decisions.md`), `docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md` §8 Risk 1.
**2026-07-01 update:** this review's statements that "MM10.5 remains blocked" (§1, Q2, §4) are
point-in-time and now superseded — MM10.5 was subsequently **retired** the same day (ADR-012),
not merely unblocked. The two-authorities verdict (§2) and the Q4/Q5 premature-abstraction
findings are unaffected by this and stand as written.

---

## 1. Summary verdict

The revised product objective is correct and should be adopted. The two-track philosophy
(local engine for research/backtest, broker for live) is correct in spirit but the word
"authoritative" is overloaded in the proposal and needs to be split before it becomes an ADR.
Two of the six questions (product objective, new ADR) can be accepted close to as-written. Two
(configurable validation policy, MarginProvider abstraction) are premature relative to what
exists today and should be scoped down. MM10.5 itself is unaffected by any of this — it remains
blocked on the same factual question it was already blocked on before this evidence arrived.

---

## 2. The core distinction the proposal needs: two authorities, not one

"The broker becomes authoritative for live" is true for exactly one thing: **order acceptance**.
It is not — and structurally cannot be — authoritative for **margin sizing/computation**,
because sizing has to run identically whether or not a broker session exists.

Split it explicitly:

| Authority | Owns | Why | Changed by this evidence? |
|---|---|---|---|
| **Computation / sizing authority** | "What margin will this position consume, as a decomposable formula?" | `NseMarginEngine` — used for pre-trade sizing gates, backtest, research, and diagnostics | No — ADR-011 stands |
| **Order-acceptance authority** | "Will the exchange/broker actually accept this order at this margin?" | The broker RMS, trivially, because it is the gateway | This is what the Upstox evidence is actually evidence *of* |

The reason this split matters: without it, "broker is authoritative for LIVE" reads as "swap
the calculator for the broker call in LIVE," which is the exact thing two platform principles
already forbid, independent of anything in this new evidence:

- **Runner is Neutral** (CLAUDE.md Principle 4) — the LoopDriver treats live and backtest data
  identically. A backtest has no broker session. If sizing depended on `/charges/margin`, live
  and backtest would run on structurally different margin logic.
- **Audit-First** (Principle 5) — every trade must be explainable by exact analytical facts. A
  broker's total is an opaque number; `NseMarginEngine`'s `span - credit + elm (+ em)` is a
  formula. Sizing must stay on the side that can be audited.

With the split, the proposal's own "Compare → Reconciliation" box is exactly right: reconciliation
is only meaningful when there are two distinct things being compared, not when one has replaced
the other.

---

## 3. Answers to the six questions

### Q1 / Q3 — Revised product objective: "deterministic implementation of public NSE rules," not "exact broker clone"

**Agree, adopt as-written.** This is a positioning correction, not an architecture change — it
doesn't touch any frozen component or existing formula. It's also the only objective that was
ever actually achievable: retail has no access to broker RMS internals or a historical SPAN
archive, so "reproduce broker margin exactly" was never a claim the local engine could honestly
make. Restating the objective as "best deterministic implementation of publicly available NSE
Clearing rules" makes the existing `NseMarginEngine` design *more* correct relative to its stated
goal, not less — nothing to redesign.

One correction to the framing: don't state the objective as "local engine for research, broker
for live" without the Section 2 split. The local engine is not *demoted* to research-only — it
remains the live sizing engine (ADR-011). What changes is only that the *broker's* authority is
now explicitly scoped to order acceptance, not to sizing.

### Q2 — Should MM10.5 proceed as planned, or does the roadmap change?

**No change to the roadmap.** MM10.5 was already blocked before this evidence arrived, on
exactly the question this evidence bears on: is "Exposure Margin" a third component additive to
SPAN + ELM, or the same regulatory charge as ELM under a different name (`MM10_5_IMPLEMENTATION_SPECIFICATION.md`
§8 Risk 1). The Upstox evidence sharpens that risk (all sampled responses reconcile to
`span_margin + exposure_margin` with zero residual, and Upstox's own field docs tie
`exposure_margin` to "ELM percentage values") but doesn't close it, because `/charges/margin` is
a pre-trade blocked-margin endpoint and could simply be silent about an end-of-day ELM charge
(`MM10_5_ARCHITECTURE_REASSESSMENT.md` §2–3). The discriminator is still: pull one itemized
NIFTY futures margin breakdown from a primary source (Zerodha/Samco SPAN calculator, or the raw
NSCCL circular text) and count the non-SPAN line items. Two → collapse MM10.4/MM10.5. Three →
proceed with rate verification. This is a research step, not a redesign — nothing in today's
proposal changes it or jumps ahead of it.

### Q4 — Configurable Margin Validation Policy (OFF / WARN / STRICT)

**Directionally sound, but premature to build now — and the tri-state framing needs a correction
before it's adopted.** OFF is not really a policy choice in backtest/research mode; it's the only
physically possible state, because there is no broker session to query. So the three states
aren't symmetric alternatives selected per-environment — they're really "no comparison is
possible" (research/backtest) vs. "a comparison is possible and you choose how much it matters"
(paper/live: WARN vs. STRICT). Worth keeping the three labels for operator clarity, but don't
model OFF as a live-mode-selectable option; it should be structurally forced whenever no broker
positions/margin source is injected — mirroring how `require_reconciliation_on_start` already
works today (branches by source presence, not by mode; see `PROJECT_STATE.md` LoopDriver Phase F).

More importantly: this policy has nothing to govern yet. There is no broker margin fetch, no
comparison logic, and no reconciliation-layer scaffolding in the repository today. Building a
configurable policy enum ahead of the mechanism it configures is exactly the kind of
speculative-flexibility CLAUDE.md's "no over-engineering" convention warns against — a
config surface with no consumer is dead weight until the consumer exists. Recommendation: don't
build this now. Scope it as part of the same milestone that builds the broker margin
reconciliation call (see Q5), not before it.

### Q5 — MarginProvider abstraction (Upstox → future Zerodha/Dhan)

**Push back on this one.** There is exactly one broker integrated in this repository (Upstox).
A `MarginProvider` hierarchy anticipating Zerodha and Dhan implementations is a premature
abstraction for a one-broker system — CLAUDE.md is explicit: "don't design for hypothetical
future requirements," and a multi-broker interface is a hypothetical until a second broker is
actually being integrated.

There's also a structural collision worth naming: the codebase already has a `MarginCalculator`
Protocol (`core/risk/margin_calculator.py`, frozen MM10.1) that `NseMarginEngine` implements.
Introducing a *second*, differently-named seam (`MarginProvider`) for "the broker as another
kind of margin source" invites exactly the ambiguity ADR-011 was written to prevent (it exists
because two plausible readings of "which component is the production calculator" were possible
without an explicit decision). Don't create a second protocol family that raises the same kind
of question again.

If/when a live-broker margin check is actually built (the reconciliation layer this document's
Section 2 anticipates), the right shape is a single, concrete, narrow function or thin class —
`fetch_upstox_order_margin(...)` — called from the reconciliation layer, not a provider
interface. Generalize to a `MarginProvider` abstraction only when a second broker integration is
real and concrete, at which point the two implementations tell you what the interface actually
needs to look like. Building it now means guessing that shape from zero real second
implementations.

### Q6 — New ADR

**Yes, and it should reconcile with ADR-011, not sit beside it as a second story.** ADR-011
already establishes `NseMarginEngine` as the production `MarginCalculator` for LIVE F&O and
states plainly that this is unaffected by broker API considerations
(`PROJECT_STATE.md` Blocked section, 2026-07-01 entry). A new ADR should not restate or duplicate
that — it should add the piece ADR-011 doesn't cover: the broker's role as order-acceptance
authority and (future) reconciliation input. Recommended ADR content:

1. **Context** — Upstox `/charges/margin` returns a full component breakdown, prompting the
   question of whether the broker should replace or supplement the local engine.
2. **Decision** — two distinct authorities, per Section 2 of this document: `NseMarginEngine`
   remains sole sizing/computation authority (research, backtest, and LIVE pre-trade gating,
   unchanged from ADR-011); the broker is authoritative only for actual order acceptance at the
   gateway. The two are reconciled, not merged.
3. **Consequences** — no change to `ExecutionHandler` construction or `MarginCalculator`
   injection; the reconciliation/comparison layer (if built) is additive and LIVE-only, consumes
   `NseMarginEngine` output and a broker margin fetch as two independent inputs, and never
   replaces either with the other. A validation-policy config (Q4) belongs to that future
   milestone, not to this ADR.
4. **Explicitly out of scope** — a `MarginProvider` abstraction (Q5) is not adopted; it is
   deferred until a second broker integration is real.

---

## 4. Roadmap impact

**None to MM10.5's blocked status.** The blocker is still the factual Risk 1 discriminator, not
an architectural question — no code in this document's scope (validation policy, provider
abstraction) sits ahead of it in the queue, and nothing here changes what unblocks it.

**One new, explicitly-not-yet-scoped candidate milestone** for the future: a LIVE-only
pre-trade margin reconciliation layer (`NseMarginEngine` output vs. `/charges/margin` response,
logged or gating per the eventual WARN/STRICT policy). This is additive, not a replacement for
existing work, and should only be scoped once there's a concrete reason to build it (e.g. live
trading is actually about to go live and needs the safety net) — building it speculatively now
would be the same premature-abstraction problem as Q5.

---

## 5. Documentation updates

- **This document** records the review; cross-referenced from `MM10_5_ARCHITECTURE_REASSESSMENT.md`.
- **ADR-011** — no change needed to its content; a new ADR (Q6) should reference it rather than
  restate it.
- **`PROJECT_STATE.md`** — add a pointer to this review under the MM10.5-blocked entry so future
  sessions don't re-litigate the "should the broker replace the engine" question from scratch.
- **New ADR** — recommended per Q6 above, once the user confirms the two-authorities framing.

---

*Ref: docs/reports/MM10_5_ARCHITECTURE_REASSESSMENT.md; docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md §8 Risk 1; docs/architecture_decisions.md ADR-011; CLAUDE.md Architecture Principles 1, 4, 5 and Development Conventions ("no over-engineering").*
