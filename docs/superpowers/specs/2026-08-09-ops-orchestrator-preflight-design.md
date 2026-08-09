# Ops Orchestrator + Preflight — Design

**Date:** 2026-08-09
**Status:** DESIGN (approved shape; pending spec review)
**Scope:** A single-command foreground supervisor for the NiftyShield PAPER trading
window, plus a standalone read-only preflight go/no-go checker.

---

## 1. Current state — the operational map (the audit)

This section is the "thorough check" that justifies the design. It is the
source-of-truth map of what runs, when, and what depends on what. Every claim
below was traced through the code, not assumed.

### 1.1 Two independent clocks

The platform has **two unrelated schedules**, and conflating them is the primary
risk this design guards against:

- **EOD / post-close (data pipeline):** `schedule_worker.py` — already a working,
  PID-locked daemon. Fires 20:00–23:30 Mon–Fri → `download_all_data.py` (equity /
  futures / options / index bhavcopy + corp actions) → probe feeds → strategy chain
  (`refresh_all_strategies` → `ts_basis_daily_signals` → `ts_basis_daily_options`)
  → Telegram book. Retry/holiday/exhaustion logic already built
  (`core/scheduler/eod_*.py`).
- **Trading-window (live, 09:15–15:30 IST):** the trio the operator currently starts
  by hand, none supervised today.

### 1.2 The trading-window dependency chain (mandatory order)

```
Upstox OAuth (token)  ──►  market_ingestor  ──►  live_buffer (NF/BN/VIX 1m)
        │                        │                       │
        │                        ▼                       ▼
        └──► chain_poller ──► chain_cache         13:00 day-type fact (in-runner)
                  │                                       │
                  └──────────► nifty_shield_runner ◄──────┘
```

1. **Upstox OAuth** — `flask_app/blueprints/ops/routes.py`: `/ops/login/upstox`
   → Upstox dialog → `/ops/callback/upstox` exchanges code → `credentials.save()`.
   The **instrument-master refresh is inside this callback** (`fetch_instrument_master.refresh()`),
   its failure swallowed into a `flash(..., "warning")`.
2. **`market_ingestor.py`** — WebSocket → `data/live_buffer/candles_today.duckdb`.
   The source of live 1m bars for the day-type engine and the LoopDriver. Its
   `_acquire_lock()` is **commented out** (`scripts/market_ingestor.py:243`) — no
   single-instance guard today. Late-connects if the token appears mid-session.
3. **`chain_poller.py`** — sole writer of `data/options/chain_cache.duckdb` (option
   marks). Has its own PID lock (`data/options/chain_poller.pid`) and a heartbeat
   (`data/options/chain_poller_heartbeat.json` = `{last_snapshot, rows, expiry}`).
   Idles outside market hours (never spins the API).
4. **`nifty_shield_paper/session.py`** — the daily Phase B PAPER session (it composes
   the LoopDriver via `nifty_shield_paper_runner.build_nifty_shield_paper_driver`; the
   runner module is Phase A wiring, `session.py` is the op — see §3.1). Publishes the
   day-type fact **in-process** at 13:00 via the driver's `publish_hook` (NOT a
   separate cron). Reads VIX/NF/BN from the live buffer, marks from the chain cache,
   SPAN from `data/span/` (PAPER tolerates absence → flat-rate `MarginTracker`).

### 1.3 What the NiftyShield session does NOT depend on

The PAPER session reads only the **live** surface: live buffer + chain marks +
in-runner day-type fact + SPAN. It does **not** read the EOD bhavcopy stores or the
`ts_basis` / `carry` signals — those feed the *other* strategies and the EOD Telegram
book. **Consequence:** stale EOD feeds do not block the trading-window session, so
the auto catch-up download is platform hygiene that runs in the background and must
never delay the runner.

### 1.4 Answer to "what if the EOD collector didn't run one night?"

Traced through `download_all_data.py`:

