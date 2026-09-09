# Carry Production-Metrics Plan — Architect / Audit Review

**Reviewer role:** auditor + technical architect (DeepSeek implements, Claude reviews).
**Artifact under review:** DeepSeek's "Carry PAPER Production Run" plan (4 phases, 8 new
files + 2 modifications).
**Verdict:** **NO-GO as written.** Revise to a 2-phase build; defer all live/forward
infrastructure. Reasoning below, severity-ranked.

---

## Verdict summary

| # | Finding | Severity | Blocks build? |
|---|---|---|---|
| C1 | Phase 2 re-runs the strategy over SEALED ("verification only") — violates the frozen one-shot protocol | **CRITICAL** | Yes |
| C2 | Plan's load-bearing premise — "path proven end-to-end by `replay_parity_check.py` at +0.0 bp" — is false | **CRITICAL** | Yes |
| H1 | Instrumentation via `_execute_deltas` subclass trusts the blended `fill.fee`; no fee/slippage decomposition (misses a real bug) | **HIGH** | Yes (design) |
| H2 | Phase 3 (live forward-run infra) is premature scope, contradicts explicit repo guardrails (YAGNI, LIVE-policy deferral) | **HIGH** | Yes (scope) |
| M1 | Determinism claimed for the full LoopDriver+hook path, which is only 3-date smoke-tested | MEDIUM | No |
| — | Metrics DB schema, provider reuse, report sections, audit-hash instinct | GOOD | — |

**Bottom line:** the *intent* (persist + report the metrics the frozen strategy produces) is
right and worth building. The *plan* mis-scopes it, rests on a false parity premise, and its
Phase 2/Phase 3 as written would breach a frozen protocol and build unfunded live
infrastructure. It goes ahead only after the revision in the last section.

---

## C1 — Re-running SEALED violates the one-shot protocol (CRITICAL)

DeepSeek Phase 2: *"Runs over TRAIN (56), HOLDOUT (23), and SEALED (42 — verification only,
compared against `CARRY_SEALED_SNAPSHOT.json`)."*

`CARRY_SEALED_READ_PROTOCOL.md` §2 (FROZEN 2026-07-23, SHA `459411ab…`):
> "The SEALED read is run **exactly once.** No re-run, no second look, no parameter change
> after seeing it — **for any reason.**"

A "verification re-run compared against the snapshot" *is* a second traversal of the sealed
window. "For any reason" forecloses the verification framing explicitly. The existing harness
already encodes this guardrail in code — `parity_check.py:13-14`:
> "SEALED parity is guaranteed by construction (identical code = identical output) — do NOT
> re-run SEALED."

The operator has independently ruled this out (decision: **snapshot-ingest only**). SEALED
metrics must be **ingested** from the frozen `CARRY_SEALED_SNAPSHOT.json`, never regenerated.
This is not a style preference; it is the integrity guarantee the whole windowing discipline
exists to protect.

## C2 — The plan's parity premise is false (CRITICAL)

DeepSeek states the production path is *"proven end-to-end by `replay_parity_check.py`
(TRAIN + HOLDOUT at +0.0 bp delta)."* Two errors:

1. There is no `replay_parity_check.py`. The file is `scripts/signal_engine/carry/parity_check.py`.
2. **It does not run the end-to-end path.** Its docstring claims "provider → LoopDriver REPLAY
   → strategy → rebalancer → PaperBroker → tracker," but `_simulate_production`
   (`parity_check.py:91`) is a **standalone re-simulation**: it reads facts directly, calls
   `compute_target_book`, and reimplements the band/fee loop inline (`:167-214`). It never
   instantiates LoopDriver, the provider, or PaperBroker.

What is actually proven at +0.0 bp is that the **construction functions**
(`compute_target_book`/`compute_deltas`) reproduce research net spread. The genuine
LoopDriver + `DailyBhavcopyProvider` + `CarryRebalancerHook` path is validated only at **3
formation dates** (`carry_integration_check.py`, `CARRY_INTEGRATION_SMOKE_REPORT.md`).

**Consequence for the build:** DeepSeek Phase 2 drives the *hook* through LoopDriver over full
windows and treats the resulting per-formation metrics as trustworthy. But the full path has
never been shown to reproduce `parity_check.py`'s numbers at scale. This is precisely the
"single most important implementation risk" flagged in `CARRY_IMPLEMENTATION_BRIDGE.md` §5.
The build must **prove the full LoopDriver+hook path matches `parity_check.py` on TRAIN+HOLDOUT
before** any metric it emits is reported as fact.

## H1 — Instrumentation design trusts a buggy blended fee field (HIGH)

