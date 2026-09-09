# Task note — CAS marking, instrument-master refresh, log rotation

**Created:** 2026-09-09, during the live PAPER window.
**Execute:** after the derivatives close (15:40 IST), and see the ordering constraint in A4.
**Status:** NOT STARTED. No code was changed and no store was written while writing this note.

Findings are in `OPS_STARTUP_SEQUENCE_AUDIT_2026-09-09.md` (§3 CAS, §4 master). This note is
the execution plan, plus two prerequisites discovered after that audit was sent.

---

## Correction to the audit's §4 — read this first

The audit says the instrument master is refreshed "only by hand … operator-triggered
dashboard actions." **That is wrong and the real cause is sharper.**

`flask_app/blueprints/ops/routes.py:184` is the **OAuth callback**, not a button. Its own
comment: *"Refresh instrument master on fresh token (once per OAuth, not per restart)."*
So the refresh **is** automatic — but only when the operator completes a fresh Upstox
login. Yesterday's 09:27 refresh was that login firing. Today the token was still valid,
so the orchestrator's token gate never opened the login, so the master never refreshed.

**It silently skips on every day the token survives from the previous day.** That is the
defect, and it will recur on every such day.

---

## A. CAS synthetic marking

### A0. Two prerequisites that would break a naive fix

**A0.1 — the Cat-I table does not cover September. This is blocking.**

```
cat1_isin_symbols(2026-08-20) -> 208 symbols
cat1_isin_symbols(2026-08-28) -> 210 symbols
cat1_isin_symbols(2026-09-08) ->   0 symbols
```

`data/cas/cas_category.duckdb` was last built 2026-08-30 (max `effective_from` 2026-08-26).
`mark_synthetic_bars.run()` **raises** `RuntimeError` on an unresolved session — and it
iterates files in sorted order, so it would mutate every August file and then raise on
2026-08-31, leaving a partial application. **Rebuild the category table first.**

`build_cas_category.py` derives from `futures_bhavcopy.duckdb`, which is current
(`max(trade_date) = 2026-09-08`), so a rebuild will cover through yesterday.

**A0.2 — the marker overwrites its own copy-first baseline.**

`mark_synthetic_bars.run()` does `shutil.copy2(path, path.with_suffix(".duckdb.pre_cas_mark"))`
unconditionally. Re-running it over an already-marked file **replaces the original baseline
with the mutated version**. At least `1m/2026-08-28.duckdb.pre_cas_mark` already exists.
This is the pitfall register's *"never let the re-run overwrite the copy-first baseline
snapshot of an already-marked file"*, live in the code.

Fix: skip the copy when the baseline already exists. Small guard inside `run()`.

### A1. Hook the marker into the pipeline

Nothing calls `scripts/cas/mark_synthetic_bars.py` today. Hook it at the end of
`download_all_data._download_1m_candles`, after a successful fetch:

```
futures bhavcopy (step 2)  ->  build_cas_category  ->  mark_synthetic_bars(apply=True)
```

Both the orchestrator's start-of-session catch-up and the EOD chain run through
`download_all_data`, so this single seam covers both.

**Chosen failure handling: hook the category rebuild immediately before the marker**, so
the `RuntimeError` path is unreachable in normal operation. Do *not* instead wrap the
marker in a bare try/except — that converts a stale category table back into the silent
gap this task exists to close. If the category rebuild itself fails, fail the 1m step
(`all_ok = False`) and let the pipeline continue, matching how the other steps behave.

### A2. Leave `is_synthetic = FALSE` in the upsert — decision, with the rejected option

`fetch_upstox_historical.py:258` resets `is_synthetic = FALSE` on conflict. **Keep it.**
The marker is deterministic and idempotent, and recomputing the flag from the row's current
data is strictly safer than carrying a mark across a data change.

**Rejected: removing `is_synthetic = FALSE` from the `DO UPDATE SET` list.** It looks like
the obvious fix and it is not — a corrected bar that now carries real volume would keep a
stale `TRUE`. Do not "fix" this later by deleting the reset. The reset is only harmful
because nothing re-marks; A1 is what makes it correct.

Consequence to accept: a direct hand-run of `fetch_upstox_historical.py` outside
`download_all_data` still erases marks. Re-run the marker after any such run.

### A3. Backfill

Once A1 is in place, **the backfill is just the EOD chain doing its job** — the post-close
`download_all_data` run will re-fetch the trailing window, rebuild the category table and
re-mark. No separate manual pass is needed, and `run()` re-marks every session
`>= CAS_EFFECTIVE (2026-08-03)` anyway, not only the trailing window.

