# NiftyShield E007 — Phase B Forward-Window Runbook

**Status:** OPERATIONAL (Phase B). The PAPER window accrues ≥20 sessions AND
≥30 round-trips (datasheet §10) of live evidence before the PAPER Validation
Report is assembled and handed back for review + the operator's E007 grant.
**Identity:** `nifty_shield_v1` @ `89fcdd6` / `c5b722ff…536c` — **FROZEN, never
touch the strategy package.** **Prompt of record:**
`docs/reports/NIFTY_SHIELD_STAGE2_PAPER_VALIDATION_IMPLEMENTATION_PROMPT.md`
(Phase B = §3 "Operate the forward window"; evidence items §4.2/§4 A–I).

---

## 1. Evidence model

Every trading session produces one self-contained package under the isolated
window root:

```
data/nifty_shield/
  journal.jsonl                 accumulated runtime journal (whole window)
  trading/trading.db            accumulated PAPER trade ledger (whole window)
  metrics.json                  execution metrics
  heartbeat.json                watchdog heartbeat (live only)
  facts.duckdb                  live 13:00 regime-fact store
  sessions/{YYYY-MM-DD}/        one package per session
    meta.json                   session date, platform commit, recorder version
    bars.duckdb                 recorded driver bar stream (driver_bars) +
                                full-session NF/BN/VIX (session_bars)
    facts_bars/{date}.duckdb    per-day-store copy the replay fact hook reads
    marks.jsonl                 recorded option-marks call log (E7-4)
    signals.jsonl               recorded signal stream (deterministic fields)
    facts.duckdb                day_type_facts copy at session close
    span_snapshot.pkl           captured SPAN snapshot (margin determinism)
    audit.json                  per-session journal audit snapshot (F4)
    telemetry.json              per-session telemetry snapshot + archive
    metrics.json                per-session risk-metrics snapshot
    session_summary.json        combined per-session summary
  window_evidence.json          assembled window evidence (report input)
```

The live runner records at the composition-root seams (source, marks provider,
bar provider) — **not** the stores — so a session's package is exactly what the
pipeline consumed, independent of later backfills.

## 2. Daily session run (the core op)

Prerequisites each session:

- Upstox token present/valid (`credentials` login via the Dashboard).
- The market-data ingestor (`scripts/market_ingestor.py`) is up and writing
  live 1m bars to `data/live_buffer/candles_today.duckdb` (Nifty 50 + Nifty
  Bank + India VIX), else the 13:00 fact cannot be produced.
- The option-chain cache (`data/options/chain_cache.duckdb`) is populating
  (E7-4 marks). The runner refuses to start on a broken cache (F3).

Run the session (start before ~09:15, stop after 15:15 flat):

```powershell
python scripts/nifty_shield_paper/session.py --date 2026-08-11
```

On stop (Ctrl+C after the structure is flat by 15:15), the runner finalizes the
session evidence (telemetry archive, journal audit, metrics snapshot, session
package). A session that ends **before 15:15 with an open structure** does **not
count** — the audit must show the structure closed (`STRUCTURE_CLOSE`).

**The per-session audit is load-bearing (review F4): run it every session, not
just at report-assembly.** `session.py` does this automatically and exits
non-zero on any guard event, reverse divergence, or telemetry violation — a
broken session must never pass silently.

## 3. What makes a session count

**Counting predicate (F-B1) — the ≥20 / ≥30 headline counts only these.** A
session counts toward the window iff ALL of:

1. **Recorded** — the session ran with the recorder (`session_summary.json`
   `replay_inputs == True`). A `--no-record` session never counts.
2. **Telemetry clean** — `telemetry.json` `clean == True`
   (`BARS_PROCESSED`/`LOOP_ITERATIONS` session-consistent,
   `SIGNALS_RECEIVED/ROUTED/EXECUTION_CALLS` mutually consistent, guard
   counters 0). A telemetry gap excludes the session.
3. **Closed structure** — the session produced ≥1 structure that fully closed
   (`StructureAudit` for that session with `status == "entered"` and
   `closed == True`). A session that ends with an open structure, or a
   VIX-skip / no-entry day, does **not** count toward ≥20.

The assembler surfaces **raw + counting** numbers and the excluded sessions with
their reasons (`window_evidence.json` → `counting.*`), so no session is dropped
silently. The ≥30 round-trips headline counts only closed structures whose
session is a counting session.

Quality gates (apply to the whole window — a violation fails it regardless of
the count):

1. **Guard cleanliness** — `STRATEGY_ERRORS = STRATEGY_QUARANTINE_EVENTS =
   SIGNAL_CONTRACT_REJECTIONS = 0` across the whole window (§7.6). One event =
   the window fails; report, do not suppress.
2. **Journal audit** — every emitted signal → fill or journaled rejection;
   divergence one-directional; no reverse divergence (ADR-017).

## 4. Margin evidence (SPAN + ELM against real marks)

- Every entry must journal `ENTRY_MARGIN` with `NseMarginEngine` SPAN + ELM
  figures computed against real option-chain marks (E7-4). The engine falls
  back to flat-rate `MarginTracker` (journaled `engine=MarginTracker`) when no
  current SPAN snapshot exists — **such a session does not satisfy §7.7** and
  is flagged in the report.