- Incremental with a **7-day trailing lookback** (`LOOKBACK_DAYS = 7`); each ingest
  starts at `latest_stored − 7d`. **One missed night self-heals on the next run;**
  any gap **≤ 7 sessions** self-heals silently.
- A gap **> 7 sessions does NOT self-heal** — `_incremental_start` never re-probes
  earlier dates and `_warn_unresolved_calendar` only *prints* a NOTE. Recovery needs
  a manual `--full` run.
- **No per-day catch-up:** `schedule_worker.is_due()` is keyed on *today* only. A day
  the worker was dead is never retried later; the 7-day lookback is a side effect that
  happens to cover short gaps, not a designed retry.

**Load-bearing consequence:** the preflight must assert feed freshness against the
expected last trading session — never "did the worker run." This operationalises the
project's own pitfalls: *"a freshness value printed but never asserted is
documentation, not a control"* and *"gating a multi-feed pipeline on one feed makes
every other feed optional"* (`eod_decision.decide()` fires on futures alone).

### 1.5 Constraints that fix the design's shape

1. **Upstox OAuth is interactive and cannot be automated.** `needs_daily_refresh` is
   True every new calendar day → this is "preflight + supervised start," not
   unattended cron. The "one command" means *one command a human runs after clicking
   through the browser once.*
2. **Instrument-master refresh is coupled to the OAuth callback, not to startup.**
   Reuse a still-valid token across a restart and the master silently never refreshes
   that day. Preflight checks master freshness **independently** of token freshness.
3. **Poller must precede runner, and "file exists" is not enough.**
   `ChainSnapshotMarksSource.check_available()` runs at driver construction; a
   *valid-but-empty* cache passes it and yields `{}` marks → the runner prices
   nothing. Preflight requires **rows > 0 + recent heartbeat**, read via the
   bounded-retry reader path (a naive `duckdb.connect` contends with the poller's
   `os.replace`).

### 1.6 Verified live state (2026-08-09)

- No `STOP` file in `F:\Nifty`.
- `data/live_buffer/` **absent**, `data/options/` **absent** → ingestor and poller
  have never run this session; a runner started now would fail `check_available()`.
- `data/market_ingestor.pid` / `data/options/chain_poller.pid` **absent**;
  `data/_eod_worker.lock` → PID 16500 (EOD worker up, or stale — liveness must be
  verified, not inferred from file presence).
- `SpanRepository` reads `data/span/` (default `SPAN_DATA_DIR`), which holds a
  snapshot for 2026-08-06. SPAN is present but PAPER tolerates absence anyway.

---

## 2. Goals & non-goals

### Goals
- One foreground command that brings up the full trading-window stack after a human
  completes OAuth, in the correct dependency order, and keeps it alive.
- A fast (~5s), standalone, read-only preflight that gives an honest go/no-go and is
  reusable by the orchestrator and by a human ("is the platform healthy right now?").
- Convert printed-but-unasserted freshness values into enforced controls.

### Non-goals (explicit)
- **SPAN as a blocker** — PAPER tolerates its absence; SPAN is WARN only.
- **Day-type fact as a separate process** — it is the in-runner 13:00 `publish_hook`.
- **Automating OAuth** — structurally interactive.
- **LIVE execution mode** — this supervises the PAPER window (`ExecutionMode.PAPER`).

---

## 3. Architecture

Two independently shippable units under a new `scripts/ops/` package.

### 3.1 Managed children & the on-demand action

