# G1_WAVE4B_POSITION_IDENTITY_REVIEW.md

**Type:** Gate G1 — Wave 4B **Forward Position Identity review + migration plan**. **Planning only; NO production code, tests, or KB changed in this turn.**
**Date:** 2026-06-11
**Scope (locked):** the **live F&O forward position-identity construction** — Migration Targets **#6** (`Position(symbol=…)` ctor) and **#7** (`PositionTracker.get_position`) from `SOLE_IDENTITY_PATH_REVIEW.md` Section 1. Forward **order** identity (#1/#2 futures DONE, #4/O1+O2 option DONE) and the **restore** replay (#8 orders DONE, #9/#7-as-restored positions DONE) are out of scope here.
**Basis (file:line, verified 2026-06-11):** `core/execution/position_models.py`, `core/execution/position_tracker.py`, `core/execution/margin_tracker.py`, `core/execution/pnl_tracker.py`, `core/execution/handler.py`, `core/execution/canonical_restore.py`, `core/execution/futures.py`, `core/instruments/instrument_parser.py`, `core/instruments/identity.py`. Master DB read-only (`data/instruments/nse_fo_instruments.duckdb`, snapshot 2026-06-09).

**Verdict:** #6 and #7 are **ONE migration**, not two — a single *forward position-identity* slice. **#6 is dead on the production path** (no `Position(symbol=)` caller exists) → it reclassifies from **MIGRATE** to a **prove-dead carve-out**, subsumed once #7's seam supplies a canonical `instrument=`. **#7 is the sole live position-identity site**, but the corruption-relevant identity is *materialized once* at the fill seam (`update_from_fill`, `position_tracker.py:152`), which is where the canonical derivation belongs (it carries a timestamp; `get_position` does not). Unlike the restore halves (#8 orders / #9 positions, which were SEPARATE — independent objects, independent reconstruction, an intervening identity-blind gate), #6 and #7 are two constructions of the **same** `Position` object and cannot be split into independently-valuable behavior-preserving commits. **G1 stays OPEN** (this slice + the Wave-5 guard + closeout remain).

> **Numbering caveat:** "#6/#7" here are the **`SOLE_IDENTITY_PATH_REVIEW.md` Section-1 site numbers** (#6 = `Position` ctor, #7 = `get_position`) — the scheme `PROJECT_STATE.md` uses ("position #6/#7, restore replay #8/#9"). They are unrelated to the `PROJECT_STATE.md` **Planned-item** scheme (where "Planned #6" = broker-side reconciliation). This document uses the site-number scheme throughout.

---

## 1 — The two sites, mapped

### #6 — `Position(symbol=…)` ctor (`position_models.py:30-52`)

```python
resolved_instrument = instrument or InstrumentParser.parse(symbol or "")   # :47
object.__setattr__(self, "instrument", resolved_instrument)
```

The `parse(symbol or "")` branch fires **only** when `instrument is None` and the caller passed `symbol=`. Two verified facts make this branch dead on the live path:

- **No production caller constructs `Position(symbol=…)`.** `grep -n "Position(symbol="` repo-wide → the only hits are the ctor's own docstring (`position_models.py:45`) and an unrelated comment in `tests/brokers/test_upstox_positions.py:5` (that file refers to the **broker adapter's** `Position`, not `core.execution.position_models.Position`). No runtime code path reaches the `symbol=` branch.
- **The tracker always builds `Position(instrument=…)`.** Every `Position(...)` construction inside `PositionTracker` passes `instrument=`: `get_position` (`:32`), `update_from_fill` (`:152`), `replace_instrument` (`:179`). So #6's `parse` fallback is **bypassed** on the only path that builds positions.

**→ #6 is a prove-dead carve-out** (the exact posture #10 `NormalizedOrder(symbol=)` received in Wave 1). Its `parse` branch is a dormant backward-compat affordance; no behavior-preserving migration is possible (there is no live behavior to preserve) or necessary. The Wave-5 guard should assert it stays unreached.

### #7 — `PositionTracker.get_position` (`position_tracker.py:27-32`)

```python
def get_position(self, symbol: str) -> Position:
    if symbol in self._positions:
        return self._positions[symbol]
    instrument = InstrumentParser.parse(symbol)          # :31  ← identity minted here
    return Position(instrument=instrument)                # :32  passes instrument=, bypassing #6
```

This is the **sole live position-identity construction**. `InstrumentParser.parse` has only an Option-regex + an Equity fallback (no Future branch, hardcodes `Option(lot_size=1, multiplier=1.0)`, `instrument_parser.py:33-46`), so:

- a **futures** symbol → `Equity(multiplier=1.0)` (the H1 mistype, at the position level);
- an **option** symbol → `Option(lot_size=1, multiplier=1.0)` (the H2 lot drift, at the position level);
- an **equity** symbol → `Equity` (correct; carve-out).

**Two structural sub-facts that shape the migration:**

1. **The FLAT identity is inert.** For an *untracked* symbol `get_position` returns a FLAT `Position(quantity=0)`. Every consumer of a FLAT position is identity-blind: `net_quantity` returns `0.0` for FLAT (`:41-43`), `has_open_position` reads only `.side` (`:36`), and margin/PnL multiply by `quantity` (0). So the FLAT position's `lot_size`/`multiplier` is **never consumed**.
2. **The OPEN identity is materialized once, at the fill seam.** `update_from_fill` does `pos = get_position(symbol)` (`:87`) then builds `new_position = Position(instrument=pos.instrument, …)` (`:152-153`), **copying** the FLAT get_position instrument into the persisted open position. So an open position inherits the parse-built (`lot=1`, futures→`Equity` `mult=1`) identity from the *first* lookup — this is the identity that lives for the life of the position and is consumed downstream.

---

## 2 — Identity ownership: who consumes `position.instrument`

| Consumer | File:line | Field read | Affected by migration? |
|---|---|---|---|
| Margin exposure | `margin_tracker.py:35` | `pos.instrument.multiplier` | **Futures: YES** (1→65). Options: no (mult stays 1.0). |
| Unrealized PnL | `pnl_tracker.py:57` | `pos.instrument.multiplier` | **Futures: YES.** Options: no. |
| Realized PnL (on fill) | `position_tracker.py:123` | `pos.instrument.multiplier` | **Futures: YES.** Options: no. |
| Greeks / portfolio | restore precedent (`portfolio_greeks.py:48,56,73`) | `position.instrument` | Futures/options: identity corrected. |
| Exit diagnostics | `handler.py:357` | `pos.side` only | No (side/qty, not identity). |
| Order-build / stacking guard | `handler.py:544,672` | `.side`, `.quantity` | No. |
| Reconciliation | `reconciliation.py:58` | symbol + quantity (identity-blind, H3) | No. |

**The load-bearing finding: the consumed field is `multiplier`, not `lot_size`.**

