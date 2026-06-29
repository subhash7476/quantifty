# MM9 — Final Architecture Certification

**Program:** MM9 — Margin Enforcement (Constitution Principle 4: *no trade without margin validation*)
**Status:** **MM9.1–MM9.4 COMPLETE** (one in-program slice, MM9.2-S3, intentionally deferred — see §5)
**Certification date:** 2026-06-28
**Author:** Claude (Opus 4.8), for independent review
**Scope of certification:** Architecture, abstractions, and code-as-built. **Not** an operational go-live sign-off for LIVE F&O (see §9 Readiness and §8 Risks).
**Test baseline:** 802 tests collected (up from the 569-test pre-MM9 baseline). The full suite was *collected* and confirmed green at slice boundaries during implementation; this certification did **not** re-run the full suite end-to-end — see §9.4.

**Primary sources audited:**
`docs/reports/MM9_IMPLEMENTATION_PLAN.md` · `docs/reports/MM9_4_S4_IMPLEMENTATION_SPEC.md` · `docs/architecture_decisions.md` (ADR-007) · as-built code in `core/risk/`, `core/execution/`, `core/runtime/`, `scripts/`.

---

## 1. Executive Summary

MM9 closed a constitutional gap: the platform had a margin calculator (`MarginTracker`) that was constructed inside `ExecutionHandler` but **never consulted in the execution decision path**. Every signal that passed `RiskManager.evaluate` proceeded unconditionally to broker submission regardless of portfolio margin. Constitution Principle 4 ("Margin validation required before order submission") was violated by every live order.

MM9 delivered a four-milestone ladder that:

1. **MM9.1** — installed a gating pre-trade margin check (`_check_margin_budget`) in `process_signal`, correctly placed between `RiskManager.evaluate` and `order_tracker.add_order`.
2. **MM9.2** — made the gate portfolio-accurate: per-symbol price cache, lot-size-correct option exposure, and realized-equity tracking through the fill path.
3. **MM9.3** — wired portfolio Greek exposure limits, integrated `PortfolioView` into runtime telemetry, and corrected the drawdown gate to mark-to-market portfolio equity.
4. **MM9.4** — introduced the `MarginCalculator` protocol (ADR-007), built the SPAN data foundation and the first concrete `SpanMarginCalculator`, and swapped it in at the F&O composition root behind the protocol seam — making SPAN the active margin engine for LIVE F&O while leaving the flat-rate path byte-identical for equity/backtest/paper and as a zero-deploy rollback.

The result is a **layered, deterministic, replay-safe margin enforcement stack** built behind a clean protocol seam, with the strangler swap concentrated at a single construction site so that no consumer and no existing test changed when SPAN was introduced.

**Two caveats that gate go-live (both verified against as-built code, not the spec):**

1. **SPAN data sourcing is unvalidated.** The NSE download URL template and CSV schema constants are explicitly flagged "for implementation-time confirmation against the actual exchange file format" and have never been run against a real NSE SPAN file. `data/span/` does not exist. MM9.4 certifies the *seam and computation*, not a *proven production data feed*.

2. **Absent/corrupt SPAN silently falls back to flat-rate margin — it does NOT refuse.** The MM9.4-S4 *spec* called for a composition-time `raise ValueError` when the SPAN archive is empty for an F&O universe. The *as-built* `scripts/fno_runner.py:155-170` instead wraps `span_repo.load()` in `try/except Exception`, logs a WARNING, and proceeds with `MarginTracker` (flat 20%). Because no readiness checker is then injected, the driver's `_check_span_readiness` guard (`driver.py:454-457`) is a no-op. **Net effect: a LIVE F&O run with missing or corrupt SPAN data proceeds on flat-rate margin with only a warning, rather than refusing to start.** Only a *loaded-but-stale* snapshot triggers a driver BLOCK→STOPPED (`driver.py:465-481`). This diverges from the spec and from the "refuse > warn > fallback" principle the program otherwise upholds, and is the single most important correctness gap to close before LIVE F&O (see §7, §8, §9.3).

---

## 2. Before vs After Architecture

### 2.1 Before MM9

