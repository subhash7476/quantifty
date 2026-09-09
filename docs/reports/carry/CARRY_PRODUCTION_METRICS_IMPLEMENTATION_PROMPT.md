# Carry Production-Metrics — Implementer Prompt (DeepSeek)

**Role:** you implement; Claude reviews. Work on branch `carry-production-metrics-357944`.
**Authority:** this prompt supersedes the original 4-phase plan, which was NO-GO
(`CARRY_PRODUCTION_METRICS_PLAN_REVIEW.md`). Build **only** Phase A + Phase B below.
**Discipline:** TDD (test → fail → minimal pass → refactor). No hand-edited numbers in any
report. Read every file before editing it. Do not touch frozen construction
(`compute_target_book`/`compute_deltas`) or `run_sealed.py`.

---

## Non-negotiable preconditions (the review's blocking findings)

- **C1 — never run the strategy over SEALED.** SEALED metrics are **ingested** from the frozen
  `docs/reports/CARRY_SEALED_SNAPSHOT.json`. `CARRY_SEALED_READ_PROTOCOL.md` §2 is one-shot:
  "no re-run, no second look, for any reason." Regenerating SEALED = protocol breach.
- **C2 — the LoopDriver+hook path is not return-validated.** It is smoke-tested at 3 dates
  only. You must reconcile it against `parity_check.py` (below) before any metric is trusted.
- **C3 — the hook does not compute P&L.** `_build_fill` fills at synthetic `price=1.0`
  (`carry_rebalancer.py`), so the hook path yields **structural** metrics only (fees, slippage,
  turnover, book, concentration, margin). **Returns/drawdown are computed analytically** from
  the captured book × research `signals.fwd_ret_1m`, exactly as `parity_check.py:130-255` does.
  Do **not** read returns from the position tracker's equity.
- **H1 — do not trust `fill.fee`.** It blends fees+slippage. Use the already-built
  `summarize_rebalance(deltas, trade_date)` → `RebalanceMetrics` (in `carry_rebalancer.py`,
  tested in `tests/portfolio/test_carry_metrics.py`) for all cost decomposition.

Already done (do not rebuild): `RebalanceMetrics`, `summarize_rebalance`, `_execute_deltas`
returns metrics, `test_carry_metrics.py`. 38 carry tests green.

---

## Phase A — instrument + historical metrics

### A1. Metrics DB schema + writer — `core/execution/portfolio/carry_metrics_db.py`
DuckDB at `data/signal_engine/carry/production.duckdb`. Tables (pin these exactly):

- `run_metadata(run_id TEXT PK, git_commit TEXT, generated_at TIMESTAMP, window_label TEXT,
  window_lo DATE, window_hi DATE, gross_exposure DOUBLE, params_json TEXT,
  determinism_hash TEXT, source TEXT)` — `source ∈ {'replay','snapshot'}`.
- `rebalance_summary(run_id, formation_date DATE, n_long INT, n_short INT,
  traded_value DOUBLE, turnover DOUBLE, fees_total DOUBLE, slippage_total DOUBLE,
  fee_brokerage DOUBLE, fee_stt DOUBLE, fee_exchange_txn DOUBLE, fee_sebi_fee DOUBLE,
  fee_stamp_duty DOUBLE, fee_gst DOUBLE, top3_conc DOUBLE, hhi DOUBLE,
  margin_util_pct DOUBLE, PRIMARY KEY(run_id, formation_date))`.
- `rebalance_positions(run_id, formation_date DATE, underlying TEXT, target_side TEXT,
  target_cap DOUBLE, z_carry_neut DOUBLE, quintile INT, action TEXT, suppressed BOOLEAN)`.
- `equity_curve(run_id, formation_date DATE, cum_net_ret DOUBLE, drawdown_pct DOUBLE,
  PRIMARY KEY(run_id, formation_date))` — computed analytically (C3), not from tracker.

Writer: idempotent create; append per run_id; a `determinism_hash` over the sorted
`rebalance_summary` rows for the run. TDD each method against an in-memory/temp DB.

### A2. Metrics sink on the hook — edit `CarryRebalancerHook.__init__`
Add optional `metrics_sink: Optional[Callable] = None`, default `None` (keeps 36 existing
tests green — verify). In `_execute_deltas`, after computing `metrics`, if a sink is present
call it with a single record:
`sink(formation_date, deltas, target, metrics, capital_state)`
where `capital_state` is the `CapitalState` already derived in `_execute`. The sink is the
**only** new behavior; do not change fills or construction. TDD: a fake sink receives one
record per formation with the expected `RebalanceMetrics`.

### A3. Replay harness — `scripts/carry_paper_replay.py`
Drive the **real** path: `DailyBhavcopyProvider` + `build_runner(execution_mode=REPLAY,
rebalance_hook_factory=...)` (follow `carry_integration_check.py` wiring, full windows) over
`TRAIN 2016-03-31→2020-12-31` and `HOLDOUT 2021-01-01→2022-12-31`. The hook's `metrics_sink`
writes structural rows to `production.duckdb`. Compute `equity_curve` analytically: apply
`signals.fwd_ret_1m` (join `signals.duckdb`, `liquid=TRUE`) to each captured book, then fees,
per `parity_check.py`. **Do not run SEALED.**

### A4. SEALED ingest (C1)
Read `docs/reports/CARRY_SEALED_SNAPSHOT.json`; write its window-level results into
`run_metadata`/`rebalance_summary` with `source='snapshot'`. No strategy execution.

### A5. Parity precondition (C2 — GATE, must pass before Phase B)
A `scripts/`-level check (or a test) that the replayed **structural** series — per-formation
turnover, fee drag, and the analytically-derived net spread — reconciles with
`parity_check.py`'s output for TRAIN+HOLDOUT within **15 bp** on net spread (same tolerance as
GATE D). If it fails, **STOP and trace**; do not proceed to Phase B or report any metric.

---

## Phase B — report generator — `scripts/carry_production_report.py`
Read `production.duckdb` → `docs/reports/CARRY_PRODUCTION_METRICS_REPORT.md`, script-generated:
returns vs research snapshot, 6-component fee decomposition, turnover distribution,
concentration (HHI/top-3), drawdown (max DD / Calmar), margin utilization, determinism hash,
and the A5 reconciliation verdict. Re-runnable: regenerates from the DB.

---

## Deferred — do NOT build (separate authorization required)
Facts-refresh scheduler; symbol resolver; live provider; live runner; LIVE gross-exposure
policy (`live_gross_exposure_policy` stays `NotImplementedError`). YAGNI / no funded LIVE
account / bridge §8 guardrail.

## Deliverables for review
Code + tests (all green), `production.duckdb`, `CARRY_PRODUCTION_METRICS_REPORT.md`, and the
A5 reconciliation result. Claude reviews before anything is considered done.