DeepSeek: *"`InstrumentedCarryRebalancerHook` subclasses `CarryRebalancerHook` and writes to
the DB in `_execute_deltas`."* Two problems:

1. **Fragile duplication.** `_execute_deltas` owns the exit/entry fill placement. To capture
   per-fill data an override must either re-implement that logic or intercept fills — both
   couple the metrics layer to execution internals.
2. **It would certify a bug.** Fills are built with `FillEvent.fee = futures_fees.total +
   slippage` (blended into one field). Any "fee breakdown by component" DeepSeek derives from
   `fill.fee` is wrong, and the per-rebalance log it would inherit **double-counts slippage and
   undercounts FLIP slippage** (used `target_cap` only, missing the exit leg). DeepSeek's plan
   did not identify this.

The correct seam is a **metrics sink that recomputes fees + slippage from each `Delta`**,
independent of `fill.fee` — mirroring what `parity_check.py:190-214` already does. *(This has
since been built and merged as `summarize_rebalance` / `RebalanceMetrics`, TDD, 38 carry tests
green; the sink hook is the small remaining piece. The reviewer notes this because it changes
what DeepSeek should be prompted to build — instrument via the sink, do not override
`_execute_deltas`.)*

## H2 — Phase 3 live-forward infrastructure is premature (HIGH)

DeepSeek Phase 3 proposes symbol resolution, a facts-refresh scheduler, a live provider, and a
live runner — a large surface that contradicts explicit, written repo guardrails:

- `carry_rebalancer.py:81` — `live_gross_exposure_policy` **raises `NotImplementedError` by
  design**: "a PnL-reactive sizing rule is new behavior never present in TRAIN/HOLDOUT/parity,
  and designing it is its own pre-registered decision" (bridge §8 no-re-optimization guardrail).
- `CLAUDE.md` — "no production strategy, no funded LIVE account exists yet"; "do not build …
  ahead of a concrete need."
- Development conventions — KISS / YAGNI / "no over-engineering… for one-time use."

The **facts-refresh scheduler** is a genuine known gap (`CARRY_PAPER_INTEGRATION_REVIEW.md`
§3), but it serves *forward paper* runs and is cleanly separable. Live provider/runner and a
PnL-reactive gross policy must not be built now. Defer the entire live track to a separate,
explicitly-authorized pre-registration.

## M1 — Determinism asserted, not established (MEDIUM)

The audit-hash instinct is correct and aligns with the platform's Audit-First principle. But
"re-runs over same data produce identical hashes" is asserted for the full LoopDriver+hook
path, whose replay determinism over ~120 names × 10y has not been demonstrated (only
construction parity has). Keep the hash; treat byte-identical replay as a **test to run**, not
a property to assume — it is the strongest guarantee available here and doubles as the C2 check.

## What the plan gets right (keep)

- The metrics DB table decomposition (`run_metadata` / `rebalance_summary` /
  `rebalance_positions` / `equity_curve`) is sensible and maps to real needs.
- Reusing `DailyBhavcopyProvider` + LoopDriver REPLAY for TRAIN+HOLDOUT is the correct stack.
- The report section list is comprehensive and mostly on-target.
- Determinism-hash and full audit-trail-to-fact instincts match Principle 5 (Audit-First).

---

## Required revision before build (the GO conditions)

Restructure to two phases; the live track is out of scope.

**Phase A — instrument + historical metrics.**
1. Metrics DB schema + writer (`carry_metrics_db.py`), TDD.
2. Instrument the hook via an **optional `metrics_sink`** that recomputes from `Delta`
   (`summarize_rebalance`) — **do not** subclass-override `_execute_deltas` or trust `fill.fee`.
   Default off, keeps existing tests green.
3. **Parity precondition (discharges C2):** run the full LoopDriver+hook path over TRAIN+HOLDOUT
   and show its net series matches `parity_check.py` within the same 15 bp tolerance the parity
   gate uses. If it does not, stop and trace before reporting any metric.
4. **SEALED = snapshot-ingest only (discharges C1):** ingest `CARRY_SEALED_SNAPSHOT.json` as a
   marked row; never run the strategy over SEALED.

**Phase B — report generator** reading `production.duckdb` → `CARRY_PRODUCTION_METRICS_REPORT.md`
(returns vs research snapshot, fee decomposition, turnover, HHI/top-3 concentration, drawdown,
determinism hash).

**Deferred (separate authorization):** facts-refresh scheduler; symbol resolver; live provider;
live runner; any LIVE gross-exposure policy.

**Recommendation:** DeepSeek may proceed **only** against a revised prompt encoding Phase A/B
and the four Phase A conditions. The plan as written should not be built.