```
SignalEvent
   ↓
process_signal
   ├─ kill switch / daily limit / drawdown / stacking guard
   ├─ _check_risk_limits
   ├─ RiskManager.evaluate(order)            → approve
   ├─ order_tracker.add_order(order)         ← registers order
   └─ broker.place_order(order)              ← SUBMITS, unconditionally

MarginTracker: constructed at handler.py, exposed in PortfolioView,
               NEVER called in the decision path.
_check_greek_limits: present but no live caller (dead path).
cash_balance: static = initial_capital for the whole session.
```

Margin, portfolio Greeks, and realized equity were all computed-or-computable but **non-gating**. Constitution Principle 4 unmet.

### 2.2 After MM9

```
SignalEvent
   ↓
process_signal
   ├─ kill switch / daily limit / drawdown(MTM equity) / stacking guard
   ├─ _check_risk_limits(signal)             (handler.py:638)
   ├─ _check_greek_limits(signal)            → D4 reject on portfolio Δ/Γ/V breach (EXIT bypass)  (handler.py:645, pre-order)
   ├─ [order construction]
   ├─ RiskManager.evaluate(order)            → approve  (handler.py:747)
   ├─ _check_margin_budget(order, price)     → D4 reject on utilisation breach (EXIT bypass)  ← MM9 GATE  (handler.py:810)
   ├─ order_tracker.add_order(order)         (handler.py:823)
   └─ broker.place_order(order)

Margin engine (behind MarginCalculator protocol):
   • LIVE F&O      → SpanMarginCalculator (scenario risk %, frozen SpanSnapshot)
   • equity/paper/backtest → MarginTracker (flat 20%) — also the rollback target

Startup gates (driver):
   recovery → master-readiness → SPAN-readiness(NEW) → canonicalize → reconcile → start
   (SPAN gate active only when LIVE ∧ has_derivatives ∧ snapshot present)

cash_balance: updated through the fill path (realized PnL); drawdown uses PortfolioView MTM equity.
Telemetry: PortfolioView.snapshot() carries margin, gross exposure, portfolio Greeks, MTM equity, per-symbol pnl_pct.
```

### 2.3 The behavioural delta an operator observes

| Observable | Equity / backtest / paper | LIVE F&O (after MM9.4) |
|---|---|---|
| `margin_tracker` concrete class | `MarginTracker` (unchanged) | `SpanMarginCalculator` |
| Used-margin source | flat `Σ notional · 0.20` | SPAN `Σ notional · max(scan_risk, short_opt_min)` |
| Required-margin source | `notional · 0.20` | SPAN `get_incremental_margin(...)` |
| Utilisation formula / threshold | unchanged | unchanged (only term *sources* moved) |
| Startup gates | unchanged | + SPAN readiness, but **stale-only**: absent/corrupt ⇒ warn + flat-rate fallback; stale (loaded-but-old) ⇒ refuse |
| Telemetry keys | unchanged | unchanged (values SPAN-sourced when a snapshot loaded) |
| Rollback | n/a | remove/withhold the SPAN snapshot from `data/span/` ⇒ handler falls back to `MarginTracker` (no named flag; no deploy) |

---

## 3. New Abstractions Introduced

| Abstraction | Location | Role | ADR |
|---|---|---|---|
| **`MarginCalculator` protocol (v1)** | `core/risk/margin_calculator.py` | Structural seam for margin computation; consumers (`ExecutionHandler`, `PortfolioView`) typed to the abstraction, not the concrete tracker. Lives in `core/risk/` (margin is a risk concern, not execution). | ADR-007 |
| **`SpanMarginCalculator`** | `core/risk/span/span_calculator.py` | First concrete `MarginCalculator`. Per-position SPAN margin = `notional · max(scan_risk, short_option_minimum)`; exposes off-protocol `get_incremental_margin()`. Stateless w.r.t. portfolio; zero runtime I/O. | ADR-007 |
| **SPAN data foundation** | `core/risk/span/` — `span_snapshot.py`, `span_parser.py` (versioned registry), `span_repository.py`, `span_readiness.py`, `span_freshness.py`, `span_pipeline.py` | Immutable `SpanSnapshot` DTO + parse/load/freshness/readiness machinery; offline-only acquisition. | ADR-007 |
| **`PriceSnapshot` value type + per-symbol price cache** | `core/execution/handler.py` (MM9.2-S1/S3-S1) | Portfolio-wide price cache so the gate prices *all* open positions, not just the signalled symbol. | — |
| **`_check_margin_budget` gate** | `core/execution/handler.py` | Capital-utilisation admission check; `(approved, utilisation)` contract; EXIT bypass; D4 reject (not kill switch). | — |
| **Portfolio Greek aggregation** | `core/risk/greeks/portfolio_greeks.py` + `_check_greek_limits` | Portfolio Δ/Γ/V summed across open positions; bool-returning D4 rejection gate. | — |
| **`_check_span_readiness` driver gate** | `core/runtime/driver.py:444-483` | Startup freshness gate mirroring `_check_master_readiness`; BLOCK → abort_startup → STOPPED. **No-op when no readiness checker was injected** (i.e. when no snapshot loaded). | — |
| **SPAN composition wiring** | `scripts/fno_runner.py:153-170, 206-207, 235` | Derivatives branch constructs `SpanRepository`, loads the expected-date snapshot, builds the readiness checker, and injects `span_snapshot=` into the handler + `span_readiness=` into the driver. | — |
| **`fetch_span_params.py`** | `scripts/` | Sole network component for SPAN acquisition; runtime never downloads. | ADR-007 (no broker/IO at margin time) |