- **SPAN does NOT gate the session count (F-B1 decision).** A missing current
  SPAN snapshot gates only the §7.7 SPAN+ELM sub-requirement — such a session
  still counts toward ≥20/≥30, but its margin evidence is flagged
  (`flat_sessions`), and §8 acceptance gate 5 is not met for it.
- The captured `span_snapshot.pkl` per session makes replay reproduce the exact
  margin figures.

## 5. Replay evidence (run ≥1 recorded session, anytime after the session)

```powershell
python scripts/nifty_shield_paper/replay.py --session 2026-08-11
```

Re-drives the recorded package through the real composition root in REPLAY and
diffs: signal stream byte-identical, ledger deterministic fields (symbol, side,
quantity, fill price, signal_id) match, fact-identity match, replay guards 0,
reverse divergence none. Standing exclusions: `trade_id`/`broker_id` UUIDs and
journal wall-clock. Writes `sessions/{date}/replay_result.json`; exit 0 = PASS.

> At least one session must be replayed before the report is assembled (§4.2
> replay row).

## 6. Kill-switch drill (E7-5 — one operator drill mid-window)

```powershell
python scripts/nifty_shield_paper/drill.py --session 2026-08-XX
```

The drill re-drives a recorded session, injects the `STOP` file at a
deterministic point before the 13:00 entry, and verifies: `KILL_SWITCH_ACTIVATED`
journaled exactly once (IN-001), the entry blocked + journaled (`ENTRY_SKIPPED`
"every leg rejected by a handler gate"), zero fills, the loop still running to
the end of the corpus (kill-switched-but-running), and a clean re-run after the
STOP removal (restart per the runbook — the kill switch is not sticky across a
restart). Evidence: `sessions/{date}/drill/drill_result.json`.

The `STOP` file's lifetime is strictly scoped (F-B3): `run_drill` removes it on
every exit path (`try/finally`), so a failed drill can never leak a `STOP` into
the operator's CWD — a leaked `STOP` would silently kill-switch the next live
session.

> In a LIVE setting the same procedure applies to the running `session.py`
> process: create `STOP` in the runner's CWD, confirm entry blocked + journaled,
> confirm heartbeat/telemetry alive, remove `STOP`, then restart the runner
> (recovery restores from the ledger). The automated REPLAY drill is the
> captured evidence artifact.

## 7. Assembling the report (at window close)

```powershell
python scripts/nifty_shield_paper/assemble_report.py --run-tests
```

Fills the **frozen marker-bearing template** —
`docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.skeleton.md` (the
committed, immutable template of record) — into the **generated output**
`docs/strategies/nifty_shield_v1/PAPER_VALIDATION_REPORT.md`, and writes
`data/nifty_shield/window_evidence.json`. The ≥20/≥30 headline counts only
**counting** sessions (F-B1); raw and excluded numbers are in the report and the
evidence JSON so nothing is silently dropped. Assembly is **idempotent** (F-B2):
re-running always succeeds and reproduces identical output — edit the skeleton
and re-assemble, never the generated report. It fails loudly if a skeleton
marker is missing or duplicated (a frozen-skeleton change must be reviewed).
`--run-tests` runs the full platform regression suite for the §6 attestation
(the standing pre-existing `tests/g1/test_g1_closure_guard.py` red on `main` is
the only allowed red; it is not strategy-attributable).

Then hand back the completed report for Claude's review and the operator's E007
grant (window dates, run commit, identity triple, all seven evidence items).

## 8. Acceptance gates (all must hold for E007)

1. ≥20 sessions **AND** ≥30 round-trips (1 RT = 1 structure fully closed;
   delta hedge is not an RT), or the §7.3 60-session escape with the shortfall
   ledgered. Deciding the escape AFTER seeing the count is prohibited.
2. Guard counters all 0 across the window.
3. Journal audit clean; divergence one-directional only.
4. Drawdown declared max (Rs 30,000 single / Rs 150,000 5-day) never breached —
   the handler drawdown gate tripping **is** the breach.
5. Margin gate exercised on every entry with real SPAN + ELM against real marks.
6. Kill-switch drill completed and captured.
7. ≥1 session byte-identical end-to-end (replay).
8. Full regression suite green at the window's platform commit (standing G1 red
   only, not strategy-attributable).

**A strategy-attributable restart resets the session-window clock (§4.2).**
Platform/ops restarts do not (recovery is a certified feature, §7.3).

## 9. Do not

- Edit `strategies/nifty_shield_v1/` or move `config_hash` — a behavioral
  change is a NEW identity → back to Stage 0.
- Use ExecutionMode.LIVE — PAPER only (`PaperBroker` synthetic fills).
- Backtest NiftyShield over the OSC-preserved window 2016-02-11 → 2022-12-31.
- Tune anything toward returns — the platform certifies safety, not alpha (§1.1).
- Cache a 404 for a date that has not yet closed (the equity miss-cache defect).
- Treat a `STOP`-drill or a broken marks cache as "market closed" — infra
  failures are loud (F3).
- Edit `PAPER_VALIDATION_REPORT.md` by hand — it is generated output; edit
  `PAPER_VALIDATION_REPORT.skeleton.md` and re-assemble (F-B2).