- **Option position:** `parse` → `Option(lot=1, mult=1.0)`; canonical-derived (`canonicalize_symbol`) → `Option(lot=ci.lot=65, mult=1.0)`. **`multiplier` is unchanged (1.0)**, so margin/PnL/exposure are **byte-identical**. Only `lot_size` corrects 1→65 — an **identity-only** fix (no live consumer reads an option position's `lot_size`). This is behavior-preserving for every numeric consumer.
- **Futures position:** `parse` → `Equity(mult=1.0)` (H1 — no Future branch); canonical-derived (`resolve_future`) → `Future(mult=ci.lot=65.0)`. **`multiplier` changes 1.0→65.0**, so margin/exposure/PnL change **65×** for any open futures position. This is a **genuine, intended behavior change** (futures *do* carry a lot multiplier; the current `mult=1` is the defect), and it must be characterized + justified — the analog of O2's EXIT-lot change, but reaching a numeric output (margin/PnL) rather than an inert identity byte.

This asymmetry (options = identity-only/behavior-preserving; futures = intended margin/PnL change) is the single most important property the Wave-4B characterization net must pin **before** the migration.

---

## 3 — Canonical insertion point (the seam) + the timestamp obstacle

**The obstacle:** `get_position(symbol)` has **no timestamp parameter**, but `canonical_restore.canonicalize_symbol(symbol, timestamp)` requires an `as_of` for point-in-time resolution (`resolver.resolve_option/resolve_future(..., as_of=)`). Canonicalizing *at* `get_position` would force either a signature change rippled across 9 call sites or a wrong `date.today()` default (incorrect under the replay clock / backtests). And it is unnecessary — the FLAT identity `get_position` mints is inert (§1, sub-fact 1).

**The seam:** `update_from_fill` (`position_tracker.py:152`) is where the **open** position — the only one whose identity is consumed — is materialized, and a `FillEvent` carries `.timestamp` (`fill.timestamp`). The clean migration derives the canonical instrument *there*, from `fill.symbol` + `fill.timestamp`, and uses it for `new_position.instrument` instead of copying the inert parse-built `pos.instrument`. This:

1. **Keeps `get_position` legacy** — the high-frequency lookup stays master-independent and timestamp-free; the FLAT identity never flips on master presence (ADR-003 determinism preserved at the hot path).
2. **Has a timestamp** (`fill.timestamp`) for correct point-in-time resolution under live and replay clocks.
3. **Reuses the existing primitive** — `canonicalize_symbol` (already the O2 + restore source): futures→`Future`, option→master-lot `Option`, equity/unresolved→`None`→keep legacy. The `CanonicalInstrument` stays internal (G1/4C.7). No resolver injection needed (it self-defaults, matching O1/O2).
4. **Guarantees forward == restored identity** — the forward open position and its restored twin both derive through `canonicalize_symbol`, so the Wave-3A forward/restore asymmetry (forward futures position `Equity`-typed, forward option position `lot=1`) closes with **no restart drift**. Optionally the existing `PositionTracker.replace_instrument` (`:170`, built for #7-as-restored) can be the swap mechanism, keeping one identity-swap path for forward and restore.

**Constraints (the DERIVE contract, mirroring O1/O2):** the position **`symbol` key is preserved byte-for-byte** (the derived instrument carries the same `.symbol`; never `ci.display_symbol`) so `_positions` keying, persistence, and reconciliation (H3, symbol-keyed) are unaffected; the legacy `Position` is *derived* from the canonical, not replaced by a `CanonicalInstrument`.

---

## 4 — One migration or two? (the question)

**ONE migration** — a single *Forward Position Identity* slice. Evidence:

1. **#6 has no live behavior to migrate.** No `Position(symbol=)` caller exists; the tracker bypasses the branch with `instrument=`. Migrating #6 in isolation is a **no-op** on the live path — it cannot be an independently-valuable, independently-revertible wave. It reclassifies to a prove-dead carve-out and is *subsumed* the moment #7's seam supplies a canonical `instrument=` (which it already does structurally).
2. **#7 mints the live identity at a single seam.** The open-position identity is materialized once (`update_from_fill:152`) into a single `Position` object; one canonical derivation at that seam fixes the whole forward position path. There is no second object or second reconstruction to split off.
3. **#6 and #7 are the same object's construction.** They share the source (`InstrumentParser.parse`) and the product (`Position`). This is structurally different from the restore halves #8/#9, which were correctly split into **two** commits because orders and positions are *independent objects* with *independent reconstruction* (`order_repository.py:60`→`NormalizedOrder` vs fill-replay→`Position`) separated by an identity-blind gate (`G1_WAVE3B_GATE_ORDERING_REVIEW.md` §3). No analogous independence exists between #6 and #7.

**Therefore:** plan it as **one slice, one commit, one rollback point** — "migrate #7 at the fill seam; fold #6 as a prove-dead carve-out." Splitting would strand a no-op half (#6) and a half-wired hot path (#7).

**Caveat that reinforces ONE (not zero-failure):** unlike O1 (pure DERIVE, zero expected failures), this slice is **not** uniformly behavior-preserving — the futures-position `multiplier` 1→65 is an intended margin/PnL change (§2). Keeping it a single focused commit with one characterization net (rather than splitting) is what makes that intended change auditable in one place.

---

## 5 — Characterization coverage required before migration (the Wave-4B safety net)

Per the F-PARSE-1 discipline (pin reality; identical assertions green before, justified deltas after), these must exist and be **green on current code** before any migration edit. They extend the position-level reality that `test_g1_restore_characterization.py` already pins forward (`fwd_pos.instrument.lot_size == 1`, futures position `Equity`-typed).

1. **P1 — forward OPTION position identity.** Open an option via the selector ENTRY path; assert the *open* `position.instrument` is a legacy `Option`, `lot_size == 1` (today) / `multiplier == 1.0`, symbol byte-identical. (Post-migration: `lot_size → 65`, `multiplier` stays `1.0` — identity-only.)
2. **P2 — forward FUTURES position identity + margin/PnL.** Open a futures position; assert `position.instrument` is `Equity`, `multiplier == 1.0` **today**, and pin `margin_tracker.get_exposure` / `pnl_tracker.get_unrealized_pnl` at a fixed price. (Post-migration: instrument `Future`, `multiplier == 65.0`, exposure/PnL ×65 — the **one intended numeric change**, justified.)
3. **P3 — margin/PnL invariance for options.** Pin `get_exposure`/`get_unrealized_pnl` on an open option position before and after — must be **unchanged** (multiplier stays 1.0). This is the proof the option half is behavior-preserving.
4. **P4 — FLAT identity inert + `get_position` untouched.** Assert an untracked symbol's `net_quantity == 0` / `has_open_position == False` regardless of master presence (ADR-003 at the hot path), and that `get_position` still returns a legacy instrument (the seam is the fill, not the lookup).
5. **P5 — forward == restore identity parity.** A forward-built futures/option open position and its restored twin (`canonicalize_restored_positions`) carry the **same** instrument identity (type + multiplier + lot) — no restart drift. Closes the Wave-3A asymmetry finding.
6. **P6 — #6 prove-dead.** Assert/guard that no production path constructs `Position(symbol=)` (grep-clean), documenting the carve-out (parallel to Wave 1's #10 treatment).
7. **P7 — equity position carve-out.** An equity-symbol position stays legacy `Equity` (`canonicalize_symbol → None → parse`), margin/PnL unchanged.

**Gate:** no migration edit merges unless P1–P7 (plus the existing restore position characterizations) are green before, and only P2's futures margin/PnL assertions move after (justified, value-corrected).

---

## 6 — Dependencies, F4, and sequencing

- **Restore precedent already supplies the primitives.** `canonical_restore.canonicalize_symbol` and `PositionTracker.replace_instrument` exist and are proven (Wave 3 #7-as-restored, #8). The forward slice **reuses** them — it does not introduce a second derivation mechanism, which is what guarantees P5 parity.
- **F4 (lot 65/30) is NOT required to land this slice.** Like O1/O2, the migration is behavior-preserving *with respect to the master's current value*: it adopts whatever the master holds (65 futures multiplier / 65 option lot). F4 exchange-verification gates the path going **live**, not the refactor. Do not change 65/30 to land Wave 4B.
- **Ordering.** Independent of the order slices (#1/#2/#4/O1/O2, all DONE). It should land **after** restore #7-as-restored (DONE) so P5 parity is definitionally achievable. It completes the *forward* identity story (orders done → positions next), leaving only #8/#9 (DONE) and the Wave-5 guard for Section-6 closure.
- **Carve-outs unchanged:** equity (ISIN-less, out of F&O scope) and paper/replay stay legacy by design; the FLAT-lookup identity at `get_position` stays legacy by design (inert).

---

## 7 — Recommended Wave 4B sequence

```text
Characterization (P1–P7, green on current code)
 ↓
Migration (ONE slice): canonicalize the open-position instrument at the fill seam
   - update_from_fill: derive instrument via canonicalize_symbol(fill.symbol, fill.timestamp)
     (reuse replace_instrument or build new_position with the derived instrument)
   - get_position stays legacy (FLAT identity inert; no timestamp); #6 = prove-dead carve-out
 ↓
Expected failures: futures-position margin/PnL ×65 (P2) — the ONE intended change; options
   identity-only (P1 lot 1→65, P3 margin/PnL unchanged); everything else green
 ↓
Assertion updates: only P2's futures multiplier/exposure/PnL (justified, F4-value-as-master);
   prove the position symbol key + reconciliation unchanged (H3)
 ↓
KB sync (PROJECT_STATE: position #6/#7 → COMPLETE; this report status; CHANGELOG)
 ↓
Commit (one revertible commit; revert → legacy forward position identity)
```

**Wave-5 (separate, follows):** the AST/grep closure guard asserts no `InstrumentParser.parse` / direct `Option`/`Future` construction is reachable from the live F&O order-build **or position-build** path except the whitelisted canonical-derivation seams, and that #6's `Position(symbol=)` branch stays unreached. This slice must land before that guard can pass for the position path.

---

## Deliverable summary

### Map of #6
`Position(symbol=…)` ctor, `position_models.py:47` — `instrument or InstrumentParser.parse(symbol or "")`. **Dead on the production path** (no `Position(symbol=)` caller; tracker always passes `instrument=`). Reclassify **MIGRATE → prove-dead carve-out**; subsumed by #7.

### Map of #7
`PositionTracker.get_position`, `position_tracker.py:31` — the sole live position-identity construction (`parse(symbol)` → `Position(instrument=…)`). FLAT identity is **inert** (never consumed); the **open** identity is materialized once at `update_from_fill:152` (copying the parse-built instrument) and consumed via `instrument.multiplier` by margin/PnL/greeks. `get_position` carries **no timestamp** → the correct canonical seam is the **fill** (`fill.timestamp`), not the lookup.

### One migration or two?
**ONE.** #6 has no live behavior to migrate (no-op in isolation) and is subsumed once #7's seam supplies a canonical `instrument=`; #7 mints the live identity at a single fill seam into a single `Position` object. They share source and object — unlike the genuinely-independent restore halves #8/#9. Plan as one slice, one commit: "migrate #7 at the fill seam; fold #6 as prove-dead." The futures-multiplier 1→65 is the one intended (margin/PnL) change, which a single focused commit keeps auditable.

---

**STOP** — review complete. No production code, tests, or KB modified; no commit. Wave 4B implementation (#6/#7 migration), the Wave-5 AST/grep guard, and the G1 closeout audit are **NOT started** — they are the subsequent steps. G1 stays OPEN.
