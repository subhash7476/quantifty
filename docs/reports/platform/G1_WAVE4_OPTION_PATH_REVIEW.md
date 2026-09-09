# G1_WAVE4_OPTION_PATH_REVIEW.md

**Type:** Gate G1 — Migration Target **#4 (Forward Option Path)** review + implementation plan. **Planning only; NO production code, tests, or KB changed in this turn.**
**Date:** 2026-06-10
**Scope (locked):** the **live F&O forward option order-build path** — `ExecutionHandler.process_signal` option branch → `OptionsContractSelector.select` → legacy `Option` → `NormalizedOrder`. Restore (#2, COMPLETE), futures (#1, COMPLETE), and forward position/order construction (#6/#7) are out of scope here.
**Basis (file:line, verified 2026-06-10):** `core/execution/handler.py`, `core/execution/options/selector.py`, `core/execution/futures.py`, `core/execution/canonical_restore.py`, `core/instruments/resolver.py`, `core/instruments/instrument_parser.py`, `tests/execution/test_g1_characterization.py`, `tests/execution/test_selector_resolves.py`. Master DB read-only (`data/instruments/nse_fo_instruments.duckdb`, snapshots 2026-06-08 / 2026-06-09).

**Verdict:** Migration Target #4 is a **DERIVE** wave (per `SOLE_IDENTITY_PATH_REVIEW.md` §2) — the lot is already resolver-sourced; the gap is that the `Option` is *constructed by the selector*, not *derived from a `CanonicalInstrument`*. The migration is **behavior-preserving** (it does not change the lot value, which is already 65). **F4 does NOT have to be closed before the #4 migration commit** — it is a precondition for the option path going **LIVE**, which cannot happen until the (still-absent) F&O entry script exists. **G1 stays OPEN** regardless (#6/#7 + the Wave-5 guard remain).

---

## 1 — Current Flow

```text
SignalEvent  (metadata["execution_mode"]=="option", signal_type != EXIT)
 ↓  ExecutionHandler.process_signal                       handler.py:548
 ↓  OptionsContractSelector().select(                     handler.py:550-556
        underlying       = signal.symbol,        # "NSE_INDEX|Nifty 50"
        underlying_price = current_price,
        direction        = signal.signal_type,   # BUY→CALL / SELL→PUT
        timestamp        = signal.timestamp,
        policy           = signal.metadata["option_policy"])
 ↓  select(): compute expiry/strike/symbol  (master-INDEPENDENT math)   selector.py:85-103
 ↓            resolve_option(...) → CanonicalInstrument  (lot_size ONLY) selector.py:108-113 → resolver.py:97
 ↓            ci.lot_size overrides INDEX_LOT_SIZES; ci then DISCARDED
 ↓  Option(symbol, underlying, expiry, strike, option_type, lot_size)   selector.py:115  ← IDENTITY CREATED HERE
 ↓  NormalizedOrder(instrument=Option, side, quantity, MARKET, …)       handler.py:583-592
 ↓  broker.place_order(order)  → payload symbol = order.symbol          handler.py:610
```

**Forward option ENTRY** (BUY/SELL, non-EXIT) is the only branch that calls the selector. Two structural facts:

- **Symbol is selector-computed, master-independent.** `_build_symbol(short_name, expiry, strike, type)` (`selector.py:103,134-140`) → e.g. `NIFTY16JUN2622500CE`. The master's `tradingsymbol` is **not** read for the payload (the resolver's `display_symbol` is never used) — this is what keeps the broker payload byte-stable and the G1/4C.7 line uncrossed.
- **The CanonicalInstrument is already the lot source but is NOT the identity source.** `select()` reads `ci.lot_size` (`selector.py:113`) then throws the `ci` away and builds the `Option` from its own computed fields (`selector.py:115`). That single direct `Option(...)` is the construction the Wave-5 AST guard will flag.

**Forward option EXIT** takes a *different* path (a latent gap — see §2): an EXIT signal carries the **option symbol** (selector docstring `selector.py:64-67`), `execution_mode=="option" ∧ signal_type != EXIT` is **False**, so it falls to the `else` branch (`handler.py:557-560`) → `resolve_future` (regex miss) → `InstrumentParser.parse(option_symbol)` → `Option(lot_size=1)` (`instrument_parser.py:33-41`).

