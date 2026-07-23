# Carry → Implementation Bridge (Design)

**Status:** DRAFT design. **Research is CLOSED** — Carry is a validated alpha across TRAIN /
HOLDOUT / SEALED (`CARRY_SEALED_REPORT.md`), construction frozen and hash-locked
(`CARRY_V2_PRE_REGISTRATION.md`, SHA `74c7311c…`). This document maps the validated signal onto
the production architecture and defines the go-live gate. **It authorizes implementation design
only — not live capital.** No research is reopened here; the signal, sign, construction, and fee
model are settled and immutable.

---

## 0. What is settled vs. what this covers

**Settled (frozen):** the signal (residual cross-sectional carry, **+sign**), the construction
(top-minus-bottom quintile, equal-weight, beta + sector neutralized, ADV-capped at 10% of
20-day ADV, monthly on the roll, 0.25σ no-trade band), the era-accurate futures fee model, and
the validation.

**This document:** how that signal becomes a **deterministic, auditable production strategy**
under the platform's architecture, and the sequenced gate that stands between a validated
backtest and real capital. The load-bearing risk is **not** the signal — it is whether the
*production code path* faithfully reproduces the *research harness* that validated it (§5).

---

## 1. Architectural placement — the four principles

Carry must obey the platform constitution (`CLAUDE.md`): strategies stay dumb, analytics
produce facts, execution owns reality, the runner is neutral, everything is auditable.

| Concern | Layer | Why |
|---|---|---|
| Residual-carry z, neutralized z, **quintile membership**, eligibility | **Analytics (facts)** | Cross-sectional ranking is a pre-computed fact, not runtime logic — "Analytics Produce Facts, runtime read-only." |
| On formation date: emit long/short/exit **intents** per name | **Strategy (dumb)** | Reads facts, emits `SignalEvent` only — no sizing, no margin, no broker. |
| Equal-weight construction, ADV caps, no-trade band, sizing, risk limits, orders | **Execution (owns reality)** | Sizing/risk/broker live exclusively in `core/execution/`; `NseMarginEngine` is the sole sizing authority. **No neutralization here** — it is already in the `z_carry_neut` fact (§2). |
| Drive formation dates + fills, identically in backtest and live | **Runner (neutral)** | `LoopDriver` treats live and backtest data identically — the basis of the §5 parity guarantee. |

The key placement decision: **the quintile ranking is analytics, not strategy.** The strategy
does not rank — it reads which quintile each name is in and emits accordingly. **Neutralization
is also analytics** — the per-name cross-sectional beta+sector OLS is computed once, in the fact
layer, producing `z_carry_neut`. Execution does **weighting, caps, and sizing only, and never
re-neutralizes.** This keeps the strategy dumb and reproduces the validated construction exactly.

---

## 2. Analytics layer — Carry as a fact table

An offline, scheduled batch job computes per `(date, symbol)`: `resid_carry_z`,
`carry_z_neutralized`, `quintile`, `eligible` (F&O-listed, ADV floor, DTE). Written to DuckDB;
runtime is read-only.

**Critical: promote the *frozen research code*, do not reimplement it.** The validated signal
came from `scripts/signal_engine/carry/`. The analytics job must run **that same construction
code**, wrapped as a scheduled producer — a reimplementation is a new, unvalidated construction
and silently breaks the edge. Same code → same facts → same edge.

---

## 3. Strategy layer — the dumb emitter

`core/strategies/carry_strategy.py` (the strategy layer is greenfield today — this is its first
inhabitant):

- On each **monthly formation date**, read the carry fact table and emit:
  `SignalEvent(symbol, direction=LONG)` for top-quintile names, `direction=SHORT` for
  bottom-quintile, and exit events for names leaving the book.
- Between formation dates: emit nothing; positions are held.
- **No sizing, no neutralization, no margin, no broker contact.** The strategy communicates
  *intent and rank only*.

