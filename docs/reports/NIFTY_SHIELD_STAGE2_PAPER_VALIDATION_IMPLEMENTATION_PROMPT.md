# NiftyShield Stage 2 — PAPER VALIDATED (E007) Implementer Prompt

**For:** DeepSeek V4 (implementer). **Reviewer:** Claude (empirical review only, never implements gate deliverables). **Grantor:** operator / Technical Lead (files Ledger **E007**).
**Strategy:** `nifty_shield_v1` — identity **FROZEN** at `code_ref 89fcdd6`, `config_hash c5b722ff…536c` (Ledger E006, 2026-08-08).
**Governing spec:** `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §4.2, §7.3–§7.9, §9.2.
**Datasheet of record:** `docs/strategies/nifty_shield_v1/datasheet.md` §7 (risk declaration), §9 (gate config), §10 (round-trip convention — **pinned**), §11 (the §7.7 real-marks obligation is the open Stage-2 item).
**Prior packages:** Stage-1 CONFORMANCE (`NIFTY_SHIELD_STAGE1_CONFORMANCE_REPORT.md`, E005), Stage-2 prerequisite (`NIFTY_SHIELD_STAGE2_PREREQ_HAND_BACK.md`, E006).

---

## 0. The one-sentence objective

Produce a **PAPER Validation Report** (§9.2) proving `nifty_shield_v1` *behaves* — end-to-end through the real composition root against real market data at **zero capital** — across the MM12.5 §4.2 seven evidence items, so the Technical Lead can grant **PAPER VALIDATED (E007)**.

> **"None new — the running platform is the test" (§4.2 Required tests).** This stage adds **NO strategy code.** The strategy package `strategies/nifty_shield_v1/` and its `config_hash` are frozen by identity. Every code deliverable below is **composition-root / runner / evidence-tooling** code — platform code, not strategy code. **Any behavioral edit to the frozen package is a new identity → back to Stage 0** (§5.2). If you believe the strategy must change to pass, **stop and report** — that is a finding, not a fix.

---

## 1. Hard invariants and prohibitions (read before touching anything)

1. **Identity is frozen.** Do not edit `strategies/nifty_shield_v1/` in any way that moves `config_hash` or changes the emitted signal stream. The re-cert `code_ref` is `89fcdd6`; the PAPER window runs at this identity.
2. **`ExecutionMode.PAPER` only.** No LIVE Upstox order routing. `PaperBroker` synthetic fills. `Mode.LIVE + ExecutionMode.PAPER` is the rung (real startup gate, real market data, empty broker book, no capital) — `fno_runner.build_runner(execution_mode=ExecutionMode.PAPER)`.
3. **`GuardedSignalSource` wrap is unconditional** (ADR-020 execution) — `build_runner` already does this; do not bypass it.
4. **OSC prohibition.** Never backtest NiftyShield over the OSC-preserved unread index-options window **2016-02-11 → 2022-12-31.** Forward PAPER *replaces* the historical read — that is the entire point of this stage.
5. **No P&L as a pass/fail criterion.** PnL facts are recorded for the owner's judgment (§7.4.2) but the platform certifies **safety, not alpha** (§1.1). Do not tune anything toward returns.
6. **Frozen corpus is not regenerated.** The Stage-1 conformance corpus stays byte-identical; `vix_at_checkpoint` is not backfilled into it (that would void E006).
7. **One guard event fails the stage.** `STRATEGY_ERRORS`, `STRATEGY_QUARANTINE_EVENTS`, `SIGNAL_CONTRACT_REJECTIONS` must be **0** across the entire window (§7.6). A certified strategy has no excuse at the boundary — if one fires, the window fails and you report it; you do not suppress it.

---

## 2. Decisions to ratify (operator, before implementation)

Each is stated with a recommendation. Do not implement until ratified.

| # | Decision | Recommendation |
|---|---|---|
| **E7-1** | **Composition-root wiring seam.** Where does the DS2-2 publish hook get wired for PAPER? | Extend `fno_runner.build_runner` with a `publish_hook_factory: Optional[Callable[[Any], Callable]]` + `publish_checkpoint_time: Optional[time]`, mirroring the existing `rebalance_hook_factory` pattern, and pass them into `LoopDriver(publish_hook=…, publish_checkpoint_time=…)`. Runner code only — no strategy edit. Checkpoint = **13:00 IST** (`time(13, 0)`). |
| **E7-2** | **DS2-4 journaling wrapper** (Claude's E006 review note #2: the driver *discards* the hook's return dict). Where does a not-ready / skipped-session line get journaled? | Wrap `make_driver_hook(db_path)` (from `scripts/daytype/publish_live_fact.py`) at the composition root so the wrapper inspects the returned dict and writes a journal line on `{"ready": False}` (F2 NULL-VIX skip, DS2-4). The driver stays journal-agnostic; the wrapper owns journaling. |
| **E7-3** | **Data source for the window vs the replay-evidence item.** | Forward window runs on the **live** `LiveDuckDBMarketDataProvider` (real sessions). Separately, the §4.2 replay-evidence item re-drives **≥1 recorded session's bar corpus** through the same composition root in REPLAY and diffs the signal stream + ledger deterministic fields byte-identical (standing UUID/wall-clock exclusions). Both are required; they are different artifacts. |
| **E7-4** | **Option marks for PAPER fills** (§7.7 real-marks obligation, datasheet §11 open item). | `PaperBroker` fills against **real Upstox V3 option-chain marks** flowing through the market-data provider for the struck legs — **not** synthetic/flat-IV marks. The external-backtest Sharpe 9.40 was flagged optimistic precisely because it used synthetic marks; PAPER must not repeat that. If real option marks for a struck leg are unavailable at fill time, that is a journaled gate outcome to audit, not a synthetic fallback. |
| **E7-5** | **Kill-switch drill** (§7.8, one operator drill in-window). | One scheduled drill mid-window: activate the kill switch, confirm entry signals blocked + journaled, confirm the kill-switched-but-running posture (heartbeat/telemetry alive), restart per the runbook draft. Capture the journal + telemetry around the drill as evidence. |
| **E7-6** | **Round-trip shortfall policy** — reaffirm datasheet §10. | No new decision; **§10 is already pinned**: ≥20 sessions **AND** ≥30 RT; 1 RT = one *structure* fully closed (iron fly = 1 RT); within-position delta hedge is not an RT; expected ~35–45 sessions to floor. If 30 RT not reached by **60 sessions**, take the §7.3 escape: accept the 60-session window with the shortfall **ledgered as an accepted deviation, visible forever**. Deciding after seeing the count is prohibited. |

---

## 3. Structure — Phase A (buildable now) / Phase B (accrues over forward calendar time)

**This stage cannot be completed in one sitting.** The evidence is ≥20 real trading sessions and ≥30 round-trips — roughly **2 calendar months** of live market data (datasheet §10). Split accordingly:

- **Phase A — Harness + tooling + report skeleton (build now, reviewable now).** All code deliverables (§4 A–F below), the report skeleton (§4 I), and a one-session smoke run proving the wired pipeline emits → guards → sizes → margins → fills → ledgers → journals → telemetry end-to-end for a single live (or replayed) session. Claude reviews Phase A before the window opens.
- **Phase B — Operate the forward window (accrues over ≥20 sessions).** Run the PAPER deployment each trading session (publish the 13:00 fact via the hook, trade the structure, flat by 15:15), accumulate the ledger/journal/telemetry archive, run the mid-window kill-switch drill, then assemble the completed report (§4 G, H, I) and hand back for review + the E007 grant.

**Do not claim Stage 2 done at the end of Phase A.** Phase A produces a *harness and a proof it runs*, not a validation. The grant waits on Phase B's real window.

---

## 4. Deliverables (map 1:1 to the §4.2 seven evidence items)

| § | Deliverable | Maps to §4.2 item | Phase |
|---|---|---|---|
| **A** | **PAPER runner wiring** — `build_runner` extended per E7-1; the DS2-4 journal wrapper per E7-2; a thin entry-point script (or extend `scripts/fno_runner.py`'s main) that composes: `nifty_shield_v1` source → `GuardedSignalSource` → `LoopDriver` with `publish_hook`(13:00) → `ExecutionHandler(PAPER)` → `PaperBroker` → ledger + journal + telemetry. Runner/composition code only. | (whole pipeline) | A |
| **B** | **Risk-gate configuration from the declaration** — wire the handler gates to datasheet §9 **exactly**: drawdown gate = Rs 30,000 single / Rs 150,000 5-day streak; daily-trade-limit = 1 structure/session; max-positions = 1 (`_has_open_trade_today`); margin budget = 25% via `NseMarginEngine`; Greek gate = \|Δ\|>500 flatten (close-only, D1). The strategy is validated **against its own promises** (§7.4.1). | (2)(4)(6) | A |
| **C** | **Journal-audit tool** (§7.4.4) — from the ledger: trace every emitted signal → fill **or** journaled gate-rejection; quantify shadow-state divergence and assert it is **one-directional only** (strategy believes in rejected entries). Any *reverse* divergence is a platform defect that **halts the pipeline for everyone** — report immediately, do not proceed. | (3) | A (tool), B (run) |
| **D** | **Risk-metrics report generator** (§7.4.2) — from the ledger: RT count, win rate, avg win/loss in R, profit factor, max DD (Rs, %), peak gross exposure, peak margin utilization, signal→fill conversion with per-gate rejection breakdown, guard counters. | (4) | A (tool), B (run) |
| **E** | **Telemetry archive** — per-session `RuntimeMetric` snapshots + heartbeat continuity (§7.2); assert `BARS_PROCESSED`/`LOOP_ITERATIONS` session-consistent, `SIGNALS_RECEIVED/ROUTED/EXECUTION_CALLS` mutually consistent, guard counters 0, heartbeats gap-free. A telemetry gap = the session does not count. | (5) | A (capture), B (accrue) |
| **F** | **Margin evidence** (§7.7, datasheet §11 open item) — every entry passes the margin gate with **`NseMarginEngine`-computed SPAN + ELM figures journaled**, on undefined-risk legs, against **real option marks** (E7-4). This closes the MM12.4 named limitation for the first F&O candidate. | (6) | A (wired), B (demonstrated live-marks) |
| **G** | **End-to-end replay evidence** — ≥1 recorded session re-driven through the real composition root; emitted signal stream byte-identical, ledger deterministic fields (symbol, side, quantity, fill price, signal_id) match, standing exclusions only (`broker_id` UUIDs, journal wall-clock). PaperBroker fills are deterministic → exact diff. | (replay row) | B |
| **H** | **Kill-switch drill capture** (E7-5 / §7.8). | (7) | B |
| **I** | **PAPER Validation Report** (§9.2 permanent record) — window dates, platform commit the window ran on, identity triple (`nifty_shield_v1`, `89fcdd6`, `c5b722ff…536c`), all seven evidence items assembled, restarts + causes, anomalies + dispositions, regression-suite-green attestation at the run commit. | (documentation) | A (skeleton), B (complete) |

---

## 5. Acceptance gate (what makes E007 grantable — all must hold)

1. **Window**: ≥20 NSE trading sessions **AND** ≥30 completed round-trips (datasheet §10 convention), OR the §7.3 60-session escape with the shortfall ledgered.
2. **Guard cleanliness**: `STRATEGY_ERRORS = STRATEGY_QUARANTINE_EVENTS = SIGNAL_CONTRACT_REJECTIONS = 0` across the whole window (§7.6). One event = fail.
3. **Journal audit**: every emitted signal traced to fill or journaled rejection; divergence one-directional; no reverse divergence.
4. **Drawdown**: declared max DD (Rs 30,000 / Rs 150,000) never breached — the handler drawdown gate tripping **is** the breach (§7.4.3). No carve-out.
5. **Margin**: margin gate exercised on **every** entry with real SPAN + ELM journaled against real option marks (§7.7).
6. **Kill-switch drill** completed and captured.
7. **Replay**: ≥1 session byte-identical end-to-end.
8. **Regression**: full platform regression suite green at the platform commit the window ran on (recorded in the report). Note the standing pre-existing `test_g1_closure_guard` failure on main is unrelated — confirm it is the *only* red and that it is not strategy-attributable.

**A strategy-attributable restart resets the session-window clock** (§4.2). Platform/ops restarts do not (recovery is a certified feature, §7.3).

---

## 6. Role split and sequencing

- **DeepSeek** implements Phase A, operates Phase B, assembles the report. Writes nothing to the frozen strategy package.
- **Claude** reviews Phase A empirically (runs the smoke session, inspects the wiring diff, verifies gates match §9, confirms no strategy-package edit) before the window opens, and reviews the completed report after Phase B.
- **Operator / Technical Lead** grants **E007** (PAPER VALIDATED) and files the ledger entry after review. The grant records window dates, run commit, identity triple, and the seven evidence items. **Claude does not grant.**
- **E007 does not begin Stage 3.** LIVE CANDIDATE (E008) is a separate package; its MM14 broker-reconciliation / margin-reconciliation infrastructure is built **only** when the candidate reaches Stage 3 — never ahead of need.

## 7. Carry-forward notes (do not lose)

- **DS2-2 review note #1 (E006):** `_published_sessions.add()` sits outside the hook try/except → a genuine exception at the 13:00 tick latches the session with no retry (late/backfilled 13:00 bars won't republish). Watch for this in Phase B; a session that silently fails to publish its fact will simply produce no entry (DS2-4 skip) — the journal audit (§4 C) must make that visible, not hide it.
- **DS2-3 semantics (E006 standing note):** the certified VIX gates (skip 20 / reduce 16 / iron-fly 14) now act on a **13:00** intraday VIX in live rows — a live-only behavior **never exercised in conformance**. PAPER is where it is first observed. It is **not** claimed equivalent to Stage-1 EOD-VIX gating; the report records what the intraday gate actually did.
- **Provenance caveat (E005, rides forever):** the DayType regime models are the retired `D:\BOT\root` `v2.0-train_thru2025` models reused as-is, **not** retrained on F:\Nifty; the caveat rides each fact row via `trained_on`. The PAPER report must surface this, not bury it. A retrain-on-F:\Nifty is a separate deferred task, not part of E007.
- **LOW-2 (E005):** `min_lots=1` floor means the margin clamp can shrink but never *prevent* a trade; the handler margin gate is the backstop. This is a Stage-3 capital-plan note; the PAPER report should show the margin gate is in fact the effective backstop.
