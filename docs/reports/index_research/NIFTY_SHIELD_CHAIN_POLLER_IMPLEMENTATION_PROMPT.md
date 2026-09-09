# NiftyShield — Option-Chain Poller (E7-4 marks populator) — Implementation Prompt

**For:** DeepSeek V4 (implementer). **Author/reviewer:** Claude.
**Mode:** DeepSeek implements from this prompt; Claude reviews. Do **not** touch
the frozen strategy package `strategies/nifty_shield_v1/` (identity `89fcdd6` /
`c5b722ff…536c`). This is new ops/composition-root tooling only.

---

## 1. Why this exists (the gap)

The NiftyShield PAPER runner reads real Upstox V3 option marks from a DuckDB
cache via `ChainSnapshotMarksSource`
(`core/execution/options/nifty_shield_marks.py`), which opens
`data/options/chain_cache.duckdb` and reads the `option_chain_snapshot` table.

**Nothing writes that file.** Verified:

- The only writer of the `option_chain_snapshot` schema is
  `OptionsProvider._persist_to_duckdb`, whose path is
  `data/market_data/options_poller.duckdb` — a **different file**
  (`app_facade/options_facade.py:49`). `chain_cache` appears in exactly three
  files repo-wide: the two NiftyShield readers and the runbook.
- The one background engine (`scripts/run_options_engine.py` → `OptionsPoller`
  → `OptionsFacade` → `OptionsProvider(read_only=True)`) writes **nothing**:
  `_persist_to_duckdb` early-returns on `read_only` (`options_provider.py:388`).
  It publishes to ZMQ only.
- `data/options/` does not exist on disk.

Consequence: `session.py` cannot start — `ChainSnapshotMarksSource.check_available()`
(F3) raises `MarksSourceUnavailable` because the file is absent. E7-4 requires
real V3 chain marks for the struck legs; this poller supplies them.

**Operator decision (2026-08-09):** build a **dedicated NiftyShield chain
poller** — self-contained, owned by NiftyShield, writing directly to
`data/options/chain_cache.duckdb`. Do **not** couple to the dashboard cache.

---

## 2. Two hard constraints — both verified empirically, both load-bearing

### 2.1 DuckDB cross-process write lock (measured, DuckDB 1.4.3, Windows)

A held **read-write** DuckDB connection **blocks** any other process from opening
the same file even **read-only** → `IOException` ("process cannot access"). The
runner's `ChainSnapshotMarksSource._connect()` opens a **fresh read-only
connection on every `marks()` call**. Therefore:

> If the poller holds its write connection open across the poll sleep, every
> `marks()` call during that time raises → `MarksSourceUnavailable` → under F3
> the runner **refuses to start / skips every entry**. This is not tolerable.

Measured results (reproduced in a two-process test):
- read-only **while** a writer holds the lock → **FAIL** (IOException)
- read-only **after** the writer closes → OK
- connect → write → **close** per cycle, read between cycles → OK

**Mandated write pattern — atomic swap, fresh single-snapshot DB per cycle:**

1. Each poll cycle, write the snapshot to a **temp file**
   `data/options/chain_cache.tmp.duckdb` (create/overwrite; a fresh DB), then
   `conn.close()`.
2. `os.replace(tmp, "data/options/chain_cache.duckdb")` — atomic on Windows for
   same-directory replace. The reader only ever opens the **target** path, which
   the poller never holds open → the reader effectively never contends with a
   live writer.
3. `os.replace` can transiently fail with `PermissionError`/sharing-violation if
   the reader has the target open at that instant. The **poller** retries the
   replace (small bounded backoff, e.g. 5×100 ms); the reader stays untouched.
   A replace that never succeeds within the cycle is logged loudly and retried
   next cycle (the previous good snapshot remains in place — never delete it).

Do **not** modify `ChainSnapshotMarksSource` — its F3 semantics
(raise on unavailable, `{}` on valid-but-empty) are the contract. The swap
design keeps them correct without a reader change.

### 2.2 One `snapshot_timestamp` per cycle (latent bug — do not reproduce)

The `option_chain_snapshot` table defines
`snapshot_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`, evaluated
**per row**. `OptionsProvider._persist_to_duckdb` relies on that default, so each
row of one chain gets a slightly different timestamp. But the reader does:

```sql
SELECT tradingsymbol, ltp FROM option_chain_snapshot
WHERE snapshot_timestamp = (SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot)
  AND tradingsymbol IN (...)
```

With per-row timestamps, `MAX` matches **only the single last-inserted row** →
the marks source can price at most one leg. **The poller must stamp one explicit
`snapshot_timestamp` value for every row of a cycle** (compute `now` once, pass
it to every INSERT). Because each cycle writes a fresh single-snapshot DB (§2.1),
`MAX(snapshot_timestamp)` trivially equals that cycle's timestamp and every row
shares it. Add a test asserting all rows in a written cache share one
`snapshot_timestamp`.

---

## 3. What to build

`scripts/nifty_shield_paper/chain_poller.py` — a standalone, long-running poller.

### 3.1 Data source (reuse, don't reinvent the fetch)

Reuse `OptionsProvider` **only for the Upstox V3 fetch**, not its persistence:

- Construct `OptionsProvider(read_only=True)` (or a fetch-only path) so its own
  `_persist_to_duckdb` never runs — you own persistence.
- Call the existing fetch to get `List[OptionChainRow]` + underlying LTP for the
  near-weekly expiry. Nifty 50 weekly expiry = Tuesday
  (`get_weekly_expiry("NSE_INDEX|Nifty 50")`).
