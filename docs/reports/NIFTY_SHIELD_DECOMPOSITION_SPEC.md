# NiftyShield — Decomposition Spec (`nifty_shield_v1`)

**Date:** 2026-08-07
**Status:** Stage 0 spec. Defines the **contract** for re-expressing the bundled monolith as a
certifiable `SignalSource` + execution-owned services. It is the spec DeepSeek V4 implements
from (role split: Claude writes the spec + reviews; DeepSeek implements). **No code exists yet.**
**Scope:** the *contract* — what the `SignalSource` emits, what execution must own, what
conformance will check, and the enumerated open decisions. **Not** a design of the exit
manager's internals.
**Spec of record:** `docs/reports/NIFTY_SHIELD_ADOPTION_ASSESSMENT.md` · **Datasheet:** `docs/strategies/nifty_shield_v1/datasheet.md`

---

## 1. Why decomposition (recap)

The bundled `nifty_shield_strategy.py` fails Stage 1 CONFORMANT on three static counts
(assessment §4): six illegal `core.*` imports, forbidden `core.execution`/`core.brokers`
handles, and side-effects in `on_bar`. The **design** is adopted; the **code** is re-expressed.
The target must pass `core/runtime/conformance.py` Layer 1 (static) + Layer 2 (behavioral).

**The load-bearing insight:** a dumb `SignalSource` **never needs option marks.** At 13:00 it
only *names* strikes (arithmetic on the underlying) and emits leg intents. Everything
marks-dependent — credit, group P&L, the 50%/2×/time exits, greeks, sizing, margin — is
**execution's**, evaluated against **real** marks. This satisfies "Strategies Stay Dumb /
Execution Owns Reality" (Principles #1/#3) *and* fixes the synthetic-pricing flaw at the exit
layer, where it matters.

## 2. Re-expression map

| Monolith piece (`nifty_shield_strategy.py`) | New home | Note |
|---|---|---|
| DayType regime read (`_fetch_vix_close`, engine `on_bar`/`on_bn_bar`) | **Regime/VIX facts** (DuckDB), read by the source | Principle #2; see §6. Relocates the model-identity concern to facts provenance (D2) |
| `_select_structure`, `_build_legs`, strike math | **Dumb `SignalSource`** | "strike/expiry chosen inside the source" is explicitly allowed (`signal_source.py:52`) |
| Regime lot sizing, VIX cut | **Execution sizing** | driven by params the source declares in `context`/`metadata`; `NseMarginEngine` authoritative (D4) |
| Structure as a book (multi-leg) | **`core/execution/groups/OrderGroup`** | `STRADDLE`/`STRANGLE` types exist; iron-fly → `IRON_CONDOR`/`CUSTOM`; spreads → `SPREAD` |
| Exits: 50% capture / 2× stop / 15:15 | **Execution exit-manager** | per-bar `GroupPnLTracker.get_group_unrealized_pnl(group_id, current_prices)` vs real marks (D5) |
| Delta-adjust hedge, `max_portfolio_delta` | **Execution risk-gate (flatten), not a new hedge** | dynamic hedging dropped in v1 (D1) — a new hedge from execution would invert ADR-006 |
| Greeks (`Black76Engine`) | **Execution** (exit-manager delta gate, margin) | `core/risk/greeks/` already present |
| `_init_db`, `_persist_signal`, `_persist_trade_entry/exit`, `_has_open_trade_today` | **Deleted** — platform ledger/journal | ADR-001/017; the source keeps only its own in-memory shadow of "did I already enter today" |

## 3. The `SignalSource` contract — `nifty_shield_v1`

### 3.1 Package and imports
- Export `build_signal_source(config) -> SignalSource` (the factory, MM12.5 §4.0).
- **Only** `core.events` and `core.runtime.signal_source` may be imported from `core.*`
  (`SANCTIONED_IMPORT_PREFIXES`). No `core.execution`, `core.brokers`, `core.instruments`,
  `core.risk`, `core.database`, `core.logging`, `core.analytics`.
- Hold **no** `core.execution`/`core.brokers` object as an attribute; **no** constructor
  parameter named `execution`/`handler`/`ledger`/`broker`/`driver`/… (`FORBIDDEN_*`).
- A read-only facts reader (regime/VIX — §6) is permitted as an input the source obtains
  itself; it must not be a ledger/broker/handler/execution object.