| Process (path) | Role | Native single-instance guard | Orchestrator's responsibility |
|---|---|---|---|
| `scripts/run_flask.py` | OAuth + dashboard | none | own a PID file; needed for the token handshake |
| `scripts/market_ingestor.py` | live feed → live buffer | **commented out** (`market_ingestor.py:243`) | own the guard it lacks |
| `scripts/nifty_shield_paper/chain_poller.py` | marks → chain cache | ✅ `data/options/chain_poller.pid` | spawn; defer to its lock; read heartbeat |
| `scripts/nifty_shield_paper/session.py` | the PAPER session (Phase B daily op) | none | own a PID file; park until marks flow; **cooperative clean stop** (§5.2), spawned in a new process group |
| `scripts/schedule_worker.py` (EOD) | data pipeline daemon | ✅ `data/_eod_worker.lock` | adopt if alive; start if its lock PID is dead |
| `scripts/download_all_data.py` | stale-feed catch-up | n/a (one-shot) | dispatch in the **background**, non-blocking |

**Runner process identity — critical.** The supervised session is
`scripts/nifty_shield_paper/session.py`, **not** `nifty_shield_paper_runner.py`.
The latter is the Phase A wiring entry point; `session.py` is the daily Phase B op —
it owns the isolated `--data-root data/nifty_shield` evidence root, the recorder
(replay-evidence input), per-session audit/telemetry finalization, the heartbeat
watchdog, and exits non-zero on a guard/telemetry/divergence violation. Its CLI
(`session.py:242`) is `--date` (defaults to today IST), `--data-root`, `--chain-db`,
`--capital`, `--max-bars`, `--no-record`.

- **Spawn command:** `python scripts/nifty_shield_paper/session.py --date <today> --data-root data/nifty_shield`
- **Never pass `--no-record`.** A non-recorded session is excluded from the ≥20/≥30
  session count (F-B1); recording must be left on (the default).
- `session.py` has **no PID file of its own** — the orchestrator-owned PID guard is
  the sole single-instance control, which is acceptable because the orchestrator lock
  already prevents a second supervisor.

### 3.2 Locked decisions (from brainstorming)
- **Scope:** full platform supervisor — trio + EOD worker + auto catch-up.
- **Token handshake:** orchestrator manages Flask; if the token is stale it prints
  (and opens) `/ops/login/upstox`, then **blocks-polls** `credentials` until fresh.
- **Supervision:** **foreground** — the orchestrator is the parent console, restarts
  crashed children with backoff (respecting locks), and tears down on Ctrl+C / `stop`.
- **Runner start:** **parked** until marks flow (pre-open the poller idles, so the
  runner cannot construct; the supervisor waits rather than failing).
- **Catch-up:** **automatic and background** — never gates the runner.

### 3.3 PID / lock model
- Orchestrator lock: `data/ops/orchestrator.pid` (refuse a second orchestrator).
- Orchestrator-owned children (flask, ingestor, runner): `data/ops/<name>.pid`,
  written atomically after spawn.
- Natively-locked children (poller, EOD): the orchestrator reads *their* lock files
  for liveness; it never writes a competing PID file for them.
- Liveness everywhere is **PID-alive**, not file-presence (reuse the Windows-safe
  `_pid_alive` pattern already in `schedule_worker.py` / `chain_poller.py` —
  `OpenProcess`, never `os.kill(pid, 0)` on Windows).

---

## 4. Preflight (`scripts/ops/preflight.py`)

