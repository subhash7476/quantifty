# NiftyShield — Stage 1 Implementer Prompt (`nifty_shield_v1`)

**For:** DeepSeek V4 (implementer). **Author/reviewer:** Claude (role split — Claude writes the
prompt + reviews; DeepSeek implements). **Status:** hand-off artifact — **not yet executable**;
execute only after the preconditions below are met. **Do not begin coding before reading the
three authoritative docs in §1.**

**Goal:** re-express the bundled NiftyShield monolith as a **Stage-1-CONFORMANT `SignalSource`**
(`nifty_shield_v1`) plus execution-owned services, taking the strategy from Stage 0 DEVELOPMENT to
the Stage 1 CONFORMANT submission (MM12.5 §4.1). This does **not** deploy or validate alpha — that
is Stage 2 forward PAPER, out of scope here.

---

## 0. Preconditions (do not start until all hold)
- [ ] **D1 and D2 ratified by the operator** (Decomposition Spec §8). D1 = delta is a flatten-gate,
      no dynamic hedge. D2 = regime read as a versioned/hashed fact. If either is overridden, stop
      and request an updated spec — do not improvise.
- [ ] **Regime/VIX fact interface exists** (Spec §6): schema fixed, and **offline regime/VIX facts
      for the conformance corpus** produced by committed, re-runnable code with a recorded
      `regime_fact_version` + content hash. (The *live* 13:00 publisher is a Stage-2 prerequisite,
      not needed for Stage 1 conformance.)
- [ ] Working on a dedicated branch; `strategy_id = nifty_shield_v1` (Ledger E004).

## 1. Read first (authoritative — this prompt does not restate them)
1. `docs/reports/NIFTY_SHIELD_DECOMPOSITION_SPEC.md` — **the contract you implement.** §2 map,
   §3 SignalSource, §4 sizing, §5 exits, §6 facts, §8 decisions D1–D5.
2. `docs/strategies/nifty_shield_v1/datasheet.md` — identity, config, risk declaration, §10
   round-trip convention.
3. `docs/reports/NIFTY_SHIELD_ADOPTION_ASSESSMENT.md` — §3 **PROHIBITION**, §4 why-decompose.
4. Contract code: `core/runtime/signal_source.py`, `core/runtime/conformance.py`, `core/events.py`.
5. Execution reuse: `core/execution/groups/order_group.py`, `core/execution/groups/group_pnl.py`.
6. Source design (reference only — **do not copy**): `F:\nifty_research_bundle\nifty_shield\`.

## 2. Deliverables

**A. The `SignalSource` package** (`build_signal_source(config) -> SignalSource`)
- `on_bar` per Spec §3.2: at the 13:00 bar, flat, VIX ≤ skip → read regime/VIX facts, select
  structure + strikes (arithmetic on `bar.close`), emit **one `SignalEvent` per leg** (§3.3,
  shared `group_id` in metadata); else `[]`. Emits **no EXIT**. No option marks read. No platform
  state mutated.
- Imports: **only** `core.events`, `core.runtime.signal_source`. No execution/broker/instrument/
  risk/database/logging/analytics imports; no forbidden handles or constructor params.
- The regime/VIX facts reader is a read-only input the source holds — never a broker/ledger/
  handler/execution object.

**B. Execution-owned services** (in `core/execution/`, honoring Principles #1/#3)
- **Sizing (D4):** final lots from declared `base_lots`/`regime_mult`/`vix_reduce`, clamped by
  `NseMarginEngine` (sole authority); journal SPAN+ELM per entry.
- **Group formation:** assemble the legs sharing a `group_id` into one `OrderGroup`
  (`STRADDLE`/`STRANGLE`/`SPREAD`/`IRON_CONDOR`/`CUSTOM`).
- **Exit-manager (D5):** own each group 13:00→15:15; per bar, using
  `GroupPnLTracker.get_group_unrealized_pnl(group_id, current_prices)` against **real marks**:
  take-profit ≥ `tp_pct × credit`, stop ≥ `sl_mult × credit`, 15:15 hard exit, and the **delta
  flatten-gate** (|Δ| > `max_portfolio_delta` → close, **no hedge**). Build the per-bar
  `current_prices` (option-marks) feed. Do **not** reuse `portfolio/exit_policy.py` (Carry-specific).
- **Persistence:** platform ledger/journal only. Delete every `_init_db`/`_persist_*`/`fetch_ltp`
  path from the design.

**C. Tests**
- A conformance test calling `run_conformance(...)` — Layer 1 + Layer 2 green over a named,
  committed recorded corpus (with recorded regime/VIX facts).
- `GuardedSignalSource(nifty_shield_v1)` passes the full suite too (mandatory, MM12.4).
- Replay-twice determinism: identical corpus + identical facts → byte-identical signal stream.
- Execution-side unit tests for sizing, group assembly, and each exit trigger (TP/SL/time/delta),
  against synthetic marks fixtures.

**D. Datasheet freeze inputs** (hand back for the CONFORMANT grant, do not self-grant)
- Pin `code_ref`, `config_hash`, package path. Resolve `iv_default`/`cost_per_lot_rs` disposition.
- Compute the **max-DD number** via datasheet §7a (stress method; **backtest DD is not an input**).
- Set the margin-utilization ceiling; confirm SPAN+ELM exercised. Measure `on_bar` p99 latency.

## 3. Hard constraints (non-negotiable)
- The three conformance gates the monolith failed (assessment §4) must all pass: sanctioned
  imports, no forbidden handles, side-effect-free `on_bar`.
- **No strategy-owned database.** **No live order placement** (paper path only).
- Implement D1–D5 exactly as ratified. Do not reintroduce a strategy-side exit, hedge, sizing, or
  persistence.
- **Do not modify any frozen platform component** (MM12.5 §0.1; CLAUDE.md Feature-Frozen table).
  If the contract seems insufficient, stop and report — a needed platform change is a milestone
  with its own ADR, not an edit inside this task.

## 4. Prohibitions (protocol-critical)
- **Never backtest over the OSC-preserved unread index-options window 2016-02-11 → 2022-12-31**
  (assessment §3). Alpha is validated **only** by Stage 2 forward PAPER, never a historical read.
- Do not produce or present any P&L number as "validation." Stage 1 certifies **safety, not alpha**.

## 5. Acceptance = Stage 1 CONFORMANT submission ready
Conformance Layer 1+2 green (raw + guard-wrapped); replay-twice determinism proven; strategy tests
green at `code_ref` (recorded); datasheet freeze inputs supplied; conformance report written to the
dossier. Then the **grantor** (Technical Lead) reviews and files **Ledger E005**
(`DEVELOPMENT → CONFORMANT`). The implementer proposes with evidence and **grants nothing** (§8).

## 6. Explicitly out of scope for this prompt
- The **DayType facts infra** (offline + live 13:00 publisher) — a separate adoption; its offline
  slice is a §0 precondition, its live slice is a Stage-2 prerequisite.
- **Stage 2 forward PAPER**, the go-live checklist, and any live Upstox wiring.
- `sweep_filter` — excluded from this identity (assessment §5.4).