**Contract check (first implementation task):** the existing `core/runtime/` signal-source
contract and `docs/DRIVER_SPECIFICATION.md` are likely shaped for **per-symbol streaming**
signals. Carry is a **cross-sectional, monthly, portfolio-formation** event. Confirm the
`SignalEvent`/SignalSource contract can carry a formation-date batch of intents; if it is
strictly per-bar/per-symbol, design a formation-date batch signal *before* writing the strategy.
This impedance mismatch is the first thing to resolve, not discover.

---

## 4. Execution layer — faithful reproduction of the validated book

`core/execution/`:

- **Portfolio constructor** turns per-name intents into the *validated* book **directly from the
  pre-neutralized `z_carry_neut` fact**: quintile assignment, equal-weight within legs, ADV cap
  (κ = 10% of 20-day ADV), 0.25σ no-trade band. **It does NOT re-neutralize** — the frozen
  research harness does per-name cross-sectional OLS once and builds straight from `z_carry_neut`
  with no book-level re-neutralization. Adding one is a new, unvalidated construction that
  breaks parity (§5) and the no-re-optimization guardrail (§8). Gross/leverage is a parity-neutral
  scaling set by the risk layer. The constructor must reproduce the research book **exactly**.
- **Sizing:** `NseMarginEngine` (`core/risk/nse_margin_engine.py`) is the **sole sizing
  authority** in paper and live alike — margin-aware, deterministic. The broker RMS is
  order-acceptance only, never consulted for sizing (ADR-011/012/013).
- **Risk:** position-stacking guard (block new entry while a position is open on the same
  symbol), gross/net exposure limits, per-name caps.
- **Broker:** `PaperBroker` first, then Upstox LIVE — same execution code, broker swapped.
- **Position tracker must update on fills** (`FillEvent → position_tracker.update_from_fill()`).
  This is a documented pitfall: without it, equity = cash only, drawdown is wrong, and TP/SL/
  time stops never fire.

### 4.1 Rebalance execution path (resolved) — book-level batch, not per-symbol streaming

A monthly portfolio rebalance is **inherently atomic and book-level**: the 0.25σ no-trade band
is a *scale* of existing positions (not exit-reentry), the margin budget is *shared across all
names*, and gross/neutrality normalization is a *whole-book* constraint. The per-symbol
`process_signal` path (one symbol at a time) plus its stacking guard (`handler.py:634`) is the
**wrong contract** for this.

**Decision: Carry rebalances through a formation-date, book-level batch operation in the
execution layer, invoked by the runner on formation dates — NOT through `process_signal`.** The
per-symbol handler and its stacking guard are **left untouched** (they still serve per-name
streaming strategies; Carry simply does not route through them).

Why not the alternatives:
- **Per-symbol streaming (constructor → `process_signal`)** requires *bypassing* the stacking
  guard **and** redesigning the margin-budget gate (`handler.py:1140`) — more handler surgery,
  it weakens the guard for the strategies that legitimately need it, and it still cannot
  naturally allocate a *shared* margin budget one symbol at a time. "Faithful to the per-bar
  contract" is a false virtue: the per-bar contract is the wrong shape for a monthly book.
- **Full exit-then-reentry** ignores the 0.25σ band and churns the whole book monthly →
  turnover roughly doubles vs. the research (1.44/yr) → net spread drops → **fails the parity
  gate (§5)**. Disqualified on parity alone.

**This is the MOST parity-faithful option, not a departure.** The research harness (`run_sealed.py`)
*is* a book-level monthly diff with a no-trade band; the batch path mirrors that computation, so
it is the likeliest to reproduce the research net spread. And it does **not** violate "Runner is
Neutral" — neutrality means live == backtest, which the batch path preserves by running
identical code in both modes. What is given up is only "reuse `process_signal` / zero handler
diffs," a lesser convention, in exchange for the correct home for a portfolio rebalance under
"Execution Owns Reality."

