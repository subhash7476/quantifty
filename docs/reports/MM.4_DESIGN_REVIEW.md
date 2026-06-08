# MM.4 Design Review — Instrument Master Readiness Startup Gate

**Type:** Design review — **NO CODE. NO IMPLEMENTATION.** A critique of the MM.4 design against the committed MM.1–MM.3 primitives and the existing runtime architecture.
**Date:** 2026-06-08
**Reviewer basis (file:line, current code):** `core/runtime/driver.py:326` (`_run_startup_gate`), `:351` (`_reconcile_ledger`), `:410` (LIVE-requires-handler), `core/runtime/config.py` (`DriverConfig`, `Mode`), `core/runtime/event_journal.py:52` (`EventType`), `:76` (severity map), `core/alerts/alerter.py` (`alerter.critical/warning`), `core/instruments/resolver.py:122` (`latest_snapshot_date`), `core/instruments/master_freshness.py` (`expected_snapshot_date`), `tests/runtime/test_driver_startup_gate.py`.
**Spec under review:** `docs/reports/MASTER_MATERIALIZATION_POLICY.md` §3–§9.
**Committed foundation:** `f8b26cd` (MM.1–MM.3): `resolver.latest_snapshot_date()` + `master_freshness.expected_snapshot_date()` + tests. **Date primitives only — no coverage primitive exists yet.**

---

## 0. Recommendation (headline)

**Conditionally ready to implement, with one mandatory scope correction.**

The gate's *placement, ownership, scope rule, alerting, and replay behavior* are all well-defined by policy §4–§6 and map cleanly onto the existing `_run_startup_gate()` contract. MM.4 can be wired with low architectural risk.

