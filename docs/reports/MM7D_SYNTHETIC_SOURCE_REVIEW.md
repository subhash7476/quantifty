# MM.7D — Synthetic SignalSource Review (Infrastructure Validation Only)

**Type:** Review — design the smallest `SignalSource` that proves the runtime wiring end-to-end. **No production code, no SignalSource implementation, no entry script, no adapter, no provider. Report only.**
**Date:** 2026-06-11
**Purpose:** *Validate infrastructure* — NOT alpha, NOT strategy performance, NOT a trading system.
**Basis (file:line, verified 2026-06-11):** `core/runtime/driver.py` · `core/runtime/signal_source.py` · `core/runtime/config.py` · `core/runtime/instrument_scope.py` · `core/execution/handler.py` · `core/brokers/paper_broker.py` · `core/execution/persistence/execution_store.py` · `core/execution/reconciliation.py` · `core/events.py` · `tests/runtime/_doubles.py` · `tests/scripts/test_fno_entry_wiring.py` · `MM7A`/`MM7B`/`MM7C` reports.
**Starting state:** G1 CLOSED · 484 passing · 0 failing · no production SignalSource/strategy/entry script/OHLCV feed/options chain.

> **Scope guard.** NiftyShield is ABANDONED. This review does not reference, port, migrate, or resurrect NiftyShield, `D:\BOT\root`, or any options-seller alpha. The object designed here carries **no** market data, OHLCV, option chain, strategy logic, broker alpha, greeks, volatility, indicators, or chain provider. It exists solely to make the wired runtime *execute a known order and close it*, so the infrastructure can be observed doing its job.

---

## 0. Verdict (the three answers, up front)

1. **Are bars actually required?** **A bar *object* is structurally mandatory; real market data is not.** The loop only advances the clock, calls `on_bar`, and routes signals *when a provider yields a bar* (`driver.py:574-588`). No bar ⇒ no `on_bar` ⇒ no routing. But the bar can be a trivial flat `OHLCVBar` (only `timestamp` and `close` are read downstream), produced by a synthetic provider with **no OHLCV, no chain, no indicators**. This is already demonstrated by `FakeMarketDataProvider` + `make_bar` (`_doubles.py:27-104`). So the synthetic source still needs a **synthetic bar feed**, but that feed is N flat ticks, not market data.

2. **Minimal SignalSource design:** a deterministic, scripted **two-event** source over an **equity** symbol: `on_bar` call #0 → `[BUY]` (carrying real `sl_distance` + `risk_r`), call #1 → `[EXIT]` (bare), all later calls → `[]`. No state beyond a call counter. This drives the entire spine source → driver → handler → PaperBroker → persistence → position tracking → restore → reconciliation. Canonicalization is a deliberate **equity no-op** in this tier (it is gated on LIVE ∧ derivatives ∧ master, `driver.py:439-444`); a second **single-derivative tier** lights it up.

3. **Recommended next implementation slice:** write the §6 characterization net first, then implement the synthetic source **plus a `tests/`-level integration harness** (NOT a `scripts/` entry script) that wires a *real* `ExecutionHandler` + `PaperBroker` + synthetic provider + synthetic source against an isolated tmp `execution.db`. This proves wiring **without** tripping the MM7A T1 tripwire (`test_fno_entry_wiring.py:90-99`) or falsely claiming a production entry script exists — that remains MM7E.

---

## 1. Minimal source design (Q1)

### 1.1 The shape

```
on_start()                      → no-op (no warmup, no subscription)
on_bar(bar) call #0             → [ SignalEvent(BUY,  sl_distance=…, risk_r=…) ]
on_bar(bar) call #1             → [ SignalEvent(EXIT) ]            # bare
on_bar(bar) call #2..N          → [ ]                              # do-nothing
on_stop()                       → no-op
```

A single integer call-counter is the entire state. It is **ledger-blind** (holds no handler/broker/tracker — MM7C C3) and **intent-stateful only** in the trivial sense that it remembers "I have emitted BUY, so next emit EXIT" — exactly the MM7C §3 shadow-state rule, reduced to its smallest form.

### 1.2 Why BUY-then-EXIT (not BUY alone)

