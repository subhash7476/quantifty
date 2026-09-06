# MM.7C — SignalSource Characterization Report

**Type:** Characterization net. **No production code, no strategy, no SignalSource implementation, no entry script, no adapter.** Tests + report only.
**Date:** 2026-06-11
**Basis:** `MM7B_SIGNALSOURCE_REVIEW.md` (findings C1–C3 + §6 test plan) · `MM7A_CHARACTERIZATION_REPORT.md` · `core/runtime/signal_source.py` · `core/execution/handler.py` · `core/events.py`.
**Starting state:** 463 passing · 0 failing · no production SignalSource/strategy.
**Ending state:** **484 passing · 0 failing** · no production SignalSource/strategy (this is the seam's consumer-contract net, not an implementation).

Pins the `SignalSource → process_signal` consumer contract and the seam boundaries before MM7D writes any strategy — the G1 / MM7A characterize-before-change discipline applied to signal origination.

---

## 1. Tests added (+21, all green)

| File | Tests | Maps to | What it pins |
|---|---|---|---|
| `tests/execution/test_signalsource_consumer_contract.py` | 7 | C1 | risk-field requirement, signal_id derivation, sizing hint+cap+default |
| `tests/execution/test_signalsource_exit_boundary.py` | 3 | C2 | EXIT resolved handler-side, flat→no-op, EXIT bypasses risk fields |
| `tests/runtime/test_signalsource_no_ledger_access.py` | 4 | C3 | seam signatures + module imports expose no ledger/broker/handler |
| `tests/runtime/test_signalsource_determinism.py` | 2 | C4 | identical inputs → identical signals; bar-time keyed, no wall-clock |
| `tests/runtime/test_signalsource_multileg_ordering.py` | 2 | C5 | multi-leg list order preserved; driver does not re-rank |
| `tests/runtime/test_signalsource_lifecycle.py` | 3 | C6 | on_start/on_bar/on_stop, clock-before-on_bar, empty-list no-op |

Validation (this session): `pytest tests/runtime -q` → 278 · `pytest tests/execution -q` → 74 · `pytest -q` → **484 passed, 0 failing.** Net **463 → 484**, no production code touched.

C1/C2 drive a **real** `ExecutionHandler` over an isolated tmp `PaperBroker` + `ExecutionStore` (the G1-characterization construction; an isolation guard confirms `data/execution.db` is untouched). C3–C6 use the `SignalSource` ABC + `LoopDriver` + the shared runtime doubles.

---

## 2. Seam contract pinned

**C1 — `SignalEvent` → `process_signal` consumer contract** (`handler.py:432-615, 819-824`):
- **Risk fields:** a non-EXIT signal needs `metadata['sl_distance']` + `['risk_r']`; when absent the handler **back-fills conservative defaults into `signal.metadata`** (mutating it) and warns. Pinned: with fields → clean order; without → the keys appear in metadata after the call. A real source must supply *real* values, not lean on the default.
- **`signal_id`:** auto-derives as `sha256(f"{symbol}_{strategy_id}_{timestamp.isoformat()}")` when omitted (pinned by recomputing the hash and finding it in `_seen_signals`). A source may set its own, but need not.
- **Sizing (refines MM7B):** the source **may** pass `metadata['quantity']` as a hint; the handler **caps** it at `config.max_position_size` and **falls back** to `default_quantity·(0.5 + confidence·0.5)` when no hint is given. Pinned all three (hint honored = 50; over-hint capped 5000→1000; no-hint default →100). **Sizing authority stays with the handler (ADR-005)** — the source hints, the handler bounds.

**C2 — EXIT resolution boundary** (`handler.py:461, 586-591`):
- An EXIT `SignalEvent` names only the symbol; the handler resolves side + **full quantity from its own position tracker**. Pinned: open long 50 → bare EXIT (no quantity/side in metadata) → order `SELL 50`.
- EXIT on a flat book → `None` (no-op).
- EXIT **bypasses** the non-EXIT risk-field requirement → a bare EXIT still closes.

**C3 — no ledger access** (`signal_source.py` / §5.4):
- `on_bar(self, bar)` and `on_start(self, context)` are the only injection points — no ledger/broker/handler parameter (pinned by signature inspection).
- The seam module **imports/binds none** of `ExecutionHandler`/`BrokerAdapter`/`PositionTracker`/`OrderTracker`/`ReconciliationEngine`/`LoopDriver` (the class docstring names `ExecutionHandler` only in prose to explain the prohibition — what matters is nothing is *bound*).
- The driver passes **nothing** to `on_start` (`context is None`) — pinned via a real run.

**C5 — multi-leg ordering:** a 4-leg structure returned in one `on_bar` is routed to `process_signal` in **exact list order**; the driver does not re-rank by side/type.

**C6 — lifecycle:** `on_start` fires once before any bar (`bars_at_start == 0`); `on_bar` once per bar; `on_stop` once on shutdown; the clock is advanced to `bar.timestamp` **before** `on_bar` (pinned by a clock-observing source); an empty-list return routes nothing while the loop advances.

---

## 3. Shadow-state findings

The C2 + C3 pins together resolve the MM7B "stateful options-selling vs dumb-source" tension into a concrete rule MM7D must follow:

- **The seam gives a source no way to read positions** (C3): no handler/ledger parameter, nothing bound in the module, `on_start` context is `None`. A source **cannot** consult broker truth — by construction, not by convention.
- **The handler closes EXITs from its own ledger** (C2): the source need not know position quantity/side to exit — it emits a bare `EXIT` for the symbol and the handler resolves the close.

**Therefore the strategy splits its knowledge:**
- *Ledger-blind* — it never reads positions, cash, or fills.
- *Intent-stateful* — it may remember **its own emitted intent** ("opened a short straddle on symbol S at premium P at 13:00") to decide *when* to exit (profit-target / stop / delta / time). Time-only exits (15:15) need no state at all.

This keeps the strategy "dumb" about the *platform ledger* while permitting the *self-tracking* a premium-selling strategy needs, with no architecture principle bent (ADR-001/005/006 intact). **The shadow-state store is source-owned and is the central object MM7D designs.**

---

## 4. Replay/live determinism findings

- **Decision logic is deterministic and bar-time-keyed** (C4): identical `(bar, timestamp)` sequences through two independent drivers produce identical routed signal streams, and each emitted signal carries `bar.timestamp` (not a wall-clock-of-the-day). `current_price` is always `bar.close` (ADR-003). So the *source* is paper/live identical by construction — `DriverConfig.Mode` (LIVE/REPLAY) and the handler's `ExecutionMode` (PAPER/LIVE) sit outside it.
- **The one parity obligation is the OPTION CHAIN, not the seam** (MM7B C3, restated): a real options strategy reads strikes/IV/greeks from its **own** `OptionsProvider`, which is *not* the driver's `bar`. Live it fetches from Upstox V3; in replay it must read **recorded** chains of the **same shape**, keyed by `bar.timestamp`. If the chain feed is not made replay-symmetric, paper/live diverge at the **data layer** even though the decision logic (C4) is identical. This is a data-provider requirement (Planned #7), and MM7D must inject a chain source that honors it — **not** call a live API directly inside `on_bar`.

---

## 5. Implementation constraints for MM7D

The strategy MM7D builds as a `SignalSource` must, per the pinned contract:

1. **Emit valid non-EXIT signals:** set `metadata['sl_distance']` and `['risk_r']` to *real* values (do not rely on the handler's warn-default). (C1)
2. **Not size, only hint:** optionally pass `metadata['quantity']`; never assume it is honored unbounded — the handler caps it. Lot/contract sizing intent goes in the hint; the bound is execution's. (C1)
3. **Emit bare EXITs:** for exits, return an `EXIT` signal for the symbol with no quantity/side; let the handler close from its ledger. (C2)
4. **Hold no ledger/broker/handler:** read positions never; track only **its own emitted intent** (shadow state) for stateful exit timing. (C3 + §3)
5. **Be a pure function of bar + chain + timestamp:** no wall-clock in the decision path; read decision time from `bar.timestamp`. (C4)
6. **Inject a replay-symmetric chain source:** take an `OptionsProvider` at construction that returns identical shapes live and in replay, keyed by `bar.timestamp`; do not call a live API inside `on_bar`. (C4 §4)
7. **Return legs in execution order:** the returned list order is the routing order — sequence multi-leg structures deliberately (e.g. shorts before long wings). (C5)
8. **Use the lifecycle hooks:** warmup/subscription in `on_start` (no ledger handle in the context), teardown in `on_stop`; `on_bar` must be side-effect-free w.r.t. platform state. (C6)

---

## 6. Position in the critical path

```
MM7B SignalSource Review            ✅ origin mapped (greenfield)
MM7C SignalSource Characterization  ✅ (this) consumer contract + boundary + determinism pinned
   ↓
MM7D SignalSource Implementation    ← port the first strategy against this green net
   ↓
MM7E Entry Script Wiring → MM7F Broker Positions Adapter → MM7G W3 Refusal
   ↓
F4 Verification → F3 Disposition → Product/Margin → 4C.7
```

MM7D now has a pinned target: the `process_signal` consumer contract (C1/C2), the no-ledger boundary that forces shadow state (C3), the determinism/chain-parity rules (C4), leg ordering (C5), and the lifecycle (C6). It builds a strategy against *known* behavior rather than guessing — exactly how G1 sequenced characterize → implement → close.

**No production code, strategy, SignalSource, entry script, or adapter was created by this report.**

---

*Filed under the G1 / MM7A / MM7B review-first, characterize-before-change discipline.*
