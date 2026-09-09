# MASTER_MATERIALIZATION_POLICY.md

**Type:** Design / policy — **PROPOSED. No code in this document.** Every mechanism below is a specification to be implemented in a later slice; none exists yet unless explicitly marked *(exists)*.
**Date:** 2026-06-08
**Phase:** 4C.7 precondition (with Gate G1 + a materialized master). Designs the "materialized master + staleness policy" the readiness review required.
**Predecessor:** `docs/reports/MASTER_MATERIALIZATION_READINESS.md` (Findings 1 & 2, 7 questions, locked decisions §6.2 of the plan).
**Basis (file:line, current code):** `scripts/fetch_instrument_master.py`, `core/instruments/resolver.py`, `core/data/options_provider.py` (Finding 2 fixed), `core/runtime/driver.py` (startup gate), `core/runtime/event_journal.py` (EventType), `core/database/utils/market_hours.py` (`MarketHours`, IST + NSE holidays).

> This policy turns the master from a soft, manually-refreshed convenience into a **trustworthy, content-verified production dependency** with a defined refresh path, a coverage-based staleness model, and fail-fast startup on the live F&O path. It is the answer to readiness Q1–Q7 and Decision 4 (plan §6.2).

---

## 1. Refresh source

- **Source** *(exists)*: the public Upstox CDN snapshot `https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz` (`fetch_instrument_master.py:39,140`). **No authentication** — plain `requests.get`. The docstring's "after OAuth" (`:9`) is misleading and should be corrected: the fetch is token-independent.
- **Consequence (load-bearing):** because the source needs no token, **refresh can be decoupled from the Upstox OAuth session entirely.** This is the foundation of §2 — it removes the dependency on the daily Upstox token (which expires ~03:30 IST) that today's only trigger relies on.
- **Segments ingested** *(exists)*: `NSE_FO, MCX_FO, NSE_EQ, NSE_INDEX` (`fetch_instrument_master.py:43`). Equity rows carry ISIN (derived from the `NSE_EQ|INE…` key when absent, `:113-117`).
- **Single source of truth:** the CDN is the *only* sanctioned source. There is **no dated/historical endpoint** — see §6 / readiness Finding 1 (forward-only snapshots).

## 2. Refresh cadence

- **PROPOSED primary:** an **OS-level scheduled job** (Windows Task Scheduler / cron — **no in-repo scheduler exists**, confirmed by grep) runs `python scripts/fetch_instrument_master.py` once per **NSE trading day**, at a fixed **refresh cutoff `08:30 IST`** — after the overnight contract/expiry updates settle, before the 09:15 open. Skips non-trading days via `MarketHours.is_trading_day()` (`market_hours.py`).
- **PROPOSED backstop** *(partially exists)*: the existing OAuth-callback refresh (`flask_app/blueprints/ops/routes.py:179-185`) is retained as a **secondary** trigger — useful when a human logs in — but is **no longer the system of record** for freshness. The scheduled job is.
- **Why decoupled (the strength):** the scheduled job hits the no-auth CDN, so a day with no manual OAuth login no longer implies a stale master. This resolves the token-lifetime ambiguity the readiness review (Q2/Q4) could not settle from the repo.
- **Idempotent** *(exists)*: re-running within a `snapshot_date` replaces that day's rows; earlier snapshots are preserved (`fetch_instrument_master.py:152-175`). Safe to run the job and the backstop on the same day.

## 3. Freshness & coverage model (centralized) — PROPOSED

Freshness must be computed **one way** by every consumer (startup gate, dashboard, ops). Propose a single accessor on the sole reader:

- **`InstrumentResolver.latest_snapshot_date() -> date | None`** *(PROPOSED — resolver has only the private `_loaded` today, `resolver.py:45`)*: returns `MAX(snapshot_date)` from `instruments`, or `None` if absent/empty. All staleness checks derive from this — no consumer re-runs its own `MAX(snapshot_date)` (which is what the now-fixed Finding 2 reads already do inline).
- **`expected_snapshot_date(now_ist)`** *(PROPOSED, pure, via `MarketHours`)*: the latest NSE trading day whose **08:30 IST refresh cutoff has passed** relative to `now_ist`. On a trading day after cutoff → today; before cutoff → previous trading day; on a weekend/holiday → the last trading day. Defining "expected" off a fixed cutoff (not "has the job run yet") removes time-of-day ambiguity across restarts.