> **Correction vs spec:** The MM9.4-S4 spec proposed a single named rollback switch `SPAN_MARGIN_ENABLED`. **No such constant exists in the as-built code** (verified by repo-wide grep). Rollback is implicit: whether a snapshot is present in `data/span/` for the expected date. This certification does not claim the named switch.

---

## 4. Architectural Principles Validated

| Principle | How MM9 honoured it |
|---|---|
| **Constitution Principle 4 — margin validation before submission** | Now a gating check on every non-EXIT signal. The binding definition adopted (D1): *an approximation that gates is constitutionally superior to an accurate calculation that never gates.* |
| **ADR-001 — Ledger Is Truth** | Both `MarginTracker` and `SpanMarginCalculator` read `PositionTracker` on demand and cache nothing. The swap kept a *single* calculator instance behind both `PortfolioView`s and the gate — no second source of margin truth. |
| **ADR-003 — Deterministic Processing** | The calculator does zero runtime I/O/clock access; the `SpanSnapshot` is frozen for the session and journaled by date+hash; replay reconstructs identical gate decisions bit-for-bit. |
| **ADR-006 — Sole Orchestrator** | No new runtime path. The swap is construction-time; the gate kept its single call site; the driver gained exactly one readiness call inside the existing startup sequence. |
| **ADR-007 — MarginCalculator is the SPAN seam** | The entire SPAN substitution happened behind the protocol; the protocol stayed v1; the calculator exposes no admission policy (handler still decides); no broker API at margin time. |
| **Execution Owns Reality** | Margin, sizing, and risk remained exclusively in `core/execution/` + `core/risk/`. `RiskManager` stayed stateless (D5) — it never grew a `margin_tracker`/`cash_balance` parameter. |
| **Refuse > warn > fallback (ADR-MM7F-1)** | **Partially honoured — with one as-built violation.** Runtime lookup faults on a loaded snapshot → D4 reject of that order (correct). A *loaded-but-stale* snapshot → driver BLOCK → STOPPED (correct). **But absent/corrupt SPAN → warn + silent flat-rate fallback**, not refusal (`fno_runner.py:165-170`). This is a genuine deviation from the principle and from the S4 spec; it is the primary fix for MM9.5 (§7 #1, §8). |
| **YAGNI / strangler migration** | The protocol was deliberately *not* introduced until a second implementation existed (MM9.4). The swap defaulted to the incumbent and injected the replacement only at the F&O root — zero consumer change, zero test churn on the incumbent path. |

---

## 5. Remaining Technical Debt (in-program, accepted)

| Item | Status | Disposition |
|---|---|---|
| **MM9.2-S3 — per-underlying notional cap** | **NOT implemented** (only in-program slice left undone) | Deferred. The capital-utilisation gate provides portfolio-level protection; a per-underlying concentration cap is a secondary control, not a constitutional requirement. Tracked in `MM9_IMPLEMENTATION_PLAN.md §9`. |
| **`process_group_signal` bypasses all gates** | Pre-existing gap, not introduced by MM9 | The group-order path does not pass through `_check_margin_budget` (or Greek/risk gates). Out of MM9 scope; needs a dedicated milestone. |
| **PnLTracker recovery gap (I.L.2)** | Pre-existing, orthogonal | Recovery does not rebuild PnLTracker state; unrelated to margin but still open. |
| **Greek limits use TTE=0.0 / IV=0.20 defaults** | Accepted approximation (MM9.3-S1) | True per-position implied volatility deferred to MM9.5; the gate is conservative-by-construction in the interim. |
| **`get_incremental_margin` reached via `hasattr` capability detection** | Deliberate (MM9.4-S4, Design Q2) | Keeps the protocol v1 frozen, but the off-protocol method is reached by duck-typing. Acceptable now; formalising it as protocol v2 is MM9.5 work (see §6). |
| **`self.margin_tracker` attribute name** | Cosmetic debt | Attribute is named `margin_tracker` but is typed `MarginCalculator` and may hold a SPAN calculator. Renaming was explicitly out of scope (touches handler/portfolio_view/fno_runner/tests for no behavioural gain). |

---

## 6. Deferred MM9.5 Work

| Item | Why deferred |
|---|---|
| **Convert absent/corrupt-SPAN fallback into a hard refusal for LIVE F&O** | The as-built `fno_runner.py:165-170` degrades to flat-rate on any snapshot-load failure (§7 #1). LIVE F&O must instead refuse to start — this is the highest-priority MM9.5 fix. |
| **`MarginCalculator` protocol v2** — formalise `get_incremental_margin` on the protocol | v1 was frozen for the S4 swap to avoid breaking `MarginTracker` conformance and to keep the diff minimal. v2 should add the incremental method and retire the `hasattr` capability check. |
| **Inter-contract spread / NOV credits** | SPAN scenario netting across legs of a spread reduces margin; the S3 calculator computes per-position margin without spread offsets — conservative but capital-inefficient for spreads. |
| **Broker-margin reconciliation** | Offline comparison of computed SPAN margin vs the broker's reported margin (diagnostic only — never at execution time, per ADR-007). |
| **True per-position implied volatility for Greeks** | Replace the TTE=0.0/IV=0.20 defaults in `_check_greek_limits`. |
| **Per-order margin reservation ledger** | Track margin reserved per in-flight order, beyond the current point-in-time utilisation estimate. |
| **Assignment-margin modeling** | Margin impact of option assignment. |

---

## 7. Known Limitations

1. **Absent/corrupt SPAN silently falls back to flat-rate (does not refuse).** `fno_runner.py:155-170` catches all snapshot-load failures, warns, and proceeds with `MarginTracker`; the driver gate is then a no-op (no checker injected). A LIVE F&O session with missing or corrupt SPAN data trades on flat-rate 20% margin with only a warning. The spec intended a hard composition-time refusal. **This is the dominant safety limitation** (see §4, §8).
2. **SPAN data sourcing is unvalidated against real NSE files.** The download URL template (`https://www.nseindia.com/span/span_{ddmmyyyy}.zip`) and the CSV schema constants (`NSE_SCHEMA_V1`, `scan_risk`, `short_option_minimum`) are explicitly flagged "for implementation-time confirmation against the actual exchange file format." No production SPAN snapshot has ever been parsed. `data/span/` does not exist (see §8, §9).
3. **SPAN margin model is conservative, not exact.** No spread credits, no NOV offsets; per-position `max(scan_risk, short_option_minimum)` only. It will over-margin spreads relative to true exchange SPAN.
4. **Equity symbols must never reach the SPAN gate.** An equity symbol with no SPAN risk array raises `MissingRiskArray` → D4 reject. The structural protection is *not injecting SPAN for equity universes* (correct by construction at the root), but a mixed universe is a latent footgun.
5. **Greek gate IV/TTE are placeholders** (see §5).
6. **Per-underlying concentration is ungated** (MM9.2-S3 deferred).
7. **`process_group_signal` is ungated** (pre-existing).

---

## 8. Risks

| Risk | Severity | Mitigation / current posture |
|---|---|---|
| **Absent/corrupt SPAN → silent flat-rate fallback** (not a refusal) | **HIGH** (unsafe LIVE F&O) | **No mitigation in code today** — `fno_runner.py:165-170` warns and proceeds on flat 20%. MM9.5 must convert this to a hard refusal for LIVE F&O (raise at composition or inject an always-BLOCK readiness checker so `_check_span_readiness` stops startup). |
| **SPAN data feed never validated** — URL/schema are placeholders; first real NSE file may not parse | **HIGH** (blocks correct LIVE F&O) | Must validate `fetch_span_params.py` + parser against a real NSE file before go-live. Note: because of the fallback above, an unparseable feed currently degrades to flat-rate rather than refusing — see the row above. |
| **SPAN schema drift** — NSE changes its file format | Medium | Versioned parser registry (`UnsupportedSpanSchema` on unknown version) refuses rather than mis-parses. |
| **`hasattr` capability detection is brittle** | Low–Medium | Works today; tightens to a typed protocol method in MM9.5. A future `MarginCalculator` that happens to define `get_incremental_margin` with a different signature would be silently picked up. |
| **Conservative SPAN over-margins spreads** | Low (capital efficiency, not safety) | Acceptable for a first cut; spread credits are explicit MM9.5 scope. |
| **Static-denominator regressions** | Low | `_update_equity_metrics` now wired to the fill path (MM9.2-S4); cash_balance tracks realized PnL. |
| **Mixed equity/F&O universe injecting SPAN** | Low | Root only injects SPAN for derivatives universes; equity reaching the SPAN gate D4-rejects rather than mis-margining. |

---

## 9. Readiness Assessment

### 9.1 Architecture readiness — **CERTIFIED COMPLETE**
The margin enforcement seam, the SPAN computation, the composition swap, the startup readiness gate, the Greek gate, and the telemetry integration are implemented as specified, behind clean ADR-007 boundaries, with the strangler swap concentrated at one construction site. The as-built code (`margin_calculator.py`, `span_calculator.py`, `handler.py:168/203-205/1172-1176`, ADR-007 §295) matches the MM9.4-S4 specification.

### 9.2 Constitutional readiness — **SATISFIED (with the data caveat)**
Principle 4 ("margin validation before submission") is now gating for every non-EXIT signal on every margin-bearing path. Constitution §8 "Margin-aware execution" is architecturally satisfied; its *operational* satisfaction for LIVE F&O depends on §9.3.

### 9.3 Operational readiness (LIVE F&O) — **NOT READY**
SPAN data sourcing is unvalidated, **and** the absent-SPAN path silently falls back to flat-rate margin rather than refusing (§7 #1). The combination is dangerous: a LIVE F&O launch today with no validated SPAN data would *not* be blocked — it would trade on flat 20% margin with only a warning. Before any LIVE F&O run:
- **Convert the absent/corrupt-SPAN fallback into a hard refusal for LIVE F&O** (the dominant fix).
- Validate `fetch_span_params.py` URL/auth against the real NSE endpoint.
- Confirm the NSE SPAN CSV schema and register the correct parser version.
- Fetch, archive, and parse at least one real snapshot; confirm `scan_risk` / `short_option_minimum` keys exist and are sane.
- Run an end-to-end paper F&O session with a real snapshot injected and verify gate numbers against an independent margin reference.

Equity / paper / backtest paths are **fully ready** — they use the unchanged `MarginTracker` and are covered by the regression baseline.

### 9.4 Test readiness — **STRONG, with one honesty note**
802 tests are collected (vs the 569-test pre-MM9 baseline), including dedicated MM9.1–MM9.4 suites and a full SPAN test package (`tests/risk/span/`, `tests/execution/test_mm9_*`). Each slice was driven green at its boundary during implementation. **This certification confirmed test *collection* (802) but did not re-execute the entire suite end-to-end** — an independent reviewer should run `python -m pytest` to confirm the full green bar before relying on it.

---

## 10. Lessons Learned

1. **A gating approximation beats a perfect non-gate.** The MM9.1 decision (D1) to ship a flat-rate single-symbol gate *first* delivered constitutional compliance immediately, then improved accuracy incrementally — rather than blocking enforcement on SPAN.
2. **Defer the abstraction until the second implementation exists.** The `MarginCalculator` protocol was correctly *not* created in MM9.1–MM9.3 (YAGNI); it appeared in MM9.4 exactly when `SpanMarginCalculator` gave it a reason to exist.
3. **Gate placement is load-bearing.** The C2 correction (place the gate *before* `order_tracker.add_order`, not before `broker.place_order`) prevented orphaned-order ledger corruption on rejection — a subtle bug the original MM9.0 design would have shipped.
4. **Strangler-at-the-root yields zero test churn.** Defaulting to the incumbent and injecting the replacement at one construction site meant 569+ existing tests passed unchanged through a margin-engine replacement.
5. **Re-source, don't re-point.** The S4 insight that swapping the *object* alone would leave `M_used` (SPAN per-position fraction) and `M_req` (flat notional) model-inconsistent — forcing the deliberate re-sourcing of the required-margin term — is the kind of correctness trap a naïve DI swap walks into.
6. **Separate per-order rejection from session kill.** Margin breach = D4 reject (next bar may clear); drawdown breach = kill switch. Conflating them would have made transient margin pressure permanently halt sessions.

---

## 11. Recommended Next Milestone

**Recommendation: MM9.5 — "SPAN Production Validation + Protocol v2," gated ahead of any further capability work.**

Priority order:

1. **Close the silent-fallback safety gap (blocking, highest priority).** Make absent/corrupt SPAN a hard refusal for LIVE F&O instead of a flat-rate fallback (§7 #1, §8, §9.3). This is a small, contained fix in `fno_runner.py`/`driver.py` and is the prerequisite for trusting any LIVE F&O run.
2. **SPAN data validation (blocking for LIVE F&O).** Validate `fetch_span_params.py` and the parser against real NSE files; archive and parse a real snapshot; end-to-end paper F&O dry-run. This converts MM9.4 from "architecturally complete" to "operationally live."
3. **`MarginCalculator` protocol v2.** Promote `get_incremental_margin` onto the protocol; retire the `hasattr` capability check (§5, §8).
4. **Spread / NOV credits.** First capital-efficiency improvement to the SPAN model.
5. **Per-position IV for the Greek gate** and **per-underlying concentration cap (MM9.2-S3)** as parallel hardening.

Do **not** begin greenfield strategy-layer work (`core/strategies/`) until SPAN production validation lands — the execution/margin substrate should be operationally proven first, consistent with ADR-005 (Execution Before Alpha).

---

## Appendix A — Milestone Completion Matrix

| Milestone | Slices | Status |
|---|---|---|
| **MM9.1** — capital-utilisation gate | S1 config · S2 estimator · S3 gate+callsite+tests · S4 fno_runner initial_capital | **COMPLETE** |
| **MM9.2** — portfolio-accurate controls | S1 price cache · S2 multiplier fix · **S3 per-underlying cap (DEFERRED)** · S4 equity wiring | **COMPLETE** (S3 deferred) |
| **MM9.3** — exposure controls | S1A Greek semantic · S1B Greek aggregation · S2 PortfolioView runtime · S3 drawdown MTM fix | **COMPLETE** |
| **MM9.4** — SPAN integration | S1 protocol (ADR-007) · S2 SPAN sourcing · S3 SpanMarginCalculator · S4 composition swap + readiness gate | **COMPLETE** (data feed unvalidated) |

## Appendix B — As-Built Anchors (verified)

- `core/risk/margin_calculator.py` — protocol v1 (margin_rate, get_exposure, get_used_margin).
- `core/risk/span/span_calculator.py` — `SpanMarginCalculator` (margin_rate default 1.0; `get_incremental_margin` off-protocol; raises `MissingRiskArray`/`MissingRiskMetric`).
- `core/execution/handler.py:168` — `span_snapshot: Optional[SpanSnapshot] = None`; `:203-205` presence-checked swap; `:1172-1176` capability-detected incremental re-source.
- `scripts/fno_runner.py:153-170` — derivatives-branch SPAN load wrapped in `try/except Exception` → **warn + flat-rate fallback on failure** (not refusal); `:206-207` conditional `span_snapshot` injection; `:235` `span_readiness` passed to the driver.
- `core/runtime/driver.py:158/185/382/444-483` — `span_readiness` param, `_check_span_readiness`; no-op guard when no checker injected; BLOCK→abort_startup→STOPPED only for a loaded-but-stale verdict.
- **`SPAN_MARGIN_ENABLED` — NOT FOUND in the repo** (repo-wide grep). The spec's named rollback switch was not implemented; rollback is implicit (snapshot presence in `data/span/`).
- `docs/architecture_decisions.md:253-297` — ADR-007 (Accepted 2026-06-28), with S3/S4 consequence notes; "The SPAN integration program is complete."
- `scripts/fetch_span_params.py:34-41` — NSE URL template + `data/span` dir, flagged for implementation-time confirmation.