A lone BUY proves intake → order → fill → open position. Adding the EXIT proves the **handler-side EXIT resolution** (MM7C C2): a bare `EXIT` names only the symbol and the handler derives `SELL` + full quantity from its own `position_tracker` (`handler.py:586-591`). EXIT also bypasses the risk-field requirement (`handler.py:461`). This closes the position back to FLAT, so the round-trip is fully observable in persistence (open row → close row) and the position tracker ends clean. Two bars is the minimum to sequence both, because each event must land on a bar the source actually sees (`on_bar` fires once per arriving bar, `driver.py:580-581`).

### 1.3 Why equity, REPLAY-or-LIVE+PAPER

- **Equity symbol** (`NSE_EQ|INE…`) deliberately sidesteps four derivative-only mechanisms so the spine is isolated:
  - the option-contract selector (`handler.py:563-571`) — only taken when `metadata["execution_mode"]=="option"`;
  - `has_derivatives` is False (`instrument_scope.py:19-21`), so the **master-readiness gate** is skipped (`driver.py:383-386`);
  - the **canonicalization pass** is skipped (same gate, `driver.py:439-442`);
  - the **F4 unverified lot (65/30)** never enters — equity carries no contract multiplier (Open Finding F4).
- **`ExecutionMode.PAPER`** on the handler gives the synchronous simulated fill (`handler.py:638-662`) — the broker leg with no network.
- **`Mode.REPLAY`** is the simplest (no watchdog, no LIVE-requires-handler rule). **`Mode.LIVE` + PAPER** is the richer variant: it additionally exercises the startup gate and the LIVE-requires-handler guard (`driver.py:505-506`). Both are valid; see the two tiers in §3.

### 1.4 What it must NOT be

Not a strategy, not an entry script, not a chain reader. It must not import or hold the handler/broker/ledger (statically forbidden by the seam, pinned in MM7C C3 via `tests/runtime/test_signalsource_no_ledger_access.py`). It must not call a live API inside `on_bar`. It computes nothing from the bar — it ignores the bar's prices entirely and emits on **call index**, which is the strongest possible determinism (MM7C C4).

---

## 2. Whether bars are required (Q2)

**Structurally required: a bar object per tick. Not required: real market data.**

Evidence from `driver.py`:

| Step | Line | Consequence if no bar |
|---|---|---|
| `bar = self._provider.get_next_bar(symbol)` | `:574` | `if bar is None: continue` (`:575-576`) — symbol skipped |
| `self._clock.set_time(bar.timestamp)` | `:578` | clock never advances |
| `self._dispatch_signals(self._source.on_bar(bar), bar)` | `:580-581` | **`on_bar` never called; nothing routed** |
| `current_price=bar.close` into `process_signal` | `:627` | no price to fill at |
| `self._bars_processed += 1` | `:585` | loop makes no progress; ends via exhaustion (`:800-808`) |

So the bar is the **clock tick + the price carrier**, and `on_bar` is strictly bar-gated. A push/event source is intentionally absent (`signal_source.py:16-20`, ADR-003). **Therefore a synthetic source cannot drive the runtime on its own — it must be paired with a synthetic bar feed.** That feed is trivial: `OHLCVBar(symbol, timestamp, open=high=low=close=C, volume=0.0)` (`events.py:42-50`; the builder already exists at `_doubles.py:27-31`). Only `timestamp` (clock) and `close` (fill price, P&L, fees) are consumed downstream — `open/high/low/volume` are inert. No OHLCV semantics, no chain, no indicators are needed.

**Bottom line:** *bars (the object + a provider) are mandatory; market data is not.* The minimal feed is N≥2 flat bars on one symbol.

---

## 3. Expected runtime flow (Q3)

### 3.1 Tier A — equity spine (proves everything except canonicalization)