If A1 is not landed the same evening, a manual `python scripts/cas/mark_synthetic_bars.py --apply`
is valid **only after** A0.1 and A0.2 are done and **after** the EOD download has finished.

### A4. Ordering constraint

The EOD chain runs `download_all_data` after the close, and its 1m step re-fetches a
7-day trailing window with the `is_synthetic = FALSE` reset. **Any marking applied before
that run is erased by it.** Land A1 first, or sequence the manual pass after EOD.

### A5. Verification

Re-run the scan from the audit (marked vs CAS-signature bars per session) over
2026-08-03 → today and assert they reconcile:

- 2026-08-31 → 09-08 should go 0 → ~2,576 per session.
- 2026-08-21 → 08-28 should go ~262–294 → ~2,870 per session.

The 08-21 → 08-28 band carries a different universe (228 `NSE_EQ` symbols vs 200) and its
near-total mark loss is **unexplained**. If those sessions reconcile after the backfill,
the anomaly was mark erosion. If they do not, that is a **separate finding** to open, not
a failed fix.

---

## B. Instrument-master refresh — wiring, not writing

### B1. What already exists

`fetch_instrument_master.run_refresh()` is a finished scheduled-job entry point: IST
trading-day guard, download, validate, publish, exit codes, and **every failure path
preserves the prior snapshot**.

It has **no caller** in the repo (only its own `__main__`), and there is **no registered
Windows scheduled task** for it — `Get-ScheduledTask` shows only `SE3SpreadCollector`. It
was built for an OS scheduler that was never created.

### B2. The fix

Call `run_refresh()` from `orchestrator.start_sequence`, **before the poller starts** — the
chain poller resolves expiries from this store, so refreshing after it boots leaves it on a
stale master for the session.

- **No Upstox token needed.** It downloads a public assets URL
  (`assets.upstox.com/market-quote/instruments/exchange/complete.json.gz`), so it can run
  before the token gate.
- **Non-fatal.** A non-zero return leaves the prior snapshot intact; log a warning and
  continue. Preflight already carries `WARN instrument_master` for staleness.
- Add it as a `Deps` callable (like `dispatch_catchup`) so the start sequence stays testable.

**Rejected: putting it in `download_all_data.py` as a step 0.** That is dispatched *after*
the poller starts, so the poller would still boot against a stale master.

**Keep the OAuth-callback refresh** at `routes.py:184`. It is a harmless backstop; it is
just not sufficient on its own.

### B3. Verification

`data/instruments/nse_fo_instruments.duckdb` mtime is today, and preflight's
`instrument_master` WARN clears.

---

## Execution order

1. Wait for the derivatives close (15:40) and let the EOD chain's `download_all_data` finish.
2. A0.2 — baseline-overwrite guard in `mark_synthetic_bars.run()`.
3. A0.1 — `python scripts/cas/build_cas_category.py`; verify `cat1_isin_symbols` resolves
   non-empty for the newest session before going further.
4. A1 — hook `build_cas_category` + `mark_synthetic_bars` into `_download_1m_candles`.
5. B2 — wire `run_refresh()` into `start_sequence` before the poller.
5b. C4 — swap `setup_logger`'s handler for a locking one (independent of A and B; can land separately).
6. Run the marker (or the whole `download_all_data`) once; verify per A5 and B3.
7. Tests for both seams; commit.

**Not in scope:** the supervisor respawn defect and the ingestor's disabled `_acquire_lock`
(`OPS_INGESTOR_RESPAWN_LOOP_2026-09-09.md` §7 and the startup audit §5) — those are a
separate fix and need an operator decision on which pidfile is authoritative. The breaker
applied at 09:40 holds until then.

**Branch note:** the working tree carries 19 modified files of unrelated NiftyShield work on
`fix/options-wall-tp-sl-thresholds`. These ops fixes should not land mixed into that.

---

## C. Log rotation dies under multi-process sharing (added 13:05)

### C1. What happened

At 10:18 `logs/options_provider.log` hit the 10 MB cap and could not roll over:

```
PermissionError: [WinError 32] The process cannot access the file because it is
being used by another process:
  'logs\options_provider.log' -> 'logs\options_provider.log.1'
```