**Coverage assertions (the authoritative guarantee — age is only a proxy):** a master can be dated *today* yet be unusable (partial parse, or the upstream schema shift that is Q7's risk → 0 OPTION rows). The gate and the materialization **acceptance check** therefore assert *content*, not just presence + date:
- non-empty row count per **traded segment** present in the run's universe (EQ / FUT / OPT / INDEX as applicable);
- **EQ rows have ISIN** populated (equity canonical identity requires it — `canonical.py:_validate`);
- the **active weekly expiry is present per traded underlying** (Nifty/BankNifty) — the real risk a stale master poses is missing the current expiry's contracts across a roll, which a date check alone does not catch.

## 4. Staleness thresholds

Two signals; **coverage is the hard gate, date is the early-warning proxy.**

| State | Condition | Live F&O path | Equity-only / paper / replay |
|---|---|---|---|
| **FRESH** | `latest_snapshot_date == expected_snapshot_date` **and** coverage assertions pass | proceed | proceed |
| **WARN** | `latest == expected − 1 trading day` (one cycle behind: job not yet run though cutoff passed) **and** coverage passes | proceed + emit warning + telemetry; the active expiry is still covered | proceed |
| **BLOCK** | coverage assertions **fail** (missing segment / missing active expiry / EQ without ISIN) **— regardless of date —** OR `latest < expected − 1 trading day` (≥2 trading days stale; almost certainly spans an expiry roll) OR master **absent** | **fail-fast: refuse to start** (§5) | soft fallback, unchanged (resolver returns `None` / selector legacy table / options calc-fallback) — never blocks paper/replay |

Rationale: a 1-day-stale master on a normal day still covers the live expiry (WARN). Coverage failure or ≥2-day staleness implies the live contract set may be wrong → BLOCK on the only path where a wrong instrument means a mis-routed real order.

## 5. Startup behavior — PROPOSED

Extend the existing LoopDriver startup gate `_run_startup_gate()` (`driver.py:326`, invoked at `:418`), which today does recovery + reconciliation and calls `abort_startup()` (`:303`) on `RECONCILIATION_FAIL` (`:372-379`). Add a **master-readiness check** with the **same refuse-to-start contract**:

- **Scope (the fail-fast flip, Decision 4):** the check is enforced **only when** `Mode.LIVE` **and** the configured universe contains a **tradable derivative** (FUT/OPT). Equity-only LIVE, paper, and replay keep today's soft fallback (no behavior change).
- **On BLOCK (§4):** emit a **new** journal event **`EventType.INSTRUMENT_MASTER_UNAVAILABLE`** *(PROPOSED — not in the enum today, `event_journal.py:52-70`; severity CRITICAL, like `RECONCILIATION_FAIL`)* with metadata (`reason`: absent | stale | coverage; `latest_snapshot_date`; `expected`), then `abort_startup()` → `STOPPED` + critical alert. The tick loop never runs; no order is built against a wrong instrument set.
- **On WARN:** start normally, emit a WARNING-severity log + telemetry line (reuse the `publish_log` path added in Phase G); the dashboard shows the staleness banner.
- **Ordering:** the master check runs **before** reconciliation (identity must be trustworthy before positions are matched against it).

## 6. Replay behavior

- **No staleness check.** Staleness is a wall-clock/live concept; replay is deterministic over historical bars (ADR-003). The resolver opens the local DB **read-only and never touches the network** (`resolver.py:133`) — replay is fully offline once the master exists.
- **Point-in-time via `as_of`** *(exists)*: backtests pass `as_of = bar date`; `_pick_effective` (`resolver.py:139-152`) returns the snapshot effective at that date.
- **Forward-only limitation (Finding 1, accepted):** the live source has no dated endpoint, so the snapshot series only accrues from first capture. A backtest before capture-start resolves to the **earliest** snapshot with a **logged warning** (`resolver.py:147-151`) — observable, not silent. Documented as a known bound on historical `as_of` accuracy until/unless a backfill source surfaces. **Materialize the master in production as early as possible** — every day delayed is a day of historical accuracy never recoverable.

## 7. CI / test behavior

- **Never hit the network** *(exists, the pattern to keep)*: tests build a fixture master through the **real ingest pipeline** — `parse_instruments()` + `write_snapshot()` into a `tmp_path` DuckDB (`tests/instruments/test_resolver.py:17,47`; `tests/data/test_options_provider_snapshot.py`). No committed binary master, real parser/schema exercised, multi-snapshot `as_of` and staleness scenarios synthesizable by stamping snapshot dates.
- **PROPOSED source-contract test (Q7):** a committed, tiny, **sanitized** sample of the real CDN payload (a handful of EQ/FUT/OPT/INDEX raw items) asserted against `parse_instruments` field expectations (`strike_price`/`strike`, `expiry` ms-vs-string `:71-83,110-111`, `instrument_type`/`option_type`, ISIN derivation). Catches an upstream Upstox **schema change** in CI rather than in production (the failure that would silently yield 0 OPTION rows and defeat a date-only freshness check). A live-network smoke test may exist but must be **marked and skipped by default**.

## 8. Failure modes

| # | Failure | Detection | Response |
|---|---|---|---|
| 1 | CDN network/HTTP error during refresh | `raise_for_status()` (`fetch_instrument_master.py:141`) | exception logged; **prior DB preserved** (no write). Scheduled job retries next cycle; staleness model (§4) governs whether the now-aging master still permits live start. |
| 2 | Empty / zero-row parse | `refresh()` returns 0, **aborts write** (`:182-183`) | prior DB preserved; logged ERROR. |
| 3 | Partial write (crash between `DELETE` and `INSERT`, `:169-171`) | next run / startup coverage check (§3) | **self-heals** on re-run (re-DELETE+INSERT). Low probability; PROPOSED hardening: wrap the per-snapshot DELETE+INSERT in one transaction. |
| 4 | Upstream **schema change** (renamed/removed fields → rows silently dropped) | **source-contract test (§7)** in CI; coverage assertion (§3) at materialization/startup | CI fails before deploy; at runtime, coverage BLOCK on live F&O (§4/§5) rather than a date-only false-pass. |
| 5 | Master **absent** at live F&O start | startup gate (§5), `latest_snapshot_date() is None` | `INSTRUMENT_MASTER_UNAVAILABLE` → `abort_startup()` → STOPPED + CRITICAL. |
| 6 | Master **stale** (missed refresh, ≥2 trading days) | startup gate (§5) date proxy | BLOCK live F&O; WARN at 1 day. |
| 7 | Master **dated-but-incomplete** (missing active expiry / segment / EQ ISIN) | coverage assertions (§3) | BLOCK regardless of date — the key gap a date-only check misses. |
| 8 | Corrupt / unreadable DuckDB | resolver query raises → returns `None` *(exists, `resolver.py` try/finally + None)* | live F&O: treated as absent → BLOCK (§5); paper/replay: soft fallback. |
| 9 | "Today" computed in the wrong timezone | `MarketHours` IST + `NSE_HOLIDAYS` (`market_hours.py:41,55`) used for `expected_snapshot_date` | single IST-based definition; no naive `date.today()` in the freshness path. |

## 9. PROPOSED code surface (for the implementing slice — not built here)

- `InstrumentResolver.latest_snapshot_date()` + `expected_snapshot_date(now_ist)` helper (freshness, centralized — §3).
- A `master_readiness()` check (presence + freshness + **coverage**) consumed by the startup gate — §3/§4.
- `EventType.INSTRUMENT_MASTER_UNAVAILABLE` (CRITICAL) + severity map entry — §5.
- Startup-gate integration in `_run_startup_gate()` gated on LIVE + F&O universe — §5.
- Source-contract test + sanitized sample fixture — §7.
- OS-scheduled refresh job + corrected `fetch_instrument_master.py` docstring (drop "after OAuth") — §1/§2.
- (Optional hardening) transactional `write_snapshot` — §8#3.

> **Design only.** None of §9 is implemented. Producing this policy does **not** satisfy the 4C.7 precondition — see `PHASE_4C_7_READINESS.md`.
