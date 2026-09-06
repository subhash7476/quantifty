# MM12.4 — Reference Strategy Architecture

**Date:** 2026-07-02
**Status:** PROPOSED — awaiting Technical Lead approval (same gate as MM12.1)
**Author role:** System Architect
**Milestone:** MM12.4 — first strategy admitted into the certified platform
(refines MM12.1 §15's MM12.4 line item; depends on MM12.2 conformance suite,
MM12.3 `GuardedSignalSource` — both complete)

This document is architecture only. No code is authored under it. It refines,
not revises, MM12.1: no ADR-016..019 decision is reopened, no frozen component
is touched by this document, and the refinement it makes to MM12.1 §15's MM12.4
line item goes to the same Technical Lead gate that approved MM12.1.

---

## 0. Preconditions and scope discipline

### 0.1 What is already certified and must not be reopened

| Certified surface | Source |
|---|---|
| `SignalSource` is the strategy interface; factory packaging | ADR-016 |
| Strategy state is shadow state; divergence is fail-safe | ADR-017 |
| Boundary validation is reject-and-journal, enforced by `GuardedSignalSource` | ADR-018 |
| Strategy fault policy is quarantine-and-continue | ADR-019 |
| `GuardedSignalSource` implementation, passes the conformance suite itself | MM12.3 (`docs/reports/MM12_3_GUARDED_SIGNAL_SOURCE_IMPLEMENTATION.md`) |
| `SignalSourceConformanceSuite` (Layers 1+2) | MM12.2 (`core/runtime/conformance.py`) |
| `LoopDriver`, `ExecutionHandler`, Risk/Margin engines, persistence, telemetry, broker adapters | Platform Infrastructure v1.0 (MM11.7) |

This document treats all of the above as fixed and designs only a new artifact
on top of them: a concrete reference strategy, and the one composition-root
wiring step ADR-018 already specified but MM12.3 explicitly deferred.

### 0.2 Refinement of MM12.1 §15, stated explicitly

MM12.1 §15's roadmap named the MM12.4 deliverable in one line: *"Reference
non-alpha `SignalSource` (inert + queue-backed discretionary example) +
end-to-end PAPER proof."* That phrasing was intentionally provisional — §15's
own header states "design-level; no code under MM12.1" — deferring the
concrete design to MM12.4's own architecture work. This document **is** that
deferred design work, and it refines the line item's shape:

An inert source (always `[]`) or a queue-backed discretionary source (idle
until a human/UI pushes something) can each pass conformance, but **neither
emits a real entry signal**, so neither exercises Risk, Margin, Persistence,
or a real Execution round trip — four of this milestone's ten stated
objectives. §7 below designs a concrete strategy that trades — deterministically,
non-alpha, on a fixed schedule — specifically so that every objective in the
task brief has a real, observable proof point. This is additive detail, not a
contract or ADR change: it touches no `SignalEvent` field, no `SignalSource`
method, no `GuardedSignalSource` behavior, and no frozen component. Because it
refines an MM12.1 line item, it is presented to the same Technical Lead gate
that approved MM12.1.

### 0.3 New surface this document proposes (complete list)

1. `reference_strategies/heartbeat/` — an external-style strategy package
   (§1–§8) living in this repo for CI/documentation reasons (§1.3), never
   imported by any `core/` module.
2. `reference_strategies/fault_fixtures/` — two throwaway, non-alpha
   `SignalSource` fixtures used only to drive `GuardedSignalSource`'s
   reject/quarantine paths through the *real* composition root (§8.2).