---

## 2 — Identity Ownership

**Q: Where is Option identity currently created on the LIVE F&O forward path?**

| Site | File:line | When (forward path) | Object | Lot source | Resolver-sourced? |
|---|---|---|---|---|---|
| **O1 — selector** | `selector.py:115` | option **ENTRY** (BUY/SELL non-EXIT) | `Option(...)` | `ci.lot_size` (master) → else `INDEX_LOT_SIZES` (75) | **Partial** — lot only; the `Option` itself is selector-built, not CI-derived |
| **O2 — parser (EXIT)** | `instrument_parser.py:33` via `handler.py:560` | option **EXIT** (option symbol → `else` branch) | `Option(lot_size=1)` | **hardcoded 1** | **No** — bare `InstrumentParser.parse`, resolver never consulted |

**`Option(...)` construction sites repo-wide (grep `Option(`):**
- `selector.py:115` — **O1, forward ENTRY (in scope).**
- `instrument_parser.py:33` — **O2, forward EXIT + every other `parse` caller (in scope for the EXIT leg).**
- `canonical_restore.py:61` — restore #2 (COMPLETE, **out of scope**).
- `core/instruments/option.py:13` — the class definition (not a construction site).

**`InstrumentParser.parse(...)` call sites on the forward path (grep):**
- `handler.py:560` — `process_signal` `else` branch. **Reached by option EXIT** (option symbol matches the parser's OPTION_REGEX → `Option` lot 1) and by equity/non-future. **In scope for the option EXIT leg.**
- `handler.py:668` — `process_group_signal` batch build (#2). **No option-mode branch** — a batched option signal is `parse`-built, never routed to the selector. Documented scope boundary (see below), tracked under #2, not #4.
- `handler.py:767` — `_check_greek_limits` (#3). For an option signal `signal.symbol` is the **underlying** (`NSE_INDEX|Nifty 50`) → `parse` → `Equity`; transient, never leaves the site (#3 carve-out, 4C.6 greeks dispatch on `asset_class`).

**`resolve_option` (the CI source) call sites:** `selector.py:110` (forward, O1) and `canonical_restore.py:57` (restore #2). Both read the `ci` for economic facts and discard it — `CanonicalInstrument` never enters `NormalizedOrder` (the G1/4C.7 boundary holds today).

**Conclusion:** forward option identity is owned at **two** sites — O1 (`selector.py:115`, ENTRY, lot-resolver-sourced) and O2 (`instrument_parser.py:33`, EXIT, lot=1, resolver-blind). The #4 migration must close **both** to satisfy Section-6 criterion #2 ("no live F&O order path constructs `Option` directly from a symbol string bypassing the resolver").

---

## 3 — Canonical Insertion Point

**Where `CanonicalInstrument → legacy Option` should replace the current logic:**

**O1 — inside `OptionsContractSelector.select()` (`selector.py:105-123`).** Replace "resolve `ci.lot_size` only, then build the `Option` from computed fields" with "resolve a `CanonicalInstrument` and **derive** the legacy `Option` from it." Constraints (the DERIVE contract):

1. **Symbol stays selector-computed** (`_build_symbol`, `selector.py:103`) — the payload byte is preserved; never substitute `ci.display_symbol`/master `tradingsymbol` (that is a payload change → 4C.7). The CI is looked up *by* the selector's computed `expiry`/`strike`, so the derived `Option`'s expiry/strike already equal the computed ones — derivation is consistent by construction.
2. **Master-absent determinism (ADR-003).** When `resolve_option(...) → None` (master absent, or contract not carried), still derive a valid `Option` from the computed fields with the `INDEX_LOT_SIZES` fallback lot — exactly as today. The returned **type never flips on DB presence** (mirrors `resolve_future`'s master-absent branch, `futures.py:52-54`). This is the load-bearing parity property the Section-4 net must pin.
3. **`policy["lot_size_override"]` still wins** (`selector.py:87-88,108`) — the override short-circuits resolution today; preserve that precedence.
4. **CanonicalInstrument stays internal** — read `lot_size` (and, if derived structurally, `expiry`/`strike`), then discard. No `ci` on `NormalizedOrder`, persistence, or the broker payload.

The cleanest shape mirrors the existing `core/execution/futures.resolve_future` / `canonical_restore.canonicalize_symbol` pattern: a single canonical-derivation step the Wave-5 AST guard can whitelist, so the only `Option(...)` on the live forward path is that one derivation point.

**O2 — the option EXIT leg (`handler.py:557-560`).** Route an option-shaped EXIT symbol through the canonical derivation (the existing `canonical_restore.canonicalize_symbol` already does exactly "symbol → canonical-derived `Option`" and is the natural reuse) **before** falling back to `InstrumentParser.parse`. Note: for EXIT, `quantity` comes from `current_position.quantity` (`handler.py:568`), so the lot=1 drift does **not** mis-size the exit today — but the **identity** is legacy, so O2 is a genuine Section-6 criterion-#2 gap that must be closed for the guard to pass. (Decide during Wave 4 whether O2 is folded into the #4 commit or tracked as its own slice; it is small and shares the restore primitive.)

**No code changes in this document.**

---

## 4 — Characterization Coverage

### Existing tests protecting #4

| Test | File | Pins |
|---|---|---|
| `test_build_order_option_via_selector_branch` | `test_g1_characterization.py:172-189` | Forward option ENTRY order build at the **handler** level: `symbol==NIFTY16JUN2622500CE`, `lot_size==65` (master-resolved), `instrument_type==OPTION`, `side==BUY`, `quantity==75`, `order_type==MARKET`. Hardcoded literals (genuine byte-for-byte tripwire — a self-referential `select()` re-call would move in lockstep). |
| `test_falls_back_to_hardcoded_lot_when_master_absent` | `test_selector_resolves.py:24-29` | Selector unit: master absent → lot 75 (`INDEX_LOT_SIZES`). |
| `test_uses_resolver_lot_size_when_master_present` | `test_selector_resolves.py:32-44` | Selector unit: master present → master lot overrides 75. |
| `test_symbol_strike_and_type_unchanged_by_resolver` | `test_selector_resolves.py:47-55` | Selector unit: symbol/strike/expiry/type unchanged when lot source moves. |
| `test_policy_override_beats_resolver` | `test_selector_resolves.py:58-70` | Selector unit: `lot_size_override` precedence. |
| `test_default_selector_preserves_legacy_behavior` | `test_selector_resolves.py:73-79` | Selector unit: no-resolver default = legacy lot 75. |

**Assessment:** the *lot-source* axis is well covered (5 selector unit tests). The *handler-level order build* has **one** characterization (`test_build_order_option_via_selector_branch`), and it exercises only **NIFTY / BUY→CALL / master-present**.

### Missing tests required before migration (the Wave-4 safety net)

The #4 migration restructures O1 (and touches O2). Per the F-PARSE-1 discipline (pin reality, identical assertions green before and after), the following must exist and be **green on current code** before any migration edit:

1. **M1 — handler-level forward option, master ABSENT.** `process_signal` option ENTRY with the resolver pointed at an absent DB → must still build an `Option` (ADR-003), symbol byte-identical, lot = `INDEX_LOT_SIZES` fallback. *(Only the selector unit pins master-absent today; nothing pins it through the handler order-build — the exact surface the migration edits.)*
2. **M2 — BANKNIFTY forward option.** Different strike step (100), lot (30), Wednesday expiry. Pins the non-NIFTY underlying the single NIFTY test leaves uncovered.
3. **M3 — SHORT-side option (SELL→PUT).** Only BUY→CALL is pinned; the option_type branch (`selector.py:97`) is untested at the handler level.
4. **M4 — option EXIT identity (O2).** Pin the current behavior: an option-symbol EXIT → `else` branch → `parse` → `Option(lot_size==1)`, `instrument_type==OPTION`, `quantity==current_position.quantity`. This is the characterization that makes the O2 migration provably behavior-preserving (and documents that EXIT sizing is position-sourced, lot-independent).
5. **M5 — CanonicalInstrument containment tripwire.** Assert the forward option `NormalizedOrder.instrument` is a legacy `Option` (not a `CanonicalInstrument`) and that no `instrument_key`/`ci.product` is read into the payload — the G1/4C.7 boundary guard for the forward path (parallel to the restore-path `D — broker boundary` check).
6. **M6 — persist + restore round-trip for a forward-built option order.** The Section-4 persist/restore characterizations currently use an **equity** order; add an option-order round-trip so the migration's persistence/restore parity is pinned for the option payload specifically.

**Gate:** no #4 migration edit merges unless M1–M6 (plus the existing six) are green before and after.

---

## 5 — F4 Dependency

**Current canonical lot values (read-only query, latest snapshot 2026-06-09, `data/instruments/nse_fo_instruments.duckdb`):**

```text
NIFTY      lot_size = 65   (distinct across CE/PE/FUT)
BANKNIFTY  lot_size = 30   (distinct across CE/PE/FUT)
```

These match the F4 finding exactly (master-raw, unscaled, correct unit). **No value changed by this review.**

**Is exchange verification still required before implementation?**

- **For the #4 migration COMMIT — NO.** The migration is **behavior-preserving**: it changes *where* the `Option` is derived (CI-as-source vs selector-built), **not** the lot value. The selector already sizes NIFTY options at **65** today (active-on-materialization, `selector.py:108-113`; F4 finding "MM.5 silently flipped 75→65"). The characterization `test_build_order_option_via_selector_branch` already pins **65** as current reality. A behavior-preserving refactor keeps 65 → the characterization stays green → no exchange check is needed to *land the refactor*.
- **For the option path going LIVE — YES.** Whether **65/30 is correct** is orthogonal to the canonical-derivation refactor and is a **hard precondition for the live option path** (F4, `PROJECT_STATE.md` Open Findings; `SOLE_IDENTITY_PATH_REVIEW.md` §5). But the option path **cannot go live yet** — there is no F&O entry script that constructs a live `LoopDriver` (MM.7 blocker #4; `LoopDriver` is built only in `tests/`). So F4 verification is **not on the Wave-4 critical path**; it gates *enabling* the path, which is downstream.

**Net: F4 does NOT have to be closed before Wave 4 is implemented. It must be closed before the option path is enabled live** (identical posture to the restore path, which "preserves whatever the master holds" — `G1_WAVE3_RESTORE_CLOSEOUT.md` §E). Do not change 65/30 until exchange-verified; the migration neither needs nor performs that change.

---

## 6 — Migration Plan (recommended Wave 4 sequence)

```text
Characterization (M1–M6, green on current code)
 ↓
Migration  O1: selector.select() derives Option from CanonicalInstrument
           O2: option-EXIT leg routes symbol via canonical_restore.canonicalize_symbol
 ↓
Expected failures  (none if truly behavior-preserving — see below)
 ↓
Assertion updates  (none expected; if any, only an intended value correction, justified)
 ↓
KB sync  (PROJECT_STATE Completed entry + this report's status + CHANGELOG)
 ↓
Commit  (independently revertible; characterization green before & after)
```

**Step detail:**

1. **Characterization (M1–M6).** Land the six missing tests **green on current code** (they encode today's reality: lot 65 NIFTY / 30 BANKNIFTY / lot-1 EXIT / legacy-Option containment / option round-trip). Zero production change in this step.
2. **Migrate O1.** Restructure `select()` to resolve a `CanonicalInstrument` and derive the legacy `Option` from it (symbol preserved, lot/expiry/strike from the CI, `INDEX_LOT_SIZES` + override fallbacks intact, master-absent still derives — ADR-003). Single-file edit to `selector.py`; the handler call site (`handler.py:550`) is unchanged.
3. **Migrate O2.** In the `else` branch (`handler.py:557-560`), try `canonicalize_symbol(signal.symbol, signal.timestamp)` before `InstrumentParser.parse` so an option-symbol EXIT derives a canonical `Option`. (May be split into its own revertible commit.)
4. **Expected failures.** If the migration is behavior-preserving, **all** characterizations stay green — including `test_build_order_option_via_selector_branch` (lot 65 unchanged) and M4 (EXIT). *The expected-failure count for #4 is **zero** — unlike #1, which intentionally flipped EQUITY→FUTURE. A red here means the refactor changed a byte and must be re-examined, not re-asserted.* The one *possible* intended change: M4's EXIT lot 1 → master lot if O2 derivation is applied; if so, confirm EXIT `quantity` is still `current_position.quantity` (lot-independent) so the broker payload is unaffected, and update only that assertion with justification.
5. **Assertion updates.** None expected (contrast Wave 2 #1). Any update must be an explicitly-justified value correction with the payload bytes proven unchanged, not a lockstep move.
6. **KB sync.** Update `PROJECT_STATE.md` (new Completed entry, #4 → COMPLETE), this report's status line, and the platform changelog — per the KB-sync discipline. State plainly that the option path remains **not-live** (F4 + F&O entry script outstanding).
7. **Commit.** One revertible commit (two if O2 is split). Revert = back to selector-built `Option` / `parse`-built EXIT; characterization parity proves the rollback is clean.

**Wave-5 (separate, not part of #4):** the AST/grep closure guard asserts no `InstrumentParser.parse` / direct `Option(...)` is reachable from the live F&O order-build path except the whitelisted canonical-derivation point. #4 must land before that guard can pass for the option path.

---

## Deliverable summary

### 1. Findings summary
- The forward option path has **two** identity-creation sites: **O1** (`selector.py:115`, ENTRY — lot already resolver-sourced, but the `Option` is selector-built not CI-derived) and **O2** (`instrument_parser.py:33` via `handler.py:560`, EXIT — bare `parse`, lot=1, resolver-blind).
- #4 is a **DERIVE** wave and is **behavior-preserving** (lot is already 65; the migration changes the derivation locus, not the value).
- The selector's **symbol is master-independent** (computed, not `ci.display_symbol`) — this is what keeps the payload byte-stable; the migration must preserve it.
- The batch/group path (`handler.py:668`, #2) has **no option branch** — a documented scope boundary, not a #4 site.

### 2. Risk ranking
1. **O1 master-absent determinism (HIGH).** The riskiest property — the derived type/identity must not flip on DB presence (ADR-003). Mitigated by M1 (handler-level master-absent characterization, currently missing).
2. **O2 EXIT identity (MED).** A real Section-6 criterion-#2 gap, but EXIT sizing is position-sourced (lot-independent), so it is identity-only, not a sizing risk today. Mitigated by M4.
3. **Payload byte drift (MED).** Any accidental use of `ci.display_symbol`/master `tradingsymbol` crosses into 4C.7. Mitigated by M5 + the existing byte-for-byte literal in `test_build_order_option_via_selector_branch`.
4. **Coverage breadth (LOW–MED).** Only NIFTY/BUY/master-present is pinned at the handler level; BANKNIFTY/SELL/master-absent are unpinned (M1–M3).

### 3. Missing characterization requirements
**M1** handler-level master-absent option build · **M2** BANKNIFTY option · **M3** SELL→PUT option · **M4** option EXIT identity (lot 1, position-sourced qty) · **M5** CanonicalInstrument containment tripwire · **M6** option-order persist+restore round-trip. All must be green on current code before any migration edit.

### 4. Recommended Wave 4 implementation plan
Characterization (M1–M6 green) → migrate O1 (selector derives Option from CI) → migrate O2 (EXIT via `canonicalize_symbol`) → expect **zero** failures (behavior-preserving) → no assertion updates expected → KB sync → revertible commit(s). Wave-5 AST guard is separate and follows.

### 5. Whether F4 must be closed first
**No — not for the #4 migration commit.** The migration is behavior-preserving and keeps the current master lot (65/30), already pinned green. **F4 verification is a precondition for enabling the option path LIVE**, which is independently blocked by the absent F&O entry script (MM.7 blocker #4). Verify 65/30 against exchange circulars before the path goes live; do not change the values to land Wave 4.

---

**STOP** — review complete. No production code, tests, or KB modified; no commits. Wave 4 implementation, #6/#7, and the Wave-5 guard are NOT started.