The batch operation (all in `core/execution/`, deterministic): read target book from the Carry
facts → read current holdings → per name compute target − held, suppress if `|Δ| < 0.25σ`
(no-trade band) → size the surviving deltas to the **shared** margin budget via `NseMarginEngine`
→ emit delta orders (scale / open / close) → `position_tracker` updates on fills. The **strategy
stays dumb** (emits target intents from facts); **execution owns the rebalance.**

---

## 5. The PARITY GATE — the single most important implementation risk

**The validated numbers came from the standalone research harness (`run_sealed.py`), not from
the production `LoopDriver` + strategy + `NseMarginEngine` + `PaperBroker` path.** These are
different code. Before anything else:

> Run the **production path** through `LoopDriver` in **backtest mode** over TRAIN + HOLDOUT +
> SEALED, and confirm it **reproduces the research harness's net quintile spread** within a
> tight, pre-stated tolerance (same sign, magnitude within a few percent per window).

If the production path does not reproduce the research edge, the implementation is **unfaithful
and the edge is not real in production** — no amount of downstream work fixes that. This is a
**hard gate**: pass it before capacity, drawdown, or paper trading. It is also the direct
expression of "Runner is Neutral / deterministic reproducibility" — same code, backtest and
live, byte-identical logic.

### 5.1 Canonical fee model (resolved) — one implementation, era-accurate tiered STT

Three fee conventions existed in the pipeline: `run_sealed.py`'s inline **tiered** STT
(0.0100 → 0.0125 → 0.0200, which produced the validated SEALED +20.52%), `run_net_spread.py`'s
flat **0.0100%** (TRAIN/HOLDOUT), and `futures_fees.py`'s **0.0125% pre-2024-10**. These are not
three legitimate choices — the **tiered schedule is canonical**: it is what `CARRY_PHASE0_PRE_REGISTRATION.md`
§8 pre-registered and what produced every validated number.

Key fact: the flat 0.0100% and the tiered model are **identical over TRAIN/HOLDOUT**
(both windows precede the 2023-04 STT change, where the tiered rate *is* 0.0100%), so the
+13%/+7% nets already sit on the canonical model. The only real divergence is
`futures_fees.py`, which is simply **wrong** — it omits the pre-2023-04 0.0100% tier and
overcharges that era (and the Jan–Mar 2023 slice inside SEALED).

**Resolution (single source of truth):**
1. **Correct `core/execution/futures/futures_fees.py`** to the full three-tier schedule
   (0.0100% ≤ 2023-03-31 · 0.0125% 2023-04-01 → 2024-09-30 · 0.0200% ≥ 2024-10-01, sell-side).
   This becomes the one fee model for research **and** production; retire the inline models.
2. **Preserve SEALED by proven equivalence, NOT by re-read.** Unit-test the corrected
   `futures_fees.py` against `run_sealed.py`'s inline tiered model on shared inputs → identical
   per-contract fees. If byte-identical, the SEALED +20.52% transfers **by construction** — the
   one-shot SEALED window is **not** re-read (SEALED protocol §2 holds).
3. **Re-derive TRAIN/HOLDOUT** on the corrected module (free, no sealed data) → must reproduce
   +13%/+7% (STT is identical in that era).
4. **Parity tolerance (§5) must NOT absorb any fee discrepancy.** The fee code is *shared and
   identical*, not reconciled by tolerance. Tolerance is reserved for genuine execution-path
   differences (float ordering, fill timing). Using it to mask a fee-model gap would pollute the
   gate that exists to catch real divergence.

### 5.2 The parity gate and the SEALED one-shot rule

The parity gate must **not** become a backdoor re-run of the SEALED window — the same discipline
that governed the fee decision (§5.1) governs here.

- **Establish parity on TRAIN + HOLDOUT**, where re-running the production path is unrestricted
  and free. That is where divergences are found and fixed.
- **SEALED parity is guaranteed *by construction*.** If the production path reproduces research
  on TRAIN + HOLDOUT (identical construction, rebalance logic, and — per §5.1 — an identical fee
  module), then it necessarily reproduces the recorded SEALED series. No fresh SEALED read is
  required to know this.