```
SyntheticSource.on_bar #0  → [BUY]
  └─ LoopDriver._dispatch_signals (driver.py:590-631)  → routes in list order
       └─ ExecutionHandler.process_signal(BUY, bar.close)  (handler.py:432)
            ├─ signal_id derived (sha256) if absent          (handler.py:444-449)
            ├─ idempotency lock                               (handler.py:452-455)
            ├─ risk fields read (sl_distance/risk_r)          (handler.py:457-482)
            ├─ instrument = InstrumentParser.parse (equity)   (handler.py:583)
            ├─ quantity = _calculate_position_size            (handler.py:594)
            ├─ NormalizedOrder built                          (handler.py:606-615)
            ├─ order_tracker.add_order(order)  → ORDERS row   (handler.py:629 → execution.db)
            └─ broker.place_order(order)  (PaperBroker)        (handler.py:633; paper_broker.py:26)
                 └─ synth FillEvent → _handle_broker_fill      (handler.py:644-657)
                      ├─ order_tracker.process_fill → FILLS row        (handler.py:325)
                      ├─ position_tracker.update_from_fill → POSITION   (handler.py:326)
                      │     (equity → canonicalize_symbol returns None → left legacy, handler.py:338-341)
                      ├─ pnl_tracker.update                              (handler.py:342)
                      └─ trading_writer.save_trade → DuckDB trades/ctx  (handler.py:387)
SyntheticSource.on_bar #1  → [EXIT]
  └─ process_signal(EXIT, bar.close)
       ├─ current_position.side != FLAT → SELL full qty       (handler.py:586-591)
       └─ fill → _handle_broker_fill → position FLAT, update_trade_exit (handler.py:377)

— restart —
ExecutionHandler #2 (load_db_state=True, same execution.db)
  └─ _replay_state (handler.py:219-…)
       ├─ order_repo.get_all → re-add orders, restore _seen_signals (handler.py:224-228)
       └─ fills replayed → position rebuilt

LoopDriver #2.run() startup gate (driver.py:335-370)
  ├─ RECOVERY_STARTED / RECOVERY_COMPLETED (reuse, never re-restore)  (driver.py:347-351)
  ├─ _check_master_readiness → True (equity ⇒ not applicable)         (driver.py:383-386)
  ├─ _canonicalize_restored_ledger → no-op (equity carve-out)         (driver.py:439-442)
  └─ _reconcile_ledger(broker_positions()) → []  → RECONCILIATION_PASS (driver.py:462-476)
       (a divergent broker book → alerts → RECONCILIATION_FAIL → abort_startup → STOPPED)
```

Tier A exercises: **SignalSource → LoopDriver → ExecutionHandler → PaperBroker → Persistence → Position Tracking → Restore → Reconciliation.** It does **not** exercise **Canonicalization** (equity is the carve-out — and pinning that it is correctly a no-op is itself a valid result).

### 3.2 Tier B — single-derivative extension (adds Canonicalization + master gate)

To light up the two remaining boxes — **Canonicalization** and the master-readiness gate — the source must emit on a **derivative** symbol under **`Mode.LIVE`** with a **materialized master** and `build_master_readiness(...)` injected:

```
driver.run() startup gate, LIVE ∧ has_derivatives ∧ master_readiness present:
  ├─ _check_master_readiness → FRESH/WARN (real resolver)            (driver.py:372-417)
  ├─ _canonicalize_restored_ledger:                                  (driver.py:439-444)
  │     ├─ execution.canonicalize_restored_positions()  (#7-as-restored)
  │     └─ execution.canonicalize_restored_orders()      (#8)
  └─ _reconcile_ledger → PASS/FAIL
```

**Tier B preconditions and honest caveats:**
- **Master must be materialized** — it is (`data/instruments/nse_fo_instruments.duckdb`, snapshots 2026-06-08/09).
- **F4 is live on this path** — `OptionsContractSelector`/`canonicalize_symbol` resolve the lot from the master (NIFTY=65, BANKNIFTY=30), which Open Finding **F4** flags as *unverified against exchange circulars*. For a **paper** wiring proof no real money is at risk, so observing canonicalization with lot 65 is acceptable **as infrastructure validation** — but the report must state the sized quantity is provisional until F4 is closed, and Tier B must **not** be read as endorsing the lot value.
- **Symbol-shape decision** — `canonicalize_symbol` (`handler.py:581-583`, `_handle_broker_fill` `:338-341`) resolves futures-shaped / option-shaped symbols, not necessarily a raw broker key. The synthetic derivative source must emit a symbol shape the canonical path actually resolves (or accept the legacy fallback). **This is the one new design decision Tier B forces** and should be settled in the characterization phase, not improvised in implementation.

Because Tier B drags in F4 + the symbol-shape question, **Tier A is the true "smallest" wiring proof**; Tier B is the *canonicalization-coverage* add-on, deliberately separated.

---

## 4. Required metadata (Q4)

From the pinned MM7C consumer contract (`handler.py:432-615, 819-824`):

