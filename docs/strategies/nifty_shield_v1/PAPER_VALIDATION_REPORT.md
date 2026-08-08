# PAPER Validation Report — `nifty_shield_v1` (Stage 2, E007)

**Status:** **SKELETON (Phase A complete — harness built and smoke-tested). NOT a validation.** The
E007 grant waits on Phase B's real forward window (≥20 sessions AND ≥30 round-trips, datasheet §10).
**Template:** MM12.5 §9.2 permanent record. **Prompt of record:**
`docs/reports/NIFTY_SHIELD_STAGE2_PAPER_VALIDATION_IMPLEMENTATION_PROMPT.md`.

---

## 1. Identity (frozen, recorded)

| Field | Value |
|---|---|
| `strategy_id` | `nifty_shield_v1` |
| `code_ref` | **`89fcdd6`** (Ledger E006 re-cert) |
| `config_hash` | `c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6` |
| Contract version | `1.0` |
| Datasheet of record | `docs/strategies/nifty_shield_v1/datasheet.md` (§7 risk, §9 gates, §10 RT convention) |

## 2. Window (Phase B — to be completed)

| Field | Value |
|---|---|
| Window dates | **[FILL AT CLOSE]** |
| Sessions | **[count] / ≥20 required** |
| Completed round-trips | **[count] / ≥30 required** (or §7.3 60-session escape, ledgered) |
| Platform commit the window ran on | **[FILL]** |
| Restarts + causes | **[FILL]** |
| Anomalies + dispositions | **[FILL]** |

## 3. Phase A status — harness, wiring, smoke (2026-08-08)

Phase A built the missing execution composition (the prompt's "the running platform is the test"
presumed it; it did not exist — see §7 findings):

| Deliverable | Status | Where |
|---|---|---|
| E7-1 `build_runner` publish_hook_factory + checkpoint + handler_factory + mode | Done | `scripts/fno_runner.py` |
| E7-2 DS2-4 journaled publish hook | Done | `scripts/nifty_shield_paper/journal_hook.py` |
| B datasheet §9 gates config | Done | `core/execution/options/nifty_shield_gates.py` |
| E7-4 option-marks feed (no synthetic fills) | Done | `core/execution/options/nifty_shield_marks.py` |
| A execution composition (groups/marks/sizing/margin) | Done | `core/execution/options/nifty_shield_handler.py` |
| D5 per-bar exit driver | Done | `core/execution/options/nifty_shield_handler.py` |
| A entry-point runner | Done | `scripts/nifty_shield_paper_runner.py` |
| C journal-audit tool | Done | `scripts/nifty_shield_paper/audit.py` |
| D risk-metrics report | Done | `scripts/nifty_shield_paper/metrics_report.py` |
| E telemetry archive | Done | `scripts/nifty_shield_paper/telemetry_archive.py` |
| F margin evidence journaling (SPAN+ELM) | Done (wired; live-marks demo is Phase B) | handler `_journal_margin` |
| One-session smoke run | **PASS** | `scripts/nifty_shield_paper_smoke.py` |

**Smoke run evidence (2026-08-08, deterministic synthetic session):** fact published
(`produced_by=live`), source emitted the structure, handler assembled + filled at marks, margin
journaled, structure closed at the 15:15 hard exit, ledger + journal + telemetry produced.
Journal audit: 1 structure entered + closed, **guard events 0**, reverse divergence none.
Risk metrics: RT=1, conversion 1.00. Telemetry clean.

**Tests:** `tests/execution/test_nifty_shield_paper_execution.py` (8) +
`tests/nifty_shield_paper/test_evidence_tools.py` (11) — 19 green at Phase A close.

## 4. The seven §4.2 evidence items (Phase B fills these)

1. **Session evidence** — [≥20 sessions AND ≥30 RTs, datasheet §10 convention: 1 RT = 1 structure fully closed].
2. **Guard cleanliness** — `STRATEGY_ERRORS = STRATEGY_QUARANTINE_EVENTS = SIGNAL_CONTRACT_REJECTIONS = 0`
   across the window. One event fails the stage (§7.6). [FILL from `scripts/nifty_shield_paper/audit.py`].
3. **Journal audit** — every emitted signal → fill or journaled rejection; divergence one-directional;
   no reverse divergence. [FILL from `audit_window(...)`].
4. **Risk metrics report** — RT count, win rate, avg win/loss in R, profit factor, max DD (Rs, %),
   peak gross exposure, peak margin utilization, signal→fill conversion with per-gate rejection
   breakdown, guard counters. PnL facts are owner's judgment, not pass/fail. [FILL from
   `risk_metrics_report(...)`].
5. **Telemetry archive** — per-session `RuntimeMetric` snapshots + heartbeat continuity; a telemetry
   gap = the session does not count. [FILL from `archive_session(...)`].
6. **Margin evidence** — every entry passed the margin gate with `NseMarginEngine` SPAN + ELM
   journaled on undefined-risk legs against real option marks (E7-4). [FILL from journal `ENTRY_MARGIN`].
   **Note:** if no SPAN snapshot is present for a session the engine falls back to flat-rate
   `MarginTracker` (journaled `engine=MarginTracker`) — such a session does not satisfy §7.7's
   SPAN+ELM requirement and must be flagged.