- If `fetch_option_chain` on a read-only provider does not perform the API call
  (because it short-circuits somewhere on `read_only`), call the lower-level
  `_fetch_from_upstox(underlying, expiry)` directly, or add a minimal fetch-only
  entry — but do **not** widen `OptionsProvider`'s write surface.

### 3.2 Symbols / scope

- Underlying: `NSE_INDEX|Nifty 50` only (NiftyShield's `NF_SYMBOL`). Make the
  index list a CLI arg defaulting to Nifty 50; do not add BankNifty yet.
- Populate the **full near-weekly chain** (all strikes the API returns for the
  ATM-centered band). The runner strikes an iron-fly then queries by
  `tradingsymbol`; a full chain guarantees every struck leg has a mark.

### 3.3 Persistence (your own writer, atomic-swap)

- Create the target `option_chain_snapshot` table with the **same schema** as
  `OptionsProvider._init_db` (copy it — same columns/types) so the reader's
  `SELECT tradingsymbol, ltp … WHERE snapshot_timestamp = MAX(...)` works
  unchanged.
- Each cycle: `now = datetime.now()`; open the temp DB read-write; create the
  table; INSERT every row with `snapshot_timestamp = now` (explicit, §2.2);
  commit; **close**; `os.replace` into place with retry (§2.1).

### 3.4 Lifecycle / loudness (respect the repo's pitfalls)

- **Token:** read Upstox token via `core.auth.credentials` (same as
  `market_ingestor.py`). If absent/stale → log loudly and keep retrying every
  30 s; do **not** attempt to obtain it (interactive Dashboard login only).
- **Market hours:** poll every 5 s during market hours
  (`core.database.utils.market_hours.MarketHours`); outside hours, idle-sleep
  (do not spin the API). Do **not** write a `.404`-style permanent miss marker
  for anything (the equity miss-cache defect). A fetch failure is a transient,
  logged event — never recorded as "no data".
- **Never silently swallow:** catch only the specific fetch exception around the
  Upstox call; a parse/write failure must surface (log ERROR), not be
  misread as "market closed". On repeated consecutive fetch failures during
  market hours, escalate log level so the operator sees the marks feed is down.
- **Bootstrap for preflight:** on start, ensure the target file exists with a
  valid (possibly empty) `option_chain_snapshot` table so
  `ChainSnapshotMarksSource.check_available()` passes even before the first
  successful fetch. An empty-but-valid cache is a legitimate `{}` (F3), not an
  error.
- **PID + signals:** write a PID file (mirror `market_ingestor.py`'s pattern),
  handle SIGINT/SIGTERM to stop cleanly.
- **CWD:** the runner's `STOP` kill-switch is CWD-scoped — this poller must not
  create or remove any `STOP` file, and its own working directory is irrelevant
  to the runner's. Just never emit a `STOP`.

### 3.5 Freshness signal (for the future preflight — build the hook now)

Expose the latest `snapshot_timestamp` cheaply so a later preflight can assert
"cache is populating": either the reader's `MAX(snapshot_timestamp)` (already
available) or a tiny `data/options/chain_poller_heartbeat.json`
(`{"last_snapshot": ISO8601, "rows": N, "expiry": "…"}`) written after each
successful swap. Prefer the heartbeat JSON — it also distinguishes "poller alive
but market closed / empty chain" from "poller dead".

---

## 4. Tests (add under `tests/` — new files only)

1. **Concurrent read never raises (the §2.1 guarantee).** Two processes/threads:
   one runs the poller's write-cycle N times against a temp dir; the other calls
   `ChainSnapshotMarksSource(path).marks([...])` in a tight loop for the whole
   duration. Assert **zero** `MarksSourceUnavailable` and that marks are returned
   for known symbols. This is the load-bearing test — it proves the design.
2. **One timestamp per snapshot (§2.2).** After a write cycle, assert every row
   in `option_chain_snapshot` shares a single `snapshot_timestamp`, and that
   `ChainSnapshotMarksSource.marks([...])` returns **all** requested present
   legs (not just one).
3. **check_available passes on a freshly-bootstrapped empty cache**, and
   `marks()` returns `{}` (not raise) on it.
4. **Atomic swap leaves a valid DB** — after an interrupted/retried replace, the
   target is always a readable single-snapshot DB (never partial, never
   deleted).

Use a synthetic/stub chain (no live Upstox) for all tests — inject the row list,
do not hit the network.

---

## 5. Out of scope (explicitly deferred)

- The one-command orchestrator (ingestor + poller + session) — deferred by the
  operator to a follow-up with additional requirements.
- The preflight command itself — deferred, but build §3.5's freshness hook so it
  is cheap to add.
- BankNifty marks, LIVE mode, any strategy-package change.

---

## 6. Acceptance (Claude review checklist)

- [ ] Writes `data/options/chain_cache.duckdb` via atomic temp-swap; write
      connection never held across the sleep (§2.1).
- [ ] Every row of a cycle shares one explicit `snapshot_timestamp` (§2.2);
      reader returns all present legs.
- [ ] `ChainSnapshotMarksSource.check_available()` passes against the poller's
      output; `session.py` no longer refuses on the marks gate.
- [ ] Token/market-hours/failure handling is loud, never a silent miss; no
      `STOP` ever emitted; PID + clean signal shutdown.
- [ ] Concurrent read-while-write test green (zero `MarksSourceUnavailable`).
- [ ] No edit to `strategies/nifty_shield_v1/` or to
      `ChainSnapshotMarksSource`'s F3 semantics.
