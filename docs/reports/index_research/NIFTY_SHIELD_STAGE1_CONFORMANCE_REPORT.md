# NiftyShield v1 — Stage 1 Conformance Report

**Date:** 2026-08-07
**Branch:** `research/nifty-shield-stage1`
**Strategy:** `nifty_shield_v1` (Promotion Ledger E004 — DEVELOPMENT → CONFORMANT submission)
**Implementer:** DeepSeek V4. **Grantor:** Technical Lead (proposes nothing here; this report proposes with evidence).
**Specs:** `NIFTY_SHIELD_DECOMPOSITION_SPEC.md` (§2–§9) · `NIFTY_SHIELD_STAGE1_IMPLEMENTATION_PROMPT.md`
**Contract:** `core/runtime/signal_source.py`, `core/runtime/conformance.py` (MM12.2), `core/events.py`
**Preconditions (§0):** D1/D2 ratified ✓ · regime/VIX fact interface exists ✓ (DayType facts publisher, `DAYTYPE_FACTS_IMPLEMENTATION_REPORT.md`) · dedicated branch ✓ · `strategy_id=nifty_shield_v1` ✓

## 1. What was built

**A. The `SignalSource` package** — `strategies/nifty_shield_v1/` (external, ADR-016):

| File | Role |
|---|---|
| `__init__.py` | `build_signal_source(config)` factory export + `config_hash` |
| `config.py` | datasheet §3 certified dict; `config_hash` excludes the `facts_db_path` runtime seam |
| `facts.py` | `RegimeFactsReader` — read-only 13pm fact load at `on_start` (D2; model never runs in the source) |
| `structures.py` | pure arithmetic: structure selection (§5a), weekly-expiry, ATM+offset strikes, leg specs |
| `source.py` | `NiftyShieldSignalSource` — dumb 13:00 emitter per §3.2 |

`on_bar` behaviour (decomposition §3.2): at the 13:00 bar of a flat session with VIX ≤ skip →
read the session's fact, select structure, compute strikes from `bar.close`, emit **one
`SignalEvent` per leg** (§3.3, shared deterministic `group_id`), set the in-memory `entered_today`
flag. Returns `[]` for non-13:00 bars, already-entered sessions, missing facts, and VIX-skip
days. Emits **no EXIT signals**, reads **no option marks**, mutates **no platform state**.

**B. Execution-owned services** (`core/execution/options/`, Principles #1/#3):

| File | Role |
|---|---|
| `nifty_shield_sizing.py` | D4: declared lots → margin-ceiling clamp via the margin engine (sole sizing authority) |
| `nifty_shield_groups.py` | §3.3/D5: assemble legs sharing a `group_id` → one `OrderGroup`; resolves tradable options at the boundary |
| `nifty_shield_exit.py` | D5: per-bar TP / SL / 15:15 time / delta-flatten triggers against real marks |

**C. Committed conformance corpus** — `strategies/nifty_shield_v1/corpus/`:
`bars.csv` (2,250 Nifty 50 1m bars, 6 sessions 2023-01-02→01-09) + `facts.csv` (matching 13pm
regime facts, Choppy/Bear/Bull, VIX 14–15 — every session fires). Built by
`scripts/nifty_shield/build_conformance_corpus.py`. **Index 1m bars + facts only — the OSC
index-options window (2016-02-11→2022-12-31) is untouched.**

## 2. Conformance evidence (all script-generated)

```
tests/strategies/test_nifty_shield_v1_conformance.py      — 7 tests
tests/execution/test_nifty_shield_execution.py            — 15 tests
```

| Gate | Check | Result |
|---|---|---|
| MM12.2 Layer 1 (static) | `is_signal_source`, non-coroutine `on_bar`, constructor surface, no forbidden handles, sanctioned import surface (package scan) | **PASS** |
| MM12.2 Layer 2 (behavioral) | lifecycle, return shape, timestamp discipline, entry risk metadata, replay equivalence | **PASS** |
| Guarded wrapper | `run_conformance(GuardedSignalSource(nifty_shield_v1), …)` full suite | **PASS** |
| Replay-twice determinism | two fresh instances over the corpus → **byte-identical 16-signal stream** | **PASS** |
| Session contract | 6 sessions × 1 structure; iron_fly (4 legs ×2 sessions), bear_call/bull_put (2 legs); shared `group_id` per structure | **PASS** |
| Risk metadata | every BUY/SELL carries `sl_distance>0`, `risk_r>0`, `exit{tp 0.50, sl 2.0, 15:15, delta 500}` | **PASS** |
| `config_hash` | stable; excludes `facts_db_path` → **`c5b722ff…536c`** | **PASS** |

**Full-suite run:** 108 tests green (daytype + strategies + nifty_shield execution +
conformance + reference strategy suites).

## 3. Execution-side unit tests (synthetic marks fixtures)

Sizing (D4): declared lots Choppy 2 / Bear 1; VIX-reduce shaves non-strangle only; margin
clamp reduces to the ceiling; engine-backed `structure_margin_over_engine`. Group assembly:
iron-fly → `IRON_CONDOR` 4 legs, SELL shorts / BUY wings, quantity = lots×75; rejects
multi-group or empty leg sets. Exit-manager (D5): take-profit, stop-loss, 15:15 time exit,
delta-flatten (close-only, no hedge), and hold-when-no-trigger — all against synthetic marks.

## 4. Datasheet freeze inputs (proposed; grantor freezes, does not take from this report)

| Input | Value |
|---|---|
| `config_hash` | `c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6` |
| `on_bar` p99 latency | **0.0022 ms** measured (2,250-bar corpus; budget 50 ms) |
| Max DD (§7a, no backtest input) | worst single day **Rs 30,000**; stressed 5-day streak **Rs 150,000** |
| Margin ceiling | proposed **25% of allocated capital** |
| `iv_default` / `cost_per_lot_rs` | inert for the source (pricing = execution vs real marks; fees = platform model) — retain or drop at grant |
| `undefined_risk_stress_pts` | **200** — the one new decomposition key (per-leg risk declaration + §7a) |

## 5. Decisions honoured

- **D1** delta = flatten-gate, close-only, **no hedge leg** (exit-manager returns `delta_flatten`, never opens a hedge).
- **D2** regime read as a versioned/hashed **fact**; the DayType model is not in the strategy triple.
- **D3** one `SignalEvent` per leg, shared deterministic `group_id` (`uuid5(strategy, session, structure)` — **deterministic so replay-equivalence holds**; a random uuid would fail it).
- **D4** source declares `base_lots`/`regime_mult`/`vix_reduce`; execution sizes + margin-clamps.
- **D5** execution owns every exit trigger; `GroupPnLTracker` reused, `portfolio/exit_policy.py` not reused.

## 6. Prohibitions honoured

- **No backtest over the OSC index-options window** — the corpus is Nifty-50 index 1m bars + facts, no option-mark read, no P&L.
- **No P&L presented as validation** — this report certifies safety/contract, not alpha.
- **No strategy-owned DB, no live order placement, no frozen-component modification.**
- **No sweep_filter** in the identity.

## 7. Hand-back (what the grantor reviews for Ledger E005)

1. Conformance Layer 1+2 green, raw + guard-wrapped (tests above).
2. Replay-twice determinism proven byte-identical.
3. Datasheet freeze inputs supplied (§4); datasheet updated in place (still DRAFT — grantor freezes).
4. `code_ref` to pin at grant: the commit of this branch.

The implementer proposes with evidence and grants nothing.
