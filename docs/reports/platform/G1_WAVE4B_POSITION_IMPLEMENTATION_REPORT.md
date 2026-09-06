# G1_WAVE4B_POSITION_IMPLEMENTATION_REPORT.md

**Type:** Gate G1 — Wave 4B **Forward Position Identity migration (#6/#7)**. Characterization net (P1–P7) + single-seam production change + justified intended-flip updates + report + commit.
**Date:** 2026-06-11
**Scope (locked):** the live F&O forward **position** identity — Migration Targets **#6** (`Position(symbol=…)` ctor) and **#7** (`PositionTracker.get_position`), per `docs/reports/G1_WAVE4B_POSITION_IDENTITY_REVIEW.md`. Implemented as **ONE migration** (the review's verdict): canonicalize the open position at the live fill seam (#7); #6 folded as a prove-dead carve-out. **`update_from_fill`, `position_models.py`, persistence, the broker payload, #8/#9, and the Wave-5 guard are NOT touched.**

**Result:** `pytest -q` → **422 passed, 0 failing**. The P1–P7 net was green on current code first; the #7 migration then flipped **exactly three intended axes** (futures position `Equity→Future` / multiplier `×65`; option position lot `1→65`; forward↔restore drift→parity) plus two forward-note assertions in the restore-characterization suite. Every other assertion stayed green. **G1 stays OPEN** (Wave-5 guard + closeout remain).

---

## 1 — Files changed

| File | Change | LOC |
|---|---|---|
| `core/execution/handler.py` | **#7 migration:** in `_handle_broker_fill` (the LIVE-only fill seam), after `update_from_fill`, canonicalize the position's identity via `canonicalize_symbol(fill.symbol, fill.timestamp)` → `position_tracker.replace_instrument`. | +15 |
| `tests/execution/test_g1_wave4b_position_characterization.py` | **new** — P1–P7 forward position characterization (7 tests). | new |
| `tests/execution/test_g1_restore_characterization.py` | Updated two **forward-note** assertions to the post-#7 reality (futures forward position `Future`; option forward position lot `65`). Restore-at-construction assertions (Option B) unchanged. | ±38 |
| `docs/reports/G1_WAVE4B_POSITION_IMPLEMENTATION_REPORT.md` | This report. | new |

**Production diff is one file (`handler.py`, +15).** `position_tracker.update_from_fill`, `position_models.py` (#6), the ledger schema, and the broker bridge are untouched.

---

## 2 — Migration mechanism (and why #6 needed no edit)

**#7 — the live fill seam.** The open position's identity is materialized in `update_from_fill` by copying the FLAT `get_position` instrument (parse-built: futures→`Equity` mult 1, option→`Option` lot 1). The migration leaves that copy alone and **upgrades the just-materialized position** at the live fill seam:

```text
_handle_broker_fill(fill):
    realized_pnl = position_tracker.update_from_fill(fill)
    derived = canonicalize_symbol(fill.symbol, fill.timestamp)   # future-then-option
    if derived is not None:
        position_tracker.replace_instrument(fill.symbol, derived)
    pnl_tracker.update(fill, realized_pnl)
```

Four properties make this the correct seam (review §3):

1. **It carries a timestamp.** `get_position(symbol)` has none; `canonicalize_symbol` needs `as_of`. `fill.timestamp` supplies it — correct under live and replay clocks.
2. **It is LIVE-only → Option B preserved.** Restore replay canonicalizes nothing at construction: `_replay_state` calls `position_tracker.update_from_fill(fill)` **directly** (`handler.py:234`), never `_handle_broker_fill`. So restored positions stay legacy at construction (ADR-003 — no env/restart type flip); their canonical upgrade remains the separate post-gate `canonicalize_restored_positions` pass. `update_from_fill` is deliberately **not** edited (it is the shared seam).
3. **It reuses the restore primitives** — `canonicalize_symbol` + `replace_instrument` (built for #7-as-restored). No second derivation mechanism, so a forward-built position and its restored twin are byte-identical (P5 parity, §4).
4. **Symbol key + containment preserved.** The derived legacy `Future`/`Option` carries the same `.symbol`, so the `_positions` key, persistence, and symbol-keyed reconciliation (H3) are unaffected; `replace_instrument` preserves side/quantity/avg_price. The `CanonicalInstrument` stays internal (G1 / 4C.7). Equity / unresolved → `canonicalize_symbol` returns `None` → position left legacy (carve-out).

**#6 — no edit.** `Position(symbol=…)`'s `parse` branch has no production caller (P6 grep-clean; the tracker always builds `Position(instrument=…)`), so it is dead on the live path and subsumed once #7's seam supplies a canonical `instrument=`. Folding it as a prove-dead carve-out (not migrating it) is the review's verdict; P6 is the standing guard that it stays unreached.

---

## 3 — Characterization net (P1–P7) and the before/after

All seven were **green on current code** before the production change, then the migration produced exactly the intended deltas:

| Test | Pinned (pre) | Post-migration | Class |
|---|---|---|---|
| **P1** option position | `Option`, **lot 1**, mult 1.0 | **lot 65**, mult 1.0 | intended (identity-only) |
| **P2** futures position + margin | **`Equity`**, **mult 1.0**, exposure ×1 | **`Future`**, **mult 65.0**, exposure **×65** | **intended (margin/PnL change)** |
| **P3** option margin/PnL | exposure 75·22500·1; unreal 100·75·1 | **unchanged** | behavior-preserving (proof) |
| **P4** FLAT inert + get_position | qty 0; `get_position`→`Equity` (futures) | **unchanged** | behavior-preserving |
| **P5** forward vs restored futures | **drift** (Equity vs Future) | **parity** (both `Future`, mult 65) | intended (closes restart drift) |
| **P6** #6 prove-dead | no `Position(symbol=)` caller in `core/` | **unchanged** | structural guard |
| **P7** equity position | `Equity`, mult 1.0, exposure ×1 | **unchanged** | carve-out (behavior-preserving) |

**The load-bearing distinction (P3 vs P2): the consumed field is `multiplier`, not `lot_size`.** An option's derived `multiplier` stays `1.0`, so P3 (margin/PnL) is **byte-identical** — the option half is an identity-only correction (lot 1→65, consumed by nothing on a position). A future's derived `multiplier` is `65.0` (`resolve_future` sets `multiplier=ci.lot_size`), so P2's margin/exposure changes **×65** — the **one intended behavior change** of Wave 4B (futures *do* carry a lot multiplier; the prior `Equity` mult-1 was the H1 defect). It adopts the master's current value; F4 exchange-verification gates going **live**, not this refactor.

---

## 4 — Proofs

- **Symbol / broker payload unchanged.** The derived instrument keeps `.symbol` (P1/P2/P5/P7 assert the position symbol byte-identical); `replace_instrument` does not touch quantity/side/avg_price; reconciliation is symbol-keyed and identity-blind (H3, unaffected). No `ci.display_symbol` is read.
- **Persistence unchanged.** The ledger persists only `symbol` (no instrument_type/lot column — the restore-suite schema tripwire stays green). The migration changes an **in-memory** identity at the fill seam; nothing new is persisted. The restore round-trip is unaffected.
- **Option B / ADR-003 preserved.** `test_restore_future_position_rebuilt_as_equity` / `test_restore_option_position_lot_is_one` still assert the **restored-at-construction** position is legacy (`Equity` / lot 1) — green — because `update_from_fill` (the restore-replay seam) is untouched. Only their **forward-note** assertions flipped (forward position now `Future` / lot 65). The post-gate `canonicalize_restored_positions` pass (Wave 3 #7-as-restored) still owns the restored upgrade.
- **Forward == restore parity (P5).** A forward-built futures position and its restored+canonicalized twin now share type and multiplier (both `Future`, 65) — closing the Wave-3A position-level drift with no restart divergence, because both derive through the same `canonicalize_symbol` primitive.
- **#6 dead (P6).** No `core/` module constructs `Position(symbol=…)` (definition module excluded); the live path always passes `instrument=`.

---

## 5 — Test results

```text
pytest tests/execution/test_g1_wave4b_position_characterization.py -q  -> 7 passed
pytest tests/execution -q                                             -> 58 passed
pytest -q                                                             -> 422 passed, 0 failing
```

Pre-migration baseline (P1–P7 added, green on current code): 422 passed. Mid-migration: 3 failures (P1 lot, P2 futures, P5 parity) + 2 restore-suite forward-note failures — all five the predicted intended changes. Post-update: **422 passed, 0 failing**. No unintended test moved.

---

## Stop

Wave 4B (#6/#7 forward position identity) complete, full suite green (422/0), report written, commit created. Both forward identity layers now derive from the canonical master — **orders** (O1 ENTRY + O2 EXIT) and **positions** (#7 at the fill seam) — with #6 a documented prove-dead carve-out. **NOT started (the next steps):** the Wave-5 AST/grep closure guard and the G1 closeout audit. `update_from_fill`, `position_models.py`, persistence, #8/#9, and the broker bridge are untouched. **G1 stays OPEN.** The option/futures path remains **not-live** (F4 verification + the absent F&O entry script are downstream).