`setup_logger` (`core/logging/logger.py`) builds a plain
`RotatingFileHandler(maxBytes=10MB, backupCount=5)`, which is **not multi-process safe**.
`core/data/options_provider.py:23` calls `setup_logger("options_provider")` at *module
import*, so every process importing it opens the same file with its own rotating handler —
here `chain_poller.py`, `options_wall_poller.py` and `run_flask.py`. On Windows the rename
fails while any other process holds the handle.

### C2. Impact — diagnostic, not functional

`doRollover()` closes the stream and renames *before* the record is written, so a failed
rename means the record is **dropped**, not appended. The file therefore froze at
10,485,881 bytes with mtime 10:18 and every subsequent write was discarded.

**~2h46m of options-provider logging was lost** (10:18 → 13:04). Nothing else broke:
`logging` swallows handler errors into `handleError`, so the pollers ran normally
throughout — heartbeats stayed fresh and the chain kept publishing.

It cleared only because the stack was restarted around 13:04, which released the handles
and let the rotation finally succeed (`options_provider.log.1` now holds the frozen 10 MB).
It did not recover on its own.

### C3. Scope — nine more loggers have the same latent defect

Ten module-level `setup_logger` calls live in `core/`, each duplicated into every importing
process: `options_analytics`, `options_provider`, `execution_handler`, `watchdog`,
`options_publisher`, `options_wall_poller`, `loop_driver`, `event_journal`,
`guarded_signal_source`, `telemetry_publisher`. `execution_handler.log` already rotated
once (2026-09-07) and would fail the same way whenever two of its importers overlap.

**No log is near the cap right now** (largest is `chain_poller.log` at 40.7%), so a repeat
today is unlikely. This is not urgent.

### C4. Fix — recommended: a locking rotating handler

Swap the handler inside `setup_logger` for `concurrent_log_handler.ConcurrentRotatingFileHandler`
(PyPI `concurrent-log-handler`), which takes a cross-process file lock around the roll. It
is a near drop-in for `RotatingFileHandler`, keeps one file per component — which is what
makes these logs readable — and matches the standing "prefer battle-tested libraries over
hand-rolled" rule. Cost: one new dependency.

Alternatives considered:

- **Per-process filenames** (derive the log name from the entry-point script). No new
  dependency and Windows-safe, but it splits one component's history across three files,
  which is a real cost when reconstructing an incident.
- **Let `core/` modules use `logging.getLogger(__name__)` and configure handlers only in
  entry-point scripts.** Architecturally the right answer and it removes the sharing
  entirely — but it touches all ten call sites and changes where every log line lands.
  Worth doing deliberately, not folded into this fix.

### C5. Verification

Force a roll on a shared logger with two importing processes running (temporarily lower
`maxBytes`, or write past the cap) and confirm both the roll and the continued append
succeed with no `WinError 32`.

---

## D. The driver latches a missed checkpoint silently (added 13:35)

`core/runtime/driver.py:732` — when the 13:00–13:30 retry window expires without a ready
fact, the driver adds the session to `_published_sessions` **without calling the publish
hook**. The hook is what journals `FACT_PUBLISH_SKIPPED`, so a genuine miss leaves *no
record at all*: no fact, no journal line, nothing to diagnose from.

Today this did not bite — the checkpoint fired at 13:01 and today's fact is in
`data/nifty_shield/facts.duckdb` (`BullTrend`, conf 0.5368, vix 11.59, `live@21e2f4f`).
But the silent branch is why the new panel has to *explain* an empty reason rather than
show a blank field.

Fix: journal a `FACT_PUBLISH_SKIPPED` (reason: "retry window expired without a ready
bar") on the expiry branch, so a miss is as durable as a not-ready. Display-side
mitigation already shipped in the panel; this is the durable half.

**Related, worth deciding separately:** two facts stores have diverged. The session writes
`data/nifty_shield/facts.duckdb` (`session.py:223`), while
`data/features/day_type/day_type_facts.duckdb` — the global/offline store — last received a
live row on 2026-08-28. Reading the global one reports a fired checkpoint as missing (it
did, to me, today). Whether the split is intended session-scoped evidence or an unnoticed
divergence is an open question, not a fix in this batch.

---

**Related, separate track:** the 90% credit floor was checked after the close — see
`docs/reports/index_research/NIFTY_SHIELD_CREDIT_FLOOR_CALIBRATION_2026-09-09.md`. Verdict: the floor is
not the problem; the reference it compares against is priced at India VIX flat across every leg,
which overstates a 6-DTE vertical by ~30%. Fix the vol input first, then calibrate. No strategy
parameter was changed.