| Field | Requirement for the synthetic source | Evidence |
|---|---|---|
| `symbol` | equity key (Tier A) or resolvable derivative shape (Tier B) | `handler.py:559,583` |
| `signal_type` | `BUY` then `EXIT` | `events.py:13-17`; `handler.py:461,586` |
| `metadata['sl_distance']` | **mandatory on BUY** — set a real value (e.g. `bar.close*0.01`). With a PaperBroker, omission does **not** hard-fail but takes the `_check_risk_limits` → warn-default path (`handler.py:470-482`); the source must supply it to avoid the warning path (MM7C C1). | `handler.py:457-482` |
| `metadata['risk_r']` | **mandatory on BUY** — set `1.0`. Same rationale. | `handler.py:457-482` |
| `metadata['signal_id']` | **optional** — handler auto-derives `sha256(symbol_strategy_timestamp)` (`handler.py:444-449`). Leaving it unset is fine **and** exercises idempotency derivation. The source MAY set it to make restart idempotency assertions explicit. | `handler.py:444-449` |
| `metadata['quantity']` | **optional hint** — handler caps at `max_position_size` and falls back to `default_quantity·(0.5+confidence·0.5)` (`handler.py:594`, MM7C C1). Source may omit (default sizing) or hint a small value. Sizing authority stays the handler's (ADR-005). | `handler.py:594, 819-824` |
| EXIT metadata | **none** — bare `EXIT`; handler resolves side/qty from its ledger; risk fields not required. | `handler.py:461,586-591` |
| `context` | **omit** — `TradeStructuralContext` is an audit snapshot, not required for routing. | `events.py:53-69`; `handler.py:542-556` |

So the only mandatory author-supplied metadata is **`sl_distance` + `risk_r` on the BUY**. Everything else is handler-derived or optional.

---

## 5. Expected persistence artifacts (Q5)

After a clean Tier-A round-trip + restart:

**SQLite `data/execution.db`** (`execution_store.py:20-63`) — the canonical execution-truth substrate:
- `orders` — 2 rows: the BUY order and the EXIT order (`correlation_id, symbol, side, quantity, order_type, strategy_id, signal_id, timestamp, metadata`).
- `fills` — 2 rows: entry fill and exit fill (`fill_id, order_id, symbol, quantity, price, side, fee, timestamp`).
- `positions` — snapshot rows written by the position tracker (note: this snapshot table is write-on-update; restore rebuilds from fills, not from this table — G1 Wave 3A H6).

**DuckDB `trading.db`** — audit/analytics projection:
- `trades` + `trade_context` — opening trade row (`save_trade`, `handler.py:387`) then exit update (`update_trade_exit`, `handler.py:377`).

**Journal `logs/runtime_events.jsonl`** (`event_journal`, driven by `driver.py:_emit`):
- `STARTUP`, `RECOVERY_STARTED`, `RECOVERY_COMPLETED`, `RECONCILIATION_PASS`, `RUNNING`, `STOPPING`, `STOPPED` (Tier A).
- Tier B adds `INSTRUMENT_MASTER_STALE` only if WARN; FRESH emits no event (G1 Wave 3B).
- A divergent reconcile adds `RECONCILIATION_FAIL` + a STOPPED refusal (MM7A T2/T3 shape).

**Side files:**
- `logs/heartbeat.json` — LIVE only (`driver.py:762`).
- `logs/execution_metrics.json` — `_persist_metrics` (`handler.py:191-217`).
- ZMQ telemetry topics — only if a `RuntimeTelemetryPublisher` is wired (optional; not needed for the proof).

**In-memory observables to assert:**
- `driver.state is RuntimeState.STOPPED`; `driver.bars_processed == N`; `driver.signals_pulled == 2`.
- `handler.position_tracker.get_all_positions()` net FLAT after EXIT.
- restored `handler._seen_signals` contains both signal ids → re-emitting the same id is a no-op (idempotency).
- `reconciliation.reconcile(matching_book) == []`.

---

## 6. Characterization plan (Q6) — tests to write before implementation

All characterization (no alpha). MM7C already pinned the *seam consumer contract*; MM7D pins the *synthetic source behavior + end-to-end artifacts*. Build against an **isolated tmp `execution.db`** with an isolation guard that `data/execution.db` is untouched (the MM7C construction).