7. **Kill-switch drill** — one operator drill mid-window (E7-5): activate the kill switch, confirm
   entry signals blocked + journaled, confirm kill-switched-but-running posture, restart per the
   runbook draft. Capture journal + telemetry. [FILL].

## 5. Replay evidence (§4.2 replay row)

[FILL — ≥1 recorded session re-driven through the same composition root in REPLAY; signal stream
byte-identical, ledger deterministic fields (symbol, side, quantity, fill price, signal_id) match,
standing exclusions only (`broker_id` UUIDs, journal wall-clock).]

## 6. Regression suite at the run commit

[FILL — full platform regression suite green at the window's platform commit; confirm the standing
pre-existing `tests/g1/test_g1_closure_guard.py` failure on `main` is the ONLY red and is not
strategy-attributable (E007 acceptance #8).]

## 7. Findings and dispositions (Phase A)

1. **The execution layer was NOT wired** (prompt's "None new — the running platform is the test"
   was not yet true): `assemble_group`, `NiftyShieldExitManager`, `nifty_shield_sizing.*` were
   referenced only by tests. PAPER fills priced option legs at the underlying's bar close (E7-4 was
   unimplemented) and no structure could ever close (no round-trips). **Disposition:** built as
   Phase A (handler composition, marks feed, exit driver). Reported per §0, not silently fixed.
2. **Stage-1 sizing helper units mismatch:** `structure_margin_over_engine` passes units-as-lots to
   the margin engines (75× overstatement vs the real convention `get_incremental_margin(symbol,
   lots, price, lot_size)`). **Disposition:** the handler builds its own correct callable; the
   helper is left for the Stage-1 test that encodes its convention (documented, not silently changed).
3. **Handler margin-gate units bug for F&O option books:** the inherited `_check_margin_budget`
   computes used margin via `MarginTracker.get_exposure` which treats option `position.quantity`
   as lots (overstate by lot_size). **Disposition:** `NiftyShieldExecutionHandler._check_margin_budget`
   overrides the gate for its own strategy (group-derived used margin at real units); the base
   handler is unchanged.
4. **E006 DS2-2 carry-forward note #1:** the driver latches `_published_sessions` outside the hook's
   try/except, so a raised publish latches the session. **Disposition:** not changed in Phase A
   (platform seam); the E7-2 journal wrapper records a durable `FACT_PUBLISH_SKIPPED` line on a
   raised/not-ready publish, and the journal audit makes the skipped session visible — the carry-forward
   note's resolution.
5. **E7-4 in Phase B:** the smoke run uses a deterministic `StaticMarksSource`; the LIVE window must
   wire `ChainSnapshotMarksSource` (real Upstox V3 chain cache) and journal any missing-mark gate
   outcome. The missing-mark path is already a journaled entry-skip (no synthetic fallback).
6. **F3 — marks-cache failures are LOUD (review fix, pre-Phase-B).** `ChainSnapshotMarksSource`
   now raises `MarksSourceUnavailable` on a missing/corrupt/unreadable cache (the repo's documented
   "bare except turns 'we failed' into 'the source doesn't have it'" pitfall), returns `{}` only for
   a VALID cache with no rows (market closed). `check_available()` is a startup gate the runner
   calls before a live window — a misconfigured cache refuses to start. A mid-window outage is
   journaled CRITICAL at entry and stops the loop from the exit driver.
7. **F2 — R base PINNED before the window (review fix).** R = structure realized PnL (Rs) ÷ the
   source's declared `risk_r` (Rs; datasheet §7: sl_distance × 75 × declared lots) → "Rs per
   declared-risk-Rs-unit", computed at DECLARED lots. `risk_r` is journaled per entry (None if the
   source/regression ever omits it), and the metrics report surfaces R columns as **vacuous
   (None), never silently 0.0** (`r_normalized_structures` counts the computable samples).

## 8. Pinned conventions (decide before you see the count — §10 discipline)

| Convention | Pin | Where |
|---|---|---|
| Round-trip | 1 RT = 1 structure fully closed (iron fly = 1 RT); delta hedge is not an RT | datasheet §10 |
| R base (F2) | R = structure PnL (Rs) ÷ declared `risk_r` (Rs); declared-lots basis | this report §7.7 |
| Max DD gate | Rs 30,000 single day → handler gate = 30 000 ÷ initial_capital | datasheet §9 / `nifty_shield_gates.py` |
| Marks infra (F3) | cache-unavailable = loud (refuse to start / CRITICAL); valid-empty = market closed | `nifty_shield_marks.py` |

## 9. Carry-forward provenance (rides every session, E005)

The DayType regime models are the retired `D:\BOT\root` `v2.0-train_thru2025` models reused as-is,
**not** retrained on F:\Nifty — surfaced here, not buried; each fact row carries `trained_on`.

## 10. Hand-back / sequencing

- **E007 does not begin Stage 3.** LIVE CANDIDATE (E008) infrastructure (MM14 reconciliation) is
  built only when a candidate reaches Stage 3 — never ahead of need.
- **Phase B operations:** run `scripts/nifty_shield_paper_runner.py` each trading session; publish
  the 13:00 fact (the hook), trade the structure, flat by 15:15; capture journal + ledger +
  telemetry; run the mid-window kill-switch drill; assemble this report and hand back for Claude's
  review + the operator's E007 grant.