Read-only. Pure check functions over injectable paths + clock (mirroring
`eod_job.Deps` and the poller's injectable seams) so they unit-test without
processes. Emits a human report and `--json`; exit code 0 = OK/WARN-only,
non-zero = BLOCK.

### 4.1 BLOCK checks (no valid session possible)
| Check | Signal |
|---|---|
| Upstox token | `credentials.has_upstox_token and not credentials.is_token_expired` |
| Kill switch | no `STOP` file in `F:\Nifty` |
| Marks warm | `chain_cache.duckdb` exists **AND** `rows > 0` **AND ≥1 row with `ltp > 0`** **AND** heartbeat `last_snapshot` within N s (market hours) — via the R1-fixed bounded-retry `_connect` |
| Live VIX | ingestor alive **AND** `NSE_INDEX|India VIX` has a bar within M min (market hours) |

**`ltp > 0` matters:** the marks reader prices only `ltp > 0.0` rows, so a cache full
of `ltp = 0` rows (e.g. a market-closed snapshot) resolves to `{}` and the runner
prices nothing despite `COUNT(*) > 0`. The check must confirm at least one priceable
row, or rely on the heartbeat `rows` + freshness.

The marks + VIX checks are **market-hours-gated**: pre-open they degrade to "poller
alive / ingestor alive" rather than "rows > 0 / recent bar," because neither can be
warm before 09:15. **Pre-open poller liveness is read from its PID file
(`data/options/chain_poller.pid`), never the heartbeat** — the poller only writes a
heartbeat on a successful swap and idles outside hours, so pre-open the heartbeat is
yesterday-stale and would false-BLOCK.

### 4.2 WARN checks (run, but surface)
| Check | Signal |
|---|---|
| SPAN | snapshot present for `expected_span_date()` in `data/span/` |
| Instrument master | age ≤ 1 day — **independent of token** |
| EOD feeds | equity / futures / options / index each ≤ 1 expected session behind (reuse `eod_decision.FEED_STORES` + `_max_index_date`) |
| EOD worker | `_eod_worker.lock` PID alive |

### 4.3 Interface
```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    tier: str          # "block" | "warn"
    ok: bool
    detail: str

def run_preflight(now: datetime, *, market_hours_gated: bool = True) -> list[CheckResult]: ...
def verdict(results: list[CheckResult]) -> str:   # "GO" | "NO-GO"
```
`main()` prints the table + verdict and returns `0` (GO) / `1` (NO-GO).

---

## 5. Orchestrator (`scripts/ops/orchestrator.py`)

Foreground supervisor. Subcommands: `start` (default), `status`, `stop`.
`status` / `stop` operate purely via PID/lock files, so they work from a second
console while `start` holds the first.

### 5.1 Start state machine
```
0. Acquire orchestrator lock (refuse if another orchestrator is alive).
1. load_dotenv(); if STOP file present → refuse (hint: `orchestrator start --clear-stop`).
2. Start Flask (if not already alive on its PID file).
3. Token gate:
     token fresh?  yes → continue
                   no  → print + webbrowser.open(/ops/login/upstox);
                         poll credentials every 5s until fresh (timeout T, default 10m).
     (A fresh OAuth also refreshed the instrument master via the callback.)
4. Start market_ingestor + chain_poller.
5. Warm-up wait:
     ingestor CONNECTED (heartbeat) AND poller rows>0 + recent heartbeat.
     pre-open → PARK: poll every 30s for market-open + warm-up; the runner start
     waits here without failing.
6. Dispatch background catch-up: if any EOD feed is stale, spawn download_all_data
     (incremental) as a detached one-shot. Non-blocking; result logged, never gates.
7. Preflight — final snapshot gate. BLOCK → report + halt (children already up are
     left for inspection or torn down per flag).
8. Start the session: `python scripts/nifty_shield_paper/session.py --date <today>
     --data-root data/nifty_shield` (recording ON; marks warm by construction of step 5).
9. Ensure EOD worker alive — adopt if its lock PID is alive, else start it.
10. Enter the supervise loop.
```

### 5.2 Supervise loop
- Poll each managed child's liveness on a tick (e.g. 5s).
- A dead child (that we started and did not intend to stop) → restart with capped
  exponential backoff, re-checking the child's own lock first so we never double-spawn.
- Surface a compact status line / write `data/ops/orchestrator_status.json` for the
  dashboard.
- **Token expiry mid-session** (~22h; rare within a window): ingestor/poller already
  log loudly + late-reconnect. The supervisor re-surfaces the login prompt; it does
  **not** kill the session.
- Ctrl+C / `stop` → graceful teardown: signal only the children **we** started;
  an *adopted* EOD worker keeps running. Remove our PID files.
- **Session shutdown is a cooperative clean stop, never a hard kill.** Today
  `session.py`'s `driver.run()` returns only on exhaustion / `max_bars` / an
  in-process `stop()` / `KeyboardInterrupt`; the `finally` block *finalizes the
  session evidence* (audit + telemetry + recorder package). A `terminate()`/hard kill
  mid-run loses that package and the session is excluded from the count. Two facts
  make external stop non-trivial and drive the mechanism:
  - The `STOP` file is **not** a session-stop — it is checked only in
    `ExecutionHandler.process_signal` (`handler.py:598`) and merely activates the
    handler kill switch (halts *new trades*); the driver loop keeps running.
  - On Windows, `CTRL_C_EVENT` cannot be targeted at one child (it hits the whole
    console group), and a child spawned with `CREATE_NEW_PROCESS_GROUP` ignores
    `CTRL_C` while `CTRL_BREAK_EVENT` does **not** raise `KeyboardInterrupt` by default.
  - **Mechanism (see Task in the plan):** `session.py` installs a `SIGBREAK`
    (Windows) / `SIGTERM` (POSIX) handler that calls `driver.stop()` → the loop drains
    to `STOPPED` and the existing `finally` finalizes. The orchestrator spawns
    `session.py` in a **new process group** and, on stop, sends `CTRL_BREAK_EVENT`
    (Windows) / `SIGTERM` (POSIX), then **waits for the clean exit** (bounded join;
    escalate to kill only if it hangs past the finalize budget). This is the single
    most important shutdown detail. Other children (ingestor, poller, Flask) take
    normal `SIGTERM`/`terminate`.

### 5.3 status / stop
- `status`: read every PID/lock file + heartbeats → one table (process, PID, alive?,
  last heartbeat, warm?). Also runs preflight in `--json` for the freshness picture.
- `stop`: SIGTERM the orchestrator-owned children via their PID files; leave adopted
  daemons; clear `data/ops/*.pid`.

---

## 6. Error handling & edge cases
- **STOP file at start** → refuse (never silently clear a kill switch).
- **Externally-started duplicate** (operator hand-ran the ingestor) → detected via PID
  file; orchestrator refuses to spawn a second and adopts / reports instead.
- **Poller never warms** (token revoked after login, chain empty) → warm-up wait times
  out with a loud BLOCK; the runner is never started against `{}` marks.
- **Catch-up download fails / times out** → logged WARN only; the live session is
  unaffected (it does not read those stores — §1.3).
- **Session hard-killed mid-finalize** → the session package is lost and the day is
  excluded from the ≥20/≥30 count. Prevented by the SIGINT-and-wait shutdown (§5.2);
  the supervisor must never `terminate()` `session.py` on a normal stop.
- **Orchestrator itself crashes** → children survive (own PID files/locks); a fresh
  `start` adopts the living ones and fills the gaps (idempotent).

---

## 7. Testing
- **Preflight:** unit tests over injected paths + frozen clock — token fresh/stale,
  empty vs. populated marks cache, missing VIX, stale feeds, market-hours gating.
  No processes.
- **Orchestrator start machine:** injected child-spawner stub + fake clock + fake
  credentials that "go fresh" after N polls → assert order, parking, background
  catch-up dispatch, final-gate halt. No real subprocesses.
- **PID/liveness helpers:** reuse the existing Windows-safe `_pid_alive` (already
  tested via the poller); add tests for adopt-vs-spawn and no-double-spawn.
- **Smoke:** a real `--dry-run` start that spawns nothing, only prints the plan.

---

## 8. Open items / future
- LIVE (`ExecutionMode.LIVE`) supervision — out of scope; would add a real
  `UpstoxAdapter`, broker reconciliation, and SPAN promotion to BLOCK.
- Optional `fetch_span_params.py` in the background catch-up (currently manual).
- A dashboard panel reading `data/ops/orchestrator_status.json`.