1. **`test_synthetic_source_emits_buy_then_exit`** — call-indexed: `on_bar` #0 → one `BUY`, #1 → one `EXIT`, #2+ → `[]`; lifecycle hooks fire (`on_start` once before bars, `on_stop` once). (Reuses the `FakeSignalSource` lifecycle pattern, `_doubles.py:113-148`.)
2. **`test_buy_carries_valid_risk_fields`** — the BUY's `metadata` has real `sl_distance`+`risk_r`, so `process_signal` takes the clean path, **not** the warn-default path (`handler.py:457-482`).
3. **`test_equity_roundtrip_persists_orders_fills_positions`** — full Tier-A run over a *real* `ExecutionHandler` + `PaperBroker` + synthetic provider: assert 2 `orders`, 2 `fills` rows; position opens then flattens; `trades` audit row written then exit-updated.
4. **`test_restart_restores_ledger_and_idempotency`** — second handler on the same db restores orders/fills/`_seen_signals`; re-emitting the recorded BUY signal_id is rejected/no-op.
5. **`test_reconciliation_pass_and_fail`** — `broker_positions()` matching the restored book → `[]` → `RECONCILIATION_PASS` → RUNNING; a divergent book → alerts → `RECONCILIATION_FAIL` → `abort_startup` → STOPPED (reuses MM7A T2/T3 shape, `reconciliation.py:24-87`).
6. **`test_canonicalization_noop_on_equity_fires_on_derivative`** — Tier A: `canonicalize_restored_*` **not** called (equity gate, `driver.py:439-442`); Tier B (LIVE + derivative + real `build_master_readiness`): both fire exactly once (mirrors MM7A T4).
7. **`test_determinism_two_runs_identical_artifacts`** — two independent Tier-A runs produce identical routed signal streams and identical persisted rows (reuses MM7C C4 determinism).
8. **`test_t1_tripwire_stays_green`** — the synthetic harness lives in `tests/`, so `test_fno_entry_wiring.py:90-99` (no `scripts/` `LoopDriver`) remains GREEN — the proof does not masquerade as a production entry script.

---

## 7. Recommended implementation sequence

```
MM7A/B/C  ✅  seam contract + boundaries + determinism pinned
MM7D (this)   synthetic-source DESIGN (review only)
   ↓
1. Write §6 characterization tests (RED where they should be)         ← tests only
2. Implement the minimal SyntheticSignalSource (BUY→EXIT, equity)     ← smallest source
3. Build a tests/-level integration harness: real ExecutionHandler
   (PAPER, load_db_state, tmp execution.db) + PaperBroker + synthetic
   provider + synthetic source → run to STOPPED                       ← Tier A spine GREEN
4. Add restart + reconciliation PASS/FAIL assertions                  ← restore + reconcile
5. (Optional, gated) Tier B single-derivative LIVE+PAPER run to light
   up master-readiness + canonicalize_restored_* — only after the
   F4 lot value and the symbol-shape decision are settled             ← canonicalization
   ↓
MM7E  Entry Script Wiring (scripts/) — flips MM7A T1, reuses the proven parts
MM7F  Broker Positions Adapter (MM7A T2) → MM7G W3 Refusal (MM7A T3)
F4 verify → F3 disposition → product/margin → 4C.7
```

**Why this order.** The synthetic source is the cheapest possible end-to-end exercise of the wiring G1 closed and MM7A–C characterized. Proving it as an **integration test** (step 3) rather than a `scripts/` entry script keeps the MM7A T1 tripwire honest (T1 flips only when a *production* entry script lands — MM7E) and lets the spine be validated with **zero** market-data, chain, or alpha surface. Tier B is deliberately last and gated, because lighting up canonicalization unavoidably touches the unverified F4 lot and the symbol-shape question — neither of which belongs in the *smallest* wiring proof.

**The smallest implementation slice to do next:** steps 1–3 (characterization net + the BUY→EXIT equity synthetic source + the Tier-A integration harness). That single slice turns "the runtime is wired and tested in pieces" into "the runtime executes a known order and closes it end-to-end" — the infrastructure validation MM.7 now exists to deliver.

---

## 8. Stop condition

Review complete. Report written. **No production code, no SignalSource implementation, no entry script, no adapter, no provider, no tests, no commits.** NiftyShield not referenced beyond the abandonment note.

*Filed under the G1 / MM7A / MM7B / MM7C review-first, characterize-before-change discipline.*