- **If a production run over SEALED is performed at all**, it is a **verification against the
  frozen `CARRY_SEALED_SNAPSHOT.json`** (an already-recorded result), makes **no new inferential
  use** of the window, and changes no construction/fee/sign. It is therefore not a "read" in the
  sense of the one-shot rule (SEALED protocol §2) — but it must be logged and framed explicitly
  as such, never as a new evaluation.

**Isolate construction from margin-sizing in the harness.** The research book used a fixed gross
(≈ ₹50 lakh/leg); production sizes via `NseMarginEngine`. Pin the *parity* harness to the
research-identical gross + injected 5 bp/side slippage, so any residual gap is **pure
construction divergence**, not a margin-model difference. Real margin sizing is validated later
in **PAPER** (§6.4), not conflated into the parity gate.

**De-risk the biggest new surface first.** Before building the daily-bar provider + full
LoopDriver replay (the largest net-new plumbing), run a cheap, deterministic **rebalancer-only
construction-parity sub-check**: feed the rebalancer the research facts and confirm it produces
the research book's target weights and deltas. If construction parity fails there, it is fixed
before any provider work.

---

## 6. Go-live gate (sequenced — no step skipped before real capital)

1. **Parity gate (§5).** Production path reproduces the research net spread. *Hard gate.*
2. **Capacity analysis.** Max AUM before the ADV caps bind and the edge compresses — set by the
   thin-name tail of the ~120-name book. Output: a capital ceiling.
3. **Drawdown / regime profile.** Worst month, max DD, and how concentrated the SEALED **+20.5%**
   is — it is likely regime-flattered (carry-favorable 2023–26), so size on the conservative
   HOLDOUT-class net, not 20.5%. Optionally evaluate the **Trend −0.246 overlay** for
   drawdown reduction here (a risk study on TRAIN/HOLDOUT — consumes no sealed data).
4. **PAPER mode.** Run live-paper via `scripts/fno_runner.py` (PAPER) for a defined period;
   validate realized slippage against the 5 bp/side assumption (slippage dominated costs — it
   is the production lever) and confirm fills + position tracking behave.
5. **LIVE.** Only after 1–4, at small size, with **IC-decay monitoring** — a validated signal is
   not a permanent one; carry edges crowd out.

---

## 7. Audit & determinism (non-negotiable)

- **Audit-first:** every order traceable to the exact carry fact `(date, symbol, z, quintile)`
  that produced it.
- **Deterministic:** same inputs → byte-identical orders, in backtest and live. This is the
  guarantee the parity gate (§5) verifies and the reason no construction parameter may drift.

---

## 8. Guardrails (explicit non-goals)

- **No re-optimization of the construction for live.** It would break both the validated edge
  and the determinism guarantee. The frozen construction is the product.
- **No broker-RMS-driven sizing.** `NseMarginEngine` is the sole authority.
- **Size on the conservative net, not the regime-flattered SEALED +20.5%.**
- **No reopening research / adding sleeves to "improve" before this is live.** The job is now
  implementation and risk, not discovery.

---

## 9. Key files (to be created)

| File | Purpose |
|---|---|
| `scripts/signal_engine/carry/publish_facts.py` | Promote frozen construction → scheduled analytics fact table |
| `core/strategies/carry_strategy.py` | Dumb formation-date `SignalEvent` emitter |
| `core/execution/portfolio/carry_constructor.py` | Book-level neutralization + equal-weight + caps |
| `scripts/signal_engine/carry/parity_check.py` | §5 production-vs-research parity harness |
| `tests/strategies/test_carry_strategy.py` | Strategy emits correct intents from facts |
| `docs/reports/CARRY_PARITY_REPORT.md` | Script-generated parity result (the §5 gate) |

---

## 10. Next step

**Resolve §3's contract check, then build §2 (fact promotion) + §3 (dumb strategy) + §5 (parity
gate) first.** The parity gate is the cheapest, highest-information step: if the production path
cannot reproduce the research edge, capacity/drawdown/paper work is premature. Everything after
§5 is conditional on §5 passing.