### 3.2 `on_bar(bar) -> List[SignalEvent]` — side-effect-free
Driven on `NSE_INDEX|Nifty 50` bars. Behavior:

- **Not the 13:00 checkpoint bar, or already entered this session, or VIX > `vix_skip_above`:**
  return `[]`.
- **At the 13:00 bar, flat, VIX ≤ skip:** read the session's regime fact + VIX (§6); select
  structure (`_select_structure` logic); compute strikes from `bar.close` + offsets/`strike_step`;
  emit **one `SignalEvent` per leg** (§3.3), then set an in-memory `entered_today` flag.
- Emits **no EXIT signals** — exits are execution-owned (§5). No option marks are read. No
  platform state is mutated (the `entered_today` flag is source-internal shadow state, allowed).

### 3.3 Leg encoding (decision D3 — recommended)
Each structure leg is a separate `SignalEvent`, all sharing a `group_id` in `metadata` so
execution assembles them into one `OrderGroup`:

```
SignalEvent(
  strategy_id = "nifty_shield_v1",
  symbol      = "<option instrument symbol, e.g. NSE_FO|NIFTY...CE>",
  timestamp   = bar.timestamp,
  signal_type = SELL (short legs) | BUY (wings),
  confidence  = <regime confidence, 0..1>,
  metadata    = {
    "group_id": "<uuid, shared across the structure's legs>",
    "structure": "short_straddle|short_strangle|iron_fly|bull_put_spread|bear_call_spread",
    "leg_role": "short_ce|short_pe|wing_ce|wing_pe",
    "strike": <int>, "expiry": "<YYYY-MM-DD>", "option_type": "CE|PE",
    "base_lots": <int>, "regime_mult": <float>, "vix_reduce": <bool>,
    "exit": {"tp_pct": 0.50, "sl_mult": 2.0, "hard_exit": "15:15",
             "max_portfolio_delta": 500}
  },
  context     = TradeStructuralContext(regime_state=..., regime_confidence=...,
                 session_type="PM", sl_distance=..., risk_r=..., ...),
)
```

`metadata.exit` and the sizing hints are **declarations** the execution layer reads and applies;
the source neither sizes nor exits. `symbol` resolution to a real option instrument is via the
existing instrument layer **at the execution boundary**, not inside the source (the source names
strike/expiry/option_type; execution resolves to the tradable symbol).

## 4. Sizing (execution) — decision D4
The source declares `base_lots`, `regime_mult`, `vix_reduce` (metadata) and regime in `context`.
Execution computes final lots = `max(1, round(base_lots × regime_mult))` then −1 if `vix_reduce`
(non-strangle), clamps to the margin ceiling via **`NseMarginEngine`** (the sole sizing
authority, ADR-011/013), and journals SPAN+ELM per entry (§7.7 evidence).

## 5. Exit management (execution) — decision D5
An execution-side exit component owns each `OrderGroup` from fill to close and evaluates, **per
bar between 13:00 and 15:15**, against **real marks**:

- **Take-profit:** `get_group_unrealized_pnl(group_id, current_prices) ≥ tp_pct × credit_received`
  → close the group.
- **Stop:** unrealized loss ≥ `sl_mult × credit_received` → close.
- **Hard time-exit:** at 15:15 → close whatever remains.
- **Delta flatten-gate (D1):** if portfolio |Δ| (Black-76, execution) > `max_portfolio_delta`
  → close the group. **v1 does not open a hedge leg** (that would be new intent from execution,
  inverting ADR-006).

**Verified reuse:** `OrderGroup` (`groups/order_group.py`) + `GroupPnLTracker`
(`groups/group_pnl.py`, `get_group_unrealized_pnl` is mark-to-market) provide the group and P&L
substrate. **Not reused:** `portfolio/exit_policy.py` — its `PositionState` (`current_z`,
`days_held`) is Carry-specific; it is cited only as **precedent** that exit decisions live in
`core/execution/`, not the strategy. **New build required:** the per-bar `current_prices`
(option-marks) feed into `get_group_unrealized_pnl`, and the exit-trigger component itself.
`credit_received` is the group's realized entry premium (execution knows it from fills).

