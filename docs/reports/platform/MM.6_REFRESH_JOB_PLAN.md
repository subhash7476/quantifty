# MM.6_REFRESH_JOB_PLAN.md

**Type:** Implementation plan / design — **PROPOSED. No code in this document.** Produced for review per the MM.5 review directive; nothing is implemented until this plan is approved.
**Date:** 2026-06-09
**Phase:** MM.6 — Refresh Job. The milestone after MM.5 (master materialized) and before MM.7 (production checker wiring). Addresses 4C.7 readiness **blocker #3** (the OS-scheduled refresh job — policy §2 — does not exist).
**Goal:** operationalize Instrument Master **freshness** — turn the manual, OAuth-piggybacked refresh into a scheduled, content-validated, fail-safe daily job that keeps the master FRESH on the live F&O path.
**Basis (ratified policy):** `MASTER_MATERIALIZATION_POLICY.md` §1 (source), §2 (cadence), §3 (freshness/coverage), §8 (failure modes). **Predecessors:** `MM.5_MATERIALIZATION_REPORT.md` (the materialized master + operational findings), MM.1–MM.4 (the freshness/coverage primitives + gate this consumes).
**Constraints (locked):** prefer the policy-approved **OS scheduler**; **no** scheduler frameworks, daemons, or background services; extend the existing script, do **not** add a wrapper/abstraction (CLAUDE.md "no over-engineering", "prefer editing existing files"); reuse the **one** coverage implementation (policy §3 "compute one way").

> **APPROVED FOR IMPLEMENTATION (2026-06-09).** The owner ratified the §9 open questions (below); implementation is authorized. The expiry-coverage clarification review closed **Outcome A — no F5** (the coverage rule is `expiry >= expected`, structure-agnostic; "weekly" was wording, never an encoded rule). 4C.7 remains blocked until **MM.7** (production checker wiring) and **Gate G1** are complete.

## Ratifications (2026-06-09 — owner-approved)

1. **Validate-before-publish = Option A** — **stage → validate → promote**; never publish a bad snapshot (§4 Option A). In-memory revalidation and publish-then-rollback are both rejected.
2. **Generic underlyings parameter** — the coverage universe is a **parameter** (default `("NIFTY","BANKNIFTY")`), not hardcoded into the validation logic. *(resolves §9 Q2)*
3. **Contract-shape guard** — the validate step also asserts the MM.5 cleanly-typed-derivative shape (derivative-segment rows ⊆ {CE,PE,FUT}, CE/PE present), catching a 0-OPTION-rows schema shift before publish. *(resolves §9 Q3)*
4. **Transactional snapshot writes** — `write_snapshot`'s per-snapshot DELETE+INSERT is wrapped in one transaction (policy §8#3); a failed INSERT rolls back the DELETE, never leaving a date's snapshot empty. *(resolves §9 Q4)*
5. **Docstring correction** — replace wording equivalent to "active **weekly** expiry" with "active expiry (≥ expected)" in `master_readiness.py` (the `assess()`/module docstring) so future maintainers do not accidentally encode a weekly-expiry requirement; and drop the misleading "after OAuth login" from `fetch_instrument_master.py` (policy §1).
6. **No scheduler framework** — OS scheduler approach only (Task Scheduler / cron, as a documented artifact); no daemon/service/in-repo scheduler.
7. **Refresh status surface (§9 Q5)** — **deferred** (exit code + the MM.4 startup gate are the backstop; no new store). **08:30 IST cutoff (§9 Q6)** — operational confirmation, non-blocking.

**Post-MM.6 expected blocker board:** Gate G1 OPEN · Master DB CLOSED · **Refresh Job CLOSED** · Production Checker OPEN — leaving two substantive readiness tracks (G1, MM.7) before 4C.7 can be reconsidered.

---

## 1. Scope

**In scope (the four MM.5-review deliverables):**