3. `scripts/run_reference_strategy.py` — a composition script (like a real
   strategy's own deployment script) that imports the reference package's
   factory and calls `fno_runner.build_runner(...)`.
4. `scripts/run_fault_drill.py` — the analogous composition script for the
   fault fixtures.
5. One production wiring change: `scripts/fno_runner.build_runner` wraps
   every injected `source` in `GuardedSignalSource` before constructing
   `LoopDriver` — this is ADR-018 executed, not a new decision (§4).
   **Implementation note:** the wrap must pass both the root's `journal`
   (already a `build_runner` parameter) and a real, shared `TelemetrySink`
   into `GuardedSignalSource`. `build_runner` has no telemetry-sink
   parameter today; `GuardedSignalSource` defaults to `NullTelemetrySink`
   if none is given. Without threading a real sink through, the fault
   drill's `STRATEGY_ERRORS`/`STRATEGY_QUARANTINE_EVENTS`/
   `SIGNAL_CONTRACT_REJECTIONS` counters (§10, §13.4–§13.5) land in a null
   sink and are unobservable — the implementer must add the parameter, not
   silently accept the default.
6. One proposed ADR (ADR-020, §11) recording the durable decisions: what a
   reference/canary strategy is, that it is PAPER-confined forever, and that
   guard behavior is proven live via throwaway fixtures through the real root.

Nothing else. No new `EventType`/`RuntimeMetric` members (the reference
strategy's happy path produces none of MM12.3's fault events by design — see
§9), no driver/handler change beyond the one guard-wrap line, no new ABC.

---

## 1. Reference strategy selection

### 1.1 The chosen design: a fixed-cadence "heartbeat" strategy

**`HeartbeatSignalSource`** trades a single, liquid NSE equity instrument on a
fixed, parameter-driven schedule that is a pure function of bar count:

> Every `entry_period_bars` bars, if flat, BUY. Exactly `holding_period_bars`
> bars after that entry, EXIT.

No indicator, no market read, no randomness. State is `position`
(`FLAT`/`LONG`), `bars_since_signal` (an integer counter, reset on every
emitted signal), and `total_bars_seen` (a never-reset counter kept only for
audit metadata, §5) — nothing else. Repeated forever, for as long as bars
arrive.

### 1.2 Instrument scope: equity, not F&O

The reference strategy trades a single NSE equity symbol (`NSE_EQ|INE...`)
using the existing 1-minute equity candle data (`CLAUDE.md` Data Layout:
2024-10-17 to present). It deliberately does **not** trade futures or
options. This is a scope decision with a direct, named tradeoff against one
of the ten stated objectives — see §1.4.

`NSE_INDEX|Nifty 50`/`Nifty Bank` are excluded as the traded instrument: they
are not directly tradable order symbols in this platform (index data feeds
signals/features; `ExecutionHandler`'s order-build path resolves a concrete
equity/future/option instrument, not a bare index). They remain a legitimate
*data* input for a future, more sophisticated reference variant, but add
nothing this design needs.

### 1.3 Where the reference strategy lives

`reference_strategies/heartbeat/` at the repository root — **not** under
`core/`, structured exactly as an external strategy repository would be (own
factory export, imports only `core.events` and `core.runtime.signal_source`).

**Why not a genuinely separate git repository** (which ADR-002's letter would
prefer): a reference/canary artifact whose entire purpose is to be exercised
by this repository's own CI, kept in lockstep with the contract it certifies
against, and read by every future strategy author as living documentation, is
better served by co-location than by a second repository that could silently
drift out of sync with the platform it's meant to validate. ADR-002's
enforced invariant is **import direction** (`core.strategies|runner|backtest|
state|models|ftmo` never imported by the platform), not physical repository
boundary — the MM12.2 conformance suite's own tests already construct
temporary strategy packages under `tmp_path` and certify them via a
`package_root: Path` argument, proving the boundary is enforced by import
scanning, not by repo topology. §12 (Definition of Done) extends that
checkable invariant to cover this new directory.

### 1.4 Naming discipline

`strategy_id = "reference_heartbeat_v1"` — versioned per ADR-016/§9 (a
strategy_id must change when logic changes; it keys the audit trail). This
name is deliberately unglamorous: it must never be mistaken for a real
trading strategy in a journal, a dashboard, or an incident review.

---

## 2. Why this strategy was chosen

### 2.1 Candidates considered and rejected

| Alternative | Rejected because |
|---|---|
| Inert source (`on_bar` always returns `[]`) | Passes conformance trivially but proves nothing about Risk, Margin, Persistence, or a real Execution round trip — 4 of 10 stated objectives go unproven. Already exists as a conformance fixture (`_InertSource` in `tests/runtime/test_signal_source_conformance.py`); no new value in re-authoring it as "the" reference strategy. |
| Queue-backed discretionary source (human/UI pushes signals) | Correctly demonstrates one of the four `SignalSource` client shapes (§5.3 of the seam docstring), but requires a human-in-the-loop to actually produce a trade, which defeats an unattended, repeatable, scriptable PAPER proof and a scriptable replay-twice proof (§8). Remains a valid pattern for a *future* discretionary-console reference, not this milestone's proof vehicle. |
| Indicator-based strategy (e.g., moving-average crossover, momentum) | Any indicator choice invites a design question ("why this indicator, this period?") that looks like real alpha — directly contradicts "not intended to make money" and invites scope creep. Also fails the "understandable in under five minutes" bar once an indicator and its parameters must be explained and justified. |
| Seeded-random signal generator | Technically reproducible with a fixed seed, but less *self-evidently* deterministic to a reviewer than a bar-count function — a reader has to trust the RNG seeding discipline rather than see it. A fixed-cadence rule needs no such trust: replay-equivalence is visually obvious from the rule itself (§6). |
| Multi-symbol / portfolio strategy | Adds cross-symbol ordering and portfolio-Greek surface with no incremental proof value; MM12.1 §3.2 defers multi-strategy composition until a second real strategy exists, and this reference strategy is not that strategy. A single symbol is sufficient to exercise every listed objective (§10 coverage table). |

### 2.2 Why fixed-cadence wins

1. **Zero design surface that could be mistaken for alpha.** The rule has no
   market awareness whatsoever — entries happen on a clock, not a signal.
   Its expected P&L is a random walk minus fees; this is provable by
   inspection of the rule, not by running a backtest (and, per §9.6, no
   backtest is required or meaningful for this strategy).
2. **It actually trades**, closing the gap the rejected inert/queue-backed
   alternatives leave (§2.1) — this is the deciding factor against the MM12.1
   §15 line item's literal wording (§0.2).
3. **Understandable in under five minutes.** The entire rule is the one
   sentence in §1.1. No indicator, no threshold tuning, no historical
   calibration.
4. **Trivially replay-equivalent** (§6) — state is an integer counter and an
   optional integer; the inductive proof of determinism fits in one
   paragraph.
5. **Naturally low-frequency** (one round trip roughly every
   `entry_period_bars + holding_period_bars` bars — see §5 for concrete
   values) — easy to audit by eye in a journal or ledger dump, unlike a
   strategy that fires every bar.

---

## 3. Strategy lifecycle

Maps directly onto MM12.1 §2's four phases; nothing here departs from the
certified lifecycle table.

| Phase | This strategy's behavior |
|---|---|
| **CONSTRUCTED** | `build_signal_source(config)` reads `entry_period_bars`, `holding_period_bars`, `sl_distance_pct`, `risk_r` (all with sane defaults, §5) from the opaque `config: dict`; allocates one empty per-symbol state entry (`position=FLAT`,
`bars_since_signal=0`, `total_bars_seen=0`) for each symbol it will see. No network, no file I/O, no ledger/broker access (none is available — §5.4). |
| **WARMUP** (`on_start`) | No-op. There is no indicator to warm and no file to open. May emit a private (stdlib `logging`, not platform journal — the strategy holds no journal handle) startup log line for local debugging only. |
| **ACTIVE** (`on_bar`) | Applies the fixed-cadence rule (§4) to the bar's symbol; O(1), no I/O, well under the S1 latency budget (MM12.1 §5.2). |
| **QUARANTINED** | Platform-imposed, not strategy behavior (ADR-019). By construction this strategy should never raise or return a malformed value in normal operation — if the fault-injection drill (§8.2, using separate throwaway fixtures, never this strategy) proves the *guard's* quarantine path, that is sufficient; the reference strategy itself reaching QUARANTINED on the happy-path run is treated as a strategy defect (§9.2) that fails acceptance, not an expected state. |
| **STOPPED** (`on_stop`) | No-op. Nothing to flush; no open resources. |

---

## 4. Signal generation rules

For each symbol independently (the strategy holds one state record per
symbol in its configured universe, keyed by symbol string):

```
on_bar(bar):
    state = per_symbol_state[bar.symbol]        # {position: FLAT|LONG,
                                                 #  bars_since_signal: int,
                                                 #  total_bars_seen: int}   (§5 audit field)
    state.total_bars_seen += 1
    state.bars_since_signal += 1

    if state.position == FLAT:
        if state.bars_since_signal >= entry_period_bars:
            state.position = LONG
            state.bars_since_signal = 0
            emit BUY(bar, sl_distance=..., risk_r=...)     (§5)
        else:
            emit nothing
    else:  # LONG
        if state.bars_since_signal >= holding_period_bars:
            state.position = FLAT
            state.bars_since_signal = 0
            emit EXIT(bar)
        else:
            emit nothing
```

`bars_since_signal` resets to 0 on every emitted signal, so a full
FLAT→LONG→FLAT cycle is exactly `entry_period_bars + holding_period_bars`
bars — the "~75 bars per round trip" figure used throughout §2.2, §5, and §8
is this pseudocode's direct consequence, not an approximation of a different
rule. `total_bars_seen` is a separate, never-reset counter kept solely for
the `reference_bar_index` audit field (§5); it plays no role in the state
machine.

**Properties, by construction:**

- At most one signal per symbol per bar — the BUY and EXIT branches are
  mutually exclusive within a single `on_bar` call, so the "EXIT before
  entries" ordering convention (MM12.1 §4.4) is trivially satisfied for a
  single symbol.
- For the multi-symbol case (should the reference strategy ever be run
  against more than one instrument), the two branches are evaluated **in two
  passes across the configured symbol list** — all EXIT-eligible symbols
  first, then all BUY-eligible symbols — so a same-bar EXIT+BUY coincidence
  across different symbols still honors the EXIT-before-entries convention.
- The rule reads only `bar.symbol`, `bar.timestamp` (passed straight through
  to the emitted signal — §5), `bar.close` (for `sl_distance`, §5), and its
  own `state` dict. It reads nothing else — no other bar field, no external
  state, no ledger.
- Shadow-state discipline (ADR-017) is exact **within a single process
  lifetime**: `state.position` is the strategy's *belief* that it is long,
  derived solely from its own emitted signals. If a BUY it emitted was
  silently rejected downstream (kill switch, margin, risk, stacking,
  priceability gate — MM12.1 §3.4), the strategy still believes it is long
  and will faithfully emit an EXIT `holding_period_bars` later — which the
  handler will no-op on FLAT (`handler.py:699-701`), per the fail-safe
  divergence table already certified in ADR-017. No new *within-lifetime*
  divergence class is introduced.
- **Named limitation, not covered by the above:** `state` is held in memory
  only and is never reconstructed from the ledger on restart (ADR-017 §3.3's
  in-scope divergence direction assumes continuous operation). If the
  process restarts while `state.position == LONG`, `ExecutionHandler`
  recovers the real open position from the ledger (`build_runner`'s
  `load_db_state=True`), but the freshly-constructed strategy instance
  starts `FLAT` — the reverse divergence direction (platform long, shadow
  flat) that ADR-017 states is structurally impossible *within* a running
  process. This is not a new platform hazard (the recovered position is
  still ledger-truth and fully risk/margin-gated on any subsequent signal),
  but it does mean this strategy's own next scheduled BUY will hit the
  stacking guard once, and its shadow EXIT will arrive with no matching
  shadow entry to explain it in the strategy's own state — an honest gap,
  not a silent one. It is exactly the case MM12.1 §3.4/ADR-017 reserved the
  `on_start(context)` read-only position projection for, and is intentionally
  not built here (no second consumer yet — see §9's restart row and §12).

---

## 5. Metadata requirements

On every BUY (never on EXIT, per MM12.1 §4.2 — EXIT carries no mandatory risk
metadata):

| Key | Value | Rationale |
|---|---|---|
| `sl_distance` | `round(bar.close * sl_distance_pct, 2)` | Deterministic function of the entry bar's close; always `> 0` since `bar.close > 0` and `sl_distance_pct > 0` — satisfies the guard's mandatory-positive-numeric check (MM12.3) by construction, not by luck. |
| `risk_r` | fixed constant from config (default `500.0`) | Deterministic, config-owned, always `> 0`. |

Recommended defaults (config-overridable, not hardcoded in the strategy
logic): `entry_period_bars=60`, `holding_period_bars=15`,
`sl_distance_pct=0.01`, `risk_r=500.0`. On 1-minute candles this yields one
round trip exactly every 75 bars (`entry_period_bars + holding_period_bars`
— §4's pseudocode; ~75 minutes intraday) — low-frequency, easy to audit, and
small enough relative to `fno_runner`'s `initial_capital=100_000.0` default
that the capital-utilisation gate is not expected to reject an entry in the
happy-path run (§9.4).

**Fields intentionally left unset:**

- `signal_id` — omitted; the handler's derived
  `sha256(symbol_strategyid_timestamp)` is sufficient because the rule never
  emits two same-type signals for the same symbol in the same bar (§4).
- `quantity` — omitted; sizing stays with the platform (Execution Owns
  Reality, CLAUDE.md Principle 3).
- `execution_mode` — omitted; plain equity order, no option routing.
- `context` (`TradeStructuralContext`) — deliberately left `None`. Its schema
  (regime state, dispersion, volatility, breadth ratio) implies real market
  analysis a strategy with no market awareness should not fabricate.
  Auditability (§10) is fully carried by the private metadata below instead.

**Strategy-owned audit metadata** (private, namespace-prefixed per MM12.1
§4.2, journaled verbatim, never interpreted by the platform):

- `reference_bar_index` — the value of `state.total_bars_seen` at emission time.
- `reference_rule` — `"fixed_cadence_entry"` or `"fixed_cadence_exit"`.

Together these make every emitted signal self-explaining without needing to
cross-reference strategy source code: "bar 660, rule=fixed_cadence_entry"
is a complete causal explanation, satisfying Audit-First (CLAUDE.md
Principle 5) with the simplest possible fact.

---

## 6. Determinism guarantees

`state = f(bars_since_signal_this_symbol, position, config)` — nothing else.
The rule reads no wall-clock, no RNG, no network, no file, no shared mutable
state, and no execution outcome (ADR-017). Determinism is not merely
asserted; it is inductively provable from §4's pseudocode: `on_bar` is a
total, side-effect-free function of `(state, bar)`, and `state` is entirely
determined by the count and content of prior `on_bar` calls on the same
symbol. Two fresh instances driven over an identical bar sequence necessarily
visit the identical sequence of `(state, bar)` pairs and therefore emit the
identical signal sequence, byte-for-byte.

This satisfies every row of MM12.1 §6's forbidden-pattern table by
construction (no `datetime.now()`, no unseeded randomness, no network calls,
no reads of mutable shared state, no unordered-collection dependence, no
conditioning on execution outcomes, no cross-symbol float-accumulation
dependence — the per-symbol state dict is fully isolated per key).

---

## 7. Replay guarantees

Two distinct, complementary replay proofs — one already certified, one new:

### 7.1 Already proven (MM12.2, in-process)

`HeartbeatSignalSource` passing the conformance suite's
`check_replay_equivalence` (replay-twice, in-process, two fresh instances
over the same in-memory bar list) is a **CONFORMANT** gate requirement — no
new mechanism needed, §6 guarantees it passes trivially.

### 7.2 New for this milestone (end-to-end, through the real root)

The conformance suite proves the *strategy* is replay-equivalent in
isolation. It has never proven that the *whole stack* — guard, driver,
execution, risk, margin, PaperBroker, persistence — preserves that
equivalence when driven for real. MM12.4's acceptance evidence (§9, §13)
requires running `scripts/run_reference_strategy.py` **twice**, from a clean
ledger, over the identical recorded historical bar corpus, through the real
`fno_runner.build_runner` composition root, and diffing two classes of output
separately:

1. **The emitted signal stream** (captured via a test-only observer or the
   journal's own record of routed signals) — must be byte-identical between
   the two runs. This is the direct, clean extension of §7.1 through the
   real root instead of the in-process harness.
2. **The resulting ledger's deterministic decision fields** — symbol, side,
   quantity, fill price, and the derived `signal_id`
   (`sha256(symbol_strategyid_timestamp)`) for every trade — must be
   identical between the two runs.

**Explicitly excluded from the ledger diff, and why:** `PaperBroker.place_order`
mints a fresh `broker_id = str(uuid.uuid4())` on every call (`paper_broker.py`),
and `RuntimeEventJournal.record` stamps every row with `datetime.now(_IST)`
wall-clock (`event_journal.py`) — both by design, both already non-deterministic
today for any run, and neither is a decision field the strategy or the guard
controls. A diff that included them would fail on every run regardless of
correctness. The replay proof is scoped to the fields that determinism
actually claims to guarantee.

**Implementation note:** both replay runs must feed the identical recorded
bar corpus via `build_runner`'s existing `provider=`/`max_bars=` injection
seams (already present, used by the driver's own characterization tests),
not the default live `LiveDuckDBMarketDataProvider` — otherwise "identical
corpus" is not actually guaranteed between the two runs. This is expected to
be a non-issue for the watchdog (which is live-only, gated on
`config.is_live` — MM12.1 §5.1 T5/DRIVER_SPECIFICATION §9.5) but the
implementer should confirm this at MM12.4d rather than assume it.

---

## 8. Paper-trading expectations

- **Mode:** `ExecutionMode.PAPER` only, via `fno_runner.build_runner(...,
  execution_mode=ExecutionMode.PAPER)`. `PaperBroker` "simulates immediate
  fills with zero slippage" (`paper_broker.py`) — no capital ever moves; no
  broker credential is required.
- **Expected frequency:** one BUY→EXIT round trip roughly every 75 bars per
  symbol at the recommended defaults (§5) — sparse enough to audit an entire
  session by eye in the journal or a ledger query.
- **Expected P&L:** flat-to-slightly-negative over any long run. The rule has
  no market view, so gross P&L is a random walk around zero; brokerage/STT/
  exchange fees (CLAUDE.md fee model) are a small, real, structural drag. A
  materially profitable or materially loss-making run over enough trades
  would itself be worth investigating (most likely a bug in the harness's
  price feed or fee application), since the design has no mechanism to
  produce a directional edge.
- **Two run modes**, both composition scripts, both strategy-agnostic
  `fno_runner.build_runner` underneath:
  1. `scripts/run_reference_strategy.py` — the happy-path proof (§9.1). Runs
     `HeartbeatSignalSource` for a full session (or a longer recorded
     multi-day corpus) and is expected to complete with **zero**
     `SIGNAL_CONTRACT_REJECTED` / `STRATEGY_ERROR` / `STRATEGY_QUARANTINED`
     journal entries.
  2. `scripts/run_fault_drill.py` — the guard-proof run (§9.2, §8.2 below),
     using the two throwaway fixtures in `reference_strategies/fault_fixtures/`
     (`AlwaysRaisesSource`, `BadMetadataSource`) instead of the heartbeat
     strategy. This run is **expected** to produce exactly the
     `SIGNAL_CONTRACT_REJECTED`/`STRATEGY_ERROR`/`STRATEGY_QUARANTINED`
     events MM12.3 designed — that is the proof, not a failure.

### 8.1 Why the drill uses separate fixtures, not the reference strategy

Deliberately: mixing "this is the well-behaved reference strategy" with
"this is deliberately broken to trigger the guard" in one artifact would
undermine the "understandable in under five minutes" property (§1's
five-minute rule now needs an exception clause) and would make it ambiguous,
on any future re-run, whether an observed rejection/quarantine is the
intended drill outcome or a real regression. Two small, clearly-named,
never-deployed fixtures (mirroring `conformance.py`'s own broken fixtures,
§7.2 of MM12.1) keep the two proofs — "the platform hosts a well-behaved
strategy correctly" and "the platform correctly rejects/contains a
misbehaving one" — visibly separate.

---

## 9. Failure modes

| Observed condition (happy-path run, §8's run 1) | Classification | Action |
|---|---|---|
| `SIGNAL_CONTRACT_REJECTED` appears | **Strategy defect** — the reference implementation violated its own contract (§5 guarantees this should be structurally impossible) | Fails acceptance (§13); root-cause and fix before certification |
| `STRATEGY_QUARANTINED` / `STRATEGY_ERROR` appears | **Strategy defect** — an unhandled exception (e.g., a config value producing invalid state) | Fails acceptance; root-cause and fix |
| Position-stacking guard blocks an entry (`handler.py:633-636`) | Should never occur for this strategy specifically — ADR-017's divergence direction (§4) means shadow-state can only be long when platform truth is flat-or-long, never falsely believe flat while platform is long — if observed, treat as a platform-defect signal worth investigating, not an expected outcome | Investigate; not an acceptance blocker by itself, but not expected |
| Margin/risk/kill-switch gate silently rejects an entry (`process_signal` returns `None`) | **Not a fault** — MM12.1 §3.4/§8.1's existing, already-certified "no strategy feedback" behavior. Legitimate outcome if `initial_capital` is configured too low relative to `risk_r`, or if an unrelated kill-switch condition is active. | Not an acceptance blocker; recommended defaults (§5) are sized to avoid it in the happy-path run, but its occurrence does not itself indicate a defect |
| Feed gap / missing bars | No effect — the rule is bar-count-driven, not wall-clock-driven (§6); a gap simply delays the next scheduled action by however many bars were skipped | Not a failure mode |
| Journal/telemetry/alerter side-channel failure during a fault drill | Already contained by `GuardedSignalSource` (MM12.3) — inherited protection, not new surface this milestone adds | Not a new failure mode |
| `scripts/run_reference_strategy.py` forgets to wrap `source` in `GuardedSignalSource` (i.e., the wiring in §1.0.3 item 5 was skipped or reverted) | **Composition defect** — an unguarded raise from a strategy would crash the whole process (MM12.1 §8.2's "today" behavior, the exact failure mode ADR-019 exists to prevent) | This is precisely what the fault drill (§8.2, run 2) is designed to catch; its absence in that run's evidence fails acceptance |
| Process restarts while `state.position == LONG` (an open position exists) | **Named, honest limitation — not a fault, not covered by acceptance evidence.** The strategy's in-memory shadow state does not survive a restart; `ExecutionHandler` recovers the real ledger position, the strategy instance restarts `FLAT` — the reverse-divergence direction ADR-017 states is impossible *within* a running process (§4's Named limitation). The recovered position remains fully ledger-truth and risk/margin-gated on any subsequent signal — no platform hazard — but the strategy's own audit narrative has a gap at that point. | Out of scope for MM12.4 acceptance (§13); the restart proof required by §13 is scoped to restart-while-flat only (between round trips). Closing this gap is the `on_start(context)` extension point ADR-017 already reserved, gated on a demonstrated need — not built here |

---

## 10. Objective → coverage table

The task brief lists ten things this milestone must demonstrate. Each row
below states how the reference strategy's two runs (§8) exercise it, and
names the gap honestly where one exists.

| Objective | Exercised by | Coverage |
|---|---|---|
| **Strategy Contract** | `HeartbeatSignalSource` passes MM12.2 Layers 1+2 (`run_conformance`) — the first non-fixture package to do so | Full |
| **GuardedSignalSource** | Happy-path run: wrapped, validates every signal, zero drops/quarantines. Fault drill: reject-and-journal + quarantine-and-continue proven live through the real root, not test doubles | Full — first proof outside unit tests |
| **LoopDriver** | Full startup gate (recovery, reconciliation, master readiness), tick loop, per-bar routing, watchdog, telemetry cadence, kill-switch edge check, all exercised across a real multi-session PAPER run | Full |
| **ExecutionHandler** | Full `process_signal` pipeline: idempotency lock, risk checks, margin gate, stacking guard, order construction, `PaperBroker` fill, position/PnL tracker update | Full for the equity non-option path; the `execution_mode="option"` branch is not exercised (§1.2) |
| **Risk** | `_check_risk_limits`, drawdown gate, kill-switch checks all run on every entry | Partial — the Greek-limit gate is exercised only in its EXIT/no-option bypass branch; option Greek risk is untouched (no options traded) |
| **Margin** | `_check_margin_budget` (the flat-rate `MarginTracker` capital-utilisation gate) runs on every entry | **Partial, by deliberate scope decision — see §1.2 and the note below.** SPAN/`NseMarginEngine` (the F&O-specific margin engine, MM9.5/MM10, feature-frozen and separately certified) is not exercised, because no F&O instrument is traded |
| **Persistence** | Real fills recorded through the SQLite ledger (ADR-001 truth) and the DuckDB audit projection; a process restart **while flat** (between round trips) exercises recovery replay cleanly | Full for the within-round-trip fill path and restart-while-flat. Restart **while holding an open position** is explicitly out of scope — see §9's restart row and §4's Named limitation (shadow state does not survive a restart; reserved for ADR-017's `on_start(context)` extension point, not built here) |
| **Telemetry** | `RuntimeMetric` counters, ZMQ telemetry publish cadence, and — in the fault drill — the three MM12.3 journal/telemetry additions (`STRATEGY_ERROR`/`STRATEGY_QUARANTINED`/`SIGNAL_CONTRACT_REJECTED`, `STRATEGY_ERRORS`/`STRATEGY_QUARANTINE_EVENTS`/`SIGNAL_CONTRACT_REJECTIONS`) all observed for the first time outside a unit test | Full |
| **Replay** | (a) MM12.2's in-process replay-twice (already passing); (b) new — two full runs of the real composition root over an identical recorded corpus, diffed on deterministic fields (§7.2) | Full, strictly extends what MM12.2 already proved |
| **Auditability** | Every signal carries `reference_bar_index`/`reference_rule`; journaled verbatim; every trade traceable bar → signal → order → fill → ledger row with no missing link | Full |

**On the Margin row, stated plainly:** this is the one place the simplicity
mandate ("complexity hides platform defects," task brief) trades directly
against full objective coverage. The alternative — trading a future or
option to exercise SPAN/`NseMarginEngine` — pulls in instrument-master
readiness, contract selection, and SPAN-snapshot freshness gating, none of
which are needed to prove "the platform correctly hosts an external
strategy" and all of which were already independently certified in MM9.5/
MM10 against real NSE SPAN files (`docs/reports/MM9_5_S4_IMPLEMENTATION_SPEC.md`,
ADR-008). F&O margin proof under a *real, external, signal-emitting* strategy
remains the responsibility of MM13 (First External Strategy Validation) or a
dedicated F&O reference variant, not this milestone.

---

## 11. What this milestone DOES prove

- The full **data → guard → driver → execution → risk → margin (flat-rate)
  → PaperBroker → ledger → persistence → telemetry → journal** pipeline
  works end-to-end for an externally-authored, dumb, replay-equivalent
  `SignalSource`, driven through the **real composition root**
  (`fno_runner.py`), not test doubles — closing the ADR-014 "named cost"
  MM12.1 §15 identified.
- `GuardedSignalSource` correctly passes clean signals through, and (via the
  fault drill) correctly rejects contract violations and quarantines a
  faulting source, **live**, not merely under conformance-suite or unit-test
  doubles.
- Determinism/replay-equivalence holds through the **entire stack**, not
  just the strategy in isolation — replaying identical historical data twice
  through the real root yields an identical signal stream and identical
  deterministic ledger outcomes.
- The flat-rate margin/risk gates run for every real order exactly as they
  would for any future real equity strategy.
- Persistence correctly records a full round-trip trade lifecycle
  originating from an external `SignalSource`, and survives a process
  restart that occurs while the strategy is flat (between round trips).
- Telemetry and journal observability reflect a real external-strategy
  session, including the MM12.3 fault vocabulary, for the first time outside
  a unit test.
- The promotion ladder's **CONFORMANT** gate (MM12.1 §14.1) is a real,
  passable bar for an actual strategy package, not only for in-repo fixtures.

## 12. What this milestone explicitly DOES NOT prove

- **Alpha or profitability of any strategy.** The reference strategy has no
  market view and is expected to be flat-to-slightly-negative over any long
  run, by design (§8).
- **LIVE trading readiness.** This milestone is PAPER-only. LIVE-APPROVED
  status requires the separate go-live checklist (MM12.5), a funded account,
  credential lifecycle management, and broker-side reconciliation (MM14,
  ADR-013) — none of which this milestone touches. The reference strategy
  is, by ADR-020 (§14), never to be promoted past PAPER.
- **SPAN / `NseMarginEngine` (F&O margin) correctness under a live strategy.**
  Explicitly scoped out — see §10's Margin row and its note.
- **Multi-strategy composition.** One process, one strategy (ADR-016 §3.2);
  unaffected here.
- **Broker-side reconciliation for a strategy-originated position.**
  `PaperBroker` never touches a real broker; that hazard is LIVE-only and
  deferred to MM14.
- **The strategy's own research/backtest quality.** There is no alpha to
  validate, so the promotion ladder's "external backtest" evidentiary step
  (MM12.1 §14.1) is not meaningful for this strategy and is not attempted —
  it is exempt because it will never seek LIVE-APPROVED status, not because
  the requirement is waived for strategies generally.
- **Real capital or real broker API behavior** (rate limits, partial fills,
  credential expiry) — LIVE-specific hazards, orthogonal to PAPER.
- **Shadow-state recovery across a process restart while a position is
  open.** The reference strategy's in-memory state does not survive a
  restart; only a restart-while-flat is covered by this milestone's
  acceptance evidence (§9, §13). This is the named limitation ADR-017
  already anticipated and reserved the `on_start(context)` read-only
  position projection for — not built here, for lack of a second
  demonstrated consumer (MM12.1 §3.4, §16.2).

---

## 13. Acceptance criteria

MM12.4 (the implementation slice this document authorizes, §15) is complete
only when all of the following hold, with evidence filed in an MM12.4
implementation report mirroring the MM12.3 report's structure:

1. `reference_strategies/heartbeat/` passes MM12.2 Layers 1+2 conformance
   unmodified (CONFORMANT gate, §7.1).
2. `scripts/run_reference_strategy.py`, run once over a recorded multi-session
   corpus in `ExecutionMode.PAPER`, completes with **zero**
   `SIGNAL_CONTRACT_REJECTED`, `STRATEGY_ERROR`, or `STRATEGY_QUARANTINED`
   journal entries, and **at least one** full BUY→EXIT round trip is present
   in the resulting ledger.
3. The same script run **twice**, from a clean ledger, over the identical
   recorded corpus, produces byte-identical emitted signal streams and
   identical deterministic ledger fields on the second run (§7.2's scoped
   diff — excluding `broker_id` and journal wall-clock timestamps).
4. `scripts/run_fault_drill.py`, using `AlwaysRaisesSource`, proves
   quarantine-and-continue live: the journal shows `STRATEGY_ERROR` then
   `STRATEGY_QUARANTINED` (edge-triggered once), matched by
   `RuntimeMetric.STRATEGY_ERRORS`/`STRATEGY_QUARANTINE_EVENTS` each reading
   exactly 1 on the shared telemetry sink (§4's implementation note), the
   driver loop, watchdog, and telemetry all continue for subsequent bars,
   and the process does not crash.
5. `scripts/run_fault_drill.py`, using `BadMetadataSource`, proves
   reject-and-journal live: `SIGNAL_CONTRACT_REJECTED` appears, matched by a
   non-zero `RuntimeMetric.SIGNAL_CONTRACT_REJECTIONS` on the shared
   telemetry sink, and any contract-clean sibling signal in the same bar
   still routes.
6. Telemetry counters (`RuntimeMetric.BARS_PROCESSED`, `SIGNALS_RECEIVED`,
   `SIGNALS_ROUTED`, `EXECUTION_CALLS`) are observably non-zero for run 1.
7. `git diff --stat` on `core/runtime/driver.py`, `core/execution/handler.py`,
   `core/runtime/signal_source.py`, `core/runtime/conformance.py`,
   `core/runtime/guarded_signal_source.py`, `core/runtime/event_journal.py`,
   and `core/runtime/metrics.py` is **empty** — this milestone adds a new
   strategy package and two composition scripts; it modifies no certified
   platform subsystem.
8. The one permitted production change — `fno_runner.build_runner` wrapping
   every injected `source` in `GuardedSignalSource` (§4) — is present, and
   every existing caller of `build_runner` that injects a signal-emitting
   source has been audited for contract-clean signals (a source lacking
   `sl_distance`/`risk_r` on BUY/SELL would have its signals silently
   dropped post-wrap where they previously routed — see §14's Consequences).
9. The full existing test suite continues to pass with zero regressions.

---

## 14. ADR recommendation

One ADR-grade decision. Recommended for authoring at MM12.4 implementation
kickoff (numbering continues from ADR-019):

### ADR-020 (proposed) — Reference Strategy Is A Permanently PAPER-Confined, Non-Alpha Canary; Guard Behavior Is Proven Live Via Throwaway Fixtures

**Decision to capture:**

- A reference/canary strategy exists solely to prove the platform correctly
  hosts an external `SignalSource` — it carries no alpha, is never intended
  to be profitable, and is **permanently confined to `ExecutionMode.PAPER`**.
  It must never be configured with a real `BrokerAdapter` or promoted through
  the CONFORMANT → PAPER-VALIDATED → LIVE-APPROVED ladder (MM12.1 §14.1);
  this is enforced by convention (no code ever constructs it with
  `execution_mode=ExecutionMode.LIVE` or a `broker=`), not by a new runtime
  policy object — building an enforcement mechanism ahead of a second
  reference strategy's need would repeat the rejected `MarginProvider`
  pattern (ADR-013 reasoning).
- The chosen design is a fixed-cadence, single-equity-symbol "heartbeat"
  (§1–§9 above); alternatives (inert, queue-backed, indicator-based, seeded
  RNG) are rejected for the reasons in §2.1.
- `GuardedSignalSource`'s reject-and-quarantine behavior is proven live
  (through the real composition root, not test doubles or the conformance
  harness) using **separate, throwaway fixture sources**
  (`reference_strategies/fault_fixtures/`), never the reference strategy
  itself — establishing the standing pattern for how any future strategy's
  guard behavior gets end-to-end proof.
- `fno_runner.build_runner` wraps every injected `source` in
  `GuardedSignalSource` unconditionally — this is **execution of ADR-018**,
  explicitly deferred by MM12.3 to this milestone (`docs/reports/
  MM12_3_GUARDED_SIGNAL_SOURCE_IMPLEMENTATION.md` §1), not a new decision,
  and therefore does not itself need a new ADR.

**Alternatives to record:** trading an F&O instrument to exercise SPAN/
`NseMarginEngine` (rejected — pulls in instrument-master/contract-selection
complexity with no proof value for this milestone's actual goal, §10);
wrapping the guard only for a strategy-specific code path in `fno_runner.py`
rather than unconditionally (rejected — contradicts ADR-018's "every
external source" wording and would silently leave a future strategy
unguarded unless a human remembered to special-case it).

**Consequences to record:** ADR-002's checkable import-direction invariant
("no `core.strategies|runner|backtest|state|models|ftmo` import anywhere in
the platform") is extended to also forbid any `core/` module importing
`reference_strategies` — a recorded consequence of this ADR, not an edit to
ADR-002 itself (ADRs are append-only).

---

## 15. Implementation roadmap

| Slice | Deliverable | Depends on | Exit criterion |
|---|---|---|---|
| **MM12.4a** | This document + ADR-020 authored | MM12.2, MM12.3 | Technical Lead approval (same gate as MM12.1) |
| **MM12.4b** | `reference_strategies/heartbeat/` package (§1, §4, §5) | MM12.4a | Passes MM12.2 conformance unmodified (§13.1) |
| **MM12.4c** | `reference_strategies/fault_fixtures/` (`AlwaysRaisesSource`, `BadMetadataSource`) + `fno_runner.build_runner` unconditional guard-wrap (§4, §14) + the `build_runner`-caller contract-clean audit (§13.8) | MM12.4b | Zero diffs in the frozen list (§13.7); existing suite green |
| **MM12.4d** | `scripts/run_reference_strategy.py` + `scripts/run_fault_drill.py` | MM12.4c | Acceptance criteria §13.2–§13.6 all pass; MM12.4 implementation report filed (mirrors the MM12.3 report structure: Implementation Summary, Boundary/Coverage Report per §10's table, Fault Injection Report, Journal Report, Telemetry Report, Test Report, Deviations) |

MM12.5 (promotion-path document + go-live checklist) and MM13 (First External
Strategy Validation, PAPER) remain sequenced as MM12.1 §15 and PROJECT_STATE
already specify — unchanged by this document.

---

## 16. Acceptance checklist

Copy of §13 in checklist form, for the implementer to run through before
filing the MM12.4 implementation report:

- [ ] `reference_strategies/heartbeat/` passes `run_conformance` (Layers 1+2)
- [ ] Happy-path PAPER run: zero `SIGNAL_CONTRACT_REJECTED` /
      `STRATEGY_ERROR` / `STRATEGY_QUARANTINED`; ≥1 full round trip in the ledger
- [ ] Replay-twice through the real root: signal stream byte-identical;
      ledger deterministic fields identical (broker_id / journal timestamps
      excluded, §7.2)
- [ ] Fault drill (`AlwaysRaisesSource`): `STRATEGY_ERROR` → `STRATEGY_QUARANTINED`
      (once) → loop/watchdog/telemetry survive → process does not crash
- [ ] Fault drill (`BadMetadataSource`): `SIGNAL_CONTRACT_REJECTED` observed;
      clean sibling signals (if any) still route
- [ ] `RuntimeMetric` counters non-zero for the happy-path run
- [ ] `git diff --stat` empty for the seven frozen files listed in §13.7
- [ ] `fno_runner.build_runner` unconditionally wraps `source` in
      `GuardedSignalSource`; every existing `build_runner` caller injecting a
      signal-emitting source audited for contract-clean signals
- [ ] Full existing test suite passes, zero regressions
- [ ] ADR-002's checkable invariant extended to cover `reference_strategies`
      (§14 Consequences)
- [ ] MM12.4 implementation report filed in `docs/reports/`
- [ ] `docs/PROJECT_STATE.md` and `docs/CHANGELOG_PLATFORM.md` synced

---

## 17. Definition of Done

MM12.4 is done when:

1. §16's checklist is fully checked, with evidence (not assertion) for each
   item, in the filed implementation report.
2. ADR-020 is authored and Accepted.
3. `reference_strategies/heartbeat/` and `reference_strategies/fault_fixtures/`
   exist, are conformant, and import nothing beyond the sanctioned surface
   (`core.events`, `core.runtime.signal_source`).
4. `scripts/run_reference_strategy.py` and `scripts/run_fault_drill.py` exist
   and are independently runnable by any future engineer without needing
   this document open beside them (self-documenting CLI help text).
5. Zero diffs in every certified platform subsystem except the one
   authorized `fno_runner.build_runner` guard-wrap line (§4, §13.7–§13.8).
6. The reference strategy's `strategy_id` (`reference_heartbeat_v1`) never
   appears in any LIVE-mode journal record, by construction (§14, ADR-020).
7. PROJECT_STATE.md and CHANGELOG_PLATFORM.md are synced to reflect MM12.4's
   completion, in the same style as the MM12.1/MM12.2/MM12.3 entries.

This milestone is complete only when the platform has hosted a real,
externally-styled, signal-emitting strategy through its full certified stack
at least twice — once cleanly, once under deliberate fault — and both runs
are recorded as durable evidence.

---

*Ref: docs/reports/MM12_1_STRATEGY_INTEGRATION_ARCHITECTURE.md (§2–§9, §14,
§15 — refined by this document, not superseded); docs/reports/
MM12_3_GUARDED_SIGNAL_SOURCE_IMPLEMENTATION.md; docs/ARCHITECTURE_DECISIONS.md
ADR-002, ADR-014, ADR-016..019; core/runtime/signal_source.py;
core/runtime/guarded_signal_source.py; core/runtime/conformance.py;
scripts/fno_runner.py; core/brokers/paper_broker.py.*