## 6. Regime + VIX facts interface (DayType) — decision D2
The source reads the session's **13pm regime** and **VIX** as facts (DuckDB), rather than running
the DayType model itself (it only receives the underlying bar, not the Bank-Nifty feed the
Block-H features need; Principle #2 favours offline facts).

- **Fact schema (to define with the DayType infra adoption):** keyed by `session_date`, carrying
  `regime ∈ {BullTrend, BearTrend, Choppy}`, `regime_confidence`, `vix_close`, and a
  **`regime_fact_version` + content hash** so a Stage-1 replay is reproducible.
- **Provenance is load-bearing:** determinism now depends on facts provenance, and this repo has
  a scar exactly there (a source-of-truth store re-keyed by uncommitted code — CLAUDE.md). The
  regime fact must be produced by committed, re-runnable code and its version/hash recorded, or
  Stage-1 replay-equivalence cannot be certified.
- **⚠ Forward-PAPER dependency (flag, not resolved here):** Stage 2 needs the 13:00 regime
  computed **intraday from that session's bars** — a purely offline publisher is insufficient.
  This is a real dependency on the **out-of-scope DayType infra adoption** (assessment §7); Stage 2
  cannot begin until a live 13:00 regime-fact publisher exists.

## 7. Persistence, determinism, telemetry
- **No strategy-owned DB.** All trade truth flows to the platform ledger/journal (ADR-001/017);
  `_init_db`/`_persist_*` are deleted.
- **Determinism (Layer 1 + Stage 2):** two fresh sources over the identical bar corpus + identical
  recorded regime/VIX facts emit byte-identical signal streams. Randomness/wall-clock/network in
  `on_bar` are forbidden (the reason `_fetch_vix_close`'s live fetch is replaced by a fact read).
- The source emits `strategy_id="nifty_shield_v1"` on every signal (journal traceability).

## 8. Enumerated open decisions (operator ratifies; recommendations given)

**D1 and D2 ratified by the operator 2026-08-07** as recommended. D3–D5 are engineering defaults the implementer applies.

| # | Decision | Recommendation | Consequence if changed |
|---|---|---|---|
| **D1** | Delta management | **Drop dynamic hedging; `max_portfolio_delta` = flatten-gate** (close-only) | (a) strategy-emitted hedge needs marks → breaks separation; (c) close-only-leg trim distorts a defined structure. Recommendation keeps ADR-006. **Updates datasheet §5a/§9.** |
| **D2** | Regime source | **Facts publisher** (source reads a versioned/hashed regime fact) | Vendoring the model in-source doesn't solve "source only gets one bar." Relocates identity to facts provenance. **Updates datasheet §1a.** Couples Stage 2 to DayType infra. |
| **D3** | Leg encoding | **One `SignalEvent` per leg**, shared `group_id` in metadata | A single multi-leg signal would need a richer `SignalEvent` schema than the frozen contract provides. |
| **D4** | Sizing seam | Source **declares** base_lots/regime_mult/vix_reduce; **execution sizes** via `NseMarginEngine` | Sizing in the source violates Principle #1. |
| **D5** | Exit infra | **Reuse** `OrderGroup` + `GroupPnLTracker`; **build** the per-bar marks feed + exit-trigger; **do not** reuse `exit_policy.py` | Forcing the Carry `ExitPolicy` dataclass onto an intraday options book is a mis-fit. |

## 9. Stage 1 acceptance (what the build must show green)
- `SignalSourceConformanceSuite` Layer 1 (static: imports, handles, constructor, `on_bar`
  non-coroutine) + Layer 2 (behavioral over a recorded corpus) all PASS.
- `GuardedSignalSource(nifty_shield_v1)` also passes the full suite (MM12.4 precedent, mandatory).
- Replay-twice determinism: identical corpus + identical regime/VIX facts → byte-identical signals.
- The strategy package's own tests green at `code_ref` (recorded, not graded).
- Datasheet frozen; `code_ref` + `config_hash` pinned; D1/D2 ratified and reflected in the datasheet.

## 10. Cross-references
- Contract: `core/runtime/signal_source.py`, `core/runtime/conformance.py`, `core/events.py`.
- Execution reuse: `core/execution/groups/order_group.py`, `core/execution/groups/group_pnl.py`;
  precedent-only: `core/execution/portfolio/exit_policy.py`.
- Sizing authority: `core/risk/nse_margin_engine.py` / `core/execution/margin_tracker.py`.
- Pipeline: `MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §4.0–§4.2, §7.2, §7.7.
- Assessment §4 (why decompose), §5.1 (DayType identity), §3 (OSC prohibition).