1. **Refresh mechanism** — a guarded, validated daily entry point (extends `scripts/fetch_instrument_master.py`).
2. **Snapshot creation** — IST-correct `snapshot_date` stamping (fixes MM.5 operational finding #1).
3. **Validation before publish** — coverage-assert the new snapshot *before* it becomes the live master, reusing the MM.4 gate's coverage facts.
4. **Refresh failure handling** — every failure mode (policy §8) leaves the prior good snapshot intact and signals via a non-zero exit code.

Plus the policy-mandated **cadence artifact** (OS-scheduler invocation, as documentation) and the §1 **docstring correction**.

**Explicitly out of scope** (see §10): live entry-script wiring of the readiness checker (**MM.7**), order routing, Gate G1, the F3/F4 dispositions, historical backfill (Finding 1, accepted).

---

## 2. Touch-points (what MM.6 changes — design intent, not code)

| Surface | Change | Reuse / leave-alone |
|---|---|---|
| `scripts/fetch_instrument_master.py` | Extend the `__main__`/`refresh()` flow into a **guarded + validated + IST-stamped** run. `parse_instruments` and `write_snapshot` stay **pure and unchanged**. | — |
| `core/instruments/resolver.py` | **No change.** Read `latest_snapshot_date()`, `segment_row_count()`, `active_expiry_present()`. | the sole reader (MM.1/MM.4) |
| `core/instruments/master_readiness.py` | **No change.** Reuse `assess()` for the validate-before-publish verdict. | the one coverage definition (MM.4) |
| `core/instruments/master_freshness.py` | **No change.** Reuse `expected_snapshot_date(now_ist)`. | MM.3 |
| `core/database/utils/market_hours.py` | **No change.** Use `get_ist_now()`, `is_trading_day()`. | IST + NSE holidays |
| OS scheduler (Task Scheduler / cron) | **New artifact** — a documented invocation (not in-repo code). | policy §2 |

**No new module, no new class.** The refresh job is an orchestration of existing primitives inside the existing script.

---

## 3. Refresh sequence (the mechanism)

The daily entry point executes this ordered flow; **any failure short-circuits to "prior DB preserved + non-zero exit".**

```
1. TRADING-DAY GUARD
   now_ist = MarketHours.get_ist_now()
   if not MarketHours.is_trading_day(now_ist):
       log "non-trading day — skip"; exit 0        # scheduler may fire daily; script self-skips

2. SNAPSHOT DATE (IST-correct — §5)
   snapshot_date = now_ist.date().isoformat()      # NOT machine-local date.today()

3. DOWNLOAD + PARSE  (existing, pure)
   raw  = download(INSTRUMENTS_URL)                # network; raise_for_status
   rows = parse_instruments(raw, snapshot_date)
   if not rows: log ERROR "empty parse"; exit 2    # prior DB untouched (existing guard)

4. VALIDATE BEFORE PUBLISH  (§4 — the new mechanism)
   verdict = validate(rows, snapshot_date, now_ist, underlyings)
   if verdict is not PUBLISHABLE:
       log ERROR "coverage failed: <reason>"; exit 3   # prior DB untouched

5. PUBLISH  (existing, idempotent)
   n = write_snapshot(rows)                         # DELETE today + INSERT (per-date)
   log INFO "published <n> rows, snapshot_date=<...>"; exit 0
```

"PUBLISHABLE" = FRESH or WARN from the gate's own model (a 1-day-old expected date is fine the instant after cutoff); only a **coverage** failure or absence blocks publish (mirrors policy §4: coverage is the hard gate).

---

## 4. Validate-before-publish — strategy (DECISION FOR REVIEW)

The point: never let a bad download **replace** a good master as the latest snapshot. Because `write_snapshot` writes a new dated snapshot and the resolver reads `MAX(snapshot_date)`, an unvalidated bad publish becomes "latest" → the live startup gate then BLOCKs (fail-closed, safe) — but the *operationally better* outcome is to **refuse to publish** so the prior good snapshot stays latest and the live path degrades only to **WARN**, not BLOCK. Validation must reuse the **exact** MM.4 coverage assertions (no second coverage definition).

**Option A — staging-validate-then-promote (RECOMMENDED).**
```
tmp = tempfile DuckDB
write_snapshot(rows, db_path=tmp)                       # reuse the real writer
verdict = assess(InstrumentResolver(db_path=tmp), underlyings, now=now_ist)
if verdict.state is BLOCK: discard tmp; refuse publish  # prior prod DB never touched
else: write_snapshot(rows, db_path=DB_PATH)             # promote the same rows
discard tmp
```
- **Pros:** production DB is **never** touched on failure (race-free); reuses `assess()` verbatim (policy §3 honored); two cheap writes (~65K rows). Composes with idempotency + the OAuth backstop.
- **Cons:** writes the rows twice (negligible at this size).

**Option B — publish-then-validate-then-rollback (alternative).**
```
write_snapshot(rows, db_path=DB_PATH)
verdict = assess(InstrumentResolver(db_path=DB_PATH), underlyings, now=now_ist)
if verdict.state is BLOCK:
    DELETE FROM instruments WHERE snapshot_date = snapshot_date   # roll back to prior
```
- **Pros:** one write, simpler.
- **Cons:** a brief window where prod holds the unvalidated snapshot (a concurrent live start at 08:30 pre-open could observe it). Small, but not race-free.

**Recommendation: Option A (staging).** Race-free, reuses the single coverage path, the extra write is trivial. (Both options reuse `assess()` — neither reimplements coverage. In-memory revalidation on the `rows` list is **rejected**: it would duplicate the coverage logic and drift from the gate.)

**Validation content** = exactly the gate's coverage assertions (MM.4 `assess`): traded segments non-empty, EQ rows carry ISIN, active weekly expiry present per configured underlying (NIFTY/BANKNIFTY). Optionally also reuse the MM.5 contract-shape guard (cleanly-typed CE/PE/FUT derivative segments) — see §9 open question.

---

## 5. Snapshot creation — IST date stamping (CORRECTNESS, not a footnote)

MM.5 operational finding #1: `download_and_parse` defaults `snapshot_date = date.today().isoformat()` — **machine-local**. The startup gate computes `expected_snapshot_date(now_ist)` in **IST**. They agreed on the MM.5 box (local date == IST date → FRESH), but on a box whose local date differs from IST near the date boundary they diverge by a day → the gate returns **WARN** (or **BLOCK("stale")**) on a perfectly fresh download.

**MM.6 requirement:** the refresh job stamps `snapshot_date` from the **IST** date (`MarketHours.get_ist_now().date()`), so materialization and the gate use one definition of "today." This is the single most load-bearing correctness item in MM.6 — without it the scheduled job can manufacture spurious staleness. (Mechanically: pass an explicit IST-derived `snapshot_date` through `download_and_parse`/`refresh`, rather than relying on the `date.today()` default.)

---

## 6. Refresh failure handling (policy §8)

| # | Failure | Response (MM.6) | Exit |
|---|---|---|---|
| 1 | CDN network/HTTP error | exception caught; **prior DB untouched**; logged ERROR | non-zero |
| 2 | Empty / zero-row parse | abort write (existing guard); prior DB preserved | non-zero |
| 3 | **Coverage fail** (missing segment / missing active expiry / EQ without ISIN) | **do NOT publish** (§4 Option A: prod never written); prior DB preserved | non-zero |
| 4 | Upstream schema change → rows silently dropped | caught as a coverage fail (#3) at validate-before-publish; the source-contract test (policy §7) catches it earlier in CI | non-zero |
| 5 | Partial write (crash between DELETE/INSERT) | self-heals on next run (existing); **optional** hardening: wrap per-snapshot DELETE+INSERT in one transaction (policy §8#3) — low priority, see §9 | — |
| 6 | Non-trading day | self-skip (§3 step 1) | 0 (skipped) |

**The non-zero exit code is the minimal alerting hook** policy §8 flagged as missing ("nothing alerts"). The OS scheduler records failed runs; **the startup gate (MM.4) remains the ultimate fail-closed backstop** — a stale/under-covered master still BLOCKs (or WARNs) a live F&O start regardless of whether anyone watched the scheduler. MM.6 deliberately does **not** add an alerting framework (out of scope; the gate already fails closed).

---

## 7. Cadence — OS scheduler artifact (policy §2)

- **Primary:** an OS-level scheduled task runs the entry point **once per NSE trading day at 08:30 IST** (after overnight contract/expiry updates settle, before the 09:15 open). The script self-skips non-trading days (§3 step 1), so the scheduler can safely fire every day.
- **Deliverable form:** **documentation only** — a Windows Task Scheduler invocation (`schtasks` command / exported XML) and an equivalent cron line, committed under `docs/` or the script's docstring. **No in-repo scheduler, daemon, or service** (constraint).
- **Backstop:** the existing OAuth-callback refresh (`flask_app/blueprints/ops/routes.py`) is retained as a **secondary** trigger, **no longer the system of record**. Idempotency makes running both on the same day safe.
- **Docstring fix (policy §1):** drop the misleading "Run once after OAuth login each morning" from `fetch_instrument_master.py` — the CDN fetch is token-independent.

---

## 8. Test plan (TDD — never hit the network)

Build fixture masters through the **real ingest pipeline** (`parse_instruments` + `write_snapshot` into `tmp_path`), the established pattern (`test_resolver.py`, `test_options_provider_snapshot.py`). Download is mocked. Proposed RED→GREEN cases:

1. **Good master publishes** — a complete fixture (all segments, EQ-ISIN, active expiry) → prod DB gains the new snapshot; `latest_snapshot_date()` == IST date.
2. **Coverage fail does NOT publish** — fixture missing the active expiry (and variants: empty FO, EQ without ISIN) → prod DB **unchanged**, prior snapshot remains latest, non-zero exit.
3. **IST stamping** — monkeypatch a box whose local date ≠ IST date → `snapshot_date` == IST date (not machine-local).
4. **Non-trading-day skip** — `is_trading_day` False → no write, exit 0.
5. **Network error** — mocked `raise_for_status` → no write, prior DB preserved, non-zero exit.
6. **(If Option A) staging isolation** — a failing validation never opens/writes the prod path (assert prod file mtime unchanged).

---

## 9. Open questions for the owner (resolve before implementation)

1. **Validate-before-publish strategy** — ratify **Option A (staging, recommended)** vs Option B (rollback). *(§4)*
2. **Coverage universe** — which underlyings define "traded" at refresh time: NIFTY/BANKNIFTY hardcoded (as MM.5/MM.4), or config-driven? *(§4)*
3. **Contract-shape guard** — also reuse the MM.5 cleanly-typed-derivative check at validate-before-publish, or rely on coverage + the policy §7 CI source-contract test? *(§4/§6#4)*
4. **Transactional `write_snapshot`** — implement the policy §8#3 DELETE+INSERT transaction hardening in MM.6, or defer (self-heals today)? *(§6#5)*
5. **Refresh status surface** — is the exit code + the startup gate sufficient, or should the job also persist a "last-successful-refresh" timestamp for the ops dashboard? (Lean: defer — the gate is the backstop; no new store.) *(§6)*
6. **08:30 IST cutoff** — confirm it clears the overnight Upstox contract-update settle window for all segments. *(§7)*

---

## 10. Out of scope (explicit — do not let MM.6 absorb these)

- **Production checker wiring** into a live F&O entry script → **MM.7** (the MM.4 `master_readiness` callable is still injected only in tests). MM.6 does **not** modify order routing or reconciliation.
- **Gate G1** (sole-identity-path migration + `SOLE_IDENTITY_PATH_REVIEW.md`) — independent, the longest pole; untouched by MM.6.
- **F3 (tick_size ×100)** — owned by the parser/4C.7 slice; **not** fixed here. **F4 (lot 65/30 vs 75)** — INVESTIGATION REQUIRED; **not** fixed here. MM.6 must **not** silently alter `parse_instruments` scaling.
- **Historical backfill** (Finding 1) — accepted limitation; the live source has no dated endpoint.
- **No scheduler framework / daemon / background service**; no SPAN / margin / broker-account-state work.

## 11. Scheduler artifact (delivered)

The OS-scheduler invocation (documentation, not in-repo code — constraint #6). The
entry point is `python scripts/fetch_instrument_master.py`, which runs
`run_refresh()` and exits with the §6 code. **Correctness is box-clock-independent**
— the script stamps `snapshot_date` in IST and self-skips non-trading days/holidays
via `MarketHours` regardless of the host clock — so the schedule only governs *when*
it fires; aim it at **~08:30 IST**.

**Windows Task Scheduler** (the host is Windows; `/SC DAILY` is safe because the
script self-skips non-trading days — the schedule need not encode the NSE calendar):
```
schtasks /Create /TN "InstrumentMasterRefresh" ^
  /TR "\"C:\Path\To\python.exe\" \"F:\nifty\scripts\fetch_instrument_master.py\"" ^
  /SC DAILY /ST 08:30 /RL LIMITED /F
```
(Set `/ST` to 08:30 in the host's local clock = 08:30 IST; if the box is not on IST,
convert. A non-zero exit marks the run failed in Task Scheduler history.)

**cron** (Linux equivalent; `TZ` IST or convert the minute/hour):
```
30 8 * * 1-5  cd /path/to/nifty && /usr/bin/python scripts/fetch_instrument_master.py >> logs/instrument_refresh.log 2>&1
```

> **Remaining operational step (not doable from the repo):** *installing* this task in
> the target environment and confirming it fires. The refresh **mechanism** is built,
> validated, and tested (365 green); marking blocker #3 CLOSED records the mechanism —
> the scheduled task must still be installed where the platform runs.

---

> **Implemented (2026-06-09).** §3–§8 are built and tested (TDD, 365 green); the
> ratifications (§Ratifications) are all incorporated. 4C.7 stays blocked until MM.7
> (production checker wiring) and Gate G1.
