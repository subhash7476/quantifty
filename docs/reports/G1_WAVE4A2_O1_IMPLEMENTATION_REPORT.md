# G1_WAVE4A2_O1_IMPLEMENTATION_REPORT.md

**Type:** Gate G1 — Wave 4A.2 **O1 (forward option ENTRY) migration**. Single-file production change + report + commit. **O2 EXIT path NOT touched; #6/#7, persistence, broker payloads, InstrumentParser, handler.py, the Wave-5 guard NOT touched.**
**Date:** 2026-06-11
**Scope (locked):** migrate **O1 only** — `OptionsContractSelector.select()` in `core/execution/options/selector.py`. Convert "resolve `CanonicalInstrument`, read `ci.lot_size`, discard the CI, then build the `Option` from computed fields" into "**derive** the legacy `Option` from the resolved `CanonicalInstrument`." Behavior-preserving DERIVE migration per `docs/reports/G1_WAVE4_OPTION_PATH_REVIEW.md` §3/§6 and `docs/reports/G1_WAVE4A1_CHARACTERIZATION_REPORT.md`.

**Result:** `pytest -q` → **415 passed, 0 failing** (identical to the Wave-4A.1 baseline). **Zero assertion updates** (expected-failure count for #4 is zero — behavior-preserving). O2 EXIT path remains OPEN; G1 stays OPEN.

---

## 1 — Files changed

| File | Change | LOC |
|---|---|---|
| `core/execution/options/selector.py` | O1 migration: `select()` now derives the legacy `Option` from the resolved `CanonicalInstrument` (CI-present branch) with a separate ADR-003 master-absent/override fallback derivation. | +23 / −9 (1 file) |
| `docs/reports/G1_WAVE4A2_O1_IMPLEMENTATION_REPORT.md` | This report. | new |

`git diff --stat` confirms **one** production file changed. `handler.py` (call site `handler.py:550`), `instrument_parser.py`, `canonical_restore.py`, persistence, and the broker bridge are **untouched**.

---

## 2 — Derivation mechanism

**Before (O1 = "read lot only, discard CI"):** a single `lot_size` was seeded from the override / `INDEX_LOT_SIZES` table; if the master resolved a CI, `lot_size` was overwritten with `ci.lot_size`; the CI was then discarded and a single `Option(...)` was built at the bottom from the computed fields. The CI was a *lot source*, not the *identity source*.

**After (O1 = "derive Option from CanonicalInstrument"):** the construction is split to make the CI the identity source, mirroring the established `core.execution.futures.resolve_future` / `canonical_restore._resolve_option` two-return shape:

```text
symbol = _build_symbol(short_name, expiry, strike, option_type)   # UNCHANGED — selector-computed

if override is None:
    ci = (self._resolver or InstrumentResolver()).resolve_option(
        underlying, expiry, float(strike), option_type, as_of=from_date)
    if ci is not None:
        return Option(symbol, underlying, expiry, float(strike),    # DERIVED FROM CI
                      option_type, lot_size=ci.lot_size, multiplier=1.0)

# master absent / contract not carried / caller override (ADR-003 fallback)
return Option(symbol, underlying, expiry, float(strike), option_type,
              lot_size=override or INDEX_LOT_SIZES.get(underlying, 50), multiplier=1.0)
```

**The DERIVE contract (review §3) is honoured exactly:**

1. **Symbol stays selector-computed.** `symbol = self._build_symbol(...)` (`selector.py:102`) is the sole symbol source in **both** return branches. `ci.display_symbol` / the master `tradingsymbol` is never read (the only textual occurrence of `display_symbol` in the file is the explanatory comment).
2. **Master-absent determinism (ADR-003).** When `resolve_option(...) → None`, control falls through to the fallback `return`, which still derives a valid `Option` with the `INDEX_LOT_SIZES` fallback lot. The returned **type never flips on DB presence** — identical to `resolve_future`'s master-absent branch.
3. **`policy["lot_size_override"]` precedence preserved.** When `override` is set, the `if override is None` guard is False, resolution is **skipped entirely** (no resolver call), and the fallback `return` uses `override` as the lot — byte-identical to the prior `override or …` precedence.
4. **CanonicalInstrument stays internal.** Only `ci.lot_size` is read from the CI; the CI object itself is never returned, never placed on `NormalizedOrder`, never persisted, never sent to the broker.

**Why this is a genuine DERIVE and not a no-op comment swap:** the `Option` for the master-present case is now constructed *inside the CI-present branch as the product of the resolved CI*, not after the CI is discarded. This is the single canonical-derivation point the Wave-5 AST guard can whitelist (the fallback `return` is the ADR-003 master-absent twin, exactly as `resolve_future` has two `Future(...)` sites).

---

## 3 — Proof: symbol unchanged

- **Mechanism:** `symbol` is computed once by `self._build_symbol(short_name, expiry, strike, option_type)` (`selector.py:102`) and passed verbatim to whichever `Option(...)` return fires. No branch substitutes `ci.display_symbol`.
- **Static check:** `grep -n display_symbol core/execution/options/selector.py` → the only hit is the comment on line 107; `_build_symbol` remains defined (line 148) and called (line 102).
- **Behavioral pins (green before AND after, zero assertion change):**
  - M1 (master absent) `order.symbol == "NIFTY16JUN2622500CE"` — byte-identical to the master-present case.
  - M2 (BANKNIFTY) `order.symbol == "BANKNIFTY17JUN2652000CE"`.
  - M3 (SELL→PUT) `order.symbol == "NIFTY16JUN2622500PE"` (CE→PE suffix flip).
  - `test_symbol_strike_and_type_unchanged_by_resolver` — symbol/strike/expiry/type invariant across lot-source moves.
  - `test_build_order_option_via_selector_branch` (the byte-for-byte handler tripwire) — `symbol == "NIFTY16JUN2622500CE"`, still green.

---

## 4 — Proof: broker payload unchanged

- **M5 containment tripwire** (green, unchanged): `NormalizedOrder.instrument` is a legacy `Option` and **not** a `CanonicalInstrument`; no canonical-only attribute (`instrument_key`, `product`, `asset_class`) is present on the payload object; `order.symbol == "NIFTY16JUN2622500CE"` (selector-computed, not a master `display_symbol`); the spy broker received the **same** instrument object (`broker.received[0].instrument is order.instrument`).
- **Lot byte across all axes** (the only economic field sourced from the CI), all unchanged:
  - master present NIFTY → `lot_size == 65` (M3 / `test_build_order_option_via_selector_branch`).
  - master absent NIFTY → `lot_size == 75` (M1, `INDEX_LOT_SIZES` fallback).
  - BANKNIFTY default (weekly unresolved) → `lot_size == 35` (M2, fallback).
  - override set → `lot_size == 25` (`test_policy_override_beats_resolver`).
  - default selector, no resolver → `lot_size == 75` (`test_default_selector_preserves_legacy_behavior`).
- **Symbol/side/qty/order_type** on the payload (M1–M3, M5) all unchanged. The broker `place_order` receives the identical object — proven by the spy assertions.

---

## 5 — Proof: persistence unchanged

- **M6 persist + restore round-trip** (green, unchanged): Handler A persists the forward option order; the `orders` row carries `symbol == "NIFTY16JUN2622500CE"`, `side == "BUY"`, `quantity == 75.0`, `order_type == "MARKET"`. Handler B (`load_db_state=True`) restores from the same ledger: restored `symbol`/`side`/`quantity`/`instrument_type` match verbatim; `position_tracker.net_quantity("NIFTY16JUN2622500CE") == 75.0` rebuilt from the replayed BUY fill.
- The migration touched neither the persistence layer nor the order repository; only the in-memory `Option` derivation locus moved, and its emitted fields are byte-identical, so the persisted row is unchanged.

---

## 6 — Test results

```text
pytest tests/execution/test_g1_wave4a1_option_characterization.py -q   ->  6 passed
pytest tests/execution -q                                              -> 51 passed
pytest -q                                                              -> 415 passed, 0 failing
```

Baseline (Wave-4A.1, pre-migration): 415 passed, 0 failing. Post-migration: **415 passed, 0 failing**. **Zero** expected failures, **zero** assertion updates — confirming the DERIVE migration is byte-for-byte behavior-preserving, as §6 predicted (a red here would have signalled a changed byte to re-examine, not re-assert).

---

## Stop

O1 migration complete, full suite green (415/0), report written, commit created. **NOT started:** O2 EXIT path (`handler.py:557-560`), #6/#7, the Wave-5 AST closure guard. G1 stays OPEN (O2 EXIT + #6/#7 + Wave-5 guard remain). The option path remains **not-live** (F4 lot verification + the absent F&O entry script are downstream preconditions, unchanged by this wave).