**But MM.4 cannot be built on the MM.1–MM.3 primitives alone without shipping false assurance.** Policy §4 makes **coverage the hard gate and date only an early-warning proxy**. The committed primitives compare *dates* only. A date-only gate **passes a master that is dated-today but contains zero OPTION rows** (failure modes #4/#7) — precisely the schema-shift risk the policy was written to catch. Therefore MM.4 must either (a) include a coverage primitive, or (b) be explicitly split MM.4a (date+absence gate) / MM.4b (coverage), with MM.4a documented as partial. **Recommendation: include coverage in MM.4** (option a) — a date-only live gate that green-lights an empty master is arguably worse than no gate, because it manufactures confidence.

Two conflicts between your own documents must be resolved before coding (see §1, §4).

---

## 1. Exact insertion point

**Recommendation: run the master-readiness check AFTER `RECOVERY_COMPLETED` and BEFORE `_reconcile_ledger()`, inside `_run_startup_gate()`.**

Concrete sequence in `_run_startup_gate()` (driver.py:337–349):

```
enter_recovery()                      # STARTUP -> RECOVERY
RECOVERY_STARTED
RECOVERY_COMPLETED                     # ledger reused (ADR-001), never re-restored
>>> MASTER READINESS CHECK (MM.4)  <<< # NEW: identity trustworthy before position-matching
_reconcile_ledger()                    # may abort_startup() on divergence
start()                                # -> RUNNING
```

**Justification:**
- Policy §5 is explicit: *"the master check runs **before** reconciliation (identity must be trustworthy before positions are matched against it)."* Reconciliation resolves broker positions through canonical instrument identity; if the master is absent/stale/wrong, that resolution is unreliable, so reconciliation would be matching the ledger against bad identity. Validate identity first.
- It is **behavior-neutral today**: LIVE reconciliation is currently vacuous (broker-book source deferred, Planned #6 — `test_live_with_handler_no_source_is_vacuous_pass`). Ordering only *matters* once reconciliation gains teeth, so adopting the correct order now costs nothing and is right when it does.
- Recovery must precede it (recovery is a pure ledger-reuse step needing no master); RUNNING must follow it (the check is a precondition of trading).

> ⚠️ **CONFLICT TO RESOLVE — your two documents disagree.** The *Ownership* diagram in this review request orders it `RECOVERY → RECONCILIATION → MASTER READINESS → RUNNING` (readiness **after** reconciliation). `MASTER_MATERIALIZATION_POLICY.md §5` orders it **before** reconciliation. **This review sides with §5 (before).** If the request diagram is authoritative instead, say so and the rationale above is the cost. They cannot both stand.

---

## 2. F&O scope detection

**Recommendation: derive scope from `config.symbols` by broker-segment prefix — `key.split("|", 1)[0] in {"NSE_FO", "MCX_FO"}` — via one small pure helper. Enforce the gate only when `config.is_live AND has_derivatives(config.symbols)`.**

**Current ownership path (evidence):**
- `DriverConfig` (config.py) carries **no F&O / asset-class field**. The only instrument information the runtime owns is `symbols: List[str]` and `mode: Mode` (LIVE/REPLAY). There is no `derivatives_enabled` flag today. *(Do not assume one exists — it does not.)*
- Instrument keys are `SEGMENT|…` broker keys. Segments ingested are `NSE_FO, MCX_FO, NSE_EQ, NSE_INDEX` (policy §1; `fetch_instrument_master.py:43`). A **tradable derivative** is therefore a key whose segment is `NSE_FO` or `MCX_FO`. `NSE_INDEX|…` is a reference underlying (`CanonicalInstrument.tradable` is False for INDEX, canonical.py:91), and `NSE_EQ|…` is equity — neither gates.
- The driver already owns `config.symbols`; reading their segment prefix introduces **no new dependency** and keeps the logic in the runtime layer (not in `InstrumentResolver`, per the constraint).

**Why segment-prefix, not resolver classification (the decisive reason):** classifying a symbol via `InstrumentResolver` → `asset_class ∈ {FUTURE, OPTION}` requires the master to be **loaded** — but *"master absent"* is itself a BLOCK trigger (policy §4, failure #5). Resolver-classification would fail exactly when scope detection matters most (chicken-and-egg). Segment-prefix parsing of the raw key string is **master-independent** and therefore the only correct basis for the scope decision.

**Bonus coupling (fold in):** the same parse that answers *"has derivatives?"* also yields *which underlyings* are traded — the input the active-expiry coverage assertion (§3) needs. One parse, two uses.

**Alternative considered:** an explicit `DriverConfig.derivatives_enabled: bool` set by the entry script (which wires the universe). More explicit and avoids a string heuristic, but adds a config field and a wiring obligation, and is redundant with information already in `symbols`. Prefer the derived helper; revisit only if the symbol-key convention proves unstable.

> ⚠️ **Load-bearing assumption (see Unresolved Questions):** there is **no live F&O LoopDriver wiring in the repo yet** to confirm `config.symbols` will carry `NSE_FO|…` keys at the driver layer. The whole scope rule rests on that key convention holding for derivatives.

---

## 3. FRESH / WARN / BLOCK matrix

Per policy §4, **coverage is the hard gate; date is the early-warning proxy.** The matrix below is **date AND coverage** — a date-only version is incorrect per §4. Evaluated **only** under `LIVE AND has_derivatives`; every other context bypasses (see §6).

| State | Triggering condition | Startup behavior | State transition | Journal |
|---|---|---|---|---|
| **BLOCK** (absent) | `latest_snapshot_date() is None` (master absent/empty/unreadable) | refuse to start + CRITICAL alert | `abort_startup()` → STOPPED; loop never runs | `INSTRUMENT_MASTER_UNAVAILABLE` (CRITICAL), `reason="absent"` |
| **BLOCK** (coverage) | coverage assertions fail — missing traded segment, missing active weekly expiry per traded underlying, or EQ row without ISIN — **regardless of date** | refuse to start + CRITICAL alert | `abort_startup()` → STOPPED | `INSTRUMENT_MASTER_UNAVAILABLE` (CRITICAL), `reason="coverage"` |
| **BLOCK** (stale) | `latest < expected − 1 trading day` (≥2 trading days stale; almost certainly spans an expiry roll) | refuse to start + CRITICAL alert | `abort_startup()` → STOPPED | `INSTRUMENT_MASTER_UNAVAILABLE` (CRITICAL), `reason="stale"` |
| **WARN** | `latest == expected − 1 trading day` (one cycle behind; cutoff passed, job not yet run) **and** coverage passes | **start normally** + WARNING alert + telemetry line; dashboard staleness banner | proceeds to reconciliation → RUNNING | `INSTRUMENT_MASTER_STALE` (WARNING) — *see §4 (your call)* |
| **FRESH** | `latest == expected` **and** coverage passes | start normally, silent | proceeds → RUNNING | none (normal `RUNNING` event covers it) |

Evaluation precedence: **absent → coverage → stale-by-date → warn-by-date → fresh.** Coverage is checked even when the date is current (that is the whole point of §4 — a dated-today empty master must BLOCK).

**The coverage primitive does not exist yet.** MM.1–MM.3 give `latest_snapshot_date()` (date) and `expected_snapshot_date()` (date). The coverage assertions require a **new** read-only accessor — see §3-impl below.

### 3-impl. Where coverage logic lives (resolves the resolver-vs-no-logic tension)

The constraint says no readiness *logic* in `InstrumentResolver`. But *reading the master is the resolver's job* — it is "the only reader of the SSOT" (resolver.py:1). Split it cleanly:

- **Resolver exposes coverage FACTS** (read-only, alongside `latest_snapshot_date()`): e.g. row counts per segment, and active-expiry-present per underlying. Data only, no verdict.
- **Verdict LOGIC** (facts + dates → FRESH/WARN/BLOCK) lives in the readiness module (sibling to `master_freshness.py`) — pure, testable, no I/O.
- **Gate DECISION** (verdict → start/abort/journal/alert) lives in the driver's `_run_startup_gate()`.

That line — *facts on the resolver, judgment outside it* — honors "no logic in the resolver" without the absurdity of forbidding the sole reader from reading.

---

## 4. Event model

**Minimal correct set = the two you proposed**, mirroring the existing `RECONCILIATION_PASS` / `RECONCILIATION_FAIL` precedent (event_journal.py:60–61):

- **`INSTRUMENT_MASTER_UNAVAILABLE`** (CRITICAL) — BLOCK. One event for all three BLOCK causes; the `reason` metadata field (`absent | coverage | stale`) + `latest_snapshot_date` + `expected` disambiguate. (Naming note: "UNAVAILABLE" is slightly narrow for the coverage/stale cases; `reason` carries the truth, so it is acceptable, but `INSTRUMENT_MASTER_NOT_READY` would read more accurately. Cosmetic.)
- **`INSTRUMENT_MASTER_STALE`** (WARNING) — WARN. A durable record that a live session started on a 1-day-stale master.

FRESH needs **no** event (the normal `RUNNING` transition covers it — there is no "RECOVERY_OK" beyond `RECOVERY_COMPLETED` either). So: **+2 EventType entries, +2 severity-map entries.**

> ⚠️ **DIVERGENCE FROM POLICY — your call.** Policy §5 proposes **one** event (`INSTRUMENT_MASTER_UNAVAILABLE` for BLOCK) and routes WARN to *log + telemetry only*, and you wrote "keep vocabulary minimal." This review **recommends the 2-event set** because the journal is the *durable, ordered "what happened and why"* record (event_journal.py:9), whereas telemetry is explicitly *"ephemeral, lossy"* — and *starting a LIVE session on a stale master* is exactly the audit-relevant fact (Audit-First, CLAUDE.md Principle) that should not live only in a lossy stream. The 2-event set also matches the PASS/FAIL precedent symmetrically. **Tradeoff is yours:** 1 event (policy-minimal, WARN un-journaled) vs 2 events (audit-complete, +1 vocabulary term). Recommend 2.

No third event. Do not model FRESH as an event.

---

## 5. Alerting model

Aligns 1:1 with the existing reconciliation-fail path (`_reconcile_ledger`, driver.py:375 → `alerter.critical` → `abort_startup`):

| State | Severity | Channel | Startup |
|---|---|---|---|
| **BLOCK** | CRITICAL | `alerter.critical(...)` (logger.error + Telegram 🔴) | `abort_startup()` → STOPPED — refuse to start |
| **WARN** | WARNING | `alerter.warning(...)` (logger.warning + Telegram ⚠️) + telemetry `publish_log("WARNING", …)` | start normally |
| **FRESH** | — | none | start normally |

- **BLOCK mirrors `RECONCILIATION_FAIL`** exactly: CRITICAL journal event + `alerter.critical` + `abort_startup()`. Same refuse-to-start contract, same severity, same terminal STOPPED. Operationally indistinguishable from the existing hard-stop, which is the intent.
- **WARN alert is edge/once-per-startup**, not per-tick — so a single Telegram ⚠️ per live start on a stale master is acceptable signal, not noise. (Contrast the per-tick paths, which are deliberately edge-triggered to avoid spam.)
- **FRESH is silent** — no alert, normal INFO `RUNNING`.

---

## 6. Replay / backtest / research behavior

**All three bypass the check entirely. No staleness concept applies (policy §6).**

| Context | Behavior | Mechanism |
|---|---|---|
| **REPLAY** | No master-readiness check. Resolver opens DB **read-only, never touches network** (resolver.py:128/148); point-in-time via `as_of` (`_pick_effective`). | Gate condition `config.is_live` is False → check skipped. |
| **Backtesting** | No freshness check; uses `as_of = bar date` snapshot resolution, not "is it current". Forward-only `as_of` limitation (policy §6, Finding 1) is a separate, pre-existing, *logged* concern. | Runs under `Mode.REPLAY`. |
| **Research** | Not on the live gate path at all. | Does not construct a LIVE LoopDriver with this gate. |
| **Equity-only LIVE** | No master-readiness BLOCK. Today's soft fallback unchanged (resolver `None` / legacy selector / options calc-fallback). | `has_derivatives(config.symbols)` is False → check skipped. |
| **Paper** | Same soft fallback; no block. | Either not `is_live`, or no derivative universe — and the gate only runs when an `ExecutionHandler` is injected. |

**Gate predicate (all must hold to enforce):** `config.is_live` **AND** `has_derivatives(config.symbols)` **AND** an `ExecutionHandler` is injected (the gate's existing entry condition, driver.py:414). Any false → skip → no behavior change from today.

---

## 7. Test plan (must exist BEFORE implementation — TDD)

**A. Readiness-evaluator unit tests** (pure; `tests/instruments/test_master_readiness.py`), built on a fixture master through the **real ingest pipeline** (`parse_instruments` + `write_snapshot` into `tmp_path`, per policy §7 — never hit the network):
1. FRESH — `latest == expected`, coverage passes → verdict FRESH.
2. WARN — `latest == expected − 1` trading day, coverage passes → verdict WARN.
3. BLOCK absent — master DB missing/empty → verdict BLOCK(absent).
4. BLOCK coverage — dated-today master with **zero OPTION rows** (and/or missing active weekly expiry, and/or EQ without ISIN) → verdict BLOCK(coverage). *(The headline test — proves date-only would wrongly pass.)*
5. BLOCK stale — `latest < expected − 1` (≥2 trading days) → verdict BLOCK(stale).
6. Precedence — absent beats coverage beats stale-date beats warn-date.
7. IST/holiday boundary — `expected_snapshot_date` around the 08:30 cutoff, weekend, and an NSE holiday (extends the MM.3 tests already green).

**B. `has_derivatives` scope-helper unit tests** (pure):
8. `NSE_FO|…` / `MCX_FO|…` → True; `NSE_EQ|…` / `NSE_INDEX|…` → False; mixed universe → True.

**C. Driver-gate integration tests** (`tests/runtime/test_driver_startup_gate.py` or a new `test_driver_master_readiness.py`), injecting a **fake readiness checker** (callable, mirroring the `broker_positions` injection pattern, driver.py:149 — keeps the driver decoupled from the resolver):
9. **LIVE + derivative + FRESH** → reaches RUNNING; no `INSTRUMENT_MASTER_*` event; no alert.
10. **LIVE + derivative + WARN** → reaches RUNNING; `INSTRUMENT_MASTER_STALE` (WARNING) journaled; `alerter.warning` called once; reconciliation still runs after.
11. **LIVE + derivative + BLOCK** → STOPPED; `INSTRUMENT_MASTER_UNAVAILABLE` (CRITICAL) journaled with `reason`; `alerter.critical` called; `bars_processed == 0`; SignalSource `on_start`/`on_stop` never fire (mirror `test_gate_abort_does_not_touch_source`).
12. **Ordering** — event order asserts `RECOVERY_COMPLETED` < `INSTRUMENT_MASTER_*` < `RECONCILIATION_*` < `RUNNING` (proves before-reconciliation placement, §1).
13. **BLOCK aborts before reconciliation** — on BLOCK, `reconcile` is **never called** (the fake handler's `reconcile_calls == []`).
14. **LIVE + equity-only** → check skipped → RUNNING; no `INSTRUMENT_MASTER_*` event (bypass, §6).
15. **REPLAY** (with handler) → check skipped → RUNNING; no `INSTRUMENT_MASTER_*` event.
16. **Alerting** — monkeypatch `alerter`; assert `critical` on BLOCK, `warning` on WARN, neither on FRESH.
17. **Startup refusal contract** — BLOCK leaves STOPPED, loop never runs, identical observable shape to `RECONCILIATION_FAIL`.

Maps to your enumerated list: LIVE+FRESH (9), LIVE+WARN (10), LIVE+BLOCK (11), REPLAY bypass (15), equity-only bypass (14), journaling (10/11), alerting (16), startup refusal (11/17). Plus the coverage test (4) and ordering test (12), which your list did not name but §4/§5 require.

---

## Risks

1. **(HIGH) Coverage gap = false assurance.** Date-only MM.4 passes a dated-today empty/partial master (failure #4/#7). A live gate that green-lights a broken master is worse than no gate. **Mitigation:** coverage primitive is in MM.4 scope (or explicit MM.4a/MM.4b split with MM.4a flagged partial). This is the gating decision for the verdict.
2. **(MED) Scope rule rests on an unverified key convention.** No live F&O LoopDriver wiring exists yet to confirm `config.symbols` are `SEGMENT|…` keys at the driver layer (Unresolved Q1).
3. **(MED) Document conflict on ordering** (§1) — request diagram vs policy §5. Must be resolved before coding.
4. **(LOW) Resolver coupling / DI.** The driver must obtain readiness facts without depending on `InstrumentResolver` internals. **Mitigation:** inject a readiness-checker callable (like `broker_positions`); the entry script constructs the resolver. Driver stays thin and testable with a fake.
5. **(LOW) WARN alert cadence.** Acceptable as once-per-startup; confirm it is not wired into any per-tick path.
6. **(LOW) Coverage assertion needs the active weekly expiry per underlying** — couples the gate to expiry-calendar truth (Nifty=Tue, BankNifty=Wed). Source that from the existing expiry logic, do not re-derive.

## Unresolved questions

1. **Will `config.symbols` carry `NSE_FO|…` keys at the LoopDriver layer for live F&O?** No wiring exists to confirm. The entire scope rule (§2) depends on it. *(Do not hunt for an example — it does not exist yet; confirm with the F&O runtime-wiring slice.)*
2. **1 event or 2?** (§4) — policy says 1 (WARN un-journaled); this review recommends 2 (WARN journaled). Your call.
3. **Ordering authority** (§1) — §5 (before reconciliation) vs the request diagram (after). This review picks §5; confirm.
4. **Coverage scope for MM.4** — full coverage (segment + active-expiry + EQ-ISIN) in MM.4, or minimal (non-empty derivative segment + active expiry) now with EQ-ISIN deferred? Recommend at least non-empty-derivative-segment + active-expiry-present, since those are the live-order-correctness assertions.
5. **Who owns `has_derivatives`?** A pure helper in `core/runtime/` (driver-adjacent, runtime-owned) vs `core/instruments/`. Recommend runtime-adjacent — it parses provider keys, a runtime concern, and must not depend on the resolver.

## Implementation-readiness verdict

**CONDITIONAL GO.**

- ✅ **Wiring is ready:** insertion point (§1, before reconciliation), scope predicate (§2), alerting (§5), and replay bypass (§6) all map onto the existing `_run_startup_gate()` contract with low risk and zero behavior change off the live-F&O path.
- ⛔ **Blocked on coverage:** MM.4 must **not** ship as a date-only gate on the MM.1–MM.3 primitives — that delivers false assurance (Risk 1). Add the coverage primitive (resolver facts + readiness verdict) within MM.4, or split MM.4a/MM.4b with MM.4a explicitly marked partial.
- 🔲 **Resolve before coding:** the ordering conflict (Q3) and the event-count decision (Q2). Both are one-line owner calls.
- ▶️ **TDD:** the §7 tests — especially the BLOCK-coverage test (#4) and the ordering test (#12) — are written first.

**No code, no edits to source, no commit accompany this review** — design only, per the request.
